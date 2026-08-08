"""A timed quest shows its countdown in the log (PRM-11).

Reported as "I couldn't find where the timer is displayed - I checked the mainscreen,
science, and comms". The chain exists end to end: the driver anchors a `qfail:<qid>` timer
lazily on the first ACTIVE tick, `_quest_remaining` formats it M:SS, and quest_log_detail
renders "<M:SS> left". This pins it, so a report of "the timer is nowhere" can be answered
with a measurement instead of a re-read.

Note what the detail line does NOT do: it returns the FIRST match, and a COUNTED goal
("3 of 6") wins over the countdown. That is deliberate - progress is the more useful fact
while both are true - but it means a counted AND timed quest never shows its clock in the
row, which is worth knowing before authoring one.

    python -m unittest tests.test_quest_timer_display
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.quest import (
    quest_add, quest_get, quest_log_build_items, quest_log_detail, QuestState)
from sbs_utils.procedural.quest_driver import quest_tick_fail_after


def _row_for(agent_id, key):
    for row in quest_log_build_items([("Mission", agent_id)]):
        # Section headers are LayoutListBoxHeader, not rows - they have no .get.
        if hasattr(row, "get") and row.get("key") == key:
            return row
    return None


class QuestTimerDisplayTests(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.agent = Agent()
        self.agent.id = get_story_id()
        self.agent.add()

    def _timed_quest(self, key="mercy", minutes=6, **extra):
        """Authored the way AMD authors it.

        `Fails when: 6 minutes` lands in the quest's **data** dict (amd_quest.py), and the
        driver reads it from exactly there - `q.get("data")`. Setting `fail_after` on the
        quest itself instead looks right, is what quest_set_key writes, is what
        quest_get_key reads back... and the deadline watcher never sees it. Worth knowing
        before hand-building a timed quest in Python.
        """
        data = {"fail_after": {"minutes": minutes}}
        data.update(extra)
        quest_add(self.agent.id, key, "Mercy Run", "Reach it before the clock runs out.",
                  state=QuestState.ACTIVE, data=data)
        return quest_get(self.agent.id, key)

    def test_the_countdown_reaches_the_log_row(self):
        self._timed_quest()
        quest_tick_fail_after()            # anchors qfail:<qid> on first ACTIVE sight
        row = _row_for(self.agent.id, "mercy")
        self.assertIsNotNone(row, "the quest is not in the log at all")
        self.assertTrue(row.get("remaining"), "no remaining time on the row")
        self.assertIn("left", quest_log_detail(row))

    def test_nothing_shows_before_the_deadline_is_anchored(self):
        """The anchor is lazy, so a quest that has never been ticked has no clock yet -
        which is the state a log built in the same frame as the accept would see."""
        self._timed_quest(key="unticked")
        row = _row_for(self.agent.id, "unticked")
        self.assertFalse(row.get("remaining"))

    def test_a_counted_goal_HIDES_the_countdown(self):
        """Documented, not endorsed: progress wins the single detail line, so a quest that
        both counts and is timed shows no clock. Authoring a counted+timed job and
        expecting a visible countdown is the shape that surprises."""
        self._timed_quest(key="counted", goal={"count": 6})
        quest_tick_fail_after()
        row = _row_for(self.agent.id, "counted")
        self.assertTrue(row.get("remaining"), "the time IS known...")
        self.assertNotIn("left", quest_log_detail(row))   # ...but the row will not say so


if __name__ == "__main__":
    unittest.main()
