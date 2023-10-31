from sbs_utils.engineobject import CloseData
from sbs_utils.engineobject import EngineObject
from sbs_utils.engineobject import SpawnData
from sbs_utils.helpers import FrameContext
def all_objects_exists (the_set):
    ...
def dec_disable_grid_selection (id_or_obj):
    ...
def dec_disable_science_selection (id_or_obj):
    ...
def dec_disable_selection (id_or_obj, console):
    ...
def dec_disable_weapons_selection (id_or_obj):
    ...
def get_comms_selection (id_or_not):
    ...
def get_data_set_value (data_set, key, index=0):
    ...
def get_engine_data (id_or_obj, key, index=0):
    ...
def get_engine_data_set (id_or_obj):
    ...
def get_grid_selection (id_or_not):
    ...
def get_science_selection (id_or_not):
    ...
def get_weapons_selection (id_or_not):
    ...
def inc_disable_grid_selection (id_or_obj):
    ...
def inc_disable_science_selection (id_or_obj):
    ...
def inc_disable_selection (id_or_obj, console):
    ...
def inc_disable_weapons_selection (id_or_obj):
    ...
def is_client_id (id):
    ...
def is_grid_object_id (id):
    ...
def is_space_object_id (id):
    ...
def is_story_id (id):
    ...
def is_task_id (id):
    ...
def object_exists (so_id):
    ...
def random_object (the_set):
    """random_object
    
    get the object from the set provide
    
    :rtype: EngineObject"""
def random_object_list (the_set, count=1):
    """random_object_list
    
    get a list of objects selected randomly from the set provided
    
    :param the_set: Set of Ids
    :type the_set: set of ids
    :param count: The number of objects to pick
    :type count: int
    :rtype: list of EngineObject"""
def set_data_set_value (data_set, key, value, index=0):
    ...
def set_engine_data (to_update, key, value, index=0):
    ...
def to_blob (id_or_obj):
    ...
def to_data_set (id_or_obj):
    ...
def to_engine_object (id_or_obj):
    ...
def to_id (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_id_list (the_set):
    """to_id_list
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
def to_list (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_list
    
    converts a single object/id, set ot list of things to a list
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of things"""
def to_object (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_object_list (the_set):
    """to_object_list
    
    converts a set to a list of objects
    
    :param the_set: A set of ids
    :type the_set: set of ids
    
    :rtype: list of EngineObject"""
def to_py_object_list (the_set):
    """to_py_object_list
    
    converts a set of ids to a set of objects
    
    :rtype: list EngineObject"""
def to_set (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_set
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
def update_engine_data (to_update, data):
    ...
