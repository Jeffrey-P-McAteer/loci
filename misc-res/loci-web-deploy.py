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

  # Ensures 3rdparty packages exist
  subprocess.run([sys.executable, '-m', 'python_packages'], check=True)

  # Build all targets
  cmd(sys.executable, '-m', 'btool')
  
  # Ask webpage_update_tool to drop www/ into /usr/share/nginx/html/
  cmd(sys.executable, '-m', 'webpage_update_tool', 'direct_folder', '/usr/share/nginx/html/')
  


if __name__ == '__main__':
  main()


