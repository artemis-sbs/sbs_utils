# Ship interiors - make every hull flyable

Mechanics reference: `GRID_REFERENCE.md`. Format spec: `GRID_ASCII_FORMAT.md`. The mod
packaging this feeds: `SHIP_MOD_PLAN.md` (deferred).

**The problem in one line.** ~120 of ~185 hulls have no interior, and a hull with no
interior has a **dead Engineering console** - no system nodes, no damcons,
`system_max_damage` never set (`GRID_REFERENCE.md` s4). Every pirate hull is in that set.

**The plan in one line.** Fix what is broken, give the mock eyes, make interiors
mod-shippable, then give every hull a generated systems-only interior before anyone
hand-authors a single room.

---

## 1. Why this order

The instinct is to start authoring pirate rooms. That is the wrong end.

- **Authoring is the expensive half and the least valuable.** A generated systems-only
  layout (s3) makes ~120 hulls work. Hand-authoring makes four hulls nicer.
- **Nothing could check a layout.** Until phase 3 the mock's `is_grid_point_open` returned
  1 unconditionally, so a room outside the hull looked fine everywhere until the engine.
  Authoring before that was authoring blind.
- **The mask rule is inferred, not confirmed.** Writing 200 rooms against an unverified
  rule risks writing them twice.

So: probe, fix, tool, generate, *then* author.

---

## 1a. This runs in the engine

Binding constraint on everything below. The mock is a development convenience; the engine
is the target.

**Stdlib only, and it must work in embedded Python 3.11.** No pip packages anywhere in the
shipped path - not in `sbs_utils`, not in `cosmos_dev`. The analysis behind
`GRID_REFERENCE.md` used PIL; no shipped line may. If the ASCII format is parsed at
runtime (`GRID_ASCII_FORMAT.md` s4 q3), that parser runs inside Cosmos.

**In the engine, do not decode the mask - ask the engine.** This corrects an earlier
design call. The engine already owns the authoritative hull map:

| Context | Source of open cells |
|---|---|
| **in engine** | `sbs.get_hull_map(id).is_grid_point_open(x, y)` - authoritative, free |
| in mock | decode the PNG alpha (`cosmos_dev/mock/hull_mask.py`) |
| offline tooling | decode the PNG alpha |

Two consequences worth having:

- **PNG decode never runs in production.** It is mock and tooling only, so `zlib`
  availability in embedded Python is not on the critical path.
- **The systems-only generator can run at spawn from the engine's own hull map** (s3.2),
  needing no precomputed mask data and no dependence on whether
  `GRID_REFERENCE.md` s2 is exactly right. The inferred rule stays load-bearing for the
  mock and the authoring tools, not for the thing players run.

**A mock pass is not evidence.** Every phase below carries an engine exit criterion, not
only a headless one. Where the two disagree, the engine is right.

---

## 2. Defects to fix

Full table in `GRID_REFERENCE.md` s6. Scheduling:

| # | Defect | Phase | Why there |
|---|---|---|---|
| 1 | mission reset never clears `ship_data_cache` / `_grid_data` / `_grid_theme` / `_grid_theme_current` | 2 | becomes a correctness bug the moment mods exist |
| 3 | `name.lower.strip()` - named theme lookup raises | 4 | per-race themes need it |
| 4 | `_grid_theme_current` is module-global | 4 | per-race themes need theme selection on the ship |
| 5 | `grid_get_grid_current_theme` returns an int when out of range | 4 | same code |
| 2 | `sensor_damage_coeff` matches `"sensors"`, data says `"sensor"` | 4 | not critical path, but in the code being touched |
| 6 | per-object `scale` is dead data | 4 | same; migration drops the field either way |

---

## 3. Layout variants per hull

Today `grid_data[art_id]` is one interior. It should be **N named layouts**.

### 3.1 Why

1. **Systems-only** - just the damageable nodes. ~10-20 objects instead of 60-200.
2. **Refit as a layout** - warp vs jump is two layouts of one hull, not a special-cased
   node edit (s7).
3. **Owner variants** - a captured TSN hull refitted by pirates is the same mesh with a
   different interior and theme.
4. **It unblocks every hull at once** - s3.2.

### 3.2 Systems-only is derivable, and that is the point

A systems-only layout needs no authoring. Every node comes from data already present:
beam count from `hull_port_sets`, tubes from `tubecount`, shields fwd/aft, sensors,
impulse, maneuver, drive from faction - placed by the `GRID_REFERENCE.md` s5 zone grammar
against the mask.

So **every interior-less hull can be given a working one mechanically.** That is the whole
Torgoth, Skaraan, Kralien, Biomech, cargo and pirate set going from dead console to
flyable with nobody placing a room.

It is also a **performance lever**. Grid objects are Agents; a juggernaut interior is 208
per player ship, ~1700 across eight ships (`GRID_REFERENCE.md` s4). Systems-only is ~20. A
hangar spawning craft, or a mission with many player ships, can ask for the cheap
interior. Worth measuring, not assuming.

### 3.3 Shape and selection

Backward-compatible - `grid_objects` stays readable as the default layout:

```
{
  "pirate_brigantine": {
    "layouts": {
      "default":  {...},
      "systems":  {...},
      "jump":     {...}
    }
  }
}
```

Selection, most specific wins:

1. explicit argument - `grid_rebuild_grid_objects(ship, layout="systems")`
2. ship inventory value - `set_inventory_value(ship, "grid_layout", "raider")`
3. `"default"`

In the ASCII format a layout is one file per layout, named for it - which makes variants
diffable against each other, the main thing an author wants when building the second one.

### 3.4 Open

- **Does a layout carry its own theme?** Built: per hull AND per layout, since the
  captured-hull case wants it. Note this is only a SKIN choice - roles live in the room
  registry, not the theme (`GRID_ASCII_FORMAT.md` s4 q1), so a re-skin cannot change what
  a ship survives.
- **Does systems-only get a distinct visual treatment**, or does it just look sparse? A
  near-empty floor plan may read as broken rather than as minimal. This is a stop
  condition (s6).

---

## 4. Phases

Phases 1-3 gate everything.

### Phase 1 - Ground truth (engine)  [DONE - RULE REFUTED]

A probe route walking `hm.is_grid_point_open(x, y)` over a live player ship for 3-4 hulls,
writing the bitmap to `debug.log` alongside `symmetrical_flag`, `grid_scale`, `hm.w`,
`hm.h`. Diff against the `GRID_REFERENCE.md` s2 computation.

Settles the mask rule, the flip and `internalsymmetry` in one run. Diagnostics to a file,
not a screenshot.

Built: `LM_TestRange/maps/test_hullmap_probe.mast` + `hmp_probe.py`, map `test_hullmap_probe`,
writes `LM_TestRange/hullmap_probe.txt`. Headless it correctly reports the mock's own
reconstruction; the ENGINE run is the one that settles the rule.

**Exit met, with the unwanted answer.** The engine run refuted the inferred rule - 0.790
agreement. `GRID_REFERENCE.md` s2 is rewritten. The consequence: the hull shape is
**captured from the engine, not derived from art** (63 hulls in
`cosmos_dev/mock/hull_maps.json`), and the art-derived path is demoted to a fallback for
hulls with no capture.

This is why the probe went first. Phases 5-8 would all have been built on it.

### Phase 2 - Reset ledger  [DONE]

Register and clear `ship_data_cache`, `_grid_data`, `_grid_theme`, `_grid_theme_current`
via `register_reset_state` + `reset_mission_state()`. Wire in the existing
`reset_ship_data_caches()`.

Done. `ship_data_reset_for_mission()` and `grid_reset_caches()` are called from
`reset_mission_state()`, with four probes registered. The subtlety worth keeping:
`reset_ship_data_caches()` is called BY the merge functions, so it must never drop the
merged list - the mission-boundary reset is a separate function, and
`test_merge_survives_its_own_cache_reset` is what stops the two being collapsed together.

**Exit met:** `tests/test_restart_mod_data.py`, 6 tests.

### Phase 3 - Mock hull maps  [DONE]

Real `is_grid_point_open` and `get_objects_at_point`, from the confirmed rule.

**Constraint:** no new dependency. Alpha-only PNG decode is `zlib` plus ~60 lines of
unfiltering, cached per art key.

Done. `cosmos_dev/mock/hull_mask.py` (stdlib `zlib` decoder, verified byte-identical to
PIL on eight hulls) plus a real `is_grid_point_open`, `get_objects_at_point`, populated
`w`/`h`/`grid_scale`/`symmetrical_flag`, and both grid-point finders - which used to
return `[0, 0]`, a cell that is usually OUTSIDE the hull now that hulls have a shape.

**Exit met:** `tests/test_mock_hull_map.py`, 11 tests, including a corpus check that
authored rooms land on open cells across all 40 ships (measured 0.986).

### Phase 4 - Grid mod API and themes  [DONE]

`grid_merge_mod_data` / `grid_merge_mod_theme` mirroring `merge_mod_ship_yaml`, with the
`#mod` stamp and same-key collision detection across mods (`SHIP_MOD_PLAN.md` s3). Theme
selection moves onto the ship - cleanest as a `"theme"` key on the grid entry read by
`grid_rebuild_grid_objects`. Layout support per s3.3. Defects 2-6.

Done. `grid_merge_mod_data` / `grid_merge_mod_theme` mirror `merge_mod_ship_yaml`, with
`#mod` stamping and same-hull collision reported by name. `grid_get_layout` /
`grid_get_theme_name` add N named layouts per hull with `grid_objects` still read as the
default, and `grid_rebuild_grid_objects` takes a `layout=` argument (falling back to the
ship's `grid_layout` inventory value). Theme selection is per hull and per layout.
Defects 2-5 fixed.

**Defect 6 resolved as "do not honor it".** The per-object `scale` values in the shipped
data (`1.2454545497894287` and friends) are artifacts of whatever tool wrote the file, not
authored intent; reading them would import that noise into the render. The theme owns
scale, the read site now says so, and the migration drops the field.

**Exit met:** `tests/test_grid_mod_api.py`, 19 tests.

### Phase 5 - The ASCII format and validator

Format per `GRID_ASCII_FORMAT.md`. Validator: every cell on-hull; fill density in the
38-75% band; port/starboard symmetry; system node counts against shipData beams/tubes;
every roleset resolves to a theme icon rather than falling to 120.

**Exit:** round-trips **all 40** authored ships - render to ASCII, read back, get identical
JSON semantics. Not spot-checked.

### Phase 6 - Migrate the stock interiors

Convert all 40 out of `data/grid_data.json` into ASCII, **split one bundled addon per
race** (`SHIP_MOD_PLAN.md` s5). `grid_data.json` becomes a deprecated fallback read.

Normalize in the same pass - safe, nothing looks a grid object up by room name
(`GRID_REFERENCE.md` s7). Drop the dead `scale`.

This is the format's real exam. A ship that will not round-trip means the format is
under-designed; fix the format, do not special-case the ship.

**Exit:** every stock ship renders from ASCII with identical semantics - same cells, same
roles, same system counts - diffed mechanically across all 40.

### Phase 7 - Systems-only for every hull

Generate a systems-only layout for all ~120 interior-less hulls. Derived from shipData
plus the mask; no hand authoring.

**The highest-value phase here and among the cheapest.** Every unflyable hull gets a
working Engineering console.

**Exit:** a player can fly any hull in shipData with functioning Engineering.
Spot-verified in the engine across several factions; the generated set checked
mechanically.

### Phase 8 - The pirate mod

Hand-authored content on top of phase 7's floor. ASCII interiors plus a pirate theme.

| Ship | Grid | Open cells | ~Objects | Beams | Tubes | Hull | Note |
|---|---|---|---|---|---|---|---|
| `pirate_fighter` | 7x9 | 30 | ~16 | 2 | 0 | 1 | hull aspect 0.97 vs grid 0.78 - **9x9 fits better** (36 cells) |
| `pirate_brigantine` | 12x12 | 78 | ~43 | 3 | 2 | 5 | aspect 0.80 - acceptable as-is |
| `pirate_longbow` | 15x15 | 96 | ~53 | 1 | 1 | 2 | aspect 0.97 - correct as-is |
| `pirate_strongbow` | 17x17 | 159 | ~87 | 4 | 2 | 4 | aspect 0.69 - **12x17 is truer**; cells 1.4x too wide |

Start with `pirate_brigantine`: 78 cells is enough to be interesting without being a slog,
and its hull is the cleanest shape of the four.

Room vocabulary re-flavored and carried by the pirate theme - `cargo` becomes a plunder
hold, `brig` does real work, `galley`/`saloon` weighted up, no `School` or
`observation-lounge`.

**shipData is not edited.** The w/h recommendations are recorded, not applied.

**Exit:** a player flies a brigantine with a working Engineering console. Verified in the
engine, in a browser, by the user - a green headless run is not evidence for a render.

---

## 5. Decisions taken

1. **The grid mod API lands in `sbs_utils`**, not in a mission. It is the missing half of
   an existing pattern, not pirate-specific.
2. **Pirates warp by default** (confirmed). The refit path (s7) is additive.
3. **`data/grid_data.json` is deprecated** (confirmed). Stock interiors migrate to bundled
   mastlib addons; the JSON is read as a fallback through the transition.
4. **A hull has N named layouts, not one interior.** `grid_objects` stays readable as the
   default, so existing data keeps working.
5. **Systems-only is generated, never hand-authored**, and comes *before* any authored
   content.
6. **shipData `internalmapw`/`internalmaph` are not edited here.** Two recommendations
   recorded against phase 8.
7. **Probes 1 and 2 are blocking; 3 and 4 are not.**

---

## 6. What would make me stop

- **Probe 1 contradicts `GRID_REFERENCE.md` s2.** The mask rule is wrong and phases 3, 5-8
  are built on sand. Stop, re-derive, edit the reference first.
- **Phase 6 cannot express one of the 40.** The format is under-designed; fix it there.
- **No mission lets a player fly a pirate hull.** Stops **phase 8 only** - phase 7 gives
  every hull a working console regardless. Still worth confirming a consumer exists before
  hand-placing ~200 rooms.
- **Systems-only reads as broken rather than minimal.** Needs a visual treatment before
  phase 7 ships, not after.

---

## 7. Warp -> jump as a refit

Because drive type is derived from grid nodes (`GRID_REFERENCE.md` s4), a refit is editing
the map at runtime. With layouts (s3) it is a layout swap:

```
grid_set_layout(ship_id, "jump")
```

Worth building for its own sake: it makes the engineering map a **surface mission state
writes to** rather than a static picture. Buy a jump drive at a black-market station and
the interior visibly changes. Damage it and you are sublight.

Two unknowns:

- `grid_ai.mast` sets both blob flags when both node types are present, but its label
  logic is a binary `"JUMP" if is_jump else "WARP"` with no third case.
- **Whether the engine honors both drives at once is unknown.** Probe 4.

---

## 8. Engine probes

All write to a file.

| # | Question | Blocks |
|---|---|---|
| 1 | Does `is_grid_point_open` match the bbox+flip rule? | phases 3, 5-8 |
| 2 | What does `symmetrical_flag` do - mirror the mask, or the objects? | phase 5 validator |
| 3 | `grid_scale` / `internalmapscale` - world units per cell? | nothing yet; affects hit mapping |
| 4 | Can a ship have `warp_drive_active` and `jump_drive_active` at once? | s7 |

Probes 1 and 2 share a single route and a single run. Two more probes, about art, live in
`SHIP_MOD_PLAN.md`.

---

## 9. Open questions

1. **Does a consumer exist for pirate interiors?** Which mission lets a player fly one -
   LM hangar, OU, something planned? Gates phase 8 only.
2. **Room vocabulary:** extend the theme with pirate-specific names and icons, or reuse
   existing names and let *placement* carry the flavor? Phase 8 assumes the former.
3. **Does a layout carry its own theme?** (s3.4)
4. The remaining format forks in `GRID_ASCII_FORMAT.md` s4 - half-map mirroring,
   runtime-parsed vs compiled, replace vs coexist. **q1 is resolved**: roles live in a
   generated room registry, the theme stays a pure skin, and the legend may override.
