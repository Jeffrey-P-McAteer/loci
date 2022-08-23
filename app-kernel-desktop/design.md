
# App-Kernel Design

This program is designed to run `loci` on desktop systems.
It assumes the user executing it is a regular desktop account,
possibly with admin access (In the `Administrators` group for windows, in `/etc/sudoers` for linux).

This program starts by asking the OS for some information:

 - Where should apps store their data?
    - We set the environment variable `LOCI_DATA_DIR` for sub-programs to use when looking up database and shared-memory locations
 - Where is my executable?
    - We set the environment variable `LOCI_INSTALL_DIR` for sub-programs to use to call other sub-programs and read their own resource files
    - We move to this directory quickly so we can use relative paths to refer to sub-programs.

This program does not assume it executes standalone; it must be run within the build `out/*` directory as constructed
by `btool` so that sub-programs can be found and executed.


# Sub-Program Environment Variable Overview

The following environment variables will be set for sub-programs, and they should be used
so all programs can agree on where data is stored to pass messages and program state around.

| Variable            | Description |
| ------------------- | ----------- |
| `LOCI_DATA_DIR`     | where database + shared memory files live |
| `LOCI_INSTALL_DIR`  | assumed read-only directory of all built sub-programs, initially constructed by `btool` under `out/*` |




