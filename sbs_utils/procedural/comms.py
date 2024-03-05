from . import query 
from .inventory import get_inventory_value
from .roles import has_role
from .. import faces
from ..agent import Agent
from ..helpers import FrameContext
from ..mast.mastscheduler import ChangeRuntimeNode
from ..mast.pollresults import PollResults
from ..mast.mast import Button
import sbs

def comms_broadcast(ids_or_obj, msg, color="#fff"):
    """Send text to the text waterfall
    The ids can be player ship ids or client/console ids

    Args:
        ids_or_obj (id or objecr): A set or single id or object to send to, 
        msg (str): The text to send
        color (str, optional): The Color for the text. Defaults to "#fff".
    """    
    if ids_or_obj is None:
        # default to the 
        ids_or_obj = FrameContext.context.event.parent_id

    _ids = query.to_id_list(ids_or_obj)
    if _ids:
        for id in _ids:
            if query.is_client_id(id):
                sbs.send_message_to_client(id, color, msg)
            else:
                # Just verify the id
                obj = Agent.get(id)
                if obj is not None or id==0:
                    sbs.send_message_to_player_ship(id, color, msg)

def comms_message(msg, from_ids_or_obj, to_ids_or_obj, title=None, face=None, color="#fff", title_color=None):
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
    if to_ids_or_obj is None:
        # internal message
        to_ids_or_obj = from_ids_or_obj
    if title_color is None:
        title_color = color
    if FrameContext.task:
        msg = FrameContext.task.compile_and_format_string(msg)
    
    from_objs = query.to_object_list(from_ids_or_obj)
    to_objs = query.to_object_list(to_ids_or_obj)
    for from_obj in from_objs:
        for to_obj in to_objs:
            # From face should be used
            if not title:
                title = from_obj.comms_id +" > "+to_obj.comms_id
                face = faces.get_face(from_obj.get_id())

            if face is None:
                face = ""
            # Only player ships send messages
            if has_role(from_obj.id, "__PLAYER__"):
                sbs.send_comms_message_to_player_ship(
                    from_obj.id,
                    to_obj.id,
                    face, 
                    title,
                    title_color, 
                    msg,
                    color)
            else:
                sbs.send_comms_message_to_player_ship(
                    to_obj.id,
                    from_obj.id,
                    face, 
                    title, 
                    title_color,
                    msg,
                    color
                    )

def _comms_get_origin_id():
    #
    # Event 
    #
    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "press_comms_button":
            return FrameContext.context.event.origin_id
    #
    # 
    #
    if FrameContext.task is not None:
        return FrameContext.task.get_variable("COMMS_ORIGIN_ID")

def _comms_get_selected_id():
    #
    # Event 
    #
    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "press_comms_button":
            return FrameContext.context.event.selected_id
    
    if FrameContext.task is not None:
        return FrameContext.task.get_variable("COMMS_SELECTED_ID")



def comms_transmit(msg, title=None, face=None, color="#fff", title_color=None):
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
    comms_message(msg, from_ids_or_obj, to_ids_or_obj,  title, face, color, title_color)

def comms_receive(msg, title=None, face=None, color="#fff", title_color=None):
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
    comms_message(msg, from_ids_or_obj, to_ids_or_obj,  title, face, color, title_color)


def comms_transmit_internal(msg, ids_or_obj=None, to_name=None, title=None, face=None, color="#fff", title_color=None):
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
        if title is None:
            title = f"{ship.name} > {to_name}"
        if face is None and to_name is not None:
            # try to find a face
            face = get_inventory_value(ship.id, f"face_{to_name}", None)
        comms_message(msg, ship, ship,  title, face, color, title_color)


def comms_receive_internal(msg, ids_or_obj=None, from_name=None,  title=None, face=None, color="#fff", title_color=None):
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
        if title is None:
            title = f"{from_name} > {ship.name}"
        if face is None and from_name is not None:
            # try to find a face
            face = get_inventory_value(ship.id, f"face_{from_name}", None)
        comms_message(msg, ship, ship,  title, face, color, title_color)
        
        
def comms_info(name, face=None, color=None):
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
        #print("Comms Info escaped")
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
        #print("Comms Info grid")
        sbs.send_grid_selection_info(from_so.id, face, color, name)
    else:
        #print(f"Comms Info comms nn{name} i{from_so.id} f{face} c{color} n{comms_id}")
        sbs.send_comms_selection_info(from_so.id, face, color, name)



from ..consoledispatcher import ConsoleDispatcher
from .gui import ButtonPromise
class CommsPromise(ButtonPromise):
    def __init__(self, task, timeout=None) -> None:
        super().__init__(task, timeout)

        self.task = task
        self.button = None
        self.is_unknown = False
        self.color = "white"
        self.expanded_buttons = None

    def initial_poll(self):
        if self._initial_poll:
            return
        
        # Will Build buttons
        if self.expanded_buttons is None:
            self.expanded_buttons = self.get_expanded_buttons()
        self.show_buttons()
        super().initial_poll()

    def comms_message(self, event):
        #
        # Check to see if this was intended for us
        #
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return

        #
        # Set the client so it knows the selected console
        #
        self.run_focus = True
        this_button = int(event.sub_tag)
        self.event = event
        self.button = self.expanded_buttons[this_button]
        self.button.visit((self.origin_id, self.selected_id))
        self.clear()
        self.task.tick()
        


    def clear(self):
        if self.is_grid_comms:
            sbs.send_grid_selection_info(self.origin_id, self.face, self.color, self.comms_id)
        else:
            sbs.send_comms_selection_info(self.origin_id, self.face, self.color, self.comms_id)

    def leave(self):
        self.clear()
        if self.is_grid_comms:
            ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'grid_selected_UID')
            ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'grid_selected_UID')
        else:
            ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'comms_target_UID')
            ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'comms_target_UID')

        if self.assign is not None:
            self.task.set_value_keep_scope(self.assign, self.button)        

    def process_on_change(self):
        # Check for on change nodes
        #
        self.on_change = None
        if self.on_change is not None:
            self.on_change=[]
            # create proxies of the runtime node to test
            for change in self.on_change:
                rt = ChangeRuntimeNode()
                rt.enter(self.task.main.mast, self.task, change)
                self.on_change.append(rt)
    
    #
    # This 
    #
    def show_buttons(self):
        if len(self.expanded_buttons) == 0:
            return

        self.tag = None
        self.button = None
        self.event = None
        self.is_running = False
        #self.color = node.color if node.color else "white"
        # If this is the same ship it is known
        self.is_unknown = False

        self.selected_id = self.task.get_variable("COMMS_SELECTED_ID")
        self.origin_id = self.task.get_variable("COMMS_ORIGIN_ID")

        self.is_grid_comms = query.is_grid_object_id(self.selected_id)
        selected_so = query.to_object(self.selected_id)
        if selected_so is None:
            return
        
        self.comms_id = selected_so.comms_id
        self.face = faces.get_face(self.selected_id)
        

        selection = None
        if self.is_grid_comms:        
            ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'grid_selected_UID', self.comms_selected)
            ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'grid_selected_UID', self.comms_message)
            selection = query.get_grid_selection(self.origin_id)
        else:
            ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'comms_target_UID', self.comms_selected)
            ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'comms_target_UID', self.comms_message)
            selection = query.get_comms_selection(self.origin_id)

        if selection == self.selected_id:
            self.set_buttons(self.origin_id, selection)
        # from_so.face_desc

    def comms_selected(self, event):
        #
        # Check to see if this was intended for us
        #
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return

        # If the button block is running do not set the buttons
        if not self.is_running:
            origin_id = event.origin_id
            selected_id = event.selected_id
            self.set_buttons(origin_id, selected_id)
            self.run_focus = True

    def set_buttons(self, origin_id, selected_id):
        if self.selected_id != selected_id or \
            self.origin_id != origin_id:
            return
        
        # check to see if the from ship still exists
        if origin_id is not None:
            if self.is_grid_comms:
                sbs.send_grid_selection_info(origin_id, self.face, self.color, self.comms_id)
            elif origin_id == selected_id:
                sbs.send_comms_selection_info(origin_id, self.face, self.color, self.comms_id)
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
                
                if initial_scan is None or initial_scan =="":
                    sbs.send_comms_selection_info(origin_id, "", "white", "unknown")
                    self.is_unknown = True
                    return
                else:
                    sbs.send_comms_selection_info(origin_id, self.face, self.color, self.comms_id)

            
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
                        sbs.send_grid_button_info(origin_id, color, msg, f"{i}")
                    else:
                        sbs.send_comms_button_info(origin_id, color, msg, f"{i}")

    def poll(self):
        super().poll()
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
            self.is_unknown = (initial_scan is None or initial_scan == "")
            # It is now known
            #
            if not self.is_unknown:
                # if selected update buttons
                player_current_select = oo.data_set.get( "comms_target_UID",0)
                if player_current_select == self.selected_id:
                    self.set_buttons(self.origin_id, self.selected_id)
                return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN



def comms(buttons=None, timeout=None):
    """Present the comms buttons. and wait for a choice.
    The timeout can be any promise, but typically is a made using the timeout function.

    Args:
        buttons (dict, optional): An dict of button dat key = button properties value label to process button press
        timeout (Promise, optional): The comms will end if this promise finishes. Defaults to None.

    Returns:
        Promise: A Promise that finishes when a comms button is selected
    """    
    task = FrameContext.task
    ret = CommsPromise(task, timeout)
    if buttons is not None:
        for k in buttons:
            # The + makes the button sticky
            ret .buttons.append(Button(k, "+", label=buttons[k],loc=0))
        
    return ret


