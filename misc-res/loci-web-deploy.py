# Run by loci-web-deploy.service
# after loci repo has been cloned

import os
import sys
import subprocess

def cmd(*args):
  subprocess.run(list(args), check=True)

def main(args=sys.argv):
  # Move to repo root
  os.chdir(
    os.path.dirname(os.path.dirname( os.path.abspath(__file__) ))
  )

  # Check current vs previous build hash & exit if already processed
  current_build_hash = str(subprocess.check_output([
    'git', 'rev-parse', 'HEAD',
  ]), 'utf-8').strip()
  last_build_hash = 'NONE'
  try:
    with open('/tmp/.last_build_hash', 'r') as fd:
      last_build_hash = fd.read()
      if not isinstance(last_build_hash, str):
        last_build_hash = str(last_build_hash, 'utf-8')
      last_build_hash = last_build_hash.strip()
  except Exception as e:
    print(e)

  if last_build_hash in current_build_hash or current_build_hash in last_build_hash:
    print('Exiting because current_build_hash={} and last_build_hash={}'.format(current_build_hash, last_build_hash))
    print('Remove /tmp/.last_build_hash to force a run.')
    return

  # Record which version is getting published
  try:
    with open('/tmp/.last_build_hash', 'w') as fd:
      fd.write(current_build_hash)
  except Exception as e:
    print(e)


  # Ensures 3rdparty packages exist
  cmd(sys.executable, '-m', 'python_packages')

  # Build all targets
  cmd(sys.executable, '-m', 'btool')
  
  # Ask webpage_update_tool to drop www/ into /usr/share/nginx/html/
  cmd(sys.executable, '-m', 'webpage_update_tool', 'direct_folder', '/usr/share/nginx/html/')


  


if __name__ == '__main__':
  main()


