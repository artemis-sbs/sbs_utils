import logging
from .mastscheduler import MastRuntimeNode, MastAsyncTask, MastScheduler
from .mast import Mast
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

