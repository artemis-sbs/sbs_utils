import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.roles import role_matches, roles_matching
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.query import to_id


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


class TestRoleExpr(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        # A tsn PLAYER ship and a raider NPC.
        self.tp = to_id(npc_spawn(0, 0, 0, "TP", "tsn,__player__", "tsn_light_cruiser", "behav_npcship"))
        self.rn = to_id(npc_spawn(0, 0, 1000, "RN", "raider,__npc__", "arvonian_destroyer", "behav_npcship"))

    def test_atoms(self):
        self.assertTrue(role_matches(self.tp, "__player__"))
        self.assertTrue(role_matches(self.tp, "tsn"))
        self.assertFalse(role_matches(self.tp, "raider"))
        self.assertFalse(role_matches(self.tp, "no_such_role"))

    def test_or(self):
        self.assertTrue(role_matches(self.tp, "raider | tsn"))
        self.assertTrue(role_matches(self.rn, "raider | tsn"))
        self.assertFalse(role_matches(self.tp, "raider | kralien"))

    def test_and(self):
        self.assertTrue(role_matches(self.tp, "tsn & __player__"))
        self.assertFalse(role_matches(self.tp, "tsn & raider"))
        self.assertFalse(role_matches(self.rn, "raider & __player__"))  # raider is an npc

    def test_not_and_minus(self):
        self.assertTrue(role_matches(self.tp, "!raider"))
        self.assertFalse(role_matches(self.tp, "!tsn"))
        self.assertTrue(role_matches(self.tp, "__player__ - raider"))   # player and not raider
        self.assertFalse(role_matches(self.tp, "__player__ - tsn"))     # it IS tsn -> false

    def test_precedence_and_parens(self):
        # & binds tighter than | : (tsn & __player__) | raider  -> tp matches via left group
        self.assertTrue(role_matches(self.tp, "tsn & __player__ | raider"))
        self.assertTrue(role_matches(self.rn, "tsn & __player__ | raider"))  # via the raider term
        # grouping changes meaning
        self.assertTrue(role_matches(self.tp, "(raider | tsn) & __player__"))
        self.assertFalse(role_matches(self.rn, "(raider | tsn) & __player__"))  # rn is not a player

    def test_empty(self):
        self.assertFalse(role_matches(self.tp, ""))
        self.assertFalse(role_matches(self.tp, None))

    def test_roles_matching_set(self):
        s = roles_matching("tsn | raider")
        self.assertIn(self.tp, s)
        self.assertIn(self.rn, s)
        players = roles_matching("__player__")
        self.assertIn(self.tp, players)
        self.assertNotIn(self.rn, players)
        # negation over the universe
        not_tsn = roles_matching("!tsn")
        self.assertIn(self.rn, not_tsn)
        self.assertNotIn(self.tp, not_tsn)


if __name__ == "__main__":
    unittest.main()
