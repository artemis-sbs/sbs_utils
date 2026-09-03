"""Wear, the `__worn__` tier, and the four-tier node colors.

Two properties make this change safe to ship, and both are pinned by name.

**It is inert until something writes wear.** A node nothing has worn reads
WEAR_NOMINAL and weighs exactly 1.0, so `set_damage_coefficients` produces numbers
identical to the old `undamaged / total` fraction. Every mission that never touches
wear sees no change at all.

**A worn node keeps `__undamaged__`.** `__worn__` is orthogonal to the damage roles,
never a third value of them - which is what keeps the explode check, `system_damage[]`
and every mission's own `role("__undamaged__")` query meaning what they always meant.
An all-worn ship must not blow up.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first to break a circular import)
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent
from sbs_utils.procedural.query import to_id, to_blob
from sbs_utils.procedural.roles import role, add_role, has_role, all_roles
from sbs_utils.procedural.spawn import grid_spawn, player_spawn
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural import internal_damage as D
from sbs_utils.procedural import grid as G
from sbs_utils.procedural import work_orders as W


class WearBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Selene", "tsn", "cruiser"))
        # Restore the shipped tuning: grid_set_wear_tuning writes module globals, so a
        # test that retunes would otherwise leak into every test after it.
        self.addCleanup(D.grid_set_wear_tuning, 0.75, 0.10, 0.60, 0.10, 0.01)

    def tearDown(self):
        FrameContext.context = None
        SpaceObject.clear()

    def node(self, x, *roles):
        go = grid_spawn(self.ship, f"n{x}", f"n{x}", x, 0, 12, "LightYellow",
                        "#,room," + ",".join(roles))
        node_id = to_id(go)
        set_inventory_value(node_id, "color", "LightYellow")
        return node_id

    def pool(self, role_name, count, wear=None):
        made = []
        for i in range(count):
            n = self.node(len(made) + i * 7 + hash(role_name) % 3, role_name,
                          "__undamaged__")
            if wear is not None:
                D.grid_set_node_wear(n, wear, self.ship)
            made.append(n)
        return made

    def coeff(self, key, idx=0):
        return to_blob(self.ship).get(key, idx)


class TestDefaultIsInert(WearBase):
    def test_an_untouched_node_reads_nominal(self):
        n = self.node(0, "beam", "__undamaged__")
        self.assertEqual(D.grid_node_wear(n), D.WEAR_NOMINAL)
        self.assertEqual(D.grid_node_state(n), "nominal")
        self.assertEqual(D.grid_node_efficiency(n), 1.0)

    def test_coefficients_match_the_OLD_formula_exactly(self):
        """THE back-compat pin. The old code was len(undamaged)/total; nothing that
        has never worn a node may see a different number."""
        for role_name, key in (("beam", "all_beam_damage_coeff"),
                               ("impulse", "impulse_damage_coeff"),
                               ("warp", "warp_damage_coeff")):
            for well, sick in ((4, 0), (3, 1), (1, 3), (0, 4), (5, 2)):
                with self.subTest(role=role_name, well=well, sick=sick):
                    self.setUp()
                    for i in range(well):
                        self.node(i, role_name, "__undamaged__")
                    for i in range(sick):
                        self.node(100 + i, role_name, "__damaged__")
                    D.set_damage_coefficients(self.ship)
                    expected = well / max(1, well + sick)
                    self.assertAlmostEqual(self.coeff(key), expected, places=6)

    def test_a_system_the_ship_does_not_have_is_1(self):
        self.node(0, "beam", "__undamaged__")
        D.set_damage_coefficients(self.ship)
        self.assertEqual(self.coeff("warp_damage_coeff"), 1.0)


class TestWornIsOrthogonalToDamage(WearBase):
    def test_a_worn_node_KEEPS_undamaged(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_set_node_wear(n, 0.9, self.ship)
        self.assertTrue(has_role(n, "__worn__"))
        self.assertTrue(has_role(n, "__undamaged__"),
                        "a worn node must still count as undamaged")
        self.assertFalse(has_role(n, "__damaged__"))

    def test_an_ALL_WORN_ship_does_not_explode(self):
        """The explode check counts undamaged system nodes. If wear touched that
        count, maintaining nothing would destroy the ship."""
        for r in ("weapon", "engine", "sensor", "shield"):
            for n in self.pool(r, 2):
                D.grid_set_node_wear(n, 0.95, self.ship)
        D.grid_apply_system_damage(self.ship)
        self.assertFalse(has_role(self.ship, "exploded"))

    def test_system_damage_counts_do_not_move_when_a_node_wears_out(self):
        """The engine's own red system bars must keep meaning BROKEN."""
        for n in self.pool("weapon", 4):
            pass
        D.grid_apply_system_damage(self.ship)
        before = to_blob(self.ship).get("system_damage", sbs.SHPSYS.WEAPONS)
        for n in G.grid_objects(self.ship) & role("weapon"):
            D.grid_set_node_wear(n, 0.9, self.ship)
        D.grid_apply_system_damage(self.ship)
        self.assertEqual(to_blob(self.ship).get("system_damage", sbs.SHPSYS.WEAPONS),
                         before)

    def test_damaging_a_worn_node_clears_worn(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_set_node_wear(n, 0.9, self.ship)
        self.assertTrue(has_role(n, "__worn__"))
        D.grid_damage_grid_object(self.ship, n, "Crimson")
        self.assertFalse(has_role(n, "__worn__"),
                         "a broken node must not also be a tired one")
        self.assertEqual(D.grid_node_state(n), "damaged")


class TestEfficiency(WearBase):
    def test_the_four_tiers(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_set_node_wear(n, 0.0, self.ship)
        self.assertEqual(D.grid_node_efficiency(n), 1.0 + D.WEAR_TUNED_BONUS)
        D.grid_set_node_wear(n, D.WEAR_NOMINAL, self.ship)
        self.assertEqual(D.grid_node_efficiency(n), 1.0)
        D.grid_set_node_wear(n, 0.9, self.ship)
        self.assertEqual(D.grid_node_efficiency(n), D.WEAR_WORN_FACTOR)
        D.grid_damage_grid_object(self.ship, n, "Crimson")
        self.assertEqual(D.grid_node_efficiency(n), 0.0)

    def test_a_fully_tuned_pool_is_capped_at_the_bonus(self):
        self.pool("beam", 4, wear=0.0)
        D.set_damage_coefficients(self.ship)
        self.assertAlmostEqual(self.coeff("all_beam_damage_coeff"),
                               1.0 + D.WEAR_TUNED_BONUS, places=6)

    def test_a_fully_worn_pool_is_the_worn_factor(self):
        self.pool("beam", 4, wear=0.9)
        D.set_damage_coefficients(self.ship)
        self.assertAlmostEqual(self.coeff("all_beam_damage_coeff"),
                               D.WEAR_WORN_FACTOR, places=6)

    def test_tuning_the_bonus_to_zero_gives_strict_parity(self):
        """The escape hatch for a mission that wants maintenance without over-unity."""
        self.pool("beam", 4, wear=0.0)
        D.grid_set_wear_tuning(tuned_bonus=0.0)
        D.set_damage_coefficients(self.ship)
        self.assertAlmostEqual(self.coeff("all_beam_damage_coeff"), 1.0, places=6)


class TestColors(WearBase):
    """One write point. A node drawn in a color that disagrees with its condition
    would be worse than no color at all."""

    def color_of(self, node_id):
        return to_blob(node_id).get("icon_color", 0)

    def test_nominal_restores_the_nodes_OWN_healthy_color(self):
        n = self.node(0, "beam", "__undamaged__")
        set_inventory_value(n, "color", "HotPink")     # a re-skinned room
        D.grid_set_node_wear(n, D.WEAR_NOMINAL, self.ship)
        self.assertEqual(self.color_of(n), "HotPink")

    def test_worn_draws_in_the_worn_color(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_set_node_wear(n, 0.9, self.ship)
        self.assertEqual(self.color_of(n), G.GRID_WORN_COLOR)

    def test_tuned_draws_in_the_tuned_color(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_set_node_wear(n, 0.0, self.ship)
        self.assertEqual(self.color_of(n), G.GRID_TUNED_COLOR)

    def test_a_theme_with_NO_worn_map_falls_back_instead_of_raising(self):
        """No shipped theme has worn_colors or tuned_colors, and a mod theme replaces
        one wholesale - so the lookup must never subscript these."""
        original = G.grid_get_grid_named_theme
        G.grid_get_grid_named_theme = lambda name=None: {
            "name": "bare", "colors": {"default": "red"},
            "damage_colors": {"default": "Crimson"}, "icons": {},
        }
        try:
            n = self.node(0, "beam", "__undamaged__")
            D.grid_set_node_wear(n, 0.9, self.ship)
            self.assertEqual(self.color_of(n), G.GRID_WORN_COLOR)
            D.grid_set_node_wear(n, 0.0, self.ship)
            self.assertEqual(self.color_of(n), G.GRID_TUNED_COLOR)
        finally:
            G.grid_get_grid_named_theme = original


class TestPatchVersusRestore(WearBase):
    def test_a_DAMCON_repair_leaves_the_node_worn(self):
        """Where maintenance work comes from: nothing invents it, damage does."""
        n = self.node(0, "beam", "__undamaged__")
        dc = grid_spawn(self.ship, "DC1", "DC1", 5, 0, 80, "slateblue",
                        "crew,damcons,lifeform")
        D.grid_damage_grid_object(self.ship, n, "Crimson")
        D.grid_repair_grid_objects(self.ship, n, to_id(dc))
        self.assertEqual(D.grid_node_state(n), "worn")
        self.assertTrue(has_role(n, "__undamaged__"))

    def test_a_DOCKYARD_repair_leaves_it_nominal(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_damage_grid_object(self.ship, n, "Crimson")
        D.grid_repair_grid_objects(self.ship, n)          # who_repaired=None
        self.assertEqual(D.grid_node_state(n), "nominal")


class TestTuning(WearBase):
    def test_tuning_zeroes_wear_and_clears_the_role(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_set_node_wear(n, 0.9, self.ship)
        self.assertTrue(D.grid_tune_grid_object(self.ship, n))
        self.assertEqual(D.grid_node_wear(n), 0.0)
        self.assertFalse(has_role(n, "__worn__"))
        self.assertEqual(D.grid_node_state(n), "tuned")

    def test_tuning_closes_the_order_for_EVERY_team(self):
        n = self.node(0, "beam", "__undamaged__")
        D.grid_set_node_wear(n, 0.9, self.ship)
        teams = [to_id(grid_spawn(self.ship, f"DC{i}", f"DC{i}", 5 + i, 0, 80,
                                  "slateblue", "crew,damcons,lifeform"))
                 for i in (1, 2)]
        for t in teams:
            W.work_order_add(t, n)
        D.grid_tune_grid_object(self.ship, n, teams[0])
        self.assertEqual(W.work_order_workers(n), set())

    def test_tuning_a_node_that_is_gone_is_False_not_a_crash(self):
        self.assertFalse(D.grid_tune_grid_object(self.ship, 999999999))


class TestWearWriters(WearBase):
    def test_wear_is_clamped(self):
        n = self.node(0, "beam", "__undamaged__")
        self.assertEqual(D.grid_set_node_wear(n, 5.0, self.ship), 1.0)
        self.assertEqual(D.grid_set_node_wear(n, -5.0, self.ship), 0.0)

    def test_wear_system_skips_damaged_nodes(self):
        """Wear on a node already at zero effectiveness would mean nothing, and
        would be thrown away the moment it was repaired."""
        good = self.node(0, "beam", "__undamaged__")
        bad = self.node(1, "beam", "__damaged__")
        D.grid_wear_system(self.ship, "beam", 0.5, count=5)
        self.assertGreater(D.grid_node_wear(good), D.WEAR_NOMINAL)
        self.assertEqual(D.grid_node_wear(bad), D.WEAR_NOMINAL)

    def test_wear_system_on_a_pool_the_ship_lacks_is_zero(self):
        self.assertEqual(D.grid_wear_system(self.ship, "warp", 0.5), 0)

    def test_upkeep_ages_every_working_node(self):
        nodes = self.pool("beam", 3)
        aged = D.grid_wear_upkeep(self.ship, 0.05)
        self.assertEqual(aged, 3)
        for n in nodes:
            self.assertAlmostEqual(D.grid_node_wear(n), D.WEAR_NOMINAL + 0.05,
                                   places=6)

    def test_crossing_the_threshold_recomputes_the_coefficient(self):
        self.pool("beam", 2)
        D.set_damage_coefficients(self.ship)
        self.assertAlmostEqual(self.coeff("all_beam_damage_coeff"), 1.0, places=6)
        for n in G.grid_objects(self.ship) & role("beam"):
            D.grid_set_node_wear(n, 0.9, self.ship)
        self.assertAlmostEqual(self.coeff("all_beam_damage_coeff"),
                               D.WEAR_WORN_FACTOR, places=6)


class TestTravelWear(WearBase):
    """The throttle split, which the routes now delegate here so it can be pinned.

    <= 1.0 is impulse, > 1.0 is warp. A ship that has never moved has never had a
    throttle written, and the ENGINE answers None for a blob field nothing has set -
    the mock answers a typed 0 and cannot show us that at all.
    """

    def test_a_stopped_ship_wears_no_drive(self):
        self.pool("impulse", 2)
        self.pool("warp", 2)
        self.assertIsNone(D.grid_wear_travel(self.ship, 0.0))

    def test_impulse_wears_only_the_impulse_pool(self):
        self.pool("impulse", 2)
        self.pool("warp", 2)
        self.assertEqual(D.grid_wear_travel(self.ship, 1.0), "impulse")
        worn = {D.grid_node_wear(n) for n in G.grid_objects(self.ship) & role("warp")}
        self.assertEqual(worn, {D.WEAR_NOMINAL}, "warp must not wear at impulse")

    def test_warp_wears_only_the_warp_pool(self):
        self.pool("impulse", 2)
        self.pool("warp", 2)
        self.assertEqual(D.grid_wear_travel(self.ship, 3.0), "warp")
        worn = {D.grid_node_wear(n) for n in G.grid_objects(self.ship) & role("impulse")}
        self.assertEqual(worn, {D.WEAR_NOMINAL}, "impulse must not wear at warp")

    def test_warp_wear_scales_with_the_factor_over_one(self):
        self.pool("warp", 1)
        node = list(G.grid_objects(self.ship) & role("warp"))[0]
        D.grid_wear_travel(self.ship, 3.0)
        self.assertAlmostEqual(D.grid_node_wear(node),
                               D.WEAR_NOMINAL + D.WEAR_PER_WARP_MINUTE * 2.0, places=6)

    def test_a_None_throttle_is_treated_as_stopped_not_a_crash(self):
        """The engine's answer for a ship that has never moved. Unguarded this is
        `None > 1.0`, and a failing expression STOPS the command - so the whole
        upkeep route would silently stop working."""
        class _NoThrottleBlob:
            def get(self, key, index=0):
                return None
        original = D.to_blob
        D.to_blob = lambda _id: _NoThrottleBlob()
        try:
            self.assertIsNone(D.grid_wear_travel(self.ship))
        finally:
            D.to_blob = original

    def test_a_ship_with_no_blob_at_all_is_stopped(self):
        original = D.to_blob
        D.to_blob = lambda _id: None
        try:
            self.assertIsNone(D.grid_wear_travel(self.ship))
        finally:
            D.to_blob = original


class TestShieldHitWear(WearBase):
    def test_face_zero_is_forward(self):
        self.pool("shield,fwd", 2)
        self.pool("shield,aft", 2)
        D.grid_wear_shield_hit(self.ship, 0)
        aft = {D.grid_node_wear(n)
               for n in G.grid_objects(self.ship) & all_roles("shield,aft")}
        self.assertEqual(aft, {D.WEAR_NOMINAL}, "a forward hit must not wear the aft shield")

    def test_any_other_face_is_aft(self):
        self.pool("shield,fwd", 2)
        self.pool("shield,aft", 2)
        D.grid_wear_shield_hit(self.ship, 1)
        fwd = {D.grid_node_wear(n)
               for n in G.grid_objects(self.ship) & all_roles("shield,fwd")}
        self.assertEqual(fwd, {D.WEAR_NOMINAL}, "an aft hit must not wear the forward shield")


class TestRateTuning(WearBase):
    def test_a_rate_can_be_moved_by_short_name(self):
        D.grid_set_wear_tuning(beam_hit=0.5)
        self.assertEqual(D.WEAR_PER_BEAM_HIT, 0.5)

    def test_upkeep_can_be_turned_off_entirely(self):
        nodes = self.pool("beam", 2)
        D.grid_set_wear_tuning(upkeep_rate=0)
        D.grid_wear_upkeep(self.ship)
        for n in nodes:
            self.assertEqual(D.grid_node_wear(n), D.WEAR_NOMINAL)

    def test_an_unknown_rate_name_does_not_silently_do_nothing(self):
        """A typo in a dial reads exactly like "the dial has no effect"."""
        seen = []
        original = D.log
        D.log = lambda msg, *a, **k: seen.append(msg)
        try:
            D.grid_set_wear_tuning(beeem_hit=0.5)
        finally:
            D.log = original
        self.assertTrue(any("beeem_hit" in m for m in seen), seen)


if __name__ == "__main__":
    unittest.main()
