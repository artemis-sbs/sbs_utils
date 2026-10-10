"""What a shot does on a tile map (procedural/boarding_combat.py `boarding_tile_fire`).

THE RULE: a shot never removes a prop. STUN does nothing to one. CUT or FULL opens a shut
prop whose `Opens with:` lists ``cut`` - and that is all either does to a thing. A hostile
is shot as ever; somebody CALM is not harmed; and a shot at a cell holding a hostile and
a pickup hits the hostile.

Driven by the crew member's own click (`boarding_arm`, then `boarding_tile_click`).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural.boarding_site import boarding_arm, boarding_setting_text
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

SHOT_CID = 0x8000000000000041

SHOT_AREA = """area: yard
title: The Yard
tileset: g
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
---
############
#..........#
#.P........#
#..........#
############
"""

SHOT_KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}


def _shot_prop(key, at, **data):
    data.update({"area": "yard", "at": at, "sprite": "g:rock"})
    return {"key": key, "display_text": key.title(), "description": "A thing.", "data": data}


SHOT_PROPS = {"children": [
    # The lessons' four: a terminal with the endings, a beacon, a door only a signal
    # opens, a door a key opens - none of them lists `cut`.
    _shot_prop("terminal", "4, 1", scene="endings", blocks="yes"),
    _shot_prop("beacon", "5, 1", scene="relight", blocks="yes"),
    _shot_prop("lift_gate", "6, 1", opens_with="signal lift_running", blocks="yes"),
    _shot_prop("yard_gate", "7, 1", opens_with="key yard_key", blocks="yes"),
    # One that lists it.
    _shot_prop("hatch", "8, 1", opens_with="key hatch_key, cut", blocks="yes"),
    # Scenery, and a pickup lying where somebody will stand.
    {"key": "bunk", "display_text": "Bunk", "description": "",
     "data": {"area": "yard", "at": "9, 1", "sprite": "g:rock", "blocks": "yes"}},
    {"key": "cell", "display_text": "Cell", "description": "",
     "data": {"area": "yard", "at": "6, 3", "sprite": "g:dirt", "item": "power_cell"}},
]}

SHOT_PEOPLE = {"children": [
    {"key": "brakk", "display_text": "Brakk", "description": "",
     "data": {"area": "yard", "at": "6, 3", "sprite": "g:rock", "hp": "3", "notice": "0",
              "drops": "fuse"}},
    {"key": "oduya", "display_text": "Oduya", "description": "",
     "data": {"area": "yard", "at": "8, 3", "sprite": "g:rock", "hp": "2", "calm": "yes",
              "drops": "ledger"}},
    {"key": "sentry", "display_text": "Sentry", "description": "",
     "data": {"area": "yard", "at": "10, 3", "sprite": "g:rock", "hp": "3", "notice": "0",
              "drops": "power_cell"}},
]}


class ShotBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        SpaceObject.clear()
        clear_shared()
        for clear in (A.boarding_clear, T.tilemap_clear, BT.boarding_tile_clear,
                      P.boarding_props_clear, C.boarding_checks_clear,
                      K.boarding_combat_clear):
            clear()
            self.addCleanup(clear)
        T.tilemap_tileset("g", SHOT_KINDS)
        T.tilemap_load(SHOT_AREA)
        T._WATCH["task"] = object()
        K._WATCH["task"] = object()
        T.tilemap_set_clock(0.0)
        A.boarding_metric_install()
        P.boarding_props_install()
        K.boarding_combat_install()
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Yard", area="yard")
        GuiClient(SHOT_CID)
        body = lifeform_spawn("Kovac", "", "boarding,security")
        set_inventory_value(body.id, A.JOBS_KEY, ["security"])
        A.boarding_assign(SHOT_CID, body.id)
        self.body = body.id
        P.boarding_props_declare(SHOT_PROPS)
        P.boarding_props_place()
        K.boarding_hostiles_declare(SHOT_PEOPLE)
        K.boarding_hostiles_place()
        G.boarding_go_down(SHOT_CID)
        self.seen = []
        signal_observe(self._obs)
        self.addCleanup(signal_unobserve, self._obs)

    def _obs(self, name, data):
        self.seen.append((name, dict(data) if isinstance(data, dict) else data))

    def shoot(self, setting, x, y, stand=None):
        T.tilemap_place(self.body, "yard", *(stand or (x, 2)))
        boarding_arm(SHOT_CID, setting)
        hit = BT.boarding_tile_click(SHOT_CID, "yard", x, y)
        return hit, [d for n, d in self.seen if n == "xess_fired"][-1]

    def aboard(self, key):
        rec = P.boarding_prop(key)
        return rec is not None and rec["id"] is not None \
            and T.tilemap_where(rec["id"]) is not None


class AShotNeverRemovesAPropTests(ShotBase):

    def test_FULL_leaves_every_prop_that_does_not_list_cut(self):
        for key, x in (("terminal", 4), ("beacon", 5), ("lift_gate", 6), ("yard_gate", 7),
                       ("bunk", 9)):
            with self.subTest(prop=key):
                hit, fired = self.shoot("full", x, 1)
                self.assertTrue(self.aboard(key), "a FULL shot removed it")
                self.assertEqual(fired["XESS_HIT"], key)
                self.assertEqual(fired["XESS_EFFECT"], "scorched")
                self.assertFalse(fired["XESS_DESTROYED"])
                self.assertFalse(T.tilemap_is_open("yard", x, 1), "it no longer blocks")
        # The doors are still shut: FULL is not a key and not a signal.
        self.assertFalse(P.boarding_prop_is_open("lift_gate"))
        self.assertFalse(P.boarding_prop_is_open("yard_gate"))

    def test_FULL_leaves_a_pickup_lying_there(self):
        K.boarding_hostile_remove("brakk")
        hit, fired = self.shoot("full", 6, 3, stand=(6, 2))
        self.assertTrue(self.aboard("cell"))
        self.assertFalse(P.boarding_prop("cell")["taken"])
        self.assertFalse(fired["XESS_DESTROYED"])

    def test_CUT_and_STUN_leave_them_too(self):
        for setting, effect in (("cut", "scorched"), ("stun", "nothing")):
            hit, fired = self.shoot(setting, 4, 1)
            self.assertTrue(self.aboard("terminal"))
            self.assertEqual(fired["XESS_EFFECT"], effect)
            self.assertFalse(fired["XESS_DESTROYED"])

    def test_a_prop_that_lists_cut_is_OPENED_by_CUT_and_by_FULL_and_stays(self):
        for setting in ("cut", "full"):
            with self.subTest(setting=setting):
                P.boarding_prop("hatch")["open"] = False
                T.tilemap_place(P.boarding_prop("hatch")["id"], "yard", 8, 1, blocks=True)
                hit, fired = self.shoot(setting, 8, 1)
                self.assertTrue(hit)
                self.assertEqual(fired["XESS_EFFECT"], "opened")
                self.assertTrue(P.boarding_prop_is_open("hatch"))
                self.assertTrue(self.aboard("hatch"), "opened, not removed")
                self.assertFalse(fired["XESS_DESTROYED"])

    def test_an_OPEN_one_is_not_removed_by_a_second_shot(self):
        self.shoot("cut", 8, 1)
        hit, fired = self.shoot("full", 8, 1)
        self.assertTrue(self.aboard("hatch"))
        self.assertTrue(P.boarding_prop_is_open("hatch"))
        self.assertEqual(fired["XESS_EFFECT"], "scorched")

    def test_STUN_does_not_open_it(self):
        hit, fired = self.shoot("stun", 8, 1)
        self.assertFalse(P.boarding_prop_is_open("hatch"))
        self.assertEqual(fired["XESS_EFFECT"], "nothing")

    def test_the_fire_app_does_not_promise_to_destroy_things(self):
        text = boarding_setting_text("full")
        self.assertNotIn("whatever that is", text)
        self.assertNotIn("Destroys", text)
        self.assertTrue(text.isascii())


class PeopleTests(ShotBase):

    def test_a_hostile_on_a_pickups_cell_is_the_one_hit(self):
        """`agent_c3d_report.md` defect 2: the pickup went and the hostile stood."""
        hit, fired = self.shoot("full", 6, 3, stand=(6, 2))
        self.assertTrue(hit)
        self.assertEqual(fired["XESS_HIT"], "brakk")
        self.assertEqual(K.boarding_hostile_state("brakk"), "down")
        self.assertTrue(self.aboard("cell"), "the pickup under her is still there")
        self.assertTrue(fired["XESS_DESTROYED"])

    def test_a_hostile_is_shot_as_ever(self):
        hit, fired = self.shoot("cut", 10, 3, stand=(10, 2))
        self.assertEqual(fired["XESS_EFFECT"], "wounded")
        self.assertEqual(K.boarding_hostile("sentry")["hp_left"], 2)
        hit, fired = self.shoot("stun", 10, 3, stand=(10, 2))
        self.assertEqual(fired["XESS_EFFECT"], "stunned")
        hit, fired = self.shoot("full", 10, 3, stand=(10, 2))
        self.assertEqual(fired["XESS_EFFECT"], "down")
        self.assertIn("hostile_down_sentry", [n for n, _ in self.seen])
        self.assertIsNotNone(P.boarding_prop("drop_sentry_0"))

    def test_somebody_CALM_is_not_harmed_by_any_setting(self):
        for setting in ("stun", "cut", "full"):
            with self.subTest(setting=setting):
                hit, fired = self.shoot(setting, 8, 3, stand=(8, 2))
                rec = K.boarding_hostile("oduya")
                self.assertFalse(hit)
                self.assertEqual(rec["state"], "calm")
                self.assertEqual(rec["hp_left"], 2)
                self.assertEqual(rec["stunned_until"], 0.0)
                self.assertIsNotNone(rec["id"])
                self.assertEqual(fired["XESS_HIT"], "oduya")
                self.assertEqual(fired["XESS_REASON"], "calm")
                self.assertFalse(fired["XESS_DESTROYED"])
        self.assertIsNone(P.boarding_prop("drop_oduya_0"))
        self.assertNotIn("hostile_down_oduya", [n for n, _ in self.seen])

    def test_somebody_CALMED_by_an_answer_is_not_harmed_either(self):
        """`agent_c3c_report.md`: FULL killed a calmed sentry and it dropped its cell."""
        K.boarding_hostile_calm("sentry")
        hit, fired = self.shoot("full", 10, 3, stand=(10, 2))
        self.assertEqual(K.boarding_hostile_state("sentry"), "calm")
        self.assertIsNone(P.boarding_prop("drop_sentry_0"))
        # Set off again, they can be shot again.
        K.boarding_hostile_calm("sentry", False)
        hit, fired = self.shoot("full", 10, 3, stand=(10, 2))
        self.assertEqual(K.boarding_hostile_state("sentry"), "down")

    def test_fire_from_orbit_leaves_the_calm_standing(self):
        down = K.boarding_strike("yard", 8, 3, radius=3)
        self.assertEqual(sorted(down), ["brakk", "sentry"])
        self.assertEqual(K.boarding_hostile_state("oduya"), "calm")
        self.assertEqual(K.boarding_hostile("oduya")["hp_left"], 2)
        for key in ("terminal", "beacon", "hatch", "cell"):
            self.assertTrue(self.aboard(key))


if __name__ == "__main__":
    unittest.main()
