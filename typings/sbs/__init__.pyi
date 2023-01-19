def add_client_tag() -> None:
    """return a list of client ids, for the computers that are currently connected to this server."""
def app_milliseconds() -> int:
    ...
def app_minutes() -> int:
    ...
def app_seconds() -> int:
    ...
def assign_client_to_ship(arg0: int, arg1: int) -> None:
    """Tells a client computer which ship it should control."""
def broad_test(arg0: float, arg1: float, arg2: float, arg3: float, arg4: int) -> List[sbs.space_object]:
    """return a list of space objects that are currently inside an x/z 2d rect  ARGS: 2D bounding rect, and type value (0, 1, or 2, -1 = all)"""
def clear_client_tags() -> None:
    """return a list of client ids, for the computers that are currently connected to this server."""
def create_new_sim() -> None:
    """all space objects are deleted; a blank slate is born."""
def create_transient(arg0: int, arg1: int, arg2: int, arg3: int, arg4: float, arg5: float, arg6: float, arg7: str) -> None:
    """Generates a temporary graphical object, like an explosion."""
def delete_object(arg0: int) -> None:
    """deletes a space object by its ID"""
def distance(arg0: sbs.space_object, arg1: sbs.space_object) -> float:
    """returns the distance between two space objects; arguments are two spaceObjects"""
def distance_between_navpoints(arg0: str, arg1: str) -> float:
    """returns the distance between two nav points; navpoints by name"""
def distance_id(arg0: int, arg1: int) -> float:
    """returns the distance between two space objects; arguments are two IDs"""
def distance_point_line(arg0: sbs.vec3, arg1: sbs.vec3, arg2: sbs.vec3) -> tuple:
    """calulates the distance from a point to a line, for checking potential collisions. Returns a tuple, containing: distance to collision pt along line; distance from line start to point; tangent (positive == in front"""
def distance_to_navpoint(arg0: str, arg1: int) -> float:
    """returns the distance between a nav point and a space object; navpoint name, then object ID"""
def get_client_ID_list() -> List[int]:
    """return a list of client ids, for the computers that are currently connected to this server."""
def get_screen_size() -> sbs.vec2:
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
def send_client_widget_rects(arg0: int, arg1: str, arg2: float, arg3: float, arg4: float, arg5: float, arg6: float, arg7: float, arg8: float, arg9: float) -> None:
    """changes the rects of a gameplay widget, on the targeted client (0 = server screen)."""
def send_comms_button_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string bodyText"""
def send_comms_message_to_player_ship(playerID: int, sourceID: int, colorDesc: str, faceDesc: str, titleText: str, bodyText: str, messageTagSet: str = '') -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string bodyText"""
def send_comms_selection_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string bodyText"""
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
def set_dmx_channel(arg0: int, arg1: int, arg2: int, arg3: int, arg4: int, arg5: int) -> None:
    """set a color channel of dmx."""
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
    def flush(self: sbs.Writer) -> None:
        ...
    def write(self: sbs.Writer, arg0: str) -> None:
        ...
class event(object): ### from pybind
    """class event"""
    @property
    def client_id (self: sbs.event) -> int:
        """id of computer this event came from."""
    @property
    def event_time (self: sbs.event) -> int:
        """long int, time this damage occured, compare to simulation.time_tick_counter"""
    @property
    def extra_tag (self: sbs.event) -> str:
        """string, even more information"""
    @property
    def origin_id (self: sbs.event) -> int:
        """id of space object this event came from"""
    @property
    def parent_id (self: sbs.event) -> int:
        """id of owner/creator of space object this event came from (like the ship that fired the missile)"""
    @property
    def selected_id (self: sbs.event) -> int:
        """id of space object this event is talking about, or doing something to"""
    @property
    def source_point (self: sbs.event) -> sbs.vec3:
        """vec3, 3d point this event originated from"""
    @property
    def sub_float (self: sbs.event) -> float:
        """float, numeric information"""
    @property
    def sub_tag (self: sbs.event) -> str:
        """string describing message sub-type"""
    @property
    def tag (self: sbs.event) -> str:
        """string describing message type"""
    @property
    def value_tag (self: sbs.event) -> str:
        """string, more information"""
class grid_object(object): ### from pybind
    """class grid_object"""
    @property
    def data_set (self: sbs.grid_object) -> ObjectDataBlob:
        """object_data_set, read only, reference to the object_data_set of this particular grid object"""
    @property
    def name (self: sbs.grid_object) -> str:
        """string, text name"""
    @name.setter
    def name (self: sbs.grid_object, arg0: str) -> None:
        """string, text name"""
    @property
    def tag (self: sbs.grid_object) -> str:
        """string, text tag"""
    @tag.setter
    def tag (self: sbs.grid_object, arg0: str) -> None:
        """string, text tag"""
    @property
    def type (self: sbs.grid_object) -> str:
        """string, text value, broad type of object"""
    @type.setter
    def type (self: sbs.grid_object, arg0: str) -> None:
        """string, text value, broad type of object"""
    @property
    def unique_ID (self: sbs.grid_object) -> int:
        """uint64, read only, id of this particular grid object"""
class hullmap(object): ### from pybind
    """class hullmap"""
    @property
    def art_file_root (self: sbs.hullmap) -> str:
        """string, file name, used to get top-down image from disk"""
    @art_file_root.setter
    def art_file_root (self: sbs.hullmap, arg0: str) -> None:
        """string, file name, used to get top-down image from disk"""
    def create_grid_object(self: sbs.hullmap, arg0: str, arg1: str, arg2: str) -> sbs.grid_object:
        """returns a gridobject, after creating it"""
    def delete_grid_object(self: sbs.hullmap, arg0: sbs.grid_object) -> bool:
        """deletes the grid object, returns true if deletion actually occured"""
    @property
    def desc (self: sbs.hullmap) -> str:
        """string, description text"""
    @desc.setter
    def desc (self: sbs.hullmap, arg0: str) -> None:
        """string, description text"""
    def get_grid_object_by_id(self: sbs.hullmap, arg0: int) -> sbs.grid_object:
        """returns a gridobject, by int32 ID"""
    def get_grid_object_by_index(self: sbs.hullmap, arg0: int) -> sbs.grid_object:
        """returns a gridobject, by position in the list"""
    def get_grid_object_by_name(*args, **kwargs):
        """Overloaded function.
        
        1. get_grid_object_by_name(self: sbs.hullmap, arg0: str) -> sbs.grid_object
        
        returns a gridobject, by name
        
        2. get_grid_object_by_name(self: sbs.hullmap, arg0: str) -> sbs.grid_object
        
        returns a gridobject, by text tag"""
    def get_grid_object_count(self: sbs.hullmap) -> int:
        """get the number of grid objects in the list, within this hullmap"""
    @property
    def grid_scale (self: sbs.hullmap) -> float:
        """float, space between grid points"""
    @grid_scale.setter
    def grid_scale (self: sbs.hullmap, arg0: float) -> None:
        """float, space between grid points"""
    @property
    def h (self: sbs.hullmap) -> int:
        """int, total grid hieght"""
    @h.setter
    def h (self: sbs.hullmap, arg0: int) -> None:
        """int, total grid hieght"""
    def is_grid_point_open(self: sbs.hullmap, arg0: int, arg1: int) -> int:
        """is the x/y point within this hullmap open (traversable)? 0 == no"""
    @property
    def name (self: sbs.hullmap) -> str:
        """string, text name"""
    @name.setter
    def name (self: sbs.hullmap, arg0: str) -> None:
        """string, text name"""
    @property
    def symmetrical_flag (self: sbs.hullmap) -> int:
        """int, non-zero if the map is symmetrical"""
    @symmetrical_flag.setter
    def symmetrical_flag (self: sbs.hullmap, arg0: int) -> None:
        """int, non-zero if the map is symmetrical"""
    @property
    def w (self: sbs.hullmap) -> int:
        """int, total grid width"""
    @w.setter
    def w (self: sbs.hullmap, arg0: int) -> None:
        """int, total grid width"""
class navpoint(object): ### from pybind
    """class navpoint"""
    def SetColor(self: sbs.navpoint, arg0: str) -> None:
        """use a string color description to set the color"""
    @property
    def color (self: sbs.navpoint) -> sbs.vec4:
        """vec4, color on 2d radar"""
    @color.setter
    def color (self: sbs.navpoint, arg0: sbs.vec4) -> None:
        """vec4, color on 2d radar"""
    @property
    def pos (self: sbs.navpoint) -> sbs.vec3:
        """vec3, position in space"""
    @pos.setter
    def pos (self: sbs.navpoint, arg0: sbs.vec3) -> None:
        """vec3, position in space"""
    @property
    def text (self: sbs.navpoint) -> str:
        """string, text label"""
    @text.setter
    def text (self: sbs.navpoint, arg0: str) -> None:
        """string, text label"""
class object_data_set(object): ### from pybind
    """class object_data_set"""
    def get(*args, **kwargs):
        """Overloaded function.
        
        1. get(self: sbs.object_data_set, arg0: str, arg1: int) -> object
        
        Get a value, by name
        
        2. get(self: sbs.object_data_set, arg0: int, arg1: int) -> object
        
        Get a value, by ID"""
    def set(*args, **kwargs):
        """Overloaded function.
        
        1. set(self: sbs.object_data_set, tag: str, in: int, index: int = 0, extraDocText: str = 'a') -> int
        
        Set an int value, by name
        
        2. set(self: sbs.object_data_set, tag: str, in: int, index: int = 0, extraDocText: str = 'a') -> int
        
        Set an int64 value, by name
        
        3. set(self: sbs.object_data_set, tag: str, in: int, index: int = 0, extraDocText: str = 'a') -> int
        
        Set a uint64 value, by name
        
        4. set(self: sbs.object_data_set, tag: str, in: float, index: int = 0, extraDocText: str = 'a') -> int
        
        Set a float value, by name
        
        5. set(self: sbs.object_data_set, tag: str, in: str, index: int = 0, extraDocText: str = 'a') -> int
        
        Set a string value, by name
        
        6. set(self: sbs.object_data_set, arg0: int, arg1: int, arg2: int) -> int
        
        Set an int value, by ID
        
        7. set(self: sbs.object_data_set, arg0: int, arg1: int, arg2: int) -> int
        
        Set an int64 value, by ID
        
        8. set(self: sbs.object_data_set, arg0: int, arg1: int, arg2: int) -> int
        
        Set a uint64 value, by ID
        
        9. set(self: sbs.object_data_set, arg0: int, arg1: float, arg2: int) -> int
        
        Set a float value, by ID
        
        10. set(self: sbs.object_data_set, arg0: int, arg1: str, arg2: int) -> int
        
        Set a string value, by ID"""
class quaternion(object): ### from pybind
    """class quaternion"""
    def __init__(*args, **kwargs):
        """Overloaded function.
        
        1. __init__(self: sbs.quaternion, arg0: float, arg1: float, arg2: float, arg3: float) -> None
        
        2. __init__(self: sbs.quaternion, arg0: sbs.quaternion) -> None
        
        3. __init__(self: sbs.quaternion) -> None"""
    @property
    def w (self: sbs.quaternion) -> float:
        """float, component value"""
    @w.setter
    def w (self: sbs.quaternion, arg0: float) -> None:
        """float, component value"""
    @property
    def x (self: sbs.quaternion) -> float:
        """float, component value"""
    @x.setter
    def x (self: sbs.quaternion, arg0: float) -> None:
        """float, component value"""
    @property
    def y (self: sbs.quaternion) -> float:
        """float, component value"""
    @y.setter
    def y (self: sbs.quaternion, arg0: float) -> None:
        """float, component value"""
    @property
    def z (self: sbs.quaternion) -> float:
        """float, component value"""
    @z.setter
    def z (self: sbs.quaternion, arg0: float) -> None:
        """float, component value"""
class simulation(object): ### from pybind
    """class simulation"""
    def AddTractorConnection(self: sbs.simulation, arg0: int, arg1: int, arg2: sbs.vec3, arg3: float) -> sbs.tractor_connection:
        """makes a new connection between two space objects.  Args: u64 sourceID, u64 targetID, sbs::vec3 offsetPoint, float pullDistance"""
    def ClearTractorConnections(self: sbs.simulation) -> None:
        """destroys all existing tractor connections right now."""
    def DeleteTractorConnection(self: sbs.simulation, arg0: int, arg1: int) -> None:
        """finds and deletes an existing tractor connection.  Args: u64 sourceID, u64 targetID"""
    def GetTractorConnection(self: sbs.simulation, arg0: int, arg1: int) -> sbs.tractor_connection:
        ...
    def add_navpoint(self: sbs.simulation, arg0: float, arg1: float, arg2: float, arg3: str, arg4: str) -> sbs.navpoint:
        """adds a new navpoint to space; don't hold on to this Navpoint object in a global; keep the name string instead    args:  float x, float y, float z, std::string text, std::string colorDesc"""
    def clear_navpoints(self: sbs.simulation) -> None:
        """deletes all navpoints"""
    def delete_navpoint_by_name(self: sbs.simulation, arg0: str) -> None:
        """deletes navpoint by its name"""
    def delete_navpoint_by_reference(self: sbs.simulation, arg0: sbs.navpoint) -> None:
        """deletes navpoint by its reference"""
    def get_hull_map(self: sbs.simulation, arg0: int) -> sbs.hullmap:
        """gets the hull map object for this space object"""
    def get_navpoint_by_name(self: sbs.simulation, arg0: str) -> sbs.navpoint:
        """takes a string name, returns the associated Navpoint object"""
    def get_space_object(self: sbs.simulation, arg0: int) -> sbs.space_object:
        """returns the refence to a spaceobject, by ID"""
    def make_new_active(self: sbs.simulation, arg0: str, arg1: str) -> int:
        """creates a new spaceobject"""
    def make_new_passive(self: sbs.simulation, arg0: str, arg1: str) -> int:
        """creates a new spaceobject"""
    def make_new_player(self: sbs.simulation, arg0: str, arg1: str) -> int:
        """creates a new spaceobject"""
    def navpoint_exists(self: sbs.simulation, arg0: str) -> bool:
        """returns true if the navpoint exists, by name"""
    def reposition_space_object(self: sbs.simulation, arg0: sbs.space_object, arg1: float, arg2: float, arg3: float) -> None:
        """immedaitely changes the position of a spaceobject"""
    def space_object_exists(self: sbs.simulation, arg0: int) -> bool:
        """returns true if the spaceobject exists, by ID"""
    @property
    def time_tick_counter (self: sbs.simulation) -> int:
        """get current time value"""
class space_object(object): ### from pybind
    """class space_object"""
    @property
    def cur_speed (self: sbs.space_object) -> float:
        """float, speed of object"""
    @cur_speed.setter
    def cur_speed (self: sbs.space_object, arg0: float) -> None:
        """float, speed of object"""
    @property
    def data_set (self: sbs.space_object) -> sbs.object_data_set:
        """object_data_set, read only, refernce to the object_data_set of this particular object"""
    @property
    def data_tag (self: sbs.space_object) -> str:
        """string, name of data entry in shipData.json"""
    @data_tag.setter
    def data_tag (self: sbs.space_object, arg0: str) -> None:
        """string, name of data entry in shipData.json"""
    @property
    def exclusion_radius (self: sbs.space_object) -> float:
        """float, other objects cannot be closer to me than this distance"""
    @exclusion_radius.setter
    def exclusion_radius (self: sbs.space_object, arg0: float) -> None:
        """float, other objects cannot be closer to me than this distance"""
    @property
    def fat_radius (self: sbs.space_object) -> float:
        """float, radius of box for internal sorting calculations"""
    @fat_radius.setter
    def fat_radius (self: sbs.space_object, arg0: float) -> None:
        """float, radius of box for internal sorting calculations"""
    def forward_vector(self: sbs.space_object) -> sbs.vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
    @property
    def pos (self: sbs.space_object) -> sbs.vec3:
        """vec3, position in space"""
    @pos.setter
    def pos (self: sbs.space_object, arg0: sbs.vec3) -> None:
        """vec3, position in space"""
    def right_vector(self: sbs.space_object) -> sbs.vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
    @property
    def rot_quat (self: sbs.space_object) -> sbs.quaternion:
        """quaternion, heading and orientation of this object"""
    @rot_quat.setter
    def rot_quat (self: sbs.space_object, arg0: sbs.quaternion) -> None:
        """quaternion, heading and orientation of this object"""
    def set_behavior(self: sbs.space_object, arg0: str) -> None:
        """set name of behavior module
        current available behavior modules : nebula, npcship, asteroid, playership, station"""
    @property
    def side (self: sbs.space_object) -> str:
        """string, friendly to other objects on this same side; leave empty for 'no side'"""
    @side.setter
    def side (self: sbs.space_object, arg0: str) -> None:
        """string, friendly to other objects on this same side; leave empty for 'no side'"""
    @property
    def steer_pitch (self: sbs.space_object) -> float:
        """float, change to heading and orientation of this object, over time"""
    @steer_pitch.setter
    def steer_pitch (self: sbs.space_object, arg0: float) -> None:
        """float, change to heading and orientation of this object, over time"""
    @property
    def steer_roll (self: sbs.space_object) -> float:
        """float, change to heading and orientation of this object, over time"""
    @steer_roll.setter
    def steer_roll (self: sbs.space_object, arg0: float) -> None:
        """float, change to heading and orientation of this object, over time"""
    @property
    def steer_yaw (self: sbs.space_object) -> float:
        """float, change to heading and orientation of this object, over time"""
    @steer_yaw.setter
    def steer_yaw (self: sbs.space_object, arg0: float) -> None:
        """float, change to heading and orientation of this object, over time"""
    @property
    def tick_type (self: sbs.space_object) -> str:
        """string, name of behavior module
        current available behavior modules : nebula, npcship, asteroid, playership, station"""
    @property
    def tick_type_ID (self: sbs.space_object) -> int:
        """int32, read only, internal representation of tick_type"""
    @property
    def type (self: sbs.space_object) -> int:
        """int, 0=passive, 1=active, 2=playerShip"""
    @property
    def unique_ID (self: sbs.space_object) -> int:
        """uint64, read only, id of this particular object"""
    def up_vector(self: sbs.space_object) -> sbs.vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
class tractor_connection(object): ### from pybind
    """class tractor_connection"""
    @property
    def offset (self: sbs.tractor_connection) -> float:
        """float, how much the target is pulled towards the offset every tick. 0 = infinite pull, target locked to boss"""
    @offset.setter
    def offset (self: sbs.tractor_connection, arg0: float) -> None:
        """float, how much the target is pulled towards the offset every tick. 0 = infinite pull, target locked to boss"""
    @property
    def source_id (self: sbs.tractor_connection) -> int:
        """int, ID of boss/master/major object"""
    @property
    def target_id (self: sbs.tractor_connection) -> int:
        """int, ID of object that is attached to the other"""
class vec2(object): ### from pybind
    """class vec2"""
    def __add__(self: sbs.vec2, arg0: sbs.vec2) -> sbs.vec2:
        ...
    def __iadd__(self: sbs.vec2, arg0: sbs.vec2) -> sbs.vec2:
        ...
    def __imul__(self: sbs.vec2, arg0: float) -> sbs.vec2:
        ...
    def __init__(*args, **kwargs):
        """Overloaded function.
        
        1. __init__(self: sbs.vec2, arg0: float, arg1: float) -> None
        
        2. __init__(self: sbs.vec2, arg0: sbs.vec2) -> None
        
        3. __init__(self: sbs.vec2) -> None"""
    def __mul__(self: sbs.vec2, arg0: float) -> sbs.vec2:
        ...
    def __neg__(self: sbs.vec2) -> sbs.vec2:
        ...
    def __rmul__(self: sbs.vec2, arg0: float) -> sbs.vec2:
        ...
    @property
    def x (self: sbs.vec2) -> float:
        """float, component value"""
    @x.setter
    def x (self: sbs.vec2, arg0: float) -> None:
        """float, component value"""
    @property
    def y (self: sbs.vec2) -> float:
        """float, component value"""
    @y.setter
    def y (self: sbs.vec2, arg0: float) -> None:
        """float, component value"""
class vec3(object): ### from pybind
    """class vec3"""
    def __add__(self: sbs.vec3, arg0: sbs.vec3) -> sbs.vec3:
        ...
    def __iadd__(self: sbs.vec3, arg0: sbs.vec3) -> sbs.vec3:
        ...
    def __imul__(self: sbs.vec3, arg0: float) -> sbs.vec3:
        ...
    def __init__(*args, **kwargs):
        """Overloaded function.
        
        1. __init__(self: sbs.vec3, arg0: float, arg1: float, arg2: float) -> None
        
        2. __init__(self: sbs.vec3, arg0: sbs.vec3) -> None
        
        3. __init__(self: sbs.vec3) -> None"""
    def __mul__(self: sbs.vec3, arg0: float) -> sbs.vec3:
        ...
    def __neg__(self: sbs.vec3) -> sbs.vec3:
        ...
    def __rmul__(self: sbs.vec3, arg0: float) -> sbs.vec3:
        ...
    @property
    def x (self: sbs.vec3) -> float:
        """float, component value"""
    @x.setter
    def x (self: sbs.vec3, arg0: float) -> None:
        """float, component value"""
    @property
    def y (self: sbs.vec3) -> float:
        """float, component value"""
    @y.setter
    def y (self: sbs.vec3, arg0: float) -> None:
        """float, component value"""
    @property
    def z (self: sbs.vec3) -> float:
        """float, component value"""
    @z.setter
    def z (self: sbs.vec3, arg0: float) -> None:
        """float, component value"""
class vec4(object): ### from pybind
    """class vec4"""
    def __add__(self: sbs.vec4, arg0: sbs.vec4) -> sbs.vec4:
        ...
    def __iadd__(self: sbs.vec4, arg0: sbs.vec4) -> sbs.vec4:
        ...
    def __imul__(self: sbs.vec4, arg0: float) -> sbs.vec4:
        ...
    def __init__(*args, **kwargs):
        """Overloaded function.
        
        1. __init__(self: sbs.vec4, arg0: float, arg1: float, arg2: float, arg3: float) -> None
        
        2. __init__(self: sbs.vec4, arg0: sbs.vec4) -> None
        
        3. __init__(self: sbs.vec4) -> None"""
    def __mul__(self: sbs.vec4, arg0: float) -> sbs.vec4:
        ...
    def __neg__(self: sbs.vec4) -> sbs.vec4:
        ...
    def __rmul__(self: sbs.vec4, arg0: float) -> sbs.vec4:
        ...
    @property
    def a (self: sbs.vec4) -> float:
        """float, component value (0.0-1.0)"""
    @a.setter
    def a (self: sbs.vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
    @property
    def b (self: sbs.vec4) -> float:
        """float, component value (0.0-1.0)"""
    @b.setter
    def b (self: sbs.vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
    @property
    def g (self: sbs.vec4) -> float:
        """float, component value (0.0-1.0)"""
    @g.setter
    def g (self: sbs.vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
    @property
    def r (self: sbs.vec4) -> float:
        """float, component value (0.0-1.0)"""
    @r.setter
    def r (self: sbs.vec4, arg0: float) -> None:
        """float, component value (0.0-1.0)"""
