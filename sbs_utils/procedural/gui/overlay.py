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

# Per-kind conventions shared by every front door (wrappers, AMD records, quest
# directives) so one kind means one slot and one "primary" text field everywhere.
_KIND_DEFAULT_SLOT = {
    "hero": "center_hero", "credits": "fullscreen", "choice": "center_hero",
    "toast": "corner_toast", "banner": "top_banner", "lower_third": "lower_third",
    "lower_third_portrait": "lower_third",
    "letterbox": "fullscreen", "flash": "fullscreen", "hud": "hud",
}
# Kinds whose text lives on ONE line and can therefore be split into timed parts
# when it does not fit: kind -> (field, font tag used by its builder).
_CYCLE_KINDS = {"banner": ("text", "gui-4"), "lower_third": ("line", "gui-3"),
                "lower_third_portrait": ("line", "gui-3")}

# Fraction of the slot's width the cycled line actually gets. A kind that spends
# part of the strip on something else (a portrait) must measure against what is
# LEFT, or it splits into segments that still do not fit.
_KIND_TEXT_WIDTH = {}

# A subtitle plays through once - a repeating one reads as a stutter.
_KIND_LOOP_DEFAULT = {"lower_third": False, "lower_third_portrait": False}

# the field a bare line of text lands in for each kind
_KIND_PRIMARY_FIELD = {
    "hero": "title", "credits": "title", "choice": "title",
    "toast": "text", "banner": "text", "lower_third": "line",
    "lower_third_portrait": "line", "letterbox": "line",
}


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


def overlay_register_label(kind, label):
    """Register a MAST **label** as the builder for ``kind`` — the MAST-native way to
    author a custom overlay card without a Python builder.

    The label builds the card with the usual ``gui_*`` verbs and ends (``->END``);
    the content fields passed to ``overlay_show`` arrive as task variables. It is
    re-run on every repaint, so keep it **build-only** (no ``await``, no state
    changes). Reference the label by name from top-level MAST::

        === my_hero_card
            gui_row("row-height: content;")
            gui_text(f"$text:`{title}`;justify:center;font:gui-6")
            ->END

        overlay_register_label("my_hero", my_hero_card)
        # then anywhere: overlay_show("center_hero", "my_hero", title="CHAPTER TWO")
    """
    def _label_builder(cid, content):
        # We are inside OverlayRegion._build_content: FrameContext.page is the
        # SubPage and its slot section is the active layout. Run the label the same
        # way a signal route runs (start_task + tick_in_context), but redirect the
        # scheduler's page at the SubPage first so the label's gui_* build INTO the
        # slot (a task ticks into `main.page`). unscheduled=True -> the one-shot
        # builder task is never added to the scheduler, so nothing lingers.
        from .gui import gui_task_for_client
        sub_page = FrameContext.page
        gtask = gui_task_for_client(cid)
        if gtask is None or sub_page is None:
            return
        scheduler = gtask.main
        saved_page = scheduler.page
        scheduler.page = sub_page
        try:
            data = {k: v for k, v in content.items() if k != "kind"}
            st = gtask.start_task(label, data, defer=True, inherit=False, unscheduled=True)
            st.tick_in_context()         # build-only label completes in one tick
            # unscheduled -> never enters scheduler.tasks, so the normal done-task
            # disposal never sees it. Unregister it here or every overlay rebuild
            # leaks one task into Agent.all.
            st.dispose()
        except Exception as e:
            print(f"[overlay] label builder for '{kind}' failed: {e}")
            print(traceback.format_exc())
        finally:
            scheduler.page = saved_page

    OVERLAY_KINDS[kind] = _label_builder
    return label


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
        # bumped on every content change; a pending transient dismiss captures it and
        # only fires when it still matches, so re-showing a slot supersedes an older
        # auto-dismiss instead of clearing the newer content.
        self.generation = 0

    @property
    def is_empty(self):
        return self.content is None

    def _fill(self, event):
        """Draw the slot's content, or an invisible placeholder when empty.

        The engine only swaps the back buffer forward on `complete` when it holds
        SOMETHING; an empty back buffer isn't swapped (stale content stays). So an
        empty slot still emits one placeholder (a space renders nothing)."""
        if self.content is None:
            FrameContext.context.sbs.send_gui_text(
                event.client_id, self.local_region_tag, f"{self.tag_prefix}_blank",
                "$text:` `;", 0.0, 0.0, 100.0, 100.0)
        else:
            self._build_content(event)

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
        r.generation += 1               # supersede any pending auto-dismiss
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
        r.generation += 1
        _dbg(f"clear slot={slot} established={r.established}")
        if r.established:
            r.update(self._event())       # out-of-band clear (region already live)

    def patch(self, slot, fields):
        """Merge ``fields`` into a live slot's content and redraw it — the cheap
        update path for a sticky HUD (out-of-band if established, else a repaint).
        No-op if the slot was never shown."""
        r = self.slots.get(slot)
        if r is None or r.content is None:
            return
        r.content.update(fields)
        r.generation += 1
        if r.established:
            r.update(self._event())
        else:
            self._request_repaint()

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
# --- Audience resolution ("to" is an audience EXPRESSION) --------------------
# Overlays draw on CONSOLES, but authors naturally hold ships and sides (that is
# what comms_broadcast takes). So `to` accepts any of them and this resolves down
# to console client ids. Ids are bit-typed, so the dispatch is unambiguous:
#
#   None              -> the current console
#   client id         -> that console
#   space-object id   -> linked_to(ship, "consoles")     (that ship's consoles)
#   side key / side id-> consoles of every ship on that side
#   set / list        -> the union, elementwise (a mixed role set is fine)
#   anything else     -> skipped
#
# `consoles=` narrows the result by console role ("mainscreen", "science, comms").
_WARNED_EMPTY = set()


def _consoles_of_ship(ship_id):
    from ..links import linked_to
    return set(linked_to(ship_id, "consoles"))


def _consoles_of_ships(ships):
    out = set()
    for ship in ships:
        out |= _consoles_of_ship(ship)
    return out


def _expand_audience_item(item):
    """Resolve ONE audience item to a set of console client ids."""
    from ..query import to_id, is_client_id, is_space_object_id
    from ..roles import has_role
    from ..sides import to_side_id, side_members_set

    # A bare string is a SIDE KEY. role(...) returns a set, so there is no clash.
    if isinstance(item, str):
        side_id = to_side_id(item, warn=False)
        if side_id is None:
            return set()
        return _consoles_of_ships(side_members_set(side_id))

    cid = to_id(item)
    if not isinstance(cid, int):
        return set()
    if cid == 0:
        return {0}                       # the server console — only when named explicitly
    # Ship BEFORE side: to_side_id() happily maps a space object to its side, which
    # would silently widen "this ship" into "everyone on its side".
    if is_space_object_id(cid):
        return _consoles_of_ship(cid)
    if has_role(cid, "__side__"):
        return _consoles_of_ships(side_members_set(cid))
    # A console: the client bit, or (belt and braces) any agent that owns a page.
    if is_client_id(cid) or gui_page_for_client(cid) is not None:
        return {cid}
    return set()


def consoles_of(to, consoles=None):
    """Resolve an audience expression to a set of console client ids.

    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.

    Returns:
        set[int]: console client ids (possibly empty).
    """
    if to is None:
        page = FrameContext.page
        ids = {page.client_id} if page is not None else set()
    else:
        items = to if isinstance(to, (set, frozenset, list, tuple)) else [to]
        ids = set()
        for item in items:
            ids |= _expand_audience_item(item)
        # A scalar that resolves to nothing is the hard-to-see bug ("I passed a
        # thing and saw no overlay"), so say so once. An empty SET is normal — no
        # consoles connected, NPCs in the set — and stays quiet.
        if not ids and not isinstance(to, (set, frozenset, list, tuple)):
            key = str(to)
            if key not in _WARNED_EMPTY:
                _WARNED_EMPTY.add(key)
                from ...mast.mast import DEBUG
                DEBUG(f"[overlay] to={key!r} resolved to no console; overlay not shown")
    if consoles and ids:
        from ..roles import any_role
        narrowed = ids & any_role(consoles)
        if not narrowed:
            # The audience existed and the NARROWING emptied it: those consoles are
            # not connected, or they carry CONSOLE_TYPE without the matching role.
            # This is the silent one - a hero card addressed to "mainscreen" with no
            # main screen up just never appears, with nothing logged anywhere. Say it
            # once per console set so a missing card is findable.
            key = f"consoles={consoles}"
            if key not in _WARNED_EMPTY:
                _WARNED_EMPTY.add(key)
                from ...mast.mast import DEBUG
                DEBUG(f"[overlay] no console matched {consoles!r} "
                      f"({len(ids)} in the audience); overlay not shown")
        ids = narrowed
    return ids


def _pages_for(to, consoles=None):
    """Resolve a ``to`` target to a list of client pages that have an overlay
    manager (see ``consoles_of`` for what ``to`` accepts)."""
    if to is None and not consoles:
        page = FrameContext.page
        return [page] if page is not None and getattr(page, "overlays", None) else []
    pages = []
    for cid in consoles_of(to, consoles):
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


def overlay_show(slot, kind, to=None, consoles=None, **content):
    """Show an overlay in ``slot`` using content builder ``kind``.

    Args:
        slot (str): a slot name (see ``OVERLAY_SLOTS``); unknown names use a
            centered default rect.
        kind (str): a registered builder (see ``overlay_register``).
        to: the audience — ``None`` = the current console; a client id; a **ship**
            (its consoles); a **side** key/agent (that side's consoles); or a set /
            role query mixing them. See ``consoles_of``.
        consoles (str, optional): narrow the audience to consoles with these roles,
            e.g. ``"mainscreen"``.
        **content: fields passed through to the builder.
    """
    for page in _pages_for(to, consoles):
        _on_page(page, lambda ov: ov.show(slot, kind, content))


def overlay_clear(slot=None, to=None, consoles=None):
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets."""
    for page in _pages_for(to, consoles):
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
    from .face import gui_face
    from .ship import gui_ship
    from .icon import gui_icon
    from .row import gui_row
    from .section import gui_sub_section

    title = content.get("title", "")
    subtitle = content.get("subtitle")
    # A scrim behind the card. Over a bright 3D view white-on-nothing is hard to
    # read, so callers can lay a (usually translucent) colour under the rows.
    bg = content.get("background")
    row_bg = f"background: {bg};" if bg else ""

    # Optional visual above the title (first one set wins).
    face = content.get("face")     # a face string  (get_face(id) / a lifeform face)
    ship = content.get("ship")     # a ship-type key (e.g. "tsn_battle_cruiser")
    icon = content.get("icon")     # an icon index   (int)
    image = content.get("image")   # an image key
    if face:
        gui_row(f"row-height: 8em;{row_bg}")
        gui_face(face)
    elif ship:
        gui_row(f"row-height: 8em;{row_bg}")
        gui_ship(ship)
    elif icon is not None:
        gui_row(f"row-height: 8em;{row_bg}")
        gui_icon(f"icon_index: {icon}; color: white;")
    elif image:
        gui_row(f"row-height: 8em;{row_bg}")
        with gui_sub_section():
            gui_image_keep_aspect_ratio_center(image)
    gui_row(f"row-height: content;{row_bg}")
    gui_text(f"$text:`{title}`;justify:center;font:gui-6;color:#fff")
    if subtitle:
        gui_row(f"row-height: content;{row_bg}")
        gui_text(f"$text:`{subtitle}`;justify:center;font:gui-3;color:#8cf")


overlay_register("hero", _hero_builder)


# --- Transient (auto-dismiss) ------------------------------------------------
def _schedule_dismiss(page, slot, gen, seconds):
    """Auto-clear ``page``'s ``slot`` after ``seconds`` — but only if it still holds
    generation ``gen`` (i.e. it wasn't re-shown / updated / already cleared in the
    meantime). One-shot tick; runs in the target page's FrameContext."""
    if not seconds or seconds <= 0:
        return
    from ...tickdispatcher import TickDispatcher

    def _fire(t):
        r = page.overlays.slots.get(slot)
        if r is not None and r.generation == gen and r.content is not None:
            _on_page(page, lambda ov: ov.clear(slot))

    return TickDispatcher.do_once(_fire, seconds)


def _show_transient(slot, kind, to, seconds, content, consoles=None):
    """Show an overlay and, if ``seconds`` is set, auto-clear it after that long.
    The dismiss is generation-guarded per target page, so re-showing the slot before
    the timer fires supersedes it instead of clearing the newer content."""
    overlay_show(slot, kind, to=to, consoles=consoles, **content)
    if seconds and seconds > 0:
        for page in _pages_for(to, consoles):
            r = page.overlays.slots.get(slot)
            if r is not None:
                _schedule_dismiss(page, slot, r.generation, seconds)


def overlay_kind(kind, to=None, consoles=None, slot=None, seconds=None, **fields):
    """Low-level front door: show any registered ``kind`` with its default slot.

    The escape hatch for callers that pick the kind at runtime (the quest driver's
    inline overlay directives, AMD records). Prefer the named wrappers when the
    kind is known at author time."""
    slot = slot or _KIND_DEFAULT_SLOT.get(kind, "center_hero")
    # Single-line kinds route through the cycling path, so text that will not fit
    # is played in timed parts here too - the quest/AMD front doors get the same
    # behaviour as a direct overlay_banner() call rather than a clipped strip.
    if kind in _CYCLE_KINDS:
        field, font = _CYCLE_KINDS[kind]
        return _show_maybe_cycled(slot, kind, to, consoles, seconds, fields, field,
                                  font, True, None, _KIND_LOOP_DEFAULT.get(kind))
    _show_transient(slot, kind, to, seconds, fields, consoles)


def overlay_hero(title, subtitle=None, image=None, face=None, ship=None, icon=None,
                 slot="center_hero", to=None, consoles=None, seconds=None,
                 background=None, letterbox=False, bar=4):
    """Show a big centered hero / chapter card with an optional visual above the
    title (first set wins): ``face`` (a face string), ``ship`` (a ship-type key),
    ``icon`` (an icon index), or ``image`` (an image key). Auto-dismiss after
    ``seconds`` if set.

    Args:
        background (str, optional): a colour laid under the card's rows - a scrim,
            so the text stays legible over a bright 3D view. Usually translucent
            (``"#000a"``).
        letterbox (bool | str): also drop cinematic bars on the full-screen slot,
            so one call gives a framed title card. Pass a string to use it as the
            line between the bars. Lifts together with the card when ``seconds``
            is set.
        bar (int): letterbox bar height in em.
    """
    if letterbox:
        line = letterbox if isinstance(letterbox, str) else None
        overlay_letterbox(line=line, bar=bar, to=to, consoles=consoles, seconds=seconds)
    _show_transient(slot, "hero", to, seconds,
                    {"title": title, "subtitle": subtitle, "background": background,
                     "image": image, "face": face, "ship": ship, "icon": icon},
                    consoles)


# --- Toast (corner, transient, STACKING) -------------------------------------
# Toasts stack: each overlay_toast appends an entry (with a unique id) and schedules
# its OWN removal, so several notifications coexist instead of clobbering each other.
_TOAST_SEQ = [0]
TOAST_MAX = 4


def _toast_builder(client_id, content):
    from .text import gui_text
    from .row import gui_row
    # `items` = the stack; fall back to a single {text} (amd / quest inline path).
    items = content.get("items")
    if items is None:
        items = [{"text": content.get("text", "")}]
    for it in items:
        gui_row("row-height: content;")
        gui_text(f"$text:`{it.get('text', '')}`;justify:center;font:gui-2;color:#fff")


overlay_register("toast", _toast_builder)


def _toast_push(ov, slot, item):
    r = ov._region(slot)
    items = (r.content or {}).get("items") if r.content else None
    items = (list(items) if items else []) + [item]
    if len(items) > TOAST_MAX:
        items = items[-TOAST_MAX:]
    ov.show(slot, "toast", {"items": items})


def _schedule_toast_remove(page, slot, tid, seconds):
    if not seconds or seconds <= 0:
        return
    from ...tickdispatcher import TickDispatcher

    def _fire(t):
        r = page.overlays.slots.get(slot)
        items = (r.content or {}).get("items") if (r and r.content) else None
        if not items:
            return
        remaining = [it for it in items if it.get("tid") != tid]
        if len(remaining) == len(items):
            return
        if remaining:
            _on_page(page, lambda ov: ov.show(slot, "toast", {"items": remaining}))
        else:
            _on_page(page, lambda ov: ov.clear(slot))

    TickDispatcher.do_once(_fire, seconds)


def overlay_toast(text, icon=None, seconds=3, to=None, consoles=None, slot="corner_toast"):
    """Small transient corner notification. Toasts STACK — several coexist, each
    auto-clearing after its own ``seconds`` (default 3), capped at TOAST_MAX."""
    _TOAST_SEQ[0] += 1
    tid = _TOAST_SEQ[0]
    item = {"text": text, "icon": icon, "tid": tid}
    for page in _pages_for(to, consoles):
        _on_page(page, lambda ov: _toast_push(ov, slot, item))
        _schedule_toast_remove(page, slot, tid, seconds)


# --- Text that does not fit: split it, and time the parts --------------------
# A single-line slot (the banner strip, a lower third) has a hard width. Clamping
# a long line keeps it readable but throws away the tail -- which for an alert is
# usually the part that matters. So instead: measure, split into segments that
# each FIT, and show them in sequence.
#
# Measurement is the engine's (pages/layout/measure.wrap_to_width), the same
# primitive content-sizing uses, so a segment that comes back has really been
# measured to fit rather than counted in characters. If the engine cannot measure
# (headless, no client), the text is left whole and the slot behaves as before.
WORDS_PER_SECOND = 2.6      # unhurried reading pace for the auto dwell
DWELL_MIN = 2.5
DWELL_MAX = 7.0


def _slot_px_width(client_id, slot, pad=0.96):
    """Pixel width available to a slot's text on this client's screen."""
    from ...gui import get_client_aspect_ratio
    spec = OVERLAY_SLOTS.get(slot, DEFAULT_SLOT)
    left, _t, right, _b = spec["rect"]
    ar = get_client_aspect_ratio(client_id)
    if ar is None or not getattr(ar, "x", 0):
        return None
    return ((right - left) / 100.0) * ar.x * pad


def _slot_px_height(client_id, slot):
    """Pixel height of a slot on this client's screen - the ceiling on how wide
    a SQUARE widget inside it can be."""
    from ...gui import get_client_aspect_ratio
    spec = OVERLAY_SLOTS.get(slot, DEFAULT_SLOT)
    _l, top, _r, bottom = spec["rect"]
    ar = get_client_aspect_ratio(client_id)
    if ar is None or not getattr(ar, "y", 0):
        return None
    return ((bottom - top) / 100.0) * ar.y


def _split_to_fit(client_id, slot, text, font, width_frac=1.0):
    """Segments of ``text`` that each fit the slot, or ``[text]`` when it already
    fits (or cannot be measured).

    ``width_frac`` is the share of the slot the text actually gets - a portrait
    lower third leaves the line only part of the strip.
    """
    text = " ".join(str(text or "").split())
    if not text:
        return [""]
    px = _slot_px_width(client_id, slot)
    if not px:
        return [text]
    px = px * max(0.05, min(1.0, width_frac))
    try:
        from ...pages.layout.measure import measure_line_width, wrap_to_width
        w = measure_line_width(font, text)
        if w is None:              # unmeasurable -> leave it to the engine
            return [text]
        if w <= px:
            return [text]
        segments = wrap_to_width(font, text, px)
    except Exception:
        return [text]
    return [seg for seg in segments if seg.strip()] or [text]


def _auto_dwell(segment):
    """Seconds to hold one segment - long enough to read, short enough to move on."""
    words = max(1, len(segment.split()))
    return min(DWELL_MAX, max(DWELL_MIN, words / WORDS_PER_SECOND))


def _start_text_cycle(page, slot, kind, fields, field, segments, dwell, loop):
    """Show ``segments`` one at a time in ``slot``, advancing on a tick.

    Generation-guarded: every show bumps the region's generation, so if anything
    else claims the slot (a newer banner, a clear) the cycle notices its own
    generation is stale and stops instead of fighting for the strip.
    """
    from ...tickdispatcher import TickDispatcher
    state = {"i": 0, "gen": None, "task": None}

    def _paint(index):
        data = dict(fields)
        data[field] = segments[index]
        _on_page(page, lambda ov: ov.show(slot, kind, data))
        r = page.overlays.slots.get(slot)
        state["gen"] = r.generation if r is not None else None

    def _advance(t):
        r = page.overlays.slots.get(slot)
        if r is None or r.generation != state["gen"]:
            t.stop()                      # someone else owns the slot now
            return
        state["i"] += 1
        if state["i"] >= len(segments):
            if not loop:
                t.stop()
                _on_page(page, lambda ov: ov.clear(slot))
                return
            state["i"] = 0
        _paint(state["i"])
        t.delay = _dwell_for(state["i"])

    def _dwell_for(index):
        return dwell if dwell else _auto_dwell(segments[index])

    _paint(0)
    state["task"] = TickDispatcher.do_interval(_advance, _dwell_for(0))
    return state["task"]


def _show_maybe_cycled(slot, kind, to, consoles, seconds, fields, field, font,
                       cycle, dwell, loop, width_frac=None):
    """Show a single-line overlay, splitting into timed parts when it will not fit.

    The split is PER CLIENT, because "does it fit" depends on that screen's width.
    """
    text = fields.get(field, "")
    pages = _pages_for(to, consoles)
    cycled_any = False
    for page in pages:
        # PER CLIENT too: a kind whose share depends on a square widget depends
        # on that screen's aspect ratio, so the fraction is resolved here rather
        # than once for everybody.
        frac = width_frac
        if frac is None:
            frac = _KIND_TEXT_WIDTH.get(kind, 1.0)
            if callable(frac):
                frac = frac(page.client_id, slot)
        segments = (_split_to_fit(page.client_id, slot, text, font, frac)
                    if cycle else [text])
        if len(segments) <= 1:
            data = dict(fields)
            data[field] = segments[0] if segments else text
            _on_page(page, lambda ov: ov.show(slot, kind, data))
            if seconds and seconds > 0:
                r = page.overlays.slots.get(slot)
                if r is not None:
                    _schedule_dismiss(page, slot, r.generation, seconds)
            continue
        cycled_any = True
        do_loop = (seconds is None) if loop is None else loop
        _start_text_cycle(page, slot, kind, fields, field, segments, dwell, do_loop)
        if seconds and seconds > 0:
            r = page.overlays.slots.get(slot)
            if r is not None:
                _schedule_dismiss(page, slot, r.generation, seconds)
    return cycled_any


# --- Banner (full-width strip) -----------------------------------------------
def _banner_builder(client_id, content):
    from .text import gui_text
    from .row import gui_row
    text = content.get("text", "")
    color = content.get("color", "#fd0")
    # A filled strip reads as a banner; without one the text floats on whatever
    # the view happens to be showing. Translucent by default so the view survives.
    bg = content.get("background", "#000a")
    row_bg = f"background: {bg};" if bg else ""
    gui_row(f"row-height: content;{row_bg}")
    gui_text(f"$text:`{text}`;justify:center;font:gui-4;color:{color}")


overlay_register("banner", _banner_builder)


def overlay_banner(text, color="#fd0", slot="top_banner", to=None, consoles=None,
                   seconds=None, background="#000a", cycle=True, dwell=None,
                   loop=None):
    """Full-width top strip (alert / countdown). Auto-dismiss after ``seconds`` if set.
    Re-call it to update in place (generation-guarded) - a countdown needs no new API.

    ``background`` fills the strip (translucent black by default) so the text reads
    over the live view; pass ``None`` for bare text on the view.

    **Text too long for the strip is shown in timed parts** rather than clipped:
    it is measured against that client's screen, split into segments that each fit,
    and advanced on a tick.

    Args:
        cycle (bool): split-and-cycle when the text does not fit. Default True;
            pass False to let a long line spill/clip as before.
        dwell (float, optional): seconds per part. Default: paced by word count
            (about 2.6 words/second, clamped to 2.5-7s).
        loop (bool, optional): repeat the sequence. Default: loop while the banner
            is sticky (no ``seconds``), play once when it has a lifetime.
    """
    return _show_maybe_cycled(
        slot, "banner", to, consoles, seconds,
        {"text": text, "color": color, "background": background}, "text",
        "gui-4", cycle, dwell, loop)


# --- Lower third (name-plate + line) -----------------------------------------
def _lower_third_builder(client_id, content):
    from .text import gui_text
    from .row import gui_row
    name = content.get("name", "")
    line = content.get("line", "")
    if name:
        gui_row("row-height: content;")
        gui_text(f"$text:`{name}`;font:gui-4;color:#8cf")
    gui_row("row-height: content;")
    gui_text(f"$text:`{line}`;font:gui-3;color:#fff")


overlay_register("lower_third", _lower_third_builder)


def overlay_lower_third(name, line, slot="lower_third", to=None, consoles=None,
                        seconds=None, cycle=True, dwell=None, loop=None):
    """Bottom name-plate + subtitle line (someone speaking over the live view).

    A line too long for the plate is shown in **timed parts** rather than clipped -
    which is what subtitles want anyway: the speaker's line arrives in readable
    chunks while their audio plays. See ``overlay_banner`` for ``cycle`` / ``dwell``
    / ``loop``; a lower third defaults to playing through once (``loop=False``)
    because a repeating subtitle reads as a stutter."""
    if loop is None:
        loop = False
    return _show_maybe_cycled(
        slot, "lower_third", to, consoles, seconds,
        {"name": name, "line": line}, "line", "gui-3", cycle, dwell, loop)


# --- Lower third with a portrait (ONE face, on either side) ------------------
# A conversation is this strip with the face ALTERNATING sides between beats -
# not two portraits on screen at once. One face keeps the width for the line,
# and it still reads for a monologue or a three-hander, which a fixed two-face
# layout does not.
# The visual is ALWAYS SQUARE, and that requirement is the design: it makes the
# bite out of the strip, the gutter, the placeholder and the cycling width
# identical whichever of the four sources is used, so a variant costs one branch
# instead of a layout each.
#
# `col-width: square` says it for all of them. Sizing the visual by hand is not a
# tuning choice but a bug: a bare `col-width: 22` is an absolute percent of the
# region, so 22 + 78 oversubscribes a strip that is not full width, and a square
# carrying a width is double-counted on top of that - and the engine DOES NOT
# CLIP, so the surplus is drawn outside the box and over its neighbours.
SQUARE_STYLE = "col-width: square;"
PORTRAIT_EM = 6.0            # strip height - the square visual sizes itself from it
PORTRAIT_GUTTER_EM = 0.6     # thin separator column between the visual and the text


def _lower_third_portrait_builder(client_id, content):
    from .text import gui_text
    from .face import gui_face
    from .ship import gui_ship
    from .icon import gui_icon
    from .image import gui_image_keep_aspect_ratio_center
    from .blank import gui_blank
    from .row import gui_row
    from .section import gui_sub_section

    name = content.get("name", "")
    line = content.get("line", "")
    # First set wins, in overlay_hero's order, so the two cards agree.
    face = content.get("face")
    ship = content.get("ship")
    icon = content.get("icon")
    image = content.get("image")
    # "align" (not "side"): in Cosmos a side is a FACTION, and this is a layout.
    align = str(content.get("align", "left")).lower()
    right = align in ("right", "r", "end")
    color = content.get("color", "#8cf")
    bg = content.get("background", "#000a")
    just = "right" if right else "left"

    def _face_col():
        # Face and Icon are square already; Ship and Image are NOT (Ship's square
        # line is commented out, Image never sets one), so unsquared they are flex
        # columns that take half the strip. Saying it explicitly for all four is
        # both the fix and the thing that keeps them interchangeable.
        if face:
            gui_face(face, style=SQUARE_STYLE)
        elif ship:
            gui_ship(ship, style=SQUARE_STYLE)
        elif icon:
            gui_icon(icon, style=SQUARE_STYLE)
        elif image:
            # A square BOX with aspect-preserved content, so a non-square source
            # letterboxes rather than distorting.
            gui_image_keep_aspect_ratio_center(image, style=SQUARE_STYLE)
        else:
            # Hold the same bite of the strip so a run of beats does not slide
            # sideways when a speaker has no visual. A square in this row is
            # about as wide as the row is tall, so ask for that.
            gui_blank(style=f"col-width: {PORTRAIT_EM}em;")

    def _gutter():
        gui_blank(style=f"col-width: {PORTRAIT_GUTTER_EM}em;")

    def _text_col():
        # No col-width: flex takes exactly what the face and gutter leave.
        with gui_sub_section():
            if name:
                gui_row("row-height: content;")
                gui_text(f"$text:`{name}`;justify:{just};font:gui-4;color:{color}")
            gui_row("row-height: content;")
            gui_text(f"$text:`{line}`;justify:{just};font:gui-3;color:#fff")

    gui_row(f"row-height: {PORTRAIT_EM}em;" + (f"background: {bg};" if bg else ""))
    # The text hangs off the portrait, so the columns swap with the face.
    if right:
        _text_col()
        _gutter()
        _face_col()
    else:
        _face_col()
        _gutter()
        _text_col()


overlay_register("lower_third_portrait", _lower_third_portrait_builder)


def _portrait_text_frac(client_id, slot):
    """Share of the strip left for the line once the square face has taken its
    bite.

    Not a constant: a square is sized from the row HEIGHT, so how much of the
    strip a portrait eats depends on the client's aspect ratio. Measuring the
    line against the full strip is how it ends up drawn across the portrait -
    the engine does not clip. The slot's height is the square's ceiling, so it
    is the safe estimate; erring wide only splits the line a beat early.
    """
    w = _slot_px_width(client_id, slot)
    h = _slot_px_height(client_id, slot)
    if not w or not h:
        return 0.75
    return max(0.3, (w - h) / w - PORTRAIT_GUTTER_EM / 40.0)


_KIND_TEXT_WIDTH["lower_third_portrait"] = _portrait_text_frac


def overlay_lower_third_portrait(name, line, face=None, ship=None, icon=None,
                                 image=None, align="left", slot="lower_third",
                                 to=None, consoles=None, seconds=None,
                                 color="#8cf", background="#000a",
                                 cycle=True, dwell=None, loop=None):
    """Lower third carrying ONE square visual, on the left or the right of the line.

    Same strip as ``overlay_lower_third``, plus a portrait. **A conversation is
    this called repeatedly with ``align`` alternating** - the visual moving side
    to side is what reads as a back-and-forth, and only the speaker is on screen.

    The visual is always laid out **square** (an image keeps its aspect ratio
    inside that square box), which is what makes the four sources interchangeable:
    the strip, the gutter and the space left for the line do not move when you
    swap a face for a ship.

    Args:
        name (str): the speaker's name plate.
        line (str): what they say. Too long for the remaining width and it is
            played in **timed parts** (measured against the strip MINUS the
            square), like ``overlay_lower_third``.
        face (str, optional): a face string - ``get_face(id)`` or a lifeform face.
        ship (str, optional): a ship-type key (e.g. ``"tsn_battle_cruiser"``) -
            a live 3D render.
        icon (str, optional): an icon property string or key.
        image (str, optional): an image key - letterboxed inside the square.
        align (str): ``"left"`` (default) or ``"right"`` - which side the visual
            sits on. Named ``align`` and not ``side`` because a *side* in Cosmos
            is a faction; this is layout only.
        color (str): the name-plate color.
        background (str): fill behind the strip so it reads over the live view;
            pass ``None`` for bare content.

    The four are **first set wins**, in ``overlay_hero``'s order (face, ship,
    icon, image). With none set the column is still reserved, so a run of beats
    does not jump sideways when one speaker has no visual.

    See ``overlay_banner`` for ``cycle`` / ``dwell`` / ``loop``.
    """
    if loop is None:
        loop = False
    return _show_maybe_cycled(
        slot, "lower_third_portrait", to, consoles, seconds,
        {"name": name, "line": line, "face": face, "ship": ship, "icon": icon,
         "image": image, "align": align, "color": color,
         "background": background},
        "line", "gui-3", cycle, dwell, loop)


# --- Credits (sequential list) -----------------------------------------------
def _credits_builder(client_id, content):
    from .text import gui_text
    from .row import gui_row
    title = content.get("title")
    entries = content.get("entries", [])
    if title:
        gui_row("row-height: content;")
        gui_text(f"$text:`{title}`;justify:center;font:gui-6;color:#fff")
    for entry in entries:
        gui_row("row-height: content;")
        gui_text(f"$text:`{entry}`;justify:center;font:gui-3;color:#cde")


overlay_register("credits", _credits_builder)


def _start_credits_roll(page, slot, title, entries, window, interval):
    """Page through ``entries`` a ``window`` at a time every ``interval`` seconds,
    then clear (a tick-driven auto-advance; smooth per-pixel scroll would need an
    engine animation channel the GUI layer doesn't expose)."""
    from ...tickdispatcher import TickDispatcher
    state = {"off": 0}

    def _paint():
        chunk = entries[state["off"]:state["off"] + window]
        _on_page(page, lambda ov: ov.show(slot, "credits", {"title": title, "entries": chunk}))

    def _advance(t):
        state["off"] += window
        if state["off"] >= len(entries):
            _on_page(page, lambda ov: ov.clear(slot))
            t.stop()
            return
        _paint()

    _paint()
    TickDispatcher.do_interval(_advance, interval)


def overlay_credits(entries, title=None, slot="fullscreen", to=None, consoles=None,
                    seconds=None, roll=None, window=8):
    """Opening/closing credits: a title + a list of lines. Static by default; pass
    ``roll`` (seconds per page) to auto-advance ``window`` lines at a time, clearing
    at the end."""
    entries = list(entries)
    if not roll:
        _show_transient(slot, "credits", to, seconds,
                        {"title": title, "entries": entries}, consoles)
        return
    for page in _pages_for(to, consoles):
        _start_credits_roll(page, slot, title, entries, window, roll)


# --- Choice (modal, returns an awaitable result) -----------------------------
def _choice_builder(client_id, content):
    from .text import gui_text
    from .button import gui_button
    from .row import gui_row

    title = content.get("title", "")
    buttons = content.get("buttons", [])
    prom = content.get("_promise")
    if title:
        gui_row("row-height: content;")
        gui_text(f"$text:`{title}`;justify:center;font:gui-5;color:#fff")
    for label in buttons:
        # each button on its own row; on_press=<Promise> resolves it on click,
        # data=label -> ButtonResult.data. data/on_press is the for-loop-safe path.
        gui_row("row-height: content;")
        gui_button(f"$text:`{label}`;justify:center;", data=label, on_press=prom)


overlay_register("choice", _choice_builder)


def overlay_choice(title, buttons, to=None, consoles=None, slot="center_hero"):
    """Show a modal choice card and return an awaitable that resolves when a button
    is pressed. Await it from a story/background task (not the target console's own
    gui task); the result's ``.data`` is the chosen label.

        result = await overlay_choice("Fire on the ambassador?", ["Yes", "No"], to=player)
        if result.data == "Yes":
            ...
    """
    from ...futures import Promise
    prom = Promise()
    overlay_show(slot, "choice", to=to, consoles=consoles, title=title,
                 buttons=list(buttons), _promise=prom)
    return prom


# --- HUD (sticky, live) ------------------------------------------------------
def _normalize_rows(rows):
    """Accept a dict or a list of (label, value) pairs; return a list of pairs."""
    if rows is None:
        return []
    if isinstance(rows, dict):
        return list(rows.items())
    return list(rows)


def _hud_builder(client_id, content):
    from .text import gui_text
    from .button import gui_button
    from .row import gui_row

    title = content.get("title")
    rows = content.get("rows", [])
    controls = content.get("controls", [])

    if title:
        gui_row("row-height: content;")
        gui_text(f"$text:`{title}`;font:gui-3;color:#8cf")
    for label, value in rows:
        # one text per row ("label: value") — reliable in the SubPage build
        # and cheap to re-fill; value updates flow through OverlayManager.patch.
        gui_row("row-height: content;")
        gui_text(f"$text:`{label}: {value}`;font:gui-2;color:#cff")
    for ctrl in controls:
        # persistent control: on_press as a sub-task so a toggle doesn't hijack
        # the console's own gui task. `action` is a MAST label or a callable.
        gui_row("row-height: content;")
        gui_button(f"$text:`{ctrl.get('label', '')}`;justify:center;",
                   data=ctrl.get("data"), on_press=ctrl.get("action"), is_sub_task=True)


overlay_register("hud", _hud_builder)


def overlay_hud(rows=None, controls=None, title=None, to=None, consoles=None, slot="hud"):
    """Show a sticky HUD (label/value rows + optional control buttons) over the
    live view. Stays until cleared. Update values with ``overlay_hud_update``.

    Args:
        rows: a dict or list of (label, value) pairs.
        controls: list of ``{"label":.., "action": <MAST label | callable>,
            "data":..}`` — rendered as persistent sub-task buttons.
    """
    overlay_show(slot, "hud", to=to, consoles=consoles, rows=_normalize_rows(rows),
                 controls=controls or [], title=title)


def overlay_hud_update(rows=None, title=None, to=None, consoles=None, slot="hud"):
    """Cheaply update a live HUD's rows (and/or title). Re-fills the slot region
    out-of-band — no page repaint. Watchers call this only when a displayed value
    actually changes."""
    patch = {}
    if rows is not None:
        patch["rows"] = _normalize_rows(rows)
    if title is not None:
        patch["title"] = title
    if not patch:
        return
    for page in _pages_for(to, consoles):
        _on_page(page, lambda ov: ov.patch(slot, patch))


# --- Fullscreen cinematic (letterbox, flash) ---------------------------------
def _letterbox_builder(client_id, content):
    from .text import gui_text
    from .row import gui_row
    from .blank import gui_blank

    line = content.get("line")
    bar = content.get("bar", 4)       # bar height in em (rows use em/px/fr, not %)
    gui_row(f"row-height: {bar}em; background: #000;")   # top bar
    gui_blank()
    gui_row("")                        # flex middle fills between the bars
    if line:
        gui_text(f"$text:`{line}`;justify:center;font:gui-3;color:#fff")
    else:
        gui_blank()
    gui_row(f"row-height: {bar}em; background: #000;")    # bottom bar
    gui_blank()


overlay_register("letterbox", _letterbox_builder)


def overlay_letterbox(line=None, bar=4, to=None, consoles=None, slot="fullscreen",
                      seconds=None):
    """Cinematic letterbox: black bars top+bottom (``bar`` em each) with an optional
    centered line. Sticky by default; pass ``seconds`` to auto-lift."""
    _show_transient(slot, "letterbox", to, seconds, {"line": line, "bar": bar}, consoles)


def _flash_builder(client_id, content):
    from .row import gui_row
    from .blank import gui_blank
    # A single flex row (fills the region) washed with a translucent color ("#f006").
    color = content.get("color", "#f006")
    gui_row(f"background: {color};")
    gui_blank()


overlay_register("flash", _flash_builder)


def overlay_flash(color="#f006", to=None, consoles=None, slot="fullscreen", seconds=0.4):
    """Full-screen color wash (hull hit, jump). Auto-dismisses fast (default 0.4s)."""
    _show_transient(slot, "flash", to, seconds, {"color": color}, consoles)
