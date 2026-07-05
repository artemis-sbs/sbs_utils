from sbs_utils.helpers import FrameContext
def _coerce_like (text, current):
    """Convert a code's string token back to the type of the live variable.
    
    The property shared vars are initialised with their real types before the
    code is applied (ints for sliders, strings for dropdowns / minute inputs),
    so matching the current type round-trips faithfully. Falls back to an
    int->float->str guess when the variable doesn't exist yet."""
def _game_code_presets_file (filename):
    ...
def _map_property_vars (map):
    """Var names bound in a map's Properties metadata, in declaration order.
    
    Walks the (possibly grouped, e.g. Main/Map) Properties dict and extracts
    every ``var="..."`` / ``var= "..."`` binding from the widget strings."""
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
    """Return the list of saved game codes for one map (newest last)."""
def game_code_presets_load (filename=None):
    """Load the saved game-code presets, a dict of ``{map_path: [code, ...]}``.
    
    Returns an empty dict if the file is missing or malformed. Presets are kept
    separated by map so each map only shows its own."""
def game_code_presets_save_code (code, filename=None):
    """Save a game code as a preset under its map, de-duplicating.
    
    The map is taken from the code's first token, so presets land in the right
    per-map bucket. Returns the code saved, or ``None`` if ``code`` is empty."""
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
def map_get_properties (map):
    """Return the ``Properties`` inventory value of a map label.
    
    Checks ``"Properties"`` first, then ``"properties"`` as a fallback.
    
    Args:
        map (Label): The map label object.
    
    Returns:
        any: The properties value, or ``None`` if not set."""
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
