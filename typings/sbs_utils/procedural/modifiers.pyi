from sbs_utils.agent import Agent
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Wrap a promise in a non-blocking waiter.
    
    Returns a ``PromiseWaiter`` whose ``done()`` method can be polled each tick
    without suspending the current task.
    
    Args:
        promise (Promise): The promise to wait on.
    
    Returns:
        PromiseWaiter: A waiter that reports completion without blocking."""
def awaitable (func):
    ...
def delay_sim (seconds=0, minutes=0) -> sbs_utils.procedural.timers.Delay:
    """Suspend the current task for a duration measured in simulation time.
    
    Simulation time can be paused (e.g. when the game is paused).
    
    Args:
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
    
    Returns:
        Delay: A promise that resolves when the time has elapsed.
    
    Example:
        await delay_sim(seconds=5)
        "Five simulation seconds have passed.""""
def format_time_remaining (id_or_obj, name):
    """Return the time remaining on a timer as a ``M:SS`` string.
    
    Returns an empty string when the timer has expired or is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        str: Formatted remaining time, e.g. ``"1:30"``, or ``""`` if expired.
    
    Example:
        gui_text("Time: {format_time_remaining(SHIP_ID, 'mission')}")"""
def get_data_set_value (id_or_obj, key, index=0):
    """Get a value from the engine data-set (blob) of a space or grid object.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
    
    Returns:
        any: The stored value, or ``None`` if the object or key is not found."""
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
def get_time_remaining (id_or_obj, name):
    """Return the number of whole seconds remaining on a timer.
    
    Returns ``0`` when the timer has expired or is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        int: Seconds remaining, or ``0`` if expired or not set.
    
    Example:
        secs = get_time_remaining(SHIP_ID, "mission")
        if secs < 60:
            "Less than a minute remaining!""""
def get_variable (key, default=None) -> any:
    """Get the value of a variable from the current task's scope.
    
    Args:
        key (str): Variable name.
        default (optional): Value to return when the variable is absent.
            Defaults to None.
    
    Returns:
        any: The variable value, or ``default``."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def is_timer_finished (id_or_obj, name):
    """Return whether a timer has expired. Returns ``True`` if the timer is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        bool: ``True`` if the timer has expired or was never set.
    
    Example:
        if is_timer_finished(SHIP_ID, "repair"):
            "Repair bay ready.""""
def label (**kwargs):
    ...
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
def modifier_exists (id, source_or_modifier) -> bool:
    """Return ``True`` if a modifier matching ``source_or_modifier`` is active on the object.
    
    Args:
        id (int): ID of the object to check.
        source_or_modifier (str | int | Modifier): Source identifier or a
            ``Modifier`` object to look for.
    
    Returns:
        bool: ``True`` if the modifier exists, ``False`` otherwise."""
def modifier_get_formatted_time_remaining (modifier) -> str:
    """Return the time remaining on a modifier's timer as a human-readable string.
    
    Args:
        modifier (Modifier): The modifier to query.
    
    Returns:
        str: Formatted time remaining (e.g. ``"1:23"``), or ``None`` if the
            modifier is permanent."""
def modifier_get_time_remaining (modifier) -> float:
    """Return the seconds remaining until a modifier expires.
    
    Args:
        modifier (Modifier): The modifier to query.
    
    Returns:
        float: Seconds remaining, or ``None`` if the modifier is permanent."""
def modifier_is_expired (modifier) -> bool:
    """Return ``True`` if the modifier's timer has elapsed.
    
    Args:
        modifier (Modifier): The modifier to check.
    
    Returns:
        bool: ``True`` if expired, ``False`` if still active or permanent."""
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
def modifiers_get_for_object (obj_or_id, key) -> list[sbs_utils.procedural.modifiers.Modifier]:
    """Return all modifiers currently applied to a blob key on an object.
    
    Combines per-object modifiers stored in inventory with any side-level
    modifiers. Useful for displaying active buffs/debuffs in a GUI.
    
    Args:
        obj_or_id (int | Agent): The object or its ID.
        key (str): The blob key whose modifiers should be retrieved.
    
    Returns:
        list[Modifier]: All active ``Modifier`` objects for that key."""
def set_data_set_value (to_update, key, value, index=0):
    """Set a value in the engine data-set (blob) for one or more space or grid objects.
    
    If ``to_update`` is a set or list, the value is applied to each member.
    
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The
            agent(s) to update.
        key (str): The data-set key.
        value (any): The value to store.
        index (int, optional): The slot index within that key. Defaults to 0."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def set_timer (id_or_obj, name, seconds=0, minutes=0):
    """Start a named countdown timer on an agent.
    
    Records the expiry tick in the agent's inventory. Use ``is_timer_finished``
    or ``get_time_remaining`` to check progress.
    
    Args:
        id_or_obj (Agent | int): The agent to set the timer on.
        name (str): Unique timer name for this agent.
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
    
    Example:
        set_timer(SHIP_ID, "repair", seconds=30)
        if is_timer_finished(SHIP_ID, "repair"):
            "Repairs complete!""""
def set_variable (key, value) -> None:
    """Set a variable in the current task's scope.
    
    Args:
        key (str): Variable name.
        value (any): Value to assign."""
def side_members_set (side):
    """Return the set of agent IDs that belong to a given side.
    
    Prefer this over ``role(side)`` as it correctly excludes the side agent
    itself from the result.
    
    Args:
        side (str | int | Agent): Side key, side agent ID, side agent, or any
            space object whose side will be used.
    
    Returns:
        set[int]: IDs of all space objects on the specified side."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def task_schedule (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """Schedule a new task starting at the given label.
    
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
        MastAsyncTask: The task created, or None outside a task context."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_id_list (the_set):
    """Convert a set or list of agents/IDs to a list of integer IDs.
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[int]: Resolved integer IDs; unresolvable items are excluded."""
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
def to_side_id (key_or_id_or_object):
    """Resolve any side reference to the side agent's ID.
    
    Accepts a side key string, a side agent ID, a side agent object, or any
    space object (in which case its side property is used).
    
    Args:
        key_or_id_or_object (str | int | Agent): Side key, side agent ID, side
            agent, or a space object whose side should be resolved.
    
    Returns:
        int | None: The side agent ID, or ``None`` if not found."""
class Modifier(Agent):
    """A class representing a modifier for a blob value. This is not meant to be used directly by the scripter, but rather as a data structure for storing modifier information."""
    def __eq__ (self, other):
        """Are the Modifier objects equal?"""
    def __init__ (self, target, key, value, source, mod_type=1, timer=None, index=None):
        """Initialize a Modifier object.
        Args:
            target (int | set): The id or set of ids of the object(s) for which the modifier is applied.
            key (str): The key of the value to be modified.
            value (list[float]): The amount by which the value should be modified.
            source (string | int): The source of the modifier. Can be named (e.g. "Rested") or the ID of a task.
            mod_type (int, optional): The type of modifier (flat, additive, multiplicative). See docs for modifier_add() for more details.
            timer (str, optional): The name of the timer. Usually will be `key + "__" + source`
            index (int, optional): The index of the value in a list blob value that is being modified. If None, the modifier is applied to all indices of a list blob value."""
    def __str__ (self):
        """Return str(self)."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    def expired (self):
        """Is the modifier expired?"""
    def format_time_remaining (self):
        """Get the time remaining on the modifier's timer formatted as a string. Returns None if the modifier has no timer."""
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
    def get_time_remaining (self):
        """Get the time remaining on the modifier's timer. Returns None if the modifier has no timer."""
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
class ModifierHandler(object):
    """This class is just a wrapper for some modifier functions that don't need to be exposed to the scripter."""
    def calculate_modified_value (base_value, modifiers, index=0) -> float:
        """Calculate the modified value of a blob based on the base value and a list of modifiers.
        
        The three types of modifiers are applied in different ways, and in the following order
        - Flat: All flat modifier values are combined and added directly to the base value of the blob.
        - Additive: All additive modifier values are added together, then multiplied by the result of the previous step.
        - Multiplicative: All multiplicative modifier values are multiplied together, then multiplied by the result of the previous step.
        
        Args:
            base_value (float): The base value of the blob before modifiers are applied.
            modifiers (list[Modifier]): A list of modifiers
            index (int, optional): The index of the blob value to which the modifiers should be applied if the blob value is a list. Default is 0.
        Returns:
            float: The modified value after all modifiers have been applied."""
    def get_blob_max_index (id, key) -> int:
        """Get the maximum valid index for a blob value. If the blob key does not exist, will return -1.
        Args:
            id (int | Agent): The ID or object for which to get the blob max index.
            key (str): The key of the blob for which to get the max index.
        Returns:
            int: The maximum valid index for the blob value."""
    def get_default_blob_value (id, key, default=1.0) -> float | list[float]:
        """Get the default value of a blob for a given object ID and blob key. This is the value of the blob before any modifiers are applied. If the default value is not already stored in the inventory, it will be retrieved from the data set and stored in the inventory for future use.
        Args:
            id (int | Agent): The ID or object
            key (str): The key of the blob for which to get the default value.
            default (float, optional): The default value for the key. Default is 1.0
        Returns:
            float | list[float]: The default value of the blob for the given object ID and blob key. If it's an inventory key, will return a float. If it's a blob key, will return a list."""
    def get_side_modifiers (side_id_or_key, key) -> list[sbs_utils.procedural.modifiers.Modifier]:
        """Get the modifiers for a given side and blob key. If the side id or key provided is invalid, returns an empty string.
        
        Args:
            side_id_or_key (int or str): The ID or key of the side for which to get the modifiers.
            key (str): The key of the blob for which to get the modifiers.
        Returns:
            list[Modifier]: A list of modifiers for the given side and blob key."""
    def is_key_for_blob (id, key) -> bool:
        """Check if a given key is a blob key for a given object ID. This is used to determine whether we should be looking for the default value in the inventory or in the data set when getting the default value of a blob.
        Args:
            id (int | Agent): The ID or object for which to check if the key is a blob key.
            key (str): The key to check.
        Returns:
            bool: True if the key is a blob key for the given object ID, False otherwise."""
    def recalculate_value (id, key) -> None:
        """Recalculate and set the value of a blob for a given object ID and blob key based on the default value and all modifiers currently applied. This should be called after adding or removing a modifier to update the blob value accordingly.
        If the given object ID is for a side, it will recalculate the blob value for all objects of that side.
        Args:
            id (int | Agent): The ID or object for which to recalculate the blob value.
            key (str): The blob key"""
    def remove_expired_modifiers ():
        """Remove all expired modifiers. This should be called regularly to ensure that modifiers are removed after their duration expires."""
