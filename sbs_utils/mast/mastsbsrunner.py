from .mast import Mast, Scope
from .mastsbs import Simulation, Target, Tell, Comms, Button, Near,Broadcast
from .mastrunner import MastRunner, PollResults, MastRuntimeNode,  MastAsync
import sbs
from ..spaceobject import SpaceObject
from ..consoledispatcher import ConsoleDispatcher
from ..gui import Gui
from .errorpage import ErrorPage
from .. import faces
from ..tickdispatcher import TickDispatcher

import traceback

class ButtonRunner(MastRuntimeNode):
    def poll(self, mast, thread, node: Button):
        if node.await_node and node.await_node.end_await_node:
            thread.jump(thread.active_label,node.await_node.end_await_node.loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class TellRunner(MastRuntimeNode):
    def enter(self, mast:Mast, thread:MastAsync, node: Tell):
        to_so= thread.get_value(node.to_tag, None)
        to_so = to_so[0]
        self.face = ""
        self.title = ""
        if to_so:
            self.to_id = to_so.get_id()
        else:
            thread.runtime_error("Tell has invalid TO")            
        from_so= thread.get_value(node.from_tag, None)
        from_so = to_so[0]
        if from_so:
            self.from_id = from_so.get_id()
            self.title = from_so.comms_id(thread.main.sim)
            self.face = faces.get_face(self.from_id)
            
        else:
            thread.runtime_error("Tell has invalid from")            

    def poll(self, mast:Mast, thread:MastAsync, node: Tell):

        if self.to_id and self.from_id:
            msg = node.message.format(**thread.get_symbols())
            sbs.send_comms_message_to_player_ship(
                self.to_id,
                self.from_id,
                node.color,
                self.face, self.title, msg)
            return PollResults.OK_ADVANCE_TRUE
        else:
            PollResults.OK_ADVANCE_FALSE

class BroadcastRunner(MastRuntimeNode):
    def enter(self, mast:Mast, thread:MastAsync, node: Broadcast):
        to_so= thread.get_value(node.to_tag, None)
        to_so = to_so[0]
        if to_so:
            self.to_id = to_so.get_id()
        else:
            thread.runtime_error(f"Broadcast has invalid TO {node.to_tag}")            
    
    def poll(self, mast:Mast, thread:MastAsync, node: Broadcast):
        if self.to_id:
            msg = thread.format_string(node.message)
            sbs.send_message_to_player_ship(self.to_id, node.color, msg)
            return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_ADVANCE_TRUE

class CommsRunner(MastRuntimeNode):
    def enter(self, mast:Mast, thread:MastAsync, node: Comms):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = TickDispatcher.current + (node.minutes*60+node.seconds)*TickDispatcher.tps

        print("CHOOSE")
        self.tag = None
        self.buttons = node.buttons
        self.button = None
        self.thread = thread
        self.color = node.color if node.color else "white"

        to_so:SpaceObject = thread.vars.get(node.to_tag)
        if to_so:
            self.to_id = to_so.get_id()
        from_so:SpaceObject = thread.vars.get(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()
            self.comms_id = from_so.comms_id(thread.main.sim)
            ConsoleDispatcher.add_select_pair(self.from_id, self.to_id, 'comms_targetUID', self.comms_selected)
            ConsoleDispatcher.add_message_pair(self.from_id, self.to_id,  'comms_targetUID', self.comms_message)
            self.set_buttons(self.from_id, self.to_id)
            # from_so.face_desc

    def comms_selected(self, sim, an_id, event):
        to_id = event.origin_id
        from_id = event.selected_id
        self.set_buttons(from_id, to_id)

    def set_buttons(self, from_id, to_id):
        # check to see if the from ship still exists
        if from_id is not None:
            from_face = faces.get_face(from_id) 
            if from_face is None:
                from_face = ""
            sbs.send_comms_selection_info(to_id, from_face, self.color, self.comms_id)
            for i, button in enumerate(self.buttons):
                value = True
                color = "blue" if button.color is None else button.color
                if button.code is not None:
                    value = self.thread.eval_code(button.code)
                if value and button.should_present((from_id, to_id)):
                    msg = self.thread.format_string(button.message)
                    sbs.send_comms_button_info(to_id, color, msg, f"{i}")

    def comms_message(self, sim, message, an_id, event):
        ### These are opposite from selected??
        from_id =self.from_id
        to_id = self.to_id
        self.button = int(event.sub_tag)
        this_button: Button = self.buttons[self.button]
        this_button.visit((from_id, to_id))
        self.thread.tick()


    def leave(self, mast:Mast, thread:MastAsync, node: Comms):
        ConsoleDispatcher.remove_select_pair(self.from_id, self.to_id, 'comms_targetUID')
        ConsoleDispatcher.remove_message_pair(self.from_id, self.to_id, 'comms_targetUID')
        sbs.send_comms_selection_info(self.to_id, "", self.color, self.comms_id)
        if node.assign is not None:
            thread.set_value_keep_scope(node.assign, self.button)
        

    def poll(self, mast:Mast, thread:MastAsync, node: Comms):
        if len(node.buttons)==0:
            # clear the comms buttons
            print("CHOOSE no but")
            return PollResults.OK_ADVANCE_TRUE

        if self.button is not None:
            print("CHOOSE selection")
            button = self.buttons[self.button] 
            self.button = None
            thread.jump(thread.active_label,button.loc+1)
            return PollResults.OK_JUMP

        if self.timeout is not None and self.timeout <= TickDispatcher.current:
            print("CHOOSE timeout")
            if node.timeout_label:
                thread.jump(thread.active_label,node.timeout_label.loc+1)
                return PollResults.OK_JUMP
            elif node.end_await_node:
                thread.jump(thread.active_label,node.end_await_node.loc+1)
                return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN

class TargetRunner(MastRuntimeNode):
    def enter(self, mast:Mast, thread:MastAsync, node: Target):
        to_so:SpaceObject = thread.vars.get(node.to_tag)
        self.to_id = to_so.get_id() if to_so else None
        from_so:SpaceObject = thread.vars.get(node.from_tag)
        self.from_id = from_so.get_id() if from_so else None


    def poll(self, mast, thread, node:Target):
        if self.to_id:
            obj:SpaceObject = SpaceObject.get(self.from_id)
            obj.target(thread.main.sim, self.to_id, not node.approach)
        else:
            obj:SpaceObject = SpaceObject.get(self.from_id)
            obj.clear_target(thread.main.sim)

        return PollResults.OK_ADVANCE_TRUE


class NearRunner(MastRuntimeNode):
    def enter(self, mast:Mast, thread:MastAsync, node: Near):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = TickDispatcher.current + (node.minutes*60+node.seconds)*TickDispatcher.tps

        self.tag = None

        to_so:SpaceObject = thread.vars.get(node.to_tag)
        if to_so:
            self.to_id = to_so.get_id()
        from_so:SpaceObject = thread.vars.get(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()

    def poll(self, mast:Mast, thread:MastAsync, node: Near):
        # Need to check the distance
        dist = sbs.distance_id(self.to_id, self.from_id)
        if dist <= node.distance:
            return PollResults.OK_ADVANCE_TRUE

        if self.timeout is not None and self.timeout <= TickDispatcher.current:
            if node.timeout_label:
                thread.jump(thread.active_label,node.timeout_label.loc+1)
                return PollResults.OK_JUMP
            elif node.end_await_node:
                thread.jump(thread.active_label,node.end_await_node.loc+1)
                return PollResults.OK_JUMP

        return PollResults.OK_RUN_AGAIN


class SimulationRunner(MastRuntimeNode):
    def poll(self, mast:Mast, thread:MastAsync, node: Simulation):
        match node.cmd:
            case "create":
                sbs.create_new_sim()
            case "pause":
                sbs.pause_sim()
            case "resume":
                sbs.resume_sim()

        return PollResults.OK_ADVANCE_TRUE

        

over =     {
      "Comms": CommsRunner,
      "Tell": TellRunner,
      "Broadcast": BroadcastRunner,
      "Near": NearRunner,
      "Target": TargetRunner,
#      "Simulation": SimulationRunner,
      "Button": ButtonRunner
    }

class MastSbsRunner(MastRunner):
    def __init__(self, mast: Mast, overrides=None):
        if overrides:
            super().__init__(mast, over|overrides)
        else:
            super().__init__(mast,  over)
        self.sim = None
        Mast.globals["sbs"] = sbs
        Mast.globals["SpaceObject"] =SpaceObject

    def run(self, sim, label="main", inputs=None):
        self.sim = sim
        inputs = inputs if inputs else {}
        super().start_thread( label, inputs)

    def sbs_tick_threads(self, sim):
        self.sim = sim
        return super().tick()

    def runtime_error(self, message):
        sbs.pause_sim()
        message += traceback.format_exc()
        Gui.push(self.sim, 0, ErrorPage(message))

