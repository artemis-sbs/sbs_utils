"""
MAST runtime benchmark — runs a (synthetic) mission and times the scheduler.

Gives Tier 2 of MAST_RUNTIME_IMPROVEMENTS.md a before/after number, the way
scratchpad/bench_compile.py did for the parser. Doubles as a **working-tree**
smoke: it ticks a real running mission against the edited source, NOT a packaged
.sbslib (see memory: project_smoke_run_sbslib_shadow).

Lives in <repo>/bench/, which is tracked in git but is NOT packaged into any
.sbslib (only sbs_utils/ and cosmos_dev/ are zipped). So it never ships and never
shadows the runtime.

The mission (bench/bench_mission.mast) spawns N live worker tasks, each with M
`on change` watchers over a wide shared symbol table; every scheduler tick drives
~N*M expression evals through get_symbols() + eval() and the run_on_change() path
(the P1/P2 hot paths).

Usage (from the sbs_utils repo root):
    python -m bench.bench_runtime                      # default scale
    python -m bench.bench_runtime --workers 400 --ticks 300
    python -m bench.bench_runtime --profile            # cProfile top hotspots
    python bench/bench_runtime.py                       # also works
"""
from __future__ import annotations

import os
import sys
import time

# --- force working-tree precedence -----------------------------------------
# This file lives at <repo>/bench/bench_runtime.py; the package root is the
# parent of bench/. Put it first so `import sbs_utils` resolves to the edited
# source, never a packaged artemis-sbs.sbs_utils.*.sbslib on the path.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
elif sys.path[0] != _REPO_ROOT:
    sys.path.remove(_REPO_ROOT)
    sys.path.insert(0, _REPO_ROOT)

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.agent import clear_shared, Agent
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.mast_sbs import story_nodes  # registers Cosmos MAST nodes (explicit)
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent
import sbs_utils.procedural.execution as ex
import sbs_utils.procedural.timers as timers

test_set_exe_dir()
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.timers')
MastGlobals.import_python_module('sbs_utils.procedural.signal')

from cosmos_dev.mock import sbs

_MISSION_FILE = os.path.join(os.path.dirname(__file__), "bench_mission.mast")


def _noop_log(*_a, **_k):
    """Swallow MAST log() so file/console I/O does not skew timings."""
    return None


Mast.make_global_var("log", _noop_log)


class _BenchScheduler(MastScheduler):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.runtime_errors = 0

    def runtime_error(self, message):
        self.runtime_errors += 1
        print(f"  RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0

    def tick(self):
        self.time_tick_counter += 30


def build_runner(workers):
    with open(_MISSION_FILE, "r") as f:
        source = f.read()
    mast = Mast()
    clear_shared()
    errors = mast.compile(source, "bench_mission", mast)
    if errors:
        for e in errors:
            print(e)
        raise SystemExit("bench mission failed to compile")
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = _BenchScheduler(mast)
    # Start "main" so the top-level `shared s0..s9 = 1` init runs, then falls
    # through into bench_main (which spawns the workers).
    runner.start_task("main", inputs={"WORKERS": workers})
    return runner


def run_ticks(runner, ticks, mutate_every):
    """Tick the scheduler `ticks` times, occasionally mutating shared vars so a
    fraction of watchers actually fire (exercises the run()/push path too)."""
    for t in range(ticks):
        if mutate_every and t % mutate_every == 0:
            Agent.SHARED.set_inventory_value("s0", (t % 3) + 1)
            Agent.SHARED.set_inventory_value("s5", (t % 5) + 1)
        runner.tick()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="MAST runtime benchmark")
    ap.add_argument("--workers", type=int, default=200, help="live worker tasks")
    ap.add_argument("--ticks", type=int, default=300, help="scheduler ticks to time")
    ap.add_argument("--mutate-every", type=int, default=7,
                    help="mutate shared vars every N ticks (0 = never)")
    ap.add_argument("--profile", action="store_true",
                    help="run under cProfile and print top cumulative functions")
    args = ap.parse_args()

    import sbs_utils.mast.mastscheduler as _m
    print(f"sbs_utils loaded from: {_m.__file__}")
    if ".sbslib" in _m.__file__:
        print("  !! WARNING: running a PACKAGED sbslib, not the working tree !!")

    runner = build_runner(args.workers)
    tasks = len(runner.tasks)
    watchers = sum(len(t.on_change_items) for t in runner.tasks)
    print(f"scale: {tasks} live tasks, {watchers} on_change watchers, "
          f"{args.ticks} ticks, mutate every {args.mutate_every}")

    if args.profile:
        import cProfile
        import pstats
        import io
        pr = cProfile.Profile()
        pr.enable()
        run_ticks(runner, args.ticks, args.mutate_every)
        pr.disable()
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(18)
        print(s.getvalue())
        print(f"runtime errors: {runner.runtime_errors}")
        return

    run_ticks(runner, 1, 0)  # warm: let spawns settle (not timed)
    t0 = time.perf_counter()
    run_ticks(runner, args.ticks, args.mutate_every)
    elapsed = time.perf_counter() - t0

    per_tick_ms = elapsed / args.ticks * 1000.0
    print(f"runtime errors: {runner.runtime_errors}")
    print(f"total: {elapsed*1000:.1f} ms over {args.ticks} ticks")
    print(f"per-tick: {per_tick_ms:.3f} ms  ({1000.0/per_tick_ms:.0f} ticks/s)")
    if watchers:
        print(f"~{watchers} watcher-evals/tick "
              f"-> {watchers/(per_tick_ms/1000.0):,.0f} evals/s")


if __name__ == "__main__":
    main()
