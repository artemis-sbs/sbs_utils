"""The Quest Log shows an `Objective:` the writer typed, and never one made up for them.

`Objective:` was read by the hangar's board, Open Universe's side-quest board and printed
documents - and by nothing in the Quest Log, though the docs said the quest log shows it.
A quest with NO `Objective:` gets one made from `Done when:` (`Reach derelict 500`); that
is right for a board with nothing else to say and wrong above a description somebody wrote.
(The course owner's decision, 2026-10-05: show the typed one only.)
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
import unittest

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.quest import quest_log_pane_text, quest_objective_typed


def _quest(fence):
    doc = amd_document("# [T](t)\n## [Quests](quests)\n### [Q](q)\n---\n" + fence
                       + "---\nFly out and locate the hulk.\n", data_parser=amd_quest_data)

    def walk(node):
        if node.get("key") == "q":
            return node
        kids = node.get("children") or {}
        for child in (kids.values() if isinstance(kids, dict) else kids):
            found = walk(child)
            if found:
                return found
    return walk(doc)


class WhichObjectiveWasTyped(unittest.TestCase):
    def test_none_typed_gives_nothing_though_one_is_made_for_the_boards(self):
        q = _quest("Done when: reach derelict 500\n")
        self.assertEqual(q["data"]["objective"], "Reach derelict 500")   # the boards' line
        self.assertEqual(quest_objective_typed(q), "")

    def test_typed_above_done_when(self):
        q = _quest("Objective: Find out who sent it.\nDone when: reach derelict 500\n")
        self.assertEqual(quest_objective_typed(q), "Find out who sent it.")

    def test_typed_below_done_when(self):
        q = _quest("Done when: reach derelict 500\nObjective: Find out who sent it.\n")
        self.assertEqual(quest_objective_typed(q), "Find out who sent it.")

    def test_typed_on_a_quest_that_waits_for_a_signal(self):
        q = _quest("Objective: Wait for the word.\nDone when: signal x\n")
        self.assertEqual(quest_objective_typed(q), "Wait for the word.")


class ThePane(unittest.TestCase):
    def row(self, **more):
        base = {"agent_id": 1, "key": "q", "title": "Q", "state": 1, "state_label": "Active",
                "progress": 0, "desc": "Fly out and locate the hulk.", "kind": "quest",
                "need": 0, "reward": "", "remaining": "", "indent": 0}
        base.update(more)
        return MastDataObject(base)

    def test_a_typed_objective_is_above_the_description(self):
        text = quest_log_pane_text(self.row(objective="Find out who sent it."))
        lines = text.split(chr(10))
        self.assertIn("Find out who sent it.", lines)
        self.assertLess(lines.index("Find out who sent it."),
                        lines.index("Fly out and locate the hulk."))

    def test_with_none_the_pane_is_as_it_was(self):
        self.assertEqual(quest_log_pane_text(self.row(objective="")),
                         quest_log_pane_text(self.row()))
        self.assertNotIn("Reach", quest_log_pane_text(self.row()))

    def test_the_same_sentence_is_not_shown_twice(self):
        text = quest_log_pane_text(self.row(objective="Fly out and locate the hulk."))
        self.assertEqual(text.count("Fly out and locate the hulk."), 1)


if __name__ == "__main__":
    unittest.main()
