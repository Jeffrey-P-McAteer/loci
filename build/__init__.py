#!/usr/bin/env python3

import os, sys, subprocess
import socket, shutil
import time
import tempfile
import traceback
import random

# python3 -m pip install --user requests
import requests, zipfile, tarfile, bz2, lzma, gzip, io

# Used to extract 7zip for windows libusb
# python3 -m pip install --user py7zr
import py7zr

def windows_host():
  return os.name == 'nt'

def cargo_build(target):
  subprocess.run([
    'cargo', 'build', '--release', '--target={}'.format(target)
  ]).check_returncode()

def cmd(*parts):
  subprocess.run(list(parts)).check_returncode()

def within(directory, *callbacks):
  orig_cwd = os.getcwd()
  os.chdir(directory)
  for c in callbacks:
    c()
  os.chdir(orig_cwd)

def j(*path):
  return os.path.join(*list(path))

def e(*path):
  return os.path.exists(os.path.join(*list(path)))

def dl_archive_to(url, dst_path, extension=None):
  print('downloading {} to {}'.format(url, dst_path))

  if extension is None:
    if url.endswith('.zip') or url.endswith('.jar'):
      extension = '.zip'
    elif url.endswith('.tar.bz2'):
      extension = '.tar.bz2'
    elif url.endswith('.tar.xz'):
      extension = '.tar.xz'
    elif url.endswith('.txz'):
      extension = '.tar.xz'
    elif url.endswith('.7z'):
      extension = '.7z'
    else:
      extension = url
  
  if extension.endswith('.zip'):
    if os.path.exists(url):
      with open(url, 'rb') as zip_content:
        zip_mem = zipfile.ZipFile(io.BytesIO(zip_content))
        if not os.path.exists(dst_path):
          os.makedirs(dst_path)
        print('extracting to {}'.format(dst_path))
        zip_mem.extractall(dst_path)

    else:
      zip_r = requests.get(url)
      zip_mem = zipfile.ZipFile(io.BytesIO(zip_r.content))
      if not os.path.exists(dst_path):
        os.makedirs(dst_path)
      print('extracting to {}'.format(dst_path))
      zip_mem.extractall(dst_path)

  elif extension.endswith('.tar.bz2'):
    if os.path.exists(url):
      with open(url, 'rb') as tar_bz2_content:
        tar_bz2_bytes = tar_bz2_content.read()
        tar_mem = tarfile.open(
          fileobj=io.BytesIO(bz2.decompress( tar_bz2_bytes ))
        )
        if not os.path.exists(dst_path):
          os.makedirs(dst_path)
        print('extracting to {}'.format(dst_path))
        tar_mem.extractall(dst_path)

    else:
      tar_bz2_r = requests.get(url)
      tar_mem = tarfile.open(
        fileobj=io.BytesIO(bz2.decompress( tar_bz2_r.content ))
      )
      if not os.path.exists(dst_path):
        os.makedirs(dst_path)
      print('extracting to {}'.format(dst_path))
      tar_mem.extractall(dst_path)

  elif extension.endswith('.tar.xz'):
    if os.path.exists(url):
      with open(url, 'rb') as tar_xz_content:
        tar_xz_bytes = tar_xz_content.read()
        tar_mem = tarfile.open(
          fileobj=io.BytesIO(lzma.decompress( tar_xz_bytes ))
        )
        if not os.path.exists(dst_path):
          os.makedirs(dst_path)
        print('extracting to {}'.format(dst_path))
        tar_mem.extractall(dst_path)

    else:
      tar_xz_r = requests.get(url)
      tar_mem = tarfile.open(
        fileobj=io.BytesIO(lzma.decompress( tar_xz_r.content ))
      )
      if not os.path.exists(dst_path):
        os.makedirs(dst_path)
      print('extracting to {}'.format(dst_path))
      tar_mem.extractall(dst_path)

  elif extension.endswith('.tar.gz'):
    if os.path.exists(url):
      with open(url, 'rb') as tar_gz_content:
        tar_gz_bytes = tar_gz_content.read()
        tar_mem = tarfile.open(
          fileobj=io.BytesIO(gzip.decompress( tar_gz_bytes ))
        )
        if not os.path.exists(dst_path):
          os.makedirs(dst_path)
        print('extracting to {}'.format(dst_path))
        tar_mem.extractall(dst_path)

    else:
      tar_gz_r = requests.get(url)
      tar_mem = tarfile.open(
        fileobj=io.BytesIO(gzip.decompress( tar_gz_r.content ))
      )
      if not os.path.exists(dst_path):
        os.makedirs(dst_path)
      print('extracting to {}'.format(dst_path))
      tar_mem.extractall(dst_path)

  elif extension.endswith('.7z'):
    if os.path.exists(url):
      with py7zr.SevenZipFile(url, mode='r') as archive:
        print('extracting to {}'.format(dst_path))
        archive.extractall(path=dst_path)

    else:
      tmp_f = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
      tmp_f.close()

      sevenZ_r = requests.get(url)
      
      with open(tmp_f.name, 'wb') as fd:
        fd.write(sevenZ_r.content)

      with py7zr.SevenZipFile(tmp_f.name, mode='r') as archive:
        print('extracting to {}'.format(dst_path))
        archive.extractall(path=dst_path)

      os.unlink(tmp_f.name)

  else:
    raise Exception("Unknown archive type: {}".format(url))

  # We move files up until there is more than 1 item at the root (dst_path)
  # This avoids messy issues where we extract to "ABC/" and get
  # "ABC/ABC-1.2.3/<actual stuff we wanted under ABC>"
  remaining_loops = 5
  while len(os.listdir(dst_path)) < 2 and remaining_loops > 0:
    remaining_loops -= 1
    # Move everything in dst_path/<directory>/* into dst_path
    child_dir = os.path.join(dst_path, os.listdir(dst_path)[0])
    for child_f in os.listdir(child_dir):
      shutil.move(os.path.join(child_dir, child_f), os.path.join(dst_path, child_f))
    os.rmdir(child_dir)

def dl_archive2d_to(url, inner_archive_name, dst_path, extension=None):
  t_dir = tempfile.TemporaryDirectory()
  dl_archive_to(url, t_dir.name, extension=extension)
  
  # now grab t_dir+/+inner_archive_name and extract to dst_path
  inner_archive_path = os.path.join(t_dir.name, inner_archive_name)
  
  if not os.path.exists(inner_archive_path):
    raise Exception('File does not exist: inner_archive_path={}'.format(inner_archive_path))

  dl_archive_to(inner_archive_path, dst_path)


def cond_dl_archive_to(url, dst_path):
  if not e(dst_path) or len(os.listdir(dst_path)) < 2:
    dl_archive_to(url, dst_path)

def cond_dl_archive2d_to(url, inner_archive_name, dst_path, extension=None):
  if not e(dst_path) or len(os.listdir(dst_path)) < 2:
    dl_archive2d_to(url, inner_archive_name, dst_path, extension=extension)

def dl_f_to(url, dst_path):
  if not e(os.path.dirname(dst_path)):
    os.makedirs(os.path.dirname(dst_path))
  r = requests.get(url)
  with open(dst_path, 'wb') as fh:
    fh.write(r.content)

def cond_dl_f_to(url, dst_path):
  if not e(dst_path):
    dl_f_to(url, dst_path)


def tar_dir(source_dir):
  output_filename = source_dir+'.tar.gz'
  
  # Skip processing if output newer than source
  if os.path.exists(output_filename) and os.path.getmtime(output_filename) > os.path.getmtime(source_dir):
    return output_filename

  with tarfile.open(output_filename, 'w:gz') as tar:
    tar.add(source_dir, arcname='.')
  return output_filename


def clone_and_build_repo(url, dst_path, build_commands):
  print('Cloning {} to {}'.format(url, dst_path))
  subprocess.run([
    'git', 'clone', '--depth', '1', url, dst_path
  ], check=True, env=os.environ)
  for c in build_commands:
    if isinstance(c, list):
      #print('Executing {}, cwd={}, env={}'.format(' '.join(c), dst_path, os.environ))
      print('Executing {}, cwd={}'.format(' '.join(c), dst_path))
      subprocess.run(c, cwd=dst_path, check=True, env=os.environ)
    elif callable(c):
      c()
    else:
      raise Exception('Unknown call convention for build step: c={}'.format(c))

def cond_clone_and_build_repo(url, dst_path, build_commands):
  if not os.path.exists(dst_path):
    clone_and_build_repo(url, dst_path, build_commands)


def build_plugin(plugin_dir, build_cmds, output_file_or_dir, eapp_target_file_or_dir):
  def build_all():
    for c in build_cmds:
      subprocess.run(list(c), check=True)

  within(plugin_dir, build_all)

  if not os.path.exists(output_file_or_dir):
    raise Exception('Expected file to exist: {}'.format(output_file_or_dir))

  if os.path.isdir(output_file_or_dir):
    shutil.copytree(output_file_or_dir, eapp_target_file_or_dir)
  else:
    shutil.copy(output_file_or_dir, eapp_target_file_or_dir)


def cond_build_plugin(plugin_dir, build_cmds, output_file_or_dir, eapp_target_file_or_dir):
  if not os.path.exists(eapp_target_file_or_dir):
    build_plugin(plugin_dir, build_cmds, output_file_or_dir, eapp_target_file_or_dir)



def build_loci_eapp_dir_linux64():
  eapp_dir = os.path.abspath( j('target', 'eapp_dir_linux64') )
  if not e(eapp_dir):
    os.makedirs(eapp_dir)

  # See https://adoptopenjdk.net/releases.html?variant=openjdk15&jvmVariant=openj9
  cond_dl_archive_to(
    'https://github.com/AdoptOpenJDK/openjdk15-binaries/releases/download/jdk-15.0.1%2B9_openj9-0.23.0/OpenJDK15U-jre_x64_linux_openj9_15.0.1_9_openj9-0.23.0.tar.gz',
    j(eapp_dir, 'jre')
  )

  cond_dl_archive_to(
    'http://sourceforge.net/projects/geoserver/files/GeoServer/2.18.0/geoserver-2.18.0-bin.zip',
    j(eapp_dir, 'geoserver')
  )

  cond_dl_archive2d_to(
    'https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-linux-amd64/13.1.0/embedded-postgres-binaries-linux-amd64-13.1.0.jar',
    'postgres-linux-x86_64.txz',
    j(eapp_dir, 'postgres')
  )

  if not windows_host():
    import build.build_standalone_rtl_sdr_readers
    build_standalone_rtl_sdr_readers.build(eapp_dir)
  else:
    print('WARNING: Cannot cross-compile RTL-SDR programs for linux from a windows host.')
    time.sleep(1)

  # Python 3 is available on nearly every linux distro,
  # and python.org does not have an embedded zip build.
  
  cond_build_plugin(
    j('plugins', 'usb_gps_reader'),
    [
      ['cargo', 'build', '--release', '--target=x86_64-unknown-linux-gnu']
    ],
    j('plugins', 'usb_gps_reader', 'target', 'x86_64-unknown-linux-gnu', 'release', 'usb_gps_reader'),
    j(eapp_dir, 'usb_gps_reader')
  )


  return eapp_dir


def build_loci_eapp_dir_win64():
  eapp_dir = os.path.abspath( j('target', 'eapp_dir_win64') )
  if not e(eapp_dir):
    os.makedirs(eapp_dir)

  # See https://adoptopenjdk.net/releases.html?variant=openjdk15&jvmVariant=openj9
  cond_dl_archive_to(
    'https://github.com/AdoptOpenJDK/openjdk15-binaries/releases/download/jdk-15.0.1%2B9_openj9-0.23.0/OpenJDK15U-jre_x64_windows_openj9_15.0.1_9_openj9-0.23.0.zip',
    j(eapp_dir, 'jre')
  )

  cond_dl_archive_to(
    'http://sourceforge.net/projects/geoserver/files/GeoServer/2.18.0/geoserver-2.18.0-bin.zip',
    j(eapp_dir, 'geoserver')
  )

  cond_dl_archive2d_to(
    'https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-windows-amd64/13.1.0/embedded-postgres-binaries-windows-amd64-13.1.0.jar',
    'postgres-windows-x86_64.txz',
    j(eapp_dir, 'postgres'),
  )

  if windows_host():
    import build.build_standalone_rtl_sdr_readers
    build_standalone_rtl_sdr_readers.build(eapp_dir)
  else:
    print('WARNING: Cannot cross-compile RTL-SDR programs for windows from a linux host.')
    time.sleep(1)

  cond_dl_archive_to(
    'https://www.python.org/ftp/python/3.9.1/python-3.9.1-embed-amd64.zip',
    j(eapp_dir, 'python')
  )

  cond_build_plugin(
    j('plugins', 'usb_gps_reader'),
    [
      ['cargo', 'build', '--release', '--target=x86_64-pc-windows-gnu']
    ],
    j('plugins', 'usb_gps_reader', 'target', 'x86_64-pc-windows-gnu', 'release', 'usb_gps_reader.exe'),
    j(eapp_dir, 'usb_gps_reader.exe')
  )


  return eapp_dir





def download_3rdparty_webserver_www_assets():
  www_dir = j('src', 'webserver', 'www', '3rdparty')
  
  cond_dl_f_to(
    'https://raw.githubusercontent.com/shagstrom/split-pane/master/split-pane.js',
    j(www_dir, 'split-pane.js')
  )
  cond_dl_f_to(
    'https://raw.githubusercontent.com/shagstrom/split-pane/master/split-pane.css',
    j(www_dir, 'split-pane.css')
  )

  cond_dl_archive_to(
    'https://jqueryui.com/resources/download/jquery-ui-1.12.1.zip',
    j(www_dir, 'jquery-ui')
  )

  cond_dl_archive_to(
    'https://github.com/NASAWorldWind/WebWorldWind/releases/download/v0.10.0/WebWorldWind-Distribution-0.10.0.zip',
    j(www_dir, 'worldwind-web')
  )



def print_elapsed(start_s, msg):
  end_s = time.time()
  print(msg.format(
    s=round(end_s - start_s, 2)
  ))
  return end_s

def dir_size(path):
  total_bytes = 0
  for dirpath, dirnames, filenames in os.walk(path):
    for f in filenames:
      fp = os.path.join(dirpath, f)
      if not os.path.islink(fp):
        total_bytes += os.path.getsize(fp)
  return total_bytes


def main(argv=sys.argv):
  start_s = time.time()

  dependency_exes = [
    # C/C++ and common build programs
    'git', 'make', 'gcc', 'cmake',
    # Rust build programs
    'cargo', 'rustc',
    # Java and it's build programs
    'java', 'javac', 'gradle',

  ]
  for exe in dependency_exes:
    if not shutil.which(exe):
      print('Refusing to continue becuase dependency .exe is not on your PATH:')
      print('  Program required: {}'.format(exe))
      print('  your PATH: {}'.format(os.environ['PATH']))
      sys.exit(1)
      return

  # We assign some common env vars used in sub-processes
  os.environ['CMAKE_C_COMPILER'] = shutil.which('gcc')
  os.environ['CC'] = shutil.which('gcc')
  os.environ['CMAKE_GENERATOR'] = 'Unix Makefiles'


  # If the git repo is clean (no changes)
  # perform a pull to grab the latest changes.
  # This is a common op on testing devices.
  git_porcelain_stdout = subprocess.check_output(['git', 'status', '--porcelain'])
  if len(git_porcelain_stdout) < 5:
    # We're clean, do a pull!
    # if this fails that's fine too.
    print('Pulling latest code because this repo is clean...')
    #subprocess.run(['git', 'pull'], check=False)
    subprocess.run(['git', 'fetch', '--all'], check=False)
    subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=False)


  download_3rdparty_webserver_www_assets();
  start_s = print_elapsed(start_s, 'Downloaded 3rdparty assets in {s}s')

  # Parse pre-commands
  if 'hard-rebuild' in argv:
    os.environ['LOCI_HARD_REBUILD'] = hex(random.randint(0, 10000000))


  # Parse primary command

  if 'run' in argv:
    if windows_host():
      os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_win64();
    else:
      os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_linux64();
    os.environ['LOCI_EAPP_TAR'] = tar_dir(os.environ['LOCI_EAPP_DIR'])
    start_s = print_elapsed(start_s, 'Built eapp run directory in {s}s')

    subprocess.run([
      'cargo', 'run', '--release'
    ]).check_returncode()

  elif 'run-debug' in argv:
    if windows_host():
      os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_win64();
    else:
      os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_linux64();
    os.environ['LOCI_EAPP_TAR'] = tar_dir(os.environ['LOCI_EAPP_DIR'])
    start_s = print_elapsed(start_s, 'Built eapp run directory in {s}s')
      
    subprocess.run([
      'cargo', 'run'
    ]).check_returncode()

  elif 'release' in argv:
    if windows_host():
      os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_win64();
    else:
      os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_linux64();
    os.environ['LOCI_EAPP_TAR'] = tar_dir(os.environ['LOCI_EAPP_DIR'])
    start_s = print_elapsed(start_s, 'Built eapp release directory in {s}s')

    subprocess.run([
      'cargo', 'build', '--release'
    ]).check_returncode()

  else:
    if not windows_host():
      os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_linux64();
      os.environ['LOCI_EAPP_TAR'] = tar_dir(os.environ['LOCI_EAPP_DIR'])
      start_s = print_elapsed(start_s, 'Built linux eapp directory in {s}s')
      print('linux64 eapp directory size: {:,}mb'.format( round(dir_size(os.environ['LOCI_EAPP_DIR'])/(1000.0*1000.0), 2) ))
      cargo_build('x86_64-unknown-linux-gnu');
      start_s = print_elapsed(start_s, 'Built linux in {s}s')

    if not windows_host():
      # Throw out some problematic environment vars for cross-compile setups
      os.environ.pop('CMAKE_C_COMPILER')
      os.environ.pop('CC')

    # On windows this is the only target run,
    # on *nix machines you must have a cross-compile tool available
    os.environ['LOCI_EAPP_DIR'] = build_loci_eapp_dir_win64();
    os.environ['LOCI_EAPP_TAR'] = tar_dir(os.environ['LOCI_EAPP_DIR'])
    start_s = print_elapsed(start_s, 'Built windows eapp directory in {s}s')
    cargo_build('x86_64-pc-windows-gnu');
    start_s = print_elapsed(start_s, 'Built windows in {s}s')

    # post-build metadata + tasks
    print('Source code: {}kb'.format( round(dir_size('src')/1000.0, 2) ))
    print('win64 eapp directory size: {:,}mb'.format( round(dir_size(os.environ['LOCI_EAPP_DIR'])/(1000.0*1000.0), 2) ))

    if 'azure-angel' in socket.gethostname():
      shutil.copy('target/x86_64-pc-windows-gnu/release/loci.exe', '/j/www/')


if __name__ == '__main__':
  main()

