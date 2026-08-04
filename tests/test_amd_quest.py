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

    def test_credits_with_trailing_words_is_still_money(self):
        # "300 credits bonus" must not become an ITEM called credits_bonus.
        self.assertEqual(amd_reward("300 credits bonus"), {"credits": 300})

    def test_items(self):
        # Keyed the way `recover 2 torpedoes` keys its goal, so the two agree.
        self.assertEqual(amd_reward("2 torpedoes"),
                         {"credits": 0, "items": {"torpedoes": 2}})

    def test_credits_and_items_together(self):
        # The regression this rewrite exists for: the old parser returned the credits
        # and dropped the torpedoes silently.
        self.assertEqual(amd_reward("300 credits, 2 torpedoes"),
                         {"credits": 300, "items": {"torpedoes": 2}})

    def test_reputation_uses_the_dialogue_grammar(self):
        self.assertEqual(amd_reward("earns tsn honest +10"),
                         {"credits": 0, "reputation": {"tsn": {"honest": 10}}})

    def test_reputation_multiword_pole_and_negative(self):
        self.assertEqual(amd_reward("earns tsn by the book -15"),
                         {"credits": 0, "reputation": {"tsn": {"by_the_book": -15}}})

    def test_penalty_sign_is_authored_not_flipped(self):
        # `Penalty:` and `Pays:` share this parser; a negative stays negative rather
        # than being silently re-signed by the block it sits in.
        self.assertEqual(amd_reward("200 credits, earns tsn diplomatic -15"),
                         {"credits": 200, "reputation": {"tsn": {"diplomatic": -15}}})

    def test_multiple_factions(self):
        self.assertEqual(amd_reward("earns tsn honest +5, earns skaraan feared +3"),
                         {"credits": 0,
                          "reputation": {"tsn": {"honest": 5}, "skaraan": {"feared": 3}}})

    def test_empty_keys_are_absent_not_empty(self):
        # Existing callers compare against the bare {"credits": n} shape.
        self.assertNotIn("items", amd_reward("300 credits"))
        self.assertNotIn("reputation", amd_reward("300 credits"))


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
        self.assertEqual(d["start_trigger"],
                         {"trigger": "on_signal", "data": {"name": "xorn_defected"}})
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


class TestOneTriggerGrammar(unittest.TestCase):
    """`Starts when:` / `Done when:` / `Fails when:` take the SAME trigger. This
    replaced seven differently-shaped fields; the point is that an author learns one
    grammar, so every form is checked against every question that accepts it."""

    def _data(self, line):
        from sbs_utils.procedural.amd_doc import document_get_amd_file
        doc = document_get_amd_file(
            None,
            content=chr(10).join(["# [J](j)", "---", line, "---", "prose", ""]),
            data_parser=amd_quest_data)
        return doc["children"][0].get("data") or {}

    def _data_lines(self, lines):
        from sbs_utils.procedural.amd_doc import document_get_amd_file
        doc = document_get_amd_file(
            None,
            content=chr(10).join(["# [J](j)", "---"] + lines + ["---", "prose", ""]),
            data_parser=amd_quest_data)
        return doc["children"][0].get("data") or {}

    def test_done_when_takes_a_duration(self):
        self.assertEqual(self._data("Done when: 30 seconds")["complete_after"],
                         {"seconds": 30})

    def test_fails_when_reaches_all_three_failure_watchers(self):
        self.assertEqual(self._data("Fails when: signal base_lost")["fail_on_signal"],
                         {"name": "base_lost"})
        self.assertEqual(self._data("Fails when: all dead convoy")["fail_on_all_dead"],
                         {"role": "convoy"})
        self.assertEqual(self._data("Fails when: 5 minutes")["fail_after"],
                         {"minutes": 5})

    def test_starts_when_says_what_At_start_used_to(self):
        # an offered job starts when the player ACCEPTS it; a hidden step when
        # something REVEALS it. Two vocabularies for one fact, now one.
        self.assertEqual(self._data("Starts when: accepted")["state"], "idle")
        self.assertEqual(self._data("Starts when: revealed")["state"], "secret")

    def test_at_once_is_the_third_arming_word(self):
        self.assertEqual(self._data("Starts when: at once")["state"], "active")

    def test_an_explicit_Objective_wins_whatever_the_field_order(self):
        """It used to depend on which line came first: `Done when:` filled the objective
        from its own trigger text and overwrote whatever was above it."""
        for order in (["Objective: Clear the lane", "Done when: destroy 6 raiders"],
                      ["Done when: destroy 6 raiders", "Objective: Clear the lane"]):
            d = self._data_lines(order)
            self.assertEqual(d.get("objective"), "Clear the lane", order[0])

    def test_only_a_doable_verb_stands_in_for_the_objective(self):
        # a kill target reads as an instruction; a signal or a timer does not
        self.assertEqual(self._data("Done when: destroy 6 raiders")["objective"],
                         "Destroy 6 raiders")
        self.assertIsNone(self._data("Done when: signal gate_11").get("objective"))
        self.assertIsNone(self._data("Done when: 30 seconds").get("objective"))

    def test_a_trigger_in_starts_when_is_a_REAL_start(self):
        """It is kept apart from the advancement trigger. Stored under the same key,
        a quest carrying both `Starts when:` and `Done when:` finished on whichever
        fired first - the gate could complete the job it was supposed to open."""
        self.assertEqual(self._data("Starts when: signal gate_1")["start_trigger"],
                         {"trigger": "on_signal", "data": {"name": "gate_1"}})
        d = self._data_lines(["Starts when: signal gate_1",
                              "Done when: destroy 3 raiders"])
        self.assertEqual(d["start_trigger"]["data"], {"name": "gate_1"})
        self.assertEqual(d["on_kill"], {"role": "raider", "count": 3})

    def test_the_old_shapes_still_parse_identically(self):
        """Nothing written against the old fields may change meaning."""
        pairs = [("Fail on signal: base_lost", "Fails when: signal base_lost",
                  "fail_on_signal"),
                 ("Fail on all dead: convoy", "Fails when: all dead convoy",
                  "fail_on_all_dead"),
                 ("Fail after: 5 minutes", "Fails when: 5 minutes", "fail_after"),
                 ("Complete after: 30 seconds", "Done when: 30 seconds",
                  "complete_after"),
                 ("State: secret", "Starts when: revealed", "state")]
        for old, new, key in pairs:
            self.assertEqual(self._data(old).get(key), self._data(new).get(key), old)


if __name__ == "__main__":
    unittest.main()
