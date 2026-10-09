"""A tile site REMEMBERS: which doors were opened, what was picked up, who is down.

Two state providers, each with the module that owns the state:

    boarding_props      {"opened": [keys], "taken": [keys]}
    boarding_hostiles   {"down": [keys]}

A saved game is handed back before the site it describes has been declared - the ground is
loaded when the crew arrives - so a restore fills a ledger, and a prop or a person reads it
as it is DECLARED and again as it is PLACED. What this file pins:

* open a door with its key, pick a thing up, put somebody down; snapshot; a mission reset;
  restore; declare and place the same ground: the door is open and can be walked through,
  the thing is not there, the person is not there;
* restored state is not news: no `boarding_prop_opened`, no `hostile_down_<key>` quest
  signal, nothing handed out twice, nothing dropped again;
* a restore that arrives AFTER the ground was declared is still applied when it is placed;
* a site not visited tonight keeps what the save said about it;
* a mission that never saves is on no ledger for it.

Unit tests only: no tile site is reachable from a saving mission yet.

    python -m unittest tests.test_boarding_saved_state
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import persistence as S
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

CID = 0x8000000000000031

AREA = """area: yard
title: The Yard
tileset: g
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
  D: dirt @door
---
############
#..........#
#.P........#
#..........#
#######D####
#..........#
#..........#
############
"""

KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

PROPS = {"children": [
    {"key": "door", "display_text": "Yard gate", "description": "A rusted gate.",
     "data": {"area": "yard", "at": "door", "sprite": "g:rock", "open_sprite": "g:dirt",
              "opens_with": "key gate_key", "blocks": "yes"}},
    {"key": "coil", "display_text": "Coil", "description": "",
     "data": {"area": "yard", "at": "9, 6", "sprite": "g:dirt", "item": "coil"}},
    {"key": "crate", "display_text": "Crate", "description": "Stencilled STILLWATER.",
     "data": {"area": "yard", "at": "5, 2", "sprite": "g:rock", "blocks": "yes"}},
]}

HOSTILES = {"children": [
    {"key": "glassback", "display_text": "Glassback", "description": "",
     "data": {"area": "yard", "at": "9, 2", "sprite": "g:rock", "hp": "2",
              "drops": "venom"}},
    {"key": "warden", "display_text": "Warden", "description": "",
     "data": {"area": "yard", "at": "3, 3", "sprite": "g:rock", "calm": "yes"}},
    {"key": "stray", "display_text": "Stray", "description": "",
     "data": {"area": "yard", "at": "5, 5", "sprite": "g:rock"}},
]}


class _Base(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.launch()
        self.addCleanup(reset_mission_state)
        self.addCleanup(signal_unobserve, self._obs)

    def _obs(self, name, data):
        self.seen.append((name, dict(data) if isinstance(data, dict) else data))

    def launch(self):
        """A new process as far as the library can tell, with the ground's art loaded
        and one engineer aboard - and NOTHING declared yet."""
        signal_unobserve(self._obs)
        reset_mock(sbs)
        del self.seen[:]
        signal_observe(self._obs)
        T.tilemap_tileset("g", KINDS)
        T.tilemap_load(AREA)
        T._WATCH["task"] = object()         # no tick task in a unit test
        K._WATCH["task"] = object()
        A.boarding_metric_install()
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Yard", area="yard")
        GuiClient(CID)
        self.body = lifeform_spawn("Kovac", "", "boarding,engineering").id
        set_inventory_value(self.body, A.JOBS_KEY, ["engineering"])
        A.boarding_assign(CID, self.body)

    def arrive(self):
        """The crew reaches the site: its ground is declared and placed."""
        P.boarding_props_declare(PROPS)
        P.boarding_props_place()
        K.boarding_hostiles_declare(HOSTILES)
        K.boarding_hostiles_place()

    def play_the_site(self):
        P.boarding_give(self.body, "gate_key")
        T.tilemap_place(self.body, "yard", 7, 3)
        self.assertEqual(P.boarding_interact(CID, "door")[0], "opened")
        T.tilemap_place(self.body, "yard", 9, 5)
        self.assertEqual(P.boarding_interact(CID, "coil")[0], "picked")
        self.assertEqual(K._hostile_hit(K.boarding_hostile("glassback"), "full"), "down")
        self.assertTrue(K.boarding_hostile_dismiss("warden"))

    def names(self):
        return [name for name, _data in self.seen]


class WhatIsWrittenDown(_Base):
    def test_an_untouched_site_writes_nothing(self):
        self.arrive()
        self.assertEqual(S.persist_providers_snapshot(), {})
        self.assertEqual(P.boarding_props_saved_count(), 0)
        self.assertEqual(K.boarding_hostiles_saved_count(), 0)

    def test_what_was_done_is_written_by_key(self):
        self.arrive()
        self.play_the_site()
        self.assertTrue(S.persist_providers_dirty(), "a change asks to be saved")
        saved = S.persist_providers_snapshot()
        # `drop_glassback_0` is what the glassback dropped; nobody picked it up.
        self.assertEqual(saved["boarding_props"], {"opened": ["door"], "taken": ["coil"]})
        self.assertEqual(saved["boarding_hostiles"], {"down": ["glassback", "warden"]})

    def test_a_door_with_no_lock_is_not_a_door_that_was_opened(self):
        """The crate and the coil have no `Opens with:`; they are `open` by nature and
        must not be written down as opened."""
        self.arrive()
        self.assertEqual(S.persist_providers_snapshot(), {})


class Continue(_Base):
    def stop_and_continue(self):
        self.arrive()
        self.play_the_site()
        saved = S.persist_providers_snapshot()
        self.launch()
        self.assertEqual(S.persist_providers_snapshot(), {}, "a reset forgets")
        S.persist_providers_restore(saved)
        return saved

    def test_the_site_is_as_it_was_left(self):
        self.stop_and_continue()
        self.assertEqual(P.boarding_props(), [], "a restore declares nothing")
        self.arrive()
        self.assertTrue(P.boarding_prop_is_open("door"))
        self.assertTrue(T.tilemap_is_open("yard", 7, 4), "the open door can be walked")
        self.assertIsNone(P.boarding_prop("coil")["id"], "what was taken is not there")
        self.assertIsNone(P.boarding_prop_at("yard", 9, 6))
        self.assertIsNotNone(P.boarding_prop("crate")["id"], "the crate still is")
        self.assertEqual(K.boarding_hostile_state("glassback"), "down")
        self.assertEqual(K.boarding_hostile_state("warden"), "down")
        self.assertIsNone(K.boarding_hostile("glassback")["id"])
        self.assertEqual(K.boarding_hostiles("yard"), ["stray"], "the third is still up")

    def test_restored_state_is_not_news(self):
        self.stop_and_continue()
        self.arrive()
        for name in ("boarding_prop_opened", "boarding_interacted", "boarding_hostile_down",
                     "hostile_down_glassback", "quest_signal"):
            self.assertNotIn(name, self.names(), name)
        self.assertEqual(P.boarding_holding(self.body, "coil"), 0, "nothing is handed out twice")
        self.assertIsNone(P.boarding_prop("drop_glassback_0"), "and nothing is dropped again")

    def test_a_restore_after_the_ground_was_declared_is_applied_when_it_is_placed(self):
        saved = self.stop_and_continue()
        S.persist_providers_restore({})         # ...as if the save had come late
        P.boarding_props_declare(PROPS)
        K.boarding_hostiles_declare(HOSTILES)
        self.assertFalse(P.boarding_prop_is_open("door"))
        S.persist_providers_restore(saved)
        P.boarding_props_place()
        K.boarding_hostiles_place()
        self.assertTrue(P.boarding_prop_is_open("door"))
        self.assertIsNone(P.boarding_prop("coil")["id"])
        self.assertEqual(K.boarding_hostiles("yard"), ["stray"])

    def test_a_second_save_is_the_same_save(self):
        saved = self.stop_and_continue()
        self.arrive()
        self.assertEqual(S.persist_providers_snapshot(), saved)

    def test_a_site_not_visited_tonight_keeps_what_was_saved(self):
        saved = self.stop_and_continue()
        self.assertEqual(S.persist_providers_snapshot(), saved)

    def test_a_new_game_starts_the_site_from_its_file(self):
        self.stop_and_continue()
        S.persist_providers_restore({})
        self.arrive()
        self.assertFalse(P.boarding_prop_is_open("door"))
        self.assertIsNotNone(P.boarding_prop("coil")["id"])
        self.assertEqual(K.boarding_hostiles("yard"), ["glassback", "stray", "warden"])

    def test_nothing_is_left_on_the_reset_ledger(self):
        self.stop_and_continue()
        self.assertGreater(P.boarding_props_saved_count(), 0)
        self.assertGreater(K.boarding_hostiles_saved_count(), 0)
        reset_mission_state()
        self.assertEqual(P.boarding_props_saved_count(), 0)
        self.assertEqual(K.boarding_hostiles_saved_count(), 0)
        left = {k: v for k, v in reset_mission_audit().items() if not k.startswith("mock.")}
        self.assertEqual(left, {})


if __name__ == "__main__":
    unittest.main()
