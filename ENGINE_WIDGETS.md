# Engine Gameplay Widgets - interaction reference

Companion to [AUTOPLAY_PLAN.md](AUTOPLAY_PLAN.md). These are the **engine gameplay
widgets** streamed via `send_client_widget_list` (helm/weapons/science/comms/eng
consoles) - a separate interaction channel from `send_gui_*` layout widgets
(driven by `on gui_message`). The mock does **not** emulate them yet; the
test-mode autoplayer must be able to drive them.

Names/descriptions seeded from `data/GUIWidgetList.txt`; per-console grouping from
`procedural/gui/console.py`; **User actions** from the per-widget screenshots in
`missions/screen_shots/` (`Shot:`); **Delivery / selection / proc** filled by Doug
from the engine. `OPEN:` marks things still to confirm (see Open questions at end).

Per widget: **Actions** (what the player does) - **Delivery** (the `data_set` key
written and/or the route/event fired) - **Selection** (UID set, if any) - **Proc**
(existing `sbs_utils` entry) - **Notes**. `[I]` interactive, `[D]` display-only.

---

## HELM (`normal_helm`)
`2dview ^ radar_zoom_ctrl ^ helm_movement ^ helm_jump ^ quick_jump ^ throttle ^ request_dock ^ shield_control ^ ship_data ^ text_waterfall ^ main_screen_control`

### [I] helm_movement - steer the ship
- Actions: click/drag the steering ring to aim a heading (ANG); ALT = altitude, AZI; surrounding contacts shown as markers.
- Delivery: data_set `steerToDirDX/DY/DZ` + `steeringToDirFlag` - **added for autoplay** and honored by the engine, so a bot/mock can use it. The native helm widget's own steering write differs (TBD; see open Q2). Selection: none.
- Shot: `helm_movement.png`

### [I] throttle - set speed
- Actions: vertical bar; **REV** and **WARP** buttons toggle how the bar is used. In impulse/reverse the bar sets any level; WARP has 4 sections.
- Delivery: data_set `playerThrottle`. **`-1` = reverse** (engine UI uses a REV button). **WARP only available if data_set `warp` == 1.0.**
- Shot: `throttle (impulse mode).png` (SPD readout, WARP top, REV bottom)

### [I] helm_jump - jump drive
- Actions: set **Direction** and **Distance(K)** sliders; ENERGY shows cost; press **JUMP**.
- Delivery: engine handles the jump (mostly internal). Check data_set `jump_energy`.
- Notes: shown only if the ship has jump (`jump_drive_active`, `jump_upgrade_coef`).
- Shot: `helm_jump.png`

### [I] quick_jump - instant ximni jump fwd/back
- Actions: click a **forward** or **back** arrow; a fill bar shows charge. Jumping before the bar is full is **less accurate**.
- Delivery: TBD (charge + fwd/back) - niche; see open Q3.
- Shot: `quick_jump.png`

### [I] request_dock - request dock / undock
- Actions: single **INITIATE DOCK** button (in range); toggles to undock/release when docked.
- Delivery: data_set `dock_state`; the script starts docking by setting `dock_base_id`.
- Notes: pressing INITIATE in range walks `dock_state`: `unknown -> docking -> docking_start -> docked`. The script watches `dock_state` and can cancel by setting `dock_base_id = 0` and `dock_state = unknown`. **Engine quirk:** the docked-with object uses a *tractor* during docking; on cancel the script must delete it.
- Shot: `request_dock (release dock).png`

### [I] shield_control - toggle shields up/down
- Actions: single **SHIELDS** button.
- Delivery: data_set `shields_raised_flag`.
- Notes: no engine event currently (maybe there should be).
- Shot: `shield_control.png`

### [I] main_screen_control - control main-screen view
- Actions: dial picks facing (FRONT/LEFT/RIGHT/BACK) and camera mode (INSIDE/CHASE/TRACK); side buttons TACT/LRS/DATA pick the view.
- Delivery: sets `MAIN_SCREEN_VIEW` / `MAIN_SCREEN_FACING` / `MAIN_SCREEN_MODE` via the **`main_screen_change`** event.
- Shot: `main_screen_control.png`

### [I] radar_zoom_ctrl - 2D radar zoom buttons
- Actions: zoom out/in (`<<` / `>>`), discrete levels; rightmost (leaf) toggles a side-color / diplomacy overlay.
- Delivery: likely client-local (no known script visibility).
- Shot: `radar_ctrl.png`

### [I] 2dview - 2D radar (click to select)
- Actions: single click sets/clears the selection (by hit); right-click / long-hold fires the **`hold_click`** event -> context menu -> **`hold_button_pressed`** event.
- Delivery / Selection: sets **`normal_target_UID`**.
- Notes: **the same for all 2D views** - only which `*_target_UID` is set differs (weapon/science/comms/grid).
- Shot: (none individually; see comms_2d_view.png)

- [D] ship_data, text_waterfall.

---

## WEAPONS (`normal_weap`)
`weapon_2d_view ^ radar_zoom_ctrl ^ weapon_control ^ weap_beam_freq ^ weap_beam_speed ^ weap_torp_conversion ^ ship_data ^ shield_control ^ text_waterfall ^ main_screen_control`

### [I] weapon_control - load / unload / fire torpedoes
- Actions: **TYPE** dropdown picks torpedo type; each tube row has **Load** and **FIRE**.
- Delivery: firing emits `//launch/missile` via the **`player_launches_missile`** event. **Load/Fire are NOT currently scriptable** (no access) - this is an asked-for feature. Torp type is not visible to the script.
- Proc: `torpedoes.py` defines torp type strings + properties (not load/fire).
- Shot: `weapon_control.png`

### [I] weapon_2d_view - select weapons target (click)
- Selection: **`weapon_target_UID`**. See `2dview` (same mechanics).
- Proc: `set_weapons_selection`. **No `follow_route_select_weapon` exists** - weapons-select routes should be added.

### [I] weap_beam_freq - set beam frequency
- Actions: pick frequency A/B/C/D/E (tune to target's weak frequency).
- Delivery: data_set `scan_type_for_shld_freq` (0.0-1.0). *(confirmed)*
- Shot: `weap_beam_frea.png`

### [I] weap_beam_speed - set beam fire rate
- Actions: pick **Beam Fire Rate** 1X/2X/3X/4X (faster = more shots, less damage each). (Widget id says "speed" but label is "Beam Fire Rate".)
- Delivery: data_set `beamCount`, `beamCycleTime`.
- Shot: `weap_beam_speed.png`

### [I] weap_torp_conversion - trade torpedo <-> energy
- Actions: buttons like "Mine to energy (+200)" / "Energy to Homing (-150)"; greyed when unaffordable.
- Delivery: affects energy. Each torp's `energy_conversion_value` (in its style string) is the value; `energy_to_torp_cost` is the conversion cost (added to the conversion value, then subtracted from energy if available).
- Shot: `weap_trop_conversion.png`

- [I] shield_control, radar_zoom_ctrl, main_screen_control - see HELM.
- [D] ship_data, text_waterfall.

---

## SCIENCE (`normal_sci`)
`science_2d_view ^ radar_zoom_ctrl ^ ship_data ^ science_data_freq ^ science_data_tabs ^ text_waterfall ^ science_data ^ science_sorted_list`

### [I] science_sorted_list - select object for science
- Actions: select a contact from the sorted/filtered list.
- Delivery: fires the select route. Selection: **`science_target_UID`**.
- Proc: `set_science_selection` / `follow_route_select_science`. *(confirmed)*

### [I] science_2d_view - select by clicking the radar
- Selection: **`science_target_UID`**. See `2dview` (same mechanics).

### [I] science_data - selected-contact data + initiate scan
- Actions: unscanned -> green **"Start Initial Scan"** button starts the scan; scanned -> range/bearing, shields, system health, hail prompt. **This is how a scan starts.**
- Delivery: the engine keeps an internal queue of in-progress scans and advances them by distance; progress in data_set `cur_scan_percent`; completion fires the **`science_scan_complete`** event.
- Shots: `science_data (start scan).png`, `science_data (scanned).png`

### [I] science_data_tabs - switch data tab
- Actions: tabs select the data category: scan / status / intel / bio (Debug in dev).
- Delivery: **`select_space_object`** event with the tab in `extra_tag`.
- Notes: **library TODO** - `ConsoleDispatcher` may currently convert this to a UID; it needs to change to handle the tab (new).
- Shot: `science_data_tabs.png`

### [D] science_data_freq - frequency analysis readout
- Read-only display: shows the target's signal strength A-E and marks the "weak" one (guides `weap_beam_freq`). Not interactive.
- Shot: `science_data_freq.png`

- [I] radar_zoom_ctrl - see HELM.
- [D] ship_data, text_waterfall.

---

## ENGINEERING (`normal_engi`)
`ship_internal_view ^ eng_presets ^ grid_object_list ^ grid_face ^ grid_control ^ text_waterfall ^ eng_heat_controls ^ eng_power_controls ^ ship_data`

### [I] eng_power_controls - power sliders per system
- Actions: one vertical slider per system (BEAM, TORP, IMPULSE, WARP, MANEUVER, SENSORS, FRONT SHIELD, REAR SHIELD); drag to set power % (up to ~300%).
- Delivery: data_set `eng_control_cost_coeff`, `eng_control_label`, `eng_control_type_index`, `eng_control_value`.
- Notes: read the labels until None/empty to get the count.
- Shot: `eng_power_control.png`

### [I] eng_heat_controls - coolant + heat per system
- Actions: per system (WEAPONS, ENGINES, SENSORS, SHIELDS) add/remove coolant via the cell buttons; HEAT bar + % shown.
- Delivery: data_set `system_coolant_available`, `system_coolant_setting`, `system_coolant_used`, `system_last_coolant_change`, `system_cur_heat`.
- Shot: `grid_heat_controls.png`

### [I] eng_presets - store/recall presets
- Actions: STOR + slots 0-9; press a number to recall, STOR+number to store.
- Delivery: file `data/engineering-presets.txt`.
- Shot: `eng_presets.png`

### [I] grid_object_list - select a grid object
- Actions: tabs (crew / tools) + list (DC1-DC3 damage-control teams, EPad, ...); select to command.
- Delivery: fires the select route. Selection: **`grid_selected_UID`**.
- Proc: `set_grid_selection` / `follow_route_select_grid`. *(confirm)*
- Shot: `grid_object_list.png`

### [I] grid_control - command grid objects (button list)
- Actions: button list of orders for the selected grid object (e.g. crew: Workout / Sleep / Eat / do work order now / cancel work order).
- Delivery: `press_grid_button` event (parallels comms's `press_comms_button`). *(confirmed)*
- Shot: `grid_control.png`

### [I] ship_internal_view - interior grid view (click select)
- Actions: click a grid object/point in the interior view to select it.
- Delivery: data_set `grid_object_selection`; fires `//point` / `//select/grid`.
- Shot: `ship_internal_view.png`

- [D] grid_face, ship_data, text_waterfall.

---

## COMMS (`normal_comm`)
`comms_2d_view ^ radar_zoom_ctrl ^ text_waterfall ^ comms_waterfall ^ comms_control ^ comms_face ^ comms_sorted_list ^ ship_data ^ red_alert`

### [I] comms_sorted_list - select comms target
- Actions: filter tabs (Active / Favorite / side / map) + ship list; select to open comms (rows mark `<com`, `<sci`).
- Delivery: fires select -> opens comms. Selection: **`comms_target_UID`**.
- Proc: `set_comms_selection` / `follow_route_select_comms`. *(confirm)*
- Shot: `comms_sorted_list.png`

### [I] comms_control - comms command buttons
- Actions: header shows the comms target; button list (Hail / Build Weapons / Request Priority Docking / ...); press to send / navigate the tree.
- Delivery: **`press_comms_button`** event.
- Proc: `comms_navigate` / `comms_navigate_override` (for navigation).
- Shot: `comms_control.png`

### [I] comms_2d_view - select by clicking the radar
- Selection: **`comms_target_UID`**. See `2dview` (same mechanics).
- Shot: `comms_2d_view.png`

### [I] red_alert - toggle red alert
- Actions: single **RED ALERT** button.
- Delivery: data_set `red_alert` (0/1) **and** fires a `red_alert` event. *(confirmed)*
- Shot: `red_alert.png`

- [I] radar_zoom_ctrl - see HELM.
- [D] comms_face, comms_waterfall (`comms_messages.png`), ship_data, text_waterfall.

---

## MAIN SCREEN / VIEWS
- [I] main_screen_control - see HELM.
- [D] 3dview, 3dview_camera (3D out-the-front / manual-beam view), ship_internal_view, text_waterfall, ship_data.

### Alternate helm widgets (when substituted)
- `helm_normal`, `helm_simple`, `helm_free_3d`, `helm_restrained_3d`, `fighter_control`
  swap the helm movement control between flat-2D, simple-3D and full-3D steering.

---

## Confirmed actuation patterns
- **Selection (2D views / lists):** a click sets a `*_target_UID`
  (`normal_target_UID` helm/nav, `weapon_target_UID`, `science_target_UID`,
  `comms_target_UID`, `grid_selected_UID`); right-click/long-hold -> `hold_click`
  -> context menu -> `hold_button_pressed`. Same mechanics across all 2D views.
- **Route-firing interactions:** the canonical headless driver is to **synthesize
  a `FakeEvent` and dispatch via `ConsoleDispatcher`** (the `_follow_route_console`
  pattern) - "FakeEvent is best".
- **data_set-driven interactions** (writing the key alone "just works" - same
  engine reaction as the widget): throttle (`playerThrottle`, -1=reverse, warp
  needs `warp==1.0`), shields (`shields_raised_flag`), dock (`dock_state` +
  `dock_base_id`), beam (`scan_type_for_shld_freq` 0-1, `beamCount`,
  `beamCycleTime`), power (`eng_control_*`), coolant/heat (`system_coolant_*`,
  `system_cur_heat`), red_alert (`red_alert`, also fires a `red_alert` event).

## Library work surfaced (for v1.4.0_dev / later)
- **Weapons load/fire scripting** - no script access today; asked-for feature
  (fire currently only observable via `//launch/missile` / `player_launches_missile`).
- **Add weapons-select routes** (`follow_route_select_weapon`) to match comms/science/grid.
- **science_data_tabs** - `ConsoleDispatcher` converts the tab event to a UID;
  needs to handle the tab in `extra_tag` instead.
- **Docking cancel tractor cleanup** - engine leaves a tractor the script must delete.
- **shield_control event** - consider emitting one (data_set-only today).

---

## Open questions (Doug)
Most are resolved above. Remaining:

1. **(cross-cutting) Which data_set changes ALSO fire a MAST route/event** a mission
   can listen to? For the mock to trigger the right `//` routes it must reproduce
   both the data_set change *and* any event the engine fires.
   Confirmed events so far: `main_screen_change`, `red_alert`, `press_comms_button`,
   `press_grid_button`, `player_launches_missile`, `science_scan_complete`,
   `select_space_object`, `hold_click` / `hold_button_pressed`, plus the select
   routes. Do the *other* data_set writes (throttle, `shields_raised_flag`,
   `dock_state`, coolant/heat, power, beam freq/rate) fire any route/event, or are
   they purely internal (scripts see them only by polling the data_set)?
   Concrete example: when `dock_state` advances, does a `//dock` route fire, or does
   the script poll `dock_state`?
2. **helm_movement native write** - `steerToDir*` was added for autoplay; what does
   the *real* helm widget write for steering? (Only needed for faithful mock
   emulation; a bot can use `steerToDir*`.) Low priority.
3. **quick_jump** delivery - the data_set/event for charge + fwd/back. Niche.
