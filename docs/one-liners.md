
# One-Liners

There are a number of common routines new developers will
want to perform, this page has examples of them all.

## Build a release

```
python -m build
# produces target/x86_64-pc-windows-gnu/release/loci.exe
# and target/x86_64-unknown-linux-gnu/release/loci.

# If the eapp files look like they aren't being embedded
# in the .exe we have a flag to force the tarball to be re-linked:
python -m build hard-rebuild

```

Full releases may only be done on their host systems; eg `loci.exe` built on a linux
system will lack some RTL-SDR programs and `loci` built on a windows system will lack
linux RTL-SDR programs.

There are long-term plans to have full cross-compilation with all 3rd-party software,
but at the moment only the core program may be cross-compiled.

## Run a release

```
python -m build run
# For a debug build:
python -m build run-debug
```

## Update landing page/docs

```
# Preview changes locally:
python -m docs.build open
# Push changes to github pages branch:
python -m docs.build publish
```

## Release a new version

```
# For new major and minor versions:
git tag -m "New release notes" v1.2.3
git push --follow-tags
# For a patch version (auto-increments last digit and pushes)
python release.py
```

## Generate a customer license

This step requires an authorized GPG key installed on your OS.
Unauthorized GPG keys will still create licenses but `loci.exe`
will not respect them and treat them as if there were no license at all.

```
python license.py
```


