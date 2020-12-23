/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use app_dirs;

use std::path::{Path, PathBuf};
//use std::process::{Command, Child};

use std::env;
use std::{thread, time};
use std::sync::Arc;
use std::sync::atomic::AtomicBool;

use std::process::{Command, Child};

use std::collections::HashMap;

pub mod geoserver;
pub mod postgis;
pub mod dump1090;
pub mod usb_gps_reader;

pub fn main(loci_exit_f: Arc<AtomicBool>) {
    let eapp_dir = extract_eapp_data();
    
    println!("eapp_dir={:?}", &eapp_dir);

    // Create the documented "user-programs" subdirectory if it does not already exist
    let user_programs_dir = eapp_dir.join("user-programs");
    if !user_programs_dir.exists() {
      if let Err(e) = std::fs::create_dir_all(&user_programs_dir) {
        println!("Error creating user-programs: {}", e);
      }
    }

    env::set_var(crate::LOCI_EAPP_DIR_ENV_KEY, &eapp_dir.to_string_lossy()[..]);

    // First we ensure the DB is consistent and assign an environment variable
    // pointing to the file. All languages have bindings to sqlite and
    // sqlite guarantees concurrent access is safe.
    {
      let _c = crate::db::get_init_db_conn();
    }
    let db_file = crate::db::get_database_file();
    env::set_var(crate::LOCI_DB_ENV_KEY, &db_file.to_string_lossy()[..]);
    
    let mut processes = vec![];

    if eapp_enabled("geoserver") {
      processes.push(
        geoserver::start(eapp_dir.as_path(), db_file.as_path())
      );
    }

    if eapp_enabled("postgis") {
      processes.push(
        postgis::start(eapp_dir.as_path(), db_file.as_path())
      );
    }

    // any child apps we want to embed get executed here


    // Now process all files in user_programs_dir. We do not recurse.
    if let Ok(dir_iter) = std::fs::read_dir(&user_programs_dir) {
      for entry in dir_iter {
        if let Ok(entry) = entry {
          let p = entry.path();
          if !p.is_dir() {
            println!("Executing user program: {}", &p.to_string_lossy()[..] );
            match spawn_user_program(&p) {
              Ok(child_p) => {
                processes.push(child_p);
              }
              Err(e) => {
                println!("Error executing user program: {}", e);
              }
            }
          }
        }
      }
    }


    // Write to the DB that child programs have started
    let mut retries = 20;
    loop {
      if let Ok(con) = crate::db::get_init_db_conn() {
        match con.execute(
          "INSERT INTO app_events (name) VALUES (?1)",
          rusqlite::params!["all-subprograms-spawned"]
        ) {
          Ok(_rows) => break,
          Err(e) => {
            println!("db e={}", e);
            thread::sleep(time::Duration::from_millis(200));
            retries -= 1;
          }
        }
      }
      else {
        thread::sleep(time::Duration::from_millis(200));
        retries -= 1;
      }
      if retries < 1 {
        break;
      }
    }

    // Poll loci_exit_f every 200ms and kill children when exit is requested
    loop {
      thread::sleep(time::Duration::from_millis(200));
      let should_exit = loci_exit_f.load(std::sync::atomic::Ordering::SeqCst);
      if should_exit {
        // Kill children
        println!("Killing subprograms...");
        for p in &mut processes {
          if let Err(e) = p.kill() {
            println!("Error killing child process after LOCI_EXIT: {}", e);
          }
        }
        break;
      }
    }

    try_to_kill_privledged_programs();

    println!("All subprograms completed!");

}


fn spawn_user_program(path: &Path) -> Result<Child, Box<dyn std::error::Error>> {
  let eapp_dir = app_dirs::app_dir(
    app_dirs::AppDataType::UserCache, &crate::APP_INFO, "eapp"
  )?;

  let db_file = crate::db::get_database_file();


  if let Some(ext) = path.extension().and_then(std::ffi::OsStr::to_str) {
    match ext.to_lowercase().as_str() {
      "py" => {
        println!("TODO impl python w/ pythonpath");
      }
      "pyz" => {
        println!("TODO impl python zip w/ pythonpath");
      }
      "jar" => {
        println!("TODO impl java w/ classpath");
      }
      unk => {
        println!("Unknown user program extension: {}", unk);
      }
    }
  }

  // Execute path directly, under the assumption the OS
  // is setup to detect + launch the process.
  Ok(
    Command::new(path)
      .env(crate::LOCI_EAPP_DIR_ENV_KEY, &eapp_dir.to_string_lossy()[..])
      .env(crate::LOCI_DB_ENV_KEY, &db_file.to_string_lossy()[..])
      .spawn()?
  )

}


// Run heuristics which may make the system behave more correctly
pub fn try_to_kill_privledged_programs() {
  if cfg!(windows) {
    println!("TODO try_to_kill_privledged_programs");
  }
  else {
    std::process::Command::new("sudo").args(&[
      "--non-interactive", "--", "pkill", "dump1090",
    ]).status().expect("Could not try_to_kill_privledged_programs");
  }
}

pub fn eapp_enabled(prog_name: &str) -> bool {
  if let Ok(programs) = env::var(crate::DISABLED_SUBPROGRAMS) {
    if programs.contains(prog_name) {
      println!("Disabling eapp {} because DISABLED_SUBPROGRAMS={}", prog_name, programs);
      return false;
    }
  }
  println!("Enabling eapp {}", prog_name);
  return true;
}

/**
 * build.rs writes some C code which creates these symbols and adds them to a .lib/.a file we link against.
 * The bytes returned by get_embed_tar_bytes are the eapp zip file that build.py constructs.
 */
extern "C" {
  fn get_embed_tar_bytes() -> *const u8;
  // fn get_embed_zip_len() -> u64; // This is a little broken
  fn get_embed_tar_bytes_end() -> *const u8;
}

// If the tarball is embedded just return pointers to it's data
// Note that while we return a Vec<>, mutating the Vec<> is illegal!
// This Vec<> must be read-only.
#[cfg(feature = "embed-eapp-tar")]
fn get_tar_bytes() -> Vec<u8> {
  return unsafe {
    let embed_length = (get_embed_tar_bytes_end() as *const usize as usize) - (get_embed_tar_bytes() as *const usize as usize);
    //std::slice::from_raw_parts(get_embed_tar_bytes(), embed_length)
    Vec::from_raw_parts(get_embed_tar_bytes() as *mut u8, embed_length, embed_length)
  };
}

// If the tarball is NOT embedded search CWD and then the location of the binary file
// for a file containing "eapp", <target> (win64 of linux64) and ".tar.gz".
#[cfg(not(feature = "embed-eapp-tar"))]
fn get_tar_bytes() -> Vec<u8> {
  use glob;
  use std::io::prelude::*;

  if let Ok(mut curr_exe) = std::env::current_exe() {
    for _ in 0..2 {
      if let Some(exe_dir) = curr_exe.parent() {
        
        let target_name = if cfg!(windows) { "win64" } else { "linux64" };

        // Search under exe_dir

        let glob_str = format!("{}/eapp*.tar.gz", exe_dir.display());
        println!("Looking for eapp tarball under {:?}", &glob_str);

        if let Ok(globiterator) = glob::glob(&glob_str) {
          for entry in globiterator {
            if let Ok(entry) = entry {
              if entry.to_string_lossy().contains(target_name) {
                // We found it!
                println!("Using eapp tarball {:?}", &entry.to_string_lossy()[..]);
                let mut f = fs::File::open(&entry).expect("no eapp file found");
                let metadata = fs::metadata(&entry).expect("unable to read eapp metadata");
                let mut buffer = vec![0; metadata.len() as usize];
                if let Err(e) = f.read(&mut buffer) {
                  println!("Could not read eapp tarball: {}", e);
                }
                return buffer;
              }
            }
          }
        }


      }
      // Jump up one dir and repeat glob search
      if let Some(parent_dir) = curr_exe.parent() {
        curr_exe = parent_dir.to_path_buf();
      }
    }
  }
  std::unimplemented!()
}

fn extract_eapp_data() -> PathBuf {
  use flate2::read::GzDecoder;
  use tar::Archive;

  let eapp_dir = app_dirs::app_dir(
    app_dirs::AppDataType::UserCache, &crate::APP_INFO, "eapp"
  ).expect("Could not create eapp directory");


  let tar_bytes = get_tar_bytes();

  let gz = GzDecoder::new(&tar_bytes[..]);
  let mut archive = Archive::new(gz);

  // Instead of having the library extract everything (which may take 5 mins)
  // we go over all entries and only extract new data (files which do not exist).
  let dst = eapp_dir.as_path();
  for entry in archive.entries().unwrap() {
    match entry {
      Ok(mut entry) => {
        let entry_path = match entry.path() {
          Ok(p) => p,
          Err(_) => continue
        };
        
        let existing_f = dst.join(entry_path);
        if existing_f.exists() {
          //println!("Skipping existing eapp file {}", &existing_f.to_string_lossy()[..]);
          continue;
        }

        println!("Extracting eapp file {}", &existing_f.to_string_lossy()[..]);
        if let Err(_e) = entry.unpack_in(&dst) { 
          //println!("Error unpacking eapp file: {}", e);
        }
      }
      Err(e) => {
        println!("Error unpacking eapp file: {}", e);
      }
    }
  }

  #[cfg(feature = "embed-eapp-tar")]
  {
    // Because we borrowed memory from the .TEXT section we must not free() it -
    // calling mem::forget ensures the underlying memory is not freed.
    std::mem::forget(tar_bytes);
  }

  println!("Done extracting eapp dir.");

  return eapp_dir;
}

pub fn main_privileged(loci_exit_f: Arc<AtomicBool>) {
  // This is run as root/Administrator so as to run programs which
  // talk to hardware (dump1090 and rtl_ais).

  // It MUST not create a database and MUST wait until the non-privledged process has
  // extracted the eapp tar. Also we cannot rely on app_dirs for this directory, so
  // we share it using an environment variable
  let eapp_dir: String;
  match env::var(crate::LOCI_EAPP_DIR_ENV_KEY) {
    Ok(dir) => {
      println!("{}={}", crate::LOCI_EAPP_DIR_ENV_KEY, &dir[..]);
      eapp_dir = dir;
    }
    Err(e) => {
      println!("e={}", e);
      match env::args().nth(1) {
        Some(dir) => {
          println!("arg[1]={}", &dir[..]);
          eapp_dir = dir;
        }
        None => {
          println!("e={}", e);
          println!("Unknown eapp dir in privledged context, aborting...");
          return;
        }
      }
    }
  }

  let eapp_dir = Path::new(&eapp_dir[..]);


  let db_file: String;
  match env::var(crate::LOCI_DB_ENV_KEY) {
    Ok(dir) => {
      println!("{}={}", crate::LOCI_DB_ENV_KEY, &dir[..]);
      db_file = dir;
    }
    Err(e) => {
      println!("e={}", e);
      match env::args().nth(2) {
        Some(dir) => {
          println!("arg[2]={}", &dir[..]);
          db_file = dir;
        }
        None => {
          println!("e={}", e);
          println!("Unknown db file in privledged context, aborting...");
          return;
        }
      }
    }
  }

  let db_file = Path::new(&db_file[..]);

  // Wait until parent creates this file
  loop {
    if db_file.exists() {
      break
    }
    thread::sleep(time::Duration::from_millis(200));
  }

  println!("Executing privledged processes...");


  let mut dump1090_p = if eapp_enabled("dump1090") {
    dump1090::start(eapp_dir)
  }
  else { dummy_proc() };
  let mut dump1090_stdout = dump1090_p.stdout.take().expect("no dump1090_p.stdout");
  let mut dump1090_stdout_buff = vec![];
  let mut dump1090_record: HashMap<&str, String> = HashMap::new();
  let mut dump1090_restart_flag = false;


  let mut usb_gps_p = if eapp_enabled("usb_gps") {
    usb_gps_reader::start(eapp_dir)
  }
  else { dummy_proc() };
  let mut usb_gps_stdout = usb_gps_p.stdout.take().expect("no usb_gps_p.stdout");
  let mut usb_gps_stdout_buff = vec![];
  let mut usb_gps_restart_flag = false;


  // Iterate all processes, possibly processing stdout and writing information to DB
  loop {
    let mut should_exit = true;
    
    if dump1090::poll(&mut dump1090_p, &mut dump1090_stdout, &mut dump1090_stdout_buff, &mut dump1090_record, &mut dump1090_restart_flag) {
      should_exit = false;
    }
    if dump1090_restart_flag {
      println!("Restarting dump1090...");
      if let Err(e) = dump1090_p.kill() {
        println!("Error killing: {}", e);
      }
      dump1090_p = if eapp_enabled("dump1090") {
        dump1090::start(eapp_dir)
      }
      else { dummy_proc() };
      dump1090_stdout = dump1090_p.stdout.take().expect("no dump1090_p.stdout");
      dump1090_record = HashMap::new();
      dump1090_restart_flag = false;
    }

    if usb_gps_reader::poll(&mut usb_gps_p, &mut usb_gps_stdout, &mut usb_gps_stdout_buff, &mut usb_gps_restart_flag) {
      should_exit = false;
    }
    if usb_gps_restart_flag {
      println!("Restarting usb_gps...");
      if let Err(e) = usb_gps_p.kill() {
        println!("Error killing: {}", e);
      }
      usb_gps_p = if eapp_enabled("usb_gps") {
        usb_gps_reader::start(eapp_dir)
      }
      else { dummy_proc() };
      usb_gps_stdout = usb_gps_p.stdout.take().expect("no usb_gps_p.stdout");
      usb_gps_restart_flag = false;
    }


    if loci_exit_f.load(std::sync::atomic::Ordering::SeqCst) {
      should_exit = true;
    }

    //println!("admin poll should_exit={}", should_exit);

    if should_exit {
      
      if let Err(e) = dump1090_p.kill() {
        println!("Error killing: {}", e);
      }

      if let Err(e) = usb_gps_p.kill() {
        println!("Error killing: {}", e);
      }

      break;
    }

  }

}

pub fn dummy_proc() -> Child {
  use std::process::{Stdio};
  if cfg!(windows) {
    Command::new("cmd.exe")
      .arg("/c")
      .arg("echo dummy-proc")
      .stdin(Stdio::null())
      .stdout(Stdio::piped())
      .stderr(Stdio::inherit())
      .spawn()
      .expect("could not start dummy process")
  }
  else {
    Command::new("sh")
      .arg("-c")
      .arg("echo dummy-proc")
      .stdin(Stdio::null())
      .stdout(Stdio::piped())
      .stderr(Stdio::inherit())
      .spawn()
      .expect("could not start dummy process")
  }
}

