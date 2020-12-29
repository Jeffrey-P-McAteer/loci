
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


-- The app_major_ui table describes 4 major functional areas of the Loci UI:
--  * Top menu bar (as a tree w/ ordering)
--  * Left tabs (as an ordered list)
--  * Right tabs (as an ordered list)
--  * Action buttons (as an ordered list)
--
-- Plugins use this table to extend the Loci UI.
--
CREATE TABLE IF NOT EXISTS app_major_ui (
  -- The "type" must be one of 'top', 'left', 'right', or 'action',
  -- which defined where this UI component goes and how it behaves.
  type TEXT CHECK( type IN ('top', 'left', 'right', 'action') ) NOT NULL DEFAULT 'right',
  
  -- For 'top', this is the menu item name.
  -- For 'left' and 'right', this is the tab title name.
  -- For 'action', this is the button text or the text directly below the icon if an icon is defined.
  -- This should be a translation key, aka lowercase with no space chars.
  display_name_tkey TEXT
    CHECK(
        lower(display_name_tkey) == display_name_tkey AND
        trim(replace(replace(display_name_tkey, '\t', ''), ' ', '')) == display_name_tkey
    )
    NOT NULL,

  -- If type == left/right and this is set, the tab will load an <iframe src="tab_content_url">
  tab_content_url TEXT,

  -- If type == left/right and a program wants to switch to ie "map" or "chat",
  -- tab_focus_switch_tags will be checked and the first tab matching that will be used to
  -- change focus. Tags ought to be comma-separated, like "map,map5,a-map-of-egypt".
  -- Tags are not subject to translation rules, they are only used for code to automate focus switching.
  tab_focus_switch_tags TEXT NOT NULL DEFAULT '',

  -- If type == top, this is a case-and-whitespace-insensitive "/"-seperated list of translation-key menu parents
  -- which this item is placed under. Eg: "file/submenu-a/" would result in "file" being translated,
  -- "submenu-a" being translated, and then under those 2 menus an entry "display_name_tkey" being translated and displayed.
  top_menu_path TEXT 
    CHECK(
        lower(top_menu_path) == top_menu_path AND
        trim(replace(replace(top_menu_path, '\t', ''), ' ', '')) == top_menu_path
    ),

  -- if type == top/action and this is set, upon being clicked this will be
  -- evaluated as javascript using window.eval(button_action).
  button_action TEXT,
  -- if type == action and this is set, this graphic will be placed in an
  -- <img src="button_icon_url"> element with the width constrained and the height set to auto.
  button_icon_url TEXT,

  -- integer between 0 and 1000 inclusive, where 0 sorts to the beginning/left-most UI
  -- area and 1000 sorts to the bottom.
  ui_order INTEGER CHECK( ui_order >= 0 AND ui_order <= 1000 ) NOT NULL default 500

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
  -- Some sources may use a relative identifier because the source does not provide one.
  -- They are listed below:
  --   usb_gps: "USB_GPS_SELF"
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
