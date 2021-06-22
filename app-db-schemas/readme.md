
# App DB Schemas

Each platform's `kernel` program will execute all `*.sql` files
in this directory before launching sub-programs. The name of the database
file is the same as the schema file; for example `ABC.sql` will result in
the database file `ABC.db` being created under `<app root>/db/ABC.db`.

Each database MUST avoid depending on unique identifiers from other databases.
If 2 pieces of data need to be tracked together (eg Nodes and node properties) they
MUST be put into the same database and a foreign key constraint MUST be used to avoid
leaking data when the primary record is deleted.

## `gui` database

The `gui` database holds the following tables:

 - `sessions`
     - The "sessions" table holds one entry for each webview connected to
       the server.
       When the window/browser tab is closed the associated row will be dropped,
       causing a cascade removal of entries from the remaining gui tables.

 - `menu`
     - The "menu" table is written to by subprograms
       and read by server-webgui to create the b-tree of
       menu items at the top of the GUI.

 - `left_tabs`
     - The "left_tabs" table is written to by subprograms
       and read by server-webgui to create left tab buttons
       at the left of the GUI.

 - `right_tabs`
     - The "right_tabs" table is written to by subprograms
       and read by server-webgui to create right tab buttons
       at the right of the GUI.

 - `action_buttons`
     - The "action_buttons" table is written to by subprograms
       and read by server-webgui to create buttons on the rightmost edge
       of the GUI.

 - `notifications`
     - The "notifications" table is written to by subprograms
       and read by server-webgui to display alerts to the user.
       The alerts will ALWAYS have a drop-down on the primary app window
       and they may POSSIBLY also be sent to the OS via a native notification API (phones & browsers provide these)

## `system` database

The `system` database holds the following tables:

 - `processes`
    - The "processes" table is written to by the kernel when it executes a sub-process.
      This should be used by subprograms to check if another process they depend on is running.

 - `launch_req`
    - The "launch_req" table is polled by the kernel and it
      reads new rows and executes processes based on the row data.
      After launching the process and adding a row to the "processes" table
      the kernel will delete the corresponding row from "launch_req".
      Subprograms may use this to request that other programs are executed
      without being attached as a child.

 - `properties`
     - The "properties" table holds key-value data appropriate for _all_
       subprograms to want to read or write.
       The app-lib functions get_prop() and set_prop() read and write to this table.


## `translations` database

The `translations` database holds the following tables:

 - `tkeys`
    - The "tkeys" table is a global unique list of word and phrase keys
      all subprograms MUST use when displaying text to the user.
      Upon startup the app-kernel will insert keys from JSON files sourced
      from the app-data-tkeys/ directory.

 - `translations`
    - the "translations" table contains language-specific values associated with
      each registered tkey. When displaying text to the user subprograms MUST query this
      table and use the value given as the text displayed to the user.
      Upon startup the app-kernel will insert values from JSON files sourced
      from the app-data-tkeys/ directory.

To assist builtin subprograms with tracking common translations, the `app-data-tkeys/` directory holds
pre-defined translations that all `app-kernel` programs will write into the `tkeys` and `translations` tables
before starting subprograms. See the readme in `app-data-tkeys/` for details on the format and the `converter.py` tool
for use creating an amalgamated `.csv` file with all translations.




