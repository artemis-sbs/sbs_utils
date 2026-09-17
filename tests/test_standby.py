"""Standby (engine-network culling by player proximity) - extracted from the
Open Universe into sbs_utils.procedural.standby. Parks objects with no player
within radius, retrieves them when a player comes near."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import unittest
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.procedural.query import to_object, to_id, to_object_list
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.links import link, linked_to
from sbs_utils.agent import Agent, get_story_id
import sbs_utils.procedural.standby as standby


def _fleet_agent():
    """A script-only fleet agent, the way LM's Fleet builds one: a story id, not a
    space object. standby_cull_fleets only needs the role + the ship_list link."""
    fleet = Agent()
    fleet.id = get_story_id()
    fleet.add()
    fleet.add_role("raider_fleet")
    return fleet


def _npc(x, name):
    # spawn returns SpawnData; standby operates on real Agents (role sets)
    return to_object(to_id(npc_spawn(x, 0, 0, name, "raider",
                                     "tsn_light_cruiser", "behav_npcship")))


class TestStandbyCull(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        standby._parked_pos.clear()      # process-singleton state; reset per test
        standby._parked_fleets.clear()
        player_spawn(0, 0, 0, "P", "tsn", "tsn_light_cruiser")  # auto-tags __player__

    def test_parks_far_keeps_near(self):
        near = _npc(500, "near")
        far = _npc(100000, "far")
        standby.standby_cull_step([near, far], 1000)
        self.assertNotIn(near.id, standby._parked_pos)   # near a player -> stays
        self.assertIn(far.id, standby._parked_pos)        # far -> parked
        self.assertEqual(standby.standby_cull_count(), 1)

    def test_no_players_is_noop(self):
        for pl in to_object_list(role("__player__")):
            pl.remove_role("__player__")
        far = _npc(100000, "far")
        standby.standby_cull_step([far], 1000)
        self.assertEqual(standby.standby_cull_count(), 0)   # nothing parks w/o players

    def test_clear_retrieves_all(self):
        far = _npc(100000, "far")
        standby.standby_cull_step([far], 1000)
        self.assertEqual(standby.standby_cull_count(), 1)
        standby.standby_cull_clear()
        self.assertEqual(standby.standby_cull_count(), 0)


class TestStandbyNeverPushesADeadId(unittest.TestCase):
    """`sbs.push_to_standby_list_id` on an id the engine does not have is a NULL
    DEREF in `SuperContainer::PushToStandbyList` - it crashes the server rather
    than raising. The mock raises on it, so these tests fail loudly if the guard
    goes away. Storm's Beacon CTD, 2026-09-17."""

    def setUp(self):
        self.sim = reset_mock(sbs)
        standby._parked_pos.clear()
        standby._parked_fleets.clear()
        player_spawn(0, 0, 0, "P", "tsn", "tsn_light_cruiser")

    def test_the_mock_raises_so_the_guard_is_testable(self):
        with self.assertRaises(ValueError):
            sbs.push_to_standby_list_id(999999)

    def test_cull_step_skips_a_destroyed_candidate(self):
        far = _npc(100000, "far")
        far.delete_object()                  # gone from the engine, Agent still held
        standby.standby_cull_step([far], 1000)   # must not push the dead id
        self.assertNotIn(far.id, standby._parked_pos)

    def test_fleet_cull_prunes_a_destroyed_member(self):
        """The real crash path: a destroyed raider stays in ship_list as a dangling
        id, because links are uni-directional and deleting an object purges it only
        as a link OWNER - nothing walks the fleets that link TO it."""
        alive = _npc(100000, "alive")
        dead = _npc(100001, "dead")
        fleet = _fleet_agent()
        link(fleet.id, "ship_list", alive.id)
        link(fleet.id, "ship_list", dead.id)
        dead.delete_object()
        # The dangling id is still there - that is the premise, not an artifact.
        self.assertIn(dead.id, linked_to(fleet.id, "ship_list"))

        standby.standby_cull_fleets("raider_fleet", 1000)

        self.assertNotIn(dead.id, linked_to(fleet.id, "ship_list"))  # pruned
        self.assertIn(alive.id, standby._parked_fleets[fleet.id])    # fleet still parks
        self.assertNotIn(dead.id, standby._parked_fleets[fleet.id])

    def test_fleet_cull_with_only_dead_members_parks_nothing(self):
        dead = _npc(100000, "dead")
        fleet = _fleet_agent()
        link(fleet.id, "ship_list", dead.id)
        dead.delete_object()
        standby.standby_cull_fleets("raider_fleet", 1000)
        self.assertNotIn(fleet.id, standby._parked_fleets)


if __name__ == "__main__":
    unittest.main(verbosity=2)
