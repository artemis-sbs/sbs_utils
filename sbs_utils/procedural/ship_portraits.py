"""Ship portraits: a pre-rendered picture of every hull, from one sheet.

`send_gui_3dship` is a live 3D render per widget, and a listbox or text area with a ship
on every row pays for every one of them. A portrait is a cell of a sheet, drawn as an
image (`send_gui_image` with a `sub_rect`) or as a FACE (`send_gui_face`). That is the
cost of a tile, and as a face it can stand in for a ship's face on comms:

    unknown contact  ->  the hull  ->  its captain

THE SHEET AND ITS MANIFEST are built by `sbs art portraits` (sbs_cli) from the hulls'
OBJ art. A set is `ship_portraits/<set>.json` beside its page PNGs:

    {"format": 1, "set": "base", "alias": "shp_base", "cell": [256, 256], "cols": 16,
     "pages": [{"file": "base_0", "rows": 12}],
     "cells": {"tsn_light_cruiser": {"page": 0, "col": 3, "row": 1, ...}, ...},
     "extras": {"unknown": {"page": 0, "col": 0, "row": 0}}}

WHERE: the base game's set ships in the LIBRARY's media pack and loads itself on first
use. A mod builds its own set into its own media pack and loads it from its addon:

    ship_portrait_load("ship_portraits/tng")     # a LOGICAL path, found in any pack

A mod's set WINS over the base for a hull both have. The base never overrides.

NOTHING HERE MAKES A HULL DISAPPEAR. A hull with no portrait answers None, and every
drawing site (text-area `ship://`, leads) falls back to the live 3D ship - so a stale
sheet costs performance, never a blank.
"""
import os

#: The hull key -> (face alias, col, row, image atlas key, set). Per mission: a mod's
#: aliases exist only while that mod is loaded.
_PORTRAITS = {}
#: Extra cells by name ("unknown") -> (alias, col, row, atlas key).
_EXTRAS = {}
#: The mission the base set was last offered for; keyed, not latched, so a restart into
#: another mission offers it again without a reset.
_base_offered_for = None
#: Hulls already reported as having no portrait (logged once each).
_MISSING_TOLD = set()

#: The image-atlas domain, so a portrait key never collides with an ordinary image name.
SHIP_PORTRAIT_DOMAIN = "ship"

#: Logical media path of the base game's set, in the library's own pack.
SHIP_PORTRAIT_BASE = "ship_portraits/base"


def ship_portrait_load(manifest, replace=True):
    """Register a portrait set: every page as a face sheet and every cell as an image.

    Args:
        manifest (str): the set's path WITHOUT `.json` - normally
            the LOGICAL path `"ship_portraits/<set>"` (searched in every media root),
            or a path relative to the mission, or absolute.
        replace (bool): whether this set's cells replace a hull another set already
            gave. True for a mod (its art wins); the base set loads with False.

    Returns:
        int: how many hull portraits this set registered. 0 when the manifest is
        missing or unreadable - logged, never raised.
    """
    import json
    from ..fs import get_mission_dir
    from ..faces import face_register_sheet
    from .gui.image import gui_image_add_atlas_grid

    stem = str(manifest)
    if stem.lower().endswith(".json"):
        stem = stem[:-5]
    full = stem if os.path.isabs(stem) else os.path.join(get_mission_dir(), stem)
    if not os.path.isfile(full + ".json") and not os.path.isabs(stem):
        # A LOGICAL path. media_shared() probes for a .png or a folder, so it cannot see
        # a manifest and hands back the mission-local fallback (`media/<path>`) - which is
        # what `media_shared("ship_portraits/tng")` returns in every mission but the
        # mod's own. Search the media roots for the manifest itself instead.
        rel = stem.replace("\\", "/")
        if rel.startswith("media/"):
            rel = rel[len("media/"):]
        found = _find_manifest(rel)
        if found is not None:
            stem = full = found
    try:
        with open(full + ".json", "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception as e:                                   # noqa: BLE001
        _say(f"ship portraits: cannot read {stem}.json ({type(e).__name__}: {e}); "
             f"hulls from that set draw as live 3D ships")
        return 0

    folder = os.path.dirname(stem)
    cell = data.get("cell") or [256, 256]
    if not isinstance(cell, (list, tuple)):
        cell = [cell, cell]
    cw, ch = int(cell[0]), int(cell[1])
    cols = int(data.get("cols") or 16)
    alias = str(data.get("alias") or ("shp_" + str(data.get("set") or "set")))
    pages = data.get("pages") or []

    page_alias = []
    for n, page in enumerate(pages):
        name = f"{alias}{n}"
        image = (folder + "/" if folder else "") + str(page.get("file"))
        face_register_sheet(name, cols, int(page.get("rows") or 1), filename=image,
                            cell_w=cw, cell_h=ch)
        page_alias.append((name, image))

    def _place(where, into, domain):
        """Register `{key: {page,col,row}}` as images in `domain` and record them in
        `into`. A key `into` already holds is skipped unless `replace` - and skipped
        BEFORE its image is registered, or the base would re-point a mod's atlas cell."""
        by_page = {}
        for key, at in where.items():
            if not replace and key in into:
                continue
            try:
                p = int(at.get("page", 0))
                by_page.setdefault(p, {})[key] = (int(at["col"]), int(at["row"]))
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
        placed = 0
        for p, cells in by_page.items():
            if p >= len(page_alias):
                continue
            alias_p, image = page_alias[p]
            gui_image_add_atlas_grid(image, cols, None, cells, (cw, ch), None, domain)
            for key, (c, r) in cells.items():
                into[key] = (alias_p, c, r)
                placed += 1
        return placed

    count = _place(data.get("cells") or {}, _PORTRAITS, SHIP_PORTRAIT_DOMAIN)
    # Extras ("unknown") in their own domain, so a hull that happens to be keyed
    # `unknown` cannot be confused with the generic contact.
    _place(data.get("extras") or {}, _EXTRAS, SHIP_PORTRAIT_DOMAIN + ".extra")
    return count


def _find_manifest(rel):
    """The first media root holding `<rel>.json`, as an absolute stem, or None."""
    try:
        from .media_paths import media_roots
        roots = media_roots()
    except Exception:                                        # noqa: BLE001
        return None
    for root in roots:
        stem = os.path.join(root, *rel.split("/"))
        if os.path.isfile(stem + ".json"):
            return stem
    return None


def _ensure_base():
    """Offer the base game's set once per mission, never over a mod's cells."""
    global _base_offered_for
    try:
        from .media_paths import media_roots, _mission_dir
        mission = _mission_dir()
        roots = media_roots()
    except Exception:                                        # noqa: BLE001
        return
    if _base_offered_for == mission:
        return
    _base_offered_for = mission
    # Searched here rather than with media_shared(), which probes for a .png or a folder
    # and so cannot see a manifest. Nearest root first, as media_shared would.
    rel = SHIP_PORTRAIT_BASE.split("/")
    for root in roots:
        stem = os.path.join(root, *rel)
        if os.path.isfile(stem + ".json"):
            ship_portrait_load(stem, replace=False)
            return


def _hull_key(ship):
    """A ship-data key from a key, an id, or a space object."""
    if ship is None:
        return None
    if isinstance(ship, str):
        return ship
    try:
        from .query import to_object
        obj = to_object(ship)
        return obj.art_id if obj is not None else None
    except Exception:                                        # noqa: BLE001
        return None


def _lookup(ship):
    key = _hull_key(ship)
    if not key:
        return None, None
    hit = _PORTRAITS.get(key)
    if hit is None:
        _ensure_base()
        hit = _PORTRAITS.get(key)
    return key, hit


def ship_portrait_has(ship):
    """Whether a hull has a portrait. `ship` is a ship-data key, an id or an object."""
    return _lookup(ship)[1] is not None


def ship_portrait_face(ship, color="#fff"):
    """The hull's portrait as a FACE string (`"shp_base0 #fff 3 1;"`), or None.

    A face string, so it goes anywhere a face does - comms, a `face://` embed, a crew
    card - and can be layered with `face_overlay`.
    """
    key, hit = _lookup(ship)
    if hit is None:
        _tell_missing(key)
        return None
    alias, col, row = hit
    return f"{alias} {color} {col} {row};"


def ship_portrait_image(ship):
    """The image-atlas key of the hull's portrait (draw with `gui_image`), or None."""
    from .gui.image import ImageAtlas
    key, hit = _lookup(ship)
    if hit is None:
        _tell_missing(key)
        return None
    atlas = ImageAtlas.qualify(key, SHIP_PORTRAIT_DOMAIN)
    return atlas if atlas in ImageAtlas.all else None


def ship_portrait_props(ship, color=None, layer=None):
    """The `send_gui_image` property string for the hull's portrait, or None."""
    from .gui.image import ImageAtlas
    atlas = ship_portrait_image(ship)
    return ImageAtlas.all[atlas].get_props(color, layer) if atlas else None


def ship_portrait_unknown_face(color="#fff"):
    """The generic UNKNOWN CONTACT face, or None when no set carries one."""
    _ensure_base()
    hit = _EXTRAS.get("unknown")
    if hit is None:
        return None
    alias, col, row = hit
    return f"{alias} {color} {col} {row};"


def ship_portrait_stage_face(ship, stage="hull", captain=None, color="#fff"):
    """The face to show for a ship at a stage of what the crew knows about it.

    The mission decides the stage (scanned yet? hailed yet?); this only builds the face:

        "unknown"  -> the generic contact (the hull, if there is no unknown cell)
        "hull"     -> the hull's portrait (unknown when there is none)
        "captain"  -> `captain` when given, else the hull

    Returns a face string, or None when nothing at all can be shown.
    """
    stage = str(stage or "hull").lower()
    if stage == "captain" and captain:
        return captain
    if stage == "unknown":
        return ship_portrait_unknown_face(color) or ship_portrait_face(ship, color)
    return ship_portrait_face(ship, color) or ship_portrait_unknown_face(color)


def ship_portrait_keys():
    """Every hull key with a portrait, the base set included."""
    _ensure_base()
    return sorted(_PORTRAITS)


def ship_portrait_clear():
    """Forget every registered set. Called by reset_mission_state()."""
    global _base_offered_for
    _PORTRAITS.clear()
    _EXTRAS.clear()
    _MISSING_TOLD.clear()
    _base_offered_for = None


def ship_portrait_size():
    """Entries held, for the reset ledger."""
    return len(_PORTRAITS) + len(_EXTRAS) + len(_MISSING_TOLD)


def _tell_missing(key):
    if not key or key in _MISSING_TOLD:
        return
    _MISSING_TOLD.add(key)
    _say(f"ship portraits: no portrait for hull '{key}' - drawn as a live 3D ship. "
         f"Rebuild the set with `sbs art portraits`.")


def _say(message):
    try:
        import logging
        logging.getLogger("mast.runtime").info(message)
    except Exception:                                        # noqa: BLE001
        pass
