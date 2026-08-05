# Mod libraries - shipData, art, and the race as a unit

**Deferred.** Recorded now because it is the constraint that shaped the interior work, and
because the survey in s5 should not have to be gathered twice. The active plan is
`GRID_INTERIORS_PLAN.md`. Mechanics: `GRID_REFERENCE.md`.

---

## 1. shipData is the most important engine file

Everything here is downstream of one fact: **the engine learns ships from files it reads
at load.** Get that wrong and it is not one mission that breaks.

Two rules that follow, and neither is negotiable:

- **Never write `data/shipData.yaml`.** That is the game's own table. A mod contributes
  through a mission-folder `extraShipData`, never by editing the base.
- **A generated engine file is validated before it is written**, never written partially,
  and never left half-updated on failure. A malformed `extraShipData` is a broken game,
  not a broken feature.

---

## 2. Three tiers

| Tier | Example | shipData | grid data | art | Needs a file generated |
|---|---|---|---|---|---|
| **1. interiors only** | pirates | - | new | - | **no** - pure runtime |
| **2. new ship, existing art** | reskins, variants | new | new | - | **yes** |
| **3. new art** | art mods | new | new | files | **yes** + art placement (s6) |

Tier 1 is what `GRID_INTERIORS_PLAN.md` delivers, and it is deliberately independent of
everything below.

---

## 3. The asymmetry: shipData needs a file, grid data does not

This is the constraint the whole design turns on.

**There is an official example, and it had been sitting in the install unread:**
`missions_sh/production/missions/legendarymissions/example-extraShipData.json`, beside
`example-extra_grid_data.json`. Three things come straight off it:

- **The file is `extraShipData.json`** - camelCase - while its grid sibling is
  `extra_grid_data.json` with underscores. They genuinely are spelled differently, which
  is why the name was worth checking rather than assuming.
- **The format is HJSON**, "a more human-usable variant of JSON": the file opens with `//`
  comments. Plain JSON is valid HJSON, so writing strict JSON is safe.
- **The sample entry is COMPLETE** - `meshscale`, `radarscale`, `exclusionradius`,
  `meshrotate`, the `internalmap*` block, `hull_port_sets`. Whether a thinner entry works
  is unknown, so anything generated should follow the sample's shape.

The grid example is worth reading too: it carries an explicit `icon` and `color` per grid
object, which the shipped `grid_data.json` does not and `grid_rebuild_grid_objects`
ignores - the same dead-field story as `scale`.

**The engine only learns ships from `data/shipData.yaml` and one `extraShipData.json`
in the mission folder.** (`.yaml` is sbs_utils' own convenience: its `load_data` tries
`.yaml` then `.json`, which is why an early probe run had the LIBRARY seeing an entry the
engine never did.) One file, fixed place, and nothing
can contribute to it from a `.mastlib`. Several mods carrying ship entries must therefore
be **merged into that one file, and that file must physically exist before the engine
reads it.**

`ship_data.py` does carry a runtime path:

```
merge_mod_ship_yaml(media_read_relative_file("extraShipData.yaml"), "MyMod")
```

**It is not a substitute.** It merges `sbs_utils`' own Python-side `#ship-list` - which
drives queries, `filter_ship_data_by_side`, the `*_keys` helpers and the spawn
post-processing in `mod_ship_data_process`. The **engine** never sees it. That is why
`mod_ship_data_process` re-derives every field by hand, and why it can only point art at a
mesh the engine already knows (`set_ship_data_key`). Prior measurement agrees: for a
runtime-merged entry the stats take effect and the hull does not.

| | Engine-visible (art, mesh, hull) | sbs_utils-visible (stats, queries, spawn) |
|---|---|---|
| merged `extraShipData` file in the mission folder | yes | yes |
| `merge_mod_ship_yaml` from a mastlib | **no** | yes |

**Grid data is exempt, structurally.** Grid objects are not engine content -
`grid_rebuild_grid_objects` creates every one at runtime through `grid_spawn`. The engine
never pre-knows an interior, so grid data has no one-file constraint and can be merged
from anywhere, including a mastlib zip. That is what makes tier 1 need no build step at
all.

---

## 4. Who generates the merged file, and when

The file must exist for the engine. **Generating it is plausible** - the open question is
who does it and at what moment, and that decides whether modding needs a CLI at all.

| Option | Who | When | Cost |
|---|---|---|---|
| **A. Build step** | `sbs mod merge` in `sbs_cli` | before ship / before run | a command authors must remember; output is committed and diffable |
| **B. Runtime generation** | `sbs_utils` at mission start | during load | no CLI at all - **if** the engine reads the file after script init |
| **C. Generate + reload** | `sbs_utils`, then re-enter the mission | first load | works regardless of read order, but a visible reload |

**PARTLY ANSWERED - see s6a.** The engine does read a mission-folder
`extraShipData.json`; that much is confirmed on engine 1.3.4. The remaining question is
WHEN, and it decides between A and B outright.

The read appears to happen inside `create_new_sim()`. If so the condition is "the file
exists before `sim_create()`", which a script can satisfy by writing it and then creating
the sim - **option B, no CLI**. Every failed run wrote the file after LM had already called
`sim_create()`, which explains them all without needing the file to pre-date the mission.

The requirements below stand either way: whoever writes that file, it must be
deterministic, stamped, collision-checked and validated before it replaces anything.

**All three options stay inside s1.** Consider them all; none may risk the engine. That
means: write to a temp file and rename atomically, so a crash mid-write cannot leave a
truncated `extraShipData`; parse and validate the result before it replaces anything; keep
the previous file recoverable; and never write while the engine may be mid-read. Option B
is the one to scrutinize hardest here - generating during load is exactly when a bad write
is least recoverable.

Requirements regardless of which:

- **Deterministic and diffable.** Same inputs, same bytes.
- **Stamped.** Source mod and version per entry, so it traces back and nobody hand-edits
  it.
- **Key-collision detection.** Two mods claiming `pirate_longbow` is an error at merge
  time, not silent last-writer-wins.
- **Staleness detection.** Lint / `--test` fails when the generated file is older than a
  declared mod's data. A generated file that silently drifts is worse than none.
- **Validated before write** (s1).

---

## 5. The race mod

The unit of modding should be a **race**, not a file. Interiors are only the first thing a
race owns.

### 5.1 A race is currently scattered

Adding or changing one means editing at least five files across two repos:

| Where | What is hardcoded |
|---|---|
| `LM/fleets/map_common.py` | six `siege_<race>_fleet` tables, 66-77 lines each (~407 total), a seven-branch `if race == "..."` dispatch, and a `random.choice([...])` roster of who can raid |
| `sbs_utils/procedural/ship_data.py` | `<race>_ship_keys()` / `<race>_starbase_keys()` - **18 hand-written functions**, nine races x two |
| `sbs_utils/faces.py` | per-race generators, feature maps, a prefix alias table (`ter`/`tor`/`ska`/`kra`/`zim`/`arv`), another roster literal |
| `data/grid_theme.json` | room vocabulary and icons |
| `data/grid_data.json` | interiors |
| `LM/comms/enemy_surrender.mast`, `LM/damage/damage.mast`, `LM/maps/siege_boss.py`, `a2x/comms.py` | scattered `if race ==` cases and `_RACE_WORDS` |

Biomech and the monsters are absent from the fleet tables entirely. That
`random.choice(["kralien", "torgoth", "arvonian", "skaraan", "ximni", "pirate"])` line *is*
the roster of raiding factions - a literal, in a mission library, that no mod can extend.

### 5.2 What a race mod owns

Interiors (ASCII layouts, including variants), theme (room vocabulary and icons), the
fleet composition ladder, the roster of its ship and starbase keys, names and faces.
Later: shipData entries (tier 2) and art (tier 3).

### 5.3 What it must NOT own

Both are tempting and both are traps.

- **Brains and AI.** `prefab_fleet_raider` carries its behavior tree in metadata. If a race
  mod may override it, nine races become nine divergent copies of one tree and every AI fix
  has to be made nine times. A race supplies *composition*, not *behavior*.
- **Diplomacy.** Who is hostile to whom is a mission's decision - that is what the sides
  system is for. A race mod declaring its own enemies would fight it directly.

### 5.4 Scope

**Done.** LegendaryMissions now carries nine `race_<name>` addons - `race_tsn`,
`race_ximni`, `race_arvonian`, `race_usfp`, `race_torgoth`, `race_skaraan`, `race_kralien`,
`race_biomech`, `race_pirate` - holding 63 ship interiors between them. They are named for
the RACE rather than for the interiors precisely so fleet composition and other per-race
configuration can join them rather than stay scattered (s5.1).

Starbases are folded into their own race's folder rather than sitting in a separate
`interiors_starbases`, so every folder is a race and there is no odd one out.

Each addon skips itself unless its race is in the **`PLAYABLE_RACES`** setting - an
interior is only ever built for a player ship, so floor plans for a race nobody can fly
would be parsed at load and never used. Matching is case- and whitespace-insensitive on
both sides; an empty setting means no restriction rather than nothing playable.

**The fleet tables do not move in that plan.** It is a behavior-preserving refactor of
shipped content used by siege, borderwar, deepstrike, doublefront, singlefront, gamemaster
and the boss maps. It belongs to LegendaryMissions. It is the natural second payload once
interiors prove the mod path.

### 5.5 Open: is the boundary `side` or `origin`?

shipData carries both and they disagree. `side` has 16 values; `origin` has 9 and is
`None` on 111 entries. Terran spans **two** sides - TSN and USFP - which share an interior
style but not a fleet role.

Fleets, rosters and starbase lookups all key on side-ish names, so **side** is the likelier
boundary, with a Terran mod covering both. Not settled.

---

## 6. Tier 3 art

Unknown where it goes, and that decides how much work tier 3 is.

- If the engine resolves `artfileroot` against the **mission folder**, art rides along with
  the mission the way media already does, and tier 3 is "generate + copy files". No mission
  currently carries ship art - checked, zero `.paxmesh` under `missions/` - so there is no
  example either way.
- If it resolves only against `data/graphics/ships/`, tier 3 needs an **installer** writing
  into the Cosmos install: idempotent, reversible, versioned, modelled on the shared-media
  pattern (`__lib__/media/<pack>/` - unpack once beside the libraries, named for the
  version, so two missions pinning different versions each get theirs).

There is prior evidence that `body_N_geom_filename` can be set at runtime while
`artfileroot` cannot, which may open a third path.

---

## 6a. Probe 7: ANSWERED - the file is read, but it must pre-exist

**Engine 1.3.4, `missions/shipdata_min`, 2026-08-05.** The engine read a mission-folder
`extraShipData.json` and applied it:

| field | control `tsn_light_cruiser` | probe, only in extraShipData.json |
|---|---|---|
| `speed_coeff` | 1.0 | **0.33000001311302185** |
| `shield_max_val` | 120.0 | **777.0** |
| `shield_val` | 120.0 | **777.0** |

That `speed_coeff` is the proof. 0.33 stored as float32 and widened back is
0.33000001311302185; sbs_utils would have returned exactly `0.33` as a Python float. The
value round-tripped through the ENGINE's own storage, so this is not the library answering.

**The condition: the file must be on disk before the mission loads.** Every earlier run
wrote it during a session - at story top level, at `create_player_ships`, inside a `@map` -
and none of them could ever have worked. In `shipdata_min` the file was committed, present
before Cosmos launched.

### What this settles, and what it does not

It settles that the file IS read. It does NOT settle when, and the first reading of it here
was wrong.

**The read happens inside `create_new_sim()`** - that is what the engine code looks like.
So the condition is not "the file existed before the mission loaded", it is **"the file
existed before `sim_create()`"**. Those are very different claims, and the difference is
the whole design:

- "before the mission loaded" means only a build step can satisfy it - option A.
- "before `sim_create()`" is something a SCRIPT can satisfy: write the file, then create
  the sim. That is **option B**, and it needs no CLI at all.

Every failed run is still explained. All of them wrote the file at a moment *after* LM's
server console had already called `sim_create()` - story top level, the
`create_player_ships` signal, inside a `@map`. `shipdata_min` worked because its file was
on disk before the `sim_create()` it makes itself.

**The test that settles it** is in `missions/shipdata_min`: write a ship no committed file
contains, THEN call `sim_create()`, then spawn it. If the engine knows
`probe_runtime_ship`, option B is alive and `sbs mod merge` is unnecessary.

### What is NOT yet known

`shipdata_min` differs from `LM_TestRange` in two ways at once: no LegendaryMissions, and a
committed file. This run shows the committed file is sufficient WITHOUT LM. It does not
show whether LM would still break it - LM's `sim_create()` discards the simulation the
engine built at load, and if the ship table belongs to that simulation, every LM mission
would lose it regardless of when the file appeared.

**That is the next run, and it matters**: nearly every real mission loads LM. A committed
`extraShipData.json` in `LM_TestRange` answers it.

---

## 7. Engine probes

| # | Question | Decides |
|---|---|---|
| 5 | Can `body_N_geom_filename` point at mod-installed art at runtime? | s6 |
| 6 | Does the engine resolve `artfileroot` against the **mission folder**, or only `data/graphics/ships/`? | s6 - "copy files" vs "write into the install" |
| 7 | **Does the engine read the mission's `extraShipData` before or after `script.py` gets control?** | s4 - whether modding needs a CLI at all |

Probe 7 is the cheapest and the most consequential. It should be run even while this plan
is deferred, because its answer may simplify the plan out of existence.

---

## 8. Open questions

1. **Where does the pirate mod repo live** - new repo under `artemis-sbs`, or a folder in
   an existing one?
2. **Does the pirate mod become the Pirate race mod?** If yes, question 1 answers itself
   and the pirate repo is the template every other race copies.
3. **`side` or `origin` as the race boundary** (s5.5).
