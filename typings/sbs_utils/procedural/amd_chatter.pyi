def _chatter_body_lines (desc):
    """Body prose -> list of chatter lines. Each non-empty, non-comment line is one pool line; a
    leading ``%`` (the random-variant marker, as in dialogue) is stripped. One line -> one fixed
    bark; several -> pick-one-at-random per call (chatter_line)."""
def _fill (line, fields):
    """Fill ``{field}`` placeholders from ``fields``; an unknown field is left LITERAL (so a stray
    ``{x}`` never crashes and never silently vanishes)."""
def amd_chatter_data (text):
    """Parse one chatter fence into a data dict (default coercion - all fields are strings). Use as
    the ``data_parser`` for a chatter-only .amd; a consolidated mission file uses ``amd_mission_data``
    and its chatter headings' bodies fall through the same way. Most chatter needs no fence at all -
    the pool is the heading BODY, not fence values."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000011CF6E5F4C0>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def chatter_line (scenes, key, **fields):
    """A line for an event key: a random candidate from ``scenes[key]``, with ``{field}``
    placeholders filled from the keyword fields (missing fields are left literal, never a crash).
    Returns ``""`` if the key/pool is missing (or ``scenes`` is None)."""
def chatter_scenes (section):
    """``{key: [lines]}`` pools from a section node's children (empty dict if None). Each
    ``# [Display](key)`` heading's BODY lines become that key's pool; a heading with an empty body
    is skipped. ``section`` is the parsed AMD section (as from ``document_get_amd_file`` /
    ``universe_section``)."""
