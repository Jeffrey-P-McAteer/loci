/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use std::path::{Path};
use std::process::{Command, Child, Stdio, ChildStdout};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::sync::atomic::AtomicBool;


pub fn start_and_poll_until_exit(eapp_dir: &Path, loci_exit_f: &Arc<AtomicBool>, child_pids: &Arc<RwLock<Vec<u32>>>) {
  let mut dump1090_p = start(eapp_dir);

  if let Ok(mut child_pids) = child_pids.write() {
    child_pids.push( dump1090_p.id() );
  }

  match dump1090_p.stdout.take() {
    Some(mut dump1090_stdout) => {
      let mut dump1090_stdout_buff = vec![];
      let mut dump1090_record: HashMap<&str, String> = HashMap::new();
      let mut dump1090_restart_flag = false;

      loop {
        let should_exit = loci_exit_f.load(std::sync::atomic::Ordering::SeqCst);
        if should_exit {
          if let Err(e) = dump1090_p.kill() {
            println!("Err killing dump1090_p: {}", e);
          }
        }

        if !poll(&mut dump1090_p, &mut dump1090_stdout, &mut dump1090_stdout_buff, &mut dump1090_record, &mut dump1090_restart_flag) {
          break;
        }

        if dump1090_restart_flag {
          if let Err(e) = dump1090_p.kill() {
            println!("Err killing dump1090_p: {}", e);
          }
          break;
        }
        
      }
    }
    None => {
      println!("Err: no dump1090.stdout");
    }
  }
}

pub fn start(eapp_dir: &Path) -> Child {

  let mut dump1090_exe = eapp_dir.to_path_buf();
  dump1090_exe.push(if cfg!(windows) { "dump1090.exe" } else { "dump1090" } );

  if !dump1090_exe.as_path().exists() {
    println!("dump1090_exe does not exist at {}", &dump1090_exe.to_string_lossy()[..]);
    return crate::subprograms::dummy_proc();
  }

  #[cfg(target_os = "windows")]
  {
    return Command::new("cmd.exe")
          .args(&[
            "/C", // 2>&1 makes sure our stdout reader gets stderr as well, and can spawn the zadig python process.
            format!("{} --modeac 2>&1", &dump1090_exe.to_string_lossy()[..]).as_str()
          ])
          .stdin(Stdio::null())
          .stdout(Stdio::piped())
          .stderr(Stdio::inherit())
          .spawn()
          .expect("dump1090 command failed to start");
  }
  #[cfg(not(target_os = "windows"))]
  {
    return Command::new(&dump1090_exe.to_string_lossy()[..])
        .args(&["--modeac"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("dump1090 command failed to start");
  }
}

// responsible for checking process stdout and writing to DB.
// The returned value should be "true" if the process is alive,
// or "false" if the process is dead.
pub fn poll(dump1090_p: &mut Child, dump1090_stdout: &mut ChildStdout, stdout_buff: &mut Vec<u8>, dump1090_record: &mut HashMap<&str, String>, dump1090_restart_flag: &mut bool) -> bool {
  use std::io::prelude::*;
  
  let dump1090_p_alive = if let Ok(None) = dump1090_p.try_wait() { true } else { false };
  if ! dump1090_p_alive {
    return false;
  }

  let mut buff: [u8; 4098] = [0u8; 4098];

  match dump1090_stdout.read(&mut buff) {
    Ok(n) => {
      if n == 0 { // EOF
        *dump1090_restart_flag = true;
      }

      // append buff[0..n] to stdout_buff,
      // then read any lines if they exist in stdout_buff.
      stdout_buff.extend_from_slice(&buff[0..n]);

      loop {
        if let Some(line_term_i) = stdout_buff.iter().position(|&r| r == '\n' as u8) {
          { // read line from vec as string
            let read_line_bytes = &stdout_buff[0..line_term_i];
            let read_line = String::from_utf8_lossy(read_line_bytes);
            let read_line = read_line.trim();
            
            // detect the (windows-only) case where a USB device needs a driver install and execute the
            // win64_libusb_installer.py script
            #[cfg(target_os = "windows")]
            {
              if read_line.contains("error querying device") {
                if let Ok(eapp_dir) = std::env::var(crate::LOCI_EAPP_DIR_ENV_KEY) {
                  let python_script = format!("{}\\win64_libusb_installer.py", eapp_dir.trim());
                  print!("executing {}", &python_script[..]);
                  Command::new("python")
                    .args(&[&python_script[..]])
                    .status()
                    .expect("Could not run win64_libusb_installer.py");
                }
              }
            }

            if read_line.contains("no supported devices") || read_line.contains("error querying device") {
              *dump1090_restart_flag = true;
            }


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
          { // mutate vec to remove read bytes
            stdout_buff.drain(0..line_term_i+1);
          }
        }
        else {
          break;
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



