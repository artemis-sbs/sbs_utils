"""A signal emitted from a tick is not lost because the LAST task to run has ended.

Routes drop a signal whose sender task is done. Library code that emits from a tick has
no task of its own: `FrameContext.task` is whatever ran last. When that was a task that
had since finished - a map label that ended long ago - the signal reached no route.
`boarding_visit_ended` and `boarding_came_back` were lost that way (found by the lesson
"Personal quests"), and which run lost them depended on what had ticked just before.

    python -m unittest tests.test_signal_stale_sender
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.agent import clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.signal import signal_emit

import sbs_utils.procedural.execution as ex  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.signal')
MastGlobals.import_python_module('sbs_utils.procedural.timers')

from cosmos_dev.mock import sbs

STORY = '''logger(var="output")

== park ==
    await delay_sim(100000)
    ->END

== short_lived ==
    x = 1
    ->END

//signal/visit_over
    log("HEARD")
'''


class _Scheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


class StaleSenderTests(unittest.TestCase):
    def setUp(self):
        mast = Mast()
        clear_shared()
        self.assertEqual(mast.compile(STORY, "stale_sender", mast), [])
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
        FrameContext.mast = mast
        self.runner = _Scheduler(mast)
        self.runner.start_task("main")
        self.drain()
        self.ended = self.runner.start_task("short_lived")
        self.drain()
        self.addCleanup(setattr, FrameContext, "task", None)
        self.addCleanup(setattr, FrameContext, "mast", None)

    def drain(self, limit=60):
        for _ in range(limit):
            if not self.runner.tick():
                break

    def heard(self):
        return self.runner.get_value("output", None)[0].getvalue()

    def test_the_fixture_has_a_finished_task(self):
        self.assertTrue(self.ended.done())

    def test_a_tick_whose_last_task_has_ended_still_reaches_the_route(self):
        FrameContext.task = self.ended          # what a tick inherits: whatever ran last
        signal_emit("visit_over")
        self.drain()
        self.assertEqual(self.heard(), "HEARD\n")

    def test_with_no_task_at_all_it_always_did(self):
        FrameContext.task = None
        signal_emit("visit_over")
        self.drain()
        self.assertEqual(self.heard(), "HEARD\n")


if __name__ == "__main__":
    unittest.main()
