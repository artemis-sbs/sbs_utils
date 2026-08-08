"""Info-panel tab that shows the ship's log - the GUI half of the Log Panel.

Kept apart from `procedural.log_panel` on purpose: the store and the renderer are pure,
so what a player ends up reading is testable without a console. This module is the thin
part that cannot be - it reads the client's ship and hands the rendered text to a widget.

Mounted as an ordinary info-panel tab (`gui_info_panel_add`), which is what the brainstorm
meant by "a tab panel similar to the info panel" - that panel already exists, already has
tabs with icons, and already hosts other content on the comms console.
"""
from ...helpers import FrameContext
from ..log_panel import log_entries, log_render, TAB_LOG
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
        gui_text_area("$text:(no log yet);color:#888;")
        return
    # markdown=False on purpose. Log lines are literal mission text, and a message that
    # happens to start with '#' or '-' must not become a heading or a bullet. It also
    # keeps the per-line styles (colors, callouts) authoritative rather than competing
    # with what markdown sniffing would infer.
    gui_text_area(text, markdown=False, line_styles=styles)
