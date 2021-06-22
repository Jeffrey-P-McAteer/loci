
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
import threading
import tempfile
import re
import glob
import platform

# python3 -m pip install --user requests
import requests, zipfile, tarfile, bz2, lzma, gzip, io

# Used to extract 7zip for windows libusb
# python3 -m pip install --user py7zr
import py7zr

# python3 -m pip install --user Pillow
from PIL import Image

def flag_name(name):
  return '_BUILD_FLAG_{}'.format(name)

def set_flag(name):
  os.environ[flag_name(name)] = '1'

def flag_set(name):
  return flag_name(name) in os.environ and len(os.environ[flag_name(name)]) > 0


def c(*cmd, check=True, cwd=None):
  c_proc = subprocess.Popen(
    list(cmd),
    cwd=cwd,
    bufsize=0,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )
  
  def fwd_stream(proc, src_stream, dst_stream):
    buff = []
    while proc.poll() is None:
      buff = src_stream.read(16)
      dst_stream.write(str(buff, 'utf-8'))

  # Spawn 2 threads to forward stderr + stdout
  t1 = threading.Thread(target=fwd_stream, args=(c_proc, c_proc.stdout, sys.stdout, ))
  t1.start()
  t2 = threading.Thread(target=fwd_stream, args=(c_proc, c_proc.stderr, sys.stderr, ))
  t2.start()

  # While process is executing or there is buffer to print
  while c_proc.poll() is None:
    time.sleep(0.2)

  if check:
    code = c_proc.poll()
    if code != 0:
      raise Exception("Process exited with code {}".format(code))

def j(*parts):
  return os.path.join(*list(parts))

def e(*parts):
  return os.path.exists(j(*parts))

def die(msg):
  caller = inspect.getframeinfo(inspect.stack()[1][0])
  print("{}:{} {}".format(caller.filename, caller.lineno, msg))
  sys.exit(1)

def host_is_win():
  return os.name == 'nt'

def host_is_linux():
  return not host_is_win()

def host_is_linux_x64():
  uname = str(platform.uname()).lower()
  return host_is_linux() and ('x86_64' in uname)

def host_is_linux_arm32():
  uname = str(platform.uname()).lower()
  return host_is_linux() and ('armv7' in uname or 'armv6' in uname)

def host_is_linux_aarch64():
  uname = str(platform.uname()).lower()
  return host_is_linux() and ('aarch64' in uname or 'armv8' in uname)


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


def dl_archive_to_once(url, dst_path, extension=None, and_then_with_dir=None):
  if os.path.exists(dst_path):
    return

  dl_archive_to(url, dst_path, extension=extension)

  if and_then_with_dir:
    if isinstance(and_then_with_dir, list):
      for and_then in and_then_with_dir:
        and_then(dst_path)
    else:
      and_then_with_dir(dst_path)


def remove_files_by_glob(glob_pattern):
  for file in glob.glob(glob_pattern, recursive=True):
    os.remove(file)


def within(cwd, *cmds):
  orig_cwd = os.getcwd()
  os.chdir(cwd)
  error = None
  for c in cmds:
    if c:
      try:
        c()
      except Exception as e:
        traceback.print_exc()
        error = e
        break
  os.chdir(orig_cwd)
  if error:
    raise error

# Accepts list of paths, directory path, and single file path.
# returns mtime for newest file in entire collection.
def get_newest_file_mtime(directory):
  if isinstance(directory, list):
    newest_mtime_s = 0
    for d in directory:
      d_mtime_s = get_newest_file_mtime(d)
      if d_mtime_s != 0 and d_mtime_s > newest_mtime_s:
        newest_mtime_s = d_mtime_s
    return newest_mtime_s

  if not os.path.exists(directory):
    return 0

  elif not os.path.isdir(directory):
    return os.path.getmtime(directory)

  else:
    newest_mtime_s = 0
    for subdir, dirs, files in os.walk(directory):
      for file in files:
        file = os.path.join(subdir, file)
        file_mtime_s = os.path.getmtime(file)
        if file_mtime_s > newest_mtime_s:
          newest_mtime_s = file_mtime_s
    return newest_mtime_s

def silenced_task(task_name, input_files, output_files, *cmds):
  print('{} '.format(task_name), end='', flush=True)
  # Skip task if build files newer than source files
  if get_newest_file_mtime(output_files) > get_newest_file_mtime(input_files):
    print('SKIPPED (output newer than input)')
    return
  
  orig_stdout = sys.stdout
  orig_stderr = sys.stderr
  new_stdout = io.StringIO()
  new_stderr = io.StringIO()
  sys.stdout = new_stdout
  if not flag_set('debug_build'):
    sys.stderr = new_stderr

  start = time.time()
  error = False
  for c in cmds:
    if c:
      try:
        c()
      except Exception as e:
        traceback.print_exc()
        error = True
        break

  end = time.time()
  duration_s = round(end - start, 2)

  sys.stdout = orig_stdout
  sys.stderr = orig_stderr

  if flag_set('debug_build') or error:
    print('')
    print(new_stdout.getvalue())
    print(new_stderr.getvalue())

  print('{}s'.format(duration_s))

  if error:
    raise Exception('unhandled error={}'.format(error))

def noisy_task(task_name, input_files, output_files, *cmds):
  print('{} '.format(task_name), end='', flush=True)
  # Skip task if build files newer than source files
  if get_newest_file_mtime(output_files) > get_newest_file_mtime(input_files):
    print('SKIPPED (output newer than input)')
    return
  
  start = time.time()
  error = False
  for c in cmds:
    if c:
      try:
        c()
      except Exception as e:
        traceback.print_exc()
        error = True
        break

  end = time.time()
  duration_s = round(end - start, 2)

  print('{}s'.format(duration_s))

  if error:
    raise Exception('unhandled error={}'.format(error))

def dl_once(url, file):
  directory = os.path.dirname(file)
  if not os.path.exists(directory):
    os.makedirs(directory)

  if not os.path.exists(file) or os.path.getsize(file) < 10:
    print('Downloading {} to {}'.format(url, file))
    urllib.request.urlretrieve(url, file)

def cp(src_f, dst_f):
  if not os.path.exists(dst_f) or os.path.getmtime(src_f) > os.path.getmtime(dst_f):
    print('Copying {} to {}'.format(src_f, dst_f))
    shutil.copy(src_f, dst_f)

# Abstraction letting us avoid re-writing different assemble_in_* functions
# by creating the implementation given assemble_dir
def assemble_in_curried(assemble_dir):
  
  def curried(src_file_or_dir, target_name):
    if not os.path.exists(assemble_dir):
      os.makedirs(assemble_dir)
    
    if os.path.isdir(src_file_or_dir):
      target_dir = j(assemble_dir, target_name)
      if not os.path.exists(os.path.dirname(target_dir)) and len(os.path.dirname(target_dir)) > 1:
        os.makedirs(os.path.dirname(target_dir))
      shutil.copytree(src_file_or_dir, target_dir, dirs_exist_ok=True)

    else:
      target_file = j(assemble_dir, target_name)
      if not os.path.exists(os.path.dirname(target_file)) and len(os.path.dirname(target_file)) > 1:
        os.makedirs(os.path.dirname(target_file))
      shutil.copy(src_file_or_dir, target_file)

  return curried


def assemble_in_linux_x86_64(src_file_or_dir, target_name):
  if not flag_set('build_linux_x86_64'):
    return
  assemble_in_curried(j('out', 'linux_x86_64'))(src_file_or_dir, target_name)

def assemble_in_linux_aarch64(src_file_or_dir, target_name):
  if not flag_set('build_linux_aarch64'):
    return
  assemble_in_curried(j('out', 'linux_aarch64'))(src_file_or_dir, target_name)

def assemble_in_win64(src_file_or_dir, target_name):
  if not flag_set('build_win64'):
    return
  assemble_in_curried(j('out', 'win64'))(src_file_or_dir, target_name)

def assemble_in_android(src_file_or_dir, target_name):
  if not flag_set('build_android'):
    return
  assemble_in_curried(j('out', 'android'))(src_file_or_dir, target_name)

def assemble_in_www(src_file_or_dir, target_name):
  assemble_in_curried(j('out', 'www'))(src_file_or_dir, target_name)


def inputs(*items):
  return list(items)

def outputs(*items):
  return list(items)

def silent_rm(file):
  if os.path.exists(file):
    os.remove(file)


def directory_size(directory):
  if not os.path.isdir(directory):
    return os.path.getsize(directory)
  else:
    return sum(directory_size(d) for d in os.scandir(directory))


def set_env_from_dev_env_conf(dev_env_conf_file):
  if not os.path.exists(dev_env_conf_file):
    print('WARNING: {} not found, some build stages will be impossible to perform.'.format(dev_env_conf_file))
    print('See readme.md for details on dev-env.conf variables and their purposes.')
    return

  envre = re.compile(r'''^([^\s=]+)=(?:[\s"']*)(.+?)(?:[\s"']*)$''')
  new_vars = {}
  with open(dev_env_conf_file, 'r') as fd:
    for line in fd:
      if line.startswith('#'):
        continue
      match = envre.match(line)
      # we must have a match and (2) needs to be at least 1 character long
      if match is not None and len(match.group(2)) > 0:
        new_vars[match.group(1)] = match.group(2)

  # append new_vars to os.environ
  os.environ.update(new_vars)

def scale_image_once(src_img, dst_img, new_size_wh):
  if e(dst_img):
    return

  if not e(os.path.dirname(dst_img)):
    os.makedirs(os.path.dirname(dst_img))

  im = Image.open(src_img)
  im_r = im.resize(new_size_wh, Image.ANTIALIAS)
  out_format = 'JPEG'
  if dst_img.lower().endswith('png'):
    out_format = 'PNG'
  im_r.save(dst_img, out_format)




