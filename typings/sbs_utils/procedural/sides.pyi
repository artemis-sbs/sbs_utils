from sbs_utils.helpers import FrameContext
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
def has_link (link_name: str):
    """Return the set of agent IDs that have at least one link under a given name.
    
    Despite the ``has_`` prefix this returns a set, not a bool. Use the result
    to iterate or test membership.
    
    Args:
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all agents that own a link entry with this name."""
def has_link_to (link_source, link_name: str, link_target) -> bool:
    """Return whether a source agent has a specific link to a target.
    
    Args:
        link_source (Agent | int): The agent ID or object hosting the link.
        link_name (str): The link key name.
        link_target (Agent | int): The target agent ID or object to check.
    
    Returns:
        bool: ``True`` if the link from source to target exists."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
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
def side_ally_members_set (side):
    """Return the set of agent IDs from all sides allied with the given side.
    
    Args:
        side (str | int | Agent): Side key, side agent ID, or any space object
            whose side will be used.
    
    Returns:
        set[int]: IDs of all space objects on allied sides."""
def side_are_allies (side1, side2) -> bool:
    """Return whether two sides are allied.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides have a ``side_ally`` link."""
def side_are_enemies (side1, side2) -> bool:
    """Return whether two sides are hostile to each other.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides have a ``side_hostile`` link."""
def side_are_neutral (side1, side2) -> bool:
    """Return whether two sides are neutral toward each other.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides have a ``side_neutral`` link."""
def side_are_same_side (side1, side2) -> bool:
    """Return whether two references resolve to the same side.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if both resolve to the same side agent."""
def side_display_name (key):
    """Return the display name of a side.
    
    Args:
        key (str | int | Agent): Side key, agent ID, or agent.
    
    Returns:
        str: The side's display name, or ``None`` if not found."""
def side_enemy_members_set (side):
    """Return the set of agent IDs from all sides hostile to the given side.
    
    Args:
        side (str | int | Agent): Side key, side agent ID, or any space object
            whose side will be used.
    
    Returns:
        set[int]: IDs of all space objects on hostile sides."""
def side_get_description (key_or_id) -> str:
    """Return the description text of a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
    
    Returns:
        str: The side description, or ``""`` if not set."""
def side_get_display_name (key_or_id) -> str:
    """Return the display name of a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
    
    Returns:
        str: The side's display name, or ``""`` if not set."""
def side_get_relations (side1, side2):
    """Return the current diplomatic relationship between two sides.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        sbs.DIPLOMACY: One of ``ALLIED``, ``HOSTILE``, ``NEUTRAL``, or
            ``UNKNOWN``."""
def side_get_side_color (key_or_id, default='#0F0') -> str:
    """Return the icon color assigned to a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        default (str, optional): Color to return if the side has no color set.
            Defaults to ``"#0F0"`` (green).
    
    Returns:
        str: The hex color code assigned to the side, or ``default``."""
def side_get_side_icon_index (key_or_id) -> int:
    """Return the icon index for a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
    
    Returns:
        int: The icon index, or ``-1`` if not found."""
def side_is_color_used (color) -> bool:
    """Return whether any side is currently using a given icon color.
    
    Args:
        color (str): Hex color code to check for.
    
    Returns:
        bool: ``True`` if at least one side uses that color."""
def side_keys_set ():
    """Return the set of key strings for all registered sides.
    
    Returns:
        set[str]: Side key strings (e.g. ``"player"``, ``"enemy"``)."""
def side_members_set (side):
    """Return the set of agent IDs that belong to a given side.
    
    Prefer this over ``role(side)`` as it correctly excludes the side agent
    itself from the result.
    
    Args:
        side (str | int | Agent): Side key, side agent ID, side agent, or any
            space object whose side will be used.
    
    Returns:
        set[int]: IDs of all space objects on the specified side."""
def side_set_description (key_or_id, desc) -> None:
    """Set the description text for a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        desc (str): The new description text."""
def side_set_display_name (key_or_id, name) -> None:
    """Set the display name for a side and update all ships on that side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        name (str): The new display name."""
def side_set_icon_color (key_or_id, color) -> None:
    """Set the icon color for a side, changing how its ships appear on the 2D map.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        color (str): Hex color code or named color (e.g. ``"#FF0000"`` or
            ``"red"``)."""
def side_set_object_side (id_or_obj, key) -> None:
    """Assign a side to one or more space objects.
    
    Updates both the ``side`` (key) and ``side_display`` (name) attributes on
    each object.
    
    Args:
        id_or_obj (int | Agent | list[int | Agent] | set[int | Agent]):
            The object(s) to update.
        key (str | int | Agent): The target side — a key string, side agent ID,
            or any object whose side will be used."""
def side_set_relations (side1, side2, relation):
    """Set the diplomatic relationship between two sides.
    
    Updates both the link-based relationship used by the scripting API and the
    engine's own side relationship table for 2D map rendering. Emits the
    ``side_relations_updated`` signal.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
        relation (sbs.DIPLOMACY): New relationship value. Use
            ``sbs.DIPLOMACY.ALLIED``, ``HOSTILE``, ``NEUTRAL``, or
            ``UNKNOWN``."""
def side_set_ship_allies_and_enemies (ship):
    """No-op placeholder — deprecated as of v1.3.0, to be removed in a future version.
    
    Args:
        ship (Agent | int): Unused."""
def side_set_side_icon_index (key_or_id, icon_index) -> None:
    """Set the icon index for a side, changing how its ships appear on the 2D map.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        icon_index (int): The icon index to use."""
def sides_set ():
    """Return the set of IDs for all registered sides (agents with the ``__side__`` role).
    
    Returns:
        set[int]: IDs of all side agents."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_side_id (key_or_id_or_object):
    """Resolve any side reference to the side agent's ID.
    
    Accepts a side key string, a side agent ID, a side agent object, or any
    space object (in which case its side property is used).
    
    Args:
        key_or_id_or_object (str | int | Agent): Side key, side agent ID, side
            agent, or a space object whose side should be resolved.
    
    Returns:
        int | None: The side agent ID, or ``None`` if not found."""
def to_side_object (key_or_id):
    """Resolve any side reference to the side agent object.
    
    Args:
        key_or_id (str | int | Agent): Side key, side agent ID, or any space
            object whose side will be resolved.
    
    Returns:
        Agent | None: The side agent, or ``None`` if not found."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).
    
    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The space-object agent, or ``None``."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
