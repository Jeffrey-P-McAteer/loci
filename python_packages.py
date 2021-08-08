
import subprocess
import sys
import importlib
import traceback

# This holds _all_ known 3rd-party python libs we depend on
# in btool, tests, and docs.
# Format is ("module", "module_pkg_name")
required_packages = [
  ('requests', 'requests'),
  ('websocket', 'websocket-client'),
  ('py7zr', 'py7zr'),
  ('PIL', 'Pillow'),
  ('matplotlib', 'matplotlib')
]

subprocess.run([sys.executable, '-m', 'ensurepip', '--default-pip'], check=True)

for module, module_pkg_name in required_packages:
  try:
    importlib.import_module(module)
  except:
    traceback.print_exc()
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', module_pkg_name], check=True)


