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
from sbs_utils.procedural.amd_doc import amd_section
from sbs_utils.procedural.volume import (
    volume_define, volume_get, volume_watch, volume_watching,
    HOLD_TRACTOR, HOLD_CLAMP, HOLD_NONE,
)
from sbs_utils.procedural.signal import signal_emit
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
        elif label == "point":
            nums = _amd_relic_numbers(value)
            data["point"] = nums[:3] if len(nums) >= 3 else None
        elif label == "roles":
            data["roles"] = [w.strip().lower() for w in str(value).split(",") if w.strip()]
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


def relics_from_section(section, source=None, section_key=None):
    """Relic records from a section node's children, each with its parts attached.

    Grouping mirrors the cutscene reader: a record naming a relic is a part of it,
    collected in DOCUMENT ORDER; a record naming none is the relic itself.

    `source` and `section_key` are carried onto every record so the relic can be REBUILT
    from its file later - see `relic_reload`. They are the reader's own arguments, not
    anything the author writes; without them a record is a snapshot with no way back to
    the text it came from, and a live preview has to be written per mission.
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
            "source": source,          # the .amd this was read from, for relic_reload
            "section": section_key,    # and which section of it
            "volume": None,            # set by relic_volume when the volume is built
            "contained": False,        # set by relic_contain; see relic_reload
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
            "points": {},
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
        if data.get("point"):
            # A place, not a shape: it adds no navigable space and nothing subtracts. What
            # it is FOR is `Roles:` - an entrance, a cache, a spawn - which the mission
            # reads, because the library has no opinion about what gets put there.
            pt = data["point"]
            rec.points[name] = [pt[0], pt[1], pt[2], data.get("roles") or []]
        for other, radius in (data.get("passage_to") or []):
            rec.passages.append([name, other, radius if radius else 200.0])
    return [relics[k] for k in order]


def relics_load(file_path, section_key="relics"):
    """Read relics straight from an `.amd` file. The verb a mission actually wants.

    Without this every mission repeats the same three lines - load the document with the
    relic fence handler wired in, find the section, walk it - and the fence handler is
    the part that is easy to forget. Miss it and every field silently falls through to
    the default coercion, so `Chamber: 0, 0, 0, 900` becomes a string and the relic
    builds as nothing.

    Returns the records; they are registered too, so `relic_record(key)` finds them
    later on a story cue.
    """
    from sbs_utils.procedural.quest import document_get_amd_file
    doc = document_get_amd_file(file_path,
                                data_parser=lambda t: amd_parse_facts(t, amd_relic_facts()))
    return relics_register(amd_section(doc, section_key),
                           source=file_path, section_key=section_key)


def relics_build(file_path, section_key="relics", name=None):
    """Load a file, build the first relic's volume, and return (record, volume).

    The whole declarative path in one call, for the common case of a mission with one
    relic. `name` overrides the volume's name; it defaults to the relic's own key.
    """
    records = relics_load(file_path, section_key)
    if not records:
        return (None, None)
    rec = records[0]
    return (rec, relic_volume(rec, name=name))


def relics_register(section, source=None, section_key=None):
    """Remember every relic record in ``section`` by key, without building any.

    Separate from ``relics_build`` for the same reason landmarks are: a mission builds
    most of its relics at setup, but a story beat reveals one on cue, and both need the
    same record.
    """
    out = relics_from_section(section, source=source, section_key=section_key)
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


def relic_point(relic_key, name):
    """The WORLD position of a named point in a relic, or None.

    Points are authored RELATIVE to the relic's `Loc:`, like every other part, so this
    shifts them - which is the whole reason a point belongs in the relic rather than being
    a landmark of its own. Move the relic and its cache, its entrance and its ambush move
    with it; a landmark's `Loc:` is absolute and would stay behind.

    What goes there is the mission's business::

        item_spawn("relic_core", *relic_point("ossuary", "cache"), qty=2)
        npc_spawn(*relic_point("ossuary", "picket"), "Sentry", "raider", ...)
        marker_point(*relic_point("ossuary", "mouth"), "The Ossuary")
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return None
    pt = (rec.get("points") or {}).get(name)
    if pt is None:
        return None
    base = relic_pos(rec)
    return (base[0] + pt[0], base[1] + pt[1], base[2] + pt[2])


def relic_points(relic_key, role=None):
    """Every point in a relic as `{name: (x, y, z)}` in world coordinates.

    `role` narrows to one purpose - `relic_points("ossuary", "spawn")` for every place an
    NPC may appear, `"entrance"` for the ways in. Roles are matched lowercased, the way
    they are authored.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return {}
    want = None if role is None else str(role).strip().lower()
    base = relic_pos(rec)
    out = {}
    for name, pt in (rec.get("points") or {}).items():
        if want is not None and want not in (pt[3] or []):
            continue
        out[name] = (base[0] + pt[0], base[1] + pt[1], base[2] + pt[2])
    return out


def relic_point_roles(relic_key, name):
    """The roles authored on one point, lowercased. Empty when it has none."""
    rec = _RELIC_RECORDS.get(relic_key)
    pt = (rec.get("points") or {}).get(name) if rec is not None else None
    return list(pt[3]) if pt else []


def relic_volume(record, name=None):
    """Build the navigable volume for a record and return it.

    The layout is authored RELATIVE to the relic's Loc, so the record's position becomes
    the volume's origin - which is what lets the same layout be placed twice.
    """
    key = name or record.get("key")
    origin = relic_pos(record)
    vol = volume_define(key,
                        chambers=record.get("chambers"),
                        passages=record.get("passages"),
                        boxes=record.get("boxes"),
                        solids=record.get("solids"),
                        origin=origin)
    # Remember WHICH volume this record built. A mission may name it something other than
    # the record's key, and when it does, everything keyed on the record key - reload,
    # and `relic_contain` - silently finds nothing.
    setattr(record, "volume", key)
    return vol


def relic_volume_name(record, name=None):
    """Which volume a record's geometry lives in: an explicit name, else the one the
    record actually BUILT, else its key.

    The middle term is the one that matters. A mission is free to build a relic under a
    name of its own (`relics_build(..., name="relic")`), and when it does, anything that
    guesses the record's key instead - containment, reload - silently addresses a volume
    that does not exist and does nothing at all. That is not hypothetical: it is why the
    Ossuary's authored `Scrape band: 120` never once reached its watcher.
    """
    return name or record.get("volume") or record.get("key")


def relic_contain(record, name=None):
    """Start containment for a built relic, honoring its authored fields.

    Returns the watcher, or None if the volume has not been built yet.
    """
    key = relic_volume_name(record, name)
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
    # Mark the watch as OURS. A reload re-applies the authored fields only for a watch
    # this function installed - see relic_reload.
    setattr(record, "contained", True)
    return volume_watch(key, **kw)


def relic_reload(key):
    """Re-read one relic's `.amd` and rebuild its volume in place. Returns a summary dict.

    THE POINT: this is what a live preview needs, and until now every mission had to write
    it. The editor's Preview button can only ring a doorbell over the debug channel; the
    rebuild has to happen inside the running mission, so it belongs here rather than in
    the tool. See `cosmos_dev.mission_runner`'s `relic_reload` debug action, which calls
    this and needs no mission code at all.

    Geometry only. The props a mission scatters over the walls are its own art, and this
    cannot know what they are - so it emits `relic_rebuilt` afterwards and a mission that
    draws walls re-dresses on that signal.

    Rebuilds UNDER THE SAME VOLUME NAME, so a watcher, a brain, or a stored id that
    addresses the relic keeps addressing it. Containment is re-applied from the AUTHORED
    fields (`relic_contain`), so an edit to `Margin:` or `Containment:` takes effect on
    the same Preview as an edit to a chamber - which is the whole promise of authoring it
    declaratively.

    Returns `{"key", "volume", "source", "chambers", "passages", "boxes", "solids"}`, or
    `None` if the key is unknown or the record has no source (built in code, not read
    from a file - there is nothing to re-read).
    """
    rec = _RELIC_RECORDS.get(key)
    if rec is None:
        return None
    source = rec.get("source")
    if not source:
        return None
    # Re-read under the name the OLD record built, before it is replaced: a fresh read
    # only knows the key the author wrote, and the mission may have built it as something
    # else. Losing this is how a reload quietly builds a second volume beside the live one.
    volume = relic_volume_name(rec)
    section_key = rec.get("section") or "relics"
    # Was this volume's watch installed from the AUTHORED fields, by relic_contain?
    ours = bool(rec.get("contained")) and volume_watching(volume)

    relics_load(source, section_key)
    rec = _RELIC_RECORDS.get(key)
    if rec is None:                     # the key vanished from the file mid-edit
        return None
    vol = relic_volume(rec, name=volume)
    # DO NOT UNWATCH. A watcher is keyed by volume NAME and re-resolves the volume every
    # tick, so it follows a rebuild by itself, keeping its margin, hold and block_jump -
    # measured, not assumed. Tearing it down and re-arming would drop the tractor and
    # emit a spurious `volume_recovered` for every ship inside.
    if ours:
        # Re-apply only OUR watch, so an edit to `Margin:` or `Containment:` goes live on
        # the same Preview as an edit to a chamber. A mission that called volume_watch by
        # hand keeps its own numbers - overriding those would be the library quietly
        # winning an argument the author did not know they were having.
        setattr(rec, "contained", True)
        relic_contain(rec, name=volume)
    out = {
        "key": key, "volume": volume, "source": source,
        "chambers": len(vol.chambers), "passages": len(vol.passages),
        "boxes": len(vol.boxes), "solids": len(vol.solids),
    }
    # A no-op when there is no MAST context (a bare tick loop, a unit test), which is why
    # the caller in mission_runner establishes one first.
    signal_emit("relic_rebuilt", dict(out))
    return out


def relics_reload_all():
    """Re-read every relic that came from a file. Returns a list of summaries.

    What the editor's Preview posts when it does not name one - the common case of a
    mission with a single relic, where naming it would only be a way to get it wrong.
    """
    out = []
    for key in list(_RELIC_RECORDS.keys()):
        got = relic_reload(key)
        if got is not None:
            out.append(got)
    return out


def relics_clear():
    """Drop every registered relic record. Called by reset_mission_state()."""
    _RELIC_RECORDS.clear()


def relics_count():
    """Number of registered relic records. The reset-ledger probe."""
    return len(_RELIC_RECORDS)
