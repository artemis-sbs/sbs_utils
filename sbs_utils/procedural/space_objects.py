from ..agent import Agent, CloseData, SpawnData
from .query import to_set, to_list, to_object, to_id, object_exists
from ..helpers import FrameContext
from ..vec import Vec3
from .roles import all_roles
import math



def broad_test(x1: float, z1: float, x2: float, z2: float, broad_type=0xfff0):
    """
    Returns a set of ids that are in the target rect.
    Args:
        x1 (float): x location (left)
        z1 (float): z location (top)
        x2 (float): x location (right)
        z2 (float): z location (bottom)
        broad_type (int, optional): The type of objects for which to search.
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0xfff0
    Returns:
        set[int]: A set of ids
    """    
    obj_list = FrameContext.context.sbs.broad_test(x1, z1, x2, z2, broad_type)
    return {so.unique_ID for so in obj_list}

def broad_test_around(id_or_obj, width: float, depth: float, broad_type=0xfff0):
    """
    Returns a set of ids that are around the specified object in the target rect.
    Args:
        id_obj (Agent | int | Vec3): The ID or object of an agent
        w (float): width
        d (float): depth
        broad_type (int, optional): The type of objects for which to search.
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0xfff0
    Returns:
        set[int]: A set of ids
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


def closest_list(source: int | CloseData | SpawnData | Agent | Vec3, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    """
    Get the list of close data that matches the test set, max_dist, and optional filter function.
    Args:
        source (Agent | int | CloseData | SpawnData): The agent object or id of the agent.
        the_set (set[int]): A set of ids to check against.
        max_dist (float, optional): The maximum distance to include. Defaults to None.
        filter_func (Callable, optional): An additional function to check against. Defaults to None.

    Returns:
        list[CloseData]: The list of CloseData representing the close objects to get the distance.
    """    
    ret = []
    test = max_dist

    if isinstance(source, Vec3):
        source_id = -1
    else:
        source_id = Agent.resolve_id(source)

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
    """
    Get the CloseData that matches the test set, max_dist, and optional filter function.

    Args:
        the_ship (Agent | int | Vec3): The agent ID or object
        the_set (Agent | int | set[Agent | int]): The agent or id or set of objects or ids to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (Callable, optional): An additional function to test with. Defaults to None.

    Returns:
        CloseData: The closest object's CloseData to get the distance.
    """
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
    """
    Get the CloseData that matches the test set, max_dist, and optional filter function.

    Args:
        the_ship (Agent | int): The agent ID or object
        the_set (Agent | int | set[Agent | int]): The agent or id or set of objects or ids to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (Callable, optional): An additional function to test with. Defaults to None.

    Returns:
        CloseData: The closest object's CloseData to get the distance.
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
    """
    Get the CloseData that matches the test set, max_dist, and optional filter function.

    Args:
        the_ship (Agent | int | Vec3): The agent ID or object.
        the_set (Agent | int | set[Agent | int]): The id or object or set of objects or ids to test against.
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (func, optional): An additional function to test with. Defaults to None.

    Returns:
        agent: Return the closest agents or None
    """    
    ret = closest(the_ship, the_set, max_dist, filter_func)
    if ret:
        return ret.py_object

def target(set_or_object, target_id, shoot: bool = True, throttle: float = 1.0, stop_dist=None):
    """
    Set the target for an agent or set of agents.
    Args:
        set_or_object (Agent | int | set[Agent | int]): The agent or set of agents for which to set the target.
        target_id (Agent | int): The agent id or object to target.
        shoot (bool, optional): Whether to also lock weapons on target. Defaults to True.
        throttle (float, optional): The speed at which to travel. Defaults to 1.0.
        stop_dist (int, optional): If the target is within this distance, then the throttle will be set to 0. Default is None.
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
    """ 
    Set the target position of an agent or set of agents

    Args:
        chasers (Agent | int | set[Agent | int]): The agents which should go to the target position.
        x (float): x location
        y (float): y location
        z (float): z location
        throttle (float, optional): The speed at which to travel. Defaults to 1.0.
        target_id (id, optional): What to shoot
        stop_dist (float, optional): If the target position is within this distance, then the throttle will be set to 0. Default is None.
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
    """ Set the target id only
    Args:
        chasers (agent id | agent set): the agents to set
        target_id (id, optional): What to shoot
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
    """ 
    Clear the target on an agent or set of agents.

    Args:
        chasers (set[Agent | int] | int | Agent | CloseData | SpawnData): an agent or set of agents
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
    """ 
    Get the position of an agent.

    Args:
        id_or_obj (Agent | int): The agent for which to get the position.

    Returns:
        Vec3 | None: The position of the agent or None if it doesn't exist.
    """    
    object = to_object(id_or_obj)
    if object is not None:
        eo = object.engine_object
        if eo:
            return eo.pos
    return None

def set_pos(id_or_obj, x, y=None, z=None):
    """
    Set the position of an agent or set of agents.

    Args:
        id_or_obj (Agent | int | set[Agent | int]): An agent or set of agent IDs or objects.
        x (float | Vec3): The x location or a vector.
        y (float, optional): y location. If None, `x` is assumed to be a Vec3. Defaults to None.
        z (float, optional): z location. Defaults to None.
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
    """
    Gets an engineering value by name.

    Args:
        id_or_obj (Agent | int): An agent id or object.
        name (str): The engineering value to get.
        default (float, optional): What to return if not found. Defaults to None.

    Returns:
        float: A value or the default
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
    """
    Sets an engineering value by name

    Args:
        id_or_obj (Agent | int): An agent id or object.
        name (str): The engineering value to set.
        value (float): The value.
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
    """ 
    Removes items from an area if they meet the broadtype and role filter requirements.
        
    Args:
        x,y,z (float,float,float): The start point/origin of the sphere.
        radius (float): The radius of the sphere.
        broad_type (int, optional) The engine level bit test for broadtest.
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0x0F
        roles (str, optional): A comma-separated list of roles that the objects must have to be deleted.
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
    """ Removes items from an area
        
    Args:
        x,y,z (float,float,float): the start point/origin
        radius (float): the radius 
        broad_type (int, optional): The engine level bit test for broadtest
            * TERRAIN = 0x01,
            * NPC = 0x10,
            * PLAYER = 0x20,
            * ALL = 0xffff,
            * NPC_AND_PLAYER = 0x30,
            * DEFAULT is 0x0F
        roles (str, optional): A comma-separated list of roles that the objects must have to be deleted.
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
    """ 
    Delete the specified object or set of objects.
    Args:
        id_or_objs (Agent | int | set[Agent | int]): The object or set of objects.
    """
    ids = to_set(id_or_objs)
    
    for id in ids:
        obj = to_object(id)
        if obj is None:
            continue
        obj.delete_object()



