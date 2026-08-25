"""A RACE is a shipData ``origin`` - derived from the hulls that exist, not declared.

WHY THIS EXISTS. Until now a race was a LITERAL STRING that missions branched on.
LegendaryMissions' maps carry ``enemyTypeNameList = ["Kralien", "Torgoth", "Arvonian",
"Ximni"]`` and three parallel ``if enemy1 == "Kralien":`` chains apiece, choosing an enemy
station hull, a roles string and a face generator. Nothing reads data, so a mod could not add
a race to those maps at all - it could only ALIAS onto one of the four. That is why every one
of the TNG pack's five theaters rosters the same four stock names and differs only in its
``Art:`` costume, while the pack itself ships EIGHT factions with their own hulls, fleet
ladders, sides and faces.

THE KEY IS ALREADY IN THE DATA. Every hull, stock or modded, carries ``origin`` in shipData,
and ``SpaceObject.race`` already IS ``origin``. So a race does not need declaring: it exists
because hulls exist. That makes mod and stock races one namespace with no aliasing, and a
roster mixing them - ``klingon, romulan, kralien`` - simply spells them.

WHAT DERIVES, AND THE ONE THAT SURPRISES. The station hull each map hardcodes turns out to be
exactly *the hull whose origin is that race and whose roles contain* ``station``::

    kralien  -> starbase_kralien    torgoth -> starbase_torgoth
    arvonian -> starbase_arvonian   skaraan -> starbase_skaraan
    ximni    -> NONE                pirate  -> NONE

Which explains a thing that read as arbitrary: borderwar and deepstrike list THREE races, not
four, because they spawn enemy stations and ximni has no starbase. That was never a design
choice about ximni - it is this constraint, written out by hand. :func:`race_has_station` is
the filter those maps want, so the rule is stated once instead of encoded in five literals.

DECLARING IS FOR OVERRIDES ONLY. A ``races.amd`` supplies the four things the ship table
cannot say - a station's name prefix, which FACE race crews it, the call-sign letters, and a
fleet-size multiplier - and nothing else. Absent means derived. A mod that ships hulls has
already registered its races; the file is optional.
"""
from ..mast.mast_node import MastDataObject
from .amd import amd_parse_facts, amd_read_text


# Origins that name something other than a playable or raidable people. `monster` and
# `roklithoid` are stock (the space monster, and asteroids), and the rest are the engine's
# own bookkeeping rows. Filtered here rather than at each call site, because every caller
# wants "races" and none of them wants to remember that asteroids have an origin.
NON_RACE_ORIGINS = frozenset((
    "monster", "roklithoid", "generic", "cursor", "unknown",
    "pickup", "asteroid", "wreck", "no origin", "",
))

# Per-mission registry of the OVERRIDE records. Derived facts are not cached here - they come
# from the ship table, which has its own reset. `cosmos_dev` reuses one interpreter across
# missions, so this is cleared from reset_mission_state(); probe registered in handlerhooks.
_races = {}


def races_clear():
    """Drop every declared race override. Called from reset_mission_state()."""
    _races.clear()


def races_count():
    """How many race overrides are declared - the reset-ledger probe."""
    return len(_races)


def _norm(value):
    """A race key, lowercased and stripped. Empty string for nothing."""
    return str(value or "").strip().lower()


# ---------------------------------------------------------------------------
# derived: what the ship table already knows
# ---------------------------------------------------------------------------

def _entries():
    """Every ship-table entry, or [] when no table is loaded.

    Deliberately does NOT force the load. `get_ship_data()` caches on first call, so asking
    it here would make merely COUNTING a race's hulls flip `ship_data_is_loaded()` to true
    for everything downstream - and that probe is what the depth guard uses to tell "this
    roster is too thin" from "I cannot judge yet". Answering "nothing known" is correct
    before the table exists; manufacturing a load to answer is not.
    """
    from .ship_data import get_ship_data, ship_data_is_loaded
    if not ship_data_is_loaded():
        return []
    data = get_ship_data()
    if not data:
        return []
    return data.get("#ship-list") or []


def _is_station(entry):
    """Whether an entry is a station, by its ROLES string.

    Matches `_side_split`'s rule deliberately, and for its reason: a ``role="ship"`` filter
    silently skips hulls that do not carry one - `arvonian_fighter` is `cockpit,fighter` -
    which shows up as "most of the faction converted and a few ships are still stock".
    """
    return "station" in str(entry.get("roles") or "").lower()


def race_list():
    """Every race the loaded ship table knows, sorted. Empty when nothing is loaded.

    This is the roster a mod joins by EXISTING. Ship a hull with ``origin: Klingon`` and
    `klingon` is a race here, with no registration call and no settings entry.
    """
    out = set()
    for entry in _entries():
        origin = _norm(entry.get("origin"))
        if origin and origin not in NON_RACE_ORIGINS:
            out.add(origin)
    return sorted(out)


def race_exists(race):
    """Whether any hull carries this origin."""
    return _norm(race) in set(race_list())


def race_hulls(race):
    """A race's MOBILE hull keys, sorted. Stations excluded."""
    want = _norm(race)
    return sorted(e.get("key") for e in _entries()
                  if _norm(e.get("origin")) == want and not _is_station(e) and e.get("key"))


def race_station_hulls(race):
    """A race's STATION hull keys, sorted. Empty when it has none."""
    want = _norm(race)
    return sorted(e.get("key") for e in _entries()
                  if _norm(e.get("origin")) == want and _is_station(e) and e.get("key"))


def race_station_hull(race):
    """The hull a map should spawn as this race's starbase, or None.

    An explicit ``Station Hull:`` override wins; otherwise the race's first station hull.
    ``None`` is a real answer and means "this race has no starbase" - ximni and pirate both
    say it, which is what borderwar's and deepstrike's three-race literals were encoding.
    """
    rec = _races.get(_norm(race))
    if rec is not None and rec.get("station_hull"):
        return rec.get("station_hull")
    hulls = race_station_hulls(race)
    return hulls[0] if hulls else None


def race_has_station(race):
    """Whether this race can be spawned as an enemy station.

    The eligibility filter for the maps that build enemy starbases. Stated once here instead
    of hand-written as a shortened race list in each of them.
    """
    return race_station_hull(race) is not None


def race_hull_count(race):
    """How many MOBILE hulls a race fields - the depth-guard input.

    A faction with one hull in a heavy weight slot does not error; the same ship simply turns
    up all night, which reads as broken art rather than as a wrong roster.
    """
    return len(race_hulls(race))


def race_npc_list():
    """The races that can actually raid: in the ship table, enabled, and with a ladder.

    Three gates, because three different things can be missing and each is invisible on its
    own - a race with no hulls spawns nothing, a race left out of ``NPC_RACES`` was
    deliberately disabled, and a race with no fleet ladder makes `fleet_create` return None
    after printing. Intersecting them here means a caller gets a list every entry of which
    can actually be spawned.
    """
    from .settings import settings_race_is_npc
    from .fleet_tables import fleet_table_has
    return [r for r in race_list() if settings_race_is_npc(r) and fleet_table_has(r)]


# ---------------------------------------------------------------------------
# declared: the four things the ship table cannot say
# ---------------------------------------------------------------------------

# Every fence label a race record understands, in the normalized form the handler sees
# (lowercased, spaces -> underscores). Kept beside the handler because it has to move with
# it: a label accepted there and missing here would be reported as a typo.
_KNOWN_FIELDS = frozenset((
    "station_prefix", "prefix",
    "station_hull", "station",
    "faces", "face",
    "call_sign", "call_signs", "callsign",
    "fleet_scale", "scale",
    "name", "desc",
))


def amd_race_facts():
    """amd_parse_facts handler for a race fence."""
    def handler(data, label, value):
        if label in ("station_prefix", "prefix"):
            data["station_prefix"] = str(value).strip()
        elif label in ("station_hull", "station"):
            data["station_hull"] = str(value).strip()
        elif label in ("faces", "face"):
            data["faces"] = str(value).strip()
        elif label in ("call_sign", "call_signs", "callsign"):
            data["call_sign"] = str(value).strip()
        elif label in ("fleet_scale", "scale"):
            try:
                data["fleet_scale"] = float(str(value).strip())
            except ValueError:
                data["fleet_scale"] = 1.0
        elif label in ("name", "desc"):
            data[label] = str(value).strip()
        else:
            return None
        return True
    return handler


def amd_race_data(text):
    """Parse one race fence into a data dict."""
    return amd_parse_facts(text, amd_race_facts())


def races_from_section(node):
    """Race records from a node whose children are the race headings."""
    out = []
    if node is not None:
        for n in node.get("children", []):
            data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
            # A field this file does not understand is DROPPED, and dropping it silently is
            # how a typo reads as accepted and changes nothing. Reported at declare time
            # because these headings carry no section name, so `sbs lint` cannot resolve
            # them to an archetype and calls the file clean whatever is in it.
            unknown = sorted(k for k in data if k not in _KNOWN_FIELDS)
            if unknown:
                print("race '" + str(n.get("key")) + "': unknown field(s) "
                      + ", ".join(unknown) + " - ignored. Known fields: "
                      + ", ".join(sorted(_KNOWN_FIELDS)))
            out.append(MastDataObject({
                "key": _norm(n.get("key")),
                "name": data.get("name") or n.get("display_text"),
                "desc": data.get("desc") or ((n.get("description") or "").strip() or None),
                "station_prefix": data.get("station_prefix"),
                "station_hull": data.get("station_hull"),
                "faces": data.get("faces"),
                "call_sign": data.get("call_sign"),
                "fleet_scale": data.get("fleet_scale"),
            }))
    return out


def race_declare(records):
    """Register every race override record. Returns {key: record}.

    A later declaration of the same key REPLACES the earlier one, matching `side_create` and
    `theater_declare`, so a mission can override what an addon shipped.
    """
    for r in records or []:
        key = _norm(r.get("key"))
        if not key:
            continue
        _races[key] = r
    return dict(_races)


def race_declare_amd(doc):
    """Declare every race in a parsed AMD document."""
    return race_declare(races_from_section(doc))


def race_declare_text(content):
    """Declare races from AMD text already in hand.

    The call an ADDON wants: pair it with `media_read_relative_file`, which reads from inside
    a packaged `.mastlib` where `get_mission_dir_filename` cannot reach.
    """
    from .amd_doc import amd_document
    return race_declare_amd(amd_document(content, data_parser=amd_race_data))


def race_load_amd(file_path):
    """Load a race file relative to the mission folder and declare it.

    Bakes in ``data_parser=amd_race_data`` so a caller cannot omit it - the default AMD
    reader is YAML and would read these fields differently.
    """
    from ..fs import get_mission_dir_filename
    return race_declare_text(amd_read_text(get_mission_dir_filename(file_path)))


def race_get(race):
    """One race's override record, or None. Derived facts do not live here."""
    return _races.get(_norm(race))


def race_display_name(race):
    """A race's display name, falling back to its key capitalized."""
    rec = race_get(race)
    if rec is not None and rec.get("name"):
        return str(rec.get("name"))
    return _norm(race).capitalize()


def race_station_prefix(race):
    """The letters a map names this race's stations with (``KB 1``, ``TB 2``).

    Falls back to the race's first two letters upper-cased plus B, so an undeclared race gets
    a usable prefix rather than an empty one - a station called " 1" is worse than "KLB 1".
    """
    rec = race_get(race)
    if rec is not None and rec.get("station_prefix"):
        return str(rec.get("station_prefix"))
    key = _norm(race)
    return (key[:2].upper() + "B") if key else "XB"


def race_faces(race):
    """The FACE race whose portraits crew this race, defaulting to the race itself.

    Different namespaces: a Federation ship is crewed by `human`, not by `federation`, and the
    TNG pack has Breen hulls and no Breen faces. That is why it cannot be inferred.
    """
    rec = race_get(race)
    if rec is not None and rec.get("faces"):
        return str(rec.get("faces"))
    return _norm(race)


def race_call_sign(race):
    """The prefix letters this race's NPC call signs are drawn from, or None.

    None means "no opinion", and `name_random_hostile` then keeps its historical default.
    """
    rec = race_get(race)
    if rec is not None and rec.get("call_sign"):
        return str(rec.get("call_sign"))
    return None


def race_fleet_scale(race):
    """How many times the normal fleet count this race spawns. 1.0 unless declared.

    Ximni is the case it exists for: LM's maps carry ``if enemy == "Ximni": fleet_count *= 2``
    with the comment "Ximni fleets are typically only one ship". That is a fact about the
    race, not about the map, so all the maps that said it can stop saying it.
    """
    rec = race_get(race)
    if rec is not None and rec.get("fleet_scale"):
        try:
            return float(rec.get("fleet_scale"))
        except (TypeError, ValueError):
            return 1.0
    return 1.0
