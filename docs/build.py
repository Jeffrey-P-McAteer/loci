
import os
import sys
import subprocess
import glob
import webbrowser

import urllib.request
import tempfile
import shutil

# python -m pip install --user markdown
from markdown import *

def download_plantuml_jar():
  """
  Downloads https://netactuate.dl.sourceforge.net/project/plantuml/plantuml.jar
  and saves to a temporary directory. Temporary data persists after
  the program exists, so running twice only needs to download the .jar once.
  This function always returns the path to the .jar file.
  """
  url = 'https://netactuate.dl.sourceforge.net/project/plantuml/plantuml.jar'
  file = os.path.join(tempfile.gettempdir(), 'plantuml.jar')
  if not os.path.exists(file) or os.path.getsize(file) < 100:
    # Download "url" to "file"
    print('Saving plantuml.jar to {}'.format(file))
    urllib.request.urlretrieve(url, file)

  return file

def main():
  # Move to ./docs/ directory
  os.chdir(os.path.dirname(os.path.abspath(__file__)))

  output_d = os.path.abspath('build')
  if not os.path.exists(output_d):
    os.makedirs(output_d)

  plantuml_jar = download_plantuml_jar()

  # Generate all content

  for markdown_f in glob.glob('*.md'):
    html_f = os.path.basename(markdown_f)[:-3]+'.html'
    html_f = os.path.join(output_d, html_f)

    with open(markdown_f, 'r') as md_fd:
      with open(html_f, 'w') as html_fd:
        html_fd.write(
          markdown(
            md_fd.read()
          )
        )

  plantuml_files = [x for x in glob.glob('*.puml')]
  subprocess.run([
    'java', '-jar', plantuml_jar, *plantuml_files, '-o', output_d
  ])

  shutil.copy(
    'pages-index.html',
    os.path.join(output_d, 'index.html')
  )

  shutil.copy(
    os.path.join('..', 'assets', 'sportscenter.ttf'),
    os.path.join(output_d, 'sportscenter.ttf')
  )

  shutil.copy(
    os.path.join('..', 'assets', 'icon.png'),
    os.path.join(output_d, 'icon.png')
  )

  # Done generating content

  if 'open' in sys.argv:
    webbrowser.open(output_d)

  if 'publish' in sys.argv:
    print('Publishing...')

    # Assumes the "doc-pages" branch exists
    # on the repository URL assigned to "origin".

    # git checkout --orphan doc-pages
    # git rm --cached -r .
    
    gh_pages_d = os.path.join(tempfile.gettempdir(), 'loci-pages')
    if not os.path.exists(gh_pages_d):
      subprocess.run([
        'git', 'clone',
          '--single-branch',
          '--branch', 'doc-pages',
          subprocess.check_output(['git', 'remote', 'get-url', 'origin']).decode('utf-8').strip(),
          gh_pages_d
      ], check=True)

    # Move into the cloned repo and delete all history (back to commit #1)
    first_commit = subprocess.check_output([
      'git', 'rev-list', '--max-parents=0', '--abbrev-commit', 'HEAD'
    ], cwd=gh_pages_d).decode('utf-8').strip()
    subprocess.run([
        'git', 'reset', '--hard', first_commit
    ], cwd=gh_pages_d)

    # Delete all files in gh_pages_d
    for f in os.listdir(gh_pages_d):
      if '.git' in f:
        continue
      f = os.path.join(gh_pages_d, f)
      if os.path.isdir(f):
        shutil.rmtree(f)
      else:
        os.remove(f)

    # Copy data from output_d into gh_pages_d
    shutil.copytree(output_d, gh_pages_d, dirs_exist_ok=True)

    # Now move into the gh_pages_d,
    # commit the new contents, and do a
    # forced push to overwrite the remote
    # with new data.
    subprocess.run([
        'git', 'add', '-A'
    ], cwd=gh_pages_d)
    subprocess.run([
        'git', 'commit', '-a', '-m', 'Commit authored by the ./docs/build.py script'
    ], cwd=gh_pages_d)
    subprocess.run([
        'git', 'push', '-f'
    ], cwd=gh_pages_d)

    pages_url = 'https://jeffrey-p-mcateer.github.io/loci/'
    print('Published to {}'.format(pages_url))

    if 'open' in sys.argv:
      webbrowser.open(pages_url)




if __name__ == '__main__':
  main()

