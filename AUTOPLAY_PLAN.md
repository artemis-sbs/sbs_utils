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
  `%` selection, scatter, fleet-race weights, faces/names). `seed_value` already
  exists in settings but is unimplemented — that is the prerequisite. Switch the
  autoplayer off `delay_app` (wall clock) onto `delay_sim`.
- **A verdict, not a vibe** — an invariant/oracle layer checked each tick: no
  NaN/inf positions, no negative HP/energy, no orphaned or never-terminating
  tasks, every scheduled task eventually ends, no MAST runtime errors, no Python
  exceptions logged. Any violation = failure with the tick + label. Pipe
  `Mast.include_code` errors and a stderr/exception sink into the verdict.
- **Coverage as the definition of "full"** — instrument the scheduler to record
  visited labels/routes/nodes, then report which `//comms`, `//signal`,
  `//damage`, `@map`, objective, and console labels were never hit. "Full
  systems test" becomes a measurable %, and shows where the autoplayer is blind.
- **Exerciser mode (≠ play-to-win)** — a policy whose goal is *coverage*, not
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

- Seed threading through the RNG (implements the existing `seed_value`).
- `delay_sim` instead of `delay_app` in the autoplayer.
- A node-visit coverage hook in `MastScheduler.tick`.
- An exception / runtime-error sink the runner treats as failure.
- A report emitter (JUnit/TAP).

All of these benefit the library beyond autoplay.

## Open questions / spikes before committing

The two highest-leverage ideas are also the least-validated; spike them first:

1. **Coverage instrumentation** — how cleanly does the scheduler expose node
   identity (file/label/line) to record visited nodes?
2. **Actuate-through-real-API** — does every console action have a clean
   procedural entry point a bot could call, or only data_set side-effects?

## Implementation / workflow notes

- **LegendaryMissions** (the autoplay mastlib, personae, attract director,
  exerciser policy): work on a dedicated branch, **never push to main**.
- **sbs_utils** (enablers: seed, coverage hook, runner test mode, invariant
  sink, report): continue on the current working branch.
- **Ask before pushing** either repo.
