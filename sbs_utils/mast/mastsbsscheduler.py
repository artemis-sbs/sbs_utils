from .mast import Mast, Scope
from .mastsbs import Simulation, Route, TransmitReceive, Tell, Comms, Button, Broadcast, ScanTab,ScanResult, Load
from .mastscheduler import MastScheduler, PollResults, MastRuntimeNode,  MastAsyncTask
import sbs
from .mastobjects import SpaceObject, MastSpaceObject, Npc, PlayerShip, Terrain, GridObject

from ..consoledispatcher import ConsoleDispatcher
from ..lifetimedispatcher import LifetimeDispatcher
from ..damagedispatcher import DamageDispatcher
from ..gui import Gui
from .errorpage import ErrorPage
from .. import faces
from ..tickdispatcher import TickDispatcher
import sys
import json
import re
from .. import query
from .. import scatter

from functools import partial


import traceback

class ButtonRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: Button):
        #task.redirect_pop_label(True)
        #return PollResults.OK_JUMP
        if node.await_node and node.await_node.end_await_node:
             #print(f"Button return {task.active_label} {node.await_node.end_await_node.loc+1}")

             task.jump(task.active_label,node.await_node.end_await_node.loc+1)
             return PollResults.OK_JUMP
            
        return PollResults.OK_ADVANCE_TRUE


class TransmitReceiveRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: TransmitReceive):
        face = ""
        title = ""
        selected_id = task.get_variable("COMMS_SELECTED_ID")
        origin_id = task.get_variable("COMMS_ORIGIN_ID")
        if node.transmit:
            to_so:SpaceObject = query.to_object(selected_id)
            from_so:SpaceObject = query.to_object(origin_id)
        else:
            to_so:SpaceObject = query.to_object(origin_id)
            from_so:SpaceObject = query.to_object(selected_id)
            

        if to_so is None or from_so is None:
            return
        
        # From face should be used
        if node.comms_string:
            title = task.format_string(node.comms_string)
        elif node.comms_var:
            title = task.get_variable(node.comms_var)
        else:
            title = from_so.comms_id +">"+to_so.comms_id

        if node.face_string:
            face = task.format_string(node.face_string)
        elif node.face_var:
            face = task.get_variable(node.face_var)
        else:
            face = faces.get_face(from_so.get_id())
    
        if face is None:
            face = ""
    
        msg = task.format_string(node.message)
        #print(f"{self.from_id} {self.from_id} {node.color} {self.face} {self.title} {msg}")
        sbs.send_comms_message_to_player_ship(
            origin_id,
            selected_id,
            node.color,
            face, 
            title, 
            msg)



class TellRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Tell):
        to_so= task.get_variable(node.to_tag)
        self.face = ""
        self.title = ""
        self.to_id = None
        self.from_id = None
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
        # 
        if node.to_tag=="SERVER":
            self.to_ids = [0]
        else:
            ship_id= query.to_id_list(task.get_variable(node.to_tag))
            if ship_id:
                self.to_ids = ship_id
            else:
                task.runtime_error(f"Broadcast has invalid TO {node.to_tag}")            
    
    def poll(self, mast:Mast, task:MastAsyncTask, node: Broadcast):
        if self.to_ids:
            for id in self.to_ids:
                #print(f"Broadcasting id {id}")
                #task.set_value("broadcast_target", obj)
                msg = task.format_string(node.message)
                if query.is_client_id(id):
                    sbs.send_message_to_client(id, node.color, msg)
                else:
                    # Just verify the id
                    obj = SpaceObject.get(id)
                    if obj is not None or id==0:
                        sbs.send_message_to_player_ship(id, node.color, msg)

        return PollResults.OK_ADVANCE_TRUE

class CommsInfoRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Comms):
        color = node.color if node.color else "white"
        to_so:SpaceObject = query.to_object(task.get_variable("COMMS_SELECTED_ID"))
        from_so:SpaceObject = query.to_object(task.get_variable("COMMS_ORIGIN_ID"))

        if to_so is None or from_so is None:
            return
        # Just in case swap if from is not a player
        if not from_so.is_player:
            swap = to_so
            to_so = from_so
            from_so = swap

        comms_id = to_so.comms_id
        if node.message:
            comms_id = task.format_string(node.message)
        face = faces.get_face(to_so.id) 
   
        sbs.send_comms_selection_info(from_so.id, face, color, comms_id)


class CommsRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Comms):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = task.main.get_seconds("sim")+ (node.minutes*60+node.seconds)

        self.tag = None
        self.button = None
        self.task = task
        self.is_running = False
        self.color = node.color if node.color else "white"

        buttons = []
        # Expand all the 'for' buttons
        for button in node.buttons:
            if button.__class__.__name__ != "Button":
                buttons.append(button)
            elif button.for_name is None:
                buttons.append(button)
            else:
                buttons.extend(self.expand(button, task))
        self.buttons = buttons


        # Origin is the player ship, selected is NPC/GridObject
        if node.selected_tag:
            selected_so:SpaceObject = query.to_object(task.get_variable(node.selected_tag))
        else:
            selected_so:SpaceObject = query.to_object(task.get_variable("COMMS_SELECTED_ID"))

        if node.origin_tag:
            origin_so:SpaceObject = query.to_object(task.get_variable(node.origin_tag))
        else:
            origin_so:SpaceObject = query.to_object(task.get_variable("COMMS_ORIGIN_ID"))


        if selected_so is None or origin_so is None:
            return
        # Just in case swap if from is not a player
        if not origin_so.is_player:
            swap = selected_so
            selected_so = origin_so
            origin_so = swap

        self.is_grid_comms = selected_so.is_grid_object
        self.selected_id = selected_so.get_id()
        self.origin_id = origin_so.get_id()
        self.comms_id = selected_so.comms_id
        self.face = faces.get_face(selected_so.id)

        if self.is_grid_comms:        
            ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'grid_selected_UID', self.comms_selected)
            ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'grid_selected_UID', self.comms_message)
        else:
            ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'comms_target_UID', self.comms_selected)
            ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'comms_target_UID', self.comms_message)
        self.set_buttons(self.origin_id, self.selected_id)
        # from_so.face_desc

    def comms_selected(self, sim, an_id, event):
        # If the button block is running do not set the buttons
        if not self.is_running:
            origin_id = event.origin_id
            selected_id = event.selected_id
            self.set_buttons(origin_id, selected_id)

    def set_buttons(self, origin_id, selected_id):
        
        # check to see if the from ship still exists
        if origin_id is not None:
            if self.is_grid_comms:
                sbs.send_grid_selection_info(origin_id, self.face, self.color, self.comms_id)
            else:
                sbs.send_comms_selection_info(origin_id, self.face, self.color, self.comms_id)
            for i, button in enumerate(self.buttons):
                value = True
                color = "blue" if button.color is None else button.color
                if button.code is not None:
                    value = self.task.eval_code(button.code)
                if value and button.should_present((origin_id, selected_id)):
                    msg = self.task.format_string(button.message)
                    if self.is_grid_comms:
                        sbs.send_grid_button_info(origin_id, color, msg, f"{i}")
                    else:
                        sbs.send_comms_button_info(origin_id, color, msg, f"{i}")

    def expand(self, button: Button, task: MastAsyncTask):
        buttons = []
        if button.for_code is not None:
            iter_value = task.eval_code(button.for_code)
            for data in iter_value:
                task.set_value(button.for_name, data, Scope.TEMP)
                clone = button.clone()
                clone.data = data
                clone.message = task.format_string(clone.message)
                buttons.append(clone)

        return buttons


    def comms_message(self, sim, message, an_id, event):
        ### These are opposite from selected??
        origin_id =self.origin_id
        selected_id = self.selected_id
        self.button = int(event.sub_tag)
        this_button: Button = self.buttons[self.button]
        this_button.visit((origin_id, selected_id))
        self.clear()
        self.task.tick()


    def clear(self):
        if self.is_grid_comms:
            sbs.send_grid_selection_info(self.origin_id, self.face, self.color, self.comms_id)
        else:
            sbs.send_comms_selection_info(self.origin_id, self.face, self.color, self.comms_id)

    def leave(self, mast:Mast, task:MastAsyncTask, node: Comms):
        self.clear()
        if self.is_grid_comms:
            ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'grid_selected_UID')
            ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'grid_selected_UID')
        else:
            ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'comms_target_UID')
            ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'comms_target_UID')

        if node.assign is not None:
            task.set_value_keep_scope(node.assign, self.button)
        

    def poll(self, mast:Mast, task:MastAsyncTask, node: Comms):
        if len(node.buttons)==0:
            # clear the comms buttons
            return PollResults.OK_ADVANCE_TRUE

        if self.button is not None:
            button = self.buttons[self.button] 
            self.button = None
            self.is_running = True
            if button.for_name:
                task.set_value(button.for_name, button.data, Scope.TEMP)
            task.jump(task.active_label,button.loc+1)
            return PollResults.OK_JUMP

        if self.timeout is not None and self.timeout <= task.main.get_seconds("sim"):
            if node.timeout_label:
                task.jump(task.active_label,node.timeout_label.loc+1)
                return PollResults.OK_JUMP
            elif node.end_await_node:
                task.jump(task.active_label,node.end_await_node.loc+1)
                return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN
    
class ScanRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Comms):
        self.button = None
        self.task = task
        self.tab = None
        self.node = node
        buttons = []
        # Expand all the 'for' buttons
        for button in node.buttons:
            if button.for_name is None:
                buttons.append(button)
            else:
                buttons.extend(self.expand(button, task))
        self.buttons = buttons

        # Check if this was caused by a routed select
        routed = task.get_variable("SCIENCE_ROUTED")
        if routed is not None:
            task.set_value_keep_scope("SCIENCE_ROUTED", False)
        if node.to_tag:
            to_so:SpaceObject = query.to_object(task.get_variable(node.to_tag))
        else:
            to_so:SpaceObject = query.to_object(task.get_variable("SCIENCE_SELECTED_ID"))

        if node.from_tag:    
            from_so:SpaceObject = query.to_object(task.get_variable(node.from_tag))
        else:
            from_so:SpaceObject = query.to_object(task.get_variable("SCIENCE_ORIGIN_ID"))

        if to_so is None or from_so is None:
            return
        # Just in case swap if from is not a player
        if not from_so.is_player:
            swap = to_so
            to_so = from_so
            from_so = swap

        self.to_id = to_so.get_id()
        self.from_id = from_so.get_id()
                ###############
        scan_tabs = ""
        if to_so is not None:
            for button in self.buttons:
                value = True
                if button.code is not None:
                    value = task.eval_code(button.code)
                if value:
                    msg = self.task.format_string(button.message).strip()
                    if msg != "scan":
                        if len(scan_tabs):
                            scan_tabs += " "
                        scan_tabs += msg
            to_so.update_engine_data(task.main.sim, {"scan_type_list":scan_tabs})

        
        ConsoleDispatcher.add_select_pair(self.from_id, self.to_id, 'science_target_UID', self.science_selected)
        ConsoleDispatcher.add_message_pair(self.from_id, self.to_id,  'science_target_UID', self.science_message)
        #self.set_buttons(self.to_id, self.from_id)
        # from_so.face_desc
        if routed:
            self.start_scan(task.main.sim, from_so.id, to_so.id, "scan")

    def science_selected(self, ctx, an_id, event):
        self.start_scan(ctx.sim, event.origin_id, event.selected_id, event.extra_tag)

    def start_scan(self, sim, origin_id, selected_id, extra_tag):
        so = query.to_object(origin_id)
        so_sel = query.to_object(selected_id)
        percent = 0.0
        if so.side == so_sel.side:
            percent = 0.90
        if so:
            so.update_engine_data(sim, {
                "cur_scan_ID": selected_id,
                "cur_scan_type": extra_tag,
                "cur_scan_percent": percent
            })

    # def set_buttons(self, from_id, to_id):
    #     # check to see if the from ship still exists
        

    def expand(self, button: ScanTab, task: MastAsyncTask):
        buttons = []
        if button.for_code is not None:
            iter_value = task.eval_code(button.for_code)
            for data in iter_value:
                task.set_value(button.for_name, data, Scope.TEMP)
                clone = button.clone()
                clone.data = data
                clone.message = task.format_string(clone.message)
                buttons.append(clone)
        return buttons


    def science_message(self, sim, message, an_id, event):
        ### These are opposite from selected??
        self.tab = event.extra_tag
        #print(f"science scanned {self.tab}")
        self.task.tick()


    def leave(self, mast:Mast, task:MastAsyncTask, node: Comms):
        ConsoleDispatcher.remove_select_pair(self.from_id, self.to_id, 'science_target_UID')
        ConsoleDispatcher.remove_message_pair(self.from_id, self.to_id, 'science_target_UID')
        

    def poll(self, mast:Mast, task:MastAsyncTask, node: Comms):
        if len(node.buttons)==0:
            # clear the comms buttons
            return PollResults.OK_ADVANCE_TRUE

        if self.tab is not None:
            for i, button in enumerate(self.buttons):
                 if task.format_string(button.message) == self.tab:
                    self.button = i
                    #print(f"science scanned {i}")
            so_player = query.to_object(self.from_id)
            if so_player:
                self.tab = so_player.side+self.tab
   
            task.set_value("__SCAN_TAB__", self,  Scope.TEMP)
            if self.button is not None:
                button = self.buttons[self.button] 
                self.button = None
                task.set_value(button.for_name, button.data, Scope.TEMP)
                task.jump(task.active_label,button.loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN

class ScanResultRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: ScanResult):
        scan = task.get_variable("__SCAN_TAB__")
        if scan is None:
            return
        
        msg = task.format_string(node.message)
        #print(f"{scan.tab} scan {msg}")
        so = query.to_object(scan.to_id)
        if so:
            so.update_engine_data(task.main.sim, {
                scan.tab: msg,
            })
        if scan.node.end_await_node:
                task.jump(task.active_label,scan.node.end_await_node.loc+1)
                return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN

class RegexEqual(str):
    def __eq__(self, pattern):
        return bool(re.search(pattern, self))

#
#
#

def handle_purge_tasks(ctx, so):
    """
    This will clear out all tasks related to the destroyed item
    """
    MastAsyncTask.stop_for_dependency(so.id)

LifetimeDispatcher.add_destroy(handle_purge_tasks)

class RouteRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: Route):
        def handle_dispatch(task, console, sim, an_id, event):
            # I it reaches this, there are no pending comms handler
            # Create a new task and jump to the routing label
            t = task.start_task(node.label, {
                    f"{console}_ORIGIN_ID": event.origin_id,
                    f"{console}_SELECTED_ID": event.selected_id,
                    f"EVENT": event,
                    f"{console}_ROUTED": True
            })
            MastAsyncTask.add_dependency(event.origin_id,t)
            MastAsyncTask.add_dependency(event.selected_id,t)

        def handle_spawn(sim, so):
            t = task.start_task(node.label, {
                    f"SPAWNED_ID": so.id,
                    f"SPAWNED_ROUTED": True
            })
            MastAsyncTask.add_dependency(so.id,t)


        def handle_spawn_grid(sim, so):
            t = task.start_task(node.label, {
                    f"SPAWNED_ID": so.id,
                    f"SPAWNED_ROUTED": True
            })
            MastAsyncTask.add_dependency(so.id,t)

        def handle_damage(ctx, event):
            # Need point? amount
            t = task.start_task(node.label, {
                    f"DAMAGE_SOURCE_ID": event.origin_id,
                    f"DAMAGE_TARGET_ID": event.selected_id,
                    f"DAMAGE_ORIGIN_ID": event.origin_id,
                    f"DAMAGE_SELECTED_ID": event.selected_id,
                    f"EVENT": event,
                    f"DAMAGE_ROUTED": True
            })
            MastAsyncTask.add_dependency(event.origin_id,t)
            MastAsyncTask.add_dependency(event.selected_id,t)
        
        def handle_damage_internal(ctx, event):
            # Need point? amount
            t= task.start_task(node.label, {
                    f"DAMAGE_SOURCE_ID": event.origin_id,
                    f"DAMAGE_TARGET_ID": event.origin_id,
                    f"DAMAGE_ORIGIN_ID": event.origin_id,
                    f"EVENT": event,
                    f"DAMAGE_ROUTED": True
            })
            MastAsyncTask.add_dependency(event.origin_id,t)
            MastAsyncTask.add_dependency(event.selected_id,t)

        match RegexEqual(node.route):
            case "comms\s+select":
                ConsoleDispatcher.add_default_select("comms_target_UID", partial(handle_dispatch, task, "COMMS"))
            
            case "science\s+select":
                ConsoleDispatcher.add_default_select("science_target_UID", partial(handle_dispatch, task, "SCIENCE"))

            case "grid\s+select":
                ConsoleDispatcher.add_default_select("grid_selected_UID", partial(handle_dispatch, task, "COMMS"))

            case "change\s+console":
                task.main.page.change_console_label = node.label

            case "grid\s+spawn":
                LifetimeDispatcher.add_spawn_grid(handle_spawn_grid)

            case "damage\s*source":
                DamageDispatcher.add_source(handle_damage)

            case "damage\s*target":
                DamageDispatcher.add_target(handle_damage)

            case "damage\s*internal":
                DamageDispatcher.add_any_internal(handle_damage_internal)

            case "spawn":
                LifetimeDispatcher.add_spawn(handle_spawn)

        return PollResults.OK_ADVANCE_TRUE



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



class LoadRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Load):
        content, errors = mast.content_from_lib_or_file(node.name, node.lib)
        if content is None:
            return
        
        match node.format:
            case "data":
                content = json.loads(content)
                self.process_data(content)
            case "map":
                content = json.loads(content)
                self.process_map(content)

    def process_data(self, content):
        pass

    def process_data(self, content):
        pass

        

over =     {
      "Route": RouteRuntimeNode,
      "Comms": CommsRuntimeNode,
      "CommsInfo": CommsInfoRuntimeNode,
      "TransmitReceive": TransmitReceiveRuntimeNode,
      "Tell": TellRuntimeNode,
      "Broadcast": BroadcastRuntimeNode,
      "Button": ButtonRuntimeNode,
      "Simulation": SimulationRuntimeNode,
      "Scan": ScanRuntimeNode,
      "Load": LoadRuntimeNode,
      "ScanResult": ScanResultRuntimeNode
    }


Mast.globals["SpaceObject"] =MastSpaceObject
Mast.globals["script"] = sys.modules['script']
for func in [
        ############################
        ## sbs
        sbs.distance_id,
        sbs.assign_client_to_ship
    ]:
    Mast.globals[func.__name__] = func


from .. import names
Mast.import_python_module('sbs_utils.query')
Mast.import_python_module('sbs_utils.faces')
Mast.import_python_module('sbs_utils.fs')
Mast.import_python_module('sbs_utils.scatter', 'scatter')
Mast.import_python_module('sbs_utils.names', 'names')
Mast.import_python_module('sbs', 'sbs')

class MastSbsScheduler(MastScheduler):
    def __init__(self, mast: Mast, overrides=None):
        if overrides:
            super().__init__(mast, over|overrides)
        else:
            super().__init__(mast,  over)
        self.sim = None
        self.vars["sbs"] = sbs
        # Create schedulable space objects
        self.vars["npc_spawn"] = self.npc_spawn
        self.vars["terrain_spawn"] = self.terrain_spawn
        self.vars["player_spawn"] = self.player_spawn
        self.vars["grid_spawn"] = self.grid_spawn


    def Npc(self):
        return Npc(self)
    def PlayerShip(self):
        return PlayerShip(self)
    def Terrain(self):
        return Terrain(self)
    
    def npc_spawn(self, x,y,z,name, side, art_id, behave_id):
        so = Npc(self)
        return so.spawn(self.sim, x,y,z,name, side, art_id, behave_id)
        
    def player_spawn(self, x,y,z,name, side, art_id):
        so = PlayerShip(self)
        return so.spawn(self.sim, x,y,z,name, side, art_id)
    def terrain_spawn(self, x,y,z,name, side, art_id, behave_id):
        so = Terrain(self)
        return so.spawn(self.sim, x,y,z,name, side, art_id, behave_id)
    
    def grid_spawn(self, id, name, tag, x,y, icon, color, roles):
        so = GridObject(self)
        
        return so.spawn(self.sim, id, name, tag, x,y, icon, color, roles)

    def run(self, ctx, label="main", inputs=None):
        self.sim = ctx.sim
        self.ctx = ctx
        inputs = inputs if inputs else {}
        super().start_task( label, inputs)

    def sbs_tick_tasks(self, ctx):
        self.sim = ctx.sim
        self.ctx = ctx
        return super().tick()

    def get_seconds(self, clock):
        if clock == "sim":
            return TickDispatcher.current/TickDispatcher.tps
        return super().get_seconds(clock)


    def runtime_error(self, message):
        sbs.pause_sim()
        message += traceback.format_exc()
        Gui.push(self.sim, 0, ErrorPage(message))

