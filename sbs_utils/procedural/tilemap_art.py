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
        "away:crate":    {"sheet": "chars", "rect": [128, 0, 256, 128]},
        "away:taxi":     {"sheet": "chars", "rect": [256, 0, 640, 256],
                          "cells": [3, 2], "base": [-1.6, -0.55, 1.6, 0.55]}
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
  ``base`` is the GROUND the thing stands on, ``[left, top, right, bottom]`` in tiles
  from the centre of its cell (x east, y south): a blocking prop blocks every cell it
  covers, and a click on any of them is a click on it (``tilemap_sprite_cells``).
  ``cells`` cannot say this - it is the picture, height and shadow included.
- ``ground`` gives a tileset kind its LOOK - never whether it can be walked or seen
  through, which are the mission's rules, not art.

A sprite with facings and a walk just has more keys: ``<base>_<n|e|s|w>_<idle|a|b>`` and
``<base>_down`` (see ``tilemap_sprite_look``). A set that lacks some of them falls back
key by key.

MIRRORING. The engine draws a cell backwards when its rect runs backwards (the
``flip_probe`` mission measured it), so:

- a figure that has its EAST looks but not its WEST ones (or the reverse) gets them
  mirrored - a set only needs to draw one side;
- ``"mirror": true`` on a sprite registers a mirrored twin, ``<key>_mirror``, and a prop that
  stands still uses the twin on about half the cells, so a wood of one tree repeats less.
  Never on anything with lettering or a handed shape.

A mirrored look is lit from the other side: its baked shadow falls the other way.

SETS OVERLAY. ``tilemap_art_use("builtin", "synty")`` loads the mission's own set first,
then the pack's; a later set wins key by key, so a pack that only redraws the people is a
valid pack. A set is found through ``media_shared`` - this mission's ``media/`` first, then
every ``shared_media`` pack in ``story.json`` - and one that is not found is reported once
and skipped: the mission keeps drawing with what it has.
"""
import json
import math
import os
import re

_SIZES = {}          # atlas key -> (w cells, h cells, anchor x, anchor y)
_BASES = {}          # atlas key -> (l, t, r, b) ground, in tiles from its cell's centre
_COVER = {}          # atlas key -> the (dx, dy) cells that ground covers (derived)
_ORIGIN = {}         # atlas key -> the set that supplied it
_LOADED = []         # set names, in load order
_WARNED = set()
_REGISTERED = set()  # atlas keys this module put in ImageAtlas.all, so clear can take them out
_MIRRORED = {}       # atlas key -> the key it mirrors: derived here, never drawn by a set

#: A facing look: `<base>_e`, `<base>_w_idle`...
_FACING = re.compile(r"^(?P<base>.+)_(?P<f>[ew])(?P<frame>_(?:idle|a|b))?$")

DEFAULT_FOOTPRINT = (1.0, 1.0, 0.5, 1.0)
ONE_CELL = frozenset({(0, 0)})
#: A cell is covered when a base holds its centre by more than this: the thing covers
#: MORE than half of the cell, each way. So a bunk two tiles long, centred on its cell,
#: reaches exactly to its neighbours' centres and covers its own cell only.
COVER_MARGIN = 0.05


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


def tilemap_sprite_base(key, rect=None):
    """Say how much GROUND a sprite stands on, so a big prop blocks all of it.

    Args:
        key (str): the atlas key.
        rect: ``(left, top, right, bottom)`` in tiles, from the centre of the actor's cell
            (x east, y south). A parked car three tiles long, nose east, is about
            ``(-1.6, -0.55, 1.6, 0.55)``. ``None`` forgets it: one cell, the old way.
    """
    _COVER.pop(key, None)
    if rect is None:
        _BASES.pop(key, None)
        return
    l, t, r, b = (float(v) for v in rect)
    _BASES[key] = (min(l, r), min(t, b), max(l, r), max(t, b))


def tilemap_sprite_cells(key):
    """The cells a sprite covers, as ``(dx, dy)`` offsets from its actor's own cell.

    Always holds ``(0, 0)``; a sprite with no ``base`` covers just that. Every other
    cell is covered when more than half of it is under the base, each way."""
    got = _COVER.get(key)
    if got is not None:
        return got
    base = _BASES.get(key)
    if base is None:
        return ONE_CELL
    l, t, r, b = base
    m = COVER_MARGIN

    def span(lo, hi):
        inside = [d for d in range(math.floor(lo), math.ceil(hi) + 1) if lo + m < d < hi - m]
        return range(min(inside + [0]), max(inside + [0]) + 1)

    got = frozenset((dx, dy) for dx in span(l, r) for dy in span(t, b))
    _COVER[key] = got
    return got


# --- mirroring ----------------------------------------------------------------------

def tilemap_art_mirror(key, as_key, origin=None):
    """Register ``as_key`` as ``key`` mirrored left to right: the picture, the point that
    stands on the cell, and the ground it covers all flipped. False when ``key`` is not
    a registered atlas key."""
    from .gui.image import gui_image_mirror
    if gui_image_mirror(key, as_key) is None:
        return False
    w, h, ax, ay = tilemap_sprite_footprint(key)
    tilemap_sprite_size(as_key, w, h, (1.0 - ax, ay))
    base = _BASES.get(key)
    tilemap_sprite_base(as_key, (-base[2], base[1], -base[0], base[3]) if base else None)
    _ORIGIN[as_key] = f"{origin or _ORIGIN.get(key) or 'art'} (mirrored)"
    _REGISTERED.add(as_key)
    _MIRRORED[as_key] = key
    return True


def tilemap_sprite_twin(key):
    """The mirrored twin a still prop may be drawn with (``"mirror": true``), or None."""
    twin = f"{key}_mirror"
    return twin if _MIRRORED.get(twin) == key else None


def _forget(key):
    from .gui.image import ImageAtlas
    ImageAtlas.all.pop(key, None)
    for table in (_SIZES, _BASES, _COVER, _ORIGIN, _MIRRORED):
        table.pop(key, None)
    _REGISTERED.discard(key)


def _fill_facings():
    """Give a figure the side it lacks: its east looks mirrored for west, or the
    reverse. Only a figure - something with south or north looks too - and never over a
    look a set or the mission drew. A look derived before is derived again, so it
    follows whatever set now draws the side it comes from."""
    from .gui.image import ImageAtlas
    have = ImageAtlas.all
    made = 0
    for key in sorted(k for k in _REGISTERED if k not in _MIRRORED):
        m = _FACING.match(key)
        if not m:
            continue
        base, side, frame = m.group("base"), m.group("f"), m.group("frame") or ""
        if not any(f"{base}_{f}{g}" in have for f in "sn" for g in (frame, "", "_idle")):
            continue
        twin = f"{base}_{'w' if side == 'e' else 'e'}{frame}"
        if twin in have and twin not in _MIRRORED:
            continue
        if tilemap_art_mirror(key, twin):
            made += 1
    return made


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
        # A later set's look for the key brings its own ground, or none.
        base = spec.get("base")
        tilemap_sprite_base(key, base if base and len(base) == 4 else None)
        _ORIGIN[key] = name
        _REGISTERED.add(key)
        # A set drew it, so it is no longer derived; and a twin made from the picture
        # this one replaces goes with it.
        _MIRRORED.pop(key, None)
        twin = f"{key}_mirror"
        if _MIRRORED.get(twin) == key:
            _forget(twin)
        if spec.get("mirror"):
            tilemap_art_mirror(key, twin, origin=name)
        keys.append(key)
    _fill_facings()
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
    for field in ("edges", "shade", "tall", "color", "grid", "fringe", "over"):
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
    _BASES.clear()
    _COVER.clear()
    _MIRRORED.clear()
    _ORIGIN.clear()
    _LOADED.clear()
    _WARNED.clear()


def tilemap_art_count():
    """For the reset ledger."""
    return len(_SIZES) + len(_BASES) + len(_MIRRORED) + len(_LOADED)
