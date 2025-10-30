from random import choice, choices
from ..agent import Agent, CloseData, SpawnData
from ..helpers import FrameContext

###################
# Set functions
# Get the set of IDS of a broad test
def to_py_object_list(the_set):
    """
    Converts a set of ids to a set of objects
    Args:
        the_set (set[int]): A set of IDs
    Returns:
        list[Agent]
    """
    return [Agent.get(id) for id in the_set]



def to_object_list(the_set):
    """
    Converts a set to a list of objects
    Args:        
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[Agent]: A list of Agent objects
    """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y := Agent.resolve_py_object(x)) is not None]

def to_id_list(the_set):
    """
    Converts a set to a list of ids
    Args:        
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[int]: A list of agent ids
    """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y:=Agent.resolve_id(x)) is not None]

def to_list(other: Agent | CloseData | int):
    """
    Converts a single object/id, set or list of things to a list
    Args:        
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        list[Agent | CloseData | int]: A list containing whatever was passed in.
    """
    if isinstance(other, set):
        return list(other)
    elif isinstance(other, list):
        return other
    elif other is None:
        return []
    return [other]

def to_set(other: Agent | CloseData | int):
    """
    Converts a single object/id, set or list of things to a set of ids
    Args:        
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        set[Agent | CloseData | int]: A set containing whatever was passed in.
    """
    if isinstance(other, list):
        # Convert to a list of IDs
        other = [y for x in other if (y:=Agent.resolve_id(x)) is not None]
        return set(other)
    elif isinstance(other, set):
        return other
    elif other is None:
        return set()
    return {to_id(other)}


def to_id(other: Agent | CloseData | int):
    """
    Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id
    """    
    other_id = other
    if isinstance(other, Agent):
        other_id = other.id
    elif isinstance(other, CloseData):
        other_id = other.id
    elif isinstance(other, SpawnData):
        other_id = other.id
   
    return other_id

def to_object(other: Agent | CloseData | int):
    """
    Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None
    """    
    py_object = other
    if isinstance(other, Agent):
        py_object = other
    elif isinstance(other, CloseData):
        py_object = other.py_object
    elif isinstance(other, SpawnData):
        py_object = other.py_object
    elif other==0:
        return None
    else:
        # should return space object or grid object
        py_object = Agent.get(other)
    return py_object


def to_client_object(other: Agent | int):
    """
    Converts the item passed to an gui client
    ??? note
    * Retrun of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None
    """    
    if isinstance(other, Agent):
        py_object = other
        if is_client_id(other.get_id()):
            return py_object
    else:
        if is_client_id(other) or other == 0:
            # should return space object or grid object
            return Agent.get(other)
    return None

def to_space_object(other: Agent | int):
    """
    Converts the item passed to an gui client
    ??? note
    * Retrun of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None
    """    
    other = to_object(other)
    if is_space_object_id(other):
            # should return space object or grid object
            return other
    return None

def to_grid_object(other: Agent | int):
    """
    Converts the item passed to an gui client
    ??? note
    * Retrun of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None
    """    
    other = to_object(other)
    if is_grid_object_id(other):
            # should return space object or grid object
            return other
    return None


def object_exists(so_id):
    """
    Check the engine to see if the item exists
    Args:
        so_id (Agent | int): agent like data converted to id internally
    Returns:
        bool: if the object exists in the engine
    """    
    so_id = to_id(so_id)
    if so_id is None:
        return False
    return FrameContext.context.sim.space_object_exists(so_id) != 0
    #return eo is not None

def all_objects_exists(the_set):
    """
    Tests to see if all the objects in the set exist
    Args:
        the_set (Agent | int | set[Agent | int] | list[Agent | int]): A set, list or single object internally it will assure it is a list
    Returns:
        bool: False if any object does not exist, True if all exist
    """    
    so_ids = to_id_list(the_set)
    for so_id in so_ids:
        if not FrameContext.context.sim.space_object_exists(so_id):
            return False
    return True

def get_data_set_value(id_or_obj, key, index=0):
    """
    Get the data set (blob) value for the object with the given key.
    Args:
        id_or_obj (Agent | int): The agent or id.
        key (str): The data set key
        index (int, optional): The index of the data set value
    Returns:
        any: The value associated with the key and index.
    """
    object = to_object(id_or_obj)
    if object is not None:
        return object.data_set.get(key, index)
    return None

def set_data_set_value(to_update, key, value, index=0):
    """
    Set the data set (blob) value for the objects with the given key. If `to_update` is a set or list, sets the data set value for each object.
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The agent or id or set or list.
        key (str): The data set key.
        value (any): The value to assign.
        index (int, optional): The index of the data set value
    """
    objects = to_object_list(to_set(to_update))
    for object in objects:
        object.data_set.set(key, value, index)

def get_engine_data_set(id_or_obj):
    """
    Get the data set (blob) for the id or object.
    Args:
        id_or_obj (Agent | SpawnData | int)
    Returns:
        data_set: The data set for the object.
    """
    if isinstance(id_or_obj, SpawnData):
        return id_or_obj.blob
    object = to_object(id_or_obj)
    if object is not None:
        return object.data_set
    return None

# easier to remember function names
def to_blob(id_or_obj):
    """
    Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_data_set
    Args:
        id_or_obj (Agent | int): Agent id or object
    Returns:
        data_set | None: Returns the data or None if it does not exist
    """    
    return get_engine_data_set(id_or_obj)

def to_data_set(id_or_obj):
    """
    Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_blob
    Args:
        id_or_obj (Agent | int): Agent id or object
    Returns:
        data_set | None: Returns the data or None if it does not exist
    """    
    return get_engine_data_set(id_or_obj)

def is_client_id(id):
    """
    Checks if the agent is a client/console id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if the agent is a client or console id
    """
    id = to_id(id)
    if id is None:
        return False
    return (id & 0x8000000000000000)!=0

def is_space_object_id(id):
    """
    Checks if the agent is a space object id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if it is a space object
    """
    id = to_id(id)
    if id is None:
        return False
    return (id & 0x4000000000000000)!=0

def is_grid_object_id(id):
    """
    Checks if the agent is a grid object id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if it is a grid object
    """
    id = to_id(id)
    if id is None:
        return False
    return (id & 0x2000000000000000)!=0

def is_task_id(id):
    """
    Checks if the agent is a task id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if the agent is a task
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x0080000000000000)!=0

def is_story_id(id):
    """
    Checks if the agent is a story id
    !!! Note
    * Story agent are object not in the engine. e.g. Fleets
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if the agent is a story object 
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x0040000000000000)!=0


def to_engine_object(id_or_obj):
    """
    Converts the agent to get its engine object pointer
    Args:
        id (Agent | int): Agent id or object
    Returns:
        pointer: A C++ pointer to the engine object
    """
    object = to_object(id_or_obj)
    if object is not None:
        eo = object.engine_object
        return eo
    return None


def get_comms_selection(id_or_not):
    """
    Gets the id of the comms selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None
    """    
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("comms_target_UID",0)
    return None

def get_science_selection(id_or_not):
    """
    Gets the id of the science selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None
    """        
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("science_target_UID",0)
    return None

def get_grid_selection(id_or_not):
    """
    Gets the id of the engineering grid selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None
    """    
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("grid_selected_UID",0)
    return None

def get_weapons_selection(id_or_not):
    """
    Gets the id of the weapons selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None
    """        
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("weapon_target_UID",0)
    return None


def set_console_selection(id_or_not, other_id_or_obj, console):
    """
    Set the id of the selection for the console and client.
    Args:
        id_or_not (Agent | int): The player ship ID.
        other_id_or_obj (Agent | int): The selected space object.
        console (str): The console for which the object is selected.
    """
    blob = to_blob(id_or_not)
    other = to_id(other_id_or_obj)
    if other is None:
        other = 0
    if blob is not None:
        blob.set(console, other, 0)


def set_comms_selection(id_or_not, other_id_or_obj):
    """
    Sets the id of the comms selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent.
    """    
    set_console_selection(id_or_not, other_id_or_obj, "comms_target_UID")

def set_science_selection(id_or_not, other_id_or_obj):
    """
    Sets the id of the science selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent.
    """    

    set_console_selection(id_or_not, other_id_or_obj, "science_target_UID")

def set_grid_selection(id_or_not, other_id_or_obj):
    """
    Sets the id of the engineering grid selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent.
    """    
    set_console_selection(id_or_not, other_id_or_obj, "grid_selected_UID")

def set_weapons_selection(id_or_not, other_id_or_obj):
    """
    Sets the id of the weapons selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent.
    """    
    set_console_selection(id_or_not, other_id_or_obj, "weapon_target_UID")

# TODO: What is the purpose of these functions? Docstrings are based on what they do, but the purpose is unclear.
def inc_disable_selection(id_or_obj, console_selected_UID):
    """
    Increase the inventory value of the given console's current selection by one and disable the selection. 
    Args:
        id_or_obj (Agent | int): The player ship
        console_selected_UID (int): The console.
    """
    _obj = to_object(id_or_obj)
    if _obj is None: return
    cur = _obj.get_inventory_value(console_selected_UID, 0)
    cur += 1
    _obj.set_inventory_value(console_selected_UID,cur)
    blob = to_blob(id_or_obj)
    blob.set(console_selected_UID,0,0)

def inc_disable_weapons_selection(id_or_obj): inc_disable_selection(id_or_obj, "weapon_target_UID")
def inc_disable_science_selection(id_or_obj): inc_disable_selection(id_or_obj, "science_target_UID")
def inc_disable_grid_selection(id_or_obj): inc_disable_selection(id_or_obj, "grid_selected_UID")

def dec_disable_selection(id_or_obj, console_selected_UID):
    """
    Decrease the inventory value of the given console's current selection by one and disable the selection. 
    Args:
        id_or_obj (Agent | int): The player ship
        console_selected_UID (int): The console.
    """
    _obj = to_object(id_or_obj)
    if _obj is None: return
    cur = _obj.get_inventory_value(console_selected_UID, 0)
    cur -= 1
    _obj.set_inventory_value(console_selected_UID,cur)
    
def dec_disable_weapons_selection(id_or_obj): dec_disable_selection(id_or_obj, "weapon_target_UID")
def dec_disable_science_selection(id_or_obj): dec_disable_selection(id_or_obj, "science_target_UID")
def dec_disable_grid_selection(id_or_obj): dec_disable_selection(id_or_obj, "grid_selected_UID")

def get_side(id_or_obj):
    """
    Gets the side of the agent
    Args:
        id_or_obj (Agent | int): agent id or object
    Returns:
        str|None: the side
    """    
    so = to_object(id_or_obj)
    if so is not None:
        return so.side
    return ""

def get_side_display(id_or_obj):
    """
    Gets the side of the agent
    Args:
        id_or_obj (Agent | int): agent id or object
    Returns:
        str|None: the side
    """    
    so = to_object(id_or_obj)
    if so is not None:
        return so.side_display
    return ""


def get_race(id_or_obj):
    """
    Get the race of the specified agent
    * Race by default is the side from shipData 
    Args:
        id_or_obj (Agent | int): an agent id or object
    Returns:
        str: The race of the object or None
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    
    return obj.race
    

def get_origin(id_or_obj):
    """ 
    Get the race of the specified agent
    * Origin by default is the side from shipData
    Args:
        id_or_obj (Agent | int): an agent id or object
    Returns:
        str: The race of the object or None
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    
    return obj.origin

def get_crew(id_or_obj):
    """
    Get the race of the specified agent
    * Race by default is the side from shipData
    Args:
        id_or_obj (Agent | int): an agent id or object
    Returns:
        str: The race of the object or None
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    
    return obj.crew

def random_id(the_set):
    """
    Get a random id from the set provided
    Args:
        the_set (set[Agent | int]): a set, list etc. of ids or agents
    Returns:
        int: The id of one of the objects
    """
    if len(the_set)==0:
        return None
    return to_id(choice(tuple(the_set)))



def random_object(the_set):
    """
    Get a random object from the set provided
    Args:
        the_set (set[Agent | int]): a set, list etc. of ids or agents
    Returns:
        Agent: The one of the objects
    """
    if len(the_set)==0:
        return None
    return to_object(choice(tuple(the_set)))



def random_object_list(the_set, count=1):
    """
    Get a list of objects selected randomly from the set provided
    Args: 
        the_set (set[Agent | int]): Set of Ids or agents
        count (int, optional): The number of objects to pick. Default is 1.

    Returns:
        list: A list of Agent
    """
    rand_id_list = choices(tuple(the_set), count)
    return [Agent.get(x) for x in rand_id_list]

def safe_int(s, defa=0):
    """
    Gets an integer or None for the passed data
    Args:
        s (str): The source assumed str, but could also be a number
        defa (int, optional): What to return if the supplied value is not an integer. Default is 0.
    Returns:
        int: the integer or the default
    """    
    if s is None:
        return defa
    if s.isdigit():
        return int(s)
    return defa

def are_variables_defined(keys):
    """
    Check if the provided variable keys are defined in the current task.
    Args:
        keys (str): A comma-separated list of the keys.
    Returns:
        bool: True if all variables are defined, otherwise False.
    """
    task = FrameContext.task
    if task is None:
        return False
    return task.are_variables_defined(keys)