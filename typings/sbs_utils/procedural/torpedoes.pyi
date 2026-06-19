from sbs_utils.helpers import FrameContext
def get_data_set_value (id_or_obj, key, index=0):
    """Get a value from the engine data-set (blob) of a space or grid object.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
    
    Returns:
        any: The stored value, or ``None`` if the object or key is not found."""
def get_torp_string_value_dict (key: str) -> dict:
    """Return a parsed attribute dictionary for a registered torpedo type.
    
    Args:
        key (str): Torpedo type identifier.
    
    Returns:
        dict: Attribute → value mapping for the torpedo."""
def get_torp_value_string (key: str) -> str:
    """Return the raw attribute string for a registered torpedo type.
    
    Args:
        key (str): Torpedo type identifier.
    
    Returns:
        str: The ``"attr:value;..."`` string, or ``None`` if not found."""
def parse_torp_string (torp_string: str) -> dict:
    """Parse a torpedo attribute string into a ``{attr: value}`` dictionary.
    
    Args:
        torp_string (str): Attribute string in ``"attr:value;attr:value;"`` format.
    
    Returns:
        dict: Parsed attribute → value mapping."""
def set_data_set_value (to_update, key, value, index=0):
    """Set a value in the engine data-set (blob) for one or more space or grid objects.
    
    If ``to_update`` is a set or list, the value is applied to each member.
    
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The
            agent(s) to update.
        key (str): The data-set key.
        value (any): The value to store.
        index (int, optional): The slot index within that key. Defaults to 0."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def torp_get_attribute_value (key: str, attribute_name: str) -> str:
    """Return the value of a single attribute from a registered torpedo type.
    
    See ``torpedo_type`` for valid attribute names (e.g. ``"damage"``,
    ``"speed"``, ``"behavior"``).
    
    Args:
        key (str): Torpedo type identifier.
        attribute_name (str): The attribute to read.
    
    Returns:
        str: The attribute's value, or ``None`` if the torpedo type or
            attribute does not exist."""
def torp_update_value (key: str, attribute_name: str, value: str | int):
    """Update a single attribute of a registered torpedo type.
    
    See ``torpedo_type`` for valid attribute names (e.g. ``"damage"``,
    ``"speed"``, ``"behavior"``).
    
    Args:
        key (str): Torpedo type identifier.
        attribute_name (str): The attribute to update.
        value (str | int): The new value."""
def torpedo_get_available_types_for_ship (id) -> list[str]:
    """Return the torpedo type keys currently available to a player ship.
    
    Args:
        id (int | Agent): The player ship.
    
    Returns:
        list[str]: Torpedo type key strings, or an empty list if none."""
def torpedo_get_count_for_ship (id, key) -> tuple[int, int]:
    """Return the current count and maximum capacity of a torpedo type on a ship.
    
    Args:
        id (int | Agent): The player ship.
        key (str): Torpedo type identifier.
    
    Returns:
        tuple[int, int]: ``(current_count, max_capacity)``, or ``(0, 0)`` if
            the torpedo type is not available on the ship."""
def torpedo_make_available (id, key: str, count: int = 0, fill: bool = True) -> None:
    """Add a torpedo type to a player ship's loadout.
    
    The torpedo type must first be registered with ``torpedo_type`` or
    ``torpedo_type_string``.
    
    Args:
        id (int | Agent): The player ship.
        key (str): Torpedo type identifier.
        count (int, optional): Maximum capacity and initial count. Defaults to
            0.
        fill (bool, optional): If ``True``, set the current count to ``count``
            (fill to max). Defaults to True."""
def torpedo_make_unavailable (id, key: str) -> None:
    """Remove a torpedo type from a player ship's loadout and zero its count.
    
    Args:
        id (int | Agent): The player ship.
        key (str): Torpedo type identifier to remove."""
def torpedo_type (key: str, gui_text=None, speed: int = 10, lifetime: int = 25, flare_color: str = 'white', trail_color: str = 'white', warhead: str = 'standard', blast_radius: int = 1000, damage: int = 35, explosion_size: int = 10, explosion_color: str = 'fire', behavior: str = 'homing', energy_conversion_value: int = 100, other: str = None):
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
            e.g. ``"key1:value1;key2:value2;"``. Defaults to None."""
def torpedo_type_string (key: str, string: str):
    """Define a torpedo type from a CSS-style attribute string, filling missing values with defaults.
    
    Useful when the torpedo definition originates from a data file or dynamic
    string rather than explicit Python parameters. Any attribute omitted from
    ``string`` inherits its default from ``torp_keys``.
    
    Args:
        key (str): Unique identifier for this torpedo type.
        string (str): Attribute string in ``"attr:value;attr:value;"`` format.
            See ``torpedo_type`` for valid attribute names.
    
    Example:
        torpedo_type_string("Type42", "gui_text:Type 42;damage:12")"""
