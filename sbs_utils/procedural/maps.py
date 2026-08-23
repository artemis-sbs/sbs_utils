import re
from ..helpers import FrameContext
#from .gui import text_sanitize


def _map_is_shown(m):
    """Evaluate a map's ``if`` condition. Unconditional maps, and any map we cannot
    evaluate, are SHOWN.

    ``@map/x "X" if COND`` was never evaluated by ``maps_get_list``, so a map hidden by
    its own condition was offered anyway. ``CardLabelBase.test`` answers this, but it
    needs a task, and there is not always one: the headless runner polls this from its
    own loop with no MAST task in context. Missing task therefore means SHOW - hiding
    every map there would stop ``--map`` working at all, which is a far worse failure
    than listing one map too many.
    """
    test = getattr(m, "test", None)
    if test is None:
        return True
    task = FrameContext.task
    if task is None:
        return True
    try:
        return bool(test(task))
    except Exception:
        # test() already reads a raising condition as "not shown"; anything that gets
        # past it is a bug in the picker, not in the mission - do not hide the map.
        return True


def maps_get_list(include_hidden=False):
    """Return the ``@map`` labels defined in the current page's story.

    If only an ``__overview__`` label exists, it is returned as a single-item
    list. If no map labels are found at all, returns a placeholder list with a
    ``"No maps found"`` entry.

    Args:
        include_hidden (bool): When True, return conditional maps whose ``if`` is
            currently false as well. Callers that are RESOLVING A KNOWN MAP rather than
            offering a menu want this - ``game_code_decode`` looks a map up by path, and
            a saved code should not stop resolving because a condition happens to be
            false right now.

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
        elif include_hidden or _map_is_shown(m):
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


# The player-ship loadout rides a code only when it is being SAVED, never when it is
# being shared. The two uses pull opposite ways: a saved setup should bring the crew's
# ships back, while a code you paste to another host has no business carrying your ship
# names - they are not part of the match, and they make the code several times longer.
#
# It is not a property var either (no map puts it on the options panel), so the property
# walk never finds it on its own. `with_loadout` is what the save paths pass.
_GAME_CODE_SAVE_ONLY = ("SHIP_LOADOUT",)


def game_code_vars(map, with_loadout=False):
    """Return the var names that make up a map's game code, in order.

    By default this is *every* property var the map exposes - the options panel, exactly
    as a person set it. A map can pin the set explicitly with a ``GameCode`` metadata list
    (``GameCode: [PLAYER_COUNT, DIFFICULTY, ...]``), which is then used verbatim.

    Args:
        map (Label): The map label object.
        with_loadout (bool): also carry ``SHIP_LOADOUT`` - the crew's ship names and
            hulls. True when SAVING a setup (a preset, or the last-used slot), False when
            producing a code to share. Appended even to an explicit ``GameCode`` list, so
            a map that pins its options still saves its ships.

    Returns:
        list[str]: Ordered var names included in the code.
    """
    declared = map.get_inventory_value("GameCode", map.get_inventory_value("game_code"))
    names = [str(v) for v in declared] if declared else _map_property_vars(map)
    if with_loadout:
        names = names + [n for n in _GAME_CODE_SAVE_ONLY if n not in names]
    return names


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


def game_code_encode(map, with_loadout=False):
    """Build a shareable, human-readable game code for a map.

    Format: ``"<map_path>;VAR=value;VAR=value;..."`` where the vars are the
    map's :func:`game_code_vars` read from the shared scope. Reproduces the
    map plus its seed and key option values so another host can recreate the
    same game.

    Args:
        map (Label): The map label whose current option values to encode.
        with_loadout (bool): also carry the crew's ship names and hulls. Pass True when
            SAVING (a named preset, the last-used slot); leave False for a code meant to
            be shared, which should not carry another crew's ship names.

    Returns:
        str: The game code, or ``""`` if ``map`` is None.
    """
    from .execution import get_shared_variable
    if map is None:
        return ""
    parts = [getattr(map, "path", "")]
    for name in game_code_vars(map, with_loadout):
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
    # include_hidden: this is a LOOKUP by path, not a menu - see maps_get_list.
    for m in maps_get_list(include_hidden=True):
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

    ``SHIP_LOADOUT`` is summarized as a ship count rather than spelled out: its value is
    every ship's name and hull joined together, which is longer than the rest of the label
    put together and unreadable in a dropdown.
    """
    if not code:
        return ""
    parts = code.split(";")
    bits = []
    for pair in parts[1:]:
        if "=" not in pair:
            continue
        name, _, val = pair.partition("=")
        name, val = name.strip(), val.strip()
        if name == "SHIP_LOADOUT":
            slots = player_loadout_decode(val)
            if slots:
                bits.append(f"ships{len(slots)}")
            continue
        bits.append(f"{_GAME_CODE_LABEL_ABBR.get(name, name)}{val}")
    return " ".join(bits) if bits else code


def _game_code_presets_file(filename):
    """Where this mission's saved setups live: one file per mission under common_data.

    NOT the mission folder. A preset is written by the game, not shipped by the author, so
    putting it in the mission meant untracked state inside a distributed repo - it needed a
    `.gitignore` line and it did not survive a re-extract. `common_data` sits beside the
    missions, so it survives both.

    `filename` stays as an injection point for the tests.
    """
    if filename is not None:
        return filename
    from ..fs import get_common_data_filename, get_mission_name
    return get_common_data_filename("game_codes", (get_mission_name() or "mission") + ".yaml")


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


def _loadout_ship_still_alive(ship):
    """True unless this is one of OUR agents and it is known deleted.

    The loadout helpers accept duck-typed stand-ins - anything with .id/.name/.art_id -
    and the tests rely on that, so a foreign object is not ours to judge. An Agent (or a
    SpawnData/CloseData wrapping one) IS ours, and a deleted one must be dropped: the
    start-of-game cull strips __player__ from the unused slots and deletes them but never
    removes default_player_ship, and a picker snapshot taken before the cull holds them
    all. `.name`/`.art_id` are cached on the Python object so a dead ship still answers,
    which is what let deleted slots reach an apply (a write straight to the engine
    object) and get baked into a saved preset.
    """
    from ..agent import Agent, CloseData, SpawnData
    from .query import to_object
    if isinstance(ship, (Agent, CloseData, SpawnData)):
        return to_object(ship) is not None
    return True


def player_loadout_from_ships(ships):
    """Build a loadout token from ship objects, reading ``.name`` and ``.art_id``.

    ``ships`` is sorted by id first so the slot order is stable and matches the
    rehydrate side (spawn_players walks the player ships in id order too).
    """
    # Drop ships that are already gone. `.name`/`.art_id` are cached on the Python
    # object so a deleted one still answers, which means a preset captured after the
    # start-of-game cull would quietly bake in the slots that were just deleted.
    ordered = sorted([s for s in (ships or []) if _loadout_ship_still_alive(s)],
                     key=lambda s: getattr(s, "id", 0))
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


def player_loadout_apply_to_ships(ships=None):
    """Write the pending ``SHIP_LOADOUT`` onto the live player ships, then CLEAR it.

    This is what makes a RESTORED setup lose to a person. A restored loadout otherwise
    sits in ``SHIP_LOADOUT`` until the game starts, and the roster reconcile applies it
    over whatever is on the ships at that moment - which includes the name and hull helm
    just chose in the lobby. Last session's ships would silently overwrite this session's
    choice, and the person who made it gets no hint that it happened.

    Applying it up front inverts that: the restored names and hulls are what helm SEES in
    the picker, and anything helm changes from there is simply the newer value. Clearing
    the var is the other half - it leaves the reconcile nothing to override with.

    Ships are matched to slots in id order, the same order :func:`player_loadout_from_ships`
    captured them in.

    No player ships yet means the restore is too early to land on anything, so the var is
    left ALONE for the reconcile to apply at start - which is correct, because nobody has
    had the chance to choose anything either.

    Args:
        ships (list|None): the player ships, or None to use the ``default_player_ship``
            role.

    Returns:
        int: how many slots were applied.
    """
    from .execution import set_shared_variable
    slots = player_loadout_active()
    if not slots:
        return 0
    if ships is None:
        from .roles import role
        from .query import to_object_list
        # `& role("__player__")` matters: the start-of-game cull strips __player__ from
        # the unused slots and deletes them, but never removes default_player_ship. On
        # its own that role can therefore name ships that are on their way out, and the
        # writes below go straight to the engine object -- `ship.name =` is
        # blob.set("name_tag", ...), which is the call a server died in.
        ships = to_object_list(role("default_player_ship") & role("__player__"))
    # A caller-supplied list is a SNAPSHOT and gets the same treatment: a console that
    # sat on the picker across the start captured the whole roster, culled slots and all.
    ships = [s for s in (ships or []) if _loadout_ship_still_alive(s)]
    ordered = sorted(ships, key=lambda s: getattr(s, "id", 0))
    if not ordered:
        return 0
    applied = 0
    for ship, slot in zip(ordered, slots):
        if slot.get("hull"):
            ship.art_id = slot["hull"]
        if slot.get("name"):
            ship.name = slot["name"]
        applied += 1
    set_shared_variable("SHIP_LOADOUT", "")
    return applied


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


# --- last-used setup --------------------------------------------------------
# "Start the next game the way the last one started." Stored in the same per-mission file
# as the named presets, under a reserved key that is not a map path - so it is never
# offered in the presets dropdown and a map can never collide with it.
#
# It reuses the game code rather than inventing a save format, which buys the
# cross-mission guard for free: game_code_decode resolves the map BY PATH against the
# current story and changes nothing when no map matches, so a setup remembered for one
# mission is already a safe no-op in another.
_GAME_CODE_LAST_KEY = "__last_used__"


def game_code_last_save(code, filename=None):
    """Remember ``code`` as this mission's last-used setup, keyed by its map.

    Called when a game STARTS, not when it ends: that records what was actually played,
    and it survives a crash or a quit that never reaches a results screen.

    Args:
        code (str): a code from :func:`game_code_encode`.
        filename (str|None): override the store path (tests).

    Returns:
        str|None: the code stored, or ``None`` if it was empty.
    """
    from ..fs import save_yaml_data
    if not code:
        return None
    map_path = code.split(";")[0]
    data = game_code_presets_load(filename)
    last = data.get(_GAME_CODE_LAST_KEY)
    if not isinstance(last, dict):
        last = {}
    last[map_path] = code
    data[_GAME_CODE_LAST_KEY] = last
    save_yaml_data(_game_code_presets_file(filename), data)
    return code


def game_code_last_code(map_path, filename=None):
    """The last-used code for one map, or ``""`` when there is none."""
    last = game_code_presets_load(filename).get(_GAME_CODE_LAST_KEY)
    if not isinstance(last, dict):
        return ""
    return str(last.get(map_path) or "")


def game_code_last_apply(map, filename=None):
    """Apply this mission's remembered setup for ``map``, if there is one.

    Safe to call unconditionally: it does nothing when nothing was remembered, when the
    setting that writes them was never on, or when the remembered code names a map this
    story does not have.

    Args:
        map (Label|str): the map label (or its path) about to be shown/started.
        filename (str|None): override the store path (tests).

    Returns:
        bool: whether a remembered setup was applied.
    """
    map_path = map if isinstance(map, str) else getattr(map, "path", None)
    if not map_path:
        return False
    code = game_code_last_code(map_path, filename)
    if not code:
        return False
    if game_code_decode(code) is None:
        return False
    # Push any restored loadout onto the ships now and clear it, so a person choosing a
    # ship afterwards wins - see player_loadout_apply_to_ships.
    player_loadout_apply_to_ships()
    return True






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


def map_start(map):
    """Start a map: apply its defaults, resume the sim, schedule it, announce it.

    The canonical launch sequence. It existed twice before this - in LegendaryMissions'
    server console and in the headless runner - and the two had DRIFTED on things that
    matter: whether the sim resumes before or after scheduling, and ``task_schedule``
    versus ``task_schedule_server``. One implementation ends that.

    What it does, in order:

      * ``map_apply_defaults`` - set-if-absent shared vars, so a value from settings.yaml,
        the story or a loaded game code still wins. Idempotent, and applied here as well
        as at panel-render time because a map can be started without a panel ever showing.
      * ``sim_resume()`` - the lobby sim is paused; a map body that awaits ``delay_sim``
        would never advance otherwise.
      * ``task_schedule(map, defer=True)`` - deferred so consoles repaint before the map
        body's first tick.
      * ``GAME_STARTED`` and the ``game_started`` signal - the contract missions gate on.

    What it deliberately does NOT do, because these are LegendaryMissions' own contract
    and are meaningless (or wrong) in a mission that does not load it: the
    ``reconcile_player_roster`` signal, ``sbs.set_beam_damages``, the ``GAME_TIME_LIMIT``
    timer, music selection, and the client/server GUI reroutes. LM does those around its
    own call to this.

    Args:
        map (Label | None): The ``@map`` label to start. ``None`` is a no-op, matching
            ``map_apply_defaults``.

    Returns:
        Label | None: The map that was started, or ``None``.
    """
    if map is None:
        return None
    from .execution import task_schedule, set_shared_variable
    from .signal import signal_emit
    from .cosmos import sim_resume

    map_apply_defaults(map)
    sim_resume()
    task_schedule(map, defer=True)
    set_shared_variable("GAME_STARTED", True)
    signal_emit("game_started", {})
    return map
