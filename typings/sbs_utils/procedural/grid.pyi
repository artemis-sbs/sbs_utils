from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.helpers import FrameContext
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def get_artemis_data_dir_filename (filename):
    """Get the full path to a file in the data directory.
    
    Args:
        filename (str): The relative path from the data directory.
    
    Returns:
        str: The full path to the file in the data directory."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
def get_open_grid_points (id_or_obj) -> set[sbs_utils.vec.Vec3]:
    """Gets a list of open grid locations
    
    Args:
        id_or_obj (agent): agent id or object to check
    
    Returns:
        set: a set of Vec3 with x and y set"""
def grid_clear_detailed_status (id_or_obj):
    """Clear the detailed status (info text) of a grid object.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object."""
def grid_clear_speech_bubble (id_or_obj):
    """Clear the speech bubble for a grid object
    
    Args:
        id_or_obj (Agent | int): agent id or object of the grid object"""
def grid_clear_target (grid_obj_or_set):
    """Clear the movement target of a grid object, stopping it in place.
    
    Args:
        grid_obj_or_set (Agent | int | set): Agent, ID, or set of grid
            object(s) to stop."""
def grid_close_list (grid_obj, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        the_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        list[CloseData]: The gird close data of the closest objects"""
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_data_is_loaded () -> int:
    """Reset-ledger probe: 1 while grid data (possibly mod-merged) is held, else 0."""
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
def grid_delete_objects (ship_id_or_obj):
    """Delete all grid objects belonging to a ship.
    
    Args:
        ship_id_or_obj (Agent | int): Agent or ID of the ship whose grid
            objects should be removed."""
def grid_detailed_status (id_or_obj, status, color=None):
    """Set the detailed status (info text) of a grid object.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        status (str): Status string to display.
        color (str, optional): Text color. ``None`` keeps the current value.
            Defaults to None."""
def grid_get_damcons (ship_key, layout=None):
    """The damcon-team declaration for a hull (or one of its layouts), or ``None``.
    
    ``None`` - which is what every hull that says nothing returns, and that is nearly all
    of them - means "three teams, wherever the engine puts them", exactly as before.
    
    Otherwise ``{"count": int, "posts": [[x, y], ...]}``: how many damage-control teams
    this interior has, and where they are stationed. A post is also the team's permanent
    rally point.
    
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
def grid_get_grid_theme ():
    """Get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid theme data
        * key (str): The ship key associated with the grid theme
        * value (dict): The grid theme data"""
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
def grid_get_mod (ship_key):
    """The mod that supplied a hull's interior, or ``None`` for built-in data."""
def grid_get_theme_name (ship_key, layout=None):
    """The theme a hull (or one of its layouts) asks for, or ``None`` for the current one.
    
    Theme selection used to be a single module-level index - a whole-game setting - which
    made per-race themes impossible. A hull, or a single layout of it, can now name its
    own: a captured TSN hull refitted by pirates is the same mesh with a different
    interior AND a different vocabulary."""
def grid_merge_ascii (content, mod=None, ship_key=None):
    """Merge one ASCII floor plan (see :mod:`grid_ascii`) into the grid data.
    
    The one-line form an addon's ``__init__.mast`` uses::
    
        grid_merge_ascii(media_read_relative_file("tsn_light_cruiser.grid"), "interiors_tsn")
    
    A plan naming a ``layout:`` other than ``default`` is merged INTO the hull's existing
    entry as a named layout rather than replacing it, so a hull's variants can arrive from
    separate files - and, later, from separate mods.
    
    Returns the entry that was merged, or ``None`` if the text could not be read (which is
    logged, not raised: one unreadable floor plan should not take a mission down)."""
def grid_merge_mod_data (content, mod=None):
    """Merge grid data supplied as a JSON/YAML string into the grid data cache.
    
    The counterpart of :func:`sbs_utils.procedural.ship_data.merge_mod_ship_yaml`, and the
    one change that lets an ADDON ship ship interiors. ``grid_get_grid_data`` reads only
    two places - the engine's ``grid_data.json`` and the *mission directory's*
    ``extra_grid_data.json`` - so an addon inside a ``.mastlib`` could not contribute at
    all. Pair it with ``media_read_relative_file``, which reads from the addon's zip when
    it is packaged and from its folder in dev::
    
        grid_merge_mod_data(media_read_relative_file("extra_grid_data.json"), "PirateMod")
    
    Unlike ship data, this needs no build step: grid objects are not engine content -
    ``grid_rebuild_grid_objects`` creates every one at runtime through ``grid_spawn`` - so
    the engine never has to pre-know an interior. See ``SHIP_MOD_PLAN.md`` s3.
    
    Merging is **whole-entry replace**, matching the ``|=`` the mission file has always
    used: a mod supplies a hull's whole interior and cannot add a room to someone else's.
    Layout variants are how one hull legitimately has more than one interior.
    
    Two mods claiming the same hull is reported by name. It is a warning rather than an
    error because failing here would take down a mission at load over a cosmetic clash,
    but silent last-writer-wins is how interiors start feeling haunted.
    
    Args:
        content (str): JSON or YAML text (YAML is a JSON superset, so both parse).
        mod (str, optional): Name of the mod these entries come from; stamped on each
            entry as ``#mod`` and used to name collisions.
    
    Returns:
        dict | None: The updated grid data, or ``None`` if ``content`` was empty or
            unparseable."""
def grid_merge_mod_theme (content):
    """Append themes supplied as a JSON/YAML string, so an addon can ship its own.
    
    Companion to :func:`grid_merge_mod_data`; same reason it exists - the built-in reader
    only looks in the engine data dir and the mission dir, so a `.mastlib` addon had no
    way in. A race mod's room VOCABULARY lives here: new room names need theme icon
    entries or they fall back to the generic icon 120.
    
    A theme with a name that already exists REPLACES it, so a mod can re-skin a built-in
    theme rather than only adding beside it.
    
    Args:
        content (str): JSON or YAML text - one theme dict, or a list of them.
    
    Returns:
        list | None: The updated theme list, or ``None`` if nothing parsed."""
def grid_object_valid (id_or_obj) -> bool:
    """Return whether a grid object still has a valid backing space object.
    
    Returns ``False`` once the host ship is destroyed, even though the grid
    object's ``Agent`` may still resolve. See :func:`grid_valid_blob`.
    
    Args:
        id_or_obj (Agent | int): Agent id or object.
    
    Returns:
        bool: ``True`` if the grid object's blob can be safely accessed."""
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
def grid_pos_data (id):
    """Return the current position and path length of a grid object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        tuple[float, float, float]: ``(curx, cury, path_length)``."""
def grid_remove_move_role (event):
    """Remove the ``_moving_`` role when a grid object finishes its path.
    
    Args:
        event: Engine event; only acts when ``event.sub_tag == "finished_path"``."""
def grid_reset_caches ():
    """Drop the loaded grid data and themes at a mission boundary.
    
    ``_grid_data`` merges the mission's ``extra_grid_data.json`` (and, once mods can
    contribute, every enabled mod's interiors) into the base table, and ``_grid_theme``
    does the same for themes - so both are PER-MISSION state wearing the clothes of a
    module-level cache. Left alone, the next mission inherits the previous one's
    interiors and its theme index.
    
    The engine forks a fresh process per mission and hides this; ``cosmos_dev`` reuses
    one interpreter and does not. Registered in the reset ledger."""
def grid_set_grid_current_theme (i):
    """Set the active grid theme by index.
    
    Args:
        i (int): Index into the loaded grid theme list."""
def grid_set_grid_named_theme (name):
    """Set the active grid theme by name.
    
    Args:
        name (str): Theme name (case-insensitive), e.g. ``"cosmos"`` or
            ``"Retro"``."""
def grid_short_status (id_or_obj, status, color=None, seconds=0, minutes=0):
    """Set the tooltip and speech bubble text of a grid object.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        status (str): Status string for both the tooltip and speech bubble.
        color (str, optional): Text color. ``None`` keeps the current value.
            Defaults to None.
        seconds (int, optional): Duration for the speech bubble. Defaults to 0
            (permanent).
        minutes (int, optional): Additional minutes for the bubble duration.
            Defaults to 0."""
def grid_speech_bubble (id_or_obj, status, color=None, seconds=0, minutes=0):
    """Sets the speech bubble text of a grid object. The text will disappear if the seconds/minutes are set
    
    Args:
        id_or_obj (Agent | int): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble"""
def grid_target (grid_obj_or_set, target_id: int, speed=0.01):
    """Set a grid object to target the location of another grid object
    
    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): an id, object or set of agent(s)
        target_id (Agent): an agent id or object
        speed (float, optional): the speed to move. Defaults to 0.01."""
def grid_target_closest (grid_obj_or_set, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): The agent or set
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        GridCloseData: The gird close data of the closest object"""
def grid_target_pos (grid_obj_or_set, x: float, y: float, speed=0.01):
    """Set a grid object to move toward a specific grid coordinate.
    
    Args:
        grid_obj_or_set (Agent | int | set): Agent, ID, or set of grid
            object(s) to move.
        x (float): Target x grid coordinate.
        y (float): Target y grid coordinate.
        speed (float, optional): Movement speed. Defaults to 0.01."""
def grid_theme_current_index () -> int:
    """Reset-ledger probe: the selected theme index, which must be back to 0 (default).
    
    Not a container - a setting. A mission that selected theme 1 would silently hand it
    to the next mission, which is a whole game re-skinned for no reason anyone could see."""
def grid_theme_is_loaded () -> int:
    """Reset-ledger probe: 1 while theme data is held, else 0."""
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
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.
    
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
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
