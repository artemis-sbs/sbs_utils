"""A @map label must launch exactly once.

Two independent launchers schedule a map: LM's server-console `start` path
(`task_schedule(WORLD_SELECT)`) and cosmos_dev's `--map` auto-start. When both fired,
the whole map body re-ran and every spawn was duplicated -- and because map seeds are
fixed, the duplicates landed on IDENTICAL positions, so it read as a content bug
rather than a double launch. Observed on the a2x hamaksector conversion: 1392 terrain
objects (461 nebulae + 931 asteroids) became 2784, each at two ids on one position.

The guard lives in cosmos_dev (mission_runner.install_map_launch_guard patches
MastScheduler.start_task for the session), NOT in the shipped library: neither
launcher exists in the engine - one server console, no --map auto-start - so the
library keeps its exact production behaviour. Non-map labels keep the normal
behaviour (many concurrent tasks), and a map may be launched again once its previous
task has ended, so mission restart still works.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.agent import clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

import sbs_utils.procedural.execution as ex  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')

from cosmos_dev.mock import sbs
from cosmos_dev.mission_runner import (
    install_map_launch_guard, live_map_task, map_label_name,
)

# The guard is a harness patch, so the behaviour under test only exists once the
# runner has installed it. Idempotent, so repeated calls across the suite are fine.
install_map_launch_guard()


class _TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


STORY = """->END

@map/dup_probe "Dup Probe"
    ->END

== plain_label ==
    ->END
"""


def _compile(code=STORY):
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "map_launch_test", mast)
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    return errors, _TMastScheduler(mast)


class TestMapLaunchOnce(unittest.TestCase):
    def setUp(self):
        self.errors, self.runner = _compile()
        self.assertEqual(self.errors, [])
        # Guard the premise: a @map label is registered under a "map/" key, and the
        # Label's own name matches that key (it carries the same trailing qualifier),
        # so a caller passing the key and one passing the object agree.
        self.map_key = next(k for k in self.runner.mast.labels if k.startswith("map/"))
        self.map_label = self.runner.mast.labels[self.map_key]
        self.assertEqual(self.map_label.name, self.map_key)

    def _drain(self, limit=20):
        for _ in range(limit):
            if not self.runner.tick():
                break

    def test_second_launch_returns_the_running_task(self):
        # defer=True so neither task ticks: the first is still live when the second
        # launch arrives, which is exactly the double-launch window.
        t1 = self.runner.start_task(self.map_key, defer=True)
        before = len(self.runner.tasks)
        t2 = self.runner.start_task(self.map_key, defer=True)
        self.assertIs(t2, t1, "second map launch must hand back the running task")
        self.assertEqual(len(self.runner.tasks), before, "no extra task scheduled")

    def test_label_object_and_name_are_the_same_map(self):
        # The two real callers disagree on type: the console passes the Label object
        # (WORLD_SELECT), the runner passes it too, but MAST scripts can pass a name.
        t1 = self.runner.start_task(self.map_label, defer=True)
        t2 = self.runner.start_task(self.map_key, defer=True)
        self.assertIs(t2, t1)

    def test_relaunch_allowed_once_the_map_task_has_ended(self):
        t1 = self.runner.start_task(self.map_key, defer=True)
        self._drain()
        self.assertIsNone(live_map_task(self.runner, self.map_label.name),
                          "an ended map task must not block a relaunch (mission restart)")
        t2 = self.runner.start_task(self.map_key, defer=True)
        self.assertIsNot(t2, t1)

    def test_non_map_labels_are_unaffected(self):
        t1 = self.runner.start_task("plain_label", defer=True)
        t2 = self.runner.start_task("plain_label", defer=True)
        self.assertIsNot(t2, t1, "ordinary labels still get one task per schedule")
        self.assertIsNone(map_label_name(self.runner, "plain_label"))
        self.assertEqual(map_label_name(self.runner, self.map_key), self.map_key)
        self.assertEqual(map_label_name(self.runner, self.map_label), self.map_key)


if __name__ == "__main__":
    unittest.main()
