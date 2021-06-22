
# python -m pip install --user requests
import requests
# python -m pip install --user websocket-client
import websocket

import os
import sys
import subprocess
import time
import socket
import re

# Tests __init__
from tests import *

# We re-use a number of utilities designed for building subprograms
import btool
from btool import j, e, download_tools
from btool.utils import within
from btool.utils import host_is_linux

HTTP_TIMEOUT_S = 1.5

# Join 'app-subprograms' on and curry to j() to return full path.
def s(*path):
  return j('app-subprograms', *path)

def unit_test_cmd(cwd, cmd):
  print('Running unit tests within {}'.format(cwd))
  check_procs = not ('ALLOW_TESTS_TO_FAIL' in os.environ and len(os.environ['ALLOW_TESTS_TO_FAIL']) > 0)
  within(
    cwd,
    lambda: subprocess.run(list(cmd), check=check_procs),
    lambda: record_unit_test_metadata_to_os_environ(cmd),
  )

# Used to make graphs when running all tests in same process.
def record_unit_test_metadata_to_os_environ(cmd):
  test_stdout = subprocess.run(
    list(cmd),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False
  ).stdout.decode(sys.stdout.encoding)

  for line in test_stdout.splitlines():
    line = line.strip()
    if line.startswith('test result:'):
      # Cargo tests!
      pass_fail_nums = re.findall(r'\d+', line)
      passed = int(pass_fail_nums[0])
      failed = int(pass_fail_nums[1])
      ignored = int(pass_fail_nums[2])
      total = passed + failed + ignored

      os.environ['UNIT_TESTS_TOTAL'] = str(
        int(os.environ.get('UNIT_TESTS_TOTAL', '0')) + total
      )
      os.environ['UNIT_TESTS_PASSED'] = str(
        int(os.environ.get('UNIT_TESTS_PASSED', '0')) + passed
      )
      os.environ['UNIT_TESTS_FAILED'] = str(
        int(os.environ.get('UNIT_TESTS_FAILED', '0')) + failed
      )



def api_test_cmd(cwd, cmd, *tests):
  print('Running API tests within {}'.format(cwd))
  
  check_procs = not ('ALLOW_TESTS_TO_FAIL' in os.environ and len(os.environ['ALLOW_TESTS_TO_FAIL']) > 0)

  child = None
  def spawn_program_under_test():
    nonlocal child
    child = subprocess.Popen(list(cmd))
  
  within(cwd, spawn_program_under_test)

  # We assume all servers will start in < .5 seconds
  time.sleep(0.5)

  for test in list(tests):
    try:
      test()
    except Exception as e:
      try:
        child.kill()
      except Exception as ignored:
        pass
      if check_procs:
        raise e

  child.kill()

def tcp_connects_within(host, port, timeout_s):
  while timeout_s > 0:
    timeout_s -= 0
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.settimeout(HTTP_TIMEOUT_S)
      if s.connect_ex((host, port)) == 0:
        # is open, test passes
        s.close()
        return
      else:
        continue
    except e:
      continue
    time.sleep(1)

  raise Exception('TCP connect fail: expected {} to connect within {} seconds.'.format(
    (host, port), timeout_s 
  ))

def http_GET_contains(url, expected_subresponse):
  response = requests.get(url, timeout=HTTP_TIMEOUT_S)
  passed = expected_subresponse in response.text
  if not passed:
    exception_msg = 'HTTP FAIL: Expected "{}" to return "{}" but instead got:'.format(url, expected_subresponse)+os.linesep+response.text
    raise Exception(exception_msg)

def ws_ctx(url, *ws_cmds):

  websocket.setdefaulttimeout(HTTP_TIMEOUT_S)

  ws = websocket.create_connection(url)
  for cmd in list(ws_cmds):
    cmd(ws)
  ws.close()

