/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use app_dirs;
use rusqlite;

use std::path::{PathBuf};

pub fn get_database_file() -> PathBuf {
  let mut db_dir = app_dirs::app_dir(
    app_dirs::AppDataType::UserData, &crate::APP_INFO, "db"
  ).expect("Could not create db directory");

  db_dir.push("db.db");

  db_dir
}

// Safest way to access db, but slower due to schema checks
pub fn get_init_db_conn() -> rusqlite::Result<rusqlite::Connection> {
  let mut c = get_db_conn()?;
  init_data_schema(&mut c);
  return Ok(c);
}

pub fn get_db_conn() -> rusqlite::Result<rusqlite::Connection> {
  use rusqlite::OpenFlags;
  let db_f = get_database_file();

  let conn = rusqlite::Connection::open_with_flags(
    &db_f,
    OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE |
    OpenFlags::SQLITE_OPEN_NO_MUTEX | OpenFlags::SQLITE_OPEN_SHARED_CACHE
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

pub fn init_data_schema(conn: &mut rusqlite::Connection) {
  if let Err(e) = conn.execute_batch(include_str!("init.sql")) {
    println!("{}:{}: db e={}", std::file!(), std::line!(), e);
  }
}


