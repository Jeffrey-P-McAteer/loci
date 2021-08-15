
-- The "sessions" table holds one entry for each webview connected to
-- the server.
-- When the window/browser tab is closed the associated row will be dropped,
-- causing a cascade removal of entries from the remaining gui tables.

CREATE TABLE IF NOT EXISTS sessions (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,
  
  -- This is the address & a unique number used to identify clients.
  -- Nonce begins as the client-side port of the websocket which GUI JS code uses
  -- to communicate with the rest of the application.
  -- The webserver will reap these values every 6 minutes. If a client disconnects and
  -- re-connects within those 6 minutes they may request the new connection be treated
  -- as the old one in terms of GUI state by presenting the previous IP+NONCE combination.
  -- For security reasons no currently connected WS session will be re-mapped if that sesson's IP+NONCE
  -- is used to request this new connection mapping.
  ip_addr_and_nonce TEXT UNIQUE NOT NULL

);

-- The "menu" table is written to by subprograms
-- and read by server-webgui to create the b-tree of
-- menu items at the top of the GUI.

CREATE TABLE IF NOT EXISTS menu (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,

  -- Used to differentiate between menus in a browser and menus in a desktop window
  session_id INTEGER NOT NULL REFERENCES sessions(rowid) ON DELETE CASCADE,

  -- eg "File>>Settings>>SettingX". All path fragments MUST be tkeys present in the translations table.
  -- The '>>' substring is used to separate menu tkey parents.
  menu_path TEXT UNIQUE NOT NULL,

  -- Used to sort menus appearing under the same parent, 0 is the top of the menu and 10_000 is the bottom.
  -- Duplicate weights within the same menu parent will be sorted according to rowid.
  weight INTEGER NOT NULL DEFAULT 5000,

  -- JS executed when the menu item is clicked/tapped.
  -- No events are generated for intermediate menu item clicks, only leaf menus!
  on_click_js TEXT NOT NULL
);


-- The "status_texts" table is written to by subprograms
-- and read by server-webgui to create a list of status messages
-- in the upper-right corner of the app.

CREATE TABLE IF NOT EXISTS status_texts (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,

  -- Used to differentiate between menus in a browser and menus in a desktop window
  session_id INTEGER NOT NULL REFERENCES sessions(rowid) ON DELETE CASCADE,

  -- value for text displayed. This is a RARE place where the gui WILL NOT TRANSLATE
  -- values placed into status_texts, under the assumption most will be numbers/letters/unicode symbols.
  title_value TEXT NOT NULL,

  -- 0 is the left-most menu item, 10_000 is the right-most menu item.
  -- LEAVE GAPS OF 100 FOR FUTURE MENU ITEMS, for example the left-most item _ought_ to be 1000
  -- so new code or 3rd-party programs can add something to the left of default menu items.
  weight INTEGER UNIQUE NOT NULL

);


-- The "left_tabs" table is written to by subprograms
-- and read by server-webgui to create left tab buttons
-- at the left of the GUI.

CREATE TABLE IF NOT EXISTS left_tabs (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,

  -- Used to differentiate between left tab in a browser and left tabs in a desktop window
  session_id INTEGER NOT NULL REFERENCES sessions(rowid) ON DELETE CASCADE,

  -- tkey for text displayed on the left side of the UI in tabs used to select different left tabs
  title_tkey TEXT NOT NULL,

  -- 0 is the top-most tab, 10_000 is the bottom-most tab.
  -- LEAVE GAPS OF 100 FOR FUTURE TABS.
  weight INTEGER UNIQUE NOT NULL,
  
  -- JS executed when the tab is clicked/tapped. Ideally this just hides/shows an <iframe>
  on_click_js TEXT NOT NULL,

  -- TRUE if tab is focused, otherwise FALSE
  is_focused INTEGER NOT NULL check(is_focused == TRUE or is_focused == FALSE),
  
  -- When not null, this is added as the 'style="css"' property of the title element.
  -- This may be used to change the background color of the tab.'
  css TEXT
);

-- The "right_tabs" table is written to by subprograms
-- and read by server-webgui to create right tab buttons
-- at the right of the GUI.

CREATE TABLE IF NOT EXISTS right_tabs (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,

  -- Differentiates right tabs across multiple browser windows
  session_id INTEGER NOT NULL REFERENCES sessions(rowid) ON DELETE CASCADE,

  -- tkey for text displayed on the top-right side of the UI in tabs used to select different right tabs
  title_tkey TEXT NOT NULL,

  -- 0 is the left-most tab, 10_000 is the right-most tab.
  -- Duplicate tab weights will be sorted according to rowid.
  weight INTEGER NOT NULL DEFAULT 5000,
  
  -- JS executed when the tab is clicked/tapped. Ideally this just hides/shows an <iframe>
  on_click_js TEXT NOT NULL,
  
  -- TRUE if tab is focused, otherwise FALSE
  is_focused INTEGER NOT NULL check(is_focused == TRUE or is_focused == FALSE),
  
  -- When not null, this is added as the 'style="css"' property of the title element.
  -- This may be used to change the background color of the tab.'
  css TEXT
);

-- The "action_buttons" table is written to by subprograms
-- and read by server-webgui to create buttons on the rightmost edge
-- of the GUI.

CREATE TABLE IF NOT EXISTS action_buttons (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,

  -- Differentiates action buttons on different browser sessions
  session_id INTEGER NOT NULL REFERENCES sessions(rowid) ON DELETE CASCADE,

  -- tkey for text displayed on the button when the user hovers over it OR displayed on the bottom
  -- of the button UI.
  title_tkey TEXT NOT NULL,

  -- 0 is the top-most button, 10_000 is the bottom-most button.
  -- LEAVE GAPS OF 100 FOR FUTURE BUTTONS.
  weight INTEGER UNIQUE NOT NULL,
  
  -- JS executed when the button is clicked/tapped.
  on_click_js TEXT NOT NULL,
  
  -- When not null, this is added as the 'style="css"' property of the button element.
  -- This may be used to change the background color or set an image for the button.
  css TEXT
);

-- The "notifications" table is written to by subprograms
-- and read by server-webgui to display alerts to the user.
-- The alerts will ALWAYS have a drop-down on the primary app window
-- and they may POSSIBLY also be sent to the OS via a native notification API (phones & browsers provide these)

CREATE TABLE IF NOT EXISTS notifications (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,

  -- Differentiates which browser session gets the notification
  session_id INTEGER NOT NULL REFERENCES sessions(rowid) ON DELETE CASCADE,

  -- Notification title tkey; not always displayed to user.
  title_tkey TEXT NOT NULL,
  -- Notification message tkey; always displayed to user.
  message_tkey TEXT NOT NULL,

  -- JS executed when the notification is clicked/tapped.
  -- Notification will ALWAYS be removed when clicked/tapped.
  on_click_js TEXT NOT NULL,

  -- Notification type hint; just an arbitrary string the frontend may
  -- or may not respect. Examples may be "large" to display a large notification,
  -- or "scrolling-bottom-wide" to display a scrolling notification along the bottom.
  -- We keep a huge amount of complexity from breaking out by having this option available.
  type_hint TEXT,

  -- When not null, this is added as the 'style="css"' property of the notification element.
  -- This may be used to change the background color or set an image for the notification.
  css TEXT
);


-- The "js_push" table is written to by subprograms
-- and read by server-webgui to execute arbitrary javascript in the GUI.
-- Expect a latency of 500ms between writing here and executing on the client.

CREATE TABLE IF NOT EXISTS js_push (
  -- Must re-declare rowid to be used in foreign key constraints
  rowid INTEGER NOT NULL PRIMARY KEY,

  -- Differentiates which browser session gets the JS code
  session_id INTEGER NOT NULL REFERENCES sessions(rowid) ON DELETE CASCADE,

  -- JS executed on the client
  client_js TEXT NOT NULL
  
);






