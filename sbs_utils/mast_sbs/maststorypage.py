from ..gui import Gui, Page
from ..helpers import FakeEvent, FrameContext
from ..procedural.inventory import get_inventory_value, set_inventory_value, has_inventory_value
from ..procedural.links import linked_to
from ..procedural.gui.navigation import gui_reroute_client
from ..procedural.style import apply_control_styles

from ..procedural.execution import log
from ..agent import Agent
#from ..pages.layout import layout
from ..pages.layout.layout import Layout
from ..pages.layout.row import Row
from ..pages.layout.text import Text
from ..pages.layout.blank import Blank
from..fs import get_mission_name, get_startup_mission_name

from .story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel

from ..mast.maststory import  MastStory
from .maststoryscheduler import StoryScheduler

# Keep for runtime supprt
from . import story_nodes
from .mastmission import MissionLabel, StateMachineLabel
from . import mast_sbs_procedural


class TabControl(Text):
    def __init__(self, tag, message, label, page) -> None:
        super().__init__(tag,message)
        self.page = page
        self.label = label

    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            if self.label is not None:
                self.page.gui_task.jump(self.label)
                self.page.gui_task.tick_in_context()




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
        self.rebuild_tag = 20000
        self.is_processing_rebuild = False
        section = Layout(None, None, 0,0, 100, 90)
        section.tag = self.get_tag()
        self.pending_layouts = self.pending_layouts = []
        self.pending_row = self.pending_row = Row()
        self.pending_row.tag = self.get_tag()
        self.pending_tag_map = {}
        self.tag_map = {}

        #self.aspect_ratio = sbs.vec2(1024,768)
        self.client_id = None
        self.sbs = None
        self.ctx = None
        self.console = ""
        self.widgets = ""
        self.pending_console = ""
        self.pending_widgets = ""
        # self.pending_on_change_items= []
        # self.on_change_items= []
        self.pending_on_click = []
        self.on_click = []
        self.gui_task = None
        self.change_console_label = None
        self.main_screen_change_label = None
        self.disconnected = False
        self.gui_promise = None

        
        self.errors = []
        self.compiler_errors = []

        cls = self.__class__
        
        if cls.story is None:
            if cls.story is  None:
                cls.story = MastStory()
                if cls.__dict__.get("story_file"):
                    # import time
                    # t = time.perf_counter()
                    self.errors =  cls.story.from_file(cls.story_file, None)
                    # elapsed_time = time.perf_counter() - t

                    self.compiler_errors = self.errors
                    #if len(self.errors)>0:
                    #    cls.story = None
        
                    
        self.story = cls.story
        self.main = cls.__dict__.get("main", "main")
        self.main_server = cls.__dict__.get("main_server", self.main)
        self.main_client = cls.__dict__.get("main_client", self.main)
        

    def start_story(self, client_id):
        if self.story_scheduler is not None:
            return
        cls = self.__class__
        self.client_id == client_id
        if len(self.compiler_errors)==0:
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


            self.story_scheduler.page = self
            #
            # signals need this to be set
            #
            FrameContext.mast = self.story
            #self.story_scheduler.set_inventory_value('sim', ctx.sim)
            self.story_scheduler.set_inventory_value('client_id', client_id)
            self.story_scheduler.set_inventory_value('IS_SERVER', client_id==0)
            self.story_scheduler.set_inventory_value('IS_CLIENT', client_id!=0)
            # self.set_inventory_value('STORY_PAGE', page)

            # Start task defer so we can set gui_task appropriately
            self.gui_task = self.story_scheduler.run(client_id, self, label, cls.inputs, None, True)
            self.gui_task.is_gui_task = True
            set_inventory_value(self.client_id, "GUI_TASK", self.gui_task)
            set_inventory_value(self.client_id, "GUI_PAGE", self)
            self.gui_task.tick_in_context()


    @property
    def task(self):
        return self.gui_task


    def tick_gui_task(self):
        #
        # Called by gui right before present
        #
        if self.story_scheduler:
            self.story_scheduler.story_tick_tasks(self.client_id)

    def swap_gui_promise(self, pending):
        if self.gui_promise is not None:
            self.gui_promise.cancel()
        self.gui_promise = pending

    def swap_layout(self):
        # self.on_change_items= self.pending_on_change_items
        # self.pending_on_change_items = []
        self.gui_task.swap_on_change()
        self.on_click = self.pending_on_click
        self.pending_on_click = []
        self.layouts = self.pending_layouts
        self.tag_map = self.pending_tag_map
        self.console = self.pending_console
        # This forces them is a certain order
        self.add_console_widget("")
        self.widgets = self.pending_widgets

        # TODO: this should be one thing
        # convert console tabs to procedural
        self.gui_queue_console_tabs()
        
        
        self.rebuild_tag = self.tag
        self.tag = 10000
        
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.calc(self.client_id)
            
            section = Layout(None, None, 0,0, 100, 90)
            section.tag = self.get_tag()
            self.pending_layouts = [section]
            self.pending_row = Row()
            self.pending_row.tag = self.get_tag()
            self.pending_tag_map = {}
            self.pending_console = ""
            self.pending_widgets = ""
        
        self.gui_state = 'repaint'
        Gui.dirty(self.client_id)


    def get_tag(self):
        if self.is_processing_rebuild:
            self.rebuild_tag += 1
            return str(self.rebuild_tag)

        self.tag += 1
        return str(self.tag)

    def add_row(self):
        if not self.pending_layouts:
            self.pending_layouts = [Layout(self.get_tag(), None, 0,0, 100, 90)]
        if self.pending_row:
            if len(self.pending_row.columns):
                self.pending_layouts[-1].add(self.pending_row)
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        self.pending_row = Row()
        # Rows have tags for background and/or clickable
        self.pending_row.tag = self.get_tag()

    def add_tag(self, layout_item, runtime_node):
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        if hasattr(layout_item, 'tag'):
            self.pending_tag_map[layout_item.tag] = (layout_item, runtime_node)

    def push_sub_section(self, style, layout_item, is_rebuild):
        #
        # If there is even an empty row, we need to cache it away for later
        #
        if is_rebuild:
            self.is_processing_rebuild = True

        if self.pending_row:
            if len(self.pending_layouts) != 0:
                self.pending_layouts[-1].add(self.pending_row)
            else:
                print("Lost main layout?")
            self.pending_row = None
        
        if layout_item is None:
            self.add_section()
            layout_item = self.get_pending_layout() 
            apply_control_styles(".section", style, layout_item, self.gui_task)
            self.add_row()
        else:
            self.pending_layouts.append(layout_item)
            rows = layout_item.rows
            if len(rows)>0:
                p_row = rows.pop()
                self.pending_row = p_row

        return layout_item
        

    def pop_sub_section(self, add_content, is_rebuild):
        if is_rebuild:
            self.is_processing_rebuild = False
            self.tag_map.update(self.pending_tag_map)
            self.pending_tag_map = {}
            
            self.on_click.extend(self.pending_on_click)
            self.pending_on_click = []
        # Finish the layout for the sub section
        if self.pending_row:
            if len(self.pending_row.columns):
                self.pending_layouts[-1].add(self.pending_row)

        sub = self.pending_layouts.pop()
        p_row = None
        if len(self.pending_layouts)>0:
            rows = self.pending_layouts[-1].rows
            if len(rows)>0:
                p_row = rows.pop()
                if add_content:
                    p_row.add(sub)
                self.pending_row = p_row
                return
        # If get here started pretty much empty
        if add_content:
            self.add_content(sub, None)


    def add_content(self, layout_item, runtime_node):
        if self.pending_layouts is None:
            self.add_row()

        self.add_tag(layout_item, runtime_node)

        self.pending_row.add(layout_item)

    # def add_on_change(self, runtime_node):
    #     self.pending_on_change_items.append(runtime_node)

    def add_on_click(self, runtime_node):
        self.pending_on_click.append(runtime_node)


    def set_widget_list(self, console,widgets):
        self.pending_console = console
        self.pending_widgets = widgets

    def activate_console(self, console):
        self.pending_console = console

    def add_console_widget(self, widget):
        if  self.pending_widgets=="":
            self.pending_widgets = widget
        elif widget=="":
            pass
        else:
            self.pending_widgets += "^"+widget
        widgets = set(self.pending_widgets.split("^"))
        new_widgets = ""
        widgets_2d = ""
        widgets_3d = ""
        delim = ""
        for widget in set(widgets):
            if widget == "3dview":
                widgets_3d = widget+"^"
            elif widget in ["2dview","weapon_2d_view", "science_2d_view"]:
                widgets_2d = widget + delim + widgets_2d
                delim = "^"
            else:
                new_widgets = new_widgets + delim + widget
                delim = "^"
        self.pending_widgets = widgets_3d+ widgets_2d+new_widgets
    
    def add_section(self, tag= None):
        if tag is None:
            tag = self.get_tag()

        section = Layout(tag, None, 0,0, 100, 90)
        
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

    def get_path(self):
        # The pending console is the one the gui is going to present
        return f"gui/{self.pending_console}"

    def set_button_layout(self, layout, gui_promise):
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
        all_tabs = all_ship_tabs.get("any", {})
        ship_id = FrameContext.context.sbs.get_ship_of_client(self.client_id) 
            #get_inventory_value(self.client_id, "assigned_ship", None)
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
            set_inventory_value(self.client_id, "CONSOLE_TYPE", console)
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
        _layout = Layout(self.get_tag(), None, 20,0, 100, 3)
        _row = Row()
        #
        # MAKE the tab button 40px
        #
        apply_control_styles(".row", "row-height:35px", _row, self.gui_task)
        _layout.add(_row)

        # Make spots for a certain amount of tabs
        count = 0
        tabs= set()
        for tab in all_tabs:
            tab_label = all_tabs[tab]
            if isinstance(tab_label, GuiTabDecoratorLabel):
                if not tab_label.test(self.gui_task):
                    continue
            
            tab_text = tab
            if tab == "__back_tab__":
                tab_text = back_tab
            if tab_text in tabs:
                continue
            tabs.add(tab_text)
            count+= 1
            msg = f"justify:center;color:black;$text:{tab_text};"

            button = TabControl(self.get_tag(),msg, all_tabs[tab], self) # Jump label all_tabs[tab]
            button.click_text = tab_text
            button.click_color = "#FFF"
            #self.click_font = None
            button.click_tag = self.get_tag()

            if tab_text == back_tab:
                button.background_color = "#fff9"
                _row.add(button)        
            else:
                button.background_color = "#fff3"
                _row.add_front(button)
            
        
        spots = 6
        blanks = spots-count
        if blanks <0: blanks = 0
        for _ in range(blanks):
            _row.add_front(Blank())

        #_layout.calc()
        self.pending_layouts.append(_layout)


    def update_props_by_tag(self, tag, props, test):
        # get item by tag
        item = self.tag_map.get(tag)
        # call update
        if item is None:
            return
        #
        # Test allows one to pass values they need to be 
        # equal to 
        # Added for example to make sure the ship picker
        # only updates if the ship is the same
        #
        if test is not None:
            for k in test:
                expected = test.get(k)

                this = self.gui_task.get_variable(k)
                if this != expected:
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
        
        # for change in self.on_change_items:
        #     if change.test():
        #         change.run()
        #         return
        if len(self.compiler_errors) > 0:
            message = "".join(self.compiler_errors)
            message = message.replace(";", "~")
            message = "$text: Mast Compiler Errors\n" + message.replace(",", ".")
            my_sbs.send_gui_clear(event.client_id,"")
            if event.client_id != 0:
                my_sbs.send_client_widget_list(event.client_id, "", "")
            my_sbs.send_gui_text(event.client_id,"", "error", message,  0,0,100,100)
            my_sbs.send_gui_button(event.client_id,"", "$Error$rerun", "$text:Attempt Rerun", 50, 90, 70, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$startup", "$text:Run startup", 75, 90, 99, 99)
            self.gui_state = "errors"
            my_sbs.send_gui_complete(event.client_id,"")
            return
        

        if self.story_scheduler is None:
            self.start_story(event.client_id)
        else:
            if len(self.story_scheduler.errors) > 0:
                self.errors = self.story_scheduler.errors
                self.story_scheduler.errors = []
            else:
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
            message = "$text: Mast Compiler Errors\n" + message.replace(",", ".")
            my_sbs.send_gui_clear(event.client_id,"")
            if event.client_id != 0:
                my_sbs.send_client_widget_list(event.client_id, "", "")
            my_sbs.send_gui_text(event.client_id,"", "error", message,  0,0,100,100)
            my_sbs.send_gui_button(event.client_id,"", "$Error$resume", "$text:Attempt Resume", 0, 90, 20, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$pause", "$text:Attempt pause", 25, 90, 45, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$rerun", "$text:Attempt Rerun", 50, 90, 70, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$startup", "$text:Run startup", 75, 90, 99, 99)
            self.gui_state = "errors"
            my_sbs.send_gui_complete(event.client_id,"")
            return
        
        
        match self.gui_state:
            
            case  "repaint":
                my_sbs.send_gui_clear(event.client_id,"")
                my_sbs.send_client_widget_list(event.client_id, self.console, self.widgets)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed

                for layout_obj in self.layouts:
                    layout_obj.present(event)
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
                my_sbs.send_gui_complete(event.client_id,"")
            case  "refresh":
                my_sbs.send_gui_clear(event.client_id,"")
                for layout_obj in self.layouts:
                    #layout_obj.calc(self.client_id)
                    layout_obj.invalidate_all()
                    layout_obj.represent(event)
                my_sbs.send_gui_complete(event.client_id,"")
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"

    def on_message(self, event):
        if event.client_id != self.client_id:
            return
        
        message_tag = event.sub_tag
        if message_tag == "$Error$resume":
            self.errors = []
            FrameContext.context.sbs.resume_sim()
            self.gui_state = "paint"
            self.present(event)
            return
        
        if message_tag == "$Error$pause":
            self.errors = []
            FrameContext.context.sbs.pause_sim()
            self.gui_state = "paint"
            self.present(event)
            return
        
        if message_tag == "$Error$rerun":
            self.errors = []
            mission = get_mission_name()
            FrameContext.context.sbs.run_next_mission(mission)
            self.gui_state = "paint"
            self.present(event)
            return
        
        if message_tag == "$Error$startup":
            self.errors = []
            start_mission = get_startup_mission_name()
            if start_mission is not None:
                FrameContext.context.sbs.run_next_mission(start_mission)
            self.gui_state = "paint"
            self.present(event)
            return
            
        

        clicked = None
        # Process layout first
        for section in self.layouts:
            section.on_message(event)

        clicked = Layout.clicked.get(self.client_id)

        runtime_node = self.tag_map.get(message_tag)
        
        refresh = False
        if runtime_node is not None and runtime_node[1] is not None:
            # tuple layout and runtime node
            runtime_node = runtime_node[1]
            runtime_node.on_message(event)
          
        # for change in self.on_change_items:
        #     if change.test():
        #         change.run()
        #         return
        self.gui_task.run_on_change()
            
        if clicked is not None:
            Layout.clicked[self.client_id] = None
            for click in self.on_click:
                if click.click(clicked.click_tag):
                    return
            
        if refresh:
            self.gui_state = "refresh"
            self.present(event)

        

    def on_event(self, event):
        if event.client_id != self.client_id:
            return
        
        if self.story_scheduler is None:
            return
        
        if event.tag =="mast:client_disconnect":
            self.disconnected = True
            self.tick_gui_task()
            # remove scheduler
            self.story_scheduler.mast.remove_scheduler(self.story_scheduler)
        elif event.tag == "client_change":
            if event.sub_tag == "change_console":
                if self.change_console_label:
                    self.gui_task.jump(self.change_console_label)
                    self.gui_task.tick_in_context()
                    self.present(event)
        elif event.tag == "main_screen_change":
            if self.main_screen_change_label:
                # get_inventory_value(self.client_id,"assigned_ship")
                _ship = FrameContext.context.sbs.get_ship_of_client(self.client_id)
                ms =  linked_to(_ship, "consoles") & has_inventory_value("CONSOLE_TYPE", "normal_main")
                # 3d_view, info, data - affects layout
                # front, left, right, back - engine controlled
                # 3d (chase, first_person, tracking) 2d (short, long) - engine controlled
                
                for m in ms:
                    t = get_inventory_value(m, "CONSOLE_TYPE", "not set")
                    log(f"Got here {len(ms)} {t}", "mast:internal")
                    gui_reroute_client(m, self.main_screen_change_label, {
                        "MAIN_SCREEN_VIEW": event.sub_tag,
                        "MAIN_SCREEN_FACING": event.value_tag,
                        "MAIN_SCREEN_MODE": event.extra_tag
                    })

        elif event.tag == "screen_size":
            save = FrameContext.page
            FrameContext.page = self
            self.gui_state = "refresh"
            self.present(event)
            FrameContext.page = save
            
