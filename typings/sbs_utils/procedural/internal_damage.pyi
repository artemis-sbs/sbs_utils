from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def all_roles (roles: str):
    """Return the set of agent IDs that hold every one of the given roles.
    
    Args:
        roles (str): A comma-separated list of role names.
    
    Returns:
        set[int]: IDs of agents that have all specified roles."""
def comms_broadcast (ids_or_obj, msg, color=None) -> None:
    """Send a text message to the text waterfall of one or more targets.
    
    Accepts player ship IDs or client/console IDs. Ship IDs use
    ``send_message_to_player_ship``; client IDs use
    ``send_message_to_client``.
    
    Args:
        ids_or_obj: Agent ID, client ID, or set/list of either to send to.
            Pass ``None`` to send to the event's ``parent_id``.
        msg (str): The message text. Supports ``{var}`` interpolation.
        color (str, optional): Text color as a name or hex string, e.g.
            ``"red"`` or ``"#3ff"``. Defaults to ``"#fff"``.
    
    Example:
        comms_broadcast(SHIP_ID, "Red alert!", color="red")"""
def convert_system_to_string (the_system):
    """Convert a ship system enum or integer to its role-name string.
    
    Args:
        the_system (sbs.SHPSYS | int | str): The system enum, integer index,
            or role-name string.
    
    Returns:
        str: Role name for the system (``"weapon"``, ``"engine"``,
            ``"sensor"``, or ``"shield"``)."""
def explode_player_ship (id_or_obj):
    """Mark a player ship as destroyed and emit the ``player_ship_destroyed`` signal.
    
    The ship is made invisible and tagged ``"exploded"`` rather than deleted
    immediately, allowing scripts to react before removal.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_pos (id_or_obj):
    """Return the current position of an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        Vec3 | None: The agent's position, or ``None`` if it does not exist."""
def grid_apply_system_damage (id_or_obj):
    """Update system-damage counts and coefficients; explode the ship if all nodes are damaged.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
    
    Returns:
        bool: ``True`` if the ship has been destroyed, ``False`` otherwise."""
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_count_grid_data (ship_key, role, default=0):
    """Count the number of grid items that have a given role in the ship's JSON data.
    
    Args:
        ship_key (str): The ship art-ID key to look up in the grid data.
        role (str): Role name to match against each grid item's role list.
        default (int, optional): Value returned if the ship key is not found in
            the grid data. Defaults to 0.
    
    Returns:
        int: Number of grid items with the specified role."""
def grid_damage_grid_object (ship_id, grid_id, damage_color):
    """Mark a grid object as damaged and apply a damage color to its icon.
    
    Tools, markers, and rally-point objects are ignored.
    
    Args:
        ship_id (Agent | int): The player ship agent ID or object.
        grid_id (Agent | int): The grid object to damage.
        damage_color (str): Color to apply to the damaged grid-object icon."""
def grid_damage_hallway (id_or_obj, loc_x, loc_y, damage_color):
    """Spawn a fire/damage marker at an empty hallway grid cell.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        loc_x (int): Grid column of the hallway cell.
        loc_y (int): Grid row of the hallway cell.
        damage_color (str): Color to apply to the damage marker icon."""
def grid_damage_pos (id_or_obj, loc_x, loc_y):
    """Apply internal damage at a specific grid cell.
    
    If no grid object occupies the cell a hallway-fire marker is placed
    instead.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        loc_x (int): Grid column to damage.
        loc_y (int): Grid row to damage."""
def grid_damage_system (id_or_obj, the_system=None):
    """Damage a random undamaged grid node for the specified ship system.
    
    Args:
        id_or_obj (Agent | int | CloseData | SpawnData): The player ship.
        the_system (sbs.SHPSYS | int | str, optional): The system to damage.
            If ``None``, a system is chosen at random. Defaults to None.
    
    Returns:
        bool: ``True`` if a node was damaged; ``False`` if no undamaged nodes
            remain or the ship has already exploded."""
def grid_get_grid_current_theme ():
    """Get the currently active grid theme data.
    
    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc."""
def grid_get_grid_data () -> dict:
    """Get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid data objects.
        * key (str): The key of the dict, which is a ship key as defined in shipData.
        * value (dict): A dict with `grid_objects` as a key, and a list of grid object data as the value."""
def grid_get_item_theme_data (roles, name=None):
    """Get icon, scale, color, and damage color for a set of roles from the grid theme.
    
    Roles are matched in reverse priority order so the last role in the list
    takes precedence. Falls back to ``"default"`` entries when no role matches.
    
    Args:
        roles (str): Comma-separated role names.
        name (str | None, optional): Theme name to use. ``None`` uses the
            current theme. Defaults to None.
    
    Returns:
        RetVal: Object with ``.icon`` (int), ``.scale`` (float), ``.color``
            (str), and ``.damage_color`` (str) attributes."""
def grid_get_max_hp ():
    """Return the current global maximum HP value for damcon-team grid objects.
    
    Returns:
        int: The max HP setting (default 6)."""
def grid_objects (so_id) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship
    
    Args:
        so_id (Agent | int): agent id or object
    
    Returns:
        set[int]: a set of agent ids"""
def grid_objects_at (so_id, x, y) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship, at the location specified
    
    Args:
        so_id (Agent | int): agent id or object
        x (int): The x grid location
        y (int): The y grid location
    
    Returns:
        set[int]: A set of agent ids"""
def grid_rebuild_grid_objects (id_or_obj, grid_data=None):
    """Rebuild all engineering-grid objects on a ship from shipData JSON.
    
    Deletes all existing grid objects for the ship, then re-creates them from
    the grid layout defined in the ship's art-ID entry in ``grid_data``.
    Also re-creates the damcon teams, the position marker, and the EPad.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        grid_data (dict, optional): Pre-loaded grid data. If ``None``, loaded
            via ``grid_get_grid_data()``."""
def grid_repair_grid_objects (player_ship, id_or_set, who_repaired=None):
    """Repair one or more grid objects and update the ship's damage state.
    
    Hallway-fire markers are deleted; system nodes have their icon color
    restored and the system-damage count decremented. Recomputes damage
    coefficients if any system node was healed.
    
    Args:
        player_ship (Agent | int): The player ship agent ID or object.
        id_or_set (Agent | int | set[Agent | int]): Grid object(s) to repair.
        who_repaired (Agent | int, optional): The damcon-team agent that
            performed the repair (used to remove work-order links). Defaults
            to None."""
def grid_repair_system_damage (id_or_obj, the_system=None):
    """Repair a single damaged grid node for the specified system.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        the_system (sbs.SHPSYS | int | str, optional): The system to repair.
            If ``None``, a system is chosen at random. Defaults to None.
    
    Returns:
        bool: ``True`` if a node was repaired; ``False`` if no damaged nodes
            remain for that system."""
def grid_restore_damcons (id_or_obj):
    """Restore all damcon teams on a ship to full health, creating them if missing.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object."""
def grid_set_hp (ship_id, GRID_OBJECT_ID, hp):
    """Set the HP of a damcon-team grid object and emit the ``life_form_hp_changed`` signal.
    
    Args:
        ship_id (Agent | int): The player ship agent ID or object.
        GRID_OBJECT_ID (Agent | int): The damcon-team grid object ID or agent.
        hp (int): The new HP value to assign."""
def grid_set_max_hp (max_hp):
    """Set the global maximum hit-point value for damcon-team grid objects.
    
    Args:
        max_hp (int): New maximum HP value. Defaults to 6 at module load."""
def grid_spawn (id, name, tag, x, y, icon_index, color, roles):
    """Spawn a grid object (engineering component) onto a ship's grid.
    
    Args:
        id (Agent | int): The ship agent ID or object to attach the grid object
            to.
        name (str): Display name of the grid object.
        tag (str): Tag identifying the grid object's side or type.
        x (int): Column position on the engineering grid.
        y (int): Row position on the engineering grid.
        icon_index (int): Icon index for the grid display.
        color (str): Display color string.
        roles (str): Comma-separated roles to assign to the grid object.
    
    Returns:
        GridObject: The newly created grid object."""
def grid_take_internal_damage_at (id_or_obj, source_point, system_hit=None, damage_amount=None):
    """Apply internal damage to a ship at a 3D world position.
    
    Maps the 3D position to the nearest grid cell, then damages the grid
    objects at that cell (or a hallway marker if the cell is empty). Also
    injures any damcon-team lifeforms at the impact location.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        source_point (Vec3): 3D position of the hit.
        system_hit (sbs.SHPSYS | int | str, optional): Unused. Defaults to
            None.
        damage_amount (int, optional): Unused. Defaults to None.
    
    Returns:
        bool: ``True`` if the ship was destroyed by this damage."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def is_dev_build ():
    """Check if the current mission is a development build.
    
    Returns True if a .git directory exists in the mission folder.
    
    Returns:
        bool: True if running in development mode, False otherwise."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def prefab_spawn (label, data=None, OFFSET_X=None, OFFSET_Y=None, OFFSET_Z=None):
    """Spawn a prefab label as an independent task and return it.
    
    Positional keys ``START_X``, ``START_Y``, ``START_Z`` inside ``data``
    set the spawn origin (default 0). The ``OFFSET_*`` params shift that
    origin without modifying the original ``data`` dict. If ``data`` contains
    a ``NAME`` key with a ``#`` placeholder, ``prefab_autoname`` is applied
    to generate a unique name.
    
    Args:
        label (str | Label): The label to spawn.
        data (dict, optional): Variables passed into the prefab task. May
            include ``START_X``, ``START_Y``, ``START_Z``, and ``NAME``.
            Defaults to None.
        OFFSET_X (float, optional): X offset added to ``START_X``. Defaults
            to None (no offset).
        OFFSET_Y (float, optional): Y offset added to ``START_Y``. Defaults
            to None (no offset).
        OFFSET_Z (float, optional): Z offset added to ``START_Z``. Defaults
            to None (no offset).
    
    Returns:
        MastAsyncTask: The running prefab task, or ``None`` if the label is
            invalid."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def respawn_player_ship (id_or_obj):
    """Respawn a previously destroyed player ship at its original spawn position.
    
    Restores the ship's art ID, repositions it to the spawn point, and removes
    the ``"exploded"`` role.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_damage_coefficients (id_or_obj):
    """Recalculate and write the damage coefficients for all ship systems.
    
    For each system (beam, torpedo, impulse, warp, maneuver, sensors, shields)
    computes the ratio of undamaged to total nodes and writes it to the blob.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def settings_get_defaults ():
    """Return the merged default settings dict, loading ``settings.yaml`` or ``setup.json`` if present.
    
    Results are cached after the first call. Mission-specific values from the
    YAML/JSON file override the built-in defaults.
    
    Returns:
        dict: The default settings mapping."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a list.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        list: A list containing whatever was passed in; ``None`` becomes ``[]``."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
