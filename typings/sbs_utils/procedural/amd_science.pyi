def _scan_body_lines (desc):
    """Body prose -> list of scan variants. Each non-empty, non-comment line is a variant; a
    leading ``%`` (the random-variant marker, as in dialogue) is stripped. One line -> one
    fixed variant; several -> pick-one-at-random at scan time (science_scan_tab)."""
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
def amd_scan_data (text):
    """Parse one scan fence into a data dict (``Scan of:`` -> ``scan_of``, ``Tab:`` -> ``tab``,
    via the default value coercion). Use as the ``data_parser`` for a scan-only .amd file; a
    consolidated mission file uses ``amd_mission_data`` instead. The scan TEXT is read from the
    fence body by ``science_define_scan_amd``, not from here."""
def science_define_scan (role, tabs):
    """Register declarative science-scan content for a ROLE.
    
    Args:
        role (str): The role an object must hold to get this scan content.
        tabs (dict | str): ``{tab_name: text}`` (e.g. ``{"scan": "...", "bio": "..."}``);
            a bare string is shorthand for ``{"scan": string}``. Standard tab names:
            ``scan``, ``status``, ``intel``, ``mat``, ``bio``. Text may contain ``{key}``
            placeholders, filled per object from inventory. Merges with any tabs already
            registered for the role."""
def science_define_scan_amd (doc):
    """Register per-role scan content from a parsed AMD doc (``document_get_amd_file`` with
    ``data_parser=amd_scan_data`` or a mission's ``amd_mission_data``). Per heading: a
    ``Scan of: <role>`` fence (+ optional ``Tab:``, default ``scan``); the BODY's ``%`` lines
    are that tab's random variants (a single line -> one fixed variant). Multiple headings for
    the same role compose - ``science_define_scan`` merges their tabs."""
