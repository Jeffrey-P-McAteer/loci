
use shrust::{Shell, ShellIO};
use std::io::prelude::*;

fn main() {
  let mut shell = Shell::new(());

  shell.new_command_noargs("info", "Print system metadata such as app root, install dir, version, running processes...", |io, _| {
    writeln!(io, "get_app_root = {}", &app_lib::get_app_root().to_string_lossy() )?;
    //writeln!(io, "get_app_root = {}", &app_lib::get_app_root().to_string_lossy() )?;
    Ok(())
  });

  shell.new_command("sql-exec", "Execute a sql statement, no data is returned on success.", 2, |io, _, args| {
    //writeln!(io, "args = {:#?}", args )?;
    let dbname = args[0];
    let sql = args[1..].join(" ");

    writeln!(io, "Opening db {} from file {}", &dbname, &app_lib::get_app_db_path(&dbname).to_string_lossy() )?;
    let mut db = app_lib::open_app_db(&dbname)?;
    writeln!(io, "Executing: {}", &sql )?;
    let res = db.execute_batch(&sql)?;

    //writeln!(io, "res={:#?}", res )?;

    Ok(())
  });

  shell.new_command("sql-query", "Execute a sql query, printing any returned rows + columns.", 2, |io, _, args| {
    //writeln!(io, "args = {:#?}", args )?;
    let dbname = args[0];
    let sql = args[1..].join(" ");

    writeln!(io, "Opening db {} from file {}", &dbname, &app_lib::get_app_db_path(&dbname).to_string_lossy() )?;
    let mut db = app_lib::open_app_db(&dbname)?;
    writeln!(io, "Querying: {}", &sql )?;
    let mut stmt = db.prepare(&sql)?;
    let mut rows = stmt.query([])?;
    let mut rows_count = 0;

    while let Some(row) = rows.next()? {
      rows_count += 1;
      for i in 0..row.column_count() {
        // then print value
        if let Ok(val) = row.get(i) {
          let val: String = val;
          write!(io, "{:#?}, ", val)?;
        }
        else if let Ok(val) = row.get(i) {
          let val: i64 = val;
          write!(io, "{:#?}, ", val)?;
        }
        else {
          write!(io, "UNKNOWN VAL, ")?;
        }
      }
      writeln!(io, "" )?;
    }
    writeln!(io, "Query returned {} rows", rows_count )?;

    Ok(())
  });

  shell.new_command("shmem", "Read/Write a shared memory file; args: name [read|poll|write [DATA]], default command is 'read', all data is represented as hex.", 1, |io, _, args| {
    let name = args[0];
    let cmd = args.get(1).unwrap_or(&"read");
    // TODO how can we ask user for size w/o making a complex API? for now just use 1kb.
    let mut shmem = app_lib::open_shmem_file(&name, 1024)?;
    match cmd {
      &"read" => {
        let bytes = unsafe{ shmem.as_slice() };
        let s = app_lib::hex::encode(bytes);
        writeln!(io, "{}", s )?;
      }
      &"poll" => {
        let bytes = unsafe{ shmem.as_slice() };
        let mut last_sum: u8 = bytes.iter().sum();
        let mut max_changes = 10;
        loop {
          let s = app_lib::hex::encode(bytes);
          writeln!(io, "content: {}", s)?;
          writeln!(io, "Waiting for change ({})...", max_changes)?;
          loop {
            std::thread::sleep( std::time::Duration::from_millis(150) );
            let this_sum: u8 = bytes.iter().sum();
            if this_sum != last_sum {
              writeln!(io, "Got change!")?;
              last_sum = this_sum;
              break;
            }
          }
          if max_changes < 1 {
            break;
          }
          max_changes -= 1;
        }
      }
      &"write" => {
        let mut hex_contents = args[2..].join("");
        hex_contents.retain(|c| !c.is_whitespace()); // remove all whitespace
        let bytes = app_lib::hex::decode(&hex_contents)?;
        // Write bytes to shmem
        let end_i = std::cmp::min(shmem.len(), bytes.len());
        let shmem_buffer = unsafe { shmem.as_slice_mut() };
        for i in 0..end_i {
          shmem_buffer[i] = bytes[i];
        }
        writeln!(io, "Wrote {} bytes to {}", end_i, app_lib::get_shmem_path(name).as_path().to_string_lossy() )?;
      }
      unk => {
        writeln!(io, "Unk cmd: {}", unk )?;
      }
    }

    Ok(())
  });

  shell.new_command("trans", "Translate a tkey in the given language (eg \"es hello_world\" or \". hello_world\")", 2, |io, _, args| {
    //writeln!(io, "args = {:#?}", args )?;
    let lang_code = args[0];
    let tkey = args[1];

    let value = if lang_code.len() < 2 {
      // "empty" lang_code
      app_lib::trans(tkey)
    }
    else {
      app_lib::trans_lang(lang_code, tkey)
    };

    writeln!(io, "{}", value )?;

    Ok(())
  });

  shell.run_loop(&mut ShellIO::default());
}


