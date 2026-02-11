# This file defines utilitiy functions that can be used to modify blob values of space objects.
# TODO: This could be adapted to also work for inventory value modifiers as well.
# TODO: This could also be adapted to work for blob values that use lists instead of floats.

from sbs_utils.consoledispatcher import get_inventory_value, set_inventory_value
from sbs_utils.procedural.query import get_data_set_value, set_data_set_value, to_object, to_id, to_set
from sbs_utils.procedural.sides import to_side_id, side_members_set
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.timers import awaitable, delay_sim

from sbs_utils.procedural.execution import AWAIT, get_variable, set_variable, task_schedule, task_schedule
from sbs_utils.mast.label import label

class ModifierHandler:
    """
    This class is just a wrapper for some modifier functions that don't need to be exposed to the scripter.
    """

    def calculate_modified_value(base_value, modifiers) -> float:
        """
        Calculate the modified value of a blob based on the base value and a list of modifiers.

        The three types of modifiers are applied in different ways, and in the following order
        - Flat: All flat modifier values are combined and added directly to the base value of the blob.
        - Additive: All additive modifier values are added together, then multiplied by the result of the previous step.
        - Multiplicative: All multiplicative modifier values are multiplied together, then multiplied by the result of the previous step.

        Args:
            base_value (float): The base value of the blob before modifiers are applied.
            modifiers (list): A list of modifiers, where each modifier is a tuple of (value, mod_source, type)
        Returns:
            float: The modified value after all modifiers have been applied.
        """
        new_value = base_value
        add_modifier = 0
        mult_modifier = 1
        for mod_value, mod_source, mod_type in modifiers:
            if mod_type == 0:
                new_value += mod_value
            elif mod_type == 1:
                add_modifier += mod_value
            elif mod_type == 2:
                mult_modifier *= (mod_value)

        new_value = new_value * (1+add_modifier) * mult_modifier
        return new_value

    def get_side_modifiers(side_id_or_key, key):
        """
        Get the modifiers for a given side and blob key. If the side id or key provided is invalid, returns an empty string.

        Args:
            side_id_or_key (int or str): The ID or key of the side for which to get the modifiers.
            key (str): The key of the blob for which to get the modifiers.
        Returns:
            list: A list of modifiers for the given side and blob key. Each modifier is a tuple of (value, source, type).
        """
        id = to_side_id(side_id_or_key)
        if id is None:
            return []
        all_mods = get_inventory_value(id, f"{key}_modifiers", [])
        return all_mods

    def get_default_blob_value(id, key):
        """
        Get the default value of a blob for a given object ID and blob key. This is the value of the blob before any modifiers are applied. If the default value is not already stored in the inventory, it will be retrieved from the data set and stored in the inventory for future use.
        Args:
            id (int | Agent): The ID or object
            key (str): The key of the blob for which to get the default value.
        Returns:
            float: The default value of the blob for the given object ID and blob key.
        """
        id = to_id(id)
        default_value = get_inventory_value(id, f"{key}_default_value", None) # The default value of the blob, used for add_mult_or_base calculations.
        if default_value is None:
            default_value = get_data_set_value(id, key)
            if default_value is None:
                default_value = 0
            set_inventory_value(id, f"{key}_default_value", default_value)
        return default_value
    
    def recalculate_value(id, key) -> None:
        """
        Recalculate the value of a blob for a given object ID and blob key based on the default value and all modifiers currently applied. This should be called after adding or removing a modifier to update the blob value accordingly.
        If the given object ID is for a side, it will recalculate the blob value for all objects of that side.
        Args:
            id (int | Agent): The ID or object for which to recalculate the blob value. 
        """
        is_side = has_role(id, "__side__")
        if not is_side: # Not as side.
            default_value = ModifierHandler.get_default_blob_value(id, key)
            ship_mods = get_inventory_value(id, f"{key}_modifiers", [])
            all_mods = ship_mods + ModifierHandler.get_side_modifiers(id, key)
            new_value = ModifierHandler.calculate_modified_value(default_value, all_mods)
            set_data_set_value(id, key, new_value)
            print("New value for", id, key, "is", new_value)
        else:
            print("Updating values for a side.")
            # Sides don't have blob values, but we need to recalculate the blob values of all members of the side since they could be affected by side modifiers.
            members = side_members_set(id)
            for member in members:
                ModifierHandler.recalculate_value(member, key)

    # Definitely don't want this to be exposed to the end user. Could cause all sorts of problems.
    # If there's a better way of doing this, let me know.
    @label()
    def handle_modifier_expiration():
        """
        Used to schedule the removal of a modifier. Don't call this directly.
        """
        duration = get_variable("duration")
        yield AWAIT(delay_sim(seconds=duration))
        id = get_variable("id")
        key = get_variable("key")   
        source = get_variable("source")
        remove_modifier(id, key, source)

def add_modifier(obj_or_id_or_set, key, value, source, flat_add_or_mult=1, duration=None):
    """
    Add and apply a modifier for a blob value of a given object.
    The modifier can also apply to all objects of a side by passing a side id or key instead of an object or object id.
    The source paramter identifies the modifier. Only one modifier with a given source can be active at a time for a given blob. If a modifier with the same source is added again, it will overwrite the previous one. This allows for easy updating of modifiers without needing to remove them first.
      
    The three types of modifiers are applied in different ways, and in the following order
    - Flat: All flat modifier values are combined and added directly to the base value of the blob.
    - Additive: All additive modifier values are added together, then multiplied by the result of the previous step.
    - Multiplicative: All multiplicative modifier values are multiplied together, then multiplied by the result of the previous step.
  
    Example usage:
    ```python
    # Assume that for this ship, the base scan range is 1000.

    # This will increase the ship's scan range by 20%
    add_modifier(id, "ship_base_scan_range", 0.2, "Scan Range Efficiency Module", 1) # New value is 1200
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
        duration (float, optional): The duration in seconds for which the modifier should be active. If None, the modifier will be permanent until removed. Defaults to None.
    """
    
    if isinstance(obj_or_id_or_set, str):
        side_id = to_side_id(obj_or_id_or_set)
        obj_or_id_or_set = side_id # Force a side id if a side key was passed.
    ship_set = to_set(obj_or_id_or_set)

    if flat_add_or_mult not in [0,1,2]:
        raise ValueError("Invalid value for flat_add_or_mult. Must be 0 (Flat), 1 (Additive), or 2 (Multiplicative).")
    
    for id in ship_set:
        all_mods = get_inventory_value(id, f"{key}_modifiers", []) # A list of all modifiers for this key. Each modifier is a tuple of (value, source, add_mult_or_base).

        # Check if the modifier exists
        mod_exists = False
        for i in range(len(all_mods)): 
            mod_value, mod_source, mod_type = all_mods[i]
            if mod_source == source:
                all_mods[i] = (value, source, flat_add_or_mult) # Update the existing modifier with the new value and type.
                mod_exists = True
                break
        # Add the new modifier
        if not mod_exists:
            all_mods.append((value, source, flat_add_or_mult))
        set_inventory_value(id, f"{key}_modifiers", all_mods)

        # Now we need to actually apply the modifier to the blob value. We will recalculate set the blob value.
        ModifierHandler.recalculate_value(id, key)
    if duration is not None:
        duration = abs(duration) # Just in case.
        task_schedule(ModifierHandler.handle_modifier_expiration, data={"id": obj_or_id_or_set, "key": key, "source": source, "duration": duration})


def remove_modifier(obj_or_id_or_set, key, source):
    """
    Remove a modifier from a blob value of a given object or objects.

    Args:
        obj_or_id_or_set (set | int | Agent | key): The set, object, ID, or a side key from which the modifier should be removed.
        key (str): The key of the blob value from which the modifier should be removed.
        source (str|int): The source of the modifier to be removed. If None, all modifiers for this key are removed. Defaults to None.
    """
    if isinstance(obj_or_id_or_set, str):
        side_id = to_side_id(obj_or_id_or_set)
        obj_or_id_or_set = side_id # Force a side id if a side key was passed.
    ship_set = to_set(obj_or_id_or_set)
    for id in ship_set:
        all_mods = get_inventory_value(id, f"{key}_modifiers", [])

        for mod_value, mod_source, mod_type in all_mods:
            if source is None or mod_source == source:
                all_mods.remove((mod_value, mod_source, mod_type))

        set_inventory_value(id, f"{key}_modifiers", all_mods)
        # Now we need to actually apply the modifier to the blob value. We will recalculate set the blob value.
        ModifierHandler.recalculate_value(id, key)
