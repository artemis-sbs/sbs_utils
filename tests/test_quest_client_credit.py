"""A job the PERSON holds counts what the person does, in whatever ship they are in.

The quest log has always had a "You" section - quests held by the CLIENT rather than by a
ship - and four of the seven triggers could never advance one. Every event is credited to
the SHIP (`quest_on_kill` is handed `DAMAGE_SOURCE_ID`, `quest_on_scan` the scanning ship,
`quest_on_dock` the docking one, `quest_on_collect` the holder), so a client-held quest
counting kills, scans, docks or pickups sat at 0 of N forever. Nothing logged, because
nothing looked.

`on_signal`, `on_reach` and `on_arrive` were always fine - they walk `_quest_holders()`,
which is every agent with a tree. This pins the other four, and the property that makes
them worth having: **the job follows the person across a change of ship.**

    python -m unittest tests.test_quest_client_credit
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.agent import Agent
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.links import link, unlink
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.quest import quest_add, quest_get_state, QuestState
from sbs_utils.procedural import quest_driver as QD

CID = 77
OTHER = 78


class CreditIdsTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        GuiClient(CID)
        self.ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="A"))

    def test_an_uncrewed_ship_credits_only_itself(self):
        """A ship-held or SHARED-held quest must behave exactly as it did."""
        self.assertEqual(QD.quest_credit_ids(self.ship), (self.ship,))

    def test_a_crewed_ship_credits_its_consoles_too(self):
        link(self.ship, "consoles", CID)
        got = QD.quest_credit_ids(self.ship)
        self.assertIn(self.ship, got)
        self.assertIn(CID, got)

    def test_none_credits_nothing(self):
        self.assertEqual(QD.quest_credit_ids(None), ())

    def test_shared_is_not_in_here(self):
        """Each caller adds SHARED itself; putting it here would double-count it."""
        link(self.ship, "consoles", CID)
        self.assertNotIn(Agent.SHARED_ID, QD.quest_credit_ids(self.ship))


class _KillBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        GuiClient(CID)
        GuiClient(OTHER)
        self.a = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="A"))
        self.b = to_id(create_enemy(100, 0, 0, "kralien_cruiser", name="B"))

    def _victim(self, x=500):
        return to_id(create_enemy(x, 0, 0, "kralien_cruiser", name="V%d" % x))

    def _job(self, holder, key="hunt", count=2, **trig):
        spec = {"count": count}
        spec.update(trig)
        quest_add(holder, key, key, "", data={"on_kill": spec})
        QD.quest_mark_active(holder, key)

    def _state(self, holder, key="hunt"):
        return int(quest_get_state(holder, key) or 0)


class AJobFollowsThePilotTests(_KillBase):
    def test_a_client_held_job_counts_kills_made_by_its_ship(self):
        """THE HOLE. Before this the count never moved at all."""
        self._job(CID, count=1)
        link(self.a, "consoles", CID)
        QD.quest_on_kill(self.a, self._victim())
        self.assertEqual(self._state(CID), int(QuestState.COMPLETE))

    def test_it_completes_ACROSS_a_change_of_ship(self):
        """The reason a job belongs to the person: one kill from each hull finishes a
        job for two, because the link is read at the moment of the event."""
        self._job(CID, count=2)
        link(self.a, "consoles", CID)
        QD.quest_on_kill(self.a, self._victim(500))
        self.assertEqual(self._state(CID), int(QuestState.ACTIVE))

        unlink(self.a, "consoles", CID)
        link(self.b, "consoles", CID)
        QD.quest_on_kill(self.b, self._victim(600))
        self.assertEqual(self._state(CID), int(QuestState.COMPLETE))

    def test_a_kill_from_a_ship_you_are_NOT_in_does_not_count(self):
        self._job(CID, count=1)
        link(self.a, "consoles", CID)
        QD.quest_on_kill(self.b, self._victim())
        self.assertEqual(self._state(CID), int(QuestState.ACTIVE))

    def test_one_crew_members_job_is_not_another_s(self):
        """Separate trees. Two people on one bridge each hold their own copy."""
        self._job(CID, count=1)
        link(self.a, "consoles", CID)
        link(self.a, "consoles", OTHER)
        QD.quest_on_kill(self.a, self._victim())
        self.assertEqual(self._state(CID), int(QuestState.COMPLETE))
        self.assertEqual(self._state(OTHER), 0)     # OTHER was never given the job

    def test_a_whole_crew_each_get_credit_for_what_the_ship_did(self):
        """Not double counting - it is what "your job" means when six share a hull."""
        self._job(CID, count=1)
        self._job(OTHER, count=1)
        link(self.a, "consoles", CID)
        link(self.a, "consoles", OTHER)
        QD.quest_on_kill(self.a, self._victim())
        self.assertEqual(self._state(CID), int(QuestState.COMPLETE))
        self.assertEqual(self._state(OTHER), int(QuestState.COMPLETE))


class NothingElseChangedTests(_KillBase):
    def test_a_ship_held_job_still_counts(self):
        self._job(self.a, count=1)
        link(self.a, "consoles", CID)
        QD.quest_on_kill(self.a, self._victim())
        self.assertEqual(self._state(self.a), int(QuestState.COMPLETE))

    def test_an_uncrewed_ship_still_counts(self):
        self._job(self.a, count=1)
        QD.quest_on_kill(self.a, self._victim())
        self.assertEqual(self._state(self.a), int(QuestState.COMPLETE))

    def test_a_crewed_ship_counts_its_own_job_ONCE(self):
        """The ship is first in the credit list; its own tree must not be walked twice."""
        self._job(self.a, count=2)
        link(self.a, "consoles", CID)
        QD.quest_on_kill(self.a, self._victim())
        self.assertEqual(self._state(self.a), int(QuestState.ACTIVE),
                         "one kill counted as two")

    def test_the_role_filter_still_applies_to_a_client_job(self):
        self._job(CID, count=1, role="raider")
        link(self.a, "consoles", CID)
        QD.quest_on_kill(self.a, self._victim())
        self.assertEqual(self._state(CID), int(QuestState.ACTIVE),
                         "a non-raider counted toward a raiders-only job")


class OtherTriggersTests(_KillBase):
    """The same hole, in the three other ship-credited events."""

    def test_a_client_job_counts_a_scan(self):
        quest_add(CID, "look", "look", "", data={"on_scan": {"count": 1}})
        QD.quest_mark_active(CID, "look")
        link(self.a, "consoles", CID)
        QD.quest_on_scan(self.a, self._victim())
        self.assertEqual(self._state(CID, "look"), int(QuestState.COMPLETE))

    def test_a_client_job_counts_a_dock(self):
        quest_add(CID, "berth", "berth", "", data={"on_dock": {"count": 1}})
        QD.quest_mark_active(CID, "berth")
        link(self.a, "consoles", CID)
        QD.quest_on_dock(self.a, self._victim())
        self.assertEqual(self._state(CID, "berth"), int(QuestState.COMPLETE))

    def test_a_client_job_counts_a_pickup(self):
        quest_add(CID, "haul", "haul", "", data={"on_collect": {"key": "ore",
                                                                "count": 1}})
        QD.quest_mark_active(CID, "haul")
        link(self.a, "consoles", CID)
        QD.quest_on_collect(self.a, "ore")
        self.assertEqual(self._state(CID, "haul"), int(QuestState.COMPLETE))


if __name__ == "__main__":
    unittest.main()
