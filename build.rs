//use walkdir::WalkDir;
//use pathdiff;
//use cc;

use std::fs;
//use std::io::{Write, Seek};
//use std::io::prelude::*;

use std::process::Command;

fn main() {
    println!("cargo:rerun-if-env-changed=LOCI_EAPP_TAR");
    println!("cargo:rerun-if-env-changed=LOCI_HARD_REBUILD");
    embed_eapp_tar(&std::env::var("LOCI_EAPP_TAR").unwrap_or(String::new())[..]);
    embed_icon();
}

fn embed_eapp_tar(eapp_tar_path: &str) {
    let out_dir = std::env::var("OUT_DIR")
        .expect("OUT_DIR is defined to always exist when cargo executes build.rs");

    // Windows systems will commonly have spaces in directory names
    // which wrecks havoc on paths passed between programs.
    //let out_dir = out_dir.replace(" ", "\\ ");

    let mut cc = "gcc";
    let mut ld = "ld";
    let mut ar = "ar";
    let mut static_lib_fname = "libeapp_tar_data.a";

    let mut compiling_for_win = false;

    // First compile the binary into a static library with symbols we want...
    if let Ok(target_triple) = std::env::var("TARGET") {
        if target_triple.contains("windows") {
            if cfg!(windows) {
                // host is windows, target is windows
                cc = "gcc";
                ld = "ld";
                ar = "ar";
                static_lib_fname = "eapp_tar_data.lib";
                compiling_for_win = true;
            } else {
                // host is linux or macos, target is windows
                cc = "x86_64-w64-mingw32-gcc";
                ld = "x86_64-w64-mingw32-ld";
                ar = "x86_64-w64-mingw32-ar";
                static_lib_fname = "eapp_tar_data.lib";
                compiling_for_win = true;
            }
        } else if target_triple.contains("darwin") {
            std::unimplemented!();
        } else {
            // linux
            cc = "gcc";
            ld = "ld";
            ar = "ar";
            static_lib_fname = "libeapp_tar_data.a";
        }
    }

    drop(compiling_for_win); // silence compiler warning, we may want to query compiling_for_win itf

    if cfg!(feature = "embed-eapp-tar") && eapp_tar_path.len() < 1 {
        panic!("Feature embed-eapp-tar requested but no environment variable set: LOCI_EAPP_TAR");
    }

    let eapp_tar_data_c_f = format!("{}/eapp_tar_data.c", out_dir);
    let mut eapp_tar_data_contents = String::new();

    if cfg!(feature = "embed-eapp-tar") {
        // Use the selected system tools build a shared lib
        let gcc_symbol_name = &eapp_tar_path.replace("/", "_");
        let gcc_symbol_name = &gcc_symbol_name.replace(".", "_");
        let gcc_symbol_name = &gcc_symbol_name.replace("-", "_");
        let gcc_symbol_name = &gcc_symbol_name.replace("\\", "_");
        let gcc_symbol_name = &gcc_symbol_name.replace(":", "_");

        eapp_tar_data_contents += format!(
            r#"

// #include <stddef.h>
// #include <stdint.h>

extern const char eapp_tar_data[]      asm("_binary_{gcc_symbol_name}_start");
extern const int eapp_tar_data_size   asm("_binary_{gcc_symbol_name}_size");
extern const char eapp_tar_data_end[]  asm("_binary_{gcc_symbol_name}_end");

// Write a function that rust can call using the extern "C" linking style
extern __attribute__((visibility("default"))) char* get_embed_tar_bytes() {{
  return &eapp_tar_data;
}}

// Write a function that rust can call using the extern "C" linking style
extern __attribute__((visibility("default"))) int get_embed_tar_len() {{
  return eapp_tar_data_size;
}}

extern __attribute__((visibility("default"))) char* get_embed_tar_bytes_end() {{
  return &eapp_tar_data_end;
}}

"#,
            gcc_symbol_name = gcc_symbol_name.as_str()
        )
        .as_str();
    }

    eapp_tar_data_contents += r#"

// If we ever need C api calls again stick 'em in here and
// use the
//    extern __attribute__((visibility("default")))
// tokens to disable name mangling so we can link to rust code.

  "#;

    fs::write(&eapp_tar_data_c_f[..], eapp_tar_data_contents)
        .expect("Could not write to eapp_tar_data.c!");

    let s = Command::new(cc)
        .args(&[
            "-g",
            "-fpic",
            "-O",
            "-c",
            format!("{}{}eapp_tar_data.c", out_dir, std::path::MAIN_SEPARATOR).as_str(),
            "-o",
            format!("{}{}eapp_tar_data_c.o", out_dir, std::path::MAIN_SEPARATOR).as_str(),
        ])
        .status()
        .expect("Could not run cc");

    if !s.success() {
        panic!("eapp_tar_data_c.o compile failed!");
    }

    let s = Command::new(ld)
        .args(&[
            "-r",
            "-b",
            "binary",
            &eapp_tar_path,
            "-o",
            format!("{}{}eapp_tar_data.o", out_dir, std::path::MAIN_SEPARATOR).as_str(),
        ])
        .status()
        .expect("Could not run ld");

    if !s.success() {
        panic!("eapp_tar_data.o link failed!");
    }

    let s = Command::new(ar)
        .args(&[
            "rcs",
            format!(
                "{}{}{}",
                out_dir,
                std::path::MAIN_SEPARATOR,
                static_lib_fname
            )
            .as_str(),
            format!("{}{}eapp_tar_data_c.o", out_dir, std::path::MAIN_SEPARATOR).as_str(),
            format!("{}{}eapp_tar_data.o", out_dir, std::path::MAIN_SEPARATOR).as_str(),
        ])
        .status()
        .expect("Could not run ar");

    if !s.success() {
        panic!("static_lib_fname compile failed!");
    }

    // tell cargo to add the object file to the list of symbols used to build the final binary
    println!("cargo:rustc-link-search=native={}", &out_dir);
    println!("cargo:rustc-link-lib=static=eapp_tar_data");
}

fn embed_icon() {
    use std::path::{Path, PathBuf};

    let mut compiling_for_windows = false;

    if let Ok(target_triple) = std::env::var("TARGET") {
        if target_triple.contains("windows") {
            compiling_for_windows = true;
        }
    }

    if compiling_for_windows {
        // Add icon
        let mut res = winres::WindowsResource::new();

        res.set_toolkit_path(".");

        let windres_paths = vec!["/usr/bin/x86_64-w64-mingw32-windres"];
        for p in windres_paths {
            if Path::new(p).exists() {
                res.set_windres_path(p);
                break;
            }
        }

        let ar_paths = vec!["/usr/bin/x86_64-w64-mingw32-ar"];
        for p in ar_paths {
            if Path::new(p).exists() {
                res.set_ar_path(p);
                break;
            }
        }

        let ico_rel_path: PathBuf = ["assets", "icon.ico"].iter().collect();

        res.set_icon(&ico_rel_path.to_string_lossy());

        println!("res={:#?}", res);

        //res.compile().unwrap();
        if let Err(e) = res.compile() {
            println!("e={:?}", e);
            //panic!();
        }
    }
}
