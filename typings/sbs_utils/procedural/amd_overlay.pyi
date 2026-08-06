def _num (v):
    """Coerce a fence string to int/float where possible (Seconds: 4 -> 4)."""
def _show_transient (slot, kind, to, seconds, content, consoles=None):
    """Show an overlay and, if ``seconds`` is set, auto-clear it after that long.
    The dismiss is generation-guarded per target page, so re-showing the slot before
    the timer fires supersedes it instead of clearing the newer content."""
def amd_overlays (section):
    """Load + register the overlay records in ``section``; returns the ``{key: record}``
    map (also merged into the module registry for ``overlay_amd``). Empty when None."""
def amd_records (section):
    """A section's children as GENERIC records - the raw AMD atom, before any domain lens.
    
    Every AMD heading (``# [Display](key)`` + an optional ``---`` fence + body prose) carries
    exactly four things; this returns one ``MastDataObject`` per child exposing them verbatim:
    
        key      : the ``(slug)``            -> ``rec.get("key")``
        display  : the ``[Display]`` text    -> ``rec.get("display")``
        body     : the prose under it        -> ``rec.get("body")`` (stripped)
        data     : the ``---`` fence dict    -> ``rec.get("data")`` (keys lower-cased, ``{}`` if none)
    
    The domain loaders (amd_lifeforms / amd_items / amd_chatter) are each a projection of this
    same node; ``amd_records`` is that substrate exposed directly, for content that IS just a
    labelled line of prose and needs no domain shape. Canonical example: a mystery clue authored as
    ``# [Container Name](slug)`` + the clue text as body -> ``{display: container, body: clue}``.
    Returns ``[]`` when ``section`` is None."""
def overlay_amd (key, to=None, fields=None, consoles=None):
    """Fire a declared overlay by key. ``fields`` (a dict) merge over the record's
    fields; a ``seconds`` field auto-dismisses. ``to`` accepts a console, ship, side
    or set (see ``consoles_of``); ``consoles`` narrows by console role. Returns the
    record, or None for an unknown key."""
