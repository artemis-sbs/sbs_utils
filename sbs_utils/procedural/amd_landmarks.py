"""Declarative object placement ("landmarks") from AMD - author the objects a mission spawns
as data instead of imperative npc_spawn/terrain_spawn loops.

A section authors one heading per object, and ``Prefab:`` says WHAT it is:

    # [Relay Station](relay)
    ---
    Prefab: npc/station/command
    Side: tsn
    Roles: relay
    Loc: 12000, 0, -8000
    Data:
      Race value: terran
    ---

``Prefab:`` names a prefab by its metadata type (``type: prefab/npc/station/command``) or
by exact label name, resolved by ``prefab_resolve``: a mission's MAST prefab first, then a
library DEFAULT. The defaults registered here are the old ``Kind:`` table - ``station``,
``npc``, ``ship``, ``terrain``, ``asteroid``, ``derelict``, ``wreck``, ``nebula`` (each
needs ``Art:``) and ``point`` (a named place; creates nothing). A mission overrides one
by writing a label of that type.

Everything under ``Data:`` is handed to the prefab as its own arguments, so a prefab can
take anything it declares without the landmark reader knowing about it.

Position is resolved most-specific-first, both optional:
  * ``Loc: x, y, z`` - an explicit in-system world position (a single-system mission uses this).
  * ``System: i, j`` - a galaxy cell; when Loc is omitted an injected PLACER derives the
    in-system position (a galaxy mission like Open Universe plugs its deterministic scatter in).
  * both -> the cell's origin plus the Loc offset; neither -> the system origin.
Mission-specific extras on the record (guards, terrain, radius...) stay in the raw fence
(``record.data``) for the caller to read.
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_coords
from sbs_utils.procedural.spawn import npc_spawn, terrain_spawn
from sbs_utils.procedural.prefab import (
    prefab_register, prefab_create, prefab_data, prefab_key_role, prefab_object)
from sbs_utils.mast.mast_node import MastDataObject

# The prefab family landmark keys are tracked under (prefab_key_role("landmark", key)).
LANDMARK_FAMILY = "landmark"

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


def _size(value):
    """`Size: 6000` or `Size: 6000, 2000` -> [x, z] floats, or None."""
    out = []
    for p in str(value).replace(",", " ").split():
        try:
            out.append(float(p))
        except ValueError:
            pass
    if not out:
        return None
    return [out[0], out[1] if len(out) > 1 else out[0]]


def amd_landmark_facts():
    """amd_parse_facts handler for landmark fences: prefab/side/roles/art/behavior (text),
    loc (3 floats), system (2 ints), size (x[, z]). ``Data:`` nests, so it arrives as a
    dict through the default coercion. Unknown labels return None (chain / default)."""
    def handler(data, label, value):
        if label in ("side", "roles", "art", "behavior"):
            data[label] = str(value).strip()
        elif label == "prefab":
            data["prefab"] = str(value).strip().lower()
        elif label == "loc":
            data["loc"] = _coords3(value)
        elif label == "system":
            data["system"] = amd_coords(value)
        elif label == "size":
            data["size"] = _size(value)
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
            args = data.get("data")
            out.append(MastDataObject({
                "key": n.get("key"),
                "name": n.get("display_text"),
                "desc": (n.get("description") or "").strip(),
                "prefab": (data.get("prefab") or "").strip().lower() or None,
                "side": data.get("side"),
                "roles": data.get("roles"),
                "art": data.get("art"),
                "behavior": data.get("behavior"),
                "loc": data.get("loc"),
                "system": data.get("system"),
                "size": data.get("size"),
                "args": args if hasattr(args, "items") else {},
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
    """The role marking the object created for AMD landmark ``key``."""
    return prefab_key_role(LANDMARK_FAMILY, key)


def landmark_object(key):
    """The live object already created for landmark ``key``, or None."""
    obj = prefab_object(LANDMARK_FAMILY, key)
    if isinstance(obj, set):
        from sbs_utils.procedural.query import to_object
        return to_object(next(iter(obj)))
    return obj


def landmark_prefab_data(record):
    """The variables a landmark hands its prefab.

    The standard ones a prefab conventionally reads - ``NAME``/``name``/``display_text``,
    ``START_X/Y/Z`` + ``START_EXACT``, ``SIZE_X/Z``, ``side_value``, ``roles_value``, ``art``, ``behavior`` -
    then ``AMD_RECORD``/``AMD_KEY``, then the ``Data:`` block, which wins over all of
    them. A standard field that was not written is not passed, so the prefab's own
    metadata default stands.
    """
    x, y, z = landmark_pos(record)
    # START_EXACT: a landmark is authored to a POINT. A prefab that scatters inside its
    # SIZE box (LM's stations) honors it and places exactly at START instead.
    data = {"START_X": x, "START_Y": y, "START_Z": z, "START_EXACT": True,
            "AMD_RECORD": record, "AMD_KEY": record.get("key")}
    name = record.get("name")
    if name:
        # Both spellings: LM prefabs read `name`, prefab_spawn's autoname reads `NAME`.
        data["NAME"] = name
        data["name"] = name
        data["display_text"] = name
    for field, var in (("side", "side_value"), ("roles", "roles_value"),
                       ("art", "art"), ("behavior", "behavior")):
        v = record.get(field)
        if v:
            data[var] = v
    size = record.get("size")
    if size:
        data["SIZE_X"], data["SIZE_Z"] = size[0], size[1]
    data.update(prefab_data(record.get("args"), where=f"landmark {record.get('key')}"))
    return data


def landmark_spawn(record):
    """Create one landmark through its ``Prefab:``; returns what it created (None for a
    ``point``, a record with no prefab, or one whose prefab does not resolve - logged).

    Idempotent on the record's ``key``: a landmark already placed is returned as-is, so
    re-running a section (a map body that runs twice, a re-emitted setup signal) does not
    litter the map with duplicates at the same coordinates. Because the check is against
    the live world rather than a did-I-run flag, a landmark that was destroyed or cleared
    IS re-placed - which is what makes a deliberate reset work.
    """
    spec = record.get("prefab")
    key = record.get("key")
    if not spec:
        from sbs_utils.procedural.execution import log
        log(f"landmark '{key}' has no Prefab: - nothing placed. Write Prefab: station, "
            f"derelict, point... or a prefab type.", "landmarks", "warning")
        return None
    return prefab_create(spec, landmark_prefab_data(record), family=LANDMARK_FAMILY,
                         key=key, where=f"landmark {key}")


def landmarks_spawn(section):
    """Spawn every landmark in a section; returns the list of what was created (skips
    points, artless defaults and unresolved prefabs). Convenience over
    landmarks_from_section + landmark_spawn."""
    out = []
    for rec in landmarks_from_section(section):
        obj = landmark_spawn(rec)
        if obj is not None:
            out.append(obj)
    return out


# ---------------------------------------------------------------------------
# Library DEFAULT prefabs: what `Kind:` used to choose between. A mission's MAST label of
# the same type wins over any of these.
# ---------------------------------------------------------------------------

def _role_csv(data):
    """`side, roles` (side first, so npc_spawn reads it as the side); side defaults to `#`
    (no side, for terrain)."""
    side = str(data.get("side_value") or "#").strip()
    roles = str(data.get("roles_value") or "").strip()
    return side + (", " + roles if roles else "")


def _default_spawner(spawn, behavior):
    def create(data):
        art = data.get("art")
        if not art:
            # A bad or missing art key crashes the engine, so a default never guesses one.
            from sbs_utils.procedural.execution import log
            log(f"'{data.get('AMD_KEY') or data.get('NAME')}' needs Art: for this prefab "
                f"- nothing placed", "landmarks", "warning")
            return None
        return spawn(data.get("START_X", 0), data.get("START_Y", 0), data.get("START_Z", 0),
                     data.get("NAME"), _role_csv(data), art,
                     data.get("behavior") or behavior)
    return create


from sbs_utils.procedural.amd_schema import PREFAB_DEFAULTS as _DECLARED

for _type, _spawn, _text in (
        ("station", npc_spawn, "Station"),
        ("npc", npc_spawn, "NPC ship"),
        ("ship", npc_spawn, "NPC ship"),
        ("terrain", terrain_spawn, "Terrain object"),
        ("asteroid", terrain_spawn, "Asteroid"),
        ("derelict", terrain_spawn, "Derelict"),
        ("wreck", terrain_spawn, "Wreck"),
        ("nebula", terrain_spawn, "Nebula")):
    _args = _DECLARED[_type]["args"]
    prefab_register(_type, _default_spawner(_spawn, _args.get("behavior")),
                    args=_args, display_text=_text)

# A named place - a zone a mission reads with landmark_pos, a speaker the document must
# know. Creates nothing, on purpose: a physical buoy would get shot or towed.
prefab_register("point", lambda data: None, args=_DECLARED["point"]["args"],
                display_text="Point (creates nothing)")
