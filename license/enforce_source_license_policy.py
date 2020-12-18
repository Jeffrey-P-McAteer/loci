#!/usr/bin/env python

# Usage:
#   python license/enforce_source_license_policy.py [update]
# 
# Writes various license stubs in ./license/ to source code
# under ./src/
#

import os
import glob
import sys

def main():
  # Move to directory above this file's parent (aka the repo root)
  os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

  update_if_existing_license = 'update' in sys.argv

  c_source_header = ""
  with open(os.path.join('license', 'c_source_header.txt'), 'r') as fd:
    c_source_header = fd.read().strip()

  for src_f in glob.glob('src/**/*.rs', recursive=True):
    src_content = ''
    with open(src_f, 'r') as fd:
      src_content = fd.read()

    if not src_content.startswith(c_source_header):
      print('Adding license header to {}'.format(src_f))
      
      if 'Copyright' in src_content[0:min(len(src_content), 200)]:
        if not update_if_existing_license:
          print('Refusing to apply license to a file that already contains "Copyright" in the first 200 bytes')
          print('Remove existing license text in {} or pass the "update" argument before applying this one!')
          sys.exit(1)
          continue

        # Remove all chars from [0] to the first "*/"
        end_of_license_i = src_content.index("*/") + 3
        src_content = src_content[end_of_license_i:].lstrip()


      with open(src_f, 'w') as fd:
        fd.write(c_source_header)
        fd.write('\n')
        fd.write('\n')
        fd.write(src_content)

    else:
      print('License header present in {}'.format(src_f))



if __name__ == '__main__':
  main()

