
# Development Environment setup + guide to `dev-env.conf`

## `dev-env.conf`

`dev-env.conf` contains key=value environment variables assigned when `btool` and other python scripts (`docs`, `tests`, etc.).

This allows developers to put large chunks of data on different drives, and to record things like
service usernams and passwords which ought never be committed to any repository.

Below is an example `dev-env.conf` file. If you need passwords speak to a dev team member, shared
resources will be shared and personal resources should be explained to you so you can deploy/manage them
yourself.

IMPORTANT: `dev-env.conf` is NOT SAFE TO SHARE across different machines or OSes, DO NOT COMMIT THIS FILE ANYPLACE.

```
# This is so large we want to let devs place it anywhere (usually on an external SSD)
OSM_BPF_FILE=/mnt/scratch/planet-latest.osm.pbf
VM_IMAGES_DIR=/mnt/scratch/loci_vms/

CDN_USER=
CDN_PASS=

```

## Arch Linux Prerequisites

```bash
sudo pacman -S base-devel python python-pip mingw-w64-gcc mingw-w64-binutils
python -m pip install --user requests websocket py7zr PIL matplotlib
# Optional, used for performance enhancements:
sudo pacman -S rsync sshpass
```

## Ubuntu Linux Prerequisites

```bash
sudo apt install -y build-essential python3 python3-pip gcc-mingw-w64
python -m pip install --user requests websocket py7zr PIL matplotlib
```

## Windows 10/11 Prerequisites

Install SDL2 and use the Ubuntu or Arch images to build; windows-hosted compilers are sufficiently difficult
to install, manage, and use correctly that they are not worth the huge amount
of work it would take to test and document their use. During the XP era microsoft relied
on GNU tooling because their compiler could no longer compile itself or windows, we can rely on GNU as well.





