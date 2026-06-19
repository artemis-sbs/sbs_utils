from sbs_utils.gridobject import GridObject
from sbs_utils.objects import Npc
from sbs_utils.objects import PlayerShip
from sbs_utils.objects import Terrain
def grid_spawn (id, name, tag, x, y, icon_index, color, roles):
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
        GridObject: The newly created grid object."""
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
def player_spawn (x, y, z, name, side, ship_key):
    """Spawn a player ship into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the ship belongs to.
        ship_key (str): Ship template key from shipData.
    
    Returns:
        SpawnData: Spawn data for the new player ship."""
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
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
