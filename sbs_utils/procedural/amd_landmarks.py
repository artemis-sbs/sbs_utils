"""Declarative object placement ("landmarks") from AMD - author the objects a mission spawns
as data instead of imperative npc_spawn/terrain_spawn loops.

A section authors one heading per object:

    # [Relay Station](relay)
    ---
    Kind: station
    Side: tsn
    Roles: relay
    Loc: 12000, 0, -8000
    ---

Position is resolved most-specific-first, both optional:
  * ``Loc: x, y, z`` - an explicit in-system world position (a single-system mission uses this).
  * ``System: i, j`` - a galaxy cell; when Loc is omitted an injected PLACER derives the
    in-system position (a galaxy mission like Open Universe plugs its deterministic scatter in).
  * both -> the cell's origin plus the Loc offset; neither -> the system origin.
Spawn is by ``Kind``: station/npc -> npc_spawn, terrain/asteroid/derelict/wreck -> terrain_spawn,
with a per-kind behavior default (override with ``Behavior:``). ``Art:`` is required (an object
with no art is skipped, since a bad art key crashes the engine). ``Side`` + ``Roles`` become the
spawn's role csv (side first). Mission-specific extras on the record (guards, terrain, ...) are
left for the caller to read after spawn.
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_coords
from sbs_utils.procedural.spawn import npc_spawn, terrain_spawn
from sbs_utils.mast.mast_node import MastDataObject

_TERRAIN_KINDS = frozenset({"terrain", "asteroid", "derelict", "wreck", "nebula"})
_KIND_BEHAVIOR = {
    "station": "behav_station", "npc": "behav_npcship", "ship": "behav_npcship",
    "terrain": "behav_asteroid", "asteroid": "behav_asteroid",
    "derelict": "behav_wreck", "wreck": "behav_wreck", "nebula": "behav_nebula",
}

# Optional injected placer: fn(system, record) -> [x, y, z] for a landmark that names a
# System (galaxy cell) but no explicit Loc. A single-system mission never needs one.
_PLACER = None


def _coords3(value):
    """Parse `x, y, z` (comma or space separated) into [x, y, z] floats, or None."""
    out = []
    for p in str(value).replace(",", " ").split():
        try:
            out.append(float(p))
        except ValueError:
            pass
    return out[:3] if len(out) >= 3 else None


def amd_landmark_facts():
    """amd_parse_facts handler for landmark fences: kind/side/roles/art/behavior (text),
    loc (3 floats), system (2 ints). Unknown labels return None (chain / default coercion)."""
    def handler(data, label, value):
        if label in ("kind", "side", "roles", "art", "behavior"):
            data[label] = str(value).strip()
        elif label == "loc":
            data["loc"] = _coords3(value)
        elif label == "system":
            data["system"] = amd_coords(value)
        else:
            return None
        return True
    return handler


def amd_landmark_data(text):
    """Parse one landmark fence into a data dict."""
    return amd_parse_facts(text, amd_landmark_facts())


def landmarks_from_section(section):
    """Landmark records (MastDataObject) from a section node's children (empty if None)."""
    out = []
    if section is not None:
        for n in section.get("children", []):
            data = n.get("data") or {}
            out.append(MastDataObject({
                "key": n.get("key"),
                "name": n.get("display_text"),
                "desc": (n.get("description") or "").strip(),
                "kind": (data.get("kind") or "station").strip().lower(),
                "side": data.get("side"),
                "roles": data.get("roles"),
                "art": data.get("art"),
                "behavior": data.get("behavior"),
                "loc": data.get("loc"),
                "system": data.get("system"),
                "data": data,   # carry the raw fence for mission-specific extras
            }))
    return out


def landmark_set_placer(fn):
    """Set the position placer for landmarks that name a System but no Loc:
    fn(system, record) -> [x, y, z]. A single-system mission needs no placer."""
    global _PLACER
    _PLACER = fn


def landmark_pos(record):
    """Resolve a landmark's world [x, y, z]: explicit Loc; else the injected placer over its
    System (offset by Loc if both); else the origin."""
    loc = record.get("loc")
    system = record.get("system")
    if system is not None and _PLACER is not None:
        base = _PLACER(system, record) or [0.0, 0.0, 0.0]
        if loc:
            return [base[0] + loc[0], base[1] + loc[1], base[2] + loc[2]]
        return base
    if loc:
        return loc
    return [0.0, 0.0, 0.0]


def _role_csv(record):
    """`side, roles` (side first, so npc_spawn reads it as the side); side defaults to `#`
    (no side, for terrain)."""
    side = str(record.get("side") or "#").strip()
    roles = str(record.get("roles") or "").strip()
    return side + (", " + roles if roles else "")


# Declared landmark records by key, so a landmark can be placed LATER by name (an
# `Action:` line - `Kessel Station arrives`) rather than only in the bulk pass at map
# setup. Per-mission, so it is on the reset ledger in handlerhooks.
_RECORDS = {}


def landmarks_register(section):
    """Remember every landmark record in ``section`` by key, without spawning any.

    Separate from ``landmarks_spawn`` on purpose: a mission places most of its landmarks
    at setup, but a story beat places one on cue, and both need the same record.
    """
    for rec in landmarks_from_section(section):
        key = rec.get("key")
        if key:
            _RECORDS[str(key).strip().lower()] = rec
    return len(_RECORDS)


def landmark_record(key):
    """A registered landmark record by key, or None."""
    if not key:
        return None
    return _RECORDS.get(str(key).strip().lower())


def landmarks_registry_clear():
    """Drop the declared-record registry - the per-mission reset."""
    _RECORDS.clear()


def landmark_key_role(key):
    """The role marking the object spawned for AMD landmark ``key``.

    A role, because role sets are the only O(1) keyed lookup and they self-clean when the
    object is deleted, so a landmark that is destroyed can be re-placed by re-running the
    section with no bookkeeping.
    """
    return f"amd_landmark:{str(key).strip()}"


def landmark_object(key):
    """The live object already spawned for landmark ``key``, or None."""
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_id_list, object_exists, to_object
    if not key:
        return None
    for so_id in to_id_list(role(landmark_key_role(key))):
        if object_exists(so_id):
            return to_object(so_id)
    return None


def landmark_spawn(record):
    """Spawn one landmark; returns the spawned object (None if it has no Art, or an unknown
    kind maps to no spawner). Kind picks npc_spawn vs terrain_spawn + a behavior default.

    Idempotent on the record's ``key``: a landmark already placed is returned as-is, so
    re-running a section (a map body that runs twice, a re-emitted setup signal) does not
    litter the map with duplicates at the same coordinates. Because the check is against
    the live world rather than a did-I-run flag, a landmark that was destroyed or cleared
    IS re-placed - which is what makes a deliberate reset work.
    """
    art = record.get("art")
    if not art:
        return None
    key = record.get("key")
    existing = landmark_object(key)
    if existing is not None:
        return existing
    kind = record.get("kind") or "station"
    behavior = record.get("behavior") or _KIND_BEHAVIOR.get(kind, "behav_npcship")
    x, y, z = landmark_pos(record)
    csv = _role_csv(record)
    spawn = terrain_spawn if kind in _TERRAIN_KINDS else npc_spawn
    obj = spawn(x, y, z, record.get("name"), csv, art, behavior)
    if key and obj is not None:
        from sbs_utils.procedural.roles import add_role
        from sbs_utils.procedural.query import to_id
        add_role(to_id(obj), landmark_key_role(key))
    return obj


def landmarks_spawn(section):
    """Spawn every landmark in a section; returns the list of spawned objects (skips artless).
    Convenience over landmarks_from_section + landmark_spawn."""
    out = []
    for rec in landmarks_from_section(section):
        obj = landmark_spawn(rec)
        if obj is not None:
            out.append(obj)
    return out
