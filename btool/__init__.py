
# Loci primary build tool.
# This is responsible for abstracting all development needs
# and assembling outputs for windows/linux/android targets.

# Required 3rdparty packages:
# python3 -m pip install --user requests py7zr


import os
import sys
import subprocess
import inspect
import urllib.request
import tarfile
import shutil
import time
import io
import pathlib
import traceback
import webbrowser
import platform

# Internal libs
from btool.utils import *
from btool.tools import *
from btool.buildall import buildall

# See individual setup functions in btool.tools
def download_tools():
  if not e('build'):
    os.makedirs(j('build'))

  os.environ['LOCI_REPO_DIR'] = os.path.abspath('.')

  download_dotnetcore()
  download_rust()
  download_java8()
  download_gradle()
  download_android_sdk()
  # download_gdal() # TODO implement this so we can use tools like ogr2ogr in build stages

  set_env_from_dev_env_conf('dev-env.conf')

  # Finally print warnings for host tools we expect and have not yet
  # fully bootstraped above
  expected_bins = [
    'javac', 'cargo', 'git',
    'x86_64-w64-mingw32-windres',
    'aarch64-linux-android28-clang', 'aarch64-linux-gnu-gcc',
  ]
  for b in expected_bins:
    if not shutil.which(b):
      print('WARNING: btool expected to have tool {} available but this is not on the PATH!'.format(b))


def main(args=sys.argv):
  
  if not e('readme.md'):
    die('Must be run from loci root like "python -m btool [args]')
  
  download_tools()

  if 'shell' in args:
    if host_is_linux():
      subprocess.run(['bash'])
    elif host_is_win():
      subprocess.run(['cmd.exe'])
    return

  debug_build = 'debug' in args
  build_linux_x86_64 = True
  build_linux_aarch64 = True
  build_linux_arm32 = False # TODO forward state through buildall.py
  build_win64 = True
  build_android = True
  if 'hostonly' in args:
    build_linux_x86_64 = host_is_linux_x64()
    build_linux_aarch64 = host_is_linux_aarch64()
    build_win64 = host_is_win()
    build_android = False
    set_flag('hostonly')
  elif 'android' in args:
    build_linux_x86_64 = False
    build_linux_aarch64 = False
    build_win64 = False
    build_android = True
  
  if debug_build:
    set_flag('debug_build')
  if build_linux_x86_64:
    set_flag('build_linux_x86_64')
  if build_linux_aarch64:
    set_flag('build_linux_aarch64')
  if build_win64:
    set_flag('build_win64')
  if build_android:
    set_flag('build_android')

  if 'force_code_rebuilds' in args:
    set_flag('force_code_rebuilds')
  else:
    if flag_name('force_code_rebuilds') in os.environ:
      os.environ.pop(flag_name('force_code_rebuilds'))

  # Global environment variables all sub-programs may read
  os.environ['PKG_CONFIG_ALLOW_CROSS'] = '1'
  os.environ['GIT_HASH'] = str(subprocess.check_output(['git', 'rev-parse', 'HEAD']), 'utf-8').strip()
  os.environ['COMPILE_TIME_EPOCH_SECONDS'] = str(int(time.time()))

  # Begin building all sub-programs and assembling outputs into ./out/<platform>/

  build_start = time.time()
  
  buildall(args)

  build_end = time.time()
  duration_s = round(build_end - build_start, 2)
  print('')
  print('Total build time: {}s'.format(duration_s))
  print('Size of out/win64: {:,}mb'.format( int(directory_size(j('out', 'win64')) / (1000*1000) )) )
  print('Size of out/linux_x86_64: {:,}mb'.format( int(directory_size(j('out', 'linux_x86_64')) / (1000*1000) )) )
  print('Size of out/linux_aarch64: {:,}mb'.format( int(directory_size(j('out', 'linux_aarch64')) / (1000*1000) )) )

  kernel_desktop_exe = None
  if build_linux_x86_64 or build_win64:
    if host_is_linux():
      kernel_desktop_exe = j('out', 'linux_x86_64', 'loci')
    elif host_is_win():
      kernel_desktop_exe = j('out', 'win64', 'loci.exe')
    else:
      raise Exception('Unknown host type')

  # Now that all builds are done continue processing arguments
  if 'run' in args:

    if kernel_desktop_exe:
      print('Running {}'.format(kernel_desktop_exe))
      subprocess.run([ kernel_desktop_exe ])

    elif build_android:
      # Install + run on physical device using adb
      apk_file = j('app-kernel-android', 'build', 'outputs', 'apk', 'debug', 'loci-debug.apk')
      app_name = ''
      subprocess.run([ 'adb', 'install', '-r', apk_file ], check=True)
      subprocess.run([ 'adb', 'shell', 'am', 'start', '-n', 'com.loci/loci.MainActivity' ], check=True)
      # Attach to logs
      subprocess.run([ 'adb', 'logcat', apk_file ])

  elif 'cleanrun' in args:

    if kernel_desktop_exe:

      # See https://docs.rs/dirs/3.0.2/dirs/fn.data_dir.html
      app_data_dir = None
      if host_is_linux():
        if 'XDG_DATA_HOME' in os.environ:
          app_data_dir = j(os.environ['XDG_DATA_HOME'], 'loci')
        else:
          app_data_dir = j(os.environ['HOME'], '.local', 'share', 'loci')

      elif host_is_win():
        app_data_dir = j(os.environ['AppData'], 'loci')

      print('Clearing app data files in {}'.format(app_data_dir))
      
      if os.path.exists(app_data_dir):
        shutil.rmtree(app_data_dir, ignore_errors=True)


      print('Running {}'.format(kernel_desktop_exe))
      subprocess.run([ kernel_desktop_exe ])

    elif build_android:
      raise Exception('Unknown way to perform "cleanrun" on android!')


