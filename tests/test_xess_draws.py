"""The xESS actually DRAWS - measured, not asserted from the source.

Every other test of this device reads its state or its source. None of them builds the
screen, and the file they replaced said so outright: "nothing in this file builds the
screen for real". That gap is where both of the bugs Doug reported from the engine lived.
A style key the engine ignores, a region pinned over a flow row, a widget that draws but
never becomes clickable - none of them is visible until something presents.

So this presents. It records the rects the page really emits
(`send_gui_text` / `send_gui_clickregion`), and checks the four things that would
otherwise only show on a bridge:

  * the identity bar and the app area do not overlap A SINGLE PIXEL;
  * every tile emits a CLICK REGION, not just words - the failure mode of the strip this
    replaced was a widget that drew and did nothing;
  * clicking a tile opens that app, and the app's own content appears;
  * Back comes home.

The recorder and the `Gui.on_message` click are lifted from LM's
`consoles/test_manual_beams_panel.py`, which is the template for driving a real panel
headless.
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
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.gui import boarding_console as C
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.spawn import npc_spawn, player_spawn

CID = 1

#: The console under test, as a story. Deliberately tiny - the builder is the subject and
#: the console around it is not.
STORY = """
gui_boarding_console()
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
        """Record BUTTONS as well as texts.

        A button goes out through `send_gui_button`, not `send_gui_text` - so a recorder
        that watches only text sees a FIRE app with no settings on it and a CREW app with
        no ship, and reports both as product bugs. It said exactly that on the first run
        of this file.
        """
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
        # THE CLIENT AGENT FIRST. Every per-console value in this design - who you are
        # holding, which app is open, whether the weapon is armed - is inventory ON THE
        # CLIENT, and `set_inventory_value` for a client with no agent goes nowhere and
        # says nothing. Without this the fixture looked right and `boarding_where` came
        # back None, so SCAN and FIRE had no tiles and three tests passed by iterating an
        # empty list.
        # REGISTERED WITH Gui, not merely constructed. `Gui.push` looks the client up in
        # `Gui.clients` and CREATES A NEW ONE when it is not there - same id, so the new
        # agent replaces the old in `Agent.all` and every per-console value written
        # before the first push is gone. The fixture then reads as a console holding
        # nobody: "aboard" in the bar, no SCAN or FIRE tile, and an app opened just
        # before the build drawing the tile sheet instead.
        Gui.clients[CID] = GuiClient(CID)
        A.boarding_clear()
        B.boarding_site_clear()
        X.xess_clear()
        self.addCleanup(X.xess_clear)
        self.addCleanup(B.boarding_site_clear)

        self.ship = to_object(player_spawn(0, 0, 0, "Artemis", "tsn",
                                           "tsn_light_cruiser"))
        self.site = to_object(npc_spawn(3000, 0, 3000, "Kepler", "tsn",
                                        "tsn_destroyer", "behav_station"))
        B.boarding_site_build(self.site)
        self.who = lifeform_spawn("Lt Marek", "terran_male", "boarding,science")
        A.boarding_invite(self.ship, [self.who], title="Kepler")
        A.boarding_beam_down(CID, self.who)
        self.fig = B.boarding_figure_spawn(self.site, self.who, 3, 1)
        B.boarding_take(CID, self.fig, self.site)

        self.emitted = _Emitted()
        self.emitted.install()
        self.addCleanup(self.emitted.remove)

        story = MastStory()
        errors = story.compile(STORY, "xessconsole", story)
        self.assertEqual([], errors, "compile errors: %s" % errors)
        story.compiler_errors = []
        ConsolePage.story = story
        FrameContext.mast = story

        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        # StoryScheduler OVERRIDES `runtime_error`, so patching that binds a method
        # nothing calls and every assertion below would be vacuous. The class-level
        # `on_runtime_error` seam is what the story scheduler actually fires.
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
        """(Re)build the console from the CURRENT state and record what it draws.

        A fresh page, because a repaint re-emits the layout tree it already has - it does
        not re-run the builder, and it is the builder that reads the device's state.

        The CLIENT is not recreated with it: `Gui.clients = {}` here would drop the
        GuiClient agent and take every per-console value in the fixture with it.
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
        """The plainest thing there is, and nothing has ever asserted it."""
        self.build()
        self.assertTrue(self.emitted.texts, "the console drew nothing at all")

    def test_it_says_who_you_are_and_where(self):
        self.build()
        self.assertTrue(self.emitted.saying("Lt Marek"), "no name in the identity bar")
        self.assertTrue(self.emitted.saying("science"), "no job in the identity bar")

    def test_a_console_with_no_character_still_draws(self):
        """An observer is an ordinary state - it is what the main screen is."""
        A.boarding_beam_up(CID)
        self.build()
        self.assertTrue(self.emitted.saying("Observer"))


class TheBandsDoNotOverlapAPixel(_DrawBase):
    """The bug Doug reported as "text overlaps", measured at last.

    Every earlier version of this test compared the AREA STRINGS. Strings agreeing is not
    the same claim as rectangles not intersecting: the strings were only ever evidence
    for it, and the thing that actually went wrong on a bridge was pixels.
    """

    def _rects(self):
        """Every text rect, as (top, bottom), ignoring zero-height ones."""
        return [(t[3], t[5]) for t in self.emitted.texts if t[5] > t[3]]

    def test_nothing_in_the_app_area_is_drawn_inside_the_bar(self):
        self.build()
        bar = [t for t in self.emitted.texts if "Lt Marek" in (t[1] or "")]
        self.assertTrue(bar, "the identity bar did not draw")
        bar_bottom = bar[0][5]
        # Everything on the device that is NOT the bar starts at or below its bottom
        # edge. A widget above that line is a widget painted into the bar.
        left = C.panel_left()
        below = [t for t in self.emitted.texts
                 if t[2] >= left and t[3] > bar[0][3] and t[5] > t[3]]
        for tag, props, l, top, r, bottom in below:
            self.assertGreaterEqual(
                top + 0.001, bar_bottom,
                "a widget at top=%s is inside the identity bar (bottom=%s): %r"
                % (top, bar_bottom, props[:60]))

    def test_the_NAME_HAS_A_ROW_TO_ITSELF(self):
        """A long name used to share its line with the job and the room, wrap, and
        drop its second half out of the bar and over the app below - the engine does
        not clip. A name's length is not ours to control: it arrives from a roster,
        an auto-namer or a mission, and the one Doug hit was "Lieutenant Lt Mira
        Okonkwo".

        So this measures with a name long enough to have wrapped: the name's row and
        the job's row must not overlap vertically, and both must stay in the bar."""
        to_object(self.who).name = "Lieutenant Lt Mira Okonkwo"
        self.build()
        name = self.emitted.saying("Okonkwo")
        job = self.emitted.saying("science")
        self.assertTrue(name, "the name did not draw")
        self.assertTrue(job, "the job did not draw")
        self.assertLessEqual(name[0][5], job[0][3] + 0.001,
                             "the name and the job share a line, so a long name "
                             "wraps out of the bar")

    def test_and_a_long_name_stays_OUT_OF_the_app_area(self):
        """Measured against what is actually drawn in the app area rather than
        against the area string - the string was right the whole time; what went
        wrong was a widget spilling past it."""
        to_object(self.who).name = "Lieutenant Lt Mira Okonkwo"
        self.build()
        head = self.emitted.saying("xESS")
        self.assertTrue(head, "the app area drew no heading to measure against")
        app_top = head[0][3]
        for tag, props, l, top, r, bottom in self.emitted.saying("Okonkwo"):
            self.assertLessEqual(bottom, app_top + 0.001,
                                 "the name overflows the bar into the app area")

    def test_the_bar_is_not_the_full_height_of_the_column(self):
        """The guard on the guard: a bar that filled the column would pass the test
        above by having nothing below it to fail."""
        self.build()
        bar = [t for t in self.emitted.texts if "Lt Marek" in (t[1] or "")][0]
        below = [t for t in self.emitted.texts
                 if t[2] >= C.panel_left() and t[3] >= bar[5] and t[5] > t[3]]
        self.assertTrue(below, "nothing was drawn in the app area")

    def test_the_map_and_the_device_do_not_share_a_column(self):
        self.build()
        left = C.panel_left()
        for tag, props, l, top, r, bottom in self.emitted.texts:
            if l < left:
                continue
            self.assertGreaterEqual(r, l, props[:40])


class EveryTileIsActuallyClickable(_DrawBase):
    """The failure mode this device already shipped once: a widget that DRAWS and never
    becomes clickable, because the click properties were written as style keys, which the
    engine silently ignores. Reported as "the SCAN and FIRE tabs do nothing"."""

    def test_all_four_apps_are_offered(self):
        """THE GUARD ON THE GUARD, and it is not hypothetical. Every sweep below walks
        `xess_apps(CID)`, so an empty list passes them all - and the first run of this
        file did exactly that, with SCAN and FIRE missing because the fixture's client
        had lost its inventory. A vacuous pass is worse than a failure."""
        self.assertEqual({X.APP_CREW, X.APP_ACT, X.APP_SCAN, X.APP_FIRE},
                         {a["key"] for a in X.xess_apps(CID)})

    def test_each_app_emits_a_click_region(self):
        self.build()
        tags = self.emitted.click_tags()
        self.assertEqual(4, len(X.xess_apps(CID)), "the sweep below would be vacuous")
        for app in X.xess_apps(CID):
            self.assertIn("xess-app-%s" % app["key"], tags,
                          "the %s tile draws but cannot be pressed" % app["key"])

    def test_the_tiles_say_their_names(self):
        self.build()
        for app in X.xess_apps(CID):
            self.assertTrue(self.emitted.saying(app["title"]),
                            "no tile for %s" % app["key"])


class PressingATileOpensThatApp(_DrawBase):
    def test_fire_opens_the_weapon(self):
        self.build()
        self.click("xess-app-fire")
        self.assertEqual(X.APP_FIRE, X.xess_opened(CID))
        self.build()
        self.assertTrue(self.emitted.saying("SAFE"),
                        "FIRE opened but drew none of its own content")

    def test_and_the_three_settings_are_all_offered(self):
        X.xess_open(CID, X.APP_FIRE)
        self.build()
        for setting in B.boarding_settings():
            self.assertTrue(self.emitted.saying(setting.upper()), setting)

    def test_crew_opens_and_lists_the_ship(self):
        self.build()
        self.click("xess-app-crew")
        self.assertEqual(X.APP_CREW, X.xess_opened(CID))
        self.build()
        self.assertTrue(self.emitted.saying("Artemis"),
                        "the ship is not on the list that carries Beam up")

    def test_scan_reads_the_room(self):
        X.xess_open(CID, X.APP_SCAN)
        self.build()
        self.assertTrue(self.emitted.texts)

    def test_act_draws_when_a_beat_is_open(self):
        A.boarding_metric_install()
        scenes = {"lab": {"key": "lab", "display_text": "lab",
                          "description": ("% Containment has failed.\n"
                                          "- [Examine the gel](lab)\n"),
                          "data": {"speaker": "outpost"}}}
        A.boarding_scene_begin(scenes, "lab", speaker="outpost")
        self.assertTrue(A.boarding_choices(CID), "fixture produced no choices")
        X.xess_open(CID, X.APP_ACT)
        self.build()
        self.assertTrue(self.emitted.saying("Examine the gel"),
                        "the choice was not drawn as a row")

    def test_every_app_draws_something_without_raising(self):
        """The broadest sweep there is, and the cheapest. An app that throws is caught
        and reported rather than taking the console down - so this asserts on the
        RUNTIME ERRORS as well, or a silently-handled crash would read as a pass."""
        for app in X.xess_apps(CID):
            X.xess_open(CID, app["key"])
            self.build()
            self.assertTrue(self.emitted.texts, "%s drew nothing" % app["key"])


class NoRowAsksForASizeThatIsNotOne(_DrawBase):
    """`1fr` IS THE ONLY FLEX SPELLING (`parsers.py` MODES). `2fr` is not "twice the
    share" - it lexes as the NUMBER 2, which is 2% of SCREEN HEIGHT, about 15px at 720p.
    No error, no warning: the row just becomes a sliver.

    It shipped in ACT, and Doug reported it as "the ACT buttons are at the bottom and
    less than 20 pixels", which is 2% measured with an eye. The source check is the cheap
    guard; the measured one below is the guard that does not care how it is spelled.
    """

    def test_no_builder_writes_a_bare_Nfr(self):
        """CODE ONLY - comment lines are stripped first, because the comment that
        explains this bug necessarily contains the bug's own spelling.

        The first version of this test was VACUOUS in a way worth recording: it was
        written through a shell heredoc, where the `\b` of the regex became a literal
        BACKSPACE byte, so the pattern required a 0x08 after "fr" and could never match
        anything. It passed on the bug and on the fix alike. Regexes do not go through
        heredocs.
        """
        import inspect
        import re
        code = "\n".join(ln for ln in inspect.getsource(X).splitlines()
                         if not ln.lstrip().startswith("#"))
        bad = [n for n in re.findall(r"row-height:\s*(\d+)fr", code) if n != "1"]
        self.assertEqual([], bad, "not a size - only `1fr` flexes: %sfr" % bad)

    def test_the_choices_are_ON_THE_SCREEN(self):
        """THE MEASURED FORM - and the height was never the discriminator, the POSITION
        was. With the broken row the choices laid out at y=99.6..103.5: below the bottom
        edge of the screen, which is why only one of the two drew at all and why what was
        left read as a sliver. The row's own height was a perfectly normal 3.96% the
        whole time, so the first version of this test - which measured height - passed on
        the bug.

        "Inside the band it was given" is also the general invariant, and it does not
        care how the next version of this bug is spelled."""
        A.boarding_metric_install()
        scenes = {"lab": {"key": "lab", "display_text": "lab",
                          "description": ("% Containment on bench three has failed, and "
                                          "the gel is cold, and the seal was opened from "
                                          "the inside, at some length.\n"
                                          "- [Examine the gel](lab)\n"
                                          "- [Read the manifest](lab)\n"),
                          "data": {"speaker": "outpost"}}}
        A.boarding_scene_begin(scenes, "lab", speaker="outpost")
        self.assertTrue(A.boarding_choices(CID), "fixture produced no choices")
        X.xess_open(CID, X.APP_ACT)
        self.build()
        wanted = ("Examine the gel", "Read the manifest")
        rows = [t for t in self.emitted.texts
                if any(w in (t[1] or "") for w in wanted)]
        self.assertEqual(len(wanted), len(rows),
                         "only %d of %d choices drew - the band is too small to hold "
                         "them" % (len(rows), len(wanted)))
        for tag, props, l, top, r, bottom in rows:
            self.assertLessEqual(bottom, 100.0,
                                 "a choice is drawn off the bottom of the screen "
                                 "(%.2f): %r" % (bottom, props[:40]))
            self.assertGreaterEqual(top, 0.0, props[:40])


class AButtonDoesNotNEED_THE_AMBIENT_PAGE(_DrawBase):
    """`MessageHandler.on_message` calls a callable handler as `self.handler()` -
    with NO ARGUMENTS (button.py:90). `data=` reaches MAST task variables and never
    a Python callable, so a handler reading `sender.data` is handed an empty dict
    and every value in it is None.

    IT FAILS SILENTLY AND INTERMITTENTLY, which is what made it expensive: the
    handlers fell back to the ambient page for the client, so a button worked
    whenever `FrameContext.page` happened to be this console's and did nothing when
    it was not. Reported as "Back does nothing on the first run, then beam up and
    down and it works" and "the FIRE app doesn't work at all".

    An earlier version of this file "clicked Back" and passed - through the same
    ambient-page fallback. So every press here is made with THE PAGE CLEARED, which
    is the only form that distinguishes a bound handler from a lucky one.
    """

    def press(self, label):
        """Press the button whose label contains `label`, with no ambient page."""
        hits = [t for t in self.emitted.texts if label in (t[1] or "")]
        self.assertTrue(hits, "no button labelled %r was drawn" % label)
        page, task = FrameContext.page, FrameContext.task
        FrameContext.page = None
        FrameContext.task = None
        try:
            self.click(hits[0][0])
        finally:
            FrameContext.page, FrameContext.task = page, task

    def test_BACK_comes_home(self):
        X.xess_open(CID, X.APP_FIRE)
        self.build()
        self.press("Back")
        self.assertIsNone(X.xess_opened(CID))

    def test_ARM_arms_THIS_console(self):
        X.xess_open(CID, X.APP_FIRE)
        self.build()
        self.press("Arm")
        self.assertTrue(B.boarding_armed(CID))

    def test_MAKE_SAFE_disarms(self):
        X.xess_open(CID, X.APP_FIRE)
        B.boarding_arm(CID, B.SETTING_CUT)
        self.build()
        self.press("Make safe")
        self.assertFalse(B.boarding_armed(CID))

    def test_each_SETTING_button_picks_its_OWN_setting(self):
        """Built in a loop, so a closure over the loop variable would leave every
        button picking the last setting - and there is no event to tell them apart.
        """
        for value in B.boarding_settings():
            X.xess_open(CID, X.APP_FIRE)
            self.build()
            self.press(value.upper())
            self.assertEqual(value, B.boarding_setting(CID))

    def test_picking_a_setting_does_NOT_arm(self):
        """Two decisions. Changing your mind about the setting must not be a shot."""
        X.xess_open(CID, X.APP_FIRE)
        self.build()
        self.press("CUT")
        self.assertFalse(B.boarding_armed(CID))

    def test_BEAM_UP_releases_the_character(self):
        X.xess_open(CID, X.APP_CREW)
        self.build()
        self.press("Beam up")
        self.assertIsNone(A.boarding_me(CID))

    def test_a_CALL_button_actually_sends(self):
        from sbs_utils.procedural.messages import message_clear, messages_count
        message_clear()
        X.xess_open(CID, X.APP_CREW)
        self.build()
        before = messages_count()
        self.press("Report in")
        self.assertGreater(messages_count(), before, "nothing was sent")


class BackComesHome(_DrawBase):
    def test_every_app_offers_a_way_back(self):
        for app in X.xess_apps(CID):
            X.xess_open(CID, app["key"])
            self.build()
            self.assertTrue(self.emitted.saying("Back"),
                            "%s has no way back to the tiles" % app["key"])

    def test_and_the_tile_sheet_has_none_to_offer(self):
        """Home is home. A Back on the tile sheet would have nowhere to go."""
        X.xess_open(CID, None)
        self.build()
        self.assertFalse(self.emitted.saying("Back"))


if __name__ == "__main__":
    unittest.main()
