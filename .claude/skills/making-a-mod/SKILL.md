---
name: making-a-mod
description: Building an Artemis Cosmos MOD - content the game does not ship (new hulls and their ship data, art and the paxmesh/sprite bake, faces and portraits, interiors, fleet ladders, races, music/skybox media) delivered as a flat mastlib plus a media pack, never by overwriting files in the install. Covers declaring custom hulls (`ship_data_add_extra` / `add_extra`, the `EXTRA_SHIP_DATA` setting, the HJSON file rules, `artfileroot` spelling), the silent ways a hull reaches the library but not the engine, the `unknown` placeholder hull, `MemoryError: bad allocation` on spawn, mod art showing on the server but stock art on clients (`RACE_ART` / `ART_KEYS` / `RACE_FACES`), NPC interiors, and laying out a mod repo like Cosmos-TNG-Mod. Use when creating or restructuring a mod, adding ships/art/faces/interiors to one, declaring custom hulls, debugging a hull that draws `unknown` or spawns with no stats, a MemoryError / access violation on spawn, client-vs-server art differences, or baking mod art.
---

A Cosmos mod adds content **without editing a single file in the install**. Replacing
`data/shipData.yaml` / `grid_data.json` / `preferences.json` is how older mods shipped, and
measured on a real one it deleted five stock ships and reverted twenty-two more (the copy was
from an older build). A mod that DECLARES can only add what it means to add.

Reference layout: `data/missions/Cosmos-TNG-Mod` (51 hulls, seven factions, interiors,
ladders, faces, portraits, music, skyboxes). Smaller sibling: `Anime-Fan-Mod` (6 hulls, not a
git repo). Each has a separate test-range mission (`TNG_TestRange`, `Anime_TestRange`).

Covered elsewhere - read, do not repeat:

- The `packaging-and-release` skill - `sbs.pyz lib`, `__lib__.json`, `story.json`, flat
  mastlibs, media pack naming/unpacking, the CRLF trap, rereleasing. Mod repos commit to
  `main` directly.
- The `writing-a-mission` skill - addons, `provides`/`requires`/`suggests`, prefixing addon
  functions, prefabs, fleets.
- The `art-pipeline` skill - making the OBJ + textures themselves (Blender, Synty,
  primitives, skyboxes).
- The `engine-debugging` skill - running the exe, `debug.log`, the crash ledger
  (`HCDraw3DShip`, `ObjectDataBlob`, `CreateIndexList`).
- `mkdocs/docs/build/making-a-mod.md` - the user-facing guide (the Driftwake example).
  **Its Art section is stale** - see "Art" below.

---

## The one idea: who opens it?

The split is not "art vs code". It is **which reader opens the file**.

| Read by | Goes in | Why |
|---|---|---|
| **MAST** - `.mast`, `.py`, `.grid`, fleet `.yaml`, `.amd`, face/portrait name lists, manifest | a **flat mastlib** | MAST reads inside the zip (`media_read_relative_file`) |
| **The engine** - ship-data file, meshes, textures, sprites, portrait/face PNGs, music, skyboxes | a **media pack** | the engine opens real files on disk and cannot read into a zip; the pack is unpacked once to `__lib__/media/<owner>.<repo>.media.<tag>/` |

```
Cosmos-TNG-Mod/
  __lib__.json      {"version":"v0.2.3","mastlib":["tng_races","tng_reskin"],"zip":["media"]}
  settings.yaml     EXTRA_SHIP_DATA: true   (only for running the mod as its OWN mission)
  story.json        sbslib + its own mastlib + shared_media, like any consumer
  story.mast, maps/ ship viewer and bake map (maps/tng_ships.mast)
  .gitignore        derived art - see "Art"
  media/            -> artemis-sbs.Cosmos-TNG-Mod.media.v0.2.3.zip
    tng_ships.json     THE ship-data file the engine reads (one file only)
    ships/  faces/  portraits/  audio/  music/  skybox/  fonts/
  tng_races/        -> ...tng_races.v0.2.3.mastlib (FLAT)
    __init__.mast  tng_setup.py  *.grid  *_fleets.yaml  tng_sides.amd  tng_crew.amd
    theaters.amd  tng_faces.json  tng_portraits.json  tng_manifest.json  tng_taunts.json
  _tools/           generators (retune, ships_to_json, face pipeline) - not shipped
```

A consuming mission pins **both** in its `story.json`: the mastlib under `mastlib` and the
pack under `shared_media`. Forgetting the pack is silent: `add_extra` logs "extra ship data
not found", `media_shared` returns its fallback, skyboxes drop out of the random pick, and
fleets spawn nothing.

Rules that come with this layout:

- **ONE addon, not one per faction.** Per-faction control belongs in settings
  (`PLAYABLE_RACES` / `NPC_RACES`), not in package boundaries - nine `race_*` addons only made
  every mission list nine mastlibs.
- **Globally distinctive addon folder name.** `addon_source_folder` looks for the folder IN
  THE CONSUMING MISSION, so an addon named `races` is silently "satisfied" by LM's own
  `races/`. Use `tng_races`, `anime_races`.
- **Mastlibs are flat, so file names must be unique across the addon** - name them
  prefix-first (`tng_klg_vorcha.grid`, `tng_klingon_fleets.yaml`).
- **Version lives in `__lib__.json` only.** Stamp it into the ship file and a manifest, log it
  at load, publish it as a shared variable (`TNG_MOD_VERSION`), and have the test range assert
  the mastlib and pack agree - that is what catches a half-updated install.
- Prefer `suggests` + a `default shared X = False` guard over `requires` for optional
  dependencies (TNG's torpedo types lean on LM's `prefab_torpedo_type` this way).

---

## Declaring hulls

### Keys: add, never replace

**Unique keys with a mod prefix: `tng_<faction>_<class>`.** Overriding a stock key does work
in the engine (an add-on entry beats the stock one for the same key), but it turns the mod
into a conversion, two such mods can never coexist, and it **cannot reach clients** (see
"Client vs server art"). Unique keys are why TNG and Anime load into one story with all
checks passing.

Consequence: a new key has **no stock interior to fall back on** - plan every hull a player
can fly (see "Interiors").

### The setting that gates everything: `EXTRA_SHIP_DATA`

Off by default (`settings.py`), because only newer engines (v1.3.7 per the code comment) have
a working extra-ship-data path and a v1.3.4 install dies with `bad allocation` on the first
spawn of a declared hull. While off, `add_extra()` returns False **without looking for the
file** (one warning per mission), `merge_mod_ship_yaml` merges nothing, and the replay and
file flush are skipped. A quoted `"false"` parses as false (fail safe).

- Set it in settings.yaml, a profile, or `COSMOS_SETTINGS`. As an ADDON, the **consuming
  mission's** settings are read, never the mod's. A mod that also runs standalone (viewer,
  bake map) needs its own `settings.yaml` with `EXTRA_SHIP_DATA: true` - TNG's bake silently
  did nothing (0/47) until it had one.
- Tell for "it is off": `debug.log` reaches the mod's breadcrumb before the ship section and
  then has **no** `add_extra(...)` line.
- **Consumers go off with the loader.** Guarding the loader alone is a crash, not a disable:
  prefabs/ladders that spawn a declared hull must be gated too. Safe one way only: loader on
  with consumers off is fine; consumers on with the loader off crashes.

### The call

```
# tng_races/__init__.mast (the real one wraps this in tng_declare_ships())
provides tng_races
ship_data_add_extra("tng_ships", mod="tng_races")
```

`ship_data.add_extra(name, path=None, mod=None)`, MAST name `ship_data_add_extra`:

- `name` has **no extension** and may carry a logical folder (`"turrets/extraShipData_turrets"`).
- With no `path` it searches the mission folder, then each pinned media root, choosing by
  whether the FILE exists, and **prefers the unpacked `__lib__/media/` copy** - a mission's
  source `media/` folder is not engine-openable (LM_TestRange worked, LM-as-mission did not).
- It merges the file into sbs_utils' `#ship-list` (replacing by key, stamping `#mod`),
  records it for replay, and hands the engine the exe-relative path **without extension**
  (the engine team's sample: `add_extra_ship_data("data/missions/BeamArcTest/extraShipDataAAA")`).
- Returns True only when the engine call did not raise. It writes one line to `debug.log`:
  `add_extra(<name>): file FOUND in ... -> engine path ..., engine told: True`.
- `sim_create()` = `ship_data_flush_mod_file(); create_new_sim(); extra_replay();
  extra_report_untold()`. **`create_new_sim()` wipes the engine's extra table**; only files
  recorded by `add_extra` are replayed.
- `ship_data_extra_enable(False)` takes out only the ENGINE half; the library merge stays,
  so headless behaves identically.

**Do not use** `ship_data_merge_mod` (writes `extraShipData.json` into the mission, which is
read back next run: 51 hulls became 102) or the `extraShipData` filename for custom assets at
all. Current engines do not read that file inside `create_new_sim()` (the 1.3.6-A exe has no
such string); the API call is the only way in.

### The file: HJSON, one of it, newline-terminated

The engine parses ship data as **HJSON** (JSON plus `#` comments) - `data/shipData.yaml`
says so in its header. PyYAML (the library side) accepts far more, so a bad file works
everywhere **except the engine**.

| Rule | What breaks otherwise |
|---|---|
| JSON body: `{ "#ship-list": [ {...} ] }`, `#` comments allowed. **Quote every key**; a quoted key may contain spaces (stock uses `"beam Primary Beams"`) | Block YAML (`- key:` sequences, unquoted `beam Primary Beams:` mappings) is rejected whole; hull draws `unknown`, turrets never fire. `add_extra` warns (`_looks_like_hjson`, also to `DEBUG`) |
| **End with a newline** | line-oriented reader: `RuntimeError: End of input while parsing an object` on valid JSON. This alone hid all 51 TNG hulls. `add_extra` warns |
| **Ship ONE file per stem** | engine tries `.yaml` before `.json`; a stale `.yaml` beside the `.json` wins and is rejected |
| **Copy a WHOLE stock entry**, then edit | an entry missing `hull_port_sets` or `torpedostart` has crashed the engine at load |
| Extension is free: `.yaml` with a JSON body is fine | template: `LegendaryMissions/media/turrets/extraShipData_turrets.yaml` |
| LF line endings in the packed file | CRLF engine-read media fails far away (`MemoryError` in `create_space_object`) - see packaging skill |

Authoring in YAML is fine if a tool **emits JSON** for the pack (TNG: `_tools/ships_to_json.py`).
When dumping YAML with PyYAML use `width=100000`; `width=100` wraps long scalars that then do
not round-trip. Generate numbers from a targets file (TNG: `_tools/balance_targets.json` ->
`retune_ships.py`) and **md5 the output across two runs** - a non-idempotent generator took the
Galaxy's magazine 40 -> 16 -> 4. Grant fields by MERGING into the entry, never replacing
(`torpedostart` written wholesale dropped the stock zero-count slots).

Field notes:

- `shipData.side` is a **lookup** field (`filter_ship_data_by_side`); the side passed to
  `npc_spawn` is **diplomacy**. `SpaceObject.race` is `origin`, which also picks taunts and
  hails. Take faction identity from the art/mod data, not prose.
- Scale convention TNG measured: **0.400 units per metre**; real size is `.obj` bounding box x
  `meshscale` (`meshscale` alone is unreadable). `exclusionradius = max(25, 0.52 x drawn)`.
- NPCs never fire torpedoes (stock NPCs have `tubecount` 0); beams carry faction identity in a
  fight, drones are the only NPC projectile, tubes matter only on player-flown hulls.
- Beam stats are fixed at the hull in the engine (`beamRange` etc. are not settable live), so
  a variant with different beams needs a new entry.
- `mod_ship_data_process` (called by `spawn_common`) copies shipData spellings onto the
  data_set for library-only entries (`baycount`->`bay_count`, `tubecount`->`torpedo_tube_count`,
  `shields[]`->`shield_count`/`shield_val`, `hull_port_sets` beams -> `beamCount`...,
  `torpedostart` -> `{Type}_NUM/_MAX/_VAL`). It must **not** override `data_tag` for a key the
  engine was told (`_extra_keys`) - that asked the engine for a type named by a PATH and drew
  `unknown`.

---

## Silent failure modes (each reports success, fails later)

**Downstream symptom of all of them:** spawning a hull the engine does not have ->
`MemoryError: bad allocation` minutes later against unrelated code; MAST swallows it and the
next line raises `AttributeError: 'NoneType' has no attribute 'blob'`. A raw
`sbs.create_space_object` on an unknown type is an access violation. Or the hull spawns with
no stats, draws `unknown`, and science lists it as unknown.

1. **Raw `sbs.add_extra_ship_data()`** is never replayed after `create_new_sim()`. Three
   shipped mods lost every hull this way. Tell: no `add_extra(...) engine told:` line in
   `debug.log`; `extra_report_untold()` names the mod at `sim_create()`.
2. **Extension in the engine argument** - handled by `add_extra`; hand-rolled calls get it wrong.
3. **No final newline**, 4. **`.yaml` beside `.json`**, 5. **block YAML** - see the file table.
6. **Wrong copy** - the source `media/` instead of the unpacked pack; `add_extra` prefers the pack.
7. **`told: True` never meant the engine READ the file** - the call raises nothing for a file
   it cannot open. Only a hull actually spawning and drawing is a verdict.
8. **`data_tag` holding a path** where a working ship holds a key (see field notes).
9. **Setting off** (`EXTRA_SHIP_DATA`) - one warning, then hulls are just absent: an empty
   picker or a race with no playable ships.
10. **Race not added to settings** - `settings_race_is_playable` is False for a race missing
    from a non-empty `PLAYABLE_RACES`: no interior loads, dead Engineering, nothing said. Add
    your race to `PLAYABLE_RACES` / `NPC_RACES` via the LIVE dict from
    `settings_get_defaults()` (`settings_add_defaults` only fills missing keys, so it cannot
    append).

Diagnose with a probe that spawns every declared hull and catches the exception itself
(`LM_TestRange/maps/mhp_probe.py`), run INSIDE the failing mission. Engine-vs-mock tell: a
value that went through the engine's C++ table comes back float32 (`speed_coeff` 0.55 ->
`0.550000011920929`).

---

## Client vs server art

MAST runs on the server; each client resolves ship art from **its own** `data/shipData.yaml`.
A key the client already knows renders with the client's stock `artfileroot`; only a key the
client does not know renders what the server sends. Symptom: the player ship shows mod art,
every NPC and station is stock. Headless is one process and cannot show this.

So a reskin **cannot** work on clients - spawn the mod's own keys. For missions that name
stock hulls, three ART-ONLY settings (empty by default, or derived from the active THEATER)
redirect the choice without touching sides:

| Setting | Maps | Reaches | Function |
|---|---|---|---|
| `RACE_ART` | mission faction -> shipData faction | hulls looked up by faction (`basic_enemy`, defenders) | `ship_data_art_faction_for(race, role)` - ignored if the target has no hull in that role |
| `ART_KEYS` | stock key -> replacement key | hulls named outright: stations (`terrain_spawn_stations`), fleet ladders, civilians, CAG fighters | `ship_data_art_key_for(key)` - falls back if the replacement is not in the table |
| `RACE_FACES` | mission race/side -> face race | every `random_face()` call | `face_race_mapped` - face races are SPECIES, not factions |

`art_keys_from_theater()` traps: do not filter on the `ship` role (`arvonian_fighter` is
`cockpit,fighter`); pair mobile vs station within a side; stock starbases/freighters are side
`USFP`. TNG ships `tng_reskin.json` (generated by `_tools/make_reskin.py`) for this.

**Ordering:** a client must not connect until the server has LOADED the mod art. Measured:
client already on the picker -> crash in 15-57 s (`HCDraw3DShip` / `ObjectDataBlob::Set`);
~6 s after map start -> assert; ~45 s -> clean. Start the mission, let the art load, then bring
consoles up.

---

## Art

**`artfileroot` carries the whole path. `artfilepath` is obsolete (engine v1.3.6) - never
write it, never bake a path at startup.** Spellings, as `_art_root_exists` judges them:

| Spelling | Resolved against | Use |
|---|---|---|
| `ships/<name>` | `data/graphics` | stock art |
| `data/missions/__lib__/media/<owner>.<repo>.media.<tag>/ships/<Name>` | the exe folder | **a mod's own art** (TNG's json) |
| bare `<name>` | - | **invalid on 1.3.6+**: spawns on the server, then asserts `the artfileroot of this ship was not found` on the first client that draws it |

The pack path contains the version, so it is known at release and written by the generator -
bump `__lib__.json` and regenerate together. `add_extra` warns about roots with no art on disk
(quiet when it cannot find the install, e.g. CI).

**Derived art is never committed or packaged.** `.paxmesh`, `.pointcube`, `.rawbitmap`,
`<root>1024.png`, `<root>256.png` are generated by the engine from the `.obj` the first time it
DRAWS the hull (spawning is not drawing). A `.paxmesh` stores texture paths for the folder it
was baked in, so a committed one points at its author's disk. Put all five in `.gitignore`;
`sbs lib` drops them from zips (`file_help.is_derived_art`; sprites only when a mesh sits
beside them).

- **Bake before play**, because mesh load is where the engine is fragile and a crash mid-bake
  leaves a half-baked root that crashes every later draw. Options:
  `sbs art check [folder]` (reports half-baked roots), `sbs art bake [folder] [--undrawn]`
  (clears half-baked roots and drives the engine to draw each hull), or a mod's own bake map:
  `Artemis3-x64-release.exe autostartserver defaultmission=Cosmos-TNG-Mod map=tng_ships bake=tng`
  (`map=` required; `bake=all` walks fragile stock art too).
- Engine 1.3.6-A rebakes 1024/256 sprites for **mod** art but **not** for stock
  `data/graphics/ships` art. `sbs art clear` only clears half-baked roots by default;
  **`sbs art clear --all` over stock art is destructive** - back up derived art first.
- **The 1024 sprite is load-bearing twice:** its alpha is the 2D radar icon's SHAPE (never
  flatten it; only `_diffuse` should be opaque), and the engine **cuts the interior hull map
  from it**. A hull with a perfect `.grid` but no `1024.png` renders a BLANK Engineering console;
  `add_extra` warns, the mock cannot see it (it fabricates a hull map from `internalmapw`).
- Bake with a 1.3.6+ build, on the machine and install that will run it; never copy baked
  meshes between installs.
- MAKING the meshes and textures (Blender export traps, Synty, the `generic-*` primitives,
  skyboxes) is the `art-pipeline` skill. Per-spawn custom mesh without a ship entry:
  `body_N_geom_filename` + `local_scale_coeff` on the data_set (how LM monsters render).
- `ships/<hull>.png` beside a mesh is the diffuse TEXTURE, not a picture of the ship; nothing
  outside the engine can render `ship://` art. A labeled placeholder is the right answer.

---

## Interiors

Interiors are the easy part: grid objects are created at runtime, so they come from the
mastlib with no engine file at all.

```
for tng_plan in tng_interiors_enabled(tng_manifest):
    grid_merge_ascii(media_read_relative_file(tng_plan), "tng_races")
```

- One ASCII `.grid` per hull (format: `GRID_ASCII_FORMAT.md`, `mkdocs/docs/build/race-addons.md`).
  Grid data is keyed by shipData **key**, not `artfileroot` (they differ on ~half of stock).
- **Fit `internalmapw` x `internalmaph`** - the renderer silently drops cells outside it.
- **One room name = one roleset** (TNG's `SHIELD` for both facings would have made all 37
  shield cells aft). Roles live in the room registry, never in the grid theme (a theme is a
  skin).
- **The interior decides the drive** - LM's `ai/grid_ai.mast` derives warp vs jump from `warp`
  / `jump` nodes. Match beam/torpedo cell counts to the hull.
- **Never mirror a half-map** - hulls are symmetric, rooms are not (16.9% of stock cells change).
- Hull shape comes from the engine (`is_grid_point_open`, captured into
  `cosmos_dev/mock/hull_maps.json`); the mock's PNG approximation is only a fallback, and
  `is_grid_point_open` in the plain mock returns 1 - **the mock cannot validate a layout**.
- **Interiors are not player-only** (engine-measured): a genuine NPC returns a real hull map,
  builds an authored layout to exact counts, pathfinds figures, accepts
  `assign_client_to_ship`, and `ship_internal_view` draws it. "Player ships only" is LM's
  `//spawn` policy, not an engine limit. **Mid-game** (after `grid_interior_arm()`),
  setting `grid_layout` and waiting builds nothing - call
  `grid_rebuild_grid_objects(obj, layout=...)`.

---

## Races, fleets, sides, faces, media

- **Race** = the gating name in `PLAYABLE_RACES` / `NPC_RACES`; **origin** = per-ship lore shown
  in science. Anime keeps four origins under one race `anime`.
- Fleet ladders: `fleet_table_load_yaml(media_read_relative_file(...), mod)`, gated with
  `settings_race_is_npc`. A ladder naming a key from a possibly-absent addon spawns nothing and
  says nothing.
- Sides: `sides_load_amd` is MISSION-relative, so an addon uses
  `sides_declare_amd(amd_document(media_read_relative_file("x_sides.amd"), data_parser=amd_side_data))`
  inside `//shared/signal/create_sides` (must not await; not `once`). Same trap and fix for
  crews: `crew_declare_amd`, not `crew_load_amd`. Theaters: `theater_declare_text(...)`.
- **Portraits vs faces.** A portrait is a flat image from an atlas in the pack
  (`image://tng:picard`, registered from `media_shared("portraits/...")`) and needs nothing
  installed. A **face** is composited by the engine from sheets listed in
  `data/graphics/allFaceFiles.txt`, which a mod cannot write - `face_register_sheet` /
  `face_register_race` teach the library, mock and AMD renderer, but the engine only finds the
  sheet once those lines are pasted in by hand (TNG `_tools/facesheets.py` prints them). A face
  string names sheet/column/row, so **never repack a shipped sheet** - add new sheets instead,
  and regenerate `allFaceFiles.txt` lines from what is INSTALLED, not from the new build output.
- **Music:** `@media/music/<Bank> "Name"` declares a bank; `settings_set_mod_default` makes it a
  default that loses to the mission. The engine's `set_music_folder` takes only a bare name
  under `data/audio/music` and HANGS on a path, so a pack bank plays `default` until
  `MUSIC_ENGINE_ACCEPTS_PATHS` is on. **Skyboxes** load from the pack with no restriction.
- **Taunts** have no mod registry; TNG updates LM's `taunt_data` shared variable via
  `get_shared_variable` (read it that way - a bare name is a NameError without LM).
- Still engine-owned and undeclarable from a mod: SFX/font names (`preferences.json`), face
  sheet registration, logo.

---

## MAST traps that hit mod code

- **Status strings, not dicts.** MAST re-runs an assigned string through f-string formatting,
  so a returned string containing `{` (a dict, or `str(e)` quoting YAML syntax) is a
  SyntaxError reported against the caller. De-brace anything built from exception text.
- **`log()` is invisible in the engine** (no handler). Use `print` for the one status line a
  person needs (`tng_races: 51 hulls, engine=True ...`) and `DEBUG`/`debug.log` for breadcrumbs.
  Put a breadcrumb BEFORE the ship section so "never ran" and "ran, found nothing" differ.
- Module-level constants are not MAST globals - expose accessors. A procedural module is
  invisible to MAST until listed in `mast_sbs/mast_sbs_procedural.py`.

---

## Verifying a mod

Ship a **test range**: a separate top-level mission folder with no copy of the addon inside
(so the compiler cannot substitute source for the built mastlib), whose `@map/<mod>_verify`
asserts the DATA arrived - a mastlib that failed to load still reports PASS. Worth asserting:
every hull exists and counts are not doubled (51, not 102); nothing stock moved; every
playable hull has an interior that fits its map; ladders name only existing keys; the
mastlib and pack versions agree; warp/jump per hull.

- Headless: `python -m cosmos_dev.mission_runner TNG_TestRange --test 8 --map 0`, and with
  `--runs 3` for the run-2 double count. The mock's `add_extra_ship_data` merges library-side
  a second time (the engine does not), so a merge that is not replace-by-key doubles only in
  the mock; match untold-detectors on ship KEY, never the `#mod` stamp.
- Headless cannot show: client art, bake crashes, the interior sprite mask, HJSON rejection,
  float32 values. **A hull is only verified when it spawns and draws in the engine**
  (`defaultmission=TNG_TestRange map=tng_verify`), and art should be judged close up, not from
  "the engine survived N seconds".
- After editing a mod `.amd`/`.mast`, rebuild (`python sbs.pyz lib Cosmos-TNG-Mod`) and read the
  zip. `sbs lib` does not re-extract an existing unpacked media folder - re-extract it yourself
  after changing the pack without bumping the version.
