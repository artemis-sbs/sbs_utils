from __future__ import annotations
from typing import List
from sbs_utils.vec import Vec3

import sys
sys.modules["sbs"] = sys.modules[__name__]


sim = None
seconds = 0


def add_client_tag() -> None:
    """stub; does nothing yet."""

def add_particle_emittor(spaceObject: space_object, lifeSpan: int, descriptorString: str) -> int:
    """creates a complex particle emittor and attaches it to a space object."""
    return 0

def app_milliseconds() -> int:
    global seconds
    return seconds * 1000

def app_minutes() -> int:
    global seconds
    return seconds / 60

def app_seconds() -> int:
    global seconds, sim
    seconds += 1
    if sim is not None:
        sim._time_tick_counter += 1
    return seconds


def assign_client_to_alt_ship(clientComputerID: int, controlledShipID: int) -> None:
    """Tells a client computer that the 2d radar should focus on controlledShipID, instead of its assigned ship.  Turn this code off by providing zero as the second argument."""
    global sim
    if sim is not None:
        if controlledShipID == 0:
            sim.client_alt_ships.pop(clientComputerID, None)
        else:
            sim.client_alt_ships[clientComputerID] = controlledShipID

def assign_client_to_ship(clientComputerID: int, controlledShipID: int) -> None:
    """Tells a client computer which ship it should control."""
    global sim
    if sim is not None:
        if controlledShipID == 0:
            sim.client_ships.pop(clientComputerID, None)
        else:
            sim.client_ships[clientComputerID] = controlledShipID

def broad_test(x1: float, z1: float, x2: float, z2: float, tick_type: int) -> List[space_object]:
    """return a list of space objects that are currently inside an x/z 2d rect  ARGS: 2D bounding rect, and bitfield"""
    global sim
    ret = []
    if x1 > x2:
        x1, x2 = x2, x1
    if z1 > z2:
        z1, z2 = z2, z1
    if sim is not None:
        for v in sim.space_objects.values():
            is_valid_bits = v._abits & tick_type
            if tick_type != -1 and not is_valid_bits:
                continue
            pos = v.pos
            if pos.x >= x1 and pos.x < x2 and pos.z >= z1 and pos.z <= z2:
                ret.append(v)
    return ret


def clear_client_tags() -> None:
    """stub; does nothing yet."""

def create_new_sim() -> None:
    """all space objects are deleted; a blank slate is born."""
    global sim
    sim = simulation()
    return sim


def delete_all_navpoints() -> None:
    """deletes all navpoints on server, and notifies all clients of the change"""
    global sim
    if sim is not None:
        sim.nav_points = {}
        sim.nav_points_by_id = {}

def delete_all_navproxies() -> None:
    """deletes all navproxies on server, and notifies all clients of the change"""
    global sim
    if sim is not None:
        sim.navproxies = {}

def delete_grid_object(spaceObjectID: int, gridObjID: int) -> None:
    """deletes the grid object, and sends the deletion message to all clients"""
    global sim
    if sim is not None:
        sim.grid_objects.pop(gridObjID, None)

def delete_object(ID: int) -> None:
    """deletes a space object by its ID"""
    global sim
    if sim is not None:
        sim.space_objects.pop(ID, None)

def delete_particle_emittor(emittorID: int) -> None:
    """deletes a particle emittor by ID."""

def distance(arg0: space_object, arg1: space_object) -> float:
    """returns the distance between two space objects; arguments are two spaceObjects"""
    if arg0 is None or arg1 is None:
        return 100000000000000.0
    one = Vec3(arg0.pos.x, arg0.pos.y, arg0.pos.z)
    two = Vec3(arg1.pos.x, arg1.pos.y, arg1.pos.z)
    return (two - one).length()

def distance_between_navpoints(arg0: int, arg1: int) -> float:
    """returns the distance between two nav points; navpoints by ID"""
    global sim
    if sim is not None:
        n1 = sim.nav_points_by_id.get(arg0)
        n2 = sim.nav_points_by_id.get(arg1)
        if n1 is not None and n2 is not None:
            p1 = Vec3(n1._pos.x, n1._pos.y, n1._pos.z)
            p2 = Vec3(n2._pos.x, n2._pos.y, n2._pos.z)
            return (p2 - p1).length()
    return 1000.0

def distance_id(arg0: int, arg1: int) -> float:
    """returns the distance between two space objects; arguments are two IDs"""
    global sim
    one = sim.space_objects.get(arg0)
    two = sim.space_objects.get(arg1)
    return distance(one, two)

def distance_point_line(arg0: vec3, arg1: vec3, arg2: vec3) -> tuple:
    """calculates the distance from a point to a line. Returns (dist along line, dist from start, tangent)."""
    return (0.0, 0.0, 0.0)

def distance_to_navpoint(arg0: int, arg1: int) -> float:
    """returns the distance between a nav point and a space object; navpoint ID, then object ID"""
    global sim
    if sim is not None:
        nav = sim.nav_points_by_id.get(arg0)
        obj = sim.space_objects.get(arg1)
        if nav is not None and obj is not None:
            p1 = Vec3(nav._pos.x, nav._pos.y, nav._pos.z)
            p2 = Vec3(obj._pos.x, obj._pos.y, obj._pos.z)
            return (p2 - p1).length()
    return 1000.0

def find_valid_grid_point_for_vector3(spaceObjectID: int, vecPoint: vec3, randomRadius: int) -> List[int]:
    """return a list of two integers, the grid x and y that is open and is closest.  The list is empty if the search fails."""
    return [0, 0]

def find_valid_unoccupied_grid_point_for_vector3(spaceObjectID: int, vecPoint: vec3, randomRadius: int) -> List[int]:
    """return a list of two integers, the grid x and y that is open and is closest.  The list is empty if the search fails."""
    return [0, 0]

def get_client_ID_list() -> List[int]:
    """return a list of client ids, for the computers that are currently connected to this server."""
    global sim
    if sim is not None:
        ids = set(sim._connected_client_ids) | set(sim.client_ships.keys())
        return list(ids)
    return []

def register_client(client_id: int) -> None:
    """Mark a WebSocket client as connected so it appears in get_client_ID_list()."""
    global sim
    if sim is not None:
        sim._connected_client_ids.add(client_id)

def unregister_client(client_id: int) -> None:
    """Remove a WebSocket client from the connected list."""
    global sim
    if sim is not None:
        sim._connected_client_ids.discard(client_id)

def get_debug_gui_tree(clientID: int, tag: str, displayListFlag: int) -> None:
    """sends a GUI debug message from the targeted client (0 = server screen)"""

def get_game_version() -> str:
    """returns the version of the game EXE currently operating this script, as a string."""
    return ""

hull_map_objects = {}
def get_hull_map(spaceObjectID: int, forceCreate: bool = False) -> hullmap:
    """gets the hull map object for this space object; setting forceCreate to True will erase and rebuild the grid (and gridObjects) of this spaceobject"""
    hull_map = hull_map_objects.get(spaceObjectID)
    if not hull_map or forceCreate:
        hull_map = hullmap()
        hull_map_objects[spaceObjectID] = hull_map
    return hull_map

def get_preference_float(key: str) -> float:
    """Gets a value from preferences.json"""
    return 0.0

def get_preference_int(key: str) -> int:
    """Gets a value from preferences.json"""
    return 0

def get_preference_string(key: str) -> str:
    """Gets a value from preferences.json"""
    return ""

def get_screen_size() -> vec2:
    """returns a VEC2, with the width and height of the display in pixels"""
    return vec2(1024, 768)

def get_shared_string(key: str) -> str:
    """gets a shared string, given the key (itself a string).  Shared strings are automatically copied from server to all clients."""
    return ""

def get_ship_of_client(clientID: int) -> int:
    """returns the player ship ID assigned to the client computer"""
    global sim
    if sim is not None:
        return sim.client_ships.get(clientID, 0)
    return 0

def get_text_block_height(fontTag: str, textToMeasure: str, width: int) -> int:
    """for a font key, a string of (possibly) multiline text, and a pixel width, this returns the height of the drawn text."""
    return 10

def get_text_line_height(fontTag: str, textToMeasure: str) -> int:
    """for a font key and a text string (one line, no wrapping), this returns the height of the drawn text."""
    return 10

def get_text_line_width(fontTag: str, textToMeasure: str) -> int:
    """for a font key and a text string (one line, no wrapping), this returns the width of the drawn text."""
    return 10

def get_type_of_client(clientID: int) -> str:
    """returns the consoleType previously assigned to the client computer"""
    global sim
    if sim is not None:
        return sim.client_types.get(clientID, "mainscreen")
    return "mainscreen"

def hide_gui_tag(clientID: int, tag: str) -> None:
    """makes a GUI element invisible, on the targeted client (0 = server screen)"""

def in_standby_list(space_object: space_object) -> bool:
    """returns true if the spaceobject is in the standby list."""
    return in_standby_list_id(space_object.unique_ID)

def in_standby_list_id(id: int) -> bool:
    """returns true if the spaceobject is in the standby list."""
    global sim
    if sim is not None:
        return id in sim.standby_list
    return False

def is_demo() -> bool:
    """Returns true if the EXE is marked as a demo version."""
    return False

def particle_at(position: vec3, descriptorString: str) -> None:
    """emit some particles in space."""

def particle_emittor_exists(emittorID: int) -> bool:
    """checks for the existence of a particle emittor."""
    return False

def particle_on(spaceObject: space_object, descriptorString: str) -> None:
    """emit some particles in space from a space object."""

def pause_sim() -> None:
    """the sim will now pause; HandlePresentGUI() and HandlePresentGUIMessage() are called."""
    global sim
    if sim is not None:
        sim._paused = True

def play_audio_file(clientID: int, filename: str, volume: float, pitch: float) -> None:
    """Plays a WAV audio file now, for just the specified client, OR zero for server."""

def play_music_file(ID: int, filename: str) -> None:
    """Plays a music file now; ID is ship, OR client, OR zero for server."""

def player_ship_setup_defaults(space_object: space_object) -> None:
    """Rebuilds the default blob data of this player ship."""

def player_ship_setup_from_data(space_object: space_object) -> None:
    """Rebuilds the blob data of this player ship from the shipdata.json and the preferences.json."""

def push_to_standby_list(space_object: space_object) -> None:
    """moves the spaceobject from normal space to the standby list."""
    push_to_standby_list_id(space_object.unique_ID)

def push_to_standby_list_id(id: int) -> None:
    """moves the spaceobject from normal space to the standby list."""
    global sim
    if sim is not None:
        obj = sim.space_objects.pop(id, None)
        if obj is not None:
            sim.standby_list[id] = obj

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
    global sim
    if sim is not None:
        sim._paused = False

def retrieve_from_standby_list(space_object: space_object) -> None:
    """moves the spaceobject from the standby list to normal space."""
    retrieve_from_standby_list_id(space_object.unique_ID)

def retrieve_from_standby_list_id(id: int) -> None:
    """moves the spaceobject from the standby list to normal space."""
    global sim
    if sim is not None:
        obj = sim.standby_list.pop(id, None)
        if obj is not None:
            sim.space_objects[id] = obj

def run_next_mission(mission_folder: str) -> None:
    """Shuts down this script and starts the mission in the folder argument"""

def send_client_widget_list(clientID: int, consoleType: str, widgetList: str) -> None:
    """sends the gameplay widgets to draw, on the targeted client (0 = server screen)"""
    global sim
    if sim is not None and consoleType:
        sim.client_types[clientID] = consoleType

def send_client_widget_rects(arg0: int, arg1: str, arg2: float, arg3: float, arg4: float, arg5: float, arg6: float, arg7: float, arg8: float, arg9: float) -> None:
    """changes the rects of a gameplay widget, on the targeted client (0 = server screen)."""

def send_comms_button_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship."""

def send_comms_message_to_player_ship(playerID: int, otherID: int, faceDesc: str, titleText: str, titleColor: str, bodyText: str, bodyColor: str) -> None:
    """sends a complex message to the comms console of a certain ship."""

def send_comms_selection_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the comms console of a certain ship."""

def send_grid_button_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the engineering console of a certain ship."""

def send_grid_selection_info(arg0: int, arg1: str, arg2: str, arg3: str) -> None:
    """sends a complex message to the engineering console of a certain ship."""

def send_gui_3dship(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a 3D ship box GUI element, on the targeted client (0 = server screen)"""

def send_gui_button(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a button GUI element, on the targeted client (0 = server screen)"""

def send_gui_checkbox(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a checkbox GUI element, on the targeted client (0 = server screen)"""

def send_gui_clear(clientID: int, tag: str) -> None:
    """Clears all GUI elements from screen, on the targeted client (0 = server screen)."""

def send_gui_clickregion(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a click-region GUI element, on the targeted client (0 = server screen)"""

def send_gui_colorbutton(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a color button GUI element, on the targeted client (0 = server screen)"""

def send_gui_colorcheckbox(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a color checkbox GUI element, on the targeted client (0 = server screen)"""

def send_gui_complete(clientID: int, tag: str) -> None:
    """Flips double-buffered GUI display list, on the targeted client (0 = server screen)."""

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
    """Creates a slider bar GUI element, on the targeted client (0 = server screen)"""

def send_gui_sub_region(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a subregion GUI element, on the targeted client (0 = server screen)"""

def send_gui_text(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a text box GUI element, on the targeted client (0 = server screen)"""

def send_gui_typein(clientID: int, parent: str, tag: str, style: str, left: float, top: float, right: float, bottom: float) -> None:
    """Creates a text entry GUI element, on the targeted client (0 = server screen)"""

def send_hold_menu(clientID: int, subject: int, object: int, extra: int, menuOptionStringSet: str) -> None:
    """sends info to client that displays a quick menu list on the 2d radar."""

def send_message_to_client(clientID: int, colorDesc: str, text: str) -> None:
    """sends a text message to the text box, for the specific client."""

def send_message_to_player_ship(playerID: int, colorDesc: str, text: str) -> None:
    """sends a text message to the text box, on every client for a certain ship."""

def send_speech_bubble_to_object(clientComputerID: int, spaceObjectID: int, seconds: int, color: str, text: str) -> None:
    """attaches a speech bubble to a space object on the 2d radar."""

def send_story_dialog(clientID: int, title: str, text: str, face: str, color: str) -> None:
    """sends a story dialog to the targeted client (0 = server screen)"""

def set_beam_damages(clientID: int, playerBeamDamage: float, npcBeamDamage: float, stationBeamDamage: float = 1) -> None:
    """sets the values for player base beam damage, npc base beam damage, and station base beam damage."""

def set_client_string(clientComputerID: int, string_key: str, string_value: str) -> None:
    """stores a string value (and its string key) to the client computer"""

def set_dmx_channel(clientID: int, channel: int, behavior: int, speed: int, low: int, high: int) -> None:
    """set a color channel of dmx."""

def set_main_view_modes(clientID: int, main_screen_view: str, cam_angle: str, cam_mode: str) -> None:
    """sets the three modes of the main screen view for the specified client."""

def set_music_folder(ID: int, filename: str) -> None:
    """Sets the folder from which music is streamed; ID is ship, OR client, OR zero for server."""

def set_music_tension(ID: int, tensionValue: float) -> None:
    """Sets the tension value of ambient music (0-100); ID is ship, OR client, OR zero for server."""

def set_shared_string(key: str, value: str) -> None:
    """sets (or changes) a shared string, given a key and a value (both strings)."""

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


from enum import IntEnum

class DIPLOMACY(IntEnum): ### from pybind
    """the different attitudes that sides have for each other"""
    UNKNOWN = 0
    NEUTRAL = 1
    ALLIED = 2
    HOSTILE = 3
    MAX = 4

class SHPSYS(IntEnum): ### from pybind
    """One of four ship systems to track damage"""
    WEAPONS = 0
    ENGINES = 1
    SENSORS = 2
    SHIELDS = 3
    MAX = 4

class Writer(object): ### from pybind
    """class Writer"""
    def flush(self: Writer) -> None:
        ...
    def write(self: Writer, arg0: str) -> None:
        ...

class event(object): ### from pybind
    """class event"""
    @property
    def client_id(self: event) -> int:
        """id of computer this event came from."""
    @property
    def event_time(self: event) -> int:
        """long int, time this damage occured, compare to simulation.time_tick_counter"""
    @property
    def extra_extra_tag(self: event) -> str:
        """string, even more-more information"""
    @property
    def extra_tag(self: event) -> str:
        """string, even more information"""
    @property
    def origin_id(self: event) -> int:
        """id of space object this event came from"""
    @property
    def parent_id(self: event) -> int:
        """id of owner/creator of space object this event came from (like the ship that fired the missile)"""
    @property
    def selected_id(self: event) -> int:
        """id of space object this event is talking about, or doing something to"""
    @property
    def source_point(self: event) -> vec3:
        """vec3, 3d point this event originated from"""
    @property
    def sub_float(self: event) -> float:
        """float, numeric information"""
    @property
    def sub_tag(self: event) -> str:
        """string describing message sub-type"""
    @property
    def tag(self: event) -> str:
        """string describing message type"""
    @property
    def value_tag(self: event) -> str:
        """string, more information"""

_grid_object_ids = 0x2000000000000000

class grid_object(object): ### from pybind
    """class grid_object"""
    def __init__(self) -> None:
        global _grid_object_ids
        self._data_set = object_data_set()
        self._name = ""
        self._tag = ""
        self._type = ""
        self._layer = 0
        self._id = _grid_object_ids
        _grid_object_ids += 1

    @property
    def data_set(self: grid_object) -> object_data_set:
        return self._data_set

    @property
    def layer(self: grid_object) -> int:
        """int, layers to help draw different grid-objects correctly.  (recommend 0-8, with 0 being lowest)"""
        return self._layer

    @layer.setter
    def layer(self: grid_object, arg0: int) -> None:
        self._layer = arg0

    @property
    def name(self: grid_object) -> str:
        """string, text name"""
        return self._name

    @name.setter
    def name(self: grid_object, arg0: str) -> None:
        self._name = arg0

    @property
    def tag(self: grid_object) -> str:
        """string, text tag"""
        return self._tag

    @tag.setter
    def tag(self: grid_object, arg0: str) -> None:
        self._tag = arg0

    @property
    def type(self: grid_object) -> str:
        """string, text value, broad type of object"""
        return self._type

    @type.setter
    def type(self: grid_object, arg0: str) -> None:
        self._type = arg0

    @property
    def unique_ID(self: grid_object) -> int:
        """uint64, read only, id of this particular grid object"""
        return self._id


class hullmap(object): ### from pybind
    """class hullmap"""
    def __init__(self) -> None:
        self._art_file_root = ""
        self._desc = ""
        self._name = ""
        self.grid_items = []
        self._grid_scale = 1.0
        self._h = 0
        self._w = 0
        self._sym = 0

    @property
    def art_file_root(self: hullmap) -> str:
        """string, file name, used to get top-down image from disk"""
        return self._art_file_root

    @art_file_root.setter
    def art_file_root(self: hullmap, arg0: str) -> None:
        self._art_file_root = arg0

    def create_grid_object(self: hullmap, name: str, tag: str, type: str) -> grid_object:
        """returns a gridobject, after creating it"""
        go = grid_object()
        go._name = name
        go._tag = tag
        go._type = type
        sim.grid_object_ids += 1
        go._id = sim.grid_object_ids
        sim.grid_objects[go._id] = go
        self.grid_items.append(go)
        return go

    def delete_grid_object(self: hullmap, arg0: grid_object) -> bool:
        """deletes the grid object, returns true if deletion actually occurred"""
        go = sim.grid_objects.pop(arg0._id, None)
        if go is not None:
            self.grid_items.remove(arg0)
            return True
        return False

    @property
    def desc(self: hullmap) -> str:
        """string, description text"""
        return self._desc

    @desc.setter
    def desc(self: hullmap, arg0: str) -> None:
        self._desc = arg0

    def get_grid_object_by_id(self: hullmap, id: int) -> grid_object:
        """returns a gridobject, by uint64 ID"""
        return sim.grid_objects.get(id)

    def get_grid_object_by_index(self: hullmap, index: int) -> grid_object:
        """returns a gridobject, by position in the list"""
        return self.grid_items[index]

    def get_grid_object_by_name(self: hullmap, name: str) -> grid_object:
        """returns a gridobject, by name"""
        for go in self.grid_items:
            if go._name == name:
                return go
        return None

    def get_grid_object_by_tag(self: hullmap, tag: str) -> grid_object:
        """returns a gridobject, by text tag"""
        for go in self.grid_items:
            if go._tag == tag:
                return go
        return None

    def get_grid_object_count(self: hullmap) -> int:
        """get the number of grid objects in the list, within this hullmap"""
        return len(self.grid_items)

    def get_objects_at_point(self: hullmap, x: int, y: int) -> List[int]:
        """returns a list of grid object IDs that are currently at the x/y point."""
        return []

    @property
    def grid_scale(self: hullmap) -> float:
        """float, space between grid points"""
        return self._grid_scale

    @grid_scale.setter
    def grid_scale(self: hullmap, arg0: float) -> None:
        self._grid_scale = arg0

    @property
    def h(self: hullmap) -> int:
        """int, total grid height"""
        return self._h

    @h.setter
    def h(self: hullmap, arg0: int) -> None:
        self._h = arg0

    def is_grid_point_open(self: hullmap, arg0: int, arg1: int) -> int:
        """is the x/y point within this hullmap open (traversable)? 0 == no"""
        return 1

    @property
    def name(self: hullmap) -> str:
        """string, text name"""
        return self._name

    @name.setter
    def name(self: hullmap, arg0: str) -> None:
        self._name = arg0

    @property
    def symmetrical_flag(self: hullmap) -> int:
        """int, non-zero if the map is symmetrical"""
        return self._sym

    @symmetrical_flag.setter
    def symmetrical_flag(self: hullmap, arg0: int) -> None:
        self._sym = arg0

    @property
    def w(self: hullmap) -> int:
        """int, total grid width"""
        return self._w

    @w.setter
    def w(self: hullmap, arg0: int) -> None:
        self._w = arg0


class navpoint(object): ### from pybind
    """class navpoint"""
    def __init__(self) -> None:
        self._text = ""
        self._color = vec4()
        self._pos = vec3(0, 0, 0)
        self._has_changed_flag = 0
        self._visible_to_ship = 0
        self._visible_to_side = ""

    def SetColor(self: navpoint, arg0: str) -> None:
        """use a string color description to set the color"""
        self._color = vec4()

    @property
    def color(self: navpoint) -> vec4:
        """vec4, color on 2d radar"""
        return self._color

    @color.setter
    def color(self: navpoint, arg0: vec4) -> None:
        self._color = arg0

    @property
    def has_changed_flag(self: navpoint) -> int:
        """int, if you change this navpoint, also set this flag to !0, so the server sends it down to the clients"""
        return self._has_changed_flag

    @has_changed_flag.setter
    def has_changed_flag(self: navpoint, arg0: int) -> None:
        self._has_changed_flag = arg0

    @property
    def pos(self: navpoint) -> vec3:
        """vec3, position in space"""
        return self._pos

    @pos.setter
    def pos(self: navpoint, arg0: vec3) -> None:
        self._pos = arg0

    @property
    def text(self: navpoint) -> str:
        """string, text label"""
        return self._text

    @text.setter
    def text(self: navpoint, arg0: str) -> None:
        sim.nav_points.pop(self._text, None)
        self._text = arg0
        sim.nav_points[arg0] = self

    @property
    def visibleToShip(self: navpoint) -> int:
        """uint64, id of the only space object that can see this navpoint (0 = all)"""
        return self._visible_to_ship

    @visibleToShip.setter
    def visibleToShip(self: navpoint, arg0: int) -> None:
        self._visible_to_ship = arg0

    @property
    def visibleToSide(self: navpoint) -> str:
        """string, text side name of side that can see this navpoint"""
        return self._visible_to_side

    @visibleToSide.setter
    def visibleToSide(self: navpoint, arg0: str) -> None:
        self._visible_to_side = arg0


class navproxy(object): ### from pybind
    """class navproxy"""
    def __init__(self) -> None:
        self._color = vec4()
        self._has_changed_flag = 0
        self._pos = vec3(0, 0, 0)
        self._proxy_id = 0
        self._shiptype = "tsn_light_cruiser"
        self._text = ""

    def SetColor(self: navproxy, arg0: str) -> None:
        """use a string color description to set the color"""

    @property
    def color(self: navproxy) -> vec4:
        """vec4, color on 2d radar"""
        return self._color

    @color.setter
    def color(self: navproxy, arg0: vec4) -> None:
        self._color = arg0

    @property
    def has_changed_flag(self: navproxy) -> int:
        """int, if you change this navpoint, also set this flag to !0, so the server sends it down to the clients"""
        return self._has_changed_flag

    @has_changed_flag.setter
    def has_changed_flag(self: navproxy, arg0: int) -> None:
        self._has_changed_flag = arg0

    @property
    def pos(self: navproxy) -> vec3:
        """vec3, position in space"""
        return self._pos

    @pos.setter
    def pos(self: navproxy, arg0: vec3) -> None:
        self._pos = arg0

    @property
    def proxy_id(self: navproxy) -> int:
        """int64, ID of associated space object"""
        return self._proxy_id

    @proxy_id.setter
    def proxy_id(self: navproxy, arg0: int) -> None:
        self._proxy_id = arg0

    @property
    def shiptype(self: navproxy) -> str:
        """string, hull key from shipdata.yaml"""
        return self._shiptype

    @shiptype.setter
    def shiptype(self: navproxy, arg0: str) -> None:
        self._shiptype = arg0

    @property
    def text(self: navproxy) -> str:
        """string, text label"""
        return self._text

    @text.setter
    def text(self: navproxy, arg0: str) -> None:
        self._text = arg0


class object_data_set(object): ### from pybind
    """class object_data_set"""
    def __init__(self):
        self.values = {}

    def clear_data(self, name: str) -> None:
        """deletes all elements in this blob value"""
        self.values.pop(name, None)

    def get(self, name, index=0):
        values = self.values.get(name, {})
        value = values.get(index, None)
        if value is not None:
            return value
        s_value = [
            "torpedo_types_available", "tsnscan", "tsnintel", "tsnbio", "tsnstatus", "ally_list",
            "hull_origin", "hull_side"
        ]
        if name == "torpedo_types_available":
            return "Homing,Nuke,EMP,Mine"
        if name in s_value:
            return ""
        return None

    def get_first(self, name: str) -> object:
        """Get the first iterator value of the map in this element"""
        values = self.values.get(name, {})
        return next(iter(values.values()), None)

    def get_next(self, name: str) -> object:
        """Get the next iterator value of the map in this element; None means end of list"""
        return None

    def num_elements(self, name: str) -> int:
        """get the number of elements in this blob value"""
        return len(self.values.get(name, {}))

    def set(self, tag, value, index=0):
        values = self.values.get(tag, {})
        values[index] = value
        self.values[tag] = values


class quaternion(object): ### from pybind
    """class quaternion"""
    def __init__(self, w=0, x=None, y=None, z=None):
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
    def w(self: quaternion) -> float:
        """float, component value"""
        return self._w

    @w.setter
    def w(self: quaternion, arg0: float) -> None:
        self._w = arg0

    @property
    def x(self: quaternion) -> float:
        """float, component value"""
        return self._x

    @x.setter
    def x(self: quaternion, arg0: float) -> None:
        self._x = arg0

    @property
    def y(self: quaternion) -> float:
        """float, component value"""
        return self._y

    @y.setter
    def y(self: quaternion, arg0: float) -> None:
        self._y = arg0

    @property
    def z(self: quaternion) -> float:
        """float, component value"""
        return self._z

    @z.setter
    def z(self: quaternion, arg0: float) -> None:
        self._z = arg0


class simulation(object): ### from pybind
    """class simulation"""
    def __init__(self):
        global sim
        sim = self
        self.object_ids = 0x4000000000000000
        self.space_objects = {}
        self.standby_list = {}
        self.grid_object_ids = 0x2000000000000000
        self.grid_objects = {}
        self.nav_points = {}          # keyed by name (str)
        self.nav_points_by_id = {}    # keyed by int ID
        self.nav_point_counter = 0x1000000000000000
        self.navproxies = {}
        self.hull_map_objects = {}
        self._time_tick_counter = 0
        self.tractor_connections = {}
        self._paused = True           # sim starts paused, like the real engine
        self._connected_client_ids: set = set()  # registered via WebSocket (mockgui)
        self.client_ships = {}        # clientID -> shipID
        self.client_alt_ships = {}    # clientID -> altShipID (radar focus)
        self.client_types = {}        # clientID -> consoleType str
        self.side_relations = {}      # frozenset({s1,s2}) -> DIPLOMACY int

    def AddTractorConnection(self: simulation, arg0: int, arg1: int, arg2: vec3, arg3: float) -> tractor_connection:
        """makes a new connection between two space objects."""
        con = tractor_connection()
        con._source_id = arg0
        con._target_id = arg1
        con._pull = arg3
        con._vec = arg2
        self.tractor_connections[(con.source_id, con.target_id)] = con
        return con

    def ClearTractorConnections(self: simulation) -> None:
        """destroys all existing tractor connections right now."""
        self.tractor_connections = {}

    def DeleteTractorConnection(self: simulation, arg0: int, arg1: int) -> None:
        """finds and deletes an existing tractor connection."""
        self.tractor_connections.pop((arg0, arg1), None)

    def GetTractorConnection(self: simulation, arg0: int, arg1: int) -> tractor_connection:
        return self.tractor_connections.get((arg0, arg1))

    def add_navarea(self: simulation, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, x4: float, y4: float, text: str, colDesc: str) -> int:
        """adds a new navarea to space"""
        return 0

    def add_navpoint(self: simulation, x: float, y: float, z: float, text: str, colDesc: str) -> int:
        """adds a new navpoint to space; returns integer ID"""
        self.nav_point_counter += 1
        nav = navpoint()
        nav._color = colDesc
        nav._pos = vec3(x, y, z)
        nav._text = text
        self.nav_points[text] = nav
        self.nav_points_by_id[self.nav_point_counter] = nav
        return self.nav_point_counter

    def add_navproxy(self: simulation, proxyID: int, name: str, shipType: str, colDesc: str) -> int:
        """adds a new navproxy to space; returns integer ID"""
        return 0

    def create_space_object(self: simulation, aiTag: str, dataTag: str, abits: int) -> int:
        """creates a new spaceobject. abits is a 16-bit bitfield for further defining the object."""
        self.object_ids += 1
        id = self.object_ids
        obj = space_object()
        obj._id = id
        obj._abits = abits
        obj._data_tag = dataTag
        obj._tick_type = aiTag
        self.space_objects[id] = obj
        return id

    def delete_navpoint_by_id(self: simulation, id: int) -> None:
        """deletes navpoint by its id"""
        nav = self.nav_points_by_id.pop(id, None)
        if nav:
            self.nav_points.pop(nav._text, None)

    def delete_navproxy_by_id(self: simulation, id: int) -> None:
        """deletes navproxy by its id"""
        self.navproxies.pop(id, None)

    def force_update_to_clients(self: simulation, spaceObjectID: int, playerShipID: int) -> None:
        """forces this space object to update its data to the clients"""

    def get_navpoint_by_id(self: simulation, id: int) -> navpoint:
        """takes an integer ID, returns the associated Navpoint object"""
        return self.nav_points_by_id.get(id)

    def get_navpoint_id_by_name(self: simulation, text: str) -> int:
        """returns a navpoint ID, given its name as the argument"""
        nav = self.nav_points.get(text)
        if nav:
            for id, n in self.nav_points_by_id.items():
                if n is nav:
                    return id
        return 0

    def get_navproxy_by_id(self: simulation, id: int) -> navproxy:
        """takes an integer ID, returns the associated NavProxy object"""
        return self.navproxies.get(id)

    def get_navproxy_by_proxy_id(self: simulation, id: int) -> navproxy:
        """takes a space object ID, returns the associated NavProxy object"""
        for np in self.navproxies.values():
            if np._proxy_id == id:
                return np
        return None

    def get_navproxy_id_by_name(self: simulation, text: str) -> int:
        """returns a navproxy ID, given its name as the argument"""
        return 0

    def get_shield_hit_index(self: simulation, sourceShip: space_object, targetShip: space_object) -> int:
        """returns the shield index that would be hit by a hypothetical beam. -1 if no shield facings."""
        return -1

    def get_shield_hit_index_source(self: simulation, sourcePoint: vec3, targetShip: space_object) -> int:
        """returns the shield index that would be hit by a hypothetical beam. -1 if no shield facings."""
        return -1

    def get_space_object(self: simulation, arg0: int) -> space_object:
        """returns the reference to a spaceobject, by ID"""
        return self.space_objects.get(arg0)

    def is_not_paused(self: simulation) -> bool:
        """returns True if the game is currently running."""
        return not self._paused

    def launch_torpedo(self: simulation, source_ship: space_object, tube_index: int, is_fighter_flag: bool) -> None:
        """launches a torpedo from the space object provided."""

    def navpoint_exists(self: simulation, id: int) -> bool:
        """returns true if the navpoint exists, by integer id"""
        return id in self.nav_points_by_id

    def navproxy_exists(self: simulation, id: int) -> bool:
        """returns true if the navproxy exists, by integer id"""
        return id in self.navproxies

    def reposition_space_object(self: simulation, arg0: space_object, arg1: float, arg2: float, arg3: float) -> None:
        """immediately changes the position of a spaceobject"""
        if arg0:
            arg0.pos.x = arg1
            arg0.pos.y = arg2
            arg0.pos.z = arg3

    def set_diplomacy_color(self: simulation, diplomacyEnumValue: int, colorString: str) -> None:
        """set the color of a diplomatic state (like DIPLOMACY::UNKNOWN or DIPLOMACY::ALLIED)"""

    def set_navproxy_pos(self: simulation, navproxy: navproxy, x: float, y: float, z: float) -> None:
        """takes a navproxy (the reference, not the ID), and sets the xyz values"""

    def set_side_icon_color(self: simulation, SideTag: str, colorString: str) -> None:
        """set the color of a SideTag (like TSN or Raider)"""

    def set_side_icon_index(self: simulation, SideTag: str, iconIndex: int) -> None:
        """set the value of the icon of a SideTag (like TSN or Raider)"""

    def set_side_relationship(self: simulation, FirstSideTag: str, SecondSideTag: str, diplomacyEnumValue: int) -> None:
        """set the diplomatic state between two sides, for GUI color purposes."""
        self.side_relations[frozenset({FirstSideTag, SecondSideTag})] = diplomacyEnumValue

    def get_side_relationship(self: simulation, FirstSideTag: str, SecondSideTag: str) -> int:
        """returns the diplomatic state between two sides (mock helper)"""
        return self.side_relations.get(frozenset({FirstSideTag, SecondSideTag}), int(DIPLOMACY.NEUTRAL))

    def space_object_exists(self: simulation, arg0: int) -> bool:
        """returns true if the spaceobject exists, by ID"""
        return arg0 in self.space_objects

    @property
    def time_tick_counter(self: simulation) -> int:
        """get current time value"""
        return self._time_tick_counter

    # --- mock-only navpoint helpers (not in engine API) ---

    def clear_navpoints(self: simulation) -> None:
        """deletes all navpoints (mock helper)"""
        self.nav_points = {}
        self.nav_points_by_id = {}

    def delete_navpoint_by_name(self: simulation, arg0: str) -> None:
        """deletes navpoint by its name (mock helper)"""
        nav = self.nav_points.pop(arg0, None)
        if nav:
            for id, n in list(self.nav_points_by_id.items()):
                if n is nav:
                    self.nav_points_by_id.pop(id)
                    break

    def delete_navpoint_by_reference(self: simulation, arg0: navpoint) -> None:
        """deletes navpoint by its reference (mock helper)"""
        self.delete_navpoint_by_name(arg0._text)

    def get_navpoint_by_name(self: simulation, arg0: str) -> navpoint:
        """takes a string name, returns the associated Navpoint object (mock helper)"""
        return self.nav_points.get(arg0, None)


class space_object(object): ### from pybind
    """class space_object"""
    def __init__(self):
        self.data_set_blob = object_data_set()
        self._side = ""
        self._cur_speed = 0.0
        self._data_tag = ""
        self._ship_data_key = ""
        self._tick_type = ""
        self._abits = 0
        self._id = 0
        self._exclusion_radius = 0.0
        self._fat_radius = 0.0
        self._steer_pitch = 0.0
        self._steer_roll = 0.0
        self._steer_yaw = 0.0
        self._pos = vec3(0, 0, 0)
        self._blink_state = 0
        self._rot_quat = quaternion(0, 0, 0, 0)

    @property
    def abits(self: space_object) -> int:
        """unsigned 16-bit bitfield for filtering.  bits 0-3 is reserved by c++."""
        return self._abits

    @abits.setter
    def abits(self: space_object, arg0: int) -> None:
        self._abits = arg0

    @property
    def blink_state(self: space_object) -> int:
        """int, positive numbers are pulse delay, negative numbers are blink delay, 0 = normal, -1 = glow off"""
        return self._blink_state

    @blink_state.setter
    def blink_state(self: space_object, arg0: int) -> None:
        self._blink_state = arg0

    @property
    def cur_speed(self: space_object) -> float:
        """float, speed of object"""
        return self._cur_speed

    @cur_speed.setter
    def cur_speed(self: space_object, arg0: float) -> None:
        self._cur_speed = arg0

    @property
    def data_set(self: space_object) -> object_data_set:
        """object_data_set, read only, reference to the object_data_set of this particular object"""
        return self.data_set_blob

    @property
    def data_tag(self: space_object) -> str:
        """string, name of data entry in shipData.json"""
        return self._data_tag

    @data_tag.setter
    def data_tag(self: space_object, arg0: str) -> None:
        self._data_tag = arg0

    @property
    def exclusion_radius(self: space_object) -> float:
        """float, other objects cannot be closer to me than this distance"""
        return self._exclusion_radius

    @exclusion_radius.setter
    def exclusion_radius(self: space_object, arg0: float) -> None:
        self._exclusion_radius = arg0

    @property
    def fat_radius(self: space_object) -> float:
        """float, radius of box for internal sorting calculations"""
        return self._fat_radius

    @fat_radius.setter
    def fat_radius(self: space_object, arg0: float) -> None:
        self._fat_radius = arg0

    def forward_vector(self: space_object) -> vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
        return vec3(0, 0, 1)

    @property
    def pos(self: space_object) -> vec3:
        """vec3, position in space"""
        return self._pos

    @pos.setter
    def pos(self: space_object, arg0: vec3) -> None:
        self._pos = arg0

    def right_vector(self: space_object) -> vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
        return vec3(1, 0, 0)

    @property
    def rot_quat(self: space_object) -> quaternion:
        """quaternion, heading and orientation of this object"""
        return self._rot_quat

    @rot_quat.setter
    def rot_quat(self: space_object, arg0: quaternion) -> None:
        self._rot_quat = arg0

    def set_behavior(self: space_object, arg0: str) -> None:
        """set name of behavior module"""
        self._tick_type = arg0

    @property
    def ship_data_key(self: space_object) -> str:
        """string, name of data entry in shipData.json"""
        return self._ship_data_key

    @ship_data_key.setter
    def ship_data_key(self: space_object, arg0: str) -> None:
        self._ship_data_key = arg0

    @property
    def side(self: space_object) -> str:
        """string, friendly to other objects on this same side; leave empty for 'no side'"""
        return self._side

    @side.setter
    def side(self: space_object, arg0: str) -> None:
        self._side = arg0

    @property
    def steer_pitch(self: space_object) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
        return self._steer_pitch

    @steer_pitch.setter
    def steer_pitch(self: space_object, arg0: float) -> None:
        self._steer_pitch = arg0

    @property
    def steer_roll(self: space_object) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
        return self._steer_roll

    @steer_roll.setter
    def steer_roll(self: space_object, arg0: float) -> None:
        self._steer_roll = arg0

    @property
    def steer_yaw(self: space_object) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
        return self._steer_yaw

    @steer_yaw.setter
    def steer_yaw(self: space_object, arg0: float) -> None:
        self._steer_yaw = arg0

    @property
    def tick_type(self: space_object) -> str:
        """string, name of behavior module"""
        return self._tick_type

    @property
    def tick_type_ID(self: space_object) -> int:
        """int32, read only, internal representation of tick_type"""
        return self._abits

    def up_vector(self: space_object) -> vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
        return vec3(0, 1, 0)

    @property
    def unique_ID(self: space_object) -> int:
        """uint64, read only, id of this particular object"""
        return self._id


class tractor_connection(object): ### from pybind
    """class tractor_connection"""
    def __init__(self) -> None:
        self._offset = 0.0
        self._source_id = 0
        self._target_id = 0
        self._vec = vec3(0, 0, 0)
        self._pull = 0.0

    @property
    def offset(self: tractor_connection) -> float:
        """float, how much the target is pulled towards the offset every tick. 0 = infinite pull, target locked to boss"""
        return self._offset

    @offset.setter
    def offset(self: tractor_connection, arg0: float) -> None:
        self._offset = arg0

    @property
    def source_id(self: tractor_connection) -> int:
        """int, ID of boss/master/major object"""
        return self._source_id

    @property
    def target_id(self: tractor_connection) -> int:
        """int, ID of object that is attached to the other"""
        return self._target_id


class vec2(object): ### from pybind
    """class vec2"""
    def __init__(self, x=None, y=None):
        if isinstance(x, vec2):
            self._x = x.x
            self._y = x.y
        elif x is None:
            self._x = 0.0
            self._y = 0.0
        else:
            self._x = float(x)
            self._y = float(y)

    def __add__(self, arg0: vec2) -> vec2:
        return vec2(self._x + arg0._x, self._y + arg0._y)

    def __iadd__(self, arg0: vec2) -> vec2:
        self._x += arg0._x
        self._y += arg0._y
        return self

    def __imul__(self, arg0: float) -> vec2:
        self._x *= arg0
        self._y *= arg0
        return self

    def __mul__(self, arg0: float) -> vec2:
        return vec2(self._x * arg0, self._y * arg0)

    def __neg__(self) -> vec2:
        return vec2(-self._x, -self._y)

    def __rmul__(self, arg0: float) -> vec2:
        return vec2(self._x * arg0, self._y * arg0)

    @property
    def x(self: vec2) -> float:
        """float, component value"""
        return self._x

    @x.setter
    def x(self: vec2, arg0: float) -> None:
        self._x = arg0

    @property
    def y(self: vec2) -> float:
        """float, component value"""
        return self._y

    @y.setter
    def y(self: vec2, arg0: float) -> None:
        self._y = arg0


class vec3(object): ### from pybind
    """class vec3"""
    def __init__(self, x=None, y=None, z=None):
        if isinstance(x, vec3):
            self._x = x._x
            self._y = x._y
            self._z = x._z
        elif x is None:
            self._x = 0.0
            self._y = 0.0
            self._z = 0.0
        else:
            self._x = float(x)
            self._y = float(y)
            self._z = float(z)

    def __add__(self, arg0: vec3) -> vec3:
        return vec3(self._x + arg0._x, self._y + arg0._y, self._z + arg0._z)

    def __iadd__(self, arg0: vec3) -> vec3:
        self._x += arg0._x
        self._y += arg0._y
        self._z += arg0._z
        return self

    def __imul__(self, arg0: float) -> vec3:
        self._x *= arg0
        self._y *= arg0
        self._z *= arg0
        return self

    def __mul__(self, arg0: float) -> vec3:
        return vec3(self._x * arg0, self._y * arg0, self._z * arg0)

    def __neg__(self) -> vec3:
        return vec3(-self._x, -self._y, -self._z)

    def __rmul__(self, arg0: float) -> vec3:
        return vec3(self._x * arg0, self._y * arg0, self._z * arg0)

    @property
    def x(self: vec3) -> float:
        """float, component value"""
        return self._x

    @x.setter
    def x(self: vec3, arg0: float) -> None:
        self._x = arg0

    @property
    def y(self: vec3) -> float:
        """float, component value"""
        return self._y

    @y.setter
    def y(self: vec3, arg0: float) -> None:
        self._y = arg0

    @property
    def z(self: vec3) -> float:
        """float, component value"""
        return self._z

    @z.setter
    def z(self: vec3, arg0: float) -> None:
        self._z = arg0


class vec4(object): ### from pybind
    """class vec4"""
    def __init__(self, r=None, g=None, b=None, a=None):
        if isinstance(r, vec4):
            self._r = r._r
            self._g = r._g
            self._b = r._b
            self._a = r._a
        elif r is None:
            self._r = 0.0
            self._g = 0.0
            self._b = 0.0
            self._a = 0.0
        else:
            self._r = float(r)
            self._g = float(g)
            self._b = float(b)
            self._a = float(a)

    def __add__(self, arg0: vec4) -> vec4:
        return vec4(self._r + arg0._r, self._g + arg0._g, self._b + arg0._b, self._a + arg0._a)

    def __iadd__(self, arg0: vec4) -> vec4:
        self._r += arg0._r
        self._g += arg0._g
        self._b += arg0._b
        self._a += arg0._a
        return self

    def __imul__(self, arg0: float) -> vec4:
        self._r *= arg0
        self._g *= arg0
        self._b *= arg0
        self._a *= arg0
        return self

    def __mul__(self, arg0: float) -> vec4:
        return vec4(self._r * arg0, self._g * arg0, self._b * arg0, self._a * arg0)

    def __neg__(self) -> vec4:
        return vec4(-self._r, -self._g, -self._b, -self._a)

    def __rmul__(self, arg0: float) -> vec4:
        return vec4(self._r * arg0, self._g * arg0, self._b * arg0, self._a * arg0)

    @property
    def a(self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._a

    @a.setter
    def a(self: vec4, arg0: float) -> None:
        self._a = arg0

    @property
    def b(self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._b

    @b.setter
    def b(self: vec4, arg0: float) -> None:
        self._b = arg0

    @property
    def g(self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._g

    @g.setter
    def g(self: vec4, arg0: float) -> None:
        self._g = arg0

    @property
    def r(self: vec4) -> float:
        """float, component value (0.0-1.0)"""
        return self._r

    @r.setter
    def r(self: vec4, arg0: float) -> None:
        self._r = arg0
