"""The place word on the handheld does not give away a secret.

A mark's name is drawn on the xESS bar, in the Crew app and as Scan's heading
(`where_text`). A mark is also how a writer places a thing - and a mark named for a thing
that is `Hidden until:` a signal told the crew it was there the moment somebody stood on
it (`agent_c3c_report.md` defect 1: "Dr Ines Hale | medical, science | cache").

THE RULE: a mark that is the placement of something NOT YET ON THE MAP is not said; the
area's title is, as on any cell with no mark. Once the thing is revealed the mark is a
place like any other.

    python -m unittest tests.test_boarding_place_words
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
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.gui.boarding_console import where_text
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.signal import signal_emit

PLACE_CID = 0x8000000000000051

PLACE_AREA = """area: yard
title: The Yard
tileset: g
entry: landing_pad
legend:
  .: dirt
  #: rock
  P: dirt @landing_pad
  C: dirt @cache
  K: dirt @keycard
  S: dirt @sentry
  A: dirt @ambush
  G: dirt @gate_house
---
############
#.P.C.K.S..#
#.A.G......#
############
"""

PLACE_KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

PLACE_PROPS = {"children": [
    {"key": "cache", "display_text": "Cache", "description": "Buried.",
     "data": {"area": "yard", "mark": "cache", "sprite": "g:dirt", "item": "fuse",
              "hidden_until": "cache_found"}},
    {"key": "keycard", "display_text": "Keycard", "description": "",
     "data": {"area": "yard", "mark": "keycard", "sprite": "g:dirt", "item": "keycard"}},
    {"key": "hut", "display_text": "Hut", "description": "A hut.",
     "data": {"area": "yard", "mark": "Gate_House", "sprite": "g:dirt"}},
]}

PLACE_PEOPLE = {"children": [
    {"key": "sentry", "display_text": "Sentry", "description": "",
     "data": {"area": "yard", "mark": "sentry", "sprite": "g:rock", "calm": "yes"}},
    {"key": "lurker", "display_text": "Lurker", "description": "",
     "data": {"area": "yard", "mark": "ambush", "sprite": "g:rock", "calm": "yes",
              "hidden_until": "sprung"}},
]}


class PlaceWordsTests(unittest.TestCase):
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
        T.tilemap_tileset("g", PLACE_KINDS)
        T.tilemap_load(PLACE_AREA)
        T._WATCH["task"] = object()
        K._WATCH["task"] = object()
        T.tilemap_set_clock(0.0)
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Yard", area="yard")
        GuiClient(PLACE_CID)
        body = lifeform_spawn("Hale", "", "boarding,science")
        set_inventory_value(body.id, A.JOBS_KEY, ["science"])
        A.boarding_assign(PLACE_CID, body.id)
        self.body = body.id
        P.boarding_props_declare(PLACE_PROPS)
        P.boarding_props_place()
        K.boarding_hostiles_declare(PLACE_PEOPLE)
        K.boarding_hostiles_place()
        G.boarding_go_down(PLACE_CID)

    def at(self, mark):
        x, y = T.tilemap_mark_cells("yard", mark)[0]
        T.tilemap_place(self.body, "yard", x, y)
        return where_text(PLACE_CID)

    def test_a_place_mark_is_the_place_word(self):
        self.assertEqual(self.at("landing_pad"), "landing pad")

    def test_a_mark_that_places_something_hidden_is_not_said(self):
        self.assertEqual(self.at("cache"), "The Yard")
        self.assertEqual(self.at("ambush"), "The Yard")

    def test_once_it_is_revealed_the_mark_is_a_place_again(self):
        signal_emit("cache_found")
        self.assertTrue(P.boarding_prop("cache")["shown"])
        self.assertEqual(self.at("cache"), "cache")
        signal_emit("sprung")
        self.assertEqual(self.at("ambush"), "ambush")

    def test_a_mark_that_places_something_in_plain_sight_is_said_as_before(self):
        self.assertEqual(self.at("keycard"), "keycard")
        self.assertEqual(self.at("sentry"), "sentry")
        # ... however the writer capitalized it on the record.
        self.assertEqual(self.at("gate_house"), "gate house")

    def test_a_cell_with_no_mark_is_the_area(self):
        T.tilemap_place(self.body, "yard", 10, 2)
        self.assertEqual(where_text(PLACE_CID), "The Yard")

    def test_the_health_suffix_goes_on_whichever_word_it_is(self):
        K.boarding_hurt(self.body, 1)
        self.assertEqual(self.at("cache"), "The Yard - HP 2/3")


if __name__ == "__main__":
    unittest.main()
