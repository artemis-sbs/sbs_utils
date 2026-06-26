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
from sbs_utils.mast.mast_globals import MastGlobals
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


class TestDefaultAssignToGlobal(unittest.TestCase):
    """A `default name = ...` to a global/keyword is a legitimate fallback (debug.mast's
    `default elite_get_all_abilities = None`) and must NOT error - including on an
    in-process recompile where the name is still a global from the prior compile. A hard
    `name = ...` to a global is still an error."""

    def setUp(self):
        Agent.clear()
        clear_shared()
        self._added = []

    def tearDown(self):
        for k in self._added:
            MastGlobals.globals.pop(k, None)

    def _register_global(self, name):
        MastGlobals.globals[name] = (lambda: None)
        self._added.append(name)

    def test_default_to_global_is_allowed(self):
        self._register_global("helper_fn_x")                    # as if an import added it
        m = Mast()
        errs = m.compile("== top_x ==\n    default helper_fn_x = None\n    ->END\n", "<t>", m)
        self.assertEqual(errs, [])                              # default is exempt

    def test_hard_assign_to_global_still_errors(self):
        self._register_global("helper_fn_y")
        m = Mast()
        errs = m.compile("== top_y ==\n    helper_fn_y = None\n    ->END\n", "<t>", m)
        self.assertTrue(any("keyword" in e for e in errs))      # hard assign still guarded


if __name__ == "__main__":
    unittest.main()
