from __future__ import annotations
from typing import List
from sbs_utils.vec import Vec3

import math
import queue
import sys
import threading
sys.modules["sbs"] = sys.modules[__name__]


sim = None
seconds = 0

# Storage for set_client_string / request_client_string round-trips.
# request_client_string() appends (client_id, key) here; the mission runner
# drains this after each tick and fires the corresponding client_string events.
_client_strings: dict = {}          # {client_id: {key: value}}
_pending_client_string_events: list = []  # [(client_id, key), ...]

# Physics events queued during physics_tick for the runner to drain.
# Each entry is a tuple: (tag, sub_tag, origin_id, selected_id).
# queue.Queue is thread-safe — the physics background thread puts() and the
# main loop get_nowait()s without needing additional locking.
_pending_physics_events: queue.Queue = queue.Queue()

# Currently-overlapping collision pairs — used to fire only on contact entry.
# Each pair is (min_id, max_id) so order is canonical.
_contact_pairs: set = set()

# Behavior dispatch: tick_type string → callable(space_object, dt_seconds)
_behavior_registry: dict = {}


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
        with sim._lock:
            sim.space_objects.pop(ID, None)
            sim._active_ids.discard(ID)
            sim._terrain_ids.discard(ID)

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
    try:
        from sbs_utils.helpers import FrameContext
        from sbs_utils.gui import get_client_aspect_ratio
        ar = get_client_aspect_ratio(FrameContext.client_id)
        return vec2(int(ar.x), int(ar.y))
    except Exception:
        return vec2(1024, 768)

def get_shared_string(key: str) -> str:
    """gets a shared string, given the key (itself a string).  Shared strings are automatically copied from server to all clients."""
    global sim
    if sim is not None:
        return sim.shared_strings.get(key, "")
    return ""

def get_ship_of_client(clientID: int) -> int:
    """returns the player ship ID assigned to the client computer"""
    global sim
    if sim is not None:
        return sim.client_ships.get(clientID, 0)
    return 0

def _font_size(fontTag: str) -> int:
    return {
        "smallest": 21,
        "gui-1": 27,
        "gui-2": 29,
        "gui-3": 35,
        "gui-4": 39,
        "gui-5": 44,
        "gui-6": 64,
    }.get(fontTag, 35)

_NARROW_CHARS = frozenset("iIl|!;:.,'`1fjr ")
_WIDE_CHARS   = frozenset("MWmw")

# Per-font char widths (narrow, wide, avg) in pixels — measured from browser canvas.measureText.
_CHAR_WIDTHS = {
    "smallest": ( 4.43, 12.38,  8.48),
    "gui-1":    ( 5.41, 15.13, 10.36),
    "gui-2":    ( 5.90, 16.50, 11.30),
    "gui-3":    ( 8.89, 28.09, 20.75),
    "gui-4":    (10.16, 32.10, 23.72),
    "gui-5":    (11.43, 36.12, 26.68),
    "gui-6":    (16.51, 52.17, 38.54),
}

def _char_pixel_width(ch: str, fontTag: str) -> float:
    narrow, wide, avg = _CHAR_WIDTHS.get(fontTag, _CHAR_WIDTHS["gui-3"])
    if ch in _NARROW_CHARS:
        return narrow
    if ch in _WIDE_CHARS:
        return wide
    return avg

def get_text_line_height(fontTag: str, textToMeasure: str) -> int:
    """for a font key and a text string (one line, no wrapping), this returns the height of the drawn text."""
    return _font_size(fontTag)

def get_text_line_width(fontTag: str, textToMeasure: str) -> int:
    """for a font key and a text string (one line, no wrapping), this returns the width of the drawn text."""
    if not textToMeasure:
        return 0
    return int(sum(_char_pixel_width(ch, fontTag) for ch in textToMeasure))

def get_text_block_height(fontTag: str, textToMeasure: str, width: int) -> int:
    """for a font key, a string of (possibly) multiline text, and a pixel width, this returns the height of the drawn text."""
    line_height = get_text_line_height(fontTag, textToMeasure)
    if not textToMeasure or width <= 0:
        return line_height
    space_w = get_text_line_width(fontTag, " ")
    total_lines = 0
    for paragraph in (textToMeasure.splitlines() or [""]):
        words = paragraph.split()
        if not words:
            total_lines += 1
            continue
        lines_in_para = 1
        current_w = 0
        for word in words:
            word_w = get_text_line_width(fontTag, word)
            if current_w == 0:
                current_w = word_w
            elif current_w + space_w + word_w > width:
                lines_in_para += 1
                current_w = word_w
            else:
                current_w += space_w + word_w
        total_lines += lines_in_para
    return total_lines * line_height

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

def _apply_ship_data_to_object(obj, data: dict) -> None:
    """Populate obj.data_set and physics fields from a shipData.yaml entry."""
    ds = obj.data_set

    # Exclusion radius
    er = data.get("exclusionradius")
    if er is not None:
        obj._exclusion_radius = float(er)

    # Scalar data_set fields that map 1-to-1
    for field in ("turn_rate", "speed_coeff", "scan_strength_coeff",
                  "ship_energy_cost", "warp_energy_cost", "jump_energy_cost",
                  "drone_launch_timer"):
        val = data.get(field)
        if val is not None:
            ds.set(field, float(val))

    # Bay count → bay_count
    bc = data.get("baycount")
    if bc is not None:
        ds.set("bay_count", int(bc))

    # Hull points → armor (hull integrity when shields fail)
    hp = data.get("hullpoints")
    if hp is not None:
        ds.set("armor",    float(hp))
        ds.set("armorMax", float(hp))

    # Shields — per-facing array
    shields = data.get("shields")
    if shields:
        ds.set("shield_count", len(shields))
        for i, sv in enumerate(shields):
            ds.set("shield_val",     float(sv), i)
            ds.set("shield_max_val", float(sv), i)

    # Beam weapons from hull_port_sets
    beams = data.get("hull_port_sets", {}).get("beam Primary Beams", [])
    if beams:
        ds.set("beamCount", len(beams))
        for i, b in enumerate(beams):
            ds.set("beamRange",       float(b.get("range",         1000)), i)
            ds.set("beamDamage",      float(b.get("damage_coeff",   1.0)) * 6.0, i)
            ds.set("beamCycleTime",   float(b.get("cycle_time",     6.0)), i)
            ds.set("beamArcWidth",    float(b.get("arcwidth",       360)), i)
            ds.set("beamBarrelAngle", float(b.get("barrel_angle",     0)), i)


def _try_populate_from_ship_data(obj) -> None:
    """Look up obj.data_tag in shipData.yaml and apply matching data to the object."""
    if not obj._data_tag:
        return
    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        data = get_ship_data_for(obj._data_tag)
        if data:
            _apply_ship_data_to_object(obj, data)
    except Exception:
        pass


def player_ship_setup_defaults(space_object: space_object) -> None:
    """Rebuilds the default blob data of this player ship."""
    _try_populate_from_ship_data(space_object)

def player_ship_setup_from_data(space_object: space_object) -> None:
    """Rebuilds the blob data of this player ship from the shipdata.json and the preferences.json."""
    _try_populate_from_ship_data(space_object)

def push_to_standby_list(space_object: space_object) -> None:
    """moves the spaceobject from normal space to the standby list."""
    push_to_standby_list_id(space_object.unique_ID)

def push_to_standby_list_id(id: int) -> None:
    """moves the spaceobject from normal space to the standby list."""
    global sim
    if sim is not None:
        with sim._lock:
            obj = sim.space_objects.pop(id, None)
            if obj is not None:
                sim.standby_list[id] = obj
                sim._active_ids.discard(id)
                sim._terrain_ids.discard(id)

def query_client_tags() -> None:
    """stub; does nothing yet."""

def query_client_widget_state(clientID: int, widgetName: str, fullScreenFlag: int) -> None:
    """sends a request for the client to send a 'widget_box_state' script event back."""

def remove_gui_hotkey(clientID: int, tag: str) -> None:
    """tells the targeted client (0 = server screen) to delete an existing hot key for a certain retained gui element."""

def request_client_string(clientComputerID: int, string_key: str) -> None:
    """requests a string value from the client computer.  This results in a script message, 'client_string'"""
    _pending_client_string_events.append((clientComputerID, string_key))

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
        with sim._lock:
            obj = sim.standby_list.pop(id, None)
            if obj is not None:
                sim.space_objects[id] = obj
                if obj._abits & 0x30:
                    sim._active_ids.add(id)
                else:
                    sim._terrain_ids.add(id)

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
    _client_strings.setdefault(clientComputerID, {})[string_key] = string_value

def set_dmx_channel(clientID: int, channel: int, behavior: int, speed: int, low: int, high: int) -> None:
    """set a color channel of dmx."""

# Main-screen view mode per client: clientID -> (view, angle, mode).
_view_modes: dict = {}

# Cinematic camera state per client, set by cinematic_control:
#   clientID -> {script, dolly_id, dolly_off, target_id, target_off}
_cinematic: dict = {}


def set_main_view_modes(clientID: int, main_screen_view: str, cam_angle: str, cam_mode: str) -> None:
    """sets the three modes of the main screen view for the specified client."""
    _view_modes[clientID] = (main_screen_view, cam_angle, cam_mode)


def cinematic_control(clientID: int, scriptControlsCamera: int, dollyID: int,
                      dollyPos: "vec3", targetID: int, targetPos: "vec3") -> None:
    """Place/track the cinematic camera for a client's 3dview main screen.

    scriptControlsCamera == 0  -> auto: track the client's assigned ship.
    scriptControlsCamera == 1  -> scripted: camera at dollyID + dollyPos,
                                  looking at targetID + targetPos.
    Pairs with set_main_view_modes(clientID, "3dview", <angle>, "cinematic").
    """
    def _tup(v):
        if v is None:
            return (0.0, 0.0, 0.0)
        return (float(v.x), float(v.y), float(v.z))
    _cinematic[clientID] = {
        "script":     int(scriptControlsCamera),
        "dolly_id":   int(dollyID),
        "dolly_off":  _tup(dollyPos),
        "target_id":  int(targetID),
        "target_off": _tup(targetPos),
    }


def get_cinematic_camera(clientID: int):
    """Resolve the current camera + look-at world positions for a client's cinematic
    view, or None if no cinematic state / no resolvable object.

    Returns {"cam": (x,y,z), "target": (x,y,z), "mode": str, "ship_id": str}.
    """
    st = _cinematic.get(clientID)
    if st is None or sim is None:
        return None

    def _obj_pos(oid):
        o = sim.space_objects.get(oid)
        return None if o is None else (o._pos.x, o._pos.y, o._pos.z)

    if st["script"] == 0:
        # Auto chase-cam: behind and above the assigned ship, looking ahead.
        ship_id = sim.client_ships.get(clientID, 0)
        o = sim.space_objects.get(ship_id)
        if o is None:
            return None
        p = o._pos
        f = o.forward_vector()
        cam = (p.x - f.x * 500.0, p.y + 150.0, p.z - f.z * 500.0)
        tgt = (p.x + f.x * 200.0, p.y, p.z + f.z * 200.0)
        return {"cam": cam, "target": tgt, "mode": "auto", "ship_id": str(ship_id)}

    # Scripted: explicit dolly/target objects + offsets.
    db = _obj_pos(st["dolly_id"]) or (0.0, 0.0, 0.0)
    do = st["dolly_off"]
    cam = (db[0] + do[0], db[1] + do[1], db[2] + do[2])
    tb = _obj_pos(st["target_id"]) or (0.0, 0.0, 0.0)
    to = st["target_off"]
    tgt = (tb[0] + to[0], tb[1] + to[1], tb[2] + to[2])
    return {"cam": cam, "target": tgt, "mode": "scripted",
            "ship_id": str(sim.client_ships.get(clientID, 0))}

def set_music_folder(ID: int, filename: str) -> None:
    """Sets the folder from which music is streamed; ID is ship, OR client, OR zero for server."""

def set_music_tension(ID: int, tensionValue: float) -> None:
    """Sets the tension value of ambient music (0-100); ID is ship, OR client, OR zero for server."""

def set_shared_string(key: str, value: str) -> None:
    """sets (or changes) a shared string, given a key and a value (both strings)."""
    global sim
    if sim is not None:
        sim.shared_strings[key] = value

# Current skybox art name (last set via set_sky_box / set_sky_box_all). The
# @media/skybox random-pick funnels through these, so tracking them is enough.
_current_skybox = None

def set_sky_box(clientID: int, artFileName: str) -> None:
    """sets the skybox art for a clientID (0 = server)."""
    global _current_skybox
    _current_skybox = artFileName

def set_sky_box_all(artFileName: str) -> None:
    """sets the skybox art for all connected computers."""
    global _current_skybox
    _current_skybox = artFileName

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


class navarea(navpoint):
    """A navpoint that also defines a 2D map region — a quad of four ground-plane
    (x, z) corners.  Being a navpoint, it carries all the standard properties
    (text, color, pos, visibleToShip, visibleToSide, …) and lives in the navpoint
    ID registry, so get_navpoint_by_id / navpoint_exists / delete_navpoint_by_id all
    operate on it just like the engine."""
    def __init__(self) -> None:
        super().__init__()
        self._points = []     # list of (x, z) ground-plane corners


# Typed defaults derived from object_data_documentation.txt
_DATA_SET_DEFAULTS = {
    # torpedo counts — int
    "EMP_MAX": 0, "EMP_NUM": 0, "EMP_VAL": 0,
    "Homing_MAX": 0, "Homing_NUM": 0, "Homing_VAL": 0,
    "Mine_MAX": 0, "Mine_NUM": 0, "Mine_VAL": 0,
    "Nuke_MAX": 0, "Nuke_NUM": 0, "Nuke_VAL": 0,
    # int fields
    "bay_count": 0, "beamCount": 0, "camera_target_UID": 0,
    "curFriendIndex": 0, "cur_scan_ID": 0, "cur_scan_percent": 0,
    "curx": 0, "cury": 0,
    "deathState": 0, "deathTick": 0, "dock_base_id": 0,
    "elite_anti_mine": 0, "elite_anti_torpedo": 0, "elite_drone_launcher": 0,
    "elite_low_vis": 0, "elite_low_vis_distance": 0, "elite_main_scn_invis": 0,
    "energy_to_torp_cost": 0, "eng_control_type_index": 0,
    "hull_hit_counter": 0, "icon_index": 0, "impulse_while_docked": 0,
    "inside_nebula_count": 0, "is_fighter_flag": 0, "is_shuttle_flag": 0,
    "jump_drive_active": 0, "jump_while_docked": 0,
    "lastx": 0, "lasty": 0,
    "monster_health": 0, "monster_health_max": 0, "move_speed": 0,
    "nebula_data_change": 0, "num_extra_scan_sources": 0,
    "pathx": 0, "pathy": 0, "pull_strength": 0, "random_seed": 0,
    "shield_count": 0, "shield_freq_strength": 0, "shield_hit_counter": 0,
    "shields_raised_flag": 0, "surrender_flag": 0,
    "system_coolant_available": 0, "system_coolant_used": 0, "system_last_coolant_change": 0,
    "target_id": 0, "torpedo_tube_count": 0, "unselectable": 0,
    "warp_drive_active": 0, "warp_while_docked": 0,
    # int64 / uint64 fields
    "beamTimer": 0, "healTimer": 0, "extra_scan_source": 0, "science_target_UID": 0,
    # float fields
    "absorption_blue": 0.0, "absorption_green": 0.0, "absorption_red": 0.0,
    "all_beam_damage_coeff": 0.0, "all_beam_upgrade_coeff": 0.0,
    "all_shield_damage_coeff": 0.0, "all_shield_upgrade_coeff": 0.0,
    "all_tube_damage_coeff": 0.0, "all_tube_upgrade_coeff": 0.0,
    "anisotropy": 0.0, "armor": 0.0, "armorMax": 0.0,
    "base_amplitude": 0.0, "base_frequency": 0.0,
    "beamArcWidth": 0.0, "beamBarrelAngle": 0.0,
    "beamColorA": 0.0, "beamColorB": 0.0, "beamColorG": 0.0, "beamColorR": 0.0,
    "beamCycleTime": 0.0, "beamDamage": 0.0,
    "beamHullPointX": 0.0, "beamHullPointY": 0.0, "beamHullPointZ": 0.0,
    "beamRange": 0.0, "beam_damage_coeff": 0.0, "beam_upgrade_coeff": 0.0,
    "body_1_size_coeff": 0.0, "body_2_size_coeff": 0.0,
    "closest_scan_delay": 0.0, "coolant_damage_coeff": 0.0, "coolant_upgrade_coeff": 0.0,
    "density": 0.0, "detail_amplitude": 0.0, "detail_frequency": 0.0,
    "detail_lacunarity": 0.0, "display_size": 0.0, "domain_warp": 0.0,
    "drone_damage": 0.0, "drone_launch_max_range": 0.0, "drone_launch_timer": 0.0,
    "effect_size": 0.0, "emission_blue": 0.0, "emission_green": 0.0, "emission_red": 0.0,
    "energy": 0.0, "eng_control_cost_coeff": 0.0, "eng_control_value": 0.0,
    "exciting": 0.0, "farthest_scan_delay": 0.0, "fractional_damage": 0.0,
    "icon_scale": 0.0, "impulse_damage_coeff": 0.0, "impulse_upgrade_coeff": 0.0,
    "jump_damage_coeff": 0.0, "jump_energy_cost": 0.0, "jump_upgrade_coeff": 0.0,
    "local_scale_coeff": 0.0, "local_scale_x_coeff": 0.0,
    "local_scale_y_coeff": 0.0, "local_scale_z_coeff": 0.0,
    "max_throttle": 0.0, "mesh_rotate_side": 0.0,
    "monster_heal_rate": 0.0, "monster_speed": 0.0,
    "overgrid_offset_x": 0.0, "overgrid_offset_z": 0.0,
    "percent": 0.0, "playerSPitch": 0.0, "playerSRoll": 0.0, "playerSYaw": 0.0,
    "playerThrottle": 0.0, "quick_jump_recharge_rate": 0.0, "quick_jump_recharge_state": 0.0,
    "reference_ring_3d_brightness": 0.0,
    "repair_rate_armor": 0.0, "repair_rate_shields": 0.0, "repair_rate_systems": 0.0,
    "scan_strength_coeff": 0.0,
    "scattering_blue": 0.0, "scattering_green": 0.0, "scattering_red": 0.0,
    "sensor_damage_coeff": 0.0, "sensor_upgrade_coeff": 0.0,
    "shield_damage_coeff": 0.0, "shield_max_val": 0.0, "shield_upgrade_coeff": 0.0,
    "shield_val": 0.0, "shield_wave_amplitude": 0.0, "shield_wave_frequency": 0.0,
    "shield_wave_offset": 0.0, "shield_wave_value": 0.0,
    "ship_apu_ceiling": 0.0, "ship_apu_output": 0.0, "ship_base_scan_range": 0.0,
    "ship_energy_cost": 0.0, "size": 0.0, "speed_coeff": 0.0, "swirl": 0.0,
    "system_coolant_setting": 0.0, "system_cur_heat": 0.0,
    "system_damage": 0.0, "system_max_damage": 0.0,
    "target_pos_x": 0.0, "target_pos_y": 0.0, "target_pos_z": 0.0,
    "throttle": 0.0, "total_speed_coeff": 0.0,
    "tube_damage_coeff": 0.0, "tube_upgrade_coeff": 0.0,
    "turnRate": 0.0, "turn_damage_coeff": 0.0, "turn_rate": 0.0, "turn_upgrade_coeff": 0.0,
    "warp_damage_coeff": 0.0, "warp_energy_cost": 0.0, "warp_upgrade_coeff": 0.0,
    # string fields
    "ally_list": "", "beamColor": "", "bio": "",
    "body_1_color": "", "body_1_diffuse_bitmap_file": "", "body_1_geom_filename": "",
    "body_2_color": "", "body_2_diffuse_bitmap_file": "", "body_2_geom_filename": "",
    "coolant_dot_active_color": "", "coolant_dot_reserve_color": "",
    "cur_scan_type": "", "display_text": "", "dock_state": "",
    "eng_control_label": "", "hull_name": "", "hull_origin": "", "hull_side": "",
    "icon_color": "", "info_text": "", "info_text_color": "", "intel": "",
    "internal_color_ship_lines": "", "internal_color_ship_nodes": "",
    "internal_color_ship_sillouette": "", "long_description": "", "name_tag": "",
    "particle_color_1": "", "particle_color_2": "", "particle_color_3": "",
    "radar_color_override": "", "scan": "", "scan_type_for_shld_freq": "",
    "scan_type_for_system_damage": "", "scan_type_list": "", "steeringType": "",
    "status": "", "torpedo_build_type": "", "torp_type_from_energy": "",
    "torpedo_types_available": "Homing,Nuke,EMP,Mine",
}


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
        return _DATA_SET_DEFAULTS.get(name, None)

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
        self.nav_points = {}          # keyed by name (str); navpoints only (not navareas)
        self.nav_points_by_id = {}    # keyed by int ID; holds both navpoints and navareas
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
        self.shared_strings = {}      # key -> value (synced server→clients in real engine)
        self._terrain_ids: set = set()   # abits & 0x30 == 0 — static; skipped in physics
        self._active_ids:  set = set()   # abits & 0x30 != 0 — NPCs + players; full physics
        self._lock = threading.Lock()

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
        """adds a new navarea to space; returns its (navpoint) integer ID.  The four
        x/y pairs are ground-plane corners (the 2D map y axis is world z).  A navarea
        is a navpoint, so it goes in the navpoint ID registry; its pos is the corner
        centroid so distance_to_navpoint and friends work on it."""
        self.nav_point_counter += 1
        area = navarea()
        area._points = [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
        area._text = text
        area._color = colDesc
        area._pos = vec3((x1 + x2 + x3 + x4) / 4.0, 0.0, (y1 + y2 + y3 + y4) / 4.0)
        self.nav_points_by_id[self.nav_point_counter] = area
        return self.nav_point_counter

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
        with self._lock:
            self.object_ids += 1
            id = self.object_ids
        obj = space_object()
        obj._id = id
        obj._abits = abits
        obj._data_tag = dataTag
        obj._tick_type = aiTag
        _try_populate_from_ship_data(obj)
        with self._lock:
            self.space_objects[id] = obj
            if abits & 0x30:
                self._active_ids.add(id)
            else:
                self._terrain_ids.add(id)
        return id

    def delete_navpoint_by_id(self: simulation, id: int) -> None:
        """deletes navpoint by its id (navareas are navpoints, so this covers them)"""
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
        self._rot_quat = quaternion(1, 0, 0, 0)  # identity rotation

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
        q = self._rot_quat
        w, x, y, z = q._w, q._x, q._y, q._z
        ql = math.sqrt(w*w + x*x + y*y + z*z)
        if ql < 1e-9:
            return vec3(0, 0, 1)
        w /= ql; x /= ql; y /= ql; z /= ql
        return vec3(2*(x*z + w*y), 2*(y*z - w*x), 1 - 2*(x*x + y*y))

    @property
    def pos(self: space_object) -> vec3:
        """vec3, position in space"""
        return self._pos

    @pos.setter
    def pos(self: space_object, arg0: vec3) -> None:
        self._pos = arg0

    def right_vector(self: space_object) -> vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
        q = self._rot_quat
        w, x, y, z = q._w, q._x, q._y, q._z
        ql = math.sqrt(w*w + x*x + y*y + z*z)
        if ql < 1e-9:
            return vec3(1, 0, 0)
        w /= ql; x /= ql; y /= ql; z /= ql
        return vec3(1 - 2*(y*y + z*z), 2*(x*y + w*z), 2*(x*z - w*y))

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
        q = self._rot_quat
        w, x, y, z = q._w, q._x, q._y, q._z
        ql = math.sqrt(w*w + x*x + y*y + z*z)
        if ql < 1e-9:
            return vec3(0, 1, 0)
        w /= ql; x /= ql; y /= ql; z /= ql
        return vec3(2*(x*y - w*z), 1 - 2*(x*x + z*z), 2*(y*z + w*x))

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


# ---------------------------------------------------------------------------
# Behavior dispatch
# ---------------------------------------------------------------------------

def register_behavior(tick_type: str, fn) -> None:
    """Register fn(space_object, dt_seconds) to run every physics tick for objects of this tick_type."""
    _behavior_registry[tick_type] = fn


# Absolute engine speed (units/sec at throttle=1.0, speed_coeff=1.0).  shipData only
# carries speed_coeff (a 0.0-1.0 multiplier), never an absolute top speed, so the
# absolute meters/sec lives here as a constant the coefficient scales.
BASE_TOP_SPEED = 200.0
# Additional units/sec per warp factor for player ships (playerThrottle > 1.0).
PLAYER_WARP_SPEED = 1000.0
# How fast _cur_speed eases toward its target (units/sec^2) — speed ramps, never snaps.
SPEED_RAMP_RATE = 60.0


def _ramp_speed(obj: space_object, target_speed: float, dt: float) -> None:
    """Ease obj._cur_speed toward target_speed at SPEED_RAMP_RATE; no instant changes."""
    cur = obj._cur_speed
    step = SPEED_RAMP_RATE * dt
    if cur < target_speed:
        obj._cur_speed = min(target_speed, cur + step)
    elif cur > target_speed:
        obj._cur_speed = max(target_speed, cur - step)


def _npcship_steer(obj: space_object, dt: float) -> None:
    """Default NPC ship behavior: steer toward target_pos_x/y/z and decelerate to
    arrive, rather than barreling in at full speed.  Speed cruises at
    throttle × BASE_TOP_SPEED × speed_coeff."""
    ds = obj.data_set
    if ds.get("deathState") > 0:
        obj._steer_yaw = 0.0
        obj._cur_speed = 0.0
        return

    throttle = ds.get("throttle") or 0.0
    tx = ds.get("target_pos_x") or 0.0
    tz = ds.get("target_pos_z") or 0.0
    dx = tx - obj._pos.x
    dz = tz - obj._pos.z
    horiz_dist = math.sqrt(dx * dx + dz * dz)

    turn_rate = ds.get("turn_rate") or 0.0
    if turn_rate <= 0.0:
        turn_rate = 0.1  # ~6 deg/s fallback when shipData not loaded

    # speed_coeff / total_speed_coeff are 0.0-1.0 multipliers on the absolute top
    # speed — not a speed themselves.  Default to 1.0 when unset (coeffs default to 1.0).
    speed_coeff = ds.get("total_speed_coeff") or ds.get("speed_coeff") or 1.0
    cruise_speed = throttle * BASE_TOP_SPEED * speed_coeff

    # Arrival radius: "close enough" — stop steering and moving.  Honor an explicit
    # stop_dist if a caller stored one, else a small default.
    arrive_dist = ds.get("stop_dist") or 0.0
    if arrive_dist <= 0.0:
        arrive_dist = 20.0

    if horiz_dist > arrive_dist and throttle > 0.0:
        fwd = obj.forward_vector()
        ndx, ndz = dx / horiz_dist, dz / horiz_dist
        # Y-component of (fwd × desired): positive → target is right of heading → steer right (+yaw)
        cross_y = fwd.z * ndx - fwd.x * ndz
        steer = cross_y * turn_rate * 5.0     # P-controller; clamp to ±turn_rate
        obj._steer_yaw = max(-turn_rate, min(turn_rate, steer))
    else:
        obj._steer_yaw = 0.0

    # Arrival braking: full speed cruises in, but within ~2× the turn radius the
    # ship slows proportionally so its turn radius shrinks below the distance to
    # the target and it can actually arrive.  Without this it orbits the target
    # forever (which reads as spinning on the 2D radar).
    turn_radius = cruise_speed / turn_rate
    brake_dist = max(2.0 * turn_radius, 100.0)
    if horiz_dist <= arrive_dist:
        target_speed = 0.0
    elif horiz_dist < brake_dist:
        target_speed = cruise_speed * (horiz_dist / brake_dist)
    else:
        target_speed = cruise_speed
    _ramp_speed(obj, target_speed, dt)


def _playership_drive(obj: space_object, dt: float) -> None:
    """Default player ship behavior: drive forward along current heading from
    playerThrottle (0.0-5.0; <=1.0 impulse, >1.0 warp).  Helm sets _steer_yaw
    elsewhere — this only ramps forward speed."""
    ds = obj.data_set
    if ds.get("deathState") > 0:
        obj._cur_speed = 0.0
        return

    pt = ds.get("playerThrottle") or 0.0
    speed_coeff = ds.get("total_speed_coeff") or ds.get("speed_coeff") or 1.0
    if pt <= 1.0:
        target_speed = pt * BASE_TOP_SPEED * speed_coeff
    else:
        # Warp: full impulse plus a warp-factor bonus.
        target_speed = (BASE_TOP_SPEED + (pt - 1.0) * PLAYER_WARP_SPEED) * speed_coeff
    _ramp_speed(obj, target_speed, dt)


# Pre-register default behaviors; mission code may override with register_behavior().
_behavior_registry["behav_npcship"] = _npcship_steer
_behavior_registry["behav_playership"] = _playership_drive


# ---------------------------------------------------------------------------
# Physics helpers
# ---------------------------------------------------------------------------

def _cell(x: float, z: float, sz: float):
    return (int(x / sz), int(z / sz))


def _physics_collision(sim, active: list) -> None:
    """Spatial-hash sphere collision.

    Checks active-active and active-terrain pairs only.  Terrain-terrain is
    skipped entirely — static objects can never enter new contacts with each
    other.  Fires collision events into _pending_physics_events (queue.Queue).
    """
    global _contact_pairs
    if not active:
        _contact_pairs = set()
        return

    space = sim.space_objects

    # Auto-tune cell size: 2 × max active exclusion radius, minimum 500 units.
    max_er = 0.0
    for _id, obj in active:
        if obj._exclusion_radius > max_er:
            max_er = obj._exclusion_radius
    cell_sz = max(max_er * 2.0, 500.0)

    # Build per-cell buckets for active objects and terrain.
    active_grid: dict = {}
    for id_, obj in active:
        if obj._exclusion_radius > 0:
            ck = _cell(obj._pos.x, obj._pos.z, cell_sz)
            active_grid.setdefault(ck, []).append((id_, obj))

    terrain_grid: dict = {}
    for tid in sim._terrain_ids:
        obj = space.get(tid)
        if obj is not None and obj._exclusion_radius > 0:
            ck = _cell(obj._pos.x, obj._pos.z, cell_sz)
            terrain_grid.setdefault(ck, []).append((tid, obj))

    new_contacts: set = set()
    visited: set = set()

    # Active vs active — 9-cell neighborhood, upper-triangle dedup via visited.
    for (cx, cz), cell_list in active_grid.items():
        neighbors: list = []
        for ndx in (-1, 0, 1):
            for ndz in (-1, 0, 1):
                nb = active_grid.get((cx + ndx, cz + ndz))
                if nb:
                    neighbors.extend(nb)

        for aid, a in cell_list:
            ra = a._exclusion_radius
            for bid, b in neighbors:
                if bid <= aid:
                    continue
                pair = (aid, bid)
                if pair in visited:
                    continue
                visited.add(pair)
                rb = b._exclusion_radius
                ddx = a._pos.x - b._pos.x
                ddy = a._pos.y - b._pos.y
                ddz = a._pos.z - b._pos.z
                if ddx * ddx + ddy * ddy + ddz * ddz < (ra + rb) * (ra + rb):
                    new_contacts.add(pair)
                    if pair not in _contact_pairs:
                        _pending_physics_events.put(("collision", "passive", aid, bid))
                        _pending_physics_events.put(("collision", "passive", bid, aid))

    # Active vs terrain — terrain never in active_grid so no dedup needed.
    for (cx, cz), cell_list in active_grid.items():
        for aid, a in cell_list:
            ra = a._exclusion_radius
            for ndx in (-1, 0, 1):
                for ndz in (-1, 0, 1):
                    tb = terrain_grid.get((cx + ndx, cz + ndz))
                    if not tb:
                        continue
                    for tid, t in tb:
                        rt = t._exclusion_radius
                        ddx = a._pos.x - t._pos.x
                        ddy = a._pos.y - t._pos.y
                        ddz = a._pos.z - t._pos.z
                        if ddx * ddx + ddy * ddy + ddz * ddz < (ra + rt) * (ra + rt):
                            pair = (min(aid, tid), max(aid, tid))
                            new_contacts.add(pair)
                            if pair not in _contact_pairs:
                                _pending_physics_events.put(("collision", "passive", aid, tid))
                                _pending_physics_events.put(("collision", "passive", tid, aid))

    _contact_pairs = new_contacts


# ---------------------------------------------------------------------------
# Physics tick
# ---------------------------------------------------------------------------

def physics_tick(dt: float = 1.0 / 60.0) -> None:
    """Integrate motion for active (NPC/PLAYER) objects and detect collisions.

    Terrain objects (abits & 0x30 == 0) are fully static and are never
    dispatched, integrated, or checked against each other.  Active objects can
    still collide with terrain (handled by _physics_collision).

    Thread-safe: acquires sim._lock for the entire tick so the main thread can
    safely spawn and delete objects between ticks.  Collision events are put()
    into _pending_physics_events (queue.Queue) for the mission runner to drain.
    """
    global sim
    if sim is None or sim._paused:
        return

    with sim._lock:
        space = sim.space_objects

        # Snapshot active (id, obj) pairs while holding the lock.
        active = [(id_, space[id_]) for id_ in sim._active_ids if id_ in space]

        # 1. Behavior dispatch — active objects only.
        for _id, obj in active:
            fn = _behavior_registry.get(obj._tick_type)
            if fn:
                try:
                    fn(obj, dt)
                except Exception:
                    pass

        # 2. Rotation and translation — active objects only.
        for _id, obj in active:
            if obj.data_set.get("deathState") > 0:
                continue
            q = obj._rot_quat
            ql = math.sqrt(q._w**2 + q._x**2 + q._y**2 + q._z**2)
            if ql < 1e-9:
                q._w, q._x, q._y, q._z = 1.0, 0.0, 0.0, 0.0
            else:
                q._w /= ql; q._x /= ql; q._y /= ql; q._z /= ql

            sy, sp, sr = obj._steer_yaw, obj._steer_pitch, obj._steer_roll
            if sy or sp or sr:
                w, x, y, z = q._w, q._x, q._y, q._z
                h = dt * 0.5
                dw = -(x * sp + y * sy + z * sr) * h
                dx = ( w * sp + y * sr - z * sy) * h
                dy = ( w * sy - x * sr + z * sp) * h
                dz = ( w * sr + x * sy - y * sp) * h
                w += dw; x += dx; y += dy; z += dz
                ql = math.sqrt(w*w + x*x + y*y + z*z)
                if ql > 1e-9:
                    q._w, q._x, q._y, q._z = w/ql, x/ql, y/ql, z/ql

            if obj._cur_speed:
                fwd = obj.forward_vector()
                obj._pos.x += fwd.x * obj._cur_speed * dt
                obj._pos.y += fwd.y * obj._cur_speed * dt
                obj._pos.z += fwd.z * obj._cur_speed * dt

        # 3. Collision — spatial hash; active-active + active-terrain only.
        _physics_collision(sim, active)

        # 4. Passive systems — shield regen + APU energy, active objects only.
        for _id, obj in active:
            if obj.data_set.get("deathState") > 0:
                continue
            ds = obj.data_set

            repair = ds.get("repair_rate_shields") or 0.0
            if repair > 0.0:
                n_shields = ds.get("shield_count") or 0
                for si in range(max(1, n_shields)):
                    sv = ds.get("shield_val", si) or 0.0
                    sm = ds.get("shield_max_val", si) or 0.0
                    if sm > 0.0 and sv < sm:
                        ds.set("shield_val", min(sm, sv + repair * dt), si)

            apu = ds.get("ship_apu_output") or 0.0
            if apu > 0.0:
                energy = ds.get("energy") or 0.0
                ceiling = ds.get("ship_apu_ceiling") or 0.0
                if ceiling > 0.0 and energy < ceiling:
                    ds.set("energy", min(ceiling, energy + apu * 2.0 * dt))
