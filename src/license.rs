/*************************************************************************************
 * Copyright (C) DeVilliers Technology, LLC - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited
 * Proprietary and confidential
 * Written by Jeffrey McAteer <jeffrey.mcateer@devil-tech.com>, Feb 2019 - Jan 2021
 *************************************************************************************/

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
  let mut db_dir = app_dirs::app_dir(
    app_dirs::AppDataType::UserData, &crate::APP_INFO, "db"
  ).expect("Could not create db directory");

  db_dir.push("loci.license.txt");

  db_dir
}



#[inline(always)]
pub fn check_license() -> bool {
  // If the feature string is >1 char long we have a valid license
  return get_licensed_features().len() > 1;
}

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
      Err(_e) => { }
    }
  }

  // Check env
  if let Ok(env_lic) = std::env::var(crate::LICENSE_TXT) {
    lic_txt = env_lic;
  }

  // Verify lic_txt was signed by one of LICENSE_ISSUERS_KEYS

  let mut lic_txt_reader = Cursor::new(lic_txt.as_bytes());

  match Message::from_armor_single(&mut lic_txt_reader) {
    Ok((msg, _)) => {
      for issuer_key in LICENSE_ISSUERS_KEYS.iter() {
        let mut issuer_key_reader = Cursor::new(issuer_key.as_bytes());
        match SignedPublicKey::from_armor_single(&mut issuer_key_reader) {
          Ok((pkey, _)) => {
            if let Ok(()) = msg.verify(&pkey) {
              
              // License is good, TODO return features / check expire dates and HWID?

              features_s += "base,";
              
            }
          }
          Err(e) => {
            println!("issuer_key e={}", e);
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




