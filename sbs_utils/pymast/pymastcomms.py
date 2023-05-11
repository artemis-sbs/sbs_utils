
from ..consoledispatcher import ConsoleDispatcher
import sbs
import inspect
from .pollresults import PollResults
from ..engineobject import EngineObject
from .. import faces


class PyMastComms:
    def __init__(self, task, buttons, origin_id, selected_id) -> None:
        self.buttons = buttons
        self.task = task
        self.done = False
        self.origin_id = origin_id
        self.selected_id = selected_id
        
        ConsoleDispatcher.add_select_pair(origin_id, selected_id, "comms_target_UID", self.selected)
        ConsoleDispatcher.add_message_pair(origin_id, selected_id, "comms_target_UID", self.message)
        # this initializes the buttons
        self.handled_selected(origin_id, selected_id)
        self.selected_id =  selected_id

    def stop(self):
        ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, "comms_target_UID")
        ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, "comms_target_UID")
        self.clear()
        self.done = True

    
    def selected(self, sim, _ , event):
        self.handled_selected(event.origin_id, event.selected_id)
        
    def handled_selected(self, origin_id, selected_id):
        self.selected_info(origin_id, selected_id)
        i = 0
        for button, data in self.buttons.items():
            color = "white"
            if isinstance(data, tuple):
                color = data[0]
            sbs.send_comms_button_info(origin_id, color, button, f"comms:{i}")
            i+=1

    def selected_info(self, origin_id, selected_id):
        player_so = EngineObject.get(origin_id)
        npc_so = EngineObject.get(selected_id)

        if player_so is None or npc_so is None:
            sbs.send_comms_selection_info(origin_id, None, "red", "static")
            return
        
        npc_comms_id = npc_so.comms_id
        face_text = faces.get_face(selected_id)
        sbs.send_comms_selection_info(origin_id, face_text, "white", npc_comms_id)
    
    def message(self, sim, message, player_id, event):
        if event.origin_id != self.origin_id:
            return
        
        if not message.startswith("comms:") or len(message)<7:
            return
        button = int(message[6:])

        if button<len(self.buttons):
            button_func = list(self.buttons.values())[button]
            if isinstance(button_func, tuple):
                button_func = button_func[1]
            if button_func:
                if inspect.isfunction(button_func):
                    def pusher(story):
                        print(f"BUTTON {button_func}")
                        gen = button_func(self.task.story, self)
                        if gen is not None:
                            for res in gen:
                                yield res
                        self.stop()
                        self.task.pop()
                    self.task.story.push(pusher)
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
                        self.task.pop()
                    self.task.story.push(pusher)



    def receive(self, text, color=None, face=None, comms_id=None):
        # Messge from NPC
        if face is None:
            face = faces.get_face(self.selected_id)
        if comms_id is None:
            npc_so = EngineObject.get(self.selected_id)
            comms_id = npc_so.comms_id
        if color is None:
            color = "gray"
        sbs.send_comms_message_to_player_ship(self.origin_id, self.selected_id, color, face, 
                comms_id,  text)
        
    def transmit(self, text, color=None, face=None, comms_id=None):
        # Message from player
        if face is None:
            face = faces.get_face(self.origin_id)
        if comms_id is None:
            so = EngineObject.get(self.origin_id)
            comms_id = so.comms_id
        if color is None:
            color = "gray"
        sbs.send_comms_message_to_player_ship(self.origin_id, self.selected_id, 
                color, face, 
                comms_id,  text)
    def get_origin(self):
            return EngineObject.get(self.origin_id)
    def get_selected(self):
            return EngineObject.get(self.selected_id)

    def clear(self):
        self.selected_info(self.origin_id, self.selected_id)
        
        
        

    def run(self):    
        while self.done == False:
           yield PollResults.OK_RUN_AGAIN
        
