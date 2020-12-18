
-- This file is run in db::init_data_schema.
-- It is responsible for creating tables and indexes if they do not exist.

BEGIN;

-- app_events are soft notifications that some event has occurred.
-- A good example would be "all-subprograms-spawned".
-- The `ts` parameter is the UTC time in epoch milliseconds when the event occurred,
-- the `invalid_after_ts` is the duration in milliseconds when this event should be ignored.
-- Values near 8 seconds (8000) should fit most scenarios, but for slower-moving events larger timeouts should be
-- used to allow for longer polling periods.
-- `name` must be a unique string, and `data` may be any payload containing event details (JSON, BARE, CBOR, etc.).
-- 
CREATE TABLE IF NOT EXISTS app_events (
  ts INTEGER NOT NULL default (strftime('%s','now') * 1000.0),
  invalid_after_ts INTEGER NOT NULL default 8000,
  name TEXT NOT NULL,
  data BLOB
);

-- pos_reps holds a rolling list of position reports.
-- 
CREATE TABLE IF NOT EXISTS pos_reps (
  
  uniq_row_id INTEGER PRIMARY KEY AUTOINCREMENT,

  -- UTC ms when this was created; may be parsed from remote message.
  ts INTEGER NOT NULL default (strftime('%s','now') * 1000.0),

  lat REAL NOT NULL,
  lon REAL NOT NULL,
  
  -- The identifier has no fixed format; it is whatever the data source says the posrep is about
  id TEXT NOT NULL,
  
  -- if a posrep goes through multiple sources, separate them with commas.
  -- eg "VIDL,IP,192.168.3.99"
  -- This field is as a hint only and readers should be as fuzzy as possible.
  src_tags TEXT NOT NULL default "unk"

);

COMMIT;

-- map_points holds every item which has a name and at least one position report.
-- additional data may be stored as JSON, either using a language-specific JSON parser or by
-- taking advantage of the JSON1 sqlite extension (https://www.sqlite.org/json1.html)
-- 
--   CREATE TABLE IF NOT EXISTS map_points (
--     display_name TEXT NOT NULL,
--     display_short_name TEXT NOT NULL,
--   
--     FOREIGN KEY(pos_rep) REFERENCES pos_reps(uniq_row_id)
--   
--   );


-- COMMIT;
