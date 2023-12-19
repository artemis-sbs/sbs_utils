import logging
from .mastscheduler import PollResults, MastRuntimeNode, MastAsyncTask, MastScheduler
from .mast import Mast
import sbs
from ..gui import Gui
from ..procedural.gui import gui_text
from ..helpers import FakeEvent, FrameContext, format_exception

from .maststory import AppendText,  Text
import traceback
from .parsers import LayoutAreaParser
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
            style = node.style
            if style is None:
                style = node.style_name
            self.layout_text = gui_text(msg,style)
        

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



over =     {
    "Text": TextRuntimeNode,
    "AppendText": AppendTextRuntimeNode,
}

class StoryScheduler(MastScheduler):
    def __init__(self, mast: Mast, overrides=None):
        if overrides:
            super().__init__(mast, over|overrides)
        else:
            super().__init__(mast,  over)
        
        self.paint_refresh = False
        self.errors = []

    def run(self, client_id, page, label="main", inputs=None):
        self.page = page
        self.client_id = client_id
        restore = FrameContext.page
        FrameContext.page = self.page
        ret =  super().start_task( label)
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
        #err = traceback.format_exc()
        if not err.startswith("NoneType"):
            #message += str(err)
            self.errors = [err]

