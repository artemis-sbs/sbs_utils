import logging
from .mastscheduler import PollResults, MastRuntimeNode, MastAsyncTask, MastScheduler
from .mast import Mast, Scope
import sbs
from ..gui import Gui
from ..procedural.gui import gui_text
from ..helpers import FakeEvent, FrameContext
from ..procedural.inventory import get_inventory_value, set_inventory_value
from .parsers import StyleDefinition
from ..agent import Agent
from ..pages import layout

from .maststory import AppendText,  Text,  OnChange, OnMessage, OnClick
import traceback
from .parsers import LayoutAreaParser
from . import mastsbsscheduler






# class StoryRuntimeNode(MastRuntimeNode):
#     def on_message(self, event):
#         pass
#     def databind(self):
#         return False
#     def compile_formatted_string(self, message):
#         if message is None:
#             return message
#         if "{" in message:
#             message = f'''f"""{message}"""'''
#             code = compile(message, "<string>", "eval")
#             return code
#         else:
#             return message

#     def apply_style_name(self, style_name, layout_item, task):
#         style_def = StyleDefinition.styles.get(style_name)
#         self.apply_style_def(style_def, layout_item, task)
#     def apply_style_def(self, style_def, layout_item, task):
#         if style_def is None:
#             return
#         aspect_ratio = task.main.page.aspect_ratio
#         if aspect_ratio.x == 0:
#             aspect_ratio.x = 1
#         if aspect_ratio.y == 0:
#             aspect_ratio.y = 1

#         area = style_def.get("area")
#         if area is not None:
#             i = 1
#             values=[]
#             for ast in area:
#                 if i >0:
#                     ratio =  aspect_ratio.x
#                 else:
#                     ratio =  aspect_ratio.y
#                 i=-i
#                 if ratio == 0:
#                     ratio = 1
#                 values.append(LayoutAreaParser.compute(ast, task.get_symbols(),ratio))
#             layout_item.set_bounds(layout.Bounds(*values))

#         height = style_def.get("row-height")
#         if height is not None:
#             height = LayoutAreaParser.compute(height, task.get_symbols(),aspect_ratio.y)
#             layout_item.set_row_height(height)        
#         width = style_def.get("col-width")
#         if width is not None:
#             width = LayoutAreaParser.compute(height, task.get_symbols(),aspect_ratio.x)
#             layout_item.set_col_width(height)        
#         padding = style_def.get("padding")
#         if padding is not None:
#             aspect_ratio = task.main.page.aspect_ratio
#             i = 1
#             values=[]
#             for ast in padding:
#                 if i >0:
#                     ratio =  aspect_ratio.x
#                 else:
#                     ratio =  aspect_ratio.y
#                 i=-i
#                 values.append(LayoutAreaParser.compute(ast, task.get_symbols(),ratio))
#             while len(values)<4:
#                 values.append(0.0)
#             layout_item.set_padding(layout.Bounds(*values))
#         background = style_def.get("background")
#         if background is not None:
#             background = self.compile_formatted_string(background)
#             layout_item.background = task.format_string(background)

#         click_text = style_def.get("click_text")
#         if click_text is not None:
#             click_text = self.compile_formatted_string(click_text)
#             layout_item.click_text = task.format_string(click_text)

#         click_font = style_def.get("click_font")
#         if click_font is not None:
#             click_font = self.compile_formatted_string(click_font)
#             layout_item.click_font = task.format_string(click_font)

#         click_color = style_def.get("click_color")
#         if click_color is not None:
#             click_color = self.compile_formatted_string(click_color)
#             layout_item.click_color = task.format_string(click_color)

#         click_tag = style_def.get("click_tag")
#         if click_tag is not None:
#             click_tag = self.compile_formatted_string(click_tag)
#             layout_item.click_tag = task.format_string(click_tag).strip()

#         tag = style_def.get("tag")
#         if tag is not None:
#             tag = self.compile_formatted_string(tag)
#             layout_item.tag = task.format_string(tag).strip()


class TextRuntimeNode(MastRuntimeNode):
    current = None
    def enter(self, mast:Mast, task:MastAsyncTask, node: Text):
        self.tag = task.main.page.get_tag()
        msg = ""
        # for databind
        self.node = node
        self.task = task 
        value = True
        if node.code is not None:
            value = task.eval_code(node.code)
        if value:
            msg = task.format_string(node.message)
            self.layout_text = gui_text(msg)
        

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





# class DisconnectRuntimeNode(MastRuntimeNode):
#     def poll(self, mast, task: MastAsyncTask, node:Disconnect):
#         if node.end_await_node:
#             task.jump(task.active_label,node.end_await_node.loc+1)

            

class OnChangeRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: OnChange):
        self.task = task
        self.node = node
        if not node.is_end:
            self.value = task.eval_code(node.value) 
            task.main.page.add_on_change(self)

    def test(self):
        prev = self.value
        self.value = self.task.eval_code(self.node.value) 
        return prev!=self.value
        

    def poll(self, mast:Mast, task:MastAsyncTask, node: OnChange):
        if node.is_end:
            self.task.pop_label(False)
            return PollResults.OK_JUMP
        if node.end_node:
            self.task.jump(self.task.active_label, node.end_node.loc+1)
            return PollResults.OK_JUMP

class OnMessageRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: OnMessage):
        self.task = task
        self.node = node
        self.label = task.active_label
        if not node.is_end:
            layout_item = task.eval_code(node.value) 
            self.layout = layout_item
            # This will remap to include this as the message handler
            task.main.page.add_tag(layout_item, self)


    def on_message(self, event):
        if event.sub_tag == self.layout.tag:
            self.task.set_value_keep_scope("__ITEM__", self.layout)
            data = self.layout.data
            self.task.push_inline_block(self.label, self.node.loc+1, data)

    def poll(self, mast:Mast, task:MastAsyncTask, node: OnMessage):
        if node.is_end:
            task.pop_label(False)
            return PollResults.OK_JUMP
        elif node.end_node:
            # skip on first pass
            self.task.jump(self.task.active_label, node.end_node.loc+1)
            return PollResults.OK_JUMP


class OnClickRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: OnClick):
        self.task = task
        self.node = node
        if not node.is_end:
            task.main.page.add_on_click(self)

    def test(self, click_tag):
        if self.node.name is not None:
            if self.node.name!= click_tag:
                return False
        self.task.set_value("__CLICKED__", click_tag, Scope.TEMP)
        return True
        

    def poll(self, mast:Mast, task:MastAsyncTask, node: OnClick):
        if node.is_end:
            self.task.pop_label(False)
            return PollResults.OK_JUMP
        if node.end_node:
            self.task.jump(self.task.active_label, node.end_node.loc+1)
            return PollResults.OK_JUMP



#
# These are needed so the import later works, domn't remove
#
from sbs_utils.widgets.listbox import Listbox
from sbs_utils.widgets.shippicker import ShipPicker

######################
## Mast extensions
Mast.import_python_module('sbs_utils.widgets.shippicker')
Mast.import_python_module('sbs_utils.widgets.listbox')

over =     {
    "Text": TextRuntimeNode,
    "AppendText": AppendTextRuntimeNode,

    "OnChange": OnChangeRuntimeNode,
    "OnMessage": OnMessageRuntimeNode,
    "OnClick": OnClickRuntimeNode,
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
                print("I was told to refresh")
                self.story_tick_tasks(self.client_id)
                self.page.gui_state = "repaint"
                event = FakeEvent(self.client_id, "gui_represent")
                self.page.present(event)


    def runtime_error(self, message):
        sbs.pause_sim()
        err = traceback.format_exc()
        if not err.startswith("NoneType"):
            message += str(err)
            self.errors = [message]

