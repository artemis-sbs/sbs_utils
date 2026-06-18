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
    """Define and register a torpedo type on the server.

    The torpedo system is actively evolving; new behaviors and warheads will be
    added in future versions. Use ``other`` to pass attributes not yet exposed
    as named params in the format ``"key1:value1;key2:value2;"``.

    Args:
        key (str): Unique identifier for this torpedo type.
        gui_text (str, optional): Player-visible name. Defaults to ``key``.
        speed (int, optional): Movement speed. Defaults to 10.
        lifetime (int, optional): Seconds before the torpedo expires. Defaults
            to 25.
        flare_color (str, optional): Exhaust flare color. Defaults to
            ``"white"``.
        trail_color (str, optional): Exhaust trail color. Defaults to
            ``"white"``.
        warhead (str, optional): Comma-separated warhead behaviors.
            ``"standard"`` damages a single target; ``"blast"`` creates an
            area-of-effect; ``"reduce_shields"`` acts as an EMP. Defaults to
            ``"standard"``.
        blast_radius (int, optional): AoE radius when ``warhead`` includes
            ``"blast"``. Defaults to 1000.
        damage (int, optional): Base damage on impact. Defaults to 35.
        explosion_size (int, optional): Visual explosion size. Defaults to 10.
        explosion_color (str, optional): Visual explosion color. Defaults to
            ``"fire"``.
        behavior (str, optional): Guidance behavior. ``"homing"`` tracks the
            target; ``"mine"`` stays in place and detonates on proximity.
            Defaults to ``"homing"``.
        energy_conversion_value (int, optional): Energy returned when the
            torpedo is disassembled. Defaults to 100.
        other (str, optional): Additional key-value pairs not yet in the API,
            e.g. ``"key1:value1;key2:value2;"``. Defaults to None.
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
    """Define a torpedo type from a CSS-style attribute string, filling missing values with defaults.

    Useful when the torpedo definition originates from a data file or dynamic
    string rather than explicit Python parameters. Any attribute omitted from
    ``string`` inherits its default from ``torp_keys``.

    Args:
        key (str): Unique identifier for this torpedo type.
        string (str): Attribute string in ``"attr:value;attr:value;"`` format.
            See ``torpedo_type`` for valid attribute names.

    Example:
        torpedo_type_string("Type42", "gui_text:Type 42;damage:12")
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
    """Parse a torpedo attribute string into a ``{attr: value}`` dictionary.

    Args:
        torp_string (str): Attribute string in ``"attr:value;attr:value;"`` format.

    Returns:
        dict: Parsed attribute → value mapping.
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
    """Return the raw attribute string for a registered torpedo type.

    Args:
        key (str): Torpedo type identifier.

    Returns:
        str: The ``"attr:value;..."`` string, or ``None`` if not found.
    """
    return FrameContext.context.sbs.get_shared_string(key)

def get_torp_string_value_dict(key:str)->dict:
    """Return a parsed attribute dictionary for a registered torpedo type.

    Args:
        key (str): Torpedo type identifier.

    Returns:
        dict: Attribute → value mapping for the torpedo.
    """
    torp = get_torp_value_string(key)
    return parse_torp_string(torp)

def torp_update_value(key:str, attribute_name:str, value:str|int):
    """Update a single attribute of a registered torpedo type.

    See ``torpedo_type`` for valid attribute names (e.g. ``"damage"``,
    ``"speed"``, ``"behavior"``).

    Args:
        key (str): Torpedo type identifier.
        attribute_name (str): The attribute to update.
        value (str | int): The new value.
    """
    torp = get_torp_string_value_dict(key)
    torp[attribute_name] = value
    torp_string = ""
    for attr, val in torp.items():
        torp_string += f"{attr}:{val};"
    FrameContext.context.sbs.set_shared_string(key, torp_string)

def torp_get_attribute_value(key:str, attribute_name:str) -> str:
    """Return the value of a single attribute from a registered torpedo type.

    See ``torpedo_type`` for valid attribute names (e.g. ``"damage"``,
    ``"speed"``, ``"behavior"``).

    Args:
        key (str): Torpedo type identifier.
        attribute_name (str): The attribute to read.

    Returns:
        str: The attribute's value, or ``None`` if the torpedo type or
            attribute does not exist.
    """
    torp = get_torp_string_value_dict(key)
    return torp.get(attribute_name)

# NOTE: Since as far as I've been able to determine, there's no way to get a list of all torpedoes 
# defined on the server without somehow parsing the whole shared string, I figured being able to 
# at least get all the ones for a given ship would be helpful.
# Follow up NOTE: With the new prefab implementation for torps, we can use role("torpedo_definition")
def torpedo_get_count_for_ship(id, key) -> tuple[int,int]:
    """Return the current count and maximum capacity of a torpedo type on a ship.

    Args:
        id (int | Agent): The player ship.
        key (str): Torpedo type identifier.

    Returns:
        tuple[int, int]: ``(current_count, max_capacity)``, or ``(0, 0)`` if
            the torpedo type is not available on the ship.
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
    """Return the torpedo type keys currently available to a player ship.

    Args:
        id (int | Agent): The player ship.

    Returns:
        list[str]: Torpedo type key strings, or an empty list if none.
    """
    obj = to_object(id)
    if obj is not None:
        types = get_data_set_value(id,"torpedo_types_available")
        if isinstance(types, str):
            type_list = types.strip().strip(",").split(",") # remove trailing comma if present
            return type_list
    return list()

def torpedo_make_available(id, key:str, count:int=0, fill:bool=True) -> None:
    """Add a torpedo type to a player ship's loadout.

    The torpedo type must first be registered with ``torpedo_type`` or
    ``torpedo_type_string``.

    Args:
        id (int | Agent): The player ship.
        key (str): Torpedo type identifier.
        count (int, optional): Maximum capacity and initial count. Defaults to
            0.
        fill (bool, optional): If ``True``, set the current count to ``count``
            (fill to max). Defaults to True.
    """
    obj = to_object(id)
    if obj is not None:
        types = get_data_set_value(id,"torpedo_types_available")
        if types is None:
            types = ""
        if isinstance(types, str):
            type_list = types.strip().strip(",").split(",")# remove trailing comma if present
            if key not in type_list:
                type_list.append(key)
                new_types = ",".join(type_list)
                set_data_set_value(id,"torpedo_types_available", new_types)
                set_data_set_value(id, f"{key}_MAX", count)
                if fill: # Set count to max number
                    set_data_set_value(id, f"{key}_NUM", count)

def torpedo_make_unavailable(id, key:str) -> None:
    """Remove a torpedo type from a player ship's loadout and zero its count.

    Args:
        id (int | Agent): The player ship.
        key (str): Torpedo type identifier to remove.
    """
    obj = to_object(id)
    if obj is not None:
        types = get_data_set_value(id,"torpedo_types_available")
        if types is None:
            types = ""
        if isinstance(types, str):
            type_list = types.strip().strip(",").split(",") # remove trailing comma if present
            if key in type_list:
                type_list.remove(key)
                new_types = ",".join(type_list)
                set_data_set_value(id,"torpedo_types_available", new_types)
                set_data_set_value(id, f"{key}_NUM", 0)

