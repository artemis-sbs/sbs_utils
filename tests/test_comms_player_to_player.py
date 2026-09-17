"""Comms between two PLAYER ships has to reach both bridges, and every contact -
ship, station or individual lifeform - needs its own thread.

`comms_message` picks which console a line lands on with a single test - "is the
sender a player?" - which is a complete answer only while the other end is an NPC.
With two player ships both ends pass it, so every line went to the sender: the
receiving crew saw nothing, and the sender saw an incoming message titled with its
own name. From the chair that is "the message was never sent".

The engine's contactID says who the other party is, and so which conversation a line
belongs to. A lifeform is not an addressable space object, so the player/other ids
are only its HOST ship - key on those and every crew member aboard one hull collapses
into a single thread with the hull.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.agent import clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural.comms import comms_message
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.log_panel import log_clear
from sbs_utils.procedural.roles import add_role
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

    def _record(self, contactID, playerID, otherID, faceDesc, titleText, titleColor,
                bodyText, bodyColor, tags, name='unset'):
        self.sent.append({"contact": contactID, "on": playerID, "other": otherID,
                          "name": name, "title": titleText, "body": bodyText,
                          "tags": tags})

    def on_ship(self, ship):
        return [m for m in self.sent if m["on"] == ship.id]

    def lifeform(self, name, host):
        """A lifeform agent aboard `host`, the shape comms_message substitutes on."""
        obj = npc_spawn(0, 0, 0, name, "tsn", "starbase", "behav_station").py_object
        add_role(obj.id, "lifeform")
        set_inventory_value(obj.id, "host", host.id)
        return obj

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
        # The direction is a TAG; the contact name rides its own `name` field,
        # which is what the title used to be spent on.
        self.assertEqual(out["name"], "Hera")
        self.assertEqual(out["tags"], "send")
        self.assertEqual(inc["name"], "Artemis")
        self.assertEqual(inc["tags"], "recv")
        self.assertEqual(inc["other"], self.artemis.id)

    def test_each_bridge_threads_on_the_other_ship(self):
        comms_message("Rendezvous at the beacon", self.artemis, self.hera,
                      is_receive=False)

        self.assertEqual(self.on_ship(self.artemis)[0]["contact"], self.hera.id)
        self.assertEqual(self.on_ship(self.hera)[0]["contact"], self.artemis.id)

    def test_a_receive_lands_on_the_addressee(self):
        # Explicit receive: Hera said it, Artemis is being told.
        comms_message("On our way", self.hera, self.artemis, is_receive=True)

        self.assertEqual(len(self.on_ship(self.artemis)), 1)
        self.assertEqual(self.on_ship(self.artemis)[0]["name"], "Hera")
        self.assertEqual(self.on_ship(self.artemis)[0]["tags"], "recv")
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
        self.assertEqual(self.on_ship(self.artemis)[0]["name"], "Phoenix")
        self.assertEqual(self.on_ship(self.artemis)[0]["tags"], "send")
        self.assertEqual(self.on_ship(self.station), [])

    def test_receive_from_an_npc_shows_on_the_player(self):
        comms_message("Clearance granted", self.station, self.artemis,
                      is_receive=True)

        self.assertEqual(len(self.on_ship(self.artemis)), 1)
        self.assertEqual(self.on_ship(self.artemis)[0]["name"], "Phoenix")
        self.assertEqual(self.on_ship(self.artemis)[0]["tags"], "recv")
        self.assertEqual(self.on_ship(self.artemis)[0]["other"], self.station.id)
        self.assertEqual(self.on_ship(self.artemis)[0]["contact"], self.station.id)


class TestLifeformThreads(_Base):
    """A lifeform is addressed THROUGH its host ship but threaded on its own id.

    Every case here asserts on BOTH bridges where there are two. The earlier versions
    of these tests only looked at the sender's, which is exactly how the receiving
    crew's copy went on arriving stripped of the person who sent it.
    """

    def test_a_lifeform_keys_on_itself_not_its_host(self):
        harkin = self.lifeform("Admiral Harkin", self.hera)
        comms_message("Report in.", harkin, self.artemis, is_receive=True)

        got = self.on_ship(self.artemis)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["contact"], harkin.id,
                         "the thread is with the admiral, not with Hera")
        self.assertEqual(got[0]["other"], self.hera.id,
                         "the addressable object is still the host ship")
        self.assertEqual(got[0]["name"], "Admiral Harkin")

    def test_two_lifeforms_aboard_one_ship_are_two_threads(self):
        harkin = self.lifeform("Admiral Harkin", self.hera)
        medic = self.lifeform("Doctor Vance", self.hera)
        comms_message("Report in.", harkin, self.artemis, is_receive=True)
        comms_message("Casualty report.", medic, self.artemis, is_receive=True)

        contacts = [m["contact"] for m in self.on_ship(self.artemis)]
        self.assertEqual(contacts, [harkin.id, medic.id])

    def test_a_lifeform_aboard_the_reading_ship_keys_on_the_lifeform(self):
        """Our own officer talking to our own bridge.

        Both ends collapse onto Artemis, so there is no "far side" to key on. Keying
        on the far side anyway named the SHIP, which put every crew member aboard into
        one thread with the hull they are standing in.
        """
        rios = self.lifeform("Lt Rios", self.artemis)
        comms_message("Report.", rios, self.artemis, is_receive=True)

        got = self.on_ship(self.artemis)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["contact"], rios.id)
        self.assertEqual(got[0]["name"], "Lt Rios")

    def test_lifeform_to_lifeform_reaches_both_bridges_as_the_people(self):
        """The case that prompted all of this.

        Rios aboard Artemis hails Harkin aboard Hera. The recursion that builds the
        receiving crew's copy used to re-enter with the HOST ships - by then the only
        thing `from_obj`/`to_obj` held - so Hera was told "Artemis hailed you" and the
        two bridges filed one exchange under two different contacts.
        """
        rios = self.lifeform("Lt Rios", self.artemis)
        harkin = self.lifeform("Admiral Harkin", self.hera)
        comms_message("Standing by.", rios, harkin, is_receive=False)

        out = self.on_ship(self.artemis)
        inc = self.on_ship(self.hera)
        self.assertEqual(len(out), 1)
        self.assertEqual(len(inc), 1, "the receiving crew saw nothing")

        self.assertEqual(out[0]["contact"], harkin.id)
        self.assertEqual(out[0]["other"], self.hera.id)
        self.assertEqual(out[0]["tags"], "send")
        self.assertEqual(out[0]["name"], "Admiral Harkin")

        self.assertEqual(inc[0]["contact"], rios.id,
                         "the admiral's crew must be told Rios called, not Artemis")
        self.assertEqual(inc[0]["other"], self.artemis.id)
        self.assertEqual(inc[0]["tags"], "recv")
        self.assertEqual(inc[0]["name"], "Lt Rios")

    def test_a_transmit_is_titled_for_the_contact_it_is_filed_under(self):
        # The thread is keyed on Harkin, so the label has to say Harkin. It used to say
        # "Hera" (the host) for a ship sender, and our own officer's name for a lifeform
        # one - either way naming something other than the id it was filed under.
        harkin = self.lifeform("Admiral Harkin", self.hera)
        comms_message("Orders received.", self.artemis, harkin, is_receive=False)

        out = self.on_ship(self.artemis)[0]
        self.assertEqual(out["contact"], harkin.id)
        self.assertEqual(out["name"], "Admiral Harkin")


class TestPerPairValues(_Base):
    """Name, portrait and colors are per PAIR, not per call.

    All four were written back to the enclosing parameters inside the nested
    `for from_obj / for to_obj` loops, so the first pair's values stuck to every later
    one - the same leak `arg_title` already had a comment about.
    """

    def test_each_sender_is_named_for_itself(self):
        rios = self.lifeform("Lt Rios", self.artemis)
        station = npc_spawn(2000, 0, 0, "Phoenix", "tsn, station",
                            "starbase", "behav_station").py_object

        comms_message("Report.", [rios, station], self.artemis, is_receive=True)

        got = self.on_ship(self.artemis)
        self.assertEqual(len(got), 2)
        self.assertEqual([m["name"] for m in got], ["Lt Rios", "Phoenix"],
                         "the station's line inherited the lifeform's name")
        self.assertEqual([m["contact"] for m in got], [rios.id, station.id])


class TestNameAndTitleAreSeparate(_Base):
    """The engine takes the speaker's name in its own field.

    Before it had one, the library packed the name into the title - a message with no
    title was titled with the name, and one with a title read "Phoenix: Docking Bay 4".
    Both halves now travel on their own.
    """

    def setUp(self):
        super().setUp()
        self.station = npc_spawn(2000, 0, 0, "Phoenix", "tsn, station",
                                 "starbase", "behav_station").py_object

    def test_a_title_is_sent_whole_beside_the_name(self):
        comms_message("Proceed to bay 4.", self.station, self.artemis,
                      title="Docking Bay 4", is_receive=True)

        got = self.on_ship(self.artemis)[0]
        self.assertEqual(got["name"], "Phoenix")
        self.assertEqual(got["title"], "Docking Bay 4")
        self.assertNotIn(": ", got["title"],
                         "the name is packed into the title again")

    def test_no_title_sends_an_empty_title_not_the_name(self):
        comms_message("Clearance granted.", self.station, self.artemis,
                      is_receive=True)

        got = self.on_ship(self.artemis)[0]
        self.assertEqual(got["name"], "Phoenix")
        self.assertEqual(got["title"], "",
                         "an untitled message must not borrow the speaker's name")

    def test_the_history_record_keeps_the_packed_label(self):
        """Comms panels built before the split render `title` as the whole header."""
        from sbs_utils.procedural.comms import comms_history_for

        comms_message("Proceed to bay 4.", self.station, self.artemis,
                      title="Docking Bay 4", is_receive=True)

        rec = comms_history_for(self.artemis.id, self.station.id)[0]
        self.assertEqual(rec["title"], "Phoenix: Docking Bay 4")
        self.assertEqual(rec["title_text"], "Docking Bay 4")
        self.assertEqual(rec["from_name"], "Phoenix")


if __name__ == "__main__":
    unittest.main()
