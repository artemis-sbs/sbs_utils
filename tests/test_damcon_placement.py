"""Damcons on an interior with no empty ("hallway") cell - LegendaryMissions issue #381.

#381: a ship whose engineering grid leaves no empty cell gets NO damcons at all, which makes
that floor plan unplayable and taxes a small hull three cells it cannot spare.

WHAT THIS FILE COVERS. The two library defects that produced that symptom, each as a
narrow unit:

  1. `grid_restore_damcons` asked `get_grid_object_by_name("DC1")` to decide whether a team
     already exists. That name lookup goes to the ENGINE, and `grid_delete_object` only
     TOMBSTONES the agent - the native free is queued to the end of the event handler. So
     during a rebuild (which deletes every grid object and then calls restore) the old teams
     were still findable, restore "healed" them instead of creating new ones, and the ship
     was left with none once the queue drained.
  2. The engine's cell finders take no "avoid these" argument and have no memory across a
     loop. With no empty cell anywhere, the occupancy-tolerant fallback returns the SAME
     cell three times, so all three teams and their rally markers stack and read as one team.

WHAT IT CANNOT COVER. Team creation itself goes through the LM MAST prefab
`prefab_lifeform_damcons`, which a bare unit test has no story to resolve, so the tests here
stop at "restore tried to create". End-to-end placement is
`LM_TestRange/maps/test_damcon_nohallway.mast`. And the question that decides playability -
can a team PATH from a room cell to a damaged room when there is no corridor - is not askable
in either: the mock has no grid pathfinder, and both cell finders are engine functions.
That map must be run in Cosmos.

The hull is `tsn_warpster` (7x7, 34 open cells, roles "ship,patrol,support,light"). The only
SHIPPED hull with a fully packed interior is `tsn_fighter`, which cannot be used: its shipData
roles are "cockpit,fighter" and `grid_restore_damcons` returns immediately on a cockpit. That
is very likely why nobody hit #381 until now - the hallway-free hull that exists today never
runs the damcon code at all.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from unittest import mock as umock

import cosmos_dev.mock.sbs as mock
from cosmos_dev.mock import hull_mask
from tests.reset_helper import reset_mock

from sbs_utils.procedural import internal_damage
from sbs_utils.procedural.grid import (
    grid_delete_object, grid_get_damcons, grid_merge_ascii, grid_objects)
from sbs_utils.procedural.internal_damage import (
    _grid_unused_point, grid_damcon_count, grid_restore_damcons, grid_set_hp,
    grid_get_max_hp)
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.spawn import grid_spawn, player_spawn


# tsn_warpster's shipped floor plan with its three hallway cells (row 2 ".p.p.") filled in,
# so every one of the engine's 34 open cells holds a room. Merged as a NAMED layout, which
# leaves the hull's shipped "default" interior untouched.
NOHALLWAY_PLAN = """ship: tsn_warpster
layout: nohallway
size: 7x7
legend:
  a: aft-shield
  i: airlock
  b: beam-fwd
  c: cargo
  r: cargo_hatch
  o: conference-room
  e: crew-quarters
  f: fwd-shield
  g: galley
  y: gymnasium
  m: impulse
  u: maneuver
  p: passenger
  s: science-lab
  S: sensors
  t: torpedo-tube
  w: warp
  k: workshop
---
  pbp
 itfSi
 epepe
 ugoyu
rekaser
ccmmmcc
w     w
"""


class TestDamconPlacement(unittest.TestCase):
    def setUp(self):
        reset_mock(mock)
        hull_mask.clear_cache()

    def _ship(self, key="tsn_warpster"):
        return to_id(player_spawn(0, 0, 0, "NoHall", "tsn", key))

    def _pack_every_open_cell(self, hm):
        """Fill every open cell with a room, so no unoccupied cell is left anywhere."""
        for y in range(hm.h):
            for x in range(hm.w):
                if hm.is_grid_point_open(x, y):
                    go = hm.create_grid_object(f"room:{x},{y}", f"room:{x},{y}", "")
                    go.data_set.set("curx", x, 0)
                    go.data_set.set("cury", y, 0)

    def test_the_finders_disagree_on_a_fully_packed_hull(self):
        """Pins the MOCK's contract so the tests below cannot go vacuous.

        The unoccupied finder must come up empty once every open cell is taken, while the
        occupancy-tolerant one must still answer. If a mock change ever made the unoccupied
        finder succeed here, a hallway-free hull would stop being hallway-free in test.
        """
        sid = self._ship()
        hm = mock.get_hull_map(sid)
        self._pack_every_open_cell(hm)

        v = mock.vec3(0.5, 0, 0.5)
        self.assertEqual(mock.find_valid_unoccupied_grid_point_for_vector3(sid, v, 5), [],
                         "every cell is taken, so the unoccupied search must fail")
        loc = mock.find_valid_grid_point_for_vector3(sid, v, 5)
        self.assertEqual(len(loc), 2, "the occupancy-tolerant search must still answer")
        self.assertTrue(hm.is_grid_point_open(loc[0], loc[1]))

    def test_unused_point_spreads_teams_that_would_otherwise_stack(self):
        """The finder hands back the same cell every time; the teams must still spread."""
        sid = self._ship()
        hm = mock.get_hull_map(sid)

        used = set()
        cells = []
        for _ in range(3):
            p = _grid_unused_point(hm, [3, 3], used)      # the finder's unchanging answer
            used.add((p[0], p[1]))
            cells.append((p[0], p[1]))

        self.assertEqual(len(set(cells)), 3, f"three teams stacked: {cells}")
        self.assertEqual(cells[0], (3, 3), "the first team must keep the cell it was given")
        for x, y in cells:
            self.assertTrue(hm.is_grid_point_open(x, y), f"({x},{y}) is not an open cell")

    def test_unused_point_gives_up_rather_than_leaving_a_team_unplaced(self):
        """A hull with fewer open cells than teams gets stacked teams, not missing ones."""
        sid = self._ship()
        hm = mock.get_hull_map(sid)
        every = {(x, y) for y in range(hm.h) for x in range(hm.w)
                 if hm.is_grid_point_open(x, y)}
        self.assertEqual(_grid_unused_point(hm, [3, 3], every), [3, 3])

    def test_a_deleted_team_is_not_mistaken_for_a_live_one(self):
        """The rebuild bug: a tombstoned DC1 must not be 'healed' instead of recreated.

        `grid_delete_object` drops the agent now and queues the native free, so the engine's
        name lookup still answers until the queue drains. Restore must notice and create.
        """
        sid = self._ship()
        hm = mock.get_hull_map(sid)

        for i in range(3):
            name = f"DC{i + 1}"
            dc = grid_spawn(sid, name, name, 2 + i, 3, 2, "#0ff", "crew,damcons,lifeform")
            grid_set_hp(sid, to_id(dc), grid_get_max_hp())
        for gid in list(grid_objects(sid)):
            grid_delete_object(sid, gid)

        # Still findable by name - that is the whole trap.
        self.assertIsNotNone(hm.get_grid_object_by_name("DC1"),
                             "setup: the deferred free has not run, so the name still resolves")

        # The library calls the LM prefab to build a team, which a bare unit test cannot
        # resolve. Counting the attempts is what distinguishes create-three from heal-three.
        with umock.patch.object(internal_damage, "prefab_spawn",
                                return_value=None) as spawned:
            grid_restore_damcons(sid)

        self.assertEqual(spawned.call_count, 3,
                         "restore healed the tombstoned teams instead of creating new ones - "
                         "the ship would end the frame with no damage control at all")

    # --- the declaration: count and posts from the interior data --------------------

    def _install(self, damcons_header=None, layout="declared"):
        """Merge the packed floor plan as a named layout, optionally with a declaration."""
        plan = NOHALLWAY_PLAN.replace("layout: nohallway", f"layout: {layout}")
        if damcons_header is not None:
            plan = plan.replace("size: 7x7", f"size: 7x7\ndamcons: {damcons_header}")
        grid_merge_ascii(plan, "test")
        return layout

    def test_a_plan_that_says_nothing_declares_nothing(self):
        """Absent is not the same as "3". The whole backward-compatibility story."""
        self._install(None, layout="silent")
        self.assertIsNone(grid_get_damcons("tsn_warpster", "silent"),
                          "a floor plan with no damcons: header must declare NOTHING, or "
                          "every shipped hull changes behavior")
        sid = self._ship()
        self.assertEqual(grid_damcon_count(sid), 3, "the unstated default must stay 3")

    def test_declared_count_is_used(self):
        self._install("5", layout="five")
        sid = self._ship()
        set_inventory_value(sid, "grid_layout", "five")
        self.assertEqual(grid_damcon_count(sid), 5)

        with umock.patch.object(internal_damage, "prefab_spawn",
                                return_value=None) as spawned:
            grid_restore_damcons(sid, layout="five")
        self.assertEqual(spawned.call_count, 5, "five teams were declared")

    def test_declared_posts_are_used(self):
        """A post is where the team stands - and, via the prefab, where it rallies."""
        self._install("3  3,2  1,4  5,4", layout="posted")
        sid = self._ship()

        with umock.patch.object(internal_damage, "prefab_spawn",
                                return_value=None) as spawned:
            grid_restore_damcons(sid, layout="posted")

        cells = [(c.args[1]["START_X"], c.args[1]["START_Y"])
                 for c in spawned.call_args_list]
        self.assertEqual(cells, [(3, 2), (1, 4), (5, 4)])

    def test_a_post_off_the_hull_falls_back_instead_of_failing(self):
        """One bad coordinate must never leave a ship without damage control."""
        self._install("3  99,99  1,4  5,4", layout="badpost")
        sid = self._ship()
        hm = mock.get_hull_map(sid)

        with umock.patch.object(internal_damage, "prefab_spawn",
                                return_value=None) as spawned:
            grid_restore_damcons(sid, layout="badpost")

        self.assertEqual(spawned.call_count, 3, "all three teams must still be placed")
        cells = [(c.args[1]["START_X"], c.args[1]["START_Y"])
                 for c in spawned.call_args_list]
        self.assertNotEqual(cells[0], (99, 99))
        self.assertTrue(hm.is_grid_point_open(cells[0][0], cells[0][1]))
        self.assertEqual(cells[1:], [(1, 4), (5, 4)], "the good posts are still honored")

    def test_fewer_posts_than_teams_lets_the_engine_place_the_rest(self):
        self._install("3  3,2", layout="partial")
        sid = self._ship()
        hm = mock.get_hull_map(sid)

        with umock.patch.object(internal_damage, "prefab_spawn",
                                return_value=None) as spawned:
            grid_restore_damcons(sid, layout="partial")

        cells = [(c.args[1]["START_X"], c.args[1]["START_Y"])
                 for c in spawned.call_args_list]
        self.assertEqual(cells[0], (3, 2))
        self.assertEqual(len(set(cells)), 3, f"the engine-placed teams stacked: {cells}")
        for x, y in cells:
            self.assertTrue(hm.is_grid_point_open(x, y))

    def test_a_shrunk_count_retires_the_extra_teams(self):
        """A refit that drops to two teams must not leave DC3 walking the halls."""
        sid = self._ship()
        hm = mock.get_hull_map(sid)
        for i in range(3):
            name = f"DC{i + 1}"
            grid_spawn(sid, name, name, 2 + i, 3, 2, "#0ff", "crew,damcons,lifeform")

        self._install("2  2,3  3,3", layout="two")
        with umock.patch.object(internal_damage, "prefab_spawn", return_value=None):
            grid_restore_damcons(sid, layout="two")

        self.assertIsNone(to_object(hm.get_grid_object_by_name("DC3").unique_ID),
                          "DC3 is above the declared count and should have been retired")

    def test_a_live_team_is_healed_not_duplicated(self):
        """The control: a team that really is alive must be healed, never respawned."""
        sid = self._ship()
        dc = grid_spawn(sid, "DC1", "DC1", 3, 3, 2, "#0ff", "crew,damcons,lifeform")
        grid_set_hp(sid, to_id(dc), 1)

        with umock.patch.object(internal_damage, "prefab_spawn",
                                return_value=None) as spawned:
            grid_restore_damcons(sid)

        self.assertEqual(spawned.call_count, 2, "DC1 is alive - only DC2 and DC3 are missing")
        from sbs_utils.procedural.inventory import get_inventory_value
        self.assertEqual(get_inventory_value(to_id(dc), "HP", 0), grid_get_max_hp(),
                         "a live team must be restored to full HP")


if __name__ == "__main__":
    unittest.main()
