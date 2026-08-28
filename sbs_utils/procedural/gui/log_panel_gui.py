"""Info-panel tab that shows the ship's log - the GUI half of the Log Panel.

Kept apart from `procedural.log_panel` on purpose: the store and the renderer are pure,
so what a player ends up reading is testable without a console. This module is the thin
part that cannot be - it reads the client's ship and hands the rendered text to a widget.

Mounted as an ordinary info-panel tab (`gui_info_panel_add`), which is what the brainstorm
meant by "a tab panel similar to the info panel" - that panel already exists, already has
tabs with icons, and already hosts other content on the comms console.
"""
from ...helpers import FrameContext
from ..log_panel import (log_entries_union, log_render, log_tail_render, log_newest_seq_union,
                         log_mark_seen, TAB_LOG, TAB_SHIP, TAB_MISSION,
                         LOG_TAIL_LINES, LOG_TAIL_BACKGROUND)
from .text import gui_text_area
from .gui import gui_page_for_client


def _ship_of(cid):
    """The scope a console's log belongs to: its SHIP, so every console on a bridge
    reads the same log rather than five diverging ones."""
    ctx = FrameContext.context
    if ctx is None or ctx.sbs is None:
        return None
    try:
        # Not get_ship_of_client: on a main screen driving a shot that answers with
        # the SUBJECT, so the tab would read out the enemy's log.
        from .viewscreen import viewscreen_home_ship
        ship = viewscreen_home_ship(cid)
    except Exception:
        return None
    return ship or None


def gui_panel_log(cid, left, top, width, height, tab=TAB_LOG):
    """Info-panel tab body: the ship's log, newest at the bottom.

    Oldest-first with the newest at the BOTTOM, which is what the waterfall did and what
    a running log should do - the text area follows the tail unless the reader has
    scrolled back (see TextArea.follow_tail).
    """
    # The ship's log PLUS anything addressed to this console alone. comms_broadcast
    # accepts either a ship or a client, so a console-only note has to show up somewhere -
    # reading only the ship scope recorded it and never displayed it.
    #
    # NEWEST FIRST, like the tail and like the `messages` tab this sits beside: new
    # content appears where you are already looking, instead of below the fold with the
    # widget needing to be scrolled to reach it. It also means the tab never depends on
    # follow_tail - the thing worth reading is at the top the moment it arrives.
    entries = list(reversed(log_entries_union([_ship_of(cid), cid], tab)))
    text, styles = log_render(entries)
    if not text:
        # An empty log should read as empty, not as a broken panel.
        gui_text_area("$text:(nothing here yet);color:#888;")
        return
    # markdown=False on purpose. Log lines are literal mission text, and a message that
    # happens to start with '#' or '-' must not become a heading or a bullet. It also
    # keeps the per-line styles (colors, callouts) authoritative rather than competing
    # with what markdown sniffing would infer.
    gui_text_area(text, markdown=False, line_styles=styles)


def gui_panel_log_ship(cid, left, top, width, height):
    """Info-panel tab: damage, systems, docking - Engineering's own feed."""
    gui_panel_log(cid, left, top, width, height, tab=TAB_SHIP)


def gui_panel_log_mission(cid, left, top, width, height):
    """Info-panel tab: objective and quest beats."""
    gui_panel_log(cid, left, top, width, height, tab=TAB_MISSION)


def gui_panel_log_tick(info_panel):
    """Redraw the log tab only when the log has actually grown.

    The panel's tick contract is 0 = done, 1 = stay, 2 = redraw. **Never 0 here**: 0
    means "this tab has nothing important" and sends the console back to its DEFAULT
    tab, which for a log the player deliberately opened would be a surface that closes
    itself.

    Comparing the newest ``seq`` rather than redrawing every tick keeps an idle log at
    zero render cost - this widget wraps every line on recalc, so a 1 Hz re-present of a
    500-line log would be real work for no change.
    """
    cid = info_panel.client_id
    if log_mark_seen(cid, log_newest_seq_union([_ship_of(cid), cid])):
        return 2      # grew - redraw
    return 1          # unchanged - stay put, draw nothing


# Severities that pull the log tab to the front. EMPTY by default -- nothing raises.
#
# Raising made sense while the log was only a tab: an urgent line the crew never opened
# the tab to see was a line lost. The ambient strip changed that. Every console now shows
# the newest line where it is already looking, in its severity color, without touching
# the panel -- so the reason to interrupt is gone, while the costs stayed: switching away
# from ship data (or a message card) that the crew chose, with nothing to switch back, so
# every warning left the panel stranded on the log.
#
# Kept as a dial rather than deleted: a mission that genuinely wants the panel seized can
# set RAISE_ON = ("danger",), and log_raise() is still callable directly for the one beat
# that has earned it.
RAISE_ON = ()


def log_raise(scope, tab=TAB_LOG):
    """Bring a log tab to the front on every console that would show this entry.

    The same move `gui_info_panel_send_message(notify=True)` makes for a card that must
    be seen now - reused rather than reinvented, so an urgent log entry behaves like every
    other interrupt on that panel.

    `scope` is a ship (raise on all its consoles) or a client (just that one).
    """
    from ...gui import Gui
    from ..query import to_id_list, is_client_id
    from ..links import linked_to
    from .tabbed_panel import gui_task_for_client

    # `or scope == 0` for the SERVER console: is_client_id tests the 0x8000... bit, which
    # 0 does not have - the same reason to_client_object spells that case out. Without it
    # a shipless server fell to the ship branch, linked_to(0, "consoles") came back empty,
    # and the host's info panel never popped to the tab the entry was written to.
    if is_client_id(scope) or scope == 0:
        client_ids = [scope]
    else:
        # Every console riding this ship - the log is the CREW's, so the interrupt is too.
        client_ids = [c for c in to_id_list(linked_to(scope, "consoles"))]
    for cid in client_ids:
        task = gui_task_for_client(cid)
        if task is None:
            continue
        panel = getattr(getattr(getattr(task, "main", None), "page", None), "info_panel", None)
        if panel is not None:
            panel.set_tab(tab)


def gui_log_tail(count=None, background=None, tab=TAB_LOG, style=None):
    """The last few log lines, drawn where a console's text waterfall used to be.

    The engine waterfall cannot be styled from script - its background is fixed, and too
    dark. This is the same content in a MAST text area, so the console owns its own look.

    It is the AMBIENT half of the log: always visible, no interaction, the last line or
    two. The history - filtered, scrollable, categorised - is the info-panel tab. Keeping
    both is deliberate: a crew reading ship data should still catch traffic going past
    without opening anything, and that is exactly what the tab cannot do.

    Args:
        count (int, optional): how many lines. Defaults to LOG_TAIL_LINES (2).
        background (str, optional): the strip's colour. Defaults to LOG_TAIL_BACKGROUND.
        tab (str, optional): which stream to tail. Defaults to everything.
        style (str, optional): extra style for the text area.
    """
    cid = FrameContext.client_id
    entries = log_entries_union([_ship_of(cid), cid], tab)
    count = LOG_TAIL_LINES if count is None else count
    if count > 0:
        entries = entries[-count:]
    # NEWEST FIRST. Two reasons, and neither is only about being easier:
    #
    # The newest line is then always in the SAME PLACE - you glance at the top rather than
    # tracking a line that moves as the strip fills. For an ambient surface that is read at
    # a glance and never scrolled, that is the whole job.
    #
    # And it takes the strip off the scroll machinery entirely. Showing the END of a text
    # area means the widget has to be scrolled there, which in the engine kept landing on
    # the top instead; showing the START needs nothing. `gui_panel_console_message_list`
    # already reads newest-first for the same reason.
    entries = list(reversed(entries))
    text, styles = log_tail_render(entries)
    bg = LOG_TAIL_BACKGROUND if background is None else background
    props = f"background:{bg};padding:4px,6px,4px,6px;" + (style or "")
    area = gui_text_area(text, props, markdown=False, line_styles=styles)
    # Remember it so new traffic can update it in place. gui_log_tail runs ONCE, when the
    # console builds its layout - without this the strip shows whatever the log held at
    # that instant and never changes, which reads as the feature not working at all.
    _TAILS[cid] = (area, tab, count, FrameContext.page)
    return area


# client id -> (text area, tab, count, page). Per-mission, so log_clear() drops it.
_TAILS = {}


def _tail_is_live(area, page):
    """Is this strip still part of what the client is actually looking at?

    _TAILS holds a widget REFERENCE, and setting its value marks it dirty - so the
    engine's dirty pass re-presents it wherever its old layout put it, long after that
    layout is gone. That is how the console strip turned up in the MIDDLE OF THE QUEST
    LIST: the quest tab never built one, and it runs on the same page (gui_activate_console
    only renames the console), so the orphan from the console layout simply redrew itself
    at the console's coordinates over whatever is there now.

    A page swaps tag_map wholesale when it rebuilds (maststorypage.present), so the tag
    missing from it means precisely "this widget belongs to a layout that no longer
    exists". pending_tag_map covers the window between building a layout and swapping it
    in, where the widget is real but not yet current.

    The entry has to be THIS widget, not merely something answering to the same tag.
    Tag numbers are recycled -- each build starts a fresh block and a page opened later
    starts over from the bottom -- so "the tag is present" was satisfied by whatever the
    NEW screen happened to give that number to, and the orphan read as live.
    """
    if page is None:
        return False
    tag = getattr(area, "tag", None)
    if tag is None:
        return False
    for name in ("tag_map", "pending_tag_map"):
        m = getattr(page, name, None)
        if not m or tag not in m:
            continue
        entry = m.get(tag)
        # tag_map holds (layout_item, runtime_node); older/other writers may hold
        # the item alone.
        item = entry[0] if isinstance(entry, tuple) else entry
        if item is area:
            return True
    return False


def log_tail_refresh(scope=None):
    """Push new traffic into every console's ambient strip.

    A push, like log_raise: the strip is built ONCE, when the console lays itself out, and
    the console is not otherwise repainting - so without this it keeps whatever the log
    held at that instant, which reads as the feature not working at all.

    `scope` is accepted for symmetry with log_raise but not used to filter: every strip
    recomputes its OWN union (its ship plus its client), which is the correct filter
    already, and there are only ever a handful of them. Both the text and the styles are
    replaced - `line_styles` is fixed at construction, so updating the value alone would
    leave the previous entry's color on the new line.
    """
    for cid, (area, tab, count, page) in list(_TAILS.items()):
        if not _tail_is_live(area, gui_page_for_client(cid) or page):
            # The console moved to another screen. Drop it rather than skip: the strip
            # re-registers the moment that console lays itself out again.
            _TAILS.pop(cid, None)
            continue
        entries = log_entries_union([_ship_of(cid), cid], tab)
        if count and count > 0:
            entries = entries[-count:]
        text, styles = log_tail_render(list(reversed(entries)))
        try:
            if area.value == text:
                continue                   # nothing new for this console
            area.line_styles = list(styles) if styles else None
            area.value = text
        except Exception:
            _TAILS.pop(cid, None)          # the widget went away with its page


def log_notify(scope, text, color=None, category=None, severity=None):
    """Log a line AND make it visible now: refresh the strips, raise the tab if urgent.

    The one front door for "the mission has something to say". Logging alone is not
    enough - the ambient strip is built once and the info panel keeps whatever tab the
    crew left it on - so every producer needs the same three steps, and each one that
    hand-rolled them got a different subset.

    Never raises: a fault in the log must not take a docking message or a broadcast with
    it. That mattered during the changeover and still does, since this is now the only
    surface some of those messages have.
    """
    try:
        from ..log_panel import log_add
        log_add(scope, text, color=color, category=category or TAB_LOG,
                severity=severity or "")
        log_tail_refresh(scope)
        # An urgent entry pulls the log to the front, the way a notify card does. Routine
        # traffic never does: a panel that grabs the console for every message is one the
        # crew learns to ignore, which defeats the point of raising at all.
        if severity in RAISE_ON:
            log_raise(scope)
    except Exception:
        pass


def log_notify_all(scopes, text, color=None, category=None, severity=None):
    """log_notify for an audience. Duplicate scopes are collapsed, so a crew whose
    consoles all resolve to one ship gets ONE entry, not one per console."""
    seen = []
    for scope in scopes:
        if scope is None or scope in seen:
            continue
        seen.append(scope)
        log_notify(scope, text, color=color, category=category, severity=severity)
    return seen
