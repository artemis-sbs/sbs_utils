from .roles import role, has_role
from .inventory import get_inventory_value, set_inventory_value
from .query import to_object, to_id, set_data_set_value, get_data_set_value
def sides_set():
    """
    Get a set containing the ids of all sides (objects with the "__side__" role).

    Returns:
        Set: A set of IDs for each side
    """
    sides = role("__side__")
    return sides

def side_keys_set():
    """
    Get a set containing the keys for all existing sides.
    
    Returns:
        Set: A set of keys for all sides
    """
    sides = role("__side__")
    side_keys = set()
    for s in sides:
        key = get_inventory_value(s, "side_key", None)
        if key is not None:
            side_keys.add(key)
    return side_keys

def side_members_set(side):
    """
    Get all objects with the specified side. Use this instead of `role(side)`
    
    Args:
        side (str|int|Agent): The key or name of the side, or the ID of the side, or the side object, or an object with the given side
    
    Returns:
        Set of ids with the specified side.
    """
    print(f"Getting set for side: {side}")
    id = to_side_id(side)
    key = get_inventory_value(id, "side_key")
    objs = role(key) - role("__side__") # remove the actual side, since it's a MastAsyncTask instead of a Ship
    # If the role for the side wasn't properly updated, remove the object?
    # objs = {x for x in objs if to_object(x).side == side}
    return objs

def side_ally_members_set(side):
    pass

def side_enemy_memnbers_set(side):
    pass

def to_side_id(key_or_id_or_object):
    """
    Get the id for the given side

    Args:
        key_or_id (str|int): the key or the Agent of the side, or the id or Agent of a space object
    
    Returns:
        int|None: The ID of the side. If the key, name, or id doesn't exist, returns None.
    """
    # Check if it's a key
    if isinstance(key_or_id_or_object, str):
        # print(f"Side id: {key_or_id_or_object}")
        key_or_id_or_object = key_or_id_or_object.strip() # Get rid of leading/trailing whitespaces
        for s in sides_set():
            if get_inventory_value(s, "side_key") == key_or_id_or_object:
                return s
            if get_inventory_value(s, "side_name") == key_or_id_or_object:
                return s
        return None # If it's not in sides_set() then it's not a valid side key
    id = to_id(key_or_id_or_object) # Will return key_or_id_or_object if it's not an object
    if isinstance(id, int):
        if has_role(id, "__side__"):
            return id # If it's a side prefab, we just return the ID
        print(f"Trying again for id: {id}")
        # if it's not a side prefab, use the side of the object as the key and continue
        obj = to_object(id)
        if obj is not None:
            side = obj.side
            # to_side_id() should be able to return the right side based on id or display text
            return to_side_id(side)
        
    return None

def to_side_object(key_or_id):
    """
    Get the object for the given side

    Args:
        key_or_id (str|int): the key or the Agent ID of the side, or an Agent or Agent ID belonging to the side
    
    Returns:
        Agent|None: The Agent object for the side. If the key, agent, or id doesn't exist, returns None.
    """
    s = to_side_id(key_or_id)
    return to_object(s)

def side_display_name(key):
    """
    Get the display name of the side.

    Args:
        key (str|int): The key or id of the side
    Returns:
        str: The display name of the side
    """
    id = to_side_id(key)
    name = get_inventory_value(id, "side_name")
    return name

def side_set_ship_allies_and_enemies(ship):
    ship = to_object(ship)
    side = to_side_id(ship)
    if isinstance(side, int):
        allies = get_inventory_value(side, "side_allies")
        enemies = get_inventory_value(side, "side_enemies")
        allies = ",".join(allies)
        enemies = ",".join(enemies)
        set_data_set_value(ship, "ally_list", allies)
        set_data_set_value(ship, "hostile_list", enemies) # Not used by the engine yet?
    

def side_set_relations(side1, side2, relation):
    """
    Update relations between two sides

    Args:
        side1 (str|int): key or id of the first side
        side2 (str|int): key or id of the second side
        relation (int): the new relations between the sides.
            1: Ally
            0: Netural
            -1: Enemy
    """
    # print(f"Side1 = {side1}")
    # print(f"Side2 = {side2}")
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)

    if o1 is None or o2 is None:
        # If a side isn't initialized yet, then we just return.
        # print(f"side is None in side_set_relations()")
        # print(f"One or both sides are not valid")
        return

    o1_enemies = get_inventory_value(o1, "side_enemies")
    # print(f"o1_enemies = {o1_enemies}")
    if isinstance(o1_enemies, str):
        o1_enemies = set(o1_enemies.split(","))

    o1_allies = get_inventory_value(o1, "side_allies")
    if isinstance(o1_allies, str):
        o1_allies = set(o1_allies.split(","))
    o1_key = get_inventory_value(o1, "side_key")


    o2_enemies = get_inventory_value(o2, "side_enemies")
    if isinstance(o2_enemies, str):
        o2_enemies = set(o2_enemies.split(","))
    o2_allies = get_inventory_value(o2, "side_allies")
    if isinstance(o2_allies, str):
        o2_allies = set(o2_allies.split(","))
    o2_key = get_inventory_value(o2, "side_key")
    # print("Allies before change")
    # print(f"{o1_allies}")
    # print(f'{o2_allies}')
    # print("Enemies before Change")
    # print(f"{o1_enemies}")
    # print(f"{o2_enemies}")

    # Since we're using sets, which don't allow duplicates, we don't need to worry about whether the key exists already
    if relation == 1:
        o1_enemies.discard(o2_key)
        o2_enemies.discard(o1_key)
        o2_allies.add(o1_key)
        o1_allies.add(o2_key)
    if relation == 0:
        o1_enemies.discard(o2_key)
        o2_enemies.discard(o1_key)
        o1_allies.discard(o2_key)
        o2_allies.discard(o1_key)
    if relation == -1:
        o1_allies.discard(o2_key)
        o2_allies.discard(o1_key)
        o2_enemies.add(o1_key)
        o1_enemies.add(o2_key)
    # print("Allies after change")
    # print(f"{o1_allies}")
    # print(f'{o2_allies}')
    # print("Enemies after Change")
    # print(f"{o1_enemies}")
    # print(f"{o2_enemies}")
    
    set_inventory_value(o1, "side_enemies", o1_enemies)
    set_inventory_value(o1, "side_allies", o1_allies)
    set_inventory_value(o2, "side_enemies", o2_enemies)
    set_inventory_value(o2, "side_allies", o2_allies)

    # Now we need to update the ally lists for all impacted ships
    # Convert to strings for blob data
    o1_enemies = ",".join(o1_enemies)
    o2_enemies = ",".join(o2_enemies)
    o1_allies = ",".join(o1_allies)
    o2_allies = ",".join(o2_allies)
    for ship in role(o2_key):
        if not has_role(ship, "__side__"): # Exclude side prefabs
            set_data_set_value(ship, "ally_list", o2_allies)
            set_data_set_value(ship, "hostile_list", o2_enemies) # Not used by the engine yet?
    for ship in role(o1_key):
        if not has_role(ship, "__side__"): # Exclude side prefabs
            set_data_set_value(ship, "ally_list", o1_allies)
            set_data_set_value(ship, "hostile_list", o1_enemies) # Not used by the engine yet?

    
def side_are_allies(side1, side2)->bool:
    """
    Check if the specified sides are allies.
    Args:
        side1 (str|int): the key or id of the first side
        side2 (str|int): the key or id of the second side
    Returns: 
        True if they are allies, otherwise False
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)

    o1_allies = get_inventory_value(o1, "side_allies")
    # print(f"side_are_allies o1_allies: {o1_allies}")
    if isinstance(o1_allies, str):
        o1_allies = o1_allies.split(",")

    o2_key = get_inventory_value(o2, "side_key")
    # print(f"o2key: {o2_key}")

    return o2_key in o1_allies

def side_are_enemies(side1, side2)->bool:
    """
    Check if the specified sides are enemies.
    Args:
        side1 (str|int): the key or id of the first side
        side2 (str|int): the key or id of the second side
    Returns: 
        True if they are allies, otherwise False
    """
    
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)

    o1_enemies = get_inventory_value(o1, "side_enemies")
    # print(f"side_are_enemies o1_enemies: {o1_enemies}")
    if isinstance(o1_enemies, str):
        o1_enemies = o1_enemies.split(",")

    o2_key = get_inventory_value(o2, "side_key")
    # print(f"o2Key = {o2_key}")

    return o2_key in o1_enemies
    
def side_are_neutral(side1, side2)->bool:
    """
    Check if the specified sides are neutral (neither enemies nor allies).
    Args:
        side1 (str|int): the key or id of the first side
        side2 (str|int): the key or id of the second side
    Returns: 
        True if they are allies, otherwise False
    """
    return (not side_are_allies(side1,side2)) and (not side_are_enemies(side1,side2))
    
    


