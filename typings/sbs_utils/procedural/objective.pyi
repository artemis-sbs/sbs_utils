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
def game_end_condition_add (promise, message, is_win, music=None, signal=None) -> int:
    """Add a game end condition.
    Args:
        promise (Promise): The promise that must be completed for the game to end.
        message (str): The message to display on game end.
        is_win (bool): Does the game end with a win or loss?
        music (str, optional): The music to play on game end. Default is None.
        signal (str, optional): The signal to emit when the game ends.
    Returns:
        int: The id of the game end promise. Used to remove the game end condition after adding it."""
def game_end_condition_remove (id):
    """Remove a game end condition.
    Args:
        id (int): The id of the game end condition."""
def game_end_run_all (tt):
    """Check if any of the game end conditions have been met.
    Args:
        tt (Task): The tick task. Not used yet."""
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
def link (set_holder, link_name: str, set_to):
    """Create a link between agents
    
    Args:
        set_holder (Agent | int | set[Agent | int]): The host (agent, id, or set) of the link
        link_name (str): The link name
        set_to (Agent | set[Agent]): The items to link to"""
def linked_to (link_source, link_name: str):
    """Get the set of ids that the source is linked to for the given key.
    
    Args:
        link_source (Agent | int): The agent or id to check
        link_name (str): The key/name of the inventory item
    Returns:
        set[int]: The set of linked ids"""
def objective_add (agent_id_or_set, label, data=None, client_id=0):
    """Add an objective to the agent or agents
    Args:
        agent_id_or_set (Agent | int | set[Agent | int]): The agent or id or set of agents or ids.
        label (str | Label): The objective label to add.
        data (dict, optional): The data associated with the objective.
        client_id (int, optional): The client id for this objective (may not be used?)
    Returns:
        list[Objective | int]: The list of objectives added. Objectives for multiple agents count as separate objectives."""
def objective_clear (agent_id_or_set):
    """Clear all objectives from the agent or agents.
    Args:
        agent_id_or_set (Agent | int | set[Agent | int]): The agent or id or set of agents or ids."""
def objective_extends (label, data=None):
    """Add an objective to the current task as a subtask.
    Args:
        label (str | Label): The label to add.
        data (dict, optional): The data to associate with the objective. Default is None.
    Returns:
        MastAsyncTask: The task"""
def objective_schedule ():
    """Schedule a simple task tick that runs all objective tasks."""
def objectives_run_all (tick_task):
    """Run all objective labels.
    Args:
        tick_task (Task): The task. (Not used)"""
def objectives_run_everything (tick_task):
    """Check objectives, brains, scan sources, and game end conditions. Which promises are checked is depenent on the value of `tick_task.state`.
    This spreads out the calculation times across multiple runs instead of everything happening at the same time. The tick_task's `state` is updated.
    Args:
        tick_task (Task): The current task."""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def signal_emit (name, data=None):
    """Emit a signal to trigger all instances of the signal route to run.
    Args:
        name (str): The name of the signal.
        data (dict): The data to provide to the signal route."""
def sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def to_object_list (the_set):
    """Converts a set to a list of objects
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[Agent]: A list of Agent objects"""
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
class Objective(Agent):
    """class Objective"""
    def __init__ (self, agent, label, data, client_id):
        """Create an Objective.
        Args:
            agent (Agent | int): The agent or id for this objective
            label (str | Label): The objective label to run
            data (dict): Data to associate with this objective. May not be used.
            client_id (int): The client ID for this objective. May not be used."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    @property
    def done (self) -> bool:
        """Is the objective completed?
        Returns:
            bool: True if the objective is complete."""
    def force_clear (self):
        """Clear this objective from its agent and undesignates it as an objective."""
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
    def result (self) -> sbs_utils.mast.pollresults.PollResults:
        """Get the result of the objective.
        Returns:
            PollResults: The result."""
    @result.setter
    def result (self, res):
        """Get the result of the objective.
        Returns:
            PollResults: The result."""
    def run (self):
        """Run the objective label."""
    def run_sub_label (self, loc):
        """Run the sublabel with the specified index.
        Args:
            loc (int): The index of the sublabel.
        Returns:
            PollResults: The result of the sublabel task."""
    def stop_and_leave (self, result=<PollResults.FAIL_END: 100>):
        """Stop the label run with a result.
        Args:
            result (PollResults): The result of the objective label."""
