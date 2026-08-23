from .query import to_blob, to_id, to_object, to_object_list, to_set, to_data_set
from ..agent import CloseData, Agent
from ..tickdispatcher import TickDispatcher
from .inventory import get_inventory_value, set_inventory_value
from ..fs import load_json_data, get_artemis_data_dir_filename, get_mission_dir_filename
import functools
from ..vec import Vec3
from ..helpers import FrameContext
from .roles import remove_role, add_role


def grid_objects(so_id) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship

    Args:
        so_id (Agent | int): agent id or object 

    Returns:
        set[int]: a set of agent ids
    """    
    gos = set()
    hm = FrameContext.context.sbs.get_hull_map(to_id(so_id))
    if hm is None:
        return gos
    count = hm.get_grid_object_count()
    for i in range(count):
        go = hm.get_grid_object_by_index(i)
        gos.add(go.unique_ID)
    return gos

def grid_objects_at(so_id, x,y) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship, at the location specified

    Args:
        so_id (Agent | int): agent id or object 
        x (int): The x grid location
        y (int): The y grid location

    Returns:
        set[int]: A set of agent ids
    """    
    gos = set()
    hm = FrameContext.context.sbs.get_hull_map(to_id(so_id))
    if hm is None:
        return gos
    return to_set(hm.get_objects_at_point(x,y))


def grid_valid_blob(id_or_obj):
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
            host space object has been destroyed.
    """
    blob = to_blob(id_or_obj)
    if blob is None:
        return None
    try:
        # Any access raises ValueError once the backing space object is gone.
        blob.get("curx", 0)
    except ValueError:
        return None
    return blob


def grid_object_valid(id_or_obj) -> bool:
    """Return whether a grid object still has a valid backing space object.

    Returns ``False`` once the host ship is destroyed, even though the grid
    object's ``Agent`` may still resolve. See :func:`grid_valid_blob`.

    Args:
        id_or_obj (Agent | int): Agent id or object.

    Returns:
        bool: ``True`` if the grid object's blob can be safely accessed.
    """
    return grid_valid_blob(id_or_obj) is not None


################################
##########################################
####### TODO: Update for sets

def grid_close_list(grid_obj, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    """Find and target the closest object matching the criteria

    Args:
        grid_obj (Agent | int): The agent or id
        the_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.

    Returns:
        list[CloseData]: The gird close data of the closest objects
    """    
    ret = []
    grid_obj=to_object(grid_obj)
    blob = grid_valid_blob(grid_obj.id)
    # Host ship destroyed out from under this brain -> nothing to compare against.
    if blob is None:
        return ret
    this_x= blob.get("curx", 0)
    this_y=blob.get("cury",  0)
    if max_dist is None:
        max_dist = 1000

    if the_set is None:
        test_roles = to_object_list(grid_objects(grid_obj.host_id))
    else:
        test_roles = to_set(the_set)
    for other_id in test_roles:
        other = to_object(other_id)
        # skip this one
        # if no longer around
        if other is None:
            continue
        # if this is the same object
        if other_id == grid_obj.id:
            continue

        if filter_func and not filter_func(other):
            continue
        
        # curx, cury
        other_blob = grid_valid_blob(other_id)
        # if this is gone (or its host was destroyed) and we missed that earlier
        if other_blob is None:
            continue
        other_x= other_blob.get("curx", 0)
        other_y= other_blob.get("cury",  0)



        test = abs(this_x-other_x) + abs(this_y-other_y)
        if test < max_dist:
            ret.append(CloseData(other.id, other, test))
        continue

    return ret

def grid_closest(grid_obj, target_set=None, max_dist=None, filter_func=None) -> CloseData:
    """Find and target the closest object matching the criteria

    Args:
        grid_obj (Agent | int): The agent or id
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.

    Returns:
        CloseData: The gird close data of the closest object
    """    
    close = grid_close_list(grid_obj, target_set, max_dist, filter_func)
    # Maybe not the most efficient
    if len(close)==1:
        return close[0]
    elif len(close)>0:
        return functools.reduce(lambda a, b: a if a.distance < b.distance else b, close)
    
    return None

def grid_target_closest(grid_obj_or_set, target_set=None, max_dist=None, filter_func=None) -> CloseData:
    """Find and target the closest object matching the criteria

    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): The agent or set
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.

    Returns:
        GridCloseData: The gird close data of the closest object
    """    
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        grid_obj=to_object(grid_obj)
        close = grid_closest(grid_obj, target_set, max_dist, filter_func)
        if close.id is not None:
            #grid_obj.target(close.id)
            grid_target(grid_obj, close.id)
        return close

def grid_target(grid_obj_or_set, target_id: int, speed=0.01):
    """Set a grid object to target the location of another grid object

    Args:
        grid_obj_or_set (Agent | int | set[Agent | int]): an id, object or set of agent(s)
        target_id (Agent): an agent id or object 
        speed (float, optional): the speed to move. Defaults to 0.01.
    """    
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        this_blob = grid_valid_blob(grid_obj.id)
        other_blob = grid_valid_blob(target_id)
        if other_blob and this_blob:
            curx= this_blob.get("curx", 0)
            cury= this_blob.get("cury",  0)
        
            x = other_blob.get("curx", 0)
            y = other_blob.get("cury", 0)

            if x!=curx or y != cury:
                this_blob.set("pathx", x, 0)
                this_blob.set("pathy", y, 0)
                if speed is not None:
                    this_blob.set("move_speed", speed, 0)
                add_role(grid_obj, "_moving_")

def grid_target_pos(grid_obj_or_set, x:float, y:float, speed=0.01):
    """Set a grid object to move toward a specific grid coordinate.

    Args:
        grid_obj_or_set (Agent | int | set): Agent, ID, or set of grid
            object(s) to move.
        x (float): Target x grid coordinate.
        y (float): Target y grid coordinate.
        speed (float, optional): Movement speed. Defaults to 0.01.
    """
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        blob = grid_valid_blob(grid_obj.id)
        if blob is None:
            continue
        curx= blob.get("curx", 0)
        cury=blob.get("cury",  0)

        pathx = blob.get("pathx", 0)
        pathy = blob.get("pathy", 0)
        
        if pathx==x and pathy == y:
            if speed is not None:
                blob.set("move_speed", 0, 0)
            continue
            
        if curx!=x or cury != y:
            blob.set("pathx", x, 0)
            blob.set("pathy", y, 0)
            if speed is not None:
                blob.set("move_speed", speed, 0)
            add_role(grid_obj, "_moving_")
        else:
            if speed is not None:
                blob.set("move_speed", 0, 0)

def grid_clear_target(grid_obj_or_set):
    """Clear the movement target of a grid object, stopping it in place.

    Args:
        grid_obj_or_set (Agent | int | set): Agent, ID, or set of grid
            object(s) to stop.
    """
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        blob = grid_valid_blob(grid_obj.id)
        if blob is None:
            continue
        x= blob.get("curx", 0)
        y=blob.get("cury",  0)
        grid_target_pos(grid_obj_or_set, x,y)
        remove_role(grid_obj, "_moving_")

        
def get_open_grid_points(id_or_obj) -> set[Vec3]:
    """Gets a list of open grid locations

    Args:
        id_or_obj (agent): agent id or object to check

    Returns:
        set: a set of Vec3 with x and y set
    """    
    the_set = []
    hull_map = FrameContext.context.sbs.get_hull_map(to_id(id_or_obj))
    if hull_map is not None:
        for x in range(hull_map.w):
            for y in range(hull_map.w):
                if hull_map.is_grid_point_open(x,y) != 0:
                    the_set.append(Vec3(x,y,0))
    return set(the_set)


def grid_speech_bubble(id_or_obj, status, color=None, seconds=0, minutes=0):
    """Sets the speech bubble text of a grid object. The text will disappear if the seconds/minutes are set

    Args:
        id_or_obj (Agent | int): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble
    """        
    blob = grid_valid_blob(id_or_obj)
    if blob is None:
        return
    # set speech bubble
    blob.set("speech_bubble_text", status, 0)
    if color is not None:
        blob.set("speech_bubble_text_color", color, 0)
    seconds += minutes*60
    t = get_inventory_value(id_or_obj, "speech_bubble_tick_task")
    if t is not None:
        t.stop()
    if seconds>0:
        t = TickDispatcher.do_once(lambda t: grid_clear_speech_bubble(t.id), seconds)
        t.id = to_id(id_or_obj)
        set_inventory_value(id_or_obj, "speech_bubble_tick_task", t)

def grid_clear_speech_bubble(id_or_obj):
    """Clear the speech bubble for a grid object

    Args:
        id_or_obj (Agent | int): agent id or object of the grid object
    """    
    grid_speech_bubble(id_or_obj, "")
    set_inventory_value(id_or_obj, "speech_bubble_tick_task", None)
    

def grid_short_status(id_or_obj, status, color=None, seconds=0, minutes=0):
    """Set the tooltip and speech bubble text of a grid object.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        status (str): Status string for both the tooltip and speech bubble.
        color (str, optional): Text color. ``None`` keeps the current value.
            Defaults to None.
        seconds (int, optional): Duration for the speech bubble. Defaults to 0
            (permanent).
        minutes (int, optional): Additional minutes for the bubble duration.
            Defaults to 0.
    """
    blob = grid_valid_blob(id_or_obj)
    if blob is None:
        return
    # Set tooltip
    blob.set("tool_tip_cur_text", status, 0)
    grid_speech_bubble(id_or_obj, status, color, seconds, minutes)

def grid_detailed_status(id_or_obj, status, color=None):
    """Set the detailed status (info text) of a grid object.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
        status (str): Status string to display.
        color (str, optional): Text color. ``None`` keeps the current value.
            Defaults to None.
    """
    blob = grid_valid_blob(id_or_obj)
    if blob is None:
        return
    # Set tooltip
    blob.set("info_text", status, 0)
    if color is not None:
        blob.set("info_text_color", color, 0)

def grid_clear_detailed_status(id_or_obj):
    """Clear the detailed status (info text) of a grid object.

    Args:
        id_or_obj (Agent | int): Agent ID or object.
    """
    grid_detailed_status(id_or_obj, "")
    


def _grid_say(msg, level="warning"):
    """Report a grid-data problem on a channel the ENGINE shows.

    ``log()`` alone is not enough: in the engine it reaches a Python logger with no
    handler, so every merge failure below was invisible on the one platform where a mod
    is actually loaded. See the twin in ``internal_damage._grid_say``.
    """
    from .execution import log
    log(msg, "grid", level)
    try:
        from ..mast.mast import DEBUG
        DEBUG("[grid] " + msg)
    except Exception:                               # noqa: BLE001
        pass                                        # diagnostics never break a load


_grid_data = None 
def grid_get_grid_data() -> dict:
    """Get the grid data from all the grid_data.json files

    Returns:
        dict: a dictionary of grid data objects.
        * key (str): The key of the dict, which is a ship key as defined in shipData.
        * value (dict): A dict with `grid_objects` as a key, and a list of grid object data as the value.
    """    
    global _grid_data
    if _grid_data is None:
        stock = get_artemis_data_dir_filename("grid_data.json")
        _grid_data = load_json_data(stock)
        if _grid_data is None:
            # Nothing else in this module can work, and every grid_merge_* call becomes a
            # silent no-op - so EVERY hull, stock and modded, loses its interior at once.
            # The cache never latches either, so this re-reads (and re-reports) per call.
            _grid_say(f"grid_data.json did not load from {stock!r} - no hull has an "
                      f"interior and every floor plan merged from now on is DROPPED.")
            return None
        script_grid_data = load_json_data(get_mission_dir_filename("extra_grid_data.json"))
        if script_grid_data is not None:
            _grid_data |= script_grid_data
    return _grid_data


GRID_DATA_MOD_KEY = "#mod"
_grid_data_mods = {}


def grid_merge_mod_data(content, mod=None):
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
            unparseable.
    """
    if not content:
        return None
    from ..fs import load_yaml_string
    data = load_yaml_string(content)
    if not isinstance(data, dict):
        return None

    grid_data = grid_get_grid_data()
    if grid_data is None:
        return None

    for key, entry in data.items():
        if not isinstance(entry, dict):
            continue
        previous = _grid_data_mods.get(key)
        if previous is not None and mod is not None and previous != mod:
            from .execution import log
            log(f"grid data collision: '{key}' is supplied by both '{previous}' and "
                f"'{mod}' - '{mod}' wins. One of them should be renamed.",
                "grid", "warning")
        if mod is not None:
            entry[GRID_DATA_MOD_KEY] = mod
            _grid_data_mods[key] = mod
        grid_data[key] = entry
    return grid_data


def grid_get_mod(ship_key):
    """The mod that supplied a hull's interior, or ``None`` for built-in data."""
    entry = grid_get_grid_data().get(ship_key)
    if not isinstance(entry, dict):
        return None
    return entry.get(GRID_DATA_MOD_KEY)


def grid_merge_report():
    """How many hull interiors each mod supplied: ``{mod_name: count}``.

    The question "did my floor plans actually load?" had no answer short of poking at
    ``grid_get_grid_data()`` by hand, and getting it wrong is invisible - a hull with no
    interior is a dead Engineering console and nothing else. Built-in hulls are not
    counted; they carry no ``#mod`` stamp.

    Intended for a mission's own start-up assertion and for the test suite::

        assert grid_merge_report().get("tng_races") == 50
    """
    out = {}
    for mod in _grid_data_mods.values():
        out[mod] = out.get(mod, 0) + 1
    return out


def grid_get_layout(ship_key, layout=None):
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
        list | None: The grid object dicts, or ``None`` when there is no such interior.
    """
    entry = grid_get_grid_data().get(ship_key)
    if not isinstance(entry, dict):
        return None

    layouts = entry.get("layouts")
    if isinstance(layouts, dict):
        chosen = layouts.get(layout or "default")
        # An explicitly requested layout that does not exist falls back to the default
        # rather than to nothing: a mission asking for "systems" on a hull that has no
        # systems layout should still get a working ship.
        if chosen is None and layout:
            chosen = layouts.get("default")
        if isinstance(chosen, list):
            return chosen
        if isinstance(chosen, dict):
            return chosen.get("grid_objects")

    return entry.get("grid_objects")


def grid_get_theme_name(ship_key, layout=None):
    """The theme a hull (or one of its layouts) asks for, or ``None`` for the current one.

    Theme selection used to be a single module-level index - a whole-game setting - which
    made per-race themes impossible. A hull, or a single layout of it, can now name its
    own: a captured TSN hull refitted by pirates is the same mesh with a different
    interior AND a different vocabulary.
    """
    entry = grid_get_grid_data().get(ship_key)
    if not isinstance(entry, dict):
        return None
    layouts = entry.get("layouts")
    if isinstance(layouts, dict):
        chosen = layouts.get(layout or "default")
        if isinstance(chosen, dict) and chosen.get("theme"):
            return chosen.get("theme")
    return entry.get("theme")


def grid_get_damcons(ship_key, layout=None):
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
        dict | None: Normalized declaration, or ``None`` when the hull declares nothing.
    """
    from .grid_ascii import grid_normalize_damcons
    entry = grid_get_grid_data().get(ship_key)
    if not isinstance(entry, dict):
        return None
    layouts = entry.get("layouts")
    if isinstance(layouts, dict):
        chosen = layouts.get(layout or "default")
        if isinstance(chosen, dict) and chosen.get("damcons") is not None:
            return grid_normalize_damcons(chosen.get("damcons"))
    return grid_normalize_damcons(entry.get("damcons"))


_grid_theme = None
def grid_get_grid_theme():
    """Get the grid data from all the grid_data.json files

    Returns:
        dict: a dictionary of grid theme data
        * key (str): The ship key associated with the grid theme
        * value (dict): The grid theme data
    """    
    global _grid_theme
    if _grid_theme is None:
        _grid_theme = load_json_data(get_artemis_data_dir_filename("GRID_THEME.json"))
        if _grid_theme is None:
            _grid_theme = []
        script_grid_data = load_json_data(get_mission_dir_filename("extra_grid_theme.json"))
        if script_grid_data is not None:
            _grid_theme.extend(script_grid_data)
    return _grid_theme


def grid_merge_mod_theme(content):
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
        list | None: The updated theme list, or ``None`` if nothing parsed.
    """
    if not content:
        return None
    from ..fs import load_yaml_string
    data = load_yaml_string(content)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None
    themes = grid_get_grid_theme()
    for t in data:
        if not isinstance(t, dict) or not t.get("name"):
            continue
        name = str(t["name"]).strip().lower()
        for i, existing in enumerate(themes):
            if str(existing.get("name", "")).strip().lower() == name:
                themes[i] = t
                break
        else:
            themes.append(t)
    return themes

_grid_theme_current = 0
def grid_get_grid_current_theme():
    """Get the currently active grid theme data.

    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc.
    """
    global _grid_theme_current
    td = grid_get_grid_theme()
    if _grid_theme_current < len(td):
        return td[_grid_theme_current]
    # Used to return the integer INDEX here, into callers that immediately subscript it
    # as a dict (theme["colors"], theme["icons"]) - so an out-of-range selection raised
    # TypeError somewhere unrelated. Fall back to the first theme, which always exists
    # once any theme has loaded.
    if td:
        return td[0]
    return {"name": "", "colors": {}, "damage_colors": {}, "icons": {}}

def grid_set_grid_current_theme(i):
    """Set the active grid theme by index.

    Args:
        i (int): Index into the loaded grid theme list.
    """
    global _grid_theme_current
    td = grid_get_grid_theme()
    if i < len(td):
        _grid_theme_current = i


def grid_reset_caches():
    """Drop the loaded grid data and themes at a mission boundary.

    ``_grid_data`` merges the mission's ``extra_grid_data.json`` (and, once mods can
    contribute, every enabled mod's interiors) into the base table, and ``_grid_theme``
    does the same for themes - so both are PER-MISSION state wearing the clothes of a
    module-level cache. Left alone, the next mission inherits the previous one's
    interiors and its theme index.

    The engine forks a fresh process per mission and hides this; ``cosmos_dev`` reuses
    one interpreter and does not. Registered in the reset ledger.
    """
    global _grid_data, _grid_theme, _grid_theme_current
    _grid_data = None
    _grid_theme = None
    _grid_theme_current = 0
    _grid_data_mods.clear()     # which mod supplied which hull, for collision reporting


def grid_data_is_loaded() -> int:
    """Reset-ledger probe: 1 while grid data (possibly mod-merged) is held, else 0."""
    return 0 if _grid_data is None else 1


def grid_theme_is_loaded() -> int:
    """Reset-ledger probe: 1 while theme data is held, else 0."""
    return 0 if _grid_theme is None else 1


def grid_theme_current_index() -> int:
    """Reset-ledger probe: the selected theme index, which must be back to 0 (default).

    Not a container - a setting. A mission that selected theme 1 would silently hand it
    to the next mission, which is a whole game re-skinned for no reason anyone could see.
    """
    return _grid_theme_current


def grid_get_grid_named_theme(name):
    """Get a grid theme by name, falling back to the current theme if not found.

    Args:
        name (str | None): Theme name to look up (case-insensitive), or
            ``None`` to return the current theme.

    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc.
    """
    if name is None:
        return grid_get_grid_current_theme()
    td = grid_get_grid_theme()
    name = name.lower().strip()
    for t in td:
        if str(t.get("name", "")).lower() == name:
            return t
    # An unknown theme name falls back to the current theme rather than None - callers
    # subscript the result, so None here would raise far from the typo that caused it.
    return grid_get_grid_current_theme()


def grid_set_grid_named_theme(name):
    """Set the active grid theme by name.

    Args:
        name (str): Theme name (case-insensitive), e.g. ``"cosmos"`` or
            ``"Retro"``.
    """
    global _grid_theme_current
    td = grid_get_grid_theme()
    name = name.lower().strip()

    for i,t in enumerate(td):
        if t["name"].lower() == name:
            _grid_theme_current = i
            break
    return _grid_theme_current

def grid_get_item_theme_data(roles, name=None):
    """Get icon, scale, color, and damage color for a set of roles from the grid theme.

    Roles are matched in reverse priority order so the last role in the list
    takes precedence. Falls back to ``"default"`` entries when no role matches.

    Args:
        roles (str): Comma-separated role names.
        name (str | None, optional): Theme name to use. ``None`` uses the
            current theme. Defaults to None.

    Returns:
        RetVal: Object with ``.icon`` (int), ``.scale`` (float), ``.color``
            (str), and ``.damage_color`` (str) attributes.
    """
    roles = roles.strip().lower().split(",") # Last is used first
    td = grid_get_grid_named_theme(name)
    
    icon = None # td["icons"].get("default", def_icon)
    damage_color = None # icon["scale"]
    color = None # td.get("default", "red")

    for r in reversed(roles):
        r = r.strip()
        if icon is None:
            icon = td["icons"].get(r, None)
        if color is None:
            color = td["colors"].get(r, None)
        if damage_color is None:
            damage_color = td["damage_colors"].get(r, None)
        if color is not None and icon is not None and damage_color is not None:
            break
    
    if icon is None:
        icon = {"icon": 120, "scale": 1.0}
    if color is None:
        color = td["colors"].get("default", "red")
    if damage_color is None:
        damage_color = td["damage_colors"].get("default", "red")


    class RetVal:
        def __init__(self, i,s,c, d) -> None:
            self.icon = i
            self.scale = s
            self.color = c
            self.damage_color = d
    
    r = RetVal(icon["icon"], icon["scale"], color, damage_color)
    
    return r

def grid_delete_object(host_id_or_obj, id_or_obj):
    """Delete a single grid object, deferring the native free.

    Tombstones the grid agent now (dropped from ``Agent.all``/roles, so
    ``object_exists()``/``to_object()`` report it gone this instant) and enqueues
    the native ``sbs.delete_grid_object(host_id, id)`` to run at the end of the
    event handler. Mirrors ``SpaceObject.delete_object`` for grid objects, closing
    the same-tick use-after-free window. See ``DeleteQueue``.

    Args:
        host_id_or_obj (Agent | int): The host ship the grid object lives on.
        id_or_obj (Agent | int): The grid object (or its id) to delete.
    """
    from ..delete_queue import DeleteQueue
    host_id = to_id(host_id_or_obj)
    gid = to_id(id_or_obj)
    if gid is None:
        return
    _grid_clear_selection_of(host_id, gid)
    Agent.remove_id(gid)
    DeleteQueue.queue_grid(host_id, gid)


def _grid_clear_selection_of(host_id, gid):
    """Drop the console's grid selection if it names the object being deleted.

    ``grid_selected_UID`` lives on the HOST SHIP's blob and is what the engine's
    grid_object_list widget resolves into an index every frame. Nothing used to
    clear it on delete, so deleting the selected object - a damcon that dies, a
    repaired hallway marker, or the whole interior during a grid rebuild - left
    the widget pointing at an id that is no longer in the array. Doing it here
    rather than at each call site means every caller inherits it.
    """
    if host_id is None:
        return
    blob = to_blob(host_id)
    if blob is None:
        return
    try:
        if blob.get("grid_selected_UID", 0) == gid:
            blob.set("grid_selected_UID", 0, 0)
    except ValueError:
        # Host space object already gone; nothing to clear. Same probe as
        # grid_valid_blob - the engine raises rather than returning None here.
        pass


def grid_delete_objects(ship_id_or_obj):
    """Delete all grid objects belonging to a ship.

    Args:
        ship_id_or_obj (Agent | int): Agent or ID of the ship whose grid
            objects should be removed.
    """
    craft_id = to_id(ship_id_or_obj)
    if craft_id is None:
        return
    items =grid_objects(craft_id)
    for k in items:
        # delete by id (deferred native free)
        grid_delete_object(craft_id, k)


def grid_pos_data(id):
    """Return the current position and path length of a grid object.

    Args:
        id (Agent | int): Agent ID or object.

    Returns:
        tuple[float, float, float]: ``(curx, cury, path_length)``.
    """
    blob = grid_valid_blob(to_id(id))
    if blob is None:
        return (None, None, None)
    path_length = blob.get("path_length", 0)
    curx= blob.get("curx", 0)
    cury=blob.get("cury",  0)
    return (curx, cury, path_length)

from ..griddispatcher import GridDispatcher

def grid_remove_move_role(event):
    """Remove the ``_moving_`` role when a grid object finishes its path.

    Args:
        event: Engine event; only acts when ``event.sub_tag == "finished_path"``.
    """
    if event.sub_tag == "finished_path":
        remove_role(event.origin_id, "_moving_")
    

GridDispatcher.add_any_object(grid_remove_move_role)

def grid_merge_ascii(content, mod=None, ship_key=None):
    """Merge one ASCII floor plan (see :mod:`grid_ascii`) into the grid data.

    The one-line form an addon's ``__init__.mast`` uses::

        grid_merge_ascii(media_read_relative_file("tsn_light_cruiser.grid"), "interiors_tsn")

    A plan naming a ``layout:`` other than ``default`` is merged INTO the hull's existing
    entry as a named layout rather than replacing it, so a hull's variants can arrive from
    separate files - and, later, from separate mods.

    Returns the entry that was merged, or ``None`` if the text could not be read (which is
    logged, not raised: one unreadable floor plan should not take a mission down).
    """
    if not content:
        # Almost always a media_read_relative_file() that returned None - a plan named in
        # a manifest that is not in the mastlib, or a read from the wrong base. Silent
        # until now, and indistinguishable downstream from a hull that never had a plan.
        _grid_say(f"floor plan not loaded for mod {mod!r} ship_key {ship_key!r}: the "
                  f"content was empty. If it came from media_read_relative_file, that "
                  f"call failed and logged its own reason.")
        return None
    from .grid_ascii import grid_ascii_parse, GridAsciiError
    try:
        parsed = grid_ascii_parse(content, ship_key)
    except GridAsciiError as e:
        _grid_say(f"floor plan not loaded (mod {mod!r}): {e}")
        return None

    grid_data = grid_get_grid_data()
    if grid_data is None:
        _grid_say(f"floor plan for {parsed['ship']!r} DROPPED - there is no grid data to "
                  f"merge it into.")
        return None
    key, layout, entry = parsed["ship"], parsed["layout"], parsed["entry"]

    if layout == "default":
        existing = grid_data.get(key)
        # Keep any named layouts a sibling file already contributed.
        if isinstance(existing, dict) and isinstance(existing.get("layouts"), dict):
            entry["layouts"] = existing["layouts"]
        grid_data[key] = entry
    else:
        existing = grid_data.get(key)
        if not isinstance(existing, dict):
            existing = {}
            grid_data[key] = existing
        existing.setdefault("layouts", {})[layout] = entry

    if mod is not None:
        grid_data[key][GRID_DATA_MOD_KEY] = mod
        _grid_data_mods[key] = mod
    return grid_data[key]
