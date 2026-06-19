# MAST Mission Reference for Claude

How to write a complete Artemis Cosmos mission in MAST. Based on SecretMeeting, LegendaryMissions, and real missions: HereThereBeMonsters, Infinite_Cosmos, WalkTheLine, Lucky_13, theta_quadrant, MiningDays.

Update this file as new things are confirmed or corrected.

---

## Mission Folder Layout

```
MyMission/
├── script.py           # Required — Cosmos entry point
├── story.mast          # Required — all mission logic
├── story.json          # Required — which .sbslib/.mastlib files to load
├── description.yaml    # Required — appears in mission list
├── settings.yaml       # Optional — runtime defaults (difficulty, players, etc.)
├── media/              # Optional — images, skyboxes, music, audio
└── maps/               # Optional — split large missions into subfolder .mast files
```

Large missions (Infinite_Cosmos, Lucky_13, MiningDays) keep `story.mast` minimal and move `@map/` labels to `maps/` subfolders. The mission's Python import path includes the mission folder, so `.py` helper modules (e.g. `here_helpers.py`, `mission_helper_functions.py`, `terrain_DOUBLE.py`) are importable directly from MAST.

---

## script.py

Boilerplate — nearly identical for every mission:

```python
try:
    import sbslibs
    from sbs_utils.handlerhooks import *
    from sbs_utils.gui import Gui
    from sbs_utils.mast.maststorypage import StoryPage
    from sbs_utils.mast.mast import Mast

    class MyStoryPage(StoryPage):
        story_file = "story.mast"

    Mast.include_code = True   # shows MAST source in runtime errors; comment out to save memory

    Gui.server_start_page_class(MyStoryPage)
    Gui.client_start_page_class(MyStoryPage)
except Exception as e:
    message = e
    def cosmos_event_handler(sim, event):
        import sbs
        sbs.send_gui_clear(event.client_id, "")
        sbs.send_gui_text(event.client_id, "", "text",
                          f"$text:sbs_utils runtime error^{message};", 0, 0, 80, 95)
        sbs.send_gui_complete(event.client_id, "")
```

`import sbslibs` reads `story.json` and adds the listed `.sbslib`/`.mastlib` zip files to `sys.path`. It lives in `PyAddons/sbslibs.py` inside the Cosmos install.

---

## story.json

Lists every library the mission needs. The engine looks for these in a shared `__lib__/` folder next to the missions directory.

```json
{
    "sbslib": [
        "artemis-sbs.sbs_utils.v1.3.0.sbslib"
    ],
    "mastlib": [
        "artemis-sbs.LegendaryMissions.ai.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.comms.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.consoles.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.damage.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.docking.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.fleets.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.prefabs.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.science_scans.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.upgrades.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.gamemaster.v1.3.0.mastlib",
        "artemis-sbs.LegendaryMissions.gamemaster_comms.v1.3.0.mastlib"
    ],
    "resources": {
        "media": "artemis-sbs.LegendaryMissions.media.v1.3.0.zip"
    }
}
```

Add only the LegendaryMissions addons you actually use — each one loads MAST labels into the global namespace.

---

## description.yaml

Shown in the mission browser. Required.

```yaml
format version: 1
Category: Standard
Category Priority: C        # A = top of list, C = standard
Visible Mission Name: My Mission
Description: Short description of the mission.
Keywords: combat, asteroids
```

**Avoid apostrophes in `Visible Mission Name`** — YAML unquoted strings with a single quote require `''` (doubled) to escape, which the engine may render literally. Use a name without apostrophes, or test carefully.

---

## settings.yaml

Provides default values for settings variables that MAST reads via `settings_get_defaults()`. Everything here is optional — the keys just become variables available to MAST.

```yaml
AUTO_START: false
DIFFICULTY: 5
PLAYER_COUNT: 1
PLAYER_SHIP_RESPAWN: false
GAME_TIME_LIMIT: 20         # in minutes — your mission can use this variable

DOCKING:
    refuel_amount: 20
    refuel_delay: 2
    shield_delay: 2
    shield_coeff: 2
    torps_delay: 6
    interior_delay: 2
    interior_count: 2

GAMEMASTER:
    enable: true

# Additional settings used by WalkTheLine, Lucky_13, theta_quadrant:
NEW_DAMCONS: true           # brain-based damage control system
SHIP_PICK_READ_ONLY: false  # allow ship selection changes in lobby
CAN_CHANGE_CONSOLE: true    # allow console switching mid-mission

PLAYER_LIST:
    -   name: "Artemis"
        side: "tsn"
        ship: "tsn_light_cruiser"
        face: "terran"
    -   name: "Intrepid"
        side: "tsn"
        ship: "tsn_battle_cruiser"
        face: "terran"
```

---

## story.mast — Overall Structure

Top-level code (before any labels) runs for every client and the server. However, **`shared` statements at the top level run only once** — after first execution they are converted to no-ops. The server client runs first, so top-level `shared` assignments are effectively server-initialised. Use `shared` for any state that all tasks need to see.

**`@map/` labels are server-only.** Their body executes only on the server when a map is selected, never on connected client consoles.

```
# 1. Shared state
shared phoenix_id = None
shared admiral = lifeform_spawn(...)

# 2. Sides
tsn = await prefab_spawn(prefab_side_generic, data={"key":"tsn", ...})
raider = await prefab_spawn(prefab_side_generic, data={"key":"raider", ...})
side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)

# 3. Media
@media/music/default "Cosmos Default Music"
@media/skybox/sky-bored-alice "borealis"

# 4. Map label (the actual playable scenario)
@map/my_mission "My Mission"
" Short mission description shown to players.
metadata: ``` yaml
Properties:
    Player Ships: 'gui_int_slider("$text:int;low: 1.0;high:8.0;", var= "PLAYER_COUNT")'
    Difficulty: 'gui_int_slider("$text:int;low: 1.0;high:11.0;", var= "DIFFICULTY")'
    Game Length: 'gui_input("desc: Minutes;", var="GAME_TIME_LIMIT")'
```
    # Spawn world
    ...
    # Spawn players
    await task_schedule(spawn_players)
    await task_schedule(docking_standard_player_station)
    # Game loop
    ...
    ->END

# 5. Helper labels
=== send_admiral_message
    ...
    ->END

=== spawn_wave
    ...
    ->END
```

---

## Sides

Use `prefab_side_generic` from the `LegendaryMissions.prefabs` mastlib.

```
tsn = await prefab_spawn(prefab_side_generic, data={"key":"tsn"})
side_set_display_name(tsn, "TSN")
side_set_description(tsn, "The Terran Stellar Navy")
side_set_icon_color(tsn, "#07F")

raider = await prefab_spawn(prefab_side_generic, data={
    "key": "raider",
    "name": "Raider",
    "color": "#F00",
    "desc": "Hostile Aliens"
})

side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)
side_set_relations(tsn, amb_side, sbs.DIPLOMACY.NEUTRAL)

sim.set_diplomacy_color(sbs.DIPLOMACY.HOSTILE, "#F00")
sim.set_diplomacy_color(sbs.DIPLOMACY.NEUTRAL, "#077")
```

`await prefab_spawn(...)` captures the value the prefab yields — here the side's ID. `prefab_side_generic` yields `fail` if the key already exists. Use `await` whenever you need the spawned object/ID back; omit it for fire-and-forget spawns. String name and label reference are interchangeable: `prefab_spawn("prefab_fleet_raider", ...)` and `prefab_spawn(prefab_fleet_raider, ...)` are the same.

---

## Lifeforms

Lifeforms are NPCs used for comms faces, names, etc. Created at top level (shared).

```
shared admiral = lifeform_spawn("Admiral Harkin", "ter #964b00 8 1;ter ...", "admiral")
```

- arg 1: display name
- arg 2: face string (see faces module)
- arg 3: role assigned to this lifeform

Get/set a face:
```
set_face(phoenix_id, random_terran(civilian=True))
face = get_face(admiral.id)
```

---

## Spawning Objects

### NPC ships and stations

```
obj = npc_spawn(x, y, z, "Display Name", "side_csv", "art_id", "behavior")
id = to_id(obj)

# Station example
station = npc_spawn(0, 0, 0, "Starbase Phoenix", "tsn, station", "starbase_civil", "behav_station")

# NPC ship example
ship = npc_spawn(100, 0, -2000, "Praetor of Peace", "ambassador", "tsn_warpster", "behav_npcship")
```

The third argument is a comma-separated **roles** list. The **first role is treated as the side**. Additional roles are extra tags used for querying (e.g. `role("station")`). There is no separate "side" argument.

### Terrain (asteroids etc.)

```
types = ship_data_plain_asteroid_keys()
points = scatter_box(200, 0, 0, 0, 10000, 1000, 10000, True)
for v in points:
    a_type = random.choice(types)
    rock = terrain_spawn(v.x, v.y, v.z, None, "#,asteroid", a_type, "behav_asteroid")
    rock.engine_object.steer_yaw = random.uniform(0.0001, 0.003)
    sx = random.uniform(1.0, 2.0) + 3
    rock.data_set.set("local_scale_x_coeff", sx)
    rock.data_set.set("local_scale_y_coeff", sx)
    rock.data_set.set("local_scale_z_coeff", sx)
    rock.engine_object.exclusion_radius *= sx
```

### Pickup / upgrades

```
points = scatter.box(5, 0, 0, 0, 10000, 1000, 10000, centered=True)
upgrade_list = ["carapaction_coil", "infusion_pcoils", "hidens_powercell"]
for v in points:
    upg = random.randint(0, len(upgrade_list)-1)
    pickup_spawn(v.x, v.y, v.z, upgrade_list[upg])
```

### Hangar craft

```
set_inventory_value(station_id, "HANGAR_ORIGIN_OVERRIDE", "ximni")
for x in range(random.randint(1, 10)):
    hangar_random_craft_spawn(station_id)
```

---

## Player Ships

When `PLAYER_CREATE_DEFAULT: true` in `settings.yaml`, the **LegendaryMissions.fleets** addon pre-creates ships from `PLAYER_LIST` and `spawn_players` positions them near a friendly station, making the right number visible based on `PLAYER_COUNT`.

If `PLAYER_CREATE_DEFAULT: false` (or not using LegendaryMissions at all), the mission script must create and assign player ships manually using `npc_spawn` and `sbs.assign_client_to_ship(client_id, ship_id)`.

```
await task_schedule(spawn_players)                  # position player ships
await task_schedule(docking_standard_player_station) # wire up docking logic

# After spawning, get references to player ships
player_list = to_object_list(role("__player__"))
player_obj = player_list[0]
player_name = player_obj.name
```

---

## Fleets (Enemy Waves)

From `LegendaryMissions.fleets`:

```
=== spawn_wave
    fleet_diff = int(DIFFICULTY - 1)
    fleet_pos = Vec3.rand_in_sphere(3000, 5000, False, True)
    prefab_spawn("prefab_fleet_raider", {
        "race": "skaraan",
        "fleet_difficulty": fleet_diff,
        "START_X": fleet_pos.x,
        "START_Y": fleet_pos.y,
        "START_Z": fleet_pos.z
    })
    ->END
```

`prefab_fleet_raider` creates a fleet and assigns a brain behavior tree automatically. `fleet_difficulty` maps to fleet size (index 0–9).

---

## Scatter / Positioning

```
# Scatter points in a box (centered at x,y,z with half-dimensions dx,dy,dz)
points = scatter_box(count, cx, cy, cz, dx, dy, dz, centered=True)
points = scatter.box(count, cx, cy, cz, dx, dy, dz, centered=True)  # both work

# Random point on a flat ring (y≈0) between min_r and max_r from origin
pos = Vec3.rand_in_sphere(min_r, max_r, include_y=False, flat=True)

# Move an NPC to a position
target_pos(id, x, y, z, throttle, accel, stop_dist)
target_pos(amb_id, 0, 0, 0, 1.0, 0, 200)     # slow approach
target_pos(amb_id, 0, 0, -55200, 50, 0, 0)   # warp out
```

---

## Game End Conditions

```
# Lose conditions (last arg False)
game_end_condition_add(destroyed_all(role("__player__")), "All ships destroyed.", False)
game_end_condition_add(destroyed_any(amb_id), "Ambassador destroyed.", False)
game_end_condition_add(destroyed_any(phoenix_id), "Station destroyed.", False)

# Win condition (last arg True) — add this once the win is reachable
game_end_condition_add(
    distance_point_greater(amb_id, Vec3(0,0,-5200), 500),
    "Mission complete! Congratulations!",
    True
)
```

Conditions are checked every tick. The first one that becomes true ends the game.

---

## Timers

```
set_timer(0, "meeting_count", minutes=20)   # id 0 = server
set_timer(id, "cooldown", seconds=30)

await is_timer_finished(id, "warmup")           # suspend until done
jump loop if not is_timer_finished(0, "meeting_count")  # conditional loop

seconds = get_time_remaining(0, "meeting_count")
t = format_time_remaining(0, "meeting_count")
```

---

## Await Distance

```
await distance_less(id1, id2, 400)                      # two objects
await distance_point_less(id, Vec3(0,0,-5200), 400)     # object vs point
```

---

## Game Loop Pattern

Use an inline `---` label for a loop inside the map body:

```
--- meeting_in_progress
    await delay_sim(seconds_between_waves)

    if not is_timer_finished(0, "meeting_count"):
        task_schedule(spawn_wave)

    jump meeting_in_progress if not is_timer_finished(0, "meeting_count")

--- meeting_adjourned ---
    # Meeting over logic
    ->END
```

---

## Comms Messages (Admiral/NPC)

Pattern: schedule a helper label that sends `sbs.send_story_dialog` to server + all main screens + all player comms.

```
await task_schedule(send_admiral_message, {"the_message": "Enemy incoming!"})

=== send_admiral_message
    default the_message = "You forgot to set the_message"
    face = get_face(admiral.id)
    sbs.send_story_dialog(0, admiral.name, the_message, face, "#444")

    main_screen_client_list = to_object_list(role("mainscreen") & role("console"))
    for c in main_screen_client_list:
        sbs.send_story_dialog(c.client_id, admiral.name, the_message, face, "#444")

    my_players = to_object_list(role("__player__") & role("tsn"))
    comms_message(the_message, my_players, admiral.id)
    ->END
```

---

## Key Roles

| Role | Meaning |
|---|---|
| `__player__` | All active player ships |
| `__side__` | All side agents |
| `station` | Stations |
| `console` | Connected console clients |
| `mainscreen` | Main screen clients |
| `default_player_ship` | All pre-created player slots (including inactive ones) |
| `tsn`, `raider`, etc. | Side membership — set via `npc_spawn`'s side_csv |

---

## sbs.DIPLOMACY Values

- `sbs.DIPLOMACY.HOSTILE`
- `sbs.DIPLOMACY.NEUTRAL`
- `sbs.DIPLOMACY.ALLIED`

`sim` and `sbs` are always available as implicit globals in MAST — no import needed.

---

## data_set vs blob

`obj.data_set` and `obj.blob` are the same underlying object. Always use `data_set`; `blob` is a legacy jargon alias.

```
obj.data_set.set("local_scale_x_coeff", 2.5)
obj.data_set.set("ally_list", "tsn,good_dudes", 0)
```

The complete list of valid property names, types, and descriptions is in:
`f:/a/Cosmos-1-3-0/data/object_data_documentation.txt`

Read that file when you need to know what `data_set` properties exist for ships, stations, terrain, or other space objects.

---

## __lib__.json

Each mission has a `__lib__.json` with just a version string:

```json
{"version": "v1.3.0"}
```

This is used only by the `sbs.pyz` packaging tool to tag what version of the library the mission was built against. It has no runtime effect but may be used for compatibility checking in the future.

---

## Tool-as-Mission Pattern

A mission does not need gameplay. modding_tools is a pure developer tool — no sides, no combat, no game end — just a server-side GUI. Use a plain `==` label as the entry point:

```mast
==== server_start
    sbs.suppress_client_connect_dialog(0)
    sbs.transparent_options_button(0, 1)
    sim_create()      # procedural wrapper for sbs.create_new_sim()
    sim_resume()      # procedural wrapper for sbs.resume_sim()

    gui_section("area: 0, 0, 100, 100;")
    on gui_message(gui_button("Open Editor")):
        jump editor_show
    await gui()
```

No `@map/` label required. Minimal `story.json` — only the sbslib. `assign_client_to_ship(client_id, ship_id)` is the procedural wrapper for `sbs.assign_client_to_ship`.

### File I/O helpers

```mast
data = load_json_data(filename)                             # parse JSON from file
save_json_data(filename, data)                              # write JSON to file
save_json_data(filename + ".bak", data)                    # backup before overwrite

get_mission_dir_filename("grid_data.json")                  # path relative to mission folder
get_artemis_data_dir_filename("grid_data.json")             # path in Artemis data folder
get_mission_has_grid_data()                                 # True if mission has grid_data.json
get_mod_dirs_with_grid_data()                               # list of mods with grid data
copy_clipboard(text)                                        # copy string to clipboard
```

---

## Console Wiring

### With LegendaryMissions

The `LegendaryMissions.consoles` mastlib provides standard `@console/` decorator labels (helm, weapons, science, engineering, comms, main screen, etc.). Loading it is sufficient — clients are routed to the right console automatically.

Mission scripts can extend this by defining additional `@console/` labels for new console types.

### Without LegendaryMissions

Route server and clients to specific labels manually:

```
gui_reroute_server("start_server")      # server runs this label
gui_reroute_clients("launch_to_cockpit") # each client runs this label

=== start_server
    sbs.create_new_sim()
    # spawn world...
    sbs.resume_sim()

==== launch_to_cockpit
    sbs.assign_client_to_ship(client_id, ship_id)
    # build GUI layout...
    await gui()
```

`gui_reroute_client(client_id, "label")` can re-route a specific client mid-mission (e.g. when docking).

---

## LegendaryMissions Addon Reference

| Mastlib | Key Labels Provided |
|---|---|
| `fleets` | `spawn_players`, `prefab_fleet_raider`, `prefab_fleet_empty` |
| `docking` | `docking_standard_player_station`, `docking_dock_with_friendly_station` |
| `prefabs` | `prefab_side_generic`, station/terrain prefabs |
| `comms` | Enemy taunt/surrender comms, player comms menus |
| `ai` | Brain behaviors (`ai_fleet_chase_roles`, etc.) |
| `consoles` | Standard helm/weapons/science/etc. console layouts |
| `damage` | `//damage/destroy` handlers for ships/stations |
| `upgrades` | Pickup/upgrade collection handlers |
| `science_scans` | Science scan response handlers |
| `gamemaster` | GM console, spawn tools |
| `gamemaster_comms` | GM comms menus (messages, spawn, map) |
| `hangar` | Landing bay, bar, hangar comms |
| `internal_comms` | Crew department comms (sickbay, security, etc.) |
| `operator` | Operator/admin console for venue use |

Truly optional (omit unless needed): `autoplay`, `commerce`, `operator`, `gamemaster`, `gamemaster_comms`.

Minimum for a standard multi-console Artemis mission: `fleets`, `docking`, `prefabs`, `comms`, `consoles`, `damage`.

A mission can also skip LegendaryMissions entirely and handle everything itself — console routing via `gui_reroute_server`/`gui_reroute_clients`, player ships via `npc_spawn` + `sbs.assign_client_to_ship`, custom GUI layouts. MiningDays is an example of this (its `story.json` has only the sbslib, no mastlibs).

---

## Terrain — Higher-Level Helpers

Beyond the manual `terrain_spawn()` loop, procedural helpers exist for common patterns:

```
# Asteroid fields
terrain_spawn_asteroid_box(cx, cy, cz, size_x=40000, size_z=15000, density_scale=3.0, density=3, height=2000, selectable=True)
terrain_spawn_asteroid_sphere(cx, cy, cz, radius=7500, density_scale=2.0, density=2, height=2000, selectable=True)
terrain_spawn_asteroid_scatter(points, height=500)   # from a pre-computed scatter list

# Nebula
terrain_spawn_nebula_sphere(cx, cy, cz, radius=12000, density_scale=3.0, density=3, height=3500, cluster_color="red", selectable=False)

# Ring scatter (useful for minefields)
points = scatter_ring(width, depth, cx, cy, cz, inner_r, inner_r, start_angle, end_angle)
for v in points:
    mine = terrain_spawn(v.x, v.y + random.randrange(-300,300), v.z, None, None, "danger_1a", "behav_mine")
    mine.data_set.set("damage_done", 5)
    mine.data_set.set("blast_radius", 1000)
```

---

## Tile Map System

For structured procedural worlds, use the tile-map system (HereThereBeMonsters, theta_quadrant). Define "decks" of terrain prefabs, map them to characters, fill from an ASCII art string.

```
tile_map = maps_tile_map_create(0, 100_000, 1_000, 2_000)  # (id, map_size, cell_x, cell_z)

# Define decks — each deck is a weighted set of terrain prefabs
nebula_deck = maps_deck_create()
nebula_deck.add_card(prefab_terrain_nebula_sphere, {"density": 0.5, "cluster_color": "red", "marker": False})

black_hole_deck = maps_deck_create()
black_hole_deck.add_card(prefab_black_hole, {"gravity_radius": 10_000})

# Map characters to decks
tile_map.map_deck("n", nebula_deck)
tile_map.map_deck("b", black_hole_deck)

# Fill — map_art is an ASCII string (often imported from a separate .mast file)
res = await tile_map.fill(map_art, x_count=100)

# Result is a role set of everything spawned
res &= role("black_hole")   # filter to specific objects
```

The ASCII art string defines the map layout. Spaces and unknown characters are skipped. Each character maps to one deck. theta_quadrant uses 16 separate tile_map calls with different cell sizes (5_000–25_000) for different sectors of space.

---

## Science: Extra Scan Sources

Link NPC objects to a player ship so science can scan them:

```
link(artemis_id, "extra_scan_source", whale_watcher_id)
link(artemis_id, "extra_scan_source", friendly_station_id)
```

Multiple objects can be linked to the same ship. This is how narrative missions (HereThereBeMonsters) surface lore via the science console.

---

## Lifeform Hosting

Attach a lifeform NPC to a player ship as crew (appears in interior views):

```
ensign_rachel.host = artemis_id
```

---

## Audio

HereThereBeMonsters plays audio files tied to comms scenes:

```
sbs.play_audio_file(0, get_mission_audio_file("audio/SD02C0166"), 1.0, 1.0)
```

`get_mission_audio_file(path)` resolves relative to the mission's `media/` folder. Controlled via a shared config flag — let the player disable audio if needed:

```
shared HTBM_AUDIO_FILE_ENABLED = True   # top-level default

# Before playing:
if HTBM_AUDIO_FILE_ENABLED:
    sbs.play_audio_file(0, get_mission_audio_file(audio_path), 1.0, 1.0)
```

---

## Custom Prefabs in story.mast

You can define local prefabs directly in story.mast using metadata-driven labels. These work like LegendaryMissions prefabs but live in the mission:

```
=== prefab_civil_arvonian
metadata: ``` yaml
display_text: Arvonian Civilian Station
station_type: starbase_arvonian
side: arvonian
```
    obj = npc_spawn(START_X, START_Y, START_Z, display_text, side, station_type, "behav_station")
    yield result to_id(obj)

=== prefab_fighter_for_this_mission
metadata: ``` yaml
side: tsn
roles: cockpit
art: tsn_fighter
level: 1
```
    craft = player_spawn(START_X, START_Y, START_Z, NAME, "", art)
    craft.py_object.add_role(roles)
    yield result craft
```

---

## Promise Patterns

### Race with timeout

`promise_any` resolves with whichever promise finishes first — useful for "button OR timeout" flows:

```
choice = gui_button("Confirm")           # returns a promise
pressed = await promise_any(choice, delay_sim(10))
```

If the user doesn't click within 10 seconds, `delay_sim(10)` wins and `pressed` is the timeout result. Check which one resolved to decide what to do.

### Win condition from distance (added mid-mission)

```
# Add win condition only once the win is actually reachable
await distance_point_less(amb_id, Vec3(0,0,-5200), 400)
game_end_condition_add(
    distance_point_greater(amb_id, Vec3(0,0,-5200), 500),
    "Mission complete!",
    True
)
```

`game_end_condition_add` requires a `Promise` / `TestPromise` object. `destroyed_all`, `destroyed_any`, `distance_less`, `distance_greater`, `distance_point_less`, `distance_point_greater` are all `@awaitable` and return `TestPromise`. `is_timer_finished` returns a plain bool — **do not** pass it to `game_end_condition_add`.

---

## Timer-Based Win (Without a Promise)

`is_timer_finished` returns a bool, not a promise. For timer-based game end, use a polling loop that manually sets the result:

```
--- defense_in_progress
    await delay_sim(seconds_between_waves)
    if seconds < milestone:
        task_schedule(spawn_wave)
        milestone -= seconds_between_waves
    jump defense_in_progress if not is_timer_finished(0, "defense_timer")

    START_TEXT = "Mission complete!"
    GAME_STARTED = False
    GAME_ENDED = True
    sbs.play_music_file(0, "music/default/victory")
    signal_emit("show_game_results", None)
    ->END
```

`START_TEXT`, `GAME_STARTED`, `GAME_ENDED` are shared variables set by the consoles mastlib's `start_server` label — write to them directly to communicate game state.

---

## Console Filtering with `linked_to`

`linked_to(ship_id, "consoles")` returns the set of console clients linked to a specific ship. Combine with role sets to target messages precisely:

```
consoles = linked_to(artemis_id, "consoles") & all_roles("console, comms")
for c in to_object_list(consoles):
    sbs.send_story_dialog(c.client_id, name, message, face, "#444")
```

---

## Custom Console Labels

Mission scripts can add new `@console/` labels beyond the LegendaryMissions defaults. Use `on change <expression>:` for reactive GUI that updates when a data value changes:

```
@console/alert_condition !0 ^10 "Alert Condition"
    " Display the alert status of this ship
    gui_section(style="area: 0, 0, 100, 76;")
    ship_id = sbs.get_ship_of_client(client_id)
    image = "RedAlert" if get_data_set_value(ship_id, "red_alert", 0) >= 1 else "AllClear"
    on_screen = gui_image_keep_aspect_ratio_center(get_mission_dir_filename(image))

    on change get_data_set_value(ship_id, "red_alert", 0):
        alert_state = get_data_set_value(ship_id, "red_alert", 0)
        image = "RedAlert" if alert_state >= 1 else "AllClear"
        on_screen.update(f"image:{get_mission_dir_filename(image)}")
        # gui_represent(on_screen)  # deprecated — dirty system handles re-render automatically

    await gui()
```

`get_mission_dir_filename(filename)` resolves a path relative to the mission folder (for loading local images).

---

## Debug Pattern

HereThereBeMonsters keeps a `debug.mast` with dev-only comms routes. Store the main task reference in a shared variable, then use `mast_task.jump("label_name")` in debug comms to teleport to any narrative chapter:

```
# In @map body:
shared main_story_task = mast_task

# In debug.mast:
//comms/chapters if main_story_task
    + "scene_distress_call_one":
        main_story_task.jump("scene_distress_call_one")
    + "salvage":
        main_story_task.jump("salvage")

//enable/comms if is_dev_build()
```

Gate debug routes with `is_dev_build()` so they only appear in development builds.

---

## Fleet Race Selection

WalkTheLine picks enemy races based on difficulty with weighted random selection:

```
=== spawn_wave
    enemy_races = ["Kralien", "Torgoth", "Arvonian", "Ximni"]
    weights = (100-6*DIFFICULTY, DIFFICULTY*2, DIFFICULTY*2, DIFFICULTY*2)
    enemy = random.choices(enemy_races, weights=weights)[0]
    fleet_pos = Vec3.rand_in_sphere(10000, 30000, False, True) + target_pos
    prefab_spawn(prefab_fleet_raider, {
        "race": enemy,
        "fleet_difficulty": DIFFICULTY,
        "START_X": fleet_pos.x,
        "START_Y": fleet_pos.y,
        "START_Z": fleet_pos.z
    })
    ->END
```

---

## LegendaryMissions Mastlib Usage by Mission Type

| Mission Type | Typical Mastlib Set |
|---|---|
| Narrative (story-driven, few enemies) | ai, comms, consoles, damage, docking, prefabs, science_scans |
| Standard multi-console combat | + fleets, upgrades, basic_player_destroy |
| Full sandbox | + commerce, hangar, internal_comms, gamemaster, gamemaster_comms, operator |
| No LegendaryMissions | sbslib only — handle everything manually |

The `side_missions` mastlib (theta_quadrant) adds structured optional objectives — include it for missions with branching side content.

---

## Creating an Addon (Mastlib)

An addon is a **subfolder with `__init__.mast`** inside the mission folder. It provides labels (consoles, comms routes, prefabs, etc.) that become globally available to any mission that loads it. Display_Panels is the canonical example.

### Folder structure

```
MyAddon/                        # the mission (dev harness)
├── script.py                   # standard boilerplate
├── story.mast                  # minimal test harness — NOT the addon itself
├── story.json                  # sbslib + any mastlibs the addon depends on
├── __lib__.json                # declares the addon folder for sbs.pyz packager
└── my_addon/                   # THE ADDON — this becomes my_addon.mastlib
    ├── __init__.mast           # entry point — imports other .mast files
    ├── panels.mast             # content
    └── helpers.mast            # more content
```

### `__lib__.json` for an addon

```json
{
    "version": "v1.3.0",
    "mastlib": ["my_addon"]
}
```

The `mastlib` list names the local subfolder(s) that make up the library. `sbs.pyz` packages each into a `.mastlib` zip for distribution.

### `__init__.mast`

```mast
import panels.mast
import helpers.mast
```

Just imports. The MAST runtime discovers and compiles this when the addon folder is on the search path.

### Test harness (`story.mast`)

Keep it minimal — just enough to exercise the addon:

```mast
PLAYER_CREATE_DEFAULT = False
PLAYER_COUNT = 1

//shared/signal/create_player_ships
    shared player = to_object(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
    ->END

@map/test "Test Map"
" A map to test the addon.
    npc_spawn(*Vec3(1000, 0, 1000), "DS 1", "tsn, station", "starbase_command", "behav_station")
    docking_set_docking_logic(player.id, role(player.side) & role("station"), docking_dock_with_friendly_station)
```

Note `PLAYER_CREATE_DEFAULT = False` + `//shared/signal/create_player_ships` route — this is how you manually create a player ship without the LegendaryMissions fleets addon.

### Watch / repaint pattern (live GUI updates)

The standard pattern for a panel that polls live ship data and repaints when it changes:

```mast
=== my_panel
--- repaint
    ship_id = sbs.get_ship_of_client(client_id)
    alert_state = get_data_set_value(ship_id, "red_alert", 0)
    prev_alert_state = alert_state

    # ... build GUI here ...
    gui_section(style=f"area: 10, 10, 90, 90; background:{'RED' if alert_state else 'GREEN'}")

    gui_sub_task_schedule("watch")   # starts a watcher that ends when a new GUI is shown
    await gui()

--- watch
    await delay_sim(1)
    ->END if not object_exists(ship_id)
    alert_state = get_data_set_value(ship_id, "red_alert", 0)
    if alert_state != prev_alert_state:
        gui_task_jump("repaint")     # redirect GUI task to repaint
    jump watch
```

- **`gui_sub_task_schedule("label")`** — starts a sub-task on the GUI task; auto-cancelled when a new GUI is presented to this client
- **`gui_task_jump("label")`** — redirects the console's GUI task to a label; used by the watcher to force a repaint when state changes
- **`object_exists(id)`** — returns False if the object has been destroyed; use as a watcher guard
- **`get_data_set_value(ship_id, "property", default)`** — procedural read of a data_set value by name

### Development vs distribution

During development, the addon folder lives inside the mission directory and is picked up automatically (the mission dir is on the MAST search path). For another mission to use it:
1. Package with `sbs.pyz` → produces `my_addon.mastlib`
2. Place in `__lib__/` alongside the missions
3. Add to the mission's `story.json` mastlib list

### Useful helpers

```mast
# Unpack a Vec3 as positional x,y,z args
npc_spawn(*Vec3(1000, 0, 1000), "Name", "tsn, station", "starbase_civil", "behav_station")

# Configure which docking label fires for a player/station pair
docking_set_docking_logic(player_id, role("tsn") & role("station"), docking_dock_with_friendly_station)
```

---

## Minimal Working Mission Skeleton

```
# story.mast

shared my_station_id = None

# Side setup
tsn = await prefab_spawn(prefab_side_generic, data={"key":"tsn", "name":"TSN", "color":"#07F"})
raider = await prefab_spawn(prefab_side_generic, data={"key":"raider", "name":"Raider", "color":"#F00"})
side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)

@media/music/default "Cosmos Default Music"
@media/skybox/sky-bored-alice "borealis"

@map/my_mission "My Mission"
" Fight off enemy raiders.
metadata: ``` yaml
Properties:
    Player Ships: 'gui_int_slider("$text:int;low: 1.0;high:8.0;", var= "PLAYER_COUNT")'
    Difficulty: 'gui_int_slider("$text:int;low: 1.0;high:11.0;", var= "DIFFICULTY")'
```
    my_station_id = to_id(npc_spawn(0,0,0, "Home Base", "tsn, station", "starbase_civil", "behav_station"))

    await task_schedule(spawn_players)
    await task_schedule(docking_standard_player_station)

    game_end_condition_add(destroyed_all(role("__player__")), "All ships lost.", False)
    game_end_condition_add(destroyed_any(my_station_id), "Station destroyed.", False)

    task_schedule(spawn_wave)

--- game_loop
    await delay_sim(120)
    task_schedule(spawn_wave)
    jump game_loop

=== spawn_wave
    fleet_pos = Vec3.rand_in_sphere(3000, 6000, False, True)
    prefab_spawn("prefab_fleet_raider", {
        "race": "skaraan",
        "fleet_difficulty": int(DIFFICULTY - 1),
        "START_X": fleet_pos.x,
        "START_Y": fleet_pos.y,
        "START_Z": fleet_pos.z
    })
    ->END
```

---

## PyMAST Missions (Python-only, no .mast file)

Some missions (e.g. `remote_mission_pick`) write all logic in Python using the `@label()` decorator. This is called **PyMAST**.

### When to use

- Tool-style missions: mission pickers, admin consoles, debug launchers
- When Python logic would be awkward to express in MAST syntax
- No `.mast` file needed — `story = MastStory()` is an empty placeholder

### `script.py` pattern (all-in-one)

```python
from sbs_utils.mast.label import label
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural.execution import AWAIT, jump, get_shared_variable, set_shared_variable
from sbs_utils.procedural.timers import timeout
from sbs_utils.procedural.cosmos import sim_create, sim_resume
from sbs_utils.procedural.gui import gui_list_box, gui_message_callback, gui, gui_section, gui_text

@label()
def main_gui():
    sim_create()
    sim_resume()
    items = build_item_list()
    lb = gui_list_box(items, "", item_template=render_item, select=True)

    def on_select(event, sender):
        idx = lb.get_selected_index()
        if idx is not None:
            set_shared_variable("selected", items[idx])

    gui_message_callback(lb, on_select)
    yield AWAIT(gui({"confirm": confirm}))

@label()
def confirm():
    selected = get_shared_variable("selected")
    if selected is not None:
        sbs.run_next_mission(selected.get("name"))
    yield AWAIT(gui({"back": main_gui}, timeout=timeout(10)))
    yield jump(main_gui)

class SimpleAiPage(StoryPage):
    story = MastStory()
    main_server = main_gui
    main_client = main_gui

Gui.server_start_page_class(SimpleAiPage)
Gui.client_start_page_class(SimpleAiPage)
```

### MAST vs PyMAST

| MAST | PyMAST |
|---|---|
| `await gui({"btn": label})` | `yield AWAIT(gui({"btn": label_fn}))` |
| `jump label_name` | `yield jump(label_fn)` |
| `await delay_sim(5)` | `yield AWAIT(delay_sim(5))` |
| `shared x = val` | `set_shared_variable("x", val)` |
| Read shared | `get_shared_variable("x")` |
| `on gui_message(widget):` | `gui_message_callback(widget, fn)` |

### `MastDataObject` — dict wrapper

Wraps a plain dict so keys become attributes. Always use `.get()` for safe reads — `obj["key"]` raises `TypeError`:

```python
item = MastDataObject({"name": "ClaudeTest", "category": "Standard"})
item.name              # "ClaudeTest"
item.get("desc", "")   # "" (safe default)
```

### `story.json` for PyMAST

Typically only the sbslib is needed:

```json
{
    "sbslib": ["artemis-sbs.sbs_utils.v1.3.0.sbslib"]
}
```

### Parsing `description.yaml` in Python

When iterating mission folders in Python (e.g. to build a mission picker), check `description.yaml` first (current format), then fall back to `description.txt` (deprecated):

```python
from sbs_utils import yaml

yaml_path = os.path.join(dir, file, "description.yaml")
txt_path = os.path.join(dir, file, "description.txt")
if os.path.isfile(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f) or {}
    category = data.get("Category", "")
    desc = data.get("Description", "")
elif os.path.isfile(txt_path):
    lines = open(txt_path).readlines()
    category = lines[0] if lines else ""
    desc = lines[1] if len(lines) > 1 else ""
```
