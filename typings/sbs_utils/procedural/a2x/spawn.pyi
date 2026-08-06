def _spawn_npc (x, y, z, name, side, art, behave):
    ...
def clear_station_carried (station):
    """2.8 ``clear_player_station_carried name="X"``: remove a station's stored single-seat
    craft.
    
    Deletes the STANDBY (in-hangar, not launched) craft hosted by the station --
    ``linked_to(station, "hangar_craft") & role("standby") & role("cockpit")`` -- leaving any
    already-launched craft flying. Returns the count removed."""
def create_anomaly (x, y, z, pickup_type, name=None):
    """2.8 ``create type="Anomaly"`` -> a Cosmos collectible pickup.
    
    Maps ``pickup_type`` (2.8 pickupType 0..7) to an upgrade key and spawns via the
    core ``pickup_spawn``. pickupType 8 (beacon) spawns an inert, recoverable Beacon
    (role ``beacon`` + ``behav_pickup``): the LegendaryMissions fabrication addon's
    fly-over route credits ``Beacon_NUM`` when a player collects it. a2x references LM
    only by the ``beacon`` role name (feature-detected), never by import."""
def create_black_hole (x, y, z, gravity_radius=10000, gravity_strength=1.0, turbulence_strength=1.0, collision_damage=200):
    """2.8 ``create type="blackHole"`` -> a Cosmos maelstrom terrain object."""
def create_enemy (x, y, z, art, name=None, side='enemy', behave='behav_npcship'):
    """2.8 ``create type="enemy"`` -> an NPC ship (no brain attached here; see a2x_add_ai)."""
def create_generic (x, y, z, art, name=None, side=None, behave='behav_do_nothing'):
    """2.8 ``create type="genericMesh"`` -> nearest-art NPC (raw .dxs meshes have no
    Cosmos equivalent; ``art`` is a best-fit chosen by the caller)."""
def create_monster (x, y, z, monster_type=0, art=None, name=None, side='monster', behave='behav_do_nothing'):
    """2.8 ``create type="monster"`` -> a placeholder creature.
    
    Uses real Cosmos art for classic (0) and derelict (8); a placeholder hull for the
    rest. Always tags the spawn with a ``creature_*`` role so the whole field can be
    re-skinned in one query when Cosmos ships real creature art."""
def create_neutral (x, y, z, art, name=None, side='civ', behave='behav_npcship'):
    """2.8 ``create type="neutral"`` -> an NPC ship."""
def create_player (x, y, z, art, name=None, side='tsn', slot=None):
    """2.8 ``create type="player"`` -> a player ship. Returns the ship ID.
    
    Tags the ship ``default_player_ship`` as it spawns. That is the role the
    LegendaryMissions crew-select / loadout machinery keys on, and it is normally added by
    LM's own ``create_default_player_ships`` -- which a converted mission turns off, since
    those ships are built on side "tsn" rather than the mission's declared player side.
    Doing it HERE rather than in a later route means a ship created mid-mission (some 2.8
    missions spawn players from an event, not ``<start>``) is tagged too.
    
    Pass ``slot`` (the 2.8 ``player_slot``) to make creation IDEMPOTENT: the ship is
    spawned only if that slot is empty, so a ``//shared/signal/create_player_ships``
    route emitted twice does not duplicate the roster. It also makes
    :func:`player_ship` resolve the slot by identity rather than by position. Without
    a slot this behaves exactly as before and every call mints a new hull."""
def create_station (x, y, z, art, name=None, side='friendly', behave='behav_station'):
    """2.8 ``create type="station"`` -> a station (first role = side, plus 'station')."""
def destroy (handle):
    """2.8 ``destroy``: remove a named object from the game.
    
    ``handle`` may be an id, object, or the value returned by an a2x_create_*.
    Returns True if an object was deleted."""
def destroy_named (name):
    """2.8 ``destroy`` by NAME for an object the converter could not statically capture --
    the name has no ``create`` the tool saw (created some other way, or a dead reference the
    2.8 mission left in). Deletes every current space object whose name matches; a no-op if
    none exist -- which mirrors 2.8, where destroying a missing object does nothing. Returns
    the count deleted."""
def destroy_near (x, y, z, radius, kind='all'):
    """2.8 ``destroy_near``: delete unnamed objects of ``kind`` within ``radius`` of a
    point. ``kind`` is a 2.8 type (nebulas/asteroids/mines/whales/drones/all). The
    point is given in 2.8 coords and flipped internally. Returns the count deleted."""
def destroy_near_object (obj, radius, kind='all'):
    """2.8 ``destroy_near`` centered on a NAMED object: delete objects of ``kind`` within
    ``radius`` of that object's runtime position (excluding the object itself). Like
    :func:`destroy_near` but the centre is a live Cosmos object, so its position is already
    in Cosmos space (no coord flip). Returns the count deleted."""
def monster_art (monster_type):
    """2.8 ``monsterType`` -> Cosmos art key (placeholder for types without real art)."""
def monster_role (monster_type):
    """2.8 ``monsterType`` -> a ``creature_*`` role tag (the re-skin seam)."""
def named (name):
    """Resolve a 2.8 object NAME to a live Cosmos object ID at runtime.
    
    For a condition (or command) that references an object the converter could not statically
    capture -- a forward reference, or a name mismatch in the 2.8 source. Returns the first
    space object whose name matches, or ``None`` if none exists.
    
    Passing that ``None`` on is safe only through the guarded helpers: ``object_exists(None)``
    is False, and ``a2x_distance_less`` / ``a2x_distance_greater`` (and the core
    ``distance_less`` / ``distance_greater`` promises) treat a missing object as "condition
    does not hold". It is NOT safe to hand to ``sbs.distance_id`` directly -- the engine
    errors with "sbs.distance_id was sent None". (A bare ``role(name)`` set would throw too.)"""
def pickup_key (pickup_type):
    """2.8 ``pickupType`` (int) -> Cosmos upgrade key, or ``None`` for type 8 (beacon)."""
def place_player (x, y, z, slot=0, name=None, side=None):
    """2.8 ``create type="player"`` OUTSIDE the ``<start>`` block: PLACE the ship, don't
    make one. Returns the ship ID, or None if that slot has no ship.
    
    In 2.8 the player ships already exist -- the crew picks one at the console -- and
    ``create type="player"`` only positions and configures the ship in that slot. There are
    exactly 8 slots, so the command can never produce a 9th ship. For the ``<start>`` block
    that distinction does not matter (Cosmos has nothing yet, so we spawn, via
    :func:`create_player`), but for a create in an EVENT it is the whole meaning: the crew
    is already flying that ship.
    
    Spawning there instead gave the mission a second, unmanned hull while the crew sat on
    the original -- and for a mission whose only player create is in an event
    (MISS_Medusa's_Maze picks one of eight maze entrances at random) it meant no ship
    existed at ship-select time at all.
    
    Repositioning uses the engine's own ``reposition_space_object``, the same call
    ``respawn_player_ship`` uses, so the move is seen by physics rather than written behind
    its back. ``name`` renames the ship in place (2.8 missions rename per entrance);
    ``side`` moves it to another declared side, diplomacy following along."""
def player_ship (slot=0):
    """2.8 references a player ship by name or slot; Cosmos references by ID. Resolve a
    2.8 ``player_slot`` (0-based) to the Cosmos player ship at that slot. Returns its ID,
    or ``None`` if that slot has no player ship.
    
    Prefers a ship STAMPED with the slot (``create_player(..., slot=N)`` /
    ``player_ensure``), which is stable no matter what else spawns or respawns.
    
    Falls back to position in the player set for ships with no stamp. That fallback
    sorts by id: ``role()`` returns an unordered set, so the historical unsorted index
    made "slot N" mean hash order rather than creation order, and it could silently
    change as ships were added or removed. Sorting matches how every other consumer
    re-derives slot order (``sorted(..., key=lambda p: p.id)``), and is identical to
    the old behavior for the single-player-ship case."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
def set_hull_side (handle, side):
    """Force an object's ``hull_side`` blob field to match the side it was spawned on.
    
    ``hull_side`` is SCAN information the engine seeds from the ``side`` field of the
    hull's shipData entry -- so a ship on art ``tsn_light_cruiser`` reads "TSN" on the
    Science object list no matter which side it actually belongs to. A converted 2.8
    mission puts its crew on its own declared side (``friendly``), so the two disagreed:
    diplomacy said one thing and the Science list showed another.
    
    This overwrites the scan string with the spawned side, taking the side's display name
    when it resolves to a registered side and the raw key otherwise. ``side`` may be the
    full spawn string ("friendly, a2x_spare_player") -- only the first token is the side.
    
    EXPEDIENT, not the final answer: the real fix is for the hull's shipData not to carry
    a side at all, since side is a property of the ship, not of the hull."""
