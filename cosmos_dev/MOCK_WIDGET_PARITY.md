# Mock Widget Parity — What the Browser Mock Can Render vs the Engine

Design note for the `cosmos_dev/mockgui` browser renderer: which GUI widgets the mock
reproduces, what those controls actually do to the simulation, where their placement
comes from, and how to add another. Read alongside `GUI.md` (widget API + gotchas) and the widget-list handling in
[`mockgui/sbs.py`](mockgui/sbs.py) / [`mockgui/client.html`](mockgui/client.html).

> **Scope reminder.** The mock's job is **route/logic coverage and layout sanity**,
> not pixel-perfect console emulation. The engine MAST compiler and native console
> renderers are the source of truth — the user verifies the real render in the browser
> at each checkpoint (`GUI.md`: "VERIFY IN BROWSER"). This doc is about *how much* of
> the console surface we can usefully fake headlessly, not about matching the engine
> pixel-for-pixel.

---

## Two widget families (they render by different paths)

"Widget" means two unrelated things in Cosmos, and conflating them is the main source
of confusion.

### Family A — story-page primitives (`send_gui_*`)

The atoms that `gui_button` / `gui_text` / `gui_list_box` / `gui_dropdown` / … compile
down to. One `send_gui_<kind>` command per widget, carrying a tag + style string + rect.

`button, checkbox, clickregion, colorbutton, colorcheckbox, dropdown, face, icon,
iconbutton, iconcheckbox, image, rawiconbutton, slider, text, typein, hotkey, 3dship`

### Family B — engine console widgets (`gui_layout_widget("name")`)

Native C++ renderers the story page only *reserves a rectangle* for. The mission sends
a **widget name list** (`send_client_widget_list`, `^`-joined); the engine paints each
named view into its slot. Nothing about the *content* crosses the MAST boundary — the
engine owns it.

`2dview, 3dview, ship_data, text_waterfall, comms_face, comms_control, comms_waterfall,
comms_2d_view, science_2d_view, weapon_2d_view, radar_zoom_ctrl, red_alert,
science_data(_tabs), science_sorted_list, comms_sorted_list, fighter_control,
grid_control, helm_free_3d` (list grows; see LM `consoles/layout_widgets.mast`).

---

## Current state of the mock

### Family A — fully covered

Every `send_gui_*` primitive has a real `case` in `client.html` `applyWidget`:
`button, checkbox, clickregion, colorbutton, colorcheckbox, dropdown, face, icon,
iconbutton, iconcheckbox, image, rawiconbutton, slider, text, typein, hotkey, 3dship`.
Plain story-page GUIs render faithfully; remaining gaps are cosmetic (fonts/spacing),
which is why a browser pass is still required.

### Family B — helm, weapons, science and comms are playable; engineering is not

Widgets are now table-driven from `_ENGINE_WIDGETS` in
[`mockgui/sbs.py`](mockgui/sbs.py) — one descriptor per widget saying which browser
command carries it, how its rect is forwarded, and (for the two consoles the engine
lays out itself) where it goes by default.

| Console | Emulated | Still dropped |
|---|---|---|
| **helm** | `2dview` `radar_zoom_ctrl` `ship_data` `throttle` `helm_movement` `shield_control` `request_dock` `main_screen_control` | `helm_jump`, `quick_jump` — drawn but **inert** (see below) |
| **weapons** | `weapon_2d_view` `radar_zoom_ctrl` `ship_data` `weapon_control` `weap_beam_freq` `weap_beam_speed` `weap_torp_conversion` `shield_control` `main_screen_control` | — |
| **science** | `science_2d_view` `radar_zoom_ctrl` `ship_data` `science_data` `science_data_tabs` `science_data_freq` `science_sorted_list` | — |
| **comms** | `comms_2d_view` `radar_zoom_ctrl` `comms_waterfall` `comms_control` `comms_face` `comms_sorted_list` `ship_data` `red_alert` | — |
| **engineering** | `ship_data` only | `eng_power_controls` `eng_heat_controls` `eng_presets` `grid_control` `grid_face` `grid_object_list` `ship_internal_view` |
| main screen / cinematic | `3dview` `2dview` `ship_data` (+ mock-only `target_data`) | — |

A widget with no descriptor is now **reported once per name** on the console
(`[mock] engine widget 'eng_power_controls' is not emulated …`). Previously an
unimplemented widget and a broken one both looked like an empty rectangle.

### How the controls actually drive the ship

Most engine console controls fire **no event**: the native widget writes a `data_set`
key and mission scripts poll it (ENGINE_WIDGETS.md, "Confirmed actuation patterns").
The mock reproduces that literally — the browser throttle writes `playerThrottle`, and
`_playership_drive` picks it up on the next physics tick exactly as it picks up the
autoplay AI's. So what a mission polls in the mock is what it would poll in Cosmos.

| Control | Delivery |
|---|---|
| `throttle` | `playerThrottle` (−1 reverse; warp band only when `warp == 1.0`) |
| `helm_movement` | `steerToDirD{X,Y,Z}` + `steeringToDirFlag` |
| `shield_control` | `shields_raised_flag` |
| `request_dock` | `dock_base_id` + `dock_state`, targeting the helm selection |
| `main_screen_control` | the real **`main_screen_change`** event (keyed on `origin_id`) |
| `weap_beam_freq` | `scan_type_for_shld_freq` (0.0–1.0 over bands A–E) |
| `weap_beam_speed` | `beamCycleTime` = hull base / rate — `_physics_beams` reads it, so 4X really does fire 4x as often |
| `weapon_control` FIRE | `sim.launch_torpedo`, which spends the round, spawns the projectile **and** emits `player_launches_missile` → `//launch/missile` |
| `science_data` scan | the mock's scan queue → the real **`science_scan_complete`** event |

### Known gaps in what these controls mean

- **Raising shields does not reduce damage.** The mock's damage model never reads
  `shields_raised_flag`; the button is correct and script-observable but currently
  cosmetic. Fixing that is a mock *physics* change, separate from widget work.
- **Docking state is script-side only** — `procedural/docking.py` walks it; the mock
  has no docking physics of its own. It does now start players 'undocked', which is
  what the engine reports, so missions that gate on the state behave.
- **`helm_jump` / `quick_jump` are deliberately inert.** ENGINE_WIDGETS.md open
  questions 2–3 leave their delivery unconfirmed. They render with a "not emulated"
  label rather than a blank rect, because guessing at a `data_set` key would be worse
  than saying so.
- **Torpedo load/fire are ahead of the engine.** ENGINE_WIDGETS.md records that
  load/fire are *not scriptable* in Cosmos today ("no access — this is an asked-for
  feature"). The mock implements them because it owns the simulation, so this is one
  place the mock is not mirroring an existing script API.
- **`science_data_tabs` is mock-local.** The engine sends the tab in a
  `select_space_object` `extra_tag` and `ConsoleDispatcher` does not read it yet (a
  library TODO). The mock switches which tab it renders rather than firing a
  half-supported event.

---

## Selection: the reticle, and preferences

A 2D view shows what its console has selected by drawing a **reticle** over it, in that
console's own colour. Both halves of that were missing.

- **`preferences.json` was never read.** `get_preference_float/int/string` were stubs
  returning `0`/`""`, so *every* preference any mission asked for came back empty. The
  file is **HJSON**, not JSON - it carries `//` comments and trailing commas (its own
  header says so) - so the reader strips comments outside strings before handing it to
  `json`. 116 keys now resolve.
- **The reticle** is `reticle-set.png`, a **5x4 grid of 266px cells**, drawn at
  `lock-reticle-size-2D` over the selected contact in the radar's own projection (so it
  tracks a moving target). Colours come straight from preferences:
  `gui-color-{weapon,science,comms}-reticle`; helm has no key of its own and falls back
  to `gui-color-main`.
- The art is **black line work on transparent**, unlike the white-on-transparent
  `grid-icon-sheet.png`. Tinting therefore has to be a `source-in` fill - the multiply
  the icon sheet uses would leave every reticle black.

**An overlay command must be TRANSIENT.** `reticle` was initially dropped: `server.py`
`_broadcast` treats any command not in its transient list as GUI *frame content*, so one
arriving mid-rebuild lands in `_pending_frame` and the next root `clear` discards it.
Combined with send-on-change, a lost send never came back. `widget_rect` is the same
shape and is transient for the same reason. **Any new per-tick, per-client overlay command
must be added to that list**, and its change-memo cleared in `_force_terrain_push()` so a
late-joining tab still gets the current state.

---

## Engine-fidelity gaps this work uncovered

Each of these made the mock quietly disagree with the engine, and each cost real debugging
time because the symptom appeared far from the cause:

| Gap | Symptom | Fix |
|---|---|---|
| `dock_state` was `""` on a new player ship | LM's `//select/weapons` route reads it to decide whether targeting is allowed; the check never passed, so **every weapons selection was cleared** the instant it was stored | player ships start `"undocked"`, which is what the engine's ship_data shows as State |
| no `warp` data_set key at all | the throttle's WARP band is gated on `warp == 1.0`, so it was **permanently disabled** | derived from the hull's `warp_energy_cost` |
| preferences unreadable | every `get_preference_*` returned 0/"" | see above |

The lesson for the next one: when a console misbehaves in the mock but the library code is
shared with the engine, suspect **a data_set key the engine populates natively and the mock
never sets**. `MOCK_LOG_SELECT=1` prints what a 2D-view click derived *and* what the shared
`do_select` actually stored - the two lines together localise this class of bug in one
click instead of a guessing round trip.

---

## Layout: who positions a Family-B widget

`send_client_widget_rects` fires **only** when a mission calls `gui_layout_widget`.

- **Comms, science and engineering lay themselves out** in MAST — LM's
  `consoles/layout_widgets.mast` places each widget — so real rects already reach the
  mock and it just has to honor them.
- **Helm and weapons place no engine widgets at all** (`//gui/normal_helm` at
  `layout_widgets.mast:293`, `//gui/normal_weap` at `:317`). The engine lays them out
  in C++ and the mock is handed nothing, so `_ENGINE_WIDGETS` carries a built-in
  default per widget per console.

Those defaults are stored as **anchor corner + capture pixels**, not percent. Two
engine console captures at different resolutions disagree on percentages while agreeing
on pixels (`ship_data` measures ~310x490 px in both), so the engine is sizing in pixels
and pinning to screen edges. The browser rescales by its own viewport **height** and
pins to the named corner, so the measured proportions survive a differently shaped
window instead of stretching. A script rect always overrides a default, and each resets
the other so a console change cannot leave a widget wearing the previous console's
placement.

---

## Extension mechanism

Adding a Family-B widget is:

1. **One `_register(_EngineWidget(...))` entry** in `mockgui/sbs.py` — name, browser
   command, rect/hide style, and a `defaults` entry only if the console does not lay
   itself out.
2. **Stream its state** from the relevant `_push_*` (helm / weapons / science), using
   `_push_delta` so only changed fields go on the wire.
3. **One `enginePanel(...)` in `client.html`** plus a `case` in the dispatch switch.
   `enginePanel` handles creation, placement (percent or anchor+px), hide, partial
   payload merge, and delegated clicks.

Two standing gotchas: overlays must mount in `#gui-root` (not `document.body`, which
sits under the mock topbar), and any broadcast/clientID-0 command must be in **both**
allow-lists (`server.py` `_broadcast` and the `client.html` `dispatch` clientID guard).

---

## What is left

**Engineering** is the remaining console: 7 widgets, none emulated. It already lays
itself out via script, so it is renderers plus state streams only — but the heat/power
model behind `eng_power_controls` / `eng_heat_controls` is the least complete part of
the mock, so the widgets would be further ahead of the simulation than elsewhere.

Library work these widgets surfaced (all `sbs_utils` changes, not mock ones) is listed
in ENGINE_WIDGETS.md: weapons-select routes, the `science_data_tabs` dispatcher change,
a `shield_control` event, and scriptable torpedo load/fire.

---

## Interaction primitives — radar click → selection ✅ DONE

Family-B rendering is only half of a *command* console; the other half is **picking an
object on the 2D view**. That primitive is now built (it's console-agnostic — every
detached-command console and the galaxy theater need it):

- **Browser** (`client.html`): a clean left-click (or right-click) inside a console 2D
  view — distinguished from a drag-pan by the existing 4px threshold — runs
  `_radarSelectAt`, which picks the nearest object to the cursor (within 20px, over
  `_dynamicMap` + `_terrainMap`, using the render's captured `_pickState` projection) and
  posts a `select_space_object` event (same type name the engine uses) with the picked id,
  the click's world point, and `lmb`/`rmb`. Empty space picks id 0 (still carries
  `source_point` for camera-pan).
- **Runner** (`mission_runner.py`): enriches the `select_space_object` event, supplying
  `origin_id` (the client's assigned ship/cam) and
  `sub_tag` (the console name, via `sbs.get_client_console_name`). `value_tag="2dview"`.
- **Routing** is the *real* shared code: `consoledispatcher.py` `convert()` maps
  (`sub_tag` console name + `value_tag`) → a selection tag — a name containing `comm` →
  comms selection, `sci`/`admiral` → science — exactly as in the engine. Nothing about
  the routing is mocked.

This unlocks marker/unit selection **and** `//focus/comms` click-to-move-camera in one
primitive. Remaining Admiral gap after this: `comms_control` (render the menu the
selection opened) + `comms_face` (Tier-1) + `radar_zoom_ctrl` (polish).

---

## Case study — the Admiral console & galaxy theater in mockgui

The Admiral console (OU `admiral/admiral.mast`, LM `admiral/`) and its **Galaxy
Theater** are the reason the Tier-1/Tier-2 gaps matter — and they're **more tractable in
the mock than they look**, because neither is a bespoke GUI surface:

- **Admiral console** = an invisible **detached camera**
  (`player_spawn(..., "#,admiral_cam,admiral,has_science_scan", "invisible")`) the client
  is assigned to, under console name `gamemaster_overseer_comms`. Its screen = 4 engine
  widgets (`radar_zoom_ctrl`, `comms_2d_view`, `comms_face`, `comms_control`) + story-page
  primitives (a `gui_text` ticker, build-queue + roster `gui_list_box`es, a cancel
  `gui_button`).
- **Galaxy Theater** is *not a grid widget* — `galaxy_theater_build` **spawns real marker
  objects** (`terrain_spawn(..., "galaxy_marker"/"galaxy_unit"/"galaxy_fleet",
  "tsn_fighter"/"tsn_battle_cruiser", "behav_selection")`) onto a board out in dead space
  (±1M coords), viewed through the **same `comms_2d_view`** (a second galaxy cam's radar).
  A marker click fires a comms selection; its `//comms` gives deploy/jump/close.

So both screens are *"a detached camera looking at real objects through the 2D view, plus
comms widgets."*

| Piece | Mock status |
|---|---|
| Detached cam spawn + `assign_client_to_ship` | ✅ (real Python path) |
| Story-page GUI (ticker, list boxes, cancel) | ✅ (Family A complete) |
| `comms_2d_view` — system view **and** galaxy board | ✅ Already renders — the markers are real spawns, so they draw on the mock radar |
| Radar pan / recenter | ✅ |
| **Click a marker/unit → command it** | ✅ **Now built** (radar-click selection above) |
| `comms_control` (deploy/jump/cancel menu) | Renders — sticky header + scrollable button list, click fires `press_comms_button` |
| `comms_face` | Renders — portrait via the shared `face.js` |
| `radar_zoom_ctrl` | Renders — the engine's -/+ buttons plus the SIDE/DIPLO colour toggle |

**Verdict: done.** The expensive part (rendering a strategic map) was always free, because
the map is real radar objects. Every widget the Admiral console declares now draws and
responds, so the console is drivable in the mock.
