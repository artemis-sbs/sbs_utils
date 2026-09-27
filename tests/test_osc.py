"""OSC: the codec, the address map driving a real (mock) player ship, and the listener.

The listener tests use a REAL loopback UDP socket and drive `_osc_tick` by hand - the
same function the TickDispatcher calls each update in the engine - so what is tested is
the production receive path, not a stand-in for it.

Run:
    python -m unittest tests.test_osc
"""
import socket
import struct
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.handlerhooks import reset_mission_state, reset_mission_audit
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural import osc as O
from sbs_utils.procedural.helm import helm_eng_controls
from sbs_utils.procedural.query import get_weapons_selection, get_science_selection
from sbs_utils.procedural.sides import side_ensure, side_set_relations
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.spaceobject import SpaceObject


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class CodecTests(unittest.TestCase):
    def test_round_trip_every_type(self):
        msg = O.osc_encode("/a/b", 1, 0.5, "hi", True, False, None)
        self.assertEqual(O.osc_decode(msg), [("/a/b", [1, 0.5, "hi", True, False, None])])

    def test_padding_is_to_four_bytes(self):
        for addr in ("/a", "/ab", "/abc", "/abcd"):
            self.assertEqual(len(O.osc_encode(addr)) % 4, 0)
            self.assertEqual(O.osc_decode(O.osc_encode(addr))[0][0], addr)

    def test_bundle_is_flattened(self):
        a, b = O.osc_encode("/x", 1), O.osc_encode("/y", 2.0)
        bundle = (b"#bundle\0" + b"\0" * 8 + struct.pack(">i", len(a)) + a
                  + struct.pack(">i", len(b)) + b)
        self.assertEqual(O.osc_decode(bundle), [("/x", [1]), ("/y", [2.0])])

    def test_malformed_packets_raise_so_they_are_dropped_whole(self):
        good = O.osc_encode("/helm/throttle", 0.5)
        for bad in (b"", b"garbage", good[:-2], b"/x\0\0,z\0\0",
                    b"#bundle\0" + b"\0" * 8 + struct.pack(">i", 999) + b"abcd"):
            with self.assertRaises(Exception, msg=repr(bad)):
                O.osc_decode(bad)


class ShipBase(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        self.ship = player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser")
        self.ds = self.ship.data_set

    def tearDown(self):
        O.osc_stop()
        SpaceObject.clear()
        FrameContext.context = None

    def send(self, address, *args, sender=None):
        return O.osc_dispatch(address, list(args), sender)


class HelmAndEngineeringTests(ShipBase):
    def test_throttle_fader(self):
        self.assertTrue(self.send("/helm/throttle", 0.5))
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.5)

    def test_impulse_reverse_and_warp_work_like_the_game_bar(self):
        self.ds.set("warp", 1.0, 0)
        self.send("/helm/impulse", 0.4)
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.4, places=5)
        self.send("/helm/reverse", 1.0)                   # same power, backwards
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), -0.4, places=5)
        self.send("/helm/impulse", 0.8)                   # the lever keeps reverse
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), -0.8, places=5)
        self.send("/helm/reverse", 0.0)
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.8, places=5)
        self.send("/helm/warp/2", 1.0)                    # warp n = throttle 1 + n
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 3.0, places=5)
        state = O.osc_state(self.ship)
        self.assertEqual(state["/state/warp"], 2)
        self.assertEqual(state["/helm/impulse"], 1.0)
        self.send("/helm/warp/0", 1.0)                    # back to full impulse
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 1.0, places=5)
        self.send("/helm/impulse", 0.3)                   # the lever leaves warp
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.3, places=5)

    def test_a_watched_panel_is_not_dropped_after_thirty_seconds(self):
        """A gauges-only tablet is never touched; it must keep receiving."""
        self.assertGreaterEqual(O.SENDER_TIMEOUT, 300)

    def test_toggles_follow_the_value(self):
        self.send("/helm/red_alert", 1.0)
        self.assertEqual(self.ds.get("red_alert", 0), 1)
        self.send("/helm/red_alert", 0.0)
        self.assertEqual(self.ds.get("red_alert", 0), 0)
        self.send("/helm/shields", 1)
        self.assertEqual(self.ds.get("shields_raised_flag", 0), 1)

    def test_a_button_acts_on_press_not_on_release(self):
        self.ds.set("playerThrottle", 0.8, 0)
        self.send("/helm/stop", 0.0)                 # the release
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.8)
        self.send("/helm/stop", 1.0)                 # the press
        self.assertEqual(self.ds.get("playerThrottle", 0), 0.0)

    def test_heading_steers_by_direction(self):
        self.send("/helm/heading", 90.0)
        self.assertEqual(self.ds.get("steeringToDirFlag", 0), 1)
        self.assertAlmostEqual(self.ds.get("steerToDirDX", 0), 1.0, places=5)
        self.assertAlmostEqual(self.ds.get("steerToDirDZ", 0), 0.0, places=5)

    def test_dock_picks_the_nearest_friendly_station(self):
        side_ensure("tsn")
        far = npc_spawn(9000, 0, 0, "DS2", "tsn,station", "starbase", "behav_station")
        near = npc_spawn(500, 0, 0, "DS1", "tsn,station", "starbase", "behav_station")
        self.send("/helm/dock", 1)
        self.assertEqual(self.ds.get("dock_base_id", 0), near.id)
        self.assertNotEqual(self.ds.get("dock_base_id", 0), far.id)

    def test_power_by_label_is_clamped(self):
        self.send("/eng/power/impulse", 9.0)
        idx = next(i for i, l, _s in helm_eng_controls(self.ship) if l == "IMPULSE")
        self.assertAlmostEqual(self.ds.get("eng_control_value", idx), 3.0)

    def test_coolant_never_exceeds_what_is_available(self):
        available = int(self.ds.get("system_coolant_available", 0))
        self.send("/eng/coolant/0", available - 2)
        self.send("/eng/coolant/1", available)       # only 2 left
        self.assertEqual(self.ds.get("system_coolant_used", 1), 2)


class TargetingTests(ShipBase):
    def setUp(self):
        super().setUp()
        side_ensure("tsn")
        side_ensure("kralien")
        side_set_relations("tsn", "kralien", sbs.DIPLOMACY.HOSTILE)
        self.a = npc_spawn(1000, 0, 0, "K1", "kralien", "kralien_cruiser", "behav_npcship")
        self.b = npc_spawn(3000, 0, 0, "K2", "kralien", "kralien_cruiser", "behav_npcship")
        self.friend = npc_spawn(500, 0, 0, "DS1", "tsn", "starbase", "behav_station")

    def test_weapons_cycle_hostiles_by_distance_never_a_friend(self):
        self.send("/weapons/target/nearest", 1)
        self.assertEqual(get_weapons_selection(self.ship), self.a.id)
        self.send("/weapons/target/next", 1)
        self.assertEqual(get_weapons_selection(self.ship), self.b.id)
        self.send("/weapons/target/next", 1)          # wraps
        self.assertEqual(get_weapons_selection(self.ship), self.a.id)
        self.send("/weapons/target/clear", 1)
        self.assertFalse(get_weapons_selection(self.ship))

    def test_science_can_pick_friends_too(self):
        self.send("/science/target/nearest", 1)
        self.assertEqual(get_science_selection(self.ship), self.friend.id)


class RoutingTests(ShipBase):
    def setUp(self):
        super().setUp()
        self.second = player_spawn(0, 0, 500, "Hera", "tsn", "tsn_light_cruiser")

    def test_ship_prefix_and_bind_pick_the_ship(self):
        first, second = sorted([self.ship.id, self.second.id])
        from sbs_utils.procedural.query import to_object
        self.send("/ship/2/helm/throttle", 0.25)
        self.assertAlmostEqual(to_object(second).data_set.get("playerThrottle", 0), 0.25)
        sender = {"slot": None, "last": {}}
        self.send("/bind", 2, sender=sender)
        self.send("/helm/throttle", 0.75, sender=sender)
        self.assertAlmostEqual(to_object(second).data_set.get("playerThrottle", 0), 0.75)
        self.assertNotAlmostEqual(to_object(first).data_set.get("playerThrottle", 0), 0.75)

    def test_unknown_addresses_are_refused(self):
        self.assertFalse(self.send("/helm/self_destruct", 1))
        self.assertFalse(self.send("/weapons/fire/", 1))


class ListenerTests(ShipBase):
    def setUp(self):
        super().setUp()
        self.port = _free_port()
        self.fb = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fb.bind(("127.0.0.1", 0))
        self.fb.settimeout(0.5)
        self.assertTrue(O.osc_listen(self.port, feedback_port=self.fb.getsockname()[1],
                                     host="127.0.0.1", rate=1000))
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def tearDown(self):
        self.fb.close()
        self.tx.close()
        super().tearDown()

    def tick(self):
        O._osc_tick()

    def test_packets_on_the_wire_drive_the_ship(self):
        self.tx.sendto(O.osc_encode("/helm/throttle", 0.6), ("127.0.0.1", self.port))
        self.tx.sendto(b"not osc", ("127.0.0.1", self.port))
        self.tick()
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.6, places=5)
        self.assertEqual(O.osc_status()["dropped"], 1)

    def test_an_empty_socket_returns_at_once(self):
        self.tick()                                  # must not wait
        self.assertEqual(O.osc_status()["received"], 0)

    def test_a_flood_is_spread_over_updates(self):
        for _ in range(O.MAX_PACKETS_PER_TICK + 10):
            self.tx.sendto(O.osc_encode("/helm/red_alert", 1), ("127.0.0.1", self.port))
        self.tick()
        self.assertEqual(O.osc_status()["received"], O.MAX_PACKETS_PER_TICK)
        self.tick()
        self.assertEqual(O.osc_status()["received"], O.MAX_PACKETS_PER_TICK + 10)

    def test_feedback_sends_state_and_only_what_changed(self):
        self.tx.sendto(O.osc_encode("/helm/throttle", 0.3), ("127.0.0.1", self.port))
        self.tick()
        first = {}
        try:
            while True:
                for address, args in O.osc_decode(self.fb.recvfrom(4096)[0]):
                    first[address] = args[0]
        except socket.timeout:
            pass
        self.assertAlmostEqual(first["/helm/throttle"], 0.3, places=5)
        self.assertIn("/state/energy", first)
        self.assertIn("/state/shields/front", first)
        # Nothing changed: the next feedback round sends nothing.
        O._OSC["next_feedback"] = 0
        self.tick()
        self.fb.settimeout(0.2)
        with self.assertRaises(socket.timeout):
            self.fb.recvfrom(4096)

    def test_nothing_escapes_the_update(self):
        """The engine found this: one bad read in the feedback raised out of the tick and
        took down the engine's whole event handler, every update. It must be contained."""
        self.tx.sendto(O.osc_encode("/helm/throttle", 0.3), ("127.0.0.1", self.port))
        real = O.osc_state
        O.osc_state = lambda ship: (_ for _ in ()).throw(ValueError("could not convert"))
        try:
            self.tick()                              # must not raise
        finally:
            O.osc_state = real
        self.assertAlmostEqual(self.ds.get("playerThrottle", 0), 0.3, places=5)

    def test_a_string_field_reads_as_zero_not_an_error(self):
        self.ds.set("red_alert", "status", 0)       # the shape of the engine's surprise
        self.assertEqual(O.osc_state(self.ship)["/helm/red_alert"], 0)

    def test_reset_closes_the_socket_so_the_next_mission_can_bind(self):
        reset_mission_state()
        self.assertFalse(O.osc_is_listening())
        self.assertNotIn("OSC listener", reset_mission_audit())
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        self.assertTrue(O.osc_listen(self.port, host="127.0.0.1"))


if __name__ == "__main__":
    unittest.main()
