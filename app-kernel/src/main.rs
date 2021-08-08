
// See ./app-lib/
use app_lib;
use app_lib::rusqlite;
use app_lib::rusqlite::params;

use std::env;
use std::path::{Path,PathBuf};
use std::fs;
use std::process::{Command,Child,Stdio};

use std::sync::atomic::{Ordering,AtomicBool};
use std::sync::{Arc, Mutex};

// sub-modules
mod run_geoserver;

// Globals
static exit_flag: AtomicBool = AtomicBool::new(false);

// Embed data assigned by btool.
const GIT_HASH: Option<&'static str> = option_env!("GIT_HASH");
const COMPILE_TIME_EPOCH_SECONDS: Option<&'static str> = option_env!("COMPILE_TIME_EPOCH_SECONDS");

/**
 * This program coordinates running all processes
 * and re-starting them on failure.
 * 
 * This program also assigns environment variables which sub-programs
 * will use to agree on where data is stored.
 * 
 */
#[cfg(not(tarpaulin_include))]
fn main() {
  exit_flag.store(false, Ordering::Relaxed);
  hide_console_on_windows();
  eprintln!("GIT_HASH={}", GIT_HASH.unwrap_or("SNAPSHOT"));
  move_to_exe_dir();
  if let Ok(current_dir) = env::current_dir() {
    add_to_path(current_dir);
  }
  set_env_vars();

  if !app_lib::license::license_is_valid() {
    if !kernel_compiled_within_48h() {
      std::thread::spawn(|| { invalid_license_kill_t(); });
    }
  }

  initialize_db_schemas();

  copy_subprogram_runtimes_to_app_root();

  update_translations_db_using_app_data_tkeys();

  // Arc & Mutex b/c this will be modified in the main thread AND in poll_launch_req_and_reap_children_t
  let mut children = Arc::new(Mutex::new(spawn_bg_programs()));

  let mut poll_launch_req_children = children.clone();
  std::thread::spawn(move || { poll_launch_req_and_reap_children_t(poll_launch_req_children); });

  // We assume children will open sockets within 1/4 second. May not be possible on all platforms.
  std::thread::sleep(std::time::Duration::from_millis(250));

  run_main_gui_until_exit();
  
  // Kill all children after GUI exits
  loop {
    if let Ok(mut children) = children.lock() {
      for (exe_file, child) in children.iter_mut() {
        if let Err(e) = child.kill() {
          eprintln!("Error killing child: {} ({})", e, exe_file);
        }
      }
      break; // Loop ends when children die
    }
    else {
      eprintln!("Error locking children on main thread!");
      std::thread::sleep(std::time::Duration::from_millis(250));
    }
  }

  exit_flag.store(false, Ordering::Relaxed);

}

fn run_main_gui_until_exit() {
  // Honor a request to run without a GUI when run with RUN_WITHOUT_GUI=1
  if let Ok(val) = env::var("RUN_WITHOUT_GUI") {
    if val.contains("1") || val.contains("t") {
      loop {
        std::thread::sleep( std::time::Duration::from_secs(2) );
        if exit_flag.load(Ordering::Relaxed) {
          break;
        }
      }
      return;
    }
  }

  let gui_exe = if cfg!(windows) { ".\\desktop-mainwindow\\DesktopMainWindow.exe" }
                else { "./desktop-mainwindow/DesktopMainWindow" };
  
  let r = Command::new(gui_exe)
    .stdin(Stdio::inherit())
    .stdout(Stdio::inherit())
    .stderr(Stdio::inherit())
    .spawn();

  match r {
    Ok(mut child) => {
      // Check exit_flag every 2 seconds
      loop {
        std::thread::sleep( std::time::Duration::from_secs(2) );
        if exit_flag.load(Ordering::Relaxed) {
          // Exit b/c invalid license!
          if let Err(e) = child.kill() {
            eprintln!("Error killing main GUI: {}", e);
          }
          break;
        }
        // Also exit if child exited
        match child.try_wait() {
          Ok(Some(status)) => {
            eprintln!("GUI exited with: {}", status);
            break;
          },
          Ok(None) => {
            // Child still executing, continue...
          }
          Err(e) => {
            eprintln!("error attempting to wait on GUI child: {}", e);
          },
        }

      }
    }
    Err(e) => {
      eprintln!("Error spawning main GUI: {}", e);
    }
  }
  
}

#[inline(always)]
fn kernel_compiled_within_48h() -> bool {
  use std::time::{SystemTime, UNIX_EPOCH};
  if let Ok(now_sec) = SystemTime::now().duration_since(UNIX_EPOCH) {
    let now_sec = now_sec.as_secs() as u64;
    if let Ok(binary_created_sec) = COMPILE_TIME_EPOCH_SECONDS.unwrap_or("0").parse::<u64>() {
      if now_sec > binary_created_sec {
        let age_seconds: u64 = now_sec - binary_created_sec;
        return age_seconds < (48*60*60);
      }
    }
  }
  return false;
}

// TODO protect against attacks where the operator just kills this thread?
#[inline(always)]
fn invalid_license_kill_t() {
  eprintln!("Exiting after 600 seconds b/c invalid license...");
  std::thread::sleep( std::time::Duration::from_secs(600) );
  
  eprintln!("Sending SIGKILL to children...");
  exit_flag.store(true, Ordering::Relaxed);

  let mut max_polls_before_exit = 15;
  loop {
    max_polls_before_exit -= 1;
    std::thread::sleep( std::time::Duration::from_secs(1) );
    if !exit_flag.load(Ordering::Relaxed) || max_polls_before_exit < 1 {
      break;
    }
  }
  
  std::process::exit(5);
}

const APP_DATA_TKEYS: include_dir::Dir = include_dir::include_dir!("../app-data-tkeys/");

fn update_translations_db_using_app_data_tkeys() {
  if let Ok(translations_db) = app_lib::open_app_db("translations") {
    for file in APP_DATA_TKEYS.files() {
      if let Some(tkey_file) = file.path().file_name() {
        let tkey_file_s = tkey_file.to_string_lossy();
        if !tkey_file_s.ends_with(".json") {
          continue; // ignore non-json files
        }
        match file.contents_utf8() {
          Some(translation_json) => {
            if let Err(e) = update_translations_db(&translations_db, translation_json) {
              eprintln!("update_translations_db_using_app_data_tkeys Could not create tkeys from {} e = {}", tkey_file_s, e);
            }
          }
          None => {
            eprintln!("update_translations_db_using_app_data_tkeys contents_utf8 appears empty for {}", tkey_file_s);
          }
        }
      }
    }
  }
}

fn update_translations_db(translations_db: &rusqlite::Connection, translation_json: &str) -> std::result::Result<(), Box<dyn std::error::Error>> {
  use app_lib::serde_json;
  use app_lib::serde_json::{Value};
  
  let translation_data: Value = serde_json::from_str(translation_json)?;
  match translation_data {
    Value::Object(data) => {
      for (tkey, values) in data.iter() {
        match values {
          Value::Object(language_translations) => {

            // Now that we have extracted all structired data
            // Insert or update into translations_db
            let r = translations_db.execute(
                "INSERT OR REPLACE INTO tkeys(tkey) VALUES(?1)",
                params![&tkey],
            );
            if let Err(e) = r {
              eprintln!("update_translations_db e1={}", e);
            }

            // Get the rowid of the tkey row
            let r: Result<usize, app_lib::rusqlite::Error> = translations_db.query_row(
              "SELECT rowid FROM tkeys WHERE tkey = ?1",
              params![&tkey],
              |row| row.get(0)
            );
            match r {
              Ok(rowid) => {

                for (lang_code, translation_payload) in language_translations.iter() {
                  let r = translations_db.execute(
                      "INSERT OR REPLACE INTO translations(tkey, lang_code, translated_text) VALUES(?1, ?2, ?3)",
                      params![&rowid, &lang_code, &translation_payload.as_str().unwrap_or("")],
                  );
                  if let Err(e) = r {
                    eprintln!("update_translations_db e3={}", e);
                  }
                }

              }
              Err(e) => {
                eprintln!("update_translations_db e2={}", e);
              }
            }

          }
          other => {
            eprintln!("update_translations_db values is not a Value::Object! {}", other);
          }
        }
      }
    }
    other => {
      eprintln!("update_translations_db translation_data is not a Value::Object! {}", other);
    }
  }

  Ok(())
}


fn copy_subprogram_runtimes_to_app_root() {
  let options = fs_extra::dir::CopyOptions {
    overwrite: false,
    skip_exist: true,
    buffer_size: 64000,
    copy_inside: true,
    content_only: false,
    depth: 16,
  };
  // Geoserver must write config data before executing, see run_geoserver.rs
  let target_geoserver_dir = app_lib::get_app_path(&["geoserver"]);
  
  if let Err(e) = fs_extra::copy_items(
      &[&app_lib::get_app_install_path(&["geoserver"])],
      &target_geoserver_dir,
      &options
  ) {
    eprintln!("error copying files: {}", e);
  }

}

fn spawn_bg_programs() -> Vec<(String, Child)> {
  // Each entry here can return a Result<Child>, errors are printed to stderr.
  return filter_child_results(vec![
    
    spawn_simple_binary(
      if cfg!(windows) { ".\\server-webgui.exe" } else { "./server-webgui" },
      &[]
    ),

    run_geoserver::start(&app_lib::get_app_path(&["geoserver"])),

  ]);
}

fn filter_child_results(child_results: Vec<Result<(String, Child), Box<dyn std::error::Error>>>) -> Vec<(String, Child)> {
  let mut v = vec![];
  for result in child_results {
    match result {
      Ok(child_tuple) => {
        v.push(child_tuple);
      }
      Err(e) => {
        eprintln!("Error spawning child: {}", e);
      }
    }
  }
  return v;
}

fn spawn_simple_binary(bin_path: &str, args: &[&str]) -> Result<(String, Child), Box<dyn std::error::Error>> {
  ensure_file_is_executable(bin_path);

  let c = Command::new(bin_path)
      .args(args)
      .stdin(Stdio::inherit())
      .stdout(Stdio::inherit())
      .stderr(Stdio::inherit())
      .spawn()?;

  register_subprocess(bin_path, c.id() as usize);

  return Ok((bin_path.to_owned(), c));
}

// OS-specific guarantee handler
pub fn ensure_file_is_executable(file: &str) {
  #[cfg(target_os = "windows")]
  {
    return; // can't do anything anyhow
  }
  
  #[cfg(not(target_os = "windows"))]
  {
    use std::os::unix::fs::PermissionsExt;
    if let Ok(meta) = fs::metadata(file) {
      let mut perms = meta.permissions();
      
      perms.set_mode(0o755); // rwx r-x r-x
      
      // Apply new perms
      if let Err(e) = fs::set_permissions(file, perms) {
        eprintln!("Error making file executable: {}", e);
      }
    }
  }

}

const APP_DB_SCHEMAS: include_dir::Dir = include_dir::include_dir!("../app-db-schemas/");

fn initialize_db_schemas() {
  for file in APP_DB_SCHEMAS.files() {
    if let Some(schema_file) = file.path().file_name() {
      let schema_file_s = schema_file.to_string_lossy();
      if !schema_file_s.ends_with(".sql") {
        continue; // ignore non-sql files
      }
      if let Some(db_name) = Path::new(&schema_file).file_stem() {
        let db_name = db_name.to_string_lossy();
        let db_file = app_lib::get_app_db_path(&db_name);

        match app_lib::open_app_db(&db_name) {
          Ok(db_conn) => {
            if let Some(schema_sql) = file.contents_utf8() {
              if let Err(e) = db_conn.execute_batch(schema_sql) {
                eprintln!("[ initialize_db_schemas ] error initializing {}: {}", &db_name, e);
                // This becomes fatal to force new code to be correct 100% of the time
                std::process::exit(5);
              }
            }
            else {
              eprintln!("[ initialize_db_schemas ] Error schema is not utf-8 content: {}", &db_name);
            }
          }
          Err(e) => {
            eprintln!("[ initialize_db_schemas ] app_lib::open_app_db e={}", e);
          }
        }

      }
    }
  }
}

fn set_env_vars() {
  let data_dir = app_lib::get_app_root();
  env::set_var("LOCI_DATA_DIR", &data_dir);
  eprintln!("LOCI_DATA_DIR={}", data_dir.to_string_lossy());

  let exe_dir = determine_exe_dir();
  env::set_var("LOCI_INSTALL_DIR", &exe_dir);
  eprintln!("LOCI_INSTALL_DIR={}", exe_dir.to_string_lossy());  

  // Find every directory named "bin" under CWD (max 4 directories deep)
  // and append to PATH
  append_bins_to_path(&Path::new("."), 4);

}

fn append_bins_to_path(root_dir: &Path, remaining_depth: usize) -> Result<(), Box<dyn std::error::Error>> {
  if remaining_depth < 1 {
    return Ok(());
  }
  for entry in fs::read_dir(root_dir)? {
    let entry = entry?;
    let path = entry.path();

    // Found a "bin" dir, add to beginning of PATH
    if let Some(name) = path.file_name() {
      if name == "bin" || name == "BIN" || name == "Bin" {
        add_to_path(path.clone());
      }
    }

    let metadata = fs::metadata(&path)?;
    if metadata.is_dir() {
      if let Err(e) = append_bins_to_path(&path, remaining_depth - 1) {
        eprintln!("append_bins_to_path e={}", e);
      }
    }
  }
  return Ok(());
}

fn add_to_path(mut directory: PathBuf) {
  let p = env::var_os("PATH").unwrap_or(std::ffi::OsString::new());
  let mut paths: Vec<PathBuf> = env::split_paths(&p).collect();
  if let Ok(c) = directory.canonicalize() {
    directory = c;
  }
  paths.insert(0, directory);
  if let Ok(joined) = std::env::join_paths(paths) {
    env::set_var("PATH", joined);
  }
}

fn determine_exe_dir() -> PathBuf {
  if let Ok(our_exe_path) = env::current_exe() {
    if let Some(exe_parent_dir) = our_exe_path.parent() {
      return exe_parent_dir.to_path_buf();
    }
  }
  // Fall back to PWD
  let our_exe_path =  PathBuf::from(".");
  if let Ok(our_exe_path) = our_exe_path.canonicalize() {
    return our_exe_path;
  }
  return our_exe_path;
}

fn move_to_exe_dir() {
  if let Err(e) = env::set_current_dir(determine_exe_dir()) {
    eprintln!("Error changing directory: {:?}", e);
  }
}


fn hide_console_on_windows() {
    #[cfg(target_os = "windows")]
    {
        if let Ok(val) = env::var("NO_CONSOLE_DETATCH") {
            if val.contains("y") || val.contains("Y") || val.contains("1") {
                return;
            }
        }
        hide_console_on_windows_win();
    }
}

#[cfg(target_os = "windows")]
fn hide_console_on_windows_win() {
    // Check if we are run from the console or just launched with explorer.exe
    let mut console_proc_list_buff: Vec<u32> = vec![0; 16];
    let num_procs = unsafe {
        winapi::um::wincon::GetConsoleProcessList(console_proc_list_buff.as_mut_ptr(), 16)
    };
    //eprintln!("num_procs={:?}", num_procs);
    if num_procs == 1 || num_procs == 2 {
        // We were launched from explorer.exe, detatch the console
        unsafe { winapi::um::wincon::FreeConsole() };
    }
    // Otherwise do nothing, we want console messages when run from the console.
}

fn register_subprocess(exe_file: &str, pid: usize) {
  if let Ok(system_db) = app_lib::open_app_db("system") {
    if let Err(e) = register_subprocess_direct(&system_db, exe_file, pid) {
      eprintln!("register_subprocess e={}", e);
    }
  }
}

fn unregister_subprocess(exe_file: &str, pid: usize) {
  if let Ok(system_db) = app_lib::open_app_db("system") {
    if let Err(e) = unregister_subprocess_direct(&system_db, exe_file, pid) {
      eprintln!("unregister_subprocess e={}", e);
    }
  }
}

fn register_subprocess_direct(system_db: &app_lib::rusqlite::Connection, exe_file: &str, pid: usize) -> Result<(), Box<dyn std::error::Error>> {

  system_db.execute(
    "INSERT INTO processes(exe_file, pid) VALUES(?1, ?2)",
    params![exe_file, pid]
  )?;

  Ok(())
}

fn unregister_subprocess_direct(system_db: &app_lib::rusqlite::Connection, exe_file: &str, pid: usize) -> Result<(), Box<dyn std::error::Error>> {

  system_db.execute(
    "DELETE FROM processes WHERE exe_file = ?1 AND pid = ?2",
    params![exe_file, pid]
  )?;

  Ok(())
}

/**
 * Function returns when exit_flag = true; continuously sleeps and runs poll_launch_req, printing any errors.
 * This function also removes any children that have exited from the system db table "processes".
 */
fn poll_launch_req_and_reap_children_t(children: Arc<Mutex<Vec<(String, Child)>>>) {
  let mut system_db_r = app_lib::open_app_db("system");
  
  let mut i = 0;
  let reap_unk_children_iterations = 5;

  loop {
    i += 1;
    if i > 1000 {
      i = 0;
    }

    std::thread::sleep(std::time::Duration::from_millis(500));

    // End loop if exit_flag is set
    if exit_flag.load(Ordering::Relaxed) {
      break;
    }

    // Check db; if open run poll_launch_req, if closed
    // attempt to open.
    match system_db_r {
      Ok(ref system_db) => {
        
        // Attempt to lock children for modification...
        if let Ok(mut children) = children.lock() {
          // Perform DB poll
          if let Err(e) = poll_launch_req(system_db, &mut children) {
            eprintln!("poll_launch_req_t e1 = {}", e);
          }

          // Record child processes that have exited
          if let Err(e) = poll_dead_children(system_db, &mut children) {
            eprintln!("poll_launch_req_t e2 = {}", e);
          }
          
          // Remove stale children every N iterations
          if i % reap_unk_children_iterations == 0 {
            let mut valid_pids: Vec<usize> = vec![];
            for (exe_file, child) in children.iter() {
              valid_pids.push(child.id() as usize);
            }
            if let Err(e) = reap_unknown_children(system_db, &valid_pids) {
              eprintln!("poll_launch_req_t e3 = {}", e);
            }
          }

        }

      }
      Err(e) => {
        eprintln!("poll_launch_req_t e4 = {}", e);
        system_db_r = app_lib::open_app_db("system");
      }
    }

  }

}

fn poll_dead_children(system_db: &app_lib::rusqlite::Connection, children: &mut Vec<(String, Child)>) -> Result<(), Box<dyn std::error::Error>> {
  use retain_mut::RetainMut;
  children.retain_mut(|(exe_file, child)| {
    match child.try_wait() {
      // Remove child, exited w/ status
      Ok(Some(status)) => {
        eprintln!("{} exited: {}", exe_file, status);

        if let Err(e) = unregister_subprocess_direct(system_db, exe_file, child.id() as usize) {
          eprintln!("poll_dead_children e1={}", e);
        }

        false
      },
      // Keep child, still executing
      Ok(None) => true,
      // Report OS error and keep child
      Err(e) => {
        eprintln!("poll_dead_children e2={}", e);
        true
      }
    }
  });
  Ok(())
}

/**
 * Performs a single poll of the system launch_req table, adding processes to the
 * processes table and the passed in Vec<(String, Child)>.
 */
fn poll_launch_req(system_db: &app_lib::rusqlite::Connection, children: &mut Vec<(String, Child)>) -> Result<(), Box<dyn std::error::Error>> {
  let mut stmt = system_db.prepare(
    "SELECT exe_file, cwd, json_env, json_args FROM launch_req LIMIT 10"
  )?;
  let mut rows = stmt.query([])?;

  while let Some(row) = rows.next()? {
    let exe_file: String = row.get(0)?;
    let cwd: String = row.get(1)?;
    let json_env: String = row.get(2)?;
    let json_args: String = row.get(3)?;
    
    std::unimplemented!(); // TODO implement process launch

  }

  Ok(())
}

/**
 * Removes records in processes table which do not have running PIDs known to the kernel.
 * NB: If two kernels run on the same host at the same time this will cause all process data to
 * be removed. The business assumption is only one kernel will be executing at a time.
 */
fn reap_unknown_children(system_db: &app_lib::rusqlite::Connection, good_pids: &Vec<usize>) -> Result<(), Box<dyn std::error::Error>> {
  
  if good_pids.len() < 1 {
    return Ok(());
  }

  let sql = format!("DELETE FROM processes WHERE pid NOT IN ({})", repeat_vars(good_pids.len()) );
  let parameters = app_lib::rusqlite::params_from_iter(good_pids.iter());

  system_db.execute(&sql, parameters)?;

  Ok(())
}


// Helper function to return a comma-separated sequence of `?`.
// - `repeat_vars(0) => panic!(...)`
// - `repeat_vars(1) => "?"`
// - `repeat_vars(2) => "?,?"`
// - `repeat_vars(3) => "?,?,?"`
// - ...
fn repeat_vars(count: usize) -> String {
    let mut s = "?,".repeat(count);
    // Remove trailing comma
    s.pop();
    s
}




