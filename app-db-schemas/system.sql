
-- The "processes" table is written to by the kernel when
-- it executes a sub-process.
-- This should be used by subprograms to check if another process
-- they depend on is running.

CREATE TABLE IF NOT EXISTS processes (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,
  exe_file TEXT NOT NULL,
  pid TEXT UNIQUE NOT NULL
);

-- The "launch_req" table is polled by the kernel and it
-- reads new rows and executes processes based on the row data.
-- After launching the process and adding a row to the "processes" table
-- the kernel will delete the corresponding row from "launch_req".
-- Subprograms may use this to request that other programs are executed
-- without being attached as a child.

CREATE TABLE IF NOT EXISTS launch_req (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,
  exe_file TEXT NOT NULL,
  cwd TEXT,          -- Working directory, defaults to app_root
  json_env TEXT,     -- eg {"DISPLAY": ":5"}
  json_args TEXT     -- eg ["a", "b", "c"]
);

-- The "properties" table holds key-value data appropriate for _all_
-- subprograms to want to read or write.
-- The app-lib functions get_prop() and set_prop() read and write to this table.

CREATE TABLE IF NOT EXISTS properties (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value TEXT NOT NULL
);




