def _costume_player_sides ():
    """Re-dress the players' side per the theater. The KEY is never changed.
    
    Only the name, colour and icon move, so diplomacy, `side_are_enemies`, the `//comms`
    gates and station-friendliness all keep reading the side the mission wrote. That is the
    whole reason "the crew are pirates tonight" is cheap: it is a costume, not a defection.
    
    Idempotent - `side_ensure` is, and the setters write the same values every time."""
def _crew_override (key, check_hull=True):
    """A map's `Defaults: CREW_HULL:` / `CREW_SIDE:`, or None.
    
    WHY THIS EXISTS. A map used to reshape its crew's ship from its own BODY, which runs
    after the console-select screen - so everyone spent the whole of that screen looking
    at the roster's ship and then watched it turn into a different one. Reported from the
    Gamma with a Q playtest as "set the hull at mission select ... after Q's intro is too
    late and confuses people".
    
    `map_apply_defaults` publishes a map's `Defaults:` block as shared variables just
    before the server panel renders, and `player_roster_apply` runs on the very next line,
    so declaring the hull there reseats the crew AS THE MISSION IS SELECTED.
    
    Weaker than the crew's own pick, like every theater layer, because a crew that chose a
    ship in front of the picker chose it deliberately. A mission that means the map to win
    outright locks the picker with SHIP_PICK_READ_ONLY, and then there is no pick to lose
    to - which is what Gamma with a Q does.
    
    A HULL THAT IS NOT LOADED IS IGNORED, said once. Swapping a player ship onto a key
    shipData has never heard of is a worse outcome than flying the wrong ship, and a map
    naming a modded hull on a stock install is the ordinary way to get here."""
def _refresh_cached_blob (obj):
    """Point an agent's cached data_set back at the engine's CURRENT blob.
    
    `spawn_common` caches `obj.data_set` once and never revisits it, which is correct
    right up until the engine rebuilds the blob underneath it. Reading it back off the
    live engine object is the only way the script layer can notice.
    
    Best-effort by design: a mock or an agent with no engine object simply keeps what it
    had, and a refresh must never be the thing that breaks a roster apply."""
def _set_parked (so_id, parked, rec):
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
    again to wake it."""
def player_roster ():
    """Every record, in slot order."""
def player_roster_active_count ():
    """How many records are currently active."""
def player_roster_adopt ():
    """Take player ships the MISSION spawned itself into the roster, one record each.
    
    :func:`player_roster_seed` builds records from the authored ``PLAYER_LIST``, which is
    the path a mission takes when it lets the library create its players
    (``PLAYER_CREATE_DEFAULT``). A mission that spawns its own has ships and no records -
    and every console binds to records now, so its picker offered nothing to select and
    its rename/hull handlers ran against a slot of None.
    
    Adoption hands each un-slotted player ship the next free slot and stamps it the way
    ``player_ensure`` stamps one, so :func:`player_roster_resolve` finds it afterwards.
    The record is read OFF the ship: this describes what the mission already made, it
    does not decide anything. Nothing on the ship is written except the slot marker.
    
    Idempotent - a ship already holding a slot is skipped - so this is safe to call on
    every roster build, and safe beside a seeded roster (adopted slots land after it).
    
    Returns:
        list: the slots adopted, in the order they were adopted."""
def player_roster_apply (loadout=None, force=False):
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
        list: the slots that were actually modified."""
def player_roster_bind (slot, client_id):
    """Record that ``client_id`` is crewing ``slot`` (and no other)."""
def player_roster_bound (slot):
    """The clients crewing ``slot``, as recorded."""
def player_roster_bound_live (slot):
    """The clients crewing ``slot`` that are still CONNECTED.
    
    A binding outlives the console that made it - nothing tells the roster a client went
    away - and a stale one would block :func:`player_roster_release_inactive` forever, so
    the parked ships would accumulate for the rest of the session.
    
    Pruned against ``Gui.clients``, which is the connected-client registry. **Only when it
    has entries**: an empty one means "nobody is connected" and "nothing is tracking
    clients" equally, and off-engine (a unit test, a headless run) it is always empty. With
    no information the conservative answer is to keep the binding - refusing to delete a
    ship is a leak, deleting one somebody is flying is a crash."""
def player_roster_clear ():
    """Drop every record and binding. On the reset ledger."""
def player_roster_count_records ():
    """How much state is held. The reset-ledger probe."""
def player_roster_crew_warn_count ():
    """How many unloaded CREW_HULL keys have been reported. On the reset ledger."""
def player_roster_display (slot):
    """What a picker row should SHOW for a slot: ``{name, hull, side}``.
    
    Prefers the live ship when there is one, so a picker opened after the game started
    reflects reality rather than the roster's intentions - a mission may have renamed or
    refitted a ship since. Falls back to the record, which is the whole point: during setup
    there may be no object worth asking, and asking anyway is what this design removes.
    
    Returns the record's values with empty strings rather than None, so a caller can
    interpolate them straight into a style string."""
def player_roster_park_inactive ():
    """Ensure every inactive slot is parked and in standby. Idempotent.
    
    :func:`player_roster_set_count` already parks on the transition; this is the backstop
    for a ship that was already inactive before the roster knew about it, or whose standby
    push did not take. Cheap - it only touches slots that are not already suspended.
    
    Returns:
        list: the slots it had to park."""
def player_roster_rebind (slot=None):
    """Re-assign bound clients wherever a slot's engine id has changed.
    
    The engine owns ids, so a ``sim_create()`` wipe or a destroy-and-respawn hands a slot a
    NEW ship. The binding is the slot, so nothing above needs to know - but the engine
    assignment does, and this is what re-runs it.
    
    Returns:
        list: the slots that were re-assigned."""
def player_roster_record (slot):
    """The record for ``slot``, or None.
    
    ANSWERS None FOR A SLOT THAT IS NOT ONE, rather than raising. Every caller here
    already has a "there is no such record" path - the setters return False, the display
    returns empty strings - and a console screen legitimately holds no selection: a
    mission that spawns its own player ships has an empty roster, so the picker's
    `client_select_slot` is None and its rename/hull handlers arrive here with it.
    
    `int(None)` made that a TypeError inside an expression, and a failing expression
    STOPS the command - so the handler died mid-way and the crew's console reported a
    runtime error for what is simply "nothing is selected"."""
def player_roster_release_inactive ():
    """Delete the parked ships. The ONLY delete here, and only at the fluid->fixed edge.
    
    Refuses to release a slot a client is still bound to: a console pointing at a ship that
    is being freed is the whole failure this module exists to remove.
    
    Returns:
        list: the slots actually released."""
def player_roster_resolve (slot):
    """The live ship holding ``slot``, or None.
    
    Resolves through the slot ROLE and deliberately does not require ``__player__``: a
    parked ship has had that role stripped, and it must still be findable or the next count
    change would spawn a duplicate beside it instead of waking it up."""
def player_roster_seed (roster=None):
    """Build the records from a roster of dicts (defaults to ``SETTINGS["PLAYER_LIST"]``).
    
    Idempotent by slot: re-seeding an existing roster updates the authored fields and leaves
    active-ness and bindings alone, so this can be called again after a sim wipe without
    disturbing who is sitting where.
    
    Args:
        roster (list, optional): dicts with ``name``/``side``/``ship``/``face``.
    
    Returns:
        list: the records."""
def player_roster_set_count (n):
    """Activate the first ``n`` records and park the rest. NEVER deletes.
    
    Parking strips ``__player__``, hides the hull and clears the side - the state the ship
    was left in before it was deleted - but keeps the object and its slot role. So raising
    the count again wakes the same ship up rather than spawning a new one, which is what
    keeps its engine id stable across a count change.
    
    Returns:
        list: the slots whose active-ness actually changed."""
def player_roster_set_hull (slot, ship_key):
    """Choose a slot's hull. Writes the RECORD, never the ship.
    
    Kept apart from the authored ``ship`` so the two stay distinguishable: ``ship`` is what
    the mission rostered and is what a theater re-skins, while this is what the crew picked
    in front of the ship. The pick wins over every theater layer and loses to a game code -
    see the precedence comment in :func:`player_roster_apply`.
    
    Pass None to drop the pick and fall back to the theater."""
def player_roster_set_name (slot, name):
    """Rename a slot. Writes the RECORD, never the ship.
    
    The console picker's rename used to run ``picked_ship.name = ...`` per keystroke, and
    that lands in ``set_name`` -> ``blob.set("name_tag", ...)`` - ``ObjectDataBlob::Set``,
    the function in every one of this build's server crash dumps, called on a live ship
    while the sim ticks it. Writing the record instead means the setup screen touches no
    engine object at all; :func:`player_roster_apply` carries it across at Start.
    
    Other consoles still see the change immediately, because they render the same record."""
def player_roster_slot_of_client (client_id):
    """Which slot ``client_id`` is crewing, or None."""
def player_roster_slot_of_ship (so_id):
    """Which slot a ship holds, or None.
    
    The inverse of :func:`player_roster_resolve`, and the bridge a console needs: it knows
    the ship it just attached to and has to say which SLOT that was in order to bind.
    Reads the slot marker written by ``player_ensure``, so it answers for a parked ship too."""
def player_roster_slots (active_only=True):
    """The slot numbers a picker should offer, in order.
    
    The list a console picker binds to. Slots rather than ships, because a slot cannot be
    freed underneath a live screen - which is the whole reason the old snapshot needed
    filtering, clamping and re-resolving everywhere it was touched.
    
    Args:
        active_only (bool): only slots that are being flown. False includes parked ones."""
def player_roster_unbind (client_id):
    """Forget ``client_id`` wherever it was bound."""
def player_ship_rebuild_stats (obj):
    """Re-derive a player ship's stats from the hull it is CURRENTLY wearing.
    
    Setting the hull key only changes the ART. `SpaceObject.set_ship_data_key` writes
    `data_tag` and tells the clients, and that is the whole of it - while the engine
    derives shields, beams, tubes and turn rate from shipData at CREATION. So a ship
    re-hulled after spawn keeps the previous hull's numbers: a Defiant that flies with
    Galaxy shields, which is what the Gamma with a Q playtest reported (2026-09-01).
    
    Also re-reads the data blob, because the rebuild replaces it. `SpaceObject._data_set`
    is captured once at spawn and nothing else refreshes it, so afterwards the agent
    would keep handing out the pre-rebuild handle while `_alive` stays True - and the
    guard that exists for deletion never fires. Every later `to_blob(id).set(...)` would
    write through the dead one.
    
    Best-effort by design: an agent with no engine object keeps what it had, and a
    rebuild must never be the thing that breaks its caller.
    
    Args:
        obj (SpaceObject): the player ship, already wearing the hull it should have.
    
    Returns:
        bool: True if the engine actually rebuilt it."""
