from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.tickdispatcher import TickTask
def extra_scan_sources_run_all (tick_task: sbs_utils.tickdispatcher.TickTask):
    ...
def extra_scan_sources_schedule ():
    ...
def follow_route_select_science (origin_id, selected_id):
    """cause the science selection route to execute
    
    Args:
        origin_id (agent): The agent id of the player ship
        selected_id (agent): The agent id of the target space object"""
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def has_link_to (link_source, link_name: str, link_target):
    """check if target and source are linked to for the given key
    
    Args:
        link_source (agent): The agent hosting the link
        link_name (str): The key/name of the inventory item
    
    Returns:
        set | None: set of ids"""
def link (set_holder, link, set_to):
    """create a link between agents
    
    Args:
        set_holder (agent | agent set): The host (set) of the link
        link (str): The link name
        set_to (agent|agent set): The items to link to"""
def linked_to (link_source, link_name: str):
    """get the set that inventor the source is linked to for the given key
    
    Args:
        link_source(id): The id object to check
        link_name (str): The key/name of the inventory item
        set | None: set of ids"""
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def to_data_set (id_or_obj):
    """gets the engine dataset of the specified agent
    
    !!! Note
        Same as to_data_set
    
    Args:
        id_or_obj (agent): Agent id or object
    
    Returns:
        data set| None: Returns the data or None if it does not exist"""
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
