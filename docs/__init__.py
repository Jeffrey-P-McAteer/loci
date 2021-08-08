
import os
import sys
import subprocess
import webbrowser
import shutil

# We re-use a number of utilities designed for building subprograms
import btool
from btool import j, e, download_tools
from btool import main as btool_main
from btool.utils import within
from btool.utils import host_is_linux


def main(args=sys.argv):
  # Docs go in ./out/docs/*/index.html
  if not e('readme.md'):
    die('Must be run from loci root like "python -m docs [args]')
  
  download_tools()

  # Compile everything "hostonly" before building docs
  #btool_main(['hostonly'])

  docs_webroot = j('out', 'docs')
  if not os.path.exists(docs_webroot):
    os.makedirs(docs_webroot)

  # Helper utility
  def build_docs_from(cwd_sub_dir, doc_gen_cmd, doc_out_dir):
    webroot_dirname = j(docs_webroot, os.path.basename(cwd_sub_dir))
    within(cwd_sub_dir,
      lambda: subprocess.run(doc_gen_cmd, check=True)
    )
    if not os.path.exists(webroot_dirname):
      os.makedirs(webroot_dirname)
    shutil.copytree(doc_out_dir, webroot_dirname, dirs_exist_ok=True)

  # List of ('Title', 'path/to/index.html') for all sub-projects,
  # used to generate ./out/docs/index.html
  docs_contents = []

  ### BEGIN Sub-Project Documentation Section ###

  build_docs_from(
    j('app-lib'),
    ['cargo', 'doc', '--no-deps'],
    j('app-lib', 'target', 'doc'),
  )
  docs_contents.append(('App-Lib', j('app-lib', 'app_lib', 'index.html')))

  build_docs_from(
    j('app-kernel'),
    ['cargo', 'doc', '--no-deps'],
    j('app-kernel', 'target', 'doc'),
  )
  docs_contents.append(('App-Kernel (Desktop)', j('app-kernel', 'app_kernel', 'index.html')))

  build_docs_from(
    j('app-kernel-android'),
    ['gradle', 'genJavadoc'],
    j('app-kernel-android', 'build', 'docs', 'javadoc'),
  )
  docs_contents.append(('App-Kernel (Android)', j('app-kernel-android', 'index.html')))

  build_docs_from(
    j('app-subprograms', 'desktop-cli'),
    ['cargo', 'doc', '--no-deps'],
    j('app-subprograms', 'desktop-cli', 'target', 'doc'),
  )
  docs_contents.append(('Desktop CLI', j('desktop-cli', 'desktop_cli', 'index.html')))

  build_docs_from(
    j('app-subprograms', 'server-webgui'),
    ['cargo', 'doc', '--no-deps'],
    j('app-subprograms', 'server-webgui', 'target', 'doc'),
  )
  docs_contents.append(('Server WebGUI', j('server-webgui', 'server_webgui', 'index.html')))


  ### END Sub-Project Documentation Section ###

  docs_index = j(docs_webroot, 'index.html')
  with open(docs_index, 'w') as fd:
    toc_html = '<ul>'
    for title, url in docs_contents:
      toc_html += '<li><a href="{}">{}</a></li>'.format(url, title)
      if not os.path.exists(j(docs_webroot, url)):
        print('FATAL: URL for {} does not exist, your documentation will have broken links! ({} cannot be found under {})'.format(title, url, docs_webroot))
        sys.exit(5)

    toc_html += '</ul>'

    fd.write('''<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    <h1>Loci Sub-project documentation</h1>
    {toc_html}
  </body>
</html>
'''.format(
  toc_html=toc_html
).strip())

  # Finally open a browser to the new doc webroot
  if not 'nobrowser' in args:
    webbrowser.open(os.path.abspath(docs_index))

