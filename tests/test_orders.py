"""orders - who can be given which orders, decided by what the object can do.

Capabilities are derived from the spawn behavior, the hull's weapons and turret mounts,
then overridden per object. An order label says what it `requires:` and what it is
`valid_for:`. The comms chip, the popup and drag all ask this module, so a station with
nothing it can carry out is no longer "orderable".

Order labels are faked here (anything with get_inventory_value), because
labels_get_type needs a live story page - which is why orders_available takes `labels=`.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.sides import side_ensure, side_set_relations
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.procedural import orders as O
from sbs_utils.procedural import turret as tr


class _Label:
    def __init__(self, name, type="objective/orders/defender", **meta):
        self.name = name
        self.meta = dict(meta, type=type)

    def get_inventory_value(self, key, default=None):
        return self.meta.get(key, default)

    def __repr__(self):
        return self.name


GOTO = _Label("goto", requires="move", valid_for="any")
ATTACK = _Label("attack", requires="move, weapons", valid_for="hostile")
GUARD = _Label("guard", requires="move", valid_for="allies, marker")
STOP = _Label("stop", requires="move", valid_for="self")
FIRE_AT = _Label("fire_at", requires="weapons", valid_for="hostile")
HOLD = _Label("hold_fire", requires="weapons", valid_for="self")
LAUNCH = _Label("launch", requires="launch", valid_for="hostile")
ESCORT = _Label("escort_only", type="objective/orders/escort/follow", requires="move", valid_for="allies")
ALL = [GOTO, ATTACK, GUARD, STOP, FIRE_AT, HOLD, LAUNCH, ESCORT]


def names(labels):
    return sorted(l.name for l in labels)


class OrdersBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        tsn = side_ensure("tsn", "TSN")
        raider = side_ensure("raider", "Raider")
        side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)
        self.hero = to_id(player_spawn(0, 0, 0, "Hero", "tsn", "tsn_light_cruiser"))
        self.cruiser = to_id(npc_spawn(1000, 0, 0, "Valiant", "tsn", "tsn_light_cruiser", "behav_npcship"))
        self.freighter = to_id(npc_spawn(1500, 0, 0, "Mule", "tsn", "transport_ship", "behav_npcship"))
        self.base = to_id(npc_spawn(2000, 0, 0, "DS 1", "tsn,station", "starbase_command", "behav_station"))
        self.foe = to_id(npc_spawn(3000, 0, 0, "Raider", "raider", "tsn_light_cruiser", "behav_npcship"))
        O._providers.clear()

    def tearDown(self):
        O._providers.clear()


class TestCapabilities(OrdersBase):

    def test_an_armed_ship_moves_and_fights(self):
        self.assertEqual({"move", "weapons"}, O.orders_caps(self.cruiser))

    def test_an_unarmed_ship_only_moves(self):
        self.assertEqual({"move"}, O.orders_caps(self.freighter))

    def test_A_STOCK_STATION_CAN_DO_NOTHING(self):
        """starbase_command HAS beams in ship data - but a behav_station on a stock hull
        never fires (engine-measured), so it is not counted as armed."""
        self.assertEqual(set(), O.orders_caps(self.base))

    def test_a_turret_has_weapons_and_no_move(self):
        tr.turret_make(self.base, range=2000)
        self.assertEqual({"weapons"}, O.orders_caps(self.base))

    def test_a_station_with_turret_mounts_has_weapons(self):
        from sbs_utils.procedural.mount import mount_spawn
        m = mount_spawn(self.base, "starbase_command", name="Mount", side="tsn")
        tr.turret_make(m, range=1000)
        self.assertEqual({"weapons"}, O.orders_caps(self.base))
        self.assertEqual([to_id(m)], O.orders_mounted_turrets(self.base))

    def test_a_provider_adds_a_capability(self):
        O.orders_caps_provider(lambda oid: ["launch"] if oid == self.base else [])
        self.assertEqual({"launch"}, O.orders_caps(self.base))
        self.assertEqual({"move"}, O.orders_caps(self.freighter))

    def test_a_broken_provider_adds_nothing(self):
        def boom(oid):
            raise RuntimeError("no")
        O.orders_caps_provider(boom)
        self.assertEqual({"move"}, O.orders_caps(self.freighter))

    def test_overrides_add_and_remove(self):
        O.orders_caps_set(self.cruiser, remove="weapons")
        self.assertEqual({"move"}, O.orders_caps(self.cruiser))
        O.orders_caps_set(self.base, add="weapons, launch")
        self.assertEqual({"weapons", "launch"}, O.orders_caps(self.base))
        O.orders_caps_set(self.cruiser, remove="")
        self.assertEqual({"move", "weapons"}, O.orders_caps(self.cruiser))

    def test_a_missing_object_has_nothing(self):
        self.assertEqual(set(), O.orders_caps(0))


class TestWhoMayBeCommanded(OrdersBase):

    def test_own_side_npcs(self):
        self.assertTrue(O.orders_may_command(self.hero, self.cruiser))

    def test_not_the_enemy(self):
        self.assertFalse(O.orders_may_command(self.hero, self.foe))

    def test_a_captured_prize_takes_orders(self):
        add_role(self.foe, O.ORDERS_DEFENDER_ROLE)
        self.assertTrue(O.orders_may_command(self.hero, self.foe))

    def test_no_orders_blocks_everything(self):
        add_role(self.cruiser, O.ORDERS_BLOCK_ROLE)
        self.assertFalse(O.orders_may_command(self.hero, self.cruiser))
        self.assertEqual([], O.orders_available(self.hero, self.cruiser, self.foe, labels=ALL))

    def test_not_a_player_ship(self):
        other = to_id(player_spawn(0, 0, 500, "Other", "tsn", "tsn_light_cruiser"))
        self.assertFalse(O.orders_may_command(self.hero, other))


class TestAvailable(OrdersBase):

    def avail(self, who, target=None):
        return names(O.orders_available(self.hero, who, target, labels=ALL))

    def test_a_cruiser_on_an_enemy(self):
        self.assertEqual(["attack", "fire_at", "goto"], self.avail(self.cruiser, self.foe))

    def test_a_cruiser_on_an_ally(self):
        self.assertEqual(["escort_only", "goto", "guard"], self.avail(self.cruiser, self.freighter))

    def test_orders_to_itself(self):
        self.assertEqual(["hold_fire", "stop"], self.avail(self.cruiser))
        self.assertEqual(["hold_fire", "stop"], self.avail(self.cruiser, self.cruiser))

    def test_AN_EMPTY_POINT_TAKES_ONLY_ANY_ORDERS(self):
        self.assertEqual(["goto"], names(O.orders_available(self.hero, self.cruiser, None, labels=ALL, at_point=True)))

    def test_an_unarmed_ship_is_never_offered_attack(self):
        self.assertEqual(["goto"], self.avail(self.freighter, self.foe))

    def test_a_marker_target(self):
        from sbs_utils.procedural.markers import marker_object
        m = marker_object(500, 0, 500, "Alpha")
        self.assertEqual(["goto", "guard"], self.avail(self.cruiser, m))

    def test_A_TURRET_STATION_GETS_ONLY_WEAPON_ORDERS(self):
        tr.turret_make(self.base, range=2000)
        self.assertEqual(["fire_at"], self.avail(self.base, self.foe))
        self.assertEqual(["hold_fire"], self.avail(self.base))

    def test_give_orders_type_narrows_the_set(self):
        set_inventory_value(self.cruiser, "give_orders_type", "objective/orders/escort")
        self.assertEqual(["escort_only"], self.avail(self.cruiser, self.freighter))


class TestCanTake(OrdersBase):

    def can(self, who):
        return O.orders_can_take(self.hero, who, labels=ALL)

    def test_A_STOCK_STATION_CANNOT_BE_ORDERED(self):
        self.assertFalse(self.can(self.base))

    def test_an_armed_station_can(self):
        tr.turret_make(self.base, range=2000)
        self.assertTrue(self.can(self.base))

    def test_a_station_that_launches_can(self):
        O.orders_caps_provider(lambda oid: ["launch"] if oid == self.base else [])
        self.assertTrue(self.can(self.base))

    def test_ships_can(self):
        self.assertTrue(self.can(self.cruiser))
        self.assertTrue(self.can(self.freighter))

    def test_the_enemy_cannot(self):
        self.assertFalse(self.can(self.foe))


class TestStance(OrdersBase):

    def test_the_default_is_weapons_free(self):
        self.assertEqual("free", O.orders_stance(self.cruiser))

    def test_hold_and_release(self):
        self.assertEqual("hold", O.orders_stance_set(self.cruiser, "hold"))
        self.assertTrue(O.orders_holding_fire(self.cruiser))
        O.orders_stance_set(self.cruiser, "free")
        self.assertFalse(O.orders_holding_fire(self.cruiser))

    def test_a_bad_stance_changes_nothing(self):
        self.assertIsNone(O.orders_stance_set(self.cruiser, "berserk"))
        self.assertEqual("free", O.orders_stance(self.cruiser))

    def test_a_host_passes_the_stance_to_its_mounts(self):
        from sbs_utils.procedural.mount import mount_spawn
        m = to_id(mount_spawn(self.base, "starbase_command", name="Mount", side="tsn"))
        tr.turret_make(m, range=1000)
        O.orders_stance_set(self.base, "hold")
        self.assertTrue(O.orders_holding_fire(m))

    def test_HOLD_FIRE_STOPS_A_TURRET_CHOOSING_ITS_OWN_TARGET(self):
        tr.turret_make(self.base, range=5000)
        self.assertEqual(self.foe, tr.turret_acquire(self.base))
        O.orders_stance_set(self.base, "hold")
        self.assertIsNone(tr.turret_acquire(self.base))

    def test_but_a_designated_target_still_stands(self):
        tr.turret_make(self.base, range=5000)
        O.orders_stance_set(self.base, "hold")
        tr.turret_designate(self.base, self.foe)
        self.assertEqual(self.foe, tr.turret_acquire(self.base))


if __name__ == "__main__":
    unittest.main()
