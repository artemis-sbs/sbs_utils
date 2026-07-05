def _spawn_npc (x, y, z, name, side, art, behave):
    ...
def create_anomaly (x, y, z, pickup_type, name=None):
    """2.8 ``create type="Anomaly"`` -> a Cosmos collectible pickup.
    
    Maps ``pickup_type`` (2.8 pickupType 0..7) to an upgrade key and spawns via the
    core ``pickup_spawn``. Returns ``None`` for type 8 (beacon), which has no Cosmos
    equivalent."""
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
def create_neutral (x, y, z, art, name=None, side='civilian', behave='behav_npcship'):
    """2.8 ``create type="neutral"`` -> an NPC ship."""
def create_player (x, y, z, art, name=None, side='tsn'):
    """2.8 ``create type="player"`` -> a player ship. Returns the ship ID."""
def create_station (x, y, z, art, name=None, side='friendly', behave='behav_station'):
    """2.8 ``create type="station"`` -> a station (first role = side, plus 'station')."""
def destroy (handle):
    """2.8 ``destroy``: remove a named object from the game.
    
    ``handle`` may be an id, object, or the value returned by an a2x_create_*.
    Returns True if an object was deleted."""
def destroy_near (x, y, z, radius, kind='all'):
    """2.8 ``destroy_near``: delete unnamed objects of ``kind`` within ``radius`` of a
    point. ``kind`` is a 2.8 type (nebulas/asteroids/mines/whales/drones/all). The
    point is given in 2.8 coords and flipped internally. Returns the count deleted."""
def monster_art (monster_type):
    """2.8 ``monsterType`` -> Cosmos art key (placeholder for types without real art)."""
def monster_role (monster_type):
    """2.8 ``monsterType`` -> a ``creature_*`` role tag (the re-skin seam)."""
def pickup_key (pickup_type):
    """2.8 ``pickupType`` (int) -> Cosmos upgrade key, or ``None`` for type 8 (beacon)."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
