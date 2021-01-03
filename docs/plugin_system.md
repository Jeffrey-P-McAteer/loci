
# Loci Plugin System

The `eapp` directory has the following child directories which `loci` will
scan for sub-programs which are executed:

NB: The CWD of all spawned child processes will be the `eapp` directory.

 - `eapp/db-init/DB_FILE_NAME.*.sql`
    - files under `eapp/db-init/` MUST contain at least 1 character and a `.` character and end in `.sql`
    - `DB_FILE_NAME` will correspond to the db file under `eapp/db` which the SQL script will be executed against
    - All sql scripts will run before `eapp/prog-*` programs, and they will be run as the user who executed `loci`.

 - `eapp/prog-user/*.[exe,py,pyz,jar]`
    - Programs are run as the user who initially executed `loci`
    - Python files are run using an embedded python interpreter. If your program requires 3rd-party libraries,
      package it as a `.pyz` file with the external libraries inside the `.pyz` file.
    - Jar files are run using an embedded java runtime. If your program requires 3rd-party libraries,
      package the external libraries inside the `.jar` file.

- `eapp/prog-admin/*.[exe,py,pyz,jar]`
    - Programs are run as admin w/ the same launch sequence as those in `eapp/prog-user/`.


NB: Programs will be restarted within 5s if they exit with a non-zero status. Programs exiting with `0` will not be restarted.

NB: Several runtimes will be added within `eapp/` and their `bin` directories will reside on the `$PATH`
when `eapp/prog-admin/` and `eapp/prog-user` programs execute. This means you may assume the following binaries
are available:

 - `java` (latest, probably v14)
 - `python` (latest, probably 3.8)

Python programs may also assume the `loci` module has been added to `$PYTHONPATH`. (eg `import loci`)

Java programs may also assume the `loci` module has been added to `$CLASSPATH`. (eg `import loci;`)

The following environment variables will be defined:

 - `LOCI_EAPP_DIR` absolute path to `eapp/` directory

 - `LOCI_DB_DIR` absolute path to `db/` directory, under which database files are stored.
    If your plugin ships a script `eapp/db-init/locations.foranything.sql` then you may assume the
    db file `$LOCI_DB_DIR/locations.db` exists and contains the schema defined by all `eapp/db-init/locations.*.sql` scripts.

 - `LOCI_DISABLED_SUBPROGRAMS` Subprograms are encouraged to use a unique short name (eg `usb-gps`) and check if it exists in
   this environment variable at startup. If it does, exit cleanly (`return 0`). This supports headless testing and debugging.

 - `LOCI_NO_GUI` If this environment variable is set GUI subprograms should not run. This supports headless testing and debugging.

# Adding proprietary/classified systems to `loci`

To add programs to the above directories and produce a single executable,
write a python script that performs the following tasks:

 - Knows where your proprietary/classified binaries/deliverables are
 - can copy proprietary/classified binaries/deliverables into `$LOCI_EAPP_DIR/db-init`, `$LOCI_EAPP_DIR/prog-admin`, and `$LOCI_EAPP_DIR/prog-user`.
 - exits with return code `0`.

Then when building `loci` pass it as an argument, eg:

```bash
python -m build release /path/to/secrets.py /another-classified/system/build.py
```

After `loci` builds it's standard embedded subprograms it will execute each python script
in turn, then embed the contents of `$LOCI_EAPP_DIR` into `loci` such that it will be extracted
and run on a user's machine.


# The `loci` python library

Python scripts are 

TODO

# The `loci` java library

TODO


