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

from ...helpers import FrameContext, FakeEvent, FrameContextOverride
from ...pages.layout import layout as layout
from ...pages.widgets.layout_listbox import SubPage
from .gui import gui_page_for_client
from ..query import to_set


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


# --- Debug logging (diagnose clear/redraw in-engine) -------------------------
# When enabled, the overlay code appends its exact send_gui_* command stream to a
# file — copyable, unlike the engine's painted get_debug_gui_tree.
_DEBUG = {"path": None, "n": 0}


def overlay_debug_log(path=None):
    """Enable overlay command-stream logging to ``path`` (default: the mission's
    overlay_debug.log). Truncates the file. Pass None-path to disable."""
    if path is None:
        try:
            from ...fs import get_mission_dir_filename
            path = get_mission_dir_filename("overlay_debug.log")
        except Exception:
            path = "overlay_debug.log"
    _DEBUG["path"] = path
    _DEBUG["n"] = 0
    try:
        open(path, "w").close()
    except Exception:
        pass
    return path


def _dbg(line):
    p = _DEBUG["path"]
    if not p:
        return
    try:
        _DEBUG["n"] += 1
        with open(p, "a") as f:
            f.write(f"{_DEBUG['n']:04d} {line}\n")
    except Exception:
        pass


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
        # Region tag follows the codebase convention: "<prefix>$$" (suffix, no
        # leading $$, no colon) — same shape as the info panel / listbox local
        # region tags and Layout.drawing_region_tag. A malformed region tag makes
        # the engine drop child widgets to root.
        self.tag_prefix = f"ovl_{slot}"
        self.local_region_tag = f"{self.tag_prefix}$$"
        self.content = None            # None = empty slot
        self.client_id = None
        # A sub-region can only be ESTABLISHED during a full page repaint (root
        # send_gui_clear("")). Established out-of-band, the engine ignores the
        # sub_region and the content's parent dangles up to root — visible, but
        # not in the slot, so clear can't reach it. So: establish in present_all
        # (full repaint), then out-of-band clear/complete updates the live region.
        self.established = False

    @property
    def is_empty(self):
        return self.content is None

    def _fill(self, event):
        """Draw the slot's content, or an invisible placeholder when empty.

        The engine only swaps the back buffer forward on `complete` when it holds
        SOMETHING; an empty back buffer isn't swapped (stale content stays). So an
        empty slot still emits one placeholder (a space renders nothing)."""
        if self.content is not None:
            self._build_content(event)
        else:
            FrameContext.context.sbs.send_gui_text(
                event.client_id, self.local_region_tag, f"{self.tag_prefix}_blank",
                "$text:` `;", 0.0, 0.0, 100.0, 100.0)

    def establish(self, event):
        """Full-repaint path: (re)register the sub-region under root, then fill it.
        Only valid while the page's root region is being rebuilt."""
        cid = event.client_id
        self.client_id = cid
        SBS = FrameContext.context.sbs
        # draggable:False so overlays aren't user-movable like the info panel.
        SBS.send_gui_sub_region(
            cid, "", self.local_region_tag,
            f"draggable:False;draw_layer:{self.draw_layer};",
            0.0, 0.0, 100.0, 100.0)
        _dbg(f"establish sub_region {self.local_region_tag} dl={self.draw_layer}")
        SBS.send_gui_clear(cid, self.local_region_tag)
        self._fill(event)
        SBS.send_gui_complete(cid, self.local_region_tag)
        self.established = True

    def update(self, event):
        """Out-of-band path: the region is already established, so just
        clear -> fill -> complete (NO sub_region). No page repaint."""
        cid = event.client_id
        self.client_id = cid
        SBS = FrameContext.context.sbs
        _dbg(f"update (no sub_region) {self.local_region_tag} content={self.content and self.content.get('kind')}")
        SBS.send_gui_clear(cid, self.local_region_tag)
        self._fill(event)
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

    def _request_repaint(self):
        """Force a full page repaint so present_all can ESTABLISH the sub-region
        (establishment is gated on the root clear("")). Used only the first time a
        slot is shown; subsequent updates go out-of-band."""
        from ...gui import Gui
        self.page.gui_state = "repaint"
        Gui.dirty(self.page.client_id)

    def show(self, slot, kind, content):
        r = self._region(slot)
        data = {"kind": kind}
        data.update(content or {})
        r.content = data
        _dbg(f"show slot={slot} kind={kind} established={r.established}")
        if r.established:
            r.update(self._event())       # out-of-band — no page repaint
        else:
            self._request_repaint()       # establish via present_all first
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
        _dbg(f"clear slot={slot} established={r.established}")
        if r.established:
            r.update(self._event())       # out-of-band clear (region already live)

    def present_all(self, event):
        """Called inside the page's repaint (after root clear("")), so this is
        where sub-regions get ESTABLISHED. Draw every slot that has content in
        draw_layer order (low → high so higher slots emit last). Empty slots are
        dropped by the root clear and marked un-established so a later show
        re-establishes them via a repaint."""
        for r in sorted(self.slots.values(), key=lambda r: r.draw_layer):
            if r.content is not None:
                _dbg(f"present_all establish+draw slot={r.slot}")
                r.establish(event)
            else:
                r.established = False


# --- Procedural API ----------------------------------------------------------
def _pages_for(to):
    """Resolve a ``to`` target to a list of client pages that have an overlay
    manager.

    - ``to is None`` → the current console (``FrameContext.page``).
    - otherwise ``to`` is normalized with ``to_set`` (accepts an int client id, a
      role set / query, an Agent, or a list) → each id's page via
      ``gui_page_for_client``. Non-client ids resolve to no page and are skipped,
      so a mixed role set is fine.
    """
    if to is None:
        page = FrameContext.page
        return [page] if page is not None and getattr(page, "overlays", None) else []
    pages = []
    for cid in to_set(to):
        p = gui_page_for_client(cid)
        if p is not None and getattr(p, "overlays", None) is not None:
            pages.append(p)
    return pages


def _on_page(page, fn):
    """Run ``fn(page.overlays)`` in ``page``'s FrameContext so the overlay builder's
    page/task/event target that client (the gui_reroute_client template)."""
    fe = FakeEvent(page.client_id, "overlay")
    with FrameContextOverride(page.gui_task, page, fe):
        fn(page.overlays)


def overlay_show(slot, kind, to=None, **content):
    """Show an overlay in ``slot`` using content builder ``kind``.

    Args:
        slot (str): a slot name (see ``OVERLAY_SLOTS``); unknown names use a
            centered default rect.
        kind (str): a registered builder (see ``overlay_register``).
        to: target consoles — ``None`` = the current console; an int client id; or a
            role set / query (e.g. ``role("mainscreen")``). Non-console ids are ignored.
        **content: fields passed through to the builder.
    """
    for page in _pages_for(to):
        _on_page(page, lambda ov: ov.show(slot, kind, content))


def overlay_clear(slot=None, to=None):
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets."""
    for page in _pages_for(to):
        _on_page(page, lambda ov: ov.clear(slot))


# --- Signal bridge -----------------------------------------------------------
# There is no Python signal-callback registry (a //signal route must be a MAST
# label), so a mission authors a one-line route that forwards to these helpers.
# Use //shared/signal so the dispatch runs ONCE on the server and fans out to the
# `to` targets (a per-console //signal would run N times, each pushing to all
# targets). Content travels as a nested ``fields`` dict so the route needs no **kw.
#
#   # emit from anywhere:
#   signal_emit("overlay", {"to": role("mainscreen"), "slot": "center_hero",
#                           "kind": "hero", "fields": {"title": "CHAPTER ONE"}})
#   # forward once, on the server:
#   //shared/signal/overlay
#       overlay_signal_show(to, slot, kind, fields)
#   //shared/signal/overlay_clear
#       overlay_signal_clear(to, slot)
def overlay_signal_show(to, slot, kind, fields=None):
    """Signal-route forwarder: overlay_show with content supplied as a dict."""
    overlay_show(slot, kind, to=to, **(fields or {}))


def overlay_signal_clear(to=None, slot=None):
    """Signal-route forwarder for clear."""
    overlay_clear(slot, to=to)


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
