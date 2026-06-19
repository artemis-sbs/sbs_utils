from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
def all_roles (roles: str):
    """Return the set of agent IDs that hold every one of the given roles.
    
    Args:
        roles (str): A comma-separated list of role names.
    
    Returns:
        set[int]: IDs of agents that have all specified roles."""
def broad_test (x1: float, z1: float, x2: float, z2: float, broad_type=65520):
    """Return the set of object IDs inside a rectangular region of the simulation.
    
    Args:
        x1 (float): Left X boundary.
        z1 (float): Top Z boundary.
        x2 (float): Right X boundary.
        z2 (float): Bottom Z boundary.
        broad_type (int, optional): Bitmask filtering which object types to
            include. TERRAIN=0x01, NPC=0x10, PLAYER=0x20, ALL=0xffff,
            NPC_AND_PLAYER=0x30. Defaults to 0xfff0.
    
    Returns:
        set[int]: IDs of objects inside the rectangle."""
def broad_test_around (id_or_obj, width: float, depth: float, broad_type=65520):
    """Return the set of object IDs inside a rectangle centered on an agent or point.
    
    Args:
        id_or_obj (Agent | int | Vec3): Center agent ID, object, or position.
        width (float): Total width of the search rectangle (X axis).
        depth (float): Total depth of the search rectangle (Z axis).
        broad_type (int, optional): Bitmask filtering which object types to
            include. TERRAIN=0x01, NPC=0x10, PLAYER=0x20, ALL=0xffff,
            NPC_AND_PLAYER=0x30. Defaults to 0xfff0.
    
    Returns:
        set[int]: IDs of objects inside the rectangle."""
def clear_target (chasers: set | int | sbs_utils.agent.Agent | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, throttle=0):
    """Clear the movement and weapons target on one or more agents.
    
    Sets the target position to the agent's current position and zeroes the
    weapon target ID, effectively stopping pursuit.
    
    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to update.
        throttle (float, optional): Throttle to apply after clearing. Defaults
            to 0."""
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Return the closest object to a source from a candidate set.
    
    Args:
        the_ship (Agent | int | Vec3): Reference agent ID, object, or position.
        the_set (Agent | int | set[Agent | int]): Candidate agent(s) to test.
        max_dist (float, optional): Maximum distance to consider. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``.
            Defaults to None.
    
    Returns:
        CloseData | None: Distance data for the closest match, or ``None`` if
            no candidates qualify."""
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
def closest_object (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.Agent:
    """Return the closest agent object to a source from a candidate set.
    
    Args:
        the_ship (Agent | int | Vec3): Reference agent ID, object, or position.
        the_set (Agent | int | set[Agent | int]): Candidate agent(s) to test.
        max_dist (float, optional): Maximum distance to consider. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``.
            Defaults to None.
    
    Returns:
        Agent | None: The closest agent, or ``None`` if no candidates qualify."""
def closest_to_point (point, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Return the closest object to a Vec3 point from a candidate set.
    
    Args:
        point (Vec3): Reference position in simulation space.
        the_set (Agent | int | set[Agent | int]): Candidate agent(s) to test.
        max_dist (float, optional): Maximum distance to consider. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``.
            Defaults to None.
    
    Returns:
        CloseData | None: Distance data for the closest match, or ``None`` if
            no candidates qualify."""
def delete_object (id_or_objs):
    """Delete one or more agents from the simulation.
    
    Args:
        id_or_objs (Agent | int | set[Agent | int]): Agent(s) to delete."""
def delete_objects_box (x, y, z, w, h, d, broad_type=15, roles=None):
    """Delete all objects inside a box that match an optional role filter.
    
    Args:
        x (float): Center X coordinate.
        y (float): Center Y coordinate.
        z (float): Center Z coordinate.
        w (float): Half-width of the box along the X axis.
        h (float): Half-height of the box along the Y axis.
        d (float): Half-depth of the box along the Z axis.
        broad_type (int, optional): Bitmask filtering which object types to
            consider. TERRAIN=0x01, NPC=0x10, PLAYER=0x20, ALL=0xffff,
            NPC_AND_PLAYER=0x30. Defaults to 0x0F.
        roles (str, optional): Comma-separated roles — only objects with all
            listed roles are deleted. Defaults to None (delete all matches)."""
def delete_objects_sphere (x, y, z, radius, broad_type=15, roles=None):
    """Delete all objects inside a sphere that match an optional role filter.
    
    Args:
        x (float): Center X coordinate.
        y (float): Center Y coordinate.
        z (float): Center Z coordinate.
        radius (float): Sphere radius in simulation units.
        broad_type (int, optional): Bitmask filtering which object types to
            consider. TERRAIN=0x01, NPC=0x10, PLAYER=0x20, ALL=0xffff,
            NPC_AND_PLAYER=0x30. Defaults to 0x0F.
        roles (str, optional): Comma-separated roles — only objects with all
            listed roles are deleted. Defaults to None (delete all matches)."""
def get_engineering_value (id_or_obj, name, default=None):
    """Get a named engineering control value from a ship.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): The engineering control label to look up (case-insensitive).
        default (float, optional): Value returned if the label is not found.
            Defaults to None.
    
    Returns:
        float | None: The current value of the control, or ``default``."""
def get_pos (id_or_obj):
    """Return the current position of an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        Vec3 | None: The agent's position, or ``None`` if it does not exist."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def set_engineering_value (id_or_obj, name, value):
    """Set a named engineering control value on a ship.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): The engineering control label to update (case-insensitive).
        value (float): The new value."""
def set_pos (id_or_obj, x, y=None, z=None):
    """Teleport one or more agents to a position.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): Agent(s) to reposition.
        x (float | Vec3): X coordinate, or a Vec3 when ``y`` is omitted.
        y (float, optional): Y coordinate. If ``None``, ``x`` is treated as a
            Vec3. Defaults to None.
        z (float, optional): Z coordinate. Defaults to None."""
def target (set_or_object, target_id, shoot: bool = True, throttle: float = 1.0, stop_dist=None):
    """Direct one or more agents to move toward and optionally shoot a target.
    
    Args:
        set_or_object (Agent | int | set[Agent | int]): Agent(s) to command.
        target_id (Agent | int): The target agent ID or object.
        shoot (bool, optional): If ``True``, lock weapons on the target as well
            as moving toward it. Defaults to True.
        throttle (float, optional): Movement speed multiplier (0.0–1.0).
            Defaults to 1.0.
        stop_dist (float, optional): Stop the agent (throttle→0) when it comes
            within this distance of the target. Defaults to None."""
def target_pos (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, x: float, y: float, z: float, throttle: float = 1.0, target_id=None, stop_dist=None):
    """Direct one or more agents to move toward a position in simulation space.
    
    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to command.
        x (float): Target X coordinate.
        y (float): Target Y coordinate.
        z (float): Target Z coordinate.
        throttle (float, optional): Movement speed multiplier (0.0–1.0).
            Defaults to 1.0.
        target_id (Agent | int, optional): If set, agents will also fire at
            this target. Defaults to None.
        stop_dist (float, optional): Stop the agent (throttle→0) when within
            this distance of the target. Defaults to None."""
def target_shoot (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, target_id=None):
    """Set the weapons target on one or more agents without changing their movement.
    
    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to update.
        target_id (Agent | int, optional): The agent to fire at. Defaults to
            None."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a list.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        list: A list containing whatever was passed in; ``None`` becomes ``[]``."""
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
