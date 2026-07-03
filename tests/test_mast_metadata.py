"""Label metadata is injected as task variables when a task ENTERS the label.

The single point is MastTicker.do_jump: entering a label (start / jump / reroute
all funnel through a jump) applies that label's metadata block to the task, as
DEFAULTS - a variable already in scope (passed data / live state) wins. Gated by
`label.has_metadata` so labels without metadata pay only a boolean check, and
only a true top-of-label entry (activate_cmd == 0) applies it.
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.mast_sbs import story_nodes  # register story nodes
from sbs_utils.mast.mast import Mast, Scope
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.agent import clear_shared
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast.mast_globals import MastGlobals
for _mod in ('sbs_utils.procedural.execution', 'sbs_utils.procedural.behavior',
             'sbs_utils.procedural.timers', 'sbs_utils.procedural.gui',
             'sbs_utils.procedural.signal'):
    MastGlobals.import_python_module(_mod)
from cosmos_dev.mock import sbs


class _Sim:
    time_tick_counter = 0
    def tick(self):
        self.time_tick_counter += 30


class _Sched(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"MAST runtime error: {message}")


def _run(code, start="main", ticks=8):
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "t", mast)
    assert not errors, f"compile errors: {errors}"
    FrameContext.context = Context(_Sim(), sbs, FakeEvent())
    FrameContext.mast = mast
    r = _Sched(mast)
    r.start_task(start)
    for _ in range(ticks):
        r.tick()
    return r


class TestLabelMetadataInjection(unittest.TestCase):
    # top-level code IS the implicit `main` label; never declare `== main`.
    def test_jump_injects_metadata(self):
        r = _run(
            "jump cfg\n"
            "=== cfg\n"
            "metadata: ``` yaml\n"
            "min_bet: 10\n"
            "width: 4\n"
            "```\n"
            "    shared a = min_bet\n    shared b = width\n    ->END\n")
        self.assertEqual(r.get_value("a")[0], 10)
        self.assertEqual(r.get_value("b")[0], 4)

    def test_existing_variable_wins(self):
        # a var already in scope before entry must beat the metadata default
        r = _run(
            "min_bet = 99\n"
            "jump cfg\n"
            "=== cfg\n"
            "metadata: ``` yaml\n"
            "min_bet: 10\n"
            "```\n"
            "    shared a = min_bet\n    ->END\n")
        self.assertEqual(r.get_value("a")[0], 99)

    def test_task_schedule_injects_metadata(self):
        # the spawn path also enters via a jump, so metadata still injects
        r = _run(
            "await task_schedule(cfg)\n"
            "->END\n"
            "=== cfg\n"
            "metadata: ``` yaml\n"
            "min_bet: 7\n"
            "```\n"
            "    shared a = min_bet\n    ->END\n")
        self.assertEqual(r.get_value("a")[0], 7)

    def test_passed_data_overrides_metadata(self):
        # data passed to task_schedule beats the metadata default
        r = _run(
            "await task_schedule(cfg, {\"min_bet\": 42})\n"
            "->END\n"
            "=== cfg\n"
            "metadata: ``` yaml\n"
            "min_bet: 7\n"
            "```\n"
            "    shared a = min_bet\n    ->END\n")
        self.assertEqual(r.get_value("a")[0], 42)


if __name__ == "__main__":
    unittest.main(verbosity=2)
