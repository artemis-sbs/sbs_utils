from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import TickDispatcher
def add_role (set_holder, role):
    """add a role to a set of agents
    
    Args:
        set_holder (agent set): a set of IDs or
        role (str): The role to add"""
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def get_story_id ():
    ...
def has_link_to (link_source, link_name: str, link_target):
    """check if target and source are linked to for the given key
    
    Args:
        link_source (agent): The agent hosting the link
        link_name (str): The key/name of the inventory item
    
    Returns:
        set | None: set of ids"""
def linked_to (link_source, link_name: str):
    """get the set that inventor the source is linked to for the given key
    
    Args:
        link_source(id): The id object to check
        link_name (str): The key/name of the inventory item
        set | None: set of ids"""
def objectives_run_all (tick_task):
    ...
def remove_role (agents, role):
    """remove a role from a set of agents
    
    Args:
        agents (agent set): a set of IDs or
        role (str): The role to add"""
def role (role: str):
    """returns a set of all the agents with a given role.
    
    Args:
        role (str): The role
    
    Returns:
        agent id set: a set of agent IDs"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts a single object/id, set ot list of things to a set of ids
    
    Args:
        the_set (set): set, list or single item
    
    Returns:
        set of things"""
def unlink (set_holder, link, set_to):
    """removes the link between things
    
    Args:
        set_holder (agent|agent set): An agent or set of agents (ids or objects)
        link (str): Link name
        set_to (agent|agent set): The agents(s) to add a link to"""
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
