from sbs_utils.agent import Agent
def get_face (ship_id):
    """Returns a face string for a specified ID
    
    Args:
        ship_id (Agent | int): The id of the ship/object
    
    Returns:
        str: A Face string"""
def get_story_id ():
    ...
def is_space_object_id (id):
    """Return whether an ID belongs to a space object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the space-object bit (0x4000…) is set."""
def lifeform_init (self, name, face, roles, host=None, comms_id=None, path=None, title_color='green', message_color='white'):
    """Initialise an existing Agent as a lifeform (in-place version of ``lifeform_spawn``).
    
    Args:
        self (Agent): The agent to initialise.
        name (str): Display name of the lifeform.
        face (str): Face image key.
        roles (str): Comma-separated roles to assign.
        host (Agent | int, optional): Space object the lifeform boards.
            Defaults to None.
        comms_id (str, optional): Unused. Defaults to None.
        path (str, optional): Comms route path. Defaults to None.
        title_color (str, optional): Color of the comms title line. Defaults
            to ``"green"``.
        message_color (str, optional): Color of the comms message text.
            Defaults to ``"white"``."""
def lifeform_set_path (lifeform, path=None):
    """Set the comms route path for a lifeform.
    
    Clears the ``comms_badge`` role when ``path`` is ``None``, and adds it
    when a path is set.
    
    Args:
        lifeform (Agent | int): The lifeform agent or its ID.
        path (str, optional): The comms route path. Defaults to None (clears)."""
def lifeform_spawn (name, face, roles, host=None, comms_id=None, path=None, title_color='green', message_color='white'):
    """Create a new Agent and initialise it as a lifeform.
    
    Args:
        name (str): Display name of the lifeform.
        face (str): Face image key.
        roles (str): Comma-separated roles to assign (e.g. ``"crew,medic"``).
        host (Agent | int, optional): Space object the lifeform boards.
            Defaults to None.
        comms_id (str, optional): Unused. Defaults to None.
        path (str, optional): Comms route path for this lifeform. Defaults to
            None.
        title_color (str, optional): Color of the comms title line. Defaults
            to ``"green"``.
        message_color (str, optional): Color of the comms message text.
            Defaults to ``"white"``.
    
    Returns:
        Agent: The newly created lifeform agent."""
def lifeform_transfer (lifeform, new_host):
    """Move a lifeform to a new host space object, emitting ``lifeform_transferred``.
    
    Unlinks from the old host (if any) and links to the new one. If
    ``new_host`` is not a space object ID the lifeform gains the
    ``"ultra_beam"`` role instead.
    
    Args:
        lifeform (Agent | int): The lifeform agent or its ID.
        new_host (Agent | int): The new host space object or its ID."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def set_face (ship_id, face):
    """Sets a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string"""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
