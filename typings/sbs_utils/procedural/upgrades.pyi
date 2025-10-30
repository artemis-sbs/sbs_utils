from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import TickDispatcher
def add_role (set_holder, role):
    """Add a role to an agent or a set of agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_story_id ():
    ...
def has_link_to (link_source, link_name: str, link_target):
    """check if target and source are linked to for the given key
    
    Args:
        link_source (Agent | int): The agent or id hosting the link
        link_name (str): The key/name of the inventory item
    
    Returns:
        set[int]: The set of linked ids"""
def linked_to (link_source, link_name: str):
    """Get the set of ids that the source is linked to for the given key.
    
    Args:
        link_source (Agent | int): The agent or id to check
        link_name (str): The key/name of the inventory item
    Returns:
        set[int]: The set of linked ids"""
def objectives_run_all (tick_task):
    ...
def remove_role (agents, role):
    """Remove a role from an agent or a set of agents.a
    
    Args:
        agents (Agent | int | set[Agent | int]): An agent or ID or a set of agents or IDs.
        role (str): The role to add."""
def role (role: str):
    """Returns a set of all the agents with a given role as a set of IDs.
    
    Args:
        role (str): The role.
    
    Returns:
        set[int]: a set of agent IDs."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts a single object/id, set or list of things to a set of ids
    Args:
        other (Agent | CloseData | int | set[Agent | int] | list[Agent | int]): The agent or id or set.
    Returns:
        set[Agent | CloseData | int]: A set containing whatever was passed in."""
def unlink (set_holder, link_name: str, set_to):
    """Removes the link between things
    
    Args:
        set_holder (Agent | int | set[Agent | int]): An agent or set of agents (ids or objects)
        link_name (str): Link name
        set_to (Agent | int | set[Agent | int]): The agent or set of agents (ids or objects) to add a link to"""
def upgrade_add (agent_id_or_set, label, data=None, client_id=0, activate=False):
    ...
def upgrade_remove_for_agent (agent):
    ...
def upgrade_schedule ():
    ...
class Upgrade(Agent):
    """class Upgrade"""
    def __init__ (self, agent_id, label, data, client_id):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def activate (self):
        ...
    def clear ():
        ...
    def deactivate (self):
        ...
    def discard (self):
        ...
    @property
    def done (self):
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def remove_id (id):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    @property
    def result (self):
        ...
    @result.setter
    def result (self, res):
        ...
