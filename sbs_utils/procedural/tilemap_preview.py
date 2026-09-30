"""What a tile area LOOKS like, as data, for tools that draw it outside the game - the
VS Code tile editor, a preview script.

The game decides a cell's picture in Python - ``tilemap_cell_look`` (variants, edges,
shade, grids) and ``tilemap_cell_fringes`` (soft seams between kinds) - and a tool that
redid that in another language would drift from it the first time either changed. So a
tool asks here instead: the same functions, run over the file being edited, with the art
sets the mission would load.

Dev-side: it reads the mission folder and its neighbors from disk (the way
``LandingParty/_tools/preview_map.py`` does), never the running game's media paths.
Stdlib only.
"""
import json
import os
import re

from . import tilemap as T
from .tilemap_lint import (_PLACED, _fields, _scan, tilemap_area_lenient,
                           tilemap_lint_placements, tilemap_world)
from .tilemap import TilemapError, tilemap_parse, _norm, _xy


def tilemap_preview_find_set(mission_root, name):
    """The folder of an art set on disk, or None.

    This mission's ``media/tileart/<name>`` first; then a repo checked out beside it
    (what you are iterating on - ``Cosmos-Tiles/frontier/tileart/frontier``); then the
    unpacked packs in ``__lib__/media`` (what the engine would load)."""
    if not mission_root:
        return None

    def ok(folder):
        return os.path.isfile(os.path.join(folder, "manifest.json"))

    here = os.path.join(mission_root, "media", "tileart", name)
    if ok(here):
        return here
    missions = os.path.dirname(os.path.abspath(mission_root))
    try:
        repos = sorted(os.listdir(missions))
    except OSError:
        repos = []
    for repo in repos:
        if repo == "__lib__" or repo.startswith("."):
            continue
        base = os.path.join(missions, repo)
        if not os.path.isdir(base):
            continue
        for folder in (os.path.join(base, "media", "tileart", name),
                       os.path.join(base, "tileart", name),
                       os.path.join(base, name, "tileart", name)):
            if ok(folder):
                return folder
    lib = os.path.join(missions, "__lib__", "media")
    try:
        packs = sorted(os.listdir(lib))
    except OSError:
        packs = []
    for pack in packs:
        folder = os.path.join(lib, pack, "tileart", name)
        if ok(folder):
            return folder
    return None


def tilemap_preview_sets(mission_root):
    """The sets a mission loads by default: ``builtin`` and then its ``TILE_ART``
    setting, read from ``settings.yaml`` without a yaml parser."""
    names = []
    try:
        with open(os.path.join(mission_root, "settings.yaml"), encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"TILE_ART\s*:\s*(.*)$", line)
                if m:
                    value = m.group(1).split(" #")[0].strip().strip("[]\"'")
                    names = [n.strip().strip("\"'") for n in
                             value.replace(";", ",").split(",") if n.strip()]
                    break
    except OSError:
        pass
    return ["builtin"] + [n for n in names if n != "builtin"]


def _load_sets(mission_root, names):
    """Every sprite the sets draw, merged in order (a later set wins key by key), plus
    the looks the game DERIVES from them by mirroring (``tilemap_art_mirror_pairs``): a
    figure's missing side and a ``"mirror": true`` prop's twin. A derived look is its
    source with the rect's left and right swapped - drawn mirrored, as the engine draws
    a rect that runs backwards."""
    from .tilemap_art import tilemap_art_mirror_pairs
    sprites, grounds, found, missing = {}, [], [], []
    mirror = {}
    for name in names:
        folder = tilemap_preview_find_set(mission_root, name)
        if folder is None:
            missing.append(name)
            continue
        try:
            with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as fh:
                m = json.load(fh)
        except Exception:                                # noqa: BLE001
            missing.append(name)
            continue
        sheets = m.get("sheets") or {}
        for key, spec in (m.get("sprites") or {}).items():
            sheet = sheets.get(spec.get("sheet"), spec.get("sheet"))
            if not sheet or not spec.get("rect"):
                continue
            path = os.path.join(folder, sheet if str(sheet).endswith(".png") else sheet + ".png")
            cells = spec.get("cells") or (1, 1)
            anchor = spec.get("anchor") or (0.5, 1.0)
            sprites[key] = {"sheet": os.path.abspath(path), "rect": list(spec["rect"]),
                            "color": spec.get("color"),
                            "cells": [float(cells[0]), float(cells[1])],
                            "anchor": [float(anchor[0]), float(anchor[1])]}
            mirror[key] = bool(spec.get("mirror"))
        grounds.append(m.get("ground") or {})
        found.append({"name": name, "folder": os.path.abspath(folder)})
    for source, key in tilemap_art_mirror_pairs(sprites, [k for k, v in mirror.items() if v]):
        src = sprites[source]
        l, t, r, b = src["rect"]
        sprites[key] = dict(src, rect=[r, t, l, b],
                            anchor=[1.0 - src["anchor"][0], src["anchor"][1]])
    return sprites, grounds, found, missing


def _truthy(value):
    return str(value or "").strip().lower() in ("yes", "true", "1")


def tilemap_placements(area, amd_docs, world=None):
    """Every prop, person and hostile a mission's AMD stands on one area, with WHERE in
    the ``.amd`` each position is written - so a tool can draw them and move them.

    Args:
        area (str): the area key.
        amd_docs: ``[(uri, parsed amd_core document, text)]`` - the mission's .amd files.
        world (dict, optional): ``tilemap_world``, for the lint findings attached to each.

    Returns:
        list: one dict per placement - ``key``, ``display``, ``kind`` (prop/hostile),
        ``calm``, ``hidden``, ``sprite``, ``color``, ``uri``, ``line`` (the heading,
        0-based), ``how`` (mark/at/None), ``mark``, ``cell`` ([x, y] or None), ``at``
        (the ``At:`` value's range: line, start, end - 0-based, end exclusive),
        ``patrol`` ([{x, y, line, start, end}]) and ``problems`` (lint messages).
    """
    area = _norm(area)
    rec = ((world or {}).get("areas") or {}).get(area)
    out = []
    for uri, doc, text in amd_docs or ():
        findings = tilemap_lint_placements(text, world, doc=doc) if world else []
        for node in doc.nodes:
            if node.kind not in _PLACED:
                continue
            f = _fields(node)
            if "area" not in f or _norm(f["area"][2]) != area:
                continue
            lines = {n for n, _raw in node.fence_lines}
            item = {"key": node.key, "display": node.display or node.key, "kind": node.kind,
                    "calm": _truthy(f.get("calm", (0, 0, ""))[2]),
                    "hidden": bool(f.get("hidden until", (0, 0, ""))[2]),
                    "sprite": f.get("sprite", (0, 0, ""))[2] or None,
                    "color": f.get("color", (0, 0, ""))[2] or None,
                    "uri": uri, "line": (node.span.line - 1) if node.span else 0,
                    "how": None, "mark": None, "cell": None, "at": None, "patrol": [],
                    "problems": [x.message for x in findings if x.line in lines]}
            if "mark" in f:
                item["how"], item["mark"] = "mark", _norm(f["mark"][2])
                cells = sorted((rec or {}).get("marks", {}).get(item["mark"], ()))
                item["cell"] = list(cells[0]) if cells else None
            elif "at" in f:
                n, col, value = f["at"]
                item["how"] = "at"
                item["at"] = {"line": n - 1, "start": col, "end": col + len(value)}
                cell = _xy(value)
                item["cell"] = list(cell) if cell else None
            if "patrol" in f:
                n, col, value = f["patrol"]
                raw = dict(node.fence_lines).get(n, "")
                pos = col
                for chunk in value.replace(";", "  ").split("  "):
                    chunk = chunk.strip()
                    pt = _xy(chunk)
                    if not chunk or pt is None:
                        continue
                    c = raw.find(chunk, pos)
                    if c < 0:
                        continue
                    pos = c + len(chunk)
                    item["patrol"].append({"x": pt[0], "y": pt[1], "line": n - 1,
                                           "start": c, "end": c + len(chunk)})
            out.append(item)
    return out


def _sprite_look(sprites, base, facing="s", cell=None, fixed=False):
    """The key a figure is drawn with standing still - the same fallbacks the game uses
    (``tilemap_sprite_look``): a facing's idle frame, the facing, then the base key. A
    still thing (``fixed`` - a prop) with a mirrored twin is the twin on the cells the
    game picks it on."""
    if fixed and cell and "%s_mirror" % base in sprites and T._cell_hash(*cell) % 2:
        base = "%s_mirror" % base
    for k in ("%s_%s_idle" % (base, facing), "%s_%s" % (base, facing), base):
        if k in sprites:
            return k
    return None


def tilemap_preview(area_text, mission_root=None, sets=None, texts=None, world=None,
                    amd_docs=None, things=None):
    """Everything a tool needs to draw one area file as the game would.

    Args:
        area_text (str): the area file - usually the unsaved editor buffer.
        mission_root (str, optional): its mission folder, for the tileset file, the
            other areas and the art sets.
        sets (list, optional): art set names; default ``tilemap_preview_sets``.
        texts (dict, optional): open buffers, ``{normcase(abspath): text}``.
        world (dict, optional): an already built ``tilemap_world``.
        things (list, optional): more placements, in ``tilemap_placements``' shape - a
            generated deck's furniture and doors (``tilemap_preview_deck``).

    Returns:
        dict: ``ok``, and on success ``area`` (key, title, tileset, w, h, entry), ``tiles``
        (rows of kind or None), ``marks``, ``exits``, ``legend``, ``kinds`` (walk/see or
        None when no tileset file says), ``looks`` (rows of sprite key or None),
        ``fringes`` ([x, y, [keys]]), ``sprites`` (key -> sheet path, rect, color - only
        the keys drawn), ``sets`` found and ``missing``.
    """
    try:
        tilemap_parse(area_text)
        error = None
    except TilemapError as e:
        error = str(e)
    rec = tilemap_area_lenient(area_text)
    if rec is None:
        return {"ok": False, "error": error or "cannot read the area"}
    if world is None:
        world = tilemap_world(mission_root, texts) if mission_root else \
            {"tilesets": None, "areas": {}}
    ts = (world.get("tilesets") or {}).get(rec["tileset"])
    scan = _scan(area_text)
    legend = []
    for ch, (n, raw) in scan["legend"].items():
        kind, _, mark = raw.strip()[2:].strip().partition("@")
        legend.append({"ch": ch, "kind": _norm(kind), "mark": _norm(mark) or None,
                       "line": n - 1})
    used = sorted({k for row in rec["tiles"] for k in row if k} |
                  {entry["kind"] for entry in legend})
    kinds = {}
    for kind in used:
        spec = (ts or {}).get("kinds", {}).get(kind) if ts else None
        kinds[kind] = {"walk": spec["walk"] if spec else None,
                       "see": spec["see"] if spec else None,
                       "look": (spec or {}).get("look"),
                       "color": (spec or {}).get("color"),
                       "declared": spec is not None}

    names = list(sets) if sets else tilemap_preview_sets(mission_root) if mission_root \
        else ["builtin"]
    sprites, grounds, found, missing = _load_sets(mission_root, names)

    # Run the game's own look functions over this area. They read the tile world's
    # module tables, so borrow them and put back exactly what was there.
    saved_ts, saved_areas = dict(T._TILESETS), dict(T._AREAS)
    looks, fringes = [], []
    try:
        name = "__preview__"
        T.tilemap_tileset(name, ts["kinds"] if ts else {k: {} for k in used})
        from .tilemap_art import tilemap_art_ground
        for ground in grounds:
            tilemap_art_ground(name, ground)
        area = dict(rec, key="__preview__", tileset=name)
        T._AREAS["__preview__"] = area
        for y in range(rec["h"]):
            row = []
            for x in range(rec["w"]):
                spec = T._kind_spec(area, rec["tiles"][y][x])
                look = T.tilemap_cell_look(spec, x, y, "__preview__") \
                    if spec and (spec.get("cell") or spec.get("grid")) else None
                row.append(look)
                fr = T.tilemap_cell_fringes("__preview__", x, y)
                if fr:
                    fringes.append([x, y, fr])
            looks.append(row)
    finally:
        T._TILESETS.clear()
        T._TILESETS.update(saved_ts)
        T._AREAS.clear()
        T._AREAS.update(saved_areas)

    placements = tilemap_placements(rec["key"], amd_docs, dict(world, areas=dict(
        world.get("areas") or {}, **{rec["key"]: rec}))) if amd_docs else []
    placements += [dict(t) for t in things or ()]
    for item in placements:
        # The game places a figure facing south and turns it as it walks; the other
        # facings are here so a tool can preview the art each way round.
        fixed = item["kind"] == "prop"
        item["looks"] = {f: _sprite_look(sprites, item["sprite"], f, item["cell"], fixed)
                         for f in "nesw"} if item["sprite"] else {}
        item["look"] = item["looks"].get("s")

    drawn = {k for row in looks for k in row if k} | {k for _, _, ks in fringes for k in ks} \
        | {k for p in placements for k in p["looks"].values() if k}
    exits = dict(rec["exits"])
    for mark in rec["marks"]:
        if mark.startswith("to_") and mark not in exits:
            exits[mark] = mark[3:]
    return {
        "ok": True, "error": error,
        "area": {"key": rec["key"], "title": rec["title"], "tileset": rec["tileset"],
                 "w": rec["w"], "h": rec["h"], "entry": rec.get("entry"),
                 "known": rec["known"], "beam": rec["beam"]},
        "tiles": rec["tiles"],
        "marks": {m: sorted([list(c) for c in cells]) for m, cells in rec["marks"].items()},
        "exits": exits,
        "legend": legend,
        "kinds": kinds,
        "tilesetFile": bool(ts),
        # Every kind the tileset declares, used or not - what a new legend entry may be.
        "tilesetKinds": {k: {"walk": s["walk"], "see": s["see"], "look": s.get("look"),
                             "color": s.get("color")}
                         for k, s in (ts or {}).get("kinds", {}).items()},
        "looks": looks,
        "fringes": fringes,
        "sprites": {k: v for k, v in sprites.items() if k in drawn},
        "sets": found,
        "missing": missing,
        "areas": sorted(world.get("areas") or {}),
        "placements": placements,
    }


def tilemap_preview_file(path, mission_root=None, sets=None):
    """``tilemap_preview`` of an area file on disk, with its mission's props and people
    read from the mission's ``.amd`` files on disk - for a tool with no editor behind it
    (``sbs site``). The mission is the nearest folder above with a ``story.json``."""
    path = os.path.abspath(path)
    if mission_root is None:
        folder = os.path.dirname(path)
        while folder and not os.path.isfile(os.path.join(folder, "story.json")):
            parent = os.path.dirname(folder)
            folder = None if parent == folder else parent
        mission_root = folder
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    world = tilemap_world(mission_root) if mission_root else None
    amd_docs = []
    if mission_root:
        from .amd_core import parse as amd_parse
        for root, dirs, files in os.walk(mission_root):
            dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))
            for name in sorted(files):
                if not name.endswith(".amd"):
                    continue
                full = os.path.join(root, name)
                try:
                    with open(full, encoding="utf-8") as fh:
                        source = fh.read()
                    amd_docs.append((full, amd_parse(source, full), source))
                except Exception:                        # noqa: BLE001
                    continue
    return tilemap_preview(text, mission_root, sets=sets, world=world, amd_docs=amd_docs)


def _thing(key, name, sprite, cell):
    return {"key": key, "display": name, "kind": "prop", "calm": False, "hidden": False,
            "sprite": sprite, "color": None, "uri": None, "line": 0, "how": "at",
            "mark": None, "cell": list(cell), "at": None, "patrol": [], "problems": []}


def tilemap_preview_deck(plan_text, mission_root=None, sets=None, title=None):
    """``tilemap_preview`` of the boarding deck the library generates from a ship's
    interior plan (a ``.grid`` file) - the deck ``boarding_deck_build`` builds, with its
    furniture and doors as ``placements`` (props) and its rooms as ``room:<name>`` marks.

    Drawn with the mission's art sets and ``station``, whose looks decks are made of.
    The result also carries ``ship`` (the plan's shipData key)."""
    from . import boarding_deckplan as D
    try:
        plan = D.boarding_deck_plan_ascii(plan_text)
    except Exception as e:                               # noqa: BLE001
        return {"ok": False, "error": str(e)}
    if not plan.get("cells"):
        return {"ok": False, "error": "the plan has no open cell"}
    layout = D.boarding_deck_layout(plan)
    key = _norm(plan.get("ship") or "deck")
    text = D.boarding_deck_text(layout, key, title or key, "deck")
    world = {"tilesets": {"deck": {"name": "deck", "kinds": D.boarding_deck_kinds()}},
             "areas": {}}
    things = [_thing(f"kit_{n}", sprite.split(":", 1)[-1].replace("_", " "), sprite, (x, y))
              for n, (sprite, x, y, _cell) in enumerate(layout["furniture"])]
    for n, d in enumerate(sorted(layout["doors"], key=lambda t: (t[1], t[0]))):
        side = layout["door_sides"].get(d, "front")
        things.append(_thing(f"door_{n}", "door", D.DOOR_SPRITES[side][0], d))
    if sets is None:
        # The mission's own sets, then `station` - where deck art lives. `builtin` only
        # when it is THIS mission's: the search would find a neighbor's.
        own = os.path.isfile(os.path.join(mission_root or "", "media", "tileart", "builtin",
                                          "manifest.json"))
        sets = [n for n in (tilemap_preview_sets(mission_root) if mission_root else [])
                if n != "builtin" or own]
        if "station" not in sets:
            sets.append("station")
    out = tilemap_preview(text, mission_root, sets=sets, world=world, things=things)
    if out.get("ok"):
        out["marks"].update({m: sorted([list(c) for c in cells])
                             for m, cells in layout["rooms"].items()
                             if m.startswith("room:") and m != "room:hallway"})
        out["ship"] = plan.get("ship")
    return out


def _look_key(look):
    """The one sprite that stands for a ground look in a list: its cell, else the first
    piece of its grid or variants."""
    if not isinstance(look, dict):
        return None
    for field in ("cell", "grid", "variants"):
        v = look.get(field)
        if isinstance(v, (list, tuple)):
            v = next((x for x in v if x), None)
        if v:
            return v
    return None


def tilemap_tileset_preview(text, mission_root=None, sets=None, world=None):
    """Everything a tool needs to edit one ``.tileset`` file: its kinds as written, every
    ground look the mission's art sets offer (with a sprite to show for each), and how
    many cells of each kind the mission's areas use.

    Returns:
        dict: ``ok``/``error``; ``name``, ``title``, ``kinds`` ({kind: rules}), ``lines``
        ({kind: 0-based line}), ``looks`` ({look: {key, tall, over, fringe, edges}}),
        ``art`` ({kind: sprite key or None - None means no art set draws it}),
        ``usage`` ({kind: cells}), ``areas`` (the areas that use this tileset),
        ``sprites``, ``sets``, ``missing``.
    """
    try:
        rec = T.tilemap_tileset_parse(text)
        error = None
    except TilemapError as e:
        rec, error = None, str(e)
    names = list(sets) if sets else tilemap_preview_sets(mission_root) if mission_root \
        else ["builtin"]
    sprites, grounds, found, missing = _load_sets(mission_root, names)
    looks = {}
    for ground in grounds:                       # later sets win, look by look
        for name, look in ground.items():
            if isinstance(look, dict):
                looks.setdefault(_norm(name), {}).update(look)
    looks_out = {name: {"key": _look_key(look), "tall": bool(look.get("tall")),
                        "over": look.get("over"), "fringe": bool(look.get("fringe")),
                        "edges": bool(look.get("edges"))}
                 for name, look in sorted(looks.items())}
    out = {"ok": rec is not None, "error": error, "looks": looks_out,
           "sets": found, "missing": missing}
    if rec is None:
        out["sprites"] = {}
        return out
    art = {}
    for kind, spec in rec["kinds"].items():
        look = looks_out.get(_norm(spec.get("look") or kind))
        art[kind] = (look or {}).get("key") or spec.get("cell")
    if world is None:
        world = tilemap_world(mission_root) if mission_root else {"areas": {}}
    usage, areas = {}, []
    for key, area in (world.get("areas") or {}).items():
        if area["tileset"] != rec["name"]:
            continue
        areas.append(key)
        for row in area["tiles"]:
            for kind in row:
                if kind:
                    usage[kind] = usage.get(kind, 0) + 1
    drawn = {k for k in art.values() if k} | {v["key"] for v in looks_out.values() if v["key"]}
    paths = world.get("area_paths") or {}
    out.update({"name": rec["name"], "title": rec["title"], "kinds": rec["kinds"],
                "lines": {k: n - 1 for k, n in rec["lines"].items()},
                "art": art, "usage": usage, "areas": sorted(areas),
                # Where each of those areas is, so renaming a kind can follow it into
                # their legends.
                "areaPaths": {k: os.path.abspath(paths[k]) for k in areas if k in paths},
                "sprites": {k: v for k, v in sprites.items() if k in drawn}})
    return out
