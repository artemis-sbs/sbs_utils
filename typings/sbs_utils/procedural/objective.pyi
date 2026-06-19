from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.procedural.modifiers import ModifierHandler
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import TickDispatcher
def awaitable (func):
    ...
def brains_run_all (tick_task):
    """Run all agent brains for the current tick.
    
    Iterates every agent with a ``__BRAIN__`` inventory entry and calls
    ``brain.run()``. Re-entrant calls are suppressed with a guard flag.
    Agents whose ``Agent.get`` returns ``None`` are silently skipped.
    
    Args:
        tick_task: The tick task or event that triggered this run."""
def extra_scan_sources_run_all (tick_task: sbs_utils.tickdispatcher.TickTask):
    """Push extra scan source IDs to all scanners that have them linked.
    
    Called each tick by the objective system. Computes a CRC of the linked
    extra scan sources per scanner and skips the update if unchanged, reducing
    network traffic.
    
    Args:
        tick_task (TickTask): The tick task that triggered this run."""
def game_end_condition_add (promise, message, is_win, music=None, signal=None) -> int:
    """Register a promise that ends the game when it resolves.
    
    Args:
        promise (Promise): Resolving this promise triggers the end condition.
        message (str): Message displayed on the results screen.
        is_win (bool): ``True`` for a victory, ``False`` for a defeat.
        music (str, optional): Music file to play at end. Defaults to None
            (uses the default victory/failure track).
        signal (str, optional): Signal to emit instead of
            ``"show_game_results"``. Defaults to None.
    
    Returns:
        int: Handle ID that can be passed to ``game_end_condition_remove``."""
def game_end_condition_remove (id):
    """Remove a registered game end condition.
    
    Args:
        id (int): Handle returned by ``game_end_condition_add``."""
def game_end_run_all (tt):
    """Poll all registered game end conditions and trigger the end screen if any resolve.
    
    Args:
        tt (Task): Tick task (unused)."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_story_id ():
    ...
def has_link_to (link_source, link_name: str, link_target) -> bool:
    """Return whether a source agent has a specific link to a target.
    
    Args:
        link_source (Agent | int): The agent ID or object hosting the link.
        link_name (str): The link key name.
        link_target (Agent | int): The target agent ID or object to check.
    
    Returns:
        bool: ``True`` if the link from source to target exists."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def objective_add (agent_id_or_set, label, data=None, client_id=0):
    """Add an objective label to one or more agents.
    
    ``label`` may be a label name, a Label object, a dict with ``"label"`` and
    ``"data"`` keys, or a list of any of these. One ``Objective`` is created
    per (agent, label) pair.
    
    Args:
        agent_id_or_set (Agent | int | set[Agent | int]): Agent(s) to attach
            the objective to.
        label (str | Label | dict | list): The objective label(s) to run.
        data (dict, optional): Variables passed into the objective label.
            Defaults to None.
        client_id (int, optional): Console client ID (reserved for future use).
            Defaults to 0.
    
    Returns:
        Objective | list[Objective]: A single Objective when exactly one is
            created, otherwise a list."""
def objective_clear (agent_id_or_set):
    """Remove all active objectives from one or more agents.
    
    Args:
        agent_id_or_set (Agent | int | set[Agent | int]): Agent(s) whose
            objectives should be cleared."""
def objective_extends (label, data=None):
    """Run an objective label as a sub-task of the current task.
    
    Args:
        label (str | Label): The label to execute.
        data (dict, optional): Variables to pass into the sub-task. Defaults to
            None.
    
    Returns:
        MastAsyncTask: The scheduled sub-task."""
def objective_schedule ():
    """Ensure the background tick task that drives objectives is running."""
def objectives_run_all (tick_task):
    """Poll every active ``OBJECTIVE_RUN`` objective, removing any whose agent no longer exists.
    
    Args:
        tick_task (Task): Tick task (unused)."""
def objectives_run_everything (tick_task):
    """Run one slice of the per-tick work: objectives, brains, scan sources, or game-end checks.
    
    Work is spread across three alternating states to avoid all processing
    happening in the same tick. ``tick_task.state`` selects which slice runs.
    
    Args:
        tick_task (Task): The repeating tick task — ``state`` is read and
            updated each call."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """Schedule a sub-task under the current task starting at the given label.
    
    Sub-tasks share lifecycle with the parent task.
    
    Args:
        label (str | Label): The label to start the sub-task at.
        data (dict, optional): Initial sub-task variables. Defaults to None.
        var (str, optional): Variable name to store the created sub-task.
            Defaults to None.
    
    Returns:
        MastAsyncTask: The sub-task created, or None outside a task context."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
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
