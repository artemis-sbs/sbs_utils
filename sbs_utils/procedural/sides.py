from .signal import signal_emit
from ..helpers import FrameContext
from .roles import role, has_role
from .inventory import get_inventory_value, set_inventory_value
from .query import to_object, to_id, set_data_set_value, get_data_set_value, to_object_list
from .links import link, linked_to, has_link, has_link_to, unlink

def sides_set():
    """
    Get a set containing the ids of all sides (objects with the "__side__" role).

    Returns:
        set[int]: A set of IDs for each side.
    """
    sides = role("__side__")
    return sides

def side_keys_set():
    """
    Get a set containing the keys for all existing sides.
    
    Returns:
        set[str]: A set of keys for all sides.
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
    Get all objects with the specified side, or all objects of the same side as the provided object. Use this instead of `role(side)`.
    
    Args:
        side (str | int | Agent): The key or name of the side, or the ID of the side, or the side object, or an object with the given side.
    
    Returns:
        set[int]: Set of ids with the specified side.
    """
    # print(f"Getting set for side: {side}")
    id = to_side_id(side)
    key = get_inventory_value(id, "side_key")
    if key is None: # Should never happen, but just in case
        return set()
    objs = role(key) - role("__side__") # remove the actual side, since it's a MastAsyncTask instead of a Ship
    # If the role for the side wasn't properly updated, remove the object?
    # objs = {x for x in objs if to_object(x).side == side}
    return objs

def side_ally_members_set(side):
    """
    Get a set of all space objects allied with the side or object, including all members of the same side as the one provided.
    Args:
        side (str | int | Agent): The id or key of the side, or the id or object of a spaceobject.
    Returns:
        set[int]: A set containing the ids of all allied ships, stations, etc.
    """
    id = to_side_id(side)
    allies = linked_to(id, "side_ally")
    
    # allies = get_inventory_value(id, "side_allies", set())
    ally_members = set()
    if allies is not None:
        for a in allies:
            ally_members = ally_members | side_members_set(a)
    return ally_members

def side_enemy_members_set(side):
    """
    Get a set of all space objects that are enemies of the side or object.
    Args:
        side (str | int | Agent): The id or key of the side, or the id or object of a spaceobject.
    Returns:
        set[int]: A set containing the ids of all enemy ships, stations, etc.
    """
    id = to_side_id(side)
    enemies = linked_to(id, "side_hostile")
    enemy_members = set()
    if enemies is not None:
        for a in enemies:
            enemy_members = enemy_members | side_members_set(a)
    return enemy_members

def to_side_id(key_or_id_or_object):
    """
    Get the id for the given side or side of object.

    Args:
        key_or_id (str | int): the key or the Agent of the side, or the id or Agent of a space object.
    
    Returns:
        int | None: The ID of the side. If the key, name, or id doesn't exist, returns None.
    """
    # Check if it's a key
    if isinstance(key_or_id_or_object, str):
        # print(f"Side id: {key_or_id_or_object}")
        key_or_id_or_object = key_or_id_or_object.strip() # Get rid of leading/trailing whitespaces
        for s in sides_set():
            if get_inventory_value(s, "side_key").strip() == key_or_id_or_object:
                return s
            if get_inventory_value(s, "side_name").strip() == key_or_id_or_object:
                return s
        return None # If it's not in sides_set() then it's not a valid side key
    id = to_id(key_or_id_or_object) # Will return key_or_id_or_object if it's not an object
    if isinstance(id, int):
        if has_role(id, "__side__"):
            return id # If it's a side prefab, we just return the ID
        # print(f"Trying again for id: {id}")
        # if it's not a side prefab, use the side of the object as the key and continue
        obj = to_object(id)
        if obj is not None:
            side = obj.side
            # to_side_id() should be able to return the right side based on id or display text
            return to_side_id(side)
        
    return None

def to_side_object(key_or_id):
    """
    Get the object for the given side or side of object.

    Args:
        key_or_id (str | int): the key or the Agent ID of the side, or an Agent or Agent ID belonging to the side.
    
    Returns:
        Agent|None: The Agent object for the side. If the key, agent, or id doesn't exist, returns None.
    """
    s = to_side_id(key_or_id)
    return to_object(s)

def side_display_name(key):
    """
    Get the display name of the side or side of object.

    Args:
        key (str | int): The key or id of the side.
    Returns:
        str: The display name of the side.
    """
    id = to_side_id(key)
    name = get_inventory_value(id, "side_name")
    return name

def side_set_object_side(id_or_obj, key)->None:
    """
    Set the side of an object, or list or set of objects.

    Args:
        id_or_obj (int | Agent | list[int | Agent] | set[int | Agent]): The object or objects for which the side should be set.
        key (str | int | Agent): The key or id of the side, or an object with that side.
    """
    id = to_side_id(key)
    if id is None:
        print(f"WARNING: Side not found: {key}.")
        return
    key = get_inventory_value(id, "side_key")
    display = get_inventory_value(id, "side_name")
    obj_list = to_object_list(id_or_obj)
    for obj in obj_list:
        # Update side and GUI side name
        obj.side = key
        obj.side_display = display
    

#TODO: I tried using the @deprecated annotation (so the extension could easily determine and show a warning), but `typing_extensions` wasn't found, and `warnings` needs python v3.13
def side_set_ship_allies_and_enemies(ship):
    """
    *Deprecated as of v1.3.0.*
    To be removed in the future.
    Generate the ally list and hostile list for the specified ship based on its side.
    Args:
        ship (Agent | int): The object for which the ally and hostile lists should be updated.
    """
    pass

def side_set_relations(side1, side2, relation):
    """
    Update relations between two sides.

    Args:
        side1 (str|int): key or id of the first side, or an object with that side
        side2 (str|int): key or id of the second side, or an object with that side
        relation (sbs.DIPLOMACY): the new relations between the sides, e.g. `sbs.DIPLOMACY.ALLIED`
            * UNKNOWN
            * NEUTRAL
            * ALLIED
            * HOSTILE
    """
    
    sbs = FrameContext.context.sbs
    sim = FrameContext.context.sim

    if int(relation) < 0: # Backwards-compatibility (crash prevention) of old version that used -1 for hostile
        print(f"INVALID RELATION VALUE: {relation}. Using {sbs.DIPLOMACY.HOSTILE} instead.")
        # TODO: This could be a separate function that always prints the current stack?
        relation = sbs.DIPLOMACY.HOSTILE
    if int(relation) > int(sbs.DIPLOMACY.MAX): # Possibly also could prevent crashes.
        print(f"INVALID RELATION VALUE: {relation}. Using {sbs.DIPLOMACY.UNKNOWN} instead.")
        relation = sbs.DIPLOMACY.UNKNOWN

    o1 = to_side_id(side1)
    o2 = to_side_id(side2)

    if o1 is None or o2 is None:
        # If a side isn't initialized yet, then we just return.
        # print(f"side is None in side_set_relations()")
        # print(f"One or both sides are not valid")
        return
    
    old_relation = side_get_relations(o1, o2)
    
    # Clear the existing relationship links (if they exist), since we'll be replacing them with the new relationship.
    unlink(o1, "side_ally", o2)
    unlink(o2, "side_ally", o1)

    unlink(o1, "side_hostile", o2)
    unlink(o2, "side_hostile", o1)

    unlink(o1, "side_neutral", o2)
    unlink(o2, "side_neutral", o1)

    unlink(o1, "side_unknown", o2)
    unlink(o2, "side_unknown", o1)
    match relation:
        case sbs.DIPLOMACY.ALLIED:
            link(o1, "side_ally", o2)
            link(o2, "side_ally", o1) 
        case sbs.DIPLOMACY.HOSTILE:
            link(o1, "side_hostile", o2)
            link(o2, "side_hostile", o1)
        case sbs.DIPLOMACY.NEUTRAL:
            link(o1, "side_neutral", o2)
            link(o2, "side_neutral", o1) 
        case sbs.DIPLOMACY.UNKNOWN: # Is this strictly necessary? Probably not???
            link(o1, "side_unknown", o2)
            link(o2, "side_unknown", o1)
        case _:
            # While we could have left DIPLOMACY.UNKNOWN as its own thing,
            # for now we can safely assume that any relation value other than ALLIED, HOSTILE, or NEUTRAL is meant to be UNKNOWN, and we can just link it with "side_unknown".
            link(o1, "side_unknown", o2)
            link(o2, "side_unknown", o1)

    # Get the side keys, since the engine uses the key and doesn't even know about the side object.
    o1_key = get_inventory_value(o1, "side_key")
    o2_key = get_inventory_value(o2, "side_key")

    # Update the engine relationship for 2d map graphics
    sim.set_side_relationship(o1_key, o2_key, relation)
    signal_emit("side_relations_updated", {"side1": o1, "side2": o2, "relation": relation, "old_relation": old_relation})

def side_get_relations(side1, side2):
    """
    Get the relations value of the two sides.

    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns:
        sbs.DIPLOMACY: The relations value, e.g. `sbs.DIPLOMACY.ALLIED`
            * UNKNOWN
            * NEUTRAL
            * ALLIED
            * HOSTILE
    """
    sbs = FrameContext.context.sbs

    if side_are_allies(side1,side2):
        return sbs.DIPLOMACY.ALLIED
    if side_are_enemies(side1,side2):
        return sbs.DIPLOMACY.HOSTILE
    if side_are_neutral(side1, side2):
        return sbs.DIPLOMACY.NEUTRAL
    else:
        return sbs.DIPLOMACY.UNKNOWN

def side_are_same_side(side1, side2)->bool:
    """
    Check if the two objects have the same side.
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns:
        bool: True if the sides are the same.
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return o1==o2
    
def side_are_allies(side1, side2)->bool:
    """
    Check if the specified sides are allies.
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns: 
        bool: True if they are allies, otherwise False
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return has_link_to(o1, "side_ally", o2)


def side_are_enemies(side1, side2)->bool:
    """
    Check if the specified sides are enemies.
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns: 
        bool: True if they are enemies, otherwise False
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return has_link_to(o1, "side_hostile", o2)
    
def side_are_neutral(side1, side2)->bool:
    """
    Check if the specified sides are neutral (neither enemies nor allies).
    Args:
        side1 (str | int): the key or id of the first side
        side2 (str | int): the key or id of the second side
    Returns: 
        bool: True if they are neutral, otherwise False
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return has_link_to(o1, "side_neutral", o2)
    
def side_set_icon_color(key_or_id, color)->None:
    """
    Set the icon color for the specified side. This will change the color of ships on the 2d map.
    Args:
        key_or_id (str | int): The key or id of the side to set the icon color for.
        color (str): The hexidecimal color code, or named color, to set the side's icon color to. For example, "#F00" or "#FF0000" or "red" for red, "#0F0" or "#00FF00" or "green" for green, etc.
    """
    # TODO: Is transparency supported in the color code? I would think not but should check.
    id = to_side_id(key_or_id)
    if id is not None:
        key = get_inventory_value(id, "side_key")
        set_inventory_value(id, "side_color", color)
        FrameContext.context.sim.set_side_icon_color(key, color)

def side_get_side_color(key_or_id, default="#0F0")->str:
    """
    Get the icon color for the specified side.
    Args:
        key_or_id (str | int | Agent): The Key, ID, or agent of the side
        default (str, optional): The color code to use if the side or side's color isn't found. Default is `#0F0` (red).
    Returns:
        str: The hexidecimal color code assigned to the side.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        return get_inventory_value(id, "side_color", default)
    return default
    
def side_is_color_used(color)->bool:
    """
    Check if the color is used by any side.
    Args:
        color (str): The hexidecmial color code to check for.
    Returns:
        bool: True if any side uses the specified color.
    """
    for side in sides_set():
        if side_get_side_color(side, color):
            return True
    return False

def side_get_description(key_or_id)->str:
    """
    Get the side description.
    Args:
        key_or_id (str | int | Agent): The side
    Returns:
        str: The description of the side.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        return get_inventory_value(id, "side_desc","")
    return ""

def side_set_description(key_or_id, desc)->None:
    """
    Set the side description
    Args:
        key_or_id (str | int | Agent): The side id or key or object.
        desc (str): The new description.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        set_inventory_value(id, "side_desc", desc)

def side_get_display_name(key_or_id)->str:
    """
    Get the side display name.
    Args:
        key_or_id (str | int | Agent): The side
    Returns:
        str: The name of the side.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        return get_inventory_value(id, "side_name","")
    return ""

def side_set_display_name(key_or_id, name)->None:
    """
    Set the side's display name and update the side name of all ships on that side.
    Args:
        key_or_id (str | int | Agent): The side id or key or object.
        desc (str): The new description.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        set_inventory_value(key_or_id, "side_name", name)
        ships = side_members_set(id)
        side_set_object_side(ships, id)

