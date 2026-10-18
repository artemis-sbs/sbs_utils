"""Out in a suit, the xESS Crew list's SHIP row still names the ship.

Seen in the engine (C4-08 scouting, 2026-10-18) and reproduced headless: the Crew app
listed "Mateo Osei", "Mateo Osei (you)", "Everyone". The first row is the ship's row -
`boarding_home_ship` fell back to the console's CURRENT ship, which after SUIT UP is the
suit, and a suit is named after its wearer. The suit records where it came from
(`eva_my_home`); that is the console's ship.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from tests.test_eva_rails import _Base, RELIC
from cosmos_dev.mock import sbs
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import eva as E
from sbs_utils.procedural.gui.boarding_gui import boarding_home_ship
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.spawn import player_spawn

CID = 0x8000000000000021


class TheShipRowIsTheShip(_Base):

    def test_a_suited_console_still_belongs_to_its_ship(self):
        GuiClient(CID)
        home = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        sbs.assign_client_to_ship(CID, home)
        who = lifeform_spawn("Mateo Osei", "terran_male", "boarding")
        suit = E.eva_suit_spawn(who, RELIC, -2300, 0, 0, hull="tsn_shuttle", side="tsn",
                                volume=RELIC)
        E.eva_take(CID, suit, RELIC, volume=RELIC, home=home)
        sbs.assign_client_to_ship(CID, to_id(suit))     # what the handover does
        self.assertEqual(boarding_home_ship(CID), home)


if __name__ == "__main__":
    unittest.main()
