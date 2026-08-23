"""Tab declarations belong to the PAGE's client, not the current event's.

`MastStoryPage` reads the strip back off `self.client_id` - the page's own client - and
DRAWING IT CONSUMES IT (`console_tabs` and `__back_tab__` are cleared once the strip is
built), so every page build has to re-declare. `gui_tab_enable` / `gui_tab_back` wrote
those declarations against `FrameContext.client_id`, which is the current EVENT's client.

Those two are the same for a click, a keypress or a plain repaint. They are NOT the same
when a page rebuilds because something ELSE emitted a signal: `tick_in_context` corrects
FrameContext.page and .task to the observing task's, but leaves the event alone, so the
console's repaint ran under the emitter's client id.

LegendaryMissions' Fabricator hit it head on. `beacon_build_done` runs on the SERVER,
emits `item_changed` when the build finishes, and Engineering's `on signal` handler
repaints - declaring that console's tabs for client 0. The console drew its strip from
its own, now-empty state and the tabs vanished at the exact moment you want them, then
came back the next time the player clicked anything, because a click carries the right
client id.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural.gui.console_tab import (
    gui_tab_back, gui_tab_enable, gui_tab_add_top)
from sbs_utils.procedural.inventory import get_inventory_value

from sbs_utils.gui import GuiClient
from sbs_utils.agent import Agent, clear_shared

from cosmos_dev.mock import sbs

CONSOLE = 7
SERVER = 0


class _Page:
    """Only what the tab helpers need off a page."""

    def __init__(self, client_id):
        self.client_id = client_id


class _FakeSim:
    time_tick_counter = 0


class TestTabClientIdentity(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent(SERVER, "test"))
        FrameContext.page = None
        FrameContext.task = None
        # set_inventory_value on an id with no Agent is a SILENT no-op, so the clients
        # have to exist before anything can declare tabs for them - Gui.push is what
        # makes them in the real system.
        clear_shared()
        for cid in (SERVER, CONSOLE):
            GuiClient(cid)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None

    def declare(self):
        gui_tab_back("engineering")
        gui_tab_enable("fabricate,cargo")

    def tabs_of(self, client_id):
        return get_inventory_value(client_id, "console_tabs", {}) or {}

    def back_of(self, client_id):
        return get_inventory_value(client_id, "__back_tab__", None)

    def test_a_server_emitted_repaint_declares_for_the_CONSOLE(self):
        """The reported bug. The event says client 0; the page says client 7."""
        FrameContext.page = _Page(CONSOLE)
        self.declare()
        self.assertEqual(self.back_of(CONSOLE), "engineering")
        self.assertEqual(set(self.tabs_of(CONSOLE)),
                         {"engineering", "fabricate", "cargo"})

    def test_and_declares_NOTHING_for_the_emitter(self):
        """Otherwise the server accumulates a console's tabs, which is its own bug."""
        FrameContext.page = _Page(CONSOLE)
        self.declare()
        self.assertEqual(self.tabs_of(SERVER), {})
        self.assertIsNone(self.back_of(SERVER))

    def test_a_click_still_declares_for_the_clicking_client(self):
        """The ordinary path must be unchanged - here event and page agree."""
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent(CONSOLE, "gui_message"))
        FrameContext.page = _Page(CONSOLE)
        self.declare()
        self.assertEqual(self.back_of(CONSOLE), "engineering")

    def test_with_no_page_it_falls_back_to_the_event(self):
        """Server-side setup code and tests declare tabs with no page in context."""
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent(CONSOLE, "test"))
        FrameContext.page = None
        gui_tab_add_top("debug")
        self.assertIn("debug", self.tabs_of(CONSOLE) or
                      get_inventory_value(CONSOLE, "top_tabs", {}))

    def test_a_page_that_never_got_a_client_falls_back_too(self):
        """MastStoryPage starts with client_id None until it is presented."""
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent(CONSOLE, "test"))
        FrameContext.page = _Page(None)
        self.declare()
        self.assertEqual(self.back_of(CONSOLE), "engineering")


if __name__ == "__main__":
    unittest.main()
