"""Tests for a2x AI helpers (2.8 add_ai/clear_ai -> brains)."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import brain
from sbs_utils.procedural.a2x.ai import ai_brain_for, add_ai, clear_ai


class A2xAiPureTests(unittest.TestCase):
    def test_brain_for_known(self):
        self.assertEqual(ai_brain_for("CHASE_PLAYER"), "ai_chase_player")
        self.assertEqual(ai_brain_for("chase_station"), "ai_chase_station")
        self.assertEqual(ai_brain_for(" CHASE_AI_SHIP "), "ai_chase_npc")

    def test_brain_for_unmapped(self):
        self.assertIsNone(ai_brain_for("PROCEED_TO_EXIT"))
        self.assertIsNone(ai_brain_for(None))


class A2xAiDispatchTests(unittest.TestCase):
    """add_ai/clear_ai delegate to core brain_add/brain_clear (label resolution
    itself needs a loaded MAST story, exercised at runtime/convert, so stub here)."""

    def setUp(self):
        self.calls = []
        self._add, self._clear = brain.brain_add, brain.brain_clear
        brain.brain_add = lambda agent, label, data=None, **kw: self.calls.append(("add", agent, label, data))
        brain.brain_clear = lambda agent: self.calls.append(("clear", agent))

    def tearDown(self):
        brain.brain_add, brain.brain_clear = self._add, self._clear

    def test_add_ai_known_calls_brain_add(self):
        self.assertEqual(add_ai("KR01", "CHASE_PLAYER"), "ai_chase_player")
        self.assertEqual(self.calls, [("add", "KR01", "ai_chase_player", None)])

    def test_add_ai_unmapped_skips_brain_add(self):
        self.assertIsNone(add_ai("KR02", "GUARD_STATION"))
        self.assertEqual(self.calls, [])

    def test_clear_ai_calls_brain_clear(self):
        clear_ai("KR03")
        self.assertEqual(self.calls, [("clear", "KR03")])


if __name__ == "__main__":
    unittest.main()
