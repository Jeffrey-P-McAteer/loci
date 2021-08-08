
# todo: add jdk/python/etc for aarch64 hosts used by developers, large task.

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
import tempfile

# Internal libs
from btool.utils import *

def download_dotnetcore():
  downloaded = False

  if host_is_linux():
    linux_dotnet_dir = j('build', 'linux-dotnet')
    if not e(j(linux_dotnet_dir, 'dotnet')):
      dl_archive_to(
        # From https://dotnet.microsoft.com/download/dotnet/
        'https://download.visualstudio.microsoft.com/download/pr/ef13f9da-46dc-4de9-a05e-5a4c20574189/be95913ebf1fb6c66833ca40060d3f65/dotnet-sdk-5.0.203-linux-x64.tar.gz',
        linux_dotnet_dir
      )
      downloaded = True
    os.environ['PATH'] = os.path.abspath(linux_dotnet_dir)+os.pathsep+os.environ['PATH']

  elif host_is_win():
    win_dotnet_dir = j('build', 'win-dotnet')
    if not e(j(win_dotnet_dir, 'dotnet.exe')):
      dl_archive_to(
        'https://download.visualstudio.microsoft.com/download/pr/fbb03203-c7d4-4958-9432-5b4e2a1ed342/1c4585ac5d74ae5d219b8c87129cfbb8/dotnet-sdk-5.0.300-win-x64.zip',
        win_dotnet_dir
      )
      downloaded = True
    os.environ['PATH'] = os.path.abspath(win_dotnet_dir)+os.pathsep+os.environ['PATH']

  # Now that we have .net core, perform one-time setup routines
  if downloaded:
    # For ./app-subprograms/desktop-mainwindow/
    # This lets us run "dotnet new photinoapp"
    c('dotnet', 'new', '-i', 'TryPhotino.VSCode.Project.Templates')

  if not shutil.which('dotnet'):
    die('download_dotnetcore failed to add program "dotnet" to PATH')

def download_rust():
  downloaded = False
  # from https://forge.rust-lang.org/infra/other-installation-methods.html#standalone-installers
  if host_is_linux():
    linux_rust_dir = j('build', 'linux-rust')
    os.environ['CARGO_HOME'] = linux_rust_dir
    os.environ['RUSTUP_HOME'] = linux_rust_dir
    
    if not e(j(linux_rust_dir, 'bin', 'cargo')):
      if not shutil.which('curl'):
        die('You need "curl" installed and added to your PATH to download the rust SDK')
      
      c('sh', '-c', 'curl https://sh.rustup.rs -sSf | sh -s -- -y --no-modify-path --profile default --default-host x86_64-unknown-linux-gnu --default-toolchain stable-x86_64-unknown-linux-gnu')
      downloaded = True

    # Add "bin" dirs to path, but SKIP any which do not have our arch in their full path.
    desired_arch = 'x86_64'
    if host_is_linux_aarch64():
      desired_arch = 'aarch64'

    os.environ['PATH'] = os.path.abspath(os.path.join(linux_rust_dir, 'bin'))+os.pathsep+os.environ['PATH']

    for dirname in pathlib.Path(linux_rust_dir).rglob('bin'):
      dirname = os.path.abspath(dirname)
      if not desired_arch in dirname:
        continue
      os.environ['PATH'] = dirname+os.pathsep+os.environ['PATH']

  elif host_is_win():
    win_rust_dir = j('build', 'win-rust')
    os.environ['CARGO_HOME'] = win_rust_dir
    os.environ['RUSTUP_HOME'] = win_rust_dir

    if not e(j(win_rust_dir, 'bin', 'cargo.exe')):
      rustup_bin = j(tempfile.gettempdir(), 'rustup-init.exe')
      dl_once('https://win.rustup.rs/x86_64', rustup_bin)
      c(rustup_bin, '-y', '--no-modify-path', '--profile', 'default', '--default-host', 'x86_64-pc-windows-gnu', '--default-toolchain', 'stable-x86_64-pc-windows-gnu')
      downloaded = True

    desired_arch = 'x86_64'

    os.environ['PATH'] = os.path.abspath(os.path.join(win_rust_dir, 'bin'))+os.pathsep+os.environ['PATH']

    for dirname in pathlib.Path(win_rust_dir).rglob('bin'):
      os.environ['PATH'] = os.path.abspath(dirname)+os.pathsep+os.environ['PATH']

    # Windows also needs some link.exe, we use public binaries for this
    # See https://winlibs.com/
    win_mingw_dir = j('build', 'win-base-devel-bins')
    if not e(j(win_mingw_dir, 'bin', 'gcc.exe')):
      dl_archive_to(
        'https://github.com/brechtsanders/winlibs_mingw/releases/download/11.1.0-12.0.0-9.0.0-r1/winlibs-x86_64-posix-seh-gcc-11.1.0-llvm-12.0.0-mingw-w64-9.0.0-r1.zip',
        win_mingw_dir,
      )

    for dirname in pathlib.Path(win_mingw_dir).rglob('bin'):
      dirname = os.path.abspath(dirname)
      if not desired_arch in dirname:
        continue
      os.environ['PATH'] = dirname+os.pathsep+os.environ['PATH']

    # We know we have gcc.exe, assign env hint to use it for all build tools
    os.environ['CC'] = shutil.which('gcc')

  if not shutil.which('cargo'):
    die('download_rust failed to add program "cargo" to PATH')

  os.environ['CARGO_HOME'] = os.path.abspath(os.environ['CARGO_HOME'])
  os.environ['RUSTUP_HOME'] = os.path.abspath(os.environ['RUSTUP_HOME'])

  # d/l related targets etc. which we use
  if downloaded:
    c('rustup', 'target', 'add', 'x86_64-pc-windows-gnu')
    c('rustup', 'target', 'add', 'x86_64-unknown-linux-gnu')
    c('rustup', 'target', 'add', 'aarch64-unknown-linux-gnu')
    
    c('rustup', 'toolchain', 'install', 'stable-x86_64-pc-windows-gnu')
    c('rustup', 'toolchain', 'install', 'stable-x86_64-unknown-linux-gnu')
    c('rustup', 'toolchain', 'install', 'stable-aarch64-unknown-linux-gnu')
    
    host_stable_toolchain = 'stable-x86_64-pc-windows-gnu' if host_is_win() else 'stable-x86_64-unknown-linux-gnu' if host_is_linux_x64() else 'stable-aarch64-unknown-linux-gnu'
    host_nightly_toolchain = 'nightly-x86_64-pc-windows-gnu' if host_is_win() else 'nightly-x86_64-unknown-linux-gnu' if host_is_linux_x64() else 'nightly-aarch64-unknown-linux-gnu'

    c('rustup', 'default', host_stable_toolchain)

    # Nightly compilers are required for android build
    c('rustup', 'toolchain', 'install', 'nightly-x86_64-pc-windows-gnu')
    c('rustup', 'toolchain', 'install', 'nightly-x86_64-unknown-linux-gnu')
    c('rustup', 'toolchain', 'install', 'nightly-aarch64-unknown-linux-gnu')
    
    c('rustup', 'default', host_stable_toolchain)

    # rust-src is necessary to compile std lib when building android using nightly tools
    c('rustup', 'target', 'add', 'aarch64-linux-android', '--toolchain', host_nightly_toolchain)
    # Used to compile std lib when building android using nightly tools
    c('rustup', 'component', 'add', 'rust-src', '--toolchain', host_stable_toolchain)
    c('rustup', 'component', 'add', 'rust-src', '--toolchain', host_nightly_toolchain)
    c('rustup', 'component', 'add', 'rust-src', '--target', 'aarch64-linux-android', '--toolchain', host_nightly_toolchain)

    if host_is_linux():
      # tarpaulin is only supported on x86_64 linux at the moment
      c('cargo', 'install', 'cargo-tarpaulin')

def download_java8():
  # From https://adoptopenjdk.net/releases.html?variant=openjdk8&jvmVariant=hotspot
  if host_is_linux():
    linux_java8_dir = j('build', 'linux-java8')

    if not e(j(linux_java8_dir, 'bin', 'java')):
      dl_archive_to(
        'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u292-b10/OpenJDK8U-jdk_x64_linux_hotspot_8u292b10.tar.gz',
        linux_java8_dir
      )
      # Ensure all bins are executable
      c('find', j(linux_java8_dir, 'bin'), '-type', 'f', '-exec', 'chmod', '+x', '{}', ';')
      
    os.environ['PATH'] = os.path.abspath(j(linux_java8_dir, 'bin'))+os.pathsep+os.environ['PATH']
    os.environ['JAVA_HOME'] = os.path.abspath(linux_java8_dir)

  elif host_is_win():
    win_java8_dir = j('build', 'win-java8')
    
    if not e(j(win_java8_dir, 'bin', 'java.exe')):
      dl_archive_to(
        'https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u292-b10/OpenJDK8U-jdk_x64_windows_hotspot_8u292b10.zip',
        win_java8_dir
      )
      
    os.environ['PATH'] = os.path.abspath(j(win_java8_dir, 'bin'))+os.pathsep+os.environ['PATH']
    os.environ['JAVA_HOME'] = os.path.abspath(win_java8_dir)


def download_gradle():
  # From https://gradle.org/install/
  if host_is_linux():
    linux_gradle_dir = j('build', 'linux-gradle')

    if not e(j(linux_gradle_dir, 'bin', 'gradle')):
      dl_archive_to(
        'https://services.gradle.org/distributions/gradle-7.0.2-bin.zip',
        linux_gradle_dir
      )
      # Ensure all bins are executable
      c('find', j(linux_gradle_dir, 'bin'), '-type', 'f', '-exec', 'chmod', '+x', '{}', ';')
      
    os.environ['PATH'] = os.path.abspath(j(linux_gradle_dir, 'bin'))+os.pathsep+os.environ['PATH']

  elif host_is_win():
    win_gradle_dir = j('build', 'win-gradle')
    if not e(j(win_gradle_dir, 'bin', 'gradle.bat')):
      dl_archive_to(
        'https://services.gradle.org/distributions/gradle-7.0.2-bin.zip',
        win_gradle_dir
      )
      
    os.environ['PATH'] = os.path.abspath(j(win_gradle_dir, 'bin'))+os.pathsep+os.environ['PATH']

def download_android_sdk():
  downloaded = False
  sdk_root = None
  # From https://developer.android.com/studio#command-tools
  if host_is_linux():
    linux_android_dir = j('build', 'linux-android')
    sdk_root = os.path.abspath(linux_android_dir)

    if not e(j(linux_android_dir, 'bin', 'sdkmanager')):
      dl_archive_to(
        'https://dl.google.com/android/repository/commandlinetools-linux-7302050_latest.zip',
        linux_android_dir
      )
      # Ensure all bins are executable
      c('find', j(linux_android_dir, 'bin'), '-type', 'f', '-exec', 'chmod', '+x', '{}', ';')
      downloaded = True

    os.environ['PATH'] = os.path.abspath(j(linux_android_dir, 'bin'))+os.pathsep+os.environ['PATH']
    os.environ['PATH'] = os.path.abspath(j(linux_android_dir, 'tools'))+os.pathsep+os.environ['PATH']
    os.environ['ANDROID_SDK_ROOT'] = os.path.abspath(linux_android_dir)

  elif host_is_win():
    win_android_dir = j('build', 'win-android')
    sdk_root = os.path.abspath(win_android_dir)

    if not e(j(win_android_dir, 'bin', 'sdkmanager.bat')):
      dl_archive_to(
        'https://dl.google.com/android/repository/commandlinetools-win-7302050_latest.zip',
        win_android_dir
      )
      downloaded = True

    os.environ['PATH'] = os.path.abspath(j(win_android_dir, 'bin'))+os.pathsep+os.environ['PATH']
    os.environ['PATH'] = os.path.abspath(j(win_android_dir, 'tools'))+os.pathsep+os.environ['PATH']
    os.environ['ANDROID_SDK_ROOT'] = os.path.abspath(win_android_dir)

  # Accept licenses and install remaining SDK tools
  if downloaded:
    accept_stdin = b'y\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\ny\n'
    if host_is_win():
      accept_stdin = b'y\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\ny\r\n'
    subprocess.run([shutil.which('sdkmanager'), '--sdk_root={}'.format(sdk_root),
      '--licenses'
    ],check=True, input=accept_stdin)
    subprocess.run([shutil.which('sdkmanager'), '--sdk_root={}'.format(sdk_root),
      'emulator', 'platform-tools', 'platforms;android-29', 'platforms;android-28', 'platforms;android-27',
    ],check=True)
    subprocess.run([shutil.which('sdkmanager'), '--sdk_root={}'.format(sdk_root),
      'ndk-bundle',
    ],check=True)

  # Finally add additional tools to PATH
  if host_is_linux():
    os.environ['PATH'] = os.path.abspath(j(linux_android_dir, 'platform-tools'))+os.pathsep+os.environ['PATH']
    os.environ['PATH'] = os.path.abspath(j(linux_android_dir, 'emulator'))+os.pathsep+os.environ['PATH']
    os.environ['PATH'] = os.environ['PATH']+os.pathsep+os.path.abspath(j(os.environ['ANDROID_SDK_ROOT'], 'ndk-bundle', 'toolchains', 'llvm', 'prebuilt', 'linux-x86_64', 'bin'))
    
  elif host_is_win():
    os.environ['PATH'] = os.path.abspath(j(win_android_dir, 'platform-tools'))+os.pathsep+os.environ['PATH']
    os.environ['PATH'] = os.path.abspath(j(win_android_dir, 'emulator'))+os.pathsep+os.environ['PATH']

def run_within_cargo_android_arm64_ndk_env(cmd):
  env_vars_changed = [
    'PATH', 'CC', 'TARGET', 'TARGET_CC',
  ]
  orig_env = {}
  for var in env_vars_changed:
    if var in os.environ:
      orig_env[var] = os.environ[var]

  if host_is_linux():
    bin_dir = j(os.environ['ANDROID_SDK_ROOT'], 'ndk-bundle', 'toolchains', 'llvm', 'prebuilt', 'linux-x86_64', 'bin')
    if not os.path.exists(bin_dir):
      die('Expected dir to exist: {}'.format(bin_dir))
    os.environ['PATH'] = os.path.abspath(bin_dir)+os.pathsep+os.environ['PATH']

  elif host_is_win():
    die('TODO find a prebuild NDK for windows targeting android-28 on aarch64.')

  # Misc env vars
  os.environ['TARGET'] = 'aarch64-linux-android28'
  #os.environ['RUSTFLAGS'] = '--sysroot={}'.format(sysroot)
  os.environ['TARGET_CC'] = 'aarch64-linux-android28-clang'

  # We expect cargo & co, so let's create a config file in each sub-program if it does not exist
  # to inform rustc which linkers to use:
  config_file = os.path.join(".cargo", "config.toml")
  if not os.path.exists(config_file):
    os.makedirs(".cargo", exist_ok=True)
    with open(config_file, 'w') as fd:
      fd.write("""
# Generated by tools.py under the assumption aarch64-linux-android will be built within
# env setup by android NDK and run_within_cargo_android_arm64_ndk_env()
[target.aarch64-linux-android]
linker = "aarch64-linux-android28-clang"
ar = "llvm-ar"

# Similar assumptions for cross-compiling to aarch64
[target.aarch64-unknown-linux-gnu]
linker = "aarch64-linux-gnu-gcc"
ar = "aarch64-linux-gnu-ar"
""")

  # Run the command
  # subprocess.run(['bash']) # Debugging build env
  cmd()

  # Remove env changes
  for var in env_vars_changed:
    if var in orig_env:
      os.environ[var] = orig_env[var]
    else:
      os.unsetenv(var)



def download_curl():
  downloaded = False
  # See https://curl.se/download.html

  if host_is_linux():
    linux_curl_dir = j('build', 'linux-curl')
    if not e(j(linux_curl_dir, 'bin', 'curl')):
      dl_archive_to(
        # From https://github.com/moparisthebest/static-curl/releases
        'https://github.com/moparisthebest/static-curl/releases/download/v7.77.0/curl-amd64',
        linux_curl_dir
      )
      downloaded = True
    os.environ['PATH'] = os.path.abspath(os.path.join(linux_curl_dir, 'bin'))+os.pathsep+os.environ['PATH']

  elif host_is_win():
    win_curl_dir = j('build', 'win-curl')
    if not e(j(win_curl_dir, 'bin', 'curl.exe')):
      dl_archive_to(
        'https://curl.se/windows/dl-7.77.0_2/curl-7.77.0_2-win64-mingw.zip',
        win_curl_dir
      )
      downloaded = True
    os.environ['PATH'] = os.path.abspath(os.path.join(win_curl_dir, 'bin'))+os.pathsep+os.environ['PATH']


  if not shutil.which('curl'):
    die('download_curl failed to add program "curl" to PATH')

# TODO build/download GDAL in a cross-platform way so we can write build tools to extract segments of OSM map data to ship as basemaps.
# def download_gdal():
#   if host_is_linux():
#     linux_gdal_dir = j('build', 'linux-gdal')
#     if not e(j(linux_gdal_dir, 'dotnet')):
#       # dl_archive_to(
#       #   'http://mirror.cs.pitt.edu/archlinux/community/os/x86_64/gdal-3.3.0-1-x86_64.pkg.tar.zst',
#       #   linux_gdal_dir
#       # )
#       downloaded = True
#     os.environ['PATH'] = os.path.abspath(os.path.join(linux_gdal_dir, 'bin'))+os.pathsep+os.environ['PATH']
# 
#   elif host_is_win():
#     win_gdal_dir = j('build', 'win-gdal')
#     if not e(j(win_gdal_dir, 'dotnet.exe')):
#       # dl_archive_to(
#       #   'https://curl.se/windows/dl-7.77.0_2/curl-7.77.0_2-win64-mingw.zip',
#       #   win_gdal_dir
#       # )
#       downloaded = True
#     os.environ['PATH'] = os.path.abspath(os.path.join(win_gdal_dir, 'bin'))+os.pathsep+os.environ['PATH']
# 
#   if not shutil.which('ogr2ogr'):
#     die('download_gdal failed to add program "ogr2ogr" to PATH')

