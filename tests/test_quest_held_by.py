"""A quest can be held by the world, not only by a crew (URGE_PLAN.md phase 2).

`quest_add` always took agents rather than players, so granting a quest to a station was
legal at the data layer - but every deadline/proximity watcher iterated
`[SHARED_ID] + players`, so a station-held quest showed its objective and its clock never
ran. Nothing logged, because nothing looked.

The holder set is now `has_inventory("__quests__")` - the registry the quest trees already
live in - and `Held by:` names the owner in AMD.

Run:
    python -m unittest tests.test_quest_held_by
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.quest import quest_add, quest_get_state, QuestState
from sbs_utils.procedural.timers import is_timer_set, TICK_PER_SECONDS
from sbs_utils.procedural.amd_quest import amd_quest_data

from sbs_utils.procedural import quest_driver as QD

SH = Agent.SHARED_ID


def make_agent(*roles):
    a = Agent()
    a.id = get_story_id()
    a.add()
    for r in roles:
        a.add_role(r)
    return a


class QuestHolderSetTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self._real_emit = QD.signal_emit
        QD.signal_emit = lambda name, data=None: None

    def tearDown(self):
        QD.signal_emit = self._real_emit

    def _advance(self, seconds):
        sbs.sim._time_tick_counter += int(seconds * TICK_PER_SECONDS)

    def test_holder_set_finds_a_station(self):
        station = make_agent("station")
        quest_add(station.id, "resupply", "Resupply DS1", "", state=QuestState.ACTIVE)
        self.assertIn(station.id, QD._quest_holders())

    def test_holder_set_excludes_an_agent_with_no_quests(self):
        bystander = make_agent("station")
        self.assertNotIn(bystander.id, QD._quest_holders())

    def test_holder_set_is_a_list_not_the_live_registry(self):
        # Completing a quest inside the walk can grant a follow-on to an agent that had
        # none, which would mutate the live set mid-iteration.
        station = make_agent("station")
        quest_add(station.id, "resupply", "Resupply DS1", "", state=QuestState.ACTIVE)
        self.assertIsInstance(QD._quest_holders(), list)

    def test_station_held_deadline_actually_fires(self):
        """The bug this phase exists for: before, this clock never started."""
        station = make_agent("station")
        quest_add(station.id, "resupply", "Resupply DS1", "",
                  state=QuestState.ACTIVE, data={"fail_after": {"minutes": 30}})
        QD.quest_tick_fail_after()
        self.assertTrue(is_timer_set(station.id, "qfail:resupply"),
                        "a station-held quest must anchor its clock")
        self._advance(60 * 31)
        QD.quest_tick_fail_after()
        self.assertEqual(int(quest_get_state(station.id, "resupply")),
                         int(QuestState.FAILED))

    def test_player_held_deadline_still_fires(self):
        # The old holder set is a subset of the new one, so nothing regresses.
        quest_add(SH, "mercy", "Mercy Run", "", state=QuestState.ACTIVE,
                  data={"fail_after": {"minutes": 6}})
        QD.quest_tick_fail_after()
        self._advance(60 * 7)
        QD.quest_tick_fail_after()
        self.assertEqual(int(quest_get_state(SH, "mercy")), int(QuestState.FAILED))

    def test_station_held_complete_after_fires(self):
        station = make_agent("station")
        quest_add(station.id, "build", "Build the relay", "",
                  state=QuestState.ACTIVE, data={"complete_after": {"minutes": 2}})
        QD.quest_tick_complete_after()
        self._advance(180)
        QD.quest_tick_complete_after()
        self.assertEqual(int(quest_get_state(station.id, "build")),
                         int(QuestState.COMPLETE))


class HeldByParseTests(unittest.TestCase):
    def test_held_by_parses(self):
        d = amd_quest_data("Objective: Resupply DS1\nHeld by: ds1")
        self.assertEqual(d["held_by"], "ds1")

    def test_underscore_spelling_parses(self):
        d = amd_quest_data("Objective: Resupply DS1\nHeld_by: ds1")
        self.assertEqual(d["held_by"], "ds1")


class HeldByGrantTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self._real_emit = QD.signal_emit
        QD.signal_emit = lambda name, data=None: None

    def tearDown(self):
        QD.signal_emit = self._real_emit

    def _doc(self, children):
        return {"children": children}

    def _node(self, key, data, children=None):
        n = {"key": key, "display_text": key, "description": "", "data": data}
        if children:
            n["children"] = children
        return n

    def test_grants_to_the_named_actor_not_the_passed_agent(self):
        station = make_agent("ds1")
        ship = make_agent("__player__")
        QD.quest_grant_amd(ship.id, self._doc([
            self._node("resupply", {"held_by": "ds1", "state": "running"})]))
        self.assertEqual(int(quest_get_state(station.id, "resupply")),
                         int(QuestState.ACTIVE))
        self.assertEqual(int(quest_get_state(ship.id, "resupply")), int(QuestState.IDLE))

    def test_shared_is_a_name(self):
        ship = make_agent("__player__")
        QD.quest_grant_amd(ship.id, self._doc([
            self._node("arc", {"held_by": "shared", "state": "running"})]))
        self.assertEqual(int(quest_get_state(SH, "arc")), int(QuestState.ACTIVE))

    def test_unresolvable_holder_grants_to_nobody(self):
        """Never fall back to the passed-in agent: a world deadline in a crew's log
        would pay its penalty out of the crew's pocket."""
        ship = make_agent("__player__")
        QD.quest_grant_amd(ship.id, self._doc([
            self._node("resupply", {"held_by": "no_such_station", "state": "running"})]))
        self.assertEqual(int(quest_get_state(ship.id, "resupply")), int(QuestState.IDLE))
        self.assertEqual(int(quest_get_state(SH, "resupply")), int(QuestState.IDLE))

    def test_several_agents_answering_the_name_all_hold_it(self):
        a = make_agent("listening_post")
        b = make_agent("listening_post")
        ship = make_agent("__player__")
        QD.quest_grant_amd(ship.id, self._doc([
            self._node("resupply", {"held_by": "listening_post", "state": "running"})]))
        for agent in (a, b):
            self.assertEqual(int(quest_get_state(agent.id, "resupply")),
                             int(QuestState.ACTIVE))

    def test_steps_of_a_held_job_belong_to_the_same_holder(self):
        station = make_agent("ds1")
        ship = make_agent("__player__")
        QD.quest_grant_amd(ship.id, self._doc([
            self._node("resupply", {"held_by": "ds1", "state": "running"},
                       children=[self._node("step1", {"state": "running"})])]))
        self.assertEqual(int(quest_get_state(station.id, "resupply/step1")),
                         int(QuestState.ACTIVE))
        self.assertEqual(int(quest_get_state(ship.id, "resupply/step1")),
                         int(QuestState.IDLE))

    def test_plain_nesting_is_byte_for_byte_unchanged(self):
        """Backward compatibility for the no-`Held by:` path.

        Pinning OBSERVED behavior, which is not what you would guess: a `Scope: shared`
        parent goes to SHARED, and its plain child then lands NOWHERE. Recursion passes
        the ship, the child re-resolves to the ship, and `quest_folder(ship,
        "arc/step1")` cannot find the parent there - so it is dropped, silently.

        That is a PRE-EXISTING quirk (verified against the previous commit), not
        something this phase introduced, and it is pinned here so the next change to
        `quest_grant_amd` finds out immediately if it moves. Whether the drop should
        warn is a separate question - see URGE_PLAN.md s10.2.
        """
        ship = make_agent("__player__")
        QD.quest_grant_amd(ship.id, self._doc([
            self._node("arc", {"scope": "shared", "state": "running"},
                       children=[self._node("step1", {"state": "running"})])]))
        self.assertEqual(int(quest_get_state(SH, "arc")), int(QuestState.ACTIVE))
        self.assertEqual(int(quest_get_state(ship.id, "arc/step1")),
                         int(QuestState.IDLE), "child on the ship (pre-existing: dropped)")
        self.assertEqual(int(quest_get_state(SH, "arc/step1")),
                         int(QuestState.IDLE), "child on SHARED (pre-existing: dropped)")

    def test_a_shared_parent_with_shared_children_does_work(self):
        """The authoring that DOES work today, pinned next to the one that does not:
        put the scope on every level and the whole arc lands on SHARED."""
        ship = make_agent("__player__")
        QD.quest_grant_amd(ship.id, self._doc([
            self._node("arc", {"scope": "shared", "state": "running"},
                       children=[self._node("step1", {"scope": "shared",
                                                      "state": "running"})])]))
        self.assertEqual(int(quest_get_state(SH, "arc/step1")), int(QuestState.ACTIVE))


if __name__ == "__main__":
    unittest.main()
