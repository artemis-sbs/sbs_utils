"""The viewscreen's data column - the pages, and the surface that shows them.

Phases 3-4 of VIEWSCREEN_PLAN.md. The pages are PURE functions of (subject, ship), so
most of this needs no page, no engine and no browser; the column tests below need a
client page because an overlay draws into one.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural.comms import (comms_history_add, comms_history_for,
                                        comms_history_clear, comms_history_size)
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.spawn import player_spawn, npc_spawn
from sbs_utils.procedural.science import science_update_scan_data
from sbs_utils.procedural.gui.viewscreen_pages import (
    viewscreen_pages, viewscreen_page_register, viewscreen_page_remove,
    viewscreen_page_names, viewscreen_relative_bearing, viewscreen_hull_percent)
from sbs_utils.procedural.gui.viewscreen import (viewscreen_set, viewscreen_clear,
                                                 COLUMN_SLOT, _VIEWERS, _column_update)


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


class PagesBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        comms_history_clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.foe = to_id(npc_spawn(3000, 0, 0, "Kraken", "raider", "battle",
                                   "behav_npcship"))

    def tearDown(self):
        comms_history_clear()
        FrameContext.context = None

    def page_named(self, name):
        for n, text in viewscreen_pages(self.foe, self.ship):
            if n == name:
                return text
        return None


class TestPages(PagesBase):
    def test_vitals_names_the_subject(self):
        text = self.page_named("vitals")
        self.assertIsNotNone(text)
        self.assertIn("Kraken", text)

    def test_vitals_reports_the_range(self):
        text = self.page_named("vitals")
        self.assertIn("Range", text)

    def test_an_unscanned_object_has_no_science_page(self):
        """Nothing scanned must not page onto an empty screen."""
        names = [n for n, _ in viewscreen_pages(self.foe, self.ship)]
        self.assertNotIn("science", names)

    def test_a_scanned_tab_becomes_the_science_page(self):
        science_update_scan_data(self.ship, self.foe, "Hull breach on deck 4", "scan")
        text = self.page_named("science")
        self.assertIsNotNone(text, "a scanned tab did not become a page")
        self.assertIn("Hull breach", text)

    def test_every_scanned_tab_is_on_that_one_page(self):
        """The whole point of the change: a contact scanned on three tabs must not read
        as a contact scanned on one, which is what a page-per-tab slideshow did."""
        science_update_scan_data(self.ship, self.foe, "Reads hot", "scan")
        science_update_scan_data(self.ship, self.foe, "Crew of nine", "intel")
        science_update_scan_data(self.ship, self.foe, "Shields at 40 percent", "status")
        text = self.page_named("science")
        self.assertIn("Reads hot", text)
        self.assertIn("Crew of nine", text)
        self.assertIn("Shields at 40 percent", text)

    def test_each_tab_is_labelled(self):
        science_update_scan_data(self.ship, self.foe, "Reads hot", "scan")
        science_update_scan_data(self.ship, self.foe, "Crew of nine", "intel")
        text = self.page_named("science")
        self.assertIn("## Scan", text)
        self.assertIn("## Intel", text)

    def test_unscanned_tabs_leave_no_empty_heading(self):
        science_update_scan_data(self.ship, self.foe, "Reads hot", "scan")
        text = self.page_named("science")
        self.assertNotIn("## Materials", text)
        self.assertNotIn("## Bio", text)

    def test_there_is_only_one_science_page(self):
        for tab in ("scan", "status", "intel", "mat", "bio"):
            science_update_scan_data(self.ship, self.foe, "something", tab)
        names = [n for n, _ in viewscreen_pages(self.foe, self.ship)]
        self.assertEqual(names.count("science"), 1)

    def test_comms_page_shows_what_was_said(self):
        comms_history_add(self.ship, self.foe,
                          {"from_name": "Kraken", "message": "Stand down", "receive": True})
        text = self.page_named("comms")
        self.assertIsNotNone(text)
        self.assertIn("Stand down", text)

    def test_comms_page_is_per_pair(self):
        other = to_id(npc_spawn(9000, 0, 0, "Vega", "tsn", "battle", "behav_npcship"))
        comms_history_add(self.ship, other, {"from_name": "Vega", "message": "Nothing to do with the Kraken"})
        self.assertIsNone(self.page_named("comms"))

    def test_pages_are_ordered(self):
        """Vitals first - it is what the crew looks at before anything else."""
        science_update_scan_data(self.ship, self.foe, "Reads hot", "scan")
        names = [n for n, _ in viewscreen_pages(self.foe, self.ship)]
        self.assertEqual(names[0], "vitals")
        self.assertEqual(names[1], "science")

    def test_nothing_at_all_gives_no_pages(self):
        self.assertEqual(viewscreen_pages(0, self.ship), [])


class TestPageRegistry(PagesBase):
    def tearDown(self):
        viewscreen_page_remove("test_page")
        super().tearDown()

    def test_a_mission_can_add_a_page(self):
        viewscreen_page_register("test_page", lambda s, sh: "# Cargo\n\nOre", order=99)
        self.assertEqual(self.page_named("test_page"), "# Cargo\n\nOre")

    def test_order_places_it(self):
        viewscreen_page_register("test_page", lambda s, sh: "first", order=1)
        names = [n for n, _ in viewscreen_pages(self.foe, self.ship)]
        self.assertEqual(names[0], "test_page")

    def test_a_page_returning_none_is_not_shown(self):
        viewscreen_page_register("test_page", lambda s, sh: None)
        self.assertNotIn("test_page", [n for n, _ in viewscreen_pages(self.foe, self.ship)])

    def test_a_page_that_raises_does_not_take_the_column_down(self):
        """One mission page with a bad key must not blank the whole viewer."""
        def boom(subject, ship):
            raise KeyError("nope")
        viewscreen_page_register("test_page", boom)
        names = [n for n, _ in viewscreen_pages(self.foe, self.ship)]
        self.assertNotIn("test_page", names)
        self.assertIn("vitals", names, "a raising page took the good pages with it")

    def test_registering_a_name_twice_replaces_it(self):
        viewscreen_page_register("test_page", lambda s, sh: "one")
        viewscreen_page_register("test_page", lambda s, sh: "two")
        self.assertEqual(self.page_named("test_page"), "two")
        self.assertEqual(viewscreen_page_names().count("test_page"), 1)


class TestMeasurements(PagesBase):
    def test_bearing_is_relative_to_our_heading(self):
        """0 is dead ahead, degrees clockwise - the engine's own convention, taken
        from the forward/right vectors rather than assumed from an axis."""
        b = viewscreen_relative_bearing(self.foe, self.ship)
        self.assertIsNotNone(b)
        self.assertTrue(0 <= b < 360)

    def test_bearing_of_something_that_is_not_there(self):
        self.assertIsNone(viewscreen_relative_bearing(0, self.ship))

    def test_hull_of_an_undamaged_ship(self):
        pct = viewscreen_hull_percent(self.foe)
        if pct is not None:            # the mock may expose no system damage at all
            self.assertEqual(pct, 100)


class TestCommsHistory(PagesBase):
    def test_it_keeps_what_comms_message_only_emitted(self):
        comms_history_add(self.ship, self.foe, {"message": "one"})
        comms_history_add(self.ship, self.foe, {"message": "two"})
        got = [e["message"] for e in comms_history_for(self.ship, self.foe)]
        self.assertEqual(got, ["one", "two"])

    def test_limit_takes_the_most_recent(self):
        for i in range(5):
            comms_history_add(self.ship, self.foe, {"message": str(i)})
        got = [e["message"] for e in comms_history_for(self.ship, self.foe, limit=2)]
        self.assertEqual(got, ["3", "4"])

    def test_it_is_capped(self):
        from sbs_utils.procedural.comms import COMMS_HISTORY_CAP
        for i in range(COMMS_HISTORY_CAP + 10):
            comms_history_add(self.ship, self.foe, {"message": str(i)})
        self.assertEqual(len(comms_history_for(self.ship, self.foe)), COMMS_HISTORY_CAP)

    def test_the_container_is_declared_to_the_reset_audit(self):
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("comms history", _RESET_PROBES)

    def test_clear_empties_it(self):
        comms_history_add(self.ship, self.foe, {"message": "one"})
        self.assertEqual(comms_history_size(), 1)
        comms_history_clear()
        self.assertEqual(comms_history_size(), 0)


class TestColumn(unittest.TestCase):
    """The surface. An overlay draws into a client PAGE, so this needs one."""

    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _VIEWERS.clear()
        comms_history_clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

        self.cid = 0x8000000000000001
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = self.cid
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(self.cid)          # self-registers under Agent.get(cid)
        client.page_stack.append(self.page)

        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.foe = to_id(npc_spawn(3000, 0, 0, "Kraken", "raider", "battle",
                                   "behav_npcship"))
        add_role(self.cid, "console")
        add_role(self.cid, "mainscreen")
        link(self.ship, "consoles", self.cid)
        mock_sbs.assign_client_to_ship(self.cid, self.ship)

    def tearDown(self):
        TickDispatcher.clear()
        _VIEWERS.clear()
        comms_history_clear()
        FrameContext.page = None
        FrameContext.context = None

    def slot(self):
        return self.page.overlays.slots.get(COLUMN_SLOT)

    def test_the_widget_list_comes_from_our_own_ship_not_the_subject(self):
        """gui_console("mainscreen") picks 3dview-vs-2dview from MAIN_SCREEN_VIEW. Read
        off get_ship_of_client mid-shot that is the SUBJECT's state, so a tactical
        viewer would rebuild itself as a 3D one (or worse, take the enemy's view)."""
        from sbs_utils.procedural.gui.console import gui_console
        # An orbit is the case where it bites: the console is ASSIGNED to the subject,
        # so get_ship_of_client answers with the enemy. Give the enemy a main-screen
        # state of its own and the two answers diverge - ours wants 3dview (an orbit
        # is a 3D shot), the enemy's says tactical.
        viewscreen_set(self.ship, "orbit", self.foe)
        set_inventory_value(self.foe, "MAIN_SCREEN_VIEW", "tactical")
        FrameContext.page = self.page
        gui_console("mainscreen")
        self.assertIn("3dview", self.page.pending_widgets,
                      "the widget list was read off the SUBJECT's ship")

    def _catchup(self):
        """Run one pass of the overlay catch-up ticker."""
        from sbs_utils.procedural.gui.overlay import _CATCHUP
        t = _CATCHUP["task"]
        self.assertIsNotNone(t, "a live overlay arms the catch-up ticker")
        t.cb(t)

    def test_the_column_stops_following_a_console_that_left_the_screen(self):
        """THE leak. The column used to be addressed to a FROZEN list of client ids
        captured when the shot started, with no console-role narrowing - so after the
        crew changed that console to Helm the catch-up ticker kept re-delivering a
        science read-out onto it, once a second, immune to any clear. The id was
        still literally in the audience whatever role it now held."""
        from sbs_utils.procedural.gui.overlay import overlay_clear_console
        from sbs_utils.procedural.roles import remove_role
        viewscreen_set(self.ship, "orbit", self.foe)
        record = _VIEWERS[self.ship]
        self.assertIsNotNone(self.slot().content)

        remove_role(self.cid, "mainscreen")          # this console is Helm now
        overlay_clear_console(self.cid)              # the transition door

        # Both ways the column re-asserts itself: the once-a-second page refresh,
        # and the catch-up ticker. Neither may reach a console that is no longer
        # one of this ship's main screens.
        record["shown"] = None                       # force the next update to send
        _column_update(record, force=True)
        self._catchup()

        region = self.slot()
        self.assertTrue(region is None or not region.content,
                        "the data column came back on a console that is no longer a "
                        "main screen")

    def test_a_console_taking_the_screen_mid_shot_is_caught_up(self):
        """The other half of the same change: the audience is the SHIP's main
        screens, re-resolved, so a console arriving after the shot started gets the
        column. A frozen id list could never grow."""
        late = 0x8000000000000002
        page = StoryPage()
        page.pending_gui = False
        page.client_id = late
        page.gui_task = _FakeGuiTask(page)
        client = GuiClient(late)
        client.page_stack.append(page)

        viewscreen_set(self.ship, "orbit", self.foe)
        self.assertIsNone(page.overlays.slots.get(COLUMN_SLOT))

        add_role(late, "console")
        add_role(late, "mainscreen")
        link(self.ship, "consoles", late)
        self._catchup()

        region = page.overlays.slots.get(COLUMN_SLOT)
        self.assertIsNotNone(region, "the late main screen never got the column")
        self.assertIn("Kraken", region.content["text"])

    def test_a_shot_puts_the_column_on_screen(self):
        viewscreen_set(self.ship, "orbit", self.foe)
        region = self.slot()
        self.assertIsNotNone(region, "no data column")
        self.assertIn("Kraken", region.content["text"])

    def test_tactical_gets_a_column_too(self):
        viewscreen_set(self.ship, "tactical", self.foe)
        self.assertIsNotNone(self.slot())

    def test_standing_down_takes_it_away(self):
        viewscreen_set(self.ship, "orbit", self.foe)
        viewscreen_clear(self.ship)
        region = self.slot()
        self.assertTrue(region is None or not region.content,
                        "the column outlived the shot")

    def test_one_page_does_not_cycle(self):
        viewscreen_set(self.ship, "orbit", self.foe)
        record = _VIEWERS[self.ship]
        self.assertEqual(record["page"], 0)
        FrameContext.context.sim._time_tick_counter += 30 * 60
        _column_update(record)
        self.assertEqual(record["page"], 0, "a single page paged away from itself")

    def test_more_than_one_page_advances_when_the_dwell_runs_out(self):
        science_update_scan_data(self.ship, self.foe, "Reads hot and getting hotter",
                                 "scan")
        viewscreen_set(self.ship, "orbit", self.foe)
        record = _VIEWERS[self.ship]
        self.assertEqual(record["page"], 0)
        FrameContext.context.sim._time_tick_counter += 30 * 60   # 60 sim seconds
        _column_update(record)
        self.assertEqual(record["page"], 1, "the slideshow did not advance")

    def test_a_changed_value_re_shows_the_same_page(self):
        """What keeps a live value live on a single-page column that never advances."""
        viewscreen_set(self.ship, "orbit", self.foe)
        record = _VIEWERS[self.ship]
        before = record["shown"]
        self.assertFalse(_column_update(record), "re-sent an unchanged column")
        from sbs_utils.vec import Vec3
        to_object(self.foe).pos = Vec3(40000, 0, 0)      # the range on the page changes
        self.assertTrue(_column_update(record), "a changed range was not re-sent")
        self.assertNotEqual(record["shown"], before)


if __name__ == "__main__":
    unittest.main()
