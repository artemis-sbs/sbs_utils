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
- items: the Vigoranium Nodule works again. Its effect label emitted an
  `item_restore_damcon` signal that nothing anywhere handled, so the item was
  consumed, started its cooldown and did nothing; it now calls
  `grid_restore_damcons` inline like every other item effect (LM #381).

### sbs_utils

- Every `gui_message` handler on a widget now runs, not just the last one
  registered (LM #614). Both registration slots -- the page's tag map (used by
  `on gui_message`, `gui_message(w, label)` and `gui_button(on_press=)`) and the
  widget's `on_message_cb` (used by `gui_message_callback` / `gui_message_label`)
  -- were plain assignments, so attaching a second handler silently discarded the
  first. They chain instead, firing in registration order; a handler that raises
  is logged and the rest still run. Two consequences worth naming:
  `gui_button("Go", on_press=lbl)` followed by `on gui_message(btn):` no longer
  destroys the `on_press`, and `gui_message_callback` / `gui_message_label` on a
  `gui_section()` no longer raises AttributeError on the first click. New
  `gui_message_clear(widget)` detaches every handler when you want to replace
  rather than add.
- `on gui_click` gained the same rule (LM #614). Its dispatch returned on the
  first handler that matched, so two blocks for one tag ran only the first --
  and a catch-all `gui_click()`, which matches every click, silently shadowed
  every handler registered after it.
- Damcons no longer vanish on a grid REBUILD (LM #381). `grid_restore_damcons`
  decided "this team already exists" from an engine name lookup, but
  `grid_delete_object` only tombstones the agent and defers the native free to the
  end of the event handler - so a rebuild, which deletes every grid object and then
  calls restore, found the teams it had just deleted, "healed" them, and left the
  ship with no damage control at all once the queue drained. Every rebuild after the
  first was affected: player respawn, hangar craft, any layout swap.
- Damcons are placed on an interior with NO hallway. A hull whose every open cell
  holds a room has no unoccupied cell, and the engine's occupancy-tolerant finder has
  no memory across the loop, so all three teams landed on one cell and read as a
  single team. They are now spread over the nearest free open cells.
- The ship marker and the EPad no longer land on the same cell on every hull: they
  made the identical unfiltered finder call with no state change between them.
- Damcon COUNT and POSTS can be declared by the interior data - the second half of
  LM #381. A `damcons:` header in a `.grid` floor plan, or a `damcons` key in a
  grid_data entry or named layout: `damcons: 5  3,2  1,4` is five teams with the
  first two posted. A post is also the team's permanent rally point, so an author can
  station a team by the nacelles. New `grid_get_damcons()` and `grid_damcon_count()`.
  Backward compatible by construction: a plan that declares nothing round-trips to an
  entry with no `damcons` key and takes exactly the old path (three engine-placed
  teams). `grid_ascii_validate` reports a post that is off the grid or off the hull as
  an error; at runtime a bad post is a warning and the engine chooses instead, because
  one typo must never leave a ship without damage control.
- `grid_restore_damcons(id, layout=None)` and a2x `set_damcon_members` bound its
  team index to the ship's declared count rather than a literal 3. No effect on 2.8
  conversions, which only ever address teams 0-2.
- `grid_restore_damcons` reports a damcon prefab it cannot spawn instead of raising
  `AttributeError` on `None` (the old success path made the code after it unreachable).

- Dropdown: a selection set from script now reaches the screen (LM #568). A
  dropdown's rendered state lives in one string - the props `_present` sends -
  and neither writer landed there. `update()` set a `props` attribute nothing
  reads (so `gui_update()` by tag was dead on a dropdown too), and the `value`
  setter set only `_value`, so `.value` read back correctly while the box still
  showed the old label. Both now write the props string and mark the widget
  dirty, and a selection the PLAYER makes is recorded there as well, so it
  survives the next present instead of reverting. `.value` is also seeded from
  the initial `text:` rather than `""`, so it reports what is on screen before
  anyone clicks.

- A MAST expression that RAISES no longer looks like one that returned None.
  `None` is a legal MAST value, so the old "report the error, then hand the node
  None anyway" laundered a failure into data: the assignment wrote None (into a
  `shared` variable, for every other task), the `if` took its `else:`, and
  `for x in <broken>` did `iter(None)` and reported a SECOND error against the
  same line - which is the one the author saw. `eval_code_checked()` returns a
  distinct `EVAL_ERROR` sentinel and the nodes stop on it, so the first error
  reported is the real one. `eval_code()` is unchanged (still returns None) for
  every existing caller.
- MAST runtime errors now name the exception type, quote the failing expression,
  and - for the `shared`/`assigned`/`client`/`temp` scope-keyword trap - say so.
  Expressions compile against a per-expression pseudo-filename registered in
  `linecache`, so the offending MAST source appears in tracebacks instead of the
  literal word "None" where the code should be.
- Urges: a recurring want held by any agent (a lifeform, a station, a side),
  authored as an `Urge` record - a `Whenever:` condition, an `Every:` cadence
  (`3-5m` to jitter), and a pool of lines in the body. One shared ticker walks
  every actor that has urges and picks at most one. An urge declares no stakes of
  its own: the consequence belongs to the quest it watches, so there is one clock
  and one place to tune it.
- Urge escalation: `%` / `%%` / `%%%` are stages, and `Escalates: with deadline`
  takes the stage from how much of the bound quest's clock has gone - the marker
  count is the curve, `Fails when:` is the tempo. The bound quest is read out of
  `Whenever:`, so there is no second field to keep in agreement.
- A speech budget, which is what decides whether autonomous speech is bearable:
  a per-actor floor (no monologuing) and a global floor shared with `announce`
  (no piling up, and nothing talks over mission dispatch). `Weight: 90+` bypasses
  the global floor only, never its own.
- Quests can be held by the world. `quest_add` always took agents, but every
  deadline/proximity watcher iterated `SHARED + players`, so a station-held quest
  showed its objective and its clock never started. The holder set is now
  `has_inventory("__quests__")`, and `Held by:` names the owner in AMD.
- Reputation as a quest consequence: `Reward:` / `Penalty:` accept
  `earns <faction> <pole> <n>` (the dialogue outcome grammar, not a second
  spelling), on player/SHARED-held quests. `amd_reward` also parses items now -
  `300 credits, 2 torpedoes` used to return the credits and drop the torpedoes
  silently, while `quest_grant_reward` had supported items all along.
- `Fails when: after 20m` finally means 20 minutes. The compact duration forms
  (`20m`, `30s`, `2h`) never parsed - the scan wanted an `isdigit()` token - so
  the deadline silently never fired. Only `6 minutes` had ever worked.
- `Action: ... departs` works on a non-space actor (a lifeform is a bare Agent, so
  it used to raise and be swallowed, leaving a direction that did nothing), and
  `self` names the actor an `Action:` block belongs to.
- `sbs lint` checks urges: an unknown `Whenever:`/`Until:` phrase (which evaluates
  false, so the urge never fires), an urge with neither lines nor an `Action:`, and
  an `Every:` under the global speech floor.
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



