import sbs
from ..mast.parsers import StyleDefinition, LayoutAreaParser
from ..gui import Page, Gui
from ..pages import layout
from . import PollResults
from .pymastscheduler import PyMastScheduler
import traceback

class CodePusher:
    def __init__(self, story, func_or_tuple, end_await=True) -> None:
        self.func_or_tuple = func_or_tuple
        self.story = story
        self.end_await = end_await

    def on_message(self, sim, event):
        data = None
        button_func = self.func_or_tuple
        if isinstance(self.func_or_tuple, tuple):
            data = self.func_or_tuple[1]
            button_func = self.func_or_tuple[0]
        def pusher(story):
            if data is not None:
                gen = button_func(data)
            else:
                gen = button_func()
            if gen is not None:
                for res in gen:
                    yield res
            story.pop()

            if story.scheduler.page is not None and self.end_await:
                story.scheduler.page.end_await = True 

        self.story.push(pusher)



class PyMastStoryPage(Page):
    tag = 0
    story=None

    def __init__(self) -> None:
        self.gui_state = 'repaint'
        self.story_scheduler = None
        self.layouts = []
        self.pending_layouts = self.pending_layouts = [layout.Layout(None, 0,0, 100, 90)]
        self.pending_row = self.pending_row = layout.Row()
        self.pending_tag_map = {}
        self.tag_map = {}
        self.aspect_ratio = sbs.vec2(1920,1071)
        self.client_id = None
        self.sim = None
        self.console = ""
        self.widgets = ""
        self.pending_console = ""
        self.pending_widgets = ""
        #self.tag = 0
        self.errors = []
        self.on_message_cb = None
        self.end_await = False

    def run(self, time_out):
        def pusher(story):
            return self._run(time_out)
        self.story.push(pusher)

    def _run(self, time_out):    
        self.end_await = False
        while self.end_await == False:
            yield PollResults.OK_RUN_AGAIN
        self.story.pop()
      

    def swap_layout(self):
        self.layouts = self.pending_layouts
        self.tag_map = self.pending_tag_map
        self.console = self.pending_console
        self.widgets = self.pending_widgets
        
        self.tag = 10000
        
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.calc()
            
            self.pending_layouts = self.pending_layouts = [layout.Layout(None, 0,0, 100, 90)]
            self.pending_row = self.pending_row = layout.Row()
            self.pending_tag_map = {}
            self.pending_console = ""
            self.pending_widgets = ""
        
        self.gui_state = 'repaint'

    def get_tag(self):
        self.tag += 1
        return str(self.tag)

    def add_row(self):
        if not self.pending_layouts:
            self.pending_layouts = [layout.Layout(None, 20,10, 100, 90)]
        if self.pending_row:
            if len(self.pending_row.columns):
                self.pending_layouts[-1].add(self.pending_row)
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        self.pending_row = layout.Row()

    def add_tag(self, layout_item, runtime_node):
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        if hasattr(layout_item, 'tag'):
            self.pending_tag_map[layout_item.tag] = runtime_node

    def add_content(self, layout_item, runtime_node):
        if self.pending_layouts is None:
            self.add_row()

        self.add_tag(layout_item, runtime_node)

        self.pending_row.add(layout_item)

    def set_widget_list(self, console,widgets):
        self.pending_console = console
        self.pending_widgets = widgets
    
    def add_section(self):
        if not self.pending_layouts:
            self.pending_layouts = [layout.Layout(None, 0,0, 100, 90)]
        else:
            self.add_row()
            self.pending_layouts.append(layout.Layout(None, 0,0, 100, 90))
        return self.pending_layouts[-1]

    def get_pending_layout(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_layouts[-1]

    def get_pending_row(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_row
    

    def set_buttons(self, buttons):
        if buttons is None:
            self.set_button_layout(None)
            return
        top = ((self.aspect_ratio.y - 30)/self.aspect_ratio.y)*100
        button_layout = layout.Layout(None, 0,top,100,100)
        layout_row = layout.Row()
        for button, value in buttons.items():
            the_button = layout.Button(button, self.get_tag())
            layout_row.add(the_button)
            self.add_tag(the_button, CodePusher(self.story, value))
        button_layout.add(layout_row)
        self.set_button_layout(button_layout)


    def set_button_layout(self, layout):
        if self.pending_row and self.pending_layouts:
            if self.pending_row:
                self.pending_layouts[-1].add(self.pending_row)
        
        if not self.pending_layouts:
            self.add_section()
        
        if layout:
            self.pending_layouts.append(layout)
        
        self.end_await = False
        self.swap_layout()

    def present(self, sim, event):
        """ Present the gui """
        if self.client_id is None:
            self.client_id = event.client_id
        if self.gui_state == "errors":
            return
        
        if self.story_scheduler is None:
            if self.story is not None:
                label = "start_server" if self.client_id ==0 else "start_client"
                self.story_scheduler = self.story.add_scheduler(sim, label)
                self.story_scheduler.page = self

        # if self.story_scheduler.paint_refresh:
        #     if self.gui_state != "repaint":  
        #         self.gui_state = "refresh"
        #     self.story_scheduler.paint_refresh = False
        try:
            self.story_scheduler.tick(sim)
        except BaseException as err:
            sbs.pause_sim()
            text_err = traceback.format_exc()
            text_err = text_err.replace(chr(94), "")
            self.errors.append(text_err)
            


        # if not self.story_scheduler.tick(sim):
        #     #self.story_runtime_node.mast.remove_runtime_node(self)
        #     Gui.pop(sim, event.client_id)
        #     # This should present "END OF Content mesage instead"
        #     return
        

        if len(self.errors) > 0:
            message = "PyMast errors\n".join(self.errors)
            sbs.send_gui_clear(event.client_id)
            if event.client_id != 0:
                sbs.send_client_widget_list(event.client_id, "", "")
            sbs.send_gui_text(event.client_id, message, "error", 0,0,100,100)
            self.gui_state = "errors"
            return
        
        sz = sbs.get_screen_size()
        if sz is not None and sz.y != 0:
            aspect_ratio = sz
            if (self.aspect_ratio.x != aspect_ratio.x or 
                self.aspect_ratio.y != aspect_ratio.y):
                self.aspect_ratio = sz
                for layout in self.layouts:
                    layout.aspect_ratio = aspect_ratio
                    layout.calc()
                self.gui_state = 'repaint'

        
        match self.gui_state:
            case  "repaint":
                sbs.send_gui_clear(event.client_id)
                if event.client_id != 0:
                    sbs.send_client_widget_list(event.client_id, self.console, self.widgets)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                for layout in self.layouts:
                    layout.present(sim,event)
                self.gui_state = "presenting"
            case  "refresh":
                for layout in self.layouts:
                    layout.present(sim,event)
                self.gui_state = "presenting"


    def on_message(self, sim, event):
        message_tag = event.sub_tag
        refresh = False        
        call_label = self.tag_map.get(message_tag)
        if call_label:
            call_label.on_message(sim, event)
        # else:
        for layout in self.layouts:
            layout.on_message(sim,event)
        if self.on_message_cb is not None:
            refresh = self.on_message_cb(self.story, sim, event)
        if refresh:
            self.gui_state = "refresh"
            self.present(sim, event)


    def on_event(self, sim, event):
        if self.story_scheduler is None:
            return
        self.story_scheduler.on_event(sim, event)

    def apply_style_name(self, style_name, layout_item):
        style_def = StyleDefinition.styles.get(style_name)
        self.apply_style_def(style_def, layout_item)
    def apply_style_def(self, style_def, layout_item):
        if style_def is None:
            return
        symbols = {}
        #task.get_symbols()
        aspect_ratio = self.aspect_ratio
        if isinstance(style_def, str):
            style_def = StyleDefinition.parse(style_def)
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
                values.append(LayoutAreaParser.compute(ast, symbols,ratio))
            layout_item.set_bounds(layout.Bounds(*values))

        height = style_def.get("row-height")
        if height is not None:
            height = LayoutAreaParser.compute(height, symbols,aspect_ratio.y)
            layout_item.set_row_height(height)        
        width = style_def.get("col-width")
        if width is not None:
            width = LayoutAreaParser.compute(height, symbols,aspect_ratio.x)
            layout_item.set_col_width(height)        
        padding = style_def.get("padding")
        if padding is not None:
            aspect_ratio = self.aspect_ratio
            i = 1
            values=[]
            for ast in padding:
                if i >0:
                    ratio =  aspect_ratio.x
                else:
                    ratio =  aspect_ratio.y
                i=-i
                values.append(LayoutAreaParser.compute(ast, symbols,ratio))
            while len(values)<4:
                values.append(0.0)
            layout_item.set_padding(layout.Bounds(*values))
