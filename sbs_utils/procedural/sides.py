from .roles import role, has_role
from .inventory import get_inventory_value, set_inventory_value
from .query import to_object, to_id, set_data_set_value, get_data_set_value
def sides_set():
    """
    Get a set containing the ids of all sides (objects with the "__side__" role).
    """
    sides = role("__side__")
    return sides

def side_keys_set():
    """
    Get a set containing the keys for all existing sides.
    """
    sides = role("__side__")
    side_keys = set()
    for s in sides:
        key = get_inventory_value(id, "side_key", None)
        if key is not None:
            side_keys.add(key)
    return side_keys

def side_members_set(side):
    """
    Get all objects with the specified side.
    
    Args:
        side (str): The key representing the side
    
    Returns:
        Set of ids with the specified side.
    """
    objs = role(side)
    # If the role for the side wasn't properly updated, remove the object
    objs = {x for x in objs if to_object(x).side == side}
    return objs

def side_ally_members_set(side):
    pass

def side_enemy_memnbers_set(side):
    pass

def to_side_id(key_or_id_or_object):
    """
    Get the id for the given side

    Args:
        key_or_id (str|int): the key or the Agent ID of the side, or a the id or Agent ID of a space object
    
    Returns:
        Agent|None: The Agent object for the side. If the key or id doesn't exist, returns None.
    """
    # Check if it's a key
    if isinstance(key_or_id_or_object, str):
        key_or_id_or_object = key_or_id_or_object.strip() # Get rid of leading/trailing whitespaces
        for s in sides_set():
            if get_inventory_value(s, "side_key") == key_or_id_or_object:
                return s
        return None # If it's not in sides_set() then it's not a valid side key
    id = to_id(key_or_id_or_object) # Will return key_or_id_or_object if it's not an object
    if isinstance(id, int):
        if has_role(id, "__side__"):
            return id # If it's a side prefab, we just return the ID
        
        # if it's not a side prefab, use the side of the object as the key and continue
        obj = to_object(id)
        side = obj.side
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
    print(f"Side1 = {side1}")
    print(f"Side2 = {side2}")
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)

    if o1 is None or o2 is None:
        print(f"side is None in side_set_relations()")
        print(f"One or both sides are not valid")
        return

    o1_enemies = get_inventory_value(o1, "side_enemies")
    print(f"o1_enemies = {o1_enemies}")
    if isinstance(o1_enemies, str):
        print("o1e STRING")
        o1_enemies = set(o1_enemies.split(","))

    o1_allies = get_inventory_value(o1, "side_allies")
    if isinstance(o1_allies, str):
        print("o1a STRING")
        o1_allies = set(o1_allies.split(","))
    o1_key = get_inventory_value(o1, "side_key")


    o2_enemies = get_inventory_value(o2, "side_enemies")
    if isinstance(o2_enemies, str):
        print("o2e STRING")
        o2_enemies = set(o2_enemies.split(","))
    o2_allies = get_inventory_value(o2, "side_allies")
    if isinstance(o2_allies, str):
        print("o2a STRING")
        o2_allies = set(o2_allies.split(","))
    o2_key = get_inventory_value(o2, "side_key")

    print(f"{o1_allies}")
    print(f'{o2_allies}')

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
    print(f"{o1_enemies}")
    print(f'{o2_enemies}')
    
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
        if not has_role("__side__"): # Exclude side prefabs
            set_data_set_value(ship, "ally_list", o2_allies)
            set_data_set_value(ship, "hostile_list", o2_enemies) # Not used by the engine yet?
    for ship in role(o1_key):
        if not has_role("__side__"): # Exclude side prefabs
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
    if isinstance(o1_allies, str):
        o1_allies = o1_allies.split(",")

    o2_key = get_inventory_value(o2, "side_key")

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
    if isinstance(o1_enemies, str):
        o1_enemies = o1_enemies.split(",")

    o2_key = get_inventory_value(o2, "side_key")

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
    
    


