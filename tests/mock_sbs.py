from __future__ import annotations
from typing import List
from sbs_utils.vec import Vec3

import sys        
sys.modules["sbs"] = sys.modules[__name__] 


sim = None
seconds = 0


def add_client_tag() -> None:
    """return a list of client ids, for the computers that are currently connected to this server."""
    
def app_milliseconds() -> int:
    global seconds
    return seconds * 1000
def app_minutes() -> int:
    global seconds
    return seconds / 60

def app_seconds() -> int:
    seconds += 1
    return seconds
    ...
def assign_client_to_ship(arg0: int, arg1: int) -> None:
    """Tells a client computer which ship it should control."""
def broad_test(x1: float, z1: float, x2: float, z2: float, tick_type: int) -> List[space_object]:
    """return a list of space objects that are currently inside an x/z 2d rect  ARGS: 2D bounding rect, and type value (0, 1, or 2, -1 = all)"""
    global sim
    ret = []
    # make sure things are oriented right
    if x1> x2:
        x = x1
        x1 = x2
        x2 = x
    if z1> z2:
        z = z1
        z1 = z2
        z2 = z
        
    if sim is not None:
        for v in sim.space_objects.values():
            if tick_type != -1 and tick_type != v._type:
                continue
            pos = v.pos
            if pos.x >= x1 and pos.x < x2 and pos.z >= z1 and pos.z <= z2:
                ret.append(v)
    return ret

            

def clear_client_tags() -> None:
    """return a list of client ids, for the computers that are currently connected to this server."""
def create_new_sim() -> None:
    """all space objects are deleted; a blank slate is born."""
    global sim
    sim = simulation()

def create_transient(arg0: int, arg1: int, arg2: int, arg3: int, arg4: float, arg5: float, arg6: float, arg7: str) -> None:
    """Generates a temporary graphical object, like an explosion."""

def delete_object(arg0: int) -> None:
    """deletes a space object by its ID"""
    

def distance(arg0: space_object, arg1: space_object) -> float:
    """returns the distance between two space objects; arguments are two spaceObjects"""
    one = Vec3(arg0.pos.x, arg0.pos.y,arg0.pos.z)
    two = Vec3(arg1.pos.x, arg1.pos.y,arg1.pos.z)
    three = two - one
    return three.length()
def distance_between_navpoints(arg0: str, arg1: str) -> float:
    """returns the distance between two nav points; navpoints by name"""
    return 1000
def distance_id(arg0: int, arg1: int) -> float:
    global sim
    one = sim.space_objects.get(arg0)
    two = sim.space_objects.get(arg1)
    return distance(one, two)

    """returns the distance between two space objects; arguments are two IDs"""
def distance_to_navpoint(arg0: str, arg1: int) -> float:
    """returns the distance between a nav point and a space object; navpoint name, then object ID"""
    return 1000

def get_client_ID_list() -> List[int]:
    """return a list of client ids, for the computers that are currently connected to this server."""
def get_screen_size() -> vec2:
    """returns a VEC2, with the width and height of the display in pixels"""
def pause_sim() -> None:
    """the sim will now pause; HandlePresentGUI() and HandlePresentGUIMessage() are called."""
def play_music_file(arg0: str, arg1: int, arg2: int) -> None:
    """Plays a music file now, for the specified ship."""
def query_client_tags() -> None:
    """return a list of client ids, for the computers that are currently connected to this server."""
def resume_sim() -> None:
    """the sim will now run; HandleStartMission() and HandleTickMission() are called."""
def send_client_widget_list(arg0: int, arg1: str, arg2: str) -> None:
    """sends the gameplay widgets to draw, on the targeted client (0 = server screen)"""
def send_comms_button_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint32_t playerID (0 = all ships), std::string color, std::string bodyText"""
def send_comms_message_to_player_ship(playerID: int, sourceID: int, colorDesc: str, faceDesc: str, titleText: str, bodyText: str, messageTagSet: str = '') -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint32_t playerID (0 = all ships), std::string color, std::string bodyText"""
def send_comms_selection_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint32_t playerID (0 = all ships), std::string color, std::string bodyText"""
def send_gui_3dship(arg0: int, arg1: str, arg2: str, arg3: float, arg4: float, arg5: float, arg6: float) -> None:
    """Creates a 3D ship box GUI element, on the targeted client (0 = server screen)"""
def send_gui_button(arg0: int, arg1: str, arg2: str, arg3: float, arg4: float, arg5: float, arg6: float) -> None:
    """Creates a button GUI element, on the targeted client (0 = server screen)"""
def send_gui_checkbox(arg0: int, arg1: str, arg2: str, arg3: int, arg4: float, arg5: float, arg6: float, arg7: float) -> None:
    """Creates a checkbox GUI element, on the targeted client (0 = server screen)"""
def send_gui_clear(arg0: int) -> None:
    """Clears all GUI elements from screen, on the targeted client (0 = server screen)"""
def send_gui_dropdown(arg0: int, arg1: str, arg2: str, arg3: str, arg4: float, arg5: float, arg6: float, arg7: float) -> None:
    """Creates a dropdown GUI element, on the targeted client (0 = server screen)"""
def send_gui_face(arg0: int, arg1: str, arg2: str, arg3: float, arg4: float, arg5: float, arg6: float) -> None:
    """Creates a face box GUI element, on the targeted client (0 = server screen)"""
def send_gui_icon(arg0: int, arg1: str, arg2: str, arg3: int, arg4: float, arg5: float, arg6: float) -> None:
    """Creates an icon art GUI element, on the targeted client (0 = server screen)"""
def send_gui_image(arg0: int, arg1: str, arg2: str, arg3: str, arg4: float, arg5: float, arg6: float, arg7: float, arg8: float, arg9: float, arg10: float, arg11: float) -> None:
    """Creates an icon art GUI element, on the targeted client (0 = server screen)"""
def send_gui_slider(arg0: int, arg1: str, arg2: float, arg3: float, arg4: float, arg5: float, arg6: float, arg7: float, arg8: float) -> None:
    """Creates a slider bar GUI element, on the targeted client (0 = server screen) (long clientID, std::string tag, float low, float high, float current, float left, float top, float right, float bottom)"""
def send_gui_text(arg0: int, arg1: str, arg2: str, arg3: float, arg4: float, arg5: float, arg6: float) -> None:
    """Creates a text box GUI element, on the targeted client (0 = server screen)"""
def send_gui_typein(arg0: int, arg1: str, arg2: str, arg3: str, arg4: float, arg5: float, arg6: float, arg7: float) -> None:
    """Creates a text entry GUI element, on the targeted client (0 = server screen)"""
def send_message_to_player_ship(arg0: int, arg1: str, arg2: str) -> None:
    """sends a text message to the text box, on every client for a certain ship. args:  uint32_t playerID (0 = all ships), std::string color, std::string text"""
def send_story_dialog(arg0: int, arg1: str, arg2: str, arg3: str, arg4: str) -> None:
    """sends a story dialog to the targeted client (0 = server screen)"""
def set_music_folder(arg0: str, arg1: int, arg2: int) -> None:
    """Sets the folder from which music is streamed, for the specified ship."""
def set_music_tension(arg0: float, arg1: int, arg2: int) -> None:
    """Sets the tension value of ambient music (0-100), for the specified ship."""
class SHPSYS(object): ### from pybind
    """One of four ship systems to track damage
    
    Members:
    
      WEAPONS : the weapons index for *system_damage*
    
      ENGINES : the engines index for *system_damage*
    
      SENSORS : the sensors index for *system_damage*
    
      SHIELDS : the shields index for *system_damage*"""
    ENGINES : 1
    SENSORS : 2
    SHIELDS : 3
    WEAPONS : 0
class TORPEDO(object): ### from pybind
    """enum of torpedo types
    
    Members:
    
      HOMING : a torpedo type index
    
      NUKE : a torpedo type index
    
      EMP : a torpedo type index
    
      MINE : a torpedo type index
    
      TORPTYPECOUNT : number of torpedo types"""
    EMP : 2
    HOMING : 0
    MINE : 3
    NUKE : 1
    TORPTYPECOUNT : 4
class Writer(object): ### from pybind
    """class Writer"""
    def flush(self: Writer) -> None:
        ...
    def write(self: Writer, arg0: str) -> None:
        ...
class event:
    pass
class event(object): ### from pybind
    """class event"""
    @property
    def client_id (self: event) -> int:
        """id of computer this event came from."""
    @property
    def event_time (self: event) -> int:
        """long int, time this damage occured, compare to simulation.time_tick_counter"""
    @property
    def origin_id (self: event) -> int:
        """id of space object this event came from"""
    @property
    def parent_id (self: event) -> int:
        """id of owner/creator of space object this event came from (like the ship that fired the missile)"""
    @property
    def selected_id (self: event) -> int:
        """id of space object this event is talking about, or doing something to"""
    @property
    def source_point (self: event) -> vec3:
        """vec3, 3d point this event originated from"""
    @property
    def sub_float (self: event) -> float:
        """float, numeric information"""
    @property
    def sub_tag (self: event) -> str:
        """string describing message sub-type"""
    @property
    def tag (self: event) -> str:
        """string describing message type"""
    @property
    def value_tag (self: event) -> str:
        """string, more information"""
class grid_object(object): ### from pybind
    """class grid_object"""
    def __init__(self) -> None:
        self._data_set = object_data_set()
        self._name = ""
        self._tag = ""
        self._type = ""
        self._id = 0
    @property
    def data_set (self: grid_object) -> object_data_set:
        """object_data_set, read only, reference to the object_data_set of this particular grid object"""
        return self._data_set
    @property
    def name (self: grid_object) -> str:
        """string, text name"""
        return self._name
    @name.setter
    def name (self: grid_object, arg0: str) -> None:
        """string, text name"""
        self._name = arg0
    @property
    def tag (self: grid_object) -> str:
        """string, text tag"""
        return self._tag
    @tag.setter
    def tag (self: grid_object, arg0: str) -> None:
        """string, text tag"""
        self._tag = arg0
    @property
    def type (self: grid_object) -> str:
        """string, text value, broad type of object"""
        return self._type
    @type.setter
    def type (self: grid_object, arg0: str) -> None:
        """string, text value, broad type of object"""
        self._type = arg0
    @property
    def unique_ID (self: grid_object) -> int:
        """int32, read only, id of this particular grid object"""
        return self._id

class hullmap(object): ### from pybind
    """class hullmap"""
    
    def __init__(self) -> None:
        self._art_file_root = ""
        self._desc = ""
        self._name = ""
        self.grid_items = []
        self._grid_scale = 1
        self._h = 0
        self._w = 0
        self._sym = 0
        
    @property
    def art_file_root (self: hullmap) -> str:
        """string, file name, used to get top-down image from disk"""
        return self._art_file_root 
    @art_file_root.setter
    def art_file_root (self: hullmap, arg0: str) -> None:
        """string, file name, used to get top-down image from disk"""
        self._art_file_root = arg0
    def create_grid_object(self: hullmap, arg0: str, arg1: str, arg2: str) -> grid_object:
        """returns a gridobject, after creating it"""
        go = grid_object()
        go._name = arg0
        go._tag = arg1
        go._type = arg2
        sim.grid_object_ids+=1
        go._id = sim.grid_object_ids
        sim.grid_objects[go._id] = go
        self.grid_items.append(go)

    def delete_grid_object(self: hullmap, arg0: grid_object) -> bool:
        """deletes the grid object, returns true if deletion actually occured"""
        go = sim.grid_objects.pop(arg0._id, None)
        if go is not None:
            self.grid_items.remove(arg0)
            return True
        return False
    @property
    def desc (self: hullmap) -> str:
        """string, description text"""
        return self._desc
    @desc.setter
    def desc (self: hullmap, arg0: str) -> None:
        """string, description text"""
        self._desc = arg0
    def get_grid_object_by_id(self: hullmap, arg0: int) -> grid_object:
        """returns a gridobject, by int32 ID"""
        return sim.grid_objects.get(arg0)
    def get_grid_object_by_index(self: hullmap, arg0: int) -> grid_object:
        """returns a gridobject, by position in the list"""
    def get_grid_object_by_name(*args, **kwargs):
        """Overloaded function.
        
        1. get_grid_object_by_name(self: hullmap, arg0: str) -> grid_object
        
        returns a gridobject, by name
        
        2. get_grid_object_by_name(self: hullmap, arg0: str) -> grid_object
        
        returns a gridobject, by text tag"""
    def get_grid_object_count(self: hullmap) -> int:
        """get the number of grid objects in the list, within this hullmap"""
    @property
    def grid_scale (self: hullmap) -> float:
        """float, space between grid points"""
        return self._grid_scale
    @grid_scale.setter
    def grid_scale (self: hullmap, arg0: float) -> None:
        """float, space between grid points"""
        self._grid_scale = arg0
    @property
    def h (self: hullmap) -> int:
        """int, total grid hieght"""
        return self._h
    @h.setter
    def h (self: hullmap, arg0: int) -> None:
        """int, total grid hieght"""
        self._h
    def is_grid_point_open(self: hullmap, arg0: int, arg1: int) -> int:
        """is the x/y point within this hullmap open (traversable)? 0 == no"""
    @property
    def name (self: hullmap) -> str:
        """string, text name"""
        return self._name
    @name.setter
    def name (self: hullmap, arg0: str) -> None:
        """string, text name"""
        self._name = arg0
    @property
    def symmetrical_flag (self: hullmap) -> int:
        """int, non-zero if the map is symmetrical"""
        return self._sym
    @symmetrical_flag.setter
    def symmetrical_flag (self: hullmap, arg0: int) -> None:
        """int, non-zero if the map is symmetrical"""
        self._sym = arg0
    @property
    def w (self: hullmap) -> int:
        """int, total grid width"""
        return self._w
    @w.setter
    def w (self: hullmap, arg0: int) -> None:
        """int, total grid width"""
        self._w = arg0
class navpoint(object): ### from pybind
    def __init__(self) -> None:
        self._text = ""
        self._color = vec4()
        self._pos = vec3()

    """class navpoint"""
    def SetColor(self: navpoint, arg0: str) -> None:
        """use a string color description to set the color"""
        self._color = vec4()

    @property
    def color (self: navpoint) -> vec4:
        """vec4, color on 2d radar"""
        return self._color
    @color.setter
    def color (self: navpoint, arg0: vec4) -> None:
        """vec4, color on 2d radar"""
        self._color = arg0
    @property
    def pos (self: navpoint) -> vec3:
        """vec3, position in space"""
        return self._pos
    @pos.setter
    def pos (self: navpoint, arg0: vec3) -> None:
        """vec3, position in space"""
        self._pos = arg0
    @property
    def text (self: navpoint) -> str:
        """string, text label"""
        return self._text
    @text.setter
    def text (self: navpoint, arg0: str) -> None:
        """string, text label"""
        sim.nav_points.pop(self._text, None)
        self._text = arg0
        sim.nav_points[arg0] = self

class object_data_set(object): ### from pybind
    """class object_data_set"""
    def get(*args, **kwargs):
        """Overloaded function.
        
        1. get(self: object_data_set, arg0: str, arg1: int) -> object
        
        Get a value, by name
        
        2. get(self: object_data_set, arg0: int, arg1: int) -> object
        
        Get a value, by ID"""
    def set(*args, **kwargs):
        """Overloaded function.
        
        1. set(self: object_data_set, tag: str, in: int, index: int = 0, extraDocText: str = 'a') -> int
        
        Set an int value, by name
        
        2. set(self: object_data_set, tag: str, in: int, index: int = 0, extraDocText: str = 'a') -> int
        
        Set an int64 value, by name
        
        3. set(self: object_data_set, tag: str, in: float, index: int = 0, extraDocText: str = 'a') -> int
        
        Set a float value, by name
        
        4. set(self: object_data_set, tag: str, in: str, index: int = 0, extraDocText: str = 'a') -> int
        
        Set a string value, by name
        
        5. set(self: object_data_set, arg0: int, arg1: int, arg2: int) -> int
        
        Set an int value, by ID
        
        6. set(self: object_data_set, arg0: int, arg1: int, arg2: int) -> int
        
        Set an int64 value, by ID
        
        7. set(self: object_data_set, arg0: int, arg1: float, arg2: int) -> int
        
        Set a float value, by ID
        
        8. set(self: object_data_set, arg0: int, arg1: str, arg2: int) -> int
        
        Set a string value, by ID"""
class quaternion(object): ### from pybind
    """class quaternion"""
    def __init__(self, w, x=None, y=None, z=None, **kwargs):
        """Overloaded function.
        
        1. __init__(self: quaternion, arg0: float, arg1: float, arg2: float, arg3: float) -> None
        
        2. __init__(self: quaternion, arg0: quaternion) -> None
        
        3. __init__(self: quaternion) -> None"""
        if isinstance(w, quaternion):
            self._w = w._w
            self._x = w._x
            self._y = w._y
            self._z = w._z
        elif x is not None:
            self._w = w
            self._x = x
            self._y = y
            self._z = z
        else:
            self._w = 0
            self._x = 0
            self._y = 0
            self._z = 0
    @property
    def w (self: quaternion) -> float:
        """float, component value"""
        return self._w
    @w.setter
    def w (self: quaternion, arg0: float) -> None:
        """float, component value"""
        self._w = arg0
    @property
    def x (self: quaternion) -> float:
        """float, component value"""
        return self._x
    @x.setter
    def x (self: quaternion, arg0: float) -> None:
        """float, component value"""
        self._x = arg0
    @property
    def y (self: quaternion) -> float:
        """float, component value"""
        return self._y
    @y.setter
    def y (self: quaternion, arg0: float) -> None:
        """float, component value"""
        self._y = arg0
    @property
    def z (self: quaternion) -> float:
        """float, component value"""
        return self._z
    @z.setter
    def z (self: quaternion, arg0: float) -> None:
        """float, component value"""
        self._z = arg0
class simulation(object): ### from pybind
    def __init__(self):
        
        self.object_ids = 0
        self.space_objects = {}
        self.grid_object_ids = 0
        self.grid_objects = {}
        self.nav_points = {}
        self.hull_map_objects = {}
        self._time_tick = 0 # increment by 30
        self.tractor_connections = {}

    """class simulation"""
    def AddTractorConnection(self: simulation, arg0: int, arg1: int, arg2: vec3, arg3: float) -> tractor_connection:
        """makes a new connection between two space objects.  Args: uint32_t sourceID, uint32_t targetID, sbs::vec3 offsetPoint, float pullDistance"""
        con = tractor_connection()
        con._source_id = arg0
        con._target_id = arg1
        con._pull = arg3
        con._vec = arg2
        self.tractor_connections[(con.source_id, con.target_id)] = con
        
    def ClearTractorConnections(self: simulation) -> None:
        """destroys all existing tractor connections right now."""
        self.tractor_connections = {}
    def DeleteTractorConnection(self: simulation, arg0: int, arg1: int) -> None:
        """finds and deletes an existing tractor connection.  Args: uint32_t sourceID, uint32_t targetID"""
        self.tractor_connections.pop((arg0,arg1))
    def GetTractorConnection(self: simulation, arg0: int, arg1: int) -> tractor_connection:
        self.tractor_connections.get((arg0,arg1))
    def add_navpoint(self: simulation, arg0: float, arg1: float, arg2: float, arg3: str, arg4: str) -> navpoint:
        """adds a new navpoint to space; don't hold on to this Navpoint object in a global; 
        keep the name string instead    
        args:  float x, float y, float z, std::string text, std::string colorDesc"""
        nav = navpoint()
        nav._color = arg4
        nav._pos = vec3(arg0, arg1, arg2)
        nav._text = arg3

        self.nav_points[nav._text] = nav

    def clear_navpoints(self: simulation) -> None:
        """deletes all navpoints"""
        self.nav_points = {}
        
    def delete_navpoint_by_name(self: simulation, arg0: str) -> None:
        """deletes navpoint by its name"""
        self.nav_points.pop(arg0, None)
    def delete_navpoint_by_reference(self: simulation, arg0: navpoint) -> None:
        """deletes navpoint by its reference"""
        self.nav_points.pop(arg0.text, None)

    def get_hull_map(self: simulation, arg0: int) -> hullmap:
        """gets the hull map object for this space object"""
        hull_map = self.hull_map_objects.get(arg0)
        if not hull_map:
            hull_map = hullmap()
            self.hull_map_objects[arg0]=hull_map
        return hullmap

    def get_navpoint_by_name(self: simulation, arg0: str) -> navpoint:
        """takes a string name, returns the associated Navpoint object"""
        return self.nav_points.get(arg0, None)

    def get_space_object(self: simulation, arg0: int) -> space_object:
        """returns the refence to a spaceobject, by ID"""
        return self.space_objects.get(arg0)

    def make_new_active(self: simulation, arg0: str, arg1: str) -> int:
        """creates a new spaceobject"""
        return self._make_space_object(arg0, arg1, 1)
    def make_new_passive(self: simulation, arg0: str, arg1: str) -> int:
        """creates a new spaceobject"""
        return self._make_space_object(arg0, arg1, 0)
    def make_new_player(self: simulation, arg0: str, arg1: str) -> int:
        return self._make_space_object(arg0, arg1, 2)

    def _make_space_object(self: simulation, arg0: str, arg1: str, tick_type:int) -> int:
        """creates a new spaceobject"""
        global sim
        sim.object_ids += 1
        id = sim.object_ids
        obj  = space_object()
        obj._id = id
        obj._type = tick_type # """int, 0=passive, 1=active, 2=playerShip""" #
        obj._data_tag = arg1
        obj._tick_type = arg0
        sim.space_objects[id] = obj
        return id

    def navpoint_exists(self: simulation, arg0: str) -> bool:
        """returns true if the navpoint exists, by name"""
        return self.nav_points.get(arg0) is not None
    def reposition_space_object(self: simulation, arg0: space_object, arg1: float, arg2: float, arg3: float) -> None:
        """immedaitely changes the position of a spaceobject"""
        
        if arg0:
            arg0.pos.x = arg1
            arg0.pos.y = arg2
            arg0.pos.z = arg3

    def space_object_exists(self: simulation, arg0: int) -> bool:
        """returns true if the spaceobject exists, by ID"""
        return (arg0 in self.space_objects)
            
    @property
    def time_tick_counter (self: simulation) -> int:
        """get current time value"""
        return self._time_tick_counter

class space_object(object): ### from pybind
    def __init__(self):
        self. data_set_blob = object_data_set()
        self._side = ""
        self._cur_speed = 0.0
        self._data_tag = ""
        self._tick_type = ""
        self._type = 0
        self._id = 0
        self._exclusion_radius= 0
        self._fat_radius= 0
        self._steer_pitch = 0
        self._steer_roll = 0
        self._steer_yaw = 0
        self._pos = vec3(0,0,0)
    """class space_object"""
    @property
    def cur_speed (self: space_object) -> float:
        """float, speed of object"""
        return self._cur_speed
    @cur_speed.setter
    def cur_speed (self: space_object, arg0: float) -> None:
        """float, speed of object"""
        self._cur_speed = arg0
    @property
    def data_set (self: space_object) -> object_data_set:
        """object_data_set, read only, refernce to the object_data_set of this particular object"""
        return self. data_set_blob
    @property
    def data_tag (self: space_object) -> str:
        """string, name of data entry in shipData.json"""
        return self._data_tag
    @data_tag.setter
    def data_tag (self: space_object, arg0: str) -> None:
        """string, name of data entry in shipData.json"""
        self._data_tag = arg0
    @property
    def exclusion_radius (self: space_object) -> float:
        """float, other objects cannot be closer to me than this distance"""
        return self._exclusion_radius
    @exclusion_radius.setter
    def exclusion_radius (self: space_object, arg0: float) -> None:
        """float, other objects cannot be closer to me than this distance"""
        self._exclusion_radius = arg0
    @property
    def fat_radius (self: space_object) -> float:
        """float, radius of box for internal sorting calculations"""
        return self._fat_radius
    @fat_radius.setter
    def fat_radius (self: space_object, arg0: float) -> None:
        """float, radius of box for internal sorting calculations"""
        self._fat_radius = arg0
    @property
    def pos (self: space_object) -> vec3:
        """vec3, position in space"""
        return self._pos
    @pos.setter
    def pos (self: space_object, arg0: vec3) -> None:
        """vec3, position in space"""
        self._pos = arg0
    @property
    def rot_quat (self: space_object) -> quaternion:
        """quaternion, heading and orientation of this object"""
    @rot_quat.setter
    def rot_quat (self: space_object, arg0: quaternion) -> None:
        """quaternion, heading and orientation of this object"""
    def set_behavior(self: space_object, arg0: str) -> None:
        """set name of behavior module
        current available behavior modules : nebula, npcship, asteroid, playership, station"""
        self._tick_type = arg0
    @property
    def side (self: space_object) -> str:
        """string, friendly to other objects on this same side; leave empty for 'no side'"""
        return self._side
    @side.setter
    def side (self: space_object, arg0: str) -> None:
        """string, friendly to other objects on this same side; leave empty for 'no side'"""
        self._side = arg0
    @property
    def steer_pitch (self: space_object) -> float:
        """float, change to heading and orientation of this object, over time"""
        return self._steer_pitch
    @steer_pitch.setter
    def steer_pitch (self: space_object, arg0: float) -> None:
        """float, change to heading and orientation of this object, over time"""
        self._steer_pitch = arg0
    @property
    def steer_roll (self: space_object) -> float:
        """float, change to heading and orientation of this object, over time"""
        return self._steer_roll
    @steer_roll.setter
    def steer_roll (self: space_object, arg0: float) -> None:
        """float, change to heading and orientation of this object, over time"""
        self._steer_roll=arg0
    @property
    def steer_yaw (self: space_object) -> float:
        """float, change to heading and orientation of this object, over time"""
        return self._steer_yaw
    @steer_yaw.setter
    def steer_yaw (self: space_object, arg0: float) -> None:
        """float, change to heading and orientation of this object, over time"""
        self._steer_yaw = arg0
    @property
    def tick_type (self: space_object) -> str:
        """string, name of behavior module
        current available behavior modules : nebula, npcship, asteroid, playership, station"""
        return self._tick_type
    @property
    def tick_type_ID (self: space_object) -> int:
        """int32, read only, internal representation of tick_type"""
    @property
    def type (self: space_object) -> int:
        """int, 0=passive, 1=active, 2=playerShip"""
        self._type
    @property
    def unique_ID (self: space_object) -> int:
        """int32, read only, id of this particular object"""
        return self._id
class tractor_connection(object): ### from pybind
    """class tractor_connection"""
    def __init__(self) -> None:
        self._offset = 0
        self._source_id = 0
        self._target_id = 0
        self._vec = vec3()
        self._pull = 0
    @property
    def offset (self: tractor_connection) -> float:
        """float, how much the target is pulled towards the offset every tick. 0 = infinite pull, target locked to boss"""
        return self._offset
    @offset.setter
    def offset (self: tractor_connection, arg0: float) -> None:
        """float, how much the target is pulled towards the offset every tick. 0 = infinite pull, target locked to boss"""
        self._offset - arg0
    @property
    def source_id (self: tractor_connection) -> int:
        """int, ID of boss/master/major object"""
        return self._source_id
    @property
    def target_id (self: tractor_connection) -> int:
        """int, ID of object that is attached to the other"""
        return self._target_id
class vec2(object): ### from pybind
    """class vec2"""
    def __init__(self, x, y=None):
        """Overloaded function.
        
        1. __init__(self: vec2, arg0: float, arg1: float) -> None
        
        2. __init__(self: vec2, arg0: vec2) -> None
        
        3. __init__(self: vec2) -> None"""
        if isinstance(x, vec2):
            self._x = x.x
            self._y = x.y
        else:
            self._x = x
            self._y = y

    @property
    def x (self: vec2) -> float:
        """float, component value"""
        return self._x
    @x.setter
    def x (self: vec2, arg0: float) -> None:
        """float, component value"""
        self._x = arg0
    @property
    def y (self: vec2) -> float:
        """float, component value"""
        return self._y
    @y.setter
    def y (self: vec2, arg0: float) -> None:
        """float, component value"""
        self._y = arg0
class vec3(object): ### from pybind
    """class vec3"""
    def __init__(self, x, y=None, z=None):
        """Overloaded function.
        
        1. __init__(self: vec3, arg0: float, arg1: float, arg2: float) -> None
        
        2. __init__(self: vec3, arg0: vec3) -> None
        
        3. __init__(self: vec3) -> None"""
        if isinstance(x, vec3):
            self._x = x._x
            self._y = x._y
            self._z = x._z
        elif y is not None:
            self._x = x
            self._y = y
            self._z = z
        else:
            self._x = 0
            self._y = 0
            self._z = 0


    @property
    def x (self: vec3) -> float:
        """float, component value"""
        return self._x
    @x.setter
    def x (self: vec3, arg0: float) -> None:
        """float, component value"""
        self._x = arg0
    @property
    def y (self: vec3) -> float:
        """float, component value"""
        return self._y
    @y.setter
    def y (self: vec3, arg0: float) -> None:
        """float, component value"""
        self._y = arg0
    @property
    def z (self: vec3) -> float:
        """float, component value"""
        return self._z
    @z.setter
    def z (self: vec3, arg0: float) -> None:
        """float, component value"""
        self._z = arg0
class vec4(object): ### from pybind
    """class vec4"""
    def __init__(self, r, g=None, b=None, a=None):
        """Overloaded function.
        
        1. __init__(self: vec4, arg0: float, arg1: float, arg2: float, arg3: float) -> None
        
        2. __init__(self: vec4, arg0: vec4) -> None
        
        3. __init__(self: vec4) -> None"""
        if isinstance(r, vec4):
            self._r = r._r
            self._g = r._g
            self._b = r._b
            self._a = r._a
        elif r is not None:
            self._r = r
            self._g = g
            self._b = b
            self._a = a
        else:
            self._r = 0
            self._g = 0
            self._b = 0
            self._a = 0

    @property
    def a (self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._a
    @a.setter
    def a (self: vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
        self._a = arg0
    @property
    def b (self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._b
    @b.setter
    def b (self: vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
        self._b = arg0
    @property
    def g (self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._g
    @g.setter
    def g (self: vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
        self._g = arg0
    @property
    def r (self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._r
    @r.setter
    def r (self: vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
        self._r = arg0

