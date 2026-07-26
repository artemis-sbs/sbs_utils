"""Legacy-style object creation mirroring Artemis 2.8 ``<create .../>`` (named objects).

Covers the 2.8 ``create`` types that map onto core Cosmos spawning:
player, enemy, neutral, station, monster, blackHole, genericMesh. All positions are
given in **Artemis 2.8 coordinates** and converted internally via :func:`coords.pos`.

Art resolution is intentionally **not** done here: 2.8 ``raceKeys``/``hullKeys`` map to
Cosmos art only through a curated crosswalk (the migration tool's ``hullmap``). These
functions take an already-resolved ``art`` key, so ``a2x`` carries no fragile art
table -- only the small, stable creature map (the re-skin seam) lives here.

All ``create_*`` functions return the spawned object's **ID**, not the object -- an ID
is a stable grounded handle, whereas an object reference can go stale when the engine
deletes the object. Pass the ID to the other ``a2x_*`` helpers; they re-validate with
``to_space_object(id)`` and no-op safely if the object is gone.

Pickups/anomalies use :func:`create_anomaly`, which maps the 2.8 ``pickupType`` to an
upgrade key (:func:`pickup_key`) and spawns via the core ``pickup_spawn``
(``sbs_utils.procedural.items`` -- moved out of LegendaryMissions, so no LM dependency).
The item *art* still comes from registered ``item/`` labels (e.g. the upgrades addon);
without them a pickup falls back to placeholder art.
"""

from .coords import pos

# --- 2.8 pickupType (0..8) -> Cosmos upgrade key (pure mapping, no LM dependency) ---
_PICKUP_KEYS = {
    0: "hidens_powercell",    # ITEMTYPE_ENERGY
    1: "vigoranium_nodule",   # ITEMTYPE_RESTORE_DAMCON
    2: "cetrocite_crystal",   # ITEMTYPE_HEAT_BUFF
    3: "lateral_array",       # ITEMTYPE_SCAN_BUFF
    4: "tauron_focuser",      # ITEMTYPE_WEAP_BUFF
    5: "infusion_pcoils",     # ITEMTYPE_SPEED_BUFF
    6: "carapaction_coil",    # ITEMTYPE_SHIELD_BUFF
    7: "secret_codecase",     # ITEMTYPE_COMM_BUFF
    # 8 = ITEMTYPE_BEACON has no direct Cosmos pickup -> None (caller handles)
}

# --- 2.8 monsterType (0..8) -> (Cosmos art, creature role) -------------------------
# Only 0 (classic) and 8 (derelict) have real Cosmos art today; 1..7 use a placeholder
# hull but always carry a creature_* role so a future re-skin is a single role query.
_MONSTER_ART = {
    0: "monster_charbdis",  # CLASSIC  (real art)
    8: "wreck",             # DERELICT (real art)
}
_MONSTER_ROLE = {
    0: "creature_classic",
    1: "creature_whale",
    2: "creature_shark",
    3: "creature_dragon",
    4: "creature_piranha",
    5: "creature_tube",
    6: "creature_bug",
    7: "creature_jelly",
    8: "creature_derelict",
}
_MONSTER_PLACEHOLDER_ART = "monster_charbdis"


def pickup_key(pickup_type):
    """2.8 ``pickupType`` (int) -> Cosmos upgrade key, or ``None`` for type 8 (beacon)."""
    return _PICKUP_KEYS.get(int(pickup_type))


def monster_art(monster_type):
    """2.8 ``monsterType`` -> Cosmos art key (placeholder for types without real art)."""
    return _MONSTER_ART.get(int(monster_type), _MONSTER_PLACEHOLDER_ART)


def monster_role(monster_type):
    """2.8 ``monsterType`` -> a ``creature_*`` role tag (the re-skin seam)."""
    return _MONSTER_ROLE.get(int(monster_type), "creature_unknown")


def set_hull_side(handle, side):
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
    a side at all, since side is a property of the ship, not of the hull.
    """
    from sbs_utils.procedural.query import to_id, set_data_set_value
    from sbs_utils.procedural.sides import to_side_id
    from sbs_utils.procedural.inventory import get_inventory_value

    if not side:
        return False
    key = str(side).split(",")[0].strip()
    if not key or key == "#":
        return False
    label = key
    sid = to_side_id(key, warn=False)
    if sid is not None:
        label = get_inventory_value(sid, "side_name", None) or key
    oid = to_id(handle)
    if oid is None:
        return False
    set_data_set_value(oid, "hull_side", label, 0)
    return True


def _spawn_npc(x, y, z, name, side, art, behave):
    from sbs_utils.procedural.spawn import npc_spawn
    from sbs_utils.procedural.query import to_id
    v = pos(x, y, z)
    # Return the ID, not the object: it's the safe grounded handle (the engine can
    # delete the object later; callers re-validate with to_space_object(id)).
    sid = to_id(npc_spawn(v.x, v.y, v.z, name, side, art, behave))
    set_hull_side(sid, side)   # scan info follows the SIDE, not the hull's shipData entry
    return sid


def create_enemy(x, y, z, art, name=None, side="enemy", behave="behav_npcship"):
    """2.8 ``create type="enemy"`` -> an NPC ship (no brain attached here; see a2x_add_ai)."""
    return _spawn_npc(x, y, z, name, side, art, behave)


def create_neutral(x, y, z, art, name=None, side="civ", behave="behav_npcship"):
    """2.8 ``create type="neutral"`` -> an NPC ship."""
    return _spawn_npc(x, y, z, name, side, art, behave)


def create_station(x, y, z, art, name=None, side="friendly", behave="behav_station"):
    """2.8 ``create type="station"`` -> a station (first role = side, plus 'station')."""
    return _spawn_npc(x, y, z, name, f"{side}, station", art, behave)


def create_generic(x, y, z, art, name=None, side=None, behave="behav_do_nothing"):
    """2.8 ``create type="genericMesh"`` -> nearest-art NPC (raw .dxs meshes have no
    Cosmos equivalent; ``art`` is a best-fit chosen by the caller)."""
    return _spawn_npc(x, y, z, name, side, art, behave)


def create_player(x, y, z, art, name=None, side="tsn"):
    """2.8 ``create type="player"`` -> a player ship. Returns the ship ID.

    Tags the ship ``default_player_ship`` as it spawns. That is the role the
    LegendaryMissions crew-select / loadout machinery keys on, and it is normally added by
    LM's own ``create_default_player_ships`` -- which a converted mission turns off, since
    those ships are built on side "tsn" rather than the mission's declared player side.
    Doing it HERE rather than in a later route means a ship created mid-mission (some 2.8
    missions spawn players from an event, not ``<start>``) is tagged too.
    """
    from sbs_utils.procedural.spawn import player_spawn
    from sbs_utils.procedural.query import to_id
    from sbs_utils.procedural.roles import add_role
    v = pos(x, y, z)
    sid = to_id(player_spawn(v.x, v.y, v.z, name, side, art))
    add_role(sid, "default_player_ship")
    set_hull_side(sid, side)   # scan info follows the SIDE, not the hull's shipData entry
    return sid


def create_monster(x, y, z, monster_type=0, art=None, name=None,
                   side="monster", behave="behav_do_nothing"):
    """2.8 ``create type="monster"`` -> a placeholder creature.

    Uses real Cosmos art for classic (0) and derelict (8); a placeholder hull for the
    rest. Always tags the spawn with a ``creature_*`` role so the whole field can be
    re-skinned in one query when Cosmos ships real creature art.
    """
    from sbs_utils.procedural.roles import add_role

    if art is None:
        art = monster_art(monster_type)
    sid = _spawn_npc(x, y, z, name, side, art, behave)  # an ID
    add_role(sid, monster_role(monster_type))
    return sid


def create_anomaly(x, y, z, pickup_type, name=None):
    """2.8 ``create type="Anomaly"`` -> a Cosmos collectible pickup.

    Maps ``pickup_type`` (2.8 pickupType 0..7) to an upgrade key and spawns via the
    core ``pickup_spawn``. pickupType 8 (beacon) spawns an inert, recoverable Beacon
    (role ``beacon`` + ``behav_pickup``): the LegendaryMissions fabrication addon's
    fly-over route credits ``Beacon_NUM`` when a player collects it. a2x references LM
    only by the ``beacon`` role name (feature-detected), never by import.
    """
    from sbs_utils.procedural.items import pickup_spawn
    from sbs_utils.procedural.query import to_id

    v = pos(x, y, z)
    if int(pickup_type) == 8:
        from sbs_utils.procedural.spawn import terrain_spawn
        return to_id(terrain_spawn(v.x, v.y, v.z, name or "Beacon", "#,beacon", "danger_4a", "behav_pickup"))
    key = pickup_key(pickup_type)
    if key is None:
        return None
    return to_id(pickup_spawn(v.x, v.y, v.z, key, name=name))


def destroy(handle):
    """2.8 ``destroy``: remove a named object from the game.

    ``handle`` may be an id, object, or the value returned by an a2x_create_*.
    Returns True if an object was deleted.
    """
    from sbs_utils.procedural.query import to_space_object

    o = to_space_object(handle)
    if o is not None:
        o.delete_object()
        return True
    return False


def clear_station_carried(station):
    """2.8 ``clear_player_station_carried name="X"``: remove a station's stored single-seat
    craft.

    Deletes the STANDBY (in-hangar, not launched) craft hosted by the station --
    ``linked_to(station, "hangar_craft") & role("standby") & role("cockpit")`` -- leaving any
    already-launched craft flying. Returns the count removed.
    """
    from sbs_utils.procedural.query import to_space_object
    from sbs_utils.procedural.links import linked_to
    from sbs_utils.procedural.roles import role

    so = to_space_object(station)
    if so is None:
        return 0
    n = 0
    for craft in linked_to(so, "hangar_craft") & role("standby") & role("cockpit"):
        c = to_space_object(craft)
        if c is not None:
            c.delete_object()
            n += 1
    return n


def named(name):
    """Resolve a 2.8 object NAME to a live Cosmos object ID at runtime.

    For a condition (or command) that references an object the converter could not statically
    capture -- a forward reference, or a name mismatch in the 2.8 source. Returns the first
    space object whose name matches, or ``None`` if none exists.

    Passing that ``None`` on is safe only through the guarded helpers: ``object_exists(None)``
    is False, and ``a2x_distance_less`` / ``a2x_distance_greater`` (and the core
    ``distance_less`` / ``distance_greater`` promises) treat a missing object as "condition
    does not hold". It is NOT safe to hand to ``sbs.distance_id`` directly -- the engine
    errors with "sbs.distance_id was sent None". (A bare ``role(name)`` set would throw too.)
    """
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_space_object, to_id

    for oid in role("__SPACE_OBJECT__"):
        o = to_space_object(oid)
        if o is not None and getattr(o, "name", None) == name:
            return to_id(oid)
    return None


def destroy_named(name):
    """2.8 ``destroy`` by NAME for an object the converter could not statically capture --
    the name has no ``create`` the tool saw (created some other way, or a dead reference the
    2.8 mission left in). Deletes every current space object whose name matches; a no-op if
    none exist -- which mirrors 2.8, where destroying a missing object does nothing. Returns
    the count deleted.
    """
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_space_object

    n = 0
    for oid in role("__SPACE_OBJECT__"):
        o = to_space_object(oid)
        if o is not None and getattr(o, "name", None) == name:
            o.delete_object()
            n += 1
    return n


# 2.8 destroy_near type -> Cosmos role.
_NEAR_ROLE = {
    "nebulas": "nebula", "asteroids": "asteroid", "mines": "mine",
    "whales": "creature_whale", "drones": "drone",
}


def destroy_near(x, y, z, radius, kind="all"):
    """2.8 ``destroy_near``: delete unnamed objects of ``kind`` within ``radius`` of a
    point. ``kind`` is a 2.8 type (nebulas/asteroids/mines/whales/drones/all). The
    point is given in 2.8 coords and flipped internally. Returns the count deleted.
    """
    from sbs_utils.procedural.space_objects import closest_list
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_space_object

    c = pos(x, y, z)
    the_set = role(_NEAR_ROLE[kind]) if kind in _NEAR_ROLE else role("__SPACE_OBJECT__")
    n = 0
    for cd in closest_list(c, the_set, max_dist=radius):
        o = to_space_object(cd)
        if o is not None:
            o.delete_object()
            n += 1
    return n


def destroy_near_object(obj, radius, kind="all"):
    """2.8 ``destroy_near`` centered on a NAMED object: delete objects of ``kind`` within
    ``radius`` of that object's runtime position (excluding the object itself). Like
    :func:`destroy_near` but the centre is a live Cosmos object, so its position is already
    in Cosmos space (no coord flip). Returns the count deleted.
    """
    from sbs_utils.procedural.space_objects import closest_list
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_space_object, to_id
    from sbs_utils.vec import Vec3

    o = to_space_object(obj)
    if o is None:
        return 0
    oid = to_id(obj)
    the_set = role(_NEAR_ROLE[kind]) if kind in _NEAR_ROLE else role("__SPACE_OBJECT__")
    n = 0
    for cd in closest_list(Vec3(o.pos), the_set, max_dist=radius):
        if to_id(cd) == oid:
            continue
        t = to_space_object(cd)
        if t is not None:
            t.delete_object()
            n += 1
    return n


def create_black_hole(x, y, z, gravity_radius=10000, gravity_strength=1.0,
                     turbulence_strength=1.0, collision_damage=200):
    """2.8 ``create type="blackHole"`` -> a Cosmos maelstrom terrain object."""
    from sbs_utils.procedural.terrain import terrain_spawn_black_hole
    from sbs_utils.procedural.query import to_id
    v = pos(x, y, z)
    return to_id(terrain_spawn_black_hole(v.x, v.y, v.z, gravity_radius=gravity_radius,
                                          gravity_strength=gravity_strength,
                                          turbulence_strength=turbulence_strength,
                                          collision_damage=collision_damage))


def player_ship(slot=0):
    """2.8 references a player ship by name or slot; Cosmos references by ID. Resolve a
    2.8 ``player_slot`` (0-based index into the game's player ships) to the Cosmos player
    ship at that slot -- the ``slot``-th member of ``role("__player__")``. Returns its ID,
    or ``None`` if that slot has no player ship."""
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_id_list
    ids = to_id_list(role("__player__"))
    try:
        return ids[int(slot)]
    except (IndexError, ValueError, TypeError):
        return None
