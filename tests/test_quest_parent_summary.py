"""Parent-quest detail pane: description + step checklist, without leaking arc length.

Selecting a collapsible ARC used to answer "Select a quest from the list" - the pane
skipped anything rendering as a header, and a parent quest renders as one.

The contract that matters: a SECRET step is neither listed NOR counted. However many
remain, they collapse to one "more to follow" line, so a player sees real progress
without learning how long the arc is.

    python -m unittest tests.test_quest_parent_summary
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.quest import (
    quest_add, quest_set_key, QuestState, quest_log_parent_summary)
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.mast.mast_node import MastDataObject


class ParentSummaryTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.p = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))
        quest_add(self.p, "arc", "Ghost Freighter", "Recover the derelict.",
                  state=QuestState.ACTIVE, data={})

    def _row(self, key="arc"):
        return MastDataObject({"agent_id": self.p, "key": key})

    def _step(self, cid, title, state):
        quest_add(self.p, "arc/" + cid, title, "", state=state, data={})

    def test_group_header_returns_empty(self):
        """A bare Game/You/Ship header is not a quest and must render nothing."""
        self.assertEqual("", quest_log_parent_summary(MastDataObject({"agent_id": self.p})))

    def test_parent_description_is_shown(self):
        self.assertIn("Recover the derelict.", quest_log_parent_summary(self._row()))

    def test_steps_are_listed_with_state_marks(self):
        self._step("hail", "Hail the Derelict", QuestState.COMPLETE)
        self._step("scan", "Scan the Hull", QuestState.ACTIVE)
        out = quest_log_parent_summary(self._row())
        self.assertIn("[x] Hail the Derelict", out)
        self.assertIn("[>] Scan the Hull", out)

    def test_secret_steps_are_not_listed(self):
        self._step("hail", "Hail the Derelict", QuestState.COMPLETE)
        self._step("tow", "Tow It Home", QuestState.SECRET)
        out = quest_log_parent_summary(self._row())
        self.assertNotIn("Tow It Home", out, "a secret step must not be named")

    def test_secret_count_is_NOT_disclosed(self):
        """The point of the design: one line stands in for any number of hidden steps."""
        self._step("hail", "Hail the Derelict", QuestState.COMPLETE)
        for i, name in enumerate(("Scan", "Tow", "Deliver", "Report")):
            self._step("s%d" % i, name, QuestState.SECRET)
        out = quest_log_parent_summary(self._row())
        self.assertEqual(1, out.count("more to follow"),
                         "four hidden steps must collapse to ONE line")
        for n in ("4", "four", "Scan", "Tow", "Deliver", "Report"):
            self.assertNotIn(n, out, f"hidden arc length leaked via {n!r}")

    def test_no_more_line_once_everything_is_revealed(self):
        self._step("hail", "Hail the Derelict", QuestState.COMPLETE)
        self._step("scan", "Scan the Hull", QuestState.ACTIVE)
        self.assertNotIn("more to follow", quest_log_parent_summary(self._row()))

    def test_failed_step_is_marked(self):
        self._step("hail", "Hail the Derelict", QuestState.FAILED)
        self.assertIn("[!] Hail the Derelict", quest_log_parent_summary(self._row()))
