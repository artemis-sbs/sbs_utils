# Grav-tether — design & build plan

> **Status: ACTIVE (2026-08-09).** Phases 0-1 shipped and the orbit/swing math works:
> `procedural/grav_tether.py` (17 functions incl. `grav_tether_swing`), 22 tests, the
> `grav_tether/` addon registered in LM's `__lib__.json`, `missions/grav_tether_spike`, and
> API docs at `api/procedural/grav_tether.md`.
>
> **The phase-3 fighter UI is absent** - no `nose` or `swing` reference anywhere in the LM
> addon, so the one-button nose-cone pick and its synthesized popup are unbuilt. Phases 2
> (tow/salvage), 4 (constraints) and 5 (growth) are untouched. The physics feel still needs a
> real engine session: **the mock is blind to the native pull**, so a green headless run says
> nothing about how this handles.

A beam that links two space objects and lets one drag, reel, lock, or swing the
other. Gives **Weapons** (capital ships) and **pilots** (fighters) a new thing to
do that isn't shooting. Named **Grav-tether** — one umbrella; the *modes* carry the
different feels.

Inspirations: the classic tractor beam (tow/salvage) + grapple-tether
anchor-and-swing aerobatics for fighters.

---

## 1. Foundation — the engine already does the physics

The Pybind `sbs.simulation` exposes a **native tractor system**. We do NOT hand-roll
per-tick position writes.

```
con = sim.AddTractorConnection(source_id, target_id, offset_point: vec3, pull_distance: float)
con.offset = 0.0     # stiffness dial (see below)
sim.DeleteTractorConnection(source_id, target_id)
sim.ClearTractorConnections()
sim.GetTractorConnection(source_id, target_id)   # -> tractor_connection | None
```

- **source** = boss/master (the puller), **target** = the object that gets pulled.
- **`.offset`** = *"how much the target is pulled toward the offset every tick.
  0 = infinite pull, target locked to boss."* → `0` is a **rigid lock**; higher is a
  **springy trailing tow** that swings on the source's turns. This single float is
  the whole lock↔tow spectrum.
- `offset_point` (vec3) and `pull_distance` (float) — exact semantics unconfirmed
  (see the spike, §7).

### The mock is blind to the pull — verification reality
`cosmos_dev/mock/sbs.py` **stores** the connection but its physics tick does **not**
apply it. So:

- `--test` / browser mock = fine for **wiring** (popup, release, role→mode logic),
  but they will NOT show the object actually moving.
- **Physics feel is engine-session-only.** This shifts the usual verify tiers: the
  drag/swing must be confirmed in real Cosmos, not the browser.

---

## 2. The primitive (sbs_utils.procedural)

Thin wrappers over the native calls, so missions/addons never touch `sim.*Tractor*`
directly:

```
grav_tether_attach(source, target, offset_point=None, stiffness=0.0)  # -> connection
grav_tether_release(source, target)
grav_tether_get(source, target)                                        # -> connection | None
grav_tether_release_all(source)                                        # drop everything a ship holds
```

Home: **`sbs_utils.procedural.grav_tether`** (the primitive) + a thin
**LegendaryMissions `grav_tether` addon** for the popup/console wiring — mirroring how
Fabrication is split (generic primitive in sbs_utils, content/UI in an LM mastlib).

---

## 3. Modes — orientation + stiffness pick the feel

One primitive; the behavior comes from *who is source*, the *offset point*, and
*stiffness*:

| Mode | source / target | offset / stiffness | Use |
|---|---|---|---|
| **Lock** | ship = source, load = target | `stiffness 0` (rigid) | grab cargo, hangar recovery |
| **Tow** | ship = source, offset behind hull | springy (a few) | drag a derelict home |
| **Reel** | ship = source, offset shrinks toward hull | springy → 0 | pull in + hand off (collect/dock) |
| **Swing** | **anchor = source, fighter = target** | springy, `pull_distance` = tether len | the fighter anchor-and-swing move |

The source/target *flip* is what turns "I drag the load" into "the anchor swings me."

**Confirmed in-engine (data harness `LM_TestRange/test_grav_tether`):**
- A **STATIC tether reels the target fully IN** regardless of `pull_distance`
  (1500 → ~165, floored by exclusion radius). `pull_distance` is **NOT** a hold-at-
  distance rest-length (this overturns the earlier spike guess).
- A per-tick **ROPE-TOGGLE holds at distance** — 798/801/801 at rope_len 800 (engage a
  stiff pull when beyond rope_len, release when inside).
- `.offset` (stiffness): `0` = rigid, `~5` = good tow feel.
- The offset point is **WORLD-fixed** (a static "behind" offset would pin to a compass
  point) — so we don't use one; the drag makes a towed load trail for free.
- A **player hull CAN be tractor-pulled** (3000 → 0) — swing is viable.

So the modes are:

| Mode | mechanism |
|---|---|
| **Lock** | static tether, stiffness 0 → reels in + holds tight (grab) |
| **Reel** | static tether, ramp → 0 → draws in (collision then collects) |
| **Tow** | **rope-toggle** at hold distance (a static tow would reel in) — load trails |
| **Swing** | **rope-toggle**, roles flipped (anchor holds the ship) |

**Tow and Swing are the same rope-hold** (`grav_tether_rope`), differing only in which
end is the source. Lock/Reel stay static.

---

## 4. UI — split by ship class, one shared popup

The interaction is the **weapons/context popup** (`PopupPromise`,
`start_popup_selected` in `procedural/popup.py`). Context buttons are chosen by the
**target's role** (asteroid → Swing, cargo → Reel, wingman → Lock), so the *same*
popup reads differently per target. Both ship classes drive the same
`//popup/tether` routes — one UI system.

### Capital ship (Weapons)
Uses the existing `weapons_popup` select channel — Weapons clicks a contact, popup
opens with grav-tether actions. Nothing new needed on the trigger side.

### Fighter (pilot) — one press, nose is the cursor
A manual click-select is wrong in a cockpit. Instead:

1. **One button** → run a **forward-cone query** (nearest tetherable object within
   range R and half-angle θ of the nose; `closest_to_point` along heading).
2. **Synthesize the popup** on the auto-picked target (Path B — robust, no select
   channel consumed):

   ```
   ev = FakeEvent()
   ev.origin_id, ev.selected_id, ev.sub_tag = my_ship_id, anchor_id, "tether"
   start_popup_selected(ev)      # opens //popup/tether on that target
   ```

3. **Auto-skip the popup when unambiguous** (nose on an asteroid → just Swing);
   show it only when the target type is ambiguous/optional. Optional split:
   **tap = best action instantly, hold = open popup to choose.**
4. **Toggle to release** (press/press) — LOCKED. Momentum preserved for the slingshot.
5. `popup_navigate` gives a **"Cycle target"** button (re-runs the cone query to the
   next candidate) — target correction *inside* the popup, still zero select channels.

**Channel decision:** comms and weapons selects stay **free**. The fighter path
consumes no select channel (Path B). If a manual override is ever wanted, route it
through **normal select** (`//focus/normal`) — science/grid are dead weight on a
fighter — but ship nose-aim first and add the override only if playtesting demands it.

**Open UI micro-decision (settle in Phase 3, not a blocker):** whether to ship the
normal-select manual override at all (ship nose-aim only first, add if playtesting
demands it).

---

## 5. Constraints — what makes it a mechanic, not a win button

- **Mass gating** — reel a pod, tow a frigate; a capital ship/station tows *you* (or
  won't lock). Read hull mass from `ship_data`.
- **Tug-of-war on your drive** — towing drops your effective throttle + turn rate by
  towed mass. Big salvage = slow, vulnerable trip home.
- **Power / heat** — tie into the engineering heat model (tether = over-power draw,
  competes with shields/weapons). Gives Engineering a stake.
- **Front-arc + range** — can't tether what you can't point at; beam breaks past max.
- **Grab needs a slowed target** — can't lock a ship at full throttle → in combat you
  must cripple engines first (ties tether to the rest of Weapons).
- **Tether holds only at impulse** — CANONICAL (precedent: old-game **Arena a28**, the
  first to simulate it this way). Confirmed in-engine: warp (playerThrottle > 1) outruns
  the rate-limited pull. **DECIDED (flew both): `cap` is the default** — clamp
  playerThrottle to 1.0 (governor to impulse; you never lose the tow). **`snap`** (break
  the tether + drop the load at warp) stays a **selectable option** (per-mission /
  per-tether config), not the default.
- **Beam breaks on hard damage** — towing under fire is a real risk.
- **Swing skill ceiling is tunable per mission** — a difficulty setting drives the
  swing assist + release window: forgiving (auto-assist, generous window) for casual
  bridge crews, demanding (mistime → overshoot / snap / smack the anchor) for skill
  missions. Both audiences served from one dial.

---

## 6. Growth directions

1. **Salvage → Fabrication loop** — tow debris/derelicts to a refinery to feed the
   Fabrication addon. Closes a currently-abstract loop.
2. **Fighter recovery → Docking** — reel a stalled friendly to the hangar mouth, hand
   off to the existing docking hook. Rescue-the-pilot beats "it despawned."
3. **Rescue / escort quests** — tow the crippled ambassador to the starbase; a
   `quest_on_reach`-style completion. Instant mission type.
4. **Stealth beacon placement** — tow a sensor beacon into position without flying in
   (pairs with the beacon work + Storm's Beacon).
5. **Puzzle / environmental** — reposition a relay, push a mine off a lane, shove an
   asteroid out of a convoy's path.
6. **Enemy tethers (counterplay)** — a boss/elite tether that holds you in a minefield
   or drags you off your escort. Cuts both ways.
7. **Black-hole aerobatics** — a Swing off a gravity well (ties to the black-hole
   gravity feature).
8. **Admiral / RTS layer (OU)** — a dedicated tug unit; salvage as a strategic economy
   input.

---

## 7. Open unknowns → engine spikes (do FIRST)

Two things the type stub / mock cannot answer, both requiring a real Cosmos session:

1. **Force-model spike.** Standalone map: spawn a stationary "boss" + a moveable
   "target," open a grav-tether, and sweep `offset ∈ {0,1,5,20}` × a few
   `pull_distance` values, with the target both stationary and given an initial
   velocity. Learn: (a) what `pull_distance` actually governs (max engage range? a
   taut-rope rest-length?), and (b) whether flipping source/target yields a real
   **orbit** (Swing native) or just a straight yank (Swing needs assist math).
   Doubles as the seed for the `grav_tether` module.
2. **Popup render surface on a fighter cockpit.** Popups normally draw against the 2D
   view; a fighter is a 3D forward view. Confirm the popup surfaces legibly there; if
   not, fall back to an in-view button strip driven by the same `//popup/tether`
   routes.

---

## 8. Phased build order

- **Phase 0 — Spikes.** Force-model spike mission + popup-surface check (§7). Gate the
  rest on what they teach (esp. Swing = native vs assisted).
  - **Force-model spike: BUILT** → standalone `missions/grav_tether_spike` (throwaway
    iteration harness; the real primitive still goes to sbs_utils + LM addon). Calls
    `sim.AddTractorConnection` directly, no rebuilt sbslib needed. Compiles + runs
    headless clean (mock can't show the pull). **Run in a real Cosmos session:**
    `sbs debug grav_tether_spike --map spike`, then switch a console to **"Tether
    Spike"** for the control panel (cycle Scenario / Stiffness / Pull dist / Offset pt,
    Attach / Clear / Reset / Kick) + a live readout (dist, world pos, pos-relative-to-
    source) beside an embedded 2D view. Observe: (1) where TARGET settles vs Pull dist
    → what pull_distance governs; (2) approach dynamics vs Stiffness (0 = rigid snap);
    (3) switch to the **swing** scenario (anchor pulls the PLAYER ship) and fly Helm to
    feel orbit-vs-yank.
  - Popup-surface check: still to do (part of Phase 3).
  - **Findings (confirmed in a Cosmos session):** `pull_distance` = rope rest-length
    (target settles at that distance); `.offset` 0 = rigid, ~5 = good tow, 20 = looser;
    native pull is **radial** so the fighter Swing needs the rope-toggle assist. Result:
    **player-ship tether (Lock/Tow/Reel) promoted to primary; Swing → secondary.** Spike
    now has a `ptow` scenario (player is the source, tows the NPC) + a **Reel in** ramp.
- **Phase 1 — Primitive + capital Lock/Reel cargo.** `grav_tether` wrappers +
  `weapons_popup` → attach → release → collect. Smallest end-to-end proof of the
  popup + attach + release path.
  - **Primitive: DONE** → `sbs_utils/procedural/grav_tether.py` (attach / release /
    release_all / get / clear_all; `lock` / `tow` / `reel` presets; impulse enforcer
    cap|snap|off; reel ramp; dead-object self-heal). Auto-runs its own
    `TickDispatcher.do_interval` while any tether is live, so **enforcement is free to
    any mission**. Registered as MAST globals (`mast_sbs_procedural.py`). Tests:
    `tests/test_grav_tether.py` — **13/13 pass** (registry/enforcer/reel logic; pull
    physics stays engine-verified). Committed-not-pushed pending.
  - **LM addon: DONE** → `LegendaryMissions/grav_tether/` (`__init__.mast` +
    `grav_tether.mast`), registered in LM `__lib__.json`, packaged to
    `artemis-sbs.LegendaryMissions.grav_tether.v1.4.0.mastlib`. A **Weapons hold-click**
    raises a role-gated hold-menu (item/upgrade→Reel; station/asteroid/__npc__→Tow;
    else→Lock; Release when tethered). **Engine-verified**: the right-click popup shows
    and toggles tether state in real Cosmos. Enforcer is automatic (primitive tick), so
    the addon is UX-only. Uncommitted in the LM repo pending.
- **Phase 2 — Tow/Reel derelict + salvage.** Tow-behind + the Fabrication tie-in.
- **Phase 3 — Fighter grav-tether.** Nose-cone acquire → synthesized popup → Swing
  (native or assisted per Phase 0). Settle toggle-vs-hold and the override question.
- **Phase 4 — Constraints layer.** Mass gating, tug-of-war, power/heat, plus fighter
  recovery → docking.
- **Phase 3 — Fighter swing: ORBIT WORKS (mock-verified), UI still to build.**
  `grav_tether_swing(anchor, ship, rope_len)` uses a **moving circle-point** pull: each
  tick it aims at the point on the rope_len circle at the ship's current bearing (radial-
  only correction), so it holds the radius and orbits instead of spiraling in. The first
  rope-toggle version spiraled (data harness: 758→663); the circle-point fix holds radius
  ~rope_len with the bearing advancing (verified in the mock now that it simulates the
  pull). Player hull confirmed tractor-pullable. **Remaining:** the fighter one-button UI
  (nose-cone acquire → synthesize popup), and a real-engine feel pass (now demoable in the
  browser mock, not just the game).
- **Phase 5 — Growth.** Enemy tethers, black-hole swing, rescue/escort quest hooks,
  admiral tug.

---

## 9. Decisions locked

- Name: **Grav-tether** (umbrella; modes carry the feel).
- Foundation: **engine-native `AddTractorConnection`**, `.offset` = stiffness dial.
- Home: **sbs_utils.procedural primitive + thin LM addon** (like Fabrication) —
  first shippable lives in the **LM addon, available to all missions**.
- Fighter UI: **one button → nose-cone auto-pick → synthesized popup (Path B)**;
  comms/weapons selects untouched. Release = **toggle (press/press)**.
- **Priority (updated Phase 0):** the **general player-ship tether** (Lock / Tow / Reel,
  all confirmed-native) is the **primary** goal; the fighter **swing** is **secondary**
  (it's the only mode needing assist math). Supersedes the earlier "equal footing".
- **Confirmed physics:** `pull_distance` = rope rest-length; `.offset` stiffness 0 =
  rigid, ~5 = good tow, 20 = looser. Lock/Tow/Reel are pure native params (§3 table).
- **Tether holds only at impulse** = canonical (Arena a28 precedent). Enforcement =
  **`cap` by default** (governor to impulse), `snap` a selectable option (§5).
- **Skill ceiling: tunable per mission** (forgiving ↔ demanding difficulty dial).
- Verify: **wiring in mock, physics feel + popup render in a real engine session.**
