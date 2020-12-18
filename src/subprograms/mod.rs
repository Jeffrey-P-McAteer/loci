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

use std::io::prelude::*;
use std::io::BufReader;

use std::collections::HashMap;

pub mod geoserver;
pub mod postgis;
pub mod rtl_sdr_programs;

pub fn main(loci_exit_f: Arc<AtomicBool>) {
    let eapp_dir = extract_eapp_data();
    println!("eapp_dir={:?}", &eapp_dir);

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

    // for p in &mut processes {
    //   if let Err(e) = p.wait() {
    //     println!("error waiting on child process: {:?}", e);
    //   }
    // }

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
  // if let Err(e) = archive.unpack(&eapp_dir) {
  //   println!("Error extracting eapp tar: {:?}", e);
  // }

  // Instead of having the library extract everything (which may take 5 mins)
  // we go over all entries and only extract new data (files which do not exist).
  let dst = eapp_dir.as_path();
  for entry in archive.entries().unwrap() {
    if let Ok(mut entry) = entry {

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
    rtl_sdr_programs::start_dump1090(eapp_dir)
  }
  else { dummy_proc() };

  let dump1090_stdout = dump1090_p.stdout.take().expect("no dump1090_p.stdout");
  let mut dump1090_stdout = BufReader::new(dump1090_stdout);

  let mut dump1090_record: HashMap<&str, String> = HashMap::new();

  // Iterate all processes, possibly processing stdout and writing information to DB
  loop {
    let mut should_exit = true;
    
    // dump1090
    let dump1090_p_alive = if let Ok(None) = dump1090_p.try_wait() { true } else { false };
    if dump1090_p_alive {
      should_exit = false;

      let mut buf = String::new();
      match dump1090_stdout.read_line(&mut buf) {
        Ok(n) => {
          let read_line = &buf[0..n];
          let read_line = read_line.trim();
          if read_line.starts_with("*") {
            // TODO Save last line as a record
            println!("dump1090_record={:?}", dump1090_record);

            dump1090_record.clear();

            dump1090_record.insert("encoded-packet", read_line.to_string());

          }
          else if read_line.starts_with("Time") {
            dump1090_record.insert("time", (&read_line[6..]).to_string());
          }
          else if read_line.starts_with("Baro altitude") {
            dump1090_record.insert("altitude", (&read_line[15..]).to_string());
          }
          else if read_line.starts_with("CPR latitude") {
            dump1090_record.insert("lat", (&read_line[14..]).to_string());
          }
          else if read_line.starts_with("CPR longitude") {
            dump1090_record.insert("lon", (&read_line[15..]).to_string());
          }
          else if read_line.starts_with("CPR type") {
            dump1090_record.insert("type", (&read_line[9..]).to_string());
          }
          else if read_line.starts_with("RSSI") {
            dump1090_record.insert("rssi", (&read_line[6..]).to_string());
          }
          else if read_line.starts_with("DF:") {
            dump1090_record.insert("id-line", (&read_line[..]).to_string());
          }
          else if read_line.len() > 2 {
            println!("unused dump1090 line = {}", read_line);
          }


        }
        Err(e) => { print!("e={:?}", e); }
      }

    }

    if loci_exit_f.load(std::sync::atomic::Ordering::SeqCst) {
      should_exit = true;
    }

    if should_exit {
      
      if let Err(e) = dump1090_p.kill() {
        println!("Error killng: {}", e);
      }

      break;
    }

  }

}

fn dummy_proc() -> std::process::Child {
  use std::process::{Command, Stdio};
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

