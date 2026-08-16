from sbs_utils.helpers import FrameContext
def _ship_of (cid):
    """The scope a console's log belongs to: its SHIP, so every console on a bridge
    reads the same log rather than five diverging ones."""
def _tail_is_live (area, page):
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
    in, where the widget is real but not yet current."""
def gui_log_tail (count=None, background=None, tab='log', style=None):
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
        style (str, optional): extra style for the text area."""
def gui_page_for_client (client_id):
    """Return the active GUI page for a client.
    
    Args:
        client_id (int): The client to look up.
    
    Returns:
        Page | None: The client's current page, or ``None`` if unavailable.
    
    Example:
        page = gui_page_for_client(CLIENT_ID)
        if page is not None:
            ~~ page.dirty() ~~"""
def gui_panel_log (cid, left, top, width, height, tab='log'):
    """Info-panel tab body: the ship's log, newest at the bottom.
    
    Oldest-first with the newest at the BOTTOM, which is what the waterfall did and what
    a running log should do - the text area follows the tail unless the reader has
    scrolled back (see TextArea.follow_tail)."""
def gui_panel_log_mission (cid, left, top, width, height):
    """Info-panel tab: objective and quest beats."""
def gui_panel_log_ship (cid, left, top, width, height):
    """Info-panel tab: damage, systems, docking - Engineering's own feed."""
def gui_panel_log_tick (info_panel):
    """Redraw the log tab only when the log has actually grown.
    
    The panel's tick contract is 0 = done, 1 = stay, 2 = redraw. **Never 0 here**: 0
    means "this tab has nothing important" and sends the console back to its DEFAULT
    tab, which for a log the player deliberately opened would be a surface that closes
    itself.
    
    Comparing the newest ``seq`` rather than redrawing every tick keeps an idle log at
    zero render cost - this widget wraps every line on recalc, so a 1 Hz re-present of a
    500-line log would be real work for no change."""
def gui_text_area (props, style=None, markdown=True, line_styles=None):
    """Add a rich text area to the current GUI layout.
    
    Supports Markdown-style formatting and inline image references
    (``![](image://key)``). Use for multi-line or formatted text blocks.
    
    Args:
        props (str): Text content or Markdown string. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
        markdown (bool, optional): Parse the mini-markdown. Pass ``False`` to
            render lines VERBATIM - the right choice for source code, a MAST
            error dump or a raw log, where the markup rules actively corrupt the
            content: ``#`` starts a heading (so every MAST comment becomes one),
            a leading ``-`` is consumed as a bullet (``->END``), any ``[...]``
            is read as a link reference and replaces the line, and ``^`` becomes
            a newline. ``{var}`` interpolation is also skipped, since a brace in
            code is a brace. Defaults to True.
        line_styles (list, optional): One style key per line, applied in order -
            how you colorize text that is no longer being parsed. Pairs with
            ``markdown=False``. Defaults to None.
    
    Returns:
        TextArea: The layout item created.
    
    Example:
        gui_text_area("## Status\nAll systems nominal.")
        gui_text_area("![](image://logo?scale=0.5) Mission active")
        gui_text_area(source, markdown=False, line_styles=per_line_keys)"""
def log_entries_union (scopes, tab='log'):
    """Entries from several scopes merged into one stream, oldest first.
    
    A console shows its SHIP's log (the crew's shared record) PLUS anything addressed to
    that console alone - `comms_broadcast` takes either, so both have to arrive somewhere
    visible. Merged by `seq`, which is monotonic across every scope, so a console-only
    note lands in the right place in time rather than clumped at one end."""
def log_mark_seen (client_id, seq):
    """Record the newest seq a client has been shown. Returns True if it CHANGED."""
def log_newest_seq_union (scopes):
    """Newest seq across several scopes - the change check for a merged view."""
def log_notify (scope, text, color=None, category=None, severity=None):
    """Log a line AND make it visible now: refresh the strips, raise the tab if urgent.
    
    The one front door for "the mission has something to say". Logging alone is not
    enough - the ambient strip is built once and the info panel keeps whatever tab the
    crew left it on - so every producer needs the same three steps, and each one that
    hand-rolled them got a different subset.
    
    Never raises: a fault in the log must not take a docking message or a broadcast with
    it. That mattered during the changeover and still does, since this is now the only
    surface some of those messages have."""
def log_notify_all (scopes, text, color=None, category=None, severity=None):
    """log_notify for an audience. Duplicate scopes are collapsed, so a crew whose
    consoles all resolve to one ship gets ONE entry, not one per console."""
def log_raise (scope, tab='log'):
    """Bring a log tab to the front on every console that would show this entry.
    
    The same move `gui_info_panel_send_message(notify=True)` makes for a card that must
    be seen now - reused rather than reinvented, so an urgent log entry behaves like every
    other interrupt on that panel.
    
    `scope` is a ship (raise on all its consoles) or a client (just that one)."""
def log_render (entries):
    """``entries`` -> ``(text, line_styles)`` for ``gui_text_area``.
    
    PURE: no GUI, no engine, no globals. This is the whole point of the split - what a
    player ends up reading can be asserted in a unit test.
    
    One entry is one line, so a style slot maps to an entry by index. An entry's own text
    is flattened for that reason: a log line that silently became three would break the
    mapping and the "N new" count with it."""
def log_tail_refresh (scope=None):
    """Push new traffic into every console's ambient strip.
    
    A push, like log_raise: the strip is built ONCE, when the console lays itself out, and
    the console is not otherwise repainting - so without this it keeps whatever the log
    held at that instant, which reads as the feature not working at all.
    
    `scope` is accepted for symmetry with log_raise but not used to filter: every strip
    recomputes its OWN union (its ship plus its client), which is the correct filter
    already, and there are only ever a handful of them. Both the text and the styles are
    replaced - `line_styles` is fixed at construction, so updating the value alone would
    leave the previous entry's color on the new line."""
def log_tail_render (entries):
    """log_render for the ambient strip: never returns empty text.
    
    The strip is a fixed slot in the console layout, so it has to draw SOMETHING - an
    empty text area is invisible and the console just looks broken."""
