"""Crew rosters - who is sitting at a console, and what they look like.

A console has always been able to carry a person's name: the picker asks for one, stores it
as ``CREW_NAME`` on the client agent, and the Director's ``<<crew_name>>`` overlay token and
the Gamemaster's message list read it back. Almost nobody fills it in, so almost every seat
on air reads ``unmanned``.

A ROSTER is a named set of people who can fill those seats without anyone typing. It comes
from an ``.amd`` file (see :mod:`sbs_utils.procedural.amd_crew`) and binds three ways, in
increasing specificity: a mod says "any Galaxy-class arrives with these people" (``Hull:``),
a mission says "the Enterprise uses this crew" (``Ship:``), and an operator picks one for the
game (``CREW_SELECT``). The player's own answer at the picker beats all three.

Two kinds of roster, declared by the ``By:`` field, because the two real uses want opposite
things:

``By: console``
    A CAST. Each member names a seat, so sitting at helm makes you Data. This is the
    Enterprise-D case, and it is what fills a Director bridge multiview with no player input.

``By: person``
    A GROUP. The console is irrelevant; you pick YOURSELF from the list and your name and
    face follow you to whatever seat you take. This is the "our gaming group, with our actual
    photographs" case.

Nothing here spawns anything. A crew member is a label on a seat occupied by a human, not an
agent in the world - which is why this is not a ``lifeform``.

**The live value stays where it was.** :func:`crew_assign` writes ``CREW_NAME`` with exactly
the meaning it has today, so every existing consumer keeps working untouched; the face,
portrait, rank and provenance arrive as additional keys beside it.

.. warning::
   **Never write a resolved name back to a client string.** ``sbs.set_client_string``
   persists per MACHINE in ``client_string_set.txt``. Writing "Data" there means a player who
   once sat helm on an Enterprise-D is called Data on every future console in every future
   mission - and since the player's own answer is the strongest tier, nothing could ever
   dislodge it. Client strings hold ONLY what the human chose.

**Addons cannot use** :func:`crew_load_amd` - it resolves mission-relative, the same trap
``sides_load_amd`` has. An addon declares its roster out of its own mastlib instead::

    crew_declare_amd(amd_document(media_read_relative_file("crew_rosters.amd"),
                                  data_parser=amd_crew_data))
"""
from random import choice


# CROSS-DOCUMENT, per-mission state, so all four are on the reset ledger (see handlerhooks).
#
# Rosters name hull keys and portrait atlas keys that exist only while THAT mod is loaded, so
# carrying them into mission 2 hands you people pointing at a sheet the engine is no longer
# told about - the same argument that puts `face_mod_reset` on the ledger.
_ROSTERS = {}          # key -> roster record, declaration order preserved
_HULL_DEFAULTS = {}    # normalized shipData key -> roster key   (the MOD tier)
_SHIP_BINDINGS = {}    # normalized ship NAME -> roster key      (the MISSION tier)

# ship_id -> {client_id: (console, member_key)}
#
# KEYED BY CLIENT, not by console, because two clients can legitimately sit at the same
# console type - a bridge with two science stations, or a spare screen someone opened. Keyed
# the other way the second one EVICTS the first: it overwrites the seat, the first client's
# person silently becomes free again, and the next client to arrive is given somebody who is
# already on screen.
#
# Module-level rather than inventory on the ship agent for the same reason: the natural
# inventory shape is one value per key, which is the collapse above wearing a different hat.
_SEATS = {}

BY_CONSOLE = "console"
BY_PERSON = "person"

# The inventory keys `crew_assign` writes on the client agent. CREW_NAME is deliberately
# unchanged - `director_overlays._tok_crew_name` and the Gamemaster's message list already
# read it and must keep working with no edit at all.
CREW_KEYS = ("CREW_NAME", "CREW_RANK", "CREW_FACE", "CREW_PORTRAIT",
             "CREW_KEY", "CREW_ROSTER", "CREW_SOURCE")

SOURCE_UNMANNED = "unmanned"


def _norm(text):
    """Fold a ship name or hull key for comparison: stripped, lowered, spaces collapsed."""
    return " ".join(str(text or "").strip().lower().split())


def _plain(text):
    """Braces and backticks out of anything bound for a MAST string or a style.

    A name reaches `gui_text` and f-string formatting, so a person genuinely called
    ``Foo{bar}`` would be a syntax error reported against the widget rather than against the
    roster that named them. Same guard the Director puts on its own screen labels.
    """
    return str(text or "").replace("{", "(").replace("}", ")").replace("`", "'").strip()


# --- registry -----------------------------------------------------------------------------


def crew_clear():
    """Drop every declared roster and every live seat - the per-mission reset."""
    _ROSTERS.clear()
    _HULL_DEFAULTS.clear()
    _SHIP_BINDINGS.clear()
    _SEATS.clear()


def crew_count():
    """Reset-ledger probe: how much DECLARED roster data is held."""
    return len(_ROSTERS) + len(_HULL_DEFAULTS) + len(_SHIP_BINDINGS)


def crew_seat_count():
    """Reset-ledger probe: how many LIVE seats are held.

    Separate from :func:`crew_count` on purpose - declared rosters and occupied seats leak
    for different reasons, and one probe covering both cannot say which of them happened.
    """
    return sum(len(v) for v in _SEATS.values())


def crew_declare(records):
    """Register roster records. Returns ``{key: roster}`` for everything registered.

    Args:
        records: an iterable of roster records - what
            :func:`sbs_utils.procedural.amd_crew.crew_from_section` returns.

    A roster re-declared under a key that already exists REPLACES it, so an in-process
    recompile re-registering the same file is a no-op rather than a duplicate.
    """
    out = {}
    for rec in records or ():
        key = str(rec.get("key") or "").strip()
        if not key:
            continue
        _ROSTERS[key] = rec
        out[key] = rec
        for hull in rec.get("hull") or ():
            _HULL_DEFAULTS[_norm(hull)] = key
        for ship in rec.get("ship") or ():
            _SHIP_BINDINGS[_norm(ship)] = key
        _register_portraits(rec)
    return out


def _register_portraits(roster):
    """Cut a roster's ``Sheet:`` into named cells, once, at declare time.

    Reuses the image atlas wholesale: each member's ``At:`` cell is registered as
    ``crew:<roster>:<member>`` and that key IS the member's portrait, so a roster sheet
    behaves exactly like an icon sheet and there is no new image machinery to maintain.
    """
    sheet = roster.get("sheet")
    if not sheet:
        return
    cells = {}
    for m in roster.get("members") or ():
        at = m.get("at")
        if at is not None:
            cells["crew:%s:%s" % (roster.get("key"), m.get("key"))] = at
    if not cells:
        return
    try:
        from .gui.image import gui_image_add_atlas_grid
        from .media_paths import media_shared
        grid = roster.get("grid") or (len(cells), 1)
        gui_image_add_atlas_grid(media_shared(sheet), int(grid[0]), int(grid[1]),
                                 names=cells, cell=roster.get("cell"))
    except Exception as e:
        from .execution import log
        log("crew roster '%s' could not cut sheet '%s': %s" % (roster.get("key"), sheet, e),
            "crew", "warning")


def crew_rosters():
    """Every declared roster, in declaration order."""
    return list(_ROSTERS.values())


def crew_roster(key):
    """One roster by exact key, or None."""
    return _ROSTERS.get(str(key or "").strip())


# --- selection - mirrors media.py so a spec resolves the one way everywhere ---------------


def crew_name_list():
    """Dropdown options string for a crew picker: ``'none, random, <Display>, ...'``.

    The map-Properties counterpart of :func:`crew_get_list`. Offers only USABLE rosters,
    for the same reason that function does - a dropdown must never offer something
    selection would then refuse.
    """
    return ", ".join(["none", "random"] + [r.display_name for r in (crew_get_list() or [])])


def crew_selected_name():
    """The current CREW_SELECT, or ``"none"``.

    Reads the shared value first, then the setting, so a map's `default shared` seed cannot
    overwrite a choice a profile already made.
    """
    try:
        from .execution import get_shared_variable
        current = get_shared_variable("CREW_SELECT", None)
    except Exception:
        current = None
    if current:
        return str(current)
    from .settings import settings_get_defaults
    return str(settings_get_defaults().get("CREW_SELECT") or "none")


def crew_get_list():
    """The rosters a dropdown may OFFER - the USABLE ones, in declaration order.

    Usable means it has at least one member. An unusable roster stays in the registry, so
    ``crew_roster`` still finds it and lint can still complain about it, but it is never put
    in front of an operator - the ``media_get_list`` principle that a dropdown must never
    offer something selection would then refuse.
    """
    return [r for r in _ROSTERS.values()
            if r.get("usable", True) and (r.get("members") or ())]


def crew_find(spec):
    """Find one roster from a loose spec - an index, a key, a display name, or an
    unambiguous substring of either.

    Uses ``maps.label_find_by_spec``, the same matcher ``maps_find`` and ``media_find`` use,
    so a roster named in ``settings.yaml``, in a ``@map`` ``Defaults:``, on the command line
    and in a dropdown all resolve identically. An AMBIGUOUS spec returns None rather than
    guessing.
    """
    from .maps import label_find_by_spec
    return label_find_by_spec(crew_get_list(), spec)


def crew_select(spec):
    """Resolve the roster a setting, a map or an operator ASKED for.

    Args:
        spec: ``""``/``None``/``"none"`` selects nothing - the deliberate default, see
            ``CREW_SELECT`` in settings; ``"random"`` picks from every usable roster;
            anything else goes through :func:`crew_find`.

    Returns:
        The roster record, or None.

    A spec that matches nothing WARNS BY NAME and selects nothing. Silence was the tempting
    choice and the wrong one: ``CREW_SELECT: Enterprize`` would leave every console unnamed,
    which is indistinguishable from never having asked.
    """
    want = "" if spec is None else str(spec).strip()
    if not want or want.lower() in ("none", "off"):
        return None
    usable = crew_get_list()
    if want.lower() == "random":
        if not usable:
            return None
        return choice(usable)
    found = crew_find(want)
    if found is None:
        from .execution import log
        known = ", ".join(str(r.get("key")) for r in usable) or "none are declared"
        log("CREW_SELECT '%s' matched no crew roster - leaving consoles unnamed. "
            "Available: %s" % (want, known), "crew", "warning")
    return found


# --- binding ------------------------------------------------------------------------------


def _name_of(ship_or_name):
    if isinstance(ship_or_name, str):
        return ship_or_name
    from .query import to_object
    obj = to_object(ship_or_name)
    return getattr(obj, "name", None) if obj is not None else None


def _as_roster(roster_spec):
    if roster_spec is None:
        return None
    if hasattr(roster_spec, "get") and not isinstance(roster_spec, (str, int)):
        return roster_spec
    return crew_find(roster_spec)


def crew_bind_ship(ship_or_name, roster_spec):
    """Bind a roster to a ship BY NAME. Returns True when it took.

    By name rather than by id on purpose: a mission binds its crews before the ships exist,
    and a player ship can be respawned across a mission's life while keeping its name.
    """
    roster = _as_roster(roster_spec)
    name = _name_of(ship_or_name)
    if roster is None or not name:
        return False
    _SHIP_BINDINGS[_norm(name)] = roster.get("key")
    return True


def crew_unbind_ship(ship_or_name):
    """Drop a ship's binding, so it falls back to the map / hull / library tiers."""
    _SHIP_BINDINGS.pop(_norm(_name_of(ship_or_name)), None)


def crew_bind_hull(hull_key, roster_spec):
    """Bind a roster to a shipData HULL KEY - the tier a mod uses. True when it took.

    The hull KEY, never ``artfileroot``: the two differ on about half the TNG hulls, so a
    roster keyed on art would silently attach to the wrong ships.
    """
    roster = _as_roster(roster_spec)
    if roster is None or not hull_key:
        return False
    _HULL_DEFAULTS[_norm(hull_key)] = roster.get("key")
    return True


def crew_roster_for(ship_id):
    """Which roster staffs this ship, and WHY: ``(roster, source)``.

    Source is ``ship`` / ``map`` / ``hull`` / None, strongest first. It is returned rather
    than merely logged because "why is this console called that" is otherwise unanswerable
    from the outside - every tier looks identical once it has produced a name.
    """
    from .query import to_object
    obj = to_object(ship_id)

    if obj is not None:
        key = _SHIP_BINDINGS.get(_norm(getattr(obj, "name", "")))
        if key and key in _ROSTERS:
            return _ROSTERS[key], "ship"

    from .execution import get_shared_variable
    picked = crew_select(get_shared_variable("CREW_SELECT", ""))
    if picked is not None:
        return picked, "map"

    if obj is not None:
        key = _HULL_DEFAULTS.get(_norm(getattr(obj, "art_id", "")))
        if key and key in _ROSTERS:
            return _ROSTERS[key], "hull"

    return None, None


# --- seats --------------------------------------------------------------------------------


def _seat_is_live(client_id, console):
    """Is this client still actually sitting at this console?

    SELF-HEALING OCCUPANCY. Rather than hooking disconnects and console changes - two events
    that can be missed, and a missed one leaks a seat for the rest of the mission - a seat is
    simply believed only while the client's own CONSOLE_TYPE still agrees with it. A client
    that left, changed station or vanished stops matching and its seat frees itself.
    """
    from .inventory import get_inventory_value
    return _norm(get_inventory_value(client_id, "CONSOLE_TYPE", None)) == _norm(console)


def _taken_members(ship_id, exclude_client=None):
    """Member keys currently occupied on this ship, pruning any seat that went stale.

    `exclude_client` frees that client's own seat first, so re-resolving a console the same
    person is already sitting at gives them back the same member rather than the next one.
    """
    seats = _SEATS.get(ship_id)
    if not seats:
        return set()
    taken = set()
    stale = []
    for cid, (console, member_key) in seats.items():
        if cid == exclude_client or not _seat_is_live(cid, console):
            stale.append(cid)
            continue
        taken.add(member_key)
    for cid in stale:
        seats.pop(cid, None)
    return taken


def _seat_pick(roster, ship_id, console, client_id=None):
    """Who this roster puts at this console, or None.

    A ``By: person`` roster NEVER auto-assigns, and that is the point of it rather than an
    omission: its members are real people who choose themselves. Handing Doug's face to
    whoever happened to open helm first is exactly what it exists to avoid.
    """
    if _norm(roster.get("by")) == BY_PERSON:
        return None
    taken = _taken_members(ship_id, exclude_client=client_id)
    free = [m for m in roster.get("members") or () if m.get("key") not in taken]
    want = _norm(console)
    # Declaration order breaks every tie, never random: a bridge should fill Picard, Riker
    # and Data in the order the author wrote them, and should fill them the same way twice.
    for m in free:
        if _norm(m.get("console")) == want:
            return m
    for m in free:                      # a floating officer - no console of their own
        if not _norm(m.get("console")):
            return m
    return None


def crew_release(client_id):
    """Give up whatever seat this client holds, on every ship.

    Called when a console changes ship or station. Occupancy is self-healing anyway, so this
    is an optimization rather than a correctness requirement - it frees the person for the
    next client in the same frame instead of on the next resolve.
    """
    for seats in _SEATS.values():
        seats.pop(client_id, None)


# --- automatic names -----------------------------------------------------------------------
#
# A console nobody named gets one anyway, and a DIFFERENT one from every other console in the
# run. That is the point of the feature: the crew name existed for years, almost nobody typed
# one, and every seat on air read "unmanned".
#
# Turn it off with `CREW_AUTONAME: false` and a console with no roster and no typed name goes
# back to "" exactly as before.
_NAME_POOL = {}     # normalized console -> {normalized race or "": [names]}

# Taken this RUN, so no two consoles are the same person. Cleared by `crew_clear`, which the
# mission reset calls - "unique per run" is exactly the lifetime of that dict.
_USED_NAMES = set()

# The stock pool, combined given x family, so the space is thousands wide and uniqueness is
# never the thing that runs out. Deliberately broad: these are the people on every bridge in
# every mission that never thought about crew names, so a narrow list would be very visible.
#
# It lives in the LIBRARY rather than in LegendaryMissions because it has to work for a
# mission that loads no add-ons at all - "defaulted" is not much of a default otherwise. A
# base game or a total conversion overrides it wholesale with `crew_register_names`, which is
# consulted FIRST.
_GIVEN = (
    "Ada", "Ansel", "Bex", "Corbin", "Dmitri", "Elena", "Farid", "Greta", "Halden", "Ines",
    "Joaquin", "Kwame", "Lena", "Mateo", "Nkechi", "Osric", "Priya", "Quinn", "Rasa", "Sana",
    "Tomas", "Ume", "Vikram", "Wren", "Xiulan", "Yusra", "Zofia", "Amara", "Bodhi", "Cato",
    "Dagny", "Emeka", "Freya", "Goro", "Hana", "Idris", "Juno", "Kiran", "Liesl", "Mira",
)
_FAMILY = (
    "Marek", "Okonjo", "Ferrero", "Lindqvist", "Raghunathan", "Nwosu", "Osei", "Vasquez",
    "Rooke", "Al-Amin", "Sarkisian", "Vale", "Balogun", "Petrauskas", "Ferreira", "Tsai",
    "Achebe", "Bergstrom", "Castellanos", "Duarte", "Eskildsen", "Fontaine", "Gallardo",
    "Haddad", "Ivanova", "Jansen", "Kowalski", "Laurent", "Mbeki", "Nakamura", "Oyelaran",
    "Pashenko", "Quiroga", "Rasmussen", "Suleiman", "Thorne", "Ueda", "Varga", "Whitlock",
)


def crew_register_names(console, names, race=None):
    """Declare fallback names for a console, optionally for one race.

    These fill seats a roster left empty - never seats nobody asked about. See
    :func:`crew_default_name`.
    """
    con = _NAME_POOL.setdefault(_norm(console), {})
    con.setdefault(_norm(race), []).extend(str(n).strip() for n in (names or ()) if str(n).strip())


def crew_names_clear():
    """Drop every registered name AND every name handed out this run."""
    _NAME_POOL.clear()
    _USED_NAMES.clear()


def crew_autoname_enabled():
    """Whether a console nobody named gets one automatically. `CREW_AUTONAME`, default on."""
    try:
        from .settings import settings_get_defaults
        return bool(settings_get_defaults().get("CREW_AUTONAME", True))
    except Exception:
        return True


def _take(name):
    """Claim a name for this run, or None if somebody already has it."""
    if not name:
        return None
    key = _norm(name)
    if key in _USED_NAMES:
        return None
    _USED_NAMES.add(key)
    return name


def crew_default_name(console, race=None):
    """An automatic name for a console, UNIQUE within this run, or "".

    Order: a pool somebody registered for this console and race, then that console's
    race-less pool, then the stock given-x-family names. A race with no pool falls back
    rather than returning nothing - asking for a Kralien helmsman should still get one.

    Uniqueness is per RUN because `_USED_NAMES` is cleared by the mission reset. Two consoles
    are never the same person, which matters most on a Director bridge wall where they are
    all on screen at once.
    """
    con = _NAME_POOL.get(_norm(console)) or {}
    for pool in ((con.get(_norm(race)) if race else None), con.get("")):
        free = [n for n in (pool or ()) if _norm(n) not in _USED_NAMES]
        if free:
            return _take(choice(free))

    # The stock space is |given| x |family|, so sampling finds a free pair long before it is
    # worth enumerating - but it is bounded, so it cannot spin on a run that somehow used
    # them all.
    for _attempt in range(40):
        name = _take("%s %s" % (choice(_GIVEN), choice(_FAMILY)))
        if name:
            return name
    for given in _GIVEN:
        for family in _FAMILY:
            name = _take("%s %s" % (given, family))
            if name:
                return name
    return ""


def crew_avatar_race(ship_id=None):
    """A race the slider-based avatar editor can actually BUILD, for this ship.

    The editor drives `faces.FACE_FEATURES`, which describes the six stock races and nothing
    else. A hull belonging to a mod race has no features to slide - its faces are whole drawn
    busts, one per atlas cell - so asking the editor for one lands on its "unknown race"
    screen. Falls back to terran, which is always buildable.

    A mod race wants :func:`crew_face_gallery` and a pick-one-of-these screen instead.
    """
    from ..faces import FACE_FEATURES
    race = _hull_race(ship_id) if ship_id is not None else ""
    if str(race or "").lower() in FACE_FEATURES:
        return str(race).lower()
    return "terran"


def crew_face_gallery(race, count=12):
    """Ready-made face strings for a race, for a PICK-one-of-these gallery.

    The avatar editor builds a face out of sliders, which only works for the six stock races
    whose features `faces.FACE_FEATURES` describes. A mod race is whole drawn busts, one per
    atlas cell, with nothing to slide - so it needs a gallery instead, and this is what fills
    it. Returns [] for a race nobody registered.
    """
    from ..faces import _MOD_RACES
    entry = _MOD_RACES.get(str(race or "").lower())
    if not entry:
        return []
    pool = list(entry.get("any") or ())
    return pool[:count] if count and count > 0 else pool


# --- resolution ----------------------------------------------------------------------------


def _post(name, rank="", face="", portrait="", key="", roster="", source=SOURCE_UNMANNED):
    from ..mast.mast_node import MastDataObject
    return MastDataObject({
        "name": _plain(name), "rank": _plain(rank),
        "face": str(face or ""), "portrait": str(portrait or ""),
        "key": str(key or ""), "roster": str(roster or ""), "source": source,
    })


def _member_by_pick(pick):
    """Resolve a persisted ``"<roster>:<member>"`` pick, or None.

    An unresolvable pick is IGNORED rather than an error: the pick persists on the player's
    machine and the roster that gave it meaning belongs to one mod, so joining a game that
    does not load that mod must simply fall through to the next tier.
    """
    text = str(pick or "").strip()
    if ":" not in text:
        return None, None
    roster_key, _, member_key = text.partition(":")
    roster = _ROSTERS.get(roster_key.strip())
    if roster is None:
        return None, None
    for m in roster.get("members") or ():
        if str(m.get("key")) == member_key.strip():
            return roster, m
    return None, None


def _member_face(roster, member):
    """This member's face, DERIVED ONCE AND KEPT.

    A member with no ``Face:`` of their own gets one from the roster's ``Race:`` - but
    `face_resolve` rolls a fresh random face every call, so asking twice gave Data two
    different faces and every repaint changed his appearance. The derived face is cached back
    onto the member record, which also fixes the ordering problem a declare-time derivation
    would have: a mod registers its faces from its own `__init__`, which may run after the
    roster is declared.
    """
    face = member.get("face") or ""
    if face:
        return face
    face = member.get("__face__") or ""
    if face:
        return face
    race = roster.get("race")
    if not race:
        return ""
    # `random_face`, NOT `face_resolve`. face_resolve passes an unrecognized spec through as
    # a LITERAL face string, which is right for `Face:` and wrong for `Race:` - a mod race
    # like `Race: klingon` would become the face string "klingon" and draw nothing. Exactly
    # the case this feature exists for. random_face checks mod-registered races first and
    # falls back to a real face for anything it does not know.
    from ..faces import random_face
    face = random_face(race) or ""
    setattr(member, "__face__", face)
    return face


def _member_post(roster, member, source):
    """Build a post from a roster member, filling its blanks from the roster's fence."""
    face = _member_face(roster, member)
    portrait = member.get("portrait") or ""
    if portrait and roster.get("portraits") and not portrait.startswith("crew:"):
        portrait = str(roster.get("portraits")).rstrip("/") + "/" + portrait
    return _post(member.get("name"), member.get("rank"), face, portrait,
                 member.get("key"), roster.get("key"), source)


def crew_resolve(client_id, ship_id, console,
                 own_name=None, own_face=None, own_portrait=None, own_pick=None):
    """Who is at this console, and why. Returns a post - see the module docstring.

    Resolution runs strongest first, and the ``source`` on the returned post says which tier
    answered:

    ``own``
        What this human chose at the picker - a typed name, a built face, or a person they
        picked out of a ``By: person`` roster. Nothing outranks a person's own answer.
    ``ship`` / ``map`` / ``hull``
        A roster bound to this named ship, selected for this game, or declared by a mod for
        this hull. :func:`crew_roster_for` picks between them; :func:`_seat_pick` then
        chooses a member within it.
    ``library``
        A registered fallback name, filling a seat the roster left empty.
    ``unmanned``
        Nobody - which is exactly what a mission that does none of this gets, and why this is
        backward compatible.

    Does NOT write anything. :func:`crew_assign` is the one that does.
    """
    picked_roster, picked_member = _member_by_pick(own_pick)
    if picked_member is not None:
        post = _member_post(picked_roster, picked_member, "own")
        # A typed name still wins over the picked person's - the player edited it on purpose.
        if own_name:
            post.name = _plain(own_name)
        if own_face:
            post.face = str(own_face)
        if own_portrait:
            post.portrait = str(own_portrait)
        return post

    if own_name or own_face or own_portrait:
        return _post(own_name, "", own_face, own_portrait, "", "", "own")

    roster, source = crew_roster_for(ship_id)
    if roster is not None:
        member = _seat_pick(roster, ship_id, console, client_id)
        if member is not None:
            return _member_post(roster, member, source)

    # NOBODY NAMED THIS CONSOLE, so name it anyway - a different person from every other
    # console in the run. Reached whether or not a roster matched: a roster that does not
    # cover this seat and no roster at all are the same situation from the seat's point of
    # view, and "unmanned" was the answer nobody wanted in either.
    #
    # This is the one tier that changes what an EXISTING mission shows: a Director lower
    # third that used to read "unmanned" now reads a name. That is the point of the feature
    # rather than a side effect - but it is why `CREW_AUTONAME: false` exists.
    if not crew_autoname_enabled():
        return _post("")

    # KEEP THE ONE THIS CLIENT ALREADY HAS. `crew_assign` runs on every console selection,
    # so allocating afresh each time would rename a player the moment they moved from helm to
    # weapons - and the old name would stay claimed, so they could never get it back.
    # An automatic name belongs to the CLIENT for the run, not to the seat.
    held = _held_autoname(client_id)
    if held is not None:
        return held

    race = (roster.get("race") if roster is not None else "") or _hull_race(ship_id)
    name = crew_default_name(console, race)
    if not name:
        return _post("")
    # Same reason as _member_face: a hull's shipData `side` is "TSN", which is a SIDE and
    # not a face race at all, and face_resolve would hand "TSN" to send_gui_face as a face
    # string. random_face answers with a real face whatever it is given.
    from ..faces import random_face
    face = random_face(race) if race else random_face()
    return _post(name, "", face, "", "",
                 roster.get("key") if roster is not None else "", "library")


def _held_autoname(client_id):
    """The automatic name this client was already given, as a post, or None.

    Only an AUTOMATIC one: a roster's answer is re-resolved every time because the roster
    may have changed, and what the player typed is tier 1 and never reaches here.
    """
    from .inventory import get_inventory_value
    if get_inventory_value(client_id, "CREW_SOURCE", None) != "library":
        return None
    name = get_inventory_value(client_id, "CREW_NAME", None)
    if not name:
        return None
    return _post(name, get_inventory_value(client_id, "CREW_RANK", ""),
                 get_inventory_value(client_id, "CREW_FACE", ""),
                 "", "", get_inventory_value(client_id, "CREW_ROSTER", ""), "library")


def _hull_race(ship_id):
    """The race a hull belongs to, for a fallback face. "" when it cannot be told."""
    try:
        from .query import to_object
        from .ship_data import get_ship_data_for
        obj = to_object(ship_id)
        entry = get_ship_data_for(getattr(obj, "art_id", "")) if obj is not None else None
        return str((entry or {}).get("side", "") or "")
    except Exception:
        return ""


# --- the write path -------------------------------------------------------------------------


def crew_assign(client_id, ship_id, console,
                own_name=None, own_face=None, own_portrait=None, own_pick=None):
    """Resolve this console's crew and PUBLISH it. Returns the post.

    Writes on the client agent:

    ``CREW_NAME``
        Unchanged in name and meaning, so ``director_overlays._tok_crew_name`` and the
        Gamemaster's message list keep working with no edit at all. This is the whole reason
        the feature drops into the existing seam rather than replacing it.
    ``CREW_RANK`` / ``CREW_FACE`` / ``CREW_PORTRAIT`` / ``CREW_KEY`` / ``CREW_ROSTER`` /
    ``CREW_SOURCE``
        Additive. ``CREW_SOURCE`` is kept because it is the only way to answer "why is this
        console called that" after the fact.

    It also takes the seat, so a second client opening the same station on the same ship gets
    the NEXT person rather than the same one.

    Writes no client string. See the module docstring for why that would be unfixable.
    """
    from .inventory import set_inventory_value
    post = crew_resolve(client_id, ship_id, console,
                        own_name=own_name, own_face=own_face,
                        own_portrait=own_portrait, own_pick=own_pick)

    crew_release(client_id)
    if post.key:
        _SEATS.setdefault(ship_id, {})[client_id] = (_norm(console), post.key)

    set_inventory_value(client_id, "CREW_NAME", post.name)
    set_inventory_value(client_id, "CREW_RANK", post.rank)
    set_inventory_value(client_id, "CREW_FACE", post.face)
    set_inventory_value(client_id, "CREW_PORTRAIT", post.portrait)
    set_inventory_value(client_id, "CREW_KEY", post.key)
    set_inventory_value(client_id, "CREW_ROSTER", post.roster)
    set_inventory_value(client_id, "CREW_SOURCE", post.source)

    if post.face:
        from ..faces import set_face
        set_face(client_id, post.face)
    return post


def crew_post_of(client_id):
    """The post this client was last assigned, rebuilt from its inventory. None if unnamed."""
    from .inventory import get_inventory_value
    name = get_inventory_value(client_id, "CREW_NAME", None)
    if not name:
        return None
    return _post(name,
                 get_inventory_value(client_id, "CREW_RANK", ""),
                 get_inventory_value(client_id, "CREW_FACE", ""),
                 get_inventory_value(client_id, "CREW_PORTRAIT", ""),
                 get_inventory_value(client_id, "CREW_KEY", ""),
                 get_inventory_value(client_id, "CREW_ROSTER", ""),
                 get_inventory_value(client_id, "CREW_SOURCE", SOURCE_UNMANNED))


def crew_choices_for(ship_id, console=None, client_id=None):
    """The people a picker may OFFER, in declaration order.

    ``console`` NARROWS a ``By: console`` roster to those who could take that exact seat.
    Pass None - which the console picker does - to offer everyone still free, because there
    the dropdown is an OVERRIDE beside a cast that already assigns itself by console: a
    player reaching for it is reaching past the automatic answer, and the automatic answer is
    the only thing the console was going to decide.

    Console is ignored outright for a ``By: person`` roster, where the seat is not what
    identifies anybody.

    Returns [] when no roster staffs this ship, which is what keeps the picker looking
    exactly as it does today for a mission that declares none.
    """
    roster, _source = crew_roster_for(ship_id)
    if roster is None:
        return []
    taken = _taken_members(ship_id, exclude_client=client_id)
    free = [m for m in roster.get("members") or () if m.get("key") not in taken]
    if not console or _norm(roster.get("by")) == BY_PERSON:
        return free
    want = _norm(console)
    return [m for m in free if _norm(m.get("console")) in (want, "")]


def crew_pick_for(ship_id, name, client_id=None):
    """The pick string for a person chosen BY DISPLAY NAME, or "" for none of them.

    The picker's dropdown is a list of names, and a MAST handler mapping one back to a member
    would be a loop inside a handler - the trap that captures the last iteration's value. So
    the mapping lives here, where it is one call.
    """
    want = _norm(name)
    if not want or want.startswith("("):        # "(auto)", "(me)" - not a person
        return ""
    roster, _source = crew_roster_for(ship_id)
    if roster is None:
        return ""
    for m in crew_choices_for(ship_id, None, client_id):
        if _norm(m.get("name")) == want:
            return crew_pick_value(roster.get("key"), m.get("key"))
    return ""


def crew_preview(pick):
    """The (name, face, portrait) a picked person shows, for a preview beside the picker.

    Returns ("", "", "") for an unresolvable pick, so a screen can bind all three without
    testing first.
    """
    roster, member = _member_by_pick(pick)
    if member is None:
        return "", "", ""
    post = _member_post(roster, member, "own")
    return post.name, post.face, post.portrait


def crew_preview_markdown(face, portrait, height=88, align="center"):
    """A `gui_text_area` body that shows one crew member, or "" for nobody.

    ONE widget for both kinds of likeness, which is the point: a text area already speaks
    `face://` and `image://`, so a screen binds a single value and never has to swap widgets
    when a roster answers with a photograph instead of a face string. It also sidesteps the
    absolute-region ghost - a plain value update on an ordinary widget refreshes cleanly,
    where a child updated inside an absolute `gui_region` keeps the old draw underneath.

    A PORTRAIT BEATS A FACE, never both: a photograph is the stronger statement, and
    stacking them has no rule to resolve it.
    """
    if portrait:
        return "![](image://%s?scale=1&fill=%s)" % (str(portrait).strip(), align)
    if face:
        return "![](face://%s?height=%s&align=%s)" % (str(face).strip(), height, align)
    return ""


# What the player chose about THEMSELVES, packed into one client string.
#
# ONE key, not three, because every key costs a `request_client_string` ROUND TRIP that the
# console picker awaits before it can draw - and those awaits carry no timeout, so each one
# is a place the picker stops if the engine ever declines to answer. The picker already makes
# three; adding three more would double the cost of opening a console for a preference most
# players never set.
#
# Pipe-delimited rather than JSON deliberately: a MAST assignment re-runs a string through
# f-string formatting, so a `{` in a value returned to a script is a syntax error reported
# against the CALLER. A face string is `alias #color col row;...`, a portrait is a path and a
# pick is `roster:key` - none of them can contain a pipe.
CREW_SELF_KEY = "crew_self"
_SELF_SEP = "|"


def _no_braces(text):
    """Braces out. The packed value is READ BACK INTO A MAST VARIABLE, and a MAST assignment
    re-runs a string through f-string formatting - so a brace anywhere in it is a SyntaxError
    reported against the console picker rather than against whatever put it there. Nothing
    legitimate carries one: a face string is `alias #color col row;`, a portrait is a path,
    and a pick is `roster:key`."""
    return str(text or "").replace("{", "(").replace("}", ")")


def crew_self_pack(pick="", face="", portrait=""):
    """Pack this player's own choices into one client-string value."""
    parts = [_no_braces(pick), _no_braces(face), _no_braces(portrait)]
    return _SELF_SEP.join(p.replace(_SELF_SEP, "/") for p in parts).rstrip(_SELF_SEP)


def crew_self_unpack(text):
    """(pick, face, portrait) out of a packed value. Always a 3-tuple, so a caller can
    unpack it without testing - an empty or malformed value reads as three blanks.

    Braces are stripped on the way OUT as well as in, because the value comes off the
    player's own disk and a hand-edited client_string_set.txt is not this file's to trust.
    """
    parts = _no_braces(text).split(_SELF_SEP)
    parts += [""] * (3 - len(parts))
    return parts[0].strip(), parts[1].strip(), parts[2].strip()


def crew_pick_value(roster_key, member_key):
    """The ``"<roster>:<member>"`` string a picker persists for a chosen person."""
    return "%s:%s" % (str(roster_key or "").strip(), str(member_key or "").strip())


def console_display_name(client_id):
    """What to CALL this console in a list of consoles.

    A person's name when there is one, else the screen's own name. The Director names its
    output windows PROG01 / PRE01 / DIR01 - those used to live in ``CREW_NAME`` too, and
    anything listing consoles by crew name showed them for free. They have their own key
    now, so the two have to be put back together here rather than at every call site.
    """
    from .inventory import get_inventory_value
    return (get_inventory_value(client_id, "CREW_NAME", None)
            or get_inventory_value(client_id, "SCREEN_NAME", None) or "")


# --- AMD entry points ------------------------------------------------------------------------


def crew_declare_amd(node):
    """Declare every crew roster in an already-parsed AMD document or section.

    THE ADDON PATH. An addon's file lives inside its mastlib, which is a zip, so it must be
    read out and parsed by the addon itself::

        crew_declare_amd(amd_document(media_read_relative_file("crew_rosters.amd"),
                                      data_parser=amd_crew_data))
    """
    from .amd_crew import crew_from_document
    return crew_declare(crew_from_document(node))


def crew_load_amd(file_path):
    """Load and declare crew rosters from a MISSION-relative ``.amd`` file.

    Mission-relative, so an ADDON CANNOT USE THIS - the same trap ``sides_load_amd`` has. Use
    :func:`crew_declare_amd` from an addon.
    """
    from .amd_crew import crew_read_amd
    return crew_declare(crew_read_amd(file_path))
