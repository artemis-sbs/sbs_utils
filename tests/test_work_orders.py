"""Work orders (procedural/work_orders.py).

Two things this file exists to pin.

**Back compat.** An order IS a link, and missions outside this repo file them with a
bare ``link(dc, "work-order", node)``. Every one of those has to keep reading back as
an ordinary order, which is why ``work_order_get`` synthesizes rather than returning
None and why ``work_order_targets`` derives from ``has_link`` rather than from a role
a bare link would not carry.

**The purge.** Orders were never purged. ``Agent._remove`` clears the role and link
REGISTRIES when a node dies but not the entry in another agent's own link set, so a
link to a deleted node outlived it forever and the count on the console was
permanently wrong.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first to break a circular import)
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import add_role, has_role
from sbs_utils.procedural.links import link, linked_to
from sbs_utils.procedural.spawn import grid_spawn, player_spawn
from sbs_utils.procedural.grid import grid_delete_object
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.internal_damage import WEAR_WORN_MIN, WEAR_NOMINAL
from sbs_utils.procedural import work_orders as W


class WorkOrderBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Selene", "tsn", "cruiser"))

    def tearDown(self):
        FrameContext.context = None
        SpaceObject.clear()

    # --- fixtures ---------------------------------------------------------
    def node(self, x, *roles, ship=None, kind="system"):
        """A REAL grid object: grid_objects walks the engine's hull map, so a
        stand-in agent is invisible to every query under test.

        `system` by default - only a system node wears, so only a system node can
        carry a maintenance order. Pass kind="room" for a crew space."""
        go = grid_spawn(ship or self.ship, f"n{x}", f"n{x}", x, 0, 12, "white",
                        f"#,{kind}," + ",".join(roles))
        return to_id(go)

    def broken(self, x, ship=None):
        return self.node(x, "weapon", "__damaged__", ship=ship)

    def healthy(self, x, ship=None):
        return self.node(x, "weapon", "__undamaged__", ship=ship)

    def worn(self, x, ship=None):
        node_id = self.node(x, "weapon", "__undamaged__", "__worn__", ship=ship)
        set_inventory_value(node_id, "wear", WEAR_WORN_MIN + 0.1)
        return node_id

    def team(self, x, name="DC1", ship=None):
        go = grid_spawn(ship or self.ship, name, name, x, 0, 80, "slateblue",
                        "crew,damcons,lifeform")
        return to_id(go)


class TestBareLinkBackCompat(WorkOrderBase):
    """A mission that never heard of this module must keep working."""

    def test_a_bare_link_IS_an_order(self):
        node = self.broken(0)
        link(self.team(1), "work-order", node)
        order = W.work_order_get(node)
        self.assertIsNotNone(order, "a bare link() has to read back as an order")
        self.assertEqual(order["kind"], W.KIND_REPAIR)
        self.assertEqual(order["priority"], W.PRIORITY_NORMAL)

    def test_work_order_targets_finds_a_bare_link(self):
        node = self.broken(0)
        link(self.team(1), "work-order", node)
        self.assertEqual(W.work_order_targets(self.ship), {node})

    def test_a_bare_link_can_be_prioritized_without_being_refiled(self):
        node = self.broken(0)
        link(self.team(1), "work-order", node)
        W.work_order_set_priority(node, W.PRIORITY_HIGH)
        self.assertEqual(W.work_order_priority(node), W.PRIORITY_HIGH)

    def test_a_node_with_no_link_has_no_order(self):
        self.assertIsNone(W.work_order_get(self.broken(0)))
        self.assertEqual(W.work_order_priority(self.broken(1)), 0)


class TestDefaults(WorkOrderBase):
    def test_a_damaged_node_defaults_to_repair_at_normal(self):
        node = self.broken(0)
        order = W.work_order_add(self.team(1), node)
        self.assertEqual((order["kind"], order["priority"]),
                         (W.KIND_REPAIR, W.PRIORITY_NORMAL))

    def test_a_worn_node_defaults_to_maintenance_at_low(self):
        node = self.worn(0)
        order = W.work_order_add(self.team(1), node)
        self.assertEqual((order["kind"], order["priority"]),
                         (W.KIND_MAINTAIN, W.PRIORITY_LOW))

    def test_a_second_team_joining_does_not_demote_the_job(self):
        node = self.broken(0)
        W.work_order_add(self.team(1, "DC1"), node, priority=W.PRIORITY_CRITICAL)
        W.work_order_add(self.team(2, "DC2"), node)
        self.assertEqual(W.work_order_priority(node), W.PRIORITY_CRITICAL)

    def test_bump_walks_the_rungs_and_clamps(self):
        node = self.broken(0)
        W.work_order_add(self.team(1), node)                 # NORMAL
        self.assertEqual(W.work_order_bump(node), W.PRIORITY_HIGH)
        self.assertEqual(W.work_order_bump(node), W.PRIORITY_CRITICAL)
        self.assertEqual(W.work_order_bump(node), W.PRIORITY_CRITICAL)
        for _ in range(5):
            W.work_order_bump(node, -1)
        self.assertEqual(W.work_order_priority(node), W.PRIORITY_LOW)

    def test_bump_on_a_node_with_no_order_is_a_no_op(self):
        self.assertIsNone(W.work_order_bump(self.broken(0)))


class TestCancel(WorkOrderBase):
    def test_the_order_survives_while_a_team_is_still_on_it(self):
        node = self.broken(0)
        dc1, dc2 = self.team(1, "DC1"), self.team(2, "DC2")
        W.work_order_add(dc1, node)
        W.work_order_add(dc2, node)
        W.work_order_cancel(dc1, node)
        self.assertIsNotNone(W.work_order_get(node))
        self.assertEqual(W.work_order_workers(node), {dc2})

    def test_cancelling_the_last_team_closes_the_order(self):
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        W.work_order_cancel(dc, node)
        self.assertIsNone(W.work_order_get(node))

    def test_cancel_all_takes_EVERY_team_off(self):
        """Repair used to drop only the repairer's link, leaving a second team
        walking to a room that was already fixed."""
        node = self.broken(0)
        dc1, dc2 = self.team(1, "DC1"), self.team(2, "DC2")
        W.work_order_add(dc1, node)
        W.work_order_add(dc2, node)
        W.work_order_cancel_all(node)
        self.assertEqual(W.work_order_workers(node), set())
        self.assertEqual(linked_to(dc2, "work-order"), set())


class TestPurge(WorkOrderBase):
    def test_a_deleted_target_is_dropped(self):
        """THE leak. Agent._remove clears the registries but not the worker's own
        link set, so this id used to come back forever."""
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        grid_delete_object(self.ship, node)
        self.assertEqual(W.work_orders_for(dc), set())
        self.assertEqual(linked_to(dc, "work-order"), set(),
                         "the stale link must actually be removed, not just filtered")

    def test_a_target_somebody_else_repaired_is_dropped(self):
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        Agent.get(node).remove_role("__damaged__")
        add_role(node, "__undamaged__")
        self.assertEqual(W.work_orders_for(dc), set())

    def test_a_satisfied_repair_does_not_come_BACK_when_the_node_wears_out(self):
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        Agent.get(node).remove_role("__damaged__")
        add_role(node, "__undamaged__")
        self.assertEqual(W.work_orders_for(dc), set())
        add_role(node, "__worn__")
        set_inventory_value(node, "wear", WEAR_WORN_MIN + 0.1)
        self.assertEqual(W.work_orders_for(dc), set(),
                         "a closed repair order must not resurrect as maintenance")

    def test_a_target_on_another_ship_is_dropped(self):
        """A grid rebuild replaces every id, so an order can end up pointing at a
        node that is real but belongs to somebody else."""
        other = to_id(player_spawn(1000, 0, 0, "Vega", "tsn", "cruiser"))
        far = self.broken(0, ship=other)
        dc = self.team(1)
        link(dc, "work-order", far)
        self.assertEqual(W.work_orders_for(dc), set())

    def test_a_dead_worker_keeps_nothing(self):
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        grid_delete_object(self.ship, dc)
        self.assertEqual(W.work_orders_for(dc), set())

    def test_an_exploded_ship_drops_every_order(self):
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        add_role(self.ship, "exploded")
        self.assertEqual(W.work_orders_for(dc), set())

    def test_purge_false_does_not_write(self):
        """A signature or a probe must be able to read without mutating."""
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        grid_delete_object(self.ship, node)
        W.work_orders_for(dc, purge=False)
        self.assertEqual(linked_to(dc, "work-order"), {node})

    def test_purge_ship_sweeps_every_team(self):
        a, b = self.broken(0), self.broken(1)
        dc1, dc2 = self.team(2, "DC1"), self.team(3, "DC2")
        W.work_order_add(dc1, a)
        W.work_order_add(dc2, b)
        grid_delete_object(self.ship, a)
        grid_delete_object(self.ship, b)
        self.assertEqual(W.work_order_purge_ship(self.ship), 2)

    def test_a_live_order_is_left_alone(self):
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        self.assertEqual(W.work_orders_for(dc), {node})
        self.assertEqual(W.work_orders_for(dc), {node})


class TestSatisfied(WorkOrderBase):
    def test_a_repair_is_satisfied_when_the_node_is_undamaged(self):
        node = self.broken(0)
        W.work_order_add(self.team(1), node)
        self.assertFalse(W.work_order_is_satisfied(node))
        Agent.get(node).remove_role("__damaged__")
        self.assertTrue(W.work_order_is_satisfied(node))

    def test_maintenance_is_satisfied_only_when_the_node_is_TUNED(self):
        """Not merely when it stopped being worn. Reading it that way made an order
        on a nominal node complete on its first read, so a healthy system could
        never be tuned at all."""
        node = self.worn(0)
        W.work_order_add(self.team(1), node)
        self.assertFalse(W.work_order_is_satisfied(node))
        Agent.get(node).remove_role("__worn__")
        set_inventory_value(node, "wear", WEAR_NOMINAL)
        self.assertFalse(W.work_order_is_satisfied(node),
                         "back to nominal is not the same as brought up to spec")
        set_inventory_value(node, "wear", 0.0)
        self.assertTrue(W.work_order_is_satisfied(node))

    def test_a_node_with_no_order_is_trivially_satisfied(self):
        self.assertTrue(W.work_order_is_satisfied(self.broken(0)))


class TestBest(WorkOrderBase):
    """The pick the brain makes. The commit is the anti-oscillation property and
    must not be lost: recomputing the straight-line closest every tick makes the
    choice flip as the team walks the corridor between two orders."""

    def test_nothing_assigned_is_None(self):
        self.assertIsNone(W.work_order_best(self.team(0)))

    def test_the_commit_is_kept_at_equal_priority(self):
        near, far = self.broken(1), self.broken(9)
        dc = self.team(0)
        W.work_order_add(dc, near)
        W.work_order_add(dc, far)
        self.assertEqual(W.work_order_best(dc, committed=far), far)

    def test_without_a_commit_the_closest_wins(self):
        near, far = self.broken(1), self.broken(9)
        dc = self.team(0)
        W.work_order_add(dc, near)
        W.work_order_add(dc, far)
        self.assertEqual(W.work_order_best(dc), near)

    def test_the_same_choice_comes_back_twice(self):
        self.broken(1)
        self.broken(9)
        dc = self.team(0)
        for node in W.work_order_targets(self.ship) or []:
            pass
        W.work_order_add(dc, self.broken(2))
        W.work_order_add(dc, self.broken(8))
        first = W.work_order_best(dc)
        self.assertEqual(W.work_order_best(dc), first)

    def test_a_raised_order_preempts_the_commit(self):
        near, far = self.broken(1), self.broken(9)
        dc = self.team(0)
        W.work_order_add(dc, near)
        W.work_order_add(dc, far)
        W.work_order_set_priority(far, W.PRIORITY_CRITICAL)
        self.assertEqual(W.work_order_best(dc, committed=near), far)

    def test_preemption_happens_once(self):
        near, far = self.broken(1), self.broken(9)
        dc = self.team(0)
        W.work_order_add(dc, near)
        W.work_order_add(dc, far, priority=W.PRIORITY_CRITICAL)
        chosen = W.work_order_best(dc, committed=near)
        self.assertEqual(W.work_order_best(dc, committed=chosen), chosen,
                         "two orders must never trade the commit back and forth")

    def test_a_room_filter_still_applies(self):
        broken_node = self.broken(1)
        worn_node = self.worn(2)
        dc = self.team(0)
        W.work_order_add(dc, broken_node)
        W.work_order_add(dc, worn_node)
        self.assertEqual(W.work_order_best(dc, room="__damaged__"), broken_node)

    def test_no_room_filter_reaches_a_maintenance_order(self):
        """The old brain node filtered on `__damaged__`, which would exclude every
        maintenance order there will ever be."""
        worn_node = self.worn(2)
        dc = self.team(0)
        W.work_order_add(dc, worn_node)
        self.assertEqual(W.work_order_best(dc), worn_node)
        self.assertIsNone(W.work_order_best(dc, room="__damaged__"))


class TestRows(WorkOrderBase):
    def test_no_orders_is_an_empty_list(self):
        self.assertEqual(W.work_order_rows(self.ship), [])
        self.assertEqual(W.work_order_rows(None), [])

    def test_two_teams_on_one_node_are_ONE_row(self):
        node = self.broken(0)
        W.work_order_add(self.team(1, "DC1"), node)
        W.work_order_add(self.team(2, "DC2"), node)
        rows = W.work_order_rows(self.ship)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["workers"], ["DC1", "DC2"])

    def test_rows_sort_highest_priority_first(self):
        low, high = self.broken(0), self.broken(1)
        dc = self.team(2)
        W.work_order_add(dc, low, priority=W.PRIORITY_LOW)
        W.work_order_add(dc, high, priority=W.PRIORITY_CRITICAL)
        self.assertEqual([r["target"] for r in W.work_order_rows(self.ship)],
                         [high, low])


class TestKindWanted(WorkOrderBase):
    def test_damaged_wants_a_repair(self):
        self.assertEqual(W.work_order_kind_wanted(self.broken(0)), W.KIND_REPAIR)

    def test_worn_wants_maintenance(self):
        self.assertEqual(W.work_order_kind_wanted(self.worn(0)), W.KIND_MAINTAIN)

    def test_a_healthy_node_accepts_maintenance(self):
        """"Wanted" is what it would ACCEPT, not what it needs - tuning a nominal
        node is how the tuned tier is earned in the first place."""
        self.assertEqual(W.work_order_kind_wanted(self.healthy(0)), W.KIND_MAINTAIN)

    def test_an_already_tuned_node_wants_nothing(self):
        node = self.healthy(0)
        set_inventory_value(node, "wear", 0.0)
        self.assertIsNone(W.work_order_kind_wanted(node))


class TestRepairClosesTheOrder(WorkOrderBase):
    """grid_repair_grid_objects is the integration point: a team arriving and
    fixing a room has to close the job for EVERY team sent to it."""

    def test_the_repairing_team_is_released(self):
        from sbs_utils.procedural.internal_damage import grid_repair_grid_objects
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        grid_repair_grid_objects(self.ship, node, dc)
        self.assertEqual(linked_to(dc, "work-order"), set())
        self.assertFalse(has_role(node, "__damaged__"))

    def test_a_SECOND_team_is_released_too(self):
        """The old behavior dropped only the repairer's link, so the other team
        kept a link to a room that was already fixed - forever, silently."""
        from sbs_utils.procedural.internal_damage import grid_repair_grid_objects
        node = self.broken(0)
        dc1, dc2 = self.team(1, "DC1"), self.team(2, "DC2")
        W.work_order_add(dc1, node)
        W.work_order_add(dc2, node)
        grid_repair_grid_objects(self.ship, node, dc1)
        self.assertEqual(linked_to(dc2, "work-order"), set())
        self.assertIsNone(W.work_order_get(node))

    def test_a_dockyard_repair_with_no_team_still_closes_it(self):
        from sbs_utils.procedural.internal_damage import grid_repair_grid_objects
        node = self.broken(0)
        dc = self.team(1)
        W.work_order_add(dc, node)
        grid_repair_grid_objects(self.ship, node)          # who_repaired=None
        self.assertEqual(linked_to(dc, "work-order"), set())

    def test_an_unrelated_order_is_left_alone(self):
        from sbs_utils.procedural.internal_damage import grid_repair_grid_objects
        fixed, other = self.broken(0), self.broken(1)
        dc = self.team(2)
        W.work_order_add(dc, fixed)
        W.work_order_add(dc, other)
        grid_repair_grid_objects(self.ship, fixed, dc)
        self.assertEqual(linked_to(dc, "work-order"), {other})


class TestTuningAHealthyNode(WorkOrderBase):
    """green -> cyan. A crew that looks after a system should be able to tune it
    BEFORE anything goes wrong; gating maintenance on `__worn__` made the tuned tier
    reachable only by neglecting a system first, which is backwards."""

    def test_a_nominal_node_accepts_a_maintenance_order(self):
        node = self.healthy(0)
        self.assertEqual(W.work_order_kind_wanted(node), W.KIND_MAINTAIN)

    def test_an_order_on_a_nominal_node_is_NOT_instantly_satisfied(self):
        """The bug: 'satisfied' for maintenance meant 'not worn', so an order on a
        healthy node completed on the first read and was purged before anyone moved."""
        node = self.healthy(0)
        dc = self.team(1)
        W.work_order_add(dc, node, W.KIND_MAINTAIN)
        self.assertFalse(W.work_order_is_satisfied(node))
        self.assertEqual(W.work_orders_for(dc), {node},
                         "a tune order on a healthy node must survive the purge")

    def test_it_is_satisfied_only_once_the_node_is_TUNED(self):
        node = self.healthy(0)
        dc = self.team(1)
        W.work_order_add(dc, node, W.KIND_MAINTAIN)
        set_inventory_value(node, "wear", 0.0)
        self.assertTrue(W.work_order_is_satisfied(node))

    def test_an_already_tuned_node_offers_nothing(self):
        node = self.healthy(0)
        set_inventory_value(node, "wear", 0.0)
        self.assertIsNone(W.work_order_kind_wanted(node),
                          "there is nothing left to do to a tuned node")

    def test_the_brain_can_FIND_a_nominal_node_it_was_sent_to(self):
        """The marker role exists because the brain matches its idle room by role,
        and a nominal node is not `__worn__`."""
        node = self.healthy(0)
        dc = self.team(1)
        W.work_order_add(dc, node, W.KIND_MAINTAIN)
        self.assertTrue(has_role(node, W.MAINTENANCE_ROLE))
        self.assertEqual(W.work_order_best(dc), node)

    def test_the_marker_goes_when_the_order_does(self):
        node = self.healthy(0)
        dc = self.team(1)
        W.work_order_add(dc, node, W.KIND_MAINTAIN)
        W.work_order_cancel(dc, node)
        self.assertFalse(has_role(node, W.MAINTENANCE_ROLE))

    def test_a_bare_link_does_not_carry_the_marker(self):
        """A bare link has always meant a repair, so it must not look like a tune."""
        node = self.broken(0)
        link(self.team(1), "work-order", node)
        self.assertFalse(has_role(node, W.MAINTENANCE_ROLE))
        self.assertEqual(W.work_order_kind(node), W.KIND_REPAIR)


class TestDamagePromotesATuneJob(WorkOrderBase):
    def test_a_node_that_breaks_mid_tune_becomes_a_repair(self):
        from sbs_utils.procedural.internal_damage import grid_damage_grid_object
        node = self.healthy(0)
        dc = self.team(1)
        W.work_order_add(dc, node, W.KIND_MAINTAIN)
        grid_damage_grid_object(self.ship, node, "Crimson")
        self.assertEqual(W.work_order_kind(node), W.KIND_REPAIR)
        self.assertFalse(has_role(node, W.MAINTENANCE_ROLE))

    def test_the_team_is_still_on_it(self):
        from sbs_utils.procedural.internal_damage import grid_damage_grid_object
        node = self.healthy(0)
        dc = self.team(1)
        W.work_order_add(dc, node, W.KIND_MAINTAIN)
        grid_damage_grid_object(self.ship, node, "Crimson")
        self.assertEqual(W.work_orders_for(dc), {node},
                         "the work got more urgent, not irrelevant")

    def test_a_promoted_order_is_not_left_at_the_bottom_of_the_list(self):
        from sbs_utils.procedural.internal_damage import grid_damage_grid_object
        node = self.healthy(0)
        W.work_order_add(self.team(1), node, W.KIND_MAINTAIN)   # LOW
        grid_damage_grid_object(self.ship, node, "Crimson")
        self.assertGreaterEqual(W.work_order_priority(node), W.PRIORITY_NORMAL)


if __name__ == "__main__":
    unittest.main()
