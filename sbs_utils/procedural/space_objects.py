from ..agent import Agent, CloseData, SpawnData
from .query import to_set, to_list, to_object, to_id, object_exists
from ..helpers import FrameContext
from ..vec import Vec3
from .roles import all_roles




def broad_test(x1: float, z1: float, x2: float, z2: float, broad_type=0xfff0):
    """returns a set of ids that are in the target rect

    Args:
        x1(float): x location (left)
        z1(float): z location (top)
        x2(float): x location (right)
        z2(float): z location (bottom)
        broad_type (int, optional): -1=All, 0=player, 1=Active, 2=Passive. Defaults to -1.

    Returns:
        set: A set of ids
    """    
    obj_list = FrameContext.context.sbs.broad_test(x1, z1, x2, z2, broad_type)
    return {so.unique_ID for so in obj_list}

def broad_test_around(id_or_obj, width: float, depth: float, broad_type=0xfff0):
    """returns a set of ids that are around the specified object in the target rect

    Args:
        id_obj(agent): The ID or object of an agent
        w(float): width
        d(float): depth
        broad_type (int, optional): -1=All, 0=player, 1=Active, 2=Passive. Defaults to -1.

    Returns:
        set: A set of ids
    """    
    so = to_object(id_or_obj)
    if so is None:
        return {}
    _pos = so.engine_object.pos
    obj_list = FrameContext.context.sbs.broad_test(_pos.x-(width/2), _pos.z-(depth/2), _pos.x+(width/2), _pos.z+(depth/2), broad_type)
    return {so.unique_ID for so in obj_list}


def closest_list(source: int | CloseData | SpawnData | Agent, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    """get the list of close data that matches the test set, max_dist and optional filter function

    Args:
        source (agent): The agent object or id of the agent
        the_set (agents set): a set of ids to check against
        max_dist (float, optional): The maximum distance to include. Defaults to None.
        filter_func (function, optional): an additional function to check against. Defaults to None.

    Returns:
        list[CloseData]: The list of close objects With close data to get the distance
    """    
    ret = []
    test = max_dist
    source_id = Agent.resolve_id(source)

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
            ret.append(CloseData(other_id, other_obj, test))
            continue

        if test < max_dist:
            ret.append(CloseData(other_id, other_obj, test))

    return ret


def closest(the_ship, the_set, max_dist=None, filter_func=None) -> CloseData:
    """get the  close data that matches the test set, max_dist and optional filter function

    Args:
        the_ship (agent): The agent ID or object
        the_set (agent set): The set of objects to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (func, optional): An additional function to test with. Defaults to None.

    Returns:
        CloseData: The close object close data to get the distance
    """    
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


def closest_object(the_ship, the_set, max_dist=None, filter_func=None) -> Agent:
    """get the  close data that matches the test set, max_dist and optional filter function

    Args:
        the_ship (agent): The agent ID or object
        the_set (agent set): The set of objects to test against
        max_dist (float, optional): The maximum distance to check. Defaults to None.
        filter_func (func, optional): An additional function to test with. Defaults to None.

    Returns:
        agent: Return the closest agents or None
    """    
    ret = closest(the_ship, the_set, max_dist, filter_func)
    if ret:
        return ret.py_object

def target(set_or_object, target_id, shoot: bool = True, throttle: float = 1.0, stop_dist=None):
    """set Target a target for an agent/set of agents

    Args:
        set_or_object (agent, set): the agent or set of object to set the target on
        target_id (agent): agent id or object to target
        shoot (bool, optional): whether to also lock weapons on target. Defaults to True.
        throttle (float, optional): The speed to travel at. Defaults to 1.0.
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
    """ Set the target position of an agent or set of agents

    Args:
        chasers (agent id | agent set): the agents to set
        x (float): x location
        y (float): y location
        z (float): z location
        throttle (float, optional): The speed to go. Defaults to 1.0.
        target_id (id, optional): What to shoot
        stop_dist (float, optional): The distance to stop
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


def clear_target(chasers: set | int | CloseData|SpawnData, throttle=0):
    """ clear the target on an agent or set of agents

    Args:
        chasers (set | int | CloseData | SpawnData): an agent or set of agents
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
    """ get the position of an agent

    Args:
        id_or_obj (agent id | agent): The agent to set position on

    Returns:
        Vec3: _description_
    """    
    object = to_object(id_or_obj)
    if object is not None:
        eo = object.engine_object
        if eo:
            return eo.pos
    return None

def set_pos(id_or_obj, x, y=None, z=None):
    """set the position of an agent or set of agents

    Args:
        id_or_obj (agent|set of agent): an agent or set of agent IDs or objects
        x (float| Cec3): The x location or a vector 
        y (float, optional): y location. Defaults to None.
        z (float, optional):z location. Defaults to None.
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
    """gets an engineering value by name

    Args:
        id_or_obj (agent): An agent id or object
        name (str): The value to get
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
    """sets an engineering value by name

    Args:
        id_or_obj (agent): An agent id or object
        name (str): The value to get
        value (float): The value
    """    
    so = to_object(id_or_obj)
    for x in range(30):
        label = so.data_set.get("eng_control_label", x)
        if label is None or label == "":
            return
        if label.lower() == name.lower():
            return so.data_set.set("eng_control_value", value, x)
    return



def remove_objects_sphere(x,y,z, radius, abits=0x0F, roles=None):
    """ Removes items from an area
        
    Args:
        x,y,z (float,float,float): the start point/origin
        radius (float): the radius 
        abits = the engine level bit test for broadtest
        roles = limit to specified roles
    """
    ids = broad_test(x-radius, z-radius, x+radius, z+radius, abits)
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



def remove_objects_box(x,y,z, w,h,d, abits=0x0F, roles=None):
    """ Removes items from an area
        
    Args:
        x,y,z (float,float,float): the start point/origin
        radius (float): the radius 
        abits = the engine level bit test for broadtest
        roles = limit to specified roles
    """
    ids = broad_test(x-w, z-d, x+w, z+d, abits)
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


    


