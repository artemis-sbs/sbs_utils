from .query import to_blob, to_id, to_object, to_object_list, to_set
from ..agent import CloseData
from ..tickdispatcher import TickDispatcher
from .inventory import get_inventory_value, set_inventory_value
from ..fs import load_json_data, get_artemis_data_dir_filename, get_mission_dir_filename
import functools
import sbs

def grid_objects(so_id):
    gos = set()
    hm = sbs.get_hull_map(to_id(so_id))
    if hm is None:
        return gos
    count = hm.get_grid_object_count()
    for i in range(count):
        go = hm.get_grid_object_by_index(i)
        gos.add(go.unique_ID)
    return gos

def grid_objects_at(so_id, x,y):
    gos = set()
    hm = sbs.get_hull_map(to_id(so_id))
    if hm is None:
        return gos
    return to_set(hm.get_objects_at_point(x,y))


################################
##########################################
####### TODO: Update for sets

def grid_close_list(grid_obj, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    """ Finds a list of matching objects
    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str]
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func:
    :return: A list of close object
    :rtype: List[GridCloseData]
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

def grid_closest(grid_obj, roles=None, max_dist=None, filter_func=None) -> CloseData:
    """ Finds the closest object matching the criteria

    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str] 
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func: function that takes ID
    :return: A list of close object
    :rtype: GridCloseData
    """
    close = grid_close_list(grid_obj, roles, max_dist, filter_func)
    # Maybe not the most efficient
    if len(close)==1:
        return close[0]
    elif len(close)>0:
        return functools.reduce(lambda a, b: a if a.distance < b.distance else b, close)
    
    return None

def grid_target_closest(grid_obj_or_set, roles=None, max_dist=None, filter_func=None):
    """ Find and target the closest object matching the criteria

    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str] 
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func: function
    :param shoot: if the target should be shot at
    :type shoot: bool
    :return: A list of close object
    :rtype: GridCloseData
    """
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        grid_obj=to_object(grid_obj)
        close = grid_closest(grid_obj, roles, max_dist, filter_func)
        if close.id is not None:
            grid_obj.target(close.id)
        return close

def grid_target(grid_obj_or_set, target_id: int, speed=0.01):
    """ Set the item to target

    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
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

def grid_target_pos(grid_obj_or_set, x:float, y:float, speed=0.01):
    """ Set the item to target

    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        blob = to_blob(grid_obj.id)
        curx= blob.get("curx", 0)
        cury=blob.get("cury",  0)

        pathx = blob.get("pathx", 0)
        pathy = blob.set("pathy", 0)
        
        if pathx==x and pathy == y:
            blob.set("move_speed", 0, 0)
            continue
            
        if curx!=x or cury != y:
            blob.set("pathx", x, 0)
            blob.set("pathy", y, 0)
            blob.set("move_speed", speed, 0)
        else:
            blob.set("move_speed", 0, 0)

def grid_clear_target(grid_obj_or_set):
    """ Clear the target

    :param id: the id of the object or set
    :type id: int
    """
    grid_objs= to_object_list(grid_obj_or_set)
    for grid_obj in grid_objs:
        blob = to_blob(grid_obj.id)
        x= blob.get("curx", 0)
        y=blob.get("cury",  0)
        grid_target_pos(grid_obj_or_set, x,y)

        
def get_open_grid_points(id_or_obj):
    the_set = []
    hull_map = sbs.get_hull_map(to_id(id_or_obj))
    if hull_map is not None:
        for x in range(hull_map.w):
            for y in range(hull_map.w):
                if hull_map.is_grid_point_open(x,y) != 0:
                    the_set.append((x,y))
    return the_set


def grid_speech_bubble(id_or_obj, status, color=None, seconds=0, minutes=0):
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
    grid_speech_bubble(id_or_obj, "")
    set_inventory_value(id_or_obj, "speech_bubble_tick_task", None)
    

def grid_short_status(id_or_obj, status, color=None, seconds=0, minutes=0):
    blob = to_blob(id_or_obj)
    if blob is None:
        return
    # Set tooltip
    blob.set("tool_tip_cur_text", status, 0)
    grid_speech_bubble(id_or_obj, status, color, seconds, minutes)

def grid_detailed_status(id_or_obj, status, color=None):
    blob = to_blob(id_or_obj)
    if blob is None:
        return
    # Set tooltip
    blob.set("info_text", status, 0)
    if color is not None:
        blob.set("info_text_color", color, 0)

def grid_clear_detailed_status(id_or_obj):
    grid_detailed_status(id_or_obj, "")
    


_grid_data = None 
def grid_get_grid_data():
    global _grid_data
    if _grid_data is None:
        _grid_data = load_json_data(get_artemis_data_dir_filename("grid_data.json"))
        script_grid_data = load_json_data(get_mission_dir_filename("data\\grid_data.json"))
        if script_grid_data is not None:
            _grid_data |= script_grid_data
    return _grid_data
