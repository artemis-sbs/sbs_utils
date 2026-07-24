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

    def format_string(self, s):
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


class TestOverlayTransientAndBuilders(OverlayTestBase):
    """Phase 3 display family: toast auto-dismiss + banner/lower_third/credits/choice
    builders render into their slot region."""

    def setUp(self):
        super().setUp()
        from sbs_utils.tickdispatcher import TickDispatcher
        TickDispatcher.clear()

    def _establish(self, tag):
        self.rec.clear()
        self.page.overlays.present_all(FakeEvent(0))
        return [a for a in self.calls("send_gui_text") if a[1] == tag]

    def test_toast_schedules_one_shot_dismiss(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.gui.overlay import overlay_toast
        overlay_toast("Objective updated", seconds=3)
        self.assertIn("corner_toast", self.page.overlays.slots)
        self.assertEqual(len(TickDispatcher._new_this_tick), 1, "one auto-dismiss task")

    def test_toast_no_dismiss_when_seconds_zero(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.gui.overlay import overlay_toast
        overlay_toast("no timer", seconds=0)
        self.assertEqual(len(TickDispatcher._new_this_tick), 0)

    def test_banner_builder_renders(self):
        from sbs_utils.procedural.gui.overlay import overlay_banner
        overlay_banner("RED ALERT")
        self.assertTrue(self._establish("ovl_top_banner$$"))

    def test_lower_third_builder_renders_name_and_line(self):
        from sbs_utils.procedural.gui.overlay import overlay_lower_third
        overlay_lower_third("Admiral Harkin", "Hold the line.")
        texts = self._establish("ovl_lower_third$$")
        self.assertGreaterEqual(len(texts), 2)      # name + line

    def test_credits_builder_renders_all_entries(self):
        from sbs_utils.procedural.gui.overlay import overlay_credits
        overlay_credits(["Alice", "Bob", "Carol"], title="CREDITS")
        texts = self._establish("ovl_fullscreen$$")
        self.assertGreaterEqual(len(texts), 4)      # title + 3 entries

    def test_choice_returns_promise_and_renders_buttons(self):
        from sbs_utils.procedural.gui.overlay import overlay_choice
        from sbs_utils.futures import Promise
        prom = overlay_choice("Fire?", ["Yes", "No"])
        self.assertIsInstance(prom, Promise)
        self.assertIn("center_hero", self.page.overlays.slots)
        self.rec.clear()
        self.page.overlays.present_all(FakeEvent(0))
        self.assertGreaterEqual(len(self.calls("send_gui_button")), 2)


class TestOverlayModalResolves(unittest.TestCase):
    """The modal choice promise resolves with the pressed button's label."""

    def setUp(self):
        from sbs_utils.spaceobject import SpaceObject
        from sbs_utils.gui import GuiClient
        sbs.create_new_sim()
        SpaceObject.clear()
        self.rec = []
        FrameContext.context = Context(sbs.sim, RecordingSbs(sbs, self.rec), FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = 0
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(0)                     # so gui_page_for_client(0) merges tag_map
        client.page_stack.append(self.page)
        FrameContext.page = self.page

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def test_pressing_a_button_resolves_with_its_label(self):
        from sbs_utils.procedural.gui.overlay import overlay_choice
        prom = overlay_choice("Fire?", ["Yes", "No"])
        self.page.overlays.present_all(FakeEvent(0))   # establish + merge tag_map

        # find the "Yes" button's MessageHandler in the page tag_map and fire it
        handler = btag = None
        for tag, (li, rn) in self.page.tag_map.items():
            if rn is not None and getattr(rn, "handler", None) is prom and getattr(li, "data", None) == "Yes":
                handler, btag = rn, tag
                break
        self.assertIsNotNone(handler, "Yes button handler present in page.tag_map")

        handler.on_message(FakeEvent(0, sub_tag=btag))
        self.assertTrue(prom.done())
        self.assertEqual(prom.result().data, "Yes")


class TestOverlayPolish(OverlayTestBase):
    """Phase 6: transient dismiss superseding + fullscreen cinematic builders."""

    def setUp(self):
        super().setUp()
        from sbs_utils.tickdispatcher import TickDispatcher
        TickDispatcher.clear()

    def test_reshow_supersedes_stale_dismiss(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.gui.overlay import overlay_banner
        overlay_banner("first", seconds=3)              # schedules dismiss @ gen 1
        r = self.page.overlays.slots["top_banner"]
        stale = set(TickDispatcher._new_this_tick)      # the gen-1 dismiss
        overlay_banner("second", seconds=3)             # gen 2 -> supersedes it
        for t in stale:                                 # fire ONLY the stale dismiss
            t.cb(t)
        self.assertIsNotNone(r.content)                 # newer content survives
        self.assertEqual(r.content["text"], "second")

    def test_dismiss_fires_when_not_superseded(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.gui.overlay import overlay_banner
        overlay_banner("only", seconds=3)
        r = self.page.overlays.slots["top_banner"]
        t = next(iter(TickDispatcher._new_this_tick))
        t.cb(t)
        self.assertTrue(r.is_empty)

    def test_toasts_stack(self):
        from sbs_utils.procedural.gui.overlay import overlay_toast
        overlay_toast("one", seconds=3)
        overlay_toast("two", seconds=3)
        items = self.page.overlays.slots["corner_toast"].content["items"]
        self.assertEqual([it["text"] for it in items], ["one", "two"])

    def test_toast_removal_drops_only_its_own(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.gui.overlay import overlay_toast
        overlay_toast("one", seconds=3)
        first = set(TickDispatcher._new_this_tick)      # the "one" removal
        overlay_toast("two", seconds=3)
        for t in first:                                 # fire only the "one" removal
            t.cb(t)
        items = self.page.overlays.slots["corner_toast"].content["items"]
        self.assertEqual([it["text"] for it in items], ["two"])

    def test_toast_stack_capped(self):
        from sbs_utils.procedural.gui.overlay import overlay_toast, TOAST_MAX
        for i in range(TOAST_MAX + 3):
            overlay_toast(f"t{i}", seconds=9)
        items = self.page.overlays.slots["corner_toast"].content["items"]
        self.assertEqual(len(items), TOAST_MAX)
        self.assertEqual(items[-1]["text"], f"t{TOAST_MAX + 2}")   # newest kept

    def test_credits_roll_pages_then_advances(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.gui.overlay import overlay_credits
        overlay_credits([f"L{i}" for i in range(10)], title="CREDITS", roll=1, window=4)
        r = self.page.overlays.slots["fullscreen"]
        self.assertEqual(r.content["entries"], ["L0", "L1", "L2", "L3"])
        t = next(iter(TickDispatcher._new_this_tick))   # the roll interval
        t.cb(t)                                         # advance one page
        self.assertEqual(r.content["entries"], ["L4", "L5", "L6", "L7"])

    def test_letterbox_builder_renders_bars(self):
        from sbs_utils.procedural.gui.overlay import overlay_letterbox
        overlay_letterbox(line="Approaching the anomaly")
        self.rec.clear()
        self.page.overlays.present_all(FakeEvent(0))
        # two black bar rows carry a background image; the line is a text
        tag = "ovl_fullscreen$$"
        self.assertTrue([a for a in self.calls("send_gui_image") if a[1] == tag])
        self.assertTrue([a for a in self.calls("send_gui_text") if a[1] == tag])

    def test_flash_builder_renders_and_auto_dismisses(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.gui.overlay import overlay_flash
        overlay_flash("#f006")
        self.assertIn("fullscreen", self.page.overlays.slots)
        self.assertEqual(len(TickDispatcher._new_this_tick), 1)   # fast auto-dismiss scheduled


class TestAmdOverlays(OverlayTestBase):
    """Declarative overlays: amd_overlays(section) -> records; overlay_amd(key) fires."""

    def setUp(self):
        super().setUp()
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.amd_overlay import OVERLAY_AMD
        TickDispatcher.clear()
        OVERLAY_AMD.clear()

    def _section(self):
        # what amd_records reads: children with key/display_text/description/data
        return {"children": [
            {"key": "ch2", "display_text": "Chapter Two", "description": "CHAPTER TWO",
             "data": {"kind": "hero", "subtitle": "The Long Dark", "seconds": "4"}},
            {"key": "obj", "display_text": "Objective", "description": "Objective updated",
             "data": {"kind": "toast"}},
            {"key": "named", "display_text": "Admiral", "description": "Hold the line.",
             "data": {"kind": "lower_third", "name": "Admiral Harkin"}},
        ]}

    def test_loader_builds_records(self):
        from sbs_utils.procedural.amd_overlay import amd_overlays
        m = amd_overlays(self._section())
        self.assertEqual(set(m), {"ch2", "obj", "named"})
        ch2 = m["ch2"]
        self.assertEqual(ch2["kind"], "hero")
        self.assertEqual(ch2["slot"], "center_hero")            # per-kind default
        self.assertEqual(ch2["fields"]["title"], "CHAPTER TWO")  # body -> primary
        self.assertEqual(ch2["fields"]["subtitle"], "The Long Dark")
        self.assertEqual(ch2["fields"]["seconds"], 4)            # coerced to int

    def test_toast_body_maps_to_text_and_default_slot(self):
        from sbs_utils.procedural.amd_overlay import amd_overlays
        m = amd_overlays(self._section())
        self.assertEqual(m["obj"]["slot"], "corner_toast")
        self.assertEqual(m["obj"]["fields"]["text"], "Objective updated")

    def test_lower_third_keeps_fence_name_and_body_line(self):
        from sbs_utils.procedural.amd_overlay import amd_overlays
        m = amd_overlays(self._section())
        self.assertEqual(m["named"]["fields"]["name"], "Admiral Harkin")
        self.assertEqual(m["named"]["fields"]["line"], "Hold the line.")

    def test_overlay_amd_fires_by_key(self):
        from sbs_utils.procedural.amd_overlay import amd_overlays, overlay_amd
        amd_overlays(self._section())
        overlay_amd("ch2")
        slot = self.page.overlays.slots["center_hero"]
        self.assertEqual(slot.content["kind"], "hero")
        self.assertEqual(slot.content["title"], "CHAPTER TWO")
        self.assertEqual(slot.content["subtitle"], "The Long Dark")
        self.assertNotIn("seconds", slot.content)               # consumed by dismiss, not a field

    def test_overlay_amd_seconds_schedules_dismiss(self):
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.procedural.amd_overlay import amd_overlays, overlay_amd
        amd_overlays(self._section())
        overlay_amd("ch2")                                       # Seconds: 4
        self.assertEqual(len(TickDispatcher._new_this_tick), 1)

    def test_overlay_amd_overrides_and_unknown_key(self):
        from sbs_utils.procedural.amd_overlay import amd_overlays, overlay_amd
        amd_overlays(self._section())
        overlay_amd("ch2", fields={"subtitle": "Overridden"})
        self.assertEqual(self.page.overlays.slots["center_hero"].content["subtitle"], "Overridden")
        self.assertIsNone(overlay_amd("nope"))                  # unknown key -> no-op


class TestOverlayHud(OverlayTestBase):
    """Phase 4 HUD: sticky rows + controls, cheap patch updates."""

    HUD_TAG = "ovl_hud$$"

    def _establish(self):
        self.rec.clear()
        self.page.overlays.present_all(FakeEvent(0))

    def test_hud_renders_rows(self):
        from sbs_utils.procedural.gui.overlay import overlay_hud
        overlay_hud(rows={"Speed": 12, "Shields": 88}, title="STATUS")
        self._establish()
        texts = [a for a in self.calls("send_gui_text") if a[1] == self.HUD_TAG]
        self.assertGreaterEqual(len(texts), 3)      # title + 2 rows

    def test_hud_accepts_list_of_pairs(self):
        from sbs_utils.procedural.gui.overlay import overlay_hud
        overlay_hud(rows=[("A", 1), ("B", 2), ("C", 3)])
        self._establish()
        texts = [a for a in self.calls("send_gui_text") if a[1] == self.HUD_TAG]
        self.assertGreaterEqual(len(texts), 3)

    def test_hud_control_is_a_button(self):
        from sbs_utils.procedural.gui.overlay import overlay_hud
        overlay_hud(rows={"HP": 5}, controls=[{"label": "Toggle", "action": "some_label"}])
        self._establish()
        self.assertGreaterEqual(len(self.calls("send_gui_button")), 1)

    def test_patch_updates_rows_without_new_sub_region(self):
        from sbs_utils.procedural.gui.overlay import overlay_hud, overlay_hud_update
        overlay_hud(rows={"Speed": 12})
        self.page.overlays.present_all(FakeEvent(0))     # establish
        self.rec.clear()
        overlay_hud_update(rows={"Speed": 34})
        # out-of-band: re-fills the region, no new sub_region, no root repaint
        self.assertFalse(self.calls("send_gui_sub_region"))
        self.assertNotIn((0, ""), self.calls("send_gui_clear"))
        self.assertIn((0, self.HUD_TAG), self.calls("send_gui_clear"))
        self.assertEqual(self.page.overlays.slots["hud"].content["rows"], [("Speed", 34)])

    def test_patch_is_noop_when_slot_never_shown(self):
        from sbs_utils.procedural.gui.overlay import overlay_hud_update
        overlay_hud_update(rows={"Speed": 1})            # nothing shown yet
        self.assertNotIn("hud", self.page.overlays.slots)


class TestOverlayHeroVisuals(OverlayTestBase):
    HERO = "ovl_center_hero$$"

    def _present(self, **kw):
        from sbs_utils.procedural.gui.overlay import overlay_hero
        overlay_hero("Admiral Harkin", subtitle="Hold the line", **kw)
        self.rec.clear()
        self.page.overlays.present_all(FakeEvent(0))

    def test_hero_with_face(self):
        self._present(face="ter #964b00 8 1;ter 0 0 0")
        self.assertTrue([a for a in self.calls("send_gui_face") if a[1] == self.HERO])

    def test_hero_with_ship(self):
        self._present(ship="tsn_battle_cruiser")
        self.assertTrue([a for a in self.calls("send_gui_3dship") if a[1] == self.HERO]
                        or [a for a in self.calls("send_gui_ship") if a[1] == self.HERO])

    def test_hero_with_icon(self):
        self._present(icon=137)
        self.assertTrue([a for a in self.calls("send_gui_icon") if a[1] == self.HERO])

    def test_hero_plain_still_works(self):
        self._present()
        self.assertTrue([a for a in self.calls("send_gui_text") if a[1] == self.HERO])


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
