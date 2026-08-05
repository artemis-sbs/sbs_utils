# The engineering grid - verified mechanics

Reference, not a plan. How ship interiors actually work, measured against the shipped
data. The plans that act on this are `GRID_INTERIORS_PLAN.md`, `GRID_ASCII_FORMAT.md`
and `SHIP_MOD_PLAN.md`.

**s2 was wrong, and the engine said so.** The probe ran on 2026-08-04 and **refuted** the
inferred mask rule: it reproduces the engine at only 0.79. The engine's hull map is
narrower and vertically offset from anything derivable from the silhouette art. s2 now
records what was tried and why it fails; the engine's own bitmap is the ground truth and
is CAPTURED, not computed. This is the stop condition in `GRID_INTERIORS_PLAN.md` s6
firing exactly as intended - before 200 rooms were authored against it.

---

## 1. The key

`grid_data.json` is keyed by `so.art_id`, which is the shipData **`key`**
(`tsn_light_cruiser`) - *not* `artfileroot` (`TSN_Destroyer`). Those differ on roughly
half the ships. Getting this backwards produces a silently empty interior.

---

## 2. The mask mapping

Cell validity comes from the alpha channel of
`data/graphics/ships/<artfileroot>1024.png`. Four candidate mappings, scored across every
ship that has authored grid data - score = fraction of authored cells landing on opaque
pixels (40 ships, 3171 objects):

| Hypothesis | Score |
|---|---|
| grid spans the full 1024x1024 image | 0.229 |
| grid spans the alpha **bounding box** | 0.875 |
| **grid spans the alpha bounding box, y flipped** | **0.987** |
| grid spans a centered 512 box, y flipped | 0.765 |

**The rule that scored 0.987:** alpha bbox, split into `internalmapw x internalmaph`, grid
row 0 at the BOTTOM (art stored bow-down).

**The engine refutes it.** Measured against the engine's own `is_grid_point_open` across
four hulls (601 cells):

| Candidate | Agreement with the engine |
|---|---|
| bbox + y-flip (the 0.987 rule) | **0.790** |
| bbox + y-flip, 90% coverage cut | 0.873 |
| centered 512 box + y-flip | 0.764 |
| best per-ship fit of a centered square cell size | 0.85 - 0.98, with cell size varying 15.5 - 29.5 px |

No constant relates the fitted cell size to `meshscale`, `internalmapscale` or the bbox.
`pirate_brigantine` is the clearest failure: the engine's silhouette sits **three rows
lower** than any bbox-normalized mapping puts it, which no sampling threshold fixes.

**Why the 0.987 was misleading.** It measured whether authored rooms fall inside the PNG
silhouette - and they do. That is a weaker claim than "the grid maps onto the bbox", and
both can hold at once, because the engine's hull is largely a *subset* of the bbox
mapping. The fit had no negative evidence in it: nothing tested the cells the rule says
are open where the engine says closed.

**The corpus is far cleaner than the old reading said.** Against the engine's actual hull,
**3143 of 3171 authored rooms are inside it - 0.9912**. Only four ships have any room
outside at all: `tsn_missile_cruiser` (17 cells), `science_ship` (5), `starbase_industry`
(4), `transport_ship` (2). The approximation blamed `science_ship` for 13 cells that are
in fact inside the engine's hull; most of the "authoring slop" was the reconstruction
being wrong, not the ships.

**So the engine's bitmap is captured, not derived.** `LM_TestRange` map
`test_hullmap_probe` dumps `is_grid_point_open` for every hull that declares an interior;
`python -m cosmos_dev.mock.hull_capture <hullmap_probe.txt>` turns that into
`cosmos_dev/mock/hull_maps.json`, which is the source of truth for the mock and for
offline tooling. **63 hulls captured** as of 2026-08-04.

The art-derived approximation survives only as a fallback for hulls with no capture - a
new mod ship, or one added since the last probe run. It agrees with the capture 0.84, and
**0 of 63 hulls identical**, which doubles as the check that a capture file really came
from the engine and not from a mock run.

In the engine nothing is derived at all - ask `is_grid_point_open`.

**Cell aspect: unknown, and no longer inferable.** The old "the grid stretches to fill the
bbox, so `tsn_carrier`'s cells are ~18x47 px" followed from the refuted rule and does not
survive it. What the capture shows is only which cells are open, not how they are drawn.
Whether `internalmapw:internalmaph` should track the hull's aspect to avoid squashed rooms
is now an open question - answerable by looking at an engineering screen, not by this
data.

**`internalmapscale`** is `hullmap.grid_scale` - "space between grid points", world units,
affecting how a 3D hit maps to a cell. Only `tsn_warpster` and `xim_corvette` deviate
from 1.0.

**`internalsymmetry`** is `hullmap.symmetrical_flag`. Runtime meaning unconfirmed. Note
that symmetry in the data is *authored*, not generated - both halves are written out
explicitly - so the flag is doing something else, or nothing.

---

## 3. Roles are mechanical

From `internal_damage.py`. Roles are lowercased on `add_role`, so the `ENGINE`/`WARP`/
`CABIN` shouting in the JSON is cosmetic.

| Role token | Effect |
|---|---|
| `weapon` / `engine` / `sensor` / `shield` | counted into `system_max_damage` for the 4 SHPSYS - **this is the system's hit-point pool** |
| `beam` | `all_beam_damage_coeff` |
| `torpedo` | `all_tube_damage_coeff` |
| `impulse` | `impulse_damage_coeff` |
| `warp` | `warp_damage_coeff` |
| `maneuver` | `turn_damage_coeff` |
| `shield` + `fwd` / `shield` + `aft` | `shield_damage_coeff[0]` / `[1]` |

Icon and color resolve from the **last** role that has a theme entry, so trailing
modifiers fall through (`system,shield,fwd` -> `fwd` has no icon -> `shield`). Every
roleset in the shipped file resolves; none reaches the fallback icon 120.

**A room is not an object.** Each *cell* is its own grid object, named
`f"{name}:{x},{y}"`. A multi-cell room is several objects that share a name and happen to
be adjacent. Nothing in the engine models "room" as a unit.

**Icons are CENTER-anchored on a grid node**, not corner-anchored to a cell. Two things
follow:

- A multi-cell room draws its icon **once per cell** - a 4-cell cargo hold is four cargo
  icons, not one large one. That is the existing visual language, and the ASCII format
  changes how it is *authored*, not how it is drawn.
- **`scale` cannot express room extent.** Scaling grows an icon about its own node, so a
  big icon straddles its neighbors' nodes instead of filling a block. Scale is for
  *emphasis within a cell* and that is exactly how the theme uses it: `shield` 1.21,
  `computer` 1.2, `passenger` 1.21, `damcons` 0.7, and the EPad hidden at 0.01.

This is the substantive reason the per-object `scale` in `grid_data.json` is not read
(defect 6): it could not have meant "this room is N cells" even if someone intended it to.

Two loose ends here, neither chased: rooms get `icon_scale = scale / 2` while damcons get
the full `scale`, and "one icon per room, at its centroid" would need a different
mechanism than scale - a second object type, or the other cells drawn as plain occupancy.

---

## 4. The interior IS the drive

`LegendaryMissions/ai/grid_ai.mast` builds the grid on
`//spawn if has_role(SPAWNED_ID, "__player__")` and then derives:

```
warp_nodes  = grid_objects(SPAWNED_ID) & role("warp")
_jump_nodes = grid_objects(SPAWNED_ID) & role("jump")
blob.set("warp_drive_active", ...)  /  blob.set("jump_drive_active", ...)
blob.set("eng_control_label", "JUMP" if is_jump else "WARP", 3)
```

- Grids are built for **player ships only**. NPCs never get one.
- A ship with **no grid data** returns early from `grid_rebuild_grid_objects` - no nodes,
  no damcons, `system_max_damage` never set. Flying such a hull gives a **dead Engineering
  console**. That is the state of ~120 of the ~185 hulls in shipData, including all four
  pirates.
- Drive type is therefore a property of the interior, not of shipData.

**Grid objects are Agents.** `grid_spawn` creates one per cell, plus role and link
entries. A `tsn_juggernaut` interior is **208 agents per player ship**. Against a measured
ceiling near 190 ships / 38k agents, interiors are not free.

---

## 5. The layout grammar

Mined from all 3171 authored objects. Positions normalized: fore->aft 0..1,
center->edge 0..1.

| Zone | Rooms |
|---|---|
| **bow** 0.13-0.25 | `beam-fwd`, `officers-mess`, `observation-lounge`, `officers-quarters`, `officers-galley`, `fwd-shield`, `officer-quarters`; `beam-port-fwd`/`beam-starboard-fwd` out at edge 0.71 |
| **fore-mid** 0.30-0.40 | `galley`, `vip-quarters` (center 0.14), `conference-room`, `torpedo-tube`, `crew-quarters` (edge 0.60), `sensors` (edge 0.55), `astro-lab`, `crew-mess` |
| **mid** 0.45-0.55 | `sick-bay` (center 0.14), `gymnasium`, `bio-lab`, `physics-lab`, `saloon`, `rec-room`, `JUMP-DRIVE` (center 0.27), `maneuvering` (edge 0.67) |
| **aft** 0.57-0.75 | `fighter-bay`, `brig`, `cargo`, `shuttle-bay`, `Workshop`, `School`, `Impulse` (0.72), `aft-shield` (0.75) |
| **far aft** 0.83-0.91 | `cargo_hatch`, `beam-aft` (centerline 0.02), `WARP` (0.90, edge 0.56 - on the nacelles) |

**Shape.** System nodes are almost always **single cells, mirrored port/starboard**.
Living spaces are **1-6 cell blobs**. Of 1519 connected room blobs: 853 are 1 cell, 309
are 2, 119 are 3, 127 are 4.

**Density.** Against the ENGINE hull: **54-100% of open cells carry an object, median
74%, mean 76%.** `arvonian_destroyer` is loosest at 54%, `tsn_fighter` is packed solid at
100% (11 of 11).

Hallway is still load-bearing - a hit on an empty cell spawns a fire instead of damaging a
system, so a fully packed ship has no soak - but dense IS the norm and should not be
treated as a defect.

*(An earlier reading of this document said 38-75%, median 52%. That was measured against
the art-derived approximation's larger open-cell count - the same refuted rule as s2. It
is the third figure that turned out to be an artifact of the denominator rather than a
fact about the ships; anything else here computed against a hull mask deserves the same
suspicion. The zone, blob-size and count statistics below are derived from `grid_data.json`
alone and are unaffected.)*

**Counts track shipData.** Beam node count equals the `hull_port_sets` beam count exactly
on the authored ships; torpedo nodes track `tubecount`. Drive nodes follow faction: TSN
warps, Ximni jumps, Arvonian has neither.

This grammar is close to a generator spec - see `GRID_ASCII_FORMAT.md` s5. It is
statistics, not design: it reproduces the averages and loses the reasons.

---

## 6. Known defects

Fixed by `GRID_INTERIORS_PLAN.md`. Listed here because they are facts about how the
system behaves today.

| # | Defect | Effect |
|---|---|---|
| 1 | `reset_mission_state()` never clears `ship_data_cache`, `_grid_data`, `_grid_theme`, `_grid_theme_current`; none are in the reset ledger | mission A's ships and interiors leak into mission B. Masked in the engine (fresh process per mission), live in `cosmos_dev`. |
| 2 | `set_damage_coefficients` matches `all_roles("sensors")` - plural. Every ship uses `sensor` - singular, 92 uses, zero plural | `sensor_damage_coeff` is permanently 1.0. Sensor damage never degrades sensors. |
| 3 | `grid_get_grid_named_theme` / `grid_set_grid_named_theme` call `name.lower.strip()` - missing parens | `AttributeError` on every call. Named theme lookup has never worked. |
| 4 | `_grid_theme_current` is module-global | a theme is a whole-game setting; per-race themes are impossible without moving selection onto the ship |
| 5 | `grid_get_grid_current_theme` returns the integer index when out of range | returns an int where callers expect a dict |
| 6 | `grid_rebuild_grid_objects` reads scale from the **theme**, never from `g["scale"]` | every per-object `scale` in the shipped file is dead data, including hand-tuned values like `1.2454545497894287` |

---

## 7. The corpus, as it stands

- **185** shipData entries; **63** carry `internalmapw`/`internalmaph`.
- **161** keys in `grid_data.json`; only **40** have a non-empty `grid_objects`.
- **121** are empty stubs - Torgoth, Skaraan, Kralien, Biomech, `cargo_ship`, and all four
  pirates. An empty stub is a feature for modding: supplying that key replaces it cleanly.
- `skaraan_executer` (grid data) vs `skaraan_executor` (shipData) - a spelling mismatch
  that leaves both as dead stubs.
- Naming is inconsistent and should be normalized on migration: `Impulse`/`impulse`,
  `WARP`/`warp`, `maneuver`/`maneuvering`, `crew-mess`/`crews-mess`,
  `physics-lab`/`physical-lab`, `Crew-Quarters`, `reADY_ROOM`.

**Renaming is safe.** No mission looks a grid object up by room name -
`get_grid_object_by_name` is used only for `DC1`/`DC2`/`DC3` (damcons, in
`internal_damage.py` and `a2x/props.py`).

---

## 8. How this was measured

So it can be re-run rather than re-argued. The analysis loaded `shipData.yaml`,
`grid_data.json` and the 1024 masks, scored the four mapping hypotheses per ship, and
mined role/position/blob statistics across the corpus.

**The mock now reconstructs this** (phase 3, done). `cosmos_dev/mock/hull_mask.py` decodes
the alpha channel with `zlib` alone - no PIL, verified byte-identical to PIL across eight
hulls - and `cosmos_dev/mock/sbs.py`'s `hullmap` answers `is_grid_point_open` from it,
populates `w`/`h`/`grid_scale`/`symmetrical_flag` from shipData, and implements
`get_objects_at_point`. It was previously a stub that hardcoded `return 1`, `[]` and 0x0,
so headless every ship was a solid rectangle.

Guarded by `tests/test_mock_hull_map.py`, whose corpus test asserts that authored rooms
land on open cells across all 40 ships - the measured figure is **0.986**, which is why
the bar sits at 0.97 rather than 1.0: the shipped data has real slop (`science_ship` puts
13 rooms outside its own hull).

**In the engine none of this runs.** `is_grid_point_open` is answered by the engine
directly and is authoritative. The reconstruction exists so the mock is not blind.
