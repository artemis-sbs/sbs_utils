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
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.sides import side_ensure, to_side_id
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.reputation import reputation_get

#: REAL client ids, bit and all. A plain small int is not a console: `is_client_id`
#: tests the 0x8000... console bit, so a fixture using 77 exercises `quest_payee`'s
#: "not a console" branch while looking like it is testing the console one.
CID = 0x8000000000000001
OTHER = 0x8000000000000002


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


class AClientHeldRewardIsPaidTests(unittest.TestCase):
    """Advancing a client-held job was half the problem; PAYING one was the other half.

    Every consumer of a reward reads a SHIP - credits go to a side, reputation is read per
    player ship (`fleet.truced_ships`, OU's dialogue guards), items are cargo. A console
    has no side and is not `__player__`, so a client-held job used to pay nothing but
    items nobody could read. `quest_payee` routes the payment to the console's ship.
    """

    def setUp(self):
        reset_mock(sbs)
        GuiClient(CID)
        side_ensure("tsn")
        self.sid = to_side_id("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        # BOTH HALVES, because production sets both together (`player_roster_rebind`):
        # the "consoles" link is what `quest_credit_ids` reads going ship -> crew, and the
        # engine assignment is what `quest_payee` reads going crew -> ship. A fixture with
        # only the link is a console the engine says is flying nothing.
        sbs.assign_client_to_ship(CID, self.ship)
        link(self.ship, "consoles", CID)
        self.reward = {"credits": 500, "items": {"ore": 3},
                       "reputation": {"tsn": {"honest": 10}}}

    def _credits(self):
        return get_inventory_value(self.sid, "credits", 0)

    def test_a_client_held_reward_pays_credits_to_the_side(self):
        QD.quest_grant_reward(CID, self.reward)
        self.assertEqual(self._credits(), 500)

    def test_a_client_held_reward_lands_reputation_on_the_ship(self):
        """On the SHIP, because that is the only place anything reads it."""
        QD.quest_grant_reward(CID, self.reward)
        self.assertEqual(reputation_get(self.ship, "tsn", "honest"), 10)

    def test_a_client_held_reward_lands_items_on_the_ship(self):
        QD.quest_grant_reward(CID, self.reward)
        self.assertEqual(get_inventory_value(self.ship, "ore", 0), 3)

    def test_a_client_held_penalty_charges_the_ship(self):
        """Or taking a job as yourself would be a way to fail one for free."""
        QD.quest_grant_reward(CID, self.reward)
        QD.quest_grant_penalty(CID, {"credits": 200, "items": {"ore": 1}})
        self.assertEqual(self._credits(), 300)
        self.assertEqual(get_inventory_value(self.ship, "ore", 0), 2)

    def test_a_ship_held_reward_is_unchanged(self):
        QD.quest_grant_reward(self.ship, self.reward)
        self.assertEqual(self._credits(), 500)
        self.assertEqual(get_inventory_value(self.ship, "ore", 0), 3)
        self.assertEqual(reputation_get(self.ship, "tsn", "honest"), 10)

    def test_the_payee_of_a_ship_is_the_ship(self):
        self.assertEqual(QD.quest_payee(self.ship), self.ship)

    def test_the_payee_of_shared_is_shared(self):
        self.assertEqual(QD.quest_payee(Agent.SHARED_ID), Agent.SHARED_ID)


class AConsoleWithNoShipAtAllTests(unittest.TestCase):
    """The one case the engine cannot answer, and it must not answer 0.

    A console with no assignment does NOT normally end up shipless: the engine grabs a
    player ship for it, and the mock mirrors that (`_grab_player_ship`). The genuinely
    shipless case is a sim with no player ship in it - the map picker, or before the
    crew is seated. `quest_payee` has to hand back the console rather than agent 0,
    which is a real agent id and would be paid somebody else's reward.
    """

    def setUp(self):
        reset_mock(sbs)
        GuiClient(CID)
        side_ensure("tsn")

    def test_the_payee_is_the_console_itself(self):
        self.assertEqual(QD.quest_payee(CID), CID)

    def test_nothing_is_paid_to_agent_zero(self):
        self.assertNotEqual(QD.quest_payee(CID), 0)

    def test_items_still_land_somewhere_readable_later(self):
        """Paid to the console, which is where a client-held quest's tree lives - so it
        is at least recoverable, rather than written onto agent 0."""
        QD.quest_grant_reward(CID, {"items": {"ore": 2}})
        self.assertEqual(get_inventory_value(CID, "ore", 0), 2)


if __name__ == "__main__":
    unittest.main()
