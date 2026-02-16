from sbs_utils.vec import Vec3
def color_noise (r_min, r_max, g_min, g_max, b_min, b_max, a_min=255, a_max=255):
    ...
def npc_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a non-player ship.
    
    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the ship is on
        ship_key (str): The key from shipData to use
        behave_id (str): Behavior type
    
    Returns:
        SpawnData: The SpawnData object for the npc."""
def plain_asteroid_keys ():
    """Get all plain asteroid keys (excludes crystal) in the ship data.
    Returns:
        list[str]: The list of keys."""
def prefab_spawn (label, data=None, OFFSET_X=None, OFFSET_Y=None, OFFSET_Z=None):
    """Spawn a prefab and return its task.
    Args:
        label (str | Label): The label to run to spawn the prefab.
        data (dict, optional): Data associated with the prefab.
        * Positional data may be optionally included in `data`: `START_X`, `START_Y`, and `START_Z`. The default for these all is 0.
        OFFSET_X (int, optional): The X offset relative to the positional data. Default is None.
        OFFSET_Y (int, optional): The Y offset relative to the positional data. Default is None.
        OFFSET_Z (int, optional): The Z offset relative to the positional data. Default is None.
    Returns:
        MastAsyncTask: The task of the prefab."""
def random_terran (face=None, civilian=None):
    """Create a random terran face.
    
    Args:
        face (int | None): The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
        civilian (boolean | None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
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
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def terrain_asteroid_clusters (terrain_value, center=None, selectable=False):
    """Spawn clusters of asteroids around the map.
    Args:
        terrain_value (int): Scales how many asteroid clusters are spawned, and how many asteroids per cluster.
        center (Vec3, optional): The center of the map. Default is None (0,0,0).
        selectable (bool, optional): Should the asteroids be selectable on a 2D radar widget? Default is False."""
def terrain_setup_nebula (nebula, diameter=4000, density_coef=1.0, color='yellow'):
    """Set up the nebulae to use the default blue values.
    Args:
        nebula (set[Agent]): The nebulae
        diameter (int, optional): The diameter of the nebula.
        density_coef (float, optional): Scales the visual nebula density (3D view)"""
def terrain_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a terrain (passive) object.
    
    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the object is on can be None
        ship_key (str): The key from shipData to use
        behave_id (str): Behavior type
    
    Returns:
        SpawnData: The SpawnData object for the terrain."""
def terrain_spawn_asteroid_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, selectable=False, is_tiled=False):
    """Spawn asteroid clusters within the box. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point. (Not currently used)
        z (int): The z position of the starting point.
        size_x (int, optional): The size of the box in the x dimension. Default is 10,000.
        size_z (int, optional): The size of the box in the z dimension. Default is None, in which case it is equal to size_x.
        density_scale (float, optional): The density of the asteroid clusters. Default is 1.0.
        density (int, optional): The density of the asteroid spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        selectable (bool, optional): Should the spawned asteroids be selectable on the 2D radar widgets? Default is False.
        is_tiled (bool, optional): Is the spawn position data tiled (using the map editor)? Default is False."""
def terrain_spawn_asteroid_points (x, y, z, points, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """Spawn asteroid clusters within the box. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point. Not currently used.
        z (int): The z position of the starting point.
        radius (int, optional): The size of the box in the x dimension. Default is 10,000. Not currently used.
        density_scale (float, optional): The density of the asteroid clusters. Default is 1.0.
        density (int, optional): The density of the asteroid spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        selectable (bool, optional): Should the spawned asteroids be selectable on the 2D radar widgets? Default is False."""
def terrain_spawn_asteroid_scatter (cluster_spawn_points, height, selectable=False):
    """Spawn asteroids at the specified spawn points.
    Args:
        cluster_spawn_points (Iterable[Vec3]): The spawn points.
        height (int): Scales where the asteroids should spawn in the y dimension.
        selectable (bool, optional): Should the asteroids be selectable on the 2D radar widget? Default is False."""
def terrain_spawn_asteroid_sphere (x, y, z, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """Spawn asteroid clusters within the sphere. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point.
        z (int): The z position of the starting point.
        radius (int, optional): The radius of the spawn sphere. Default is 10,000.
        density_scale (float, optional): The density of the asteroid clusters. Default is 1.0.
        density (int, optional): The density of the asteroid spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        selectable (bool, optional): Should the spawned asteroids be selectable on the 2D radar widgets? Default is False."""
def terrain_spawn_black_hole (x, y, z, gravity_radius=1500, gravity_strength=1.0, turbulence_strength=1.0, collision_damage=200):
    """Spawn a black hole.
    Args:
        x (int): The x position.
        y (int): The y position.
        z (int): The z position.
        gravity_radius (int, optional): The radius in which objects will be pulled towards the black hole. Default is 1500.
        gravity_strength (float, optional): How fast the black hole pulls objects. Default is 1.0.
        turbulence_strength (float, optional): The turbulence of the black hole. Default is 1.0.
        collision_damage (int, optional): The damage to apply to objects that fall into the black hole. Default is 200."""
def terrain_spawn_black_holes (lethal_value, center=None):
    """Spawn black holes based on the game's lethal terrain value.
    Args:
        lethal_value (int): The integer value representing how much lethal terrain should spawn.
        center (Vec3): The center of the spawn points. Default is None (0,0,0)."""
def terrain_spawn_monsters (monster_value, center=None):
    """Spawn monsters based on the monster value of the game.
    Args:
        monster_value (int): Scales the numnber of monsters to spawn.
        center (Vec3): The center of the spawn area. Defaults to None (0,0,0)."""
def terrain_spawn_nebula_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, cluster_color=None, selectable=False, is_tiled=False):
    """Spawn asteroids throughout a box.
    Args:
        x (int): The X position.
        y (int): The Y position. (Not currently used).
        z (int): The Z position.
        size_x (int, optional): The width of the box in the x dimension. Default is 10,000.
        size_z (int, optional): The width of the box in the z dimension. If None, equal to `size_x`. Default is None.
        density_scale(float, optional): How dense the nebulae spawn. Default is 1.0.
        density (int, optional): The density of the nebulae (3D view). Default is 1.
        height (int): Scales where the asteroids should spawn in the y dimension.
        cluster_color (int, optional): The color the nebulae should spawn as. Default is 0.
        * 0: purple
        * 1: red
        * 2: blue
        * 3: yellow
        selectable (bool, optional): Should the asteroids be selectable on the 2D radar widget? Default is False.
        is_tiled (bool, optional): Is the spawn position data tiled (using the map editor)? Default is False."""
def terrain_spawn_nebula_clusters (terrain_value, center=None, selectable=False):
    """Spawn clusters of nebulae around the map.
    Args:
        terrain_value (int): Scales how many nebulae clusters are spawned, and how many nebulae per cluster.
        center (Vec3, optional): The center of the map. Default is None (0,0,0).
        selectable (bool, optional): Should the nebulae be selectable on a 2D radar widget? Default is False."""
def terrain_spawn_nebula_scatter (cluster_spawn_points, height, cluster_color=None, diameter=4800, density=1.0, selectable=False):
    """Spawn asteroids at the specified spawn points.
    Args:
        cluster_spawn_points (Iterable[Vec3]): The spawn points.
        height (int): Scales where the asteroids should spawn in the y dimension.
        cluster_color (int, optional): The color the nebulae should spawn as. Default is 0.
        * 0: purple
        * 1: red
        * 2: blue
        * 3: yellow
        diameter (int, optional): The diameter of the nebulae.
        density (float, optional): The density of the nebulae (3D view). Default is 1.0.
        selectable (bool, optional): Should the asteroids be selectable on the 2D radar widget? Default is False."""
def terrain_spawn_nebula_sphere (x, y, z, radius=10000, density_scale=1.0, density=1.0, height=1000, cluster_color=None, selectable=False):
    """Spawn nebula clusters within the sphere. Density is per 1000.
    Args:
        x (int): The x position of the starting point.
        y (int): The y position of the starting point.
        z (int): The z position of the starting point.
        radius (int, optional): The radius of the spawn sphere. Default is 10,000.
        density_scale (float, optional): The density of the nebulae clusters. Default is 1.0.
        density (int, optional): The density of the nebulae spawns. Default is 1.
        height (int, optional): The size of the box in the y dimension. Default is 1000.
        cluster_colors (int, optional): The color the nebulae should spawn as. Default is 0.
        * 0: purple
        * 1: red
        * 2: blue
        * 3: yellow
        selectable (bool, optional): Should the spawned nebulae be selectable on the 2D radar widgets? Default is False."""
def terrain_spawn_stations (DIFFICULTY, lethal_value, x_min=-32500, x_max=32500, center=None, min_num=0):
    """Spawn stations throughout the map, weighted by the game difficutly, and wrap minefields around them as applicable based on the lethal terrain value.
    Args:
        DIFFICULTY (int): The game difficulty.
        lethal_value (int): The lethal terrain value.
        x_min (int, optional): The minimum X value on the map
        x_max (int, optional): The maximum X value on the map
        center (Vec3, optional): The center of the map. Default is None (0,0,0)."""
def terrain_to_value (dropdown_select, default=0):
    """Convert a string representation of the terrain density (shown to the players) to an integer.
    Args:
        dropdown_select (str): The string representation of the terrain density.
        default (int, optional): The default integer value, if `dropdown_select` is not a valid value. Default is 0.
    Returns:
        int: The integer value that corresponds to the string. (0 - 4)"""
def to_data_set (id_or_obj):
    """Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_blob
    Args:
        id_or_obj (Agent | int): Agent id or object
    Returns:
        data_set | None: Returns the data or None if it does not exist"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
