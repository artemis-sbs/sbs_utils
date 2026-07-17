"""Branching dialogue driver (sbs_utils.procedural.amd_dialogue), promoted from OU.

Covers pure parsing (lines/%/gates/choices/outcomes), scene lookup, and the injected seams
(metric resolver for guards, outcome handlers). Run: python -m unittest tests.test_amd_dialogue
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural import amd_dialogue as D


class _Rec(dict):
    pass


class DialogueParseTests(unittest.TestCase):
    def _scene(self, body, speaker="ashfang", when="comms"):
        return {"data": {"speaker": speaker, "when": when}, "description": body}

    def test_lines_and_choices(self):
        s = D.dialogue_parse(self._scene(
            "% You're a long way from friends.\n"
            "% Brave or stupid, flying in here.\n"
            "- [Apologize](backoff)\n"
            "- [Threaten](standoff) if fearsome > 20\n"
            "- [Offer a cut](deal) if credits >= 200 ; costs 200 credits, earns ashfang selfish +5\n"))
        self.assertEqual(s["speaker"], "ashfang")
        self.assertEqual([t for t, g in s["lines"]],
                         ["You're a long way from friends.", "Brave or stupid, flying in here."])
        self.assertEqual(len(s["choices"]), 3)
        deal = s["choices"][2]
        self.assertEqual(deal["target"], "deal")
        self.assertEqual(deal["guard"], "credits >= 200")
        self.assertEqual(deal["outcomes"],
                         [("costs", "200", "credits"), ("earns", "ashfang", "selfish", "+5")])

    def test_gated_line(self):
        s = D.dialogue_parse(self._scene("{fearsome > 20} Only the bold survive.\n"))
        self.assertEqual(s["lines"], [("Only the bold survive.", "fearsome > 20")])


class DialogueSceneLookupTests(unittest.TestCase):
    def test_scenes_and_entry(self):
        # root -> section(talk) -> scenes; sections are children of the root heading
        doc = amd_document(
            "# [Root](root)\n"
            "## [Talk](talk)\n"
            "### [Hail](ashfang_hail)\n---\nSpeaker: ashfang\nWhen: comms\n---\n% Hi.\n"
            "### [Bye](ashfang_bye)\n---\nSpeaker: ashfang\n---\n% Later.\n",
            data_parser=amd_parse_facts)
        scenes = D.dialogue_scenes(amd_section(doc, "talk"))
        self.assertIn("ashfang_hail", scenes)
        self.assertEqual(D.dialogue_entry_for(scenes, "ashfang", "comms"), "ashfang_hail")
        self.assertIsNone(D.dialogue_entry_for(scenes, "verdant", "comms"))


class DialogueSeamTests(unittest.TestCase):
    def setUp(self):
        self.metrics = {"fearsome": 30, "credits": 100}
        D.dialogue_set_metric_resolver(lambda name, agent, spk: self.metrics.get(name, 0))
        self.applied = []
        D._OUTCOME_HANDLERS.clear()
        D.dialogue_register_outcome("costs", lambda a, s, toks: self.applied.append(("costs", toks)))

    def test_guard_uses_metric_resolver(self):
        self.assertTrue(D.dialogue_guard_ok("fearsome > 20", 1, None))
        self.assertFalse(D.dialogue_guard_ok("credits >= 200", 1, None))
        self.assertTrue(D.dialogue_guard_ok("", 1, None))          # no guard -> True

    def test_choices_filtered_by_guard(self):
        scene = D.dialogue_parse({"data": {}, "description":
            "- [Bold](a) if fearsome > 20\n- [Rich](b) if credits >= 200\n"})
        labels = [c.label for c in D.dialogue_choices(scene, 1, None)]
        self.assertEqual(labels, ["Bold"])   # only the affordable/eligible one

    def test_pick_line_respects_gate(self):
        scene = D.dialogue_parse({"data": {}, "description":
            "{fearsome > 20} shown\n{credits >= 200} hidden\n"})
        self.assertEqual(D.dialogue_pick_line(scene, 1, None), "shown")

    def test_apply_signal_builtin_and_registered(self):
        # signal is built in (no handler needed); costs is registered
        ok = D.dialogue_apply(1, None, [("costs", "50", "credits"), ("signal", "done")])
        self.assertTrue(ok)
        self.assertEqual(self.applied, [("costs", ("50", "credits"))])

    def test_apply_refused_when_handler_returns_false(self):
        D.dialogue_register_outcome("costs", lambda a, s, toks: False)
        self.assertFalse(D.dialogue_apply(1, None, [("costs", "999")]))


if __name__ == "__main__":
    unittest.main()
