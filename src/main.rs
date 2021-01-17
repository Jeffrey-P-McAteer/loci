/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

use crossbeam;

use std::env;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::{thread, time};

pub const LOCI_DB_ENV_KEY: &'static str = "LOCI_DB_FILE";
pub const LOCI_EAPP_DIR_ENV_KEY: &'static str = "LOCI_EAPP_DIR";

pub const DISABLED_SUBPROGRAMS: &'static str = "LOCI_DISABLED_SUBPROGRAMS";
pub const LICENSE_TXT: &'static str = "LOCI_LICENSE_TXT";

// Responsible for extracting and executing
// seperate OS processes which Loci expects to be available.
mod eapp;

// Responsible for saving and restoring data across runs
mod db;

// Responsible for negotiating admin privileges and re-executing
// main() in an admin context so we can run eapp programs which talk to hardware.
mod privileged_ops;

// This module embeds translation .json files,
// extracts them to the user's home directory,
// and searches for user-specified translations
// which get merged into defaults.
mod trans;

// This module is responsible for determining if this
// copy of locorum is running with a license.
mod license;

mod lib;

use lib::get_app_dir;

fn main() {
    let loci_exit_f: Arc<AtomicBool> = Arc::new(AtomicBool::new(false));

    if !license::check_license() {
        let loci_exit_f_l = loci_exit_f.clone();
        std::thread::spawn(move || {
            println!("No license; exiting after 10min demo...");
            thread::sleep(time::Duration::from_millis(10 * 60 * 1000));
            loci_exit_f_l.store(true, Ordering::SeqCst);
            thread::sleep(time::Duration::from_millis(1600));
            on_proc_exit();
            std::process::exit(0);
        });
    }

    #[cfg(not(target_os = "windows"))]
    {
        setup_signal_handlers(loci_exit_f.clone());
    }

    // Rather than hard-coding stuff in subprograms, we add the ./bin/ directories
    // of sub-programs to the PATH so we can run "java.exe" and invoke our bundled copy.
    add_eapp_bin_dirs_to_path();

    // If we assign LOCI_NO_ADMIN and inadventantly call ourselves
    // as admin the LOCI_NO_ADMIN state takes priority and we do
    // not run admin functions.
    if let Ok(_val) = std::env::var("LOCI_NO_ADMIN") {
        println!("Skipping privileged_ops::elevate_privileges b/c LOCI_NO_ADMIN set");
    } else {
        // If we are root and spawn administrative BG threads.
        if privileged_ops::we_are_privileged() {
            eapp::main_privileged(loci_exit_f.clone());
            std::process::exit(0)
        } else {
            // We are not root; Call ourselves again, asking the user to grant us privileges
            let root_loci_exit_f = loci_exit_f.clone();
            std::thread::spawn(move || {
                privileged_ops::elevate_privileges(root_loci_exit_f);
            });
        }
    }

    // Print machine HWID to stdout to support customers who want offline activation
    println!("");
    println!("HWID={}", license::get_host_hwid());
    println!("");

    // Init db schema and begin a thread to trim the db forever
    let db_loci_exit_f = loci_exit_f.clone();
    std::thread::spawn(move || {
        {
            // init sql schema
            let _c = db::get_init_db_conn();
        }
        db::trim_db_t(db_loci_exit_f);
    });

    hide_console_on_windows();

    // Run background threads in the background
    let bg_loci_exit_f = loci_exit_f.clone();
    std::thread::spawn(move || {
        bg_main(bg_loci_exit_f);
    });

    // Run graphics on main thread (windows cares quite a bit about this)
    if let Err(e) = gui_main(loci_exit_f.clone()) {
      println!("gui error = {:?}", e);
    }

    // When gui exits tell children to exit
    loci_exit_f.store(true, Ordering::SeqCst);
    on_proc_exit();

    println!("giving sub-programs 1600ms to exit...");
    thread::sleep(time::Duration::from_millis(1600));
    for _ in 0..9 {
        println!("");
    } // whitespace makes reading logs cleaner
    std::process::exit(0);
}


fn add_eapp_bin_dirs_to_path() {
    let eapp_dir = get_app_dir("eapp");

    // Here we store copies of all out sub-program bin/ directories
    let mut paths = vec![];

    paths.push(eapp_dir.join("python")); // python.exe lives here
    paths.push(eapp_dir.join("jre").join("bin")); // java.exe lives here
    paths.push(eapp_dir.join("postgres").join("bin")); // postgres.exe and also winpthread.dll is here

    // Now we prepend that to the existing PATH

    let os_path;
    if let Some(env_os_path) = env::var_os("PATH") {
        os_path = env_os_path;
    } else {
        os_path = std::ffi::OsString::new();
    }

    let mut os_paths = env::split_paths(&os_path).collect::<Vec<_>>();
    paths.append(&mut os_paths); // os_paths now empty

    match std::env::join_paths(paths) {
        Ok(new_os_paths) => {
            env::set_var("PATH", new_os_paths);
        }
        Err(e) => {
            println!("Could not join paths for new PATH: {}", e);
        }
    }
}

// these threads all expect to be in the background and are not
// "special" in any way
fn bg_main(loci_exit_f: Arc<AtomicBool>) {
    let r = crossbeam::thread::scope(|s| {
        let f = loci_exit_f.clone();
        s.spawn(move |_| {
            //subprograms::main(f);
        });

        let f = loci_exit_f.clone();
        s.spawn(move |_| {
            //webserver::main(f);
        });
    });
    if let Err(e) = r {
        println!("Error joining bg threads: {:?}", e);
        on_proc_exit();
        std::process::exit(1);
    }
}

// This fn does nothing on linux/unix machines
// and it calls winapi system calls to hide the console
// on windows.
// Users may set the environment variable NO_CONSOLE_DETATCH=1
// to prevent detatching from the console when the GUI is opened.
fn hide_console_on_windows() {
    #[cfg(target_os = "windows")]
    {
        if let Ok(val) = env::var("NO_CONSOLE_DETATCH") {
            if val.contains("y") || val.contains("Y") || val.contains("1") {
                return;
            }
        }
        hide_console_on_windows_win();
    }
}

#[cfg(target_os = "windows")]
fn hide_console_on_windows_win() {
    // Check if we are run from the console or just launched with explorer.exe
    let mut console_proc_list_buff: Vec<u32> = vec![0; 16];
    let num_procs = unsafe {
        winapi::um::wincon::GetConsoleProcessList(console_proc_list_buff.as_mut_ptr(), 16)
    };
    println!("num_procs={:?}", num_procs);
    if num_procs == 1 || num_procs == 2 {
        // We were launched from explorer.exe, detatch the console
        unsafe { winapi::um::wincon::FreeConsole() };
    }
    // Otherwise do nothing, we want console messages when run from the console.
}

#[cfg(not(target_os = "windows"))]
fn setup_signal_handlers(loci_exit_f: Arc<AtomicBool>) {
    //use signal_hook;

    // signal_hook writes True to loci_exit_f on SIGTERM
    if let Err(e) = signal_hook::flag::register(signal_hook::SIGTERM, loci_exit_f) {
        println!("Error installing signal handler: {}", e);
    }
}

fn gui_main(loci_exit_f: Arc<AtomicBool>) -> Result<(), systray::Error> {
    
    if let Ok(_var) = std::env::var("LOCI_NO_GUI") {
        loop {
            thread::sleep(time::Duration::from_millis(5000));
        }
        return Ok(());
    }

    let mut a = systray::Application::new()?;

    a.add_menu_item("Loci is Running", |window| {
        Ok::<_, systray::Error>(())
    })?;

    a.add_menu_item("Quit", move |window| {
        loci_exit_f.store(true, Ordering::SeqCst);
        window.quit();
        Ok::<_, systray::Error>(())
    })?;

    a.wait_for_message()?;

    Ok(())
}



pub fn on_proc_exit() {
    // Write to the DB that Loci should exit (all other apps may query this w/ timestamp)
    let r = crate::db::execute(
        20,
        100, // up to 2 seconds of retries
        "INSERT INTO app_events (name) VALUES (?1)",
        rusqlite::params!["loci-shutting-down"],
    );
    if let Err(e) = r {
        println!("error writing loci-shutting-down: {}", e);
    }
}



