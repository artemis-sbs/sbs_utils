# MAST Runtime — Performance & Robustness Improvements

Planning/tracking doc for proposed changes to the MAST **runtime** (execution
layer), as distinct from the compiler/parser work tracked in
[MAST_PARSER_IMPROVEMENTS.md](MAST_PARSER_IMPROVEMENTS.md). Started 2026-06-23.

> **Status: PLANNING ONLY.** No runtime changes have been made. This document is
> speculation + a plan to be reviewed before any code is touched. The runtime is
> higher-risk than the parser: a parser change can only break compilation (loud,
> at load time), but a runtime change can subtly alter *mission behavior* in the
> field. Treat every item here as a hypothesis until confirmed.

---

## Runtime model (as currently understood)

The execution stack, bottom to top:

- **`MastScheduler`** ([mastscheduler.py](sbs_utils/mast/mastscheduler.py)) — owns
  a list of `MastAsyncTask`s; `tick()` ticks each task, harvests `done`, then runs
  `run_on_change()` across all tasks. `StoryScheduler`
  ([maststoryscheduler.py](sbs_utils/mast_sbs/maststoryscheduler.py)) is the
  Cosmos subclass: adds `client_id`/`page`, the full scope-resolution chain
  (SHARED → CLIENT → ASSIGNED ship → task), and routes runtime errors to
  `sbs.pause_sim()` + an error page.

- **`MastAsyncTask`** — both an `Agent` and a `Promise`. Holds **two tickers**:
  - `MastTicker` — interprets compiled `.mast` nodes.
  - `PyTicker` — drives PyMAST Python generators (`@label()` functions).
  - `active_ticker` switches between them inside `jump()` based on label type.
  - Variable scope lives in the task's `inventory`; `get_symbols()` builds the
    eval namespace by union-ing SHARED ▸ scheduler ▸ task inventory ▸
    label_stack data on **every** `eval_code`/`format_string` call.

- **`MastTicker.tick()`** — the core interpreter loop:
  - Applies `pending_jump` (wins) or `pending_pop`.
  - Polls `runtime_node.poll()` and dispatches on `PollResults`
    (`OK_ADVANCE_TRUE/FALSE`, `OK_YIELD`, `OK_END`, `OK_IDLE`, `OK_RUN_AGAIN`,
    `OK_JUMP`).
  - `next()` runs `leave()`, advances `active_cmd`, and either builds the next
    runtime node or falls through to the next label (`prune_main()` on wrap).
  - Has a `count > 100000` runaway-loop guard that prints but does **not** stop.

- **Control flow / stack** — `label_stack` of `PushData`. Two push styles:
  - `push_label` — true call (saves label+cmd, jumps).
  - `push_inline_block` — buttons/dropdowns/events; resumes the *same* runtime
    node after the block, tracked via `pop_on_jump` counter.
  - `jump` cancels outstanding `pop_on_jump` entries; pending_jump trumps
    pending_pop.

- **on_change** — `OnChange` nodes register on the task; `run_on_change()` tests
  each and re-runs/jumps when the watched expression changes. GUI tasks
  double-buffer via `pending_on_change_items` / `swap_on_change()`.

- **`PollResults`** ([pollresults.py](sbs_utils/mast/pollresults.py)) — IntEnum;
  note `OK_END == OK_SUCCESS == BT_SUCCESS == 99` and `FAIL_END == BT_FAIL == 100`
  (behavior-tree yields reuse the same codes).

---

## Direction (confirmed 2026-06-23)

- **Goals:** performance + robustness/crash-hardening + code clarity/de-risk.
- **Scope:** generic `mast/` **and** Cosmos `mast_sbs/`.
- **Risk bar:** *fix clear bugs, gated* — behavior-changing fixes are allowed but
  each is called out explicitly and approved **individually** before applying.
- **This pass produces the plan only. No runtime code is changed yet.**

### Validation bar
- **Unit floor:** existing `tests/` suite (was 350) **+ 15 new runtime
  characterization tests** → **365 OK**. New file
  [tests/test_mast_runtime.py](tests/test_mast_runtime.py) pins previously
  uncovered runtime behavior:
  - `StoryScheduler` scope resolution (SHARED/CLIENT/ASSIGNED/NORMAL precedence,
    set_value handling, and that `get_symbols()` excludes client/ship) → guards **P1**
  - PyMAST (`PyTicker`) fall-through after a yield → guards **T3.1**
  - `on_change` runtime fires once per change, not when unchanged → guards **P2**
- **Runtime benchmark + working-tree smoke:** [bench/bench_runtime.py](bench/bench_runtime.py)
  runs [bench/bench_mission.mast](bench/bench_mission.mast) (a real running
  mission) against the **working tree** and reports ticks/sec + cProfile
  hotspots. `bench/` is tracked in git but **not packaged** (only `sbs_utils/`
  and `cosmos_dev/` are zipped into sbslibs), so it never ships and never
  shadows the runtime. Run: `python -m bench.bench_runtime [--profile]`.
  The clean tick (0 runtime errors) IS the working-tree smoke.
- **Real full-mission smoke (HelloWorld etc.) — still optional/BLOCKED on the
  sbslib-shadow setup (see below).**

#### Baseline numbers (2026-06-23, before any Tier 2 change)
Scale: 200 worker tasks, 1000 `on change` watchers, 300 ticks.
- **6.2 ms/tick, 161 ticks/s, ~160k watcher-evals/s.**

cProfile (200 ticks, by cumulative / self time) — **P1 confirmed**:
| function | calls | cum | tot(self) |
|---|---:|---:|---:|
| `MastScheduler.tick` | 200 | 3.15s | — |
| `run_on_change` | 40,200 | **2.54s (~80%)** | — |
| `eval_code` | 220,000 | 1.37s | — |
| `OnChange.test` | 200,000 | 1.37s | — |
| **`get_symbols`** | 220,000 | 1.03s | **0.92s (~30% of total)** |

`get_symbols` (the dict-union per eval) is the single largest **self-time**
function — but see **P1 below**: that self-time is inherent per-key copy cost,
so making each `get_symbols` call cheaper (ChainMap / one-pass) did **not** speed
the bench up. The bench remains the harness for any future call-count-reduction
attempt.

#### ✅ Real-mission smoke: LegendaryMissions `@map/siege` (headless, working tree)
Now boots and runs clean headless (0 runtime errors, 0 tracebacks) against the
working tree. Required fixing real bugs found along the way:

- **Side/player ordering race (engine bug too).** Sides (`tsn`/`raider`/`civ`)
  were created in a `//shared/signal/game_started` route via `await prefab_spawn`,
  which raced the map's `spawn_players` → "Side not found" + `set_diplomacy_color`
  on `None`. **Fix (LegendaryMissions):** moved side+diplomacy creation into a
  `=== create_sides_and_diplomacy` label called/awaited at `server_console`
  `start_server` init, before player ships and before any map runs.
  (`maps/watch_for_end.mast`, `consoles/server_console.mast`.)
- **Invalid side on dry-docked ships.** `spawn_players` tagged unused player
  ships `side = "unused"` (not a registered side); the hangar system then spammed
  "Side not found: unused". **Fix (LegendaryMissions):** dropped the assignment
  (ships are already de-roled and deleted). (`fleets/map_common.mast`.)
- **sbs_utils None-derefs (robustness, harmless in engine):**
  - `internal_damage.grid_restore_damcons` — guard `_blob is None` before `.set`.
  - `space_objects.clear_target` — guard `get_space_object()` returning `None`
    (chaser destroyed mid-AI-tick).

Smoke harness: throwaway probe that forces working-tree precedence then calls
`mission_runner._run(..., map_arg="siege")`. (Could be promoted into `bench/` as a
real-mission smoke later.) Remaining noise: 3 benign "Side not found" existence
prints from `prefab_side_generic` creating each side; "Unhandled event collision
passive" (no `//collision/passive` route — expected).

#### ⚠️ Smoke-run gotcha: packaged sbslib shadows the working tree
`cosmos_dev/mission_runner.py` `_load_libs()` does `sys.path.insert(0, lib_path)`
for each entry in the mission's `story.json`. The `__lib__/` folder ships a
**packaged `artemis-sbs.sbs_utils.v1.3.0.sbslib`** that contains a full
top-level `sbs_utils/` package. Verified empirically: a mission run loads
`__lib__\...sbs_utils.v1.3.0.sbslib\sbs_utils\mast\mastscheduler.py`, **not** the
working tree. So a naive `mission_runner` smoke tests the **build artifact**, not
local edits — it would prove nothing about Tier 0/1/2 changes. To get a
meaningful smoke we must force working-tree precedence (pre-import working-tree
`sbs_utils` before `_load_libs`, or temporarily drop the sbs_utils sbslib from
the path). **Need: must-pass mission shortlist + decision to wire a working-tree
smoke harness.**

---

## The plan — tiers by risk

Tiers are ordered by safety. **Tier 0/1 are no-observable-behavior-change**
(the parser-pass bar). **Tier 2 is performance** (needs measurement first).
**Tier 3 is behavior-changing** and each item needs its own sign-off (per the
gated bar). Status legend: 🔎 verified in code · 📐 needs measurement ·
🚧 needs design.

### Tier 0 — pure crash/robustness fixes (no behavior change) ✅ DONE

These mirror the parser pass's #5/#6/#7. Low risk; high cleanliness payoff.
**Applied 2026-06-23; 350 tests still OK (no regression).**

| # | Item | File / loc | Status |
|---|------|-----------|--------|
| R1 | `BaseException`→`OK_END` in `MastTicker.tick()` swallowed `KeyboardInterrupt`/`SystemExit`/`GeneratorExit` | [mastscheduler.py](sbs_utils/mast/mastscheduler.py) ~290 | ✅ narrowed to `Exception` |
| R2 | `PyTicker.tick()` typo `fallthrough - False` (no-op expr) | [mastscheduler.py](sbs_utils/mast/mastscheduler.py) ~436 | ⏸️ **NOT done — gated**, see T3.1 (fixing it changes PyMAST fallthrough behavior) |
| R3 | `remove_all_sub_tasks` called `self.sub_tasks()` (list as fn) → `TypeError`; **also** both it and `remove_sub_task` called non-existent `t.stop()` | [mastscheduler.py](sbs_utils/mast/mastscheduler.py) ~1020 | ✅ both fixed: iterate `list(self.sub_tasks)`, call `t.end()`. Dead code (no callers in sbs_utils), zero behavior risk. **Wider than the original typo-only plan — `t.stop()`→`t.end()` added because `stop` doesn't exist on tasks.** |
| R4 | bare `except:` in `eval_code`/`exec_code`; `BaseException` in `next()` and `format_string()` | [mastscheduler.py](sbs_utils/mast/mastscheduler.py) ~366/~911/~932/~955 | ✅ all four narrowed to `Exception` (5 catch sites total with R1) |

### Tier 1 — clarity / de-risk (no behavior change) 🚧

Make the control-flow code legible so later changes are safe. **No logic edits**
— comments, docstrings, dead-code removal only, each verified inert.

- **C1.** Document the `push_label` vs `push_inline_block` vs `pop_on_jump`
  protocol in one place (a module docstring + a state diagram). This is the
  single most tangled, least-documented part of the runtime.
- **C2.** Triage the commented-out blocks in `do_jump` ("Why is this here?"),
  the `call_leave` "post 1.0" note, and `mastmission.py` (entirely commented
  out — confirm it's dead and either delete or annotate why it's kept).
- **C3.** Name the `PollResults` aliasing explicitly in code comments
  (`OK_END==OK_SUCCESS==BT_SUCCESS==99`) so BT vs flow reuse is obvious.

### Tier 2 — performance (measure before touching) 📐

**Do not optimize without a benchmark first** (parser pass discipline). Build a
runtime micro-bench (hot GUI task with `on change` + f-strings) and profile
before/after.

- **P1. `get_symbols()` dict-union per eval.** ❌ **ATTEMPTED, REVERTED — not
  worth it.** Two behavior-preserving rewrites were built, tested (365 OK), and
  benchmarked A/B (git-stash, same machine):
  - **`ChainMap` (copy-free view):** *regression.* Microbench shows it only wins
    above ~500–800 symbols; realistic tables (tens–low hundreds) favor the dict
    union because eval name lookups go from C-level dict to Python-level chain
    walks. (6.2→8.2 ms/tick on the bench.)
  - **One-pass `.update()` build (one allocation):** **flat / within noise.**
    Rigorous A/B: 200 workers ~5.37→~5.19 ms (~3%, noisy); 500 workers
    ~11.58→~11.72 ms (no win). The profiler's "30% self-time" is **inherent
    per-key copy cost** (copying ~15 symbols into a dict 220k times), not
    allocation overhead — so cheaper *construction* doesn't move the needle.
  - **Conclusion:** the only real lever is calling `get_symbols` **fewer times**
    (e.g. cache a task's symbols across the M watchers in one `run_on_change`
    pass, invalidating after any watcher `run()`), which is **behavior-sensitive
    and overlaps T3** — not a free perf win. The micro-opt path is closed.
  The scope/`get_symbols` characterization tests added for P1 are kept (they
  guard any future caching attempt).
- **P2. `run_on_change()` every tick, every task + sub-task.** Re-`eval`s every
  watched expression each frame. Candidate: only test when the task is the
  active GUI task, or dirty-flag. **Behavior-sensitive — overlaps T3.** ✅
  **MEASURED** — `run_on_change` is ~80% of tick time in the bench (it's the
  caller of the `get_symbols` hot path).
- **P3. Runtime-node re-instantiation per command** (`next()` builds a fresh
  `runtime_node_cls()` each execution). Likely minor; measure before bothering.
  📐

### Tier 3 — behavior-changing bug fixes (INDIVIDUAL sign-off each) 🔎/🚧

Each of these changes observable mission behavior. Per the gated bar, **none
ships without its own approval.** Listed so they're tracked, not lost.

- **T3.1. `PyTicker` `fallthrough - False` → `=`.** The variable `fallthrough`
  is set once at the top of the loop and the typo means the "generator finished"
  branch may take the fallthrough path when it shouldn't. Fixing it changes when
  PyMAST labels fall through to `fall_through_label`. **Needs a PyMAST repro +
  sign-off.** (Also tracked as R2.)
- **T3.2. Runaway-loop guard never stops the task** (~233): at 100k iterations it
  prints and `break`s the inner loop, returning `OK_RUN_AGAIN`, so the task
  re-enters the same spin next frame — a hang, not a guard. A real fix would end
  or error the task, which changes behavior for any mission currently surviving
  on this. **Sign-off + decide policy (error vs end).**
- **T3.3.** Anything P2 (`run_on_change` gating) turns out to require.

---

## Verified-real vs needs-confirmation

**Verified by reading code (🔎):** R1, R2/T3.1, R3, R4, T3.2, P1 (hotness),
`PollResults` aliasing, `StoryScheduler.get_symbols` reduced to `super()`.

**Needs measurement (📐):** all of Tier 2.

**Needs design/triage (🚧):** Tier 1, the validation-mission shortlist.

---

## Decisions / changes log

- 2026-06-23 — Plan drafted, direction confirmed (perf + robustness + clarity;
  both layers; gated bug-fixes).
- 2026-06-23 — **Tier 0 applied** (R1, R3, R4): 5 catch sites narrowed
  `BaseException`/bare `except` → `Exception`; `remove_sub_task` /
  `remove_all_sub_tasks` corrected (`t.stop()`→`t.end()`, list-call typo). Single
  file [mastscheduler.py](sbs_utils/mast/mastscheduler.py). `python -m unittest
  discover -s tests` → **350 OK**, no regression. Not committed yet.
- 2026-06-23 — **Runtime characterization tests added** (15) →
  [tests/test_mast_runtime.py](tests/test_mast_runtime.py); suite **350 → 365 OK**.
  Covers StoryScheduler scope (P1 guard), PyMAST fall-through (T3.1 guard),
  on_change runtime (P2 guard).
- 2026-06-23 — **Runtime benchmark built** ([bench/](bench/), not packaged);
  baseline captured; **cProfile confirms P1** (`get_symbols` ~30% self-time,
  `run_on_change` ~80% cum). Bench is the before/after harness for Tier 2.
- 2026-06-23 — **P1 attempted and REVERTED.** ChainMap regressed; one-pass build
  was flat/noise (rigorous git-stash A/B). `get_symbols` self-time is inherent
  per-key copy cost, not allocation overhead — micro-opt doesn't pay. Working
  tree restored to `afedb08`; 365 tests OK. Negative result recorded under P1.
- **Next / awaiting:** (a) decide whether to pursue the only remaining perf
  lever — **caching get_symbols across watchers per tick** (behavior-sensitive,
  overlaps T3, needs sign-off); (b) Tier 1 clarity docs (safe, no logic change);
  (c) optional full-mission smoke; (d) sign-off for T3.1/T3.2 (gated). Committed:
  Tier 0 + tests + bench (`afedb08`). Nothing else outstanding in the tree.
