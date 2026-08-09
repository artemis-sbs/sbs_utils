# Grav-tether — design & build plan

> **Status: ACTIVE (2026-08-09).** Phases 0-1 shipped and the orbit/swing math works:
> `procedural/grav_tether.py` (17 functions incl. `grav_tether_swing`), 22 tests, the
> `grav_tether/` addon registered in LM's `__lib__.json`, `missions/grav_tether_spike`, and
> API docs at `api/procedural/grav_tether.md`.
>
> **Phase 3 is now BUILT.** The one-button fighter path is complete: nose-cone acquire,
> act-at-once when the target is unambiguous, a synthesized `//popup/tether` when it is a
> choice, Cycle target inside that popup, and toggle-to-release. `grav_tether/tether_fighter.py`
> + the `//popup/tether` routes; the cockpit button (hangar) delegates to `lm_tether_press`
> so the button and the menu cannot drift. 19/19 in ENGINE
> (`LM_TestRange/maps/test_tether_fighter.mast`).
>
> (The earlier note here said the fighter UI was "absent - no nose or swing reference in the
> LM addon". That was true of `grav_tether/` and wrong overall: the cockpit button and the
> nose-cone pick already existed in the **hangar** addon. What was genuinely missing was the
> popup half, which is what got built.)
>
> **Phases 2, 4 and 5 are now BUILT too - every phase in this plan is done.**
> - **4 (constraints)** is the load-bearing one: mass is pluggable in the library with LM
>   authoring the table, and it decides who drags whom (a starbase tows YOU), what the haul
>   costs in throttle/turn, whether you can grab a ship under power, and what it spends in
>   energy. 11/11 in engine.
> - **2 (salvage)** pays by MASS, so the heavy freighter is both the slow vulnerable trip
>   and the big payout. 9/9.
> - **5 (growth)** - black-hole slingshot (rope clamped clear of the gravity well), enemy
>   tethers with a burn-hard counter-play, a declarative `tow` quest trigger, and the
>   admiral tug. 18/18 in engine.
>
> **The ONLY thing still open is the FEEL.** Every number in here - reach, cone angle,
> swing radius, mass values, drag, energy cost, break threshold - is a reasoned guess that
> no test can judge. They are all named constants for exactly that reason. This needs
> someone flying it.

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
- The offset point is **SOURCE-RELATIVE — it rotates with the hull.** ~~WORLD-fixed~~.
  Later measured directly (`LM_TestRange/maps/test_tractor_mount.mast`):
  `AddTractorConnection(host, target, vec3(0,0,200), 0)` held the target at **exactly
  200.0u and exactly 0.0° off the host's nose while the host's heading swung 51°**.
  This module still passes **no** offset — a tow wants the load dragged behind, and the
  drag does that for free — which is why its load always reels to the source's own
  position, and is what the original "world-fixed" reading was actually seeing.
  **This line was wrong for months and cost a design decision:** the turret feature built
  a whole per-tick body-frame transform because it trusted it. If you want to bolt
  something ONTO a hull rather than drag it behind one, pass an offset — or use
  `sbs_utils.procedural.mount`, which does exactly that (and deliberately does not route
  through here, because `_enforce_impulse` would cap the carrying ship to impulse).
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
- **Phase 2 — DONE.** Tow a hulk to a friendly station and it pays salvage by its MASS,
  into the same `salvage` key the Fabricator spends. Only TETHERED hulks count (a wreck
  drifting past a dock is not salvage), and the dock has to be friendly to the HAULER -
  a derelict's own diplomacy is civilian scrap and meant nothing.
- **Phase 3 — Fighter grav-tether.** Nose-cone acquire → synthesized popup → Swing
  (native or assisted per Phase 0). Settle toggle-vs-hold and the override question.
- **Phase 4 — DONE.** Mass is PLUGGABLE (the library ships no numbers; a mission installs
  them) because shipData has no mass field and the proxies do not order ships - exclusion
  radius puts a fighter and a shuttle both at 25. Soft gating: a heavier load reverses the
  engine connection so it tows YOU, which beats refusing the grab. Tug-of-war via the same
  upgrade-coefficient modifiers the item system uses, floored so a haul is slow rather than
  impossible. Grab-needs-a-slowed-target ties the tether to the rest of Weapons. Energy per
  tick per mass, and running dry breaks the beam rather than stranding the ship.
  Fighter recovery → docking is NOT built (the hangar already recovers craft by other means).
- **Phase 3 — Fighter: DONE (engine-verified).** Orbit math + the one-button UI.
  `grav_tether_swing(anchor, ship, rope_len)` uses a **moving circle-point** pull: each
  tick it aims at the point on the rope_len circle at the ship's current bearing (radial-
  only correction), so it holds the radius and orbits instead of spiraling in. The first
  rope-toggle version spiraled (data harness: 758→663); the circle-point fix holds radius
  ~rope_len with the bearing advancing (verified in the mock now that it simulates the
  pull). Player hull confirmed tractor-pullable.

  The UI shipped as designed: **Path B**, so no select channel is consumed - the popup
  event is fabricated, not clicked. One press releases if already tethered; otherwise it
  nose-cone acquires and either acts at once (a rock is an anchor, a pod is a pickup -
  confirming that is a menu for its own sake) or opens `//popup/tether` when the target is
  genuinely a choice, e.g. a derelict that could be towed OR locked. **Cycle target** walks
  outward through the cone and wraps. The tap-vs-hold split was NOT built: a GUI button
  cannot distinguish them, and the act-or-ask rule covers the same ground.

  One thing found on the way: the old inline call asked for `max_dist=8000` and silently
  got ~4000, because `closest(max_dist=D)` narrows with a box of WIDTH D. `LM_TETHER_RANGE`
  is now an honest 4000, which preserves exactly the old feel while meaning what it says -
  raise it deliberately.

  **Remaining:** a real-engine FEEL pass. Reach, cone half-angle and swing radius are
  guesses that no test can judge.
- **Phase 5 — DONE.** Black-hole slingshot with the rope clamped clear of the gravity well
  (the tether must never be the thing that drops someone in). Enemy tethers routed through
  the ordinary tow so every constraint applies to the NPC too, with a counter-play needing
  BOTH a hard burn and time - breaking free is something the crew DOES. A declarative `tow`
  trigger verb (`Done when: tow 2 survivors`), so a rescue is authored in AMD instead of
  each mission inventing a signal name. Admiral tug drags rather than teleports, because a
  drag is an event players can see coming.

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
