
# groundup goes a step further than btool.
# btool downloads development SDKs for the host OS
# and sometimes (linux x86_64 only for now) adds tools
# to cross-compile for foreign hosts.
# groundup downloads operating system images
# and uses QEMU to boot VMs.
# Once booted, groundup uses the serial connection
# to issue commands to the VM.
# The commands issued will copy the CWD into the VM,
# run btool as a non-privledged user, and report
# how much was built within the VM.
# Finally, graphics may be provided for the VM
# so that developers can use this as a development environment.

# Dependencies:
#  python, qemu, tar, pexpect, ssh,

# CURRENT STATUS
#   Abandoned, but this is a distinct nice-to-have for later.


import os
import sys
import urllib
import urllib.request
import json
import zipfile
import subprocess
import time
import signal
import traceback
import shutil
import tempfile

# Our own tools
import btool


VM_IMAGES_DIR = os.path.join('out', 'vms')

windows_x86_64_qcow2 = None
fedora_x86_64_qcow2 = None

children_ps = []

def on_exit_req(sig, frame):
  global children_ps
  print("Exiting...")
  for child_ps in children_ps:
    try:
      child_ps.terminate()
      
      max_polls = 15
      while child_ps.poll() is None:
        time.sleep(0.1)

      if child_ps.poll() is None:
        child_ps.kill()

    except:
      traceback.print_exc()
  
  sys.exit(0)

def is_linux():
  return 'linux' in sys.platform.lower()


def json_key_search(json_input, lookup_key):
    if isinstance(json_input, dict):
        for k, v in json_input.items():
            if k == lookup_key:
                yield v
            else:
                yield from json_key_search(v, lookup_key)
    elif isinstance(json_input, list):
        for item in json_input:
            yield from json_key_search(item, lookup_key)

def get_msecnd_url(search_s):
  vm_json = urllib.request.urlopen('https://developer.microsoft.com/en-us/microsoft-edge/api/tools/vms/').read()
  vm_data = json.loads(vm_json)
  for url in json_key_search(vm_data, 'url'):
    if search_s in url and url.endswith('.zip'):
      return url
  print('Error: No VM available for search: {}.'.format(search_s), file=sys.stderr)
  sys.exit(5)

# Empties file; used to leave work state
# without keeping unecessary data around
def zero_file(file):
  with open(file, 'w+') as f:
    f.write(' ')

def find_file_by_glob(directory, glob):
  for file in glob.glob(os.path.join(directory, glob)):
    return file
  return None

def filter_nones(l):
  l2 = []
  for i in l:
    if i is None:
      continue
    l2.append(i)
  return l2

# only works as long as there is 1+ partitions on the disk
def next_free_nbd():
  def ith(i):
    return '/dev/nbd{}'.format(i)
  i = 0
  while os.path.exists(ith(i)+'p1'):
    i += 1
  return ith(i)

def download_windows_vm():
  global windows_x86_64_qcow2
  global VM_IMAGES_DIR

  vm_zip_name = 'MSEdge.Win10.VirtualBox.zip'
  vm_unzipped_name = 'MSEdge.Win10.VirtualBox';
  vm_ova_name = 'MSEdge*Win10.ova';

  vm_image_zip = os.path.join(VM_IMAGES_DIR, vm_zip_name)
  if not os.path.exists(vm_image_zip):
    img_url = get_msecnd_url(vm_zip_name)
    print('Downloading zipped image from {}...'.format(img_url))
    
    def report(chunk_num, max_chunk_size, total_dl_size):
      if total_dl_size > 1:
        percent = (chunk_num*max_chunk_size) / total_dl_size
        sys.stderr.write("Progress: {:.2f}%     \r".format(percent*100.0) )
        sys.stderr.flush()
      else:
        if chunk_num % 10 == 0:
          sys.stderr.write(".")
          sys.stderr.flush()

    urllib.request.urlretrieve(img_url, vm_image_zip, reporthook=report);

  vm_unzipped_dir = os.path.join(VM_IMAGES_DIR, vm_unzipped_name)
  if not os.path.exists(vm_unzipped_dir):
    print('Unzipping to {}'.format(vm_unzipped_dir))
    with zipfile.ZipFile(vm_image_zip, 'r') as zip_ref:
      zip_ref.extractall(vm_unzipped_dir)
  
  zero_file(vm_image_zip)

  vm_ova_f = os.path.join(vm_unzipped_dir, vm_ova_name)
  vm_vmdk_f = os.path.join(vm_unzipped_dir, 'MSEdge - Win10-disk001.vmdk')
  if not os.path.exists(vm_vmdk_f):
    print("Un-tarring {}...".format(vm_ova_f))
    os.system('cd "{}" ; tar -xvf *.ova '.format(vm_unzipped_dir))

  zero_file(vm_ova_f)

  vm_qcow2 = os.path.join(VM_IMAGES_DIR, 'MSEdgeWin.qcow2')
  if not os.path.exists(vm_qcow2):
    print("converting {} to {}".format(vm_vmdk_f, vm_qcow2))
    subprocess.run([
      'qemu-img', 'convert', '-O', 'qcow2', vm_vmdk_f, vm_qcow2
    ], check=True)

  zero_file(vm_vmdk_f)

  windows_x86_64_qcow2 = os.path.abspath(vm_qcow2)
  print('Windows OS resides in {}'.format(windows_x86_64_qcow2))

  # Attempt to mount+write admin bootup powershell configure script to VM
  # so we enable OpenSSH-Server at first boot
  vm_image_modification_flag = os.path.join(VM_IMAGES_DIR, 'MSEdgeWin_qcow2_altered.txt')
  if not os.path.exists(vm_image_modification_flag):
    if is_linux():
      # Resize .qcow2 to be dynamic supporting up to 128gb
      subprocess.run(['qemu-img', 'resize', windows_x86_64_qcow2, '128G'], check=True)

      # Mount block devices within .qcow2
      subprocess.run(['sudo', 'modprobe', 'nbd', 'max_part=8'], check=True)
      nbd_device = next_free_nbd()
      subprocess.run(['sudo', 'qemu-nbd', '--connect={}'.format(nbd_device), windows_x86_64_qcow2], check=True)

      # Now we have partitions as nbd_device+'p1' etc.
      windows_fat32_part = nbd_device+'p1'
      subprocess.run(['sudo', 'ntfsfix', '--clear-dirty', windows_fat32_part], check=True)
      win_c_mount_dir = tempfile.mkdtemp()
      subprocess.run(['sudo', 'mount', '-o', 'rw', windows_fat32_part, win_c_mount_dir], check=True)
      print('Mounted C:\\ to {}'.format(win_c_mount_dir))

      # NB: all files under win_c_mount_dir will be owned by root

      windows_startup_dir = os.path.join(
        win_c_mount_dir, 'Windows', 'System32', 'GroupPolicy', 'Machine', 'Scripts', 'Startup',
      )
      subprocess.run(['sudo', 'mkdir', '-p', windows_startup_dir], check=True)
      
      # Now write a powershell script to run on all boots to enable SSH + resize first partition
      fd_ps1, path_ps1 = tempfile.mkstemp()
      fd_ini, path_ini = tempfile.mkstemp()
      try:
        with os.fdopen(fd_ps1, 'w') as tmp:
          # Add PS to deploy OpenSSHD (https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse)
          tmp.write('''
set-executionpolicy -executionpolicy unrestricted
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22

Stop-Service sshd

''')

        subprocess.run(['sudo', 'cp', path_ps1, os.path.join(windows_startup_dir, 'vmsetup.ps1')], check=True)
        subprocess.run(['sudo', 'chmod', '+x', os.path.join(windows_startup_dir, 'vmsetup.ps1')], check=True)

        with os.fdopen(fd_ini, 'w') as tmp:
          # Add PS to deploy OpenSSHD (https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse)
          tmp.write('''
[ScriptsConfig]
StartExecutePSFirst=true
EndExecutePSFirst=true

[Startup]
0CmdLine=C:\\Windows\\System32\\GroupPolicy\\Machine\\Scripts\\Startup\\vmsetup.ps1
0Parameters=

''')

        # Documentation is unclear, create both psscripts.ini and scripts.ini
        subprocess.run(['sudo', 'cp', path_ini, os.path.join(windows_startup_dir, 'psscripts.ini')], check=True)
        subprocess.run(['sudo', 'cp', path_ini, os.path.join(windows_startup_dir, 'scripts.ini')], check=True)

      finally:
        subprocess.run(['sync'])
        subprocess.run(['sudo', 'umount', windows_fat32_part], check=True)
        os.remove(path_ps1)
        os.remove(path_ini)

      subprocess.run(['sudo', 'qemu-nbd', '--disconnect', nbd_device], check=True)
      # find /dev -maxdepth 1 -iname 'nbd*' -print -exec sudo qemu-nbd --disconnect {} \;

      os.rmdir(win_c_mount_dir)
      
    else:
      raise Exception('Cannot modify VM .qcow2 using windows system, no implemented way to mount and write to VM hdd.')

    zero_file(vm_image_modification_flag)



def download_fedora_vm():
  global fedora_x86_64_qcow2
  global VM_IMAGES_DIR

  vdi_image = os.path.join(VM_IMAGES_DIR, '64bit', 'Fedora 34 (64bit).vdi')
  if not os.path.exists(vdi_image):
    btool.utils.dl_archive_to(
      'https://sourceforge.net/projects/osboxes/files/v/vb/18-F-d/34/64bit.7z/download',
      VM_IMAGES_DIR,
      extension='.7z'
    )

  vm_qcow2 = os.path.join(VM_IMAGES_DIR, 'Fedora34.qcow2')
  if not os.path.exists(vm_qcow2):
    print("converting {} to {}".format(vdi_image, vm_qcow2))
    subprocess.run([
      'qemu-img', 'convert', '-f', 'vdi', '-O', 'qcow2', vdi_image, vm_qcow2
    ], check=True)

  zero_file(vdi_image)


  fedora_x86_64_qcow2 = os.path.abspath(vm_qcow2)
  print('Fedora OS resides in {}'.format(fedora_x86_64_qcow2))



def boot_windows_vm():
  global windows_x86_64_qcow2
  global children_ps

  children_ps.append(subprocess.Popen(filter_nones([
    'qemu-system-x86_64',
      '-drive', f'format=qcow2,file={windows_x86_64_qcow2}',
      '-enable-kvm' if is_linux() else None,
      '-smp', '4', '-cpu', 'host', '-m', '8056',
      '-net', 'nic', '-net', 'user,hostfwd=tcp::10022-:22,smb={}'.format(os.path.abspath('.')),
      # Mount within VM: \\10.0.2.4\qemu\, ssh to IEUser@localhost:10022
      '-chardev', 'socket,path=/tmp/qga.sock,server=on,wait=off,id=qga0',
      '-device', 'virtio-serial',
      '-device', 'virtserialport,chardev=qga0,name=org.qemu.guest_agent.0',

      #'-nographic',
      '-serial', 'mon:stdio',

  ])))

def boot_fedora_vm():
  pass

def main(args=sys.argv):
  global VM_IMAGES_DIR
  global children_ps

  signal.signal(signal.SIGINT, on_exit_req)

  req_cmds = [
    'qemu-system-x86_64', 'tar', 'ssh',
  ]
  for c in req_cmds:
    if not shutil.which(c):
      print('Error, tool missing: {}'.format(c))
      sys.exit(1)
      return

  if not os.path.exists(VM_IMAGES_DIR):
    os.makedirs(VM_IMAGES_DIR)

  btool.utils.set_env_from_dev_env_conf('dev-env.conf')
  if 'VM_IMAGES_DIR' in os.environ:
    VM_IMAGES_DIR = os.environ['VM_IMAGES_DIR']


  download_windows_vm()
  download_fedora_vm()

  if 'win' in args or 'windows' in args:
    boot_windows_vm()

  elif 'fedora' in args or 'linux' in args:
    boot_fedora_vm()

  else:
    print('Taking no action; pass "win"/"windows" or "fedora"/"linux" to boot that VM')
    return


  while len(children_ps) > 0:
    time.sleep(0.5)
    # Remove finished processes
    children_ps = [x for x in children_ps if x.poll() is None]

  on_exit_req(None, None)


if __name__ == '__main__':
  main()

