
import time
import os
import sys
import subprocess
import traceback

# Import our children
from test import posrep_sqlite_to_ws_performance

# All of these have a .test() function defined
# All .test() functions assume they run at the root of the repository,
# and they execute os.environ['LOCI_RELEASE_EXE'] if they need loci.exe.
test_modules = [
  posrep_sqlite_to_ws_performance
]

def run_tests():

  print('Running build...')
  subprocess.run([
    sys.executable, '-m', 'build', 'release'
  ], check=True)

  os.environ['LOCI_RELEASE_EXE'] = os.path.join('target', 'release', 'loci')
  if not os.path.exists(os.environ['LOCI_RELEASE_EXE']):
    os.environ['LOCI_RELEASE_EXE'] = os.path.join('target', 'release', 'loci.exe')

  os.environ['LOCI_RELEASE_EXE'] = os.path.abspath(os.environ['LOCI_RELEASE_EXE'])

  print('')

  num_failures = 0
  misc_reports = []

  for t in test_modules:
    time_start_s = time.time()
    print('Testing {}'.format(t.__name__), end='', flush=True)
    try:
      misc_reports.append( t.test() )
      time_delta_s = round( time.time() - time_start_s, 2)
      print(' PASS ({}s)'.format(time_delta_s), flush=True)
    except Exception as e:
      tb = traceback.format_exc()
      time_delta_s = round( time.time() - time_start_s, 2)
      print(' FAIL ({}s)'.format(time_delta_s), flush=True)
      num_failures += 1
      misc_reports.append( tb )
      time.sleep(0.1)

  print('')
  print('{}/{} tests passed'.format(len(test_modules) - num_failures, len(test_modules)))
  print('')
  print('Misc reports:')
  for r in misc_reports:
    print('')
    print('{}'.format(r))

  if num_failures > 0:
    sys.exit(1)


