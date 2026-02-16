def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def add_modifier (obj_or_id_or_set, key, value, source, flat_add_or_mult=1, duration=None):
    """Add and apply a modifier for a blob value of a given object.
    The modifier can also apply to all objects of a side by passing a side id or key instead of an object or object id.
    The source paramter identifies the modifier. Only one modifier with a given source can be active at a time for a given blob. If a modifier with the same source is added again, it will overwrite the previous one. This allows for easy updating of modifiers without needing to remove them first.
    
    The three types of modifiers are applied in different ways, and in the following order
    - Flat: All flat modifier values are combined and added directly to the base value of the blob.
    - Additive: All additive modifier values are added together, then multiplied by the result of the previous step.
    - Multiplicative: All multiplicative modifier values are multiplied together, then multiplied by the result of the previous step.
    
    Example usage:
    ```python
    # Assume that for this example, the base scan range is 1000.
    
    # This will increase the ship's scan range by 20% relative to the base range
    add_modifier(id, "ship_base_scan_range", 0.2, "Scan Range Efficiency Module", 1) # New value is 1200
    
    # This will add a flat 1000 to the ship's base scan range, and then apply the 20% buff.
    # Note that flat modifiers are always applied first when recalculating.
    add_modifier(id, "ship_base_scan_range", 1000, "Scan Range Extender", 0) # New value is 2400 (1000 base + 1000 flat from extender, which is then multiplied by the efficiency module modifier.)
    
    # this will add a 10% additive modifier. This stacks with the Scan Range Efficency Module for a total of 30% additive bonus
    add_modifier(id, "ship_base_scan_range", 0.1, "AI Scan Enhancement") # New value is 2600
    
    # This will add a multiplicative modifier that multiplies the ship's scan range by 0.5 (i.e. halves it) after the previous modifier types are applied.
    # Note that Multipicative modifier are always applied last when recalculating.
    add_modifier(id, "ship_base_scan_range", 0.5, "Nebula Interference", 2) # New value is 1300
    ```
    
    Args:
        obj_or_id (set | int | Agent | key): The set, object, ID, or a side key to which the modifier should be added
        key (str): The key of the blob value which the modifier should affect.
        value (float): The value of the modifier to be added.
        source (str|int): The source of the modifier, which can be used to identify and remove the modifier later if needed.
        flat_add_or_mult (float): How the modifier should be applied. Default is 1.
            - If 0, the modifier is a Flat modifier
            - If 1, the modifier is an Additive modifier
            - If 2, the modifier is a Multiplicative modifier
        duration (float, optional): The duration in seconds for which the modifier should be active. If None, the modifier will be permanent until removed. Defaults to None."""
def awaitable (func):
    ...
def delay_sim (seconds=0, minutes=0) -> sbs_utils.procedural.timers.Delay:
    """Creates a Promise that waits for the specified time to elapse.
    This is in simulation time (i.e. it could get paused).
    
    Args:
        seconds (int, optional): The number of seconds. Defaults to 0.
        minutes (int, optional): The number of minutes. Defaults to 0.
    
    Returns:
        Promise: A promise that is done when time has elapsed."""
def get_data_set_value (id_or_obj, key, index=0):
    """Get the data set (blob) value for the object with the given key.
    Args:
        id_or_obj (Agent | int): The agent or id.
        key (str): The data set key
        index (int, optional): The index of the data set value
    Returns:
        any: The value associated with the key and index."""
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def get_variable (key, default=None) -> any:
    """get the value of a variable at task scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        default (optional): What to return if the variable doesn't exist. Defaults to None.
    
    Returns:
        any: The value of the variable, or default value"""
def has_role (so, role):
    """Check if an agent has the specified role.
    
    Args:
        so (Agent | int): An agent or id.
        role (str): The role to test for
    
    Returns:
        bool: True if the agent has that role"""
def label (**kwargs):
    ...
def remove_modifier (obj_or_id_or_set, key, source):
    """Remove a modifier from a blob value of a given object or objects.
    
    Args:
        obj_or_id_or_set (set | int | Agent | key): The set, object, ID, or a side key from which the modifier should be removed.
        key (str): The key of the blob value from which the modifier should be removed.
        source (str|int): The source of the modifier to be removed. If None, all modifiers for this key are removed. Defaults to None."""
def set_data_set_value (to_update, key, value, index=0):
    """Set the data set (blob) value for the objects with the given key. If `to_update` is a set or list, sets the data set value for each object.
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The agent or id or set or list.
        key (str): The data set key.
        value (any): The value to assign.
        index (int, optional): The index of the data set value"""
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def set_variable (key, value) -> None:
    """set the value of a variable at task scope. Or returns the passed default if it doesn't exist.
    
    Args:
        key (str): the variable name
        value (any): The value to set the variable to"""
def side_members_set (side):
    """Get all objects with the specified side. Use this instead of `role(side)`.
    
    Args:
        side (str | int | Agent): The key or name of the side, or the ID of the side, or the side object, or an object with the given side.
    
    Returns:
        set[int]: Set of ids with the specified side."""
def signal_emit (name, data=None):
    """Emit a signal to trigger all instances of the signal route to run.
    Args:
        name (str): The name of the signal.
        data (dict): The data to provide to the signal route."""
def task_schedule (label: str | sbs_utils.mast.core_nodes.label.Label, data=None, var: str = None, defer=False, inherit=True, unscheduled=False) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
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
def to_side_id (key_or_id_or_object):
    """Get the id for the given side.
    
    Args:
        key_or_id (str | int): the key or the Agent of the side, or the id or Agent of a space object.
    
    Returns:
        int | None: The ID of the side. If the key, name, or id doesn't exist, returns None."""
class ModifierHandler(object):
    """This class is just a wrapper for some modifier functions that don't need to be exposed to the scripter."""
    def calculate_modified_value (base_value, modifiers) -> float:
        """Calculate the modified value of a blob based on the base value and a list of modifiers.
        
        The three types of modifiers are applied in different ways, and in the following order
        - Flat: All flat modifier values are combined and added directly to the base value of the blob.
        - Additive: All additive modifier values are added together, then multiplied by the result of the previous step.
        - Multiplicative: All multiplicative modifier values are multiplied together, then multiplied by the result of the previous step.
        
        Args:
            base_value (float): The base value of the blob before modifiers are applied.
            modifiers (list): A list of modifiers, where each modifier is a tuple of (value, mod_source, type)
        Returns:
            float: The modified value after all modifiers have been applied."""
    def get_default_blob_value (id, key):
        """Get the default value of a blob for a given object ID and blob key. This is the value of the blob before any modifiers are applied. If the default value is not already stored in the inventory, it will be retrieved from the data set and stored in the inventory for future use.
        Args:
            id (int | Agent): The ID or object
            key (str): The key of the blob for which to get the default value.
        Returns:
            float: The default value of the blob for the given object ID and blob key."""
    def get_side_modifiers (side_id_or_key, key):
        """Get the modifiers for a given side and blob key. If the side id or key provided is invalid, returns an empty string.
        
        Args:
            side_id_or_key (int or str): The ID or key of the side for which to get the modifiers.
            key (str): The key of the blob for which to get the modifiers.
        Returns:
            list: A list of modifiers for the given side and blob key. Each modifier is a tuple of (value, source, type)."""
    def handle_modifier_expiration ():
        """Used to schedule the removal of a modifier. Don't call this directly."""
    def recalculate_value (id, key) -> None:
        """Recalculate and set the value of a blob for a given object ID and blob key based on the default value and all modifiers currently applied. This should be called after adding or removing a modifier to update the blob value accordingly.
        If the given object ID is for a side, it will recalculate the blob value for all objects of that side.
        Args:
            id (int | Agent): The ID or object for which to recalculate the blob value.
            key (str): The blob key"""
