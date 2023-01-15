from .mast import Mast, Scope
from .mastsbs import Role, Simulation, Target, Tell, Comms, Button, ButtonSet, Near,Broadcast
from .mastscheduler import MastScheduler, PollResults, MastRuntimeNode,  MastAsyncTask
import sbs
from .mastobjects import SpaceObject, MastSpaceObject, Npc, PlayerShip, Terrain

from ..consoledispatcher import ConsoleDispatcher
from ..gui import Gui
from .errorpage import ErrorPage
from .. import faces
from ..tickdispatcher import TickDispatcher
import sys
from .. import query

import traceback

class ButtonRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: Button):
        if node.await_node and node.await_node.end_await_node:
            task.jump(task.active_label,node.await_node.end_await_node.loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class ButtonSetRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: ButtonSet):
        if node.use is not None:
            return
        # the end node needs to format all the buttons at runtime
        if node.append:
            main_node = task.get_variable(node.name)
            # if main_node is None:
            #     task.set_value_keep_scope(node.name, node)    
            #     main_node = node
            for button in node.buttons:
                message=task.format_string(button.message)
                proxy = Button(message=message,proxy=True)
                proxy.code = button.code
                proxy.color = button.color
                proxy.loc = button.loc
                proxy.await_node = button.await_node
                proxy.sticky = True #button.sticky
                proxy.visited = None
                main_node.buttons.append(proxy)
        elif node.clear:
            proxy = ButtonSet(clear=True)
            proxy.loc = node.loc
            proxy.buttons = []
            proxy.use = None
            proxy.end = node.end
            self.name = node.name
            task.set_value_keep_scope(node.name, proxy)
        elif node.name is not None:
            task.set_value_keep_scope(node.name, node)
       
    def poll(self, mast:Mast, task:MastAsyncTask, node: ButtonSet):
        if node.end:
            task.jump(task.active_label,node.end.loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE


class TellRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Tell):
        to_so= task.get_variable(node.to_tag)
        self.face = ""
        self.title = ""
        to_so:SpaceObject = task.get_variable(node.to_tag)
        from_so:SpaceObject = task.get_variable(node.from_tag)
        if to_so is None or from_so is None:
            return
        # From face should be used
        self.title = from_so.comms_id +">"+to_so.comms_id
        self.face = faces.get_face(from_so.get_id())
        # Just in case swap if from is not a player
        if not from_so.is_player:
            swap = to_so
            to_so = from_so
            from_so = swap

        self.to_id = to_so.get_id()
        self.from_id = from_so.get_id()
    
        if self.face is None:
            self.face = ""

    def poll(self, mast:Mast, task:MastAsyncTask, node: Tell):

        if self.to_id and self.from_id:
            msg = task.format_string(node.message)
            #print(f"{self.from_id} {self.from_id} {node.color} {self.face} {self.title} {msg}")
            sbs.send_comms_message_to_player_ship(
                self.from_id,
                self.to_id,
                node.color,
                self.face, 
                self.title, 
                msg)
            return PollResults.OK_ADVANCE_TRUE
        else:
            PollResults.OK_ADVANCE_FALSE

class BroadcastRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Broadcast):
        self.to_ids = None
        if node.to_tag.startswith('*'):
            role = node.to_tag[1:]
            self.to_ids = SpaceObject.get_objects_with_role(role)
        elif node.to_tag=="SERVER":
            self.to_ids = [0]
        else:
            to_so= task.get_variable(node.to_tag, None)
            if to_so:
                self.to_ids = [to_so.get_id()]
            else:
                task.runtime_error(f"Broadcast has invalid TO {node.to_tag}")            
    
    def poll(self, mast:Mast, task:MastAsyncTask, node: Broadcast):
        if self.to_ids:
            for id in self.to_ids:
                print(f"Broadcasting id {id}")
                obj = SpaceObject.get(id)
                if obj is not None:
                    task.set_value("broadcast_target", obj)
                    msg = task.format_string(node.message)
                    sbs.send_message_to_player_ship(id, node.color, msg)

        return PollResults.OK_ADVANCE_TRUE

class CommsRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Comms):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = task.main.get_seconds("sim")+ (node.minutes*60+node.seconds)

        self.tag = None
        self.buttons = node.buttons
        self.button = None
        self.task = task
        self.color = node.color if node.color else "white"

        to_so:SpaceObject = task.get_variable(node.to_tag)
        from_so:SpaceObject = task.get_variable(node.from_tag)
        if to_so is None or from_so is None:
            return
        # Just in case swap if from is not a player
        if not from_so.is_player:
            swap = to_so
            to_so = from_so
            from_so = swap

        self.to_id = to_so.get_id()
        self.from_id = from_so.get_id()
        self.comms_id = to_so.comms_id
        self.face = faces.get_face(to_so.id) 
        
        ConsoleDispatcher.add_select_pair(self.from_id, self.to_id, 'comms_target_UID', self.comms_selected)
        ConsoleDispatcher.add_message_pair(self.from_id, self.to_id,  'comms_target_UID', self.comms_message)
        self.set_buttons(self.to_id, self.from_id)
        # from_so.face_desc

    def comms_selected(self, sim, an_id, event):
        to_id = event.origin_id
        from_id = event.selected_id
        self.set_buttons(from_id, to_id)

    def set_buttons(self, from_id, to_id):
        # check to see if the from ship still exists
        if from_id is not None:
            sbs.send_comms_selection_info(to_id, self.face, self.color, self.comms_id)
            for i, button in enumerate(self.buttons):
                value = True
                color = "blue" if button.color is None else button.color
                if button.code is not None:
                    value = self.task.eval_code(button.code)
                if value and button.should_present((from_id, to_id)):
                    msg = self.task.format_string(button.message)
                    sbs.send_comms_button_info(to_id, color, msg, f"{i}")

    def comms_message(self, sim, message, an_id, event):
        ### These are opposite from selected??
        from_id =self.from_id
        to_id = self.to_id
        self.button = int(event.sub_tag)
        this_button: Button = self.buttons[self.button]
        this_button.visit((from_id, to_id))
        self.task.tick()


    def leave(self, mast:Mast, task:MastAsyncTask, node: Comms):
        ConsoleDispatcher.remove_select_pair(self.from_id, self.to_id, 'comms_target_UID')
        ConsoleDispatcher.remove_message_pair(self.from_id, self.to_id, 'comms_target_UID')
        sbs.send_comms_selection_info(self.from_id, self.face, self.color, self.comms_id)
        if node.assign is not None:
            task.set_value_keep_scope(node.assign, self.button)
        

    def poll(self, mast:Mast, task:MastAsyncTask, node: Comms):
        if len(node.buttons)==0:
            # clear the comms buttons
            print("CHOOSE no but")
            return PollResults.OK_ADVANCE_TRUE

        if self.button is not None:
            print("CHOOSE selection")
            button = self.buttons[self.button] 
            self.button = None
            task.jump(task.active_label,button.loc+1)
            return PollResults.OK_JUMP

        if self.timeout is not None and self.timeout <= task.main.get_seconds("sim"):
            print("CHOOSE timeout")
            if node.timeout_label:
                task.jump(task.active_label,node.timeout_label.loc+1)
                return PollResults.OK_JUMP
            elif node.end_await_node:
                task.jump(task.active_label,node.end_await_node.loc+1)
                return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN

class TargetRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Target):
        to_so:SpaceObject = task.get_variable(node.to_tag)
        self.to_id = to_so.get_id() if to_so else None
        from_so:SpaceObject = task.get_variable(node.from_tag)
        self.from_id = from_so.get_id() if from_so else None



    def poll(self, mast, task, node:Target):
        if self.to_id:
            obj:SpaceObject = SpaceObject.get(self.from_id)
            query.target(task.main.sim, obj, self.to_id, not node.approach)
        else:
            obj:SpaceObject = SpaceObject.get(self.from_id)
            query.clear_target(task.main.sim, obj)

        return PollResults.OK_ADVANCE_TRUE


class NearRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Near):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = task.main.get_seconds("sim")+ (node.minutes*60+node.seconds)

        self.tag = None

        to_so:SpaceObject = task.get_variable(node.to_tag)
        if to_so:
            self.to_id = to_so.get_id()
        from_so:SpaceObject = task.get_variable(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()

    def poll(self, mast:Mast, task:MastAsyncTask, node: Near):
        # Need to check the distance
        dist = sbs.distance_id(self.to_id, self.from_id)
        if dist <= node.distance:
            return PollResults.OK_ADVANCE_TRUE

        if self.timeout is not None and self.timeout <= task.main.get_seconds("sim"):
            if node.timeout_label:
                task.jump(task.active_label,node.timeout_label.loc+1)
                return PollResults.OK_JUMP
            elif node.end_await_node:
                task.jump(task.active_label,node.end_await_node.loc+1)
                return PollResults.OK_JUMP

        return PollResults.OK_RUN_AGAIN


class SimulationRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: Simulation):
        match node.cmd:
            case "create":
                sbs.create_new_sim()
            case "pause":
                sbs.pause_sim()
            case "resume":
                sbs.resume_sim()

        return PollResults.OK_ADVANCE_TRUE

class RoleRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: Role):
        py_object = task.get_variable(node.name)
        if py_object is None:
            return
        match node.cmd:
            case "add":
                for role in node.roles:
                    py_object.add_role(role)
            case "remove":
                for role in node.roles:
                    py_object.remove_role(role)
            

        return PollResults.OK_ADVANCE_TRUE

        

over =     {
      "Comms": CommsRuntimeNode,
      "Tell": TellRuntimeNode,
      "Broadcast": BroadcastRuntimeNode,
      "Near": NearRuntimeNode,
      "Target": TargetRuntimeNode,
      "Button": ButtonRuntimeNode,
      "ButtonSet": ButtonSetRuntimeNode,
      "Simulation": SimulationRuntimeNode
    }


Mast.globals["SpaceObject"] =MastSpaceObject
Mast.globals["script"] = sys.modules['script']
for func in [
        # query sets
        query.role,
        query.has_inventory,
        query.has_link,
        query.inventory_set,
        query.inventory_value,
        query.linked_to,
        query.broad_test,
        # resolvers
        query.closest_list,
        query.closest,
        query.target,
        query.target_pos,
        query.clear_target,
        query.closest_object,
        query.random_object,
        query.random_object_list,
        query.to_py_object_list,
        query.link,
        query.unlink,
        query.to_id_list,
        query.to_object_list,
        query.to_id,
        query.to_object,
        query.get_dedicated_link,
        query.set_dedicated_link,
        query.get_inventory_value,
        query.set_inventory_value,
        query.object_exists,
        query.has_role,
        query.add_role,
        query.remove_role,
        ############################
        ## sbs
        sbs.distance_id

    ]:
    Mast.globals[func.__name__] = func



class MastSbsScheduler(MastScheduler):
    def __init__(self, mast: Mast, overrides=None):
        if overrides:
            super().__init__(mast, over|overrides)
        else:
            super().__init__(mast,  over)
        self.sim = None
        self.vars["sbs"] = sbs
        # Create schedulable space objects
        self.vars["Npc"] = self.Npc
        self.vars["Terrain"] = self.Terrain
        self.vars["PlayerShip"] = self.PlayerShip


    def Npc(self):
        return Npc(self)
    def PlayerShip(self):
        return PlayerShip(self)
    def Terrain(self):
        return Terrain(self)

    def run(self, sim, label="main", inputs=None):
        self.sim = sim
        inputs = inputs if inputs else {}
        super().start_task( label, inputs)

    def sbs_tick_tasks(self, sim):
        self.sim = sim
        return super().tick()

    def get_seconds(self, clock):
        if clock == "sim":
            return TickDispatcher.current/TickDispatcher.tps
        return super().get_seconds(clock)


    def runtime_error(self, message):
        sbs.pause_sim()
        message += traceback.format_exc()
        Gui.push(self.sim, 0, ErrorPage(message))

