from ..objects import Terrain, PlayerShip, Npc
from ..gridobject import GridObject

def npc_spawn(x,y,z,name, side, ship_key, behave_id):
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
        SpawnData: Spawn data for the new NPC.
    """
    # TODO: Modify such that a Vec3 can be provided?
    so = Npc()
    return so.spawn(x,y,z,name, side, ship_key, behave_id)
    
def player_spawn(x,y,z,name, side, ship_key):
    """Spawn a player ship into the simulation.

    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the ship belongs to.
        ship_key (str): Ship template key from shipData.

    Returns:
        SpawnData: Spawn data for the new player ship.
    """
    so = PlayerShip()
    return so.spawn(x,y,z,name, side, ship_key)

def terrain_spawn(x,y,z,name, side, ship_key, behave_id):
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
        SpawnData: Spawn data for the new terrain object.
    """
    so = Terrain()
    return so.spawn(x,y,z,name, side, ship_key, behave_id)

from .query import to_id
def grid_spawn(id, name, tag, x,y, icon_index, color, roles):
    """Spawn a grid object (engineering component) onto a ship's grid.

    Args:
        id (Agent | int): The ship agent ID or object to attach the grid object
            to.
        name (str): Display name of the grid object.
        tag (str): Tag identifying the grid object's side or type.
        x (int): Column position on the engineering grid.
        y (int): Row position on the engineering grid.
        icon_index (int): Icon index for the grid display.
        color (str): Display color string.
        roles (str): Comma-separated roles to assign to the grid object.

    Returns:
        GridObject: The newly created grid object.
    """
    # TODO: The docs for 'tag' imply that this is the side of the grid object? Clarify.
    so = GridObject()
    id = to_id(id)
    return so.spawn(id, name, tag, x,y, icon_index, color, roles)
