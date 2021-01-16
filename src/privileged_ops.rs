/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use std::process::Command;
use std::sync::atomic::AtomicBool;
use std::sync::Arc;
use std::{thread, time};

pub fn we_are_privileged() -> bool {
    match std::env::var("LOCI_PPID") {
        Ok(_ppid) => {} // do nothing, we are a child process as expected
        Err(_e) => {
            // force us to think we are not privledged.
            // This means if a user runs the primary .exe as admin we will still
            // re-launch and perform admin functions in a new process.
            return false;
        }
    }

    #[cfg(target_os = "windows")]
    {
        let out = Command::new("whoami")
            .arg("/priv")
            .output()
            .expect("Could not run whoami");

        // The admin account has >5 lines and "SeCreateGlobalPrivilege" = Enabled.
        // This is a heuristic check and may need to be changed if
        // corporate domain accounts come into play.
        match std::str::from_utf8(&out.stdout) {
            Ok(out) => {
                // This is a fairly soft check which may not be 100% accurate.
                return out.contains("SeCreateGlobalPrivilege")
                    && out.contains("SeImpersonatePrivilege");
            }
            Err(e) => {
                println!("e={}", e);
                return false;
            }
        }
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

    let eapp_dir = crate::get_app_dir("eapp");

    let self_exe = env::current_exe().expect("Could not get self exe file");

    env::set_var(
        crate::LOCI_EAPP_DIR_ENV_KEY,
        &eapp_dir.to_string_lossy()[..],
    );

    let db_file = crate::db::get_database_file();

    env::set_var(crate::LOCI_DB_ENV_KEY, &db_file.to_string_lossy()[..]);

    // Re-type these variables
    let eapp_dir = eapp_dir.to_string_lossy();
    let db_file = db_file.to_string_lossy();

    let args: Vec<&str> = vec![&eapp_dir[..], &db_file[..]];

    let mut child;

    #[cfg(target_os = "windows")]
    {
        // "powershell" is documented to always exist on windorks
        let mut arglist = String::new();
        for a in args.iter() {
            arglist += &format!("'{}',", a)[..];
        }
        // remove the last ","
        arglist.pop();

        child = Command::new("powershell")
            .arg("start")
            .arg(&self_exe.to_string_lossy()[..])
            .arg("-argumentlist")
            .arg(&arglist[..])
            .arg("-verb")
            .arg("runas")
            .env("LOCI_PPID", format!("{}", std::process::id()).as_str())
            //.env(crate::DISABLED_SUBPROGRAMS, env::var(crate::DISABLED_SUBPROGRAMS).unwrap_or(String::new()))
            .spawn()
            .expect("Could not run admin b/c sub-process failed");
    }

    #[cfg(not(target_os = "windows"))]
    {
        match which::which("gksudo") {
            Ok(_) => {
                child = Command::new("gksudo")
                    .arg("-E")
                    .arg("--")
                    .arg(&self_exe.to_string_lossy()[..])
                    .args(&args[..])
                    .env("LOCI_PPID", format!("{}", std::process::id()).as_str())
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
                            .env("LOCI_PPID", format!("{}", std::process::id()).as_str())
                            //.env(crate::DISABLED_SUBPROGRAMS, env::var(crate::DISABLED_SUBPROGRAMS).unwrap_or(String::new()))
                            .spawn()
                            .expect("Could not run admin b/c sub-process failed");
                    }
                    Err(_) => {
                        panic!("Cannot run admin because no priv elevation programs exist on this system");
                    }
                }
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
