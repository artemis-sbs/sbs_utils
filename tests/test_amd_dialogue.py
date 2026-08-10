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
        # Snapshot rather than clear: the library registers its OWN outcome verbs now
        # (quest_driver's accepts/completes/fails), and wiping the registry left them
        # gone for every test that ran afterwards - which passes alone and fails under
        # discover, the worst shape of test failure.
        self._prev_outcomes = dict(D._OUTCOME_HANDLERS)
        D._OUTCOME_HANDLERS.clear()
        D.dialogue_register_outcome("costs", lambda a, s, toks: self.applied.append(("costs", toks)))

    def tearDown(self):
        D._OUTCOME_HANDLERS.clear()
        D._OUTCOME_HANDLERS.update(self._prev_outcomes)

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

    def test_a_choice_with_an_EMPTY_target_is_a_choice(self):
        # `- [Accept Message]()` - an acknowledgement that ends the conversation.
        # `hail_answer` closes the hail on a falsy target, so this is the ordinary
        # shape of a last beat; the regex used to require a target and dropped the
        # line without a word, which read as "my choice did not show up".
        scene = D.dialogue_parse({"data": {}, "description":
            """It is done.
- [Accept Message]()
"""})
        self.assertEqual([c["label"] for c in scene["choices"]], ["Accept Message"])
        self.assertEqual(scene["choices"][0]["target"], "")

    def test_an_empty_target_still_carries_a_guard_and_outcomes(self):
        scene = D.dialogue_parse({"data": {}, "description":
            """- [Pay up]() if credits >= 200; costs 200 credits
"""})
        ch = scene["choices"][0]
        self.assertEqual(ch["target"], "")
        self.assertEqual(ch["guard"], "credits >= 200")
        self.assertEqual(ch["outcomes"], [("costs", "200", "credits")])


class SceneRegistryTests(unittest.TestCase):
    """The registry that lets something with only a KEY find a scene.

    A declarative `Action: DS1 hails ds1_brief` has a key and nothing else, and so does
    `hail_offer(scene=...)` called without `scenes=`. Every mission already holds its
    scenes in a MAST variable; this is the same dict, registered.
    """

    def setUp(self):
        D.dialogue_scenes_registry_clear()

    def tearDown(self):
        D.dialogue_scenes_registry_clear()

    @staticmethod
    def _node(key, **data):
        return {"key": key, "children": [], "data": dict(data), "description": ""}

    def _section(self, *keys):
        return {"key": "voices", "children": [self._node(k) for k in keys]}

    def test_a_section_registers_its_scenes_and_is_returned(self):
        scenes = D.dialogue_register_scenes(self._section("a", "b"))
        self.assertEqual(sorted(scenes), ["a", "b"])       # the caller keeps its dict
        self.assertIsNotNone(D.dialogue_scene("a"))

    def test_a_whole_DOCUMENT_registers_the_leaves(self):
        # `enemy_taunt.mast` hands dialogue_scenes() a whole document today, and a
        # sectioned document nests one level deeper. Descending to the leaves is what
        # tells the two apart without being told which was passed.
        doc = {"key": "__root__", "children": [
            {"key": "root", "children": [self._section("a", "b")]}]}
        scenes = D.dialogue_register_scenes(doc)
        self.assertEqual(sorted(scenes), ["a", "b"])

    def test_an_already_built_dict_registers(self):
        scenes = D.dialogue_register_scenes({"a": self._node("a")})
        self.assertEqual(sorted(scenes), ["a"])
        self.assertIsNotNone(D.dialogue_scene("a"))

    def test_last_registration_wins_quietly(self):
        # A document cache miss re-parses and re-registers DIFFERENT node objects for
        # the same keys, so a collision is normal rather than an error.
        first = self._node("a", title="one")
        D.dialogue_register_scenes({"a": first})
        D.dialogue_register_scenes({"a": self._node("a", title="two")})
        self.assertEqual(D.dialogue_scene("a")["data"]["title"], "two")

    def test_clear_empties_it(self):
        D.dialogue_register_scenes({"a": self._node("a")})
        D.dialogue_scenes_registry_clear()
        self.assertIsNone(D.dialogue_scene("a"))
        self.assertEqual(D.dialogue_registered_scenes(), {})

    def test_none_and_unknown_are_not_errors(self):
        self.assertEqual(D.dialogue_register_scenes(None), {})
        self.assertIsNone(D.dialogue_scene("nope"))
        self.assertIsNone(D.dialogue_scene(None))


class EntryLookupTests(unittest.TestCase):
    """`dialogue_entry_for` - which scene is this speaker's door."""

    @staticmethod
    def _scenes():
        return {
            "greet": {"key": "greet", "data": {"speaker": "DS 1", "when": "comms"}},
            "call":  {"key": "call",  "data": {"speaker": "ds_1", "when": "hail"}},
        }

    def test_the_speaker_is_NORMALIZED_on_both_sides(self):
        # This was the one comparison in the module that skipped _dlg_norm, so
        # `Speaker: DS 1` did not match an actor written `DS-1` or `ds_1` - and a
        # scene that is there reads as missing.
        self.assertEqual(D.dialogue_entry_for(self._scenes(), "ds_1"), "greet")
        self.assertEqual(D.dialogue_entry_for(self._scenes(), "DS-1"), "greet")

    def test_when_selects_the_door(self):
        scenes = self._scenes()
        self.assertEqual(D.dialogue_entry_for(scenes, "DS 1", D.DIALOGUE_WHEN_HAIL), "call")
        self.assertEqual(D.dialogue_entry_for(scenes, "DS 1", D.DIALOGUE_WHEN_COMMS), "greet")

    def test_when_None_means_either_door(self):
        self.assertIn(D.dialogue_entry_for(self._scenes(), "DS 1", None), ("greet", "call"))

    def test_no_match_is_None(self):
        self.assertIsNone(D.dialogue_entry_for(self._scenes(), "nobody"))


if __name__ == "__main__":
    unittest.main()
