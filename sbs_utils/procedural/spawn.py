from ..objects import Terrain, PlayerShip, Npc
from ..gridobject import GridObject

def npc_spawn(x,y,z,name, side, art_id, behave_id):
    """ spawn a non-player ship

    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the ship is on
        art_id (str): The art ID to use
        behave_id (str): Behavior type

    Returns:
        SpawnData: 
    """    
    so = Npc()
    return so.spawn(x,y,z,name, side, art_id, behave_id)
    
def player_spawn(x,y,z,name, side, art_id):
    """ spawn a player ship

    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the ship is on
        art_id (str): The art ID to use

    Returns:
        SpawnData: 
    """    
    so = PlayerShip()
    return so.spawn(x,y,z,name, side, art_id)

def terrain_spawn(x,y,z,name, side, art_id, behave_id):
    """ spawn a terrain (passive) object

    Args:
        x (float): the x location
        y (float): the y location
        z (float): The z location
        name (str): The name can be None
        side (str): The side the the object is on can be None
        art_id (str): The art ID to use
        behave_id (str): Behavior type

    Returns:
        SpawnData: 
    """    
    so = Terrain()
    return so.spawn(x,y,z,name, side, art_id, behave_id)

def grid_spawn(id, name, tag, x,y, icon, color, roles):
    """ Spawn a grid object on a ship

    Args:
        id (agent): The agent to add the grid object to
        name (str): The name of the grid item
        tag (str): The tag/side
        x (int): the x grid location
        y (int): the y grid location
        icon (int): the icon index
        color (str): color 
        roles (str): string of comma separated roles

    Returns:
        GridObject: The grid object
    """    
    so = GridObject()
    return so.spawn(id, name, tag, x,y, icon, color, roles)
