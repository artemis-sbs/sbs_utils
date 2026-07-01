# Changelog


## 1.4.0

### LegendaryMissions (core addons)

- hangar_crafts.yaml reworked as deltas over shipData hulls: each loadout is a
  shipData `key` + `type` + a list of default `upgrades`, instead of restating
  roles/name/shields/ammo. Craft name and roles now derive from shipData.
- hangar craft loadouts applied through the item/upgrade system: new
  `item/loadout/*` prefab items (cockpit_shields, torp_bay) in hangar_loadout.mast,
  resolved by key and applied with upgrade_add at spawn. Ammo is additive on top
  of the hull's torpedostart; shields scale via a multiplier modifier.
- hangar cockpit uses an overlay image + widget layout (MiningDays style); the
  Air Wing info panel is retained.
- items: `item_activate` uses `//shared/signal` (server-only) so an item/upgrade
  applies once, not once per connected client.
- items: pickup collection guards against a re-collision on an already-removed
  object (fixes a runtime error setting position on a None).

### sbs_utils

- MAST web pages: author browser pages in MAST with `//web/<path>` routes,
  rendered live in a browser with the normal gui_* layout - with no engine
  changes. Query string seeds page variables (`/web/scores?title=Hi`),
  `Gui.web_page_navigate` moves an open session to another page, and web clients
  carry the `__web__` role so mission code can target viewers.
- Living web pages: `web_refresh(path)` re-renders open `//web/<path>` sessions
  after data changes (e.g. a leaderboard); `web_living(persist=True, refresh=N)`
  (called in the route body) declares a page persistent, so the web proxy saves a
  snapshot at game end / on a cadence and serves it after the game.
- `signal_next(name)`: one-shot await of the next `signal_emit(name)` (composes
  with `promise_any` / a `timeout`); safe no-op when there is no MAST context.
- cosmos_dev web proxy (dev tooling): serve MAST `//web` pages to browsers from a
  running engine over the dev queue, or in-process from a non-engine MAST host.
  Push-channel streaming, static one-shot HTML rendering, an always-on proxy that
  survives engine restarts, and one proxy fronting multiple engines by URL. See
  `cosmos_dev/webproxy/README.md`.
- cosmos_dev dev queue can be enabled with a `dev_queue.enable` marker file in the
  mission dir (launch the engine normally, no env vars).
- `settings_get_defaults()` honors a `COSMOS_SETTINGS` env override, so the
  sbs debug/overnight tooling can set AUTO_START / player count / etc. without
  editing settings.yaml.

Fixes:
- `Gui.present` / `send_custom_event` iterate a snapshot of `Gui.clients` (fixes
  "dictionary changed size during iteration" when a client is added/removed
  mid-present).
- modifier "already exists" / removal messages use `debug_print` (no log spam).


## 1.3.0

### LegendaryMissions (core addons)

- Improved Game master console
- elite abilities refactor to allow new and custom abilities
- Ship changes can be disable via settings.yaml SHIP_PICK_READ_ONLY
- changing console can be disabled via settings.yaml CAN_CHANGE_CONSOLE
- added more comms select popup speech bubble text from forum feedback
- a number of gui changes based on sub_utils updates: e.g. removed gui_represent calls
- wreck behavior now behav_wreck the engine does use this new value

- hangar has a override setting file hangar_crafts.yaml
- craft names changed


-  #518, #369, #454, #460, #476, #473, #467, #463, #442, #432, #425, #423, #304, #407

### sbs_utils

- the fetch batch file system was replaced with the sbs command line tool. Docs were updated.
- added log files for compile errors (mast.compile.log) and runtime errors (mast.runtime.log)
- comms_message emits a signal comms_message
- is_dev_build is cached and can be set via set_dev_build
- Added debug_print
- added gui dirty system so script no longer needs to call gui_represent items mark themselves dirty and the represent is handled automatically
- a mock version of sbs ships with library in sbs_utils.mock.sbs used for testing and debugging outside of the Cosmos exe
- added Image atlas
- Improve gui_tab system
- Removed engine grid in hangar crafts
- Buttons and checkbox have icon options, background color
- Add more option to log and logger
- Improved listbox handling of gui_subsection
- gui_subsection can be used in gui_message e.g. to make a custom button/clickable area
- gui margin, borders padding work correctly 
- listbox supports tree like expand and collapse
- listbox supports custom collapse item
- listbox supports custom click_tag
- text area fixed measuring issues
- text area subset of markdown syntax: can have images, face, ship sections
- Quest screen
- if, for, match statements can be used in main




Fixes:
    #382, #399, #351, #513, #335, #515, #362, #532, #525



