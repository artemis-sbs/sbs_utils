"""Wall KITS: a relic's walls, floors, ceilings and set pieces from an art pack.

`volume_dress` builds a relic out of the game's generic primitives - a grey slab per
wall, asteroids for rock. A kit is the same build pass with real pieces: an art pack
ships OBJ meshes, a ship-data file naming them, and a MANIFEST saying what each piece is
and how big it is::

    ships/ruins_kit.json
    {"version": 1, "pack": "ruins", "ships": "ruins_ships", "units_per_metre": 10,
     "pieces": {"ruins_tg_wall_a": {"kind": "wall", "kit": "torgoth",
                                    "size": [40, 40, 3], "tris": 380}, ...},
     "kits": {"torgoth": {"scale": 8.0, "wall": [...], "floor": [...], "ceiling": [...],
                          "trim": [...], "pillar": [...], "setpieces": [...]}}}

`volume_kit_load("ruins")` reads it and registers each kit as a wall STYLE, so a relic
says ``Walls: torgoth, plates`` and gets the kit when the mission has the pack and plates
when it does not.

THE PACK IS VERIFIED BEFORE ANYTHING IS REGISTERED. A piece of scenery whose art the
engine cannot find spawns fine on the server and then puts a modal assert on the first
client that draws it. A released pack's `artfileroot` carries its release tag, so a pack
unpacked under a different tag, or a mission with `EXTRA_SHIP_DATA` off, is exactly that
case - and the right answer is the fallback style, loudly logged, never a half-registered
kit. `volume_kit_load` must run before any client connects (at a mission's top level),
because that is when ship data has to reach the engine.

Piece frames (what the manifest's `size` means): a SURFACE piece - wall, floor, ceiling,
trim - is a slab, thin in local Z, its finished face toward +Z and the "up" of its
pattern toward +Y. A pillar runs along +Y. A set piece stands upright on +Y facing +Z.
`size` is the world extent at scale 1, in those axes.
"""
import json
import os

from .execution import log

_KITS = {}        # kit name -> {"scale", "wall", "floor", ...}
_PIECES = {}      # art key -> {"kind", "kit", "size": (x, y, z), "tris"}
_PACKS = {}       # pack name -> {"folder", "kits": [...]}

#: Piece lists a kit may carry. A surface kind with no list borrows `wall`.
KIT_KINDS = ("wall", "floor", "ceiling", "trim", "pillar", "setpieces", "finds", "solid")


def _debug(message):
    """log() has no handler in the engine; DEBUG reaches debug.log there. Both, because
    a kit that silently did not load looks exactly like a relic dressed in plates."""
    log(message, "volume_kit", "warning")
    try:
        from ..mast.mast import DEBUG
        DEBUG(message)
    except Exception:                                    # noqa: BLE001
        pass


def _manifest_path(name, path=None):
    """Where `ships/<name>_kit.json` is: an explicit folder, else the mission's media,
    else a pinned pack - the order `media_shared` already searches."""
    rel = f"ships/{name}_kit.json"
    if path is not None:
        full = os.path.join(path, f"{name}_kit.json")
        return full if os.path.exists(full) else None
    try:
        from .media_paths import media_shared, media_shared_exists
        from ..fs import get_mission_dir_filename
        if not media_shared_exists(rel):
            return None
        full = get_mission_dir_filename(media_shared(rel))
        return full if os.path.exists(full) else None
    except Exception as e:                               # noqa: BLE001
        _debug(f"kit '{name}': could not look for {rel}: {e}")
        return None


def volume_kit_load(name, path=None, ships=True):
    """Load an art pack's kits. Returns the kit names registered - [] when nothing was.

    `name` is the pack (`"ruins"`); `path` an explicit folder holding its manifest, for a
    tool or a test. `ships=False` skips telling the engine about the art - only for a
    caller that already did, or a test with no engine.

    Idempotent: loading a pack twice registers it once.
    """
    if name in _PACKS:
        return list(_PACKS[name]["kits"])
    full = _manifest_path(name, path)
    if full is None:
        _debug(f"kit pack '{name}': no ships/{name}_kit.json in the mission or any pinned "
               f"pack - relics asking for its kits use their fallback style")
        return []
    try:
        with open(full, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:                               # noqa: BLE001
        _debug(f"kit pack '{name}': {full} is not readable JSON: {e}")
        return []
    folder = os.path.dirname(full)
    if ships and not _kit_ships(name, manifest, folder):
        return []
    kits = volume_kit_register(manifest)
    _PACKS[name] = {"folder": folder, "kits": kits}
    return list(kits)


def _kit_ships(name, manifest, folder):
    """Tell the engine about the pack's art - only if every piece's art is really there."""
    stem = str(manifest.get("ships") or f"{name}_ships")
    text = None
    for ext in (".json", ".yaml"):
        cand = os.path.join(folder, stem + ext)
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as f:
                text = f.read()
            break
    if text is None:
        _debug(f"kit pack '{name}': its ship data '{stem}' is not beside the manifest")
        return False
    from .ship_data import _art_that_is_not_there, add_extra, extra_ship_data_enabled
    if not extra_ship_data_enabled():
        _debug(f"kit pack '{name}': EXTRA_SHIP_DATA is off, so its art cannot reach the "
               f"engine - relics use their fallback style. Set EXTRA_SHIP_DATA: true.")
        return False
    missing = _art_that_is_not_there(text)
    if missing:
        key, root = missing[0]
        _debug(f"kit pack '{name}': {len(missing)} piece(s) name art that is not there, "
               f"e.g. '{key}' -> '{root}'. NOT loaded - it would assert on the first "
               f"client to draw it. A pack unpacked under another release tag does this.")
        return False
    if not add_extra(f"ships/{stem}"):
        _debug(f"kit pack '{name}': the engine was not told about '{stem}'")
        return False
    return True


def volume_kit_register(manifest):
    """Register a manifest's pieces and kits (already-loaded art). Returns kit names.

    The half of `volume_kit_load` that needs no files - what a test, or a mission that
    builds its own manifest, calls.
    """
    from .volume_dress import volume_style_add_kit
    for key, piece in (manifest.get("pieces") or {}).items():
        size = piece.get("size") or (100.0, 100.0, 1.0)
        _PIECES[str(key)] = {"kind": str(piece.get("kind") or ""),
                             "kit": piece.get("kit"),
                             "size": (float(size[0]), float(size[1]), float(size[2])),
                             "tris": piece.get("tris")}
    out = []
    for kit, spec in (manifest.get("kits") or {}).items():
        rec = {"scale": float(spec.get("scale") or 1.0)}
        for kind in KIT_KINDS:
            rec[kind] = tuple(k for k in (spec.get(kind) or ()) if str(k) in _PIECES)
        if not rec["wall"]:
            _debug(f"kit '{kit}' has no wall pieces - not registered")
            continue
        _KITS[str(kit).lower()] = rec
        volume_style_add_kit(str(kit).lower())
        out.append(str(kit).lower())
    return out


def volume_kit(name):
    """A registered kit's record, or None."""
    return _KITS.get(str(name or "").strip().lower())


def volume_kit_names():
    """Every registered kit."""
    return tuple(sorted(_KITS))


def volume_kit_pieces(kit, kind):
    """The piece keys a kit has for one kind - a surface kind with none borrows `wall`."""
    rec = volume_kit(kit)
    if rec is None:
        return ()
    got = rec.get(kind) or ()
    if not got and kind in ("floor", "ceiling"):
        got = rec.get("wall") or ()
    return got


def volume_kit_piece(key):
    """A piece's record - kind, kit, size - or None for a key no kit knows."""
    return _PIECES.get(str(key))


def volume_kit_size(key, default=None):
    """A piece's world size at scale 1, `(x, y, z)`, or `default`."""
    rec = _PIECES.get(str(key))
    return rec["size"] if rec is not None else default


def volume_kits_clear():
    """Forget every kit - the per-mission reset. The styles they added go too."""
    from .volume_dress import volume_style_remove_kits
    volume_style_remove_kits(tuple(_KITS))
    _KITS.clear()
    _PIECES.clear()
    _PACKS.clear()


def volume_kits_count():
    """Reset-ledger probe. Must not create anything by asking."""
    return len(_KITS) + len(_PACKS)
