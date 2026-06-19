from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.tickdispatcher import TickTask
def _docking_handle_dock_start (player, npc, brain):
    ...
def _docking_handle_docked (player, npc, brain):
    ...
def _docking_handle_docking (player, npc, brain):
    ...
def _docking_handle_undocked (player_id, player, pairs):
    ...
def _docking_handle_undocking (player, npc, brain):
    ...
def _docking_run_task (player, npc, brain, inner_label):
    ...
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Return the closest object to a source from a candidate set.
    
    Args:
        the_ship (Agent | int | Vec3): Reference agent ID, object, or position.
        the_set (Agent | int | set[Agent | int]): Candidate agent(s) to test.
        max_dist (float, optional): Maximum distance to consider. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``.
            Defaults to None.
    
    Returns:
        CloseData | None: Distance data for the closest match, or ``None`` if
            no candidates qualify."""
def docking_run_all (tick_task):
    """Process docking state for all registered player/NPC pairs.
    
    Called each tick. Handles undocked proximity detection, docking approach,
    dock_start handshake, docked refit/throttle, and undocking. Cleans up
    stale pairs where the player or NPC no longer exists.
    
    Args:
        tick_task (TickTask | event): Tick task or event triggering this run."""
def docking_schedule ():
    """Schedule the docking tick task (runs every 1 second) if not already running."""
def docking_set_docking_logic (player_set, npc_set, label, data=None):
    """Register docking logic between a set of players and a set of NPCs.
    
    For each (player, NPC) pair, associates ``label`` as the brain that drives
    docking state transitions (``enable``, ``docking``, ``docked``,
    ``undocking``, ``refit``, ``throttle`` inline sections). Automatically
    schedules the docking tick task.
    
    Args:
        player_set (int | set): Player ship agent ID(s) or object(s).
        npc_set (int | set): NPC agent ID(s) or object(s) to dock with.
        label (Label): MAST label with docking inline sub-labels.
        data (dict, optional): Variables passed to docking tasks. Defaults to
            None."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
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
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
class _DockingBrain(object):
    """class _DockingBrain"""
    def __init__ (self, label, data):
        """Initialize self.  See help(type(self)) for accurate signature."""
