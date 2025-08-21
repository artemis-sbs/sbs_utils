from sbs_utils.agent import Agent
def get_face (ship_id):
    """returns a face string for a specified ID
    
    Args:
        ship_id (agent): The id of the ship/object
    
    Returns:
        str: A Face string"""
def get_story_id ():
    ...
def is_space_object_id (id):
    """checks if the agent is a space object id
    
    Args:
        id (agent): Agent id or object
    
    Returns:
        bool: true if it is a space object"""
def lifeform_init (self, name, face, roles, host=None, comms_id=None, path=None, title_color='green', message_color='white'):
    ...
def lifeform_set_path (lifeform, path=None):
    ...
def lifeform_spawn (name, face, roles, host=None, comms_id=None, path=None, title_color='green', message_color='white'):
    ...
def lifeform_transfer (lifeform, new_host):
    ...
def link (set_holder, link, set_to):
    """create a link between agents
    
    Args:
        set_holder (agent | agent set): The host (set) of the link
        link (str): The link name
        set_to (agent|agent set): The items to link to"""
def set_face (ship_id, face):
    """sets a face string for a specified ID
    
    Args:
        ship_id (agent): The id of the ship/object
        face (str): A Face string"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def unlink (set_holder, link, set_to):
    """removes the link between things
    
    Args:
        set_holder (agent|agent set): An agent or set of agents (ids or objects)
        link (str): Link name
        set_to (agent|agent set): The agents(s) to add a link to"""
