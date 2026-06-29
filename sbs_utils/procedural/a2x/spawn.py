"""Legacy-style object creation mirroring Artemis 2.8 ``<create .../>`` (named objects).

Covers the 2.8 ``create`` types that map onto core Cosmos spawning:
player, enemy, neutral, station, monster, blackHole, genericMesh. All positions are
given in **Artemis 2.8 coordinates** and converted internally via :func:`coords.pos`.

Art resolution is intentionally **not** done here: 2.8 ``raceKeys``/``hullKeys`` map to
Cosmos art only through a curated crosswalk (the migration tool's ``hullmap``). These
functions take an already-resolved ``art`` key, so ``a2x`` carries no fragile art
table -- only the small, stable creature map (the re-skin seam) lives here.

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


def _spawn_npc(x, y, z, name, side, art, behave):
    from sbs_utils.procedural.spawn import npc_spawn
    v = pos(x, y, z)
    return npc_spawn(v.x, v.y, v.z, name, side, art, behave)


def create_enemy(x, y, z, art, name=None, side="enemy", behave="behav_npcship"):
    """2.8 ``create type="enemy"`` -> an NPC ship (no brain attached here; see a2x_add_ai)."""
    return _spawn_npc(x, y, z, name, side, art, behave)


def create_neutral(x, y, z, art, name=None, side="civilian", behave="behav_npcship"):
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
    """2.8 ``create type="player"`` -> a player ship."""
    from sbs_utils.procedural.spawn import player_spawn
    v = pos(x, y, z)
    return player_spawn(v.x, v.y, v.z, name, side, art)


def create_monster(x, y, z, monster_type=0, art=None, name=None,
                   side="monster", behave="behav_do_nothing"):
    """2.8 ``create type="monster"`` -> a placeholder creature.

    Uses real Cosmos art for classic (0) and derelict (8); a placeholder hull for the
    rest. Always tags the spawn with a ``creature_*`` role so the whole field can be
    re-skinned in one query when Cosmos ships real creature art.
    """
    from sbs_utils.procedural.roles import add_role
    from sbs_utils.procedural.query import to_id

    if art is None:
        art = monster_art(monster_type)
    so = _spawn_npc(x, y, z, name, side, art, behave)
    add_role(to_id(so), monster_role(monster_type))
    return so


def create_anomaly(x, y, z, pickup_type, name=None):
    """2.8 ``create type="Anomaly"`` -> a Cosmos collectible pickup.

    Maps ``pickup_type`` (2.8 pickupType 0..7) to an upgrade key and spawns via the
    core ``pickup_spawn``. Returns ``None`` for type 8 (beacon), which has no Cosmos
    equivalent.
    """
    from sbs_utils.procedural.items import pickup_spawn

    key = pickup_key(pickup_type)
    if key is None:
        return None
    v = pos(x, y, z)
    return pickup_spawn(v.x, v.y, v.z, key, name=name)


def destroy(handle):
    """2.8 ``destroy``: remove a named object from the game.

    ``handle`` may be an id, object, or the value returned by an a2x_create_*.
    Returns True if an object was deleted.
    """
    from sbs_utils.procedural.query import to_object

    o = to_object(handle)
    if o is not None:
        o.delete_object()
        return True
    return False


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
    from sbs_utils.procedural.query import to_object

    c = pos(x, y, z)
    the_set = role(_NEAR_ROLE[kind]) if kind in _NEAR_ROLE else role("__SPACE_OBJECT__")
    n = 0
    for cd in closest_list(c, the_set, max_dist=radius):
        o = to_object(cd)
        if o is not None:
            o.delete_object()
            n += 1
    return n


def create_black_hole(x, y, z, gravity_radius=10000, gravity_strength=1.0,
                     turbulence_strength=1.0, collision_damage=200):
    """2.8 ``create type="blackHole"`` -> a Cosmos maelstrom terrain object."""
    from sbs_utils.procedural.terrain import terrain_spawn_black_hole
    v = pos(x, y, z)
    return terrain_spawn_black_hole(v.x, v.y, v.z, gravity_radius=gravity_radius,
                                    gravity_strength=gravity_strength,
                                    turbulence_strength=turbulence_strength,
                                    collision_damage=collision_damage)
