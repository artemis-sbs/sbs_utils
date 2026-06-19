from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
def all_objects_exists (the_set):
    """Return whether every object in a collection exists in the simulation.
    
    Args:
        the_set (Agent | int | set[Agent | int] | list[Agent | int]): One or
            more agent IDs or objects.
    
    Returns:
        bool: ``True`` if all objects exist; ``False`` if any is missing."""
def are_variables_defined (keys):
    """Return whether all named variables are defined in the current MAST task.
    
    Args:
        keys (str): Comma-separated variable names to check.
    
    Returns:
        bool: ``True`` if every key is defined in the current task scope."""
def dec_disable_grid_selection (id_or_obj):
    ...
def dec_disable_science_selection (id_or_obj):
    ...
def dec_disable_selection (id_or_obj, console_selected_UID):
    """Decrement the disable-count for a console selection.
    
    Reverses an ``inc_disable_selection`` call. When the counter reaches zero
    the console is no longer suppressed.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"weapon_target_UID"``)."""
def dec_disable_weapons_selection (id_or_obj):
    ...
def get_comms_selection (id_or_not):
    """Return the ID of the object currently selected on the comms console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_crew (id_or_obj):
    """Get the crew string of a space object (defaults to the side from shipData).
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The crew string, or ``""`` if the object does not exist."""
def get_data_set_value (id_or_obj, key, index=0):
    """Get a value from the engine data-set (blob) of a space or grid object.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
    
    Returns:
        any: The stored value, or ``None`` if the object or key is not found."""
def get_engine_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID, object, or SpawnData.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if not found."""
def get_grid_selection (id_or_not):
    """Return the ID of the object currently selected on the engineering grid console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_origin (id_or_obj):
    """Get the origin string of a space object (defaults to the side from shipData).
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The origin string, or ``""`` if the object does not exist."""
def get_race (id_or_obj):
    """Return the race string of a space object (defaults to side from shipData).
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The race string, or ``""`` if the object does not exist."""
def get_science_selection (id_or_not):
    """Return the ID of the object currently selected on the science console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_side (id_or_obj):
    """Return the side string of an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The side string, or ``""`` if the object does not exist."""
def get_side_display (id_or_obj):
    """Return the display name of an agent's side.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The side display string, or ``""`` if the object does not exist."""
def get_weapons_selection (id_or_not):
    """Return the ID of the object currently selected on the weapons console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def inc_disable_grid_selection (id_or_obj):
    ...
def inc_disable_science_selection (id_or_obj):
    ...
def inc_disable_selection (id_or_obj, console_selected_UID):
    """Increment the disable-count for a console selection and clear it.
    
    Increments an internal counter tracking how many callers have suppressed
    the selection for this console, then zeroes the console's selected UID
    in the blob so the console has no active target.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"weapon_target_UID"``)."""
def inc_disable_weapons_selection (id_or_obj):
    ...
def is_client_id (id):
    """Return whether an ID belongs to a client (player console) agent.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the client-console bit (0x8000…) is set."""
def is_grid_object_id (id):
    """Return whether an ID belongs to an engineering-grid object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the grid-object bit (0x2000…) is set."""
def is_space_object_id (id):
    """Return whether an ID belongs to a space object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the space-object bit (0x4000…) is set."""
def is_story_id (id):
    """Return whether an ID belongs to a story agent (not an engine object, e.g. Fleets).
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the ID has the story-object bit set."""
def is_task_id (id):
    """Return whether an ID belongs to a MAST task.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the task-id bit (0x0080…) is set."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def random_id (the_set):
    """Return the ID of a randomly chosen element from a collection.
    
    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.
    
    Returns:
        int | None: A random agent ID, or ``None`` if the collection is empty."""
def random_object (the_set):
    """Return a randomly chosen agent object from a collection.
    
    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.
    
    Returns:
        Agent | None: A random agent, or ``None`` if the collection is empty."""
def random_object_list (the_set, count=1):
    """Return a list of randomly chosen agent objects from a collection.
    
    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.
        count (int, optional): Number of objects to pick. Defaults to 1.
    
    Returns:
        list[Agent]: Randomly selected agents (may contain duplicates)."""
def safe_int (s, defa=0):
    """Convert a string to an integer, returning a default on failure.
    
    Args:
        s (str | any): The value to convert. Expected to be a string.
        defa (int, optional): Value returned if ``s`` is not a valid integer.
            Defaults to 0.
    
    Returns:
        int: The converted integer, or ``defa``."""
def set_comms_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the comms console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_console_selection (id_or_not, other_id_or_obj, console):
    """Set the selected object for a named console on a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select, or ``0`` to clear.
        console (str): The blob key for the console (e.g. ``"comms_target_UID"``)."""
def set_data_set_value (to_update, key, value, index=0):
    """Set a value in the engine data-set (blob) for one or more space or grid objects.
    
    If ``to_update`` is a set or list, the value is applied to each member.
    
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The
            agent(s) to update.
        key (str): The data-set key.
        value (any): The value to store.
        index (int, optional): The slot index within that key. Defaults to 0."""
def set_grid_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the engineering grid console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_science_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the science console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_weapons_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the weapons console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_client_object (other: sbs_utils.agent.Agent | int):
    """Resolve a client/console ID or Agent to its Agent object.
    
    Returns ``None`` when the ID is not a valid client ID or the agent no
    longer exists.
    
    Args:
        other (Agent | int): Client ID or agent to resolve.
    
    Returns:
        Agent | None: The client agent, or ``None``."""
def to_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_engine_object (id_or_obj):
    """Return the C++ engine-object pointer for an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        pointer | None: The underlying C++ engine-object, or ``None`` if the
            agent does not exist."""
def to_grid_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a GridObject agent.
    
    Returns ``None`` when the ID is not a grid-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The grid-object agent, or ``None``."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_id_list (the_set):
    """Convert a set or list of agents/IDs to a list of integer IDs.
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[int]: Resolved integer IDs; unresolvable items are excluded."""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a list.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        list: A list containing whatever was passed in; ``None`` becomes ``[]``."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_py_object_list (the_set):
    """Convert a set of IDs to a list of Agent objects.
    
    Args:
        the_set (set[int]): A set of agent IDs.
    
    Returns:
        list[Agent]: Agents resolved from the set; items that no longer exist
            are included as ``None``."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).
    
    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The space-object agent, or ``None``."""
def to_space_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of SpaceObject agents (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Space-object agents only; grid/client IDs are excluded."""
