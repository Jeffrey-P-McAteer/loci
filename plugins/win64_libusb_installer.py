
# This python script automates zadig.exe to install winusb0 drivers.
# It uses pywinauto (https://github.com/pywinauto/pywinauto)
# to do this, and the Loci build module packages this script
# alongside it's dependencies as a .pyz executable.

# The goal is to add detect plugged in SDR USB devices and tell the windows OS
# to use libusb-1.0 for communication with them.
# This script will have to be run as admin.


import os
import sys
import subprocess
import urllib.request
import tempfile
import time
import traceback

libusb_install_py_pkgs = os.path.join(tempfile.gettempdir(), 'libusb_install_py_pkgs')
sys.path.append(libusb_install_py_pkgs)

# python -m pip install --target=DIRECTORY_NAME six comtypes pypiwin32
# python -m pip install --user pywinauto
try:
  from pywinauto.application import Application
except Exception as e:
  print(e)
  print('Attempting to auto-install dependencies using -m pip --user...')

  # print('libusb_install_py_pkgs={}'.format(libusb_install_py_pkgs))

  # if not os.path.exists(libusb_install_py_pkgs):
  #   os.makedirs(libusb_install_py_pkgs)

  # subprocess.run([
  #   sys.executable, '-m', 'pip', 'install', '--target', libusb_install_py_pkgs, 'pywinauto', 'pywin32', 'pypiwin32'
  # ])

  # Small TODO: don't use the user's home directory for these packages;
  # TBH not crying much over this one.
  subprocess.run([
    sys.executable, '-m', 'pip', 'install', '--user', 'pywinauto'
  ])

  from pywinauto.application import Application


if __name__ == '__main__':
  zadig_tmp_exe = os.path.join(tempfile.gettempdir(), 'zadig.exe')
  print('zadig_tmp_exe={}'.format(zadig_tmp_exe))

  if not os.path.exists(zadig_tmp_exe):
    with urllib.request.urlopen('https://github.com/pbatard/libwdi/releases/download/b730/zadig-2.5.exe') as url_f:
      with open(zadig_tmp_exe, 'wb') as zadig_tmp_f:
        zadig_tmp_f.write( url_f.read() )

  # Now we use pywinauto to automate execution
  app = Application().start(zadig_tmp_exe)

  try:
    
    app.print_control_identifiers()
    
    time.sleep(10)

  except Exception as e:
    traceback.print_exc()


  app.kill()




