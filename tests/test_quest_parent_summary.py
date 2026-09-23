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

    def test_steps_are_listed_with_state_icons(self):
        """Each step's bullet is an icon: done / under way / failed / not yet."""
        self._step("hail", "Hail the Derelict", QuestState.COMPLETE)
        self._step("scan", "Scan the Hull", QuestState.ACTIVE)
        out = quest_log_parent_summary(self._row())
        self.assertRegex(out, r"- !\[\]\(icon://check\.on\?color=[^)]*\) Hail the Derelict")
        self.assertRegex(out, r"- !\[\]\(icon://list\.next\?color=[^)]*\) Scan the Hull")
        self.assertNotIn("[x]", out)

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
        self.assertRegex(quest_log_parent_summary(self._row()),
                         r"icon://ban\?color=[^)]*\) Hail the Derelict")

    def test_the_checklist_draws_as_icon_bullets(self):
        """Parsed the way the pane parses it: one IconLine per visible step."""
        from sbs_utils.helpers import FrameContext, Context, FakeEvent
        from sbs_utils.pages.layout.text_area import TextArea, IconLine
        from sbs_utils.pages.layout.layout import Bounds
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self._step("hail", "Hail the Derelict", QuestState.COMPLETE)
        self._step("scan", "Scan the Hull", QuestState.IDLE)
        ta = TextArea("t", quest_log_parent_summary(self._row()))
        ta.bounds = Bounds(0, 0, 40, 80)
        ta.calc_rich(0)
        steps = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertEqual([s.text for s in steps], ["Hail the Derelict", "Scan the Hull"])
        self.assertEqual(steps[1].urn.split("?")[0], "check.off")


class PaneTextTests(unittest.TestCase):
    """quest_log_pane_text: a single quest's facts first, then its story."""

    def setUp(self):
        from sbs_utils.helpers import FrameContext, Context, FakeEvent
        reset_mock(sbs)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _parse(self, text):
        from sbs_utils.pages.layout.text_area import TextArea
        from sbs_utils.pages.layout.layout import Bounds
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 40, 80)
        ta.calc_rich(0)
        return ta

    def _row(self, **kw):
        base = {"agent_id": 1, "key": "job1", "state": int(QuestState.ACTIVE),
                "state_label": "Active", "desc": "Salvage the wreck.", "kind": "job"}
        base.update(kw)
        return MastDataObject(base)

    def test_progress_is_a_gauge_and_facts_a_grid(self):
        from sbs_utils.procedural.quest import quest_log_pane_text
        from sbs_utils.pages.layout.text_area import GaugeLine, TableLine, TextLine
        text = quest_log_pane_text(self._row(need=5, progress=3, reward="120 credits",
                                             remaining="4:30"))
        ta = self._parse(text)
        gauge = [ln for ln in ta.lines if isinstance(ln, GaugeLine)][0]
        self.assertEqual((gauge.spec["value"], gauge.spec["max"], gauge.spec["show"]),
                         (3.0, 5.0, "frac"))
        grid = [ln for ln in ta.lines if isinstance(ln, TableLine)][0]
        self.assertFalse(grid.has_header)
        self.assertEqual([r[0] for r in grid.rows], ["State", "Reward", "Time left"])
        self.assertIn((0, 1), grid.icons)                     # the state pip
        self.assertTrue(any(isinstance(ln, TextLine) and "Salvage" in ln.text for ln in ta.lines))

    def test_only_what_the_quest_has(self):
        from sbs_utils.procedural.quest import quest_log_pane_text
        text = quest_log_pane_text(self._row())
        self.assertNotIn("gauge://", text)
        self.assertNotIn("Reward", text)
        self.assertNotIn("Time left", text)

    def test_a_pipe_in_authored_text_cannot_split_the_grid(self):
        from sbs_utils.procedural.quest import quest_log_pane_text
        from sbs_utils.pages.layout.text_area import TableLine
        ta = self._parse(quest_log_pane_text(self._row(reward="10 | 20 credits")))
        grid = [ln for ln in ta.lines if isinstance(ln, TableLine)][0]
        self.assertEqual(grid.ncols, 2)

    def test_not_a_quest(self):
        from sbs_utils.procedural.quest import quest_log_pane_text
        self.assertEqual(quest_log_pane_text(None), "")
        self.assertEqual(quest_log_pane_text(MastDataObject({"agent_id": 1})), "")
