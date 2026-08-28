"""Overlay live-records are scoped to an AUDIENCE, not to a slot name.

Slot names are global strings - `viewer_data`, `hail_band`, `center_hero` - and
the late-joiner record used to be keyed by the slot alone. Two consequences, both
invisible with one player ship, which is all any other overlay test builds:

* the Intrepid raising a card OVERWROTE the Artemis's record for the same slot,
  so the Artemis's late console got nothing (or the wrong ship's content);
* a per-console clear dropped the record for EVERYBODY, cancelling an unrelated
  mission-wide card's catch-up delivery on consoles that never cleared anything.

Plus `overlay_clear_console`, the transition door: everything ONE console is
carrying, and nothing anyone else is.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.gui import GuiClient
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.gui.overlay import (
    _LIVE, _CATCHUP, _live_records_for, overlay_clear, overlay_clear_console,
    overlay_live_clear, overlay_register, overlay_show)


def _test_builder(client_id, content):
    from sbs_utils.procedural.gui.row import gui_row
    from sbs_utils.procedural.gui.text import gui_text
    gui_row("row-height: content;")
    gui_text("$text:" + str(content.get("title", "")) + ";")


overlay_register("scope_test", _test_builder)


class _FakeTicker:
    done = False


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)
        self.active_ticker = _FakeTicker()

    def done(self):
        return False

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None


class TwoBridges(unittest.TestCase):
    """Two player ships, two consoles each, and one spare that has joined nothing."""

    CIDS = (0, 1001, 1002, 2001, 2002, 3001)

    def setUp(self):
        from sbs_utils.spaceobject import SpaceObject
        from sbs_utils.procedural.links import link
        from sbs_utils.procedural.query import to_object
        from sbs_utils.procedural.spawn import player_spawn
        from sbs_utils.tickdispatcher import TickDispatcher

        sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        overlay_live_clear()
        self.addCleanup(overlay_live_clear)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

        self.pages = {}
        for cid in self.CIDS:
            page = StoryPage()
            page.pending_gui = False
            page.client_id = cid
            page.gui_task = _FakeGuiTask(page)
            client = GuiClient(cid)
            client.page_stack.append(page)
            self.pages[cid] = page

        self.artemis = to_object(player_spawn(0, 0, 0, "Artemis", "tsn",
                                              "tsn_light_cruiser"))
        self.intrepid = to_object(player_spawn(5000, 0, 0, "Intrepid", "tsn",
                                               "tsn_light_cruiser"))
        link(self.artemis.id, "consoles", 1001)
        link(self.intrepid.id, "consoles", 2001)
        FrameContext.page = self.pages[0]

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def _catchup(self):
        t = _CATCHUP["task"]
        self.assertIsNotNone(t, "a live overlay arms the catch-up ticker")
        t.cb(t)

    def _content(self, cid, slot="center_hero"):
        r = self.pages[cid].overlays.slots.get(slot)
        return None if r is None else r.content


class TestTwoShipsShareASlotName(TwoBridges):

    def test_the_second_ship_does_not_overwrite_the_first(self):
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        overlay_show("center_hero", "scope_test", to=self.intrepid.id, title="B")
        self.assertEqual(len(_live_records_for("center_hero")), 2,
                         "one live record per audience, not one per slot name")
        self.assertEqual(self._content(1001)["title"], "A")
        self.assertEqual(self._content(2001)["title"], "B")

    def test_a_late_console_gets_its_own_ships_card(self):
        from sbs_utils.procedural.links import link
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        overlay_show("center_hero", "scope_test", to=self.intrepid.id, title="B")

        link(self.artemis.id, "consoles", 1002)     # takes its post late
        self._catchup()
        self.assertIsNotNone(self._content(1002),
                             "the Artemis's late console got no card at all")
        self.assertEqual(self._content(1002)["title"], "A",
                         "the late console was handed the OTHER ship's card")

    def test_clearing_one_ship_leaves_the_other_running(self):
        from sbs_utils.procedural.links import link
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        overlay_show("center_hero", "scope_test", to=self.intrepid.id, title="B")

        overlay_clear("center_hero", to=self.artemis.id)
        self.assertEqual(len(_live_records_for("center_hero")), 1,
                         "clearing one bridge retired the other bridge's record")

        link(self.intrepid.id, "consoles", 2002)
        self._catchup()
        self.assertEqual(self._content(2002)["title"], "B")
        self.assertIsNone(self._content(1001), "the cleared bridge kept its card")

    def test_a_re_show_to_the_same_audience_replaces_rather_than_stacks(self):
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A2")
        self.assertEqual(len(_live_records_for("center_hero")), 1)
        self.assertEqual(self._content(1001)["title"], "A2")

    def test_an_overlapping_audience_evicts_the_older_record(self):
        # One card per slot PER CONSOLE: a card to the whole ship supersedes one
        # aimed at a single console of it, rather than both catching up forever.
        overlay_show("center_hero", "scope_test", to=1001, title="just me")
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="all of us")
        self.assertEqual(len(_live_records_for("center_hero")), 1)
        self.assertEqual(self._content(1001)["title"], "all of us")


class TestPerConsoleClear(TwoBridges):

    def test_clearing_one_console_does_not_cancel_the_rest(self):
        from sbs_utils.procedural.links import link
        link(self.artemis.id, "consoles", 1002)
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        self.assertIsNotNone(self._content(1001))
        self.assertIsNotNone(self._content(1002))

        overlay_clear("center_hero", to=1001)
        self.assertEqual(len(_live_records_for("center_hero")), 1,
                         "a per-console clear retired the whole ship's record")
        self._catchup()
        self.assertIsNone(self._content(1001),
                          "the catch-up put the card back on the console that cleared it")
        self.assertIsNotNone(self._content(1002))

    def test_clearing_every_console_retires_the_record(self):
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        overlay_clear("center_hero", to=self.artemis.id)
        self.assertEqual(_live_records_for("center_hero"), [])


class TestClearConsole(TwoBridges):

    def test_it_clears_every_slot_that_console_holds(self):
        overlay_show("center_hero", "scope_test", to=1001, title="hero")
        overlay_show("top_banner", "scope_test", to=1001, title="banner")
        self.assertEqual(overlay_clear_console(1001), 2)
        self.assertIsNone(self._content(1001, "center_hero"))
        self.assertIsNone(self._content(1001, "top_banner"))

    def test_it_does_not_wipe_the_world(self):
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        overlay_show("center_hero", "scope_test", to=self.intrepid.id, title="B")
        overlay_clear_console(1001)
        self.assertEqual(len(_live_records_for("center_hero")), 1,
                         "clearing one console dropped another ship's live record")
        self.assertIsNotNone(self._content(2001))

    def test_the_card_does_not_come_back_on_the_next_catchup(self):
        # THE point of the door. OverlayManager.clear sets content = None, which is
        # exactly the condition the catch-up ticker tests for when it decides a
        # console is missing the card - so clearing the page alone is not enough.
        overlay_show("center_hero", "scope_test", to=self.artemis.id, title="A")
        overlay_clear_console(1001)
        self._catchup()
        self.assertIsNone(self._content(1001),
                          "the console the crew just left got its card straight back")

    def test_a_console_with_nothing_up_is_a_no_op(self):
        self.assertEqual(overlay_clear_console(3001), 0)

    def test_an_unknown_client_is_a_no_op(self):
        self.assertEqual(overlay_clear_console(987654), 0)


if __name__ == "__main__":
    unittest.main()
