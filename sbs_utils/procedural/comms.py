from . import query 
from .inventory import get_inventory_value
from .roles import has_role
from .. import faces
from ..agent import Agent
from ..helpers import FrameContext, FakeEvent
from ..futures import Promise, awaitable
from ..garbagecollector import GarbageCollector
from ..mast.mastscheduler import ChangeRuntimeNode
from ..mast.pollresults import PollResults
from ..mast_sbs.story_nodes.button import Button
from .gui import gui_properties_set


class CommsOverride:
    active_overrides = []
    def __init__(self, origin_id=None, selected_id=None, face=None, from_name=None):
        self.origin_id = query.to_set(origin_id) if origin_id is not None else origin_id
        self.selected_id = query.to_set(selected_id) if selected_id is not None else selected_id

        self.face = face
        self.from_name = from_name

    def __enter__(self):
        CommsOverride.active_overrides.append(self)
        return self

    def __exit__(self, ex_type=None, ex_val=None, ex_tb=None):
        if len(CommsOverride.active_overrides)>0:
            CommsOverride.active_overrides.pop()
        if ex_type:
            return False
        return True
        

    @classmethod
    def active(cls):
        if len(CommsOverride.active_overrides)>0:
            return CommsOverride.active_overrides[-1]
        return None

        
def comms_override(origin_id=None, selected_id=None, face=None, from_name=None):
    return CommsOverride(origin_id, selected_id, face, from_name)


def comms_broadcast(ids_or_obj, msg, color=None) -> None:
    """Send text to the text waterfall
    The ids can be player ship ids or client/console ids

    Args:
        ids_or_obj (id or objecr): A set or single id or object to send to, 
        msg (str): The text to send
        color (str, optional): The Color for the text. Defaults to "#fff".
    """
    if color is None:
        color="#fff"
    if ids_or_obj is None:
        # default to the 
        ids_or_obj = FrameContext.context.event.parent_id

    if FrameContext.task:
        msg = FrameContext.task.compile_and_format_string(msg)

    _ids = query.to_id_list(ids_or_obj)
    if _ids:
        for id in _ids:
            if query.is_client_id(id):
                FrameContext.context.sbs.send_message_to_client(id, color, msg)
            else:
                # Just verify the id
                obj = Agent.get(id)
                if obj is not None or id==0:
                    FrameContext.context.sbs.send_message_to_player_ship(id, color, msg)

def _comms_get_colors(to_obj, from_obj, is_receive, title_color, color):
    from .lifeform import Lifeform

    if title_color is None and isinstance(to_obj, Lifeform):
        title_color = to_obj.title_color

    if color is None and isinstance(to_obj, Lifeform):
        color = to_obj.message_color

    if title_color is None and isinstance(from_obj, Lifeform):
        title_color = from_obj.title_color

    if color is None and isinstance(from_obj, Lifeform):
        color = from_obj.message_color

    if title_color is None:
        allies = role_are_allies(to_obj.id, from_obj.id)
        if not allies:
            title_color = "red"
        else:
            title_color = "green"

    if color is None:
        color = "#fff"
    if title_color is None:
        title_color = color
        

    return title_color, color


def comms_message(msg, from_ids_or_obj, to_ids_or_obj, title=None, face=None, color=None, title_color=None, is_receive=True, from_name=None) -> None:
    """ Send a Comms message 
    This is a lower level function that lets you have more control the sender and receiver

    Args:
        msg (str): The message to send
        from_ids_or_obj (idset): The senders of the message
        to_ids_or_obj (idset): The set or receivers
        title (str, optional): The title text. Defaults to None.
        face (str, optional): The face string to use. Defaults to None.
        color (str, optional): The color of the body text. Defaults to "#fff".
        title_color (str, optional): The color of the title text. Defaults to None.
    """ 
    _override = CommsOverride.active()
    if _override is not None:
        if _override.face is not None:
            face = _override.face
        if _override.from_name is not None:
            from_name = _override.from_name
        if _override.origin_id is not None:
            to_ids_or_obj = _override.origin_id
        if _override.selected_id is not None:
            from_ids_or_obj = _override.selected_id

    if to_ids_or_obj is None:
        # internal message
        to_ids_or_obj = from_ids_or_obj
    if FrameContext.task:
        msg = FrameContext.task.compile_and_format_string(msg)
        if title is not None:
            title = FrameContext.task.compile_and_format_string(title)
    
    from_objs = query.to_object_list(from_ids_or_obj)
    to_objs = query.to_object_list(to_ids_or_obj)

    for from_obj in from_objs:
        for to_obj in to_objs:
            # From face should be used
            # Handle life forms at this low level
            from .lifeform import Lifeform
            from ..gridobject import GridObject
            from ..gui import GuiClient
            from ..faces import get_face
            life = False

            # Make sure life forms have an object
            title_color, color = _comms_get_colors(to_obj, from_obj, is_receive, title_color, color)

            if isinstance(from_obj, (Lifeform, GridObject)):
                if from_name is None:
                    from_name = from_obj.name
                    face = get_face(from_obj.id)
                if from_obj.host==0:
                    from_obj = to_obj
                else:
                    from_obj = to_object(from_obj.host)
                life = True

                

            if isinstance(to_obj, (Lifeform, GridObject)):
                if to_obj.host==0:
                    to_obj = from_obj
                else:
                    to_obj = to_object(to_obj.host)
                life = True



            # This happens if one of them is id 0
            if isinstance(to_obj, GuiClient) or isinstance(from_obj, GuiClient) is None:
                print("COMMS Message set to ID 0")
                continue

            if to_obj is None and from_obj is None:
                print("COMMS Message set to ID 0")
                continue

            from_name_now = from_name
            if from_name is None:
                if is_receive:
                    from_name_now = from_obj.comms_id
                else:
                    from_name_now = to_obj.comms_id
                    

            if title is None:
                title = from_name_now # +" > "+to_obj.comms_id
            else:
                title = from_name_now +": "+ title

            if is_receive:
                title = "< < " + title
            else:
                title = "> > " + title


            if face is None:
                face = faces.get_face(from_obj.get_id())
            
            
            
            if life:
                if from_obj is None:
                    from_obj = to_obj
                elif to_obj is None:
                    to_obj = from_obj

            if to_obj is None or from_obj is None:
                continue

            
            # Only player ships send messages
            if has_role(from_obj.id, "__PLAYER__"):
                FrameContext.context.sbs.send_comms_message_to_player_ship(
                    from_obj.id,
                    to_obj.id,
                    face, 
                    title,
                    title_color, 
                    msg,
                    color)
            else:

                FrameContext.context.sbs.send_comms_message_to_player_ship(
                    to_obj.id,
                    from_obj.id,
                    face, 
                    title, 
                    title_color,
                    msg,
                    color
                    )

def _comms_get_origin_id() -> int:
    #
    # Event, Event origin is the best guess when the button is pressed
    #
    _override = CommsOverride.active()
    if _override is not None:
        if _override.origin_id is not None:
            return _override.origin_id

    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "press_comms_button":
            return FrameContext.context.event.origin_id
    #
    # 
    #
    if FrameContext.task is not None:
        # This will attempt to default to the client ship if all else fails
        event = FrameContext.context.event
        
        if event is None:
            return 0
        _ship_id = FrameContext.context.sbs.get_ship_of_client(FrameContext.context.event.client_id)
        return FrameContext.task.get_variable("COMMS_ORIGIN_ID", _ship_id)

def _comms_get_selected_id() -> int:
    #
    # Event 
    #
    _override = CommsOverride.active()
    if _override is not None:
        if _override.selected_id is not None:
            return _override.selected_id

    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "press_comms_button":
            return FrameContext.context.event.selected_id
    
    if FrameContext.task is not None:
        return FrameContext.task.get_variable("COMMS_SELECTED_ID", 0)



def comms_transmit(msg, title=None, face=None, color=None, title_color=None) -> None:
    """ Transmits a message from a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.

    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None.
    """    
    from_ids_or_obj = _comms_get_origin_id()
    to_ids_or_obj = _comms_get_selected_id()
    if to_ids_or_obj is None or from_ids_or_obj is None:
        #
        # Communicate an error
        #
        pass 
    # player transmits a message
    comms_message(msg, from_ids_or_obj, to_ids_or_obj,  title, face, color, title_color, False)

def comms_receive(msg, title=None, face=None, color=None, title_color=None) -> None:
    """ Receive a message on a player ship from another ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.

    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None.
    """    
    to_ids_or_obj = _comms_get_origin_id()
    from_ids_or_obj = _comms_get_selected_id()
    if to_ids_or_obj is None or from_ids_or_obj is None:
        #
        # Communicate an error
        #
        pass 
    # player receives a message
    comms_message(msg, from_ids_or_obj, to_ids_or_obj,  title, face, color, title_color, True)


def comms_speech_bubble(msg, seconds=3, color=None, client_id=None, selected_id=None) -> None:
    """ Transmits a message from a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.

    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None.
    """
    if color is None:
        color="#fff"    
    from_ids_or_obj = _comms_get_origin_id()
    to_ids_or_obj = _comms_get_selected_id()
    if to_ids_or_obj is None or from_ids_or_obj is None:
        #
        # Communicate an error
        #
        pass 
    if FrameContext.context.event is None:
         return
    
    client_id = FrameContext.context.event.client_id
    selected_id = FrameContext.context.event.selected_id

    # player transmits a message
    # sbs.send_speech_bubble_to_object()   attaches a speech bubble to a space object on the 2d radar.
    #     py::arg("clientComputerID"),     send to this client (0 = server)
    #     py::arg("spaceObjectID"),        spaceobject to attach the bubble to
    #     py::arg("seconds"),              set seconds to zero for an everlasting bubble.
    #     py::arg("color"),                text, "red", "#3ff", the usual
    #     py::arg("text"),                 text message. like "curse you terran!"
    FrameContext.context.sbs.send_speech_bubble_to_object(client_id, selected_id, seconds, color, msg)


def comms_transmit_internal(msg, ids_or_obj=None, to_name=None, title=None, face=None, color=None, title_color=None) -> None:
    """ Transmits a message within a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.

    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None.
    """    
    ids_or_obj = _comms_get_origin_id()
    # player transmits a message to a named internal
    for ship in query.to_object_list(ids_or_obj):
        if to_name is None:
            to_name = ship.name
        # if title is None:
        #     title = f"{ship.name} > {to_name}"
        if face is None and to_name is not None:
            # try to find a face
            face = get_inventory_value(ship.id, f"face_{to_name}", None)
        comms_message(msg, ship, ship,  title, face, color, title_color, False, to_name)


def comms_receive_internal(msg, ids_or_obj=None, from_name=None,  title=None, face=None, color=None, title_color=None) -> None:
    """ Receiver a message within a player ship
    It uses the current context to determine the sender and receiver.
    typically from the event that it being handled provide the context.

    Args:
        msg (str): The message to send
        title (str, optional):The title text. Defaults to None.
        face (str, optional): The face string of the face to use. Defaults to None.
        color (str, optional): The body text color. Defaults to "#fff".
        title_color (str, optional): The title text color. Defaults to None.
    """    
    if ids_or_obj is None:
        ids_or_obj = _comms_get_origin_id()
    # player transmits a message to a named internal
    for ship in query.to_object_list(ids_or_obj):
        if from_name is None:
            from_name = ship.name
        # if title is None:
        #     title = f"{from_name} > {ship.name}"
        if face is None and from_name is not None:
            # try to find a face
            face = get_inventory_value(ship.id, f"face_{from_name}", None)
        comms_message(msg, ship, ship,  title, face, color, title_color, True, from_name)
        
        
def comms_info(name, face=None, color=None) -> None:
    """Set the communication information status in the comms console

    Args:
        name (str): The name to present
        face (str, optional): The face string of the face. Defaults to None.
        color (str, optional): The colot of the text. Defaults to None.
    """    
    if FrameContext.task is not None:
        color = FrameContext.task.compile_and_format_string(color) if color else "white"
        name = FrameContext.task.compile_and_format_string(name) if name else None

    to_so = query.to_object(_comms_get_selected_id())
    from_so = query.to_object(_comms_get_origin_id())

    if to_so is None or from_so is None:
        return
    # Just in case swap if from is not a player
    if not from_so.is_player:
        swap = to_so
        to_so = from_so
        from_so = swap

    if name is None:
        name = to_so.comms_id

    if face is None:    
        face = faces.get_face(to_so.id) 

    
    if to_so.is_grid_object:
        FrameContext.context.sbs.send_grid_selection_info(from_so.id, face, color, name)
    else:
        FrameContext.context.sbs.send_comms_selection_info(from_so.id, face, color, name)



from ..consoledispatcher import ConsoleDispatcher
from .gui import ButtonPromise
class CommsPromise(ButtonPromise):

    def __init__(self, path, task, timeout=None) -> None:
        path = path if path is not None else ""
        path = f"comms"
        super().__init__(path, task, timeout)
        self.path_root = "comms"

        #in super self.task = task
        self.button = None
        self.is_unknown = False
        self.color = "white"
        self.expanded_buttons = None
        self.comms_id = "static"
        self.face = ""
        self.face_override = None
        self.is_grid_comms = False
        self.assign = None
        # Unschedule from scheduler
        # Task needs to run the await comms()
        # Which is here, then we unschedule it
        # System makes sure it runs
        self.task.main.tasks.remove(self.task)
        self.promise_buttons = []
        self.comms_badge = None
        

    def set_path(self, path) -> None:
        # Always clear properties
        page = FrameContext.page 
        task = FrameContext.task
        FrameContext.page = self.task.main.page
        FrameContext.task = self.task
        gui_properties_set(None)
        FrameContext.page = page
        FrameContext.task = task
        if len(path)<len(self.path_root):
            path = self.path_root

        p = path.strip("/")
        # 
        # This may not be enough, but should cover 
        # resetting the comms badge
        if p == "comms/comms_badge" or p == "comms":
            self.set_comms_badge(None)

        #self.set_comms_badge(None)

        super().set_path(path)
        

    def set_face_override(self, face):
        self.face_override = face

    def initial_poll(self) -> None:
        if self._initial_poll:
            return
        
        # Will Build buttons
        # if self.expanded_buttons is None:
        #     self.expanded_buttons = self.get_expanded_buttons()
        self.show_buttons()
        super().initial_poll()

    def message(self, event) -> None:
        #
        # Check to see if this was intended for us
        #
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return
        
        #
        # Set the client so it knows the selected console
        #
        self.face_override = None
        self.run_focus = True
        this_button = int(event.sub_tag)
        self.event = event
        if this_button < len(self.expanded_buttons):
            self.button = self.expanded_buttons[this_button]
            self.button.visit((self.origin_id, self.selected_id))
        self.clear()
        self.task.tick()
       
        
    def collect(self) -> bool:
        oo = query.to_object(self.origin_id)
        selected_so = query.to_object(self.selected_id)
        if oo is not None and self.selected_id == 0:
            return False
        if oo is not None and selected_so is not None:
            return False
        self.leave()
        self.task.end()
        return True


    def clear(self) -> None:
        if self.is_grid_comms:
            FrameContext.context.sbs.send_grid_selection_info(self.origin_id, self.face, self.color, self.comms_id)
        else:
            FrameContext.context.sbs.send_comms_selection_info(self.origin_id, self.face, self.color, self.comms_id)

    def leave(self) -> None:
        self.clear()
        GarbageCollector.remove_garbage_collect(self.collect)
        if self.is_grid_comms:
            ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'grid_selected_UID')
            ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'grid_selected_UID')
        else:
            ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'comms_target_UID')
            ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'comms_target_UID')

        if self.assign is not None:
            self.task.set_value_keep_scope(self.assign, self.button)        

    def process_on_change(self) -> None:
        # Check for on change nodes
        #
        print("ProcessOnChangeComms")
        self.on_change = None
        if self.on_change is not None:
            self.on_change=[]
            # create proxies of the runtime node to test
            for change in self.on_change:
                rt = ChangeRuntimeNode()
                rt.enter(self.task.main.mast, self.task, change)
                self.on_change.append(rt)

    #def build_navigation_buttons(self):
    #    return []
    #
    # This 
    #
    def show_buttons(self) -> None:
        
        self.selected_id = self.task.get_variable("COMMS_SELECTED_ID")
        self.origin_id = self.task.get_variable("COMMS_ORIGIN_ID")
        #
        # Odd sometimes a zero slip though
        #
        oo = query.to_object(self.origin_id)
        if oo is None:
            self.set_result(True)
            return


        selected_so = query.to_object(self.selected_id)
        if selected_so is None and self.selected_id != 0:
            self.set_result(True)
            return
            
        # Not ready yet
        self.expanded_buttons = self.get_expanded_buttons()
        if len(self.expanded_buttons) == 0:
            return
        
        self.tag = None
        self.button = None
        self.event = None
        self.is_running = False
        #self.color = node.color if node.color else "white"
        # If this is the same ship it is known
        self.is_unknown = False

        self.is_grid_comms = query.is_grid_object_id(self.selected_id)
        #
        # Handle case where the selection is not a grid or space object
        #
        if self.selected_id != 0:
            is_space_object = query.is_space_object_id(self.selected_id)
            if not self.is_grid_comms and not is_space_object:
                self.set_result(True)
                return
            
            selected_so = query.to_object(self.selected_id)
            if selected_so is None:
                return
            
            self.comms_id = selected_so.comms_id
            if self.face_override is None: 
                self.face = faces.get_face(self.selected_id)
            else: 
                self.face = self.face_override
        else:
            if self.face_override is None: 
                self.face = faces.get_face(self.origin_id)
            else: 
                self.face = self.face_override
            self.comms_id = ""
            # TODO: This should check console type
            self.is_grid_comms = False
            
        

        selection = None
        if self.is_grid_comms:        
            ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'grid_selected_UID', self.selected)
            ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'grid_selected_UID', self.message)
            GarbageCollector.add_garbage_collect(self.collect)
            selection = query.get_grid_selection(self.origin_id)
        else:
            ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'comms_target_UID', self.selected)
            ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'comms_target_UID', self.message)
            GarbageCollector.add_garbage_collect(self.collect)
            selection = query.get_comms_selection(self.origin_id)

        if selection == self.selected_id:
            self.set_buttons(self.origin_id, selection)
        # from_so.face_desc

    def selected(self, event) -> None:
        #
        # Check to see if this was intended for us
        #

        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return
        
        #if prev != self.selected_id and prev != 0:
        self.set_path("comms")
        self.set_face_override(None)
        self.face = faces.get_face(event.selected_id)
        if event.selected_id == 0:
            self.face = faces.get_face(event.origin_id)
        
        # If the button block is running do not set the buttons
        if not self.is_running:
            origin_id = event.origin_id
            selected_id = event.selected_id
            self.set_buttons(origin_id, selected_id)
            self.run_focus = True

    def set_buttons(self, origin_id, selected_id) -> None:
        if self.selected_id != selected_id or \
            self.origin_id != origin_id:
            return
        
        # check to see if the from ship still exists
        if origin_id is not None:

            title = f"{self.comms_id}"
            if len(self.path)>6:
                title = f"{self.comms_id} {self.path[6:]}"
            if self.is_grid_comms:
                FrameContext.context.sbs.send_grid_selection_info(origin_id, self.face, self.color, title)
            elif origin_id == selected_id:
                FrameContext.context.sbs.send_comms_selection_info(origin_id, self.face, self.color, title)
            elif selected_id == 0:
                FrameContext.context.sbs.send_comms_selection_info(origin_id, self.face, self.color, title)
            else:
                #
                # Check for unknown 
                #
                oo = query.to_object(origin_id)
                so = query.to_object(selected_id)
                
                if oo is None or so is None:
                    return
                scan_name = oo.side+"scan"
                initial_scan = so.data_set.get(scan_name,0)
                
                if initial_scan is None or initial_scan =="no data":
                    FrameContext.context.sbs.send_comms_selection_info(origin_id, "", "white", "unknown")
                    self.is_unknown = True
                    return
                else:
                    FrameContext.context.sbs.send_comms_selection_info(origin_id, self.face, self.color, title)

            for i, button in enumerate(self.expanded_buttons):
                value = True
                color = "white"
                if button.color is not None:
                    color = self.task.format_string(button.color)
                if button.code is not None:
                    value = self.task.eval_code(button.code)
                if value and button.should_present((origin_id, selected_id)):
                    msg = self.task.format_string(button.message)
                    if self.is_grid_comms:
                        FrameContext.context.sbs.send_grid_button_info(origin_id, color, msg, f"{i}")
                    else:
                        FrameContext.context.sbs.send_comms_button_info(origin_id, color, msg, f"{i}")


    def pressed_set_values(self, task) -> None:
        oo = query.to_object(self.origin_id)
        so = query.to_object(self.selected_id)
        if oo is  None: # or so is None:
            return
        #
        # Set Name Value
        #
        task.set_variable("COMMS_ORIGIN", oo)
        task.set_variable("COMMS_SELECTED", so)
        task.set_variable("COMMS_ORIGIN_ID", self.origin_id)
        task.set_variable("COMMS_SELECTED_ID", self.selected_id)
        task.set_variable("COMMS_LIFEFORM_ID", self.comms_badge)

    def pressed_test(self) -> bool:
        oo = query.to_object(self.origin_id)
        so = query.to_object(self.selected_id)
        if oo is  None:
            # Player no longer valid
            return False
        
        if so is  None and self.selected_id != 0:
            # Other no longer valid
            comms_message(f"Lost communications with {self.comms_id}", self.origin_id, self.origin_id, "Signal Lost", "", from_name="communication grid")
            self.comms_id = "static"
            self.face = ""
            self.clear()
            return False
        
            
        return True

    def handle_button_sub_task(self, sub_task):
        FrameContext.server_task.main.tasks.append(sub_task)
        self.show_buttons()

    def poll(self):
        event = FrameContext.context.event
        #if self.event is not None:
        FrameContext.context.event = self.event
        # else:
        #     FrameContext.context.event = FakeEvent(client_id=1)
        super().poll()
        #print("COMMS POLL")
        FrameContext.context.event = event
        #
        # Selecting 0 now mean Long Range Comms
        #
        if self.selected_id == 0:
            self.is_unknown = False
        #
        # If the ship was unknown, but now is known
        #
        if self.is_unknown:
            oo = query.to_object(self.origin_id)
            so = query.to_object(self.selected_id)
            # Should the END?
            if oo is None or so is None:
                self.set_result(True)
                return PollResults.OK_ADVANCE_TRUE
            
            scan_name = oo.side+"scan"
            initial_scan = so.data_set.get(scan_name,0)
            self.is_unknown = (initial_scan is None or initial_scan == "" or initial_scan == "no data")
            
            # It is now known
            #
            if not self.is_unknown:
                # if selected update buttons
                player_current_select = oo.data_set.get( "comms_target_UID",0)
                if player_current_select == self.selected_id:
                    self.set_buttons(self.origin_id, self.selected_id)
                return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN
    
    def build_promise_buttons(self):
        ret = []
        for cp in self.promise_buttons:
            new_buttons = cp.get_buttons(self.path)
            if new_buttons is not None:
                ret.extend(new_buttons)
        return ret
    
    def pre_button_run(self, button):
        if button.promise is not None:
            data = button.data
            if data is None:
                data = {}
            data["COMMS_ORIGIN_ID"] = self.origin_id
            data["COMMS_SELECTED_ID"] = self.selected_id
            data["COMMS_LIFEFORM_ID"] = self.comms_badge
            button.data = data
        return super().pre_button_run(button)
    def post_button_run(self, button):
        return super().post_button_run(button)
    
    def set_comms_badge(self, comms_badge):
        self.comms_badge = query.to_id(comms_badge)



from .execution import AWAIT, task_all, labels_get_type
################
## This is a PyMAST label used to run comms
def create_comms_label():
    try:
        c = comms()
        yield AWAIT(c)
    except Exception as e:
        print ("COMMS Exception")

def create_grid_comms_label():
    try:
        c = comms()
        c.path_root = "comms/grid"
        c.path = "comms/grid"
        c.is_grid_comms = True
        yield AWAIT(c)
    except Exception as e:
        print ("COMMS, grid Exception")

__comms_promises = {}
def start_comms_common_selected(event, is_grid):
    # Don't run if the selection doesn't exist
    if event.origin_id == 0:
        return
    
    so = to_object(event.selected_id)
    if event.selected_id != 0 and so is None:
        return
    
    # Don't run if the selection doesn't exist
    if event.origin_id !=0 and to_object(event.origin_id) is None:
        return
    
    #
    # If we're already running
    #
    #
    test = (event.origin_id, event.selected_id)
    promise_task = __comms_promises.get(test)
    if promise_task is not None:
        #
        # This is not expected to be called
        #
        print ("__COMMS_PROMISE creation already exists")
        return promise_task
    
    

    console = "COMMS"
    point = None
    if event.selected_id == 0:
        point = FrameContext.context.sbs.vec3()
        point.x = event.source_point.x
        point.y = event.source_point.y
        point.z = event.source_point.z
    
    data = {
                f"{console}_POINT": event.source_point,
                f"EVENT": event,
                f"{console}_ROUTED": True
    }
    

    if event.origin_id:
        data[f"{console}_ORIGIN_ID"] = event.origin_id
        data[f"{console}_ORIGIN"] = to_object(event.origin_id)
    else:
        data[f"{console}_ORIGIN_ID"] = 0
        data[f"{console}_ORIGIN"] = None

    if event.parent_id:
        data[f"{console}_PARENT_ID"] = event.parent_id
        data[f"{console}_PARENT"] = to_object(event.parent_id)
    else:
        data[f"{console}_PARENT_ID"] = 0
        data[f"{console}_PARENT"] = None

    if event.selected_id:
        data[f"{console}_SELECTED_ID"] = event.selected_id
        data[f"{console}_SELECTED"] = to_object(event.selected_id)
    else:
        data[f"{console}_SELECTED_ID"] = 0
        data[f"{console}_SELECTED"] = None
        # Only point selections can have a NONE
    #
    #
    #
    #
    task = FrameContext.server_task
    #
    # May need a null label
    #
    label = create_comms_label
    if is_grid:
        label = create_grid_comms_label
    t = task.start_task(label, data, inherit=False, defer=True)
    #
    restore_task =  FrameContext.task
    restore_page =  FrameContext.page

    path_labels = []
    if is_grid:
        path_labels = labels_get_type("enable/grid/comms")
    else:
        path_labels = labels_get_type("enable/comms")
    #
    # Run all the valid enables
    #

    FrameContext.task = t
    FrameContext.page= t.main.page
    p = task_all(*path_labels, data=data, sub_tasks=True)

    p.poll()
    #
    # This could get into a lock
    # but the expectation is this runs in one pass
    #
    count = 0
    while not p.done():
        p.poll()

        if p.is_idle:
            break

        if count > 100000:
            print(f"Comms enables caused hang build")
            break
        count += 1

    legit = False
    for r in p.result():
        if r != PollResults.FAIL_END:
            legit = True
            break
    if legit == False:
        t.end()
        FrameContext.task = restore_task
        FrameContext.page = restore_page
        return
    
    #
    # After all the sub task have run, NOW the 
    # actual task can run
    #
    __comms_promises[test] = t
    t.tick_in_context()

    FrameContext.task = restore_task
    FrameContext.page = restore_page

    return t

    
def start_comms_selected(event):
    return start_comms_common_selected(event, False)
    
ConsoleDispatcher.add_default_select("comms_target_UID", start_comms_selected)
ConsoleDispatcher.add_default_message("comms_target_UID", start_comms_selected)


def start_grid_comms_selected(event):
    return start_comms_common_selected(event, True)


ConsoleDispatcher.add_default_select("grid_selected_UID", start_grid_comms_selected)
ConsoleDispatcher.add_default_message("grid_selected_UID", start_grid_comms_selected)



@awaitable
def comms(path=None, buttons=None, timeout=None) -> CommsPromise:
    """Present the comms buttons. and wait for a choice.
    The timeout can be any promise, but typically is a made using the timeout function.

    Args:
        buttons (dict, optional): An dict of button dat key = button properties value label to process button press
        timeout (Promise, optional): The comms will end if this promise finishes. Defaults to None.

    Returns:
        Promise: A Promise that finishes when a comms button is selected
    """
    # 
    # This should be running on the server task    
    task = FrameContext.task
    if task.main.client_id != 0:
        raise Exception("Comms is not on Server")
    ret = CommsPromise(path, task, timeout)
    task.set_variable("BUTTON_PROMISE", ret)

    if buttons is not None:
        for k in buttons:
            # The + makes the button sticky
            ret .buttons.append(Button(k, "+", label=buttons[k],loc=0))
        
    return ret


def comms_add_button(message, label=None, color=None, data=None, path=None) -> None:
    p = ButtonPromise.navigating_promise
    if p is None:
        return
    if path is not None:
        # makes sure path starts with //comms
        path = path.strip("'//")
        if not path.startswith("comms"):
            path = "//comms/" + path
        else:
            path = "//"+path

    p.add_nav_button(Button(message, "+", color=color, label=label, data=data, new_task=True, path=path, loc=0))

def comms_info_face_override(face=None) -> None:    
    task = FrameContext.task
    p = task.get_variable("BUTTON_PROMISE")
    if p is None:
        return
    p.set_face_override(face)


def comms_navigate(path, face=None, comms_badge=None) -> None:
    """ Change the comms path for what buttons to present

    Args:
        path (str): _description_
        face (str, optional): _description_. Defaults to None.
    """
    task = FrameContext.task
    p = task.get_variable("BUTTON_PROMISE")
    if p is None:
        return
    
    if path is None or path == "":
        path = p.path_root

    # makes sure path starts with //comms
    path = path.strip("'//")
    if not path.startswith("comms"):
        path = "//comms/" + path
    else:
        path = "//"+path

    
    p.set_path(path)
    p.set_face_override(face)
    p.set_comms_badge(comms_badge)


def comms_navigate_override(ids_or_obj, sel_ids_or_obj, path=None, path_must_match=True) -> None:
    """ Change the comms path for what buttons to present for specific comms 
    pair. You need the two things in the relationship.
    If the things are selected in comms, this is a way to refresh the buttons.
    If the code is in the comms for the things involved, just use comms_navigate
    This is for a non comms task

    Args:
        ids_or_obj(id| set| list): The id, set of ids, or list of objects of player ships
        sel_ids_or_obj(id| set| list): The id, set of ids, or list of objects of other ship
        path (str): if none it will use the current path
        path_must_match (bool): Typically the path must match to avoid player confusion
    """

    players = to_object_list(ids_or_obj)
    targets = to_object_list(sel_ids_or_obj)

    for p in players:
        for s in targets:
            if p is None or s is None:
                continue
            if p.id == 0 or s.id == 0:
                continue

            t = __comms_promises.get((p.id, s.id))
            if t is None:
                return
            prom = t.get_variable("BUTTON_PROMISE")
            if prom is None:
                return
            
            if path is None or path == "":
                path = prom.path

            # makes sure path starts with //comms
            path = path.strip("'//")
            if not path.startswith("comms"):
                path = "//comms/" + path
            else:
                path = "//"+path

            if (path_must_match and path.strip("//")==prom.path) or not path_must_match:
                prom.set_path(path)
            


from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.helpers import FrameContext
from sbs_utils.procedural.query import to_object, get_comms_selection, to_object_list
from sbs_utils.procedural.roles import role_are_allies
from sbs_utils.vec import Vec3
import sbs

def comms_set_2dview_focus(client_id, focus_id=0, EVENT=None):
    if focus_id is None:
        return
    
    follow = get_inventory_value(client_id, "2d_follow")
    on_ship =  sbs.get_ship_of_client(client_id)
    set_inventory_value(client_id, "2dview_alt_ship", focus_id)
    set_inventory_value(on_ship, "2dview_alt_ship", focus_id)
    
    set_id = focus_id
    if not follow:
        set_id = 0

    previous = get_inventory_value(client_id, "2dview_alt_ship_prev", 0)
    if previous != set_id:
        sbs.assign_client_to_alt_ship(client_id, set_id)
        set_inventory_value(client_id, "2dview_alt_ship_prev", set_id)
    

    # ###### UPDATE NAVAREAS
    # on_ship =  sbs.get_ship_of_client(client_id)
    # alt_ship = focus_id
    # sim = FrameContext.context.sim
    # if alt_ship == 0:
    #     del_ships = [on_ship]
    # else:
    #     del_ships = [alt_ship, on_ship]

    # ## Remember selection defaults
    # selected_id = get_comms_selection(on_ship)
    # selected_id = get_inventory_value(alt_ship, "ORDERS_SELECTED_OBJECT", None )
    # source_point = get_inventory_value(alt_ship, "ORDERS_SELECTED_POINT", None)
    # if EVENT is not None:
    #     selected_id = EVENT.selected_id
    #     source_point = Vec3(EVENT.source_point)
    
    # #
    # # Delete the Nav areas here
    # #  Then create then if needed
    # for this_ship in del_ships:
    #     set_inventory_value(this_ship, "ORDERS_SELECTED_POINT", None)
    #     set_inventory_value(this_ship, "ORDERS_SELECTED_OBJECT", None)
    #     nav_id = get_inventory_value(this_ship, "ORDERS_SELECTED_NAV", None)
    #     if nav_id is not None:
    #         sim.delete_navpoint_by_id(nav_id)

    
    # if alt_ship == 0:
    #     return
    # alt_ship_obj = to_object(alt_ship)
    # if alt_ship_obj is None:
    #     return

    # if not role_are_allies(on_ship, alt_ship):
    #     return
    
    # if get_inventory_value(alt_ship, "give_orders_type", None) is None:
    #     return
    
    # # Now the event is important 
    # nav_color = "#444"
    # if selected_id != 0 and selected_id is not None:
    #     _sel_ship = to_object(selected_id)
    #     if _sel_ship is None:
    #         return
        
    #     pos = source_point
    #     set_inventory_value(alt_ship, "ORDERS_SELECTED_POINT", None)
    #     #set_inventory_value(alt_ship, "ORDERS_SELECTED_ID", EVENT.selected_id)
    #     pos = Vec3(_sel_ship.pos)
    #     set_inventory_value(alt_ship, "ORDERS_SELECTED_POINT", pos)
    #     set_inventory_value(alt_ship, "ORDERS_SELECTED_OBJECT", selected_id)
    #     # Need to update
    #     set_inventory_value(on_ship, "ORDERS_SELECTED_OBJECT", selected_id)
    

    #     size = 1000
    #     nav_color = "#044"
    #     nav_name = f"^^^^^^Order Object^for {alt_ship_obj.name}"
    
    #     x = pos.x
    #     y = pos.y
    #     z = pos.z

    # elif source_point is not None:
    #     set_inventory_value(alt_ship, "ORDERS_SELECTED_POINT", Vec3(source_point))
    #     set_inventory_value(alt_ship, "ORDERS_SELECTED_OBJECT", None)
    #     x = source_point.x
    #     # Same plan as ship
    #     y = alt_ship_obj.pos.y # EVENT.source_point.y
    #     z = source_point.z
    #     size = 400
    #     nav_color = "#00a"
    #     nav_name = f"^^^Order Waypoint^for {alt_ship_obj.name}"
    # else:
    #     return
    
    # # Create/update nav point
    # # On both the alt_ship and on_ship
    # for this_ship in [alt_ship, on_ship]:
    #     y = z
    #     nav_id = sim.add_navarea(x-size, y-size,x+size, y-size,x-size, y+size,x+size, y+size, nav_name, nav_color)
    #     #nav_id = sim.add_navpoint(x, y, z, nav_name, "#eee")
    #     nav = sim.get_navpoint_by_id(nav_id)
    #     nav.visibleToShip = this_ship
    #     set_inventory_value(this_ship, "ORDERS_SELECTED_NAV", nav_id)

class CommsChoiceButtonPromise(Promise):
    def __init__(self, buttons, path, nav_button):
        super().__init__()
        self.buttons = []
        for button in buttons:
            self.buttons.append(Button(button,"+", promise=self))
        self.path = path.strip("/")
        self.path_root = self.path
        if nav_button:
            self.path_root = self.path.rpartition('/')[0]
        self.nav_button = nav_button
        self.hosts = []
        self.origin_id = None
        self.selected_id = None

    def set_result(self, result):
        self._result = result
        for bp in self.hosts:
            bp.promise_buttons.remove(self)
            if bp.path == self.path:
                bp.set_path(self.path_root)


    def get_buttons(self, path):
        if path == self.path:
            return self.buttons
        if self.nav_button is not None and path == self.path_root:
            return [Button(self.nav_button,"+", path="//"+self.path)]
        return None


@awaitable
def comms_story_buttons(ids, sel_ids, buttons, path, nav_button=None) -> CommsChoiceButtonPromise:

    
    
    comms_promise = CommsChoiceButtonPromise(buttons, path, nav_button)
    players = to_object_list(ids)
    selects = to_object_list(sel_ids)
    for p in players:
        if p is None:
            continue
        for s in selects:
            if s is None:
                continue

            event = FakeEvent(0,origin_id=p.id, selected_id=s.id)
            promise_task = start_comms_selected(event)
            if promise_task is None:
                continue
            button_promise = promise_task.get_variable("BUTTON_PROMISE")
            if button_promise is None:
                continue
            button_promise.promise_buttons.append(comms_promise)
            comms_promise.hosts.append(button_promise)
    return comms_promise