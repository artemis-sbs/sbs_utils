from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
def all_objects_exists (the_set):
    """tests to see if all the objects in the set exist
    
    Args:
        the_set (set): A set, list or single object internally it will assure it is a list
    
    Returns:
        bool: False if any object does not exist, True if all exist"""
def are_variables_defined (keys):
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
    """gets the id of the comms selection
    
    Args:
        id_or_not (agent): agent id or object
    
    Returns:
        agent id | None: The agent id or None"""
def get_crew (id_or_obj):
    """get the race of the specified agent
        race by default is the side from ship_data
    
    Args:
        id_or_obj (agent): an agent id or object
    
    Returns:
        str: The race of the object or None"""
def get_data_set_value (id_or_obj, key, index=0):
    ...
def get_engine_data_set (id_or_obj):
    ...
def get_grid_selection (id_or_not):
    """gets the id of the engineering grid selection
    
    Args:
        id_or_not (agent): agent id or object
    
    Returns:
        agent id | None: The agent id or None"""
def get_origin (id_or_obj):
    """get the race of the specified agent
        race by default is the side from ship_data
    
    Args:
        id_or_obj (agent): an agent id or object
    
    Returns:
        str: The race of the object or None"""
def get_race (id_or_obj):
    """get the race of the specified agent
        race by default is the side from ship_data
    
    Args:
        id_or_obj (agent): an agent id or object
    
    Returns:
        str: The race of the object or None"""
def get_science_selection (id_or_not):
    """gets the id of the science selection
    
    Args:
        id_or_not (agent): agent id or object
    
    Returns:
        agent id | None: The agent id or None"""
def get_side (id_or_obj):
    """gets the side of the agent
    
    Args:
        id_or_obj (agent): agent id or object
    
    Returns:
        str|None: the side"""
def get_side_display (id_or_obj):
    """gets the side of the agent
    
    Args:
        id_or_obj (agent): agent id or object
    
    Returns:
        str|None: the side"""
def get_weapons_selection (id_or_not):
    """gets the id of the weapons selection
    
    Args:
        id_or_not (agent): agent id or object
    
    Returns:
        agent id | None: The agent id or None"""
def inc_disable_grid_selection (id_or_obj):
    ...
def inc_disable_science_selection (id_or_obj):
    ...
def inc_disable_selection (id_or_obj, console):
    ...
def inc_disable_weapons_selection (id_or_obj):
    ...
def is_client_id (id):
    """checks if the agent is a client/console id
    
    Args:
        id (agent): Agent id or object
    
    Returns:
        bool: """
def is_grid_object_id (id):
    """checks if the agent is a grid object id
    
    Args:
        id (agent): Agent id or object
    
    Returns:
        bool: grid object"""
def is_space_object_id (id):
    """checks if the agent is a space object id
    
    Args:
        id (agent): Agent id or object
    
    Returns:
        bool: true if it is a space object"""
def is_story_id (id):
    """checks if the agent is a story id
    
    !!! Note
        Story agent are object not in the engine. e.g. Fleets
    
    Args:
        id (agent): Agent id or object
    
    Returns:
        bool: True if the agent is a story object """
def is_task_id (id):
    """checks if the agent is a task id
    
    Args:
        id (agent): Agent id or object
    
    Returns:
        bool: True if the agent is a task"""
def object_exists (so_id):
    """check the engine to see if the item exists
    
    Args:
        so_id (agent): agent like data converted to id internally
    
    Returns:
        bool: if the object exists in the engine"""
def random_id (the_set):
    """get the object from the set provide
    
    Args:
        the_set (set): a set, list etc. of ids or agents
    
    Returns:
        id: The id of one of the objects"""
def random_object (the_set):
    """get the object from the set provide
    
    Args:
        the_set (set): a set, list etc. of ids or agents
    
    Returns:
        agent: The one of the objects"""
def random_object_list (the_set, count=1):
    """get a list of objects selected randomly from the set provided
    
    Args:
        the_set (set): Set of Ids
        count (int): The number of objects to pick
    
    Returns:
        list: A list of Agent"""
def safe_int (s, defa=0):
    """gets an integer or None for the passed data
    
    Args:
        s (str): The source assumed str, but could also be a number
        defa (int, optional): What to return of cannot get an integer. Defaults to 0.
    
    Returns:
        int: the integer or the default"""
def set_comms_selection (id_or_not, other_id_or_obj):
    """sets the id of the comms selection
    
    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent"""
def set_console_selection (id_or_not, other_id_or_obj, console):
    ...
def set_data_set_value (to_update, key, value, index=0):
    ...
def set_grid_selection (id_or_not, other_id_or_obj):
    """sets the id of the engineering grid selection
    
    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent"""
def set_science_selection (id_or_not, other_id_or_obj):
    """sets the id of the science selection
    
    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent"""
def set_weapons_selection (id_or_not, other_id_or_obj):
    """sets the id of the weapons selection
    
    Args:
        id_or_not (agent): agent id or object of the player ship
        other_id_or_obj: The agent id or object target agent"""
def to_blob (id_or_obj):
    """gets the engine dataset of the specified agent
    
    !!! Note
        Same as to_data_set
    
    Args:
        id_or_obj (agent): Agent id or object
    
    Returns:
        data set| None: Returns the data or None if it does not exist"""
def to_client_object (other: sbs_utils.agent.Agent | int):
    """converts the item passed to an gui client
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def to_data_set (id_or_obj):
    """gets the engine dataset of the specified agent
    
    !!! Note
        Same as to_data_set
    
    Args:
        id_or_obj (agent): Agent id or object
    
    Returns:
        data set| None: Returns the data or None if it does not exist"""
def to_engine_object (id_or_obj):
    """converts the agent to get its engine object pointer
    
    Args:
        id (agent): Agent id or object
    
    Returns:
        pointer: A C++ pointer to the engine object"""
def to_grid_object (other: sbs_utils.agent.Agent | int):
    """converts the item passed to an gui client
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def to_id_list (the_set):
    """converts a set to a list of ids
    
    Args:
        the_set (set|list): a set of agents or ids
    
    Returns:
        list: of agent ids"""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a list
    
    Args:
        the_set (set|list): a set of agent ids
    
    Returns:
        list: containing whatever was passed in"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def to_object_list (the_set):
    """to_object_list
    converts a set to a list of objects
    
    Args:
        the_set (set|list): a set of agent ids
    
    Returns:
        list: of Agents"""
def to_py_object_list (the_set):
    """to_py_object_list
    
    converts a set of ids to a set of objects
    
    Returns:
        list Agent"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a set of ids
    
    Args:
        the_set (set): set, list or single item
    
    Returns:
        set of things"""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """converts the item passed to an gui client
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
