from sbs_utils.helpers import FrameContext
def _coerce_like (text, current):
    """Convert a code's string token back to the type of the live variable.
    
    The property shared vars are initialised with their real types before the
    code is applied (ints for sliders, strings for dropdowns / minute inputs),
    so matching the current type round-trips faithfully. Falls back to an
    int->float->str guess when the variable doesn't exist yet."""
def _game_code_presets_file (filename):
    ...
def _loadout_clean (text):
    """Strip the loadout + game-code separators from a free-text field."""
def _map_property_vars (map):
    """Var names bound in a map's Properties metadata, in declaration order.
    
    Walks the (possibly grouped, e.g. Main/Map) Properties dict and extracts
    every ``var="..."`` / ``var= "..."`` binding from the widget strings."""
def _preset_normalize (entry, position):
    """Coerce a stored preset entry to ``{"name": str, "code": str}``.
    
    New entries are already that dict. A legacy bare-string entry (just the
    code) gets a generated ``"Preset N"`` name from its 1-based ``position``."""
def game_code_decode (code):
    """Apply a game code: set its shared variables and return the matching map.
    
    Resolves the map by path first; if no current map matches, nothing is
    changed and ``None`` is returned (so a code from a different mission is a
    safe no-op). Otherwise each ``VAR=value`` is written to the shared scope,
    coerced to the live variable's type, and the map Label is returned. The
    caller starts the map (e.g. ``task_schedule(map)``).
    
    Args:
        code (str): A code previously produced by :func:`game_code_encode`.
    
    Returns:
        Label | None: The map to start, or ``None`` if the code is empty or
        names a map not present in the current story."""
def game_code_encode (map):
    """Build a shareable, human-readable game code for a map.
    
    Format: ``"<map_path>;VAR=value;VAR=value;..."`` where the vars are the
    map's :func:`game_code_vars` read from the shared scope. Reproduces the
    map plus its seed and key option values so another host can recreate the
    same game.
    
    Args:
        map (Label): The map label whose current option values to encode.
    
    Returns:
        str: The game code, or ``""`` if ``map`` is None."""
def game_code_label (code):
    """A short, human-readable label for a game code (for preset menus).
    
    e.g. ``"siege;PLAYER_COUNT=2;DIFFICULTY=5;seed_value=4242"`` -> ``"P2 D5 seed4242"``.
    Falls back to the raw code if it has no value pairs."""
def game_code_presets_for_map (map_path, filename=None):
    """Return one map's saved presets as ``[{"name", "code"}, ...]`` (newest last)."""
def game_code_presets_load (filename=None):
    """Load the saved game-code presets, a dict of ``{map_path: [entry, ...]}``.
    
    Each entry is a ``{"name": str, "code": str}`` dict. Legacy files stored a
    bare code string per entry; those still load (see :func:`_preset_normalize`).
    Returns an empty dict if the file is missing or malformed. Presets are kept
    separated by map so each map only shows its own."""
def game_code_presets_save_code (code, name=None, filename=None):
    """Save a game code as a named preset under its map, de-duplicating on code.
    
    The map is taken from the code's first token, so presets land in the right
    per-map bucket. ``name`` defaults to ``"Preset N"`` (N = the next slot for
    that map). Re-saving an identical code is a no-op (keeps the first name).
    Returns the code saved, or ``None`` if ``code`` is empty."""
def game_code_vars (map):
    """Return the var names that make up a map's game code, in order.
    
    By default this is *every* property var the map exposes, so a saved code
    reproduces the full setup; a person can delete any entries they don't care
    about from the code string. A map can also pin the set explicitly with a
    ``GameCode`` metadata list (``GameCode: [PLAYER_COUNT, DIFFICULTY, ...]``).
    
    Args:
        map (Label): The map label object.
    
    Returns:
        list[str]: Ordered var names included in the code."""
def map_apply_defaults (map):
    """Apply a map's ``Defaults:`` metadata as SET-IF-ABSENT shared variables.
    
    For each ``VAR: value`` in the map's ``Defaults`` block, set the shared variable to
    ``value`` ONLY if it is not already set - so a value seeded by ``settings.yaml``, the
    story, or a loaded game code always wins (the same semantics as ``default shared``). This
    lets a map give its own Properties controls a starting value without promoting a map-local
    setting (e.g. a ``JOBS_SELECT`` only this map uses) to global settings or scattering
    ``default`` through the map body.
    
    The map's Properties panel renders (and binds its controls to SHARED scope) BEFORE the map
    body runs, so this must be applied at BOTH moments: when the panel is presented, AND again
    whenever the map is started as a task (AUTO_START and a headless ``--map`` runner start the
    map task without ever presenting the panel). It is idempotent - a map with no ``Defaults``
    is a no-op, and an already-set var is left untouched - so calling it at both points is safe.
    
    Args:
        map (Label): The map label object (``None`` is a no-op)."""
def map_get_defaults (map):
    """Return the ``Defaults`` metadata dict of a map label (fallback ``defaults``).
    
    A sibling of ``Properties`` in a map's ``metadata:`` block: a flat ``{VAR: value}`` map of
    starting values for the variables the map's Properties controls bind to (and any other var
    the map wants defaulted). Read the same way as ``Properties`` / ``GameCode``.
    
    Args:
        map (Label): The map label object.
    
    Returns:
        dict | None: The defaults dict, or ``None`` if the map declares none."""
def map_get_properties (map):
    """Return the ``Properties`` inventory value of a map label.
    
    Checks ``"Properties"`` first, then ``"properties"`` as a fallback.
    
    Args:
        map (Label): The map label object.
    
    Returns:
        any: The properties value, or ``None`` if not set."""
def maps_find (spec):
    """Find one `@map` label from a loose, human-typed spec.
    
    Built for launch arguments - `map=test_shipdata_probe` on the engine command line, or
    `--map 0` under cosmos_dev - where the value is typed by a person or pasted from a
    script and should not have to be exact.
    
    Accepts, in order of preference so an exact hit always wins over a fuzzy one:
    
    * an integer, or a string of digits - an index into the map list
    * the label `path`, case-insensitively
    * the `display_name`, case-insensitively
    * a unique case-insensitive substring of either; AMBIGUOUS matches return None
      rather than picking one, because silently starting the wrong map is worse than
      starting none and saying so.
    
    Returns:
        Label | None: the map, or None if nothing matched or the spec was ambiguous."""
def maps_get_init ():
    """Return the ``__overview__`` map label from the current MAST story, or ``None``.
    
    Returns:
        Label | None: The overview map label, or ``None`` if not defined."""
def maps_get_list ():
    """Return all ``@map`` labels defined in the current page's story.
    
    If only an ``__overview__`` label exists, it is returned as a single-item
    list. If no map labels are found at all, returns a placeholder list with a
    ``"No maps found"`` entry.
    
    Returns:
        list: ``@map`` Label objects, or a fallback list if none are defined."""
def player_loadout_active ():
    """Decode the live ``SHIP_LOADOUT`` shared var into a slot list (``[]`` if unset)."""
def player_loadout_capture (ships):
    """Capture ``ships`` into the shared ``SHIP_LOADOUT`` var; return the token.
    
    Call right before encoding a game code so the code carries the current
    crew's hulls + names."""
def player_loadout_decode (token):
    """Inverse of :func:`player_loadout_encode`. Empty/None -> ``[]``."""
def player_loadout_encode (slots):
    """Pack ``[{"name","hull"}, ...]`` into one game-code-safe token (``""`` for none)."""
def player_loadout_from_ships (ships):
    """Build a loadout token from ship objects, reading ``.name`` and ``.art_id``.
    
    ``ships`` is sorted by id first so the slot order is stable and matches the
    rehydrate side (spawn_players walks the player ships in id order too)."""
