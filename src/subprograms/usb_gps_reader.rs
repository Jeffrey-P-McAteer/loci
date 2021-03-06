/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use std::path::{Path};
use std::process::{Command, Child, Stdio, ChildStdout};
use std::sync::{Arc, RwLock};
use std::sync::atomic::AtomicBool;

pub fn start_and_poll_until_exit(eapp_dir: &Path, loci_exit_f: &Arc<AtomicBool>, child_pids: &Arc<RwLock<Vec<u32>>>) {
  let mut usb_gps_p = start(eapp_dir);

  if let Ok(mut child_pids) = child_pids.write() {
    child_pids.push( usb_gps_p.id() );
  }

  match usb_gps_p.stdout.take() {
    Some(mut usb_gps_stdout) => {
      let mut usb_gps_stdout_buff = vec![];
      let mut usb_gps_restart_flag = false;

      loop {
        let should_exit = loci_exit_f.load(std::sync::atomic::Ordering::SeqCst);
        if should_exit {
          if let Err(e) = usb_gps_p.kill() {
            println!("Err killing usb_gps_p: {}", e);
          }
        }

        if !poll(&mut usb_gps_p, &mut usb_gps_stdout, &mut usb_gps_stdout_buff, &mut usb_gps_restart_flag) {
          break;
        }

        if usb_gps_restart_flag {
          if let Err(e) = usb_gps_p.kill() {
            println!("Err killing usb_gps_p: {}", e);
          }
          break;
        }
        
      }
    }
    None => {
      println!("Err: no usb_gps_p.stdout");
    }
  }
}

pub fn start(eapp_dir: &Path) -> Child {

  let mut usb_gps_reader_exe = eapp_dir.to_path_buf();
  usb_gps_reader_exe.push(if cfg!(windows) { "usb_gps_reader.exe" } else { "usb_gps_reader" } );

  if !usb_gps_reader_exe.as_path().exists() {
    println!("usb_gps_reader_exe does not exist at {}", &usb_gps_reader_exe.to_string_lossy()[..]);
    return crate::subprograms::dummy_proc();
  }

  return Command::new(&usb_gps_reader_exe.to_string_lossy()[..])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("usb_gps_reader command failed to start");
}


// responsible for checking process stdout and writing to DB.
// The returned value should be "true" if the process is alive,
// or "false" if the process is dead.
pub fn poll(usb_gps_p: &mut Child, usb_gps_stdout: &mut ChildStdout, stdout_buff: &mut Vec<u8>, usb_gps_restart_flag: &mut bool) -> bool {
  use std::io::prelude::*;
  use nmea0183::{Parser, ParseResult};
  
  let usb_gps_p_alive = if let Ok(None) = usb_gps_p.try_wait() { true } else { false };
  if ! usb_gps_p_alive {
    return false;
  }

  let mut parser = Parser::new();

  let mut buff: [u8; 4098] = [0u8; 4098];

  match usb_gps_stdout.read(&mut buff) {
    Ok(n) => {
      if n == 0 { // EOF
        *usb_gps_restart_flag = true;
      }

      // append buff[0..n] to stdout_buff,
      // then read any lines if they exist in stdout_buff.
      stdout_buff.extend_from_slice(&buff[0..n]);

      loop {
        if let Some(line_term_i) = stdout_buff.iter().position(|&r| r == '\n' as u8) {
          { // read from vec + process string
            let read_line_bytes = &stdout_buff[0..line_term_i];
            let read_line = String::from_utf8_lossy(read_line_bytes);
            let read_line = read_line.trim();

            // NMEA packets must end in RN to be parsed
            let read_line = format!("{}\r\n", read_line.trim());

            //println!("read_line={}", &read_line[..]);

            // TODO detect + use _usb_gps_restart_flag when GPS is detected to be broken
            
            for result in parser.parse_from_bytes(read_line.as_bytes()) {
              match result {
                Ok(ParseResult::RMC(Some(rmc))) => {
                  //println!("Got RMC packet: {:?}", rmc);
                  let r = crate::db::execute(
                    1, 0,
                    "INSERT INTO pos_reps (id, lat, lon, src_tags) VALUES (?1, ?2, ?3, \"usb-gps,self-posrep,\")",
                    rusqlite::params![
                      "SELF",
                      rmc.latitude.as_f64(),
                      rmc.longitude.as_f64(),
                    ]
                  );
                  if let Err(e) = r {
                    println!("{}:{} {}", std::file!(), std::line!(), e);
                  }
                },
                
                Ok(_p) => {
                  //println!("Got other packet: {:?}", p);
                }
                Err(_e) => {
                  //println!("nmea parse e={}", e);
                }
              }
            }


          }
          { // mutate (trim) vec
            stdout_buff.drain(0..line_term_i+1);
          }

        }
        else {
          break; // no '\n'
        }
      }

      // remove '\r' and '\n' chars in the buffer for safer parsing next poll()
      stdout_buff.retain(|&x| x != '\r' as u8);
      stdout_buff.retain(|&x| x != '\n' as u8);

    }
    Err(e) => { print!("e={:?}", e); }
  }


  return true;
}



