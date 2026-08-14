"""Which client a redraw is addressed to (LM #571).

A `//signal` route runs once per connected console, so while it paints console
A the frame event still carries console B -- the console that emitted. The old
`gui_represent` broke the tie with `max(event_client, page_client)`, which with
two real clients means "whichever connected later". Console A then kept showing
stale text while console B got a widget that was never its own.

Two things must hold, and they are separate mechanisms:

* a value change routes itself, through the dirty system, on the item's OWN id
* an explicit `gui_represent` -- still what a visibility change or a rebuilt
  sub-section needs -- addresses the item's owner, not the larger of two ids
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.procedural.gui.update import gui_represent


# Real engine client ids: large, and ordered by connection. CLIENT_A connected
# first, so it is the one the old max() heuristic dropped.
CLIENT_A = 0x8000000000000001
CLIENT_B = 0x8000000000000002


class StubSbs:
    def __init__(self):
        self.sends = []

    def get_text_line_width(self, font, text):
        return len(text) * 10

    def get_text_line_height(self, font, text):
        return 20

    def get_text_block_height(self, font, text, px_width):
        return 20

    def send_gui_text(self, client_id, region, tag, message, left, top, right, bottom):
        self.sends.append((client_id, message))


class GuiRepresentClientTest(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)
        self.sbs = StubSbs()
        # The frame event carries CLIENT_B: it is the console that emitted.
        FrameContext.context = types.SimpleNamespace(
            sbs=self.sbs, sim=None,
            event=types.SimpleNamespace(client_id=CLIENT_B))
        # ...but the page being painted is CLIENT_A's.
        FrameContext.page = types.SimpleNamespace(client_id=CLIENT_A)
        Dirty.dirty = {}

    def tearDown(self):
        FrameContext.context = None
        FrameContext.page = None
        Dirty.dirty = {}

    def owned_widget(self, text):
        """A widget already on CLIENT_A's screen -- present() stamped it."""
        widget = Text("t", f"$text:`{text}`;")
        widget.client_id = CLIENT_A
        return widget

    def sent_to(self, client_id):
        return [message for cid, message in self.sbs.sends if cid == client_id]

    def test_value_change_redraws_on_the_owning_client(self):
        widget = self.owned_widget("Old Name")
        widget.value = "$text:`New Name`;"

        self.assertIn(CLIENT_A, Dirty.dirty,
                      "a value change must mark the widget's OWN client dirty")
        Dirty.represent_dirty()
        self.assertTrue(any("New Name" in m for m in self.sent_to(CLIENT_A)))

    def test_represent_addresses_the_owner_not_the_larger_id(self):
        widget = self.owned_widget("Old Name")
        gui_represent(widget)

        self.assertTrue(self.sent_to(CLIENT_A),
                        "the widget belongs to CLIENT_A and must be drawn there")
        self.assertFalse(self.sent_to(CLIENT_B),
                         "CLIENT_B must not receive another console's widget")

    def test_represent_leaves_the_owner_intact(self):
        # Addressing the wrong client also RE-STAMPED the item with that id,
        # so every later dirty redraw went to the wrong console too.
        widget = self.owned_widget("Old Name")
        gui_represent(widget)
        self.assertEqual(widget.client_id, CLIENT_A)

    def test_lower_id_owner_is_not_special(self):
        # Same test with the ids swapped: behavior must not depend on which
        # console connected first.
        FrameContext.context.event.client_id = CLIENT_A
        FrameContext.page.client_id = CLIENT_B
        widget = Text("t", "$text:`Old Name`;")
        widget.client_id = CLIENT_B

        gui_represent(widget)
        self.assertTrue(self.sent_to(CLIENT_B))
        self.assertFalse(self.sent_to(CLIENT_A))

    def test_server_page_still_reaches_its_client(self):
        # The case the old heuristic was written for: the event is the server
        # (manual beams), the widget is a real console's. Still correct.
        FrameContext.context.event.client_id = 0
        widget = self.owned_widget("Old Name")
        gui_represent(widget)
        self.assertTrue(self.sent_to(CLIENT_A))
        self.assertFalse(self.sent_to(0))


if __name__ == "__main__":
    unittest.main()
