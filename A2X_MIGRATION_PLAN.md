# A2X — Artemis 2.8 XML → Cosmos MAST Migration Plan

> Status: **planning only — no code changed.**
> Goal: help authors port legacy Artemis 2.8 (`MISS_*.xml`) missions to Artemis Cosmos (MAST),
> getting them 80–90% of the way with idiomatic output and a clear punch-list for the rest.
> Guiding rule: **Cosmos is the new engine — respect it over the old one.** The legacy layer is a
> *porting-comfort* aid, never the recommended idiom.

---

## 1. Two deliverables

1. **`arme2cosmos`** — a standalone CLI tool in its own repo (`git init`), a migration *assistant/scaffolder*.
2. **`a2x`** — a new, optional, clearly-quarantined namespace inside `sbs_utils` providing
   legacy-shaped helper functions so generated (and hand-ported) MAST reads like the old XML.

The tool emits `a2x.*` calls; the library provides them. The XML command vocabulary, the tool's emit
table, and the `a2x` namespace are kept as a 1:1 mirror.

### Migration philosophy
The goal is **XML → MAST**, not "reproduce the hand-port." The MAST `HereThereBeMonsters` is an *enhanced
re-imagining* (grid-items saboteur plot, info-panel comms, lore via `extra_scan_source`, lifeform crew) —
so it is a source of **idioms and suggestions only**. The tool is free to **choose new, cleaner paths** that
fit MAST better than a literal transliteration of the 2.8 construct. Two constructs explicitly get new paths
rather than faithful replicas: **comms buttons** and the **Game Master** (see §4.1).

---

## 2. The coordinate system (fully resolved)

**Artemis 2.8**
- `x`: `0 … 100000`, `z`: `0 … 100000` — a 100 km × 100 km square, **origin at a corner**.
- `y`: `-100000 … 100000` — vertical, `0` = play plane.
- `angle`: `0–360°` (degrees) on `create`; the `angle`/`pitch`/`roll` *properties* are radians `0…2π`.

**Cosmos** uses the same 0…100000 footprint but **X and Z are mirrored about the center (50000)** —
a 180° rotation in the horizontal plane. Y is identical.

This is exactly `Vec3.from2x_coord(x, y, z) → Vec3(100000 − x, y, 100000 − z)` (`sbs_utils/vec.py:89`).
Proven by the hand-port: the 2.8 player spawns at `(98000,0,98000)`; the port spawns at
`from2x_coord(98000,0,98000)` == `(2000,0,2000)` (opposite corner).

**Consequences**
- Every positional arg (`x/z/startX/endX/centerX/pointX…`) passes through `from2x_coord`; Y passes through.
- **Headings are also mirrored:** `angle_cosmos = (angle_2x + 180) mod 360` (plus a possible sign flip for
  Cosmos's heading convention). Emit the converted heading with a `# TODO verify heading` marker.
- Region tests (`if_inside_box`/`if_inside_sphere`): transform both corners/center — a mirrored box is
  still the same box, so logic stays correct.

---

## 3. `arme2cosmos` — the tool

**Decisions locked in:**
- **Output target:** *Scaffold + TODOs* (assistant). Emit idiomatic MAST ~80–90% done, keep the original
  XML inline as comments, produce a `MIGRATION_NOTES.md` punch-list. Human finishes it.
- **Event model:** *Linear scene chain* — translate flag/timer-gated `<event>`s into a chain of `---`
  inline labels with `await delay_sim(...)` / `await distance_less(...)`, exactly as the hand-port did.
  No emulation of 2.8's flat re-check-every-tick loop.

### Architecture (stdlib-only, its own repo)
1. **Parse** — `xml.etree.ElementTree` → typed model of `<start>`, `<event>` (conditions + commands),
   `<mission_description>`.
2. **Translate** — visitor per XML command/condition → MAST fragments. Central coordinate transform wraps
   all positional args. Data-driven lookup tables for art ids, roles, property names.
3. **Emit** — `story.mast` + `script.py` + `story.json` + `description.yaml` + `MIGRATION_NOTES.md`.

### CLI surface
```
arme2cosmos report   MISS_Foo/            # read-only coverage: what maps, what doesn't  (FIRST deliverable)
arme2cosmos convert  MISS_Foo/            # → out/Foo/ scaffold
arme2cosmos convert  MISS_Foo/ --emit-comments   # keep original XML inline
arme2cosmos artmap --generate             # draft vesselData.xml ↔ shipDataBB.json crosswalk
```

### Library dependencies (`story.json` policy)
LegendaryMissions addons are **not engine-required** — a mission can run on the sbslib + `a2x` alone
(MiningDays does). **But a practical gameplay port needs at least the `consoles` addon** (so players get
helm/weapons/science/etc.), and usually a few more. So the tool:
- Emits a **baseline `story.json`** for gameplay missions: `consoles` + `docking`, `comms`, `damage`,
  `prefabs`, `fleets` (the standard multi-console minimum).
- **Feature-detects** extras from the XML and adds only what's used: GM commands → `gamemaster`
  (+ `gamemaster_comms`); `set_comms_button` → `comms`; fleet spawns → `fleets`; docking → `docking`;
  damage/destroy handlers → `damage`; pickups/anomalies → `upgrades`.
- Offers `--standalone` for tool-style / no-gameplay missions: sbslib + `a2x` only, consoles wired
  manually via `gui_reroute_*`.
- The `a2x` namespace itself **never depends on LegendaryMissions** — LM is an emit choice, not an `a2x`
  dependency. (Pickup spawning was the one exception: `pickup_spawn` + the item registry/spawn cluster were
  **moved from LM `items` into core `sbs_utils.procedural.items`**; LM re-exports them, so all existing call
  sites keep working. `a2x_create_anomaly` now uses the core `pickup_spawn`. Item *art* still comes from
  registered `item/` labels, so a mission with pickups still feature-detects the upgrades/items content.)

### Event translation strategy (per-event heuristic)
- **Timer/flag-sequenced events** (the common case) → linear chain of `---` labels + `await delay_sim`.
  This is the default and matches the hand-port's `scene_distress_call_one → …` structure.
- **Reactive events** (`if_distance`, `if_docked`, `if_scan_level`, GM/comms buttons) → routes or
  `await distance_less(...)` / `await signal_wait(...)`.
- **Ambiguous** → labeled stub with its conditions listed, for the author to wire. The tool does **not**
  auto-order arbitrary events; it emits each as a named label + a wiring guide in `MIGRATION_NOTES.md`.

### Validation (not a byte-diff against the hand-port)
The MAST `HereThereBeMonsters` is an **enhanced re-imagining**, not a faithful 1:1 port — it leans on
Cosmos-only features with no 2.8 XML source (e.g. the grid-items saboteur plot, info-panel comms,
`extra_scan_source` lore, lifeform crew hosting). So **the hand-port is a reference for idioms, not a diff
target** — the tool's output will be a thinner, mechanical translation and should not be expected to match it.

Validate instead by:
- **Compile + headless run:** generated mission compiles and survives `mission_runner --test` (no crashes,
  reasonable MAST coverage).
- **Beat/asset parity:** the same spawns, pickups, timers, and story beats present as in the XML `<start>`
  and `<event>` blocks (the tool's `report` mode quantifies this) — *not* parity with the enhanced port.
- **Human gut-check** against the hand-port for "does this feel like the same mission," accepting that
  Cosmos enhancements are out of scope for an automated pass.
- Broaden to **simpler / more mechanical** a28 missions where the XML maps more directly — those are
  better automated-fidelity benchmarks than HTBM.

### Test corpus (`f:/a/a28/dat/missions/`)
13 missions (the `missions/` and `Missions/` dirs are the same set under a case-insensitive FS — dedup
case-insensitively). By size / suitability:

| Mission | Lines | Role |
|---|---|---|
| Cruiser_Tournament | 3998 | stress test (largest) |
| Dawn_Patrol_2.8 | 2663 | complex |
| HamakSector | 2357 | complex |
| HereThereBeMonsters | 1759 | idiom reference only (enhanced Cosmos re-imagining exists) |
| Sirius_Feint | 1253 | mid |
| Battle_of_Elihu_12 | 842 | mid |
| AttractMode | 283 | **has a Cosmos counterpart** (`cosmos_auto_play`) — real before/after |
| Module_3_bases | 239 | **has a Cosmos counterpart** (`module_3_bases`) — real before/after |
| TheWaningDark | 208 | simple |
| TrialsOfDeneb 01/02/03 | 100–125 | **simplest — first targets / fidelity benchmarks** |
| TheEndOfPeace | 41 | tiny smoke test |

Start on Trials of Deneb + TheEndOfPeace (small, mechanical); use AttractMode / Module_3_bases for genuine
before/after against their Cosmos counterparts; treat the 2000–4000-line missions as the coverage stress set.

---

## 4. Command / condition → MAST mapping (the heart of it)

High-confidence, automatable (tool emits `a2x.*` where a legacy shape helps):

| 2.8 XML | Cosmos MAST | Notes |
|---|---|---|
| `create type="player"` | `player_spawn(*Vec3.from2x_coord(x,y,z), name, side, art)` | via `//shared/signal/create_player_ships`, `PLAYER_CREATE_DEFAULT=False` |
| `create type="enemy/neutral"` | `a2x.create_enemy(...)` → `npc_spawn(..., "behav_npcship")` | raceKeys/hullKeys → art lookup |
| `create type="station"` | `npc_spawn(..., "side, station", art, "behav_station")` | |
| `create type="nebulas"` | `a2x.create_nebulas(...)` | see §6 |
| `create type="asteroids"` | `a2x.create_asteroids(...)` | see §6 |
| `create type="mines"` | `a2x.create_mines(...)` | see §6 |
| `create type="blackHole"` | `prefab_black_hole` (deck / `prefab_spawn`) | exists in Cosmos |
| `create type="Anomaly"` | `pickup_spawn(*from2x_coord(...), <upgrade_key>)` | pickupType → key table |
| `create type="monster"` | `a2x.create_monster(...)` → best-fit art + `# PLACEHOLDER` | see §5 |
| `create type="genericMesh"` | `npc_spawn` nearest art + `# TODO mesh` | raw `.dxs` meshes don't exist in Cosmos |
| `destroy` / `destroy_near` | `.delete_object()` / query+loop delete | |
| `add_ai CHASE_PLAYER` | `brain_add(obj, ai_chase_player)` | port does exactly this |
| other `add_ai` blocks | `brain_add(obj, <closest LM brain>)` + `# TODO` | partial map |
| `direct` | `a2x.direct(...)` → `target_pos(...)` | |
| `set_variable` | `x = …` / `shared x = …` | floats by default |
| `set_timer` / `if_timer_finished` | `set_timer(0, name, seconds=…)` / `is_timer_finished(0, name)` | |
| `if_distance` | `await distance_less/greater(...)` or `sbs.distance_id` | |
| `if_inside/outside_sphere/box` | `distance_point_less` / explicit bounds | corners via from2x_coord |
| `if_exists` / `if_not_exists` | `object_exists(id)` | |
| `if_variable` / `if_difficulty` | plain Python `if` | |
| `incoming_comms_text` / `incoming_message` | `comms_receive` / info-panel helpers + `play_audio_file` | mirror `here_helpers.py` |
| `big_message` | story dialog / `gui_info_panel_send_message` | |
| `set_object_property` | `obj.data_set.set("<mapped>", v)` | property-name table → `object_data_documentation.txt` |
| `set_skybox_index` | `@media/skybox/...` | index → name table (manual) |
| `set_player_grid_damage` | `grid_damage_system(id, sbs.SHPSYS.*)` | port uses this |
| `end_mission` | `signal_emit("show_game_results")` | |

A `report` mode prints "X of Y command types mapped, N occurrences need TODO" — a confidence meter + punch-list.

---

## 4.1 Interaction-heavy constructs — choose new paths

These don't transliterate cleanly; the tool picks the better MAST path rather than mimicking 2.8.

### Comms buttons
2.8 uses a **flat, global** model: `set_comms_button text=...` adds a button to the comms console,
`if_comms_button text=...` is a separate event that fires when it's clicked, `clear_comms_button` removes it.
MAST comms is **route/tree-based** (`//comms`, `+ "Label"` buttons, `comms_navigate`). New path:
- `set_comms_button` + its matching `if_comms_button` event → fold into a single **`//comms` route with a
  `+ "Label"` button** whose body is the event's commands. The button's `sideValue`/`name`/`player_slot`
  scoping → an `if` guard on the route/button (`if side_are_enemies(...)`, role checks).
- Alternatively, for one-shot story prompts (the common case), emit an **info-panel button promise**
  (`gui_info_panel_send_message(..., button=...)` → `await choice`) — the pattern the hand-port uses.
- The tool keys `set_comms_button`/`if_comms_button` pairs by their `text` attribute to stitch them back
  together; unpaired ones become a `# TODO comms button` stub. `a2x` may offer a thin
  `a2x.comms_button(text, handler, side=...)` so simple cases stay one-liners.

### Game Master (GM)
**Primary path (when GM is used): feature-detect the LegendaryMissions `gamemaster` + `gamemaster_comms`
addons** — they already provide GM console, spawn/maps/messages/stations menus, and info panel. These are
added to `story.json` only because the mission's XML uses GM commands (per the dependency policy above),
not assumed present:
- `use_gm_selection` → the **`//select/...` route** + selected-object context (`SELECTED_ID`).
- `use_gm_position` / `set_to_gm_position` → the **`//point/...` route** + `source_point` (click-to-place).
- `set_gm_button` / `if_gm_button` → a **GM console label with `gui_button(...)`** (or a `gamemaster_comms`
  menu entry) whose handler runs the event's commands. Menu paths (`"Create Enemy/Extras/Minefield"`) →
  nested sub-sections / submenu buttons.
- `if_gm_key` → an `on`/key handler on the GM console (lower priority; many missions can drop it).

**Fallback: an a28-compatible GM screen.** Where a mission's GM logic is too bespoke to fit the LM menus
(dense custom button grids with explicit `x,y,w,h`, key-driven control), generate a dedicated **`a2x` GM
console** that reproduces the 2.8 GM console literally: a flat button list with positions, click-to-place
position capture, object-selection state, and key triggers — driven by `a2x.set_gm_button` /
`a2x.if_gm_button` / `a2x.use_gm_position`. This is a compatibility layer, clearly marked, not the
recommended idiom. The tool chooses per-mission: LM-menu path when the GM use is "spawn/message/map," the
a28 screen when it's a bespoke control panel; `MIGRATION_NOTES.md` records which and why.

---

## 5. Space creatures — strategy

**Finding (from `shipDataBB.json`, grouped by `side`):**
- `monster_charbdis` exists → real art for 2.8 `monsterType=0` (CLASSIC).
- `wreck` exists → real art for 2.8 `monsterType=8` (DERELICT). HTBM spawns 8 of these.
- **Missing:** whale / shark / dragon / piranha / tube / bug / jelly (monsterTypes 1–7).
- Generic `alien_*`, `biomech`, `Kralien` hulls exist and are already repurposed by the port
  (`alien_small_3b` = "Strange Object", `biomech_a` = BioMechs).

**Strategy (now → future):**
1. **Data-driven `creatures.json`** mapping each `monsterType` → best-fit Cosmos art id + role tag.
   Real entries for 0 (charbdis) and 8 (wreck); placeholders (`monster_charbdis`/`alien_*`) for 1–7.
2. **Role tag** `creature_*` on every spawn → a single re-skin seam (one query) when real art lands.
3. **Behavior placeholder:** `behav_do_nothing` + manual `steer_yaw/pitch/roll` drift (the port's
   blink/spin trick) so placeholders look alive; `# TODO creature AI` where 2.8 had monster brain stacks.
4. **Never fabricate art:** map to real Cosmos hulls or leave a clearly-marked stub. (Respects point 9.)
5. `MIGRATION_NOTES.md` lists every placeholder spawn explicitly.

---

## 6. Terrain — new `sbs_utils` functions (authorized)

**2.8 `create` (nebulas/asteroids/mines) packs three placement modes + determinism:**

| 2.8 attribute | meaning | Cosmos today |
|---|---|---|
| `startX/Y/Z` + `radius` + `count` | point-cloud sphere | ✅ `terrain_spawn_*_sphere`, `scatter.sphere` |
| `startX/Y/Z` → `endX/Y/Z` | line distribution | ⚠️ `scatter.line` jitters only *along* the line |
| `startAngle`/`endAngle` + `radius` | arc / ring | ✅ `scatter.arc` / `scatter.ring` |
| `randomRange` | per-object jitter (all directions) | ❌ **no equivalent — biggest gap** |
| `randomSeed` | reproducible placement | ⚠️ seed system exists (keyed lattice) but not on simple count-scatter |
| `nebType` 1–3 | nebula variant | ⚠️ `_neb_colors` table exists; needs a 1/2/3 → color mapper |
| `type="mines"` | mine field | ❌ no helper (only an inline `terrain_spawn(...,"behav_mine")`) |

**Two layers:**

**Layer A — small, generally-useful core additions** (valuable beyond migration; idiomatic names):
- Add optional `jitter` / `random_range` to `scatter.line` and `scatter.arc` (per-point offset).
- Add optional `seed=` so any count-scatter is reproducible (reuse the existing FNV-1a per-cell seeding).
- Add a `terrain_spawn_mines_*` family (sphere/line/box) setting `damage_done` / `blast_radius`.

> **Status:** Layer B shipped first (self-contained in `a2x/terrain.py`: jitter + seeded RNG envelope +
> mine placement, all composing existing public spawners — no edits to `scatter.py`/`terrain.py`, to avoid
> collision with concurrent work). Promoting jitter/seed/mines into core `scatter`/`terrain` (Layer A) is
> the deferred follow-up.

**Layer B — thin `a2x` wrappers** mirroring the XML 1:1:
```python
a2x.create_nebulas(count, start, end=None, radius=0, random_range=0, seed=None, neb_type=1, selectable=False)
a2x.create_asteroids(count, start, end=None, radius=0, random_range=0, seed=None)
a2x.create_mines(count, start, end=None, radius=0, random_range=0, seed=None, damage=5, blast_radius=1000)
```
`end` given → line mode; else → sphere/point-cloud of `radius`; apply `random_range` jitter; honor `seed`;
`neb_type` → color. Internally compose Layer-A primitives — no new spawn logic, Cosmos stays authoritative.
`start`/`end`/center pass through `from2x_coord`; with `seed`, a migrated field lands in the same mirrored
spot every play (matching 2.8's deterministic feel).

---

## 7. The `a2x` namespace — naming & module layout

**Mechanism (confirmed by implementation):** `import_python_module(mod, prepend)` exposes a module's
functions as MAST globals with an **underscore prepend** — `prepend='a2x'` yields `a2x_pos`, `a2x_angle`,
`a2x_create_nebulas`, … (NOT dotted `a2x.pos`). The dotted form that `scatter.box` also enjoys comes from a
*second* mechanism: a static `"scatter": scatter` entry in `mast/mast_globals.py`. So:

**Decision (shipped): an `a2x` subpackage registered with `prepend='a2x'`** → callable as **`a2x_*`**
(the prefix style explicitly sanctioned). One line added to `mast_sbs/mast_sbs_procedural.py`. The dotted
`a2x.pos` alias is an *optional* later add (one entry in `mast_globals.py`, exactly like `scatter`) —
deferred to avoid touching that core file during concurrent work. The migration tool emits the guaranteed
`a2x_*` form.

The subpackage (= "Artemis 2.x") unifies the terrain helpers, the coordinate/angle math, and any future
comfort functions under one name across the tool, library, and docs.

```
procedural/a2x/
├── __init__.py        # re-exports submodules: from .coords import *  etc.   [DONE]
├── coords.py          # a2x_pos (from2x_coord), a2x_angle (deg -> Cosmos heading)   [DONE]
├── spawn.py           # a2x_create_enemy/neutral/station/monster/anomaly/black_hole + pickup_key   [DONE]
├── terrain.py         # a2x_create_nebulas / _asteroids / _mines (thin wrappers)   [DONE]
├── ai.py              # a2x_add_ai / a2x_clear_ai   [DONE] (a2x_direct TODO)
├── props.py           # a2x_set_object_property / a2x_get_object_property / a2x_addto_object_property
├── comms.py           # a2x_incoming_comms_text / a2x_big_message / a2x_incoming_message   [DONE] (comms_button TODO)
├── gm.py              # a28-compatible GM screen: a2x_set_gm_button / a2x_if_gm_button / a2x_use_gm_position (fallback)
└── conditions.py      # a2x_is_docked / a2x_in_box   [DONE] (distance/sphere/exists map to core awaitables)
```
Registered with one line (DONE): `MastGlobals.import_python_module('sbs_utils.procedural.a2x', 'a2x')`.

**Why namespaced `a2x.` over an `a2x_` prefix:**
- **Author muscle memory** — MAST reads like the old XML: `a2x.create(...)`, `a2x.add_ai(...)`,
  `a2x.set_object_property(...)`, `a2x.if_distance(...)`. No prefix noise.
- **One discoverable group** — type `a2x.` for the whole layer; `grep a2x\.` finds every legacy call.
- **Honest signaling** — the namespace flags Artemis-2.x semantics (corner coords, degrees, count/range)
  so nobody mistakes it for the idiomatic Cosmos API.
- **Proven pattern** — `scatter.*` already works this way; zero new machinery, one registration line.

**Reusable vs. comfort split stays:** general primitives (scatter `jitter`/`seed`, `terrain_spawn_mines_*`)
live in **core** `scatter.py`/`terrain.py` with idiomatic names. `a2x` only composes them + adds the
coordinate flip + XML-shaped signatures.

---

## 8. `vesselData.xml` ↔ `shipDataBB.json` crosswalk

The 2.8 `vesselData.xml` (`<hullRace>` race→keys; `<vessel classname broadType side>` with raw `.dxs`
`<art meshfile>`) is the analog of Cosmos `shipDataBB.json` (180 entries grouped by `side`). **There is no
shared identifier** — the art link is raw mesh paths that don't exist in Cosmos. So the map must be a
**curated lookup** on `(race name/keys, classname/broadType)`.

Both sides are small and stable (2.8: 9 races / 58 classes; Cosmos: ~4–17 hulls per side). The tool can
**auto-generate a draft** crosswalk by fuzzy-matching race + classname, ship it as an editable
`hullmap.json` flagged `# unverified`, and apply the 2.8 fallback priority (`hullKeys="Battleship medium"`
→ try "Battleship", then broadType "medium") as the matcher's order.

---

## 9. `sbs_utils` functions that ease migration (author cheat-sheet)

- **Coordinates:** `Vec3.from2x_coord` (the indispensable one) → wrapped as `a2x.pos`.
- **Spawning:** `player_spawn`, `npc_spawn`, `pickup_spawn`, `terrain_spawn`, `prefab_spawn`, `hangar_random_craft_spawn`.
- **Terrain:** `terrain_spawn_asteroid_box/sphere/scatter`, `terrain_spawn_nebula_sphere`, `terrain_spawn_black_hole(s)`,
  `terrain_spawn_monsters`, `scatter.line/arc/box/ring/sphere`, the tile-map system (`maps_tile_map_create`,
  `maps_deck_create`, `prefab_terrain_*`, `prefab_black_hole`).
- **Identity/query:** `to_id`, `to_object`, `to_object_list`, `object_exists`, `sbs.distance_id`.
- **Roles/links (replace `name=`+`sideValue`):** `add_role`/`has_role`/`role()` set algebra,
  `link(ship,"extra_scan_source",id)`, `linked_to`.
- **AI:** `brain_add` + LegendaryMissions `ai_chase_player` et al.
- **Timing/flow:** `set_timer`, `is_timer_finished`, `await delay_sim`, `await distance_less/greater`,
  `distance_point_less`, `promise_any`, `signal_emit`/`signal_wait`.
- **Comms/story (replace `incoming_*`, `big_message`):** `comms_override`, `comms_receive`/`comms_transmit`,
  `gui_info_panel_send_message`, `sbs.send_story_dialog`, `set_face`/`get_face`, `lifeform_spawn`. The
  mission-local `here_helpers.py` is a *suggested* pattern, not a required one.
- **Game Master:** LegendaryMissions `gamemaster` / `gamemaster_comms` addons; `//select/...` and
  `//point/...` routes; `gui_button` on a GM console label — primary GM path (see §4.1).
- **Data/damage:** `obj.data_set.set(...)`, `grid_damage_system`, `get_data_set_value`.
- **Audio:** `sbs.play_audio_file(0, get_mission_audio_file(path), 1.0, 1.0)` (≈ 2.8 `play_sound_now`).
- **End/scoring:** `game_end_condition_add`, `signal_emit("show_game_results")`.

---

## 10. Suggested build order

1. **`a2x/coords.py`** + core `scatter` `jitter`/`seed` additions — small, independently unit-testable.
2. **`a2x/terrain.py`** (`create_nebulas/_asteroids/_mines`) on top of Layer A; add `terrain_spawn_mines_*`.
3. Scaffold the **`arme2cosmos`** repo (`git init`, `pyproject.toml`, stdlib parser, `pytest`); ship
   **`report`** mode first (read-only coverage across all a28 missions).
4. Coordinate transform + `create`/`pickup`/terrain emitters (highest volume, highest confidence).
5. `description.yaml`/`story.json`/`script.py` scaffolding.
6. Event → label/route translation with `# TODO` markers + `MIGRATION_NOTES.md`.
7. Remaining `a2x` modules (spawn, ai, props, comms, conditions) as the emitters need them. Comms-button
   pairing (`set_`/`if_comms_button` by `text`) → `//comms` routes. GM: emit LM-menu path when the use is
   spawn/message/map; the `a2x` GM screen (`gm.py`) only as the bespoke-control fallback.
8. `creatures.json` placeholder map + re-skin seam; `hullmap.json` auto-draft (`artmap --generate`).
9. **Validate:** compile + headless `--test` run; beat/asset parity via `report` mode; human gut-check vs.
   the hand-port (idiom reference only — *not* a byte-diff). Lean on simpler a28 missions for fidelity benchmarks.

---

## 11. Notes / risks

- **Concurrent edits:** another session may touch this tree. This plan keys off `vec.py`,
  `here_helpers.py`, `scatter.py`, `terrain.py`, and the HTBM port — re-verify those before generating code.
- **"Close enough" is the bar.** Headings, monster AI, and reactive-event wiring are intentionally left as
  `# TODO`/placeholders rather than over-engineered.
- **`a2x` is optional and removable.** Idiomatic Cosmos missions never need it; it exists purely to make
  legacy ports comfortable and to give the tool a clean, stable emit target.
