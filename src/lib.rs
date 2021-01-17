/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

// Responsible for making core loci functionality available
// for use by Rust code. A big TODO is to massage this
// interface to become suitable for public use, but that
// will require a decent amount of knowledge related to what
// people want to build for loci.


#[cfg(feature = "compile-lib-only")]
pub mod db;

use std::path::PathBuf;

#[cfg(target_os = "windows")]
pub fn get_app_dir(dirname: &str) -> PathBuf {
    let pb = dirs::data_dir().unwrap_or(PathBuf::from("."))
        .join(".loci")
        .join(dirname);

    if !pb.as_path().exists() {
        if let Err(e) = std::fs::create_dir_all(&pb) {
            println!("{}:{}: {}", std::file!(), std::line!(), e);
        }
    }

    pb
}

#[cfg(target_os = "linux")]
pub fn get_app_dir(dirname: &str) -> PathBuf {
    let pb = dirs::data_dir().unwrap_or(PathBuf::from("."))
        .join(".loci")
        .join(dirname);

    if !pb.as_path().exists() {
        if let Err(e) = std::fs::create_dir_all(&pb) {
            println!("{}:{}: {}", std::file!(), std::line!(), e);
        }
    }

    pb
}
