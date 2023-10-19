from random import randrange, choice, choices
from ..engineobject import EngineObject, CloseData, SpawnData
from ..helpers import FrameContext

###################
# Set functions
# Get the set of IDS of a broad test
def to_py_object_list(the_set):
    """ to_py_object_list

        converts a set of ids to a set of objects

        :rtype: list EngineObject
        """
    return [EngineObject.get(id) for id in the_set]



def to_object_list(the_set):
    """ to_object_list

        converts a set to a list of objects

        :param the_set: A set of ids
        :type the_set: set of ids
        
        :rtype: list of EngineObject
        """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y := EngineObject.resolve_py_object(x)) is not None]

def to_id_list(the_set):
    """ to_id_list

        converts a single object/id, set ot list of things to a set of ids

        :param the_set: The a set of things
        :type the_set: set, list or single item
        :rtype: list of ids
        """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y:=EngineObject.resolve_id(x)) is not None]

def to_list(other: EngineObject | CloseData | int):
    """ to_list

        converts a single object/id, set ot list of things to a list

        :param the_set: The a set of things
        :type the_set: set, list or single item
        :rtype: list of things
        """
    if isinstance(other, set):
        return list(other)
    elif isinstance(other, list):
        return other
    elif other is None:
        return None
    return [other]

def to_set(other: EngineObject | CloseData | int):
    """ to_set

        converts a single object/id, set ot list of things to a set of ids

        :param the_set: The a set of things
        :type the_set: set, list or single item
        :rtype: list of ids
        """
    if isinstance(other, list):
        return set(other)
    elif isinstance(other, set):
        return other
    elif other is None:
        return None
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


def object_exists(so_id):
    so_id = to_id(so_id)
    return FrameContext.context.sim.space_object_exists(so_id)
    #return eo is not None

def all_objects_exists(the_set):
    so_ids = to_id_list(the_set)
    for so_id in so_ids:
        if not FrameContext.context.sim.space_object_exists(so_id):
            return False
    return True



def update_engine_data(to_update, data):
    objects = to_object_list(to_set(to_update))
    for object in objects:
        object.update_engine_data( data)

def get_engine_data(id_or_obj, key, index=0):
    object = to_object(id_or_obj)
    if object is not None:
        return object.get_engine_data(key, index)
    return None

def get_data_set_value(data_set, key, index=0):
    return data_set.get(key, index)
def set_data_set_value(data_set, key, value, index=0):
    return data_set.set(key, value, index)


def get_engine_data_set(id_or_obj):
    if isinstance(id_or_obj, SpawnData):
        return id_or_obj.blob
    object = to_object(id_or_obj)
    if object is not None:
        return object.get_engine_data_set()
    return None



def set_engine_data(to_update, key, value, index=0):
    objects = to_object_list(to_set(to_update))
    for object in objects:
        object.set_engine_data(key, value, index=0)

# easier to remember function names
def to_blob(id_or_obj):
    return get_engine_data_set(id_or_obj)

def to_data_set(id_or_obj):
    return get_engine_data_set(id_or_obj)

def is_client_id(id):
    if id is None:
        return False
    return (id & 0x8000000000000000)!=0
def is_space_object_id(id):
    if id is None:
        return False
    return (id & 0x4000000000000000)!=0
def is_grid_object_id(id):
    if id is None:
        return False
    return (id & 0x2000000000000000)!=0

def is_task_id(id):
    if id is None:
        return False
    return (id & 0x0080000000000000)!=0

def is_story_id(id):
    if id is None:
        return False
    return (id & 0x0040000000000000)!=0



def get_comms_selection(id_or_not):
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("comms_target_UID",0)
    return None

def get_science_selection(id_or_not):
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("science_target_UID",0)
    return None

def get_grid_selection(id_or_not):
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("grid_selected_UID",0)
    return None

def get_weapons_selection(id_or_not):
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("weapon_target_UID",0)
    return None



def random_object(the_set):
    """ random_object

        get the object from the set provide

        :rtype: EngineObject
        """
    rand_id = choice(tuple(the_set))
    return EngineObject.get(rand_id)


def random_object_list(the_set, count=1):
    """ random_object_list

        get a list of objects selected randomly from the set provided

        :param the_set: Set of Ids
        :type the_set: set of ids
        :param count: The number of objects to pick
        :type count: int
        :rtype: list of EngineObject
        """
    rand_id_list = choices(tuple(the_set), count)
    return [EngineObject.get(x) for x in rand_id_list]
