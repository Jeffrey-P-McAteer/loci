
# Often it is useful to ask the codebase something.
#
# "Where is variable X read and written?"
# "When does db table T get used?"
# 
# This tool iterates all files tracked in git,
# performs a rudimentary test to see if they begin with ASCII text,
# and for all git-tracked ASCII files it reports back regex matches.
# 
# In addition to searching for any regex, this tool acts as a
# central point to record common regexes, such as: [Ee]nv[^"]*"([a-zA-Z0-9]+)"
# The above regex pulls out the names of environment variables using
# a capture group, and is generic enough to match:
#   env::var("ABC")       - rust
#   os.environ["ABC"]     - python
#   System.getenv("ABC")  - java
# 
# As common searches become used we will add them here so searching for all env vars
# is as easy as:
#    python -m code_query_tool list-all-env-vars

import os
import sys
import subprocess
import re

def help():
  print("""
Usage: python -m code_query_tool REGEX|<arg> [REGEX|<arg>]*

where REGEX is a regular expression or <arg> may be any of the following:

   list-all-env-vars    Prints all places where code reads/writes an environment variable.
                          These are often used for development-grade configuration, such as the "NO_CONSOLE_DETATCH" variable
                          in app-kernel which keeps the console open when double-clicked in explorer.exe.

   list-all-sys-props   Prints all system properties by querying strings in all places where
                          code gets/sets a system property.

   todos                Print all lines with comments like "# TODO" or "// TODO"

""".strip())

def get_regex_str(arg):
  if arg == 'list-all-env-vars':
    return 'env[^"]*"([a-zA-Z0-9_-]+)"'
  elif arg == 'list-all-sys-props':
    return '[gs]et_prop[^"]*"([a-zA-Z0-9_-]+)"'
  elif arg == 'todos':
    return '(#|\\/\\/)\\s+todo'
  else:
    return arg

def process_regex(tracked_files, regex_str, pattern=None, debug=False):
  if not pattern:
    pattern = re.compile(regex_str)

  for tracked_file in tracked_files:
    file_is_ascii = True
    with open(tracked_file, 'rb') as fd:
      chunk = fd.read(128)
      for b in chunk:
        if b < 0x08: # less than backspace
          file_is_ascii = False
          break
        elif b > 0x97:
          file_is_ascii = False
          break
    
    if not file_is_ascii:
      if debug:
        print("ignoring {}".format(tracked_file))
      continue

    with open(tracked_file, 'r') as fd:
      contents = fd.read()
      for i, line in enumerate(contents.split(os.linesep), start=1):
        if pattern.search(line.lower()):
          print('{}:{}: {}'.format(tracked_file, i, line))

def main(args=sys.argv):
  if len(args) < 2:
    return help()

  tracked_files_bin = subprocess.check_output([
    'git', 'ls-tree', '-r', 'HEAD', '--name-only'
  ])
  tracked_files = tracked_files_bin.decode('utf-8')
  tracked_files = [x.strip() for x in tracked_files.split(os.linesep) if len(x.strip()) > 1 and os.path.exists(x.strip())]
  
  debug = 'CQT_DEBUG' in os.environ

  if debug:
    for f in tracked_files:
      print('tracked file = {}'.format(f))

  for arg in args[1:]:
    regex_str = get_regex_str(arg)
    pattern = re.compile(regex_str)
    if debug:
      print('regex_str={}'.format(regex_str))
    process_regex(tracked_files, regex_str, pattern=pattern, debug=debug)





if __name__ == '__main__':
  main()

