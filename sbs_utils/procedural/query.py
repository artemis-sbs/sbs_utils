from random import randrange, choice, choices
from ..agent import Agent, CloseData, SpawnData
from ..helpers import FrameContext

###################
# Set functions
# Get the set of IDS of a broad test
def to_py_object_list(the_set):
    """ to_py_object_list

        converts a set of ids to a set of objects

        Returns:
            list Agent
        """
    return [Agent.get(id) for id in the_set]



def to_object_list(the_set):
    """ to_object_list
        converts a set to a list of objects

        Args:        
            the_set (set|list): a set of agent ids
        
        Returns:
            list: of Agents
        """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y := Agent.resolve_py_object(x)) is not None]

def to_id_list(the_set):
    """converts a set to a list of ids

        Args:        
            the_set (set|list): a set of agents or ids
        
        Returns:
            list: of agent ids
    """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y:=Agent.resolve_id(x)) is not None]

def to_list(other: Agent | CloseData | int):
    """converts a single object/id, set ot list of things to a list

    Args:        
        the_set (set|list): a set of agent ids
    
    Returns:
        list: containing whatever was passed in
    """
    if isinstance(other, set):
        return list(other)
    elif isinstance(other, list):
        return other
    elif other is None:
        return []
    return [other]

def to_set(other: Agent | CloseData | int):
    """ converts a single object/id, set ot list of things to a set of ids

        Args:
            the_set (set): set, list or single item

        Returns:
            set of things
        """
    if isinstance(other, list):
        return set(other)
    elif isinstance(other, set):
        return other
    elif other is None:
        return set()
    return {to_id(other)}


def to_id(other: Agent | CloseData | int):
    """converts item passed to an agent id

    Args:
        other (Agent | CloseData | int): The agent

    Returns:
        id: The agent id
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
    """converts the item passed to an agent

    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data

    Returns:
        agent | None: The agent or None
    """    
    py_object = other
    if isinstance(other, Agent):
        py_object = other
    elif isinstance(other, CloseData):
        py_object = other.py_object
    elif isinstance(other, SpawnData):
        py_object = other.py_object
    else:
        # should return space object or grid object
        py_object = Agent.get(other)
    return py_object


def object_exists(so_id):
    """check the engine to see if the item exists

    Args:
        so_id (agent): agent like data converted to id internally

    Returns:
        bool: if the object exists in the engine
    """    
    so_id = to_id(so_id)
    return FrameContext.context.sim.space_object_exists(so_id)
    #return eo is not None

def all_objects_exists(the_set):
    """tests to see if all the objects in the set exist

    Args:
        the_set (set): A set, list or single object internally it will assure it is a list

    Returns:
        bool: False if any object does not exist, True if all exist
    """    
    so_ids = to_id_list(the_set)
    for so_id in so_ids:
        if not FrameContext.context.sim.space_object_exists(so_id):
            return False
    return True

def get_data_set_value(id_or_obj, key, index=0):
    object = to_object(id_or_obj)
    if object is not None:
        return object.data_set.get(key, index)
    return None

def set_data_set_value(to_update, key, value, index=0):
    objects = to_object_list(to_set(to_update))
    for object in objects:
        object.data_set.set(key, value, index)

def get_engine_data_set(id_or_obj):
    if isinstance(id_or_obj, SpawnData):
        return id_or_obj.blob
    object = to_object(id_or_obj)
    if object is not None:
        return object.data_set
    return None

# easier to remember function names
def to_blob(id_or_obj):
    """gets the engine dataset of the specified agent

    !!! Note
        Same as to_data_set

    Args:
        id_or_obj (agent): Agent id or object

    Returns:
        data set| None: Returns the data or None if it does not exist
    """    
    return get_engine_data_set(id_or_obj)

def to_data_set(id_or_obj):
    """gets the engine dataset of the specified agent

    !!! Note
        Same as to_data_set

    Args:
        id_or_obj (agent): Agent id or object

    Returns:
        data set| None: Returns the data or None if it does not exist
    """    
    return get_engine_data_set(id_or_obj)

def is_client_id(id):
    """checks if the agent is a client/console id

    Args:
        id (agent): Agent id or object

    Returns:
        bool: 
    """
    id = to_id(id)
    if id is None:
        return False
    return (id & 0x8000000000000000)!=0

def is_space_object_id(id):
    """checks if the agent is a space object id

    Args:
        id (agent): Agent id or object

    Returns:
        bool: true if it is a space object
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x4000000000000000)!=0

def is_grid_object_id(id):
    """checks if the agent is a grid object id

    Args:
        id (agent): Agent id or object

    Returns:
        bool: grid object
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x2000000000000000)!=0

def is_task_id(id):
    """checks if the agent is a task id

    Args:
        id (agent): Agent id or object

    Returns:
        bool: True if the agent is a task
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x0080000000000000)!=0

def is_story_id(id):
    """checks if the agent is a story id

    !!! Note
        Story agent are object not in the engine. e.g. Fleets
    
    Args:
        id (agent): Agent id or object

    Returns:
        bool: True if the agent is a story object 
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x0040000000000000)!=0


def to_engine_object(id_or_obj):
    """converts the agent to get its engine object pointer

    Args:
        id (agent): Agent id or object

    Returns:
        pointer: A C++ pointer to the engine object
    """
    object = to_object(id_or_obj)
    if object is not None:
        eo = object.engine_object
        return eo
    return None


def get_comms_selection(id_or_not):
    """gets the id of the comms selection

    Args:
        id_or_not (agent): agent id or object

    Returns:
        agent id | None: The agent id or None
    """    
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("comms_target_UID",0)
    return None

def get_science_selection(id_or_not):
    """gets the id of the science selection

    Args:
        id_or_not (agent): agent id or object

    Returns:
        agent id | None: The agent id or None
    """        
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("science_target_UID",0)
    return None

def get_grid_selection(id_or_not):
    """gets the id of the engineering grid selection

    Args:
        id_or_not (agent): agent id or object

    Returns:
        agent id | None: The agent id or None
    """    
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("grid_selected_UID",0)
    return None

def get_weapons_selection(id_or_not):
    """gets the id of the weapons selection

    Args:
        id_or_not (agent): agent id or object

    Returns:
        agent id | None: The agent id or None
    """        
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("weapon_target_UID",0)
    return None


def set_console_selection(id_or_not, other_id_or_obj, console):
    blob = to_blob(id_or_not)
    other = to_id(other_id_or_obj)
    if other is None:
        other = 0
    if blob is not None:
        blob.set(console, other, 0)


def set_comms_selection(id_or_not, other_id_or_obj):
    """sets the id of the comms selection

    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent
    """    
    set_console_selection(id_or_not, other_id_or_obj, "comms_target_UID")

def set_science_selection(id_or_not, other_id_or_obj):
    """sets the id of the science selection

    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent
    """    

    set_console_selection(id_or_not, other_id_or_obj, "science_target_UID")

def set_grid_selection(id_or_not, other_id_or_obj):
    """sets the id of the engineering grid selection

    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent
    """    
    set_console_selection(id_or_not, other_id_or_obj, "grid_selected_UID")

def set_weapons_selection(id_or_not, other_id_or_obj):
    """sets the id of the weapons selection

    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent
    """    
    set_console_selection(id_or_not, other_id_or_obj, "weapon_target_UID")


def inc_disable_selection(id_or_obj, console):
    _obj = to_object(id_or_obj)
    if _obj is None: return
    cur = _obj.get_inventory_value(console, 0)
    cur += 1
    _obj.set_inventory_value(console,cur)
    blob = to_blob(id_or_obj)
    blob.set(console,0,0)

def inc_disable_weapons_selection(id_or_obj): inc_disable_selection(id_or_obj, "weapon_target_UID")
def inc_disable_science_selection(id_or_obj): inc_disable_selection(id_or_obj, "science_target_UID")
def inc_disable_grid_selection(id_or_obj): inc_disable_selection(id_or_obj, "grid_selected_UID")

def dec_disable_selection(id_or_obj, console):
    _obj = to_object(id_or_obj)
    if _obj is None: return
    cur = _obj.get_inventory_value(console, 0)
    cur -= 1
    _obj.set_inventory_value(console,cur)
    
def dec_disable_weapons_selection(id_or_obj): dec_disable_selection(id_or_obj, "weapon_target_UID")
def dec_disable_science_selection(id_or_obj): dec_disable_selection(id_or_obj, "science_target_UID")
def dec_disable_grid_selection(id_or_obj): dec_disable_selection(id_or_obj, "grid_selected_UID")

def get_side(id_or_obj):
    """gets the side of the agent

    Args:
        id_or_obj (agent): agent id or object

    Returns:
        str|None: the side
    """    
    so = to_object(id_or_obj)
    if so is not None:
        return so.side
    return ""

def random_id(the_set):
    """ get the object from the set provide

        Args:
            the_set (set): a set, list etc. of ids or agents

        Returns:
            id: The id of one of the objects
    """
    if len(the_set)==0:
        return None
    return to_id(choice(tuple(the_set)))



def random_object(the_set):
    """ get the object from the set provide

        Args:
            the_set (set): a set, list etc. of ids or agents

        Returns:
            agent: The one of the objects

    """
    if len(the_set)==0:
        return None
    return to_object(choice(tuple(the_set)))



def random_object_list(the_set, count=1):
    """get a list of objects selected randomly from the set provided

        Args: 
            the_set (set): Set of Ids
            count (int): The number of objects to pick

        Returns:
            list: A list of Agent
        """
    rand_id_list = choices(tuple(the_set), count)
    return [Agent.get(x) for x in rand_id_list]

def safe_int(s, defa=0):
    """gets an integer or None for the passed data

    Args:
        s (str): The source assumed str, but could also be a number
        defa (int, optional): What to return of cannot get an integer. Defaults to 0.

    Returns:
        int: the integer or the default
    """    
    if s is None:
        return defa
    if s.isdigit():
        return int(s)
    return defa
