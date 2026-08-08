"""Info-panel tab that shows the ship's log - the GUI half of the Log Panel.

Kept apart from `procedural.log_panel` on purpose: the store and the renderer are pure,
so what a player ends up reading is testable without a console. This module is the thin
part that cannot be - it reads the client's ship and hands the rendered text to a widget.

Mounted as an ordinary info-panel tab (`gui_info_panel_add`), which is what the brainstorm
meant by "a tab panel similar to the info panel" - that panel already exists, already has
tabs with icons, and already hosts other content on the comms console.
"""
from ...helpers import FrameContext
from ..log_panel import (log_entries_union, log_render, log_newest_seq_union,
                         log_mark_seen, TAB_LOG, TAB_SHIP, TAB_MISSION,
                         LOG_TAIL_LINES, LOG_TAIL_BACKGROUND)
from .text import gui_text_area


def _ship_of(cid):
    """The scope a console's log belongs to: its SHIP, so every console on a bridge
    reads the same log rather than five diverging ones."""
    ctx = FrameContext.context
    if ctx is None or ctx.sbs is None:
        return None
    try:
        ship = ctx.sbs.get_ship_of_client(cid)
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
    text, styles = log_render(log_entries_union([_ship_of(cid), cid], tab))
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


# Severities that pull the log to the front. `tip` deliberately does not: good news can
# wait, and a surface that grabs the console for every completion becomes one the crew
# learns to resent.
RAISE_ON = ("warning", "danger")


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

    if is_client_id(scope):
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
    text, styles = log_render(entries)
    bg = LOG_TAIL_BACKGROUND if background is None else background
    props = f"background:{bg};padding:4px,6px,4px,6px;" + (style or "")
    return gui_text_area(text, props, markdown=False, line_styles=styles)
