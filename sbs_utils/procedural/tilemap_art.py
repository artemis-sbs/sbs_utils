"""Art sets for a tile world: which picture each logical key is, swappable per mission.

A mission names LOGICAL keys only - ``away:crew``, ``away:crate``, ``away:dust`` - and an
ART SET says what they look like. So the same mission can be drawn by its own built-in
art, by a media pack of rendered 3D sprites, or by somebody else's pixel art, and
changing between them is a setting, not an edit.

AN ART SET is a folder ``media/tileart/<set>/`` holding its sheets and a
``manifest.json``::

    {
      "sheets": {"chars": "chars.png"},
      "sprites": {
        "away:crew_s_a": {"sheet": "chars", "rect": [0, 0, 128, 192],
                          "cells": [1, 1.5], "anchor": [0.5, 1.0]},
        "away:crate":    {"sheet": "chars", "rect": [128, 0, 256, 128]}
      },
      "ground": {
        "dust": {"cell": "away:dust", "variants": ["away:dust_v2"],
                 "shade": "away:dust_shade"},
        "wall": {"cell": "away:wall", "tall": true, "edges": {"5": "away:wall_ns"}},
        "sand": {"cell": "g:sand_0", "grid": ["g:sand_0", "g:sand_1", "g:sand_2", "g:sand_3"]}
      }
    }

- ``sheets`` are paths RELATIVE TO THE MANIFEST'S FOLDER. A pack's folder name carries
  its version, so nothing in a manifest may spell one.
- ``sprites``: a rect in pixels on a sheet; ``color`` an optional default tint (an
  actor's own color still wins); ``cells`` is the footprint in tiles (a figure
  seen in 3/4 is taller than its cell, a landed ship is several cells wide); ``anchor`` is
  the point of the sprite, as fractions of it, that sits on the bottom-center of the
  actor's cell. Both default to one cell, anchored at the bottom - the old flat tile.
- ``ground`` gives a tileset kind its LOOK - never whether it can be walked or seen
  through, which are the mission's rules, not art.

A sprite with facings and a walk just has more keys: ``<base>_<n|e|s|w>_<idle|a|b>`` and
``<base>_down`` (see ``tilemap_sprite_look``). A set that lacks some of them falls back
key by key.

SETS OVERLAY. ``tilemap_art_use("builtin", "synty")`` loads the mission's own set first,
then the pack's; a later set wins key by key, so a pack that only redraws the people is a
valid pack. A set is found through ``media_shared`` - this mission's ``media/`` first, then
every ``shared_media`` pack in ``story.json`` - and one that is not found is reported once
and skipped: the mission keeps drawing with what it has.
"""
import json
import os

_SIZES = {}          # atlas key -> (w cells, h cells, anchor x, anchor y)
_ORIGIN = {}         # atlas key -> the set that supplied it
_LOADED = []         # set names, in load order
_WARNED = set()
_REGISTERED = set()  # atlas keys this module put in ImageAtlas.all, so clear can take them out

DEFAULT_FOOTPRINT = (1.0, 1.0, 0.5, 1.0)


def _log(text, level="warning"):
    try:
        from .execution import log
        log(text, "tilemap", level)
    except Exception:                                    # noqa: BLE001
        pass
    print(text)


# --- footprints --------------------------------------------------------------------

def tilemap_sprite_size(key, w=1.0, h=1.0, anchor=(0.5, 1.0)):
    """Say how big a sprite is drawn, in tiles, and which point of it stands on the
    actor's cell (fractions of the sprite; the default is its bottom-center)."""
    ax, ay = anchor if anchor is not None else (0.5, 1.0)
    _SIZES[key] = (float(w), float(h), float(ax), float(ay))


def tilemap_sprite_footprint(key):
    """``(w, h, anchor x, anchor y)`` for a sprite - one flat cell unless told."""
    return _SIZES.get(key, DEFAULT_FOOTPRINT)


# --- sets ---------------------------------------------------------------------------

def tilemap_art_sets(default=None):
    """The sets a mission should load, in order: ``builtin`` and then whatever the
    ``TILE_ART`` setting names (a list, or a comma separated string).

    Args:
        default (str | list, optional): what to use when the setting says nothing.
    """
    want = None
    try:
        from .settings import settings_get_defaults
        want = settings_get_defaults().get("TILE_ART")
    except Exception:                                    # noqa: BLE001
        want = None
    if want is None:
        want = default
    if isinstance(want, str):
        want = [w for w in want.replace(";", ",").split(",")]
    names = [str(w).strip() for w in (want or []) if str(w).strip()]
    return ["builtin"] + [n for n in names if n != "builtin"]


def tilemap_art_find(name):
    """The folder of an art set, relative to the mission, or None when no mission
    folder or pinned pack has one."""
    from .media_paths import media_shared, media_shared_exists
    logical = f"tileart/{name}"
    if not media_shared_exists(logical):
        return None
    folder = media_shared(logical)
    from ..fs import get_mission_dir_filename
    if not os.path.exists(os.path.join(get_mission_dir_filename(folder), "manifest.json")):
        return None
    return folder


def tilemap_art_load(manifest, folder, name="set", tileset=None):
    """Register one manifest. ``folder`` is where its sheets are (relative to the
    mission, the way image paths are). Returns the sprite keys it registered."""
    from .gui.image import ImageAtlas
    if isinstance(manifest, str):
        manifest = json.loads(manifest)
    manifest = manifest or {}
    sheets = manifest.get("sheets") or {}
    folder = str(folder).replace("\\", "/").rstrip("/")
    keys = []
    for key, spec in (manifest.get("sprites") or {}).items():
        sheet = sheets.get(spec.get("sheet"), spec.get("sheet"))
        if not sheet:
            _log(f"tile art '{name}': sprite {key} names no sheet")
            continue
        sheet = os.path.splitext(str(sheet))[0]          # the engine adds .png
        rect = spec.get("rect")
        # A sprite may carry its own tint: the builtin art tells two colonists apart
        # that way, where a set with a model per person needs none.
        color = spec.get("color")
        if rect and len(rect) == 4:
            ImageAtlas(key, f"{folder}/{sheet}", *[int(v) for v in rect], color)
        else:
            ImageAtlas(key, f"{folder}/{sheet}", color=color)
        cells = spec.get("cells") or (1, 1)
        tilemap_sprite_size(key, cells[0], cells[1], spec.get("anchor"))
        _ORIGIN[key] = name
        _REGISTERED.add(key)
        keys.append(key)
    if tileset is not None:
        tilemap_art_ground(tileset, manifest.get("ground") or {})
    return keys


def tilemap_art_ground(tileset, ground):
    """Give a tileset's kinds their looks from an art set. Kinds the tileset does not
    have are ignored; whether a kind can be walked or seen through is never touched."""
    from .tilemap import _TILESETS, _norm
    table = _TILESETS.get(_norm(tileset))
    if table is None:
        return 0
    n = 0
    # A kind takes the art named by its own `look` if it has one, else its own name.
    wanted = {}
    for kind, spec in table.items():
        wanted.setdefault(_norm(spec.get("look") or kind), []).append(spec)
    for name, look in (ground or {}).items():
        specs = wanted.get(_norm(name), [])
        if not specs or not isinstance(look, dict):
            continue
        for spec in specs:
            _dress(spec, look)
            n += 1
    return n


def _dress(spec, look):
    """Copy an art set's look onto one tileset kind (never its walk/see rules)."""
    if look.get("cell"):
        spec["cell"] = look["cell"]
        spec["variants"] = [look["cell"]] + list(look.get("variants") or [])
    elif look.get("variants"):
        spec["variants"] = [spec.get("cell")] + list(look["variants"])
    for field in ("edges", "shade", "tall", "color", "grid"):
        if field in look:
            spec[field] = look[field]


def tilemap_art_use(*sets, tileset=None):
    """Load art sets in order, later ones overriding earlier ones key by key.

    Args:
        *sets (str): set names - ``tileart/<name>`` in this mission or a pinned pack.
            With none, ``tilemap_art_sets()``: ``builtin`` plus the ``TILE_ART`` setting.
        tileset (str, optional): the tileset whose kinds the sets' ``ground`` dresses.

    Returns:
        list: the sets that were found and loaded.
    """
    from ..fs import get_mission_dir_filename
    names = list(sets) or tilemap_art_sets()
    loaded = []
    for name in names:
        folder = tilemap_art_find(name)
        if folder is None:
            if name not in _WARNED:
                _WARNED.add(name)
                _log(f"tile art '{name}' not found (no media/tileart/{name}/manifest.json "
                     f"in the mission or a pinned pack) - drawing without it")
            continue
        try:
            with open(os.path.join(get_mission_dir_filename(folder), "manifest.json"),
                      encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:                           # noqa: BLE001
            _log(f"tile art '{name}': cannot read its manifest: {e}")
            continue
        tilemap_art_load(manifest, folder, name, tileset=tileset)
        loaded.append(name)
        if name not in _LOADED:
            _LOADED.append(name)
    return loaded


def tilemap_art_origin(key):
    """Which set supplied a sprite key, or None - for a debug line and for tests."""
    return _ORIGIN.get(key)


def tilemap_art_loaded():
    return list(_LOADED)


def tilemap_art_clear():
    """Forget everything the sets registered - footprints, origins, AND their atlas keys.

    The keys matter: ``ImageAtlas.all`` is process-wide, and a pack's facing frames left
    in it would still be found by ``tilemap_sprite_look`` for the next mission in the
    same interpreter (the dev runner reuses one), even one that never loads the pack."""
    from .gui.image import ImageAtlas
    for key in _REGISTERED:
        ImageAtlas.all.pop(key, None)
    _REGISTERED.clear()
    _SIZES.clear()
    _ORIGIN.clear()
    _LOADED.clear()
    _WARNED.clear()


def tilemap_art_count():
    """For the reset ledger."""
    return len(_SIZES) + len(_LOADED)
