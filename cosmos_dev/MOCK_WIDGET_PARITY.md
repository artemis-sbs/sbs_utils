# Mock Widget Parity — What the Browser Mock Can Render vs the Engine

Design note / roadmap for the `cosmos_dev/mockgui` browser renderer. Captures which
GUI widgets the mock reproduces today, which it silently drops, and how to close the
gap. Read alongside `GUI.md` (widget API + gotchas) and the widget-list handling in
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

### Family A — fully covered ✅

Every `send_gui_*` primitive has a real `case` in `client.html` `applyWidget`
(~lines 2751–2982): `button, checkbox, clickregion, colorbutton, colorcheckbox,
dropdown, face, icon, iconbutton, iconcheckbox, image, rawiconbutton, slider, text,
typein, hotkey, 3dship`. Plain story-page GUIs render faithfully; remaining gaps are
cosmetic (fonts/spacing), which is exactly why a browser pass is still required.

### Family B — four faked, the rest dropped ⚠️

`mockgui/sbs.py` intercepts `send_client_widget_list`, string-matches the names, and
synthesizes browser equivalents for five:

| Engine widget | Mock reproduction | Path |
|---|---|---|
| `2dview` (+ `comms_/science_/weapon_2d_view`) | Browser **radar** (navareas as quads) | `radar` cmd |
| `3dview` | **Cinematic** three.js hull scene | `cmdCinematic` |
| `ship_data` | **HUD stat panel**, streamed each tick | `_push_ship_data` → `cmdShipData` |
| `text_waterfall` | **Text overlay** | `text_msg` / `text_active` |
| `red_alert` | **Toggle button** (in comms) + ship-wide pulsing vignette | `_push_red_alert` → `cmdRedAlertBtn` / `cmdRedAlert` |

Everything else in Family B is **silently dropped** — the mission runs, the reserved
rectangle is just empty in the browser:
`comms_face, comms_control, comms_waterfall, radar_zoom_ctrl, red_alert,
science_data(_tabs), *_sorted_list, fighter_control, grid_control, helm_free_3d`.

This bites the **detached-command consoles** (Game Master, OU Admiral), which lean on
`comms_face` / `comms_control` / `science_data` / `red_alert` and today show blank
panels in the mock.

---

## Extension mechanism (fixed, cheap to repeat)

Adding a Family-B widget is always the same three steps:

1. **Recognize the name** in `send_client_widget_list` (`mockgui/sbs.py`) — it already
   parses the `^`-joined list and reserves rects via `send_client_widget_rects`.
2. **Stream a per-tick payload** for it (mirror `_push_ship_data`: gather state, `_send`
   a small dict), or send once on change.
3. **Add a `cmd<Name>` renderer** in `client.html` (register it in the `dispatch`
   switch ~line 669) that paints DOM/canvas into the widget's rect.

Family-A event round-trips (click → `gui_message`) already exist and can be reused for
any interactive Family-B widget.

---

## Roadmap — ranked by value / effort

### Tier 1 — data panels from existing state (high value, low effort)

Read data the mock already holds; paint DOM. No new event plumbing.

- **`red_alert`** — ✅ **DONE + browser-verified.** The real engine widget is a **toggle
  button** (lives on the comms console `normal_comm`): `cmdRedAlertBtn` renders a clickable
  button positioned by the `ConsoleWidget` layout rect (forwarded as `red_alert_btn` from
  `send_client_widget_rects`); a click → `red_alert_toggle` → the runner fires the engine
  `red_alert` event → `handlerhooks` sets the ship's `red_alert` + emits `red_alert_change`
  (the real path). **Separately**, the pulsing full-viewport **vignette** (`cmdRedAlert`)
  lights **every console of a ship in red alert** (helm/weapons/comms/engineering/science) —
  `_push_red_alert` iterates `get_client_ID_list()`, keyed on each client's own ship state.
  Gotcha: `red_alert` lives on the **Agent inventory** in the mock (via `set_inventory_value`
  in handlerhooks), not the engine data_set — read it by id with procedural
  `get_inventory_value(sid,…)` (`sim.space_objects.get()` returns the engine object, which has
  no `get_inventory_value`). Dev knob `MOCK_FORCE_RED_ALERT=1` forces the vignette on for
  eyeballing without a button.
- **`comms_face`** — reuse the existing `face.js` renderer (already backing
  `send_gui_face`); stream the current comms origin's face string. ~2 hr.
- **`comms_waterfall`** — clone the `text_waterfall` overlay, fed from comms dialog
  sends instead of story text. ~2 hr.
- **`science_data` / `science_data_tabs` / `*_sorted_list`** — list/table panels over
  scanned objects (the mock knows the object set + roles). Model on `cmdShipData`; the
  sorted-lists share one renderer parameterized by source query. ~½ day each.

### Tier 2 — interactive control widgets (medium effort)

Emit events back, so they need the event round-trip too.

- **`comms_control`** — the comms button tree. With radar-click selection now built
  (see *Interaction primitives* below), a click already opens the right comms context;
  this widget renders that menu's buttons from the current comms page state and posts
  `gui_message` on click (reuse Family-A button events). Highest-value Tier 2 — lets comms
  flows be exercised headlessly instead of only in the engine. ~1 day.
- **`radar_zoom_ctrl`** — slider bound to the radar scale in `cmdRadar`. ~½ day.
- **`fighter_control` / `grid_control`** — engine-specific; approximate as a labeled
  button cluster driving the same events. Lower fidelity, enough to exercise routes.
  ~1 day each.

### Tier 3 — hard / probably not worth faking

- **`helm_free_3d`** — interactive free-fly piloting. The cinematic three.js scene
  exists, but wiring flight controls back through `steerToDirD*` + the event queue is a
  real project. Stub as `3dview` until there's demand.

---

## Recommendation

Don't chase broad Family-B fidelity. The high-leverage work is the **Tier-1 data
panels** — they unblock the detached-command consoles (GM, OU Admiral) that currently
render blank rectangles in the mock — plus **`comms_control`** from Tier 2 as the one
interactive widget worth building (headless comms exercise). Start with `red_alert` as
a one-widget proof of the recognize → stream → `cmd*` pattern, then `comms_face` and the
`science_data` list panels.

---

## Interaction primitives — radar click → selection ✅ DONE

Family-B rendering is only half of a *command* console; the other half is **picking an
object on the 2D view**. That primitive is now built (it's console-agnostic — every
detached-command console and the galaxy theater need it):

- **Browser** (`client.html`): a clean left-click (or right-click) inside a console 2D
  view — distinguished from a drag-pan by the existing 4px threshold — runs
  `_radarSelectAt`, which picks the nearest object to the cursor (within 20px, over
  `_dynamicMap` + `_terrainMap`, using the render's captured `_pickState` projection) and
  posts a `radar_select` event with the picked id, the click's world point, and
  `lmb`/`rmb`. Empty space picks id 0 (still carries `source_point` for camera-pan).
- **Runner** (`mission_runner.py`): turns `radar_select` into the engine's
  `select_space_object` event, supplying `origin_id` (the client's assigned ship/cam) and
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
| `comms_control` (deploy/jump/cancel menu) | ❌ Tier 2 — the action buttons don't render yet |
| `comms_face` | ❌ Tier 1 (~2 hr, reuses `face.js`) |
| `radar_zoom_ctrl` | ❌ Polish (board can be dense at default zoom) |

**Verdict:** the expensive part (rendering a strategic map) was already free — the map is
real radar objects. The remaining gap is a **`comms_control` renderer** so the menu a
selection opens is visible/clickable; then `comms_face` + `radar_zoom_ctrl` are polish.
Rough total for a genuinely drivable Admiral in the mock from here: **~1.5–2 days**.
