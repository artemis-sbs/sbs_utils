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
    """Checks if the agent is a space object id
    Args:
        id (Agent | int): Agent id or object
    Returns:
        bool: True if it is a space object"""
def lifeform_init (self, name, face, roles, host=None, comms_id=None, path=None, title_color='green', message_color='white'):
    """Initialize a lifeform.
    Args:
        name (str): The name of the lifeform
        face (str): The face string of the lifeform.
        roles (str): A comma-separated list of roles assigned to the lifeform.
        host (Agent | int, optional): The agent or id of the host space object. Default is None.
        comms_id (str, optional): The comms_id of the lifeform (unused). Default is None.
        path (str, optional): The comms path to use to communicate with this lifeform. Default is None.
        title_color (str, optional): The color of the title of comms messages with this lifeform. Default is "green".
        message_color (str, optional): The color of the message of comms messages with this lifeform. Default is "white"."""
def lifeform_set_path (lifeform, path=None):
    """Set the comms path of the lifeform. If the path is None, then the `comms_badge` role is removed from the lifeform.
    Args:
        lifeform (Agent | int): The agent or id of the lifeform
        path (str, optional): The new path to use. Default is None."""
def lifeform_spawn (name, face, roles, host=None, comms_id=None, path=None, title_color='green', message_color='white'):
    """Spawn a new Agent and initialize it as a lifeform.
    Args:
        name (str): The name of the lifeform.
        face (str): The face string of the lifeform.
        roles (str): A comma-separated list of roles assigned to the lifeform.
        host (Agent | int, optional): The agent or id of the host space object. Default is None.
        comms_id (str, optional): The comms_id of the lifeform (unused). Default is None.
        path (str, optional): The comms path to use to communicate with this lifeform. Default is None.
        title_color (str, optional): The color of the title of comms messages with this lifeform. Default is "green".
        message_color (str, optional): The color of the message of comms messages with this lifeform. Default is "white"."""
def lifeform_transfer (lifeform, new_host):
    """Assign a new host to this lifeform.
    Args:
        lifeform (Agent | int): The agent or id of the lifeform.
        new_host (Agent | int): The agent or id of the new host."""
def link (set_holder, link_name: str, set_to):
    """Create a link between agents
    
    Args:
        set_holder (Agent | int | set[Agent | int]): The host (agent, id, or set) of the link
        link_name (str): The link name
        set_to (Agent | set[Agent]): The items to link to"""
def set_face (ship_id, face):
    """Sets a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def unlink (set_holder, link_name: str, set_to):
    """Removes the link between things
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or set of agents (ids or objects)
        link_name (str): Link name
        set_to (Agent | int | set[Agent | int]): The agent or set of agents (ids or objects) to add a link to"""
