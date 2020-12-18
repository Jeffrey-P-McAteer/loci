
//use walkdir::WalkDir;
//use pathdiff;
//use cc;

use std::fs;
//use std::io::{Write, Seek};
//use std::io::prelude::*;

use std::process::{Command};

fn main() {
  println!("cargo:rerun-if-env-changed=LOCI_EAPP_TAR");
  embed_eapp_tar(
    &std::env::var("LOCI_EAPP_TAR").unwrap_or(String::new())[..]
  );
}


fn embed_eapp_tar(eapp_tar_path: &str) {
  let out_dir = std::env::var("OUT_DIR").expect("OUT_DIR is defined to always exist when cargo executes build.rs");
  
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
      if cfg!(windows) { // host is windows, target is windows
        cc = "gcc";
        ld = "ld";
        ar = "ar";
        static_lib_fname = "eapp_tar_data.lib";
        compiling_for_win = true;
      }
      else { // host is linux or macos, target is windows
        cc = "x86_64-w64-mingw32-gcc";
        ld = "x86_64-w64-mingw32-ld";
        ar = "x86_64-w64-mingw32-ar";
        static_lib_fname = "eapp_tar_data.lib";
        compiling_for_win = true;
      }
    }
    else if target_triple.contains("darwin") {
      std::unimplemented!();

    }
    else { // linux
      cc = "gcc";
      ld = "ld";
      ar = "ar";
      static_lib_fname = "libeapp_tar_data.a";
    }
  }

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

    eapp_tar_data_contents += format!(r#"

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

"#, gcc_symbol_name=gcc_symbol_name.as_str()).as_str();

  }

  eapp_tar_data_contents += r#"
#ifdef _WIN32
#include <windows.h> 
#include <lmaccess.h>
#include <lmerr.h>
extern __attribute__((visibility("default"))) _Bool loci_win_is_administrator()  {
      /*
      _Bool result;
      DWORD rc;
      wchar_t user_name[256];
      USER_INFO_1 *info;
      DWORD size = sizeof( user_name );
      GetUserNameW( user_name, &size);
      rc = NetUserGetInfo( NULL, user_name, 1, (byte **) &info );
      if ( rc != NERR_Success ) 
              return FALSE;
      result = info->usri1_priv == USER_PRIV_ADMIN;
      NetApiBufferFree( info );
      return result;
      */
      return FALSE;
}

DWORD rust_win_runas(LPCTSTR *cmd, LPCTSTR *params, int show)
{
    /*
    DWORD code;
    SHELLEXECUTEINFO sei = { sizeof(sei) };

    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);

    sei.fMask = SEE_MASK_NOASYNC | SEE_MASK_NOCLOSEPROCESS;
    sei.lpVerb = L"runas";
    sei.lpFile = cmd;
    sei.lpParameters = params;
    sei.nShow = show ? SW_NORMAL : SW_HIDE;

    if (ShellExecuteExW(&sei) == FALSE || sei.hProcess == NULL) {
        return -1;
    }

    WaitForSingleObject(sei.hProcess, INFINITE);

    if (GetExitCodeProcess(sei.hProcess, &code) == 0) {
        return -1;
    }

    return code;
    */
    return -1;
}

#endif
  "#;

  fs::write(&eapp_tar_data_c_f[..], eapp_tar_data_contents).expect("Could not write to eapp_tar_data.c!");
  
  Command::new(cc)
    .args(&[
      "-g", "-fpic", "-O", "-c",
      format!("{}{}eapp_tar_data.c", out_dir, std::path::MAIN_SEPARATOR).as_str(),
      "-o", format!("{}{}eapp_tar_data_c.o", out_dir, std::path::MAIN_SEPARATOR).as_str()
    ])
    .status()
    .expect("Could not run cc");

  Command::new(ld)
    .args(&[
      "-r", "-b", "binary", 
      &eapp_tar_path,
      "-o", format!("{}{}eapp_tar_data.o", out_dir, std::path::MAIN_SEPARATOR).as_str()
    ])
    .status()
    .expect("Could not run ld");

  Command::new(ar)
    .args(&[
      "rcs", format!("{}{}{}", out_dir, std::path::MAIN_SEPARATOR, static_lib_fname).as_str(),
        format!("{}{}eapp_tar_data_c.o", out_dir, std::path::MAIN_SEPARATOR).as_str(),
        format!("{}{}eapp_tar_data.o", out_dir, std::path::MAIN_SEPARATOR).as_str()
    ])
    .status()
    .expect("Could not run ar");

  if compiling_for_win {
    // cargo needs to link against netapi32 for the symbol NetUserGetInfo
    println!("cargo:rustc-link-lib=static=netapi32");
  }

  // tell cargo to add the object file to the list of symbols used to build the final binary
  println!("cargo:rustc-link-search=native={}", &out_dir);
  println!("cargo:rustc-link-lib=static=eapp_tar_data");
}


