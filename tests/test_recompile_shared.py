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


class TestMastGlobalsReset(unittest.TestCase):
    def test_reset_drops_mission_globals_keeps_builtins(self):
        MastGlobals._builtin_keys = None
        MastGlobals.mark_builtins()                              # snapshot baseline
        MastGlobals.globals["mission_helper_xyz"] = lambda: None  # a mission addition
        MastGlobals._imported_mods.add("mission_mod_xyz")
        MastGlobals.reset()
        self.assertNotIn("mission_helper_xyz", MastGlobals.globals)     # dropped
        self.assertNotIn("mission_mod_xyz", MastGlobals._imported_mods)  # import dedup cleared
        self.assertIn("math", MastGlobals.globals)                      # built-in kept

    def test_default_assign_to_imported_name_survives_recompile(self):
        # Mirrors the elite_get_all_abilities crash: a `default name = None` that
        # precedes the import which registers `name` as a global. First compile (name
        # already a global) errors; the runner's reset (Agent + shared + MAST globals)
        # makes the recompile clean again.
        src = "== top_x ==\n    default helper_fn_x = None\n    ->END\n"
        Agent.clear(); clear_shared()
        MastGlobals._builtin_keys = None; MastGlobals.mark_builtins()
        MastGlobals.globals["helper_fn_x"] = lambda: None       # as if an import added it
        m = Mast()
        errs = m.compile(src, "<t>", m)
        self.assertTrue(any("keyword" in e for e in errs))      # reproduces the crash
        Agent.clear(); clear_shared(); MastGlobals.reset()      # full reload reset
        m2 = Mast()
        self.assertEqual(m2.compile(src, "<t>", m2), [])        # clean after reset


if __name__ == "__main__":
    unittest.main()
