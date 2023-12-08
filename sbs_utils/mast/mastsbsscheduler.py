from .mast import Mast, Scope, Button
from .mastsbs import Comms
from .mastscheduler import MastScheduler, PollResults, MastRuntimeNode,  MastAsyncTask, ChangeRuntimeNode
import sbs
from .mastobjects import SpaceObject, MastSpaceObject

from ..consoledispatcher import ConsoleDispatcher
from ..lifetimedispatcher import LifetimeDispatcher
from ..gui import Gui
from .errorpage import ErrorPage
from .. import faces
from ..tickdispatcher import TickDispatcher
import sys

import re
from ..procedural import query
from ..procedural import links
from ..procedural import inventory

from .. import vec


import traceback



class CommsRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Comms):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = FrameContext.sim_seconds+ (node.minutes*60+node.seconds)

        #
        # Check for on change nodes
        #
        self.on_change = None
        if node.on_change is not None:
            self.on_change=[]
            # create proxies of the runtime node to test
            for change in node.on_change:
                rt = ChangeRuntimeNode()
                rt.enter(mast, task, change)
                self.on_change.append(rt)


        self.tag = None
        self.button = None
        self.task = task
        self.event = None
        self.is_running = False
        self.color = node.color if node.color else "white"
        # If this is the same ship it is known
        self.is_unknown = False
        self.run_focus = False
        
        
        
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

    def comms_selected(self, an_id, event):
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

            for i, button in enumerate(self.buttons):
                value = True
                color = "white" if button.color is None else button.color
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
                if clone.color is not None:
                    clone.color = task.format_string(clone.color)
                buttons.append(clone)

        return buttons


    def comms_message(self, message, an_id, event):
        #
        # Check to see if this was intended for us
        #
        if self.selected_id != event.selected_id or \
            self.origin_id != event.origin_id:
            return

        #
        # Set the client so it knows the selected console
        #
        self.button = int(event.sub_tag)
        self.event = event
        this_button: Button = self.buttons[self.button]
        this_button.visit((self.origin_id, self.selected_id))
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
        #
        # If the ship was unknown, but know is known
        #
        if self.is_unknown:
            oo = query.to_object(self.origin_id)
            so = query.to_object(self.selected_id)
            # Should the END?
            if oo is None or so is None:
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
            return PollResults.OK_RUN_AGAIN


        if self.button is not None:
            button = self.buttons[self.button] 
            self.button = None
            self.is_running = True
            if button.for_name:
                task.set_value(button.for_name, button.data, Scope.TEMP)
                self.clear()
            task.set_value("EVENT", self.event, Scope.TEMP)
            task.jump(task.active_label,button.loc+1)
            return PollResults.OK_JUMP

        if self.timeout is not None and self.timeout <= FrameContext.sim_seconds:
            if node.timeout_label:
                task.jump(task.active_label,node.timeout_label.loc+1)
                return PollResults.OK_JUMP
            elif node.end_await_node:
                task.jump(task.active_label,node.end_await_node.loc+1)
                return PollResults.OK_JUMP

        if self.on_change:
            for change in self.on_change:
                if change.test():
                    task.jump(task.active_label,change.node.loc+1)
                    return PollResults.OK_JUMP
        if node.focus and self.run_focus:
            self.run_focus = False
            task.push_inline_block(task.active_label,node.focus.loc+1)
            return PollResults.OK_JUMP


        if len(node.buttons)==0:
            # clear the comms buttons
            return PollResults.OK_ADVANCE_TRUE

        return PollResults.OK_RUN_AGAIN
    
# class ScanRuntimeNode(MastRuntimeNode):
#     def enter(self, mast:Mast, task:MastAsyncTask, node: Scan):
#         self.button = None
#         self.task = task
#         self.tab = None
#         self.node = node
#         self.event = None
#         ###############
#         # If this is the first scan only have the scan button
#         # Otherwise have them all
#         self.scan_is_done = False
#         buttons = []
#         # Expand all the 'for' buttons
#         for button in node.buttons:
#             if button.for_name is None:
#                 buttons.append(button)
#             else:
#                 buttons.extend(self.expand(button, task))
#         self.buttons = buttons

#         # Check if this was caused by a routed select
#         routed = task.get_variable("SCIENCE_ROUTED")
#         # if routed is None:
#         # Only roue once
#         task.set_value_keep_scope("SCIENCE_ROUTED", False)
#         if node.to_tag:
#             to_so:SpaceObject = query.to_object(task.get_variable(node.to_tag))
#         else:
#             to_so:SpaceObject = query.to_object(task.get_variable("SCIENCE_SELECTED_ID"))

#         if node.from_tag:    
#             from_so:SpaceObject = query.to_object(task.get_variable(node.from_tag))
#         else:
#             from_so:SpaceObject = query.to_object(task.get_variable("SCIENCE_ORIGIN_ID"))

#         if to_so is None or from_so is None:
#             return
#         # Just in case swap if from is not a player
#         if not from_so.is_player:
#             swap = to_so
#             to_so = from_so
#             from_so = swap

#         self.selected_id = to_so.get_id()
#         self.origin_id = from_so.get_id()

#         if to_so is not None:
#             scan_tab = from_so.side+"scan"
#             has_scan = to_so.data_set.get(scan_tab,0)
#             if has_scan is None:
#                 scan_tabs = "scan"
#                 self.scan_is_done = False
#             else:
#                 scan_tabs = ""
#                 scanned_tabs = 0
#                 button_count = 0
#                 for button in self.buttons:
#                     value = True
#                     if button.code is not None:
#                         value = task.eval_code(button.code)
#                     if value:
#                         button_count += 1
#                         msg = self.task.format_string(button.message).strip()
#                         if msg != "scan":
#                             if len(scan_tabs):
#                                 scan_tabs += " "
#                             scan_tabs += msg
#                         # Check if this has been scanned
#                         has_scan = to_so.data_set.get(from_so.side+msg, 0)
#                         if has_scan:
#                             scanned_tabs += 1
#                 self.scan_is_done = scanned_tabs == button_count
#                 to_so.data_set.set("scan_type_list", scan_tabs, 0)

        
#         ConsoleDispatcher.add_select_pair(self.origin_id, self.selected_id, 'science_target_UID', self.science_selected)
#         ConsoleDispatcher.add_message_pair(self.origin_id, self.selected_id,  'science_target_UID', self.science_message)
#         #self.set_buttons(self.to_id, self.from_id)
#         # from_so.face_desc
#         if routed:
#             event = task.get_variable("EVENT")
#             if event is not None:
#                 self.start_scan(from_so.id, to_so.id, event.extra_tag)
#             else:
#                 self.start_scan( from_so.id, to_so.id, "__init__")

#     def science_selected(self, an_id, event):
#         #
#         # avoid if this isn't for us
#         #
#         if self.origin_id != event.origin_id or \
#             self.selected_id != event.selected_id:
#             return
        
#         self.start_scan(event.origin_id, event.selected_id, event.extra_tag)

#     def start_scan(self, origin_id, selected_id, extra_tag):
#         #
#         # Check if this was initiated by a "Follow route"
#         #
#         if self.selected_id != selected_id or \
#             self.origin_id != origin_id:
#             return
#         if extra_tag == "__init__":
#             self.tab = extra_tag
#             return
#         so = query.to_object(origin_id)
#         so_sel = query.to_object(selected_id)
#         percent = 0.0

#         if so.side == so_sel.side:
#             percent = 0.90
#         if so:
#             so.data_set.set("cur_scan_ID", selected_id,0)
#             so.data_set.set("cur_scan_type", extra_tag,0)
#             so.data_set.set("cur_scan_percent", percent,0)
            

#     # def set_buttons(self, from_id, to_id):
#     #     # check to see if the from ship still exists
        

#     def expand(self, button: Button, task: MastAsyncTask):
#         buttons = []
#         if button.for_code is not None:
#             iter_value = task.eval_code(button.for_code)
#             for data in iter_value:
#                 task.set_value(button.for_name, data, Scope.TEMP)
#                 clone = button.clone()
#                 clone.data = data
#                 clone.message = task.format_string(clone.message)
#                 buttons.append(clone)
#         return buttons


#     def science_message(self, message, an_id, event):
#         # makes sure this was for us
#         if event.selected_id != self.selected_id or self.origin_id != event.origin_id:
#             return
#         self.tab = event.extra_tag
#         self.event = event
#         #print(f"science scanned {self.tab}")
#         self.task.tick()


#     def leave(self, mast:Mast, task:MastAsyncTask, node: Comms):
#         ConsoleDispatcher.remove_select_pair(self.origin_id, self.selected_id, 'science_target_UID')
#         ConsoleDispatcher.remove_message_pair(self.origin_id, self.selected_id, 'science_target_UID')
        

#     def poll(self, mast:Mast, task:MastAsyncTask, node: Comms):
#         if len(node.buttons)==0:
#             self.scan_is_done = True
#             return PollResults.OK_ADVANCE_TRUE

#         if self.scan_is_done:
#             task.jump(task.active_label,node.end_await_node.loc+1)
#             return PollResults.OK_JUMP

#         #
#         # Check if the first scan should auto trigger
#         #
#         if self.tab == "__init__":        
#             so = query.to_object(self.selected_id)
#             so_player = query.to_object(self.origin_id)
#             # Clear tab it maybe set below
#             self.tab = None
#             if so and so_player:
#                 tab = so_player.side+"scan"
#                 scan_tab = so.data_set.get(tab,0)
#                 if scan_tab is None:
#                     if node.fog == 0:
#                         self.tab = "scan"
#                     else:
#                         dist = sbs.distance_id(self.origin_id, self.selected_id)
#                         if dist < node.fog:
#                             self.tab = "scan"
#                         #fall through


#         if self.tab is not None:
#             for i, button in enumerate(self.buttons):
#                 if task.format_string(button.message) == self.tab:
#                     self.button = i
#                     #print(f"science scanned {i}")
#             so_player = query.to_object(self.origin_id)
#             if so_player:
#                 self.tab = so_player.side+self.tab

#             task.set_value("__SCAN_TAB__", self,  Scope.TEMP)
#             if self.button is not None:
#                 button = self.buttons[self.button] 
#                 self.button = None
#                 #task.set_value(button.for_name, button.data, Scope.TEMP)
#                 task.set_value("EVENT", self.event, Scope.TEMP)
#                 task.jump(task.active_label,button.loc+1)
#             return PollResults.OK_JUMP
#         return PollResults.OK_RUN_AGAIN


class RegexEqual(str):
    def __eq__(self, pattern):
        return bool(re.search(pattern, self))

#
#
#
def handle_purge_tasks(so):
    """
    This will clear out all tasks related to the destroyed item
    """
    MastAsyncTask.stop_for_dependency(so.id)

LifetimeDispatcher.add_destroy(handle_purge_tasks)


over =     {
    "Comms": CommsRuntimeNode,
#    "Scan": ScanRuntimeNode
}

from ..helpers import FrameContext
def mast_format_string(s):
    if FrameContext.task is not None:
        return FrameContext.task.compile_and_format_string(s)

Mast.globals["mast_format_string"] = mast_format_string

Mast.globals["SpaceObject"] =MastSpaceObject
Mast.globals["script"] = sys.modules['script']
Mast.globals["sbs"] = sbs
Mast.globals['Vec3'] = vec.Vec3
for func in [
        ############################
        ## sbs
        sbs.distance_id,
        sbs.assign_client_to_ship
    ]:
    Mast.globals[func.__name__] = func


#
# Expose procedural methods to script
#
from ..procedural import query
from ..procedural import spawn
from ..procedural import timers
from ..procedural import grid
from ..procedural import space_objects
from ..procedural import roles
from ..procedural import inventory
from ..procedural import links
from ..procedural import gui
from ..procedural import comms
from ..procedural import science
from ..procedural import cosmos
from ..procedural import routes
from ..procedural import execution
from ..procedural import behavior


Mast.import_python_module('sbs_utils.procedural.query')
Mast.import_python_module('sbs_utils.procedural.spawn')
Mast.import_python_module('sbs_utils.procedural.timers')
Mast.import_python_module('sbs_utils.procedural.grid')
Mast.import_python_module('sbs_utils.procedural.space_objects')
Mast.import_python_module('sbs_utils.procedural.roles')
Mast.import_python_module('sbs_utils.procedural.inventory')
Mast.import_python_module('sbs_utils.procedural.links')
Mast.import_python_module('sbs_utils.procedural.gui')
Mast.import_python_module('sbs_utils.procedural.comms')
Mast.import_python_module('sbs_utils.procedural.science')
Mast.import_python_module('sbs_utils.procedural.cosmos')
Mast.import_python_module('sbs_utils.procedural.routes')
Mast.import_python_module('sbs_utils.procedural.execution')
Mast.import_python_module('sbs_utils.procedural.behavior')

Mast.import_python_module('sbs_utils.faces')
Mast.import_python_module('sbs_utils.fs')
Mast.import_python_module('sbs_utils.vec')
Mast.import_python_module('sbs_utils.scatter', 'scatter')
Mast.import_python_module('sbs_utils.names', 'names')
Mast.import_python_module('sbs', 'sbs')

class MastSbsScheduler(MastScheduler):
    def __init__(self, mast: Mast, overrides=None):
        if overrides:
            super().__init__(mast, over|overrides)
        else:
            super().__init__(mast,  over)


    def runtime_error(self, message):
        sbs.pause_sim()
        message += traceback.format_exc()
        Gui.push(self.sim, 0, ErrorPage(message))

