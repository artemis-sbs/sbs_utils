"""Audience resolution (`to` as a ship / side / mixed set) + the announce() pairing.

Two things under test:
- ``consoles_of`` — overlays draw on CONSOLES but authors hold ships and sides, so
  `to` accepts any of them. A ship resolves through its "consoles" link; a side
  through its members' consoles; a mixed set unions elementwise.
- ``announce`` — one call fires the level's overlay AND leaves the level's durable
  record, so information is never carried by a transient surface alone.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.gui.overlay import consoles_of, _pages_for
from sbs_utils.procedural.links import link
from sbs_utils.procedural.announce import announce, announce_headline


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    """Enough of a MAST gui task for the overlay builders and the info-panel
    message queue (which stores its cards in task variables)."""

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


class AudienceBase(unittest.TestCase):
    """Two player ships, each with two consoles (one of them a mainscreen)."""

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.pages = {}
        for cid in (0, 1001, 1002, 1003):
            page = StoryPage()
            page.pending_gui = False
            page.client_id = cid
            page.gui_task = _FakeGuiTask(page)
            client = GuiClient(cid)
            client.page_stack.append(page)
            client.add_role("console")
            self.pages[cid] = page
        Agent.get(1001).add_role("mainscreen")

        from sbs_utils.procedural.sides import side_ensure
        side_ensure("tsn", "TSN")
        from sbs_utils.procedural.spawn import player_spawn
        self.ship_a = player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser")
        self.ship_b = player_spawn(100, 0, 0, "Intrepid", "tsn", "tsn_light_cruiser")
        self.a_id, self.b_id = self.ship_a.id, self.ship_b.id
        link(self.a_id, "consoles", 1001)
        link(self.a_id, "consoles", 1002)
        link(self.b_id, "consoles", 1003)
        FrameContext.page = self.pages[0]

    def tearDown(self):
        # This fixture registers GuiClients (whose pages FrameContext.page falls
        # back to), ships and a side. Clear the whole agent registry so later test
        # modules don't inherit a live console page / fake gui task.
        FrameContext.page = None
        FrameContext.context = None
        Agent.clear()
        SpaceObject.clear()


class TestConsolesOf(AudienceBase):
    def test_none_is_current_console(self):
        self.assertEqual(consoles_of(None), {0})

    def test_client_id_passes_through(self):
        self.assertEqual(consoles_of(1001), {1001})

    def test_ship_resolves_to_its_consoles(self):
        self.assertEqual(consoles_of(self.a_id), {1001, 1002})

    def test_ship_object_resolves_too(self):
        self.assertEqual(consoles_of(self.ship_a), {1001, 1002})

    def test_side_key_resolves_to_all_member_consoles(self):
        # both ships are "tsn"; a side key is a plain string
        self.assertEqual(consoles_of("tsn"), {1001, 1002, 1003})

    def test_mixed_set_unions_ships_and_clients(self):
        self.assertEqual(consoles_of({self.a_id, 1003}), {1001, 1002, 1003})

    def test_console_filter_narrows_by_role(self):
        self.assertEqual(consoles_of(self.a_id, consoles="mainscreen"), {1001})

    def test_unknown_side_key_is_empty_not_an_error(self):
        self.assertEqual(consoles_of("no_such_side"), set())

    def test_server_zero_only_when_named(self):
        self.assertEqual(consoles_of(0), {0})
        self.assertNotIn(0, consoles_of(self.a_id))

    def test_ship_wins_over_its_side(self):
        # a ship must NOT widen into everyone on its side
        self.assertNotIn(1003, consoles_of(self.a_id))

    def test_pages_for_resolves_ship_to_pages(self):
        pages = _pages_for(self.a_id)
        self.assertEqual({p.client_id for p in pages}, {1001, 1002})

    def test_ship_id_no_longer_raises(self):
        # regression: gui_page_for_client used to AttributeError on a SpaceObject
        from sbs_utils.procedural.gui.gui import gui_page_for_client
        self.assertIsNone(gui_page_for_client(self.a_id))


class TestAnnounceHeadline(unittest.TestCase):
    def test_ascii_folds_and_collapses(self):
        self.assertEqual(announce_headline("Hold\n the  line — now"),
                         "Hold the line - now")

    def test_clamps_at_word_boundary(self):
        out = announce_headline("word " * 40)
        self.assertLessEqual(len(out), 63)
        self.assertTrue(out.endswith("..."))

    def test_strips_non_ascii(self):
        self.assertEqual(announce_headline("café ☃"), "caf")


class TestAnnouncePairs(AudienceBase):
    """Each level fires its overlay AND leaves its record on the same audience."""

    def _slots(self, cid):
        return self.pages[cid].overlays.slots

    def _logged(self):
        """Every log line, across scopes - announce logs at SHIP scope, and which id
        that is depends on how the mock links this console to its ship."""
        from sbs_utils.procedural import log_panel as LP
        out = []
        for tab in (LP.TAB_LOG,):
            for scope in list(LP._LOG.keys()):
                out += [e["text"] for e in LP.log_entries(scope, tab)]
        return out

    def _cards(self, cid):
        """The info-panel LOG for a console - the durable record half. announce()
        leaves the interrupting to the overlay, so its card is filed rather than
        queued live (see tests/test_info_panel_log.py)."""
        return self.pages[cid].gui_task.get_variable("$MESSAGES", [])

    def test_chapter_shows_hero_on_every_console_of_the_ship(self):
        announce("The long dark begins.", title="CHAPTER TWO",
                 level="chapter", ship=self.a_id)
        for cid in (1001, 1002):
            self.assertIn("center_hero", self._slots(cid))
            self.assertEqual(self._slots(cid)["center_hero"].content["title"], "CHAPTER TWO")
        self.assertNotIn("center_hero", self._slots(1003))   # other ship untouched

    def test_alert_shows_banner_and_keeps_a_card(self):
        announce("Raiders inbound", title="TSN Command", level="alert", ship=self.a_id)
        self.assertIn("top_banner", self._slots(1001))
        # the durable twin landed on the same consoles' info panel queue
        self.assertEqual(self._cards(1001)[0]["message"], "Raiders inbound")

    def test_status_is_a_LOG_line_and_no_overlay(self):
        """status/minor were the one pair of levels carrying information on a surface
        that kept no record - the corner toast. They are log lines now: visible in the
        ambient strip immediately, and still there when the crew looks back."""
        announce("Cargo ejected", level="status", ship=self.a_id)
        self.assertFalse(self._slots(1001), "status draws no overlay at all")
        self.assertEqual(self._cards(1001), [])
        self.assertIn("Cargo ejected", self._logged())

    def test_record_false_suppresses_the_twin(self):
        announce("Raiders inbound", level="alert", ship=self.a_id, record=False)
        self.assertIn("top_banner", self._slots(1001))
        self.assertEqual(self._cards(1001), [])

    def test_record_true_still_forces_a_card_on_a_status_level(self):
        """record=True has always meant "give this one a card". The default twin for
        status changed to the log; the escape hatch must still reach a card."""
        announce("Beacon built", level="status", ship=self.a_id, record=True)
        self.assertEqual(self._cards(1001)[0]["message"], "Beacon built")

    def test_consoles_filter_scopes_both_halves(self):
        announce("Visual contact", title="Ensign Rachel", level="chapter",
                 ship=self.a_id, consoles="mainscreen")
        self.assertIn("center_hero", self._slots(1001))
        self.assertNotIn("center_hero", self._slots(1002))

    def test_hail_uses_lower_third_and_shortens_the_line(self):
        announce("W" * 200, title="Admiral Harkin", level="hail",
                 ship=self.a_id, sender=self.b_id)
        content = self._slots(1001)["lower_third"].content
        self.assertEqual(content["name"], "Admiral Harkin")
        self.assertLessEqual(len(content["line"]), 93)

    def test_side_audience_reaches_both_ships(self):
        announce("War declared", level="alert", to="tsn")
        for cid in (1001, 1002, 1003):
            self.assertIn("top_banner", self._slots(cid))

    def test_unknown_level_falls_back_to_status(self):
        announce("something", level="bogus", ship=self.a_id)
        self.assertFalse(self._slots(1001))
        self.assertIn("something", self._logged())


if __name__ == "__main__":
    unittest.main()
