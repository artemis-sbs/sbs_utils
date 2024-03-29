
import sbs
from ..gui import Gui, Page, get_client_aspect_ratio
from ..helpers import FakeEvent, FrameContext
from ..procedural.inventory import get_inventory_value, set_inventory_value, has_inventory_value
from ..procedural.links import linked_to
from ..procedural.gui import gui_reroute_client
from ..procedural.execution import log
from ..agent import Agent
from ..pages import layout

from .maststory import  MastStory
from .maststoryscheduler import StoryScheduler


class TabControl(layout.Text):
    def __init__(self, tag, message, label, page) -> None:
        super().__init__(tag,message)
        self.page = page
        self.label = label

    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            if self.label is not None:
                self.page.gui_task.jump(self.label)



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
        #self.aspect_ratio = sbs.vec2(1024,768)
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
        self.main_screen_change_label = None
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

            # Start task defer so we can set gui_task appropriately
            self.gui_task = self.story_scheduler.run(client_id, self, label, cls.inputs, None, True)
            set_inventory_value(self.client_id, "GUI_TASK", self.gui_task)
            set_inventory_value(self.client_id, "GUI_PAGE", self)
            self.gui_task.tick_in_context()


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
                layout_obj.calc(self.client_id)
            
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
            self.pending_layouts = [layout.Layout(self.get_tag(), None, 0,0, 100, 90)]
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
        _layout = layout.Layout(self.get_tag(), None, 20,0, 100, 3)
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
        
        for change in self.on_change_items:
            if change.test():
                change.run()
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
        
        
        match self.gui_state:
            
            case  "repaint":
                my_sbs.send_gui_clear(event.client_id)
                my_sbs.send_client_widget_list(event.client_id, self.console, self.widgets)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed

                for layout_obj in self.layouts:
                    layout_obj.present(event)
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
                my_sbs.send_gui_complete(event.client_id)
            case  "refresh":
                for layout_obj in self.layouts:
                    layout_obj.calc(self.client_id)
                    layout_obj.present(event)
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
            case _:
                for change in self.on_change_items:
                    if change.test():
                        print("ON CHANGE - match")
                        change.run()
                        #self.gui_task.push_inline_block(self.gui_task.active_label, change.node.loc+1)
                        #self.gui_task.tick_in_context()
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
            runtime_node.on_message(event)
          
        for change in self.on_change_items:
            if change.test():
                change.run()
                return
            
        if clicked is not None:
            layout.Layout.clicked[self.client_id] = None
            for click in self.on_click:
                if click.click(clicked.click_tag):
                    return


            
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
                    if self.change_console_label:
                        self.gui_task.jump(self.change_console_label)
                        self.present(event)
        elif event.tag == "main_screen_change":
            if self.main_screen_change_label:
                ms =  linked_to(get_inventory_value(self.client_id,"assigned_ship"), "consoles") & has_inventory_value("CONSOLE_TYPE", "normal_main")
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
            # print(f"Aspect Event {self.aspect_ratio.x} {self.aspect_ratio .y}")
