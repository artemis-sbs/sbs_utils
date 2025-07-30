from sbs_utils.vec import Vec3
def npc_spawn (x, y, z, name, side, art_id, behave_id):
    """spawn a non-player ship
    
    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the ship is on
        art_id (str): The art ID to use
        behave_id (str): Behavior type
    
    Returns:
        SpawnData: """
def plain_asteroid_keys ():
    ...
def prefab_spawn (*args, **kwargs):
    ...
def random_terran (face=None, civilian=None):
    """Create a random terran face
    
    Args:
        face ( int or None): The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
        civilian ( boolean or None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def scatter_ring (ca, cr, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False):
    """Calculate the points on rings with each ring has same count
    
    Args:
        ca (int): The number of points to generate on each ring
        cr (int): The number of rings
        x,y,z (float,float,float): the start point/origin
        outer_r (float): the radius
        inner_r (float, optional): the radius inner
        start (float): degrees start angle
        end (float): degrees start angle
        random (bool): when true pointw will be randomly placed. when false points will be evenly placed
    
    Returns:
        points (generator): A generator of Vec3"""
def set_face (ship_id, face):
    """sets a face string for a specified ID
    
    Args:
        ship_id (agent): The id of the ship/object
        face (str): A Face string"""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def terrain_asteroid_clusters (terrain_value, center=None, selectable=False):
    ...
def terrain_setup_nebula_blue (nebula, diameter=4000, density_coef=1.0):
    ...
def terrain_setup_nebula_red (nebula, diameter=4000, density_coef=1.0):
    ...
def terrain_setup_nebula_yellow (nebula, diameter=4000, density_coef=1.0):
    ...
def terrain_spawn (x, y, z, name, side, art_id, behave_id):
    """spawn a terrain (passive) object
    
    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the object is on can be None
        art_id (str): The art ID to use
        behave_id (str): Behavior type
    
    Returns:
        SpawnData: """
def terrain_spawn_asteroid_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, selectable=False, is_tiled=False):
    """density is per 1000. Defaults to 0.5."""
def terrain_spawn_asteroid_points (x, y, z, points, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    ...
def terrain_spawn_asteroid_scatter (cluster_spawn_points, height, selectable=False):
    ...
def terrain_spawn_asteroid_sphere (x, y, z, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    ...
def terrain_spawn_black_hole (x, y, z, gravity_radius=1500, gravity_strength=1.0, turbulence_strength=1.0, collision_damage=200):
    ...
def terrain_spawn_black_holes (lethal_value, center=None):
    ...
def terrain_spawn_monsters (monster_value, center=None):
    ...
def terrain_spawn_nebula_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, cluster_color=None, selectable=False, is_tiled=False):
    ...
def terrain_spawn_nebula_clusters (terrain_value, center=None, selectable=False):
    ...
def terrain_spawn_nebula_scatter (cluster_spawn_points, height, cluster_color=None, diameter=4000, density=1.0, selectable=False):
    ...
def terrain_spawn_nebula_sphere (x, y, z, radius=10000, density_scale=1.0, density=1.0, height=1000, cluster_color=None, selectable=False):
    ...
def terrain_spawn_stations (DIFFICULTY, lethal_value, x_min=-32500, x_max=32500, center=None, min_num=0):
    ...
def terrain_to_value (dropdown_select, default=0):
    ...
def to_data_set (id_or_obj):
    """gets the engine dataset of the specified agent
    
    !!! Note
        Same as to_data_set
    
    Args:
        id_or_obj (agent): Agent id or object
    
    Returns:
        data set| None: Returns the data or None if it does not exist"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
