"""Microbenchmark for MAST task scope + Agent registry bookkeeping.

Isolates the paths that dominate a busy mission's frame once finished tasks are
disposed: creating a task (which copies the parent scope), registering every
variable name in the class-level Agent registries, and unregistering them again
on disposal.

Deterministic and single-threaded on purpose -- the mission runner's numbers move
with physics/GIL noise, so use this to compare code changes and the runner's
--probe-leak / cProfile output to confirm the change shows up for real.

    python -m cosmos_dev.bench_task_scope
    python -m cosmos_dev.bench_task_scope --tasks 20000 --scope 40 --repeat 5
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import argparse
import gc
import time

from sbs_utils.agent import Agent, clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.mastscheduler import MastAsyncTask, MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)

import sbs_utils.procedural.execution as ex  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')

from cosmos_dev.mock import sbs


class _BenchScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


def _fresh(scope_vars):
    """A scheduler whose root task carries `scope_vars` variables."""
    Agent.clear()
    gc.collect()
    mast = Mast()
    clear_shared()
    errors = mast.compile('x = 1\n->END\n=== child\n    y = 2\n    ->END\n', "bench", mast)
    assert not errors, errors
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = _BenchScheduler(mast)
    parent = runner.start_task("main")
    for i in range(scope_vars):
        parent.set_inventory_value(f"scope_var_{i}", i)
    return runner, parent


def _bench_once(n_tasks, scope_vars, distinct=0):
    runner, parent = _fresh(scope_vars)

    # A real mission's inventory registry is ~1500 collections wide (every distinct
    # variable name across every label), not the handful a uniform benchmark makes.
    # --distinct widens it so registry-width effects are visible here too.
    for i in range(distinct):
        Agent._has_inventory.add_to_collection(f"wide_name_{i}", parent.id)

    t0 = time.perf_counter()
    tasks = [parent.start_task("child", task_name=None) for _ in range(n_tasks)]
    t_create = time.perf_counter() - t0

    widths = (len(Agent.roles.collections),
              len(Agent._has_inventory.collections),
              len(Agent.has_links.collections))
    agents_peak = len(Agent.all)

    t0 = time.perf_counter()
    for t in tasks:
        t.dispose()
    t_dispose = time.perf_counter() - t0

    # The parent task is still running, so it SHOULD remain registered.
    leftover = sum(1 for a in Agent.all.values()
                   if isinstance(a, MastAsyncTask) and a is not parent)
    return {
        "create_s": t_create,
        "dispose_s": t_dispose,
        "widths": widths,
        "agents_peak": agents_peak,
        "leftover_tasks": leftover,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", type=int, default=10000,
                    help="tasks created (and disposed) per run")
    ap.add_argument("--scope", type=int, default=30,
                    help="variables in the parent scope each task inherits")
    ap.add_argument("--repeat", type=int, default=3, help="runs; the BEST is reported")
    ap.add_argument("--distinct", type=int, default=0, metavar="N",
                    help="pad the inventory registry with N extra distinct names, "
                         "so its width resembles a real mission (~1500)")
    args = ap.parse_args()

    print(f"tasks={args.tasks} scope_vars={args.scope} distinct={args.distinct} repeat={args.repeat}")
    best = None
    for i in range(args.repeat):
        r = _bench_once(args.tasks, args.scope, args.distinct)
        tag = ""
        if best is None or (r["create_s"] + r["dispose_s"]) < (best["create_s"] + best["dispose_s"]):
            best = r
            tag = "  <- best"
        print(f"  run {i+1}: create {r['create_s']*1000:8.1f}ms  "
              f"dispose {r['dispose_s']*1000:8.1f}ms{tag}")

    n = args.tasks
    print()
    print(f"create   {best['create_s']*1000:9.1f} ms   {best['create_s']/n*1e6:7.2f} us/task")
    print(f"dispose  {best['dispose_s']*1000:9.1f} ms   {best['dispose_s']/n*1e6:7.2f} us/task")
    print(f"total    {(best['create_s']+best['dispose_s'])*1000:9.1f} ms")
    print(f"registry widths  roles={best['widths'][0]} "
          f"inventory={best['widths'][1]} links={best['widths'][2]}")
    print(f"agents at peak   {best['agents_peak']}")
    print(f"tasks left after dispose  {best['leftover_tasks']} (must be 0)")


if __name__ == "__main__":
    main()
