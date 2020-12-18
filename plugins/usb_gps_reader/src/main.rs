
use std::{thread, time::Duration};
use std::io::{self, prelude::*, BufReader};

fn main() {
  let sleep_ms = Duration::from_millis(250);
  loop {
    thread::sleep(sleep_ms);

    if let Ok(ports) = serialport::available_ports() {
      
      let mut port_connection_s: Option<String> = None;

      for p in ports {
        match p.port_type {
          serialport::SerialPortType::UsbPort(usb_info) => {
            if looks_like_gps(&p.port_name) {
              if cfg!(windows) {
                port_connection_s = Some(p.port_name);
              }
              else {
                port_connection_s = Some(p.port_name);
              }
            }
          }
          _ => { }
        }
      }

      if let Some(conn_s) = port_connection_s {
        read_from_gps(&conn_s);
      }

    }

  }
}

fn looks_like_gps(conn_s: &str) -> bool {
  println!("looks_like_gps({})", conn_s);

  let port = serialport::new(conn_s, 4800) // most USB GPS use baud 4800
        .timeout(Duration::from_millis(20))
        .open();

  match port {
    Ok(mut port) => {
      
      // We try to read until we see a constant we like.
      // port.read() times out after 20ms, and we exit
      // if we try for 1 second and do not get anything we like.

      let mut remaining_attempts = 20;
      loop {
        
        thread::sleep(Duration::from_millis(50));

        let mut serial_buf: Vec<u8> = vec![0; 32];
        match port.read(serial_buf.as_mut_slice()) {
          Ok(num) => {
            // Does &serial_buf[..num] contain a good constant?
            let read_bytes = &serial_buf[..num];
            if let Ok(read_str) = std::str::from_utf8(read_bytes) {
              if read_str.contains("$GPRMC,") || read_str.contains("$GPGGA,") {
                return true; // Yup, this looks like a GPS device
              }
            }
          }
          // This is normal + we just loop again
          Err(ref e) if e.kind() == io::ErrorKind::TimedOut => (),
          // report actual errors
          Err(e) => { eprintln!("{:?}", e); }
        }

        remaining_attempts -= 1;
        if remaining_attempts < 1 {
          break;
        }
      }

    }
    Err(e) => {
      println!("e={}", e);
    }
  }

  false
}

fn read_from_gps(conn_s: &str) {
  //println!("read_from_gps({})", conn_s);

  let port = serialport::new(conn_s, 4800) // most USB GPS use baud 4800
        .timeout(Duration::from_millis(20))
        .open();

  match port {
    Ok(mut port) => {
      
      // We read and print a buffer on "\n" chars;
      // if we get 60 timeouts in a row we exit (3 seconds w/o data)
      let mut remaining_attempts = 60;
      let mut next_line_buf = String::new();
      loop {
        
        thread::sleep(Duration::from_millis(50));

        let mut serial_buf: Vec<u8> = vec![0; 128];
        match port.read(serial_buf.as_mut_slice()) {
          Ok(num) => {
            // Does &serial_buf[..num] contain a good constant?
            let read_bytes = &serial_buf[..num];
            if let Ok(read_str) = std::str::from_utf8(read_bytes) {
              next_line_buf += read_str;
              if let Some(i) = next_line_buf.chars().collect::<Vec<char>>().iter().position(|&c| c == '\n') {
                let line = &next_line_buf[0..i];
                
                // Each line is parsed by loci subprograms/usb_gps_reader.rs,
                // this binary is merely responsible for printing GPS packets.
                println!("{}", line);

                // Truncate original buffer b/c we read the above chars!
                for _ in 0..i+1 {
                  next_line_buf.remove(0); // this is not efficient.
                }

              }
            }

            // Reset error counter
            remaining_attempts = 60;

          }
          // This is normal + we just loop again
          Err(ref e) if e.kind() == io::ErrorKind::TimedOut => {
            remaining_attempts -= 1;
          },
          // report actual errors
          Err(e) => {
            remaining_attempts -= 1;
            //eprintln!("{:?}", e);
          }
        }

        remaining_attempts -= 1;
        if remaining_attempts < 1 {
          break;
        }
      }

    }
    Err(e) => {
      println!("e={}", e);
    }
  }
}

