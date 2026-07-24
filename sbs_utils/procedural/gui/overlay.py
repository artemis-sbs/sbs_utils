"""Overlay system — screen-anchored surfaces drawn on top of a console's page.

An overlay is an independent absolute sub-region (a "slot") drawn above the page
via ``draw_layer``, populated by a builder at present time (like the info panel's
``show`` callbacks), and updated out-of-band without a full page repaint.

Architecture (see OVERLAY_PLAN.md):
- Each slot is its OWN named sub-region (``$$ovl:<slot>``), not a section in the
  page's layout tree. Showing/clearing a slot brackets just that sub-region
  (send_gui_sub_region + clear ... complete) — no page ``swap_layout``, so no full
  repaint.
- The slots are owned by an ``OverlayManager`` that persists on the page across page
  rebuilds; ``present_all`` re-draws every non-empty slot after the page's layouts
  each repaint, so overlays survive tab/console/page changes and always draw last.
- Content is data (a ``{kind, ...}`` dict); widget building happens at present time
  through a ``SubPage`` running the registered ``kind`` builder — so a show is a full
  rebuild of that one slot (no in-place child mutation → no region ghosting).

Phase 1 provides the core + a static ``hero`` card. Signal routing, ``to`` targeting,
and the AMD/quest bindings layer on top of this without changing it.
"""
import traceback

from ...helpers import FrameContext, FakeEvent
from ...pages.layout import layout as layout
from ...pages.widgets.layout_listbox import SubPage
from .gui import gui_page_for_client


# --- Slot registry -----------------------------------------------------------
# name -> {"rect": (l, t, r, b) in screen %, "draw_layer": int, "input": mode}
# draw_layer must exceed the page's button layer (10000) to sit on top; higher
# slots stack over lower ones. ``input`` is plumbed now (all "passthrough") so the
# engine input-routing upgrade is a per-slot switch later, not a redesign.
DEFAULT_SLOT = {"rect": (10.0, 40.0, 90.0, 60.0), "draw_layer": 28000, "input": "passthrough"}

OVERLAY_SLOTS = {
    "objective":    {"rect": (72.0,  4.0, 99.0, 40.0), "draw_layer": 20000, "input": "passthrough"},
    "hud":          {"rect": ( 1.0, 60.0, 99.0, 99.0), "draw_layer": 21000, "input": "passthrough"},
    "corner_toast": {"rect": (66.0, 70.0, 99.0, 96.0), "draw_layer": 22000, "input": "passthrough"},
    "top_banner":   {"rect": ( 0.0,  0.0,100.0,  8.0), "draw_layer": 24000, "input": "passthrough"},
    "lower_third":  {"rect": (20.0, 74.0, 80.0, 94.0), "draw_layer": 26000, "input": "passthrough"},
    "center_hero":  {"rect": (25.0, 30.0, 75.0, 70.0), "draw_layer": 28000, "input": "passthrough"},
    "fullscreen":   {"rect": ( 0.0,  0.0,100.0,100.0), "draw_layer": 30000, "input": "passthrough"},
}


def overlay_slot_define(slot, rect, draw_layer=28000, input="passthrough"):
    """Define or override a slot's default rect / draw_layer / input mode."""
    OVERLAY_SLOTS[slot] = {"rect": tuple(rect), "draw_layer": draw_layer, "input": input}


# --- Kind (builder) registry -------------------------------------------------
# kind -> builder(client_id, content_dict). The builder calls the normal gui_*
# procedural functions; they land in the slot's sub-region because present() swaps
# FrameContext.page to a SubPage before calling it.
OVERLAY_KINDS = {}


def overlay_register(kind, builder):
    """Register a content builder for an overlay ``kind``.

    Args:
        kind (str): the ``kind`` value callers pass to ``overlay_show``.
        builder (callable): ``builder(client_id, content)`` — content is the dict
            passed to ``overlay_show`` (with ``kind`` included). Build widgets with
            the normal ``gui_*`` functions.
    """
    OVERLAY_KINDS[kind] = builder
    return builder


# --- OverlayRegion -----------------------------------------------------------
class OverlayRegion:
    """One slot: an absolute sub-region rebuilt from ``content`` on present.

    Modeled on ``TabbedPanel`` — brackets its own sub-region and runs a builder
    through a ``SubPage`` so procedural ``gui_*`` calls land inside it.
    """

    def __init__(self, slot, spec):
        self.slot = slot
        self.rect = spec["rect"]
        self.draw_layer = spec["draw_layer"]
        self.input = spec.get("input", "passthrough")
        self.local_region_tag = f"$$ovl:{slot}"
        self.tag_prefix = f"ovl:{slot}"
        self.content = None            # None = empty slot
        self.client_id = None

    @property
    def is_empty(self):
        return self.content is None

    def _draw(self, event, build):
        """Bracket the sub-region; optionally build content inside it."""
        cid = event.client_id
        SBS = FrameContext.context.sbs
        # A high draw_layer on the sub-region lifts the whole overlay above the
        # page. draggable:False so overlays aren't user-movable like the info panel.
        SBS.send_gui_sub_region(
            cid, "", self.local_region_tag,
            f"draggable:False;draw_layer:{self.draw_layer};",
            0.0, 0.0, 100.0, 100.0)
        SBS.send_gui_clear(cid, self.local_region_tag)
        if build and self.content is not None:
            self._build_content(event)
        SBS.send_gui_complete(cid, self.local_region_tag)

    def _build_content(self, event):
        cid = event.client_id
        builder = OVERLAY_KINDS.get(self.content.get("kind"))
        if builder is None:
            return
        restore = FrameContext.page
        if restore is None:
            return
        sub_page = SubPage(self.tag_prefix, self.local_region_tag, restore.gui_task, cid)
        FrameContext.page = sub_page
        # Content Layout positioned at the slot rect within the full-screen sub-region.
        sec = layout.Layout(self.tag_prefix + ":sec", None, *self.rect)
        sec.region_tag = self.local_region_tag
        sec.item_index = 0
        sub_page.next_slot(0, sec)
        try:
            builder(cid, self.content)
        except Exception as e:
            print(f"[overlay] builder '{self.content.get('kind')}' failed: {e}")
            print(traceback.format_exc())
        sec.calc(cid)
        sec.present(event)
        FrameContext.page = restore
        # Merge widget tags into the real page so clicks route (interactive slots).
        page = gui_page_for_client(cid)
        if page is not None:
            page.tag_map |= sub_page.tag_map

    def present(self, event):
        """Draw this slot fresh (called from the page present loop each repaint)."""
        self.client_id = event.client_id
        self._draw(event, build=True)

    def represent(self, event):
        """Out-of-band update: rebuild just this slot's sub-region. No page repaint."""
        if self.client_id is None:
            self.client_id = event.client_id
        self._draw(event, build=True)

    def clear_region(self, event):
        """Draw the slot empty (clears its sub-region), no content build."""
        self.client_id = event.client_id
        self._draw(event, build=False)


# --- OverlayManager (one per page) -------------------------------------------
class OverlayManager:
    """Owns a page's overlay slots; persists across page rebuilds."""

    def __init__(self, page):
        self.page = page
        self.slots = {}   # name -> OverlayRegion

    def _region(self, slot):
        r = self.slots.get(slot)
        if r is None:
            spec = OVERLAY_SLOTS.get(slot, DEFAULT_SLOT)
            r = OverlayRegion(slot, spec)
            self.slots[slot] = r
        return r

    def _event(self):
        return FakeEvent(self.page.client_id)

    def show(self, slot, kind, content):
        r = self._region(slot)
        data = {"kind": kind}
        data.update(content or {})
        r.content = data
        r.represent(self._event())     # immediate, out-of-band — no page repaint
        return r

    def clear(self, slot=None):
        if slot is None:
            for name in list(self.slots.keys()):
                self.clear(name)
            return
        r = self.slots.get(slot)
        if r is None:
            return
        r.content = None
        r.clear_region(self._event())

    def present_all(self, event):
        """Re-draw every non-empty slot after the page's layouts, in draw_layer
        order (low → high so higher slots emit last). Called each page repaint so
        overlays survive the page's root clear."""
        for r in sorted(self.slots.values(), key=lambda r: r.draw_layer):
            if not r.is_empty:
                r.present(event)


# --- Procedural API ----------------------------------------------------------
def _managers_for(to):
    """Resolve the OverlayManager(s) for a ``to`` target.

    Phase 1: ``to=None`` → the current client's page. Multi-client ``to`` targeting
    (role sets) is added with the signal layer in Phase 2.
    """
    page = FrameContext.page
    if page is None:
        return []
    mgr = getattr(page, "overlays", None)
    return [mgr] if mgr is not None else []


def overlay_show(slot, kind, to=None, **content):
    """Show an overlay in ``slot`` using content builder ``kind``.

    Args:
        slot (str): a slot name (see ``OVERLAY_SLOTS``); unknown names use a
            centered default rect.
        kind (str): a registered builder (see ``overlay_register``).
        to: target — Phase 1 uses the current console; role-set targeting is Phase 2.
        **content: fields passed through to the builder.
    """
    for mgr in _managers_for(to):
        mgr.show(slot, kind, content)


def overlay_clear(slot=None, to=None):
    """Clear one slot (or all slots if ``slot`` is None)."""
    for mgr in _managers_for(to):
        mgr.clear(slot)


# --- Default builders + ergonomic wrappers -----------------------------------
def _hero_builder(client_id, content):
    from .text import gui_text
    from .image import gui_image_keep_aspect_ratio_center
    from .row import gui_row
    from .section import gui_sub_section

    title = content.get("title", "")
    subtitle = content.get("subtitle")
    image = content.get("image")

    if image:
        gui_row("row-height: 60%;")
        with gui_sub_section():
            gui_image_keep_aspect_ratio_center(image)
    gui_row("row-height: content;")
    gui_text(f"$text:`{title}`;justify:center;font:gui-6;color:#fff")
    if subtitle:
        gui_row("row-height: content;")
        gui_text(f"$text:`{subtitle}`;justify:center;font:gui-3;color:#8cf")


overlay_register("hero", _hero_builder)


def overlay_hero(title, subtitle=None, image=None, slot="center_hero", to=None, seconds=None):
    """Show a big centered hero / chapter card. (``seconds`` auto-dismiss is Phase 6.)"""
    overlay_show(slot, "hero", to=to, title=title, subtitle=subtitle, image=image)
