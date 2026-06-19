from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
from sbs_utils.vec import Vec3
def awaitable (func):
    ...
def destroyed_all (the_set, snapshot=False):
    """Build a promise that resolves when every object in a set is destroyed.
    
    Args:
        the_set (Agent | int | set[Agent | int]): Object(s) to watch.
        snapshot (bool, optional): If True, take a copy of the set so later
            changes to the original do not affect what is watched. Defaults to
            False.
    
    Returns:
        TestPromise: Resolves once no object in the set remains in the sim.
    
    Example:
        await destroyed_all(enemies)
        "All enemies eliminated!""""
def destroyed_any (the_set, snapshot=False):
    """Build a promise that resolves when any object in a set is destroyed.
    
    Args:
        the_set (Agent | int | set[Agent | int]): Object(s) to watch.
        snapshot (bool, optional): If True, take a copy of the set so later
            changes to the original do not affect what is watched. Defaults to
            False.
    
    Returns:
        TestPromise: Resolves as soon as any object in the set no longer exists.
    
    Example:
        await destroyed_any(enemies)
        "First kill achieved.""""
def distance_greater (obj_or_id1, obj_or_id2, distance):
    """Build a promise that resolves when two objects are farther than a distance.
    
    Args:
        obj_or_id1 (Agent | int): First space object or ID.
        obj_or_id2 (Agent | int): Second space object or ID.
        distance (float): Threshold distance in simulation units.
    
    Returns:
        TestPromise: Resolves when ``dist(obj1, obj2) > distance``.
    
    Example:
        await distance_greater(SHIP_ID, ENEMY_ID, 2000)
        "Enemy out of range.""""
def distance_less (obj_or_id1, obj_or_id2, distance):
    """Build a promise that resolves when two objects are closer than a distance.
    
    Args:
        obj_or_id1 (Agent | int): First space object or ID.
        obj_or_id2 (Agent | int): Second space object or ID.
        distance (float): Threshold distance in simulation units.
    
    Returns:
        TestPromise: Resolves when ``dist(obj1, obj2) < distance``.
    
    Example:
        await distance_less(SHIP_ID, ENEMY_ID, 500)
        "Enemy in range!""""
def distance_point_greater (obj_or_id, point, distance):
    """Build a promise that resolves when an object is farther than a distance from a point.
    
    Args:
        obj_or_id (Agent | int): Space object or ID.
        point (Vec3): Reference point in simulation space.
        distance (float): Threshold distance in simulation units.
    
    Returns:
        TestPromise: Resolves when ``dist(obj, point) > distance``.
    
    Example:
        await distance_point_greater(SHIP_ID, base_pos, 1000)
        "Ship has left the area.""""
def distance_point_less (obj_or_id, point, distance):
    """Build a promise that resolves when an object is closer than a distance to a point.
    
    Args:
        obj_or_id (Agent | int): Space object or ID.
        point (Vec3): Reference point in simulation space.
        distance (float): Threshold distance in simulation units.
    
    Returns:
        TestPromise: Resolves when ``dist(obj, point) < distance``.
    
    Example:
        await distance_point_less(SHIP_ID, waypoint, 300)
        "Arrived at waypoint.""""
def grid_arrive_id (the_set, target_id, snapshot=False):
    """Build a promise that resolves when grid objects arrive at a target cell.
    
    Resolves the target cell position from ``target_id`` and delegates to
    ``grid_arrive_location``.
    
    Args:
        the_set (Agent | int | set[Agent | int]): Grid object(s) to watch.
        target_id (int): ID of the grid object whose current position is used as
            the target cell.
        snapshot (bool, optional): If True, copy the set so later changes don't
            affect what is watched. Defaults to False.
    
    Returns:
        TestPromise: Resolves when movement is complete, or a cancelled promise
            if ``target_id`` has no grid position."""
def grid_arrive_location (the_set, x=0, y=0, snapshot=False):
    """Build a promise that resolves when grid objects finish moving.
    
    Checks whether the first object in the set no longer has the ``_moving_``
    role. The ``x`` and ``y`` parameters are accepted for API compatibility but
    are not used.
    
    Args:
        the_set (Agent | int | set[Agent | int]): Grid object(s) to watch.
        x (int, optional): Unused target column. Defaults to 0.
        y (int, optional): Unused target row. Defaults to 0.
        snapshot (bool, optional): If True, copy the set so later changes don't
            affect what is watched. Defaults to False.
    
    Returns:
        TestPromise: Resolves when the first object in the set is no longer
            moving."""
def grid_pos_data (id):
    """Return the current position and path length of a grid object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        tuple[float, float, float]: ``(curx, cury, path_length)``."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
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
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
class TestPromise(Promise):
    """class TestPromise"""
    def __init__ (self, test_func) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def poll (self):
        ...
