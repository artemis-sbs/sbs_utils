"""Recompiling a story in one process needs a fresh shared/agent state.

A label registers its name into Agent.SHARED (so MAST can reference labels as
values), and the compiler errors if that name already exists ("Label conflicts
with shared name"). The engine gets a fresh process per mission, but the dev
runner's run_next_mission recompiles IN-PROCESS - so it must reset Agent.clear()
+ clear_shared() first, or the previous compile's label names collide. This pins
that contract (the bug surfaced the first time run_next_mission was exercised).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import sbs_utils.mast_sbs.story_nodes  # register node types
from sbs_utils.mast.mast import Mast
from sbs_utils.agent import Agent, clear_shared


def _compile_label():
    m = Mast()
    return m.compile("== admiral_move_camera_sync ==\n    ->END\n", "<test>", m)


class TestRecompileSharedReset(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()

    def test_recompile_without_reset_conflicts(self):
        self.assertEqual(_compile_label(), [])                 # first compile clean
        errs = _compile_label()                                # recompile, no reset
        self.assertTrue(any("conflicts with shared name" in e for e in errs),
                        "recompiling the same label without clearing SHARED should conflict")

    def test_recompile_after_reset_is_clean(self):
        self.assertEqual(_compile_label(), [])
        Agent.clear()                                          # what the runner reload does
        clear_shared()
        self.assertEqual(_compile_label(), [])                 # clean again


if __name__ == "__main__":
    unittest.main()
