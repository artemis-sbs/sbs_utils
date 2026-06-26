# Autoplay Redesign — Design Proposal

> Status: **speculative design proposal**, not yet implemented. Captures the plan
> for splitting and improving the LegendaryMissions autoplay system.
>
> Implementation split: LegendaryMissions changes go on a **branch (never pushed
> to main)**; `sbs_utils` enabler changes continue on the current working branch.
> Ask before any push.

## Background

The current autoplay (`LegendaryMissions/autoplay/auto_player_console.mast`) is
triggered by `//signal/game_started` (gated on `SETTINGS["AUTO_PLAY"]["enable"]`)
and schedules per-ship helm/science/weapons/comms AI loops. A single greedy
combat policy drives player ships: approach the closest raider / upgrade / wreck
/ dock, fire beams, select targets for science/weapons/comms.

It serves **two purposes that pull in opposite directions**:

- **(a) Attract mode (in-engine)** — autoplay player ship(s) to draw people in.
  Wants *spectacle and robustness*: look good, never die, never get stuck, loop
  forever.
- **(b) Systems test (in-engine today)** — exercise missions and the library.
  Wants *coverage, determinism, and a verdict*: exercise everything,
  reproducibly, and report pass/fail.

One greedy loop serves both, and serves neither fully. Worse, its **survival
cheats actively hide the bugs a systems test should catch**:

- Energy refill (`if energy < 30: energy = 300`) — real energy/heat mechanics
  never get stressed.
- `ship.pos` teleport for vertical dodging — masks steering/physics/collision
  issues.
- Real-time `delay_app(2)` — non-deterministic and slow.
- No assertions, no coverage, no pass/fail — you eyeball it.
- Only the "happy combat path" is exercised; comms trees, science scans, docking
  variety, upgrades, objectives, GM tools, internal damage, hangar are barely
  touched or not at all.

## Proposal: split over a shared core

### Shared core — a player "brain," not a script

Recast `automated_player_*` as a behavior-tree/brain with a blackboard (the
library already has the primitives: `yield success/fail/idle`, `BRAIN_AGENT`,
inventory-as-blackboard). Composable behaviors: `navigate`, `engage`, `evade`,
`dock`, `collect`, `scan`, `comms`, `wander`.

Two design choices make this pay off:

- **Personae** — select a policy per ship (aggressive / cautious / trader /
  explorer) so a fleet of autoplayers looks alive instead of N identical greedy
  bots.
- **Actuation abstraction (the key split)** — the brain emits *intents*
  ("approach X", "fire at Y", "open comms with Z"); a back-end realizes them:
  - **Attract back-end**: shortcut via direct `data_set` writes for reliability.
  - **Test back-end**: drive the game **through the same API a human console
    uses** (widget clicks, `set_weapons_selection`, comms navigation, science
    scan requests). This is what turns autoplay from "tests the physics
    happy-path" into "tests the console/GUI/comms/science code paths."

## Engine "Attract" mode

Goals: spectacle, robustness, indefinite loop.

- **Cinematic director** decoupled from the actor: score events (combat,
  near-miss, destruction, docking) and cut the camera to the most interesting
  one, with easing/holds. (Today the camera just follows one ship.)
- **Anti-degeneracy watchdog**: detect "no target / stuck / orbiting" and inject
  wander/regroup so it never looks broken on a lobby screen.
- **Spectacle pacing**: modulate spawn cadence / difficulty for ebb-and-flow
  rather than a constant grind; stage set-pieces.
- **Survival cheats are acceptable here** (it's a screensaver) but must be gated
  *off* in test mode.
- Loops cleanly via the results screen → `run_next_mission` (now functional in
  the mock too).

## Mock "Conformance / systems-test" mode

Goals: coverage, determinism, a verdict. This is the higher-investment half,
made cheap by the mock harness (headless, 30 Hz fixed-step sim time,
`settings.yaml` honored, `world_reset`, `run_next_mission` map cycling).

- **Determinism** — thread a seed through everything random (`random`, dialogue
  `%` selection, scatter, fleet-race weights, faces/names). **DONE** for the RNG:
  all sbs_utils randomness funnels through Python's one global `Random` instance
  (module-level `random.*` and the `from random import ...` bindings in
  vec/scatter all resolve to it), so `settings_seed_apply(value=None)`
  (`procedural/settings.py`) seeds the whole chain with a single call; it
  resolves `--seed` → `seed_value` setting → fresh random seed and always
  returns/prints the concrete seed used so any run is reproducible. The mock
  runner applies it before world spawn (`--seed N`); same seed → identical
  coverage confirmed. The autoplayer's one remaining wall-clock wait was the
  AUTO_PLAY `//signal/show_game_results` handler (`delay_app(2)` →
  `run_next_mission`); rather than convert it to `delay_sim`, the mission loop
  is being driven by the documented **AUTO_START** setting instead (it already
  auto-skips the startup map-select and console-select screens after a
  `run_next_mission` reload), so that handler goes away — leaving no `delay_app`
  in the autoplayer.
- **A verdict, not a vibe** — an invariant/oracle layer checked each tick: no
  NaN/inf positions, no negative HP/energy, no orphaned or never-terminating
  tasks, every scheduled task eventually ends, no MAST runtime errors, no Python
  exceptions logged. Any violation = failure with the tick + label. Pipe
  `Mast.include_code` errors and a stderr/exception sink into the verdict.
- **Coverage as the definition of "full"** — instrument the scheduler to record
  visited labels/routes/nodes, then report which `//comms`, `//signal`,
  `//damage`, `@map`, objective, and console labels were never hit. "Full
  systems test" becomes a measurable %, and shows where the autoplayer is blind.
- **Exerciser mode (≠ play-to-win)** — STARTED (`cosmos_dev/exerciser.py`,
  `--test --exercise`): science+comms selects + forced combat each tick. On
  LegendaryMissions ~12.8%→28.7%, comms 0→24/108, damage 0→9/14. Combat is forced
  via `apply_damage` (mission-spawned mock ships lack beam shipData, so emergent
  beams don't engage in seconds; apply_damage queues the same damage/destroy/killed
  events). Remaining damage 5/14 = internal/heat: the mock now emits them with the
  CORRECT payloads (heat -> sub_tag = system index; internal -> sub_float +
  source_point; origin = the ship; per LM internal_damage.mast) and the runner's
  event drain carries extra attrs. But they CAN'T be force-covered in --test:
  dispatch_internal/heat key on the ship's registered handler, and forcing player
  damage trips game logic that pauses the sim. They need the REAL damage flow
  (NPCs hitting players) -> ties to the spawn-beam-data gap. Damage is shields-first
  (shields absorb; then NPC hull, player internal). Beam damage respects
  `set_beam_damages` (base*coeff). Next: comms-submenu walk, scan-start, grid.
  REAL-combat finding (combat-ready diag): the earlier "player is a starbase on
  siege --map" symptom is **RESOLVED** — it was a stale-sim bug in the mock's
  create_new_sim path (the sim object was swapped instead of reset in place,
  leaving FrameContext.context.sim pointing at the old sim; see the
  mock-create-new-sim-in-place memory). With that fixed the siege player has a
  real ship hull with beams, so the remaining gap is just enemy distance, not a
  bad player hull. — a policy whose goal is *coverage*, not
  victory: breadth-first walk every comms tree, scan every scannable,
  dock/undock, fire each weapon/torpedo type, collect each upgrade, trigger
  destroy/heat/internal-damage routes, poke GM tools. Plus a **monkey/fuzz**
  policy: random *valid* GUI clicks and comms navigation against the invariant
  layer — catches crashes the greedy player never reaches.
- **Scenario matrix** — drive the mock runner across (every `@map`) ×
  (difficulty, player_count, world/terrain/monster selects) × seed, cycling via
  `run_next_mission`, emitting JUnit/TAP for CI.
- **Capture-replay** — record a real session's input events and replay them
  deterministically as a regression test.

## Where the boundary sits (two-tier strategy)

The **mock is an approximation of engine physics**, so:

- **Mock tier (fast, CI, every commit)** validates *library + mission logic*:
  routes, signals, scheduling, GUI/widgets, comms, scoring, end conditions,
  no-crash. Cheap and deterministic.
- **Engine tier (slow, pre-release smoke)** validates what only real physics can:
  steering/collision/heat/beam geometry, true energy/shield dynamics. The
  attract bot doubles as this smoke test — but **without the survival cheats**,
  so it stresses real mechanics.

The current autoplayer is really the engine tier wearing a test hat; the gap is
a genuine mock-tier conformance harness with seed + coverage + invariants + a
report.

## Enablers needed first (additive — no MAST backward-compat break)

- Seed threading through the RNG (implements the existing `seed_value`). —
  **DONE** (`settings_seed_apply` + runner `--seed`; one global-RNG seed covers
  scatter/fleet weights/dialogue `%`/faces/names — `tests/test_settings_seed.py`).
- `delay_sim` instead of `delay_app` in the autoplayer. — **OBSOLETE**: the only
  `delay_app` was the AUTO_PLAY `show_game_results` loop handler; the loop is
  moving to the **AUTO_START** setting and that handler is being deleted, so
  there is no `delay_app` left to convert. (LM-branch change, owned by Doug.)
- A node-visit coverage hook in `MastScheduler.tick`. — **DONE** (`MastTicker.on_enter_node`
  seam + `cosmos_dev/coverage.py`, commit a6df5ee).
- An exception / runtime-error sink the runner treats as failure. — **DONE**
  (`MastScheduler.on_runtime_error` seam + `cosmos_dev/verdict.py`).
- A report emitter (JUnit/TAP). — **DONE** (mission_runner `--test SECONDS`
  [`--junit PATH`]: headless run + coverage + verdict + exit 0/1).

All of these benefit the library beyond autoplay.

## Open questions / spikes before committing

The two highest-leverage ideas are also the least-validated; spike them first:

1. **Coverage instrumentation** — how cleanly does the scheduler expose node
   identity (file/label/line) to record visited nodes? — **RESOLVED**: every
   entered node funnels through `MastTicker.next()` and exposes
   `(label, file_num→filename, line_num, node_type)`; a single class seam is
   enough. Spike on LegendaryMissions autoplay measured ~13% of labels entered,
   comms 0/108 and damage 0/14 — confirming both feasibility and value.
2. **Actuate-through-real-API** — does every console action have a clean
   procedural entry point a bot could call, or only data_set side-effects? —
   **RESOLVED**: yes, via two layers, and nothing is a dead-end:
   - **Procedural calls** exercise the real route/handler code directly:
     `set_{weapons,science,comms,grid}_selection`, and especially
     `follow_route_select_{comms,science,grid}` which "fire the selection route
     as if the player selected" by building a `FakeEvent` and calling
     `ConsoleDispatcher.dispatch_select` (`procedural/routes.py
     _follow_route_console`). Comms tree: `comms_navigate(path)` /
     `comms_navigate_override(ids, sel, path)`. Plus docking, science scans, etc.
   - **GUI event synthesis** for any button/widget with no dedicated proc:
     widgets carry `.tag` and match on `event.sub_tag == self.tag`
     (`pages/layout/layout.py is_message_for`), so a `FakeEvent(tag="gui_message",
     sub_tag=widget_tag)` through `cosmos_event_handler` runs its
     `on gui_message` handler — the exact path the mock runner already uses for
     browser clicks. The `_follow_route_console` pattern (synthesize event →
     dispatch) is the reusable template for selects/points/comms too.
   - **Engine-confirmed**: a gameplay console *does* render on a rerouted screen
     (validated in-engine via the `director` addon's highlight). This also
     de-risks putting a console on the server screen (client 0) for screenshots,
     and the broader "drive a console view" mechanism. (Deferred polish: the
     director's pickers don't yet refresh on console connect/disconnect - likely
     needs connect/disconnect signals.)
   - **Discoverability** (needed by the monkey/exerciser): pages expose
     `self.layouts`; walking layouts → rows → widgets yields the live `.tag`s to
     press, and the comms runtime builds an enumerable button list. Small
     follow-on: confirm tag stability across rebuilds and a tidy
     `enumerate_widgets(page)` / `press(tag)` helper.

   Design consequence: the test-mode actuation back-end prefers procedural calls
   where they exist and falls back to event synthesis for arbitrary
   buttons/widgets; the attract back-end keeps direct `data_set` writes for
   reliability.

## Adjacent opportunity: MAST debugger (future spike)

The `MastTicker.on_enter_node` seam added for coverage (commit a6df5ee) is also
the natural foundation for an **interactive MAST debugger**. At every command
boundary it already gives the active label, the cmd node, and — via the node's
`file_num`/`line_num` + `Mast.get_source_file_name()` — the exact source line.
The call stack (`task.label_stack` + `active_label`/`active_cmd`) and
Python-in-task-scope eval (for watch expressions) are also already present.

What a debugger needs on top of the seam:

- **Control, not just notify.** `on_enter_node` is read-only today. A debugger
  needs breakpoint → pause → step/continue. MAST is cooperatively ticked (no
  threads/async), so "pause" = stop scheduling further MAST ticks between frames
  (freeze MAST while the GUI/physics loop keeps running), and "step" = allow
  exactly one node entry then re-pause. The seam detects the hit and flips a
  pause flag the runner/scheduler honors. **This control model is the spike.**
- **State inspection**: enumerate task variables (task inventory / scope), show
  the call stack, and "set variable".
- **Breakpoint model**: by (file, line), by label, by node type, conditional
  (expr evaluated in task scope), and "break on MAST runtime error" (ties into
  the planned exception sink).
- **Multi-task reality**: many tasks tick per frame (server + clients +
  sub-tasks). Breakpoints/stepping must be scopeable to a chosen task, or
  pause-all.
- **UI**: a mockgui browser panel (source view + current line, vars, stack,
  step/continue/breakpoints) over the existing WebSocket bridge.

Spike questions: (1) can the tick loop be paused/stepped cleanly between frames
without wedging the GUI/physics threads? (2) is task variable scope
enumerable/writable for an inspector? (3) presenting the active source line
given the lib/import `file_num` mapping (the source map already exists). Builds
directly on the `on_enter_node` seam and the planned exception/runtime-error
sink.

## Implementation / workflow notes

- **LegendaryMissions** (the autoplay mastlib, personae, attract director,
  exerciser policy): work on a dedicated branch, **never push to main**.
- **sbs_utils** (enablers: seed, coverage hook, runner test mode, invariant
  sink, report): continue on the current working branch.
- **Ask before pushing** either repo.
