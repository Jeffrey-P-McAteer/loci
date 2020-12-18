/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use std::path::{Path};
use std::process::{Command, Child, Stdio};

pub fn start_dump1090(eapp_dir: &Path) -> Child {

  let mut dump1090_exe = eapp_dir.to_path_buf();
  dump1090_exe.push(if cfg!(windows) { "dump1090.exe" } else { "dump1090" } );

  if !dump1090_exe.as_path().exists() {
    panic!("dump1090_exe does not exist at {}", &dump1090_exe.to_string_lossy()[..])
  }

  return Command::new(&dump1090_exe.to_string_lossy()[..])
        .args(&["--modeac"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("dump1090 command failed to start");
}



