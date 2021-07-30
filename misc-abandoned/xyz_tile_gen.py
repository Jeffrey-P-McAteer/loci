
# Assumes dev-env.conf exists and most base-dev tools
# exist (make, autoconf, a compiler, git).
# In addition mapnik requires boost headers installed.
# We also use pyrosm to read the compressed OSM data in pbf format.


import os
import sys
import subprocess
import pathlib

# Hope we hit the directory holding btool/__init__.py
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))

from btool.utils import set_env_from_dev_env_conf
from btool.utils import dl_archive_to

# Import 3rd-party libs

def setup_dependencies():
  # See https://github.com/systemed/tilemaker,
  # dev dependencies are documented at: https://github.com/systemed/tilemaker/blob/master/docs/INSTALL.md
  tilemaker_dir = os.path.join('build', 'tilemaker')
  if not os.path.exists(tilemaker_dir):
    dl_archive_to(
      'https://github.com/systemed/tilemaker/releases/download/v2.0.0/tilemaker-ubuntu-16.04.zip',
      tilemaker_dir
    )

  tilemaker_exe = os.path.join(tilemaker_dir, 'build', 'tilemaker')
  subprocess.run([
    'chmod', '+x', tilemaker_exe,
  ])

  os.environ['PATH'] = os.path.abspath(os.path.join(
    tilemaker_dir, 'build',
  )) + os.pathsep + os.environ['PATH']



  osmium_tool_dir = os.path.join('build', 'osmium-tool')
  libosmium_dir = os.path.join('build', 'libosmium')
  protozero_dir = os.path.join('build', 'protozero')
  osmium_build_dir = os.path.join(osmium_tool_dir, 'build')
  if not os.path.exists(osmium_tool_dir):
    if not os.path.exists(libosmium_dir):
      subprocess.run([ # Because https://github.com/osmcode/osmium-tool/issues/52#issuecomment-311893097 ???
        'git', 'clone', '--depth', '1', '--branch', 'v2.17.0', 'https://github.com/osmcode/libosmium.git', libosmium_dir
      ], check=True)

    if not os.path.exists(protozero_dir):
      subprocess.run([ # Because https://github.com/osmcode/osmium-tool/issues/85
        'git', 'clone', '--depth', '1', '--branch', 'v1.7.0', 'https://github.com/mapbox/protozero.git', protozero_dir
      ], check=True)

    subprocess.run([
      'git', 'clone', '--depth', '1', '--branch', 'v1.13.1', 'https://github.com/osmcode/osmium-tool.git', osmium_tool_dir
    ], check=True)

    if not os.path.exists(osmium_build_dir):
      os.makedirs(osmium_build_dir)

    subprocess.run([
      'cmake', '..'
    ], check=True, cwd=osmium_build_dir)

    subprocess.run([
      'make'
    ], check=True, cwd=osmium_build_dir)


  os.environ['PATH'] = os.path.abspath(os.path.join(
    osmium_tool_dir, 'src',
  )) + os.pathsep + os.path.abspath(os.path.join(
    osmium_build_dir,
  )) + os.pathsep + os.environ['PATH']


def main(args=sys.argv):

  if not os.path.exists('dev-env.conf') or not os.path.exists('out'):
    print('Error: Must run script from repo root, like "python misc-abandoned/xyz_tile_gen.py" and ensure dev-env.conf and ./out/ exists.')
    return

  set_env_from_dev_env_conf('dev-env.conf')

  if not 'OSM_BPF_FILE' in os.environ:
    print('Error: OSM_BPF_FILE not set in dev-env.conf!')
    return

  setup_dependencies()

  osm_bpf_file = os.environ['OSM_BPF_FILE']
  output_xyz_tiles_dir = os.path.abspath(os.path.join('out', 'osm-xyz-tiles') if len(args) < 2 else args[1])

  print('Converting {} into a directory of tiles {}'.format(osm_bpf_file, output_xyz_tiles_dir))

  if not os.path.exists(output_xyz_tiles_dir):
    os.makedirs(output_xyz_tiles_dir)

  # TODO arbitrary tiles + resolution depths

  tile_bbox = '38.99,-77.18,38.78,-76.92'
  tile_fname_frag = '_'.join([x for x in tile_bbox.split(',')]).replace('-', '_').replace('.', '_')
  tile_osm_pbf = os.path.join(output_xyz_tiles_dir, '{}.osm.pbf'.format(tile_fname_frag))
  tile_geojson = os.path.join(output_xyz_tiles_dir, '{}.geojson'.format(tile_fname_frag))
  tile_mbtiles = os.path.join(output_xyz_tiles_dir, '{}.mbtiles'.format(tile_fname_frag))

  if not os.path.exists(tile_osm_pbf):
    print('Using osmium to extract a rectangle {}'.format(tile_bbox))
    # See https://osmcode.org/osmium-tool/manual.html
    subprocess.run([
      'osmium', 'extract', '--bbox={}'.format(tile_bbox), '--set-bounds', '--strategy=complete_ways', osm_bpf_file, '--output', tile_osm_pbf,
    ], check=True)
    # kept_tags = '''
    #   r/type=multipolygon,boundary
    #   w/highway
    #   wr/natural=wood wr/landuse=forest
    # '''.strip().split()
    # print('Using osmium to remove all data except: {}'.format(kept_tags))
    # subprocess.run([
    #   'osmium', 'tags-filter', '--overwrite', tile_osm_pbf, '--output', tile_osm_pbf, *kept_tags,
    # ], check=True)

  if not os.path.exists(tile_geojson):
    print('Using osmium to convert to .geojson: {}'.format(tile_geojson))
    subprocess.run([
      'osmium', 'export', '--progress', tile_osm_pbf, '-o', tile_geojson,
    ], check=True)

  if not os.path.exists(tile_mbtiles):
    print('Using tilemaker to convert to .mbtiles format')
    subprocess.run([
      'tilemaker', '--input', tile_osm_pbf, '--output', tile_mbtiles,
    ], check=True)

  print('Done: {}'.format(tile_mbtiles))






if __name__ == '__main__':
  main()


