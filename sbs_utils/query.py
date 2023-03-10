import functools
from random import randrange, choice, choices
from .engineobject import EngineObject, CloseData, SpawnData
import sbs
###################
# Set functions
def role(role: str):
    return EngineObject.get_role_set(role)

def has_inventory(role: str):
    return EngineObject.has_inventory_set(role)


def has_link(role: str):
    return EngineObject.has_links_set(role)

def inventory_set(link_source, link_name: str):
    link_source = EngineObject.resolve_py_object(link_source)
    return link_source.get_inventory_set(link_name)

def inventory_value(link_source, link_name: str):
    link_source = EngineObject.resolve_py_object(link_source)
    return link_source.get_inventory_value(link_name)


def linked_to(link_source, link_name: str):
    link_source = EngineObject.resolve_py_object(link_source)
    return link_source.get_link_set(link_name)

# Get the set of IDS of a broad test


def broad_test(x1: float, z1: float, x2: float, z2: float, broad_type=-1):
    obj_list = sbs.broad_test(x1, z1, x2, z2, broad_type)
    return {so.unique_ID for so in obj_list}


#######################
# Set resolvers
def closest_list(source: int | CloseData | SpawnData | EngineObject, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    ret = []
    test = max_dist
    source_id = EngineObject.resolve_id(source)

    for other_id in the_set:
        # if this is self skip
        if other_id == source_id:
            continue
        other_obj = EngineObject.get(other_id)
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
    source_id = EngineObject.resolve_id(self)
    the_set = to_set(the_set)

    for other_id in the_set:
        # if this is self skip
        if other_id == source_id:
            continue
        other_obj = EngineObject.get(other_id)
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


def closest_object(self, the_set, max_dist=None, filter_func=None) -> EngineObject:
    ret = closest(self, the_set, max_dist, filter_func)
    if ret:
        return ret.py_object

def random_object(the_set):
    rand_id = choice(tuple(the_set))
    return EngineObject.get(rand_id)


def random_object_list(the_set, count=1):
    rand_id_list = choices(tuple(the_set), count)
    return [EngineObject.get(x) for x in rand_id_list]


def to_py_object_list(the_set):
    return [EngineObject.get(id) for id in the_set]


def target(sim, set_or_object, target_id, shoot: bool = True):
    """ Set the item to target
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    target_id = EngineObject.resolve_id(target_id)
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
        chaser = EngineObject.resolve_py_object(chaser)
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
        chaser = EngineObject.resolve_py_object(chaser)
        chaser.update_engine_data(sim, data)

def clear_target(sim, chasers: set | int | CloseData|SpawnData):
        """ Clear the target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        """
        all = to_list(chasers)
        for chaser in all:
            chaser = EngineObject.resolve_py_object(chaser)
            this = sim.get_space_object(chaser.id)
            chaser.update_engine_data(sim, {
                "target_pos_x": this.pos.x,
                "target_pos_y": this.pos.y,
                "target_pos_z": this.pos.z,
                "target_id": 0
            })

def to_object_list(the_set):
    return [EngineObject.resolve_py_object(x) for x in list(the_set)]
def to_id_list(the_set):
    return [EngineObject.resolve_id(x) for x in list(the_set)]

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
        # should return space object or grid object
        py_object = EngineObject.get(other)
    return py_object


def link(set_holder, link, set_to):
    linkers = to_object_list(to_set(set_holder))
    ids = to_id_list(to_set(set_to))
    for so in linkers:
        for target in ids:
            so.add_link(link, target)

def add_role(set_holder, role):
    linkers = to_object_list(to_set(set_holder))
    for so in linkers:
        so.add_role(role)

def remove_role(set_holder, role):
    linkers = to_object_list(to_set(set_holder))
    for so in linkers:
        so.remove_role(role)


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


def grid_objects(sim, so_id):
    gos = set()
    hm = sbs.get_hull_map(sim, to_id(so_id))
    if hm is None:
        return gos
    count = hm.get_grid_object_count()
    for i in range(count):
        go = hm.get_grid_object_by_index(i)
        gos.add(go.unique_ID)
    return gos

def update_engine_data(sim, to_update, data):
    objects = to_object_list(to_set(to_update))
    for object in objects:
        object.update_engine_data(sim, data)

def get_engine_data(id_or_obj, sim, key, index=0):
    object = to_object(id_or_obj)
    if object is not None:
        return object.get_engine_data(sim, key, index)
    return None


def set_engine_data(to_update, sim, key, value, index=0):
    objects = to_object_list(to_set(to_update))
    for object in objects:
        object.set_engine_data(sim, key, value, index=0)



################################
##########################################
####### TODO: Update for sets

def grid_close_list(grid_obj, sim, roles=None, max_dist=None, filter_func=None) -> list[CloseData]:
    """ Finds a list of matching objects
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str]
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func:
    :return: A list of close object
    :rtype: List[GridCloseData]
    """
    ret = []
    test_roles = None
    if roles is not None:
        test_roles = set(roles)
    hullMap = sim.get_hull_map(grid_obj.host_id)
    if hullMap != None:
        num_units = hullMap.get_grid_object_count()
        for x in range(num_units):
            other = hullMap.get_grid_object_by_index(x)
            other_id = other.unique_ID
            other_go = EngineObject.get(other_id)
            # skip this one
            if other_id == grid_obj.id:
                continue
            if test_roles:
                other_roles = set(other_go.get_roles())
                intersect = test_roles.intersection(other_roles)
                # if no overlap of roles - skip
                if len(intersect)==0:
                    continue

            if filter_func and not filter_func(other_go):
                continue
            
            test = 0
            if test < max_dist:
                ret.append(CloseData(other_id, other_go, test))

            ret.append(CloseData(other_id, other_go, test))
            continue

            

        return ret

def grid_closest(grid_obj, sim, roles=None, max_dist=None, filter_func=None) -> CloseData:
    """ Finds the closest object matching the criteria

    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str] 
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func: function that takes ID
    :return: A list of close object
    :rtype: GridCloseData
    """
    close = grid_obj.find_close_list(sim, roles, max_dist, filter_func)
    # Maybe not the most efficient
    functools.reduce(lambda a, b: a if a.distance < b.distance else b, close)

def grid_target_closest(grid_obj, sim, roles=None, max_dist=None, filter_func=None):
    """ Find and target the closest object matching the criteria

    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str] 
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func: function
    :param shoot: if the target should be shot at
    :type shoot: bool
    :return: A list of close object
    :rtype: GridCloseData
    """
    close = grid_obj.find_closest(sim, roles, max_dist, filter_func)
    if close.id is not None:
        grid_obj.target(sim, close.id)
    return close

def grid_target(grid_obj, sim, other_id: int):
    """ Set the item to target

    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    this = sim.get_grid_object(grid_obj.id)
    other = sim.get_grid_object(other_id)
    if other:
        x = blob.get("pathx", 0)
        y = blob.get("pathy", 0)

        blob = this.data_set
        blob.set("pathx", x, 0)
        blob.set("pathy", y, 0)

def grid_target_pos(grid_obj, sim, x:float, y:float):
    """ Set the item to target

    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    go = grid_obj.grid_object(sim)
    blob = go.data_set
    blob.set("pathx", x, 0)
    blob.set("pathy", y, 0)

def grid_clear_target(grid_obj, sim):
    """ Clear the target

    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    """
    go = grid_obj.get_grid_object()
    blob = go.data_set
    x= blob.get("curx", x, 0)
    y=blob.get("curx", x, 0)
    grid_obj.target_pos(x,y)

