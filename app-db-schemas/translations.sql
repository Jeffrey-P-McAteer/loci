

-- The "tkeys" table is a global unique list of word and phrase keys
-- all subprograms MUST use when displaying text to the user.
-- Upon startup the app-kernel will insert keys from JSON files sourced
-- from the app-data-tkeys/ directory.

CREATE TABLE IF NOT EXISTS tkeys (
  rowid INTEGER PRIMARY KEY,

  -- Unique key used by subprograms to request a phrase; NO WHITESPACE ALLOWED!
  tkey TEXT UNIQUE NOT NULL check(instr(tkey, ' ') == 0)
);

-- the "translations" table contains language-specific values associated with
-- each registered tkey. When displaying text to the user subprograms MUST query this
-- table and use the value given as the text displayed to the user.
-- Upon startup the app-kernel will insert values from JSON files sourced
-- from the app-data-tkeys/ directory.

CREATE TABLE IF NOT EXISTS translations (
  -- Implicit "rowid" column
  -- Reference to a unique tkeys row
  tkey INTEGER NOT NULL REFERENCES tkeys(rowid) ON DELETE CASCADE,
  -- Language code, eg "en" or "es" for english or spanish
  lang_code TEXT NOT NULL check(length(lang_code) >= 2 and length(lang_code) <= 3),
  -- tkey human-readable text for the given lang_code
  translated_text TEXT NOT NULL
);


