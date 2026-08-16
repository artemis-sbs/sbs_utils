def amd_callout_render (text):
    """`text` -> `(clean_text, line_styles)` ready for `gui_text_area`.
    
    The `>` markers come off (they are markup, not words) and each line of a block
    gets that kind's style, with the title line a size larger. Lines outside any
    block get `None`, which `line_style_for` already treats as "style it normally",
    so a document with no callouts renders exactly as it does today and passing the
    styles through is always safe."""
def log_add (scope, text, color=None, category='log', severity=''):
    """Append one entry to a scope's log and return it.
    
    ``scope`` is normally a player-ship id: every console on that ship shares one log,
    which is what makes it the SHIP's log rather than five diverging ones. A client id
    may be used for a console-specific notice.
    
    The ``seq`` is monotonic across the whole mission, NOT an index into the list. That
    is what lets a reader who has scrolled back keep a stable "N new below" count while
    the ring drops entries off the top underneath them."""
def log_clear ():
    """Drop every scope's log (fresh mission / in-process recompile)."""
def log_entries (scope, tab='log'):
    """Entries for a scope, filtered to a tab, oldest first.
    
    The Log tab is not a category - it is EVERYTHING. Subset tabs match their category,
    so an entry nobody tagged appears in Log and nowhere else."""
def log_entries_union (scopes, tab='log'):
    """Entries from several scopes merged into one stream, oldest first.
    
    A console shows its SHIP's log (the crew's shared record) PLUS anything addressed to
    that console alone - `comms_broadcast` takes either, so both have to arrive somewhere
    visible. Merged by `seq`, which is monotonic across every scope, so a console-only
    note lands in the right place in time rather than clumped at one end."""
def log_mark_seen (client_id, seq):
    """Record the newest seq a client has been shown. Returns True if it CHANGED."""
def log_newest_seq (scope):
    """The newest entry's ``seq`` for a scope, or 0 when it has no log yet.
    
    Cheap change detection: a panel compares this against what it last drew rather than
    re-rendering on a timer."""
def log_newest_seq_union (scopes):
    """Newest seq across several scopes - the change check for a merged view."""
def log_render (entries):
    """``entries`` -> ``(text, line_styles)`` for ``gui_text_area``.
    
    PURE: no GUI, no engine, no globals. This is the whole point of the split - what a
    player ends up reading can be asserted in a unit test.
    
    One entry is one line, so a style slot maps to an entry by index. An entry's own text
    is flattened for that reason: a log line that silently became three would break the
    mapping and the "N new" count with it."""
def log_size ():
    """Total entries held across all scopes - the reset-ledger probe."""
def log_tail_render (entries):
    """log_render for the ambient strip: never returns empty text.
    
    The strip is a fixed slot in the console layout, so it has to draw SOMETHING - an
    empty text area is invisible and the console just looks broken."""
def log_unseen (client_id, scope):
    """How many entries have arrived for `scope` since this client last saw it.
    
    Counts by SEQ, not by index, so it stays right when the ring has dropped entries off
    the top underneath a reader who scrolled back."""
