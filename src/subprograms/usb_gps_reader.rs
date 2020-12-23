/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use std::path::{Path};
use std::process::{Command, Child, Stdio, ChildStdout};


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

  let mut buff: [u8; 128] = [0u8; 128];

  match usb_gps_stdout.read(&mut buff) {
    Ok(n) => {
      if n == 0 { // EOF
        *usb_gps_restart_flag = true;
      }

      // append buff[0..n] to stdout_buff,
      // then read any lines if they exist in stdout_buff.
      stdout_buff.extend_from_slice(&buff[0..n]);

      while let Some(line_term_i) = stdout_buff.iter().position(|&r| r == '\n' as u8) {
        let read_line_bytes = &buff[0..line_term_i];
        let read_line = String::from_utf8_lossy(read_line_bytes);
        let read_line = read_line.trim();
        // read 0 -> '\n' as string, then trim stdout_buff.
        stdout_buff.drain(0..line_term_i+1);

        // NMEA packets must end in RN to be parsed
        let read_line = format!("{}\r\n", read_line.trim());

        println!("read_line={}", &read_line[..]);

        // TODO detect + use _usb_gps_restart_flag when GPS is detected to be broken
        
        for result in parser.parse_from_bytes(read_line.as_bytes()) {
          match result {
            Ok(ParseResult::RMC(Some(rmc))) => {
              println!("Got RMC packet: {:?}", rmc);
            },
            
            Ok(_p) => {
              //println!("Got other packet: {:?}", p);
            }
            Err(e) => {
              println!("nmea parse e={}", e);
            }
          }
        }

      }


    }
    Err(e) => { print!("e={:?}", e); }
  }


  return true;
}



