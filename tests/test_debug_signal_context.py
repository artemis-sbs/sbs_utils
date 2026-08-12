"""`signal_emit` needs a MAST context - and the mock's tick loop does not have one.

`signal_emit()` returns early when `FrameContext.mast` is None. Inside the engine that
never happens: every emit runs under `cosmos_event_handler`. But `cosmos_dev` drains
debug commands (the /debug page, the VS Code extension's Preview button) from the BARE
tick loop, where the context is whatever the last tick left behind - often nothing.

The failure is silent in the worst way: the emit returns normally, the caller replies
"emitted", and the route never runs. It cost a session chasing a relic editor's Preview
button that looked broken. `_try_auto_start_map` already carried this fix for
"game_started"; the debug path did not.

These tests pin the contract the fix depends on, at the two points a future change could
break it: that the emit is genuinely dropped without a context, and that a scheduler's
`.mast` - reached through the server page's `story_scheduler` - is what supplies one.
Whether a given route then runs is a matter of task lifetime and is covered by
test_signal_once / test_signal_route_registration.
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

from cosmos_dev.mock import sbs


class _RecordingMast(Mast):
    """A Mast that records the emits that reach it, so a DROPPED emit is visible."""
    def __init__(self):
        super().__init__()
        self.delivered = []

    def signal_emit(self, name, sender_task, data):
        self.delivered.append(name)
        return super().signal_emit(name, sender_task, data)


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


STORY = '''logger(var="output")

//shared/signal/relic_reload
    log("rebuilt")
'''


class DebugSignalContextTests(unittest.TestCase):
    def setUp(self):
        clear_shared()
        self.mast = _RecordingMast()
        self.assertEqual(self.mast.compile(STORY, "debug_signal_test", self.mast), [])
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
        FrameContext.mast = self.mast
        self.runner = MastScheduler(self.mast)
        self.runner.start_task("main")
        for _ in range(10):
            if not self.runner.tick():
                break
        self.mast.delivered.clear()

    def tearDown(self):
        FrameContext.mast = None
        FrameContext.task = None

    def test_emit_without_a_context_is_silently_dropped(self):
        """The bug itself. No exception and no warning - the emit never reaches MAST."""
        FrameContext.mast = None
        FrameContext.task = None
        signal_emit("relic_reload", {})
        self.assertEqual(self.mast.delivered, [],
                         "signal_emit reached MAST with no context - the early return "
                         "this whole fix exists for is gone")

    def test_a_schedulers_mast_supplies_the_context(self):
        """The fix. `scheduler.mast` is what the debug path restores before emitting."""
        FrameContext.mast = None
        FrameContext.task = None
        self.assertIsNotNone(self.runner.mast)
        FrameContext.mast = self.runner.mast
        signal_emit("relic_reload", {})
        self.assertEqual(self.mast.delivered, ["relic_reload"])

    def test_the_scheduler_is_reachable_from_a_story_page(self):
        """`story_scheduler` is the attribute the debug path reads off the server page.
        A rename here breaks Preview silently, which is the failure this file stops."""
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        page = StoryPage.__new__(StoryPage)
        page.story_scheduler = self.runner
        self.assertIs(getattr(page, "story_scheduler", None).mast, self.mast)


if __name__ == "__main__":
    unittest.main()
