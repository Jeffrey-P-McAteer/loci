
use std::path::{Path, PathBuf};
//use std::process::{Command, Child};

use std::env;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, RwLock};
use std::{thread, time};

use std::process::{Child, Command};

mod extraction;

pub fn eapp_enabled(prog_name: &str) -> bool {
    if let Ok(programs) = env::var(crate::DISABLED_SUBPROGRAMS) {
        if programs.contains(prog_name) {
            println!(
                "Disabling eapp {} because DISABLED_SUBPROGRAMS={}",
                prog_name, programs
            );
            return false;
        }
    }
    println!("Enabling eapp {}", prog_name);
    return true;
}

pub fn main(loci_exit_f: Arc<AtomicBool>) {
    let eapp_dir = extraction::extract_eapp_data();
    println!("eapp_dir={:?}", &eapp_dir);
}

pub fn main_privileged(loci_exit_f: Arc<AtomicBool>) {
    // This is run as root/Administrator so as to run programs which
    // talk to hardware (dump1090 and rtl_ais).
}
