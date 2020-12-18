#!/usr/bin/env python


# This program uses your GPG private key to 
# create and sign Locorum licenses.
# A list of GPG public keys which are allowed to
# create licenses is hard-coded in src/license.rs

# Generated license files will be placed under
# target/gen_licenses/<NAME>.license.txt

import os
import sys
import datetime

# python -m pip install --user python-gnupg
import gnupg

# python -m pip install --user HumanTime
import HumanTime


def main():
  license_d = os.path.join('target', 'gen_licenses')
  if not os.path.exists(license_d):
    os.makedirs(license_d)

  gpg = gnupg.GPG()
  gpg.encoding = 'utf-8'

  sign_key_id = None
  for k in gpg.list_keys(True):
    sign_key_id = k['keyid']
    break

  if not sign_key_id:
    print('You have no private keys to sign with!')
    print('Exiting.')
    sys.exit(1)

  print('Signing using the following public key:')
  print(gpg.export_keys(sign_key_id))

  license_owner = sys.argv[1] if len(sys.argv) > 1 else input('license_owner:').strip()
  
  features = sys.argv[2] if len(sys.argv) > 2 else input('features:').strip()
  
  hwid = sys.argv[3] if len(sys.argv) > 3 else input('hwid (none makes license req. online activation):').strip()
  
  timestamp_f = '%Y-%m-%d %H:%M'

  issue_timestamp = datetime.datetime.now().strftime(timestamp_f)
  
  expire_timestamp = sys.argv[4] if len(sys.argv) > 4 else input('See https://github.com/AgalmicVentures/HumanTime#usage for soft format details\nexpire timestamp (HumanTime):').strip()
  expire_timestamp = HumanTime.parseTime(expire_timestamp).strftime(timestamp_f)

  license_text = '''
license_owner={license_owner}
features={features}
hwid={hwid}
issue_timestamp={issue_timestamp}
expire_timestamp={expire_timestamp}
  '''.format(
    license_owner=license_owner,
    features=features,
    hwid=hwid,
    issue_timestamp=issue_timestamp,
    expire_timestamp=expire_timestamp,
  ).strip()

  print(('-' * 6) + ' license_text ' + ('-' * 6))
  print(license_text)
  print(('-' * 6) + ' license_text ' + ('-' * 6))
  print('')
  print('')

  signed_license_text = gpg.sign(license_text, keyid=sign_key_id)
  print(signed_license_text)

  print('')




if __name__ == '__main__':
  main()

