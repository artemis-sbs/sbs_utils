"""The EVA console, PRESENTED - not inspected.

`test_eva.py` asserts the suit and the route. This asserts the screen: the console is
built headless, every rect it emits is recorded, and the questions are the ones a reader
cannot answer by reading. The same harness as `test_xess_draws.py`, and for the same
reason - band overlap, a row asking for a size that is not a size, a tile with no click
region and a handler that only works while the ambient page happens to be right are all
invisible in source and obvious in the emitted rects.
"""
from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sys
import unittest

import cosmos_dev.mock.sbs as mock_sbs

# The GUI modules do `import sbs`, which only resolves inside the engine or under the
# mission runner. Bind it before importing anything that needs it.
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (registers the gui/route nodes)
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui, GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.gui import eva_console as EC
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.spawn import player_spawn

CID = 1
RELIC = "draw_relic"

STORY = """
gui_eva_console()
await gui()
"""


class ConsolePage(StoryPage):
    story = None


class _Emitted:
    """Every rect the page sent this present, by kind."""

    def __init__(self):
        self.texts = []
        self.clicks = []

    def install(self):
        # Buttons go out through `send_gui_button`, not `send_gui_text` - a recorder that
        # watches only text sees a Nav screen with no Hold station on it.
        self._orig = {}
        for name, sink in (("send_gui_text", self.texts),
                           ("send_gui_button", self.texts),
                           ("send_gui_clickregion", self.clicks)):
            self._orig[name] = getattr(mock_sbs, name)
            setattr(mock_sbs, name, self._recorder(sink, self._orig[name]))

    def remove(self):
        for name, fn in self._orig.items():
            setattr(mock_sbs, name, fn)

    def _recorder(self, sink, orig):
        def _fn(client_id, parent, tag, props, left, top, right, bottom):
            sink.append((tag, props or "", left, top, right, bottom))
            return orig(client_id, parent, tag, props, left, top, right, bottom)
        return _fn

    def clear(self):
        self.texts.clear()
        self.clicks.clear()

    def saying(self, needle):
        return [t for t in self.texts if needle in (t[1] or "")]

    def click_tags(self):
        return [c[0] for c in self.clicks]


class _DrawBase(unittest.TestCase):
    def setUp(self):
        clear_shared()
        SpaceObject.clear()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        FrameContext.task = None
        # THE CLIENT AGENT FIRST, and registered with Gui rather than merely constructed:
        # `Gui.push` creates a new one when the id is not in `Gui.clients`, which replaces
        # the agent and takes every per-console value written before the first push with
        # it. The fixture then reads as a console holding nobody.
        Gui.clients[CID] = GuiClient(CID)
        A.boarding_clear()
        E.eva_clear()
        V.volume_clear()
        X.xess_clear()
        self.addCleanup(X.xess_clear)
        self.addCleanup(E.eva_clear)
        self.addCleanup(V.volume_clear)

        V.volume_define(RELIC,
                        chambers={"mouth": (0, 0, 0, 300), "hall": (1000, 0, 0, 300)},
                        passages=[("mouth", "hall", 60)])
        from sbs_utils.procedural import amd_relics as R
        R._RELIC_RECORDS[RELIC] = {
            "key": RELIC, "loc": (0, 0, 0), "volume": RELIC,
            "points": {"the cradle": [1000, 0, 0, ["relic_piece"], "The Cradle"]},
        }
        self.addCleanup(R._RELIC_RECORDS.pop, RELIC, None)

        self.ship = to_object(player_spawn(0, 0, 0, "Artemis", "tsn",
                                           "tsn_light_cruiser"))
        self.who = lifeform_spawn("Lt Marek", "terran_male", "boarding,science")
        A.boarding_invite(self.ship, [self.who], title="The Relic")
        A.boarding_beam_down(CID, self.who)
        self.suit = E.eva_suit_spawn(self.who, RELIC, 0, 0, 0, hull="tsn_shuttle",
                                     side="tsn")
        E.eva_take(CID, self.suit, RELIC, volume=RELIC, home=self.ship)

        self.emitted = _Emitted()
        self.emitted.install()
        self.addCleanup(self.emitted.remove)

        story = MastStory()
        errors = story.compile(STORY, "evaconsole", story)
        self.assertEqual([], errors, "compile errors: %s" % errors)
        story.compiler_errors = []
        ConsolePage.story = story
        FrameContext.mast = story

        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.errors.append
        self.page = None

    def tearDown(self):
        MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        ConsolePage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        SpaceObject.clear()

    def build(self):
        """(Re)build from the CURRENT state and record what it draws.

        A fresh page, because a repaint re-emits the layout tree it already has - it does
        not re-run the builder, and it is the builder that reads the device's state.
        """
        Gui.widget_list_sent = {}
        self.page = ConsolePage()
        Gui.push(CID, self.page)
        self.present()
        return self.page

    def present(self):
        self.emitted.clear()
        mock_sbs.sim._time_tick_counter += 30
        self.page.gui_state = "repaint"
        self.page.present(FakeEvent(CID, "gui_present"))
        self.assertEqual([], self.errors, "runtime errors: %s" % self.errors)

    def click(self, click_tag):
        FrameContext.context = Context(mock_sbs.sim, mock_sbs,
                                       FakeEvent(CID, "gui_message"))
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=click_tag))


class ItDrawsWithoutRaising(_DrawBase):
    def test_the_console_builds(self):
        self.build()
        self.assertTrue(self.emitted.texts, "the console drew nothing at all")

    def test_it_says_who_you_are(self):
        self.build()
        self.assertTrue(self.emitted.saying("Lt Marek"), "no name in the identity bar")

    def test_the_bar_says_the_CHAMBER_not_aboard(self):
        """A boarder half a kilometre inside a ruin is not "aboard".

        The identity bar is shared with grid boarding, where "somewhere" means a room on
        a deck. Without the EVA fallback it has no answer for a suit and says the ship.
        """
        self.build()
        self.assertTrue(self.emitted.saying("mouth"),
                        "the bar does not name the chamber: %s"
                        % [t[1] for t in self.emitted.texts])
        self.assertFalse(self.emitted.saying("aboard"))


class TheViewIsAnEngineWidget(_DrawBase):
    def test_the_console_is_assigned_to_the_SUIT(self):
        """`3dview` draws whatever the client is ASSIGNED to.

        Re-aiming a camera without assigning is the documented way to get a black frame,
        so the console assigns rather than leaving it to the caller.
        """
        self.build()
        from sbs_utils.procedural.query import to_id
        self.assertEqual(mock_sbs.get_ship_of_client(CID), to_id(self.suit))

    def test_the_3dview_is_in_the_widget_list(self):
        self.build()
        sent = " ".join(str(v) for v in Gui.widget_list_sent.values())
        self.assertIn("3dview", sent)

    def test_the_view_does_not_share_a_row_with_the_device(self):
        """An engine widget draws at its own size over anything beside it.

        Measured as a gap in screen percent rather than by reading the area strings -
        strings agreeing is not the same as rects not overlapping.
        """
        self.build()
        left_edge = EC.MAP_WIDTH_DEFAULT
        for tag, props, left, _top, _right, _bottom in self.emitted.texts:
            self.assertGreaterEqual(
                left, left_edge,
                "widget %r at x=%s is drawn over the 3d view" % (tag, left))


class TheCornerRadar(_DrawBase):
    """A 2D view tucked into the bottom-right of the 3D one.

    Third person tells a pilot what the room LOOKS like and almost nothing about where
    they are in it - a ruin's chambers all look alike from inside, which is the same
    problem the Nav marks exist for. The radar is the only thing that answers "what is
    around me, and which way is out".
    """

    def test_both_views_are_declared(self):
        """Two engine widgets are fine in SEPARATE areas - what they cannot do is share
        a row, because each draws at its own size over whatever is beside it."""
        self.build()
        sent = " ".join(str(v) for v in Gui.widget_list_sent.values())
        self.assertIn("3dview", sent)
        self.assertIn("2dview", sent)

    def test_it_can_be_turned_off(self):
        """A console that wants the whole column back says so once, at the build."""
        from sbs_utils.mast.maststory import MastStory
        story = MastStory()
        src = "gui_eva_console(radar=False)" + chr(10) + "await gui()" + chr(10)
        errors = story.compile(src, "evaconsole_noradar", story)
        self.assertEqual([], errors, "compile errors: %s" % errors)
        story.compiler_errors = []
        ConsolePage.story = story
        FrameContext.mast = story
        self.build()
        sent = " ".join(str(v) for v in Gui.widget_list_sent.values())
        self.assertIn("3dview", sent)
        self.assertNotIn("2dview", sent)

    def test_it_sits_inside_the_view_not_beside_it(self):
        """The whole point: it is ON the 3D view, so the view keeps the full column."""
        area = EC.eva_radar_area(EC.MAP_WIDTH_DEFAULT)
        nums = [int(n) for n in area.replace("area:", "").rstrip(";").split(",")]
        left, top, right, bottom = nums
        self.assertLess(right, EC.MAP_WIDTH_DEFAULT + 1,
                        "the radar spills out of the 3d view column")
        self.assertGreater(left, 0)
        self.assertGreater(bottom, top)

    def test_it_is_in_the_BOTTOM_RIGHT(self):
        area = EC.eva_radar_area(EC.MAP_WIDTH_DEFAULT)
        left, top, right, bottom = [int(n) for n in
                                    area.replace("area:", "").rstrip(";").split(",")]
        mid_x = EC.MAP_WIDTH_DEFAULT / 2.0
        self.assertGreater(left, mid_x, "not on the right half of the view")
        self.assertGreater(top, 50, "not in the bottom half of the view")

    def test_it_follows_the_map_width(self):
        """Measured off the SAME width the 3D view uses, so the two cannot drift."""
        narrow = EC.eva_radar_area(40)
        wide = EC.eva_radar_area(80)
        self.assertNotEqual(narrow, wide)
        n_right = int(narrow.replace("area:", "").rstrip(";").split(",")[2])
        w_right = int(wide.replace("area:", "").rstrip(";").split(",")[2])
        self.assertLess(n_right, 40 + 1)
        self.assertLess(w_right, 80 + 1)


class NavIsOnlyThereWhenYouAreFlying(_DrawBase):
    def test_the_nav_tile_is_offered_to_a_suit(self):
        self.build()
        self.assertIn("xess-app-nav", self.emitted.click_tags())

    def test_it_is_NOT_offered_without_one(self):
        """On a grid interior NAV has nothing to do, and a tile that cannot act is worse
        than no tile - it is a promise the device does not keep."""
        E.eva_release(CID)
        self.build()
        self.assertNotIn("xess-app-nav", self.emitted.click_tags())

    def test_opening_nav_lists_where_you_can_go(self):
        self.build()
        self.click("xess-app-nav")
        # BUILD, not present. A repaint re-emits the layout tree it already has - it does
        # not re-run the builder, and the builder is what reads which app is open.
        self.build()
        self.assertTrue(self.emitted.saying("The Cradle"),
                        "Nav listed nothing: %s" % [t[1] for t in self.emitted.texts])

    def test_nav_offers_back_like_every_other_app(self):
        X.xess_open(CID, X.APP_NAV)
        self.build()
        self.assertTrue(self.emitted.saying("Back"))

    def test_under_way_it_says_so_and_offers_to_stop(self):
        E.eva_goto(CID, "the cradle")
        X.xess_open(CID, X.APP_NAV)
        self.build()
        self.assertTrue(self.emitted.saying("Under way"))
        self.assertTrue(self.emitted.saying("Hold station"))


class TheCameraHoldsStill(_DrawBase):
    """A pilot's view, not a director's.

    Reported from a bridge 2026-09-17: "the cinematic camera may not be the right choice,
    the camera changing position is annoying." The cinematic director picks its own shots
    and keeps changing them, which is right for a cutscene and wrong for the one screen
    that has to show which way the suit is pointing.
    """

    def test_the_console_drives_its_own_lens(self):
        """The default is `third` - our rig - so the lens is placed by script rather than
        chosen by the engine."""
        self.build()
        self.assertEqual(mock_sbs._view_modes.get(CID, (None, None, None))[0], "3dview")
        self.assertEqual(mock_sbs._cinematic.get(CID, {}).get("script"), 1)

    def test_it_is_not_the_cinematic_director(self):
        """THE POINT OF THE REPORT, and it is about who PICKS the shot, not about the view
        mode's name. `scriptControlsCamera = 1` is the director being taken out of it;
        `gui_cinematic_auto` sends 0 and is what hands the picking back."""
        self.build()
        self.assertNotEqual(mock_sbs._cinematic.get(CID, {}).get("script"), 0,
                            "the engine's director is choosing the shot again")

    def test_the_lens_rides_the_suit_and_is_not_inside_it(self):
        """Dolly and target must be the SAME object or the frame is black, and a lens at
        zero offset sits inside the hull."""
        self.build()
        st = mock_sbs._cinematic.get(CID, {})
        self.assertEqual(st.get("dolly_id"), st.get("target_id"))
        self.assertNotEqual(tuple(st.get("dolly_off") or (0, 0, 0)), (0.0, 0.0, 0.0))

    def test_a_mission_can_choose_another(self):
        from sbs_utils.procedural.gui.eva_console import eva_camera_mode, CAMERA_MODE_DEFAULT
        self.addCleanup(eva_camera_mode, CAMERA_MODE_DEFAULT)
        eva_camera_mode("first_person")
        self.build()
        self.assertEqual(mock_sbs._view_modes.get(CID), ("3dview", "front", "first_person"))


class TheBadgeIsWhatMakesItRepaint(_DrawBase):
    def test_the_badge_carries_the_distance_left(self):
        """`gui_xess_tick` only rebuilds when `xess_revision` changes, and a suit crossing
        a chamber changes nothing else in that tuple. Without a badge that MOVES, the Nav
        screen freezes the moment a destination is pressed."""
        E.eva_goto(CID, "the cradle")
        # A badge provider takes NO arguments and finds its console from the ambient page,
        # so it only answers inside a build. Standing one up is what the real flow does.
        self.build()
        FrameContext.page = self.page
        before = X.xess_revision(CID)
        # ASSIGN the whole position. Mutating `pos.x` writes to a copy the engine hands
        # back and the ship never moves - which reads exactly like "the badge does not
        # change", the bug under test.
        from sbs_utils.vec import Vec3
        to_object(self.suit).pos = Vec3(600, 0, 0)
        self.assertNotEqual(X.xess_revision(CID), before)

    def test_holding_station_shows_no_badge(self):
        self.build()
        FrameContext.page = self.page
        self.assertEqual(X._nav_badge(), "")


if __name__ == "__main__":
    unittest.main()
