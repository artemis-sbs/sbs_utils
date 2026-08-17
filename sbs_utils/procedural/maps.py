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


def map_get_defaults(map):
    """Return the ``Defaults`` metadata dict of a map label (fallback ``defaults``).

    A sibling of ``Properties`` in a map's ``metadata:`` block: a flat ``{VAR: value}`` map of
    starting values for the variables the map's Properties controls bind to (and any other var
    the map wants defaulted). Read the same way as ``Properties`` / ``GameCode``.

    Args:
        map (Label): The map label object.

    Returns:
        dict | None: The defaults dict, or ``None`` if the map declares none.
    """
    return map.get_inventory_value("Defaults", map.get_inventory_value("defaults"))


_DEFAULT_MISSING = object()


def map_apply_defaults(map):
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
        map (Label): The map label object (``None`` is a no-op).
    """
    if map is None:
        return
    defaults = map_get_defaults(map)
    if not isinstance(defaults, dict):
        return
    from .execution import get_shared_variable, set_shared_variable
    for name, value in defaults.items():
        if get_shared_variable(name, _DEFAULT_MISSING) is _DEFAULT_MISSING:
            set_shared_variable(str(name), value)


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
    """Load the saved game-code presets, a dict of ``{map_path: [entry, ...]}``.

    Each entry is a ``{"name": str, "code": str}`` dict. Legacy files stored a
    bare code string per entry; those still load (see :func:`_preset_normalize`).
    Returns an empty dict if the file is missing or malformed. Presets are kept
    separated by map so each map only shows its own.
    """
    from ..fs import load_yaml_data
    data = load_yaml_data(_game_code_presets_file(filename))
    return data if isinstance(data, dict) else {}


def _preset_normalize(entry, position):
    """Coerce a stored preset entry to ``{"name": str, "code": str}``.

    New entries are already that dict. A legacy bare-string entry (just the
    code) gets a generated ``"Preset N"`` name from its 1-based ``position``.
    """
    if isinstance(entry, dict):
        code = entry.get("code", "")
        name = entry.get("name") or f"Preset {position}"
        return {"name": name, "code": code}
    return {"name": f"Preset {position}", "code": str(entry)}


def game_code_presets_for_map(map_path, filename=None):
    """Return one map's saved presets as ``[{"name", "code"}, ...]`` (newest last)."""
    entries = game_code_presets_load(filename).get(map_path)
    if not isinstance(entries, list):
        return []
    return [_preset_normalize(e, i + 1) for i, e in enumerate(entries)]


# --- player-ship loadout, foldable into a game code -------------------------
# "Start the next crew like the last one": a loadout is a list of per-slot
# {"name", "hull"} dicts packed into ONE game-code value (the SHIP_LOADOUT var),
# so it rides the same shareable code / preset as the map options. It must avoid
# the code's own separators (';' between pairs, '=' after a key): slots join with
# '|', the two fields within a slot with '~'.

def _loadout_clean(text):
    """Strip the loadout + game-code separators from a free-text field."""
    for ch in ("|", "~", ";", "="):
        text = text.replace(ch, " ")
    return text.strip()


def player_loadout_encode(slots):
    """Pack ``[{"name","hull"}, ...]`` into one game-code-safe token (``""`` for none)."""
    parts = []
    for s in slots:
        name = _loadout_clean(str(s.get("name", "")))
        hull = _loadout_clean(str(s.get("hull", "")))
        parts.append(f"{name}~{hull}")
    return "|".join(parts)


def player_loadout_decode(token):
    """Inverse of :func:`player_loadout_encode`. Empty/None -> ``[]``."""
    if not token:
        return []
    slots = []
    for part in str(token).split("|"):
        name, _, hull = part.partition("~")
        slots.append({"name": name, "hull": hull})
    return slots


def player_loadout_from_ships(ships):
    """Build a loadout token from ship objects, reading ``.name`` and ``.art_id``.

    ``ships`` is sorted by id first so the slot order is stable and matches the
    rehydrate side (spawn_players walks the player ships in id order too).
    """
    ordered = sorted(ships, key=lambda s: getattr(s, "id", 0))
    return player_loadout_encode(
        [{"name": getattr(s, "name", ""), "hull": getattr(s, "art_id", "")} for s in ordered])


def player_loadout_capture(ships):
    """Capture ``ships`` into the shared ``SHIP_LOADOUT`` var; return the token.

    Call right before encoding a game code so the code carries the current
    crew's hulls + names.
    """
    from .execution import set_shared_variable
    token = player_loadout_from_ships(ships)
    set_shared_variable("SHIP_LOADOUT", token)
    return token


def player_loadout_active():
    """Decode the live ``SHIP_LOADOUT`` shared var into a slot list (``[]`` if unset)."""
    from .execution import get_shared_variable
    return player_loadout_decode(get_shared_variable("SHIP_LOADOUT"))


def game_code_presets_save_code(code, name=None, filename=None):
    """Save a game code as a named preset under its map, de-duplicating on code.

    The map is taken from the code's first token, so presets land in the right
    per-map bucket. ``name`` defaults to ``"Preset N"`` (N = the next slot for
    that map). Re-saving an identical code is a no-op (keeps the first name).
    Returns the code saved, or ``None`` if ``code`` is empty.
    """
    from ..fs import save_yaml_data
    if not code:
        return None
    map_path = code.split(";")[0]
    data = game_code_presets_load(filename)
    entries = data.get(map_path)
    if not isinstance(entries, list):
        entries = []
    for e in entries:
        e_code = e.get("code", "") if isinstance(e, dict) else str(e)
        if e_code == code:
            return code
    if not name:
        name = f"Preset {len(entries) + 1}"
    # Commas would split the preset dropdown's comma-joined label list.
    name = str(name).replace(",", " ").strip() or f"Preset {len(entries) + 1}"
    entries.append({"name": name, "code": code})
    data[map_path] = entries
    save_yaml_data(_game_code_presets_file(filename), data)
    return code






def maps_find(spec):
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
        Label | None: the map, or None if nothing matched or the spec was ambiguous.
    """
    return label_find_by_spec(maps_get_list(), spec)


def label_find_by_spec(labels, spec):
    """Find one label from a loose, human-typed spec - the rule `maps_find` documents,
    factored out so every other "name a label on a command line or in a dropdown" lookup
    resolves IDENTICALLY.

    Shared with `media_find` (skybox and music), which is why it lives here rather than
    inside `maps_find`: two copies of a fuzzy matcher drift, and the day they disagree is
    the day `map=siege` and `MUSIC_SELECT=siege` mean different things.

    Args:
        labels (list): anything with `.path` and (optionally) `.display_name`.
        spec: an index, a path, a display name, or a unique substring of either.

    Returns:
        The label, or None if nothing matched or the spec was AMBIGUOUS.
    """
    labels = [m for m in (labels or []) if hasattr(m, "path")]
    if not labels or spec is None:
        return None

    if isinstance(spec, bool):          # bool is an int; a True index is nonsense
        return None
    if isinstance(spec, int):
        return labels[spec] if 0 <= spec < len(labels) else None

    want = str(spec).strip()
    if not want:
        return None
    if want.isdigit():
        idx = int(want)
        return labels[idx] if 0 <= idx < len(labels) else None

    lowered = want.lower()

    def _name(m):
        return str(getattr(m, "display_name", "") or "")

    for m in labels:
        if str(getattr(m, "path", "")).lower() == lowered:
            return m
    for m in labels:
        if _name(m).lower() == lowered:
            return m

    partial = [m for m in labels
               if lowered in str(getattr(m, "path", "")).lower()
               or lowered in _name(m).lower()]
    return partial[0] if len(partial) == 1 else None
