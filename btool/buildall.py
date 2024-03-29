
# Responsible for executing build commands using
# SDKS (dotnet, cargo, gradle, etc.)
# and producing built artifacts under ./out/

from btool import *

def buildall(args):
  build_win64 = flag_set('build_win64')
  build_linux_x86_64 = flag_set('build_linux_x86_64')
  build_linux_aarch64 = flag_set('build_linux_aarch64')
  build_android = flag_set('build_android')

  # Used to quicky refer to the repo root
  r = os.path.abspath('.')

  download_OSM_BPF_FILE()

  create_selfsigned_ssl_certs()

  silenced_task(
    'Downloading python runtime (pypy)', # See https://www.pypy.org/download.html
    inputs(),
    outputs(
      j('out', 'linux_x86_64', 'python'),
      j('out', 'linux_aarch64', 'python'),
      j('out', 'win64', 'python'),
    ),
    lambda: dl_archive_to(
      #'https://www.python.org/ftp/python/3.9.5/python-3.9.5-embed-amd64.zip',
      'https://downloads.python.org/pypy/pypy3.7-v7.3.5-win64.zip',
      j('out', 'win64', 'python')
    ),
    lambda: dl_archive_to(
      'https://downloads.python.org/pypy/pypy3.7-v7.3.5-linux64.tar.bz2',
      j('out', 'linux_x86_64', 'python')
    ),
    lambda: dl_archive_to(
      'https://downloads.python.org/pypy/pypy3.7-v7.3.5-aarch64.tar.bz2',
      j('out', 'linux_aarch64', 'python')
    ),
  )


  silenced_task(
    'Downloading java (adoptopenjdk)', # See https://adoptopenjdk.net/releases.html?variant=openjdk16&jvmVariant=hotspot
    inputs(),
    outputs(
      j('out', 'linux_x86_64', 'jre'),
      j('out', 'linux_aarch64', 'jre'),
      j('out', 'win64', 'jre'),
    ),
    lambda: dl_archive_to(
      'https://github.com/AdoptOpenJDK/openjdk16-binaries/releases/download/jdk-16.0.1%2B9/OpenJDK16U-jre_x64_windows_hotspot_16.0.1_9.zip',
      j('out', 'win64', 'jre')
    ),
    lambda: dl_archive_to(
      'https://github.com/AdoptOpenJDK/openjdk16-binaries/releases/download/jdk-16.0.1%2B9/OpenJDK16U-jre_x64_linux_hotspot_16.0.1_9.tar.gz',
      j('out', 'linux_x86_64', 'jre')
    ),
    lambda: dl_archive_to(
      'https://github.com/AdoptOpenJDK/openjdk16-binaries/releases/download/jdk-16.0.1%2B9/OpenJDK16U-jre_aarch64_linux_hotspot_16.0.1_9.tar.gz',
      j('out', 'linux_aarch64', 'jre')
    ),
  )


  silenced_task(
    'Downloading geoserver', # See http://geoserver.org/release/stable/
    inputs(),
    outputs(
      j('out', 'linux_x86_64', 'geoserver'),
      j('out', 'linux_aarch64', 'geoserver'),
      j('out', 'win64', 'geoserver'),
    ),
    lambda: dl_archive_to(
      'https://versaweb.dl.sourceforge.net/project/geoserver/GeoServer/2.19.1/geoserver-2.19.1-bin.zip',
      j('out', 'win64', 'geoserver')
    ),
    lambda: dl_archive_to(
      'https://versaweb.dl.sourceforge.net/project/geoserver/GeoServer/2.19.1/geoserver-2.19.1-bin.zip',
      j('out', 'linux_x86_64', 'geoserver')
    ),
    lambda: dl_archive_to(
      'https://versaweb.dl.sourceforge.net/project/geoserver/GeoServer/2.19.1/geoserver-2.19.1-bin.zip',
      j('out', 'linux_aarch64', 'geoserver')
    ),
  )


  silenced_task(
    'Building app-lib',
    force_code_rebuilds_conditional_touch(inputs(
      j('app-lib', 'src'),
      j('app-lib', 'Cargo.toml')
    )),
    outputs(
      j('app-lib', 'target', 'x86_64-pc-windows-gnu', 'release'),
      j('app-lib', 'target', 'x86_64-unknown-linux-gnu', 'release'),
      j('app-lib', 'target', 'aarch64-unknown-linux-gnu', 'release'),
    ),
    lambda: within(
      j('app-lib'),
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-pc-windows-gnu') if build_win64 else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-unknown-linux-gnu') if build_linux_x86_64 else None,
      lambda: run_within_cargo_android_arm64_ndk_env(
        lambda: c('rustup', 'run', 'nightly', 'cargo', 'build', '--release', '--target', 'aarch64-linux-android', '-Zbuild-std')
      ) if build_android else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'aarch64-unknown-linux-gnu') if build_linux_aarch64 else None,
    ),
  )


  silenced_task(
    'Building app-kernel-desktop (loci.exe)',
    force_code_rebuilds_conditional_touch(inputs(
      j('app-kernel-desktop', 'src'),
      j('app-kernel-desktop', 'Cargo.toml'),
      j('app-kernel-desktop', 'build.rs'),
      j('app-data-tkeys'),
      j('app-db-schemas'),
    )),
    outputs(
      # j('app-kernel-desktop', 'target', 'x86_64-pc-windows-gnu', 'release'),
      # j('app-kernel-desktop', 'target', 'x86_64-unknown-linux-gnu', 'release'),
      j('out', 'linux_x86_64', 'loci'),
      j('out', 'linux_aarch64', 'loci'),
      j('out', 'win64', 'loci.exe'),
    ),
    lambda: within(
      j('app-kernel-desktop'),
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-pc-windows-gnu') if build_win64 else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-unknown-linux-gnu') if build_linux_x86_64 else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'aarch64-unknown-linux-gnu') if build_linux_aarch64 else None,
    ),
    lambda: assemble_in_win64(
      j('app-kernel-desktop', 'target', 'x86_64-pc-windows-gnu', 'release', 'app-kernel-desktop.exe'),
      'loci.exe'
    ),
    lambda: assemble_in_linux_x86_64(
      j('app-kernel-desktop', 'target', 'x86_64-unknown-linux-gnu', 'release', 'app-kernel-desktop'),
      'loci'
    ),
    lambda: assemble_in_linux_aarch64(
      j('app-kernel-desktop', 'target', 'aarch64-unknown-linux-gnu', 'release', 'app-kernel-desktop'),
      'loci'
    ),
  )


  silenced_task(
    'Building server-webgui',
    force_code_rebuilds_conditional_touch(inputs(
      j('app-subprograms', 'server-webgui', 'src'),
      j('app-subprograms', 'server-webgui', 'www'),
      j('app-subprograms', 'server-webgui', 'Cargo.toml')
    )),
    outputs(
      j('out', 'linux_x86_64', 'server-webgui'),
      j('out', 'linux_aarch64', 'server-webgui'),
      j('out', 'win64', 'server-webgui.exe'),
      j('out', 'android', 'server-webgui'),
    ),
    lambda: within(
      j('app-subprograms', 'server-webgui'),
      # Download www/lib/* files from 3rdparties (.gitignored for safety)
      lambda: dl_once(
        'https://files.worldwind.arc.nasa.gov/artifactory/apps/web/worldwind.min.js',
        j('www', 'lib', 'worldwind.min.js')
      ),
      lambda: dl_archive_to_once(
        'https://github.com/openlayers/openlayers/releases/download/v6.6.1/v6.6.1-dist.zip',
        j('www', 'lib', 'openlayers')
      ),
      lambda: dl_once(
        'https://cdnjs.cloudflare.com/ajax/libs/split.js/1.6.0/split.min.js',
        j('www', 'lib', 'split.min.js')
      ),
      lambda: dl_once(
        'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js',
        j('www', 'lib', 'jquery.min.js')
      ),
      lambda: dl_archive_to_once(
        'https://www.smartmenus.org/files/?file=smartmenus-jquery/smartmenus-1.1.1.zip',
        j('www', 'lib', 'smartmenus'),
        and_then_with_dir=[
          # ensure phones get desktop menu styles as well
          lambda d: simple_replace(j(d, 'css', 'sm-simple', 'sm-simple.css'), '@media (min-width: 768px)', '@media (min-width: 8px)'),
        ]
      ),
      lambda: scale_image_once(j('..', '..', 'misc-res', 'icon.png'), j('www', 'gen', 'icon-192.png'), (192, 192)),
      lambda: scale_image_once(j('..', '..', 'misc-res', 'icon.png'), j('www', 'gen', 'icon-512.png'), (512, 512)),
      # Build standalone webserver
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-pc-windows-gnu') if build_win64 else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-unknown-linux-gnu') if build_linux_x86_64 else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'aarch64-unknown-linux-gnu') if build_linux_aarch64 else None,
      lambda: run_within_cargo_android_arm64_ndk_env(
        lambda: c('rustup', 'run', 'nightly', 'cargo', 'build', '--release', '--target', 'aarch64-linux-android', '-Zbuild-std')
      ) if build_android else None,
    ),
    lambda: assemble_in_win64(
      j('app-subprograms', 'server-webgui', 'target', 'x86_64-pc-windows-gnu', 'release', 'server-webgui.exe'),
      'server-webgui.exe'
    ),
    lambda: assemble_in_linux_x86_64(
      j('app-subprograms', 'server-webgui', 'target', 'x86_64-unknown-linux-gnu', 'release', 'server-webgui'),
      'server-webgui'
    ),
    lambda: assemble_in_linux_aarch64(
      j('app-subprograms', 'server-webgui', 'target', 'aarch64-unknown-linux-gnu', 'release', 'server-webgui'),
      'server-webgui'
    ),
    lambda: assemble_in_android(
      j('app-subprograms', 'server-webgui', 'target', 'aarch64-linux-android', 'release', 'server-webgui'),
      j('raw', 'server_webgui')
    ),
  )


  # TODO hunt down build failure which showed up on all targets after modifying tools.py to add aarch64 tools to PATH
  silenced_task(
    'Building desktop-cli',
    force_code_rebuilds_conditional_touch(inputs(
      j('app-subprograms', 'desktop-cli', 'src'),
      j('app-subprograms', 'desktop-cli', 'Cargo.toml')
    )),
    outputs(
      j('out', 'linux_x86_64', 'desktop-cli'),
      j('out', 'linux_aarch64', 'desktop-cli'),
      j('out', 'win64', 'desktop-cli.exe'),
    ),
    lambda: within(
      j('app-subprograms', 'desktop-cli'),
      # Build standalone cli exe shell
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-pc-windows-gnu') if build_win64 else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'x86_64-unknown-linux-gnu') if build_linux_x86_64 else None,
      lambda: c('rustup', 'run', 'stable', 'cargo', 'build', '--release', '--target', 'aarch64-unknown-linux-gnu') if build_linux_aarch64 else None,
    ),
    lambda: assemble_in_win64(
      j('app-subprograms', 'desktop-cli', 'target', 'x86_64-pc-windows-gnu', 'release', 'desktop-cli.exe'),
      'desktop-cli.exe'
    ),
    lambda: assemble_in_linux_x86_64(
      j('app-subprograms', 'desktop-cli', 'target', 'x86_64-unknown-linux-gnu', 'release', 'desktop-cli'),
      'desktop-cli'
    ),
    lambda: assemble_in_linux_aarch64(
      j('app-subprograms', 'desktop-cli', 'target', 'aarch64-unknown-linux-gnu', 'release', 'desktop-cli'),
      'desktop-cli'
    ),
  )


  silenced_task(
    'Building desktop-mainwindow',
    force_code_rebuilds_conditional_touch(inputs(
      j('app-subprograms', 'desktop-mainwindow', 'DesktopMainWindow.csproj'),
      j('app-subprograms', 'desktop-mainwindow', 'Program.cs'),
      j(r, 'misc-res', 'icon.png'),
    )),
    outputs(
      j('out', 'linux_x86_64', 'desktop-mainwindow'),
      j('out', 'linux_aarch64', 'desktop-mainwindow'),
      j('out', 'win64', 'desktop-mainwindow'),
    ),
    lambda: within(
      j('app-subprograms', 'desktop-mainwindow'),
      # Copy the icon from misc-res into the .gitignore'd file www/icon.png
      lambda: cp(j(r, 'misc-res', 'icon.png'), j('www', 'icon.png')),
      # Run the usual dotnet builds
      lambda: c('dotnet', 'publish', '-c', 'Release', '-r', 'win10-x64') if build_win64 else None,
      lambda: c('dotnet', 'publish', '-c', 'Release', '-r', 'linux-x64') if build_linux_x86_64 else None,
      lambda: c('dotnet', 'publish', '-c', 'Release', '-r', 'linux-arm64') if build_linux_aarch64 else None,
    ),
    lambda: assemble_in_win64(
      j('app-subprograms', 'desktop-mainwindow', 'bin', 'Release', 'net5.0', 'win10-x64', 'publish'),
      'desktop-mainwindow'
    ),
    lambda: assemble_in_linux_x86_64(
      j('app-subprograms', 'desktop-mainwindow', 'bin', 'Release', 'net5.0', 'linux-x64', 'publish'),
      'desktop-mainwindow'
    ),
    lambda: assemble_in_linux_aarch64(
      j('app-subprograms', 'desktop-mainwindow', 'bin', 'Release', 'net5.0', 'linux-arm64', 'publish'),
      'desktop-mainwindow'
    ),
  )


  silenced_task(
    'Building app-kernel-android (loci.apk)',
    force_code_rebuilds_conditional_touch(inputs(
      j('app-kernel-android', 'src'), j('app-kernel-android', 'build.gradle')
    )),
    outputs(
      j('out', 'android', 'loci.apk'),
    ),
    lambda: silent_rm(j('out', 'android', 'loci.apk')) if build_android else None,
    lambda: within(
      j('app-kernel-android'),
      lambda: silent_rm(j('build', 'outputs', 'apk', 'debug', 'loci-debug.apk')) if build_android else None,
      lambda: c('gradle', 'assembleDebug') if build_android else None,
    ),
    # TODO assemble android deployment-ready stuff
    lambda: assemble_in_android(
      j('app-kernel-android', 'build', 'outputs', 'apk', 'debug', 'loci-debug.apk'),
      'loci.apk'
    ),
  )


  # Finally assemble a web www/ directory containing win64/linux64/android distributables
  if not flag_set('hostonly'):
    build_www(build_win64, build_linux_x86_64, build_linux_aarch64, build_android, not 'nobrowser' in args)

def force_code_rebuilds_conditional_touch(inputs):
  if flag_set('force_code_rebuilds'):
    for i in inputs:
      if os.path.isfile(i):
        pathlib.Path(i).touch()

  return inputs

def download_OSM_BPF_FILE():
  if 'OSM_BPF_FILE' in os.environ:
    print('Downloading planet-latest.osm.pbf (bbike.org) ', end='', flush=True)
    completed_file = os.environ['OSM_BPF_FILE']+'.completed'
    if os.path.exists(completed_file):
      print('SKIPPED (completion file exists: {})'.format(completed_file))
    else:
      parent_dir = os.path.dirname(os.environ['OSM_BPF_FILE'])
      if not os.path.exists(parent_dir):
        print('Cannot download OSM BPF file to non-existent directory, please make sure "{}" exists!'.format(parent_dir))
        return
      print('')
      start = time.time()
      c('curl',
        '-o', os.environ['OSM_BPF_FILE'], # Where the data is output
        '-L', '-O', '-C', '-',            # Continue flags
        'https://download.bbbike.org/osm/planet/planet-latest.osm.pbf'
      )
      pathlib.Path(completed_file).touch()
      end = time.time()
      duration_s = round(end - start, 2)
      print('Download completed in {}s'.format(duration_s))
  else:
    print('OSM_BPF_FILE not set, skipping download.')

def create_selfsigned_ssl_certs():
  ssl_cert_path = j('out', 'ssl', 'cert.pem')
  ssl_key_path = j('out', 'ssl', 'key.pem')
  if shutil.which('openssl') and (not e(ssl_cert_path) or not e(ssl_key_path)):
    print('Generating self-signed SSL certificate for testing')
    if not e(j('out', 'ssl')):
      os.makedirs(j('out', 'ssl'))
    subprocess.run([
      'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
        '-nodes', # No DES encryption
        '-keyout', ssl_key_path,
        '-out', ssl_cert_path,
        '-days', '30',
        '-subj', '/C=US/ST=Virginia/L=Spotsylvania/O=NA/OU=NA/CN=localhost',
        # Add alt name for HOSTNAME.local (used by linux/mac/windows)
        '-addext', 'subjectAltName = DNS:{}.local'.format(platform.node()),
        '-addext', 'certificatePolicies = 1.2.3.4',
    ])

  if e(ssl_cert_path) and e(ssl_key_path):
    ssl_cert_path = os.path.abspath(ssl_cert_path)
    ssl_key_path = os.path.abspath(ssl_key_path)
    print('Assigning LOCI_SSL_CERT={} and LOCI_SSL_KEY={}'.format(ssl_cert_path, ssl_key_path))
    os.environ['LOCI_SSL_CERT'] = ssl_cert_path
    os.environ['LOCI_SSL_KEY'] = ssl_key_path

def build_www(build_win64, build_linux_x86_64, build_linux_aarch64, build_android, open_browser):
  print('Building www/ directory...')
  
  if not e(j('out', 'www')):
    os.makedirs(j('out', 'www'))
  
  if build_win64:
    if get_newest_file_mtime(j('out', 'win64')) > get_newest_file_mtime(j('out', 'www', 'win64.zip')):
      shutil.make_archive(j('out', 'www', 'win64'), 'zip', j('out', 'win64'))

  if build_linux_x86_64:
    if get_newest_file_mtime(j('out', 'linux_x86_64')) > get_newest_file_mtime(j('out', 'www', 'linux_x86_64.tar.gz')):
      shutil.make_archive(j('out', 'www', 'linux_x86_64'), 'gztar', j('out', 'linux_x86_64'))

  if build_linux_aarch64:
    if get_newest_file_mtime(j('out', 'linux_aarch64')) > get_newest_file_mtime(j('out', 'www', 'linux_aarch64.tar.gz')):
      shutil.make_archive(j('out', 'www', 'linux_aarch64'), 'gztar', j('out', 'linux_aarch64'))

  if build_android:
    if get_newest_file_mtime(j('out', 'android', 'loci.apk')) > get_newest_file_mtime(j('out', 'www', 'loci.apk')):
      assemble_in_www(j('out', 'android', 'loci.apk'), 'loci.apk')

  # Finally presentation graphics
  cp(j('misc-res', 'windows_icon.png'), j('out', 'www', 'windows_icon.png'))
  cp(j('misc-res', 'linux_icon.png'),   j('out', 'www', 'linux_icon.png'))
  cp(j('misc-res', 'android_icon.png'), j('out', 'www', 'android_icon.png'))

  # Instead of building index.html, we let webpage_update_tool.py do that.
  # This task only assembles distributable archives (.zip, .tar.gz, and .apk files)
