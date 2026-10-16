"""On a GENERATED ship deck the xESS bar says the room, not the generator's key.

Engine-seen, author course 3 lesson 15 (boarding the Black Gull): the bar's place slot
read `room:captains-cabin`, `room:sensors`, `room:hallway`, `room:brig` and a bare `door`.
Those are `boarding_deckplan`'s mark keys. The bar says `Captains Cabin`, `Sensors`,
`Hallway`, `Brig`, a doorway as `Door`, and the deck's `entry` cell as its room.

    python -m unittest tests.test_boarding_deck_place_words
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
import unittest

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_deckplan as D
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural.gui.boarding_console import where_text
from sbs_utils.procedural.lifeform import lifeform_spawn

CID = 0x8000000000000081

PLAN = """ship: test_ship
size: 8x5
legend:
  q: captains-cabin / room,quarters
  i: impulse
  c: brig
  s: sensors
---
qq..ii
qq..ii
..cc..
..cc..
       s
"""


class TheDeckBarSaysTheRoom(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        SpaceObject.clear()
        clear_shared()
        for clear in (A.boarding_clear, T.tilemap_clear, T.tilemap_clear_tilesets,
                      P.boarding_props_clear, D.boarding_deck_clear):
            clear()
            self.addCleanup(clear)
        self.area = D.boarding_deck_build(D.boarding_deck_plan_ascii(PLAN), "deck_words",
                                          title="Black Gull")
        GuiClient(CID)
        body = lifeform_spawn("Ross", "", "boarding,helm")
        A.boarding_assign(CID, body.id)
        self.body = body.id

    def at_mark(self, mark):
        cells = T.tilemap_mark_cells(self.area, mark)
        self.assertTrue(cells, "fixture: no %s on the deck" % mark)
        # A cell that ANSWERS with this mark - a room's own cells may also be the entry.
        cell = next((c for c in cells if T.tilemap_mark_at(self.area, *c) == mark), None)
        self.assertIsNotNone(cell, "fixture: every %s cell answers another mark" % mark)
        T.tilemap_place(self.body, self.area, cell[0], cell[1])
        return where_text(CID)

    def test_a_room_is_its_name(self):
        self.assertEqual("Brig", self.at_mark("room:brig"))
        self.assertEqual("Impulse", self.at_mark("room:impulse"))

    def test_a_hyphenated_room_is_words(self):
        self.assertEqual("Captains Cabin", self.at_mark("room:captains-cabin"))

    def test_the_hallway(self):
        self.assertEqual("Hallway", self.at_mark("room:hallway"))

    def test_a_doorway_is_a_door(self):
        self.assertEqual("Door", self.at_mark("door"))

    def test_the_entry_is_the_room_it_is_in(self):
        said = self.at_mark("entry")
        self.assertNotIn("entry", said)
        self.assertNotIn(":", said)

    def test_no_raw_key_anywhere_on_the_deck(self):
        for mark in T.tilemap_marks(self.area):
            for cell in T.tilemap_mark_cells(self.area, mark):
                T.tilemap_place(self.body, self.area, cell[0], cell[1])
                said = where_text(CID)
                self.assertNotIn("room:", said, (mark, cell))
                self.assertNotEqual("door", said, (mark, cell))
                self.assertNotEqual("entry", said, (mark, cell))


if __name__ == "__main__":
    unittest.main()
