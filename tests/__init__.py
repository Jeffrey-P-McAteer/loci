
# python -m pip install --user requests
import requests
# python -m pip install --user websocket-client
import websocket

import os
import sys
import subprocess
import time
import socket
from pathlib import Path
import webbrowser

# The tests internal modules
from tests.testall import run_all_tests

# We re-use a number of utilities designed for building subprograms
import btool
from btool import j, e, download_tools
from btool import main as btool_main
from btool.utils import within
from btool.utils import host_is_linux
from btool.utils import die


def main(args=sys.argv):
  if not e('readme.md'):
    die('Must be run from loci root like "python -m tests [args]')
  
  download_tools()

  # Compile everything "hostonly" before running tests
  btool_main(['hostonly'])

  # Now we have all SDKs installed, run the tests
  # The first test to fail stops the entire script, having less
  # than 100% passing should not be normal.

  test_start = time.time()

  run_all_tests(args)

  test_end = time.time()
  duration_s = round(test_end - test_start, 2)
  print('Total test time: {}s'.format(duration_s))

  # Finally, open all .html output reports in a browser
  if not 'nobrowser' in args:
    print('Opening reports in browser...')
    for file in Path('.').rglob('tarpaulin-report.html'):
      print('{}'.format(file))
      webbrowser.open(str(file.absolute()))

  print('UNIT_TESTS_TOTAL={}'.format(os.environ.get('UNIT_TESTS_TOTAL', '0')))
  print('UNIT_TESTS_PASSED={}'.format(os.environ.get('UNIT_TESTS_PASSED', '0')))
  print('UNIT_TESTS_FAILED={}'.format(os.environ.get('UNIT_TESTS_FAILED', '0')))
    

