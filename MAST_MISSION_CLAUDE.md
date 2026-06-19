# MAST Mission Reference for Claude

How to write a complete Artemis Cosmos mission in MAST. Based on SecretMeeting and LegendaryMissions.

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
└── media/              # Optional — images, skyboxes, music
```

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

Top-level code (before any labels) runs **for every client and the server** at startup. Use `shared` variables to share state across tasks. This is where sides and media are set up. Then one `@map/` label defines the playable scenario.

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

The `side_csv` string sets both the side **and** the role(s) for the object.

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

Player ships are pre-created from `PLAYER_LIST` in `settings.yaml`. The `spawn_players` label (from `LegendaryMissions.fleets`) positions them near a friendly station and makes the right number visible based on `PLAYER_COUNT`.

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

Most missions need at minimum: `fleets`, `docking`, `prefabs`, `comms`, `consoles`, `damage`.

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
