from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.tickdispatcher import TickDispatcher
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
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
def modifier_add (obj_or_id_or_set, key, value, source, flat_add_or_mult=1, duration=None, index=None) -> sbs_utils.procedural.modifiers.Modifier:
    """Add and apply a modifier to a blob value on one or more objects.
    
    ``obj_or_id_or_set`` may be an agent, an ID, a set of IDs, or a side key
    (str) — in which case the modifier is applied to every object on that side.
    
    ``source`` identifies the modifier. Only one modifier per source can be
    active for a given key on a given object. Adding a modifier with an
    existing source overwrites the previous one, making updates easy without
    an explicit remove.
    
    Modifiers are applied in this order:
    Flat (0) — all flat values are summed and added to the base.
    Additive (1) — all additive values are summed, then multiplied by the
    result of the Flat step.
    Multiplicative (2) — all multiplicative values are multiplied together,
    then applied to the result of the Additive step.
    
    Args:
        obj_or_id_or_set (set | int | Agent | str): Object, ID, set of IDs, or
            side key to apply the modifier to.
        key (str): The blob key the modifier should affect.
        value (float): The modifier amount.
        source (str | int): Identifier for this modifier — used to overwrite or
            remove it later.
        flat_add_or_mult (int): Modifier type: 0 = Flat, 1 = Additive
            (default), 2 = Multiplicative.
        duration (float, optional): Seconds before the modifier expires
            automatically. Defaults to None (permanent).
        index (int, optional): Index into a list blob value. ``None`` applies
            to all indices. Ignored for inventory keys. Defaults to None.
    
    Returns:
        Modifier | set[int]: The created ``Modifier`` when exactly one is
            added; otherwise a set of all created modifier IDs.
    
    Example:
        # Base scan range is 1000.
        modifier_add(id, "ship_base_scan_range", 0.2, "Efficiency Module")   # 1200
        modifier_add(id, "ship_base_scan_range", 1000, "Range Extender", 0)  # 2400
        modifier_add(id, "ship_base_scan_range", 0.1, "AI Enhancement")      # 2600
        modifier_add(id, "ship_base_scan_range", -0.5, "Nebula", 2)          # 1300"""
def modifier_remove (obj_or_id_or_set, key_or_modifier, source=None) -> None:
    """Remove a modifier (or all modifiers for a key) from one or more objects.
    
    If ``key_or_modifier`` is a ``Modifier`` object, that specific modifier is
    removed directly and ``obj_or_id_or_set`` is ignored. Otherwise
    ``key_or_modifier`` is treated as a blob key: if ``source`` is given only
    that source's modifier is removed; if ``source`` is ``None`` all modifiers
    for that key are cleared.
    
    Args:
        obj_or_id_or_set (set | int | Agent | str): Object, ID, set of IDs, or
            side key to remove modifiers from.
        key_or_modifier (str | Modifier): Blob key, or a ``Modifier`` object to
            remove directly.
        source (str | int, optional): Source identifier to remove. ``None``
            removes all modifiers for the key. Defaults to None."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def task_schedule_server (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """Schedule a new task on the server starting at the given label.
    
    Like ``task_schedule`` but always runs under ``FrameContext.server_task``.
    
    Args:
        label (str | Label): The label to start the task at.
        data (dict, optional): Initial task variables. Defaults to None.
        var (str, optional): Variable name to store the created task. Defaults
            to None.
        defer (bool, optional): Defer first tick to the next frame. Defaults to
            False.
        inherit (bool, optional): Inherit parent task variables. Defaults to
            True.
        unscheduled (bool, optional): Create without scheduling immediately.
            Defaults to False.
    
    Returns:
        MastAsyncTask: The task created, or None outside a server task context."""
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
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
def upgrade_add (agent_id_or_set, label, data=None, activate=False):
    """Add an upgrade to one or more agents.
    
    Creates an ``Upgrade`` object linked to each agent. If ``activate=True``,
    the upgrade's MAST label is scheduled immediately as a server task and the
    ``upgrade_activated`` signal is emitted.
    
    Args:
        agent_id_or_set (int | set | list | object): Agent ID(s) or object(s)
            to apply the upgrade to.
        label (label | str | dict): MAST label to run when the upgrade
            activates. Pass a dict with a ``"label"`` key to merge extra data:
            ``{"label": my_label, "power": 2}``.
        data (dict, optional): Variables passed to the upgrade task. Merged
            with dict-form ``label`` data. Defaults to None.
        activate (bool, optional): Activate the upgrade immediately after
            adding. Defaults to ``False``.
    
    Returns:
        Upgrade: The last ``Upgrade`` object created.
    
    Example:
        upgrade_add(SHIP_ID, shield_boost_label, activate=True)
        upgrade_add(SHIP_ID, {"label": power_label, "multiplier": 2})"""
def upgrade_remove_all (agent):
    """Deactivate and remove all upgrades from an agent.
    
    Calls ``deactivate()`` and ``discard()`` on every ``Upgrade`` linked to
    the agent, stopping their tasks and removing the ``__UPGRADE__`` links.
    
    Args:
        agent: Agent ID or object whose upgrades should be removed.
    
    Example:
        upgrade_remove_all(SHIP_ID)"""
class Upgrade(Agent):
    """class Upgrade"""
    def __init__ (self, agent_id, label, data):
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
    @property
    def is_active (self):
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
