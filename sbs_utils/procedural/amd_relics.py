"""Declarative relic interiors from AMD - a structure a ship flies INSIDE, authored as
data instead of a YAML string buried in a Python file.

A relic is a navigable VOLUME (``procedural/volume.py``): chambers are spheres, passages
are capsules, boxes are rectangles, solids are subtracted. Containment is script-side, so
the engine's collision system - one keep-out sphere per object - is never involved.

A section authors the relic and its parts as FLAT SIBLINGS, the same shape a cutscene bed
and its shots use::

    ## [Relics](relics)

    ### [The Ossuary](ossuary)
    ---
    Loc: 12000, 0, -8000
    Atmosphere: purple
    Containment: tractor
    Margin: 60
    ---

    ### [hub](ossuary_hub)
    ---
    Relic: ossuary
    Chamber: 0, 0, 0, 900
    ---

    ### [gallery](ossuary_gallery)
    ---
    Relic: ossuary
    Chamber: 3000, 0, 0, 700
    Passage to: hub 300
    ---

**A record carrying ``Relic:`` is a PART; one carrying neither is the relic itself.**
Which kind of part follows from the field it carries - ``Chamber:``, ``Box:`` or
``Solid:``. This is the bed/shot discriminator, and it is why relics and their parts share
ONE archetype: a section resolves to a single archetype, so splitting them would leave
half of every relic file untyped and lint calling its fields unknown.

Chamber coordinates are **relative to the relic's ``Loc:``**, which is what lets one
authored layout be dropped at two places in a system.

Parts are records rather than a nested fence on purpose. AMD does support nesting inside
one fence, but inner names are unschema'd and unlinted by design - and a record gets a
key, a heading and a source span, which is what an editor needs to write one chamber back.
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_coords
from sbs_utils.procedural.volume import (
    volume_define, volume_get, volume_watch, HOLD_TRACTOR, HOLD_CLAMP, HOLD_NONE,
)
from sbs_utils.mast.mast_node import MastDataObject

# Declared relic records by key, so a relic can be BUILT later on a story cue rather than
# only in the bulk pass at map setup. Per-mission, so it is on the reset ledger.
_RELIC_RECORDS = {}

_HOLDS = {"tractor": HOLD_TRACTOR, "clamp": HOLD_CLAMP, "none": HOLD_NONE}


def _amd_relic_numbers(value):
    """Every number in a value, comma or space separated. Non-numeric words are skipped,
    so `hub 300` yields [300.0] and the word survives for the caller to read."""
    out = []
    for part in str(value).replace(",", " ").split():
        try:
            out.append(float(part))
        except ValueError:
            pass
    return out


def _amd_relic_words(value):
    """Every non-numeric word in a value - the names in `hub 300, gallery 240`."""
    out = []
    for part in str(value).replace(",", " ").split():
        try:
            float(part)
        except ValueError:
            out.append(part)
    return out


def _amd_relic_pairs(value):
    """`hub 300, gallery 240` -> [("hub", 300.0), ("gallery", 240.0)].

    Comma-separated groups, each a name plus a radius. A group with no radius yields
    None for it, so the caller can fall back to a default rather than guess here.
    """
    out = []
    for group in str(value).split(","):
        words = _amd_relic_words(group)
        nums = _amd_relic_numbers(group)
        if not words:
            continue
        out.append((words[0], nums[0] if nums else None))
    return out


def amd_relic_facts():
    """``amd_parse_facts`` handler for relic fences.

    Unknown labels return None so they chain to the field registry and then to the
    default coercion - the same contract ``amd_landmark_facts`` follows.
    """
    def handler(data, label, value):
        if label in ("relic", "atmosphere", "containment", "art", "speed limit",
                     "speed_limit"):
            data[label.replace(" ", "_")] = str(value).strip()
        elif label == "loc":
            nums = _amd_relic_numbers(value)
            data["loc"] = nums[:3] if len(nums) >= 3 else None
        elif label == "system":
            data["system"] = amd_coords(value)
        elif label == "chamber":
            nums = _amd_relic_numbers(value)
            data["chamber"] = nums[:4] if len(nums) >= 4 else None
        elif label == "box":
            nums = _amd_relic_numbers(value)
            data["box"] = nums[:6] if len(nums) >= 6 else None
        elif label == "solid":
            words = _amd_relic_words(value)
            data["solid"] = ([words[0].lower()] if words else ["sphere"]) + \
                _amd_relic_numbers(value)
        elif label in ("passage to", "passage_to"):
            data["passage_to"] = _amd_relic_pairs(value)
        elif label in ("scrape band", "scrape_band", "margin", "seed"):
            nums = _amd_relic_numbers(value)
            data[label.replace(" ", "_")] = nums[0] if nums else None
        elif label in ("forbid jump", "forbid_jump"):
            data["forbid_jump"] = str(value).strip().lower() in (
                "yes", "true", "on", "1")
        else:
            return None
        return True
    return handler


def amd_relic_data(text):
    """Parse one relic fence into a data dict."""
    return amd_parse_facts(text, amd_relic_facts())


def relics_from_section(section):
    """Relic records from a section node's children, each with its parts attached.

    Grouping mirrors the cutscene reader: a record naming a relic is a part of it,
    collected in DOCUMENT ORDER; a record naming none is the relic itself.
    """
    relics = {}
    order = []
    parts = []
    if section is None:
        return []
    for n in section.get("children", []):
        data = n.get("data") or {}
        key = n.get("key")
        owner = (data.get("relic") or "").strip()
        if owner:
            parts.append((owner, n, data))
            continue
        relics[key] = MastDataObject({
            "key": key,
            "name": n.get("display_text"),
            "desc": (n.get("description") or "").strip(),
            "loc": data.get("loc"),
            "system": data.get("system"),
            "atmosphere": data.get("atmosphere"),
            "containment": (data.get("containment") or "tractor").strip().lower(),
            "scrape_band": data.get("scrape_band"),
            "margin": data.get("margin"),
            "speed_limit": data.get("speed_limit"),
            "forbid_jump": bool(data.get("forbid_jump")),
            "art": data.get("art"),
            "seed": data.get("seed"),
            "chambers": {},
            "passages": [],
            "boxes": {},
            "solids": [],
            "parts": [],
            "data": data,   # carry the raw fence for mission-specific extras
        })
        order.append(key)
    for owner, node, data in parts:
        rec = relics.get(owner)
        if rec is None:                     # dangling - lint reports it; skip quietly
            continue
        name = node.get("key") or node.get("display_text")
        rec.parts.append(node)
        if data.get("chamber"):
            c = data["chamber"]
            rec.chambers[name] = [c[0], c[1], c[2], c[3]]
        if data.get("box"):
            b = data["box"]
            rec.boxes[name] = [b[0], b[1], b[2], b[3], b[4], b[5]]
        if data.get("solid"):
            rec.solids.append(data["solid"])
        for other, radius in (data.get("passage_to") or []):
            rec.passages.append([name, other, radius if radius else 200.0])
    return [relics[k] for k in order]


def relics_register(section):
    """Remember every relic record in ``section`` by key, without building any.

    Separate from ``relics_build`` for the same reason landmarks are: a mission builds
    most of its relics at setup, but a story beat reveals one on cue, and both need the
    same record.
    """
    out = relics_from_section(section)
    for rec in out:
        _RELIC_RECORDS[rec.get("key")] = rec
    return out


def relic_record(key):
    """The registered record for ``key``, or None."""
    return _RELIC_RECORDS.get(key)


def relic_keys():
    """Every registered relic key."""
    return list(_RELIC_RECORDS.keys())


def relic_pos(record):
    """A relic's world [x, y, z] - its ``Loc:``, else the origin.

    Deliberately simpler than ``landmark_pos``: relics have no galaxy placer, because
    the landmark one has never been used by a shipped mission (Open Universe rolls its
    own). If a galaxy mission needs one, add it the way landmarks did rather than
    assuming this hook exists.
    """
    loc = record.get("loc")
    return [float(loc[0]), float(loc[1]), float(loc[2])] if loc else [0.0, 0.0, 0.0]


def relic_volume(record, name=None):
    """Build the navigable volume for a record and return it.

    The layout is authored RELATIVE to the relic's Loc, so the record's position becomes
    the volume's origin - which is what lets the same layout be placed twice.
    """
    key = name or record.get("key")
    origin = relic_pos(record)
    return volume_define(key,
                         chambers=record.get("chambers"),
                         passages=record.get("passages"),
                         boxes=record.get("boxes"),
                         solids=record.get("solids"),
                         origin=origin)


def relic_contain(record, name=None):
    """Start containment for a built relic, honoring its authored fields.

    Returns the watcher, or None if the volume has not been built yet.
    """
    key = name or record.get("key")
    if volume_get(key) is None:
        return None
    hold = _HOLDS.get(str(record.get("containment") or "tractor").lower(), HOLD_TRACTOR)
    kw = {"hold": hold, "block_jump": bool(record.get("forbid_jump"))}
    if record.get("margin") is not None:
        kw["margin"] = float(record.get("margin"))
    if record.get("scrape_band") is not None:
        kw["scrape_band"] = float(record.get("scrape_band"))
    limit = record.get("speed_limit")
    if limit:
        try:
            kw["speed_limit"] = float(limit)
        except (TypeError, ValueError):
            pass
    return volume_watch(key, **kw)


def relics_clear():
    """Drop every registered relic record. Called by reset_mission_state()."""
    _RELIC_RECORDS.clear()


def relics_count():
    """Number of registered relic records. The reset-ledger probe."""
    return len(_RELIC_RECORDS)
