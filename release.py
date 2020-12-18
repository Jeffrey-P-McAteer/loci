
import os
import sys
import subprocess

def main():
  # Grab the most revent tag, split off the last integer,
  # increment that integer, tag and push!
  most_recent_tag = subprocess.check_output([
    'git','describe','--abbrev=0'
  ]).decode('utf-8').strip()

  most_recent_tag_hash = subprocess.check_output([
    'git', 'rev-parse', most_recent_tag+'^{}'
  ]).decode('utf-8').strip()

  current_head_hash = subprocess.check_output([
    'git', 'rev-parse', 'HEAD'
  ]).decode('utf-8').strip()

  if most_recent_tag_hash.lower() == current_head_hash.lower():
    print('This content is already tagged as {}!'.format(most_recent_tag))
    print('Make a change and commit it to create a new version!')
    sys.exit(1)

  last_nondigit_i = len(most_recent_tag)-1
  while most_recent_tag[last_nondigit_i].isdigit():
    last_nondigit_i -= 1

  next_tag_num = most_recent_tag[:last_nondigit_i] +'.'+ str( int(most_recent_tag[last_nondigit_i+1:]) + 1)

  msg = ' '.join(sys.argv[1:]).strip()
  if not msg:
    msg = 'No version message'

  subprocess.run([
    'git', 'tag', '-m', msg, next_tag_num
  ], check=True)

  subprocess.run([
    'git', 'push', '--follow-tags'
  ], check=True)


if __name__ == '__main__':
  main()
