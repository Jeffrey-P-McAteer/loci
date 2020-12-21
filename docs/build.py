
import os
import sys
import subprocess
import glob
import webbrowser

import urllib.request
import tempfile
import shutil
import datetime

# python -m pip install --user requests
import requests


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

def get_release_download_url(lower_title_contains):
  r = requests.get('https://api.github.com/repos/Jeffrey-P-McAteer/loci/releases')
  
  # Releases are newest -> oldest
  for release in r.json():
    # Get first with "windows" in title
    if lower_title_contains in release['name'].lower():
      # Return the first asset URL
      return release['assets'][0]['browser_download_url']

  return 'javascript:alert("Coming soon!");'


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
          '<head><link rel="stylesheet" href="pages_style.css"></head>'+
          markdown(
            md_fd.read()
          )
        )

  plantuml_files = [x for x in glob.glob('*.puml')]
  subprocess.run([
    'java', '-jar', plantuml_jar, *plantuml_files, '-o', output_d
  ])

  with open('pages-index.html', 'r') as src_fd:
    contents = src_fd.read()
    
    contents = contents.replace(
      'LAST_UPDATE_TIMESTAMP',
      datetime.datetime.now().strftime('%Y-%m-%d %H:%M %Z')
    )

    contents = contents.replace(
      'WINDOWS_DOWNLOAD_URL',
      get_release_download_url('windows64')
    )

    contents = contents.replace(
      'LINUX_DOWNLOAD_URL',
      get_release_download_url('linux64')
    )

    contents = contents.replace(
      'SERVER_DOWNLOAD_URL',
      get_release_download_url('linux64')
    )

    with open(os.path.join(output_d, 'index.html'), 'w') as dst_fd:
      dst_fd.write(contents)


  shutil.copy(
    'pages_style.css',
    os.path.join(output_d, 'pages_style.css')
  )

  asset_files = [
    'sportscenter.ttf',
    'icon.png',
    'splash.jpg',

    'linux_icon.png',
    'macos_icon.png',
    'windows_icon.png',
    'server_icon.png',
    'android_icon.png',
    'wearos_icon.png',

  ]
  for af in asset_files:
    shutil.copy(
      os.path.join('..', 'assets', af),
      os.path.join(output_d, af)
    )

  # Done generating content

  if 'open' in sys.argv or 'show' in sys.argv:
    webbrowser.open(output_d)

  if 'publish' in sys.argv or 'upload' in sys.argv:
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

    if 'open' in sys.argv or 'show' in sys.argv:
      webbrowser.open(pages_url)




if __name__ == '__main__':
  main()

