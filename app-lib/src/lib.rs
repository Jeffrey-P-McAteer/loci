
use std::path::PathBuf;
use rusqlite::params;

// Re-export some crates
pub use hex;
pub use serde_json;
pub use rusqlite;

// our own crates
pub mod license;
pub mod capi;

#[cfg(test)]
mod tests;


/**
 * Returns owned buffer containing a directory guaranteed to exist but which may not be writeable.
 * panic!()s if LOCI_INSTALL_DIR not set!
 */
pub fn get_app_install_dir() -> PathBuf {
    let install_dir = std::env::var("LOCI_INSTALL_DIR").expect("get_app_install_dir called before LOCI_INSTALL_DIR assigned by kernel!");
    PathBuf::from(install_dir)
}

pub fn get_app_install_path(parts: &[&str]) -> PathBuf {
  let mut path = get_app_install_dir();
  for p in parts {
    path = path.join(p);
  }
  return path;
}

/**
 * Returns owned buffer containing a directory guaranteed to exist and be writeable.
 */
pub fn get_app_root() -> PathBuf {
    let pb = dirs::data_dir().unwrap_or(PathBuf::from("."))
        .join("loci");

    if !pb.as_path().exists() {
        if let Err(e) = std::fs::create_dir_all(&pb) {
            eprintln!("{}:{}: {}", std::file!(), std::line!(), e);
        }
    }

    pb
}

/**
 * Appends given parts to get_app_root() and returns the resulting Path buffer.
 */
pub fn get_app_path(parts: &[&str]) -> PathBuf {
  let mut path = get_app_root();
  for p in parts {
    path = path.join(p);
  }
  return path;
}

/**
 * Returns owned buffer containing a file which may not exist.
 */
pub fn get_app_db_path(db_name: &str) -> PathBuf {
    let pb = get_app_root().join("db");

    if !pb.as_path().exists() {
        if let Err(e) = std::fs::create_dir_all(&pb) {
            eprintln!("{}:{}: {}", std::file!(), std::line!(), e);
        }
    }

    pb.join(format!("{}.db", db_name))
}

/**
 * Returns a Result usually containing a [Connection][rusqlite::Connection] object,
 * which lets you read and write to the database file.
 * Note that many database tables have constraints which MUST be respected,
 * for example no row in `translations` may exist without a `tkeys` row being inserted first.
 * (Which makes orphan and single-use-case translations impossible).
 */
pub fn open_app_db(db_name: &str) -> rusqlite::Result<rusqlite::Connection>  {
  use rusqlite::OpenFlags;
  
  let db_file = get_app_db_path(db_name);

  let conn = rusqlite::Connection::open_with_flags(
      &db_file,
      OpenFlags::SQLITE_OPEN_READ_WRITE
          | OpenFlags::SQLITE_OPEN_CREATE
          | OpenFlags::SQLITE_OPEN_NO_MUTEX
          | OpenFlags::SQLITE_OPEN_SHARED_CACHE,
  )?;

  // https://sqlite.org/pragma.html
  // All of these may be tuned for 1000x gains in either performance or stability (exclusive goals)

  conn.execute_batch(r#"

PRAGMA foreign_keys = ON;
PRAGMA auto_vacuum = FULL;
PRAGMA cache_size = 9046;
PRAGMA case_sensitive_like = false;
PRAGMA count_changes = false;
PRAGMA encoding = "UTF-8";
-- PRAGMA journal_mode = MEMORY;
PRAGMA journal_mode = TRUNCATE;
PRAGMA secure_delete = false;
PRAGMA synchronous = NORMAL;
PRAGMA read_uncommitted = true;

"#)?;

  return Ok(conn);
}


/**
 * Returns owned buffer containing a file which may not exist.
 */
pub fn get_shmem_path(name: &str) -> PathBuf {
    let pb = get_app_root().join("shmem");

    if !pb.as_path().exists() {
        if let Err(e) = std::fs::create_dir_all(&pb) {
            eprintln!("{}:{}: {}", std::file!(), std::line!(), e);
        }
    }

    pb.join(format!("{}.bin", name))
}

/**
 * Returns a Result usually containing a [Shmem][shared_memory::Shmem] object
 * which will allow you to read+write to the same segment of memory as another process.
 * Shared memory structure is defined on a per-use-case basis, so make sure all programs
 * using a given name agree on the format of the data within.
 */
#[cfg(any(target_os="windows", target_os="linux"))] // BIG TODO: figure out shared memory on android, will we just have to be latent?
pub fn open_shmem_file(name: &str, size: usize) -> Result<shared_memory::Shmem, shared_memory::ShmemError> {
  let file = get_shmem_path(name);
  
  let shmem = match shared_memory::ShmemConf::new().size(size).flink(file.as_path()).create() {
    Ok(m) => m,
    Err(shared_memory::ShmemError::LinkExists) => shared_memory::ShmemConf::new().flink(file.as_path()).open()?,
    Err(e) => {
      eprintln!("Unable to create or open shmem flink {} : {}", &file.as_path().to_string_lossy(), e);
      return Err(e);
    }
  };

  Ok(shmem)
}


/* * *
 * The following API functions are less critical and
 * operate with an assumption about DB states outside their
 * own definitions.
 * * */

/**
 * Queries the system DB table properties and returns the value for prop_name
 * or empty string ("") if none found or a DB error occurred.
 */
pub fn get_prop(prop_name: &str) -> String {
  if let Ok(system_db) = open_app_db("system") {
    let r: Result<String, rusqlite::Error> = system_db.query_row(
      "SELECT value FROM properties WHERE key = ?1",
      params![&prop_name],
      |row| row.get(0)
    );
    match r {
      Ok(value) => {
        return value;
      }
      Err(e) => {
        eprintln!("app_lib::get_prop e={}", e);
      }
    }
  }
  // Something blew up
  return String::new();
}

/**
 * Writes to the system DB table properties, returning any errors encountered.
 */
pub fn set_prop(prop_name: &str, prop_val: &str) -> Result<(), Box<dyn std::error::Error>> {
  let system_db = open_app_db("system")?;

  system_db.execute(
    "INSERT OR REPLACE INTO properties(key, value) VALUES(?1, ?2)",
    params![prop_name, prop_val]
  )?;

  return Ok(());
}


/**
 * Uses locale_config to determine current language,
 * then uses the 2-character code to return the value from trans_lang.
 * If no locale information is available, falls back to using "en" as the language.
 */
pub fn trans(tkey: &str) -> String {
  // First check DB for user-set override
  let system_lang_code = get_prop("system_lang_code");
  if system_lang_code.len() > 1 {
    let lang_code = &system_lang_code[0..2];
    let lang_code = lang_code.to_lowercase();
    return trans_lang(&lang_code, tkey);
  }

  // Then check OS locale data
  let l = locale_config::Locale::user_default();
  
  for (opt_name, lrange) in l.tags() {
    let lrange = lrange.to_string();
    if lrange.len() > 1 {
      // trim first 2 chars, see https://docs.rs/locale_config/0.3.0/locale_config/struct.LanguageRange.html
      let lang_code = &lrange[0..2];
      let lang_code = lang_code.to_lowercase();
      return trans_lang(&lang_code, tkey);
    }
  }

  // Finally fall back to "en"
  return trans_lang("en", tkey);
}

/**
 * Queries the translations db translations table for a value matching the
 * language code and tkey. If no matching tkey exists, the function panics, ending the
 * current process. If no matching translation in lang_code for the tkey exists,
 * the function panics.
 * Panicing agressively is a check to ensure _all_ tkeys are translated in the languages
 * we actually use.
 */
pub fn trans_lang(lang_code: &str, tkey: &str) -> String {
  let system_db = open_app_db("translations").expect("Could not open translations db in trans_lang");
  let value: String = system_db.query_row(
    "SELECT translated_text FROM translations WHERE lang_code = ?1 AND tkey =( SELECT rowid FROM tkeys WHERE tkey = ?2 LIMIT 1 )",
    params![lang_code, tkey],
    |row| row.get(0)
  ).expect("Could not query translations for lang_code and tkey, check that all tkeys are registered correctly!");
  return value;
}






// Helper function to return a comma-separated sequence of `?`.
// - `repeat_vars(0) => panic!(...)`
// - `repeat_vars(1) => "?"`
// - `repeat_vars(2) => "?,?"`
// - `repeat_vars(3) => "?,?,?"`
// - ...
pub fn util_repeat_sql_vars(count: usize) -> String {
    let mut s = "?,".repeat(count);
    // Remove trailing comma
    s.pop();
    s
}

