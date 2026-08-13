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
from sbs_utils.procedural.execution import log
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
        elif label == "item":
            data["item"] = str(value).strip()
        elif label == "qty":
            nums = _amd_relic_numbers(value)
            data["qty"] = int(nums[0]) if nums else 1
        elif label == "spawn":
            data["spawn"] = [w.strip() for w in str(value).split(",") if w.strip()]
        elif label in ("starts when", "starts_when", "when"):
            # Stored RAW. Parsing is amd_quest.amd_trigger's job, and it is imported at
            # arm time rather than here so a relic file still reads without the quest
            # layer loaded.
            data["starts_when"] = str(value).strip()
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
            "contents": [],
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
        # CONTENTS may hang off any part - a point marks a spot, but a chamber carrying
        # `Item:` means "somewhere in this room", which is how an author thinks about a
        # ruin. The position is resolved at arm time, from whichever part it is on.
        if data.get("item") or data.get("spawn"):
            rec.contents.append({
                "part": name,
                "item": data.get("item"),
                "qty": int(data.get("qty") or 1),
                "spawn": data.get("spawn") or [],
                "starts_when": data.get("starts_when"),
                # Carried so a placed thing can wear the roles of its place, and know
                # which ruin it is standing in - see _relic_mark_placed.
                "roles": data.get("roles") or [],
                "relic": owner,
            })
        for other, radius in (data.get("passage_to") or []):
            rec.passages.append([name, other, radius if radius else 200.0])
    return [relics[k] for k in order]


def relics_load(file_path, section_key="relics", content=None):
    """Read relics straight from an `.amd` file. The verb a mission actually wants.

    Without this every mission repeats the same three lines - load the document with the
    relic fence handler wired in, find the section, walk it - and the fence handler is
    the part that is easy to forget. Miss it and every field silently falls through to
    the default coercion, so `Chamber: 0, 0, 0, 900` becomes a string and the relic
    builds as nothing.

    Returns the records; they are registered too, so `relic_record(key)` finds them
    later on a story cue.

    `content` is the text, for a caller that has already read it - an addon inside a
    packaged `.mastlib` cannot open its own files by path, so it resolves them with its
    own reader and hands the text over. `file_path` is still recorded as the source, so a
    live editor reload knows what to re-read.
    """
    from sbs_utils.procedural.quest import document_get_amd_file
    doc = document_get_amd_file(file_path, content=content,
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


def relic_place(record, x, y, z):
    """Put a relic somewhere at RUNTIME, overriding its authored `Loc:`.

    An `.amd` cannot know where a relic will stand when the world decides that late. An
    Open Universe cell has a transient world origin - the same system lands at a different
    slot on a different visit - so a galaxy relic has to be placed when the cell is built,
    not when the file is read.

    Every reader goes through `relic_pos`, so setting `loc` here moves the geometry, the
    points, the contents and the containment together. Anything already built keeps the
    position it was built at: place BEFORE `relic_volume`.

    Takes the record (or a key) and returns it, so it reads as one step in a build.
    """
    if not isinstance(record, MastDataObject):
        record = _RELIC_RECORDS.get(record)
    if record is None:
        return None
    setattr(record, "loc", [float(x), float(y), float(z)])
    return record


def relic_release(key):
    """Tear ONE relic down: stop its containment, drop its volume, forget what was armed.

    The counterpart to building a relic into a world that comes and goes. A galaxy tears a
    system down while the next one is already being built, so the whole-registry verbs
    (`volume_clear`, `relics_clear`) are the wrong tools there - they would take the relic
    the crew is currently inside.

    The RECORD stays registered: the relic is a thing the mission still knows about and
    may rebuild on the next visit. Objects are not deleted either - whoever tore the world
    down did that, and a relic outliving its props is not this function's business.
    """
    rec = _RELIC_RECORDS.get(key)
    name = rec.get("volume") if rec is not None else None
    if name is None:
        name = key
    from .volume import volume_remove
    removed = volume_remove(name)
    relic_contents_clear(key)
    if rec is not None:
        setattr(rec, "contained", False)
    return removed


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


# ---------------------------------------------------------------------------
# CONTENTS - what is in a relic, and when it appears.
#
# An author writing an adventure module writes "the vault holds the Red Beacon", not a
# spawn call. So contents hang off the part they are at, and WHEN they appear reuses the
# trigger grammar quests already use - `Starts when:` - rather than inventing a second way
# to say the same thing.
#
# Nothing here is automatic. A mission calls `relic_contents_arm(key)` once; magic that
# spawns loot as a side effect of loading geometry is the kind of thing nobody can find
# later.
# ---------------------------------------------------------------------------

# Armed content records, by (relic key, part name). Per-mission, so it is on the reset
# ledger with everything else.
_ARMED = {}
_ARM_TASK = None


def relic_contents(relic_key):
    """Every authored content record for a relic, with its world position resolved.

    `[{part, item, qty, spawn, starts_when, pos}]`. The position comes from whichever part
    carries it - a point marks a spot, a chamber means "somewhere in this room" and
    resolves to its centre.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return []
    base = relic_pos(rec)
    out = []
    for c in (rec.get("contents") or []):
        pos = _relic_part_pos(rec, c["part"], base)
        if pos is None:
            continue
        d = dict(c)
        d["pos"] = pos
        out.append(d)
    return out


def _relic_part_pos(rec, name, base=None):
    """Where a named part is, in world coordinates - point, chamber or box."""
    if base is None:
        base = relic_pos(rec)
    pt = (rec.get("points") or {}).get(name)
    if pt is not None:
        return (base[0] + pt[0], base[1] + pt[1], base[2] + pt[2])
    ch = (rec.get("chambers") or {}).get(name)
    if ch is not None:
        return (base[0] + ch[0], base[1] + ch[1], base[2] + ch[2])
    bx = (rec.get("boxes") or {}).get(name)
    if bx is not None:
        return (base[0] + bx[0], base[1] + bx[1], base[2] + bx[2])
    return None


def relic_contents_arm(relic_key, radius_default=900.0):
    """Arm a relic's authored contents. Returns how many are waiting on a trigger.

    Three things happen, in this order:

    1. Every point carrying `Roles:` gets a **role marker** - an invisible, selectable
       object at that spot holding those roles. That is what makes `Starts when: reach
       <role>` work at all, since the quest driver's reach test measures against OBJECTS
       holding a role, and it is the plumbing an author should never have to think about.
    2. Contents with no trigger are placed now. That is the common case - a ruin with
       things in it - and it needs no word in the file.
    3. The rest are armed and checked by ONE shared tick, in the pattern
       `quest_tick_reach` established: a watcher per item would be the same work done
       many times.

    Idempotent by (relic, part): re-arming, or a live reload, places nothing twice.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return 0
    _relic_place_role_markers(rec, relic_key)
    waiting = 0
    for c in relic_contents(relic_key):
        key = (relic_key, c["part"])
        if key in _ARMED:
            continue
        trig = _relic_trigger(c.get("starts_when"))
        if trig is None:
            _relic_place_contents(c)
            _ARMED[key] = {"done": True}
            continue
        kind = trig[0] if isinstance(trig, (list, tuple)) else None
        if kind not in RELIC_TRIGGERS:
            # It parsed, so lint would have caught it - but a mission can be run without
            # linting, and a phrase that never fires is invisible at runtime. Say so once,
            # here, rather than leaving an author to wonder where the beacon went.
            log(f"relic '{relic_key}': '{c['part']}' waits on "
                f"'{c.get('starts_when')}', which a relic cannot watch - its contents "
                f"will never appear", "relics", "warning")
        _ARMED[key] = {"done": False, "trig": trig, "content": c,
                       "radius_default": radius_default}
        waiting += 1
    _relic_arm_tick()
    return waiting


def _relic_trigger(phrase):
    """Parse a `Starts when:` phrase, or None when there is none.

    Uses the quest layer's own parser, so the vocabulary is the one the author already
    knows. An unevaluable phrase is NOT silently swallowed - `relic_contents_can_trigger`
    is what lint calls to say so before the mission ever runs.
    """
    if not phrase:
        return None
    try:
        from .amd_quest import amd_trigger
    except Exception:
        return None
    try:
        got = amd_trigger(phrase)
    except Exception:
        return None
    return got or None


# The phrases this watcher knows how to answer. Anything else parses fine and would simply
# never fire, so lint refuses it rather than letting an author wait for a beacon that is
# never coming.
RELIC_TRIGGERS = ("on_reach", "on_signal", "after")


def relic_contents_can_trigger(phrase):
    """True when `phrase` is one this can actually evaluate. What lint asks."""
    trig = _relic_trigger(phrase)
    if trig is None:
        return not phrase
    kind = trig[0] if isinstance(trig, (list, tuple)) else None
    return kind in RELIC_TRIGGERS

def _relic_place_role_markers(rec, relic_key):
    """Put a measuring post at every point carrying `Roles:`.

    This is the plumbing behind `Starts when: reach <role>`. The quest driver's reach test
    measures a player against OBJECTS HOLDING A ROLE, so a role written on a point is only
    half the sentence until something is standing there. An author should never have to
    know that, so arming supplies the other half.

    IT IS NOT MAP FURNITURE. These were `marker_object`s at first - selectable, radar-gold
    - which put a blip on every room, every cache and every trigger in the ruin. A dungeon
    that draws its own floor plan on your radar is not a dungeon; the crew arrives already
    knowing where the treasure is and which rooms matter. So a post is invisible on the
    main screen, unselectable on radar, and carries no exclusion radius that could shove a
    ship off course. Nothing renders it and nothing can click it - it is a place to measure
    from, and a mission that wants a VISIBLE mark puts one there itself.

    Marked with `relic_marker` and keyed by (relic, part) so a reload replaces rather than
    accumulates - the same identity rule the contents use.
    """
    from .spawn import terrain_spawn
    base = relic_pos(rec)
    for name, pt in (rec.get("points") or {}).items():
        roles = pt[3] or []
        if not roles:
            continue
        key = ("marker", relic_key, name)
        if key in _ARMED:
            continue
        try:
            obj = terrain_spawn(base[0] + pt[0], base[1] + pt[1], base[2] + pt[2], "",
                                "#," + ",".join(["relic_marker"] + list(roles)),
                                "generic-sphere", "behav_asteroid")
            obj.data_set.set("elite_main_scn_invis", 1, 0)
            obj.blob.set("unselectable", 1)
            # A prop with a radius pushes ships around; a measuring post must not.
            obj.engine_object.exclusion_radius = 0
        except Exception as e:
            log(f"relic '{relic_key}': could not mark point '{name}': {e}",
                "relics", "warning")
            continue
        _ARMED[key] = {"done": True, "id": getattr(obj, "id", None)}


def _relic_place_contents(c):
    """Put one content record in the world: its item, then its spawns.

    Failures are logged and stepped over rather than raised. Half a placed ruin beats a
    tick that dies on the first unregistered key and silently places nothing after it.
    """
    pos = c.get("pos")
    if pos is None:
        return
    if c.get("item"):
        try:
            from .items import item_spawn
            obj = item_spawn(c["item"], pos[0], pos[1], pos[2],
                             qty=int(c.get("qty") or 1))
            _relic_mark_placed(obj, c)
        except Exception as e:
            log(f"relic contents: item '{c['item']}' at '{c['part']}' failed: {e}",
                "relics", "warning")
    for phrase in (c.get("spawn") or []):
        _relic_spawn_phrase(phrase, pos, c)


def _relic_mark_placed(obj, c):
    """Give a placed thing the ROLES of the place it was placed, and its relic's key.

    An author already says what a spot is for - `Roles: vault_door, relic_piece` - and
    saying it twice, once for the marker and once for the thing sitting there, is how the
    two drift apart. So the roles carry over, and the object knows which ruin it is in.

    That second half is what makes "carry it OUT" answerable at all: the containment latch
    tracks ships, and a thing on the end of a tether is not one, so the only way to ask
    whether the treasure has left is to ask the treasure which ruin to measure against.
    """
    if obj is None:
        return
    for r in (c.get("roles") or []):
        try:
            obj.add_role(r)
        except Exception:
            pass
    try:
        from .inventory import set_inventory_value
        set_inventory_value(obj.id, "relic_key", c.get("relic"))
        set_inventory_value(obj.id, "relic_part", c.get("part"))
    except Exception:
        pass


def _relic_spawn_phrase(phrase, pos, c):
    """`raider x2`, `skaraan 4`, `raider` - the `Guards:` grammar, one entry.

    Scattered rather than stacked: several NPCs on one point would spawn inside each
    other. The spread is small on purpose - they should read as being IN the room the
    author put them in, not near it.
    """
    import random
    words = [w for w in str(phrase).replace("x", " ").split() if w]
    count, race = 1, None
    for w in words:
        if w.isdigit():
            count = int(w)
        elif race is None:
            race = w
    if not race:
        return
    try:
        from .spawn import npc_spawn
    except Exception:
        return
    rnd = random.Random(hash((c.get("part"), race)) & 0xFFFF)
    for i in range(max(1, count)):
        j = (pos[0] + rnd.uniform(-120, 120), pos[1] + rnd.uniform(-60, 60),
             pos[2] + rnd.uniform(-120, 120))
        try:
            npc_spawn(j[0], j[1], j[2], "", race, "", "behav_npcship")
        except Exception as e:
            log(f"relic contents: spawn '{phrase}' at '{c.get('part')}' failed: {e}",
                "relics", "warning")
            return


# ---------------------------------------------------------------------------
# The watcher.
#
# ONE tick for every armed record in every relic, in the pattern quest_tick_reach
# established - a watcher per item is the same work done many times over. Signals do not
# poll at all: they arrive on an observer and set a flag the tick reads, so a signal that
# fires and is gone between two ticks is not missed.
# ---------------------------------------------------------------------------
_SIGNALS_SEEN = set()


def _relic_signal_observer(name, data=None):
    _SIGNALS_SEEN.add(str(name))


def _relic_arm_tick():
    """Start the shared tick, once, and only while something is waiting on it."""
    global _ARM_TASK
    if _ARM_TASK is not None:
        return
    from .signal import signal_observe
    # The observer goes on FIRST and unconditionally. A signal fired before the tick
    # exists still has to be remembered, or a relic armed early misses its own trigger.
    signal_observe(_relic_signal_observer)
    from ..tickdispatcher import TickDispatcher
    try:
        _ARM_TASK = TickDispatcher.do_interval(_relic_contents_tick, 1)
    except Exception:
        # No sim yet. Arming is legal here (a mission may arm as it loads) and the next
        # arm starts the tick, so this is a retry rather than a failure.
        _ARM_TASK = None


def _relic_contents_tick(t=None):
    """Place every armed record whose trigger has now fired."""
    pending = [(k, v) for k, v in _ARMED.items() if not v.get("done")]
    if not pending:
        return
    for key, rec in pending:
        if _relic_trigger_fired(rec):
            _relic_place_contents(rec["content"])
            rec["done"] = True


def _relic_trigger_fired(rec):
    kind, args = rec["trig"][0], (rec["trig"][1] or {})
    if kind == "on_signal":
        return str(args.get("name")) in _SIGNALS_SEEN
    if kind == "after":
        return _relic_timer_done(rec, args)
    if kind == "on_reach":
        return _relic_reached(rec, args)
    return False


def _relic_timer_done(rec, args):
    """`5 minutes` - measured from the moment the record was ARMED, not from mission
    start, so a relic armed late still gives its full delay."""
    from ..helpers import FrameContext
    now = FrameContext.sim_seconds
    if now is None:
        return False
    if "t0" not in rec:
        rec["t0"] = now
        return False
    secs = float(args.get("seconds") or 0) + float(args.get("minutes") or 0) * 60.0
    return (now - rec["t0"]) >= secs


def _relic_reached(rec, args):
    """The same test quest_tick_reach runs: any player within radius of any object
    holding the role."""
    from .query import to_object_list
    from .roles import role
    want = args.get("role")
    if not want:
        return False
    players = to_object_list(role("__player__"))
    if not players:
        return False
    targets = to_object_list(role(str(want)))
    if not targets:
        return False
    radius = float(args.get("radius") or rec.get("radius_default") or 900.0)
    r2 = radius * radius
    for p in players:
        pp = p.pos
        for t in targets:
            tp = t.pos
            dx, dy, dz = pp.x - tp.x, pp.y - tp.y, pp.z - tp.z
            if dx * dx + dy * dy + dz * dz <= r2:
                return True
    return False


def relic_contents_state(relic_key, part):
    """`"placed"`, `"waiting"` or `"unarmed"` for one content record.

    What a report or a test asks. Distinguishing WAITING from UNARMED matters: both look
    like "the loot is not there", and only one of them is a bug.
    """
    rec = _ARMED.get((relic_key, part))
    if rec is None:
        return "unarmed"
    return "placed" if rec.get("done") else "waiting"


def relic_contents_clear(relic_key=None):
    """Forget what has been armed and placed. Does not delete objects.

    With no key this is the mission reset: everything, including the signal observer and
    the shared tick, since the world is going away anyway.

    With a KEY it forgets one relic - the galaxy case, where a system is torn down while
    other systems are still live. The observer and the tick stay, because the relics that
    are still standing are still waiting on them.
    """
    global _ARM_TASK
    if relic_key is not None:
        # Two key shapes live in _ARMED: a content record is (relic, part) and a role
        # marker is ("marker", relic, point). Spelled out rather than indexed cleverly,
        # because a filter that silently matched neither would leak the whole relic.
        for k in [k for k in _ARMED
                  if (len(k) == 2 and k[0] == relic_key)
                  or (len(k) == 3 and k[1] == relic_key)]:
            del _ARMED[k]
        return
    _ARMED.clear()
    _SIGNALS_SEEN.clear()
    _ARM_TASK = None
    from .signal import signal_unobserve
    signal_unobserve(_relic_signal_observer)


def relics_clear():
    """Drop every registered relic record. Called by reset_mission_state()."""
    _RELIC_RECORDS.clear()
    relic_contents_clear()


def relics_count():
    """Number of registered relic records. The reset-ledger probe."""
    return len(_RELIC_RECORDS)


def relic_contents_count():
    """How many content records are armed. The reset-ledger probe - an armed record that
    survives a mission reset would place loot in the NEXT mission."""
    return len(_ARMED)
