from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
def all_objects_exists (the_set):
    """Tests to see if all the objects in the set exist
    Args:
        the_set (Agent | int | set[Agent | int] | list[Agent | int]): A set, list or single object internally it will assure it is a list
    Returns:
        bool: False if any object does not exist, True if all exist"""
def are_variables_defined (keys):
    """Check if the provided variable keys are defined in the current task.
    Args:
        keys (str): A comma-separated list of the keys.
    Returns:
        bool: True if all variables are defined, otherwise False."""
def dec_disable_grid_selection (id_or_obj):
    ...
def dec_disable_science_selection (id_or_obj):
    ...
def dec_disable_selection (id_or_obj, console_selected_UID):
    """Decrease the inventory value of the given console's current selection by one and disable the selection.
    Args:
        id_or_obj (Agent | int): The player ship
        console_selected_UID (int): The console."""
def dec_disable_weapons_selection (id_or_obj):
    ...
def get_comms_selection (id_or_not):
    """Gets the id of the comms selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def get_crew (id_or_obj):
    """Get the race of the specified agent
    * Race by default is the side from shipData
    Args:
        id_or_obj (Agent | int): an agent id or object
    Returns:
        str: The race of the object or None"""
def get_data_set_value (id_or_obj, key, index=0):
    """Get the data set (blob) value for the object with the given key.
    Args:
        id_or_obj (Agent | int): The agent or id.
        key (str): The data set key
        index (int, optional): The index of the data set value
    Returns:
        any: The value associated with the key and index."""
def get_engine_data_set (id_or_obj):
    """Get the data set (blob) for the id or object.
    Args:
        id_or_obj (Agent | SpawnData | int)
    Returns:
        data_set: The data set for the object."""
def get_grid_selection (id_or_not):
    """Gets the id of the engineering grid selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def get_origin (id_or_obj):
    """Get the race of the specified agent
    * Origin by default is the side from shipData
    Args:
        id_or_obj (Agent | int): an agent id or object
    Returns:
        str: The race of the object or None"""
def get_race (id_or_obj):
    """Get the race of the specified agent
    * Race by default is the side from shipData
    Args:
        id_or_obj (Agent | int): an agent id or object
    Returns:
        str: The race of the object or None"""
def get_science_selection (id_or_not):
    """Gets the id of the science selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def get_side (id_or_obj):
    """Gets the side of the agent
    Args:
        id_or_obj (Agent | int): agent id or object
    Returns:
        str|None: the side"""
def get_side_display (id_or_obj):
    """Gets the side of the agent
    Args:
        id_or_obj (Agent | int): agent id or object
    Returns:
        str|None: the side"""
def get_weapons_selection (id_or_not):
    """Gets the id of the weapons selection
    Args:
        id_or_not (Agent | int): agent id or object
    Returns:
        int | None: The agent id or None"""
def inc_disable_grid_selection (id_or_obj):
    ...
def inc_disable_science_selection (id_or_obj):
    ...
def inc_disable_selection (id_or_obj, console_selected_UID):
    """Increase the inventory value of the given console's current selection by one and disable the selection.
    Args:
        id_or_obj (Agent | int): The player ship
        console_selected_UID (int): The console."""
def inc_disable_weapons_selection (id_or_obj):
    ...
def is_client_id (id):
    """Checks if the agent is a client/console id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if the agent is a client or console id"""
def is_grid_object_id (id):
    """Checks if the agent is a grid object id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if it is a grid object"""
def is_space_object_id (id):
    """Checks if the agent is a space object id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if it is a space object"""
def is_story_id (id):
    """Checks if the agent is a story id
    !!! Note
    * Story agent are object not in the engine. e.g. Fleets
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if the agent is a story object """
def is_task_id (id):
    """Checks if the agent is a task id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if the agent is a task"""
def object_exists (so_id):
    """Check the engine to see if the item exists
    Args:
        so_id (Agent | int): agent like data converted to id internally
    Returns:
        bool: if the object exists in the engine"""
def random_id (the_set):
    """Get a random id from the set provided
    Args:
        the_set (set[Agent | int]): a set, list etc. of ids or agents
    Returns:
        int: The id of one of the objects"""
def random_object (the_set):
    """Get a random object from the set provided
    Args:
        the_set (set[Agent | int]): a set, list etc. of ids or agents
    Returns:
        Agent: The one of the objects"""
def random_object_list (the_set, count=1):
    """Get a list of objects selected randomly from the set provided
    Args:
        the_set (set[Agent | int]): Set of Ids or agents
        count (int, optional): The number of objects to pick. Default is 1.
    
    Returns:
        list: A list of Agent"""
def safe_int (s, defa=0):
    """Gets an integer or None for the passed data
    Args:
        s (str): The source assumed str, but could also be a number
        defa (int, optional): What to return if the supplied value is not an integer. Default is 0.
    Returns:
        int: the integer or the default"""
def set_comms_selection (id_or_not, other_id_or_obj):
    """Sets the id of the comms selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent."""
def set_console_selection (id_or_not, other_id_or_obj, console):
    """Set the id of the selection for the console and client.
    Args:
        id_or_not (Agent | int): The player ship ID.
        other_id_or_obj (Agent | int): The selected space object.
        console (str): The console for which the object is selected."""
def set_data_set_value (to_update, key, value, index=0):
    """Set the data set (blob) value for the objects with the given key. If `to_update` is a set or list, sets the data set value for each object.
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The agent or id or set or list.
        key (str): The data set key.
        value (any): The value to assign.
        index (int, optional): The index of the data set value"""
def set_grid_selection (id_or_not, other_id_or_obj):
    """Sets the id of the engineering grid selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent."""
def set_science_selection (id_or_not, other_id_or_obj):
    """Sets the id of the science selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent."""
def set_weapons_selection (id_or_not, other_id_or_obj):
    """Sets the id of the weapons selection.
    Args:
        id_or_not (Agent | int): agent id or object of the player ship.
        other_id_or_obj (Agent | int): The agent id or object target agent."""
def to_blob (id_or_obj):
    """Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_data_set
    Args:
        id_or_obj (Agent | int): Agent id or object
    Returns:
        data_set | None: Returns the data or None if it does not exist"""
def to_client_object (other: sbs_utils.agent.Agent | int):
    """Converts the item passed to an gui client
    ??? note
    * Retrun of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def to_data_set (id_or_obj):
    """Gets the engine dataset of the specified agent
    !!! Note
    * Same as to_blob
    Args:
        id_or_obj (Agent | int): Agent id or object
    Returns:
        data_set | None: Returns the data or None if it does not exist"""
def to_engine_object (id_or_obj):
    """Converts the agent to get its engine object pointer
    Args:
        id (Agent | int): Agent id or object
    Returns:
        pointer: A C++ pointer to the engine object"""
def to_grid_object (other: sbs_utils.agent.Agent | int):
    """Converts the item passed to an gui client
    ??? note
    * Retrun of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_id_list (the_set):
    """Converts a set to a list of ids
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[int]: A list of agent ids"""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a list
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        list[Agent | CloseData | int]: A list containing whatever was passed in."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def to_object_list (the_set):
    """Converts a set to a list of objects
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[Agent]: A list of Agent objects"""
def to_py_object_list (the_set):
    """Converts a set of ids to a set of objects
    Args:
        the_set (set[int]): A set of IDs
    Returns:
        list[Agent]"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a set of ids
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        set[Agent | CloseData | int]: A set containing whatever was passed in."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Converts the item passed to an gui client
    ??? note
    * Retrun of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
