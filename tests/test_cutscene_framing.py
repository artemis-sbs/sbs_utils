"""A cutscene shot framed by the SUBJECT rather than by a typed coordinate.

THE REPORT THAT CAUSED THIS: in a mission built on the TNG pack, the authored cutscenes
put big ships through the frame and left small ones as specks. Two independent faults,
either of which alone still misframes:

  * ``lens`` and ``move`` are world POSITIONS, not offsets. A shot written as though its
    subject sat at the origin frames a subject parked 7,000 units away 7,000 units
    differently. In the mission that reported this, exactly one shot of six looked right
    - the one whose subject happened to be the only one at the origin.
  * nothing scaled with hull size. Across that pack a Bird of Prey is 25 units of hull
    radius and Deep Space Nine is 220, and one typed distance cannot serve both.

``framing`` closes both: the distance comes from ``viewscreen_framing`` (hull radii, the
same arithmetic the Director has used since it deleted its own distance sliders), and it
is applied relative to wherever the subject is.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.gui import GuiClient
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.gui.camera import camera_anchor, _MOVES
from sbs_utils.procedural.gui.cutscene import (cutscene_framing, shot_apply,
                                               _CUTSCENES, _PLAYING)
from sbs_utils.procedural.gui.viewscreen import FRAME_MIN


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)
        self.vars = {}

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


C1 = 0x8000000000000001


class FramingBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        _CUTSCENES.clear()
        _PLAYING.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = C1
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(C1)
        client.page_stack.append(self.page)
        FrameContext.page = self.page

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        _CUTSCENES.clear()
        _PLAYING.clear()
        DeleteQueue.clear()
        FrameContext.page = None
        FrameContext.context = None

    def subject(self, x=0, y=0, z=0, radius=None):
        """An anchor standing in for a hull, with a size the framing can read.

        `camera_anchor` hands back an id, so the size has to be set through the space
        object behind it - which is also where `viewscreen_framing` reads it from.
        """
        from sbs_utils.procedural.query import to_object
        oid = camera_anchor(x, y, z)
        if radius is not None:
            obj = to_object(oid)
            eo = obj.space_object() if obj is not None else None
            if eo is not None:
                eo.exclusion_radius = float(radius)
        return oid

    def offset(self):
        """The offset the ENGINE was handed for this console."""
        state = mock_sbs._cinematic.get(C1)
        return None if state is None else state["dolly_off"]

    def distance(self):
        ox, oy, oz = self.offset()
        return (ox * ox + oy * oy + oz * oz) ** 0.5


class TestFramingScalesWithTheHull(FramingBase):
    def test_a_bigger_hull_is_framed_from_further_out(self):
        # The whole point: one shot, two sizes, two distances.
        small = self.subject(radius=25)      # a Bird of Prey
        shot_apply(C1, {"subject": small, "framing": "medium"})
        near_d = self.distance()

        mock_sbs._cinematic.clear()
        big = self.subject(radius=220)       # Deep Space Nine
        shot_apply(C1, {"subject": big, "framing": "medium"})
        far_d = self.distance()

        self.assertGreater(far_d, near_d * 2.0,
                           "a hull ~9x larger must be framed from meaningfully further")

    def test_the_named_sizes_are_ordered(self):
        got = []
        for size in ("close", "medium", "wide"):
            mock_sbs._cinematic.clear()
            s = self.subject(radius=200)
            shot_apply(C1, {"subject": s, "framing": size})
            got.append(self.distance())
        self.assertLess(got[0], got[1])
        self.assertLess(got[1], got[2])

    def test_a_tiny_hull_still_clears_the_floor(self):
        # FRAME_MIN exists so the engine reporting a 10-unit hull cannot park the lens
        # inside it. Without it, "close" on a fighter is 60 units - inside the model.
        s = self.subject(radius=10)
        self.assertGreaterEqual(cutscene_framing(s, "close"), FRAME_MIN)

    def test_an_unknown_size_is_a_usable_shot(self):
        # A misspelled size should give a shot, not no shot.
        s = self.subject(radius=100)
        self.assertEqual(cutscene_framing(s, "meduim"), cutscene_framing(s, "medium"))


class TestFramingIgnoresWhereTheSubjectIsParked(FramingBase):
    """The fault that left exactly one shot of six looking right."""

    def test_the_same_shot_frames_the_same_wherever_the_subject_sits(self):
        at_origin = self.subject(0, 0, 0, radius=95)
        shot_apply(C1, {"subject": at_origin, "framing": "medium"})
        a = self.offset()

        mock_sbs._cinematic.clear()
        parked = self.subject(-7000, 0, 2000, radius=95)   # where the hero actually sits
        shot_apply(C1, {"subject": parked, "framing": "medium"})
        b = self.offset()

        for got, want in zip(b, a):
            self.assertAlmostEqual(got, want, places=3)

    def test_a_literal_lens_still_depends_on_position(self):
        # The old behavior, pinned deliberately: this is what `framing` exists to avoid,
        # and it must keep working for every shot already written against it.
        parked = self.subject(-7000, 0, 2000, radius=95)
        shot_apply(C1, {"subject": parked, "lens": (0, 700, -2400)})
        self.assertAlmostEqual(self.offset()[0], 7000.0, places=3)


class TestTheOldWayIsUntouched(FramingBase):
    def test_an_absolute_lens_reaches_the_engine_unchanged(self):
        s = self.subject(0, 0, 0, radius=95)
        shot_apply(C1, {"subject": s, "lens": (0, 700, -2400)})
        ox, oy, oz = self.offset()
        self.assertAlmostEqual(oy, 700.0, places=3)
        self.assertAlmostEqual(oz, -2400.0, places=3)

    def test_a_shot_with_neither_still_does_nothing(self):
        s = self.subject(radius=95)
        self.assertIsNone(shot_apply(C1, {"subject": s, "seconds": 2}))


class TestAMoveFollowsTheSubject(FramingBase):
    def test_a_framing_pair_returns_a_move(self):
        s = self.subject(radius=95)
        prom = shot_apply(C1, {"subject": s, "framing": ["wide", "close"], "seconds": 3})
        self.assertIsNotNone(prom, "a two-item framing is a move, not a held shot")

    def test_a_push_in_starts_wide_and_ends_close(self):
        s = self.subject(radius=95)
        shot_apply(C1, {"subject": s, "framing": ["wide", "close"], "seconds": 4})
        TickDispatcher.dispatch_tick()
        start = self.distance()
        for _ in range(int(4 * mock_sbs.TICKS_PER_SECOND) + 2):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1
        self.assertLess(self.distance(), start,
                        "a wide->close move must end nearer than it began")


class TestTheMainscreenComesBack(FramingBase):
    """A cutscene gives the console back the ship it was riding.

    A shot ASSIGNS its console to the object the lens rides, and that outlives the
    cutscene. Releasing to the engine director afterwards leaves it following the last
    shot subject - so a trial whose reveal held on a station ended with the mainscreen
    watching the station. The trials whose reveal fell back to the crew ship looked fine,
    which is why it read as one broken mission instead of a missing rule.
    """

    def assigned(self):
        return mock_sbs.get_ship_of_client(C1)

    def test_the_console_is_put_back_on_its_own_ship(self):
        from sbs_utils.procedural.gui.cutscene import cutscene_play
        ship = self.subject(0, 0, 0, radius=95)         # the crew ship
        station = self.subject(9000, 0, 9000, radius=220)   # what the reveal holds on
        mock_sbs.assign_client_to_ship(C1, ship)
        self.assertEqual(self.assigned(), ship)

        cutscene_play([{"subject": station, "framing": "wide", "seconds": 1}], to=C1)
        self.assertEqual(self.assigned(), station,
                         "the shot must ride its subject while it plays")
        for _ in range(int(2 * mock_sbs.TICKS_PER_SECOND) + 2):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1
        self.assertEqual(self.assigned(), ship,
                         "when it ends the console rides its own ship again")

    def test_a_skipped_cutscene_puts_it_back_too(self):
        from sbs_utils.procedural.gui.cutscene import cutscene_play, cutscene_skip
        ship = self.subject(0, 0, 0, radius=95)
        station = self.subject(9000, 0, 9000, radius=220)
        mock_sbs.assign_client_to_ship(C1, ship)
        cutscene_play([{"subject": station, "framing": "wide", "seconds": 30}], to=C1)
        cutscene_skip(C1)
        TickDispatcher.dispatch_tick()
        self.assertEqual(self.assigned(), ship,
                         "a bridge crew that skips still gets its own ship back")

    def test_release_false_leaves_the_camera_alone(self):
        from sbs_utils.procedural.gui.cutscene import cutscene_define, cutscene_play
        ship = self.subject(0, 0, 0, radius=95)
        station = self.subject(9000, 0, 9000, radius=220)
        mock_sbs.assign_client_to_ship(C1, ship)
        cutscene_define("held", [{"subject": station, "framing": "wide", "seconds": 1}],
                        release=False)
        cutscene_play("held", to=C1)
        for _ in range(int(2 * mock_sbs.TICKS_PER_SECOND) + 2):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1
        self.assertEqual(self.assigned(), station,
                         "release=False means the caller is taking over - do not undo it")
