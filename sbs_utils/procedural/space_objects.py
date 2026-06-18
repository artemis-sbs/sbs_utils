from ..agent import Agent, CloseData, SpawnData
from .query import to_set, to_list, to_object, to_id, object_exists
from ..helpers import FrameContext
from ..vec import Vec3
from .roles import all_roles
import math



def broad_test(x1: float, z1: float, x2: float, z2: float, broad_type=0xfff0):
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
        set[int]: IDs of objects inside the rectangle.
    """
    obj_list = FrameContext.context.sbs.broad_test(x1, z1, x2, z2, broad_type)
    return {so.unique_ID for so in obj_list}

def broad_test_around(id_or_obj, width: float, depth: float, broad_type=0xfff0):
    """Return the set of object IDs inside a rectangle centered on an agent or point.

    Args:
        id_or_obj (Agent | int | Vec3): Center agent ID, object, or position.
        width (float): Total width of the search rectangle (X axis).
        depth (float): Total depth of the search rectangle (Z axis).
        broad_type (int, optional): Bitmask filtering which object types to
            include. TERRAIN=0x01, NPC=0x10, PLAYER=0x20, ALL=0xffff,
            NPC_AND_PLAYER=0x30. Defaults to 0xfff0.

    Returns:
        set[int]: IDs of objects inside the rectangle.
    """
    if isinstance(id_or_obj, Vec3):
        _pos = id_or_obj
    else:
        so = to_object(id_or_obj)
        if so is None:
            return set()
        _pos = so.engine_object.pos
    obj_list = FrameContext.context.sbs.broad_test(_pos.x-(width/2), _pos.z-(depth/2), _pos.x+(width/2), _pos.z+(depth/2), broad_type)
    return {so.unique_ID for so in obj_list}

MAX_BROAD_TEST_DIST = 5001
def closest_list(source: int | CloseData | SpawnData | Agent | Vec3, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
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
        list[CloseData]: All qualifying candidates with their distances.
    """
    ret = []
    test = max_dist

    if isinstance(source, Vec3):
        source_id = -1
    else:
        source_id = Agent.resolve_id(source)

    if max_dist is not None and max_dist < MAX_BROAD_TEST_DIST:
        the_set &= broad_test_around(source, max_dist, max_dist, 0xFFFF)

    for other_id in the_set:
        # if this is self skip
        if other_id == source_id:
            continue
        other_obj = Agent.get(other_id)
        if filter_func is not None and not filter_func(other_obj):
            continue
        # test distance
        if source_id !=-1:
            test = FrameContext.context.sbs.distance_id(source_id, other_id)
        else:
            test = source - Vec3(other_obj.pos)
            test = test.length()
            
        if max_dist is None:
            ret.append(CloseData(other_id, other_obj, test))
            continue

        if test < max_dist:
            ret.append(CloseData(other_id, other_obj, test))

    return ret


def closest(the_ship, the_set, max_dist=None, filter_func=None) -> CloseData:
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
            no candidates qualify.
    """
    if max_dist is not None and max_dist < MAX_BROAD_TEST_DIST:
        the_set &= broad_test_around(the_ship, max_dist, max_dist, 0xFFFF)

    if isinstance(the_ship, Vec3):
        return closest_to_point(the_ship,the_set, max_dist, filter_func)
    test = max_dist
    ret = None
    source_id = Agent.resolve_id(the_ship)
    the_set = to_set(the_set)

    for other_id in the_set:
        # if this is self skip
        if other_id == source_id:
            continue
        other_obj = Agent.get(other_id)
        if filter_func is not None and not filter_func(other_obj):
            continue

        # test distance
        test = FrameContext.context.sbs.distance_id(source_id, other_id)
        if max_dist is None:
            ret = CloseData(other_id, other_obj, test)
            max_dist = test
            continue
        elif test < max_dist:
            ret = CloseData(other_id, other_obj, test)
            max_dist = test
            continue

    return ret

def closest_to_point(point, the_set, max_dist=None, filter_func=None) -> CloseData:
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
            no candidates qualify.
    """
    if max_dist is not None:
        max_dist = max_dist*max_dist
    test = max_dist
    ret = None

    the_set = to_set(the_set)
    
    closest_id = None
    for other_id in the_set:
        other_obj = Agent.get(other_id)
        if filter_func is not None and not filter_func(other_obj):
            continue

        # test distance
        test = Vec3(other_obj.pos) - point
        test = test.dot(test)


        if max_dist is None:
            closest_id = other_id
            max_dist = test
            continue
        elif test < max_dist:
            closest_id = other_id
            max_dist = test
            continue

    if closest_id is None:
        return None
    return CloseData(other_id, other_obj, math.sqrt(test))



def closest_object(the_ship, the_set, max_dist=None, filter_func=None) -> Agent:
    """Return the closest agent object to a source from a candidate set.

    Args:
        the_ship (Agent | int | Vec3): Reference agent ID, object, or position.
        the_set (Agent | int | set[Agent | int]): Candidate agent(s) to test.
        max_dist (float, optional): Maximum distance to consider. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``.
            Defaults to None.

    Returns:
        Agent | None: The closest agent, or ``None`` if no candidates qualify.
    """
    ret = closest(the_ship, the_set, max_dist, filter_func)
    if ret:
        return ret.py_object

def target(set_or_object, target_id, shoot: bool = True, throttle: float = 1.0, stop_dist=None):
    """Direct one or more agents to move toward and optionally shoot a target.

    Args:
        set_or_object (Agent | int | set[Agent | int]): Agent(s) to command.
        target_id (Agent | int): The target agent ID or object.
        shoot (bool, optional): If ``True``, lock weapons on the target as well
            as moving toward it. Defaults to True.
        throttle (float, optional): Movement speed multiplier (0.0–1.0).
            Defaults to 1.0.
        stop_dist (float, optional): Stop the agent (throttle→0) when it comes
            within this distance of the target. Defaults to None.
    """
    target_obj = to_object(target_id)
    if target_obj  is None:
        return
    
    target_id = 0
    _pos = Vec3(target_obj.pos)
    if shoot:
        target_id = target_obj.id
    all = to_list(set_or_object)
    for chaser in all:
        chaser = Agent.resolve_py_object(chaser)
        if chaser is not None:
            chaser.data_set.set("target_pos_x", _pos.x,0)
            chaser.data_set.set("target_pos_y", _pos.y,0)
            chaser.data_set.set("target_pos_z", _pos.z,0)
            chaser.data_set.set("target_id", target_id,0)
            t = throttle
            if stop_dist is not None:
                diff = Vec3(chaser.pos) - _pos
                if diff.length() < stop_dist:
                    t = 0
            chaser.data_set.set("throttle", t,0)



def target_pos(chasers: set | int | CloseData|SpawnData, x: float, y: float, z: float, throttle: float = 1.0, target_id=None, stop_dist=None):
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
            this distance of the target. Defaults to None.
    """
    pos = Vec3(x,y,z)   
    all = to_list(chasers)
    if target_id is not None:
        target_id = to_id(target_id)
    for chaser in all:
        chaser = Agent.resolve_py_object(chaser)
        if chaser is None or not object_exists(chaser):
            continue
        chaser.data_set.set("target_pos_x", x, 0)
        chaser.data_set.set("target_pos_y", y,0)
        chaser.data_set.set("target_pos_z", z,0)
        if target_id is not None:
            chaser.data_set.set("target_id", target_id,0)

        t = throttle
        if stop_dist is not None:
            diff = Vec3(chaser.pos) - pos
            if diff.length() < stop_dist:
                t = 0
        chaser.data_set.set("throttle", t, 0)
    

def target_shoot(chasers: set | int | CloseData|SpawnData, target_id=None):
    """Set the weapons target on one or more agents without changing their movement.

    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to update.
        target_id (Agent | int, optional): The agent to fire at. Defaults to
            None.
    """
    all = to_list(chasers)
    if target_id is not None:
        target_id = to_id(target_id)
    if not object_exists(target_id):
        return
    
    for chaser in all:
        chaser = to_object(chaser)
        if chaser is None or not object_exists(chaser):
            continue
        if target_id is not None:
            chaser.data_set.set("target_id", target_id,0)


def clear_target(chasers: set | int | Agent | CloseData | SpawnData, throttle=0):
    """Clear the movement and weapons target on one or more agents.

    Sets the target position to the agent's current position and zeroes the
    weapon target ID, effectively stopping pursuit.

    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to update.
        throttle (float, optional): Throttle to apply after clearing. Defaults
            to 0.
    """
    all = to_list(chasers)
    for chaser in all:
        chaser = Agent.resolve_py_object(chaser)
        this = FrameContext.context.sim.get_space_object(chaser.id)
        chaser.data_set.set("target_pos_x", this.pos.x,0)
        chaser.data_set.set("target_pos_y", this.pos.y,0)
        chaser.data_set.set("target_pos_z", this.pos.z,0)
        chaser.data_set.set("target_id", 0,0)
        chaser.data_set.set("throttle", throttle, 0)


def get_pos(id_or_obj):
    """Return the current position of an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        Vec3 | None: The agent's position, or ``None`` if it does not exist.
    """
    object = to_object(id_or_obj)
    if object is not None:
        eo = object.engine_object
        if eo:
            return eo.pos
    return None

def set_pos(id_or_obj, x, y=None, z=None):
    """Teleport one or more agents to a position.

    Args:
        id_or_obj (Agent | int | set[Agent | int]): Agent(s) to reposition.
        x (float | Vec3): X coordinate, or a Vec3 when ``y`` is omitted.
        y (float, optional): Y coordinate. If ``None``, ``x`` is treated as a
            Vec3. Defaults to None.
        z (float, optional): Z coordinate. Defaults to None.
    """
    ids = to_set(id_or_obj)
    for id in ids:
        object = to_object(id)
        if object is not None:
            eo = object.engine_object
            if eo:
                if y is None:
                    FrameContext.context.sim.reposition_space_object(eo, x.x, x.y, x.z)
                else:
                    FrameContext.context.sim.reposition_space_object(eo, x, y, z)

def get_engineering_value(id_or_obj, name, default=None):
    """Get a named engineering control value from a ship.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): The engineering control label to look up (case-insensitive).
        default (float, optional): Value returned if the label is not found.
            Defaults to None.

    Returns:
        float | None: The current value of the control, or ``default``.
    """
    so = to_object(id_or_obj)
    if so is None: return default

    for x in range(30):
        label = so.data_set.get("eng_control_label", x)
        if label is None or label == "":
            return default
        
        if label.lower() == name.lower():
            return so.data_set.get("eng_control_value", x)
    return default

def set_engineering_value(id_or_obj, name, value):
    """Set a named engineering control value on a ship.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): The engineering control label to update (case-insensitive).
        value (float): The new value.
    """
    so = to_object(id_or_obj)
    for x in range(30):
        label = so.data_set.get("eng_control_label", x)
        if label is None or label == "":
            return
        if label.lower() == name.lower():
            return so.data_set.set("eng_control_value", value, x)
    return



def delete_objects_sphere(x,y,z, radius, broad_type=0x0F, roles=None):
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
            listed roles are deleted. Defaults to None (delete all matches).
    """
    # TODO: Modify such that a Vec3 can be provided.
    ids = broad_test(x-radius, z-radius, x+radius, z+radius, broad_type)
    if roles is not None:
        ids = ids & all_roles(roles)

    r = radius * radius
    mid = Vec3(x,y,z)
    for id in ids:
        obj = to_object(id)
        if obj is None:
            continue
        pos = Vec3(obj.pos)
        diff = mid-pos
        if diff.dot(diff) <= r:
            obj.remove()
            FrameContext.context.sbs.delete_object(id)



def delete_objects_box(x,y,z, w,h,d, broad_type=0x0F, roles=None):
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
            listed roles are deleted. Defaults to None (delete all matches).
    """
    # TODO: Modify such that a Vec3 can be provided.
    ids = broad_test(x-w, z-d, x+w, z+d, broad_type)
    if roles is not None:
        ids = ids & all_roles(roles)

    for id in ids:
        obj = to_object(id)
        if obj is None:
            continue
        pos = Vec3(obj.pos)

        if abs(pos.y-y) <= h:
            obj.remove()
            FrameContext.context.sbs.delete_object(id)

def delete_object(id_or_objs):
    """Delete one or more agents from the simulation.

    Args:
        id_or_objs (Agent | int | set[Agent | int]): Agent(s) to delete.
    """
    ids = to_set(id_or_objs)
    
    for id in ids:
        obj = to_object(id)
        if obj is None:
            continue
        obj.delete_object()



