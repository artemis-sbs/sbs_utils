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
from sbs_utils.procedural.gui.overlay import (
    overlay_register, overlay_hero, overlay_show, overlay_clear, _pages_for)


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
    # region bracketing, not widget rendering. Parent = the slot's region tag.
    slot = content.get("slot")
    if slot:
        FrameContext.context.sbs.send_gui_text(
            cid, f"ovl_{slot}$$", "t", f"$text:{content.get('title', '')}", 0, 0, 100, 10)


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


HERO_TAG = "ovl_center_hero$$"      # region tag convention: "<prefix>$$"
BANNER_TAG = "ovl_top_banner$$"


class TestOverlayEstablish(OverlayTestBase):
    def test_first_show_requests_repaint_not_out_of_band_draw(self):
        # The sub-region can only be established during a full repaint, so the
        # first show requests one instead of drawing out-of-band.
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})
        self.assertEqual(self.page.gui_state, "repaint")
        self.assertFalse(ov.slots["center_hero"].established)
        self.assertFalse(self.sub_regions(), "no out-of-band sub_region before establish")

    def test_present_all_establishes_and_draws_into_region(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})
        self.rec.clear()
        ov.present_all(FakeEvent(0))     # the full-repaint hook

        subs = [a for a in self.sub_regions() if a[2] == HERO_TAG]
        self.assertEqual(len(subs), 1, "one sub_region established for the slot")
        self.assertIn("draw_layer:28000", subs[0][3])
        self.assertIn((0, HERO_TAG), self.calls("send_gui_clear"))
        self.assertIn((0, HERO_TAG), self.calls("send_gui_complete"))
        # content is parented to the SLOT region, not root
        self.assertTrue([a for a in self.calls("send_gui_text") if a[1] == HERO_TAG],
                        "content built inside the slot region")
        self.assertTrue(ov.slots["center_hero"].established)

    def test_update_after_established_is_out_of_band_no_sub_region(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "A"})
        ov.present_all(FakeEvent(0))         # establish
        self.rec.clear()
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "B"})   # update

        self.assertFalse(self.sub_regions(), "established slot updates without sub_region")
        self.assertIn((0, HERO_TAG), self.calls("send_gui_clear"))
        self.assertIn((0, HERO_TAG), self.calls("send_gui_complete"))
        # crucially, no ROOT clear -> no full page repaint
        self.assertNotIn((0, ""), self.calls("send_gui_clear"))


class TestOverlayClear(OverlayTestBase):
    def test_clear_out_of_band_draws_placeholder(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})
        ov.present_all(FakeEvent(0))         # establish
        self.rec.clear()
        ov.clear("center_hero")

        self.assertTrue(ov.slots["center_hero"].is_empty)
        self.assertFalse(self.sub_regions(), "clear is out-of-band, no sub_region")
        self.assertNotIn((0, ""), self.calls("send_gui_clear"), "no page repaint")
        self.assertIn((0, HERO_TAG), self.calls("send_gui_clear"))
        self.assertIn((0, HERO_TAG), self.calls("send_gui_complete"))
        texts = [a for a in self.calls("send_gui_text") if a[1] == HERO_TAG]
        self.assertEqual(len(texts), 1, "just the placeholder")
        self.assertTrue(texts[0][2].endswith("_blank"), "placeholder tag")

    def test_present_all_drops_empty_slot_and_unestablishes(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "HI"})
        ov.present_all(FakeEvent(0))
        ov.clear("center_hero")
        self.rec.clear()
        ov.present_all(FakeEvent(0))         # empty slot: not drawn, un-established
        self.assertNotIn(HERO_TAG, self.region_tags_in_order())
        self.assertFalse(ov.slots["center_hero"].established)


class TestOverlayOrder(OverlayTestBase):
    def test_present_all_draw_layer_order_low_to_high(self):
        ov = self.page.overlays
        ov.show("center_hero", "test", {"slot": "center_hero", "title": "H"})   # 28000
        ov.show("top_banner", "test", {"slot": "top_banner", "title": "B"})     # 24000
        self.rec.clear()
        ov.present_all(FakeEvent(0))
        order = self.region_tags_in_order()
        self.assertLess(order.index(BANNER_TAG), order.index(HERO_TAG),
                        "lower draw_layer emitted first (drawn under)")


class TestOverlayHeroBuilder(OverlayTestBase):
    def test_hero_wrapper_builds_through_layout(self):
        # Exercises the real _hero_builder via the SubPage layout path (no image).
        overlay_hero("CHAPTER TWO", subtitle="The Long Dark")
        self.page.overlays.present_all(FakeEvent(0))     # establish + draw
        self.assertIn(HERO_TAG, self.region_tags_in_order())
        # title + subtitle => at least two text widgets rendered into the region
        texts = [a for a in self.calls("send_gui_text") if a[1] == HERO_TAG]
        self.assertGreaterEqual(len(texts), 2)


class TestOverlayToTargeting(unittest.TestCase):
    """`to` role-set / client-id targeting: push overlays to specific consoles."""

    def setUp(self):
        from sbs_utils.spaceobject import SpaceObject
        from sbs_utils.gui import GuiClient
        sbs.create_new_sim()
        SpaceObject.clear()
        self.rec = []
        FrameContext.context = Context(sbs.sim, RecordingSbs(sbs, self.rec), FakeEvent())

        self.pages = {}
        for cid in (0, 1001, 1002):
            page = StoryPage()
            page.pending_gui = False
            page.client_id = cid
            page.gui_task = _FakeGuiTask(page)
            client = GuiClient(cid)              # self-registers under Agent.get(cid)
            client.page_stack.append(page)
            self._client = client if cid == 1001 else getattr(self, "_client", None)
            self.pages[cid] = page
        # console 1001 is a "mainscreen"
        from sbs_utils.agent import Agent
        Agent.get(1001).add_role("mainscreen")
        FrameContext.page = self.pages[0]        # "server" is the caller

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def test_pages_for_none_is_current(self):
        self.assertEqual(_pages_for(None), [self.pages[0]])

    def test_pages_for_int_client(self):
        self.assertEqual(_pages_for(1001), [self.pages[1001]])

    def test_pages_for_role_set(self):
        from sbs_utils.procedural.roles import role
        self.assertEqual(_pages_for(role("mainscreen")), [self.pages[1001]])

    def test_pages_for_skips_non_client_ids(self):
        # a mixed set: a real client + a bogus id with no page
        self.assertEqual(_pages_for({1001, 424242}), [self.pages[1001]])

    def test_show_targets_only_the_to_console(self):
        overlay_show("center_hero", "test", to=1001, title="HI")
        # target got the content + a repaint request; the caller (0) did not
        self.assertIn("center_hero", self.pages[1001].overlays.slots)
        self.assertEqual(self.pages[1001].overlays.slots["center_hero"].content["title"], "HI")
        self.assertEqual(self.pages[1001].gui_state, "repaint")
        self.assertNotIn("center_hero", self.pages[0].overlays.slots)

    def test_show_to_role_set_fans_out(self):
        from sbs_utils.agent import Agent
        Agent.get(1002).add_role("mainscreen")
        from sbs_utils.procedural.roles import role
        overlay_show("top_banner", "test", to=role("mainscreen"), title="ALERT")
        self.assertIn("top_banner", self.pages[1001].overlays.slots)
        self.assertIn("top_banner", self.pages[1002].overlays.slots)
        self.assertNotIn("top_banner", self.pages[0].overlays.slots)

    def test_clear_targets_only_the_to_console(self):
        # establish on 1001, then clear only 1001
        ov = self.pages[1001].overlays
        overlay_show("center_hero", "test", to=1001, title="HI")
        ov.present_all(FakeEvent(1001))          # establish
        overlay_clear("center_hero", to=1001)
        self.assertTrue(ov.slots["center_hero"].is_empty)


if __name__ == "__main__":
    unittest.main()
