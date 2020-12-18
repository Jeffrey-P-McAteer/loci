/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use std::path::{Path};
use std::process::{Command, Child};

pub fn start(eapp_dir: &Path, db_file: &Path) -> Child {
  let mut postgres_home = eapp_dir.to_path_buf();
  postgres_home.push("postgres");

  let postgres_exe = if cfg!(windows) {
    format!("{}\\bin\\postgres.exe", postgres_home.to_string_lossy())
  }
  else {
    format!("{}/bin/postgres", postgres_home.to_string_lossy())
  };



  return Command::new(&postgres_exe[..])
        .current_dir(&postgres_home.to_string_lossy()[..])
        .env(crate::LOCI_DB_ENV_KEY, &db_file.to_string_lossy()[..])
        //.args(&split[1..])
        .spawn()
        .expect("postgres command failed to start");

}
