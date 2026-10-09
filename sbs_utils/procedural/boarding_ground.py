"""The ground a boarding party walks, loaded with one call.

A tile-map away mission is files a writer makes - ``*.tileset`` (which ground can be
walked), ``*.tiles`` (the areas) and sections of a ``.amd`` (the things on the ground, the
people, what they say). Getting those into the game used to be a dozen calls in the right
order, and Dawnline carried them in a Python file of its own. This is that sequence::

    shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"), data_parser=amd_mission_data)
    boarding_ground_load(MISSION_DOC)

What it does, in order:

1. every ``*.tileset`` in the mission folder is declared, and every ``*.tiles`` area is
   loaded (the same files ``sbs lint`` and the tile editor read);
2. the art is loaded - the mission's own ``media/tileart/builtin`` if it has one, then the
   sets the ``TILE_ART`` setting names, found in the mission or in a media pack pinned in
   ``story.json``. A set that is not installed is said ONCE, plainly, and the ground is
   drawn without it;
3. default looks: the crew figure, the bag a fallen hostile leaves, the badges over what
   is still worth a look - each only when the art that was loaded has it, and only where
   the mission has not chosen its own;
4. the document's ``Props`` section is declared and placed, then ``People`` and
   ``Hostiles``; its ``Scenes`` are what a prop's ``Scene:`` and a person's
   ``Talk scene:`` name; ``Skills:`` on its crew are read for ``check``;
5. clicks reach props and people, guards read jobs, skills and packs, and the walk tick
   is started.

Section keys are the frozen ones: ``props`` / ``prop`` / ``objects``; ``people`` /
``hostiles`` / ``hostile``; ``scenes`` / ``scene`` / ``boarding``.

SAFE TO CALL AGAIN. Everything is keyed: an area already loaded, a prop or a person
already declared is left exactly as it is - opened doors stay open - so a map body that
runs twice does not rebuild the world under the party.

Every public name is ``boarding_ground_``. Stdlib only.
"""
import glob
import os

#: Section keys, in the order they are looked for. Frozen for 1.4.0.
PROP_SECTIONS = ("props", "prop", "objects")
PEOPLE_SECTIONS = ("people", "hostiles", "hostile")
SCENE_SECTIONS = ("scenes", "scene", "boarding")

#: The default looks, by the shared key the Cosmos-Tiles packs draw them with.
CREW_SPRITE = "fig:crew_eva"
DROP_SPRITE = "prop:bag"
HINT_SPRITES = {"new": "ui:hint_new", "lead": "ui:hint_lead", "way": "ui:hint_way"}

# Per-mission, on the reset ledger (`boarding_ground_clear` / `boarding_ground_count`).
_STATE = {"result": None, "scenes": None, "said": set(), "styled": set(),
          "tilesets": set()}


def _say(message, once=None, loud=False):
    """Tell the author. ``loud`` also writes ``mast.runtime``, which a headless test
    fails on - for a mistake in the mission's own files, never for art that is merely
    not installed on this machine."""
    if once is not None:
        if once in _STATE["said"]:
            return
        _STATE["said"].add(once)
    try:
        from .execution import log
        log(message, "boarding", "warning")
    except Exception:                                    # noqa: BLE001
        pass
    try:
        # The engine's debug.log: `log()` to a named category has no handler there and
        # `print` goes nowhere, so this is the line an author can actually find.
        from ..mast.mast import DEBUG
        DEBUG("[boarding_ground] " + message)
    except Exception:                                    # noqa: BLE001
        pass
    print("boarding_ground: " + message)
    if loud:
        import logging
        logging.getLogger("mast.runtime").warning("boarding_ground: " + message)


def boarding_ground_files(folder=None):
    """The tileset and area files of a mission: ``(tilesets, areas)``, sorted paths.

    The same recursive ``*.tileset`` / ``*.tiles`` search ``tilemap_world`` makes for the
    linter, less anything under a folder whose name starts ``__`` or ``.`` - a built
    ``__site__``, a ``.git`` - which hold copies, not the mission.
    """
    if folder is None:
        from ..fs import get_mission_dir
        folder = get_mission_dir()

    def mine(path):
        rel = os.path.relpath(path, folder).replace("\\", "/")
        return not any(part.startswith("__") or part.startswith(".")
                       for part in rel.split("/")[:-1])

    def find(ext):
        return sorted(p for p in glob.glob(os.path.join(folder, "**", "*." + ext),
                                           recursive=True) if mine(p))
    return find("tileset"), find("tiles")


def _read(path):
    try:
        from .amd import amd_read_text
        return amd_read_text(path)
    except Exception as e:                               # noqa: BLE001
        _say("cannot read %s: %s" % (path, e), loud=True)
        return None


def _sections(docs, keys):
    """Every section, across the documents, whose key is one of ``keys``."""
    from .amd_doc import amd_section
    out = []
    for doc in docs:
        for key in keys:
            section = amd_section(doc, key)
            if section is not None and not any(section is s for s in out):
                out.append(section)
    return out


def _only_new(section, known):
    """The section's records nothing has declared yet, as a section."""
    fresh = [n for n in section.get("children", []) or []
             if str(n.get("key") or "").strip() and known(n.get("key")) is None]
    return {"children": fresh}


def _load_art(tilesets):
    """Load the art sets that are installed. Returns ``(loaded, missing)``."""
    from .tilemap_art import tilemap_art_sets, tilemap_art_find, tilemap_art_use
    found, missing = [], []
    for name in tilemap_art_sets():
        if tilemap_art_find(name) is not None:
            found.append(name)
        elif name != "builtin":
            # `builtin` is the mission's OWN art, and a mission is free to have none.
            missing.append(name)
    loaded = tilemap_art_use(*found, tileset=list(tilesets)) if found else []
    if missing:
        _say("the tile art %s is not installed, so what it draws is missing%s. It comes "
             "from the media packs pinned under `shared_media` in story.json (and named "
             "by the TILE_ART setting): fetch them with `sbs fetch <this mission> "
             "--update-libs`. The mission still runs - walking, scenes and quests do "
             "not need the art."
             % (", ".join("'%s'" % m for m in missing),
                "" if loaded else " - with no art at all the map on the crew console is "
                                  "BLACK, and nothing on it is drawn"),
             once="art-missing")
    return loaded, missing


def _default_looks():
    """The looks the loaded art can draw, where the mission chose none of its own."""
    from .gui.image import ImageAtlas
    from . import boarding_tiles, boarding_combat, boarding_hints
    have = ImageAtlas.all
    if boarding_tiles._STYLE.get("sprite") is None and CREW_SPRITE in have:
        boarding_tiles.boarding_tile_style(sprite=CREW_SPRITE)
        _STATE["styled"].add("crew")
    if boarding_combat._DROP.get("sprite") is None and DROP_SPRITE in have:
        boarding_combat.boarding_drop_sprite(DROP_SPRITE)
        _STATE["styled"].add("drop")
    if not any(boarding_hints._STYLE.values()):
        style = {kind: key for kind, key in HINT_SPRITES.items() if key in have}
        if style:
            boarding_hints.boarding_hint_style(**style)
            _STATE["styled"].add("hints")


def boarding_ground_load(doc=None, folder=None):
    """Load a mission's ground: its tile files, its art, and what stands on it.

    Args:
        doc (optional): the parsed mission document - what
            ``document_get_amd_file(..., data_parser=amd_mission_data)`` returns - or a
            list of them when the world and its scenes are separate files. Without one
            only the tile files and the art are loaded.
        folder (str, optional): where to look for ``*.tileset`` / ``*.tiles``. The
            mission folder by default.

    Returns:
        dict: what was done - ``tilesets``, ``areas``, ``props``, ``people``, ``scenes``,
        ``skills`` (counts), ``art`` (the sets loaded),
        ``art_missing`` (the sets named and not installed), and ``unplaced`` (the keys of
        props and people that could not be put on the map: an ``Area:`` that is no area,
        a ``Mark:`` the area file does not have). Each of those is also said in
        ``mast.runtime.log``.
    """
    from . import boarding_props, boarding_combat
    from .tilemap import (tilemap_tileset_load, tilemap_load, tilemap_parse, tilemap_area,
                          tilemap_tileset_known, tilemap_tileset_parse, tilemap_watch,
                          TilemapError)
    from .tilemap_art import tilemap_art_loaded
    from .boarding import boarding_metric_install
    from .boarding_checks import boarding_skills_from_amd
    from .amd_dialogue import dialogue_scenes

    docs = [d for d in (doc if isinstance(doc, (list, tuple)) else [doc]) if d is not None]
    result = _STATE["result"] or {"tilesets": 0, "areas": 0, "props": 0, "people": 0,
                                  "scenes": 0, "skills": 0, "art": [], "art_missing": [],
                                  "unplaced": []}

    # 1. The tile files. A tileset first: an area names the one it is drawn with.
    ts_files, area_files = boarding_ground_files(folder)
    tilesets = []
    for path in ts_files:
        text = _read(path)
        if text is None:
            continue
        try:
            name = tilemap_tileset_parse(text)["name"]
        except TilemapError as e:
            _say("%s is not a tileset: %s" % (os.path.basename(path), e), loud=True)
            continue
        # DECLARED ONCE PER MISSION, not "unless somebody already has": tilesets outlive
        # the per-mission reset (an addon may own one), so a tileset of the same name
        # left by the mission before this one would otherwise be kept, rules and all.
        if name not in _STATE["tilesets"]:
            tilemap_tileset_load(text)
            _STATE["tilesets"].add(name)
            result["tilesets"] += 1
        tilesets.append(name)
    for path in area_files:
        text = _read(path)
        if text is None:
            continue
        try:
            rec = tilemap_parse(text)
        except TilemapError as e:
            _say("%s is not a tile area: %s" % (os.path.basename(path), e), loud=True)
            continue
        if tilemap_area(rec["key"]) is not None:
            continue                                     # loaded already: left as it is
        if not tilemap_tileset_known(rec["tileset"]):
            _say("the area '%s' (%s) is drawn with the tileset '%s', and no .tileset file "
                 "in the mission declares one. Nothing on it can be walked."
                 % (rec["key"], os.path.basename(path), rec["tileset"]), loud=True)
        if tilemap_load(text):
            result["areas"] += 1
    if docs and not area_files:
        _say("no .tiles file was found in the mission folder, so there is no ground to "
             "stand on. An area is a text file - see `ground/landing.tiles` in the "
             "`away` template.", once="no-areas", loud=True)

    # 2. The art, once: a second call finds it loaded.
    if not result["art"] and not result["art_missing"]:
        loaded, missing = _load_art(tilesets)
        result["art"], result["art_missing"] = list(loaded), list(missing)
    result["art"] = [name for name in tilemap_art_loaded()] or result["art"]

    # 3. Default looks, from whatever art there is.
    _default_looks()

    # 4. What stands on the ground, and what it says.
    scenes = dict(_STATE["scenes"] or {})
    for section in _sections(docs, SCENE_SECTIONS):
        for key, node in dialogue_scenes(section).items():
            scenes.setdefault(key, node)
    if scenes:
        _STATE["scenes"] = scenes
        boarding_props.boarding_props_scenes(scenes)
    result["scenes"] = len(scenes)
    for section in _sections(docs, PROP_SECTIONS):
        result["props"] += len(boarding_props.boarding_props_declare(
            _only_new(section, boarding_props.boarding_prop)))
    for section in _sections(docs, PEOPLE_SECTIONS):
        result["people"] += len(boarding_combat.boarding_hostiles_declare(
            _only_new(section, boarding_combat.boarding_hostile)))
    if docs:
        result["skills"] = sum(boarding_skills_from_amd(one) for one in docs)
    boarding_props.boarding_props_place()
    boarding_combat.boarding_hostiles_place()

    # 5. Clicks, guards and the walk.
    boarding_metric_install()
    boarding_props.boarding_props_install()
    boarding_combat.boarding_combat_install()
    tilemap_watch()

    result["unplaced"] = boarding_ground_unplaced()
    for key in result["unplaced"]:
        _say(_why_unplaced(key), once="unplaced:" + key, loud=True)
    _STATE["result"] = result
    return dict(result)


def boarding_ground_unplaced():
    """The keys of props and people that should be on the map and are not, sorted.

    Not the ones that are meant to be absent: hidden until a signal, picked up, down.
    """
    from . import boarding_props, boarding_combat
    out = []
    for key, rec in boarding_props._PROPS.items():
        if rec["id"] is None and rec["shown"] and not rec["taken"]:
            out.append(key)
    for key, rec in boarding_combat._HOSTILES.items():
        if rec["id"] is None and rec["shown"] and rec["state"] != "down":
            out.append(key)
    return sorted(out)


def _why_unplaced(key):
    from . import boarding_props, boarding_combat
    from .tilemap import tilemap_area, tilemap_marks
    rec = boarding_props._PROPS.get(key) or boarding_combat._HOSTILES.get(key) or {}
    what = "'%s' (%s)" % (rec.get("name") or key, key)
    area = rec.get("area")
    if not area:
        return "%s has no `Area:`, so it is nowhere." % what
    if tilemap_area(area) is None:
        return ("%s is in the area '%s', and no .tiles file is an area with that key, "
                "so it was not placed." % (what, area))
    at = rec.get("at")
    if at is None:
        return ("%s has no place in '%s': give it `Mark:` (a mark in the area file) or "
                "`At: x, y`." % (what, area))
    if isinstance(at, (list, tuple)) and len(at) < 2:
        # `At:` is a coordinate everywhere in AMD, so a word written there arrives empty.
        return ("%s has an `At:` that is not `x, y`, so it has no place in '%s'. A mark "
                "name goes in `Mark:`, not `At:`." % (what, area))
    marks = ", ".join(sorted(str(m) for m in (tilemap_marks(area) or ()))) or "none"
    return ("%s is at '%s' in '%s', which is neither a mark in that area file nor a "
            "cell. A mark name goes in `Mark:`, not `At:`. The marks there: %s."
            % (what, at, area, marks))


def boarding_ground_scenes():
    """The scenes the loaded documents hold, ``{key: scene}`` - what a prop's ``Scene:``
    and a person's ``Talk scene:`` name, and what ``boarding_visit`` is handed."""
    return dict(_STATE["scenes"] or {})


def boarding_ground_loaded():
    """What the last ``boarding_ground_load`` reported, or None before the first."""
    return dict(_STATE["result"]) if _STATE["result"] else None


def boarding_ground_clear():
    """The per-mission reset: nothing loaded, nothing said, and the default looks this
    module chose are handed back so the next mission's art decides its own."""
    from . import boarding_combat, boarding_hints
    if "drop" in _STATE["styled"]:
        boarding_combat._DROP["sprite"] = None
    if "hints" in _STATE["styled"]:
        for kind in boarding_hints._STYLE:
            boarding_hints._STYLE[kind] = None
    _STATE["result"] = None
    _STATE["scenes"] = None
    _STATE["said"].clear()
    _STATE["styled"].clear()
    _STATE["tilesets"].clear()


def boarding_ground_count():
    """Reset-ledger probe."""
    return ((1 if _STATE["result"] else 0) + len(_STATE["scenes"] or ())
            + len(_STATE["said"]) + len(_STATE["styled"]) + len(_STATE["tilesets"]))
