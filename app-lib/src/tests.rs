
// Only compiled with cfg!(test)

// Import everything visible to the crate (lib.rs)
use super::*;

use std::env;

#[test]
fn test_license_acceptance() {
  
  let bad_license = r#"
This doesn't even make sense!
"#;
  env::set_var("LOCI_LICENSE_TXT", bad_license);
  assert!(!license::license_is_valid(), "Some random text was detected as a good license!");

  let bad_license = r#"
-----BEGIN LICENSE MSG-----
license_owner=This text was modified
features=
hwid=
issue_timestamp=2021-05-28 13:05
expire_timestamp=2021-05-28 18:05
-----END LICENSE MSG-----
-----BEGIN PGP SIGNATURE-----

iQEzBAABCAAdFiEEC1qgfY4z/ARiC7LLuorp75HMMxgFAmCxIvEACgkQuorp75HM
MxhPxQf/S7vUzn61+PH4/+iCJ5+Hxbh4gfv+b5G9a3PWYz6hNtWh+25T+yMyFtm8
DOKDirf3+F6V8ypgi0oSDlRXcvNWujhVBzH1TATZTi6PhIutLJ567Ms32dv153Wh
ej843/he+y7FumyuGS63XDxeERAxe8fl+8iBqxmhsIw4lWPD/+x3wsfvnJSATWhm
p/5RA9qPqyd2Sor/i2lxr42vIzGEOnpArAWUOlr5sOJ7hRDtkMbrf6nB+sE3SuZj
XbrqIfa3TkeqQeIyZ76BBfNyv+ibIQNxUnNhmlDLyJvCrqxzAhT5oeWdooaMp5J9
/8MIVlIjkIIvQ0LYVRDo2HKD8i8J8A==
=Ctad
-----END PGP SIGNATURE-----
"#;
  env::set_var("LOCI_LICENSE_TXT", bad_license);
  assert!(!license::license_is_valid(), "A known-bad license was detected as a good license!");
  assert!(!license::has_licensed_feature("core"), "A known-bad license was detected to have feature 'core'");

  let good_license = r#"
-----BEGIN LICENSE MSG-----
license_owner=An official test license
features=featureA
hwid=
issue_timestamp=2021-06-06 18:46
expire_timestamp=2030-01-01 00:00
-----END LICENSE MSG-----
-----BEGIN PGP SIGNATURE-----

iQEzBAABCAAdFiEEC1qgfY4z/ARiC7LLuorp75HMMxgFAmC9UFoACgkQuorp75HM
MxgCtQf/dw/pxz8p7b4ivNSlIUI9FdMmcMDc6Wemv1r4CR8RWZXx9VhhhJ+UUf/N
bi+5o830+F+gciWzFE8NU5NO0L7jKARQsa4qTZf+CNudl4f759xiCj7li/WkpfNn
lGUgyk/hVyl59DZvtK+ljnGL9jHEOXWubTpk2tBRycQsRU50xc73NoSVLYco0bOz
B8kuqF5iE9PUkmgUsna0uZGuO1+I0LnptCx6/4nGncYqE9vZaPk5ed/tBsQpuLkc
nOd3xQpLd+LLPtXYVY5wL6REoLCdvBk3sFuwXQ+4sCXSNPD4moM2+OmlSyJXvzwC
0gEyQyhVLyRO1T3SAGql80WdZUDLIg==
=MNMr
-----END PGP SIGNATURE-----
"#;
  env::set_var("LOCI_LICENSE_TXT", good_license);
  assert!(license::license_is_valid(), "A known-valid license was not detected as bing valid!");
  assert!(license::has_licensed_feature("featureA"), "A known-valid license issued with featureA does not report having featureA!");

  // Bad not b/c crypto sig is wrong, bad b/c no machine will ever give a HWID of "BAD-HWID"
  // These tests execute code which checks the HWID.
  let bad_license = r#"
-----BEGIN LICENSE MSG-----
license_owner=An official test license
features=featureB
hwid=BAD-HWID
issue_timestamp=2021-06-08 08:45
expire_timestamp=2030-01-01 00:00
-----END LICENSE MSG-----
-----BEGIN PGP SIGNATURE-----

iQEzBAABCAAdFiEEC1qgfY4z/ARiC7LLuorp75HMMxgFAmC/ZmwACgkQuorp75HM
MxiFFAf/ULaHI6jVUE2f4LCSKpRZv+unrPlNu6dpxUFGb35lpYhV1FeSshwuVNLb
ySYh+TeN3PbTYTo5nJB21+toFkfeJHGy7D9gF+TsHVF/GiLgyPdE7dn3hYDs8vMW
HSkPWHFjn3AlxF0/KNSCs8a3m0DeF7u0OLzie6u2oAPn8dU7hUm4xw47d6hVrv9N
vt8D5iY6WTlPZcg05na5XsKazlPWTuwB8v0pDC1c5NCklBvZ2fAJnTSdKDlKy49t
gsbhqR2OlwUUEG2DCwGbh8rLcBvXhhFLaRJOGpSUF0Qr7eB43mMv2KtI61rZOPGQ
bq+QcUiwcLaHi7F3lZJ6Fj2AKwzjjg==
=+Ohc
-----END PGP SIGNATURE-----
"#;
  
  {
    use std::io::Write;
    // Put license in temp file to excersize an if statement
    let mut lic_file = tempfile::NamedTempFile::new().expect("Could not create temp file");
    lic_file.write_all(bad_license.as_bytes()).expect("Could not write to temp file");
    // Remove LOCI_LICENSE_TXT from prev tests
    env::remove_var("LOCI_LICENSE_TXT");
    // Go from mutable File to named path we can assign to LOCI_LICENSE_FILE_PATH
    let lic_file = lic_file.into_temp_path();
    // Override default file location
    env::set_var("LOCI_LICENSE_FILE_PATH", lic_file);
    
    assert!(!license::license_is_valid(), "A signed license with a HWID that should never exist on a real machine was accepted as valid; no machine should report \"BAD-HWID\" as a hwid.");
  }

}

#[test]
fn test_hwid() {
  assert!(license::get_host_hwid() != "", "license::get_host_hwid should never return an empty string!");
}


#[test]
fn test_db() {
  let mut conn = open_app_db("unit_tests").expect("Could not open a DB for tests!");
  conn.execute_batch(r#"
CREATE TABLE IF NOT EXISTS test_points (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  lat REAL default 0.0,
  lon REAL default 0.0
)
"#).expect("Failed to exec sql");

  let num_points = 10;

  let tx = conn.transaction().expect("Could not get a transaction to use for inserting data");
  for i in 0..num_points {
    let mut statement = tx.prepare("INSERT INTO test_points (name, lat, lon) VALUES (:name, :lat, :lon)").expect("Could not prepare statement");
    statement.execute(&[
      (":name", format!("POINT-{}", i).as_str()),
      (":lat", format!("{}", 0.5 * i as f64).as_str()),
      (":lon", format!("{}", 0.3 * i as f64).as_str()),
    ]).expect("statement failed to execute");
  }
  tx.commit().expect("Could not commit changes to DB");

  // TODO query points back? This excersises all branches and sqlite is rock solid, so not much point investing time here.

  conn.execute_batch(r#"
DELETE FROM test_points;
"#).expect("Failed to exec sql");
}

#[test]
fn test_shmem() {
  use rand::Rng;

  // Spawn 2 threads, have 1 wait for data from the other thread.
  let data_s: String = rand::thread_rng()
        .sample_iter(&rand::distributions::Alphanumeric)
        .take(12)
        .map(char::from)
        .collect();

  crossbeam::scope(|s| {
    // Poll for data
    s.spawn(|_| {
      let mut remaining_checks: usize = 110;
      let s = open_shmem_file("test01", 128).expect("Could not open 128-byte shmem file 'test01'");
      loop {
        std::thread::sleep( std::time::Duration::from_millis(50) );

        // Read shared memory
        let shmem_buffer = unsafe{ s.as_slice() };
        let data_bytes = data_s.as_bytes();
        let mut shared_mem_matches = true;
        for i in 0..data_bytes.len() {
          if shmem_buffer[i] != data_bytes[i] {
            shared_mem_matches = false;
          }
        }
        // Test if == data_s and break if so
        if shared_mem_matches {
          break; // test passed!
        }

        remaining_checks -= 1;
        if remaining_checks < 1 {
          panic!("Shared memory did not see the written value in ~5000ms, test failed!");
        }
      }
    });

    // Write the data in a new thread
    s.spawn(|_| {
      let mut s = open_shmem_file("test01", 128).expect("Could not open 128-byte shmem file 'test01'");
      
      // Wait for 100ms before writing data
      std::thread::sleep( std::time::Duration::from_millis(100) );
      
      let shmem_buffer = unsafe { s.as_slice_mut() };

      let data_bytes = data_s.as_bytes();
      for i in 0..data_bytes.len() {
        shmem_buffer[i] = data_bytes[i];
      }
    });

  }).expect("Could not join threads post-test!");

}



#[test]
fn test_capi() {
  let mut buffer: [u8; 512] = [0; 512];

  capi::loci_get_app_root(buffer.as_mut_ptr(), 512);
  


}


