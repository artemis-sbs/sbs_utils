
from ..consoledispatcher import ConsoleDispatcher
import sbs
import inspect
from .pollresults import PollResults
from ..engineobject import EngineObject
from .. import query
from .. import faces





def transmit(text, origin_id, selected_id, color=None, face=None, title=None):
    # Message from player
    if face is None:
        face = faces.get_face(origin_id)
    if title is None:
        origin_so = EngineObject.get(origin_id)
        npc_so = EngineObject.get(selected_id)
        if origin_so is not None and npc_so is not None:
            title = f"{origin_so.comms_id}>{npc_so.comms_id}"
        else:
            title = "unknown"
    if color is None:
        color = "gray"
    sbs.send_comms_message_to_player_ship(origin_id, selected_id, 
            color, face, 
            title,  text)
        
    
def receive(text, origin_id, selected_id, color=None, face=None, title=None):
    # Message from NPC
    if face is None:
        face = faces.get_face(selected_id)
    if title is None:
        origin_so = EngineObject.get(origin_id)
        npc_so = EngineObject.get(selected_id)
        if origin_so is not None and npc_so is not None:
            title = f"{npc_so.comms_id}>{origin_so.comms_id}"
        else:
            title = "unknown"
    if color is None:
        color = "gray"
    sbs.send_comms_message_to_player_ship(origin_id, selected_id, color, face, 
            title,  text)


class PyMastComms:
    def __init__(self, task, buttons, origin_id, selected_id) -> None:
        self.buttons = buttons
        self.task = task
        self.done = False
        self.origin_id = origin_id
        self.selected_id = selected_id

        console = "comms_target_UID" if query.is_space_object_id(self.selected_id) else "grid_selected_UID"
        ConsoleDispatcher.add_select_pair(origin_id, selected_id, console, self.selected)
        ConsoleDispatcher.add_message_pair(origin_id, selected_id, console, self.message)
        # this initializes the buttons
        self.handled_selected(origin_id, selected_id)
        
    def stop(self):
        console = "comms_target_UID" if query.is_space_object_id(self.selected_id) else "grid_selected_UID"
        ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, console)
        ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, console)
        self.clear()
        self.done = True

    
    def selected(self, _ , event):
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return

        self.task.EVENT = event
        self.handled_selected(event.origin_id, event.selected_id)
        
    def handled_selected(self, origin_id, selected_id):
        self.selected_info(origin_id, selected_id)
        i = 0
        for button, data in self.buttons.items():
            color = "white"
            if isinstance(data, tuple):
                color = data[0]
            if query.is_space_object_id(selected_id):
                sbs.send_comms_button_info(origin_id, color, button, f"comms:{i}")
            else:
                sbs.send_grid_button_info(origin_id, color, button, f"comms:{i}")
            i+=1

    def selected_info(self, origin_id, selected_id):
        player_so = EngineObject.get(origin_id)
        npc_so = EngineObject.get(selected_id)

        if player_so is None or npc_so is None:
            if query.is_space_object_id(selected_id):
                sbs.send_comms_selection_info(origin_id, None, "red", "static")
            else:
                sbs.send_grid_selection_info(origin_id, None, "red", "static")
            return
        
        npc_comms_id = npc_so.comms_id
        face_text = faces.get_face(selected_id)
        if query.is_space_object_id(selected_id):
            sbs.send_comms_selection_info(origin_id, face_text, "white", npc_comms_id)
        else:
            sbs.send_grid_selection_info(origin_id, face_text, "white", npc_comms_id)
    
    def message(self, message, player_id, event):
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return
        
        if not message.startswith("comms:") or len(message)<7:
            return
        button = int(message[6:])

        if button<len(self.buttons):
            button_func = list(self.buttons.values())[button]
            if isinstance(button_func, tuple):
                button_func = button_func[1]
            if button_func:
                self.selected_info(event.origin_id, event.selected_id)
                self.task.EVENT = event
                if inspect.isfunction(button_func):
                    def pusher(story):
                        # print(f"BUTTON {button_func}")
                        gen = button_func(self.task.story, self)
                        if gen is not None:
                            for res in gen:
                                yield res
                        self.stop()
                        yield self.task.pop()
                    self.task.push_jump_pop(pusher)
                elif inspect.ismethod(button_func):
                    ##############
                    ## This is some wild code
                    ## Schedule a inner function 
                    ## to automatically pop()
                    def pusher(story):
                        gen = button_func(self)
                        if gen is not None:
                            for res in gen:
                                yield res
                        self.stop()
                        yield self.task.pop()
                    self.task.push_jump_pop(pusher)




    def receive(self, text, color=None, face=None, title=None):
        receive(text, self.origin_id, self.selected_id, color, face, title)
        
    def transmit(self, text, color=None, face=None, title=None):
        transmit(text, self.origin_id, self.selected_id, color, face, title)
        
    @classmethod        
    def broadcast(self_cls, id, text, color=None):
        # Message from player
        if color is None:
            color = "gray"
        if query.is_client_id(id):
            sbs.send_message_to_client(id, color,  text)
        else:
            sbs.send_message_to_player_ship(id, color,  text)

        

    def get_origin(self):
            return EngineObject.get(self.origin_id)
    def get_selected(self):
            return EngineObject.get(self.selected_id)

    def clear(self):
        self.selected_info(self.origin_id, self.selected_id)
        
        
        

    def run(self):    
        while self.done == False:
            yield PollResults.OK_RUN_AGAIN
        yield PollResults.OK_ADVANCE_TRUE
        
