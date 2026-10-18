"""The suit's header names the room the way the author wrote it, never by its key.

Seen in the engine (C4-08/C4-09 scouting, 2026-10-18): the xESS header read "mouth",
"nave", "vault" and "yard_area" - the record KEYS - where the page says The Mouth, The
Nave, The Vault and The Work Area. `eva_where` returned the volume's chamber key and
nothing looked up the heading.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.spaceobject import SpaceObject

CID = 0x8000000000000061
RELIC = "where_relic"


class TheHeaderNamesTheRoom(unittest.TestCase):

    def setUp(self):
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        R._RELIC_RECORDS.clear()
        GuiClient(CID)
        V.volume_define(RELIC, chambers={"mouth": (0, 0, 0, 900)},
                        boxes={"gallery": (3000, 0, 0, 600, 400, 800)})
        R._RELIC_RECORDS[RELIC] = {
            "key": RELIC, "loc": (0, 0, 0), "volume": RELIC,
            "chambers": {"mouth": (0, 0, 0, 900)},
            "boxes": {"gallery": (3000, 0, 0, 600, 400, 800)},
            "part_info": {"mouth": {"kind": "chamber", "display": "The Mouth"},
                          "gallery": {"kind": "box", "display": "The Gallery"}},
            "points": {}, "barriers": {}, "contents": [],
        }

    def tearDown(self):
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        R._RELIC_RECORDS.clear()

    def suit_at(self, x, y, z):
        who = lifeform_spawn("Boarder", "terran_male", "boarding")
        suit = E.eva_suit_spawn(who, RELIC, x, y, z, hull="tsn_shuttle", side="tsn",
                                volume=RELIC)
        E.eva_take(CID, suit, RELIC, volume=RELIC)
        return suit

    def test_a_chamber_is_named_by_its_heading(self):
        self.suit_at(0, 0, 0)
        self.assertEqual(E.eva_where(CID), "The Mouth")

    def test_a_BOX_room_is_named_too(self):
        """A box is a room as much as a chamber is; the Gallery is one."""
        self.suit_at(3000, 0, 0)
        self.assertEqual(E.eva_where(CID), "The Gallery")

    def test_a_part_with_no_heading_falls_back_to_its_key(self):
        R._RELIC_RECORDS[RELIC]["part_info"] = {}
        self.suit_at(0, 0, 0)
        self.assertEqual(E.eva_where(CID), "mouth")


if __name__ == "__main__":
    unittest.main()
