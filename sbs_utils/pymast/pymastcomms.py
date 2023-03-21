
from ..consoledispatcher import ConsoleDispatcher
import sbs
import inspect
from . import PollResults
from ..engineobject import EngineObject
from .. import faces


class PyMastComms:
    def __init__(self, task, player_id, npc_id_or_filter, buttons ) -> None:
        self.buttons = buttons
        # if the npc is None or a filter function it is a more general scan
        if inspect.isfunction(npc_id_or_filter) or inspect.ismethod(npc_id_or_filter) or npc_id_or_filter is None:
            self.filter_npc = npc_id_or_filter
            ConsoleDispatcher.add_select(player_id, "comms_target_UID", self.selected)
            ConsoleDispatcher.add_message(player_id, "comms_target_UID", self.message)
        else:
            ConsoleDispatcher.add_select_pair(player_id, npc_id_or_filter, "comms_target_UID", self.selected)
            ConsoleDispatcher.add_message(player_id, npc_id_or_filter, "comms_target_UID", self.message)
        self.task = task
        self.event = None
        self.done = False

        
    def selected(self, sim, _ , event):
        if self.filter_npc and not self.filter_npc(event.selected_id):
            return
        
        player_so = EngineObject.get(event.origin_id)
        npc_so = EngineObject.get(event.selected_id)

        if player_so is None or npc_so is None:
            return
        npc_comms_id = npc_so.comms_id
        face_text = faces.get_face(event.selected_id)
        sbs.send_comms_selection_info(event.origin_id, face_text, "white", npc_comms_id)
        i = 0
        for button, data in self.buttons.items():
            color = "white"
            if isinstance(data, tuple):
                color = data[0]
            sbs.send_comms_button_info(event.origin_id, color, button, f"comms:{i}")
            i+=1

    
    def message(self, sim, message, player_id, event):
        if self.filter_npc and not self.filter_npc(event.selected_id):
            return

        if not message.startswith("comms:") or len(message)<7:
            return
        self.event = event
        button = int(message[6:])
        if button<len(self.buttons):
            button_func = list(self.buttons.values())[button]
            if isinstance(button_func, tuple):
                button_func = button_func[1]
            if button_func:
                if inspect.isfunction(button_func):
                    def pusher(story):
                        gen = button_func(self.task.story, self)
                        if gen is not None:
                            for res in gen:
                                yield res
                        story.pop()
                    self.story.push(pusher)
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
                        story.pop()
                    self.task.story.push(pusher)
        self.done = True

    def have_other_tell_player(self, text, color=None, face=None, comms_id=None):
        # Messge from NPC
        if face is None:
            face = faces.get_face(self.event.selected_id)
        if comms_id is None:
            npc_so = EngineObject.get(self.event.selected_id)
            comms_id = npc_so.comms_id
        if color is None:
            color = "gray"
        sbs.send_comms_message_to_player_ship(self.event.origin_id, self.event.selected_id, color, face, 
                comms_id,  text)
        
    def have_player_tell_other(self, text, color=None, face=None, comms_id=None):
        # Messge from player
        if face is None:
            face = faces.get_face(self.event.origin_id)
        if comms_id is None:
            so = EngineObject.get(self.event.origin_id)
            comms_id = so.comms_id
        if color is None:
            color = "gray"
        sbs.send_comms_message_to_player_ship(self.event.origin_id, self.event.selected_id, 
                color, face, 
                comms_id,  text)
    def get_player(self):
            return EngineObject.get(self.event.origin_id)
    def get_other(self):
            return EngineObject.get(self.event.origin_id)


    def run(self):    
        while self.done == False:
            yield PollResults.OK_RUN_AGAIN
        
