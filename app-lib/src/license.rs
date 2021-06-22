

const LICENSE_ISSUERS_KEYS: [&'static str; 3] = [
    // Jeffrey's PHP key, also at http://blog.jmcateer.pw/jeff.asc
    r#"-----BEGIN PGP PUBLIC KEY BLOCK-----

mQENBF/Obf0BCADX871ZV1NERBNGcQ2B19aBz3LQs2jGDaDQAyquDmCjYyFGfT+q
XR+fJrjlsK47wtoXQVNo7nZStCYn9HmG1CDa3vONxW+AU8aaao+djMupWkL61vO0
lr3o2V7Zs1vp0htOBggObgp8Z5Fnk94hGccHegTf7ZR9zHSLL5pvi3LFScHkShqI
uWJJ6c0I3hs7CUhjSRwmSvRogS9Zo0YzSr2O/Ky/l4wxc4zJsWBsezb/m8fgvgV0
IWrAkXjN2x8NOBH5uTAFIY0ZnHzeOhyGQar1u2P/OX0DhnnxywEqS5BhN49puWwN
4kayyikvfEGuqiKorsQCsHj8I/L/8BAYoxq9ABEBAAG0LUplZmZyZXkgTWNBdGVl
ciA8amVmZnJleS5wLm1jYXRlZXJAZ21haWwuY29tPokBTgQTAQgAOBYhBAtaoH2O
M/wEYguyy7qK6e+RzDMYBQJfzm39AhsDBQsJCAcCBhUKCQgLAgQWAgMBAh4BAheA
AAoJELqK6e+RzDMYDz0H/3cV0OUZQmkhTpl4xTHF/rAdgpLVJD/qns3kEQg578Kj
CqzdMBN8PohSgUcZ396iBh2dGFdEEGr36rqye0AF2vzZZyIYO59eHN0IfK+sJizv
9LNB9Lxh5miY9le9JqZ0pqQPZv+lVAI2mvszw5QUfnpc9U1/KChRYdyIHoFIH4j/
bi3XxmfVxCH8qd8rimT1LwYZayXvhwutCP4KN/Y8OfV5r32dtuC6BU+xy9abOAaB
y8h8oAkCqR3mbOMsxsEAh7rn2tlzacRE2mN1bo94iTQ6WzATNNWOKrMKFwNA4Syo
2eYftn6LEgzVmud/xIVDsKU6WAaHmpieB8Tb8fT/mAW5AQ0EX85t/QEIAM32Af0M
kTUSVHoV+vBiG0py0A0fuiYij6K7VY9WbojBGlN98+6GgH06jZI4NoHtVqEIhz6R
DRupInnGh87C6/BBFkEDTkMi8cS9YTAb4f5/HBt+6H66C5/zbKbdx3QKObM41bCp
0Ldy49h0JQmKtUPZa80txw9MXEIyOC3TcqxFDfQdooXK11ZQ7lw4gywzv87agdgY
G6SIdqOTERL/U6IaR7OgbtH/igMfAn0lskkxhNtsTGRfnY6h7EPMf0gdSnVceqPv
gH6XMMXA4iMHhSTGmxUFA1X1DotG/HhpSUVS1BJSuhGVLHETRe+C9mCGJ+O9y9XA
ucmCktu/fGx6TscAEQEAAYkBNgQYAQgAIBYhBAtaoH2OM/wEYguyy7qK6e+RzDMY
BQJfzm39AhsMAAoJELqK6e+RzDMYX6UH/0SzCEelHQzn8DN18cYIJJ4HgKyhhajo
VQvXhJ2v8dFFuiuUzM226v5Q7R4SI0XR/1p9XJTP2fo1dHwUNxsr/w4fZmWDT8eH
ZHIwQX6KOaPzGjge/E6gr2BB25kl8B1ZmSnxMZRzRkqsZN/zPbHSvklQbck60ciA
LqjJM0qhPfLJ2fMfJbNUbSDIwNSh5vO4NcMY7xnqJUB/cK767Zue0jRTwDXg7td7
WAmbYAbwWB9d5tDvI6KIbR3idp5hTxAy4uSiSTQCwawJbPVxEOH8hAzqtMshStrA
oFflg4sWT0bswwa6dmDSn+xhft46dqbpkmzCPgxM8ltmut+DSSb4RGg=
=lV4c
-----END PGP PUBLIC KEY BLOCK-----
"#,
    r#"This is an invalid PGP key
"#,
    r#"This is an invalid PGP key
"#,
];

use std::path::PathBuf;

pub fn license_file() -> PathBuf {
    if let Ok(file_override_path) = std::env::var("LOCI_LICENSE_FILE_PATH") {
        PathBuf::from(file_override_path)
    }
    else {
        let mut db_dir = crate::get_app_root();
        db_dir.push("loci.license.txt");
        db_dir
    }
}

#[inline(always)]
pub fn license_is_valid() -> bool {
    // If the feature string is >1 char long we have a valid license
    return get_licensed_features().len() > 1;
}

#[allow(dead_code)]
#[inline(always)]
pub fn has_licensed_feature(feature: &str) -> bool {
    get_licensed_features().contains(feature)
}

// "" means no license, "base"+feat-a,feat-b is the feature string.
#[inline(always)]
pub fn get_licensed_features() -> String {
    use pgp::*;
    use std::io::Cursor;

    let mut features_s = String::new();

    let mut lic_txt = String::new();

    // Check file
    let f = license_file();
    if f.exists() {
        match std::fs::read_to_string(f) {
            Ok(s) => lic_txt = s,
            Err(_e) => {}
        }
    }

    // Check env
    if let Ok(env_lic) = std::env::var("LOCI_LICENSE_TXT") {
        lic_txt = env_lic;
    }

    // Split license message & PGP signature
    let chunks: Vec<&str> = lic_txt.split("-----END LICENSE MSG-----").collect();

    if chunks.len() != 2 {
        return features_s;
    }

    let msg_txt = chunks[0].replace("-----BEGIN LICENSE MSG-----", "");
    let msg_txt = msg_txt.trim();
    let sig_armor = chunks[1];
    let sig_armor = sig_armor.trim();

    //println!("msg_txt={}", &msg_txt);
    //println!("sig_armor={}", &sig_armor);

    let orig_msg_txt = msg_txt.clone();

    // normalize msg_txt by splitting on whitespace and joining without:
    let msg_txt: String = msg_txt.chars().filter(|c| !c.is_whitespace()).collect();

    // Verify msg_txt was signed by one of LICENSE_ISSUERS_KEYS

    let mut sig_armor_reader = Cursor::new(sig_armor.as_bytes());

    match Message::from_armor_single(&mut sig_armor_reader) {
        Ok((mut msg, _headers)) => {
            //println!("msg={:?}", msg);
            //println!("headers={:?}", headers);

            if let Message::Signed {
                ref mut message,
                one_pass_signature: _,
                signature: _,
            } = msg
            {
                *message = Some(Box::new(Message::Literal(packet::LiteralData::from_str(
                    "memory.txt",
                    &msg_txt[..],
                ))));
            }

            for issuer_key in LICENSE_ISSUERS_KEYS.iter() {
                let mut issuer_key_reader = Cursor::new(issuer_key.as_bytes());
                match SignedPublicKey::from_armor_single(&mut issuer_key_reader) {
                    Ok((pkey, _headers)) => {
                        //println!("pkey={:?}", &pkey);
                        //println!("headers={:?}", &headers);

                        match msg.verify(&pkey) {
                            Ok(()) => {
                                // License is good,
                                // check expire + hwid

                                if let Some(hwid) = parse_val(&orig_msg_txt, "hwid") {
                                    // if hwid is empty that means the license may be used on any machine
                                    // and we rely on a soft online check to prevent duplicate license use.
                                    if hwid.len() > 1 {
                                        if get_host_hwid() != hwid {
                                            // This license is signed but it was issued to a different machine!
                                            return features_s;
                                        }
                                    }
                                }

                                if let Some(expire_timestamp) = parse_val(&orig_msg_txt, "expire_timestamp")
                                {
                                    // if current time > expire_timestamp this license is invalid.
                                    // Also notice we don't put a huge amount of effort into normalizing
                                    // across timezones, so some customers may get an extra 24 hours for free.
                                    match chrono::naive::NaiveDateTime::parse_from_str(
                                        &expire_timestamp,
                                        "%Y-%m-%d %H:%M",
                                    ) {
                                        Ok(expire_dt) => {
                                            let now_time = chrono::Utc::now().naive_local();
                                            let diff = expire_dt - now_time;
                                            // We expect expire_dt to be in the future, so if "diff"
                                            // has a negative value that means the license has expired.

                                            if diff.num_days() < 0 {
                                                // There are <0 days remaining on this license!
                                                return features_s;
                                            }
                                        }
                                        Err(e) => {
                                            println!("Error parsing expire_timestamp: {}", e);
                                            // A badly formatted timestamp will invalidate the license
                                            return features_s;
                                        }
                                    }
                                }

                                // Parse feature string (this actually "activates" the license as all checks have passed)

                                features_s += "base,";

                                if let Some(features_list) = parse_val(&orig_msg_txt, "features") {
                                    features_s += &features_list;
                                }
                            }
                            Err(e) => {
                                println!("verify e={}", e);
                            }
                        }
                    }
                    Err(_e) => {
                        // Unecessary unless we see public PGP keys not validating licenses
                        //println!("issuer_key e={}", e);
                    }
                }
            }
        }
        Err(e) => {
            println!("lic_txt_reader e={}", e);
        }
    }

    return features_s;
}

#[inline(always)]
fn parse_val(license_txt: &str, key: &str) -> Option<String> {
    for line in license_txt.lines() {
        let line = line.trim();
        if line.starts_with(key) {
            if let Some(val) = line.split('=').skip(1).next() {
                return Some(val.to_string());
            }
        }
    }
    return None;
}

#[inline(always)]
pub fn get_host_hwid() -> String {
    get_id()
}

/**
 * The below fns come from https://github.com/tilda/rust-hwid.
 * The entire library is 40 lines long so we just copy the implementation here
 * instead of adding it to Cargo.toml; this has the benefit of making new
 * hardware and OSes easy to support.
 *
 * The original implementation remains (c) tilda under the MIT license.
 */

// rust-hwid
// (c) 2020 tilda, under MIT license

#[cfg(target_os = "windows")]
use winreg::enums::HKEY_LOCAL_MACHINE;

#[cfg(target_os = "windows")]
#[inline(always)]
fn get_id() -> String {
    if let Ok(hive) = winreg::RegKey::predef(HKEY_LOCAL_MACHINE)
        .open_subkey("\\\\SOFTWARE\\Microsoft\\Cryptography")
    {
        if let Ok(id) = hive.get_value("MachineGuid") {
            return id;
        }
    }

    let cmd = std::process::Command::new("wmic")
        .args(&["csproduct", "get", "UUID"])
        .output()
        .expect("Failed to get HWID");

    let stdout = String::from_utf8_lossy(&cmd.stdout);
    let stdout = stdout.replace("UUID", "");

    // Just remove whitespace and call it an ID
    return stdout.chars().filter(|c| !c.is_whitespace()).collect();
}

#[cfg(target_os = "linux")]
#[inline(always)]
fn get_id() -> String {
    use std::path::Path;

    if Path::new("/var/lib/dbus/machine-id").exists() {
        if let Ok(id) = std::fs::read_to_string("/var/lib/dbus/machine-id") {
            return id.trim().to_string();
        }
    }

    if Path::new("/etc/machine-id").exists() {
        if let Ok(id) = std::fs::read_to_string("/etc/machine-id") {
            return id.trim().to_string();
        }
    }

    panic!("No HWID file found!")
}

#[cfg(target_os = "android")]
#[inline(always)]
fn get_id() -> String {
    use std::fs;
    // We depend on app-kernel-android to set LOCI_DATA_DIR
    // and create this file and write the value of ANDROID_ID into it.
    if let Ok(data_dir) = std::env::var("LOCI_DATA_DIR") {
        let id_file: PathBuf = [&data_dir, "machine_id.txt"].iter().collect();
        match fs::read_to_string(id_file) {
            Ok(machine_id) => {
                return machine_id.trim().to_string();
            }
            Err(e) => {
                eprintln!("Error reading machine_id.txt: {}", e);
            }
        }
    }
    panic!("No id file in LOCI_DATA_DIR! Check app-kernel-android to ensure it creates this information.");
}

#[cfg(target_os = "freebsd")]
#[cfg(target_os = "dragonfly")]
#[cfg(target_os = "openbsd")]
#[cfg(target_os = "netbsd")]
#[cfg(target_os = "darwin")]
#[inline(always)]
fn get_id() -> String {
    unimplemented!("MacOS / *BSD support is not implemented")
}
