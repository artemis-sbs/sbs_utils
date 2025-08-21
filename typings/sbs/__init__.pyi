def add_client_tag() -> None:
    """stub; does nothing yet."""
def add_particle_emittor(spaceObject: sbs.space_object, lifeSpan: int, descriptorString: str) -> int:
    """creates a complex particle emittor and attaches it to a space object."""
def app_milliseconds() -> int:
    ...
def app_minutes() -> int:
    ...
def app_seconds() -> int:
    ...
def assign_client_to_alt_ship(clientComputerID: int, controlledShipID: int) -> None:
    """Tells a client computer that the 2d radar should focus on controlledShipID, instead of its assigned ship.  Turn this code off by providing zero as the second argument."""
def assign_client_to_ship(clientComputerID: int, controlledShipID: int) -> None:
    """Tells a client computer which ship it should control."""
def broad_test(lx: float, lz: float, mx: float, mz: float, abits: int) -> List[sbs.space_object]:
    """return a list of space objects that are currently inside an x/z 2d rect  ARGS: 2D bounding rect, and bitfield"""
def cinematic_control(clientID: int, scriptControlsCamera: int, dollyID: int, dollyPos: sbs.vec3, targetID: int, targetPos: sbs.vec3) -> None:
    """for a specific client (0=server machine), this sets the values to be used with the 'cinematic' console, which requiers a 3d_view widget, and 'cinematic' == camModeTag"""
def clear_client_tags() -> None:
    """stub; does nothing yet."""
def create_new_sim() -> None:
    """all space objects are deleted; a blank slate is born."""
def delete_all_navpoints() -> None:
    """deletes all navpoints on server, and notifies all clients of the change"""
def delete_all_navproxies() -> None:
    """deletes all navproxies on server, and notifies all clients of the change"""
def delete_grid_object(spaceObjectID: int, gridObjID: int) -> None:
    """deletes the grid object, and sends the deletion message to all clients"""
def delete_object(ID: int) -> None:
    """deletes a space object by its ID"""
def delete_particle_emittor(emittorID: int) -> None:
    """deletes a particle emittor by ID."""
def distance(arg0: sbs.space_object, arg1: sbs.space_object) -> float:
    """returns the distance between two space objects; arguments are two spaceObjects"""
def distance_between_navpoints(arg0: int, arg1: int) -> float:
    """returns the distance between two nav points; navpoints by ID"""
def distance_id(arg0: int, arg1: int) -> float:
    """returns the distance between two space objects; arguments are two IDs"""
def distance_point_line(arg0: sbs.vec3, arg1: sbs.vec3, arg2: sbs.vec3) -> tuple:
    """calulates the distance from a point to a line, for checking potential collisions. Returns a tuple, containing: distance to collision pt along line; distance from line start to point; tangent (positive == in front"""
def distance_to_navpoint(arg0: int, arg1: int) -> float:
    """returns the distance between a nav point and a space object; navpoint ID, then object ID"""
def find_valid_grid_point_for_vector3(spaceObjectID: int, vecPoint: sbs.vec3, randomRadius: int) -> List[int]:
    """return a list of two integers, the grid x and y that is open and is closest.  The list is empty if the search fails."""
def find_valid_unoccupied_grid_point_for_vector3(spaceObjectID: int, vecPoint: sbs.vec3, randomRadius: int) -> List[int]:
    """return a list of two integers, the grid x and y that is open and is closest.  The list is empty if the search fails."""
def get_client_ID_list() -> List[int]:
    """return a list of client ids, for the computers that are currently connected to this server."""
def get_debug_gui_tree(clientID: int, tag: str, displayListFlag: int) -> None:
    """sends a GUI debug message from the targeted client (0 = server screen)"""
def get_game_version() -> str:
    """returns the version of the game EXE currently operating this script, as a string."""
def get_hull_map(spaceObjectID: int, forceCreate: bool = False) -> sbs.hullmap:
    """gets the hull map object for this space object; setting forceCreate to True will erase and rebuild the grid (and gridObjects) of this spaceobject"""
def get_preference_float(key: str) -> float:
    """Gets a value from preferences.json"""
def get_preference_int(key: str) -> int:
    """Gets a value from preferences.json"""
def get_preference_string(key: str) -> str:
    """Gets a value from preferences.json"""
def get_screen_size() -> sbs.vec2:
    """returns a VEC2, with the width and height of the display in pixels"""
def get_shared_string(key: str) -> str:
    """gets a shared string, given the key (itself a string).  Shared strings are automatically copied from server to all clients."""
def get_ship_of_client(clientID: int) -> int:
    """returns the player ship ID assigned to the client computer"""
def get_text_block_height(fontTag: str, textToMeasure: str, width: int) -> int:
    """for a font key, a string of (possibly) multiline text, and a pixel width, this returns the height of the drawn text."""
def get_text_line_height(fontTag: str, textToMeasure: str) -> int:
    """for a font key and a text string (one line, no wrapping), this returns the height of the drawn text."""
def get_text_line_width(fontTag: str, textToMeasure: str) -> int:
    """for a font key and a text string (one line, no wrapping), this returns the width of the drawn text."""
def get_type_of_client(clientID: int) -> str:
    """returns the consoleType perviously assigned to the client computer"""
def hide_gui_tag(clientID: int, tag: str) -> None:
    """makes a GUI element invisible, on the targeted client (0 = server screen)"""
def in_standby_list(space_object: sbs.space_object) -> bool:
    """returns true if the spaceobject is in the standby list."""
def in_standby_list_id(id: int) -> bool:
    """returns true if the spaceobject is in the standby list."""
def is_demo() -> bool:
    """Returns true if the EXE is marked as a demo version."""
def particle_at(position: sbs.vec3, descriptorString: str) -> None:
    """emit some particles in space."""
def particle_emittor_exists(emittorID: int) -> bool:
    """checks for the existance of a particle emittor."""
def particle_on(spaceObject: sbs.space_object, descriptorString: str) -> None:
    """emit some particles in space from a space object."""
def pause_sim() -> None:
    """the sim will now pause; HandlePresentGUI() and HandlePresentGUIMessage() are called."""
def play_audio_file(clientID: int, filename: str, volume: float, pitch: float) -> None:
    """Plays a WAV audio file now, for just the specified client, OR zero for server."""
def play_music_file(ID: int, filename: str) -> None:
    """Plays a music file now; ID is ship, OR client, OR zero for server."""
def player_ship_setup_defaults(space_object: sbs.space_object) -> None:
    """Rebuilds the default blob data of this player ship."""
def player_ship_setup_from_data(space_object: sbs.space_object) -> None:
    """Rebuilds the blob data of this player ship from the shipdata.json and the preferences.json."""
def push_to_standby_list(space_object: sbs.space_object) -> None:
    """moves the spaceobject from normal space to the standby list."""
def push_to_standby_list_id(id: int) -> None:
    """moves the spaceobject from normal space to the standby list."""
def query_client_tags() -> None:
    """stub; does nothing yet."""
def query_client_widget_state(clientID: int, widgetName: str, fullScreenFlag: int) -> None:
    """sends a request for the client to send a 'widget_box_state' script event back."""
def remove_gui_hotkey(clientID: int, tag: str) -> None:
    """tells the targeted client (0 = server screen) to delete an existing hot key for a certain retained gui element."""
def request_client_string(clientComputerID: int, string_key: str) -> None:
    """requests a string value from the client computer.  This results in a script message, 'client_string'"""
def resume_sim() -> None:
    """the sim will now run; HandleStartMission() and HandleTickMission() are called."""
def retrieve_from_standby_list(space_object: sbs.space_object) -> None:
    """moves the spaceobject from the standby list to normal space."""
def retrieve_from_standby_list_id(id: int) -> None:
    """moves the spaceobject from the standby list to normal space."""
def run_next_mission(mission_folder: str) -> None:
    """Shuts down this script and starts the mission in the folder argument"""
def send_client_widget_list(clientID: int, consoleType: str, widgetList: str) -> None:
    """sends the gameplay widgets to draw, on the targeted client (0 = server screen)"""
def send_client_widget_rects(arg0: int, arg1: str, arg2: float, arg3: float, arg4: float, arg5: float, arg6: float, arg7: float, arg8: float, arg9: float) -> None:
    """changes the rects of a gameplay widget, on the targeted client (0 = server screen)."""
def send_comms_button_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string bodyText"""
def send_comms_message_to_player_ship(playerID: int, otherID: int, faceDesc: str, titleText: str, titleColor: str, bodyText: str, bodyColor: str) -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint64 playerID (0 = all ships), uint64 otherID, std::string titleText, std::string titleColor, std::string bodyText, std::string bodyColor"""
def send_comms_selection_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string bodyText"""
def send_grid_button_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the engineering console of a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string bodyText"""
def send_grid_selection_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the engineering console of a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string bodyText"""
def send_gui_3dship(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a 3D ship box GUI element, on the targeted client (0 = server screen)"""
def send_gui_button(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a button GUI element, on the targeted client (0 = server screen)"""
def send_gui_checkbox(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a checkbox GUI element, on the targeted client (0 = server screen)"""
def send_gui_clear(clientID: int, tag: str) -> None:
    """Clears all GUI elements from screen, on the targeted client (0 = server screen).  remember to use send_gui_complete after adding widgets."""
def send_gui_clickregion(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a click-region GUI element, on the targeted client (0 = server screen)"""
def send_gui_colorbutton(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a color button GUI element, on the targeted client (0 = server screen)"""
def send_gui_colorcheckbox(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a color checkbox GUI element, on the targeted client (0 = server screen)"""
def send_gui_complete(clientID: int, tag: str) -> None:
    """Flips double-buffered GUI display list, on the targeted client (0 = server screen).  Use after a send_gui_clear() and some send_gui* calls"""
def send_gui_dropdown(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a dropdown GUI element, on the targeted client (0 = server screen)"""
def send_gui_face(clientID: int, parent: str, tag: str, face_string: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a face box GUI element, on the targeted client (0 = server screen)"""
def send_gui_hotkey(clientID: int, category: str, tag: str, keyType: str, description: str) -> None:
    """tells the targeted client (0 = server screen) to handle a hot key for a certain retained gui element."""
def send_gui_icon(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates an icon art GUI element, on the targeted client (0 = server screen)"""
def send_gui_iconbutton(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates an icon-button GUI element, on the targeted client (0 = server screen)"""
def send_gui_iconcheckbox(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates an icon-checkbox GUI element, on the targeted client (0 = server screen)"""
def send_gui_image(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a 2d art image GUI element, on the targeted client (0 = server screen)"""
def send_gui_rawiconbutton(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a simple clickable icon GUI element, on the targeted client (0 = server screen)"""
def send_gui_slider(clientID: int, parent: str, tag: str, current: float, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a slider bar GUI element, on the targeted client (0 = server screen) (long clientID, std::string tag, float low, float high, float current, float left, float top, float right, float bottom, bool showNumberFlag)"""
def send_gui_sub_region(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a subregion GUI element, on the targeted client (0 = server screen)"""
def send_gui_text(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a text box GUI element, on the targeted client (0 = server screen)"""
def send_gui_typein(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a text entry GUI element, on the targeted client (0 = server screen)"""
def send_hold_menu(clientID: int, subject: int, object: int, extra: int, menuOptionStringSet: str) -> None:
    """sends info to client that displays a quick menu list on the 2d radar, as a result of a hold-click. menuOptionStringSet is semicolon-delimited.  Subject, object, and extra are repeated back in message when one of these menu buttons is clicked."""
def send_message_to_client(clientID: int, colorDesc: str, text: str) -> None:
    """sends a text message to the text box, for the specific client. args:  uint64 clientID (0 = server screen), std::string color, std::string text"""
def send_message_to_player_ship(playerID: int, colorDesc: str, text: str) -> None:
    """sends a text message to the text box, on every client for a certain ship. args:  uint64 playerID (0 = all ships), std::string color, std::string text"""
def send_speech_bubble_to_object(clientComputerID: int, spaceObjectID: int, seconds: int, color: str, text: str) -> None:
    """attaches a speech bubble to a space object on the 2d radar."""
def send_story_dialog(clientID: int, title: str, text: str, face: str, color: str) -> None:
    """sends a story dialog to the targeted client (0 = server screen)"""
def set_beam_damages(clientID: int, playerBeamDamage: float, npcBeamDamage: float) -> None:
    """sets the values for player base beam damage, and npc base beam damage.  Per client, or all clients + server (if ID = 0)."""
def set_client_string(clientComputerID: int, string_key: str, string_value: str) -> None:
    """stores a string value (and its string key) to the client computer"""
def set_dmx_channel(clientID: int, channel: int, behavior: int, speed: int, low: int, high: int) -> None:
    """set a color channel of dmx."""
def set_main_view_modes(clientID: int, main_screen_view: str, cam_angle: str, cam_mode: str) -> None:
    """sets the three modes of the main screen view for the specified client.  main_screen_view = (3d_view, info, data);  cam_angle = (front, back, left, right); cam_mode = (first_person, chase, tracking)"""
def set_music_folder(ID: int, filename: str) -> None:
    """Sets the folder from which music is streamed; ID is ship, OR client, OR zero for server."""
def set_music_tension(ID: int, tensionValue: float) -> None:
    """Sets the tension value of ambient music (0-100); ID is ship, OR client, OR zero for server."""
def set_shared_string(key: str, value: str) -> None:
    """sets (or changes) a shared string, given a key and a value (both strings).  The shared strings are automatically copied from server to all clients."""
def set_sky_box(clientID: int, artFileName: str) -> None:
    """sets the skybox art for a clientID (0 = server)."""
def set_sky_box_all(artFileName: str) -> None:
    """sets the skybox art for all connected computers."""
def show_gui_tag(clientID: int, tag: str) -> None:
    """makes a GUI element visible, on the targeted client (0 = server screen)"""
def super_hyper_warp_mode(clientID: int, ship_hull_key: str, on_off_flag: int) -> None:
    """turns on (or off) the super_hyper_warp_mode screen to a particular computer"""
def suppress_client_connect_dialog(on_off_flag: int) -> None:
    """turns on (or off) the client connect dialog on the server (arg is 1 or 0)"""
def transparent_options_button(clientID: int, on_off_flag: int) -> None:
    """for a specific client (0=server machine), turns on (or off) the Options button transparency (arg is 1 or 0)"""
class SHPSYS(object): ### from pybind
    """One of four ship systems to track damage
    
    Members:
    
      WEAPONS : the weapons index for *system_damage*
    
      ENGINES : the engines index for *system_damage*
    
      SENSORS : the sensors index for *system_damage*
    
      SHIELDS : the shields index for *system_damage*
    
      MAX : the total number of types of *system_damage*"""
    def __eq__(self: object, other: object) -> bool:
        ...
    def __getstate__(self: object) -> int:
        ...
    def __hash__(self: object) -> int:
        ...
    def __index__(self: sbs.SHPSYS) -> int:
        ...
    def __init__(self: sbs.SHPSYS, value: int) -> None:
        ...
    def __int__(self: sbs.SHPSYS) -> int:
        ...
    def __ne__(self: object, other: object) -> bool:
        ...
    def __repr__(self: object) -> str:
        ...
    def __setstate__(self: sbs.SHPSYS, state: int) -> None:
        ...
    def __str__(*argv):
        """name(self: handle) -> str"""
    @property
    def name name(self: handle) -> str:
        """name(self: handle) -> str"""
    @property
    def value (arg0: sbs.SHPSYS) -> int:
        ...
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
    def extra_extra_tag (self: sbs.event) -> str:
        """string, even more-more information"""
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
    def layer (self: sbs.grid_object) -> int:
        """int, layers to help draw different grid-objects correctly.  (recommend 0-8, with 0 being lowest)"""
    @layer.setter
    def layer (self: sbs.grid_object, arg0: int) -> None:
        """int, layers to help draw different grid-objects correctly.  (recommend 0-8, with 0 being lowest)"""
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
    def create_grid_object(self: sbs.hullmap, name: str, tag: str, type: str) -> sbs.grid_object:
        """returns a gridobject, after creating it"""
    @property
    def desc (self: sbs.hullmap) -> str:
        """string, description text"""
    @desc.setter
    def desc (self: sbs.hullmap, arg0: str) -> None:
        """string, description text"""
    def get_grid_object_by_id(self: sbs.hullmap, id: int) -> sbs.grid_object:
        """returns a gridobject, by uint64 ID"""
    def get_grid_object_by_index(self: sbs.hullmap, index: int) -> sbs.grid_object:
        """returns a gridobject, by position in the list"""
    def get_grid_object_by_name(self: sbs.hullmap, name: str) -> sbs.grid_object:
        """returns a gridobject, by name"""
    def get_grid_object_by_tag(self: sbs.hullmap, tag: str) -> sbs.grid_object:
        """returns a gridobject, by text tag"""
    def get_grid_object_count(self: sbs.hullmap) -> int:
        """get the number of grid objects in the list, within this hullmap"""
    def get_objects_at_point(self: sbs.hullmap, x: int, y: int) -> List[int]:
        """returns a list of grid object IDs that are currently at the x/y point."""
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
    def has_changed_flag (self: sbs.navpoint) -> int:
        """int, if you change this navpoint, also set this flag to !0, so the server sends it down to the clients"""
    @has_changed_flag.setter
    def has_changed_flag (self: sbs.navpoint, arg0: int) -> None:
        """int, if you change this navpoint, also set this flag to !0, so the server sends it down to the clients"""
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
    @property
    def visibleToShip (self: sbs.navpoint) -> int:
        """uint64, id of the only space object that can see this navpoint (0 = all)"""
    @visibleToShip.setter
    def visibleToShip (self: sbs.navpoint, arg0: int) -> None:
        """uint64, id of the only space object that can see this navpoint (0 = all)"""
    @property
    def visibleToSide (self: sbs.navpoint) -> str:
        """string, text side name of side that can see this navpoint"""
    @visibleToSide.setter
    def visibleToSide (self: sbs.navpoint, arg0: str) -> None:
        """string, text side name of side that can see this navpoint"""
class navproxy(object): ### from pybind
    """class navproxy"""
    def SetColor(self: sbs.navproxy, arg0: str) -> None:
        """use a string color description to set the color"""
    @property
    def color (self: sbs.navproxy) -> sbs.vec4:
        """vec4, color on 2d radar"""
    @color.setter
    def color (self: sbs.navproxy, arg0: sbs.vec4) -> None:
        """vec4, color on 2d radar"""
    @property
    def has_changed_flag (self: sbs.navproxy) -> int:
        """int, if you change this navpoint, also set this flag to !0, so the server sends it down to the clients"""
    @has_changed_flag.setter
    def has_changed_flag (self: sbs.navproxy, arg0: int) -> None:
        """int, if you change this navpoint, also set this flag to !0, so the server sends it down to the clients"""
    @property
    def pos (self: sbs.navproxy) -> sbs.vec3:
        """vec3, position in space"""
    @pos.setter
    def pos (self: sbs.navproxy, arg0: sbs.vec3) -> None:
        """vec3, position in space"""
    @property
    def proxy_id (self: sbs.navproxy) -> int:
        """int64, ID of associated space object"""
    @proxy_id.setter
    def proxy_id (self: sbs.navproxy, arg0: int) -> None:
        """int64, ID of associated space object"""
    @property
    def shiptype (self: sbs.navproxy) -> str:
        """string, hull key from shipdata.yaml"""
    @shiptype.setter
    def shiptype (self: sbs.navproxy, arg0: str) -> None:
        """string, hull key from shipdata.yaml"""
    @property
    def text (self: sbs.navproxy) -> str:
        """string, text label"""
    @text.setter
    def text (self: sbs.navproxy, arg0: str) -> None:
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
    def add_navarea(self: sbs.simulation, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, x4: float, y4: float, text: str, colDesc: str) -> int:
        """adds a new navarea to space; don't hold on to this Navpoint object in a global; keep the integer ID return value instead    args:  four x/y floats, std::string text, std::string colorDesc"""
    def add_navpoint(self: sbs.simulation, x: float, y: float, z: float, text: str, colDesc: str) -> int:
        """adds a new navpoint to space; don't hold on to this Navpoint object in a global; keep the integer ID return value instead    args:  float x, float y, float z, std::string text, std::string colorDesc"""
    def add_navproxy(self: sbs.simulation, proxyID: int, name: str, shipType: str, colDesc: str) -> int:
        """adds a new navproxy to space; don't hold on to this NavProxy object in a global; keep the integer ID return value instead    args: in proxyID, string name, string shipType, string colorDesc"""
    def create_space_object(self: sbs.simulation, aiTag: str, dataTag: str, abits: int) -> int:
        """creates a new spaceobject. abits is a 16-bit bitfield for further defining the object.  bit 1, when set, means the object is unmoving and static."""
    def delete_navpoint_by_id(self: sbs.simulation, id: int) -> None:
        """deletes navpoint by its id"""
    def delete_navproxy_by_id(self: sbs.simulation, id: int) -> None:
        """deletes navproxy by its id"""
    def force_update_to_clients(self: sbs.simulation, spaceObjectID: int, playerShipID: int) -> None:
        """forces this space object to update its data to the clients attached to the playerShipID (all clients, if playerShipID is zero)"""
    def get_navpoint_by_id(self: sbs.simulation, id: int) -> sbs.navpoint:
        """takes an integer ID, returns the associated Navpoint object"""
    def get_navpoint_id_by_name(self: sbs.simulation, text: str) -> int:
        """returns a navpoint ID, given its name as the argument"""
    def get_navproxy_by_id(self: sbs.simulation, id: int) -> sbs.navproxy:
        """takes an integer ID, returns the associated NavProxy object"""
    def get_navproxy_by_proxy_id(self: sbs.simulation, id: int) -> sbs.navproxy:
        """takes a space object ID, returns the associated NavProxy object"""
    def get_navproxy_id_by_name(self: sbs.simulation, text: str) -> int:
        """returns a navproxy ID, given its name as the argument"""
    def get_shield_hit_index(self: sbs.simulation, sourceShip: sbs.space_object, targetShip: sbs.space_object) -> int:
        """Given a source ship and a target ship, this returns the shield (index) that would be hit by a hypothetical beam. -1 if the target ship has no shield facings."""
    def get_shield_hit_index_source(self: sbs.simulation, sourcePoint: sbs.vec3, targetShip: sbs.space_object) -> int:
        """Given a source position (vec3) and a target ship, this returns the shield (index) that would be hit by a hypothetical beam. -1 if the target ship has no shield facings."""
    def get_space_object(self: sbs.simulation, arg0: int) -> sbs.space_object:
        """returns the reference to a spaceobject, by ID"""
    def is_not_paused(self: sbs.simulation) -> bool:
        """returns True if the game is currently running."""
    def navpoint_exists(self: sbs.simulation, id: int) -> bool:
        """returns true if the navpoint exists, by integer id"""
    def navproxy_exists(self: sbs.simulation, id: int) -> bool:
        """returns true if the navproxy exists, by integer id"""
    def reposition_space_object(self: sbs.simulation, arg0: sbs.space_object, arg1: float, arg2: float, arg3: float) -> None:
        """immediately changes the position of a spaceobject"""
    def set_navproxy_pos(self: sbs.simulation, navproxy: sbs.navproxy, x: float, y: float, z: float) -> None:
        """takes a navproxy (the reference, not the ID), and sets the xyz values"""
    def space_object_exists(self: sbs.simulation, arg0: int) -> bool:
        """returns true if the spaceobject exists, by ID"""
    @property
    def time_tick_counter (self: sbs.simulation) -> int:
        """get current time value"""
class space_object(object): ### from pybind
    """class space_object"""
    @property
    def abits (self: sbs.space_object) -> int:
        """unsigned 16-bit bitfield for filtering.  bits 0-3 is reserved by c++. bit 0, if set, means that this object is unmoving and static (nebula, asteroid, black hole, etc)"""
    @abits.setter
    def abits (self: sbs.space_object, arg0: int) -> None:
        """unsigned 16-bit bitfield for filtering.  bits 0-3 is reserved by c++. bit 0, if set, means that this object is unmoving and static (nebula, asteroid, black hole, etc)"""
    @property
    def blink_state (self: sbs.space_object) -> int:
        """int, positive numbers are pulse delay, negative numbers are blink delay, 0 = normal, -1 = glow off"""
    @blink_state.setter
    def blink_state (self: sbs.space_object, arg0: int) -> None:
        """int, positive numbers are pulse delay, negative numbers are blink delay, 0 = normal, -1 = glow off"""
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
        """float, continuing change to heading and orientation of this object, over time"""
    @steer_pitch.setter
    def steer_pitch (self: sbs.space_object, arg0: float) -> None:
        """float, continuing change to heading and orientation of this object, over time"""
    @property
    def steer_roll (self: sbs.space_object) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
    @steer_roll.setter
    def steer_roll (self: sbs.space_object, arg0: float) -> None:
        """float, continuing change to heading and orientation of this object, over time"""
    @property
    def steer_yaw (self: sbs.space_object) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
    @steer_yaw.setter
    def steer_yaw (self: sbs.space_object, arg0: float) -> None:
        """float, continuing change to heading and orientation of this object, over time"""
    @property
    def tick_type (self: sbs.space_object) -> str:
        """string, name of behavior module
        current available behavior modules : nebula, npcship, asteroid, playership, station"""
    @property
    def tick_type_ID (self: sbs.space_object) -> int:
        """int32, read only, internal representation of tick_type"""
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
