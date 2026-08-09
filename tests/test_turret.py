"""turret primitive - configuration, target policy, and the "never moves" contract.

What the mock CAN cover is the Python we own: config stamping, the role-expression and
diplomacy filters, the anti-thrash hysteresis, and - most importantly - that engaging a
target writes ``target_id`` and nothing else.

What it CANNOT cover is whether the engine's beams then actually fire. That is
engine-measured in ``LM_TestRange/maps/test_turret_probe.mast``, which established that
a ``behav_station`` fires only from a hull declared through ``ship_data_merge_mod``. A
green run here says the policy is right, not that a turret shoots.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.query import get_data_set_value, to_id, to_object
from sbs_utils.procedural.roles import add_role, remove_role
from sbs_utils.procedural.sides import side_ensure, side_set_relations
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural import turret as tr


class TurretTestBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        # Real diplomacy, so the hostile-set filter is exercised rather than bypassed.
        tsn = side_ensure("tsn", "TSN")
        raider = side_ensure("raider", "Raider")
        side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)
        self.gun = to_id(npc_spawn(0, 0, 0, "Gun", "tsn", "starbase_command", "behav_station"))
        tr.turret_make(self.gun, range=2000)

    def _foe(self, z, name="Foe", side="raider"):
        return to_id(npc_spawn(0, 0, z, name, side, "tsn_light_cruiser", "behav_npcship"))


class TestTurretConfig(TurretTestBase):
    def test_make_stamps_roles_and_config(self):
        self.assertTrue(tr.turret_is(self.gun))
        self.assertIn(self.gun, tr.turret_all())
        self.assertEqual(tr.turret_range(self.gun), 2000)
        self.assertEqual(tr.turret_config(self.gun, "priority"), "closest")

    def test_make_on_missing_object_returns_none(self):
        self.assertIsNone(tr.turret_make(0))

    def test_range_defaults_when_unconfigured(self):
        g = to_id(npc_spawn(0, 0, 5000, "Bare", "tsn", "starbase_command", "behav_station"))
        tr.turret_make(g)
        self.assertEqual(tr.turret_range(g), tr.TURRET_DEFAULT_RANGE)

    def test_set_changes_a_live_turret(self):
        tr.turret_set(self.gun, "range", 500)
        self.assertEqual(tr.turret_range(self.gun), 500)

    def test_config_is_per_object_not_global(self):
        other = to_id(npc_spawn(0, 0, 9000, "Other", "tsn", "starbase_command", "behav_station"))
        tr.turret_make(other, range=750)
        self.assertEqual(tr.turret_range(self.gun), 2000)
        self.assertEqual(tr.turret_range(other), 750)


class TestTurretAcquire(TurretTestBase):
    def test_acquires_nearest_hostile(self):
        near = self._foe(500, "Near")
        self._foe(1500, "Far")
        self.assertEqual(tr.turret_acquire(self.gun), near)

    def test_ignores_out_of_range(self):
        self._foe(9000, "TooFar")
        self.assertIsNone(tr.turret_acquire(self.gun))

    def test_ignores_allies(self):
        self._foe(500, "Friend", side="tsn")
        self.assertIsNone(tr.turret_acquire(self.gun))

    def test_ignores_other_turrets(self):
        # An emplacement duelling another emplacement while the ships it was built to
        # stop fly past is never what an author wanted.
        other = self._foe(500, "EnemyTurret")
        tr.turret_make(other)
        self.assertIsNone(tr.turret_acquire(self.gun))

    def test_targets_expression_filters(self):
        # tsn_light_cruiser carries `warship` from its own shipData roles, so that is a
        # real positive; `monster` is a role no ship art grants.
        foe = self._foe(500, "Foe")
        tr.turret_set(self.gun, "targets", "monster")
        self.assertIsNone(tr.turret_acquire(self.gun))
        tr.turret_set(self.gun, "targets", "warship")
        self.assertEqual(tr.turret_acquire(self.gun), foe)

    def test_acquires_across_the_full_configured_range(self):
        # Regression: closest(max_dist=D) narrows with a box of WIDTH D, i.e. +-D/2, so
        # a naive call silently ignores everything past half range.
        far = self._foe(1800, "NearMaxRange")
        self.assertEqual(tr.turret_acquire(self.gun), far)

    def test_no_candidates_returns_none(self):
        self.assertIsNone(tr.turret_acquire(self.gun))

    def test_weakest_priority_prefers_damaged_over_near(self):
        near = self._foe(500, "Healthy")
        far = self._foe(1500, "Hurt")
        to_object(far).data_set.set("shield_val", 1.0, 0)
        self.assertEqual(tr.turret_acquire(self.gun), near)
        tr.turret_set(self.gun, "priority", "weakest")
        self.assertEqual(tr.turret_acquire(self.gun), far)


class TestTurretHysteresis(TurretTestBase):
    def test_closer_candidate_does_not_steal_during_hold(self):
        first = self._foe(1000, "First")
        tr.turret_engage(self.gun, first)
        self._foe(200, "Closer")
        # Inside hold_seconds the turret sticks. Without this a turret between two
        # enemies re-picks every scan and effectively never fires.
        self.assertEqual(tr.turret_acquire(self.gun), first)

    def test_switches_once_the_hold_expires(self):
        first = self._foe(1000, "First")
        tr.turret_engage(self.gun, first)
        closer = self._foe(200, "Closer")
        tr.turret_set(self.gun, "hold_until", 0.0)
        self.assertEqual(tr.turret_acquire(self.gun), closer)

    def test_target_leaving_slack_range_is_dropped(self):
        foe = self._foe(1000, "Foe")
        tr.turret_engage(self.gun, foe)
        to_object(foe).pos = sbs.vec3(0, 0, 9000)
        self.assertIsNone(tr.turret_acquire(self.gun))

    def test_target_inside_slack_is_kept_though_beyond_range(self):
        # range 2000, slack 1.15 -> still held at 2100.
        foe = self._foe(1000, "Foe")
        tr.turret_engage(self.gun, foe)
        to_object(foe).pos = sbs.vec3(0, 0, 2100)
        self.assertEqual(tr.turret_acquire(self.gun), foe)


class TestTurretDesignate(TurretTestBase):
    def test_designated_beats_a_closer_candidate(self):
        far = self._foe(1500, "Ordered")
        self._foe(200, "Closer")
        tr.turret_designate(self.gun, far)
        self.assertEqual(tr.turret_acquire(self.gun), far)

    def test_designated_survives_rescan(self):
        far = self._foe(1500, "Ordered")
        self._foe(200, "Closer")
        tr.turret_designate(self.gun, far)
        tr.turret_tick(self.gun)
        tr.turret_set(self.gun, "hold_until", 0.0)
        self.assertEqual(tr.turret_acquire(self.gun), far)

    def test_designated_out_of_range_falls_back_to_scan(self):
        far = self._foe(9000, "Unreachable")
        near = self._foe(200, "Reachable")
        tr.turret_designate(self.gun, far)
        self.assertEqual(tr.turret_acquire(self.gun), near)

    def test_clearing_designation_returns_to_free_fire(self):
        far = self._foe(1500, "Ordered")
        near = self._foe(200, "Closer")
        tr.turret_designate(self.gun, far)
        tr.turret_designate(self.gun, None)
        self.assertEqual(tr.turret_acquire(self.gun), near)


class TestTurretEngage(TurretTestBase):
    def test_engage_writes_only_target_id(self):
        """The 'a turret does not move' contract.

        target() would also write throttle and target_pos_* and the turret would chase
        its victim across the map. target_shoot() writes target_id alone - if this test
        ever fails, turrets have started flying.
        """
        foe = self._foe(500)
        before = [get_data_set_value(self.gun, k, 0)
                  for k in ("throttle", "target_pos_x", "target_pos_y", "target_pos_z")]
        tr.turret_engage(self.gun, foe)
        self.assertEqual(get_data_set_value(self.gun, "target_id", 0), foe)
        after = [get_data_set_value(self.gun, k, 0)
                 for k in ("throttle", "target_pos_x", "target_pos_y", "target_pos_z")]
        self.assertEqual(before, after)

    def test_engage_missing_target_is_a_noop(self):
        self.assertIsNone(tr.turret_engage(self.gun, 0))
        self.assertIsNone(tr.turret_target(self.gun))

    def test_disengage_clears_the_weapon_target(self):
        foe = self._foe(500)
        tr.turret_engage(self.gun, foe)
        tr.turret_disengage(self.gun)
        self.assertEqual(get_data_set_value(self.gun, "target_id", 0), 0)
        self.assertIsNone(tr.turret_target(self.gun))

    def test_tick_acquires_and_engages(self):
        foe = self._foe(500)
        self.assertEqual(tr.turret_tick(self.gun), foe)
        self.assertEqual(get_data_set_value(self.gun, "target_id", 0), foe)

    def test_tick_stands_down_when_the_target_dies(self):
        foe = self._foe(500)
        tr.turret_tick(self.gun)
        sbs.delete_object(foe)
        tr.turret_set(self.gun, "hold_until", 0.0)
        self.assertIsNone(tr.turret_tick(self.gun))
        self.assertEqual(get_data_set_value(self.gun, "target_id", 0), 0)

    def test_tick_on_a_dead_turret_does_not_raise(self):
        foe = self._foe(500)
        tr.turret_tick(self.gun)
        sbs.delete_object(self.gun)
        self.assertIsNone(tr.turret_tick(self.gun))


class TestTurretDiplomacy(TurretTestBase):
    def test_ceasefire_stops_the_turret_with_no_tag_to_update(self):
        foe = self._foe(500)
        self.assertEqual(tr.turret_acquire(self.gun), foe)
        side_set_relations(side_ensure("tsn"), side_ensure("raider"),
                           sbs.DIPLOMACY.NEUTRAL)
        tr.turret_set(self.gun, "hold_until", 0.0)
        self.assertIsNone(tr.turret_acquire(self.gun))

    def test_surrendered_ship_is_spared(self):
        foe = self._foe(500)
        add_role(foe, "surrendered")
        self.assertIsNone(tr.turret_acquire(self.gun))
        remove_role(foe, "surrendered")
        self.assertEqual(tr.turret_acquire(self.gun), foe)


if __name__ == "__main__":
    unittest.main()
