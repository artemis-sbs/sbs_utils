from random import randrange, choice, choices
from .spaceobject import SpaceObject
from .engineobject import EngineObject, CloseData, SpawnData
import sbs
###################
# Set functions
def role(role: str):
    return SpaceObject.get_role_set(role)

def has_inventory(role: str):
    return SpaceObject.has_inventory_set(role)


def has_link(role: str):
    return SpaceObject.has_links_set(role)

def inventory_set(link_source, link_name: str):
    link_source = SpaceObject.resolve_py_object(link_source)
    return link_source.get_inventory_set(link_name)

def inventory_value(link_source, link_name: str):
    link_source = SpaceObject.resolve_py_object(link_source)
    return link_source.get_inventory_value(link_name)


def linked_to(link_source, link_name: str):
    link_source = SpaceObject.resolve_py_object(link_source)
    return link_source.get_link_set(link_name)

# Get the set of IDS of a broad test


def broad_test(x1: float, z1: float, x2: float, z2: float, broad_type=-1):
    obj_list = sbs.broad_test(x1, z1, x2, z2, broad_type)
    return {so.unique_ID for so in obj_list}


#######################
# Set resolvers
def closest_list(source: int | CloseData | SpawnData | SpaceObject, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    ret = []
    test = max_dist
    source_id = SpaceObject.resolve_id(source)

    for other_id in the_set:
        # if this is self skip
        if other_id == source_id:
            continue
        other_obj = SpaceObject.get(other_id)
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


def closest(self, the_set, max_dist=None, filter_func=None) -> CloseData:
    test = max_dist
    ret = None
    source_id = SpaceObject.resolve_id(self)

    for other_id in the_set:
        # if this is self skip
        if other_id == SpaceObject.resolve_id(self):
            continue
        other_obj = SpaceObject.get(other_id)
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


def closest_object(self, the_set, max_dist=None, filter_func=None) -> SpaceObject:
    ret = closest(self, the_set, max_dist, filter_func)
    if ret:
        return ret.py_object

def random_object(the_set):
    rand_id = choice(tuple(the_set))
    return SpaceObject.get(rand_id)


def random_object_list(the_set, count=1):
    rand_id_list = choices(tuple(the_set), count)
    return [SpaceObject.get(x) for x in rand_id_list]


def to_py_object_list(the_set):
    return [SpaceObject.get(id) for id in the_set]


def target(sim, set_or_object, target_id, shoot: bool = True):
    """ Set the item to target
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    target_id = SpaceObject.resolve_id(target_id)
    target_engine = sim.get_space_object(target_id)

    if target_engine:
        data = {
            "target_pos_x": target_engine.pos.x,
            "target_pos_y": target_engine.pos.y,
            "target_pos_z": target_engine.pos.z,
            "target_id": 0
        }
        if shoot:
            data["target_id"] = target_engine.unique_ID
    all = to_list(set_or_object)
    for chaser in all:
        chaser = SpaceObject.resolve_py_object(chaser)
        chaser.update_engine_data(sim, data)


def target_pos(sim, chasers: set | int | CloseData|SpawnData, x: float, y: float, z: float):
    """ Set the item to target

    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    data = {
        "target_pos_x": x,
        "target_pos_y": y,
        "target_pos_z": z,
        "target_id": 0
    }
    all = to_list(chasers)
    for chaser in all:
        chaser = SpaceObject.resolve_py_object(chaser)
        chaser.update_engine_data(sim, data)

def clear_target(sim, chasers: set | int | CloseData|SpawnData):
        """ Clear the target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        """
        all = to_list(chasers)
        for chaser in all:
            chaser = SpaceObject.resolve_py_object(chaser)
            this = sim.get_space_object(chaser.id)
            chaser.update_engine_data(sim, {
                "target_pos_x": this.pos.x,
                "target_pos_y": this.pos.y,
                "target_pos_z": this.pos.z,
                "target_id": 0
            })

def to_object_list(the_set):
    return [SpaceObject.resolve_py_object(x) for x in list(the_set)]
def to_id_list(the_set):
    return [SpaceObject.resolve_id(x) for x in list(the_set)]

def to_list(other: EngineObject | CloseData | int):
    if isinstance(other, set):
        return list(other)
    elif isinstance(other, list):
        return other
    elif other is None:
        return []
    return [other]

def to_set(other: EngineObject | CloseData | int):
    if isinstance(other, list):
        return set(other)
    elif isinstance(other, set):
        return other
    elif other is None:
        return {}
    return {to_id(other)}



def to_id(other: EngineObject | CloseData | int):
    other_id = other
    if isinstance(other, EngineObject):
        other_id = other.id
    elif isinstance(other, CloseData):
        other_id = other.id
    elif isinstance(other, SpawnData):
        other_id = other.id
   
    return other_id

def to_object(other: EngineObject | CloseData | int):
    py_object = other
    if isinstance(other, EngineObject):
        py_object = other
    elif isinstance(other, CloseData):
        py_object = other.py_object
    elif isinstance(other, SpawnData):
        py_object = other.py_object
    else:
        # In the future this should be EngineObject
        # When Grid  Items and space object live as one
        py_object = SpaceObject.get(other)
    return py_object


def link(set_holder, link, set_to):
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            so.add_link(link, target)

def get_dedicated_link(so, link):
    so = to_object(so)
    return so.get_dedicated_link(link)
            
def set_dedicated_link(so, link, to):
    so = to_object(so)
    to = to_id(to)
    so.set_dedicated_link(link, to)


def has_role(so, role):
    so = to_object(so)
    return so.has_role(role)


def get_inventory_value(so, link):
    so = to_object(so)
    return so.get_inventory_value(link)
            
def set_inventory_value(so, link, to):
    so = to_object(so)
    to = to_id(to)
    so.set_inventory_value(link, to)


def unlink(set_holder, link, set_to):
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            so.remove_link(link, target)

def object_exists(sim, so_id):
    so_id = to_id(so_id)
    eo = sim.get_space_object(so_id)
    return eo is not None


