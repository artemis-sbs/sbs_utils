from random import randrange, choice, choices
from .spaceobject import SpaceObject, CloseData, SpawnData
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
    SpaceObject.resolve_id(target_id)
    target = sim.get_space_object(target_id)

    if target:
        data = {
            "target_pos_x": target.pos.x,
            "target_pos_y": target.pos.y,
            "target_pos_z": target.pos.z,
            "target_id": 0
        }
        if shoot:
            data["target_id"] = target.unique_ID

    all = list(set_or_object)
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
    all = list(chasers)
    for chaser in all:
        chaser = SpaceObject.resolve_py_object(chaser)
        chaser.update_engine_data(sim, data)

def to_object(the_set):
    return [SpaceObject.resolve_py_object(x) for x in list(the_set)]
def to_id(the_set):
    return [SpaceObject.resolve_id(x) for x in list(the_set)]


def link(set_holder, link, set_to):
    linkers = to_object(set_holder)
    ids = to_id(set_to)
    for so in linkers:
        for target in ids:
            so.add_link(link, target)

def unlink(set_holder, link, set_to):
    linkers = to_object(set_holder)
    ids = to_id(set_to)
    for so in linkers:
        for target in ids:
            so.remove_link(link, target)
