
# Loci

Rapid rebuild of legacy app using modern engineering tools and design to eliminate scope creep
while providing the ability to staple on new features forever.

To setup a development environment, read [dev_env.md](dev_env.md).

# Build + Run

```bash
# Build everything, see results in ./out/<target>/
python -m btool

# Build + run
python -m btool run

# Build Android and push to device using adb
python -m btool android run

# Debug a failing build process
python -m btool debug

# Get a shell w/ all the 3rd-party SDKs and compiler added to PATH:
python -m btool shell
```

# Generate Licenses

```bash
# Dependencies
python -m pip install --user python-gnupg
python -m pip install --user HumanTime
# License Tool writes to ./out/issued_licenses/*.txt
python -m license_tool
```

# Outputs

See `./out/`

# Testing

```bash
python -m tests
```

# Generate Documentation

```bash
python -m docs
```

# Project Management Reports

```bash
# High-level reports using a "features.json" file in all sub-projects
python -m feature_tracking_tool
python -m feature_tracking_tool todo
python -m feature_tracking_tool began
python -m feature_tracking_tool completed
python -m feature_tracking_tool next

# Low-level reports from parsing source code comments directly
python -m code_query_tool
python -m code_query_tool --todos
python -m code_query_tool --list-all-env-vars
```

# Platform notes

We assume tcp port `7010` is free on all OSes for use serving the web UI.


## Android

We target the `android-28` runtime assuming an `aarch64` 64-bit processor.

Check your phone's processor details with `adb shell cat /proc/cpuinfo`.


## Windows

Assume 64-bit x86

## Linux (Desktop)

Assume 64-bit x86; TODO list web libraries & graphics requirements

## Linux (Server)

Assume 64-bit x86


# Overall Repo Design

`app-*/` contains code which is compiled + assempled into the output directory containing the application
and all resource files and subprograms.

`app-kernel-desktop/` is the desktop app responsible for spawning subprograms and restarting anything that fails.

`app-kernel-android/` builds the .apk file shipped to android devices, and it sets up environments for subprograms to execute on an android device.

`btool/` is the build tool, responsible for downloading SDKs (android SDK, java, gradle, cargo, etc.),
executing builds, and assembling subprogram build outputs into the `./out/<target>/` directory.

`license_tool.py` uses your existing GPG key to create license files. Add your public key to `app-lib/src/license.rs` under `LICENSE_ISSUERS_KEYS` to add a new authority which can generate valid loci license files.

`tests/` is a test tool, it is responsible for running all unit tests in subprograms and executing a few integration tests using
desktop programs build under `./out/<host target>/`

`docs/` is a documentation-generating tool, it is responsible for running all documentation generation in subprograms and writing an `index.html` under `./out/docs/index.html` which points to the documentation of every subprogram.

`code_query_tool.py` is designed to query the entire codebase for regular expressions and several pre-defined searched which are useful for project management.

`feature_tracking_tool.py` reads "features.json" in all subprograms and lets you filter the feature report.


# Misc oneliners

Common things used during development but not important enough to factor into a script someplace:

```bash
# Build for host, override builtin www/ with src www, and only run server-side functions for debugging UI in a browser.
LOCI_WWW_OVERRIDE=$PWD/app-subprograms/server-webgui/www/ RUN_WITHOUT_GUI=1 python -m btool hostonly cleanrun


```

