import logging
from .mastscheduler import PollResults, MastRuntimeNode, MastAsyncTask
from .mast import Mast, Scope
import sbs
from ..gui import Gui, Page
from ..helpers import FakeEvent, FrameContext
from ..procedural.inventory import get_inventory_value, set_inventory_value
from .parsers import StyleDefinition
from ..agent import Agent
from ..pages import layout

from .maststory import AppendText,  MastStory, Choose, Disconnect, Text, AwaitGui, OnChange, OnMessage, OnClick
import traceback
from .mastsbsscheduler import MastSbsScheduler, Button
from .parsers import LayoutAreaParser



class TabControl(layout.Text):
    def __init__(self, tag, message, label, page) -> None:
        super().__init__(tag,message)
        self.page = page
        self.label = label

    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            if self.label is not None:
                self.page.gui_task.jump(self.label)


class StoryRuntimeNode(MastRuntimeNode):
    def on_message(self, event):
        pass
    def databind(self):
        return False
    def compile_formatted_string(self, message):
        if message is None:
            return message
        if "{" in message:
            message = f'''f"""{message}"""'''
            code = compile(message, "<string>", "eval")
            return code
        else:
            return message

    def apply_style_name(self, style_name, layout_item, task):
        style_def = StyleDefinition.styles.get(style_name)
        self.apply_style_def(style_def, layout_item, task)
    def apply_style_def(self, style_def, layout_item, task):
        if style_def is None:
            return
        aspect_ratio = task.main.page.aspect_ratio
        if aspect_ratio.x == 0:
            aspect_ratio.x = 1
        if aspect_ratio.y == 0:
            aspect_ratio.y = 1

        area = style_def.get("area")
        if area is not None:
            i = 1
            values=[]
            for ast in area:
                if i >0:
                    ratio =  aspect_ratio.x
                else:
                    ratio =  aspect_ratio.y
                i=-i
                if ratio == 0:
                    ratio = 1
                values.append(LayoutAreaParser.compute(ast, task.get_symbols(),ratio))
            layout_item.set_bounds(layout.Bounds(*values))

        height = style_def.get("row-height")
        if height is not None:
            height = LayoutAreaParser.compute(height, task.get_symbols(),aspect_ratio.y)
            layout_item.set_row_height(height)        
        width = style_def.get("col-width")
        if width is not None:
            width = LayoutAreaParser.compute(height, task.get_symbols(),aspect_ratio.x)
            layout_item.set_col_width(height)        
        padding = style_def.get("padding")
        if padding is not None:
            aspect_ratio = task.main.page.aspect_ratio
            i = 1
            values=[]
            for ast in padding:
                if i >0:
                    ratio =  aspect_ratio.x
                else:
                    ratio =  aspect_ratio.y
                i=-i
                values.append(LayoutAreaParser.compute(ast, task.get_symbols(),ratio))
            while len(values)<4:
                values.append(0.0)
            layout_item.set_padding(layout.Bounds(*values))
        background = style_def.get("background")
        if background is not None:
            background = self.compile_formatted_string(background)
            layout_item.background = task.format_string(background)

        click_text = style_def.get("click_text")
        if click_text is not None:
            click_text = self.compile_formatted_string(click_text)
            layout_item.click_text = task.format_string(click_text)

        click_font = style_def.get("click_font")
        if click_font is not None:
            click_font = self.compile_formatted_string(click_font)
            layout_item.click_font = task.format_string(click_font)

        click_color = style_def.get("click_color")
        if click_color is not None:
            click_color = self.compile_formatted_string(click_color)
            layout_item.click_color = task.format_string(click_color)

        click_tag = style_def.get("click_tag")
        if click_tag is not None:
            click_tag = self.compile_formatted_string(click_tag)
            layout_item.click_tag = task.format_string(click_tag).strip()

        tag = style_def.get("tag")
        if tag is not None:
            tag = self.compile_formatted_string(tag)
            layout_item.tag = task.format_string(tag).strip()


class TextRuntimeNode(StoryRuntimeNode):
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
            self.layout_text = layout.Text(self.tag, msg)
            TextRuntimeNode.current = self

            self.apply_style_name(".text", self.layout_text, task)
            if node.style_def is not None:
                self.apply_style_def(node.style_def, self.layout_text, task)
            if node.style_name is not None:
                self.apply_style_name(node.style_name, self.layout, task)

            # After style in case tag changed
            task.main.page.add_content(self.layout_text, self)

    def databind(self):
        if True:
            return False
        

class AppendTextRuntimeNode(StoryRuntimeNode):
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




class AwaitGuiRuntimeNode(StoryRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: AwaitGui):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = sbs.app_seconds()+ (node.minutes*60+node.seconds)
        task.main.page.set_button_layout(None)

    def poll(self, mast:Mast, task:MastAsyncTask, node: AwaitGui):
        if self.timeout:
            if self.timeout <= sbs.app_seconds():
                return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_RUN_AGAIN


class DisconnectRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task: MastAsyncTask, node:Disconnect):
        if node.end_await_node:
            task.jump(task.active_label,node.end_await_node.loc+1)

class ChooseRuntimeNode(StoryRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Choose):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = sbs.app_seconds()+ seconds

        top = ((task.main.page.aspect_ratio.y - 30)/task.main.page.aspect_ratio.y)*100

        # ast = LayoutAreaParser.parse_e(LayoutAreaParser.lex("100-30px"))
        # top = LayoutAreaParser.compute(ast, {}, task.main.page.aspect_ratio.y)
        button_layout = layout.Layout(None, None, 0,top,100,100)
        button_layout.tag = task.main.page.get_tag()

        active = 0
        index = 0
        layout_row: layout.Row
        layout_row = layout.Row()
        layout_row.tag = task.main.page.get_tag()

        buttons = []

        # Expand all the 'for' buttons
        for button in node.buttons:
            if button.__class__.__name__ != "Button":
                buttons.append(button)
            elif button.for_name is None:
                buttons.append(button)
            else:
                buttons.extend(self.expand(button, task))
        
        for button in buttons:
            match button.__class__.__name__:
                case "Button":
                    value = True
                    #button.end_await_node = node.end_await_node
                    if button.code is not None:
                        value = task.eval_code(button.code)
                    if value and button.should_present(0):#task.main.client_id):
                        runtime_node = ChoiceButtonRuntimeNode(self, task, index, task.main.page.get_tag(), button)
                        #runtime_node.enter(mast, task, button)
                        msg = task.format_string(button.message)
                        layout_button = layout.Button(runtime_node.tag, msg)
                        layout_row.add(layout_button)
                        
                        self.apply_style_name(".choice", layout_button, task)
                        if node.style_def is not None:
                            self.apply_style_def(node.style_def,  layout_button, task)
                        if node.style_name is not None:
                            self.apply_style_name(node.style_name, layout_button, task)
                        # After style could change tag
                        task.main.page.add_tag(layout_button, runtime_node)
                        active += 1
                case "Separator":
                    # Handle face expression
                    layout_row.add(layout.Blank())
            index+=1

        if active>0:    
            button_layout.add(layout_row)
            task.main.page.set_button_layout(button_layout)
        else:
            task.main.page.set_button_layout(None)

        self.active = active
        self.buttons = buttons
        self.button = None

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


    def poll(self, mast:Mast, task:MastAsyncTask, node: Choose):
        if node.disconnect_label is not None:
            page = task.main.page
            if page is not None and page.disconnected:
                task.push_inline_block(task.active_label,node.disconnect_label.loc+1)
                return PollResults.OK_JUMP
        
        if self.active==0 and self.timeout is None:
            return PollResults.OK_ADVANCE_TRUE


        if self.button is not None:
            if node.assign:
                task.set_value_keep_scope(node.assign, self.button.index)
                return PollResults.OK_ADVANCE_TRUE
            
            self.button.node.visit(self.button.client_id)
            button = self.buttons[self.button.index]
            if button.for_name:
                task.set_value(button.for_name, button.data, Scope.TEMP)

            self.button = None
            #print(f"CHOICE {button.loc+1} {node.end_await_node.loc}")
            task.push_inline_block(task.active_label,button.loc+1)
            return PollResults.OK_JUMP

        if self.timeout is not None:
            if self.timeout <= sbs.app_seconds():
                if node.timeout_label:
                    task.jump(task.active_label,node.timeout_label.loc+1)
                    return PollResults.OK_JUMP
                elif node.end_await_node:
                    task.jump(task.active_label,node.end_await_node.loc+1)
                    return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN


class ChoiceButtonRuntimeNode(StoryRuntimeNode):
    def __init__(self, choice, task, index, tag, node):
        self.choice = choice
        self.index = index
        self.tag = tag
        self.client_id = None
        self.node = node
        self.task = task
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.choice.button = self
            self.client_id = event.client_id
            self.task.tick()
            

class OnChangeRuntimeNode(StoryRuntimeNode):
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

class OnMessageRuntimeNode(StoryRuntimeNode):
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


class OnClickRuntimeNode(StoryRuntimeNode):
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

    "AwaitGui": AwaitGuiRuntimeNode,
    "Choose": ChooseRuntimeNode,
}

class StoryScheduler(MastSbsScheduler):
    def __init__(self, mast: Mast, overrides=None):
        if overrides:
            super().__init__(mast, over|overrides)
        else:
            super().__init__(mast,  over)
        
        self.paint_refresh = False
        self.errors = []
        # self.sim = None
        # self.client_id = None

    def run(self, client_id, page, label="main", inputs=None):
        # ctx = FrameContext.context
        # self.sim = ctx.sim
        # self.ctx = ctx
        self.page = page
        self.client_id = client_id
        #inputs = inputs if inputs else {}
        # self.set_inventory_value('sim', ctx.sim)
        # self.set_inventory_value('client_id', client_id)
        # self.set_inventory_value('IS_SERVER', client_id==0)
        # self.set_inventory_value('IS_CLIENT', client_id!=0)
        # self.set_inventory_value('STORY_PAGE', page)
        FrameContext.page = self.page
        return super().start_task( label)

    def story_tick_tasks(self, client_id):
        #
        restore = FrameContext.page
        FrameContext.page = self.page
        # self.sim = ctx.sim
        # self.ctx = ctx
        # self.set_inventory_value('sim', ctx.sim)
        # self.set_inventory_value('ctx', ctx)
        # self.client_id = client_id
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

class StoryPage(Page):
    tag = 0
    story_file = None
    inputs = None
    story = None
    def __init__(self) -> None:
        self.gui_state = 'repaint'
        self.story_scheduler = None
        self.layouts = []
        self.tag = 10000
        section = layout.Layout(None, None, 0,0, 100, 90)
        section.tag = self.get_tag()
        self.pending_layouts = self.pending_layouts = []
        self.pending_row = self.pending_row = layout.Row()
        self.pending_row.tag = self.get_tag()
        self.pending_tag_map = {}
        self.tag_map = {}
        self.aspect_ratio = sbs.vec2(1024,768)
        self.client_id = None
        self.sbs = None
        self.ctx = None
        self.console = ""
        self.widgets = ""
        self.pending_console = ""
        self.pending_widgets = ""
        self.pending_on_change_items= []
        self.on_change_items= []
        self.pending_on_click = []
        self.on_click = []
        self.gui_task = None
        self.change_console_label = None
        self.disconnected = False
        
        self.errors = []
        cls = self.__class__
        
        if cls.story is None:
            if cls.story is  None:
                cls.story = MastStory()
                if cls.__dict__.get("story_file"):
                    self.errors =  cls.story.from_file(cls.story_file)
        self.story = cls.story
        self.main = cls.__dict__.get("main", "main")
        self.main_server = cls.__dict__.get("main_server", self.main)
        self.main_client = cls.__dict__.get("main_client", self.main)
        
        

    def start_story(self, client_id):
        if self.story_scheduler is not None:
            return
        cls = self.__class__
        self.client_id == client_id
        if len(self.errors)==0:
            self.story_scheduler = StoryScheduler(self.story)
            #
            # Get a label from the story class or us main
            # main should at least be an empty label
            label = self.__dict__.get("main", "main")
            # Look for server specific main
            if client_id == 0:
                label = self.__dict__.get("main_server", label)
            # Look for client specific main
            if client_id != 0:
                label = self.__dict__.get("main_client", label)
            #print(f"LABEL: {label}")

            self.story_scheduler.page = self
            #self.story_scheduler.set_inventory_value('sim', ctx.sim)
            self.story_scheduler.set_inventory_value('client_id', client_id)
            self.story_scheduler.set_inventory_value('IS_SERVER', client_id==0)
            self.story_scheduler.set_inventory_value('IS_CLIENT', client_id!=0)
            # self.set_inventory_value('STORY_PAGE', page)

            self.gui_task = self.story_scheduler.run(client_id, self, label, inputs=cls.inputs)


    def tick_gui_task(self):
        #
        # Called by gui right before present
        #
        if self.story_scheduler:
            self.story_scheduler.story_tick_tasks(self.client_id)


    def swap_layout(self):
        self.on_change_items= self.pending_on_change_items
        self.pending_on_change_items = []
        self.on_click = self.pending_on_click
        self.pending_on_click = []
        self.layouts = self.pending_layouts
        self.tag_map = self.pending_tag_map
        self.console = self.pending_console
        self.widgets = self.pending_widgets

        
        self.gui_queue_console_tabs()
                
        self.tag = 10000
        
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.calc()
            
            section = layout.Layout(None, None, 0,0, 100, 90)
            section.tag = self.get_tag()
            self.pending_layouts = self.pending_layouts = [section]
            self.pending_row = self.pending_row = layout.Row()
            self.pending_row.tag = self.get_tag()
            self.pending_tag_map = {}
            self.pending_console = ""
            self.pending_widgets = ""
        
        self.gui_state = 'repaint'


    def get_tag(self):
        self.tag += 1
        return str(self.tag)

    def add_row(self):
        if not self.pending_layouts:
            self.pending_layouts = [layout.Layout(None, None, 0,0, 100, 90)]
        if self.pending_row:
            if len(self.pending_row.columns):
                self.pending_layouts[-1].add(self.pending_row)
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        self.pending_row = layout.Row()
        # Rows have tags for background and/or clickable
        self.pending_row.tag = self.get_tag()

    def add_tag(self, layout_item, runtime_node):
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        if hasattr(layout_item, 'tag'):
            self.pending_tag_map[layout_item.tag] = (layout_item, runtime_node)



    def add_content(self, layout_item, runtime_node):
        if self.pending_layouts is None:
            self.add_row()

        self.add_tag(layout_item, runtime_node)

        self.pending_row.add(layout_item)

    def add_on_change(self, runtime_node):
        self.pending_on_change_items.append(runtime_node)

    def add_on_click(self, runtime_node):
        self.pending_on_click.append(runtime_node)

    def add_on_message(self, runtime_node):
        self.pending_on_click.append(runtime_node)

    def set_widget_list(self, console,widgets):
        self.pending_console = console
        self.pending_widgets = widgets

    def activate_console(self, console):
        self.pending_console = console

    def add_console_widget(self, widget):
        if  self.pending_widgets=="":
            self.pending_widgets = widget
        else:
            self.pending_widgets += "^"+widget
    
    def add_section(self, tag= None):
        if tag is None:
            tag = self.get_tag()

        section = layout.Layout(tag, None, 0,0, 100, 90)
        
        if not self.pending_layouts:
            self.pending_layouts = [section]
        else:
            self.add_row()
            self.pending_layouts.append(section)

    def get_pending_layout(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_layouts[-1]

    def get_pending_row(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_row


    def set_button_layout(self, layout):
        if self.pending_row and self.pending_layouts:
            if self.pending_row:
                self.pending_layouts[-1].add(self.pending_row)
        
        if not self.pending_layouts:
            self.add_section()
        
        if layout:
            self.pending_layouts.append(layout)
        
        self.swap_layout()

    def gui_queue_console_tabs(self):
        console = self.console
        if self.console is not None: 
            console = self.console.lower()
        
        convert = {
            "normal_helm": "helm",
            "normal_weap": "weapons",
            "normal_sci": "science",
            "normal_engi": "engineering",
            "normal_comm": "comms"
        }
        console = convert.get(console, console)
        #
        # tabs can be for all ships or single
        #
        all_ship_tabs = Agent.SHARED.get_inventory_value("console_tabs", {})
        # print(all_ship_tabs)
        all_tabs = all_ship_tabs.get("any", {})
        ship_id = get_inventory_value(self.client_id, "assigned_ship", None)
        #
        # Add ship any
        #
        ship_any_tabs = {}
        ship_tabs = {}
        if ship_id is not None:
            ship_tabs = get_inventory_value(ship_id, "console_tabs", {})
            ship_any_tabs = ship_tabs.get("any", {})
        
        #
        #  Add console
        #
        all_console_tabs = {}
        ship_console_tabs ={}
        back_tab = get_inventory_value(self.client_id, "__back_tab__", "back")
        back_tab = get_inventory_value(self.client_id, "CONSOLE_TYPE", back_tab)
        if console is not None:
            console = console.lower()
            set_inventory_value(self.client_id, "__back_tab__", console)
            all_console_tabs = all_ship_tabs.get(console, {})
            ship_console_tabs = ship_tabs.get(console, {})
        #
        # Ship and console override if keys match
        #
        all_tabs  = all_tabs |  all_console_tabs | ship_any_tabs | ship_console_tabs
            
        if len(all_tabs) == 0 : return
        #
        # Ok we're on a ship, on a console
        #
        _layout = layout.Layout(None, None, 20,0, 100, 3)
        _row = layout.Row(height=3)
        _layout.add(_row)

        # Make spots for a certain amount of tabs
        spots = 6
        blanks = spots-len(all_tabs)
        if blanks <0: blanks = 0
        for _ in range(blanks):
            _row.add(layout.Blank())

        for tab in all_tabs:
            
            tab_text = tab
            if tab == "__back_tab__":
                tab_text = back_tab
            msg = f"justify:center;color:black;text:{tab_text};"

            button = TabControl(self.get_tag(),msg, all_tabs[tab], self) # Jump label all_tabs[tab]
            button.click_text = tab_text
            button.click_color = "#FFF"
            #self.click_font = None
            button.click_tag = self.get_tag()

            if tab == console:
                button.background = "#fff9"
            else:
                button.background = "#fff3"
            
            _row.add(button)
        #_layout.calc()
        self.pending_layouts.append(_layout)


    def update_props_by_tag(self, tag, props):
        # get item by tag
        item = self.tag_map.get(tag)
        # call update
        if item is None:
            return
        item = item[0]
        item.update(props)
        # present it
        event = FakeEvent(self.client_id, "", "")
        item.present(event)

    
    def present(self, event):
        """ Present the gui """
        if self.client_id is None:
            self.client_id = event.client_id
        if self.gui_state == "errors":
            return
        if self.disconnected:
            return
        #
        # Cache sbs this should not change
        # cache will be used in updates they only need sbs, ratio and client_id
        #
        my_sbs = FrameContext.context.sbs
        
            
        
        for change in self.on_change_items:
            if change.test():
                self.gui_task.push_inline_block(self.gui_task.active_label, change.node.loc+1)
                self.tick_gui_task()
                return

        
        if self.story_scheduler is None:
            self.start_story(event.client_id)
        else:
            if len(self.story_scheduler.errors) > 0:
                #errors = self.errors.reverse()
                message = ''.join([str(elem) for elem in self.story_scheduler.errors])
                message = message.replace(chr(94), "-")
                message = message.replace(chr(44), "`")
                message = "text:"+message
                print(message)
                my_sbs.send_gui_clear(event.client_id)
                if event.client_id != 0:
                    my_sbs.send_client_widget_list(event.client_id, "", "")
                my_sbs.send_gui_text(event.client_id, "error",  message, 0,0,99,99)
                self.gui_state = "errors"
                my_sbs.send_gui_complete(event.client_id)
                return

            if self.story_scheduler.paint_refresh:
                if self.gui_state != "repaint":  
                    self.gui_state = "refresh"
                self.story_scheduler.paint_refresh = False
            
            if not self.story_scheduler.story_tick_tasks(event.client_id):
                #self.story_runtime_node.mast.remove_runtime_node(self)
                Gui.pop(event.client_id)
                return
        if len(self.errors) > 0:
            message = "".join(self.errors)
            message = message.replace(";", "~")
            message = "text: Mast Compiler Errors\n" + message.replace(",", ".")
            my_sbs.send_gui_clear(event.client_id)
            if event.client_id != 0:
                my_sbs.send_client_widget_list(event.client_id, "", "")
            my_sbs.send_gui_text(event.client_id, "error", message,  0,0,100,100)
            self.gui_state = "errors"
            my_sbs.send_gui_complete(event.client_id)
            return
        
        sz = FrameContext.aspect_ratio
        if sz is not None and sz.y != 0:
            aspect_ratio = sz
            if (self.aspect_ratio.x != aspect_ratio.x or 
                self.aspect_ratio.y != aspect_ratio.y):
                self.aspect_ratio.x = sz.x
                self.aspect_ratio.y = sz.y
                #print(f"Aspect Change {self.aspect_ratio.x} {self.aspect_ratio .y}")
                for layout in self.layouts:
                    # layout.aspect_ratio.x = aspect_ratio.x
                    layout.calc()
                self.gui_state = 'repaint'

        
        match self.gui_state:
            
            case  "repaint":
                my_sbs.send_gui_clear(event.client_id)
                if event.client_id != 0:
                    my_sbs.send_client_widget_list(event.client_id, self.console, self.widgets)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed

                for layout in self.layouts:
                    layout.present(event)
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
                my_sbs.send_gui_complete(event.client_id)
            case  "refresh":
                for layout in self.layouts:
                    layout.present(event)
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
            case _:
                for change in self.on_change_items:
                    if change.test():
                        self.gui_task.push_inline_block(self.gui_task.active_label, change.node.loc+1)
                        break

    def on_message(self, event):
        if event.client_id != self.client_id:
            return
        
        message_tag = event.sub_tag
        

        clicked = None
        # Process layout first
        for section in self.layouts:
            section.on_message(event)
        clicked = layout.Layout.clicked.get(self.client_id)

        runtime_node = self.tag_map.get(message_tag)
        refresh = False
        if runtime_node is not None and runtime_node[1] is not None:
            # tuple layout and runtime node
            runtime_node = runtime_node[1]
            FrameContext.context.aspect_ratio = self.aspect_ratio
            runtime_node.on_message(event)
            # for node in self.tag_map.values():
            #     if node != runtime_node:
            #         bound = node.databind()
            #         refresh = bound or refresh
        
        for change in self.on_change_items:
            if change.test():
                self.gui_task.push_inline_block(self.gui_task.active_label, change.node.loc+1)
                return
            
        if clicked is not None:
            for click in self.on_click:
                if click.test(clicked.click_tag):
                    self.gui_task.push_inline_block(self.gui_task.active_label, click.node.loc+1)
                    return
            layout.Layout.clicked[self.client_id] = None
            
        if refresh:
            self.gui_state = "refresh"
            self.present(event)

        

    def on_event(self, event):
        if event.client_id != self.client_id:
            return
        
        #print (f"Story event {event.client_id} {event.tag} {event.sub_tag}")
        if self.story_scheduler is None:
            return
        
        if event.tag =="mast:client_disconnect":
            #print("event discon")
            self.disconnected = True
            self.tick_gui_task()
        elif event.tag == "client_change":
            if event.sub_tag == "change_console":
                if self.gui_task is not None and not self.gui_task.done():
                    if self.change_console_label:
                        self.gui_task.jump(self.change_console_label)
                        self.present(event)
