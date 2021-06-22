
import pathlib

import btool
from tests import *
from tests.utils import *

def run_all_tests(args):

  cargo_test_cmd = ['cargo', 'test']
  if btool.utils.host_is_linux() and not 'SKIP_TARPAULIN' in os.environ:
    cargo_test_cmd = [
      'cargo', 'tarpaulin',
      '--tests', '--line', '--out', 'html',
      '--output-dir', 'target',
      '--run-types', 'Tests', '--verbose',
    ]
    # Also find every "coverage.json" file and delete it
    for f in pathlib.Path('.').rglob('coverage.json'):
      if 'tarpaulin' in str(f):
        print('Deleting {}'.format(f))
        os.remove(f)

  unit_test_cmd(j('app-kernel'), cargo_test_cmd + ['--package', 'app-kernel'])
  unit_test_cmd(j('app-lib'),    cargo_test_cmd + ['--package', 'app-lib'])

  unit_test_cmd(s('server-webgui'), cargo_test_cmd + ['--package', 'server-webgui'])
  
  api_test_cmd(s('server-webgui'), ['cargo', 'run', '--release'],
    lambda: tcp_connects_within('127.0.0.1', 7010, 5),
    lambda: http_GET_contains('http://127.0.0.1:7010/', '<title>Loci</title>'),
    lambda: http_GET_contains('http://127.0.0.1:7010/api/something/more-junk?a=b', ''),
    lambda: ws_ctx('ws://127.0.0.1:7010/ws',
      lambda ws: ws.send('{"hello world":123}'),
      lambda ws: 'hello world' in str(ws.recv()),
    ),
  )



