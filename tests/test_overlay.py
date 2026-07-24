"""Overlay system core (Phase 1).

Drives OverlayManager / OverlayRegion directly with a recording sbs, asserting:
- a show brackets ONLY the slot's own sub-region (send_gui_sub_region + clear ...
  complete) with the slot's draw_layer, and builds content inside it;
- a show does NOT clear the root region "" (i.e. it is off the full-page-repaint
  path);
- present_all() re-emits non-empty slots (retain across page repaint) and skips
  empty ones, in draw_layer order;
- clear() empties a slot's sub-region and drops it from present_all.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.gui.overlay import overlay_register, overlay_hero


class RecordingSbs:
    """Wraps the mock sbs module, recording every call as (name, args)."""
    def __init__(self, real, rec):
        self._real = real
        self._rec = rec

    def __getattr__(self, name):
        attr = getattr(self._real, name)
        if not callable(attr):
            return attr
        def wrapper(*args, **kwargs):
            self._rec.append((name, args))
            return attr(*args, **kwargs)
        return wrapper


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    """Minimal stand-in for the client's GUI task — enough for style parsing
    (`task.main.page.client_id`) and variable set/get during a builder."""
    def __init__(self, page):
        self.main = _FakeMain(page)

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None

    def compile_and_format_string(self, s):
        return s


def _emit_builder(cid, content):
    # Bypass the layout machinery — emit straight to sbs so the test asserts the
    # region bracketing, not widget rendering.
    FrameContext.context.sbs.send_gui_text(
        cid, f"$$ovl:{content['slot']}", "t", f"$text:{content['title']}", 0, 0, 100, 10)


overlay_register("test", _emit_builder)


class OverlayTestBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        self.rec = []
        FrameContext.context = Context(sbs.sim, RecordingSbs(sbs, self.rec), FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = 0
        self.page.gui_task = _FakeGuiTask(self.page)
        FrameContext.page = self.page

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    # helpers -----------------------------------------------------------------
    def calls(self, name):
        return [args for (n, args) in self.rec if n == name]

    def sub_regions(self):
        # send_gui_sub_region(cid, parent, tag, style, l, t, r, b)
        return self.calls("send_gui_sub_region")

    def region_tags_in_order(self):
        return [a[2] for a in self.sub_regions()]


class TestOverlayShow(OverlayTestBase):
    def test_show_brackets_only_its_subregion(self):
        self.page.overlays.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})

        tag = "$$ovl:center_hero"
        subs = [a for a in self.sub_regions() if a[2] == tag]
        self.assertEqual(len(subs), 1, "exactly one sub_region for the slot")
        # style carries the slot's draw_layer
        self.assertIn("draw_layer:28000", subs[0][3])
        # its own region was cleared and completed
        self.assertIn((0, tag), self.calls("send_gui_clear"))
        self.assertIn((0, tag), self.calls("send_gui_complete"))
        # content was built inside it
        self.assertTrue(self.calls("send_gui_text"), "builder emitted content")

    def test_show_does_not_repaint_the_page(self):
        self.page.overlays.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})
        # The full page repaint clears the root region ""; a show must not.
        self.assertNotIn((0, ""), self.calls("send_gui_clear"))

    def test_clear_empties_slot_and_drops_from_present_all(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})
        ov.clear("center_hero")
        self.assertTrue(ov.slots["center_hero"].is_empty)

        # after clear, a repaint re-emit should NOT redraw the slot
        self.rec.clear()
        ov.present_all(FakeEvent(0))
        self.assertNotIn("$$ovl:center_hero", self.region_tags_in_order())


class TestOverlayRetainAndOrder(OverlayTestBase):
    def test_present_all_reemits_nonempty_slot(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})
        self.rec.clear()
        ov.present_all(FakeEvent(0))     # what the page present loop calls each repaint
        self.assertIn("$$ovl:center_hero", self.region_tags_in_order())

    def test_present_all_draw_layer_order_low_to_high(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "H"})   # 28000
        ov.show("top_banner", "test", {"slot": "top_banner", "title": "B"})     # 24000
        self.rec.clear()
        ov.present_all(FakeEvent(0))
        order = self.region_tags_in_order()
        self.assertLess(order.index("$$ovl:top_banner"),
                        order.index("$$ovl:center_hero"),
                        "lower draw_layer emitted first (drawn under)")


class TestOverlayHeroBuilder(OverlayTestBase):
    def test_hero_wrapper_builds_through_layout(self):
        # Exercises the real _hero_builder via the SubPage layout path (no image).
        overlay_hero("CHAPTER TWO", subtitle="The Long Dark")
        tag = "$$ovl:center_hero"
        self.assertIn(tag, self.region_tags_in_order())
        # title + subtitle => at least two text widgets rendered into the region
        texts = [a for a in self.calls("send_gui_text") if a[1] == tag]
        self.assertGreaterEqual(len(texts), 2)


if __name__ == "__main__":
    unittest.main()
