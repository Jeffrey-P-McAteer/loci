
import os
import sys
import subprocess
import glob
import webbrowser

import urllib.request
import tempfile

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

  webbrowser.open(output_d)



if __name__ == '__main__':
  main()

