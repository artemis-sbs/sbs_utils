from sbs_utils.vec import Vec3
def closest_list (source: int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData | sbs_utils.agent.Agent | sbs_utils.vec.Vec3, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """Return all objects in a set within optional distance and filter criteria.
    
    Args:
        source (Agent | int | CloseData | SpawnData | Vec3): The reference
            agent ID, object, or position.
        the_set (set[int]): IDs of candidates to test.
        max_dist (float, optional): Maximum distance to include. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``
            applied to each candidate. Defaults to None.
    
    Returns:
        list[CloseData]: All qualifying candidates with their distances."""
def color_noise (r_min, r_max, g_min, g_max, b_min, b_max, a_min=255, a_max=255):
    ...
def npc_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a non-player (NPC) ship into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the ship belongs to.
        ship_key (str): Ship template key from shipData.
        behave_id (str): Behavior type identifier.
    
    Returns:
        SpawnData: Spawn data for the new NPC."""
def plain_asteroid_keys ():
    """Return all plain asteroid keys, excluding crystal asteroids (cached).
    
    Returns:
        list[str]: Plain asteroid type keys."""
def prefab_spawn (label, data=None, OFFSET_X=None, OFFSET_Y=None, OFFSET_Z=None):
    """Spawn a prefab label as an independent task and return it.
    
    Positional keys ``START_X``, ``START_Y``, ``START_Z`` inside ``data``
    set the spawn origin (default 0). The ``OFFSET_*`` params shift that
    origin without modifying the original ``data`` dict. If ``data`` contains
    a ``NAME`` key with a ``#`` placeholder, ``prefab_autoname`` is applied
    to generate a unique name.
    
    Args:
        label (str | Label): The label to spawn.
        data (dict, optional): Variables passed into the prefab task. May
            include ``START_X``, ``START_Y``, ``START_Z``, and ``NAME``.
            Defaults to None.
        OFFSET_X (float, optional): X offset added to ``START_X``. Defaults
            to None (no offset).
        OFFSET_Y (float, optional): Y offset added to ``START_Y``. Defaults
            to None (no offset).
        OFFSET_Z (float, optional): Z offset added to ``START_Z``. Defaults
            to None (no offset).
    
    Returns:
        MastAsyncTask: The running prefab task, or ``None`` if the label is
            invalid."""
def random_terran (face=None, civilian=None):
    """Create a random terran face.
    
    Args:
        face (int | None): The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
        civilian (boolean | None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def scatter_ring (ca, cr, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> collections.abc.Generator:
    """Calculate the points on rings with each ring has same count.
    
    Args:
        ca (int): The number of points to generate on each ring
        cr (int): The number of rings
        x (float): The start point/origin
        y (float): The start point/origin
        z (float): The start point/origin
        outer_r (float): The radius
        inner_r (float, optional): The inner radius. Default is 0.
        start (float): degrees start angle. Default is 0.
        end (float): degrees start angle. Default is 90.0.
        random (bool): When True, points will be randomly placed. When False, points will be evenly placed.
    
    Returns:
        points (Generator): A generator of Vec3"""
def set_face (ship_id, face):
    """Sets a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string"""
def terrain_asteroid_clusters (terrain_value, center=None, selectable=False, points=None):
    """Scatter random asteroid clusters across the map.
    
    Args:
        terrain_value (int): 0–4 scale controlling cluster count and density.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False.
        points (list[Vec3], optional): Explicit cluster origins instead of
            random positions. Defaults to None.
    
    Returns:
        list[Vec3]: The cluster centre positions used."""
def terrain_nebula_color (cluster_color):
    ...
def terrain_nebula_spawn (v2, height, cluster_color, diameter, density, selectable):
    ...
def terrain_random_point_box (all_points, left, top, front, right, bottom, back, inside=True, count=1):
    """wraps a set of points in a generator returning unique points inside (or outside) a box
    
    
    Args:
        all_points (_type_): The source set of points
        left (_type_): left (x)
        top (_type_): top (y)
        front (_type_): front (z)
        right (_type_): right (x)
        bottom (_type_): bottom (y)
        back (_type_): back (z)
        inside (bool, optional): Within the box or out side it. Defaults to True.
        count (int, optional): Number of points each iteration. Defaults to True.
    
    Yields:
        Vec3 | list[Vec3]: A random point"""
def terrain_remove_points_near (all_points, test_points, radius):
    """Return only the points that are outside a given radius of every test point.
    
    Filters ``all_points`` by removing any point within ``radius`` of at least
    one entry in ``test_points``. Useful for clearing spawn candidates around
    existing objects.
    
    Args:
        all_points (list[Vec3]): Candidate spawn positions.
        test_points (list[Vec3 | Agent | int]): Exclusion reference points.
            Non-``Vec3`` items are resolved to their space-object position.
        radius (float): Exclusion radius in simulation units.
    
    Returns:
        list[Vec3]: Subset of ``all_points`` farther than ``radius`` from every
            test point."""
def terrain_setup_nebula (nebula, diameter=4000, density_coef=1.0, color='yellow'):
    """Apply visual and physical properties to an existing nebula space object.
    
    Args:
        nebula (SpaceObject | Agent): The nebula to configure.
        diameter (int, optional): Nebula diameter (capped at ``NEB_MAX_SIZE``).
            Defaults to 4000.
        density_coef (float, optional): Visual nebula density multiplier (3D
            view). Defaults to 1.0.
        color (str | dict, optional): Colour name or a full colour dict.
            Defaults to ``"yellow"``."""
def terrain_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a passive terrain object into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the object belongs to, or ``None``.
        ship_key (str): Object template key from shipData.
        behave_id (str): Behavior type identifier.
    
    Returns:
        SpawnData: Spawn data for the new terrain object."""
def terrain_spawn_asteroid_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, selectable=False, is_tiled=False):
    """Spawn asteroids scattered inside a box volume; density is per 1000 units.
    
    Args:
        x (float): Box origin X.
        y (float): Box origin Y (unused for placement; passed through).
        z (float): Box origin Z.
        size_x (int, optional): Box width along X. Defaults to 10000.
        size_z (int | None, optional): Box depth along Z. Defaults to
            ``size_x``.
        density_scale (float, optional): Multiplier for asteroid count.
            Defaults to 1.0.
        density (int, optional): Base density per 1000 units. Defaults to 1.
        height (int, optional): Box height (Y spread). Defaults to 1000.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False.
        is_tiled (bool, optional): Adjust origin for map-editor tile coordinates.
            Defaults to False."""
def terrain_spawn_asteroid_points (x, y, z, points, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """Spawn asteroids along a polyline defined by a list of 2D points.
    
    Offsets each point by ``(x, z)`` and scatters asteroids along the
    resulting line segments.
    
    Args:
        x (float): X offset applied to all points.
        y (float): Unused.
        z (float): Z offset applied to all points.
        points (list[tuple]): 2D ``(x, z)`` vertices defining the polyline.
        radius (int, optional): Unused. Defaults to 10000.
        density_scale (float, optional): Multiplier for per-segment density.
            Defaults to 1.0.
        density (int, optional): Base density. Defaults to 1.
        height (int, optional): Y spread of each asteroid. Defaults to 1000.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False."""
def terrain_spawn_asteroid_scatter (cluster_spawn_points, height, selectable=False):
    """Spawn a randomised asteroid (with possible satellite cluster) at each given point.
    
    Args:
        cluster_spawn_points (Iterable[Vec3]): Spawn positions.
        height (int): Controls Y scatter range around each point.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False."""
def terrain_spawn_asteroid_sphere (x, y, z, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """Spawn asteroids scattered inside a sphere volume; density is per 1000 units.
    
    Args:
        x (float): Sphere centre X.
        y (float): Sphere centre Y.
        z (float): Sphere centre Z.
        radius (int, optional): Sphere radius. Defaults to 10000.
        density_scale (float, optional): Multiplier for asteroid count.
            Defaults to 1.0.
        density (int, optional): Base density per 1000 units. Defaults to 1.
        height (int, optional): Y spread of each asteroid. Defaults to 1000.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False."""
def terrain_spawn_black_hole (x, y, z, gravity_radius=1500, gravity_strength=1.0, turbulence_strength=1.0, collision_damage=200):
    """Spawn a black hole (maelstrom) terrain object at the given position.
    
    Args:
        x (float): X position.
        y (float): Y position.
        z (float): Z position.
        gravity_radius (int, optional): Radius within which objects are pulled
            in. Defaults to 1500.
        gravity_strength (float, optional): Pull speed multiplier. Defaults to
            1.0.
        turbulence_strength (float, optional): Turbulence intensity. Defaults
            to 1.0.
        collision_damage (int, optional): Damage on entry into the event
            horizon. Defaults to 200.
    
    Returns:
        SpaceObject: The spawned black hole object."""
def terrain_spawn_black_holes (lethal_value, center=None, points=None):
    """Spawn multiple black holes based on the game's lethal terrain value.
    
    Args:
        lethal_value (int): Number of black holes to spawn.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        points (list[Vec3], optional): Explicit spawn positions. Defaults to
            None (random within 75 000 units of centre).
    
    Returns:
        list[SpaceObject]: The spawned black hole objects."""
def terrain_spawn_monsters (monster_value, center=None, points=None):
    """Spawn Typhon-class monster prefabs based on the monster difficulty value.
    
    Args:
        monster_value (int): Number of monsters to spawn.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        points (list[Vec3], optional): Explicit spawn positions. Defaults to
            None (random within 75 000 units of centre).
    
    Returns:
        list[Vec3]: The spawn positions used."""
def terrain_spawn_nebula_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, cluster_color=None, selectable=False, marker=True, name=''):
    """Spawn nebulae scattered inside a box volume.
    
    Delegates to ``terrain_spawn_nebula_common`` with box geometry.
    
    Args:
        x (float): Box origin X.
        y (float): Unused.
        z (float): Box origin Z.
        size_x (int, optional): Box width along X. Defaults to 10000.
        size_z (int | None, optional): Box depth; defaults to ``size_x``.
        density_scale (float, optional): Nebula count multiplier. Defaults to
            1.0.
        density (int, optional): Visual density per nebula (3D view). Defaults
            to 1.
        height (int, optional): Y spread. Defaults to 1000.
        cluster_color (str | int | dict | None, optional): Colour override;
            see ``terrain_spawn_nebula_common``. Defaults to None (random).
        selectable (bool, optional): Make nebulae selectable. Defaults to
            False.
        marker (bool, optional): Place a radar marker. Defaults to True.
        name (str, optional): Marker name. Defaults to ``""``.
    
    Returns:
        list[SpaceObject]: Spawned nebula objects."""
def terrain_spawn_nebula_clusters (terrain_value, center=None, selectable=False, points=None, marker=True, name=''):
    """Scatter random nebula clusters across the map and merge nearby markers.
    
    After spawning, neighbouring ``nebula_marker`` objects within 15 000 units
    are merged into a single marker that represents the combined cluster.
    
    Args:
        terrain_value (int): 0–4 scale controlling cluster count and density.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        selectable (bool, optional): Make nebulae selectable on 2D radar.
            Defaults to False.
        points (list[Vec3], optional): Explicit cluster origins. Defaults to
            None (random positions).
        marker (bool, optional): Place a radar marker at each cluster origin.
            Defaults to True.
        name (str, optional): Name assigned to each radar marker. Defaults to
            ``""``.
    
    Returns:
        list[SpaceObject]: All spawned nebula objects."""
def terrain_spawn_nebula_common (x, y, z, size_x=10000, size_z=None, radius=None, density_scale=1.0, density=1, height=1000, cluster_color=None, selectable=False, marker=True, name=''):
    """Spawn a nebula cluster using either box or sphere geometry.
    
    Shared implementation called by ``terrain_spawn_nebula_box`` and
    ``terrain_spawn_nebula_sphere``. Distributes nebulae with noise-based
    scatter and optionally places a radar marker at the cluster centre.
    
    Args:
        x (float): Centre X position.
        y (float): Centre Y position.
        z (float): Centre Z position.
        size_x (int, optional): Box width or sphere radius X. Defaults to
            10000.
        size_z (int | None, optional): Box depth; if None uses ``size_x``.
            Defaults to None.
        radius (float | None, optional): Override for sphere scatter radius.
            Defaults to None (uses box geometry).
        density_scale (float, optional): Multiplier for cluster density.
            Defaults to 1.0.
        density (float, optional): Visual density of each nebula (3D view).
            Defaults to 1.
        height (int, optional): Vertical spread in simulation units. Defaults
            to 1000.
        cluster_color (str | int | dict | None, optional): Nebula colour — a
            colour name string (e.g. ``"purple"``), an integer index into the
            colour table, a full colour dict, or ``None`` for a random colour.
            Defaults to None.
        selectable (bool, optional): Make nebulae selectable on 2D radar.
            Defaults to False.
        marker (bool, optional): Place a radar marker at the cluster origin.
            Defaults to True.
        name (str, optional): Name assigned to the radar marker. Defaults to
            ``""``.
    
    Returns:
        list[SpaceObject]: Spawned nebula objects."""
def terrain_spawn_nebula_scatter (cluster_spawn_points, height, cluster_color=None, diameter=1500, density=1.0, selectable=False):
    """Spawn a nebula at each given point with randomised Y scatter.
    
    Args:
        cluster_spawn_points (Iterable[Vec3]): Spawn positions.
        height (int): Controls Y scatter range around each point.
        cluster_color (str | int | dict | None, optional): Colour name, index
            (0=purple, 1=red, 2=blue, 3=yellow), dict, or ``None`` for random.
            Defaults to None.
        diameter (int, optional): Max nebula diameter. Defaults to
            ``NEB_MAX_SIZE``.
        density (float, optional): Visual nebula density (3D view). Defaults
            to 1.0.
        selectable (bool, optional): Make nebulae selectable on 2D radar.
            Defaults to False.
    
    Returns:
        list[SpaceObject]: The spawned nebula objects."""
def terrain_spawn_nebula_sphere (x, y, z, radius=1500, density_scale=1.0, density=1.0, height=1000, cluster_color=None, selectable=False, marker=True, name=''):
    """Spawn nebulae scattered inside a sphere volume.
    
    Delegates to ``terrain_spawn_nebula_common`` with sphere geometry.
    
    Args:
        x (float): Sphere centre X.
        y (float): Sphere centre Y.
        z (float): Sphere centre Z.
        radius (int, optional): Sphere radius. Defaults to ``NEB_MAX_SIZE``.
        density_scale (float, optional): Nebula count multiplier. Defaults to
            1.0.
        density (float, optional): Visual density per nebula. Defaults to 1.0.
        height (int, optional): Y spread. Defaults to 1000.
        cluster_color (str | int | dict | None, optional): Colour override;
            see ``terrain_spawn_nebula_common``. Defaults to None (random).
        selectable (bool, optional): Make nebulae selectable. Defaults to
            False.
        marker (bool, optional): Place a radar marker. Defaults to True.
        name (str, optional): Marker name. Defaults to ``""``.
    
    Returns:
        list[SpaceObject]: Spawned nebula objects."""
def terrain_spawn_stations (DIFFICULTY, lethal_value, x_min=-32500, x_max=32500, center=None, min_num=0, points=None):
    """Spawn starbases weighted by difficulty and optionally surround them with minefields.
    
    Args:
        DIFFICULTY (int): Game difficulty (affects station count and type mix).
        lethal_value (int): Lethal terrain level; ``> 0`` wraps minefields
            around each station.
        x_min (int, optional): Minimum X spawn bound. Defaults to -32500.
        x_max (int, optional): Maximum X spawn bound. Defaults to 32500.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        min_num (int, optional): Minimum station count. Defaults to 0.
        points (list[Vec3], optional): Explicit spawn positions. If provided,
            stations are sampled from this list. Defaults to None.
    
    Returns:
        list[SpaceObject]: The spawned station objects."""
def terrain_to_value (dropdown_select, default=0):
    """Convert a terrain density string to an integer level (0–4).
    
    Args:
        dropdown_select (str): Density string: ``"few"`` → 1, ``"some"`` → 2,
            ``"lots"`` → 3, ``"max"``/``"many"`` → 4.
        default (int, optional): Value returned for unrecognised strings.
            Defaults to 0.
    
    Returns:
        int: Terrain density level 0–4."""
def to_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).
    
    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The space-object agent, or ``None``."""
