# Engine Events & Captured Values

A reference for the **event object** the {{ab.ac}} engine passes to
`cosmos_event_handler`, the fields each kind of event carries, and engine values
that are not in `shipData` (learned from the source or by capturing a running
mission). This is a **living document** — add to it whenever a field meaning or an
engine value is confirmed.

!!! note "How a fact got here"
    Each entry is tagged with how it was confirmed:

    - **(code)** — read directly from the `sbs_utils` source or the engine API.
    - **(capture)** — observed by running the `data_capture` mission in the real
      engine and logging the event/data (see *Capturing values* below).
    - **(TBD)** — not yet confirmed; the expected location is noted.

---

## The event object

The engine drives everything through one handler:

```python
def cosmos_event_handler(sim, event):
    ...
```

`event` carries these fields (code):

| Field | Type | Meaning |
|---|---|---|
| `client_id` | int | Console the event came from. `0` = server; `>0` = a connected console. |
| `tag` | str | Event kind — the dispatcher keys on this (e.g. `"gui_message"`, `"damage"`). |
| `sub_tag` | str | Secondary key — widget tag, damaged-system index, collision kind, … |
| `origin_id` | int | The acting / source object. |
| `selected_id` | int | The target / selected object. |
| `parent_id` | int | Parent object (e.g. the ship a launched weapon came from). |
| `value_tag` | str | A string value (dropdown selection, typed text, …). |
| `extra_tag` | str | Extra string slot. |
| `extra_extra_tag` | str | Extra string slot (e.g. weapon kind on a launch). |
| `sub_float` | float | A numeric value (slider value, dropdown index, …). |
| `source_point` | vec3 | A 3D point (e.g. the mesh point an internal hit landed on). |
| `event_time` | float | Engine time of the event. |

`client_id == 0` is the server; client IDs `> 0` are player consoles.

---

## Routed context variables

Routes (`//…` labels) translate event fields into named variables before the
route body runs. Confirmed mappings:

### `//damage/*` (code — `procedural/routes.py`)

| Variable | Source |
|---|---|
| `DAMAGE_SOURCE_ID` / `DAMAGE_ORIGIN_ID` | `event.origin_id` |
| `DAMAGE_TARGET_ID` / `DAMAGE_SELECTED_ID` | `event.selected_id` |
| `DAMAGE_PARENT_ID` | `event.parent_id` |
| `EVENT` | the whole event object |

Damage route variants: `//damage/object` (any hit), `//damage/destroy`,
`//damage/killed`, `//damage/internal` (player system damage), `//damage/heat`.

!!! success "The damage amount is in `sub_float` (capture)"
    A `//damage/object` capture (`capture_damage.json`) confirms the per-hit fields:

    | `EVENT` field | Carries |
    |---|---|
    | `sub_float` | **the damage amount delivered by this hit** (raw weapon damage, e.g. a beam shot `5.5`) |
    | `sub_tag` | **weapon kind**: `beam`, `drone`, `destroyed` (the fatal hit) |
    | `origin_id` | source ship |
    | `selected_id` | target ship |
    | `value_tag` | source ship's **side** (e.g. `tsn`) |
    | `extra_tag` | source ship's **name** |
    | `event_time` | engine time of the hit |

    So to read actual delivered damage, listen on `//damage/object` and use
    `EVENT.sub_float` (+ `EVENT.sub_tag` for the weapon). The mock does not yet emit
    `sub_float` on its `damage` events — see the note below.

### GUI events (code / `cosmos_dev` confirmed)

All browser/console widget interactions arrive as `tag = "gui_message"`. The
widget tag is a **string** (`page.get_tag()` → `str(int)`).

| Widget | `sub_tag` | `value_tag` | `sub_float` |
|---|---|---|---|
| Button / Checkbox | widget tag | — | — |
| Dropdown | widget tag | selected string | selected index |
| Slider | widget tag | — | raw value |
| Icon (`click_tag`) | the click_tag string | — | — |
| Text input | widget tag | cumulative string | — |

Browser `type` values seen by the dev runner: `"gui_message"` (click/activation),
`"change"` (value change), `"submit"` (typein Enter).

---

## Damage / combat events (code — emitted by `cosmos_dev/mock/sbs.py`)

The mock emits these to mirror the engine so `handlerhooks` routes them. Tuple
order is `(tag, sub_tag, origin_id, selected_id[, parent_id][, {extra fields}])`.

| `tag` | `sub_tag` | origin → selected | Fires |
|---|---|---|---|
| `damage` | `""` | source → target | `//damage/object` (non-fatal hit) |
| `damage` | `"destroyed"` | source → target | `//damage/destroy` + object removal |
| `npc_killed` | `""` | target → target | `//damage/killed` (NPC ship) |
| `station_killed` | `""` | target → target | `//damage/killed` (station) |
| `player_internal_damage` | `""` | target → source | `//damage/internal`; carries `sub_float` (system/amount) + `source_point` (mesh hit point) |
| `heat_critical_damage` | `str(system_index)` | ship → ship | `//damage/heat` |
| `ship_launches_drone` | `""` | source → target | `//launch/drone`; `extra_extra_tag = "drone"` |
| `player_launches_missile` | `""` | source → target | `//launch/missile`; `extra_extra_tag = kind` (Homing / Nuke / EMP / Mine) |
| `*_collision_start` / `*_collision_end` | kind | a ↔ b | `//collision/*` |

!!! note "Mock damage events carry no amount yet"
    The mock currently emits `damage` events **without** the hit amount. Once a
    capture reveals the engine's amount field (above), the mock should emit it
    (the dev runner supports a trailing dict, e.g. `{"sub_float": amount}`) so
    `//damage` routes — and this reference — agree across engine and mock.

---

## Captured engine values

Combat-relevant values that are **not** in `shipData` (the engine sets them at
runtime) or that needed measuring. Unless noted, captured at **DIFFICULTY 5** —
several scale with difficulty (1–11), so re-capture at other difficulties to map
the scaling.

### Movement (capture — `capture_speed.json`)

Engine velocity = `cur_speed × 36` units/s. The throttle → `cur_speed` mapping:

| | `cur_speed` at full | units/s | Notes |
|---|---|---|---|
| NPC (`throttle` 1.0) | `1.0 × speed_coeff` | **36 × speed_coeff** | scales per hull via `speed_coeff` |
| Player impulse (`playerThrottle` 1.0) | `5.0` | **180** | hull-independent (speed_coeff **not** applied) |
| Player warp (`playerThrottle` 3.0) | `30.0` | **1080** | `180 + (pt−1) × 450` |

Acceleration is a first-order lag (`cur_speed` approaches its target geometrically),
time constant ≈ 0.8 s NPC / 1.7 s player.

### Hull & death (capture — `capture_battle_matrix.json`)

- NPC ship `system_max_damage[i] = hullpoints` per SHPSYS (e.g. `tsn_light_cruiser`
  hp 3 → `[3,3,3,3]`; `tsn_battle_cruiser` hp 4 → `[4,4,4,4]`). Death = **all four
  systems maxed**.
- Stations use `armor` (= `hullpoints`); ships have no armor.

**Time-to-kill reference** (DIFFICULTY 5, the mock should land near these): cruiser
duels resolve in ~40–70 s (e.g. `tsn_battle_cruiser` dies ~48 s, `tsn_light_cruiser`
~60 s, `skaraan_executor` ~67 s); players beat a single enemy in ~37–39 s; stations
survive a lone attacker for the full 2 min.

### Shields (capture)

- **Per-facing**, not pooled: a fixed attacker drains only the facing toward it,
  then overflow hits the hull — the other facings stay up (ships die with shields
  on their far side).
- Regen: each facing recovers at **`repair_rate_shields ÷ shield_count`** per second.
  Confirmed by the regen bench (ships alone, shields at 10%): player `1.0/2 → 0.5/s`,
  NPCs `0.1/2 → 0.05/s` — and Kralien / Torgoth / Skaraan all regen at the same
  0.05/s (no per-hull difference). Rates: player `1.0`, NPC `0.1` (code).

### Beams (capture — `capture_damage.json`, `sub_float`)

- `beamDamage` in the data_set is the per-beam **coefficient** (`1.0` for base
  hulls), **not** the per-shot damage. Per-shot = `set_beam_damages` base × coeff.
- Per-shot **full-health** base (coeff 1.0 hulls). Use *early-fight / max* hits, not
  the median — the engine's death spiral lowers a damaged ship's logged beam damage,
  so medians under-report the base.

| Firer | per-shot base | Notes |
|---|---|---|
| NPC ship | **≈ 5.5** | base × coeff(1.0) |
| Player | **≈ 8.5** | players hit ~55% harder than NPCs |
| Skaraan (elite) NPC | **≈ 16.5** | shipData `damage_coeff` ≈ 3.0 |

- `beamCycleTime ≈ 6 s`, `beamArcWidth = 144°`, `beamRange` 1000–1300 (code/capture).
- Mock: when a mission calls `set_beam_damages` (LegendaryMissions does) the mock
  honors it. Otherwise it falls back to `coeff × _BEAM_LOAD_BASE = 6` for every
  firer — so NPC beams are about right (6 vs ~5.5) but player beams are ~30% low
  (6 vs ~8.5). Splitting the fallback to player 8.5 / NPC 5.5 would close it (the
  values are difficulty-independent, so safe to pin).

!!! info "Difficulty does NOT scale per-ship combat stats (captures at DIFFICULTY 1, 5, 11)"
    Running the battle matrix at difficulty 1, 5 and 11 shows the per-ship combat
    inputs are **flat across all three**:

    - NPC beam (~5.5 full-health), player beam (~8.5), Skaraan beam (~16.5), drone (15)
    - shields and `system_max_damage` (hull) — identical per hull at every level

    (An earlier read suggested player beam scaled with difficulty; that was an
    artifact of comparing fight *medians*, which the death spiral confounds. The
    full-health bases are difficulty-independent.)

    So the mock needs **no difficulty-aware combat scaling**. Difficulty must affect
    other things (fleet size, AI behaviour, …) that this per-ship capture doesn't
    measure. NPC-vs-NPC *outcomes* still vary run to run — combat variance, not
    difficulty.

### Drones (capture)

Drone-capable hulls carry `drone_launch_timer` in `shipData` — **Torgoth** and
**Ximni** only (e.g. `torgoth_behemoth`, `xim_dreadnought`). The engine sets the
rest at runtime:

| Field | Value (diff 5) | Source |
|---|---|---|
| `drone_damage` | **15** | capture |
| `drone_launch_max_range` | **7000** | capture |
| `drone_launch_timer` | 20–60 (per hull) | shipData |
| `elite_drone_launcher` | unset (= 0) | capture — *not* the trigger; `drone_damage`/range being set is |

Drone damage is **difficulty-independent** (15 at diff 1, 5 and 11).

### Torpedoes (capture — `capture_damage.json`, torpedo cluster)

- **Player-exclusive** — NPCs never fire torpedoes (they fire drones). Tube count
  from `shipData` `tubecount` (code).
- Per-hit damage by type (the `//damage` `sub_tag` is the torp type):

| Type | per-hit | Behavior |
|---|---|---|
| **Homing** | **35** | single target |
| **Nuke** | **~120** (center) | **area-of-effect**, falls off with distance (observed 10–120 across the cluster); damage event `value_tag = "warhead"` |
| **Mine** | **~120** | AoE, **same as Nuke** |
| **EMP** | **0** hull/shield | not a hull weapon — disables systems / drains energy (shows in `energy`/`heat`, not shields) |

  (Confirmed difficulty-independent: identical at DIFFICULTY 1, 5 and 11.)

---

## Capturing values

The `data_capture` dev mission (in `data/missions/data_capture`) runs scenarios in
the real engine and dumps JSON for calibration:

| Map | Output | Captures |
|---|---|---|
| Data Capture | `capture_battle.json`, `capture_spawn.json` | 1v1 starting data_set + fight log |
| Speed Capture | `capture_speed.json` | impulse/warp speed per hull |
| Battle Matrix | `capture_battle_matrix.json`, `capture_damage.json` | NPC/player/station/drone fights + per-hit `//damage` events |
| Torpedo Capture | `capture_torpedo.json` | player torpedo damage + AoE ripple |

Every capture is tagged with `DIFFICULTY` (forced in the map body — `start_server`
overwrites a top-level value). Change `CAPTURE_DIFFICULTY` to capture another level.
