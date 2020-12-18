/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use app_dirs;

#[cfg(not(target_os = "windows"))]
use std::{thread, time};

use std::sync::Arc;
use std::sync::atomic::AtomicBool;


#[cfg(not(target_os = "windows"))]
use std::process::Command;

#[cfg(target_os = "windows")]
use std::os::raw::c_ushort;

// This is defined by build.rs for windows targets
#[cfg(target_os = "windows")]
extern "C" {
  fn loci_win_is_administrator() -> bool;
  fn rust_win_runas(cmd: *const c_ushort, args: *const c_ushort, show: i32) -> u32;
}

pub fn we_are_privileged() -> bool {
  #[cfg(target_os = "windows")]
  {
    return unsafe { loci_win_is_administrator() };
  }
  #[cfg(not(target_os = "windows"))]
  {
    use nix::unistd::Uid;
    return Uid::effective().is_root();
  }
}


// Requests that the OS execute this same process,
// passing the eapp dir and database file as args 1 and 2
// and also in the environment variables.

pub fn elevate_privileges(loci_exit_f: Arc<AtomicBool>) {
  // We MUST pass this environment variable to the privledged process.
  // It also must match the value from subprograms/mod.rs

  use std::env;

  let eapp_dir = app_dirs::app_dir(
    app_dirs::AppDataType::UserCache, &crate::APP_INFO, "eapp"
  ).expect("Could not create eapp directory");

  let self_exe = env::current_exe().expect("Could not get self exe file");

  env::set_var(crate::LOCI_EAPP_DIR_ENV_KEY, &eapp_dir.to_string_lossy()[..]);

  let db_file = crate::db::get_database_file();
  
  env::set_var(crate::LOCI_DB_ENV_KEY, &db_file.to_string_lossy()[..]);

  // Re-type these variables
  let eapp_dir = eapp_dir.to_string_lossy();
  let db_file = db_file.to_string_lossy();

  let args: Vec<&str> = vec![
      &eapp_dir[..], &db_file[..]
  ];

  #[cfg(target_os = "windows")]
  {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;

    // Silences a warning; TODO can the win32 API kill a process in here?
    drop(loci_exit_f);

    let mut params = String::new();
    for arg in args.iter() {
        params.push(' ');
        if arg.len() == 0 {
            params.push_str("\"\"");
        } else if arg.find(&[' ', '\t', '"'][..]).is_none() {
            params.push_str(&arg);
        } else {
            params.push('"');
            for c in arg.chars() {
                match c {
                    '\\' => params.push_str("\\\\"),
                    '"' => params.push_str("\\\""),
                    c => params.push(c),
                }
            }
            params.push('"');
        }
    }

    let file = OsStr::new(&self_exe.to_string_lossy()[..])
        .encode_wide()
        .chain(Some(0))
        .collect::<Vec<_>>();

    let params = OsStr::new(&params)
        .encode_wide()
        .chain(Some(0))
        .collect::<Vec<_>>();

    unsafe {
        let show = 1;
        rust_win_runas(
            file.as_ptr(),
            params.as_ptr(),
            show,
        );
    }
  }


  #[cfg(not(target_os = "windows"))]
  {
    //use which;
    let mut child;
    match which::which("gksudo") {
        Ok(_) => {
            child = Command::new("gksudo")
              .arg("-E")
              .arg("--")
              .arg(&self_exe.to_string_lossy()[..])
              .args(&args[..])
              //.env(crate::DISABLED_SUBPROGRAMS, env::var(crate::DISABLED_SUBPROGRAMS).unwrap_or(String::new()))
              .spawn()
              .expect("Could not run admin b/c sub-process failed");
        }
        Err(_) => {
            match which::which("sudo") {
                Ok(_) => {
                    child = Command::new("sudo")
                      .arg("-E")
                      .arg("--")
                      .arg(&self_exe.to_string_lossy()[..])
                      .args(&args[..])
                      //.env(crate::DISABLED_SUBPROGRAMS, env::var(crate::DISABLED_SUBPROGRAMS).unwrap_or(String::new()))
                      .spawn()
                      .expect("Could not run admin b/c sub-process failed");
                }
                Err(_) => {
                    panic!("Cannot run admin because no priv elevation programs exist on this system");
                },
            }
        }
    }

    // Poll exit flag and kill child
    loop {
      thread::sleep(time::Duration::from_millis(200));
      if loci_exit_f.load(std::sync::atomic::Ordering::SeqCst) {
        if let Err(e) = child.kill() {
          println!("error killing child: {:?}", e);
        }
        break;
      }
    }

  }
}



