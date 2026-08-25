"""The player roster: an indirection layer between a console and a player ship.

WHY THIS EXISTS
---------------
A console used to bind to a live ``Agent`` object, held across frames and indexed by its
position in ``sorted(to_object_list(role("__player__")))``. That assumed three things, and
all three are false during the part of a session where the operator is still setting up:

  * that the snapshot's objects stay alive - but ships past ``PLAYER_COUNT`` were deleted;
  * that list position identifies a ship - but any roster edit reorders it;
  * that hull, name and side are fixed once created - but a theater rewrites them.

Every time one of those broke, the fix was another guard around the same pointer: re-resolve
before writing, filter the dead out of the list, clamp the index, re-clamp on
``on change PLAYER_COUNT``. Five guards defending one reference.

This is the other answer. A console binds to a RECORD, keyed by slot. The record owns the
hull, name, side and face; the roster owns the records; the live object is something the
roster resolves on demand and may replace. Nothing holds an object across a frame, so there
is nothing to harden.

WHAT THIS DOES NOT DO
---------------------
**It cannot morph a ship onto a new engine ID.** IDs are engine-managed and
``sbs.assign_client_to_ship`` takes one, so there is no indirection inside the engine to
lean on. What the roster does instead is make SURVIVING an id change its own job rather than
every console's - see :func:`player_roster_rebind`.

That distinction matters less than it sounds, because the common changes do not need a new
id at all. Re-hulling, renaming, changing side and setting a face are all field writes on a
live object; only a ``sim_create()`` wipe or a destroy-and-respawn produces a new id.

TWO PHASES
----------
**Fluid** - the server console is open, ``PLAYER_COUNT`` is a live slider on every map, and
the set of ships that will play is not settled. Here a count change only flips records
between active and parked. **Nothing is ever deleted.**

**Fixed** - the game has started. :func:`player_roster_release_inactive` runs ONCE, and is
the only place this module deletes anything. Deferring it to a single defined moment is
deliberate: ``delete_object`` frees the C++ object synchronously, so deleting while a
selection screen is live is how a console ends up pointing at freed memory.
"""


# Records are plain dicts, index == slot. Deliberately NOT keyed by the live id: an id is
# something we resolve, never something we bind to.
_ROSTER = []

# slot -> set of client ids currently crewing it. Held HERE, not as a link on the ship,
# because the ship's own links die with the ship - and re-assigning the clients of a ship
# that just went away is exactly what this has to survive.
_BOUND = {}

# slot -> the id we last saw, so a change can be DETECTED. Change detection only; the
# binding is the slot.
_LAST_ID = {}


def player_roster_clear():
    """Drop every record and binding. On the reset ledger."""
    _ROSTER.clear()
    _BOUND.clear()
    _LAST_ID.clear()


def player_roster_count_records():
    """How much state is held. The reset-ledger probe."""
    return len(_ROSTER) + len(_BOUND) + len(_LAST_ID)


def player_roster():
    """Every record, in slot order."""
    return list(_ROSTER)


def player_roster_record(slot):
    """The record for ``slot``, or None."""
    slot = int(slot)
    if 0 <= slot < len(_ROSTER):
        return _ROSTER[slot]
    return None


def player_roster_seed(roster=None):
    """Build the records from a roster of dicts (defaults to ``SETTINGS["PLAYER_LIST"]``).

    Idempotent by slot: re-seeding an existing roster updates the authored fields and leaves
    active-ness and bindings alone, so this can be called again after a sim wipe without
    disturbing who is sitting where.

    Args:
        roster (list, optional): dicts with ``name``/``side``/``ship``/``face``.

    Returns:
        list: the records.
    """
    if roster is None:
        from .settings import settings_get_defaults
        roster = settings_get_defaults().get("PLAYER_LIST") or []
    for slot, entry in enumerate(roster):
        if not isinstance(entry, dict):
            continue
        rec = player_roster_record(slot)
        if rec is None:
            rec = {"slot": slot, "active": True}
            _ROSTER.append(rec)
        # The AUTHORED values. `ship` is the key the author wrote; what actually gets drawn
        # is art_key_for(ship), resolved at apply time so a theater picked later still lands.
        rec["name"] = entry.get("name")
        rec["side"] = entry.get("side", "tsn")
        rec["ship"] = entry.get("ship")
        rec["face"] = entry.get("face")
    return player_roster()


def player_roster_resolve(slot):
    """The live ship holding ``slot``, or None.

    Resolves through the slot ROLE and deliberately does not require ``__player__``: a
    parked ship has had that role stripped, and it must still be findable or the next count
    change would spawn a duplicate beside it instead of waking it up.
    """
    from .roles import role
    from .query import to_id_list, object_exists
    from .spawn import player_slot_role
    for so_id in to_id_list(role(player_slot_role(slot))):
        if object_exists(so_id):
            return so_id
    return None


def player_roster_slot_of_ship(so_id):
    """Which slot a ship holds, or None.

    The inverse of :func:`player_roster_resolve`, and the bridge a console needs: it knows
    the ship it just attached to and has to say which SLOT that was in order to bind.
    Reads the slot marker written by ``player_ensure``, so it answers for a parked ship too.
    """
    from .inventory import get_inventory_value
    from .spawn import PLAYER_SLOT_KEY
    if so_id is None:
        return None
    slot = get_inventory_value(so_id, PLAYER_SLOT_KEY, None)
    return None if slot is None else int(slot)


def player_roster_slots(active_only=True):
    """The slot numbers a picker should offer, in order.

    The list a console picker binds to. Slots rather than ships, because a slot cannot be
    freed underneath a live screen - which is the whole reason the old snapshot needed
    filtering, clamping and re-resolving everywhere it was touched.

    Args:
        active_only (bool): only slots that are being flown. False includes parked ones.
    """
    return [r["slot"] for r in _ROSTER if r.get("active") or not active_only]


def player_roster_set_name(slot, name):
    """Rename a slot. Writes the RECORD, never the ship.

    The console picker's rename used to run ``picked_ship.name = ...`` per keystroke, and
    that lands in ``set_name`` -> ``blob.set("name_tag", ...)`` - ``ObjectDataBlob::Set``,
    the function in every one of this build's server crash dumps, called on a live ship
    while the sim ticks it. Writing the record instead means the setup screen touches no
    engine object at all; :func:`player_roster_apply` carries it across at Start.

    Other consoles still see the change immediately, because they render the same record.
    """
    rec = player_roster_record(slot)
    if rec is None:
        return False
    rec["picked_name"] = str(name) if name is not None else None
    return True


def player_roster_set_hull(slot, ship_key):
    """Choose a slot's hull. Writes the RECORD, never the ship.

    Kept apart from the authored ``ship`` so the two stay distinguishable: ``ship`` is what
    the mission rostered and is what a theater re-skins, while this is what the crew picked
    in front of the ship. The pick wins over every theater layer and loses to a game code -
    see the precedence comment in :func:`player_roster_apply`.

    Pass None to drop the pick and fall back to the theater.
    """
    rec = player_roster_record(slot)
    if rec is None:
        return False
    rec["picked_hull"] = str(ship_key) if ship_key else None
    return True


def player_roster_display(slot):
    """What a picker row should SHOW for a slot: ``{name, hull, side}``.

    Prefers the live ship when there is one, so a picker opened after the game started
    reflects reality rather than the roster's intentions - a mission may have renamed or
    refitted a ship since. Falls back to the record, which is the whole point: during setup
    there may be no object worth asking, and asking anyway is what this design removes.

    Returns the record's values with empty strings rather than None, so a caller can
    interpolate them straight into a style string.
    """
    rec = player_roster_record(slot)
    if rec is None:
        return {"name": "", "hull": "", "side": ""}

    # NEWEST INTENT WINS, and a pending pick is the newest there is. Preferring the live
    # ship over it looks reasonable and is wrong: during setup the ship exists and still
    # wears its old name, so a crew renaming their ship would watch the old name stay on
    # screen. The whole point of writing the record is that the screen updates without the
    # object being touched.
    name = rec.get("picked_name")
    hull = rec.get("picked_hull")
    side = None

    # Then the live ship, which is what makes a picker opened AFTER the start show reality -
    # a mission may have refitted or renamed a ship since the roster last had an opinion.
    # Skipped for a parked hull, whose art reads "invisible": bookkeeping, not something to
    # show anybody.
    if rec.get("active"):
        so_id = player_roster_resolve(slot)
        if so_id is not None:
            from .query import to_object
            obj = to_object(so_id)
            if obj is not None:
                name = name or obj.name
                hull = hull or obj.art_id
                side = obj.side or None

    # Then what the mission rostered.
    return {"name": name or rec.get("name") or "",
            "hull": hull or rec.get("ship") or "",
            "side": side or rec.get("side") or ""}


def player_roster_active_count():
    """How many records are currently active."""
    return sum(1 for r in _ROSTER if r.get("active"))


def player_roster_set_count(n):
    """Activate the first ``n`` records and park the rest. NEVER deletes.

    Parking strips ``__player__``, hides the hull and clears the side - the state the ship
    was left in before it was deleted - but keeps the object and its slot role. So raising
    the count again wakes the same ship up rather than spawning a new one, which is what
    keeps its engine id stable across a count change.

    Returns:
        list: the slots whose active-ness actually changed.
    """
    n = max(0, int(n))
    changed = []
    for rec in _ROSTER:
        want = rec["slot"] < n
        if bool(rec.get("active")) == want:
            continue
        rec["active"] = want
        changed.append(rec["slot"])
        so_id = player_roster_resolve(rec["slot"])
        if so_id is None:
            continue
        _set_parked(so_id, not want, rec)
    return changed


def _set_parked(so_id, parked, rec):
    """Park or wake one ship. The engine id never changes either way.

    PARKING PUSHES TO STANDBY, and that is the point of the whole mechanism.
    ``push_to_standby_list_id`` suspends an object from the active physics arena AND FROM
    NETWORK REPLICATION without freeing it - so a client can no longer ask the server for
    data about a ship it is not being told about, and there is no freed blob for that
    question to land on.

    The alternative was deleting the ship, which frees the C++ object synchronously
    (`delete_object`), and a client asking about it across that window is the
    `ObjectDataBlob::Set` use-after-free that has crashed servers within seconds of a
    console connecting. Standby removes the window rather than narrowing it: nothing is
    ever freed, so there is nothing to race.

    Every ROLE is stripped as well, so no query, targeting sweep, objective or role
    expression can still consider a parked hull. The slot marker is the single exception -
    it is bookkeeping rather than gameplay, it is script-side only (an Agent registry, not
    anything the engine replicates), and without it the roster could not find the ship
    again to wake it.
    """
    import sbs
    from .roles import add_role, remove_role, get_role_list
    from .query import to_object
    from .spawn import player_slot_role
    obj = to_object(so_id)
    if obj is None:
        return
    keep = player_slot_role(rec["slot"])
    if parked:
        # ORDER IS LOad-BEARING, and getting it wrong is expensive.
        #
        # Setting `art_id` emits `ship_hull_changed`, and LM acts on that by calling
        # `grid_rebuild_grid_objects` - which DELETES AND RESPAWNS 60-100 grid objects.
        # Its only guard is `->END if not has_role(ship, "__player__")`. So blanking the
        # hull while the ship is still a player fires a rebuild on every parked slot:
        # seven hulls is 400-700 grid deletions at map start, and grid objects have no
        # standby to go to. Strip the roles FIRST and the route bails before deleting
        # anything.
        #
        # Clear the SIDE before the strip for a different reason: membership in a side IS
        # a role, so `side = ""` adds an EMPTY-NAMED one, and clearing after leaves a
        # stray '' role on every parked hull. (An invented key like "unused" is worse
        # still - every later lookup logs `Side not found`.)
        obj.side = ""
        for r in list(get_role_list(so_id) or []):
            if r != keep:
                remove_role(so_id, r)
        # Now it is nobody's player ship, so this is just a field write.
        obj.art_id = "invisible"
        try:
            sbs.push_to_standby_list_id(so_id)
        except Exception as exc:                       # pragma: no cover - defensive
            from .execution import log
            log(f"could not standby player slot {rec['slot']}: {exc}", "player_roster")
    else:
        try:
            sbs.retrieve_from_standby_list_id(so_id)
        except Exception as exc:                       # pragma: no cover - defensive
            from .execution import log
            log(f"could not retrieve player slot {rec['slot']}: {exc}", "player_roster")
        add_role(so_id, "__player__")
        add_role(so_id, "default_player_ship")
        obj.side = rec.get("side") or ""
        # Hull and stats are restored by the next apply(), which is the one place that
        # decides what a record should be wearing.


def _refresh_cached_blob(obj):
    """Point an agent's cached data_set back at the engine's CURRENT blob.

    `spawn_common` caches `obj.data_set` once and never revisits it, which is correct
    right up until the engine rebuilds the blob underneath it. Reading it back off the
    live engine object is the only way the script layer can notice.

    Best-effort by design: a mock or an agent with no engine object simply keeps what it
    had, and a refresh must never be the thing that breaks a roster apply.
    """
    try:
        eo = obj.engine_object
        if eo is None:
            return False
        blob = eo.data_set
        if blob is None:
            return False
        obj._data_set = blob
        return True
    except Exception:                               # noqa: BLE001
        return False


def player_roster_apply(loadout=None, force=False):
    """Reshape every active record's ship to match the record. Idempotent.

    Diff-then-write: a ship is only touched where it actually differs from its record, and
    ``player_ship_setup_from_data`` is only re-run when the HULL changed. That is what makes
    this safe to call repeatedly - from the panel on every map or theater change, and again
    at Start - instead of needing a did-I-run latch. Re-running it unconditionally would
    rebuild stats and wipe whatever a map had set on a ship in between.

    Args:
        loadout (list, optional): per-slot ``{"hull":..., "name":...}`` overrides from a game
            code. These WIN over the theater - the crew chose them explicitly.
        force (bool): rebuild stats even when the hull did not change.

    Returns:
        list: the slots that were actually modified.
    """
    import sbs
    from .query import to_object
    from .ship_data import art_key_for, art_key_in_faction
    from .amd_theater import theater_player_faction, theater_players

    touched = []
    for rec in _ROSTER:
        if not rec.get("active"):
            continue
        so_id = player_roster_resolve(rec["slot"])
        obj = to_object(so_id) if so_id is not None else None
        if obj is None:
            continue

        # WHAT THIS SLOT WEARS, weakest first. Every layer is optional and absent means
        # the one below it, so an unset theater leaves the authored hull untouched.
        #
        #   authored PLAYER_LIST hull
        #     -> ART_KEYS / the theater's own race map   (art_key_for)
        #     -> the theater's Player Faction            (crew fly Orion, allies stay TSN)
        #     -> the theater's explicit Players list     (this slot, by name)
        #     -> what the CREW picked on the console picker
        #     -> a game-code loadout                     (handled below)
        #
        # The crew's own pick beats every theater layer because they made it deliberately,
        # in front of the ship they were choosing. A game code still beats the pick: it is
        # the same crew choosing, earlier and more explicitly.
        want_hull = art_key_for(rec.get("ship"))
        faction = theater_player_faction()
        if faction:
            want_hull = art_key_in_faction(rec.get("ship"), faction)
        explicit = theater_players()
        if rec["slot"] < len(explicit) and explicit[rec["slot"]]:
            want_hull = explicit[rec["slot"]]
        if rec.get("picked_hull"):
            want_hull = rec["picked_hull"]
        want_name = rec.get("picked_name") or rec.get("name")
        slot_override = None
        if loadout is not None and rec["slot"] < len(loadout):
            slot_override = loadout[rec["slot"]]
        if slot_override is not None:
            if slot_override.get("hull"):
                want_hull = slot_override["hull"]
            if slot_override.get("name"):
                want_name = slot_override["name"]

        dirty = False
        rebuilt = False
        if want_hull and obj.art_id != want_hull:
            obj.art_id = want_hull
            # Stats must follow the hull, or a Galaxy flies with a shuttle's shields.
            sbs.player_ship_setup_defaults(obj.engine_object)
            sbs.player_ship_setup_from_data(obj.engine_object)
            dirty = rebuilt = True
        elif force:
            sbs.player_ship_setup_defaults(obj.engine_object)
            sbs.player_ship_setup_from_data(obj.engine_object)
            dirty = rebuilt = True

        # RE-READ THE BLOB AFTER A REBUILD. `SpaceObject._data_set` is captured ONCE, at
        # spawn, and nothing else ever refreshes it - so after `player_ship_setup_from_data`
        # the agent keeps handing out the pre-rebuild handle, while `_alive` stays True and
        # the guard that exists for deletion never fires. Every later `to_blob(id).set(...)`
        # then writes through it.
        #
        # This is the same window that arms the engineering interiors: LM reconciles with
        # force=True (rebuilding EVERY player blob), then `//shared/signal/game_started`
        # calls `grid_interior_arm()`. Both land inside the console-connect window that
        # `autostartserver` collapses to nothing.
        if rebuilt:
            _refresh_cached_blob(obj)

        want_side = rec.get("side") or ""
        if rebuilt or obj.side != want_side:
            obj.side = want_side
            dirty = True

        # NAME LAST, and UNCONDITIONALLY after a rebuild - the diff cannot be trusted here.
        #
        # `obj.name` reads a SCRIPT-SIDE cache (`self._name`). The name the engine shows
        # lives in the blob as `name_tag`, and `player_ship_setup_from_data` rebuilds the
        # blob without touching the cache. So after a rebuild the two disagree: the cache
        # still holds the right name, the diff concludes there is nothing to do, and the
        # blob keeps whatever the engine defaulted to. Every player ship came up called
        # "Player".
        #
        # The code this replaced wrote the name unconditionally after setup and was right
        # to; diff-then-write is what introduced the bug. Anything else read back through a
        # cached attribute after a rebuild deserves the same suspicion.
        if want_name and (rebuilt or obj.name != want_name):
            obj.name = want_name
            dirty = True

        # NO FACE HERE, deliberately. `random_face` already routes through the theater's
        # Faces map, and whoever creates the ship sets it once. Re-rolling here would draw
        # from the seeded RNG on every apply - and apply runs on every panel build, so the
        # sequence would shift and every NPC spawned afterwards would change. Measured: it
        # moved a seeded stock run from 15 NPC hulls to 13.
        if dirty:
            touched.append(rec["slot"])

    _costume_player_sides()

    if touched:
        from .signal import signal_emit
        # Safe when there is no MAST context - signal_emit returns early.
        signal_emit("player_roster_changed", {"slots": touched})
    return touched


def player_roster_park_inactive():
    """Ensure every inactive slot is parked and in standby. Idempotent.

    :func:`player_roster_set_count` already parks on the transition; this is the backstop
    for a ship that was already inactive before the roster knew about it, or whose standby
    push did not take. Cheap - it only touches slots that are not already suspended.

    Returns:
        list: the slots it had to park.
    """
    import sbs
    parked = []
    for rec in _ROSTER:
        if rec.get("active"):
            continue
        so_id = player_roster_resolve(rec["slot"])
        if so_id is None:
            continue
        try:
            if sbs.in_standby_list_id(so_id):
                continue
        except Exception:                              # pragma: no cover - defensive
            pass
        _set_parked(so_id, True, rec)
        parked.append(rec["slot"])
    return parked


def _costume_player_sides():
    """Re-dress the players' side per the theater. The KEY is never changed.

    Only the name, colour and icon move, so diplomacy, `side_are_enemies`, the `//comms`
    gates and station-friendliness all keep reading the side the mission wrote. That is the
    whole reason "the crew are pirates tonight" is cheap: it is a costume, not a defection.

    Idempotent - `side_ensure` is, and the setters write the same values every time.
    """
    from .amd_theater import theater_player_side, theater_player_side_key
    # Read even though it always answers None: that call is what WARNS an author who asked
    # for a real side change, and staying silent about it is how a theater looks like it
    # worked until the crew spawn nowhere.
    theater_player_side_key()
    costume = theater_player_side()
    if not costume:
        return
    from .sides import side_ensure, side_set_side_icon_index, side_set_icon_color
    seen = set()
    for rec in _ROSTER:
        if not rec.get("active"):
            continue
        key = rec.get("side")
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            side_ensure(key, costume.get("name"))
            if costume.get("color"):
                side_set_icon_color(key, costume["color"])
            if costume.get("icon") is not None:
                side_set_side_icon_index(key, costume["icon"])
        except Exception as exc:                       # pragma: no cover - defensive
            from .execution import log
            log(f"theater could not re-dress side '{key}': {exc}", "theater", "warning")


def player_roster_release_inactive():
    """Delete the parked ships. The ONLY delete here, and only at the fluid->fixed edge.

    Refuses to release a slot a client is still bound to: a console pointing at a ship that
    is being freed is the whole failure this module exists to remove.

    Returns:
        list: the slots actually released.
    """
    from .query import object_exists, to_object
    from .roles import remove_role
    from .spawn import player_slot_role
    from .execution import log

    released = []
    for rec in _ROSTER:
        if rec.get("active"):
            continue
        slot = rec["slot"]
        crewed = player_roster_bound_live(slot)
        if crewed:
            log(f"player slot {slot} still crewed by {sorted(crewed)}; not releasing",
                "player_roster")
            continue
        so_id = player_roster_resolve(slot)
        if so_id is None or not object_exists(so_id):
            continue
        # Drop the marker first so a resolve during the delete cannot hand the id back out.
        remove_role(so_id, player_slot_role(slot))
        _LAST_ID.pop(slot, None)
        obj = to_object(so_id)
        if obj is not None:
            obj.delete_object()
        released.append(slot)
    return released


# ---------------------------------------------------------------------------
# Binding. A console says which SLOT it is crewing; the roster keeps the list so it
# survives the ship those clients were on being replaced or released.
# ---------------------------------------------------------------------------

def player_roster_bind(slot, client_id):
    """Record that ``client_id`` is crewing ``slot`` (and no other)."""
    slot = int(slot)
    player_roster_unbind(client_id)
    _BOUND.setdefault(slot, set()).add(client_id)


def player_roster_unbind(client_id):
    """Forget ``client_id`` wherever it was bound."""
    for clients in _BOUND.values():
        clients.discard(client_id)


def player_roster_bound(slot):
    """The clients crewing ``slot``, as recorded."""
    return set(_BOUND.get(int(slot), set()))


def player_roster_bound_live(slot):
    """The clients crewing ``slot`` that are still CONNECTED.

    A binding outlives the console that made it - nothing tells the roster a client went
    away - and a stale one would block :func:`player_roster_release_inactive` forever, so
    the parked ships would accumulate for the rest of the session.

    Pruned against ``Gui.clients``, which is the connected-client registry. **Only when it
    has entries**: an empty one means "nobody is connected" and "nothing is tracking
    clients" equally, and off-engine (a unit test, a headless run) it is always empty. With
    no information the conservative answer is to keep the binding - refusing to delete a
    ship is a leak, deleting one somebody is flying is a crash.
    """
    bound = player_roster_bound(slot)
    if not bound:
        return bound
    try:
        from ..gui import Gui
        connected = set(Gui.clients.keys())
    except Exception:
        return bound
    if not connected:
        return bound
    return {c for c in bound if c in connected}


def player_roster_slot_of_client(client_id):
    """Which slot ``client_id`` is crewing, or None."""
    for slot, clients in _BOUND.items():
        if client_id in clients:
            return slot
    return None


def player_roster_rebind(slot=None):
    """Re-assign bound clients wherever a slot's engine id has changed.

    The engine owns ids, so a ``sim_create()`` wipe or a destroy-and-respawn hands a slot a
    NEW ship. The binding is the slot, so nothing above needs to know - but the engine
    assignment does, and this is what re-runs it.

    Returns:
        list: the slots that were re-assigned.
    """
    import sbs
    from .links import link, unlink

    slots = [int(slot)] if slot is not None else [r["slot"] for r in _ROSTER]
    rebound = []
    for s in slots:
        so_id = player_roster_resolve(s)
        if so_id is None:
            continue
        was = _LAST_ID.get(s)
        _LAST_ID[s] = so_id
        if was == so_id:
            continue
        clients = player_roster_bound(s)
        if was is None or not clients:
            # First sighting, or nobody aboard: record the id and move on.
            continue
        for client_id in clients:
            unlink(was, "consoles", client_id)
            sbs.assign_client_to_ship(client_id, so_id)
            link(so_id, "consoles", client_id)
        rebound.append(s)
    return rebound
