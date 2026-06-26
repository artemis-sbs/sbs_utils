import re
from ..helpers import FrameContext
#from .gui import text_sanitize


def maps_get_list():
    """Return all ``@map`` labels defined in the current page's story.

    If only an ``__overview__`` label exists, it is returned as a single-item
    list. If no map labels are found at all, returns a placeholder list with a
    ``"No maps found"`` entry.

    Returns:
        list: ``@map`` Label objects, or a fallback list if none are defined.
    """
    ret = []
    page = FrameContext.page
    if page is None:
        return []
    #
    # Walk all labels looking for map Labels
    #
    init_label = None
    all_labels = page.story.labels
    for l in all_labels:
        if not l.startswith("map/"):
            continue
        m = all_labels[l]
        if m.path == "__overview__":
            init_label = m
        else:
            ret.append(m)
#                {"name": m.display_name, "description": text_sanitize(m.desc), "label": m},
#            )
    #
    # If there is just the one i.e. the init return that
    #
    if len(ret)==0 and init_label is not None:
        return [init_label]
    elif len(ret)==0:
        return  [
            {"name": "No maps found", "description": "No maps were found when searching all mast/python labels."},
        ]
    return ret


def maps_get_init():
    """Return the ``__overview__`` map label from the current MAST story, or ``None``.

    Returns:
        Label | None: The overview map label, or ``None`` if not defined.
    """
    mast = FrameContext.mast
    if mast is None:
        return []
    #
    # Walk all labels looking for map Labels
    #
    all_labels = mast.labels
    init_label = None
    for l in all_labels:
        if not l.startswith("map/"):
            continue
        if all_labels[l].path == "__overview__":
            init_label = all_labels[l]
            break

    return init_label


def map_get_properties(map):
    """Return the ``Properties`` inventory value of a map label.

    Checks ``"Properties"`` first, then ``"properties"`` as a fallback.

    Args:
        map (Label): The map label object.

    Returns:
        any: The properties value, or ``None`` if not set.
    """
    # Try Properties and properties
    return map.get_inventory_value("Properties", map.get_inventory_value("properties"))


def _map_property_vars(map):
    """Var names bound in a map's Properties metadata, in declaration order.

    Walks the (possibly grouped, e.g. Main/Map) Properties dict and extracts
    every ``var="..."`` / ``var= "..."`` binding from the widget strings.
    """
    found = []
    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            for m in re.finditer(r'var\s*=\s*"([^"]+)"', node):
                name = m.group(1)
                if name not in found:
                    found.append(name)
    walk(map_get_properties(map))
    return found


def game_code_vars(map):
    """Return the var names that make up a map's game code, in order.

    By default this is *every* property var the map exposes, so a saved code
    reproduces the full setup; a person can delete any entries they don't care
    about from the code string. A map can also pin the set explicitly with a
    ``GameCode`` metadata list (``GameCode: [PLAYER_COUNT, DIFFICULTY, ...]``).

    Args:
        map (Label): The map label object.

    Returns:
        list[str]: Ordered var names included in the code.
    """
    declared = map.get_inventory_value("GameCode", map.get_inventory_value("game_code"))
    if declared:
        return [str(v) for v in declared]
    return _map_property_vars(map)


def _coerce_like(text, current):
    """Convert a code's string token back to the type of the live variable.

    The property shared vars are initialised with their real types before the
    code is applied (ints for sliders, strings for dropdowns / minute inputs),
    so matching the current type round-trips faithfully. Falls back to an
    int->float->str guess when the variable doesn't exist yet.
    """
    text = text.strip()
    if isinstance(current, bool):
        return text.lower() in ("1", "true", "yes", "on")
    if isinstance(current, int):
        try:
            return int(text)
        except ValueError:
            return text
    if isinstance(current, float):
        try:
            return float(text)
        except ValueError:
            return text
    if current is None:
        for cast in (int, float):
            try:
                return cast(text)
            except ValueError:
                pass
    return text


def game_code_encode(map):
    """Build a shareable, human-readable game code for a map.

    Format: ``"<map_path>;VAR=value;VAR=value;..."`` where the vars are the
    map's :func:`game_code_vars` read from the shared scope. Reproduces the
    map plus its seed and key option values so another host can recreate the
    same game.

    Args:
        map (Label): The map label whose current option values to encode.

    Returns:
        str: The game code, or ``""`` if ``map`` is None.
    """
    from .execution import get_shared_variable
    if map is None:
        return ""
    parts = [getattr(map, "path", "")]
    for name in game_code_vars(map):
        val = get_shared_variable(name)
        if val is None:
            continue
        parts.append(f"{name}={val}")
    return ";".join(parts)


def game_code_decode(code):
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
        names a map not present in the current story.
    """
    from .execution import get_shared_variable, set_shared_variable
    if not code:
        return None
    parts = [p.strip() for p in code.split(";") if p.strip()]
    if not parts:
        return None
    map_path = parts[0]
    target = None
    for m in maps_get_list():
        if getattr(m, "path", None) == map_path:
            target = m
            break
    if target is None:
        return None
    for pair in parts[1:]:
        if "=" not in pair:
            continue
        name, _, value = pair.partition("=")
        name = name.strip()
        set_shared_variable(name, _coerce_like(value, get_shared_variable(name)))
    return target


# Abbreviations for building short preset labels from a code.
_GAME_CODE_LABEL_ABBR = {
    "DIFFICULTY": "D", "PLAYER_COUNT": "P", "GAME_TIME_LIMIT": "T",
    "seed_value": "seed", "FRIENDLY_SELECT": "F", "WAR_TIME_DELAY": "war",
}


def game_code_label(code):
    """A short, human-readable label for a game code (for preset menus).

    e.g. ``"siege;PLAYER_COUNT=2;DIFFICULTY=5;seed_value=4242"`` -> ``"P2 D5 seed4242"``.
    Falls back to the raw code if it has no value pairs.
    """
    if not code:
        return ""
    parts = code.split(";")
    bits = []
    for pair in parts[1:]:
        if "=" not in pair:
            continue
        name, _, val = pair.partition("=")
        bits.append(f"{_GAME_CODE_LABEL_ABBR.get(name.strip(), name.strip())}{val.strip()}")
    return " ".join(bits) if bits else code


def _game_code_presets_file(filename):
    from ..fs import get_mission_dir_filename
    return filename if filename is not None else get_mission_dir_filename("game_code_presets.yaml")


def game_code_presets_load(filename=None):
    """Load the saved game-code presets, a dict of ``{map_path: [code, ...]}``.

    Returns an empty dict if the file is missing or malformed. Presets are kept
    separated by map so each map only shows its own.
    """
    from ..fs import load_yaml_data
    data = load_yaml_data(_game_code_presets_file(filename))
    return data if isinstance(data, dict) else {}


def game_code_presets_for_map(map_path, filename=None):
    """Return the list of saved game codes for one map (newest last)."""
    codes = game_code_presets_load(filename).get(map_path)
    return list(codes) if isinstance(codes, list) else []


def game_code_presets_save_code(code, filename=None):
    """Save a game code as a preset under its map, de-duplicating.

    The map is taken from the code's first token, so presets land in the right
    per-map bucket. Returns the code saved, or ``None`` if ``code`` is empty.
    """
    from ..fs import save_yaml_data
    if not code:
        return None
    map_path = code.split(";")[0]
    data = game_code_presets_load(filename)
    codes = data.get(map_path)
    if not isinstance(codes, list):
        codes = []
    if code not in codes:
        codes.append(code)
    data[map_path] = codes
    save_yaml_data(_game_code_presets_file(filename), data)
    return code




