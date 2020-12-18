
# Loci

`loci` and `loci.exe` are stand-alone executables
designed to perform all the functions that `locorum.exe` can perform.

This iteration of Locorum differs significantly in design and goals:

# Goals

 - single executable file deployment (no install step, very few dependencies (only things like `kernel.dll` and `libc`))
 - heavy use of polling and async io as a replacement for threads + blocking io
 - ability to deploy anything we can fit in a .zip directory as a sub-process

# Design

 - `loci.exe` is executed
 - determine app data directory (`%AppData%` on windows, `$HOME/.loci/` on linux)
 - T1: idemepotent extraction of embedded .zip directories to app data directory
  - T1.a as .zip files are extracted, execute sub-processes when done. Store sub-processes in an array and
    watch + restart them if they die.
 - T2: webserver on port ABC (where ABC is configurable w/ env var)
  - webserver serves a relatively static UI with a websocket for server comms
 - T3: HTML webview UI, with OS-specific tuning (eg win10 titlebar color changes and icons)

# Dependencies

`build.py` needs python 3.6+

cargo toolchains used:

```bash
rustup toolchain install stable-x86_64-pc-windows-gnu
rustup target add x86_64-pc-windows-gnu

rustup toolchain install stable-x86_64-unknown-linux-gnu
rustup target add x86_64-unknown-linux-gnu
```

You will need `gcc`, `git`, `make`, and `cmake` on your $PATH to build 3rd-party code
like the dumo1090.exe program.

Windows users will need `Cygwin` to build the `dump1090.exe` program as well, because 
dumo1090 uses `sys/ioctl.h`.

Linux users will need 'libusb-1.0-0-dev' (or sys equivalent) to build `dump1090`.

When cross-compiling on modern filesystems that respect case sensitivity you may need to find
the header file `windows.h` and symlink it to `Windows.h`. The `runas` crate in particular has only
ever been tested on case-insensitive filesystems. The Arch one-liner is:

```bash
sudo ln -s /usr/x86_64-w64-mingw32/include/windows.h /usr/x86_64-w64-mingw32/include/Windows.h
```



# Building

```bash
python build.py
```

# Running

```bash
python build.py run
# or
LOCI_DISABLED_SUBPROGRAMS=dump1090 python build.py run-debug
LOCI_DISABLED_SUBPROGRAMS=dump1090,postgis,geoserver python build.py run-debug
```

# Testing

Tests are written in python in the `test` module located at `./test`.

Running tests is simple:

```bash
python -m test
```

Try to keep tests isolated to 1 feature per file, the goal is to
have 100% of our advertised behaviour (aka user-observable state changes)
be tested, which means the test codebase will sprawl. Let it sprawl.


# Hygiene

Loci has several hard rules that keep the project from becoming impossible to maintain:

 - No warnings on the default build
 - No failing unit/integration tests on the default build

If we get compile-time warnings or a failed test case, that
becomes the #1 priority item for today.

The entire build output of Loci should look like:

`python -m build`

```
Downloaded 3rdparty assets in 0.01s
Built linux eapp directory in 0.0s
linux64 eapp directory size: 172.0mb
   Compiling loci v0.1.0 (/j/proj/loci)
    Finished release [optimized] target(s) in 39.82s
Built linux in 40.04s
WARNING: Cannot cross-compile dump1090 for windows from a linux host.
Built windows eapp directory in 1.0s
   Compiling loci v0.1.0 (/j/proj/loci)
    Finished release [optimized] target(s) in 41.86s
Built windows in 42.04s
Source code: 53122.46kb
win64 eapp directory size: 228.63mb
```

# CI

At the moment the CI system is Github Actions. There are two
defined under `.github/workflows` which build and test release
binaries, then upload them to https://github.com/Jeffrey-P-McAteer/loci/releases

To trigger a release simply tag your commit beginning with a `v*` and push it:

```bash
git tag -m 'New features yay \o/' v0.0.12
git push --follow-tags
```

CI builds take about 25 minutes as of 2020-12-18.


# Project Unknowns

 - Do linux systems need `libusb-1.0` at runtime as well as compile-time?
 - Can we automate the 1 remaining step in windows rtl-sdr driver stuff?
 - Is OpenDDS's 3-hr compile time worth it for message integration? How will we track classified messages?


