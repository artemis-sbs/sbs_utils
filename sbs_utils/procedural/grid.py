from .query import to_blob, to_id, to_object, to_object_list, to_set, to_data_set
from ..agent import CloseData, Agent
from ..tickdispatcher import TickDispatcher
from .inventory import get_inventory_value, set_inventory_value
from ..fs import load_json_data, get_artemis_data_dir_filename, get_mission_dir_filename
import functools
from ..vec import Vec3
from ..helpers import FrameContext
from .roles import remove_role, add_role


def grid_objects(so_id):
    """get a set of agent ids of the grid objects on the specified ship

    Args:
        so_id (agent): agent id or object 

    Returns:
        set: a set of agent ids
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

def grid_objects_at(so_id, x,y):
    """get a set of agent ids of the grid objects on the specified ship, at the location specified

    Args:
        so_id (agent): agent id or object 
        x (int): The x grid location
        y (int): The y grid location

    Returns:
        set: a set of agent ids
    """    
    gos = set()
    hm = FrameContext.context.sbs.get_hull_map(to_id(so_id))
    if hm is None:
        return gos
    return to_set(hm.get_objects_at_point(x,y))


################################
##########################################
####### TODO: Update for sets

def grid_close_list(grid_obj, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    """Find and target the closest object matching the criteria

    Args:
        grid_obj_or_set (agent set): The agent 
        target_set (agent set, optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (_type_, optional): additional filer function. Defaults to None.

    Returns:
        CloseData list: The gird close data of the closest objects
    """    
    ret = []
    grid_obj=to_object(grid_obj)
    blob = to_blob(grid_obj.id)
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
        other_blob = to_blob(other_id)
        # if this is gone and we missed that fact ealier
        if other_blob is None:
            continue
        other_x= other_blob.get("curx", 0)
        other_y= other_blob.get("cury",  0)



        test = abs(this_x-other_x) + abs(this_y-other_y)
        if test < max_dist:
            ret.append(CloseData(other.id, other, test))

        ret.append(CloseData(other.id, other, test))
        continue

    return ret

def grid_closest(grid_obj, target_set=None, max_dist=None, filter_func=None) -> CloseData:
    """Find and target the closest object matching the criteria

    Args:
        grid_obj_or_set (agent set): The agent 
        target_set (agent set, optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (_type_, optional): additional filer function. Defaults to None.

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

def grid_target_closest(grid_obj_or_set, target_set=None, max_dist=None, filter_func=None):
    """Find and target the closest object matching the criteria

    Args:
        grid_obj_or_set (agent set): The agent 
        target_set (agent set, optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (_type_, optional): additional filer function. Defaults to None.

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
        grid_obj_or_set (agent): an id, object or set of agent(s)
        target_id (agent): an agent id or object 
        speed (float, optional): the speed to move. Defaults to 0.01.
    """    
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        this_blob = to_blob(grid_obj.id)
        other_blob = to_blob(target_id)
        if other_blob and this_blob:
            curx= this_blob.get("curx", 0)
            cury= this_blob.get("cury",  0)
        
            x = other_blob.get("curx", 0)
            y = other_blob.get("cury", 0)

            if x!=curx or y != cury:
                this_blob.set("pathx", x, 0)
                this_blob.set("pathy", y, 0)
                this_blob.set("move_speed", speed, 0)
                add_role(grid_obj, "_moving_")

def grid_target_pos(grid_obj_or_set, x:float, y:float, speed=0.01):
    """ Set the grid object go to the target location

    Args:
        grid_obj_or_set (agent): An id, object or set of grid object agent(s)
        x (float): x location
        y (float): y location
        speed (float, optional): The grid object speed. Defaults to 0.01.
    """    
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        blob = to_blob(grid_obj.id)
        curx= blob.get("curx", 0)
        cury=blob.get("cury",  0)

        pathx = blob.get("pathx", 0)
        pathy = blob.get("pathy", 0)
        
        if pathx==x and pathy == y:
            blob.set("move_speed", 0, 0)
            continue
            
        if curx!=x or cury != y:
            blob.set("pathx", x, 0)
            blob.set("pathy", y, 0)
            blob.set("move_speed", speed, 0)
            add_role(grid_obj, "_moving_")
        else:
            blob.set("move_speed", 0, 0)

def grid_clear_target(grid_obj_or_set):
    """ Clear the target of a grid object

    Args:
        grid_obj_or_set (agent): the id of the object or set

    """
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        blob = to_blob(grid_obj.id)
        x= blob.get("curx", 0)
        y=blob.get("cury",  0)
        grid_target_pos(grid_obj_or_set, x,y)
        remove_role(grid_obj, "_moving_")

        
def get_open_grid_points(id_or_obj):
    """gets a list of open grid location

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
    return the_set


def grid_speech_bubble(id_or_obj, status, color=None, seconds=0, minutes=0):
    """sets the speech bubble text of a grid object. The text will disappear if the seconds/minutes are set

    Args:
        id_or_obj (agent): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble
    """        
    blob = to_blob(id_or_obj)
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
    """clear the speech bubble for a grid object

    Args:
        id_or_obj (agent): agent id or object of the grid object
    """    
    grid_speech_bubble(id_or_obj, "")
    set_inventory_value(id_or_obj, "speech_bubble_tick_task", None)
    

def grid_short_status(id_or_obj, status, color=None, seconds=0, minutes=0):
    """sets the short status (tool tip) and speech bubble text of a grid object

    Args:
        id_or_obj (agent): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
        seconds (int): The seconds for the speech bubble
        minutes: (int): The minutes for the speech bubble
    """    
    blob = to_blob(id_or_obj)
    if blob is None:
        return
    # Set tooltip
    blob.set("tool_tip_cur_text", status, 0)
    grid_speech_bubble(id_or_obj, status, color, seconds, minutes)

def grid_detailed_status(id_or_obj, status, color=None):
    """sets the detailed status of a grid object

    Args:
        id_or_obj (agent): Agent id or object
        status (str): The detailed status string
        color (str, optional): change the color of the detailed status text. None does not change the current value
    """    
    blob = to_blob(id_or_obj)
    if blob is None:
        return
    # Set tooltip
    blob.set("info_text", status, 0)
    if color is not None:
        blob.set("info_text_color", color, 0)

def grid_clear_detailed_status(id_or_obj):
    """clears the detailed status string of a grid object

    Args:
        id_or_obj (agent): The agent id of object
    """    
    grid_detailed_status(id_or_obj, "")
    


_grid_data = None 
def grid_get_grid_data():
    """get the grid data from all the grid_data.json files

    Returns:
        dict: a dictionary of grid data objects key is a ship key
    """    
    global _grid_data
    if _grid_data is None:
        _grid_data = load_json_data(get_artemis_data_dir_filename("grid_data.json"))
        script_grid_data = load_json_data(get_mission_dir_filename("extra_grid_data.json"))
        if script_grid_data is not None:
            _grid_data |= script_grid_data
    return _grid_data


_grid_theme = None 
def grid_get_grid_theme():
    """get the grid data from all the grid_data.json files

    Returns:
        dict: a dictionary of grid data objects key is a ship key
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

_grid_theme_current = 0
def grid_get_grid_current_theme():
    global _grid_theme_current
    td = grid_get_grid_theme()
    if _grid_theme_current < len(td):
        return td[_grid_theme_current]
    return _grid_theme_current

def grid_set_grid_current_theme(i):
    global _grid_theme_current
    td = grid_get_grid_theme()
    if i < len(td):
        _grid_theme_current = i


def grid_get_grid_named_theme(name):
    if name is None:
        return grid_get_grid_current_theme()
    td = grid_get_grid_theme()
    name = name.lower.strip()
    for t in td:
        if t["name"].lower() == name:
            return t


def grid_set_grid_named_theme(name):
    global _grid_theme_current
    td = grid_get_grid_theme()
    name = name.lower.strip()

    for i,t in enumerate(td):
        if t["name"].lower() == name:
            _grid_theme_current = i
            break
    return _grid_theme_current

def grid_get_item_theme_data(roles, name=None):
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

def grid_delete_objects(ship_id_or_obj):
    craft_id = to_id(ship_id_or_obj)
    if craft_id is None:
        return
    items =grid_objects(craft_id)
    for k in items:
        # delete by id
        FrameContext.context.sbs.delete_grid_object(craft_id, k)
        Agent.remove_id(k)


def grid_pos_data(id):
    """get a set of agent ids of the grid objects on the specified ship, at the location specified

    Args:
        so_id (agent): agent id or object 
        x (int): The x grid location
        y (int): The y grid location

    Returns:
        (float,float,float) : x, y, path_length
    """
    blob = to_data_set(to_id(id))
    if blob is None:
        (None, None, None)
    path_length = blob.get("path_length", 0)
    curx= blob.get("curx", 0)
    cury=blob.get("cury",  0)
    return (curx, cury, path_length)

from ..griddispatcher import GridDispatcher

def grid_remove_move_role(event):
    if event.sub_tag == "finished_path":
        remove_role(event.origin_id, "_moving_")
    

GridDispatcher.add_any_object(grid_remove_move_role)