/**
 * build.rs writes some C code which creates these symbols and adds them to a .lib/.a file we link against.
 * The bytes returned by get_embed_tar_bytes are the eapp zip file that build.py constructs.
 */
extern "C" {
    fn get_embed_tar_bytes() -> *const u8;
    // fn get_embed_zip_len() -> u64; // This is a little broken
    fn get_embed_tar_bytes_end() -> *const u8;
}

#[cfg(feature = "embed-eapp-tar")]
pub fn extract_eapp_data() -> std::path::PathBuf {
    use flate2::read::GzDecoder;
    use glob;
    use std::io::prelude::*;
    use tar::Archive;
    use std::fs;

    let eapp_dir = crate::get_app_dir("eapp");


    let tar_bytes = unsafe {
        let embed_length = (get_embed_tar_bytes_end() as *const usize as usize)
            - (get_embed_tar_bytes() as *const usize as usize);
        std::slice::from_raw_parts(get_embed_tar_bytes(), embed_length)
        //Vec::from_raw_parts(get_embed_tar_bytes() as *mut u8, embed_length, embed_length)
    };
    let gz = GzDecoder::new(&tar_bytes[..]);

    // Because we borrowed memory from the .TEXT section we must not free() it -
    // calling mem::forget ensures the underlying memory is not freed.
    std::mem::forget(tar_bytes);

    let mut archive = Archive::new(gz);

    // Instead of having the library extract everything (which may take 5 mins)
    // we go over all entries and only extract new data (files which do not exist).
    let dst = eapp_dir.as_path();
    for entry in archive.entries().unwrap() {
        match entry {
            Ok(mut entry) => {
                let entry_path = match entry.path() {
                    Ok(p) => p,
                    Err(_) => continue,
                };

                let existing_f = dst.join(entry_path);
                if existing_f.exists() {
                    //println!("Skipping existing eapp file {}", &existing_f.to_string_lossy()[..]);
                    continue;
                }

                println!("Extracting eapp file {}", &existing_f.to_string_lossy()[..]);
                if let Err(_e) = entry.unpack_in(&dst) {
                    //println!("Error unpacking eapp file: {}", e);
                }
            }
            Err(e) => {
                println!("Error unpacking eapp file: {}", e);
            }
        }
    }

    println!("Done extracting eapp dir.");

    return eapp_dir;
}

#[cfg(not(feature = "embed-eapp-tar"))]
pub fn extract_eapp_data() -> std::path::PathBuf {
    use flate2::read::GzDecoder;
    use glob;
    use std::io::prelude::*;
    use tar::Archive;
    use std::fs;


    let mut option_decoder = None;
    if let Ok(mut curr_exe) = std::env::current_exe() {
        for _ in 0..2 {
            if let Some(exe_dir) = curr_exe.parent() {
                let target_name = if cfg!(windows) { "win64" } else { "linux64" };

                // Search under exe_dir

                let glob_str = format!("{}/eapp*.tar.gz", exe_dir.display());
                println!("Looking for eapp tarball under {:?}", &glob_str);

                if let Ok(globiterator) = glob::glob(&glob_str) {
                    for entry in globiterator {
                        if let Ok(entry) = entry {
                            if entry.to_string_lossy().contains(target_name) {
                                // We found it!
                                println!(
                                    "Using eapp tarball {:?}",
                                    &entry.to_string_lossy()[..]
                                );
                                let mut f = fs::File::open(&entry).expect("no eapp file found");
                                option_decoder = Some(GzDecoder::new(f));
                                break;
                            }
                        }
                    }
                }

                if option_decoder.is_some() {
                    break;
                }
            }
            // Jump up one dir and repeat glob search
            if let Some(parent_dir) = curr_exe.parent() {
                curr_exe = parent_dir.to_path_buf();
            }
        }
    }
    let gz = option_decoder.expect("Could not find eapp tarball");

    let mut archive = Archive::new(gz);

    // Instead of having the library extract everything (which may take 5 mins)
    // we go over all entries and only extract new data (files which do not exist).
    let dst = eapp_dir.as_path();
    for entry in archive.entries().unwrap() {
        match entry {
            Ok(mut entry) => {
                let entry_path = match entry.path() {
                    Ok(p) => p,
                    Err(_) => continue,
                };

                let existing_f = dst.join(entry_path);
                if existing_f.exists() {
                    //println!("Skipping existing eapp file {}", &existing_f.to_string_lossy()[..]);
                    continue;
                }

                println!("Extracting eapp file {}", &existing_f.to_string_lossy()[..]);
                if let Err(_e) = entry.unpack_in(&dst) {
                    //println!("Error unpacking eapp file: {}", e);
                }
            }
            Err(e) => {
                println!("Error unpacking eapp file: {}", e);
            }
        }
    }

    println!("Done extracting eapp dir.");

    return eapp_dir;
}
