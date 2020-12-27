
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

embedded_site_packages = os.path.join(os.path.dirname(sys.executable), 'site-packages')
sys.path.append(embedded_site_packages)

full_auto_possible = False


try:
  # embedded by build_loci_eapp_dir_win64()
  from pywinauto.application import Application
  full_auto_possible = True
except Exception as e:
  traceback.print_exc()


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

  if not full_auto_possible:
    # Best we can do is open zadig_tmp_exe and hope the user can press
    # the same buttons we do.
    # TODO figure out how to ensure "pip install pywinauto" is portable.
    p = subprocess.run([zadig_tmp_exe])
    sys.exit(p.returncode)

  # Now we use pywinauto to automate execution
  app = Application().start(zadig_tmp_exe)

  try:
    
    winspec = app.top_window()

    winspec.wait('visible')

    # Debugging
    winspec.dump_tree()

    # rotate through all items from USB dropdown
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

      # TODO wait for "close" button and click it. Currently we need the user to do this.

      popup_win.wait_not('visible', timeout=120)
      print("Popup closed!")


  except Exception as e:
    traceback.print_exc()

  app.kill()




