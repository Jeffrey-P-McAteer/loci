#!/usr/bin/env python

# This program uses your GPG private key to 
# create and sign Locorum licenses.
# A list of GPG public keys which are allowed to
# create licenses is hard-coded in src/license.rs

# Generated license files will be placed under
# out/issued_licenses/<NAME>.license.txt

# Execution:
#  python -m license_tool ['License Owner' ['features string' ['hwid string' ['expire timestamp']]]]
#  python -m license_tool 'License Owner' 'features string' 'hwid string' 'expire timestamp'
#  python -m license_tool 


import os
import sys
import datetime
import re

# python -m pip install --user python-gnupg
import gnupg

# python -m pip install --user HumanTime
import HumanTime


def main():
  license_d = os.path.join('out', 'issued_licenses')
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
  
  expire_timestamp = sys.argv[4] if len(sys.argv) > 4 else input('See https://github.com/AgalmicVentures/HumanTime#usage for soft format details{}expire timestamp (HumanTime):'.format(os.linesep)).strip()
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

  # normalization - we sign the text w/o whitespace
  license_text_normalized = ''.join(license_text.split())

  signed_license_text = gpg.sign(license_text_normalized, keyid=sign_key_id, clearsign=False, detach=True)
  
  license_txt_file_content = (
    ('-' * 5) + 'BEGIN LICENSE MSG' + ('-' * 5) + os.linesep + 
    license_text + os.linesep + 
    ('-' * 5) + 'END LICENSE MSG' + ('-' * 5) + os.linesep +
    str(signed_license_text)
  );

  print(license_txt_file_content)

  print('')

  # Save to license_d/<NAME>[.N].license.txt
  # where .N is generated for duplicate names
  safe_name = re.sub('[\W_]+', '', license_owner)
  n = 0
  while True:
    if n == 0:
      license_out_f = os.path.join(license_d, safe_name+".license.txt")
    else:
      license_out_f = os.path.join(license_d, safe_name+str(n)+".license.txt")

    if os.path.exists(license_out_f):
      print('WARNING: not overwriting existing license file {}'.format(license_out_f))
      n += 1
      continue

    print('Saving license to {}'.format(license_out_f))
    with open(license_out_f, 'w') as fd:
      fd.write(license_txt_file_content)

    break


if __name__ == '__main__':
  main()

