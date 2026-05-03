from ..helpers import FrameContext
from .query import to_object, set_data_set_value, get_data_set_value

# Set default values here.
torp_keys = dict()
torp_keys["speed"] = 10
torp_keys["lifetime"] = 25
torp_keys["flare_color"] = "white"
torp_keys["trail_color"] = "white"
torp_keys["warhead"] = "standard"
torp_keys["blast_radius"] = 1000
torp_keys["damage"] = 35
torp_keys["explosion_size"] = 10
torp_keys["explosion_color"] = "fire"
torp_keys["behavior"] = "homing"
torp_keys["energy_conversion_value"] = 100

def torpedo_type(
        key:str,
        gui_text=None,
        speed:int=10,
        lifetime:int=25,
        flare_color:str="white",
        trail_color:str="white",
        warhead:str="standard",
        blast_radius:int=1000,
        damage:int=35,
        explosion_size:int=10,
        explosion_color:str="fire",
        behavior:str="homing",
        energy_conversion_value:int=100,
        other:str=None
        ):
    """
    Define a new type of torpedo for use by the players.
    * The torpedo system is still being developed, with new behaviors and warheads in the pipeline.
    * Additional entries may be added in the future to allow further customization. The `other` argument can be filled with these additional entries if they are not yet included in the function.

    Args:
        key (str): The key by which the torpodo is identified.
        gui_text (str, optional): The name of the torpedo as seen by the players. If None, then will be the same as the key.
        speed (int, optional): The speed at which the torpedo moves. Default is 10.
        lifetime (int, optional): How long (in seconds) the torpedo continues to move. Default is 25.
        flare_color (str, optional): The color of the torpedo's exhuast flare. Default is white.
        trail_color (str, optional): The color of the torpedo's exhaust trail. Default is white.
        warhead (str, optional): A comma-separated string defining the behavior of the warhead upon contact. Default is standard.
            * standard - the default behavior of damaging a single target upon hit.
            * blast - creates an area of effect with diminishing effects as the distance from the blast epicenter increases.
            * reduce_shields - reduces the shields of the target(s). (EMP)
        blast_radius (int, optional): How large the area of effect should be, if `warhead` has the type "blast". Default is 1000.
        damage (int, optional): The base damage dealt to the target. If `warhead` has the type "blast", damage decreases depending on the distance from the blast's epicenter. Default is 5.
        explosion_size (int, optional): The size of the explosion visual effect on the 3d view. Default is 10.
        explosion_color (str, optional): The color of the explosion visual effect on the 3d view. Default is "fire".
        behaviour (str, optional): The behavior of the torpedo guidance system. Default is homing.
            * homing - the torpedo will home in on its target, compensating for movement.
            * mine - the torpedo will not move after it has been placed and will detonate when a ship gets close.
        energy_conversion_value (int, optional): The amount of energy to provide to the ship by disassembling the torpedo. Default is 100.
        other (str, optional): Additional arguments to add, using the format "key1:value1;key2:value2;"
    """
    if gui_text is None:
        gui_text = key
    

    string = f"gui_text:{gui_text};speed:{speed};lifetime:{lifetime};flare_color:{flare_color};trail_color:{trail_color};warhead:{warhead};damage:{damage};explosion_size:{explosion_size};explosion_color:{explosion_color};behavior:{behavior};energy_conversion_value:{energy_conversion_value};"
    if warhead.find("blast") > -1:
        string += f"blast_radius:{blast_radius};"
    if other is not None:
        string += other
    FrameContext.context.sbs.set_shared_string(key, string)

def torpedo_type_string(key:str, string:str):
    """
    Define a torpedo type using the values specified in the string. Values that are not included will use default values.
    E.g. if you use `torpedo_type_string("SomeTorp","gui_text:Type 42;damage:12")`, it will make a homing torpedo called the Type 42 that does 12 damage, and all the other values will be identical to a regular homing torpedo.
    Args:
        key (str): The key by which the torpodo is identified.
        string (str): The torpedo value string containing any non-default values.
    """
    global torp_keys
    d = parse_torp_string(string)
    ret = string.strip()
    if not ret.endswith(";"):
        ret += ";"
    if d.get("gui_text") is None:
        ret = ret + f"gui_text:{key};"
    for key in torp_keys.keys():
        if d.get(key) is None:
            ret += f"{key}:{torp_keys.get(key)};"
    FrameContext.context.sbs.set_shared_string(key, ret)

    

def parse_torp_string(torp_string:str) -> dict:
    """
    Convert a torpedo value string to a dictionary of key:value.
    Args:
        torp_string (str): The torp string, in a "key1:value1; key2:value2;" format.
    Returns:
        dict: A dictionary.
    """
    split = torp_string.split(";")
    d = dict()
    for keyval in split:
        arr = keyval.split(":")
        key = arr[0].strip()
        if key == "":
            continue
        if arr[1]:
            val = arr[1].strip()
            d[key] = val
        else:
            d[key] = None
            print(f"Dict value not found: '{keyval}'")
    return d

def get_torp_value_string(key:str)->str:
    """
    Get the torp value string, provided the key for the torpedo type.
    The torp value string is a css-style string containing values such as the torpode speed, damage, and behavior.

    Args:
        key (str): The key of the torpedo type.
    Returns:
        str: The torpedo value string.
    """
    return FrameContext.context.sbs.get_shared_string(key)

def get_torp_string_value_dict(key:str)->dict:
    """
    Get a dictionary of torp string keys for the specified topedo key.
    Args:
        key (str): The key representing the torpedo type.
    Returns:
        dict: Dictionary containing the keys and values for each torpedo value.
    """
    torp = get_torp_value_string(key)
    return parse_torp_string(torp)

def torp_update_value(key:str, attribute_name:str, value:str):
    """
    Update one attribute of a specified torpedo type.
    Args:
        key (str): The key of the torpedo to modify.
        attribute_name (str): The name of the attribute to modify
        value (str): The new value for the attribute
    """
    torp = get_torp_string_value_dict(key)
    torp[attribute_name] = value
    torp_string = ""
    for attr, val in torp:
        torp_string = torp_string + attr + ": " + val + "; "
    return torp_string

# NOTE: Since as far as I've been able to determine, there's no way to get a list of all torpedoes 
# defined on the server without somehow parsing the whole shared string, I figured being able to 
# at least get all the ones for a given ship would be helpful.
def torpedo_get_count_for_ship(id, key) -> tuple[int,int]:
    """
    Get the count and the maximum of the specified torpedo type for the ship.
    Args:
        id (int | Agent): The ship
        key (str): The key representing the torpedo type.
    Returns:
        tuple[int,int] | None: The number of torpedoes and the maximum number of those torpdoes that can fit on the ship
    """
    obj = to_object(id)
    if obj is not None:
        count = get_data_set_value(id, f"{key}_NUM")
        if count is None:
            count = 0
        max = get_data_set_value(id, f"{key}_MAX")
        if max is None:
            max = 0
        return (count, max)
    return (0,0)

def torpedo_get_available_types_for_ship(id) -> list[str]:
    """
    Get a list of the keys for all the torpedo types currently available to a player ship.
    Args:
        id (int | Agent): The id of the ship, or the Agent representing it.
    Returns:
        list[str]: The list of torpedo keys.
    """
    obj = to_object(id)
    if obj is not None:
        types = get_data_set_value(id,"torpedo_types_available")
        if isinstance(types, str):
            type_list = types.split(",")
            return type_list
    return list()

def torpedo_make_available(id, key:str, count:int=0) -> None:
    """
    Make a torpedo type available to a player ship. The torpedo type must be defined using `torpedo_type()` or `torpedo_type_string()` before it can be made available.
    Args:
        id (int | Agent): The id of the torpedo to make available. This is the id that will be used in the ship's loadout to specify this torpedo.
        key (str): The key of the torpedo type to make available.
        count (int, optional): The number of torpedoes of this type to add to the ship's inventory. Default is 0.
    """
    obj = to_object(id)
    if obj is not None:
        types = get_data_set_value(id,"torpedo_types_available")
        if types is None:
            types = ""
        if isinstance(types, str):
            type_list = types.split(",")
            if key not in type_list:
                type_list.append(key)
                new_types = ",".join(type_list)
                set_data_set_value(id,"torpedo_types_available", new_types)
                set_data_set_value(id, f"{key}_NUM", count)

def torpedo_make_unavailable(id, key:str) -> None:
    """
    Make a torpedo type unavailable to a player ship. The torpedo type must be defined using `torpedo_type()` or `torpedo_type_string()` before it can be made unavailable.
    Args:
        id (int | Agent): The id of the torpedo to make unavailable. This is the id that will be used in the ship's loadout to specify this torpedo.
        key (str): The key of the torpedo type to make unavailable.
    """
    obj = to_object(id)
    if obj is not None:
        types = get_data_set_value(id,"torpedo_types_available")
        if types is None:
            types = ""
        if isinstance(types, str):
            type_list = types.split(",")
            if key in type_list:
                type_list.remove(key)
                new_types = ",".join(type_list)
                set_data_set_value(id,"torpedo_types_available", new_types)
                set_data_set_value(id, f"{key}_NUM", 0)

