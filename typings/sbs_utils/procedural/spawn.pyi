from sbs_utils.gridobject import GridObject
from sbs_utils.objects import Npc
from sbs_utils.objects import PlayerShip
from sbs_utils.objects import Terrain
def grid_spawn (id, name, tag, x, y, icon_index, color, roles):
    """Spawn a grid object on a ship.
    
    Args:
        id (Agent | int): The agent to which the grid object should be added
        name (str): The name of the grid object
        tag (str): The tag/side
        x (int): the x grid location
        y (int): the y grid location
        icon_index (int): the icon index
        color (str): color
        roles (str): string of comma-separated roles
    
    Returns:
        GridObject: The grid object."""
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
def player_spawn (x, y, z, name, side, ship_key):
    """Spawn a player ship.
    
    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the ship is on
        ship_key (str): The key from shipData to use
    
    Returns:
        SpawnData: The SpawnData object for the player ship."""
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
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
