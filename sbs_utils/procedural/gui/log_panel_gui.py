"""Info-panel tab that shows the ship's log - the GUI half of the Log Panel.

Kept apart from `procedural.log_panel` on purpose: the store and the renderer are pure,
so what a player ends up reading is testable without a console. This module is the thin
part that cannot be - it reads the client's ship and hands the rendered text to a widget.

Mounted as an ordinary info-panel tab (`gui_info_panel_add`), which is what the brainstorm
meant by "a tab panel similar to the info panel" - that panel already exists, already has
tabs with icons, and already hosts other content on the comms console.
"""
from ...helpers import FrameContext
from ..log_panel import (log_entries, log_render, log_newest_seq,
                         log_mark_seen, TAB_LOG, TAB_SHIP, TAB_MISSION)
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
    ship = _ship_of(cid)
    if ship is None:
        return
    text, styles = log_render(log_entries(ship, tab))
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
    ship = _ship_of(info_panel.client_id)
    if ship is None:
        return 1
    if log_mark_seen(info_panel.client_id, log_newest_seq(ship)):
        return 2      # grew - redraw
    return 1          # unchanged - stay put, draw nothing
