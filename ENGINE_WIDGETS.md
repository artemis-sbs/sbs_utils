# Engine Gameplay Widgets — interaction reference (FILL-IN)

> Companion to [AUTOPLAY_PLAN.md](AUTOPLAY_PLAN.md). These are the **engine
> gameplay widgets** streamed via `send_client_widget_list` (helm/weapons/science/
> comms/eng consoles) — distinct from `send_gui_*` layout widgets driven by
> `on gui_message`. They are a separate interaction channel the mock does **not**
> emulate yet, and the test-mode autoplayer must be able to drive.
>
> Names + descriptions seeded from `data/GUIWidgetList.txt`; per-console grouping
> from `procedural/gui/console.py`. **Doug to fill the `>` fields.**

## What I need per interactive widget

For each widget a player can *act on*, I want:

1. **User actions** — the discrete things a player does (e.g. "select target",
   "load tube 1 with homing", "fire", "set beam frequency", "raise shields").
2. **Delivery to script/sim** — for each action, how does it surface?
   - **Event/route**: which MAST route fires and the event fields — `tag`,
     `sub_tag`, `value_tag`, `sub_float`, `selected_id`/`origin_id` (e.g.
     `//select/...`, `//point/...`, `//launch/missile`, `//focus/...`,
     `console/change`). This is the engine→script signal.
   - **data_set write**: which key(s) the interaction sets, and value/range
     (e.g. `playerThrottle` 0–5, `shield_state` 0/1, `weapon_load_type`...).
   - Both, or neither (engine-internal only)?
3. **Sets selection?** — does it set a selection UID (`weapon_target_UID`,
   `science_target_UID`, `grid_selected_UID`, `comms_target_UID`)?
4. **Procedural entry** — any existing `sbs_utils` function that drives it
   (I've pre-filled guesses marked *(confirm)*), or "none — event/data_set only".
5. **Notes/quirks.**

Legend: **[I]** interactive · **[D]** display-only (no fill needed) ·
*(confirm)* = my guess, please verify.

---

## HELM (`normal_helm`)
`2dview ^ radar_zoom_ctrl ^ helm_movement ^ helm_jump ^ quick_jump ^ throttle ^ request_dock ^ shield_control ^ ship_data ^ text_waterfall ^ main_screen_control`

### [I] helm_movement — steer the ship
- Desc: steers the ship per the player's chosen option (normal capital ships).
- User actions: > 
- Delivery (event/route and/or data_set key): > _(autoplay writes `steerToDirDX/DY/DZ` + `steeringToDirFlag` — is that the real helm path, or does the widget write something else?)_
- Sets selection: > 
- Procedural entry: > none? *(confirm)*
- Notes: > 

### [I] throttle — set speed
- Desc: vertical speed control.
- User actions: > 
- Delivery: > _(autoplay writes `playerThrottle` 0–5; confirm that's the widget's write and the range/semantics, incl. warp >1.0)_
- Procedural entry: > none? *(confirm)*
- Notes: > 

### [I] helm_jump — jump drive
- User actions: > 
- Delivery: > 
- Notes: > 

### [I] quick_jump — instant ximni jump fwd/back (+ cooldown)
- User actions: > 
- Delivery: > 
- Notes: > 

### [I] request_dock — request dock / undock
- User actions: > 
- Delivery: > _(data_set `dock_state`? a route? both?)_
- Procedural entry: > docking_* helpers? *(confirm)*
- Notes: > 

### [I] shield_control — toggle shields up/down
- User actions: > 
- Delivery: > _(data_set key? `shield_state`/`shield_up`? a route?)_
- Notes: > 

### [I] main_screen_control — control main-screen view
- User actions: > 
- Delivery: > _(sets `MAIN_SCREEN_VIEW/FACING/MODE`? via event or data_set?)_
- Notes: > 

### [I] radar_zoom_ctrl — 2D radar zoom buttons
- User actions: > 
- Delivery: > _(client-local view only, or script-visible?)_
- Notes: > 

### [I] 2dview — 2D radar (click to select?)
- User actions: > _(does clicking an object here set the helm/nav selection or fire a `//select`/`//point` route?)_
- Delivery: > 
- Sets selection: > 
- Notes: > 

- [D] ship_data, text_waterfall — display only.

---

## WEAPONS (`normal_weap`)
`weapon_2d_view ^ radar_zoom_ctrl ^ weapon_control ^ weap_beam_freq ^ weap_beam_speed ^ weap_torp_conversion ^ ship_data ^ shield_control ^ text_waterfall ^ main_screen_control`

### [I] weapon_control — load / unload / fire torpedoes
- Desc: load, unload and fire torpedoes.
- User actions: > _(select tube? choose torp type? load/unload/fire?)_
- Delivery: > _(does firing emit `//launch/missile`? what event fields? what data_set keys for load type/tube?)_
- Sets selection: > 
- Procedural entry: > `torpedoes.py` helpers? *(confirm what exists)*
- Notes: > 

### [I] weapon_2d_view — select weapons target (click)
- User actions: > 
- Delivery: > _(`//select` route? fires like follow_route_select_weapon?)_
- Sets selection: > `weapon_target_UID` *(confirm)*
- Procedural entry: > `set_weapons_selection` / there is no `follow_route_select_weapon` (only comms/science/grid) — confirm how weapons selection is normally driven
- Notes: > 

### [I] weap_beam_freq — set beam frequency
- User actions: > 
- Delivery: > _(data_set key + range?)_
- Notes: > 

### [I] weap_beam_speed — set beam speed (slow=full dmg, fast=less)
- User actions: > 
- Delivery: > _(data_set key + range?)_
- Notes: > 

### [I] weap_torp_conversion — trade torpedo ↔ energy
- User actions: > 
- Delivery: > 
- Notes: > 

- [I] shield_control, radar_zoom_ctrl, main_screen_control — see HELM.
- [D] ship_data, text_waterfall — display only.

---

## SCIENCE (`normal_sci`)
`science_2d_view ^ radar_zoom_ctrl ^ ship_data ^ science_data_freq ^ science_data_tabs ^ text_waterfall ^ science_data ^ science_sorted_list`

### [I] science_sorted_list — select object for science
- User actions: > 
- Delivery: > fires the select route. *(confirm)*
- Sets selection: > `science_target_UID` *(confirm)*
- Procedural entry: > `set_science_selection` / `follow_route_select_science` *(confirm)*
- Notes: > 

### [I] science_2d_view — select by clicking the radar
- User actions: > 
- Delivery: > 
- Sets selection: > 
- Notes: > 

### [I] science_data_tabs — switch data tab
- User actions: > _(does selecting a tab fire an event or just change client view? does it trigger a scan?)_
- Delivery: > 
- Notes: > 

### [I] science_data_freq — scan / frequency interaction?
- User actions: > _(is this interactive — initiate scan / read freq — or display?)_
- Delivery: > 
- Notes: > 

- [I] radar_zoom_ctrl — see HELM.
- [D] ship_data, text_waterfall, science_data — display only.
- Scan note: > how is a **scan initiated** and **completed** (data_set `cur_scan_percent`/`science_scan_complete`/`science_auto_scan`)? Which action starts it?

---

## ENGINEERING (`normal_engi`)
`ship_internal_view ^ eng_presets ^ grid_object_list ^ grid_face ^ grid_control ^ text_waterfall ^ eng_heat_controls ^ eng_power_controls ^ ship_data`

### [I] eng_power_controls — power sliders for systems
- User actions: > 
- Delivery: > _(data_set keys per system + range? event?)_
- Notes: > 

### [I] eng_heat_controls — coolant dot buttons + heat values
- User actions: > 
- Delivery: > 
- Notes: > 

### [I] eng_presets — store/recall engineering presets
- User actions: > 
- Delivery: > 
- Notes: > 

### [I] grid_object_list — select a grid object
- User actions: > 
- Delivery: > fires select route. *(confirm)*
- Sets selection: > `grid_selected_UID` *(confirm)*
- Procedural entry: > `set_grid_selection` / `follow_route_select_grid` *(confirm)*
- Notes: > 

### [I] grid_control — command grid objects (button list)
- User actions: > 
- Delivery: > _(`//object/grid`? `press_grid_button`? event fields?)_
- Notes: > 

### [I] ship_internal_view — interior grid view (click select?)
- User actions: > _(click a grid object/point to select? fires `//point`/`//select/grid`?)_
- Delivery: > 
- Notes: > 

- [D] grid_face, ship_data, text_waterfall — display only.

---

## COMMS (`normal_comm`)
`comms_2d_view ^ radar_zoom_ctrl ^ text_waterfall ^ comms_waterfall ^ comms_control ^ comms_face ^ comms_sorted_list ^ ship_data ^ red_alert`

### [I] comms_sorted_list — select comms target
- User actions: > 
- Delivery: > fires select → opens comms. *(confirm)*
- Sets selection: > `comms_target_UID` *(confirm)*
- Procedural entry: > `set_comms_selection` / `follow_route_select_comms` *(confirm)*
- Notes: > 

### [I] comms_control — comms command buttons (send commands)
- User actions: > _(press a comms button)_
- Delivery: > _(how does a button press surface — `gui_message` with the button tag, or an engine event? this drives whether the bot synthesizes gui_message or calls comms_navigate)_
- Procedural entry: > `comms_navigate` / `comms_navigate_override` for nav; button press = ? *(confirm)*
- Notes: > 

### [I] comms_2d_view — select by clicking radar
- User actions: > 
- Delivery: > 
- Notes: > 

### [I] red_alert — toggle red alert
- User actions: > 
- Delivery: > data_set `red_alert` 0/1? event? *(confirm)*
- Notes: > 

- [I] radar_zoom_ctrl — see HELM.
- [D] comms_face, comms_waterfall, ship_data, text_waterfall — display only.

---

## MAIN SCREEN / VIEWS

- [I] main_screen_control — see HELM.
- [D] 3dview, 3dview_camera — 3D out-the-front / manual-beam view (display; any click interaction?).
- [D] ship_internal_view, text_waterfall, ship_data.

### Alternate helm widgets (not in default lists — when used?)
- helm_normal, helm_simple, helm_free_3d, helm_restrained_3d, fighter_control —
  > when are these substituted, and do they deliver via the same data_set keys
  as `helm_movement`/`throttle`, or different ones?

---

## Cross-cutting questions

1. For interactions that fire a **route**, is the canonical headless driver the
   `_follow_route_console` pattern (synthesize `FakeEvent` → `ConsoleDispatcher`),
   or is there a per-action proc?
2. For interactions that only **write data_set**, can the test bot just write the
   key (like autoplay does for throttle/steer), and will the engine react the same
   as a real widget? Any keys that need an accompanying event to take effect?
3. Which of these does the **real engine** turn into MAST-visible events vs handle
   internally (so the mock knows what it must synthesize vs can ignore)?
