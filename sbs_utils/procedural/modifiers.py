# This file defines utilitiy functions that can be used to modify blob values of space objects.
# TODO: This could be adapted to also work for inventory value modifiers as well.
# TODO: This could also be adapted to work for blob values that use lists instead of floats.

from sbs_utils.consoledispatcher import get_inventory_value, set_inventory_value
from sbs_utils.mast_sbs.maststorypage import signal_emit
from sbs_utils.procedural.query import get_data_set_value, set_data_set_value, to_blob, to_object, to_id, to_set, to_id_list
from sbs_utils.procedural.sides import to_side_id, side_members_set
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.timers import awaitable, delay_sim, set_timer, is_timer_finished, get_time_remaining, format_time_remaining

from sbs_utils.procedural.execution import AWAIT, get_variable, set_variable, task_schedule, task_schedule
from sbs_utils.mast.label import label

from sbs_utils.agent import Agent, get_story_id
class Modifier(Agent):
    """
    A class representing a modifier for a blob value. This is not meant to be used directly by the scripter, but rather as a data structure for storing modifier information.
    """
    def __init__(self, target, key, value, source, mod_type=1, timer=None, index=None):
        """
        Initialize a Modifier object.
        Args:
            target (int | set): The id or set of ids of the object(s) for which the modifier is applied.
            key (str): The key of the value to be modified.
            value (list[float]): The amount by which the value should be modified.
            source (string | int): The source of the modifier. Can be named (e.g. "Rested") or the ID of a task.
            mod_type (int, optional): The type of modifier (flat, additive, multiplicative). See docs for modifier_add() for more details.
            timer (str, optional): The name of the timer. Usually will be `key + "__" + source`
            index (int, optional): The index of the value in a list blob value that is being modified. If None, the modifier is applied to all indices of a list blob value.
        """
        super().__init__()
        self.target = target
        self.key = key
        self.value = value
        self.source = source
        self.mod_type = mod_type
        self.timer = timer
        self.index = index
        self.id = get_story_id()
        self.add_role("__modifier__") # This allows us to easily check if an object in the modifiers list is a Modifier object or not, since we will be storing the modifiers in the inventory of the objects they are modifying.
        


    def __eq__(self, other):
        """Are the Modifier objects equal?"""
        if self.target != other.target:
            return False
        if self.key != other.key:
            return False
        if self.mod_type != other.mod_type:
            return False
        if self.timer != other.timer:
            return False
        if self.index != other.index:
            return False
        return True
    
    def expired(self):
        """Is the modifier expired?"""
        if self.timer is None:
            return False
        print("checking timer expiration")
        return is_timer_finished(self.target, self.timer)
    
    def get_time_remaining(self):
        """Get the time remaining on the modifier's timer. Returns None if the modifier has no timer."""
        if self.timer is None:
            return None
        return get_time_remaining(self.target, self.timer)

    def format_time_remaining(self):
        """Get the time remaining on the modifier's timer formatted as a string. Returns None if the modifier has no timer."""
        if self.timer is None:
            return None
        return format_time_remaining(self.target, self.timer)
    
    def __str__(self):        
        return f"Modifier(target={self.target}, key={self.key}, value={self.value}, source={self.source}, mod_type={self.mod_type}, timer={self.timer})"


class ModifierHandler:
    """
    This class is just a wrapper for some modifier functions that don't need to be exposed to the scripter.
    """

    all_modifiers = [] # A list of all active modifiers. This is used to check for modifier existence and for when mdoifiers should be removed after a duration expires.

    # Called from objective.py, objectives_run_everything(), to remove expired modifiers on a regular basis.
    def remove_expired_modifiers():
        """
        Remove all expired modifiers. This should be called regularly to ensure that modifiers are removed after their duration expires.
        """
        for mod in ModifierHandler.all_modifiers:
            if mod.expired():
                modifier_remove(mod.target, mod)

    def calculate_modified_value(base_value, modifiers, index=0) -> float:
        """
        Calculate the modified value of a blob based on the base value and a list of modifiers.

        The three types of modifiers are applied in different ways, and in the following order
        - Flat: All flat modifier values are combined and added directly to the base value of the blob.
        - Additive: All additive modifier values are added together, then multiplied by the result of the previous step.
        - Multiplicative: All multiplicative modifier values are multiplied together, then multiplied by the result of the previous step.

        Args:
            base_value (float): The base value of the blob before modifiers are applied.
            modifiers (list[Modifier]): A list of modifiers
            index (int, optional): The index of the blob value to which the modifiers should be applied if the blob value is a list. Default is 0.
        Returns:
            float: The modified value after all modifiers have been applied.
        """
        new_value = base_value
        add_modifier = 0
        mult_modifier = 1
        for mod in modifiers:
            if mod.mod_type == 0:
                new_value += mod.value[index]
            elif mod.mod_type == 1:
                add_modifier += mod.value[index]
            elif mod.mod_type == 2:
                mult_modifier *= (mod.value[index]+1)

        new_value = new_value * (1+add_modifier) * mult_modifier
        return new_value

    def get_side_modifiers(side_id_or_key, key) -> list[Modifier]:
        """
        Get the modifiers for a given side and blob key. If the side id or key provided is invalid, returns an empty string.

        Args:
            side_id_or_key (int or str): The ID or key of the side for which to get the modifiers.
            key (str): The key of the blob for which to get the modifiers.
        Returns:
            list[Modifier]: A list of modifiers for the given side and blob key.
        """
        id = to_side_id(side_id_or_key)
        if id is None:
            return []
        all_mods = get_inventory_value(id, f"{key}_modifiers", [])
        return all_mods
    
    def is_key_for_blob(id, key) -> bool:
        """
        Check if a given key is a blob key for a given object ID. This is used to determine whether we should be looking for the default value in the inventory or in the data set when getting the default value of a blob.
        Args:
            id (int | Agent): The ID or object for which to check if the key is a blob key.
            key (str): The key to check.
        Returns:
            bool: True if the key is a blob key for the given object ID, False otherwise.
        """
        return get_data_set_value(id, key) is not None

    def get_default_blob_value(id, key, default=1.0) -> float | list[float]:
        """
        Get the default value of a blob for a given object ID and blob key. This is the value of the blob before any modifiers are applied. If the default value is not already stored in the inventory, it will be retrieved from the data set and stored in the inventory for future use.
        Args:
            id (int | Agent): The ID or object
            key (str): The key of the blob for which to get the default value.
            default (float, optional): The default value for the key. Default is 1.0
        Returns:
            float | list[float]: The default value of the blob for the given object ID and blob key. If it's an inventory key, will return a float. If it's a blob key, will return a list.
        """
        id = to_id(id)
        # First check if a default value is already set.
        default_value = get_inventory_value(id, f"{key}_default_value", None) # The default value of the blob, used for add_mult_or_base calculations.
        is_blob = ModifierHandler.is_key_for_blob(id, key)
        if default_value is None:
            if not is_blob:
                set_inventory_value(id, f"{key}_default_value", default)
                # print("default value is None. Setting to ", default, " for object with id:", id, " and key:", key)
                return default
            
            else:
                # IS a blob key.
                blob = to_blob(id)
                indices = ModifierHandler.get_blob_max_index(id, key) + 1 # Get the number of valid indices for the blob value.
                default_value = []
                for i in range(indices): # From 0 to indices - 1
                    value = blob.get(key, i)
                    if value is not None:
                        default_value.append(value)
                    else:
                        break
                set_inventory_value(id, f"{key}_default_value", default_value)
                # print("Set default blob value for object with id:", id, " and key:", key, " to ", default_value)
                return default_value
        else:
            # print("Checking for index updates for blob key:", key, " on object with id:", id)
            # Just check to make sure that the blob indices haven't been added to. Who knows what people might try to do.
            if is_blob:
                current_indices = len(default_value)
                max_indices = ModifierHandler.get_blob_max_index(id, key) + 1
                if current_indices < max_indices:
                    # If there are more indices in the data set than in the inventory, update the inventory.
                    blob = to_blob(id)
                    defaults = get_inventory_value(id, f"{key}_default_value", [])
                    for i in range(current_indices, max_indices):
                        value = blob.get(key, i)
                        if value is not None:
                            defaults.append(value)
                        else:
                            break
                    print("Updated default blob value for object with id:", id, " and key:", key, " to ", defaults)
                    set_inventory_value(id, f"{key}_default_value", defaults)
                    return defaults
        return default_value
    
    def recalculate_value(id, key) -> None:
        """
        Recalculate and set the value of a blob for a given object ID and blob key based on the default value and all modifiers currently applied. This should be called after adding or removing a modifier to update the blob value accordingly.
        If the given object ID is for a side, it will recalculate the blob value for all objects of that side.
        Args:
            id (int | Agent): The ID or object for which to recalculate the blob value. 
            key (str): The blob key
        """
        is_side = has_role(id, "__side__")
        if not is_side: # Not as side.
            is_blob = ModifierHandler.is_key_for_blob(id, key)
            all_mods = modifiers_get_for_object(id, key)
            default_value = ModifierHandler.get_default_blob_value(id, key) # float or list
            print("New default value: ", default_value)

            if not is_blob:
                new_value = ModifierHandler.calculate_modified_value(default_value, all_mods)
                set_inventory_value(id, key, new_value)
                return
            
            # If it IS a blob key
            new_value = []
            for i in range(len(default_value)):
                val = ModifierHandler.calculate_modified_value(default_value[i], all_mods, index=i)
                new_value.append(val)
                set_data_set_value(id, key, val, i)
            # print("New value for ", id, " key:",key, " is ", new_value)
        else:
            # print("Updating values for a side.")
            # Sides don't have blob values, but we need to recalculate the blob values of all members of the side since they could be affected by side modifiers.
            members = side_members_set(id)
            for member in members:
                ModifierHandler.recalculate_value(member, key)

    def get_blob_max_index(id, key) -> int:
        """
        Get the maximum valid index for a blob value. If the blob key does not exist, will return -1.
        Args:
            id (int | Agent): The ID or object for which to get the blob max index.
            key (str): The key of the blob for which to get the max index.
        Returns:
            int: The maximum valid index for the blob value.
        """
        blob = to_blob(id)
        # For most blob keys, this loop will only run twice and will return 0.
        for i in range(0,100): # Arbitrary max index of 100 to prevent infinite loop. Should be high enough for any reasonable blob list length.
            value = blob.get(key, i)
            if value is None:
                return i-1
        print("Warning: Reached max index of 100 when getting blob max index for", id, " for key:", key)
        return 100

def modifier_add(obj_or_id_or_set, key, value, source, flat_add_or_mult=1, duration=None, index=None) -> Modifier:
    """
    Add and apply a modifier for a blob value of a given object.
    The modifier can also apply to all objects of a side by passing a side id or key instead of an object or object id.
    The source paramter identifies the modifier. Only one modifier with a given source can be active at a time for a given blob. If a modifier with the same source is added again, it will overwrite the previous one. This allows for easy updating of modifiers without needing to remove them first.
    The duration parameter specifies how long the modifier should be active. If duration is None, the modifier will be permanent until manually removed. If duration is specified, the modifier will be automatically removed after the duration expires.

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
        
        # This will add a multiplicative modifier that reduces the ship's scan range by 50% after the previous modifier types are applied.
        # Note that Multipicative modifier are always applied last when recalculating.
        add_modifier(id, "ship_base_scan_range", -0.5, "Nebula Interference", 2) # New value is 1300
    ```
  
    Args:
        obj_or_id (set | int | Agent | key): The set, object, ID, or a side key to which the modifier should be added
        key (str): The key of the blob value which the modifier should affect.
        value (float): The value of the modifier to be added.
        source (str | int): The source of the modifier, which can be used to identify and remove the modifier later if needed. Source can be a string or an int.
        flat_add_or_mult (float): How the modifier should be applied. Default is 1.
            - If 0, the modifier is a Flat modifier
            - If 1, the modifier is an Additive modifier
            - If 2, the modifier is a Multiplicative modifier
        duration (float, optional): The duration in seconds for which the modifier should be active. If None, the modifier will be permanent until removed. Defaults to None.
        index (int, optional): The index of the blob value to which the modifier should be applied if the blob value is a list. If None, it will apply to all valid indices. Not applicable if the key is for an inventory value. Default is None.
    Returns:
        Modifier | set[int]: The modifier object, or a set of the IDs of all the modifiers that were created and added.
    """
    if duration is not None:
        duration = abs(duration)
        timer = key + "__" + source
    
    if isinstance(obj_or_id_or_set, str):
        side_id = to_side_id(obj_or_id_or_set)
        obj_or_id_or_set = side_id # Force a side id if a side key was passed.
    ship_set = to_set(obj_or_id_or_set)

    if flat_add_or_mult not in [0,1,2]:
        raise ValueError("Invalid value for flat_add_or_mult. Must be 0 (Flat), 1 (Additive), or 2 (Multiplicative).")
    

    
    added_mods = []

    for id in ship_set:
        all_mods = get_inventory_value(id, f"{key}_modifiers", []) # A list of all modifiers for this key.

        # The new modifier must be on a per-ship basis.
        # That way it is stored in the inventory of each ship, as well as the timer being unique.

        if duration is not None:
            set_timer(id, timer, duration)

        is_blob = ModifierHandler.is_key_for_blob(id, key)
        values = [0]
        if not is_blob:
            # If not a blob key, treat as an inventory key.
            values = [value] # Just a single value for inventory keys.

        else:
            indices = ModifierHandler.get_blob_max_index(id, key) + 1 # Get the number of valid indices for the blob value.
            if index is None:
                # If no index is specified, apply the modifier to all indices of the blob value.
                values = [value] * indices # Apply the same modifier value to all indices.
            else:
                values = [0] * indices # Initialize all values to 0 for each index.
                values[index] = value # Set the specified index to the modifier value, leaving the rest as 0.



        new_mod = Modifier(id, key, values, source, flat_add_or_mult, timer, index)
        

        # Check if the modifier exists
        mod_exists = modifier_exists(id, new_mod)
        if mod_exists:
            print("This modifier already exists:", mod_exists)
        
        # Add the new modifier
        if not mod_exists:
            all_mods.append(new_mod)
            ModifierHandler.all_modifiers.append(new_mod)
            # print("Adding modifier:", new_mod, " to object with id:", id)
            # print("Length of modifier list:", len(ModifierHandler.all_modifiers))
            added_mods.append(new_mod)
            set_inventory_value(id, f"{key}_modifiers", all_mods)

            # Now we need to actually apply the modifier to the blob value. We will recalculate set the blob value.
            ModifierHandler.recalculate_value(id, key)
    signal_emit("modifier_added", data={"obj_or_id_or_set": obj_or_id_or_set, "key": key, "source": source, "added_mods": added_mods})
    if len(added_mods) == 0:
        return added_mods[0]
    return to_set(to_id_list(added_mods))


def modifier_remove(obj_or_id_or_set, key_or_modifier, source=None) -> None:
    """
    Remove a modifier from a blob value of a given object or objects.

    Args:
        obj_or_id_or_set (set | int | Agent | key): The set, object, ID, or a side key from which the modifier should be removed.
        key_or_modifier (str | Modifier): The key of the blob value from which the modifier should be removed, or the modifier object itself.
        source (str | int): The source of the modifier to be removed. If None, all modifiers for this key are removed. Source can be a string or an int. Defaults to None.
    """
    removed_mods = []

    if isinstance(key_or_modifier, Modifier):
        ship = key_or_modifier.target
        key = key_or_modifier.key
        all_mods = get_inventory_value(ship, f"{key}_modifiers", [])
        print(len(all_mods), " modifiers found for ship ", ship, " and key ", key)
        if key_or_modifier in all_mods:
            all_mods.remove(key_or_modifier)
            print(len(all_mods), " modifiers remaining after removal.")
            set_inventory_value(ship, f"{key}_modifiers", all_mods)
            ModifierHandler.all_modifiers.remove(key_or_modifier)
            ModifierHandler.recalculate_value(ship, key)
            removed_mods.append(key_or_modifier)
            signal_emit("modifier_removed", data={"obj_or_id_or_set": obj_or_id_or_set, "modifier": removed_mods})
            return
        print("Modifier not found:", key_or_modifier)
        return removed_mods

    # Check if the object is a side key, and if so, convert it to a side id.
    if isinstance(obj_or_id_or_set, str):
        side_id = to_side_id(obj_or_id_or_set)
        if side_id is None:
            print("Invalid side key provided to modifier_remove(): ", obj_or_id_or_set)
            return
        obj_or_id_or_set = side_id # Force a side id if a side key was passed.
    ship_set = to_set(obj_or_id_or_set)

    # Now we can assume that obj_or_id_or_set is a set of object ids, and that key_or_modifier is a key.
    key = key_or_modifier
    for id in ship_set:
        if source is None:
            # If source is None, remove all modifiers for this key.
            set_inventory_value(id, f"{key}_modifiers", [])
            ModifierHandler.recalculate_value(id, key) # This still accounts for side modifiers, since those are stored separately and are not affected by this.
            for mod in ModifierHandler.all_modifiers:
                if mod.key == key and id == mod.id:
                    ModifierHandler.all_modifiers.remove(mod)
            continue
        
        else:
            ship_mods = get_inventory_value(id, f"{key}_modifiers", [])
            for mod in ship_mods:
                if mod.source == source:
                    removed_mods.append(mod)
                    ship_mods.remove(mod)
                    ModifierHandler.all_modifiers.remove(mod)
            set_inventory_value(id, f"{key}_modifiers", ship_mods)
            ModifierHandler.recalculate_value(id, key)

    signal_emit("modifier_removed", data={"obj_or_id_or_set": obj_or_id_or_set, "modifier": removed_mods})

def modifier_exists(id, source_or_modifier)->bool:
    """
    Check if the specified modifier exists on the specified object.
    Args:
        id (int): The ID of the object for which to check for the modifier.
        source_or_modifier (str | int | Modifier): The source of the modifier to check for, or the modifier object. Source can be a string or an int.
    Returns:
        bool: True if the modifier exists, False otherwise.
    """
    all_mods = ModifierHandler.all_modifiers
    if isinstance(source_or_modifier, Modifier):
        return source_or_modifier in all_mods
    # TODO: Determine under what conditions we want to consider a modifier to "exist". If the target and source match, what do we do with that? Do we reset the timer, if it exists? Do we only allow one instance of a modifier with a given source for any single ship?
    for mod in all_mods:
        if id in mod.id and mod.source == source_or_modifier:
            return True
    return False

def modifiers_get_for_object(obj_or_id, key) -> list[Modifier]:
    """
    Get all modifiers currently applied to a blob value of a given object.
    This can be used to display the active modifiers for a blob value in a GUI, for example.

    Args:
        obj_or_id (int | Agent): The ID or object for which to get the modifiers.
        key (str): The key of the blob value for which to get the modifiers.

    Returns:
        list[Modifier]: A list of modifiers currently applied to the blob value. Source can be a string or an int.
    """
    id = to_id(obj_or_id)
    ship_mods = get_inventory_value(id, f"{key}_modifiers", [])
    all_mods = ship_mods + ModifierHandler.get_side_modifiers(id, key)
    return all_mods

def modifier_is_expired(modifier) -> bool:
    """
    Check if a modifier is expired based on its timer.
    Args:
        modifier (Modifier): The modifier to check for expiration.
    Returns:
        bool: True if the modifier is expired, False otherwise.
    """
    mod = to_object(modifier)
    return mod.expired()

def modifier_get_time_remaining(modifier) -> float:
    """
    Get the time remaining on a modifier's timer. Returns None if the modifier has no timer.
    Args:
        modifier (Modifier): The modifier for which to get the time remaining.  
    Returns:    
        float: The time remaining on the modifier's timer in seconds, or None if the modifier has no timer.
    """
    mod = to_object(modifier)
    return mod.get_time_remaining()

def modifier_get_formatted_time_remaining(modifier) -> str:
    """
    Get the formatted time remaining on a modifier's timer. Returns None if the modifier has no timer.
    Args:
        modifier (Modifier): The modifier for which to get the formatted time remaining.  
    Returns:    
        str: The formatted time remaining on the modifier's timer, or None if the modifier has no timer.
    """
    mod = to_object(modifier)
    return mod.format_time_remaining()
