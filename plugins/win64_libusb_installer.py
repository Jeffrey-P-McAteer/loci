
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
if not os.path.exists(libusb_install_py_pkgs):
  os.makedirs(libusb_install_py_pkgs)
sys.path.append(libusb_install_py_pkgs)
# This is used by pip when you pass --user
os.environ['PYTHONUSERBASE'] = libusb_install_py_pkgs

# python -m pip install --target=DIRECTORY_NAME six comtypes pypiwin32
# python -m pip install --user pywinauto
try:
  from pywinauto.application import Application
except Exception as e:
  print(e)

  we_have_pip = False
  try:
    import pip
    we_have_pip = True
  except Exception as e:
    print(e)    

  if not we_have_pip:
    get_pip_script = os.path.join(tempfile.gettempdir(), 'get-pip.py')
    print('get_pip_script={}'.format(get_pip_script))

    if not os.path.exists(get_pip_script):
      with urllib.request.urlopen('https://bootstrap.pypa.io/get-pip.py') as url_f:
        with open(get_pip_script, 'wb') as pip_tmp_f:
          pip_tmp_f.write( url_f.read() )

    subprocess.run([
      sys.executable, get_pip_script, '--user'
    ])

  print('Attempting to auto-install dependencies using -m pip --user...')

  # Small TODO: don't use the user's home directory for these packages;
  # TBH not crying much over this one.
  subprocess.run([
    sys.executable, '-m', 'pip', 'install', '--user', 'pywinauto'
  ])


  from pywinauto.application import Application


if __name__ == '__main__':
  
  if 'ZADIG_EXE_PATH' in os.environ and os.path.exists(os.environ['ZADIG_EXE_PATH']):
    zadig_tmp_exe = os.environ['ZADIG_EXE_PATH']

  else:
    zadig_tmp_exe = os.path.join(tempfile.gettempdir(), 'zadig.exe')
  
  print('zadig_tmp_exe={}'.format(zadig_tmp_exe))

  if not os.path.exists(zadig_tmp_exe):
    with urllib.request.urlopen('https://github.com/pbatard/libwdi/releases/download/b730/zadig-2.5.exe') as url_f:
      with open(zadig_tmp_exe, 'wb') as zadig_tmp_f:
        zadig_tmp_f.write( url_f.read() )

  # Now we use pywinauto to automate execution
  app = Application().start(zadig_tmp_exe)

  try:
    
    winspec = app.top_window()

    winspec.wait('visible')

    # Debugging
    winspec.dump_tree()


    # TODO rotate through all items from USB dropdown
    # By default this is filtered so we only see things that look like RTL-SDRs
    for i in range(0, winspec['ComboBox'].item_count()):
      print('Installing driver for device {}'.format(i))

      winspec['ComboBox'].select(i)
      time.sleep(0.25)

      # Run through values of DriverEdit2 until it contains 'libusb-win32'
      max_tries = 12
      while not ( 'libusb-win32' in winspec['DriverEdit2'].text_block() ) and max_tries > 0:
        max_tries -= 1
        winspec['UpDown'].increment()

      winspec['Install DriverButton'].click()

      # Wait for 'Installing Driver' window to appear + wait for it to exit
      while app.top_window() == winspec:
        print("Waiting for popup...")
        time.sleep(0.5)

      print("Popup opened!")
      popup_win = app.top_window()
      popup_win.wait('visible')
      popup_win.dump_tree()

      popup_win.wait_not('visible', timeout=120)
      print("Popup closed!")


  except Exception as e:
    traceback.print_exc()

  app.kill()




