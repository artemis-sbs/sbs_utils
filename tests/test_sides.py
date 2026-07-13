from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.objects import PlayerShip, Npc
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.sides import (
    to_side_id, side_keys_set,
    side_members_set, side_ally_members_set, side_enemy_members_set,
    side_are_allies, side_are_enemies, side_are_neutral, side_are_same_side,
    side_set_relations, side_get_relations,
    side_hostile_members, is_hostile_combatant,
)
import unittest

test_set_exe_dir()


def make_side(key, name):
    """Create a side Agent the same way MAST/prefab code would."""
    side = Agent()
    side.id = get_story_id()
    side.add()
    side.add_role("__side__")
    side.set_inventory_value("side_key", key)
    side.set_inventory_value("side_name", name)
    return side


class TestSides(unittest.TestCase):

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    # ------------------------------------------------------------------
    # to_side_id
    # ------------------------------------------------------------------

    def test_to_side_id_by_key(self):
        tsn = make_side("tsn", "TSN")
        self.assertEqual(to_side_id("tsn"), tsn.id)

    def test_to_side_id_by_key_case_insensitive(self):
        tsn = make_side("tsn", "TSN")
        self.assertEqual(to_side_id("TSN"), tsn.id)

    def test_to_side_id_by_display_name(self):
        pirates = make_side("pirate", "Pirates")
        self.assertEqual(to_side_id("Pirates"), pirates.id)

    def test_to_side_id_by_agent_id(self):
        tsn = make_side("tsn", "TSN")
        self.assertEqual(to_side_id(tsn.id), tsn.id)

    def test_to_side_id_unknown_returns_none(self):
        self.assertIsNone(to_side_id("no_such_side_xyz"))

    # ------------------------------------------------------------------
    # side_keys_set
    # ------------------------------------------------------------------

    def test_side_keys_set(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        keys = side_keys_set()
        self.assertIn("tsn", keys)
        self.assertIn("pirate", keys)
        self.assertEqual(len(keys), 2)

    # ------------------------------------------------------------------
    # Relationship setting and querying
    # ------------------------------------------------------------------

    def test_allied_relations(self):
        make_side("tsn", "TSN")
        make_side("uspf", "USPF")
        side_set_relations("tsn", "uspf", sbs.DIPLOMACY.ALLIED)
        self.assertTrue(side_are_allies("tsn", "uspf"))
        self.assertTrue(side_are_allies("uspf", "tsn"))  # bidirectional
        self.assertFalse(side_are_enemies("tsn", "uspf"))
        self.assertFalse(side_are_neutral("tsn", "uspf"))

    def test_hostile_relations(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        self.assertTrue(side_are_enemies("tsn", "pirate"))
        self.assertTrue(side_are_enemies("pirate", "tsn"))  # bidirectional
        self.assertFalse(side_are_allies("tsn", "pirate"))
        self.assertFalse(side_are_neutral("tsn", "pirate"))

    def test_neutral_relations(self):
        make_side("tsn", "TSN")
        make_side("alien", "Aliens")
        side_set_relations("tsn", "alien", sbs.DIPLOMACY.NEUTRAL)
        self.assertTrue(side_are_neutral("tsn", "alien"))
        self.assertTrue(side_are_neutral("alien", "tsn"))  # bidirectional
        self.assertFalse(side_are_allies("tsn", "alien"))
        self.assertFalse(side_are_enemies("tsn", "alien"))

    def test_change_relations_clears_old(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        self.assertTrue(side_are_enemies("tsn", "pirate"))
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.ALLIED)
        self.assertTrue(side_are_allies("tsn", "pirate"))
        self.assertFalse(side_are_enemies("tsn", "pirate"))  # old link gone

    def test_get_relations_allied(self):
        make_side("tsn", "TSN")
        make_side("uspf", "USPF")
        side_set_relations("tsn", "uspf", sbs.DIPLOMACY.ALLIED)
        self.assertEqual(side_get_relations("tsn", "uspf"), sbs.DIPLOMACY.ALLIED)

    def test_get_relations_hostile(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        self.assertEqual(side_get_relations("tsn", "pirate"), sbs.DIPLOMACY.HOSTILE)

    def test_get_relations_unknown_when_unset(self):
        make_side("tsn", "TSN")
        make_side("alien", "Aliens")
        # No relation set — should return UNKNOWN
        self.assertEqual(side_get_relations("tsn", "alien"), sbs.DIPLOMACY.UNKNOWN)

    def test_same_side(self):
        tsn = make_side("tsn", "TSN")
        self.assertTrue(side_are_same_side("tsn", "tsn"))
        self.assertTrue(side_are_same_side(tsn.id, "tsn"))

    def test_different_sides_not_same(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        self.assertFalse(side_are_same_side("tsn", "pirate"))

    # ------------------------------------------------------------------
    # side_members_set
    # ------------------------------------------------------------------

    def test_side_members_set(self):
        make_side("tsn", "TSN")
        ship1 = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        ship2 = PlayerShip().spawn(0, 0, 0, "Hera", "tsn", "tsn_battle_cruiser").py_object
        members = side_members_set("tsn")
        self.assertIn(ship1.id, members)
        self.assertIn(ship2.id, members)

    def test_side_members_excludes_other_sides(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        tsn_members = side_members_set("tsn")
        self.assertIn(tsn_ship.id, tsn_members)
        self.assertNotIn(pirate_ship.id, tsn_members)

    # ------------------------------------------------------------------
    # side_ally_members_set / side_enemy_members_set
    # ------------------------------------------------------------------

    def test_ally_members_set(self):
        make_side("tsn", "TSN")
        make_side("uspf", "USPF")
        make_side("pirate", "Pirates")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        uspf_ship = Npc().spawn(0, 0, 0, "DS1", "uspf", "starbase_command", "behav_spaceport").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        side_set_relations("tsn", "uspf", sbs.DIPLOMACY.ALLIED)
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        allies = side_ally_members_set("tsn")
        self.assertIn(uspf_ship.id, allies)
        self.assertNotIn(tsn_ship.id, allies)   # own side not in ally set
        self.assertNotIn(pirate_ship.id, allies)

    def test_enemy_members_set(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        enemies = side_enemy_members_set("tsn")
        self.assertIn(pirate_ship.id, enemies)
        self.assertNotIn(tsn_ship.id, enemies)

    # ------------------------------------------------------------------
    # side_hostile_members / is_hostile_combatant  (raider-migration source of truth)
    # ------------------------------------------------------------------

    def _hostile_setup(self):
        """tsn (player), pirate (hostile, raider-tagged), civ (neutral, raider-tagged).
        Returns (tsn_ship, pirate_ship, civ_ship)."""
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        make_side("civ", "Civ")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        civ_ship = Npc().spawn(0, 0, 0, "Trader", "civ", "Light Cruiser", "behav_npcship").py_object
        # Both foe and neutral carry the combat "raider" tag (the overloaded marker).
        pirate_ship.add_role("raider")
        civ_ship.add_role("raider")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        side_set_relations("tsn", "civ", sbs.DIPLOMACY.NEUTRAL)
        return tsn_ship, pirate_ship, civ_ship

    def test_side_hostile_members_scoped_excludes_neutral(self):
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        foes = side_hostile_members("tsn", "raider")
        self.assertIn(pirate_ship.id, foes)       # hostile + raider-tagged
        self.assertNotIn(civ_ship.id, foes)       # neutral (ceasefire analogue) drops out
        self.assertNotIn(tsn_ship.id, foes)       # own side

    def test_side_hostile_members_scope_respects_role_removal(self):
        # A surrendered/defected ship drops the raider role -> leaves the scoped set
        # even though its side is still diplomatically hostile.
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        pirate_ship.remove_role("raider")
        self.assertNotIn(pirate_ship.id, side_hostile_members("tsn", "raider"))
        # ...but without the scope it is still a hostile-side member.
        self.assertIn(pirate_ship.id, side_hostile_members("tsn"))

    def test_is_hostile_combatant(self):
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        self.assertTrue(is_hostile_combatant("tsn", pirate_ship))    # hostile + raider
        self.assertFalse(is_hostile_combatant("tsn", civ_ship))      # neutral
        # Surrender/defection removes the role -> no longer a combatant.
        pirate_ship.remove_role("raider")
        self.assertFalse(is_hostile_combatant("tsn", pirate_ship))
        # Pure diplomacy test (scope_role=None) ignores the role.
        self.assertTrue(is_hostile_combatant("tsn", pirate_ship, scope_role=None))


if __name__ == '__main__':
    unittest.main()
