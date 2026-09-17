"""The EVA console's third-person camera: behind the suit, close, and never in the rock.

**EVERY LENS ASSERTION HERE READS THE POSITION THE ENGINE DERIVES**, which is the dolly
MINUS the offset, not plus it. The mock's own convention is the kinder one, and reading it
is how an establishing shot once passed a test while pointing the wrong way on real
hardware - see `test_camera_convention.py`, which pins the mirror itself.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.gui import eva_camera as CAM
from sbs_utils.procedural.gui.camera import _MOVES
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3

CID = 0x8000000000000001
CID2 = 0x8000000000000002
RELIC = "cam_relic"


class _Base(unittest.TestCase):
    """A wide hall opening into a narrow shaft - the two cases the rig has to tell apart."""

    def setUp(self):
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        R._RELIC_RECORDS.clear()
        for cid in (CID, CID2):
            GuiClient(cid)
        V.volume_define(RELIC, boxes={
            "hall": (0, 0, 0, 2000, 900, 900),          # room to spare
            "shaft": (3000, 0, 0, 1000, 90, 90),        # 180 units across
        })
        R._RELIC_RECORDS[RELIC] = {
            "key": RELIC, "loc": (0, 0, 0), "volume": RELIC,
            "points": {"hall": [0, 0, 0, [], "The Hall"],
                       "shaft": [3600, 0, 0, [], "The Shaft"]},
            "barriers": {}, "contents": [],
        }
        R.relic_rails_ensure(RELIC)

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        DeleteQueue.clear()
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        R._RELIC_RECORDS.clear()
        FrameContext.context = None

    def suit_up(self, cid=CID, at=(0, 0, 0)):
        who = lifeform_spawn("Boarder", "terran_male", "boarding")
        suit = E.eva_suit_spawn(who, RELIC, at[0], at[1], at[2],
                                hull="tsn_shuttle", side="tsn", volume=RELIC)
        E.eva_take(cid, suit, RELIC, volume=RELIC)
        return suit

    def face(self, suit, x, z):
        """Point the suit. The mock derives `forward_vector` from the object's heading.

        Via the AGENT's own `space_object()`, not `sim.get_space_object(agent_id)`: an
        agent id is not an engine id, and asking the sim for one answers None.
        """
        import math
        eo = self.engine_obj(suit)
        eo.pitch, eo.roll = 0.0, 0.0
        eo.heading = math.degrees(math.atan2(x, z))
        return eo.forward_vector()

    def engine_obj(self, suit):
        from sbs_utils.procedural.query import to_object
        return to_object(suit).space_object()

    def engine_lens(self, cid=CID):
        """Where the ENGINE puts the lens: the dolly MINUS the offset."""
        state = mock_sbs._cinematic.get(cid)
        if state is None:
            return None
        obj = mock_sbs.sim.get_space_object(state["dolly_id"])
        off = state["dolly_off"]
        return Vec3(obj.pos.x - off[0], obj.pos.y - off[1], obj.pos.z - off[2])


class TheLensSitsBehindTheSuit(_Base):
    def test_behind_not_in_front(self):
        """The mirror. `camera_chase` shipped doing the opposite of what it promised for
        as long as it did because nothing tested this."""
        suit = self.suit_up()
        fwd = self.face(suit, 0, 1)
        CAM.eva_camera_aim(CID)
        lens = self.engine_lens()
        self.assertIsNotNone(lens)
        along = lens.x * fwd.x + lens.y * fwd.y + lens.z * fwd.z
        self.assertLess(along, 0, "the lens is IN FRONT of the suit it is following")

    def test_dolly_and_target_are_the_same_object(self):
        """Two ids render a BLACK frame, silently."""
        self.suit_up()
        CAM.eva_camera_aim(CID)
        st = mock_sbs._cinematic[CID]
        self.assertEqual(st["dolly_id"], st["target_id"])

    def test_the_script_is_driving_not_the_director(self):
        self.suit_up()
        CAM.eva_camera_aim(CID)
        self.assertEqual(mock_sbs._cinematic[CID]["script"], 1)

    def test_a_suit_with_no_readable_heading_still_gets_a_camera(self):
        """A hull whose facing cannot be read must not leave the console with a black
        view - not being behind the ship still shows the ship."""
        suit = self.suit_up()
        eo = self.engine_obj(suit)
        eo.forward_vector = lambda: (_ for _ in ()).throw(RuntimeError("no heading"))
        self.assertIsNotNone(CAM.eva_camera_aim(CID))


class TheLensStaysInsideTheRelic(_Base):
    def test_a_shaft_does_not_put_the_camera_in_the_rock(self):
        """THE WHOLE REASON THIS RIG EXISTS. `set_main_view_modes` chase holds station
        behind its subject with no idea there is a wall there, and a relic has no engine
        collision to stop it."""
        suit = self.suit_up(at=(3600, 0, 0))
        self.face(suit, 1, 0)             # along the shaft, so "behind" is up the shaft
        CAM.eva_camera_aim(CID)
        lens = self.engine_lens()
        self.assertTrue(V.volume_inside(RELIC, (lens.x, lens.y, lens.z), 0.0),
                        "the lens ended up outside the relic at %r" % (lens,))

    def test_a_lens_asked_for_outside_is_walked_back_in(self):
        """The clamp on its own, without the rest of the rig in the way."""
        clamp = CAM.eva_camera_clamp(RELIC)
        base = Vec3(3600, 0, 0)
        want = Vec3(3600, 4000, 0)        # straight up, well through the shaft roof
        got = clamp(base, want)
        self.assertTrue(V.volume_inside(RELIC, (got[0], got[1], got[2]), 0.0))

    def test_a_lens_already_inside_is_left_alone(self):
        """The clamp is a limit, not a steering input - it must not move a good shot."""
        clamp = CAM.eva_camera_clamp(RELIC)
        base, want = Vec3(0, 0, 0), Vec3(0, 200, 0)
        got = clamp(base, want)
        self.assertEqual((got.x, got.y, got.z), (0.0, 200.0, 0.0))

    def test_no_volume_means_no_clamp(self):
        """Outside a relic there is nothing to clip against, and a camera that refused to
        move because it could not find a volume would be a dead console."""
        clamp = CAM.eva_camera_clamp(None)
        want = Vec3(0, 9999, 0)
        self.assertEqual(clamp(Vec3(0, 0, 0), want), want)


class TheFramingAnswersToTheRoomAndTheSpeed(_Base):
    def test_a_tight_shaft_pulls_the_lens_in(self):
        """The soft half of keeping out of the wall: come in BEFORE the hard clamp has
        to, so the shot changes smoothly rather than snapping."""
        suit = self.suit_up(at=(3600, 0, 0))
        tight = CAM.eva_camera_distance(CID, suit, RELIC)
        E.eva_release(CID)
        suit2 = self.suit_up(at=(0, 0, 0))
        roomy = CAM.eva_camera_distance(CID, suit2, RELIC)
        self.assertLess(tight, roomy, "the shaft framed the same as the hall")

    def test_speed_dollies_the_lens_in(self):
        """Doug's ask: dolly in on the chase while it is moving."""
        suit = self.suit_up()
        still = CAM.eva_camera_distance(CID, suit, RELIC)
        from sbs_utils.procedural.helm import helm_throttle
        helm_throttle(suit, E.CRUISE, allow_warp=False)
        moving = CAM.eva_camera_distance(CID, suit, RELIC)
        self.assertLess(moving, still, "the lens did not close up as the suit got going")

    def test_a_manual_distance_wins_outright(self):
        """A console that asked for a distance should get it, not have the clearance rule
        quietly argue with it."""
        suit = self.suit_up(at=(3600, 0, 0))
        CAM.eva_camera_dolly(CID, 500)       # clamped to CAM_MAX
        self.assertEqual(CAM.eva_camera_distance(CID, suit, RELIC), CAM.CAM_MAX)

    def test_the_distance_stays_in_its_range(self):
        suit = self.suit_up(at=(3600, 0, 0))
        d = CAM.eva_camera_distance(CID, suit, RELIC)
        self.assertGreaterEqual(d, CAM.CAM_MIN)
        self.assertLessEqual(d, CAM.CAM_MAX)


class TheControlsArePerConsole(_Base):
    def test_one_console_orbiting_does_not_move_another(self):
        """Six consoles fly six suits in one relic, so the view belongs to the client
        exactly as the suit does."""
        self.suit_up(CID)
        self.suit_up(CID2)
        CAM.eva_camera_orbit(CID, 90)
        self.assertEqual(CAM.eva_camera_state(CID)[0], 90.0)
        self.assertEqual(CAM.eva_camera_state(CID2)[0], 0.0)

    def test_orbit_wraps_rather_than_running_away(self):
        self.suit_up()
        for _ in range(10):
            CAM.eva_camera_orbit(CID, 45)
        self.assertLessEqual(abs(CAM.eva_camera_state(CID)[0]), 180.0)

    def test_tilt_is_clamped_short_of_straight_down(self):
        """A chase with no horizon reads as a map, not as flying."""
        self.suit_up()
        for _ in range(40):
            CAM.eva_camera_tilt(CID, -30)
        self.assertGreaterEqual(CAM.eva_camera_state(CID)[1], -60.0)

    def test_recenter_undoes_all_of_it_at_once(self):
        """"The camera is somewhere odd" is one problem however it got there."""
        self.suit_up()
        CAM.eva_camera_orbit(CID, 120)
        CAM.eva_camera_tilt(CID, 40)
        CAM.eva_camera_dolly(CID, -40)
        CAM.eva_camera_recenter(CID)
        yaw, pitch, dist, free = CAM.eva_camera_state(CID)
        self.assertEqual((yaw, pitch, dist, free), (0.0, CAM.CAM_PITCH, None, False))

    def test_a_stray_yaw_washes_out_but_a_locked_one_does_not(self):
        """A console that orbited to look at something should not have to put the camera
        back by hand; one that meant it should keep what it chose."""
        self.suit_up()
        from sbs_utils.procedural.inventory import set_inventory_value
        set_inventory_value(CID, CAM.KEY_YAW, 30.0)
        set_inventory_value(CID, CAM.KEY_FREE, False)
        for _ in range(20):
            CAM.eva_camera_aim(CID)
        self.assertEqual(CAM.eva_camera_state(CID)[0], 0.0)

        CAM.eva_camera_orbit(CID, 30)                 # deliberate: sets FREE
        for _ in range(20):
            CAM.eva_camera_aim(CID)
        self.assertEqual(CAM.eva_camera_state(CID)[0], 30.0)


class TheCameraPassIsShared(_Base):
    def test_one_watcher_however_many_consoles_ask(self):
        self.suit_up(CID)
        self.suit_up(CID2)
        first = CAM.eva_camera_watch()
        self.assertIs(CAM.eva_camera_watch(), first)
        self.assertEqual(CAM.eva_camera_watching(), 1)

    def test_the_probe_does_not_conjure_state_by_asking(self):
        """A reset-ledger probe that creates what it measures reports state surviving a
        reset with nothing running."""
        self.assertEqual(CAM.eva_camera_watching(), 0)
        self.assertEqual(CAM.eva_camera_watching(), 0)

    def test_stowing_the_suits_stops_the_pass(self):
        self.suit_up(CID)
        CAM.eva_camera_watch()
        E.eva_clear()
        self.assertEqual(CAM.eva_camera_watching(), 0)

    def test_the_pass_aims_every_console_flying_a_suit(self):
        self.suit_up(CID)
        self.suit_up(CID2)
        CAM.eva_camera_tick()
        self.assertIn(CID, mock_sbs._cinematic)
        self.assertIn(CID2, mock_sbs._cinematic)

    def test_a_console_with_no_suit_is_skipped_not_raised(self):
        self.suit_up(CID)
        E.eva_release(CID2)
        CAM.eva_camera_tick()
        self.assertNotIn(CID2, mock_sbs._cinematic)

    def test_another_mode_turns_the_pass_off(self):
        """A mission that wants the engine's own framing back gets it, and our pass must
        not keep re-aiming underneath it."""
        from sbs_utils.procedural.gui.eva_console import CAMERA_MODE_DEFAULT, eva_camera_mode
        self.addCleanup(eva_camera_mode, CAMERA_MODE_DEFAULT)
        self.suit_up(CID)
        eva_camera_mode("chase")
        CAM.eva_camera_tick()
        self.assertNotIn(CID, mock_sbs._cinematic)


if __name__ == "__main__":
    unittest.main()
