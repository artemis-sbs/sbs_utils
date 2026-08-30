"""Comms between two PLAYER ships has to reach both bridges.

`comms_message` picks which console a line lands on with a single test - "is the
sender a player?" - which is a complete answer only while the other end is an NPC.
With two player ships both ends pass it, so every line went to the sender: the
receiving crew saw nothing, and the sender saw an incoming message titled with its
own name. From the chair that is "the message was never sent".
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.agent import clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural.comms import comms_message
from sbs_utils.procedural.log_panel import log_clear
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.spaceobject import SpaceObject


class _Base(unittest.TestCase):
    def setUp(self):
        clear_shared()
        SpaceObject.clear()
        log_clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        self.sent = []
        self._orig = sbs.send_comms_message_to_player_ship
        sbs.send_comms_message_to_player_ship = self._record

        self.artemis = player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser").py_object
        self.hera = player_spawn(1000, 0, 0, "Hera", "tsn", "tsn_light_cruiser").py_object

    def tearDown(self):
        sbs.send_comms_message_to_player_ship = self._orig
        FrameContext.context = None
        SpaceObject.clear()

    def _record(self, playerID, otherID, faceDesc, titleText, titleColor, bodyText, bodyColor):
        self.sent.append({"on": playerID, "other": otherID,
                          "title": titleText, "body": bodyText})

    def on_ship(self, ship):
        return [m for m in self.sent if m["on"] == ship.id]

class TestPlayerToPlayer(_Base):
    def test_transmit_reaches_both_bridges(self):
        comms_message("Rendezvous at the beacon", self.artemis, self.hera,
                      is_receive=False)

        self.assertEqual(len(self.on_ship(self.artemis)), 1,
                         "the sender must see its own outgoing line")
        self.assertEqual(len(self.on_ship(self.hera)), 1,
                         "the receiving crew saw nothing at all")

    def test_each_side_is_named_for_the_other(self):
        comms_message("Rendezvous at the beacon", self.artemis, self.hera,
                      is_receive=False)

        out = self.on_ship(self.artemis)[0]
        inc = self.on_ship(self.hera)[0]
        self.assertEqual(out["title"], "> > Hera")
        self.assertEqual(inc["title"], "< < Artemis")
        self.assertEqual(inc["other"], self.artemis.id)

    def test_a_receive_lands_on_the_addressee(self):
        # Explicit receive: Hera said it, Artemis is being told.
        comms_message("On our way", self.hera, self.artemis, is_receive=True)

        self.assertEqual(len(self.on_ship(self.artemis)), 1)
        self.assertEqual(self.on_ship(self.artemis)[0]["title"], "< < Hera")
        self.assertEqual(self.on_ship(self.hera), [],
                         "a receive must not echo onto the sender")


class TestPlayerToNpcUnchanged(_Base):
    """The one-player cases the old two-way test already got right."""

    def setUp(self):
        super().setUp()
        self.station = npc_spawn(2000, 0, 0, "Phoenix", "tsn, station",
                                 "starbase", "behav_station").py_object

    def test_transmit_to_an_npc_shows_only_on_the_player(self):
        comms_message("Requesting docking clearance", self.artemis, self.station,
                      is_receive=False)

        self.assertEqual(len(self.on_ship(self.artemis)), 1)
        self.assertEqual(self.on_ship(self.artemis)[0]["title"], "> > Phoenix")
        self.assertEqual(self.on_ship(self.station), [])

    def test_receive_from_an_npc_shows_on_the_player(self):
        comms_message("Clearance granted", self.station, self.artemis,
                      is_receive=True)

        self.assertEqual(len(self.on_ship(self.artemis)), 1)
        self.assertEqual(self.on_ship(self.artemis)[0]["title"], "< < Phoenix")
        self.assertEqual(self.on_ship(self.artemis)[0]["other"], self.station.id)


if __name__ == "__main__":
    unittest.main()
