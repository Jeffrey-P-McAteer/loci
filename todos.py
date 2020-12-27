
import os
import sys
import subprocess
import re

if __name__ == '__main__':
  
  tracked_files = subprocess.check_output([
    'git', 'ls-tree', '-r', 'main', '--name-only'
  ]).decode('utf-8')
  
  num_todos = 0
  num_high_priority = 0

  for file in tracked_files.splitlines():
    with open(file, 'r') as fd:
      try:
        content = fd.read()
        for line_num, line in enumerate(content.splitlines()):
          matches = re.findall('#.+todo.*', line, re.DOTALL)
          matches += re.findall('#.+TODO.*', line, re.DOTALL)
          matches += re.findall('//.+todo.*', line, re.DOTALL)
          matches += re.findall('//.+TODO.*', line, re.DOTALL)
          matches += re.findall('\\*.+todo.*', line, re.DOTALL)
          matches += re.findall('\\*.+TODO.*', line, re.DOTALL)

          for m in matches:
            print("{}:{}:{}     {}".format(file, line_num+1, os.linesep, m.strip(), os.linesep))

      except UnicodeDecodeError as ude:
        pass
        # unicode errors are from PNG/JPEG and other binaries
        # we add to the repository.
        # This is a known bad pattern.


  print("="*6, "Summary", "="*6)
  print("  {} Todos ({} high priority)".format(num_todos, num_high_priority))
  


