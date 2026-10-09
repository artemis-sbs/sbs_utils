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

#: Worn by everything a relic PLACES in the world (a find, a spawn), beside the roles of
#: its place - so "what is still lying about in this ruin" is one role query.
RELIC_PLACED_ROLE = "relic_placed"

#: The role that makes a placed thing THE PIECE - what the crew came for. Carrying it out
#: of the ruin, or reeling it in from a suit, sends the quest signal `<relic key>_taken`.
RELIC_PIECE_ROLE = "relic_piece"


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
        elif label == "prop":
            # SCENERY, not a place: where a set piece stands. Unlike a `Point:` it is
            # nowhere the crew can be sent and takes nothing out of the navigable space -
            # a gate you fly through, a lamp on a gantry.
            nums = _amd_relic_numbers(value)
            data["prop"] = nums[:3] if len(nums) >= 3 else None
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
        elif label == "barrier":
            # A sphere that severs every rail edge crossing it. FOUR numbers like a
            # chamber - x, y, z, radius - because a barrier is a thing in the world with
            # a size, not a property of an edge. Nothing in a relic authors an edge.
            nums = _amd_relic_numbers(value)
            data["barrier"] = nums[:4] if len(nums) >= 4 else None
        elif label == "repair":
            # A JOB, written exactly like a barrier - x, y, z, radius - and done with the
            # same `Clear with:` verbs. The one difference is the point of it: a repair
            # never touches the rail web, so nothing is ever shut behind one.
            nums = _amd_relic_numbers(value)
            data["repair"] = nums[:4] if len(nums) >= 4 else None
        elif label in ("opens when", "opens_when"):
            # Stored RAW, like `Starts when:`, and parsed by the same `amd_trigger` at arm
            # time - so a barrier's grammar is the one an author already knows.
            data["opens_when"] = str(value).strip()
        elif label in ("clear with", "clear_with"):
            data["clear_with"] = [w.strip().lower()
                                  for w in str(value).split(",") if w.strip()]
        elif label == "hidden":
            data["hidden"] = str(value).strip().lower() in ("yes", "true", "on", "1")
        elif label in ("scene", "scan", "facing"):
            # Player-facing words and a scene key. Stored as written: a scene key is
            # matched lowercased when it is looked up, and scan text is shown verbatim.
            data[label] = str(value).strip()
        elif label == "dress":
            # `Dress: ruins_tg_statue 2, generic-cylinder` - art keys in order of
            # preference, each with an optional size multiplier. The first one the engine
            # knows is used, so a mission without the art pack still gets SOMETHING.
            data["dress"] = _amd_relic_pairs(value)
        elif label in ("rail step", "rail_step"):
            nums = _amd_relic_numbers(value)
            data["rail_step"] = nums[0] if nums else None
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
            "walls": data.get("walls"),
            "debris": data.get("debris"),
            "plate": data.get("plate"),
            "gaps": data.get("gaps"),
            "seed": data.get("seed"),
            # How finely the rail web is seeded through this ruin. A number, not a graph:
            # the web is DERIVED, and this is the only dial over it.
            "rail_step": data.get("rail_step"),
            # Per-PART look, filled in below. A relic is rarely one material all
            # through: a plated hall opens into a cave that came down on top of it.
            "part_art": {},
            "part_walls": {},
            # Per-part extras that are not geometry: the scene a place opens, what the
            # Scan app says about it, and what it is dressed with. Keyed by part name and
            # kept OUT of `points` - that list is positional and its readers index it.
            "part_info": {},
            "chambers": {},
            "passages": [],
            "boxes": {},
            "solids": [],
            "points": {},
            "props": {},
            "barriers": {},
            "repairs": {},
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
        # A part may name its own look. This was PARSED and silently dropped before -
        # `Art:` on a chamber passed lint, read cleanly, and then nothing ever looked at
        # it, so "this room is different" quietly meant nothing at all.
        if data.get("art"):
            rec.part_art[name] = data.get("art")
        if data.get("walls"):
            rec.part_walls[name] = data.get("walls")
        info = {"kind": ("point" if data.get("point") else "prop" if data.get("prop")
                         else "chamber" if data.get("chamber")
                         else "box" if data.get("box") else "solid" if data.get("solid")
                         else "barrier" if data.get("barrier")
                         else "repair" if data.get("repair") else None),
                "display": node.get("display_text") or name}
        for k in ("scene", "scan", "dress", "facing"):
            if data.get(k):
                info[k] = data.get(k)
        if data.get("solid"):
            # Which entry of `solids` this part is, so a set piece can stand in for the
            # generic primitive that would otherwise dress it.
            info["solid_index"] = len(rec.solids)
        rec.part_info[name] = info
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
            # [x, y, z, roles, display]. The display name is APPENDED, so every existing
            # reader of [0..3] is unaffected; it is what a revealed marker is labelled
            # with, and "the transmitter bay" reads better on a radar than "at_bay".
            # [x, y, z, roles, display, hidden]. `hidden` is APPENDED for the same
            # reason display was: every existing reader of [0..4] is untouched.
            rec.points[name] = [pt[0], pt[1], pt[2], data.get("roles") or [],
                                node.get("display_text") or name,
                                bool(data.get("hidden"))]
        if data.get("prop"):
            rec.props[name] = list(data["prop"][:3])
        if data.get("barrier"):
            # [x, y, z, radius, opens_when, clear_with, display]. A barrier is not
            # navigable space and it is not subtracted from it either - the geometry is
            # untouched. It acts on the WEB, which is why it is kept apart from `solids`.
            b = data["barrier"]
            rec.barriers[name] = [b[0], b[1], b[2], b[3],
                                  data.get("opens_when"),
                                  data.get("clear_with") or [],
                                  node.get("display_text") or name]
        if data.get("repair"):
            # THE SAME SEVEN SLOTS AS A BARRIER, so everything that reads one reads the
            # other: [x, y, z, radius, None, clear_with, display]. Slot 4 is a barrier's
            # `Opens when:`, which a repair does not have - a job is done by somebody.
            r = data["repair"]
            rec.repairs[name] = [r[0], r[1], r[2], r[3], None,
                                 data.get("clear_with") or [],
                                 node.get("display_text") or name]
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


def relics_load(file_path, section_key="relics", content=None, scenes=True):
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
    if content is not None:
        _RELIC_TEXT[file_path] = content
    if scenes:
        # A relic file's own `## Dialogue` is what its places' `Scene:` names. Registered
        # here so a mission that loads relics directly gets them; Open Universe also
        # registers them itself (`universe_relic_declare_scenes`), which is harmless -
        # last registration wins, quietly.
        _relic_register_dialogue(file_path, content)
    section = amd_section(doc, section_key)
    if section is None and section_key == "relics":
        # THE SECTION MAY BE CALLED WHAT THE SCHEMA SAYS A RELIC SECTION IS CALLED. Every
        # tool types the records of `## [Ruins](ruins)` as relics - lint checks them, the
        # plan view draws them - and this reader alone wanted the one key, so a ruin
        # under the other name was clean, was drawn, and was not built.
        section, section_key = _relic_section_any(doc)
    return relics_register(section, source=file_path, section_key=section_key)


def _relic_section_any(doc):
    """(section, its key) for the first top-level section the schema calls a relic
    section, else (None, "relics")."""
    from sbs_utils.procedural.amd_doc import amd_root_node
    from sbs_utils.procedural.amd_schema import archetype_for_section
    root = amd_root_node(doc)
    for n in (root.get("children", []) if root is not None else []):
        key = n.get("key")
        if key and archetype_for_section(str(key)) == "relic":
            return n, key
    return None, "relics"


#: The text a relic file was loaded from, when the caller handed it over - a relic inside a
#: packaged addon cannot be re-opened by path.
_RELIC_TEXT = {}


def relic_section(relic_key, section_key):
    """Another section of the file a relic came from - its `side_stories`, its `items`.

    A relic file is self-contained: the space, what is in it, what is said in it and the
    stories told in it open as one document. This is how a mission reaches the parts the
    library does not read itself - `boarding_quests_grant(relic_section(key,
    "side_stories"))` gives the crew who go inside the stories that belong to that ruin.
    None when the relic or the section is unknown.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    source = rec.get("source") if rec is not None else None
    if not source:
        return None
    try:
        from sbs_utils.procedural.quest import document_get_amd_file
        doc = document_get_amd_file(source, content=_RELIC_TEXT.get(source))
        return amd_section(doc, section_key)
    except Exception as e:                                # noqa: BLE001
        log(f"relic '{relic_key}': section '{section_key}' not read: {e}", "relics",
            "warning")
        return None


def _relic_register_dialogue(file_path, content=None):
    """Register a relic file's `## Dialogue` scenes. Never raises; returns how many."""
    try:
        from sbs_utils.procedural.quest import document_get_amd_file
        from sbs_utils.procedural.amd_dialogue import dialogue_register_scenes
        doc = document_get_amd_file(file_path, content=content)
        section = amd_section(doc, "dialogue")
        return len(dialogue_register_scenes(section)) if section is not None else 0
    except Exception as e:                                # noqa: BLE001
        log(f"relic dialogue in '{file_path}' not registered: {e}", "relics", "warning")
        return 0


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


# ---------------------------------------------------------------------------
# SPAWN - a whole ruin in the game from one call.
#
# `relics_build` stops at the geometry: a volume nobody can see. Everything after it -
# walls, atmosphere, what is inside, a name on the map - was four more calls a mission had
# to know to make, in the right order, and the only code that made all of them lived in
# Open Universe. A standalone mission got a recipe card of four lines, built the FIRST
# relic in its file and silently ignored the rest, and took the whole map label down with
# it when one passage named a room that was not there.
# ---------------------------------------------------------------------------

#: A nebula thin enough to see the wall you are trying not to hit, built from objects of a
#: size the renderer is known to be happy with. Open Universe's numbers, now the library's.
RELIC_NEBULA_DENSITY = 0.6
RELIC_NEBULA_SCALE = 0.35
RELIC_NEBULA_OBJECT = 2500


def relic_wall_role(key):
    """The role one relic's wall props carry: `relic_wall:<key>`.

    Scoped to the relic, so that tearing one ruin down - or re-dressing it after a live
    edit - cannot take another ruin's walls with it.
    """
    return "relic_wall:" + str(key)


def relic_atmos_role(key):
    """The role one relic's nebula carries: `relic_atmos:<key>`."""
    return "relic_atmos:" + str(key)


def _relic_say(message):
    """Say that a ruin was not built as written, where the author will see it.

    A named log category has no handler unless the mission attached one, so the same line
    goes to `mast.runtime` - the log a headless test fails on and the first one anybody
    opens.
    """
    try:
        log(message, "relics", "warning")
    except Exception:                                   # noqa: BLE001
        pass
    try:
        import logging
        logging.getLogger("mast.runtime").warning(message)
    except Exception:                                   # noqa: BLE001
        pass


def relic_atmosphere(relic_key, roles=None, default=None, name=None):
    """Fill a built relic with ONE nebula, in the color its `Atmosphere:` names.
    Returns how many nebula objects were made.

    The point is not the look: the engine caps warp for a ship inside a nebula by itself,
    so the interior needs no script governor.

    `Atmosphere: none` - and, here, no `Atmosphere:` line at all - makes none. `default`
    is the color for a relic that does not say (Open Universe passes `purple`).

    Identity, not a once-flag: a relic that already has its nebula gets no second one.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return 0
    vol = volume_get(relic_volume_name(rec, name))
    if vol is None:
        return 0
    # LOWER-CASED, AND CHECKED. The word was handed over as written, and the nebula
    # spawner picks a RANDOM color for one it does not know - so `Atmosphere: Purple`, with
    # a capital, was green on one run and white on the next, and a misspelled color was
    # whatever the dice said. A word that is not a color now makes no cloud, and says so.
    color = str(rec.get("atmosphere") or default or "none").strip().lower()
    if color in ("none", "no", "off", ""):
        return 0
    known = relic_atmosphere_colors()
    if known and color not in known:
        _relic_say(f"relic '{relic_key}': `Atmosphere: {rec.get('atmosphere')}` is not a "
                   f"nebula color ({', '.join(known)}), so it has no cloud.")
        return 0
    atmos = relic_atmos_role(relic_key)
    from .roles import role
    have = len(role(atmos))
    if have:
        return have
    from . import terrain as _terrain
    (cx, cy, cz), radius = vol.bound()
    # The CLOUD covers the ruin; each nebula OBJECT stays a size the renderer has been
    # seen to draw. The object size is a GLOBAL, so it is put back: left set, this ruin
    # would resize every cloud spawned after it.
    was = getattr(_terrain, "NEB_SIZE_LARGE", 1500)
    _terrain.terrain_set_nebula_object_size(RELIC_NEBULA_OBJECT)
    try:
        neb = _terrain.terrain_spawn_nebula_sphere(
            cx, cy, cz, radius=int(radius), density_scale=RELIC_NEBULA_SCALE,
            density=RELIC_NEBULA_DENSITY, height=int(radius),
            cluster_color=color, marker=False)
    finally:
        _terrain.terrain_set_nebula_object_size(was)
    extra = [r.strip() for r in str(roles or "").split(",") if r.strip()]
    made = 0
    for n in (neb or []):
        agent = getattr(n, "py_object", None)      # terrain_* hands back SpawnData
        if agent is None:
            continue
        agent.add_role(atmos)
        for r in extra:
            agent.add_role(r)
        made += 1
    return made


def relic_atmosphere_colors():
    """The words `Atmosphere:` accepts, sorted. Empty when the color table cannot be
    read, which callers treat as "do not judge"."""
    try:
        from .terrain import _neb_colors
        return tuple(sorted(_neb_colors.keys()))
    except Exception:                                   # noqa: BLE001
        return ()


def relic_entrance(relic_key):
    """Where a relic is entered: its first point carrying `Roles: entrance`, else its
    own `Loc:`. World (x, y, z), or None for an unknown relic."""
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return None
    ways = relic_points(relic_key, "entrance")
    if ways:
        return tuple(list(ways.values())[0][:3])
    return tuple(relic_pos(rec))


def relic_holds(relic_key, pos):
    """Is this position inside relic `relic_key`? The extraction test.

    Hauling a thing OUT of a ruin is the one question containment cannot answer: the
    containment latch tracks ships, and the thing on the end of a tether is cargo. So the
    cargo is asked instead - `pos` is an (x, y, z), a Vec3, or anything with a position.

    False for a relic that is not registered or whose space is not built, which is the
    same answer as "it is not in there".
    """
    from .volume import volume_contains
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None or pos is None:
        return False
    vol = volume_get(relic_volume_name(rec))
    if vol is None:
        return False
    if not isinstance(pos, (tuple, list)):
        p = getattr(pos, "pos", pos)
        try:
            pos = (p.x, p.y, p.z)
        except AttributeError:
            return False
    return bool(volume_contains(vol, pos))


def relic_spawn(relic_key, walls=True, atmosphere=True, contents=True, marker=True,
                contain=False, props=None):
    """Put one registered relic in the game: space, walls, nebula, contents, map marker.
    Returns the record, or None when it could not be built - and says why.

        relics_load(get_mission_dir_filename("mission.amd"))
        relic_spawn("hollow")

    | part | from the file | turned off with |
    |---|---|---|
    | the space | `Chamber:`, `Box:`, `Passage to:`, `Solid:` | - |
    | walls | `Walls:`, `Art:`, `Seed:`, `Gaps:`, `Debris:`, `Dress:` | `walls=False` |
    | nebula | `Atmosphere: <color>`; none when the line is absent | `atmosphere=False` |
    | what is inside | `Item:`, `Spawn:`, `Starts when:`, points and their markers | `contents=False` |
    | a name on the map | the `Roles: entrance` point, else `Loc:` | `marker=False` |

    CONTAINMENT IS OFF unless asked for. `contain=True` applies the authored
    `Containment:` - and a ship held inside a ruin has no way out of one that is not also
    a galaxy cell, because containment lets go only a whole relic clear of the walls and a
    held ship never gets there. Open Universe leaves by jumping. Until a ruin can say
    where its door is, walls in a plain mission are scenery.

    IDENTITY, not a once-flag: a relic whose space is already built is left alone, so
    calling this twice - a route that fires again, a late joiner - builds nothing twice.

    NEVER RAISES. A passage naming a room that does not exist used to raise out of the map
    label, and a map label that dies spawns no players either. The reason is logged and
    the rest of the mission carries on.

    Emits `relic_built` with RELIC_KEY, RELIC_VOLUME and RELIC_NAME.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        _relic_say(f"relic '{relic_key}' is not registered, so it was not built. "
                   f"Load its file first (relics_load / relics_spawn).")
        return None
    props = int(props if props is not None else RELIC_PROPS)
    volume = relic_volume_name(rec)
    if volume_get(volume) is not None:
        # Already standing. The RECORD may be a fresh one - reading the file again
        # replaces it - so tell it which volume is its own; without that, everything
        # keyed on the record would address nothing.
        if not rec.get("volume"):
            setattr(rec, "volume", volume)
        return rec
    if not (rec.get("chambers") or rec.get("boxes")):
        _relic_say(f"relic '{relic_key}' has no rooms, so it was not built. A room is a "
                   f"record with `Relic: {relic_key}` and a `Chamber:` or `Box:` line, "
                   f"written with the same number of hashes as the relic itself.")
        return None
    if not rec.get("loc"):
        _relic_say(f"relic '{relic_key}' has no `Loc:` line, so it is built at 0, 0, 0.")
    try:
        vol = relic_volume(rec)
    except Exception as e:                              # noqa: BLE001
        _relic_say(f"relic '{relic_key}' was not built: {e}")
        return None
    if vol is None:
        _relic_say(f"relic '{relic_key}' was not built: it has no space.")
        return None
    steps = []
    if walls:
        steps.append(("walls", lambda: relic_walls(
            relic_key, n=props, roles=relic_wall_role(relic_key) + ", relic_wall")))
    if atmosphere:
        steps.append(("atmosphere", lambda: relic_atmosphere(relic_key)))
    if contain:
        steps.append(("containment", lambda: relic_contain(rec)))
    if contents:
        # Items first: `Item:` on a room is a reference, and one that resolves to nothing
        # places a pickup that looks like a question mark.
        steps.append(("items", lambda: relic_items(relic_key)))
        steps.append(("contents", lambda: relic_contents_arm(relic_key)))
    if marker:
        steps.append(("map marker", lambda: _relic_spawn_marker(relic_key, rec)))
    for what, step in steps:
        # Each part on its own: a ruin with walls and no marker is still a ruin, and the
        # one line saying which part failed is worth more than losing all of them.
        try:
            step()
        except Exception as e:                          # noqa: BLE001
            _relic_say(f"relic '{relic_key}': {what} failed: {e}")
    setattr(rec, "spawned", {"walls": bool(walls), "props": int(props)})
    signal_emit("relic_built", {"RELIC_KEY": relic_key,
                                "RELIC_VOLUME": relic_volume_name(rec),
                                "RELIC_NAME": rec.get("name") or relic_key})
    return rec


def relic_items(relic_key=None):
    """Declare the `Items` section of a relic's own file. Returns the item keys.

    A relic file is self-contained - the ruin, what is in it, and what those things ARE,
    in one document. `Item:` on a room only names an item; this is what makes the name
    mean something. With no key, every registered relic's file is read, once each.
    Nothing to do, and no error, for a file with no `Items` section.
    """
    from .amd_items import items_declare_amd
    keys = [relic_key] if relic_key is not None else list(_RELIC_RECORDS.keys())
    seen, out = set(), []
    for key in keys:
        rec = _RELIC_RECORDS.get(key)
        source = rec.get("source") if rec is not None else None
        if not source or source in seen:
            continue
        seen.add(source)
        section = relic_section(key, "items")
        if section is not None:
            out += items_declare_amd(section) or []
    return out


def _relic_spawn_marker(relic_key, rec):
    from .markers import marker_point
    pos = relic_entrance(relic_key)
    if pos is not None:
        marker_point(pos[0], pos[1], pos[2], str(rec.get("name") or relic_key))


def relics_spawn(file_path, section_key="relics", **spawn):
    """Build EVERY relic written in a file. Returns the records that were built.

        relics_spawn(get_mission_dir_filename("mission.amd"))

    The one line a mission needs. A file with no `relics` section is not an error - it
    returns an empty list - so the line can sit in a template whether the mission has a
    ruin or not. Keyword arguments go to `relic_spawn` (`contain=True`, `walls=False`...).
    """
    try:
        records = relics_load(file_path, section_key)
    except Exception as e:                              # noqa: BLE001
        _relic_say(f"the relics in '{file_path}' were not read: {e}")
        return []
    built = []
    for rec in records:
        got = relic_spawn(rec.get("key"), **spawn)
        if got is not None:
            built.append(got)
    return built


def relic_redress(relic_key):
    """Tear a spawned relic's walls down and dress it again. Returns how many were made.

    What a live edit needs: `relic_reload` moves the SPACE, and walls left where the old
    space was are worse than no walls. A no-op for a relic `relic_spawn` did not dress -
    a mission that dresses its own answers `relic_rebuilt` itself.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    spawned = rec.get("spawned") if rec is not None else None
    if not spawned or not spawned.get("walls"):
        return 0
    from .roles import role
    from .space_objects import delete_object
    wall = relic_wall_role(relic_key)
    for oid in list(role(wall)):
        delete_object(oid)
    return relic_walls(relic_key, n=int(spawned.get("props") or RELIC_PROPS),
                       roles=wall + ", relic_wall")


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
    from .rails import rail_remove
    # THE CREW FIRST, while the ruin is still there to come back from. A suit left flying
    # a volume that no longer exists has no route home, and SUIT UP left pointing at it
    # would put the next boarder inside nothing. Never raises: a teardown that dies half
    # way leaves a volume watching ships in a system that is gone.
    try:
        from .eva_relics import eva_relic_released
        eva_relic_released(key)
    except Exception as e:                              # noqa: BLE001
        log(f"relic '{key}': its boarding party was not brought in: {e}", "relics",
            "warning")
    removed = volume_remove(name)
    rail_remove(name)
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


def relic_point_display(relic_key, name):
    """What a point is CALLED - the authored label, else its key.

    The same string `_relic_place_role_markers` names the marker with, so a list of places
    to go and the label that lights up on the radar cannot disagree.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    pt = (rec.get("points") or {}).get(name) if rec is not None else None
    if not pt:
        return name
    return pt[4] if len(pt) > 4 and pt[4] else name


def relic_point_revealed(relic_key, name):
    """Whether the crew has been close enough to light this point's marker.

    TRUE WHEN THERE IS NO MARKER, which is the case that matters: a point without
    `Roles:` is never armed, and a relic whose contents were never armed has no markers at
    all. Answering False for those would hide every destination in a relic that simply
    does not use the reveal mechanism.
    """
    rec = _ARMED.get(("marker", relic_key, name))
    return True if rec is None else bool(rec.get("shown"))


def relic_point_has_marker(relic_key, name):
    """Whether this point was armed with a marker at all.

    The companion `relic_point_revealed` answers TRUE for a point with no marker, which
    is right for its own job - it gates destinations, and a relic that does not use the
    reveal mechanism must not have every destination hidden. It makes it useless as a
    record of where the crew has BEEN, though: without this test, every place in an
    unarmed relic reads as already seen.
    """
    return _ARMED.get(("marker", relic_key, name)) is not None


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
    relic_rails(record, name=key)
    return vol


def relic_rails(record, name=None, margin=None):
    """Solve this relic's rail web. Called by `relic_volume`; returns the stats dict.

    ONCE PER RELIC, HERE, rather than once per trip. Every destination a console picks
    used to re-derive the ruin's connectivity from the geometry - doorways, skirts and an
    N-squared visibility graph, measured at 96ms for the first pick and 17ms for every one
    after, per console, on a bridge. Connectivity is a property of the RUIN, so it is
    solved when the ruin is built.

    Nothing about it is authored. The relic's own `Point:` records become named
    destinations; everything else - the stations through each room, the doorways, the way
    round a pillar - is derived. `Rail step:` is the one dial, and `Barrier:` parts are
    registered here so a shut way is shut from the first route anybody asks for.
    """
    from .rails import rail_barrier, rail_build
    key = relic_volume_name(record, name)
    base = relic_pos(record)
    places = {}
    for pname, pt in (record.get("points") or {}).items():
        places[pname] = {
            "pos": (base[0] + pt[0], base[1] + pt[1], base[2] + pt[2]),
            "roles": tuple(pt[3]) if len(pt) > 3 else (),
            "display": pt[4] if len(pt) > 4 else pname,
            "hidden": bool(pt[5]) if len(pt) > 5 else False,
        }
    step = record.get("rail_step")
    stats = rail_build(key, places=places, margin=margin,
                       step=float(step) if step else None)
    for bname, b in (record.get("barriers") or {}).items():
        rail_barrier(key, bname,
                     (base[0] + b[0], base[1] + b[1], base[2] + b[2]), b[3],
                     display=b[6] if len(b) > 6 else bname)
    return stats


def relic_rails_ensure(relic_key, name=None):
    """The relic's rail web name, solving the web now if it has not been solved yet.

    `relic_volume` builds it, which covers every relic read from an `.amd`. A mission - or
    a test - that defines the volume itself and registers the points by hand never goes
    through that, and a route with no web to walk would simply refuse. So the first route
    asked for is what builds it, once, and everything after that walks the cache.

    Returns the volume name, or None when there is no such relic or its volume has not
    been built.
    """
    from .rails import rail_get
    from .volume import volume_get
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return None
    key = relic_volume_name(rec, name)
    if rail_get(key) is not None:
        return key
    if volume_get(key) is None:
        return None
    relic_rails(rec, name=key)
    return key


#: What a barrier object is made of. `hullpoints` is the only dial that decides how long
#: cutting takes now - the engine's beam damage does the work, so a soft blockage and a
#: bulkhead differ by a number rather than by a scripted timer.
RELIC_BARRIER_HULL = 40
RELIC_BARRIER_ROLE = "relic_barrier"


def relic_barriers_spawn(relic_key, name=None):
    """Give every SHUT barrier a space object, so a beam has something to hit.

    A barrier is a sphere in the rail web, and nothing in the engine can shoot a sphere -
    which is the whole reason cutting one used to be a scripted timer with no beam on
    screen. A real object makes it an ordinary weapons problem: point at it, fire, and the
    thing dies. `relic_barrier_destroyed` is the other end.

    Idempotent per (relic, barrier): a reload replaces rather than accumulates, the same
    identity rule the markers and contents use. Returns how many were placed.
    """
    from .rails import rail_barrier_set_object, rail_barriers
    from .spawn import terrain_spawn
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return 0
    volume = relic_volume_name(rec, name)
    # WHAT WAS OPENED STAYS OPEN. The web is solved fresh each time the ruin is built,
    # with every barrier shut, so the ledger opens the ones the crew already dealt with
    # before anything is given a body. Quietly: this is not news (see the ledger).
    _relic_ledger_open_web(relic_key, volume)
    placed = 0
    for bkey, bar in rail_barriers(volume, shut_only=True):
        akey = ("barrier_obj", relic_key, bkey)
        if akey in _ARMED:
            continue
        pos = bar["pos"]
        label = bar.get("display") or bkey
        # A barrier may be DRESSED - a seized hatch, a grate - and is then drawn as that
        # piece, fitted to its radius. Otherwise the plain sphere it always was.
        art, mult = _relic_dress_pick(relic_part_info(relic_key, bkey).get("dress"))
        try:
            obj = terrain_spawn(pos[0], pos[1], pos[2], str(label),
                                "#," + RELIC_BARRIER_ROLE,
                                art or "generic-sphere", "behav_selection")
            if art:
                from .volume_dress import _mesh_size
                size = _mesh_size(art, (200.0, 200.0, 200.0))
                s = 2.0 * float(bar.get("radius") or 200.0) / max(size) * mult
                for axis in "xyz":
                    obj.data_set.set("local_scale_%s_coeff" % axis, s, 0)
                # `Facing: 0, 1, 0` lays a grate ACROSS a vertical shaft: a barrier is
                # not upright scenery, so its facing is taken as given, not flattened.
                nums = _amd_relic_numbers(relic_part_info(relic_key, bkey).get("facing")
                                          or "")
                if len(nums) >= 3:
                    try:
                        import sbs
                        from .volume import volume_look_quat
                        w, qx, qy, qz = volume_look_quat(nums[:3])
                        obj.engine_object.rot_quat = sbs.quaternion(w, qx, qy, qz)
                    except Exception:                    # noqa: BLE001
                        pass
            # NO EXCLUSION RADIUS. Containment and the rails already keep a suit off the
            # geometry; a prop that shoves ships would fight the route that was solved to
            # fly right up to this thing and cut it.
            obj.engine_object.exclusion_radius = 0
            obj.data_set.set("hullpoints", RELIC_BARRIER_HULL, 0)
            obj.data_set.set("hull_max", RELIC_BARRIER_HULL, 0)
        except Exception as e:                            # noqa: BLE001
            log(f"relic '{relic_key}': could not place barrier '{bkey}': {e}",
                "relics", "warning")
            continue
        oid = getattr(obj, "id", None)
        rail_barrier_set_object(volume, bkey, oid)
        _ARMED[akey] = {"done": True, "id": oid, "relic": relic_key,
                        "barrier": bkey, "volume": volume}
        placed += 1
    return placed


def relic_barrier_destroyed(obj_id):
    """A destroyed barrier object opens its barrier. What a `//damage/destroy` route calls.

    Returns the barrier key it opened, or None when the object was not a barrier - so a
    route can hand it every destruction without asking first.

    A REPAIR JOB IS NOT DONE BY BEING SHOT. Handed the marker of a `Repair:` job this
    repairs nothing and returns None: the job is read from the record, so it is still
    there to do. It only FORGETS the marker's id - ids are recycled, and
    `relic_repair_done` puts the plain marker away by id, so a remembered id of a marker
    that is gone would one day delete whatever the engine gave that number to next.
    """
    from .query import to_id
    obj_id = to_id(obj_id)
    for akey, rec in list(_ARMED.items()):
        if rec.get("id") != obj_id or obj_id is None:
            continue
        if akey[0] == "repair":
            rec["id"] = None
            return None
        if akey[0] != "barrier_obj":
            continue
        relic_open_barrier(rec.get("relic"), rec.get("barrier"))
        return rec.get("barrier")
    return None


def relic_open_barrier(relic_key, barrier, name=None):
    """Open one of a relic's barriers - what a cutting beam or a haul ends in.

    Emits `rail_opened` so a suit holding for a shut way re-plans at once rather than
    waiting out its stall counter. False when there is no such barrier, or it was already
    open.
    """
    from .rails import rail_barrier_open
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return False
    volume = relic_volume_name(rec, name)
    if not rail_barrier_open(volume, barrier):
        return False
    # THE WAY IS CLEAR, SO THE THING IS GONE. Leaving the object behind would leave a
    # shootable obstacle sitting in a doorway the router now happily plans through.
    akey = ("barrier_obj", relic_key, barrier)
    rec_obj = _ARMED.pop(akey, None)
    if rec_obj and rec_obj.get("id") is not None:
        from .rails import rail_barrier_set_object
        rail_barrier_set_object(volume, barrier, None)
        try:
            from .space_objects import delete_object
            # QUEUED, not immediate. `SpaceObject.delete_object` defers the real
            # sbs.delete_object to the garbage collector at the end of the event, because
            # deleting under a live event is a use-after-free - and this is called FROM a
            # damage route, which is exactly that situation.
            delete_object(rec_obj["id"])
        except Exception as e:                            # noqa: BLE001
            log(f"relic '{relic_key}': barrier '{barrier}' opened but its object "
                f"could not be removed: {e}", "relics", "warning")
    _relic_ledger_note(relic_key, "opened", barrier)
    signal_emit("rail_opened", {"RAIL_VOLUME": volume, "RAIL_RELIC": relic_key,
                                "RAIL_BARRIER": barrier})
    relic_quest_signal(str(barrier) + "_opened")
    return True


def relic_barriers(relic_key):
    """``{name: [x, y, z, radius, opens_when, clear_with, display]}`` as AUTHORED.

    Positions are relic-relative, like every other authored part. For the live state - is
    it open, which edges is it severing - ask the web with `rail_barriers`.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    return dict(rec.get("barriers") or {}) if rec is not None else {}


# --- repair jobs ------------------------------------------------------------------------
#
# `Repair: x, y, z, radius` is a barrier that is not in anybody's way. It is a thing in the
# world with a position and a size, a suit works on it with the same tools (`Clear with:`),
# and it reports the same way - but it never touches the rail web, so a ruin, or a station
# under repair, is never divided by its own to-do list. Doing one sends the quest signal
# `<repair key>_repaired`.

RELIC_REPAIR_ROLE = "relic_repair"
RELIC_REPAIRED_ROLE = "relic_repaired"


def relic_repairs(relic_key):
    """``{name: [x, y, z, radius, None, clear_with, display]}`` as AUTHORED - the shape
    `relic_barriers` returns, so one reader serves both. Positions are relic-relative."""
    rec = _RELIC_RECORDS.get(relic_key)
    return dict(rec.get("repairs") or {}) if rec is not None else {}


def relic_repair_jobs(relic_key, open_only=False):
    """``[(name, job)]`` with the live state: ``{"pos", "radius", "display",
    "clear_with", "fixed", "object"}``, `pos` in WORLD coordinates.

    What the suit's Fire app lists. Read from the record, not from the objects standing
    in for the jobs - so a job whose marker was never placed, or was destroyed, is still
    a job that can be done.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return []
    base = relic_pos(rec)
    out = []
    done = _relic_ledger_has(relic_key, "repaired")
    for name, r in (rec.get("repairs") or {}).items():
        armed = _ARMED.get(("repair", relic_key, name)) or {}
        fixed = bool(armed.get("fixed")) or name in done
        if open_only and fixed:
            continue
        out.append((name, {
            "pos": (base[0] + r[0], base[1] + r[1], base[2] + r[2]),
            "radius": float(r[3]),
            "display": r[6] if len(r) > 6 and r[6] else name,
            "clear_with": list(r[5] or []) if len(r) > 5 else [],
            "fixed": fixed,
            "object": armed.get("id")}))
    return out


def relic_repair_fixed(relic_key, repair):
    """Whether a repair job has been done - now, or on an earlier visit."""
    return (bool((_ARMED.get(("repair", relic_key, repair)) or {}).get("fixed"))
            or repair in _relic_ledger_has(relic_key, "repaired"))


def relic_repairs_spawn(relic_key, name=None):
    """Give every repair job a marker in the world, and somewhere to fly to.

    The marker is what the crew sees and selects - dressed with the part's `Dress:` art
    when it has any, else the plain sphere a barrier uses. It has no exclusion radius and
    is NOT what makes the job doable: `relic_repair_jobs` reads the record.

    The job also joins the rail web as a DESTINATION (`rail_attach`), so the Nav app can
    send a suit to it. That adds a node and its own legs; it severs nothing.

    Idempotent per (relic, job). Returns how many were placed.
    """
    from .spawn import terrain_spawn
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return 0
    volume = relic_volume_name(rec, name)
    placed = 0
    for rkey, job in relic_repair_jobs(relic_key):
        akey = ("repair", relic_key, rkey)
        if akey in _ARMED:
            continue
        pos, label = job["pos"], job["display"]
        oid = None
        art, mult = _relic_dress_pick(relic_part_info(relic_key, rkey).get("dress"))
        # DONE ON AN EARLIER VISIT (the ledger): the fault is not there to mark. A
        # dressed job - a panel, a coupling - is still furniture and stands as repaired;
        # a plain marker is simply not made. Nothing is announced.
        was_done = rkey in _relic_ledger_has(relic_key, "repaired")
        try:
            if was_done and not art:
                raise _RelicNothingToPlace()
            obj = terrain_spawn(pos[0], pos[1], pos[2], str(label),
                                "#," + (RELIC_REPAIRED_ROLE if was_done else RELIC_REPAIR_ROLE),
                                art or "generic-sphere", "behav_selection")
            if art:
                from .volume_dress import _mesh_size
                size = _mesh_size(art, (200.0, 200.0, 200.0))
                s = 2.0 * float(job["radius"] or 200.0) / max(size) * mult
                for axis in "xyz":
                    obj.data_set.set("local_scale_%s_coeff" % axis, s, 0)
            obj.engine_object.exclusion_radius = 0
            oid = getattr(obj, "id", None)
        except _RelicNothingToPlace:
            pass
        except Exception as e:                            # noqa: BLE001
            log(f"relic '{relic_key}': could not mark repair '{rkey}': {e}",
                "relics", "warning")
        try:
            from .rails import rail_attach
            rail_attach(volume, rkey, pos, roles=("repair",), display=label)
        except Exception as e:                            # noqa: BLE001
            log(f"relic '{relic_key}': repair '{rkey}' could not join the rail web: {e}",
                "relics", "warning")
        # `done` so the contents tick never treats it as waiting on a trigger; `at`, not
        # `pos`, so the reveal tick never mistakes it for a marker to light.
        _ARMED[akey] = {"kind": "repair", "done": True, "id": oid, "relic": relic_key,
                        "repair": rkey, "at": pos, "fixed": was_done,
                        "dressed": bool(art)}
        placed += 1
    return placed


def relic_repair_done(relic_key, repair):
    """A repair job is finished - what a suit's tool, or a story beat, ends in.

    Emits `relic_repaired` (RELIC_KEY, RELIC_REPAIR) and sends the quest signal
    `<repair key>_repaired`. False when there is no such job or it was already done.

    The plain marker goes: it marked a fault, and the fault is gone. A DRESSED job - a
    panel, a coupling - stays where it is and wears `relic_repaired` instead.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None or repair not in (rec.get("repairs") or {}):
        return False
    akey = ("repair", relic_key, repair)
    armed = _ARMED.get(akey)
    if armed is None:
        # Never armed - a relic built without its contents. The job is still a job.
        armed = _ARMED[akey] = {"kind": "repair", "done": True, "id": None,
                                "relic": relic_key, "repair": repair, "fixed": False}
    if armed.get("fixed"):
        return False
    armed["fixed"] = True
    oid = armed.get("id")
    if oid is not None:
        try:
            from .query import to_object
            obj = to_object(oid)
            if obj is not None and armed.get("dressed"):
                obj.remove_role(RELIC_REPAIR_ROLE)
                obj.add_role(RELIC_REPAIRED_ROLE)
            elif obj is not None:
                from .space_objects import delete_object
                delete_object(oid)          # queued, like a barrier's - see above
                armed["id"] = None
        except Exception as e:                            # noqa: BLE001
            log(f"relic '{relic_key}': repair '{repair}' is done but its marker could "
                f"not be put away: {e}", "relics", "warning")
    _relic_ledger_note(relic_key, "repaired", repair)
    signal_emit("relic_repaired", {"RELIC_KEY": relic_key, "RELIC_REPAIR": repair})
    relic_quest_signal(str(repair) + "_repaired")
    return True


def relic_point_hidden(relic_key, name):
    """Whether a point is authored `Hidden:` - off the destination list until found.

    Hidden is a property of the LIST, never of the graph: a route still passes THROUGH a
    hidden place, because stumbling into a secret on the way somewhere else is the point
    of having one.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return False
    pt = (rec.get("points") or {}).get(name)
    return bool(pt[5]) if pt is not None and len(pt) > 5 else False


def relic_part_info(relic_key, name):
    """The non-geometry facts of one part - `scene`, `scan`, `dress`, `facing`, `kind`,
    `display`. An empty dict for an unknown part."""
    rec = _RELIC_RECORDS.get(relic_key)
    info = (rec.get("part_info") or {}).get(name) if rec is not None else None
    return dict(info or {})


def relic_part_scene(relic_key, name):
    """The scene key a place opens when a suit arrives there, or None."""
    scene = relic_part_info(relic_key, name).get("scene")
    return str(scene).strip().lower() if scene else None


def relic_part_scan(relic_key, name):
    """What the xESS Scan app says about a place, or None.

    Never the part's prose: in a shipped relic that is written for the AUTHOR ("the
    cradle is a box solid so the rails skirt it") and must never reach a player."""
    return relic_part_info(relic_key, name).get("scan") or None


def relic_part_at(relic_key, pos):
    """The room (chamber or box) a world position is in, else the nearest one, else None.

    Boxes count - `volume_chamber_at` only knows chambers, and four of Storm's Beacon's
    seven ruins are built from boxes, so it answered "open space" in the middle of a hall.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None or pos is None:
        return None
    base = relic_pos(rec)
    p = (float(pos[0]) - base[0], float(pos[1]) - base[1], float(pos[2]) - base[2])
    best, best_d = None, float("inf")
    for name, (x, y, z, r) in (rec.get("chambers") or {}).items():
        d = ((p[0] - x) ** 2 + (p[1] - y) ** 2 + (p[2] - z) ** 2) ** 0.5 - r
        if d < best_d:
            best, best_d = name, d
    for name, (x, y, z, hx, hy, hz) in (rec.get("boxes") or {}).items():
        # Signed distance to a box: negative inside, the deepest box wins overlaps.
        q = (abs(p[0] - x) - hx, abs(p[1] - y) - hy, abs(p[2] - z) - hz)
        out = sum(max(c, 0.0) ** 2 for c in q) ** 0.5
        d = out if out > 0 else max(q)
        if d < best_d:
            best, best_d = name, d
    return best


def relic_find_part(name, near=None):
    """Which relic has a barrier or point called `name`, or None.

    `near` is anything a suit can be traced from - a lifeform, a suit, or a console - and
    that suit's relic is asked first, because two relics may well both have a `door`.
    """
    prefer = _relic_of(near) if near is not None else None
    keys = ([prefer] if prefer else []) + [k for k in _RELIC_RECORDS if k != prefer]
    for key in keys:
        rec = _RELIC_RECORDS.get(key)
        if rec is None:
            continue
        if name in (rec.get("barriers") or {}) or name in (rec.get("points") or {}):
            return key
    return None


def _relic_of(thing):
    """The relic a suit - or the person in it, or the console flying it - is inside."""
    try:
        from .eva import KEY_RELIC, eva_suit_of
        from .inventory import get_inventory_value
        for probe in (thing, eva_suit_of(thing)):
            if probe is None:
                continue
            key = get_inventory_value(probe, KEY_RELIC, None)
            if key:
                return key
    except Exception:                                    # noqa: BLE001
        pass
    return None


def relic_finds(relic_key):
    """The things a relic put in the world that are still there, as `{part: [ids]}`.

    Matched by the `relic_key` / `relic_part` stamp `_relic_mark_placed` puts on everything
    it places, so a find is traced to its spot without guessing from names or positions."""
    from .query import to_object
    from .roles import role
    from .inventory import get_inventory_value
    out = {}
    for oid in role(RELIC_PLACED_ROLE):
        if get_inventory_value(oid, "relic_key", None) != relic_key:
            continue
        if to_object(oid) is None:
            continue
        part = get_inventory_value(oid, "relic_part", None)
        if part:
            out.setdefault(part, []).append(oid)
    return out


# --- the look: walls and set pieces ---------------------------------------------------------

#: The same numbers Open Universe dressed its relics with, now the library's defaults.
RELIC_WALL_DEPTH = 40.0
RELIC_GAPS = 0.06
RELIC_DEBRIS = 60
RELIC_PROPS = 600


def relic_walls(relic_key, n=RELIC_PROPS, roles="", wall_depth=RELIC_WALL_DEPTH,
                seed=None, name=None, setpieces=True):
    """Dress a built relic: its walls in the authored style, and its set pieces.
    Returns how many objects were made.

    The AMD-to-`volume_dress` mapping every mission was about to write for itself:
    `Walls:` (a fallback chain - `torgoth, plates`), `Art:`, per-part looks, `Plate:`,
    `Gaps:`, `Debris:`, `Seed:`. Then every part carrying `Dress:` gets its set piece, and
    a solid dressed that way is not ALSO dressed as a generic primitive.

    `roles` go on everything made, and are how the caller tears it down again. Not
    idempotent on its own - a caller guards on its role, the way Open Universe does.
    """
    from .volume_dress import volume_dress, DEFAULT_STYLE
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return 0
    vol = volume_get(relic_volume_name(rec, name))
    if vol is None:
        return 0
    made = 0
    skip = set()
    if setpieces:
        got, skip = relic_setpieces_place(relic_key, roles=roles, name=name)
        made += got

    def num(field, default, cast=float):
        value = rec.get(field)
        try:
            return cast(value) if value not in (None, "") else default
        except (TypeError, ValueError):
            return default
    made += volume_dress(
        vol, n=int(n), seed=int(seed if seed is not None else num("seed", 7, int)),
        roles=roles, wall_depth=float(wall_depth),
        plate=relic_plate_size(num("plate", 0.0)),
        gaps=min(max(num("gaps", RELIC_GAPS), 0.0), 1.0),
        debris=max(num("debris", RELIC_DEBRIS, int), 0),
        style=rec.get("walls") or DEFAULT_STYLE, art=rec.get("art"),
        part_styles=rec.get("part_walls"), part_art=rec.get("part_art"),
        solid_skip=skip)
    return made


#: The smallest and largest plate an author may ask for, in units. The automatic size is
#: clamped to 250..900; an authored one gets more room, but not unlimited: `Plate: 20` on
#: one ordinary box was 20,092 objects.
RELIC_PLATE_MIN = 150.0
RELIC_PLATE_MAX = 2000.0


def relic_plate_size(value):
    """An authored `Plate:` as the size the dresser will use. 0 means "work it out"."""
    try:
        size = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if size <= 0.0:
        return 0.0
    return min(max(size, RELIC_PLATE_MIN), RELIC_PLATE_MAX)


def relic_setpieces(relic_key):
    """Every part carrying `Dress:`, as `[{part, kind, dress, facing, solid_index}]`."""
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return []
    out = []
    for part, info in (rec.get("part_info") or {}).items():
        if info.get("dress"):
            out.append({"part": part, "kind": info.get("kind"), "dress": info["dress"],
                        "facing": info.get("facing"),
                        "solid_index": info.get("solid_index")})
    return out


def _relic_dress_pick(dress):
    """The first `(art, size)` in a `Dress:` list the engine knows, or (None, 1.0)."""
    from .volume_dress import _known_art
    for art, mult in dress or ():
        if _known_art([art]):
            return art, float(mult) if mult else 1.0
    return None, 1.0


def _relic_facing(rec, relic_key, spec, pos, base):
    """Which way a set piece looks, flattened so it stays upright: `Facing:` a named
    place, or `Facing: x, y, z` as a direction; else the middle of the room it stands in.
    """
    target = None
    if spec:
        nums = _amd_relic_numbers(spec)
        if len(nums) >= 3 and not _amd_relic_words(spec):
            d = (nums[0], 0.0, nums[2])
            return d if abs(d[0]) + abs(d[2]) > 1e-6 else (0.0, 0.0, 1.0)
        target = relic_point(relic_key, spec) or _relic_part_pos(rec, spec, base)
        if target is None and spec in (rec.get("props") or {}):
            pr = rec["props"][spec]
            target = (base[0] + pr[0], base[1] + pr[1], base[2] + pr[2])
    if target is None:
        room = relic_part_at(relic_key, pos)
        target = _relic_part_pos(rec, room, base) if room else None
    if target is not None:
        d = (target[0] - pos[0], 0.0, target[2] - pos[2])
        if abs(d[0]) + abs(d[2]) > 1e-6:
            return d
    return (0.0, 0.0, 1.0)


def relic_setpieces_place(relic_key, roles="", name=None):
    """Place a relic's set pieces. Returns `(made, solid_indices_dressed)`.

    A POINT or a PROP gets its piece standing upright on the spot, facing its `Facing:`
    (else the middle of its room). A SOLID gets its piece fitted to the solid's size, so
    the cradle a route already skirts is drawn as the cradle rather than as a grey cube -
    turned the same way, and fitted AFTER the turn. Size is the kit's scale for a kit
    piece, times the optional number after the key.
    """
    from .volume import volume_look_quat
    from .volume_dress import _dress_finish, _mesh_size
    from .spawn import terrain_spawn
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None:
        return 0, set()
    base = relic_pos(rec)
    made, skip = 0, set()
    for sp in relic_setpieces(relic_key):
        art, mult = _relic_dress_pick(sp["dress"])
        if art is None:
            # Nothing known: the part keeps its default look - and SAYS so. A set piece
            # is one object the author put somewhere on purpose; one that silently is
            # not there reads as a bug in the game, not a typo in a key.
            names = ", ".join(str(a) for a, _m in (sp.get("dress") or ()))
            _relic_say(f"relic '{relic_key}': `Dress: {names}` on '{sp.get('part')}' "
                       f"names no art the game has, so nothing is placed there. A key "
                       f"has no file extension, and a wall kit is not a set piece.")
            continue
        size = _mesh_size(art, (100.0, 100.0, 100.0))
        kit_scale = 1.0
        try:
            from .volume_kit import volume_kit, volume_kit_piece
            piece = volume_kit_piece(art)
            kit = volume_kit(piece.get("kit")) if piece else None
            if kit is not None:
                kit_scale = kit["scale"]
        except Exception:                                # noqa: BLE001
            pass
        facing, scale, pos, up_axis = (0.0, 0.0, 1.0), None, None, None
        if sp["kind"] in ("point", "prop"):
            if sp["kind"] == "point":
                pos = relic_point(relic_key, sp["part"])
            else:
                pr = (rec.get("props") or {}).get(sp["part"])
                pos = (base[0] + pr[0], base[1] + pr[1], base[2] + pr[2]) if pr else None
            if pos is None:
                continue
            facing = _relic_facing(rec, relic_key, sp.get("facing"), pos, base)
            s = kit_scale * mult
            scale = (s, s, s)
        elif sp["kind"] == "solid" and sp.get("solid_index") is not None:
            solid = rec.get("solids")[sp["solid_index"]]
            kind, nums = solid[0], [float(v) for v in solid[1:]]
            if kind == "box" and len(nums) >= 6:
                pos = (base[0] + nums[0], base[1] + nums[1], base[2] + nums[2])
                facing = _relic_facing(rec, relic_key, sp.get("facing"), pos, base)
                # Turned a quarter, the piece's width runs along the other axis - fit it
                # in the box it will actually occupy.
                sx, sy, sz = size
                if abs(facing[0]) > abs(facing[2]):
                    sx, sz = sz, sx
                s = min(2.0 * nums[3] / sx, 2.0 * nums[4] / sy, 2.0 * nums[5] / sz) * mult
                scale = (s, s, s)
            elif kind == "sphere" and len(nums) >= 4:
                pos = (base[0] + nums[0], base[1] + nums[1], base[2] + nums[2])
                facing = _relic_facing(rec, relic_key, sp.get("facing"), pos, base)
                s = 2.0 * nums[3] / max(size) * mult
                scale = (s, s, s)
            elif kind == "capsule" and len(nums) >= 7:
                a = (base[0] + nums[0], base[1] + nums[1], base[2] + nums[2])
                b = (base[0] + nums[3], base[1] + nums[4], base[2] + nums[5])
                pos = tuple((a[i] + b[i]) * 0.5 for i in range(3))
                axis = tuple(b[i] - a[i] for i in range(3))
                length = sum(v * v for v in axis) ** 0.5
                if size[1] >= size[2]:
                    # A TALL piece - a column, a pillar - stands along the capsule: its
                    # local +Y up the axis, facing whichever way is across it. Laid on
                    # +Z like a span, a column through a room lies on its side.
                    across = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 * length else \
                        (1.0, 0.0, 0.0)
                    up_axis = axis
                    # Square the facing to the axis, so it is the AXIS that is exact:
                    # `volume_look_quat` keeps the facing and bends `up` to fit it.
                    u = tuple(v / (length or 1.0) for v in axis)
                    d = sum(across[i] * u[i] for i in range(3))
                    facing = tuple(across[i] - d * u[i] for i in range(3))
                    scale = (2.0 * nums[6] / size[0] * mult,
                             (length + 2.0 * nums[6]) / size[1] * mult,
                             2.0 * nums[6] / size[2] * mult)
                else:
                    # Lying along the span: its local +Z down the capsule's axis.
                    up_axis = None
                    facing = axis
                    scale = (2.0 * nums[6] / size[0] * mult,
                             2.0 * nums[6] / size[1] * mult,
                             (length + 2.0 * nums[6]) / size[2] * mult)
            if scale is not None:
                skip.add(sp["solid_index"])
        if pos is None or scale is None:
            continue
        try:
            p = terrain_spawn(pos[0], pos[1], pos[2], "", ("#," + roles) if roles else "#",
                              art, "behav_asteroid")
            if p is None:
                continue
            try:
                import sbs
                w, qx, qy, qz = volume_look_quat(facing, up_axis or (0.0, 1.0, 0.0))
                p.engine_object.rot_quat = sbs.quaternion(w, qx, qy, qz)
            except Exception:                            # noqa: BLE001
                pass
            p.blob.set("local_scale_x_coeff", scale[0], 0)
            p.blob.set("local_scale_y_coeff", scale[1], 0)
            p.blob.set("local_scale_z_coeff", scale[2], 0)
            _dress_finish(p)
            made += 1
        except Exception as e:                           # noqa: BLE001
            log(f"relic '{relic_key}': set piece '{art}' at '{sp['part']}' failed: {e}",
                "relics", "warning")
    return made, skip


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
    # Did relic_spawn dress it? Then the walls are ours to move with the space.
    spawned = rec.get("spawned")

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
    if spawned:
        setattr(rec, "spawned", spawned)
        try:
            relic_redress(key)
        except Exception as e:                          # noqa: BLE001
            _relic_say(f"relic '{key}': the walls were not rebuilt: {e}")
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
# How close a ship has to get before a named place lights up on the radar. Roughly a
# room: near enough that you are IN the place rather than passing it at range, far enough
# that you do not have to fly through the exact point to be credited with finding it.
# `relic_contents_arm(reveal=0)` turns the whole behaviour off.
RELIC_REVEAL_RANGE = 1200.0

# Gold, the same color the library's own map markers use - a place the crew has found
# should read as map furniture, not as a contact.
RELIC_MARK_COLOR = "gold"

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


def relic_contents_arm(relic_key, radius_default=900.0,
                       reveal=RELIC_REVEAL_RANGE):
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
    _relic_place_role_markers(rec, relic_key, reveal=reveal)
    waiting = _relic_arm_barriers(rec, relic_key)
    # A SHUT BARRIER GETS A BODY. Arming is where the ruin stops being geometry and starts
    # being things, and a barrier with no object is a door a beam cannot touch.
    relic_barriers_spawn(relic_key)
    # And a repair job gets a marker and a place on the web - but severs nothing.
    relic_repairs_spawn(relic_key)
    taken = _relic_ledger_has(relic_key, "taken")
    fired = _relic_ledger_has(relic_key, "placed")
    for c in relic_contents(relic_key):
        key = (relic_key, c["part"])
        if key in _ARMED:
            continue
        # THE PIECE THE CREW TOOK IS NOT PUT BACK. The ledger outlives the system being
        # torn down, so coming back the same evening - or tomorrow, from a save - finds
        # the room as it was left. Nothing else of that record is placed either: what
        # guarded the piece guarded it.
        if c["part"] in taken:
            _ARMED[key] = {"done": True, "taken_before": True}
            continue
        trig = _relic_trigger(c.get("starts_when"))
        # A record whose trigger ALREADY FIRED on an earlier visit is simply there: the
        # signal it waited for was sent once and will not be sent again.
        if trig is None or c["part"] in fired:
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


def _relic_arm_barriers(rec, relic_key):
    """Arm every `Barrier:` that has an `Opens when:`. Returns how many are waiting.

    A barrier with no trigger is a hard block: it opens when somebody CUTS it, and that is
    the weapons app's business, not a clock's. One with a trigger is armed on the same
    shared tick as the contents, using the same `amd_trigger` grammar - so an author has
    one vocabulary for "when does this happen", not two.
    """
    waiting = 0
    opened = _relic_ledger_has(relic_key, "opened")
    for name, b in (rec.get("barriers") or {}).items():
        key = ("barrier", relic_key, name)
        if key in _ARMED:
            continue
        if name in opened:
            # Opened on an earlier visit: nothing to wait for.
            _ARMED[key] = {"kind": "barrier", "done": True, "relic": relic_key,
                           "barrier": name}
            continue
        phrase = b[4] if len(b) > 4 else None
        trig = _relic_trigger(phrase)
        if trig is None:
            # No trigger is not an error. It means the only way through is to open it.
            _ARMED[key] = {"kind": "barrier", "done": True, "relic": relic_key,
                           "barrier": name}
            continue
        kind = trig[0] if isinstance(trig, (list, tuple)) else None
        if kind not in RELIC_TRIGGERS:
            log(f"relic '{relic_key}': barrier '{name}' waits on '{phrase}', which a "
                f"relic cannot watch - it will never open on its own", "relics", "warning")
        _ARMED[key] = {"kind": "barrier", "done": False, "trig": trig,
                       "relic": relic_key, "barrier": name, "radius_default": 900.0}
        waiting += 1
    return waiting


def _relic_reveal_tick():
    """Light up the markers the crew has reached. The ruin drawing its own map.

    Runs on the same shared tick as the contents triggers, and for the same reason: one
    tick for every relic beats a watcher per point.

    A revealed marker STAYS revealed - it is a record of where the crew has been, which is
    the whole value of it in a structure where every room looks like the last one.
    """
    from .query import to_object_list
    from .roles import any_role
    # `key` below is the armed marker's ("marker", relic, point) tuple - the reveal needs
    # both halves of it to tell the web which node has just been found.
    posts = [(k, v) for k, v in _ARMED.items()
             if len(k) == 3 and not v.get("shown") and v.get("pos") is not None
             and (v.get("reveal") or 0) > 0]
    if not posts:
        return
    # EVA SUITS REVEAL TOO, and leaving them out gutted the feature they exist for. A
    # suit is a player hull with `__player__` deliberately REMOVED - that is what keeps
    # six boarders out of NPC targeting and the end-game checks - so a party could fly a
    # ruin from end to end and light up nothing at all. The crew's Nav list stayed at the
    # one marker their SHIP had passed on the way in, which reads as the relic having only
    # one place in it.
    players = to_object_list(any_role("__player__,eva_suit"))
    if not players:
        return
    for key, rec in posts:
        r = float(rec.get("reveal") or RELIC_REVEAL_RANGE)
        r2 = r * r
        p0 = rec["pos"]
        near = None
        for p in players:
            pp = p.pos
            dx, dy, dz = pp.x - p0[0], pp.y - p0[1], pp.z - p0[2]
            if dx * dx + dy * dy + dz * dz <= r2:
                near = p
                break
        if near is not None:
            _relic_light(key, rec, by=near)


def _relic_light(key, rec, by=None):
    """Light one armed marker, find its place on the web, and say so. Idempotent.

    `key` is the armed ("marker", relic, point) tuple. `by` is whoever came near enough -
    a ship, a suit, or None when a story beat revealed it (`relic_reveal_point`).
    """
    from .query import to_object, to_id
    if rec.get("shown"):
        return False
    rec["shown"] = True
    obj = to_object(rec.get("id"))
    if obj is None:
        return False               # gone; nothing to light
    try:
        # `data_set`, not `blob`. They are the SAME store under two names - a spawn
        # hands back SpawnData whose `.blob` IS the agent's `data_set` - but only the
        # id survives to here, and what an id resolves to is the agent. Reaching for
        # `.blob` on it raises, inside a try, which would have made every marker
        # quietly refuse to light.
        obj.data_set.set("unselectable", 0, 0)
        obj.data_set.set("radar_color_override", RELIC_MARK_COLOR, 0)
    except Exception as e:
        log(f"relic marker would not light: {e}", "relics", "warning")
    # A `Hidden:` place is off the destination list until it is FOUND, and reaching it
    # is what finds it. An ordinary place was never hidden, so this is a no-op there.
    try:
        from .rails import rail_reveal
        owner = _RELIC_RECORDS.get(key[1])
        if owner is not None:
            rail_reveal(relic_volume_name(owner), key[2])
    except Exception:
        pass
    # SOMETHING TO HANG A BEAT ON. The marker lighting was the one moment in a ruin with
    # no signal - a place first seen, which is exactly when a crew member says "what is
    # that". `RELIC_SUIT` tells a crew member's discovery from the ship's sensors.
    by_id = to_id(by) if by is not None else None
    suit = False
    if by_id is not None:
        try:
            from .roles import has_role
            suit = bool(has_role(by_id, "eva_suit"))
        except Exception:                                # noqa: BLE001
            suit = False
    signal_emit("relic_marker_lit", {"RELIC_KEY": key[1], "RELIC_POINT": key[2],
                                     "RELIC_BY": by_id, "RELIC_SUIT": suit})
    return True


def relic_reveal_point(relic_key, name):
    """Reveal a place on cue - what a scene's `reveal <point>` does, and a mission's
    story beat can too. Lights its marker when it has one, and puts a `Hidden:` place on
    the destination list either way. True when anything changed.
    """
    rec = _RELIC_RECORDS.get(relic_key)
    if rec is None or name not in (rec.get("points") or {}):
        return False
    changed = False
    armed = _ARMED.get(("marker", relic_key, name))
    if armed is not None:
        changed = _relic_light(("marker", relic_key, name), armed)
    try:
        from .rails import rail_is_hidden, rail_reveal
        vol = relic_volume_name(rec)
        if rail_is_hidden(vol, name):
            changed = bool(rail_reveal(vol, name)) or changed
    except Exception:                                    # noqa: BLE001
        pass
    return changed


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

def _relic_place_role_markers(rec, relic_key, reveal=None):
    """Put a measuring post at every point carrying `Roles:`.

    This is the plumbing behind `Starts when: reach <role>`. The quest driver's reach test
    measures a player against OBJECTS HOLDING A ROLE, so a role written on a point is only
    half the sentence until something is standing there. An author should never have to
    know that, so arming supplies the other half.

    IT STARTS INVISIBLE AND EARNS ITS PLACE ON THE RADAR. These were `marker_object`s at
    first - selectable, radar-gold - which put a blip on every room, every cache and every
    trigger the moment the ruin was built. A dungeon that draws its own floor plan is not a
    dungeon; the crew arrives already knowing which rooms matter and where the treasure is.

    Invisible for good is no better - the crew has no record of where they have been, in a
    structure whose whole problem is that it all looks alike. So a post is dark until a
    ship reaches it, and then it lights up and stays lit: the ruin draws its own map, in
    the order you fly it. `_relic_reveal_tick` is the other half.

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
        pos = (base[0] + pt[0], base[1] + pt[1], base[2] + pt[2])
        label = pt[4] if len(pt) > 4 and pt[4] else name
        try:
            # Named at SPAWN: an invisible object's name costs nothing, and it is the
            # label the marker wears the moment it is revealed.
            obj = terrain_spawn(pos[0], pos[1], pos[2], str(label),
                                "#," + ",".join(["relic_marker"] + list(roles)),
                                "generic-sphere", "behav_selection")
            obj.data_set.set("elite_main_scn_invis", 1, 0)
            obj.data_set.set("unselectable", 1, 0)
            # A prop with a radius pushes ships around; a measuring post must not.
            obj.engine_object.exclusion_radius = 0
        except Exception as e:
            log(f"relic '{relic_key}': could not mark point '{name}': {e}",
                "relics", "warning")
            continue
        _ARMED[key] = {"done": True, "id": getattr(obj, "id", None),
                       "pos": pos, "shown": False, "reveal": reveal}


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
    _relic_attach_content(c, pos)


def _relic_attach_content(c, pos):
    """Put a placed thing ON THE RAIL WEB, so it is somewhere you can be SENT.

    This is what makes a cache a destination rather than something you happen to fly past.
    A relic's contents do not all exist when the ruin is built - `Starts when: reach ...`
    places one the first time somebody gets near the room - so the web is joined to rather
    than resolved again.

    A content hanging off a POINT is already a node under the author's own key; only one
    on a chamber or a box needs its own.
    """
    rec = _RELIC_RECORDS.get(c.get("relic"))
    if rec is None:
        return
    part = c.get("part")
    if part in (rec.get("points") or {}):
        return
    try:
        from .rails import rail_attach
        rail_attach(relic_volume_name(rec), part, pos, roles=tuple(c.get("roles") or ()),
                    display=part)
    except Exception as e:
        log(f"relic contents: '{part}' could not join the rail web: {e}",
            "relics", "warning")


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
    for r in [RELIC_PLACED_ROLE] + list(c.get("roles") or []):
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
    # A PIECE IS WATCHED, so `<relic>_taken` is sent when it leaves - see
    # `_relic_taken_tick`. Keyed ("piece", relic, id): a three-part key with the relic
    # second, the shape `relic_contents_clear(key)` already forgets a relic by.
    if RELIC_PIECE_ROLE in (c.get("roles") or []) and c.get("relic"):
        _ARMED[("piece", c.get("relic"), obj.id)] = {
            "kind": "piece", "done": True, "id": obj.id, "relic": c.get("relic"),
            "part": c.get("part"), "item": c.get("item"), "taken": False}


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
    """Place every armed record whose trigger has now fired, and light up the places the
    crew has reached."""
    _relic_reveal_tick()
    _relic_taken_tick()
    pending = [(k, v) for k, v in _ARMED.items() if not v.get("done")]
    if not pending:
        return
    for key, rec in pending:
        if not _relic_trigger_fired(rec):
            continue
        if rec.get("kind") == "barrier":
            _relic_open_barrier(rec)
        else:
            _relic_place_contents(rec["content"])
            _relic_ledger_note(rec["content"].get("relic"), "placed",
                               rec["content"].get("part"))
        rec["done"] = True


# --- what a ruin REMEMBERS ---------------------------------------------------------------
#
# `_ARMED` is what is standing in a ruin RIGHT NOW, and `relic_release` forgets it - it
# has to, the objects are gone. So a galaxy that tears a system down behind the crew
# rebuilt the ruin from its file on the way back: every barrier shut again, every repair
# undone, and the piece the crew had carried out sitting where it had always been.
#
# The LEDGER is what has HAPPENED there: which barriers were opened, which repairs were
# done, which pieces were taken, and which waiting contents have had their trigger. It is
# keyed by relic and by the author's own part names, never by object ids; it outlives a
# release, for the length of the mission; and arming CONSULTS it, so a ruin is rebuilt as
# it was left. A saved game writes it down and hands it back (the state provider below),
# which is the same thing over a longer gap.
#
# RESTORED STATE IS NOT NEWS. Nothing that reads the ledger sends a signal or grants
# anything: the barrier is simply open, the piece simply is not there. `<barrier>_opened`,
# `<relic>_taken` and `<key>_repaired` were sent when it happened and are not sent again.
_LEDGER = {}            # relic key -> {"opened": set, "repaired": set, "taken": set, "placed": set}
_LEDGER_KINDS = ("opened", "repaired", "taken", "placed")


class _RelicNothingToPlace(Exception):
    """A repair that was done on an earlier visit and has no furniture to stand as."""


def _relic_ledger_has(relic_key, kind):
    """The part names of one kind remembered for a relic. An empty set when none."""
    return (_LEDGER.get(relic_key) or {}).get(kind) or frozenset()


def _relic_ledger_note(relic_key, kind, name):
    if relic_key is None or not name:
        return False
    names = _LEDGER.setdefault(relic_key, {}).setdefault(kind, set())
    if name in names:
        return False
    names.add(name)
    try:
        from .persistence import persist_provider_touch
        persist_provider_touch("relics")
    except Exception:                                    # noqa: BLE001
        pass
    return True


def _relic_ledger_open_web(relic_key, volume):
    """Open, on a freshly solved web, every barrier the ledger says was opened."""
    opened = _relic_ledger_has(relic_key, "opened")
    if not opened:
        return 0
    from .rails import rail_barrier_open
    return sum(1 for name in opened if rail_barrier_open(volume, name))


def relic_ledger(relic_key=None):
    """What has happened in a ruin - or in every ruin - as plain sorted lists.

    `{"opened": [...], "repaired": [...], "taken": [...], "placed": [...]}` for one
    relic, `{relic key: {...}}` for all of them. `taken` and `placed` name the PART a
    content record hangs off. What a report, a test or a mission asks; the ruin does
    not have to be standing.
    """
    def plain(entry):
        return {k: sorted(entry.get(k) or ()) for k in _LEDGER_KINDS if entry.get(k)}
    if relic_key is not None:
        return plain(_LEDGER.get(relic_key) or {})
    return {key: plain(entry) for key, entry in _LEDGER.items() if plain(entry)}


def relic_ledger_forget(relic_key=None):
    """Forget what happened in one ruin - or in all of them, with no key.

    For a ruin that RESETS: one that is meant to be a different ruin each time it is
    found. The next build is from the file. The quest signals it sent stay sent.
    """
    if relic_key is None:
        _LEDGER.clear()
    else:
        _LEDGER.pop(relic_key, None)


def relic_ledger_count():
    """Reset-ledger probe: how many things ruins are remembering."""
    return sum(len(names) for entry in _LEDGER.values() for names in entry.values())


def _relic_state_snapshot():
    """The state provider's half: the ledger, and the quest signals already sent."""
    out = {}
    ruins = relic_ledger()
    if ruins:
        out["ruins"] = ruins
    if _QUEST_SENT:
        out["sent"] = sorted(_QUEST_SENT)
    return out


def _relic_state_restore(blob):
    """REPLACE the ledger with what a save says. Lazy: no ruin is touched, and the next
    one armed reads it. Announces nothing."""
    _LEDGER.clear()
    _QUEST_SENT.clear()
    if not isinstance(blob, dict):
        return
    for key, entry in (blob.get("ruins") or {}).items():
        if not isinstance(entry, dict):
            continue
        kept = {kind: {str(n) for n in (entry.get(kind) or ())}
                for kind in _LEDGER_KINDS if entry.get(kind)}
        if kept:
            _LEDGER[str(key)] = kept
    for name in (blob.get("sent") or ()):
        _QUEST_SENT.add(str(name))


from .persistence import persist_provider_register as _persist_provider_register  # noqa: E402
_persist_provider_register("relics", _relic_state_snapshot, _relic_state_restore,
                           library=True)


# --- the quest signals a ruin sends by itself --------------------------------------------
#
# Three story beats belong to the RUIN rather than to any one mission, so the library
# sends them: a way opened (`<barrier key>_opened`), the piece carried out
# (`<relic key>_taken`) and a job done (`<repair key>_repaired`). A quest waits on one
# with `Done when: signal shaft_grate_opened` and no mission code is involved.
#
# ONCE EACH, per mission. A piece that leaves the volume and is then reeled in is one
# event, and a mission that still sends the same name from a route of its own is harmless
# rather than a double count. Names, not objects: the name is what a quest hears.
_QUEST_SENT = set()


def relic_quest_signal(name):
    """Send a quest signal on a relic's behalf, once per mission. True when it was sent.

    `signal_emit("quest_signal", {"SIGNAL_NAME": name})` - the line a quest's
    `Done when: signal <name>` hears. Called from a tick or from another signal's
    handler, which is always the server, so it is sent once whatever the console count.
    """
    from .amd import amd_signal_name
    name = amd_signal_name(name)
    if not name or name in _QUEST_SENT:
        return False
    _QUEST_SENT.add(name)
    signal_emit("quest_signal", {"SIGNAL_NAME": name})
    return True


def relic_quest_signal_sent(name):
    """Whether a relic already sent this quest signal. What a test or a report asks."""
    from .amd import amd_signal_name
    return amd_signal_name(name) in _QUEST_SENT


def relic_quest_signal_count():
    """Reset-ledger probe: quest signals relics have sent this mission."""
    return len(_QUEST_SENT)


def _relic_piece_taken(rec):
    """One watched piece is out of its ruin: say so, once, and stop watching it."""
    if rec.get("taken"):
        return False
    rec["taken"] = True
    relic_key = rec.get("relic")
    if rec.get("part"):
        _relic_ledger_note(relic_key, "taken", rec.get("part"))
    signal_emit("relic_piece_taken", {"RELIC_KEY": relic_key,
                                      "RELIC_PIECE": rec.get("id"),
                                      "RELIC_ITEM": rec.get("item")})
    relic_quest_signal(str(relic_key) + "_taken")
    return True


def _relic_taken_tick():
    """Send `<relic>_taken` for every piece that has LEFT its ruin.

    Asked of the piece, not of the ship towing it: see `relic_holds`. A piece whose
    object is gone is NOT taken by that alone - it may have been destroyed, or torn down
    with its system - so it is only marked as gone, and `relic_piece_collected` is what
    says it was picked up. A relic whose space is not standing is skipped rather than
    read as "outside": `relic_holds` answers False for both, and only one is an exit.
    """
    from .query import to_object
    for rec in list(_ARMED.values()):
        if rec.get("kind") != "piece" or rec.get("taken") or rec.get("gone"):
            continue
        obj = to_object(rec.get("id"))
        if obj is None:
            rec["gone"] = True
            continue
        owner = _RELIC_RECORDS.get(rec.get("relic"))
        if owner is None or volume_get(relic_volume_name(owner)) is None:
            continue
        p = obj.pos
        if not relic_holds(rec.get("relic"), (p.x, p.y, p.z)):
            _relic_piece_taken(rec)


def relic_piece_collected(item_key, item_id=None):
    """A pickup was collected: if it was a relic's piece, send `<relic>_taken`.

    What an `item_collected` route calls, with the signal's `key` and - when the sender
    carries it - the id of the pickup itself. REELING A PIECE IN from a suit collects and
    deletes it while it is still inside the ruin, so it never "leaves the volume"; without
    this the crew would hold the piece and the quest would wait forever.

    Matched by id when there is one, else by the item key against pieces not yet taken.
    Returns the relic key whose piece it was, or None - so a route can hand it every
    pickup without asking first.
    """
    for rec in list(_ARMED.values()):
        if rec.get("kind") != "piece" or rec.get("taken"):
            continue
        if item_id is not None:
            if rec.get("id") != item_id:
                continue
        elif not item_key or rec.get("item") != item_key:
            continue
        _relic_piece_taken(rec)
        return rec.get("relic")
    return None


def relic_pieces(relic_key=None, taken=None):
    """The ids of the pieces relics have placed - one relic's, or every one's.

    `taken=True` / `taken=False` narrows to the ones already out, or still inside.
    """
    out = []
    for rec in _ARMED.values():
        if rec.get("kind") != "piece":
            continue
        if relic_key is not None and rec.get("relic") != relic_key:
            continue
        if taken is not None and bool(rec.get("taken")) != bool(taken):
            continue
        out.append(rec.get("id"))
    return out


def _relic_open_barrier(rec):
    """Open one barrier and say so, so a suit holding for a shut way re-plans at once."""
    owner = _RELIC_RECORDS.get(rec.get("relic"))
    if owner is None:
        return
    from .rails import rail_barrier_open
    volume = relic_volume_name(owner)
    if rail_barrier_open(volume, rec.get("barrier")):
        _relic_ledger_note(rec.get("relic"), "opened", rec.get("barrier"))
        signal_emit("rail_opened", {"RAIL_VOLUME": volume,
                                    "RAIL_RELIC": rec.get("relic"),
                                    "RAIL_BARRIER": rec.get("barrier")})
        relic_quest_signal(str(rec.get("barrier")) + "_opened")


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
    from .roles import any_role, role
    want = args.get("role")
    if not want:
        return False
    # A SUIT COUNTS AS ARRIVING. A boarding party reaching the core IS the beat, and a
    # suit carries `eva_suit` precisely because `__player__` was taken off it.
    players = to_object_list(any_role("__player__,eva_suit"))
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
    _QUEST_SENT.clear()
    _LEDGER.clear()
    _ARM_TASK = None
    from .signal import signal_unobserve
    signal_unobserve(_relic_signal_observer)


def relics_clear():
    """Drop every registered relic record. Called by reset_mission_state()."""
    _RELIC_RECORDS.clear()
    _RELIC_TEXT.clear()
    relic_contents_clear()


def relics_count():
    """Number of registered relic records. The reset-ledger probe."""
    return len(_RELIC_RECORDS)


def relic_contents_count():
    """How many content records are armed. The reset-ledger probe - an armed record that
    survives a mission reset would place loot in the NEXT mission."""
    return len(_ARMED)
