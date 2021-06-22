
/**
 * C/C++ function definitions. These all require the caller
 * to provide allocated memory.
 */

use crate::*;

use std::slice;
use std::ffi::CString;

#[no_mangle]
pub extern "C" fn loci_get_app_root(buffer_ptr: *mut u8, buffer_size: u32) {
  if buffer_ptr.is_null() {
    return;
  }
  let app_root = get_app_root();
  let app_root = &app_root.to_string_lossy();
  let app_root = match CString::new(&app_root[..]) {
    Err(e) => {
      eprintln!("e={}", e);
      return;
    },
    Ok(c_str) => c_str,
  };
  let app_root_c_bytes = app_root.as_bytes_with_nul();
  let buffer_size = buffer_size as usize;

  // Safe b/c we check buffer_ptr.is_null() above & we do a bounds check below (copied_len)
  let buffer_bytes = unsafe {
    slice::from_raw_parts_mut(buffer_ptr, buffer_size)
  };
  let copied_len = if buffer_size > app_root_c_bytes.len() { app_root_c_bytes.len() } else { buffer_size };
  buffer_bytes[..copied_len].copy_from_slice(app_root_c_bytes);
}


