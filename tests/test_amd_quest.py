"""Tests for the shared AMD quest vocabulary (sbs_utils.procedural.amd_quest).

This is the grammar the LM siege map and Open Universe both parse, so siege AMD is
a strict subset of universe AMD. Run:
    python -m unittest tests.test_amd_quest
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_quest import (
    amd_trigger, amd_reward, amd_quest_facts, amd_quest_data, TRIGGER_VERBS)


class AmdTriggerTests(unittest.TestCase):
    def test_destroy_role_count(self):
        self.assertEqual(amd_trigger("destroy 4 raiders"),
                         ("on_kill", {"role": "raider", "count": 4}))

    def test_kill_singularizes_and_defaults_count_1(self):
        self.assertEqual(amd_trigger("kill boss"),
                         ("on_kill", {"role": "boss", "count": 1}))

    def test_signal_normalizes_case_and_spaces(self):
        self.assertEqual(amd_trigger("signal Xorn Defected"),
                         ("on_signal", {"name": "xorn_defected"}))

    def test_reach_sector(self):
        self.assertEqual(amd_trigger("reach 6, 4"),
                         ("on_reach", {"sector": [6, 4]}))

    def test_collect_key_count(self):
        self.assertEqual(amd_trigger("recover 3 provisions"),
                         ("on_collect", {"key": "provisions", "count": 3}))

    def test_aliases_map_role(self):
        self.assertEqual(amd_trigger("scan 1 derelict", {"derelict": "universe_derelict"}),
                         ("on_scan", {"role": "universe_derelict", "count": 1}))

    def test_unknown_verb_is_none(self):
        self.assertIsNone(amd_trigger("frobnicate the widget"))

    def test_verb_table_covers_the_drivers(self):
        for v in ("destroy", "kill", "collect", "scan", "dock", "reach", "signal"):
            self.assertIn(v, TRIGGER_VERBS)


class AmdRewardTests(unittest.TestCase):
    def test_credits(self):
        self.assertEqual(amd_reward("300 credits"), {"credits": 300})

    def test_no_number_is_zero(self):
        self.assertEqual(amd_reward("a favor"), {"credits": 0})


class AmdQuestFactsTests(unittest.TestCase):
    def test_full_quest_fence(self):
        text = ("Goal: destroy 3 raiders\n"
                "When: signal xorn_defected\n"
                "Then: reveal step2\n"
                "Pays: 300 credits\n"
                "Scope: shared\n"
                "State: secret\n"
                "Win: true")
        d = amd_quest_data(text)
        self.assertEqual(d["on_kill"], {"role": "raider", "count": 3})
        self.assertEqual(d["objective"], "Destroy 3 raiders")
        self.assertEqual(d["on_signal"], {"name": "xorn_defected"})
        self.assertEqual(d["reveal"], "step2")
        self.assertEqual(d["reward"], {"credits": 300})
        self.assertEqual(d["scope"], "shared")
        self.assertEqual(d["state"], "secret")
        # Win/Lose unify on end_win/end_lose - the LM quest end-game driver's keys.
        self.assertTrue(d["end_win"])

    def test_lose_maps_to_end_lose(self):
        self.assertTrue(amd_quest_data("Lose: true")["end_lose"])

    def test_handler_returns_none_for_unknown_label(self):
        # so a mission can chain its own handler after this one
        self.assertIsNone(amd_quest_facts()({}, "disposition", "foe"))

    def test_when_without_verb_kept_as_when(self):
        self.assertEqual(amd_quest_data("When: the stars align")["when"], "the stars align")


if __name__ == "__main__":
    unittest.main()
