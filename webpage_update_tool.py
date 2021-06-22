
# This tool calls other build-script tools
# such as btool, tests, and docs.

# It reads the output and measures execution time,
# then checks out the branch "www" to a temporary directory.

# After merging new data into existing .json files,
# it uses "git commit --amend" to alter the existing commit,
# ensuring no history is builtup for multiple runs.

# Assign CLEAN_WWW_HISTORIC_DATA=1 to remove all historic data + start fresh.

import os
import sys
import subprocess
import time
import datetime
import importlib
import traceback
import shutil
import tempfile
import json
import getpass
import socket
import ftplib
import webbrowser
import re

# This holds _all_ known 3rd-party python libs we depend on
# in btool, tests, and docs.
# Format is ("module", "module_pkg_name")
required_packages = [
  ('requests', 'requests'),
  ('websocket', 'websocket-client'),
  ('py7zr', 'py7zr'),
  ('PIL', 'Pillow'),
  ('matplotlib', 'matplotlib')
]

subprocess.run([sys.executable, '-m', 'ensurepip', '--default-pip'], check=True)

for module, module_pkg_name in required_packages:
  try:
    importlib.import_module(module)
  except:
    traceback.print_exc()
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', module_pkg_name], check=True)

# 3rd-party libs which we need pip to install (above) first
import matplotlib
import matplotlib.pyplot
import matplotlib.dates

# Our libs
import btool
from btool import j
import docs
import tests


def read_json(filename):
  try:
    with open(filename, 'r') as fd:
      return json.load(fd)
  except:
    traceback.print_exc()
    return {}

def save_json(filename, data):
  with open(filename, 'w') as fd:
    json.dump(data, fd)

def trim_list(the_list, max_items):
  if len(the_list) > max_items:
    the_list.pop(0)

# returns total, passed, failed.
# See record_unit_test_metadata_to_os_environ in tests/utils.py
def get_unit_test_data(repo_root, misc_measures):
  return int(os.environ.get('UNIT_TESTS_TOTAL', '0')), int(os.environ.get('UNIT_TESTS_PASSED', '0')), int(os.environ.get('UNIT_TESTS_FAILED', '0'))

# Returns total, in-progress, not-yet-started
def get_features_data(repo_root, misc_measures):
  features_stdout = subprocess.run(
    [sys.executable, '-m', 'feature_tracking_tool'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
    cwd=repo_root,
  ).stdout.decode(sys.stdout.encoding)

  total = 0
  in_progress = 0
  not_yet_started = 0
  for line in features_stdout.splitlines():
    if re.match(r'^\d+:\s', line):
      total += 1

    if re.match(r'^\s+BEGAN\s', line):
      in_progress += 1

    if re.match(r'^\s+TODO', line):
      not_yet_started += 1

  return total, in_progress, not_yet_started

# returns win64, linux_x86_64, linux_aarch64, android built distributable sizes
def get_build_sizes(repo_root, misc_measures):
  win_64_size = os.path.getsize(
    os.path.join(repo_root, 'out', 'www', 'win64.zip')
  )
  linux_x86_64_size = os.path.getsize(
    os.path.join(repo_root, 'out', 'www', 'linux_x86_64.tar.gz')
  )
  linux_aarch64_size = os.path.getsize(
    os.path.join(repo_root, 'out', 'www', 'linux_aarch64.tar.gz')
  )
  android_size = os.path.getsize(
    os.path.join(repo_root, 'out', 'www', 'loci.apk')
  )
  return win_64_size, linux_x86_64_size, linux_aarch64_size, android_size


def update_kpi_data(repo_root, misc_measures):
  delta_build_duration_s = misc_measures['delta_build_duration_s']
  full_build_duration_s = misc_measures['full_build_duration_s']
  publish_utc_epoch_seconds = misc_measures['publish_utc_epoch_seconds']

  build_data = read_json('kbi_build_data.json')
  if len(os.environ.get('CLEAN_WWW_HISTORIC_DATA', '')) >= 1:
    build_data = {}

  if not 'raw_build_times' in build_data:
    build_data['raw_build_times'] = []

  trim_list(build_data['raw_build_times'], 20)

  build_data['raw_build_times'].append({
    'utc_epoch_seconds': publish_utc_epoch_seconds,
    'delta_build_duration_s': delta_build_duration_s,
    'full_build_duration_s': full_build_duration_s,
  })


  if not 'unit_tests' in build_data:
    build_data['unit_tests'] = []

  trim_list(build_data['unit_tests'], 20)

  total, passed, failed = get_unit_test_data(repo_root, misc_measures)
  build_data['unit_tests'].append({
    'utc_epoch_seconds': publish_utc_epoch_seconds,
    'total': total,
    'passed': passed,
    'failed': failed,
  })

  if not 'build_size' in build_data:
    build_data['build_size'] = []

  trim_list(build_data['build_size'], 20)

  win_64_size, linux_x86_64_size, linux_aarch64_size, android_size = get_build_sizes(repo_root, misc_measures)
  build_data['build_size'].append({
    'utc_epoch_seconds': publish_utc_epoch_seconds,
    'win_64_size': win_64_size,
    'linux_x86_64_size': linux_x86_64_size,
    'linux_aarch64_size': linux_aarch64_size,
    'android_size': android_size,
  })


  if not 'features' in build_data:
    build_data['features'] = []

  trim_list(build_data['features'], 20)

  total, in_progress, not_yet_started = get_features_data(repo_root, misc_measures)
  build_data['features'].append({
    'utc_epoch_seconds': publish_utc_epoch_seconds,
    'total': total,
    'in_progress': in_progress,
    'not_yet_started': not_yet_started,
  })

  save_json('kbi_build_data.json', build_data)



def gen_kpi_graphs(repo_root):
  build_data = read_json('kbi_build_data.json')
  # We may assume build_data is initialized
  
  full_build_times_x = [datetime.datetime.fromtimestamp(x['utc_epoch_seconds']) for x in build_data['raw_build_times']]
  full_build_times_y = [x.get('full_build_duration_s', 0) for x in build_data['raw_build_times']]

  fig, ax = matplotlib.pyplot.subplots()
  ax.plot_date(full_build_times_x, full_build_times_y, linestyle='solid', color='#17517e')
  ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M"))
  ax.autoscale_view()
  ax.set_title('Full Build Times')
  ax.set_ylabel('Time in Seconds')
  ax.grid(True)
  fig.autofmt_xdate()
  fig.savefig('full_build_times.png')



  delta_build_times_x = [datetime.datetime.fromtimestamp(x['utc_epoch_seconds']) for x in build_data['raw_build_times']]
  delta_build_times_y = [x.get('delta_build_duration_s', 0) for x in build_data['raw_build_times']]

  fig, ax = matplotlib.pyplot.subplots()
  ax.plot_date(delta_build_times_x, delta_build_times_y, linestyle='solid', color='#17517e')
  ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M"))
  ax.autoscale_view()
  ax.set_title('Delta Build Times')
  ax.set_ylabel('Time in Seconds')
  ax.grid(True)
  fig.autofmt_xdate()
  fig.savefig('delta_build_times.png')


  build_size_x = [datetime.datetime.fromtimestamp(x['utc_epoch_seconds']) for x in build_data['build_size']]
  build_size_y_win64 = [x.get('win_64_size', 0) / (1024*1024) for x in build_data['build_size']]
  build_size_y_linux_x86_64 = [x.get('linux_x86_64_size', 0) / (1024*1024) for x in build_data['build_size']]
  build_size_y_linux_aarch64 = [x.get('linux_aarch64_size', 0) / (1024*1024) for x in build_data['build_size']]
  build_size_y_android = [x.get('android_size', 0) / (1024*1024) for x in build_data['build_size']]

  fig, ax = matplotlib.pyplot.subplots(sharey=True)
  ax.plot_date(build_size_x, build_size_y_win64, linestyle='solid', label='Windows x86_64', color='#17517e')
  ax.plot_date(build_size_x, build_size_y_linux_x86_64, linestyle='solid', label='Linux x86_64', color='#078451')
  ax.plot_date(build_size_x, build_size_y_linux_aarch64, linestyle='solid', label='Linux aarch64', color='#FAD5A5')
  ax.plot_date(build_size_x, build_size_y_android, linestyle='solid', label='Android 21+', color='#FF3D00')
  ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M"))
  ax.autoscale_view()
  ax.set_title('Build Sizes')
  ax.set_ylabel('Megabytes')
  ax.grid(True)
  fig.autofmt_xdate()
  fig.legend()
  fig.savefig('build_sizes.png')



  unit_tests_x = [datetime.datetime.fromtimestamp(x['utc_epoch_seconds']) for x in build_data['unit_tests']]
  unit_tests_y_total = [x.get('total', 0) for x in build_data['unit_tests']]
  unit_tests_y_passed = [x.get('passed', 0) for x in build_data['unit_tests']]
  unit_tests_y_failed = [x.get('failed', 0) for x in build_data['unit_tests']]

  fig, ax = matplotlib.pyplot.subplots(sharey=True)
  ax.plot_date(unit_tests_x, unit_tests_y_total, linestyle='solid', label='Total Tests', color='#17517e')
  ax.plot_date(unit_tests_x, unit_tests_y_passed, linestyle='solid', label='Passed', color='#078451')
  ax.plot_date(unit_tests_x, unit_tests_y_failed, linestyle='solid', label='Failed', color='#FF3D00')
  ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M"))
  ax.autoscale_view()
  ax.set_title('Unit Tests')
  ax.set_ylabel('Number of Tests')
  ax.grid(True)
  fig.autofmt_xdate()
  fig.legend()
  fig.savefig('unit_tests.png')


  features_x = [datetime.datetime.fromtimestamp(x['utc_epoch_seconds']) for x in build_data['features']]
  features_y_total = [x.get('total', 0) for x in build_data['features']]
  features_y_in_progress = [x.get('in_progress', 0) for x in build_data['features']]
  features_y_not_yet_started = [x.get('not_yet_started', 0) for x in build_data['features']]

  fig, ax = matplotlib.pyplot.subplots(sharey=True)
  ax.plot_date(features_x, features_y_total, linestyle='solid', label='Total Features', color='#17517e')
  ax.plot_date(features_x, features_y_in_progress, linestyle='solid', label='In Progress', color='#078451')
  ax.plot_date(features_x, features_y_not_yet_started, linestyle='solid', label='Not Yet Started', color='#FF3D00')
  ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d %H:%M"))
  ax.autoscale_view()
  ax.set_title('Features')
  ax.set_ylabel('Number of Features')
  ax.grid(True)
  fig.autofmt_xdate()
  fig.legend()
  fig.savefig('features.png')


# Returns the parent dir for all uploaded files
def push_distributables_to_cdn(repo_root, misc_measures):
  # Copy build assets to large storage CDN
  # TODO move from ADrive account owned by Jeffrey McAteer to business server someplace (just need ftp+nginx setup)
  win64_zip = j(repo_root, 'out', 'www', 'win64.zip')
  linux_x86_64_tar_gz = j(repo_root, 'out', 'www', 'linux_x86_64.tar.gz')
  linux_aarch64_tar_gz = j(repo_root, 'out', 'www', 'linux_aarch64.tar.gz')
  android_apk = j(repo_root, 'out', 'android', 'loci.apk')

  if not misc_measures['preview_mode']:
    if shutil.which('rsync') and shutil.which('sshpass'):

      for file in [win64_zip, linux_x86_64_tar_gz, linux_aarch64_tar_gz, android_apk]:
        subprocess.run([
          shutil.which('sshpass'),
          '-p', os.environ['CDN_PASS'],
          shutil.which('rsync'),
          '-e', 'ssh -o StrictHostKeyChecking=no',
          '--block-size={}'.format(32*1024),
          '--progress',
          file,
          '{}@rsync.adrive.com:./www/'.format(os.environ['CDN_USER'])
        ], check=True)
        print('Done {}!'.format(os.path.basename(file)))

    else:
      print('Rsync+sshpass not found, falling back to FTP (much slower)...')
      ftp = ftplib.FTP_TLS('ftp.adrive.com', user=os.environ['CDN_USER'], passwd=os.environ['CDN_PASS'])
      ftp.set_pasv(True)
      # ftp.login(user=os.environ['CDN_USER'], passwd=os.environ['CDN_PASS'])
      ftp.cwd('www')

      def spinning_cursor():
        while True:
          for cursor in '|/-\\':
              yield cursor

      spinner = spinning_cursor()

      def progress_cb(block_written):
        nonlocal spinner
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write('\b')
        sys.stdout.flush()

      with open(win64_zip, 'rb') as fp:
        ftp.storbinary('STOR win64.zip', fp, callback=progress_cb)
      print('Done win64.zip!')
      with open(linux_x86_64_tar_gz, 'rb') as fp:
        ftp.storbinary('STOR linux_x86_64.tar.gz', fp, callback=progress_cb)
      print('Done linux_x86_64.tar.gz!')
      with open(linux_aarch64_tar_gz, 'rb') as fp:
        ftp.storbinary('STOR linux_aarch64.tar.gz', fp, callback=progress_cb)
      print('Done linux_aarch64.tar.gz!')
      with open(android_apk, 'rb') as fp:
        ftp.storbinary('STOR loci.apk', fp, callback=progress_cb)
      print('Done loci.apk!')

      ftp.quit()

  # Return the parent dir for all uploaded files
  return 'https://www.adrive.com/public/ENP5Cf/www'

def update_www_dir(repo_root, misc_measures):
  # Copy assets built by btool's build_www task
  shutil.copyfile(j(repo_root, 'misc-res', 'windows_icon.png'), 'windows_icon.png')
  shutil.copyfile(j(repo_root, 'misc-res', 'linux_icon.png'), 'linux_icon.png')
  shutil.copyfile(j(repo_root, 'misc-res', 'android_icon.png'), 'android_icon.png')
  shutil.copyfile(j(repo_root, 'misc-res', 'web_globe_icon.png'), 'web_globe_icon.png')
  shutil.copyfile(j(repo_root, 'misc-res', 'icon.png'), 'icon.png')
  
  storage_cdn_base_url = push_distributables_to_cdn(repo_root, misc_measures)
  

  if os.path.exists('api-docs'):
    shutil.rmtree('api-docs')
  shutil.copytree(j(repo_root, 'out', 'docs'), 'api-docs')

  if os.path.exists('noapp-www'):
    shutil.rmtree('noapp-www')
  shutil.copytree(j(repo_root, 'app-subprograms', 'server-webgui', 'www'), 'noapp-www')

  # Read some repo metadata
  master_commit = str(subprocess.check_output(['git', 'rev-parse', 'master']), 'utf-8').strip()
  
  publish_utc_epoch_seconds = time.mktime(time.gmtime())
  publish_ts = datetime.datetime.fromtimestamp(publish_utc_epoch_seconds).strftime('%Y-%m-%d %H:%M:%S')
  hostname = socket.gethostname()
  username = getpass.getuser()

  # Generate PKI graphs
  misc_measures['publish_utc_epoch_seconds'] = int(publish_utc_epoch_seconds)
  update_kpi_data(repo_root, misc_measures)
  gen_kpi_graphs(repo_root)

  # Finally write the main landing page
  with open('index.html', 'w') as fd:
    fd.write(('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Loci</title>
  <link rel="icon" type="image/png" href="icon.png"/>
  <style>
/* https://www.colourlovers.com/palette/118332/earth_tones */
html, body {
  background-color: #fefefe;
  color: #202020;
  width: 960px;
  min-width: 50vw;
  max-width: 100vw;
  line-height: 1.35;
}
p {
  text-indent: 2em;
  text-indent: 2em each-line;
}
a.dl {
  color: inherit;
  text-decoration: inherit;
  font-size: 1.74em;
  padding: 32pt 12pt;
  padding-left: 122pt;
  margin: 8pt 16pt;
  border: 8pt solid #4D4B17;
  background-color: #4D4B17;
  border-radius: 6pt;
  display: inline-block;
  background-repeat: no-repeat;
  background-position: left;
  background-size: contain;
  background-origin: padding-box;
  transition: transform .2s;
}
a.dl:hover {
  transform: scale(1.06);
}
a.win {
  background-image: url("windows_icon.png");
  background-color: #4687b0;
  border-color: #4687b0;
}
a.linux {
  background-image: url("linux_icon.png");
  background-color: #8D8B57;
  border-color: #8D8B57;
}
a.android {
  background-image: url("android_icon.png");
  background-color: #a2654F;
  border-color: #a2654F;
}
a.noapp {
  background-image: url("web_globe_icon.png");
  background-color: #ffa700;
  border-color: #ffa700;
}
img.kpi-chart {
  width: 300pt;
  padding: 0;
  display: inline-block;
}
img.kpi-chart:hover {
  transform: scale(1.06);
}
  </style>
</head>
<body>
  <h1>Loci</h1>
  <h2>About</h2>
  <p>
    Loci is a flexible low-overhead fault-tolerant high-throughput geospatial common operational picture (COP)
    client, server, and standalone utility. Loci may be run on commercial-grade PCs, phones, and enterprise-grade servers.
    An exact list of platforms tested appears below, alongside deployment documentation.
  </p>
  <p>
    All copies of Loci come with an unlimited 10-minute trial period with a 10-minute backoff timer. This means you can use the
    software at no cost for 10 minutes, after which it will stop and not continue until 10 minutes have elapsed.
    This was determined to strike a balance between the needs of our sales team (sales, demos) and the needs of our development team (testing, simple designs).
  </p>
  <p>
    // TODO add license sales contact info (also mentioned in deployment guides)
  </p>
  <p>
    Loci may also be extended in arbitrary ways; the most common is to add support for a new type of radio, which usually takes
    less than a week of development work followed by a week of testing.
    <a href="api-docs/index.html">Link to API Docs</a>.
  </p>
  <hr>
  <h2>Download</h2>
  <p style="text-indent: 0;">'''+f'''
    <a class="dl win" href="{storage_cdn_base_url}/win64.zip">Windows 64-bit</a><br>
    <a class="dl linux" href="{storage_cdn_base_url}/linux_x86_64.tar.gz">Linux x86 64-bit</a><br>
    <a class="dl linux" href="{storage_cdn_base_url}/linux_aarch64.tar.gz">Linux ARM 64-bit</a><br>
    <a class="dl android" href="{storage_cdn_base_url}/loci.apk">Android</a><br>
    <a class="dl noapp" href="noapp-www/index.html">Online Only</a><br>
    '''+'''
  </p>
  <hr>
  <h2>Deployment Guides</h2>
  <p>
    // TODO build asciidoc source from /guides/ into .pdf files and link output here
  </p>
  <hr>
  <h2>Key Performance Indicators</h2>
  <p>
    The colossal scope of this project necessitates constant rigour to avoid making the system
    unmaintainably complex. The following metrics are tracked with every build and may be used to
    ensure the system is not rotting, becoming incorrect, or otherwise accumulating debt at a pace the dev team cannot pay off.
    <br>
    <a href="full_build_times.png"><img class="kpi-chart" src="full_build_times.png"></a>
    <a href="delta_build_times.png"><img class="kpi-chart" src="delta_build_times.png"></a>
    <a href="build_sizes.png"><img class="kpi-chart" src="build_sizes.png"></a>
    <a href="unit_tests.png"><img class="kpi-chart" src="unit_tests.png"></a>
    <a href="features.png"><img class="kpi-chart" src="features.png"></a>
  </p>
  <hr>
  <p style="text-indent: 0;">
'''+f'Generated by change number <code>{master_commit}</code> at <code>{publish_ts} UTC</code> on <code>{hostname}</code> by <code>{username}</code>.'+'''
  </p>
</body>
''').strip())


def main(args=sys.argv):
  
  if not os.path.exists('readme.md'):
    raise Exception('Must be run from top of repository')

  preview_mode = 'PREVIEW' in os.environ and len(os.environ['PREVIEW']) > 0

  repo_root = os.path.abspath('.')

  full_build_start = time.time()
  btool.main(['nobrowser', 'force_code_rebuilds'])
  full_build_end = time.time()
  full_build_duration_s = full_build_end - full_build_start

  delta_build_start = time.time()
  btool.main(['nobrowser'])
  delta_build_end = time.time()
  delta_build_duration_s = delta_build_end - delta_build_start
  
  # tarpaulin likes to break, so we ~let~ skip it.
  os.environ['SKIP_TARPAULIN'] = 'y'
  os.environ['ALLOW_TESTS_TO_FAIL'] = 'y'
  remaining_tests_attempts = 2
  while remaining_tests_attempts > 0:
    try:
      tests.main(['nobrowser'])
      break
    except:
      traceback.print_exc()
      remaining_tests_attempts -= 1
      time.sleep(2)
      print('Retrying tests...')
      os.environ['SKIP_TARPAULIN'] = 'y'
  
  if remaining_tests_attempts < 1: # TODO be more strict about this!
    raise Exception('tests did not complete!')

  try:
    docs.main(['nobrowser'])
  except:
    traceback.print_exc()

  # Checkout "www" branch into temp dir
  www_branch_d = tempfile.mkdtemp(prefix='loci_www_')
  try:
    os.environ['GIT_DISCOVERY_ACROSS_FILESYSTEM'] = '1'
    # Attempt to prune previous "www" prunable directories
    for line in str(subprocess.check_output(['git', 'worktree', 'list']), 'utf-8').splitlines():
      if '[www]' in line and 'tmp' in line.lower():
        dead_worktree_path = line.split()[0]
        print('Removing dead worktree detected at {}'.format(dead_worktree_path))
        subprocess.run([
          'git', 'worktree', 'remove', '--force', dead_worktree_path,
        ])
        time.sleep(0.75)

    subprocess.run([
      'git', 'worktree', 'add', www_branch_d, 'www',
    ])
    os.chdir(www_branch_d)

    update_www_dir(repo_root, {
      'full_build_duration_s': full_build_duration_s,
      'delta_build_duration_s': delta_build_duration_s,
      'preview_mode': preview_mode,
    })

    if preview_mode:
      webbrowser.open(os.path.abspath('index.html'))
      input('Press enter to commit + cleanup...')

    # Alter current commit to include new changes
    subprocess.run(['git', 'add', '--all'], check=True)
    subprocess.run(['git', 'commit', '--amend', '--no-edit'], check=True)

    # Force override remote branch
    subprocess.run(['git', 'push', '-f'], check=True)

  except:
    traceback.print_exc()
  finally:
    os.chdir(repo_root)
    if not 'NO_RM' in os.environ:
      subprocess.run([
        'git', 'worktree', 'remove', www_branch_d,
      ])
      if os.path.exists(www_branch_d):
        shutil.rmtree(www_branch_d)
    else:
      print('NO_RM set, left files intact at {}'.format(www_branch_d))

  print('Done, see published site at https://jeffrey-p-mcateer.github.io/loci/')



if __name__ == '__main__':
  main()
