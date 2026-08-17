from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def _grid_damcon_decl (ship_id, layout=None):
    """The hull's damcon declaration, or ``None`` when it declares nothing."""
def _grid_resolve_point (SBS, ship_id, hm, declared, used=None, prefer_empty=True, who=''):
    """Where to put one grid object: the declared cell if it is usable, else the engine's.
    
    ``None`` only when the hull has no usable cell at all.
    
    A DECLARED cell that is occupied is accepted without comment - that is the entire
    point of an interior with no hallway (LM #381), and damcons walk over room cells
    constantly. A declared cell that is off the hull is a WARNING and falls through to the
    finder: one bad coordinate must never leave a ship without damage control, and a
    shipData resize can invalidate a good declaration without anyone touching the floor
    plan. ``grid_ascii_validate`` is where an author is told loudly.
    
    Args:
        SBS: The sbs module.
        ship_id (int): The host ship.
        hm: Its hull map.
        declared (list | None): ``[x, y]`` the interior asked for, if any.
        used (set, optional): ``(x, y)`` cells already taken in this pass, to spread.
        prefer_empty (bool): Try the unoccupied finder before the tolerant one.
        who (str): Name for the warning, e.g. ``"DC2"``.
    
    Returns:
        list[int] | None: ``[x, y]``."""
def _grid_retire_extra_damcons (hm, ship_id, count):
    """Delete DC teams above ``count`` - a hull whose declaration shrank, or a refit.
    
    Matches ``DC<n>`` carrying the ``damcons`` role only, so nothing else on the grid can
    be caught by a name that happens to look like one."""
def _grid_unused_point (hm, point, used):
    """The nearest open cell to ``point`` that is not already in ``used``.
    
    ``point`` itself when it is free, and ``point`` again when the hull has no free cell
    left - a ship with fewer open cells than damcon teams still gets its teams, stacked,
    rather than losing one.
    
    Only reached when the occupancy-tolerant finder had to be used, i.e. on a hull with no
    empty cell. The engine's finders take no "avoid these" argument and have no memory
    across a loop, so spreading the teams is the caller's job.
    
    Args:
        hm: The ship's hull map.
        point (list[int]): ``[x, y]`` the engine chose.
        used (set): ``(x, y)`` cells already taken in this pass.
    
    Returns:
        list[int]: ``[x, y]``."""
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
def comms_broadcast (ids_or_obj, msg, color=None, category=None, severity=None) -> None:
    """Send a text message to the text waterfall of one or more targets.
    
    Accepts player ship IDs or client/console IDs. Ship IDs use
    ``send_message_to_player_ship``; client IDs use
    ``send_message_to_client``.
    
    ALSO appends to the ship's log (``procedural.log_panel``), which is the waterfall's
    replacement - see mkdocs build/messages.md. Both surfaces are written during the changeover
    so they can be compared side by side; retiring the waterfall is then deleting the
    engine half of this function.
    
    Args:
        ids_or_obj: Agent ID, client ID, or set/list of either to send to.
            Pass ``None`` to send to the event's ``parent_id``.
        msg (str): The message text. Supports ``{var}`` interpolation.
        color (str, optional): Text color as a name or hex string, e.g.
            ``"red"`` or ``"#3ff"``. Defaults to ``"#fff"``.
        category (str, optional): Which log TAB this belongs in - ``"ship"`` or
            ``"mission"``. Omitted (the default) means it appears in the Log tab, which
            shows everything, and in no subset tab. That is what makes tagging
            incremental: nothing is lost by not being tagged.
        severity (str, optional): ``"tip"`` / ``"warning"`` / ``"danger"``. Draws the
            entry as a callout. Reserved for things that matter - a box costs two rows,
            so one per line would halve how much log fits on screen.
    
    Example:
        comms_broadcast(SHIP_ID, "Red alert!", color="red", severity="danger")"""
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
def grid_damcon_count (id_or_obj, layout=None):
    """How many damcon teams this ship's interior declares.
    
    ``3`` for every hull that declares nothing, which is nearly all of them.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        layout (str, optional): Layout name. Defaults to the ship's ``grid_layout``.
    
    Returns:
        int: The team count."""
def grid_delete_object (host_id_or_obj, id_or_obj):
    """Delete a single grid object, deferring the native free.
    
    Tombstones the grid agent now (dropped from ``Agent.all``/roles, so
    ``object_exists()``/``to_object()`` report it gone this instant) and enqueues
    the native ``sbs.delete_grid_object(host_id, id)`` to run at the end of the
    event handler. Mirrors ``SpaceObject.delete_object`` for grid objects, closing
    the same-tick use-after-free window. See ``DeleteQueue``.
    
    Args:
        host_id_or_obj (Agent | int): The host ship the grid object lives on.
        id_or_obj (Agent | int): The grid object (or its id) to delete."""
def grid_get_damcons (ship_key, layout=None):
    """The damcon-team declaration for a hull (or one of its layouts), or ``None``.
    
    ``None`` - which is what every hull that says nothing returns, and that is nearly all
    of them - means "three teams, wherever the engine puts them", exactly as before. That
    sentinel is what keeps the shipped floor plans and every third-party hull working
    unchanged.
    
    Otherwise ``{"count": int, "posts": [[x, y], ...]}``: how many damage-control teams
    this interior has, and where they are stationed. Fewer posts than teams is fine - the
    rest are engine-placed. A post is also the team's permanent rally point, because the
    prefab spawns the rally marker on the cell it is given, so posting a team by the
    nacelles is all it takes to keep it there.
    
    Read as a sibling of ``grid_objects``/``theme``, at the entry level or inside a named
    layout, most specific winning - the same shape :func:`grid_get_theme_name` uses. A
    layout expressed as a bare list has nowhere to hold one and falls back to the entry.
    
    Args:
        ship_key (str): Ship key as defined in shipData.
        layout (str, optional): Layout name. Defaults to ``"default"``.
    
    Returns:
        dict | None: Normalized declaration, or ``None`` when the hull declares nothing."""
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
def grid_get_grid_named_theme (name):
    """Get a grid theme by name, falling back to the current theme if not found.
    
    Args:
        name (str | None): Theme name to look up (case-insensitive), or
            ``None`` to return the current theme.
    
    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc."""
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
def grid_get_layout (ship_key, layout=None):
    """The grid-object list for one hull's layout.
    
    A hull has N named LAYOUTS, not one interior - a full authored interior, a cheap
    systems-only one, a jump-drive refit of the same hull. ``grid_objects`` at the top
    level is still read as the default, so every existing entry keeps working::
    
        {"tsn_light_cruiser": {"grid_objects": [...]}}                    # still valid
        {"pirate_brigantine": {"layouts": {"default": {...},
                                           "systems": {...}}}}
    
    A layout may be either ``{"grid_objects": [...]}`` or a bare list.
    
    Args:
        ship_key (str): Ship key as defined in shipData.
        layout (str, optional): Layout name. Defaults to ``"default"``, then to the
            top-level ``grid_objects``.
    
    Returns:
        list | None: The grid object dicts, or ``None`` when there is no such interior."""
def grid_get_max_hp ():
    """Return the current global maximum HP value for damcon-team grid objects.
    
    Returns:
        int: The max HP setting (default 6)."""
def grid_get_theme_name (ship_key, layout=None):
    """The theme a hull (or one of its layouts) asks for, or ``None`` for the current one.
    
    Theme selection used to be a single module-level index - a whole-game setting - which
    made per-race themes impossible. A hull, or a single layout of it, can now name its
    own: a captured TSN hull refitted by pirates is the same mesh with a different
    interior AND a different vocabulary."""
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
def grid_rebuild_grid_objects (id_or_obj, grid_data=None, layout=None):
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
def grid_restore_damcons (id_or_obj, layout=None):
    """Restore all damcon teams on a ship to full health, creating them if missing.
    
    How many teams there are, and where they stand, come from the hull's interior data
    when it says (``grid_get_damcons``); otherwise three teams wherever the engine puts
    them, exactly as before. A declared post is also the team's permanent rally point,
    because the prefab spawns the rally marker on the cell it is handed.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        layout (str, optional): Layout name. Defaults to the ship's ``grid_layout``
            inventory value. Pass it explicitly when rebuilding into a layout the ship has
            not been switched to yet."""
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
def grid_valid_blob (id_or_obj):
    """Return a grid object's engine blob only if its backing space object is
    still valid, otherwise ``None``.
    
    A destroyed host ship leaves the grid object's ``Agent`` and its cached blob
    wrapper in place, so ``to_blob`` still returns a non-``None`` wrapper -- but
    the engine raises ``ValueError: invalid space object`` on any ``get``/``set``
    of that wrapper. This probes cheaply so callers can guard the dead-object
    case with a plain ``is None`` check, the same as a missing object.
    
    Args:
        id_or_obj (Agent | int): Agent id or object.
    
    Returns:
        data_set | None: The live blob, or ``None`` if the object is gone or its
            host space object has been destroyed."""
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
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
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
