from ..agent import Agent, CloseData, SpawnData
from .query import to_set, to_list, to_object
from ..helpers import FrameContext
import sbs




def broad_test(x1: float, z1: float, x2: float, z2: float, broad_type=-1):
    """ broad_test

        returns a set of ids that are in the target rect

        :param x1: x location (left)
        :type x1: float
        :param z1: z location (top)
        :type z1: float
        :param x2: x location (right)
        :type x2: float
        :param z2: z location (bottom)
        :type z2: float

        :param broad type:  -1=All, 0=player, 1=Active, 2=Passive
        :type broad_type: int
        :rtype: set of ids
        """
    
    obj_list = sbs.broad_test(x1, z1, x2, z2, broad_type)
    return {so.unique_ID for so in obj_list}

def broad_test_around(id_or_obj, width: float, depth: float, broad_type=-1):
    """ broad_test_around

        returns a set of ids that are in the target rect

        :param id_or_obj: object to use as a center point
        :type id_or_obj: id or object
        :param width: width
        :type width: float
        :param depth: depth z dimension
        :type depth: float

        :param broad type:  -1=All, 0=player, 1=Active, 2=Passive
        :type broad_type: int
        :rtype: set of ids
        """
    so = to_object(id_or_obj)
    if so is None:
        return {}
    _pos = so.engine_object.pos
    obj_list = sbs.broad_test(_pos.x-(width/2), _pos.z-(depth/2), _pos.x+(width/2), _pos.z+(depth/2), broad_type)
    return {so.unique_ID for so in obj_list}


#######################
# Set resolvers
def closest_list(source: int | CloseData | SpawnData | Agent, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    """ close_list

        get the list of close data that matches the test set, max_dist and optional filter function

        :param source: The id object to check
        :type source: int / id
        :param the_set: a set of ids to check against
        :type the_set: set of ids
        :param max_dist: The maximum distance to include
        :type link_name: float
        :param filter_func: A function to filter the set
        :type filter_func: func
        :rtype: list of CloseData
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
        test = sbs.distance_id(source_id, other_id)
        if max_dist is None:
            ret.append(CloseData(other_id, other_obj, test))
            continue

        if test < max_dist:
            ret.append(CloseData(other_id, other_obj, test))

    return ret


def closest(the_ship, the_set, max_dist=None, filter_func=None) -> CloseData:
    """ closest

        get the  close data that matches the test set, max_dist and optional filter function

        :param source: The id object to check
        :type source: int / id
        :param the_set: a set of ids to check against
        :type the_set: set of ids
        :param max_dist: The maximum distance to include
        :type link_name: float
        :param filter_func: A function to filter the set
        :type filter_func: func
        :rtype: CloseData
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
        test = sbs.distance_id(source_id, other_id)
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
    """ closest_object

        get the object that matches the test set, max_dist and optional filter function

        :param source: The id object to check
        :type source: int / id
        :param the_set: a set of ids to check against
        :type the_set: set of ids
        :param max_dist: The maximum distance to include
        :type link_name: float
        :param filter_func: A function to filter the set
        :type filter_func: func
        :rtype: Agent
        """
    ret = closest(the_ship, the_set, max_dist, filter_func)
    if ret:
        return ret.py_object

def target(set_or_object, target_id, shoot: bool = True, throttle: float = 1.0):
    """ Set the item to target
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    target_id = Agent.resolve_id(target_id)
    target_engine = FrameContext.context.sim.get_space_object(target_id)

    if target_engine:
        target_id = 0
        if shoot:
            target_id = target_engine.unique_ID
        all = to_list(set_or_object)
        for chaser in all:
            chaser = Agent.resolve_py_object(chaser)
            if chaser is not None:
                chaser.data_set.set("target_pos_x", target_engine.pos.x,0)
                chaser.data_set.set("target_pos_y", target_engine.pos.y,0)
                chaser.data_set.set("target_pos_z", target_engine.pos.z,0)
                chaser.data_set.set("target_id", target_id,0)
                chaser.data_set.set("throttle", throttle,0)



def target_pos(chasers: set | int | CloseData|SpawnData, x: float, y: float, z: float, throttle: float = 1.0):
    """ Set the item to target

    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    all = to_list(chasers)
    for chaser in all:
        chaser = Agent.resolve_py_object(chaser)
        chaser.data_set.set("target_pos_x", x, 0)
        chaser.data_set.set("target_pos_y", y,0)
        chaser.data_set.set("target_pos_z", z,0)
        chaser.data_set.set("target_id", 0,0)
        chaser.data_set.set("throttle", throttle, 0)
    
   

def clear_target(chasers: set | int | CloseData|SpawnData):
        """ Clear the target
        
        :param the_set: A set of ids, id, CloseData, or SpawnData
        :type the_set: set of ids, id, CloseData, or SpawnData
        
        """
        all = to_list(chasers)
        for chaser in all:
            chaser = Agent.resolve_py_object(chaser)
            this = FrameContext.context.sim.get_space_object(chaser.id)
            chaser.data_set.set("target_pos_x", this.pos.x,0)
            chaser.data_set.set("target_pos_y", this.pos.y,0)
            chaser.data_set.set("target_pos_z", this.pos.z,0)
            chaser.data_set.set("target_id", 0,0)


def get_pos(id_or_obj):
    object = to_object(id_or_obj)
    if object is not None:
        eo = object.engine_object
        if eo:
            return eo.pos
    return None

def set_pos(id_or_obj, x, y=None, z=None):
    ids = to_set(id_or_obj)
    for id in ids:
        object = to_object(id)
        if object is not None:
            eo = object.engine_object
            if eo:
                if y is None:
                    return FrameContext.context.sim.reposition_space_object(eo, x.x, x.y, x.z)
                return FrameContext.context.sim.reposition_space_object(eo, x, y, z)

def get_engineering_value(id_or_obj, name, default=None):
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
    so = to_object(id_or_obj)
    for x in range(30):
        label = so.data_set.get("eng_control_label", x)
        if label is None or label == "":
            return
        if label.lower() == name.lower():
            return so.data_set.set("eng_control_value", value, x)
    return
