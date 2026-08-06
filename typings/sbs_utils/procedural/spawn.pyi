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
def player_ensure (slot, x, y, z, ship_key, name=None, side='tsn'):
    """Ensure a player ship occupies ``slot``, spawning one only if it is empty.
    
    Idempotent: returns the existing ship's ID if the slot is already filled, so an
    initialization route that gets emitted more than once creates nothing extra.
    Because the check is against the live world and not a did-I-run flag, a slot
    emptied by ``sim_create()``, a deletion or a destroyed ship is refilled on the
    next call - which is what makes reset, respawn and late-joining crew work.
    
    An existing ship is returned UNTOUCHED (not repositioned or renamed); use
    ``a2x_place_player`` to converge one in place. This mirrors ``side_ensure`` /
    ``side_create``.
    
    Args:
        slot (int): Player slot, stable across re-runs.
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        ship_key (str): Ship template key from shipData.
        name (str, optional): Display name.
        side (str, optional): Side the ship belongs to. Comma tokens become roles.
    
    Returns:
        int|None: The ship's ID, or None if the spawn failed."""
def player_slot_id (slot):
    """The live player ship holding ``slot``, or ``None``.
    
    Args:
        slot (int): The player slot.
    
    Returns:
        int|None: The ship's ID, or None if the slot is empty."""
def player_slot_role (slot):
    """The role marking the ship that holds ``slot`` (e.g. ``player_slot_3``).
    
    A role, because role sets are the only O(1) keyed lookup available and they
    self-clean when the object is deleted (``Agent._remove`` purges the registries),
    so a slot is freed by deleting its ship with no bookkeeping."""
def player_slots ():
    """Every filled player slot as ``{slot: id}``.
    
    Returns:
        dict: Slot number -> ship ID, for live player ships carrying a slot."""
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
def players_reset ():
    """Delete every player ship, freeing all slots.
    
    The explicit path for an INTENTIONAL re-initialization (reset the scenario
    without reloading the mission): wipe, then re-emit the create signal and let
    ``player_ensure`` rebuild the roster. Slot roles are purged by the delete, so
    nothing else needs clearing.
    
    Returns:
        int: How many ships were deleted."""
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
