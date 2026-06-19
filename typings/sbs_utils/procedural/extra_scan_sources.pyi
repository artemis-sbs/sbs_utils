from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.tickdispatcher import TickTask
def extra_scan_sources_run_all (tick_task: sbs_utils.tickdispatcher.TickTask):
    """Push extra scan source IDs to all scanners that have them linked.
    
    Called each tick by the objective system. Computes a CRC of the linked
    extra scan sources per scanner and skips the update if unchanged, reducing
    network traffic.
    
    Args:
        tick_task (TickTask): The tick task that triggered this run."""
def extra_scan_sources_schedule ():
    """Schedule the extra scan sources tick task via the objective system."""
def follow_route_select_science (origin_id, selected_id):
    """Programmatically fire the science selection route as if the player made a selection.
    
    Args:
        origin_id (Agent | int): The player ship agent ID or object.
        selected_id (Agent | int): The target space object agent ID or object."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
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
def to_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
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
