import logging
from .mastscheduler import MastRuntimeNode, MastAsyncTask, MastScheduler
from .mast import Mast, Scope
from ..agent import Agent
import sbs
from ..gui import Gui
from ..procedural.gui import gui_text_area
from ..procedural.comms import comms_receive, comms_transmit, comms_speech_bubble
from ..procedural.science import scan_results
from ..helpers import FakeEvent, FrameContext, format_exception

from .maststory import AppendText,  Text, CommsMessageStart
import random

# Needed to get procedural in memory
from . import mast_sbs_procedural
import sys


class TextRuntimeNode(MastRuntimeNode):
    current = None
    def enter(self, mast:Mast, task:MastAsyncTask, node: Text):
        self.tag = task.main.page.get_tag()
        msg = ""
        self.task = task 
        value = True
        TextRuntimeNode.current = self
        if node.code is not None:
            value = task.eval_code(node.code)
        if value:
            msg = task.format_string(node.message)
            #msg = node.message
            style = node.style
            if style is None:
                style = node.style_name
            self.layout_text = gui_text_area(msg,style)
        

class AppendTextRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: AppendText):
        msg = ""
        value = True
        if node.code is not None:
            value = task.eval_code(node.code)
        if value:
            msg = task.format_string(node.message)
            text = TextRuntimeNode.current
            if text is not None:
                text.layout_text.message += '\n'
                text.layout_text.message += msg

class CommsMessageStartRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: CommsMessageStart):
        if len(node.options)==0:
            return
        msg = random.choice(node.options)
        if node.mtype == "<<": 
            comms_receive(msg, node.title, color=node.body_color, title_color=node.title_color)
        elif node.mtype == ">>": 
            comms_transmit(msg, node.tile, color=node.body_color, title_color=node.title_color)
        elif node.mtype == "<scan>": 
            scan_results(msg)
        elif node.mtype == "()": 
            comms_speech_bubble(msg, color=node.title_color)

over =     {
    "Text": TextRuntimeNode,
    "AppendText": AppendTextRuntimeNode,
    "CommsMessageStart": CommsMessageStartRuntimeNode
}

class StoryScheduler(MastScheduler):
    def __init__(self, mast: Mast, overrides=None):
        if overrides:
            super().__init__(mast, over|overrides)
        else:
            super().__init__(mast,  over)
        
        self.paint_refresh = False
        self.errors = []
        self.client_id = None

    def run(self, client_id, page, label="main", inputs=None, task_name=None, defer=False):
        self.page = page
        self.client_id = client_id
        restore = FrameContext.page
        FrameContext.page = self.page
        ret =  super().start_task( label, inputs, task_name, defer)
        FrameContext.page = restore
        return ret

    def story_tick_tasks(self, client_id):
        #
        restore = FrameContext.page
        FrameContext.page = self.page
        ret = super().tick()
        FrameContext.page = restore
        return ret


    def refresh(self, label):
        for task in self.tasks:
            if label == task.active_label:
                restore = FrameContext.page
                FrameContext.page = self.page
                task.jump(task.active_label)
                task.tick()
                FrameContext.page = restore
                Gui.dirty(self.client_id)
            if label == None:
                # On change or element requested refresh?
                #task.jump(task.active_label)
                #print("I was told to refresh")
                self.story_tick_tasks(self.client_id)
                self.page.gui_state = "repaint"
                event = FakeEvent(self.client_id, "gui_represent")
                self.page.present(event)


    def runtime_error(self, message):
        sbs.pause_sim()
        err = format_exception(message, "SBS Utils Page level Runtime Error:")
        task = self.active_task
        if task is not None:
            err = task.get_runtime_error_info(err)
        #err = traceback.format_exc()
        if not err.startswith("NoneType"):
            #message += str(err)
            self.errors = [err]

    def get_value(self, key, defa=None):
        """_summary_

        Args:
            key (_type_): _description_
            defa (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        val = Mast.globals.get(key, None) # don't use defa here
        if val is not None:
            return (val, Scope.SHARED)
        # Check shared
        val = Agent.SHARED.get_inventory_value(key, None) # don't use defa here
        if val is not None:
            return (val, Scope.SHARED)
        
        if self.client_id is not None:
            val = Agent.get(self.client_id).get_inventory_value(key, None) # don't use defa here
            if val is not None:
                return (val, Scope.CLIENT)
            
            assign = None
            if self.client_id is not None:
                _id = sbs.get_ship_of_client(self.client_id)
                if _id:
                    assign = Agent.get(_id)
            if assign is not None:
                val = assign.get_inventory_value(key, None) # don't use defa here
                if val is not None:
                    return (val, Scope.ASSIGNED)

        val = self.get_inventory_value(key, None) # now defa make sense
        if val is not None:
            #TODO: Should this no longer be NORMAL
            return (val, Scope.NORMAL) # NORMAL is the same as TASK
        return (val, Scope.UNKNOWN)
    
    def set_value(self, key, value, scope):
        if scope == Scope.SHARED:
            # self.main.mast.vars[key] = value
            Agent.SHARED.set_inventory_value(key, value)
            return scope
        
        if self.client_id is None:
            return Scope.UNKNOWN
        
        if scope == Scope.CLIENT:
            Agent.get(self.client_id).set_inventory_value(key, value) # don't use defa here
            return scope
        
        if scope == Scope.ASSIGNED:
            _ship = sbs.get_ship_of_client(self.client_id) 
            _ship = None if _ship == 0 else _ship
            assign = Agent.get(_ship)
            if assign is not None:
                assign.set_inventory_value(key, value) # don't use defa here
            return scope
    
        return Scope.UNKNOWN
    
    def get_symbols(self):
        mast_inv = super().get_symbols()
        if self.client_id is None:        
            return mast_inv
        m1 = mast_inv | Agent.get(self.client_id).inventory.collections
        _ship = sbs.get_ship_of_client(self.client_id) 
        _ship = None if _ship == 0 else _ship
        assign = Agent.get(_ship)
        if assign is not None:
            m1 = m1 | assign.inventory.collections
        return m1

