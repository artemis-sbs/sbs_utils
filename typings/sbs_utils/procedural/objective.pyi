from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import TickDispatcher
def awaitable (func):
    ...
def brains_run_all (tick_task):
    ...
def extra_scan_sources_run_all (tick_task: sbs_utils.tickdispatcher.TickTask):
    ...
def game_end_condition_add (promise, message, is_win, music=None, signal=None):
    ...
def game_end_condition_remove (id):
    ...
def game_end_run_all (tt):
    ...
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
def objective_add (agent_id_or_set, label, data=None, client_id=0):
    ...
def objective_clear (agent_id_or_set):
    ...
def objective_extends (*args, **kwargs):
    ...
def objective_schedule ():
    ...
def objectives_run_all (tick_task):
    ...
def objectives_run_everything (tick_task):
    ...
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def signal_emit (name, data=None):
    ...
def sub_task_schedule (*args, **kwargs):
    ...
def to_object_list (the_set):
    """to_object_list
    converts a set to a list of objects
    
    Args:
        the_set (set|list): a set of agent ids
    
    Returns:
        list: of Agents"""
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
class Objective(Agent):
    """class Objective"""
    def __init__ (self, agent, label, data, client_id):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    @property
    def done (self):
        ...
    def force_clear (self):
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
    def run (self):
        ...
    def run_sub_label (self, loc):
        ...
    def stop_and_leave (self, result=<PollResults.FAIL_END: 100>):
        ...
