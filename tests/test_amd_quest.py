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

    def test_destroy_enemies_is_diplomacy_based(self):
        # The general, faction-agnostic, ceasefire-safe kill goal: scores by
        # diplomacy (hostile) rather than binding to a specific faction role.
        self.assertEqual(amd_trigger("destroy 5 enemies"),
                         ("on_kill", {"hostile": True, "count": 5}))
        self.assertEqual(amd_trigger("kill hostiles"),
                         ("on_kill", {"hostile": True, "count": 1}))

    def test_signal_normalizes_case_and_spaces(self):
        self.assertEqual(amd_trigger("signal Xorn Defected"),
                         ("on_signal", {"name": "xorn_defected"}))

    def test_reach_sector(self):
        self.assertEqual(amd_trigger("reach 6, 4"),
                         ("on_reach", {"sector": [6, 4]}))

    def test_reach_landmark_role(self):
        # 2.8 "fly within R of <object>" -> a landmark reach (role + radius), not a sector
        self.assertEqual(amd_trigger("reach relay 7000"),
                         ("on_reach", {"role": "relay", "radius": 7000}))
        self.assertEqual(amd_trigger("travel starbase"),
                         ("on_reach", {"role": "starbase"}))
        # alias resolution still applies to the role
        self.assertEqual(amd_trigger("reach derelict", {"derelict": "universe_derelict"}),
                         ("on_reach", {"role": "universe_derelict"}))

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

    def test_reveals_sets_reveal_scan(self):
        # Declarative science-scan content: `Reveals:` carries what a scan returns, so a
        # `Goal: scan X` quest needs no hand-authored //science route.
        d = amd_quest_data("Goal: scan anomaly\nReveals: A stable subspace distortion.")
        self.assertEqual(d["on_scan"], {"role": "anomaly", "count": 1})
        self.assertEqual(d["reveal_scan"], "A stable subspace distortion.")

    def test_scan_text_alias(self):
        self.assertEqual(amd_quest_data("Scan text: Bio-signs detected.")["reveal_scan"],
                         "Bio-signs detected.")


class MissionTreeTests(unittest.TestCase):
    def test_parent_required_critical(self):
        d = amd_quest_data("Parent: siege_mission\nRequired: true\nCritical: true")
        self.assertEqual(d["parent"], "siege_mission")
        self.assertTrue(d["required"])
        self.assertTrue(d["critical"])

    def test_win_prose_becomes_reason_text(self):
        d = amd_quest_data("Win: Victory! The starbases held.")
        self.assertTrue(d["end_win"])
        self.assertEqual(d["win_text"], "Victory! The starbases held.")

    def test_win_bare_flag_has_no_text(self):
        d = amd_quest_data("Win: true")
        self.assertTrue(d["end_win"])
        self.assertNotIn("win_text", d)

    def test_win_false(self):
        self.assertFalse(amd_quest_data("Win: false")["end_win"])

    def test_lose_prose(self):
        d = amd_quest_data("Lose: The starbases have fallen.")
        self.assertTrue(d["end_lose"])
        self.assertEqual(d["lose_text"], "The starbases have fallen.")

    def test_fail_on_signal(self):
        self.assertEqual(amd_quest_data("Fail on signal: Siege Bases Lost")["fail_on_signal"],
                         {"name": "siege_bases_lost"})

    def test_fail_on_all_dead_keeps_boss_and_singularizes(self):
        self.assertEqual(amd_quest_data("Fail on all dead: convoys")["fail_on_all_dead"],
                         {"role": "convoy"})
        self.assertEqual(amd_quest_data("Fail on all dead: boss")["fail_on_all_dead"],
                         {"role": "boss"})

    def test_fail_after_minutes_and_seconds(self):
        self.assertEqual(amd_quest_data("Fail after: 10 minutes")["fail_after"], {"minutes": 10})
        self.assertEqual(amd_quest_data("Fail after: 30 seconds")["fail_after"], {"seconds": 30})


if __name__ == "__main__":
    unittest.main()
