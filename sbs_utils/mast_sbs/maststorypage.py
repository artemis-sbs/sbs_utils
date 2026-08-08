from ..gui import Gui, Page
from ..helpers import FakeEvent, FrameContext, FrameContextOverride
from ..procedural.inventory import get_inventory_value, set_inventory_value, has_inventory_value
from ..procedural.links import linked_to
from ..procedural.gui.navigation import gui_reroute_client
from ..procedural.style import apply_control_styles

from ..procedural.signal import signal_emit
from ..procedural.execution import log
from ..agent import Agent
#from ..pages.layout import layout
from ..pages.layout.layout import Layout
from ..pages.layout.row import Row
from ..pages.layout.text import Text
from ..pages.layout.blank import Blank
from ..pages.layout.dropdown import Dropdown
from..fs import get_mission_name, get_startup_mission_name, is_dev_build

from .story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel

from ..mast.maststory import  MastStory
from .maststoryscheduler import StoryScheduler

# Keep for runtime supprt
from . import story_nodes
#from .mastmission import MissionLabel, StateMachineLabel
from . import mast_sbs_procedural


class TabControl(Text):
    def __init__(self, tag, message, label, page) -> None:
        super().__init__(tag,message)
        self.page = page
        self.label = label
        apply_control_styles(None, "margin:1px,0,0,0;", self, page.task)

    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            if self.label is not None:
                self.page.gui_task.jump(self.label)
                self.page.gui_task.tick_in_context()




# How many tabs the strip shows before the rest go into an overflow menu.
#
# The strip is a FIXED width (20%..100%) divided evenly, so it never dropped a tab and
# never scrolled - it just kept making them narrower. At 18 registered tabs that is 4.4%
# each, about 85px on a 1920 screen, and "engineering" needs roughly 130. The engine does
# not clip text, so the labels drew straight over their neighbours: the tabs were all
# present and all illegible, which is why adding tabs made EXISTING ones unreadable
# (PRM-26).
#
# Eight keeps every visible tab at 10% (~192px), comfortably wider than the longest label
# we ship.
TAB_MAX_VISIBLE = 8


class TabOverflow(Dropdown):
    """The tabs that did not fit, as a menu. Selecting one jumps to it exactly as
    clicking its tab would - the same two lines TabControl runs."""

    def __init__(self, tag, props, labels, page) -> None:
        super().__init__(tag, props)
        self.labels = labels
        self.page = page

    def on_message(self, event):
        if event.sub_tag == self.tag:
            label = self.labels.get(event.value_tag)
            if label is not None:
                self.page.gui_task.jump(label)
                self.page.gui_task.tick_in_context()
                return
        super().on_message(event)


class StoryPage(Page):
    tag = 0
    story_file = None
    inputs = None
    story = None
    def __init__(self) -> None:
        self.gui_state = 'repaint'
        self.story_scheduler = None
        self.layouts = []
        self.tag = 100
        self.rebuild_tag = 200
        self.is_processing_rebuild = False
        section = Layout(None, None, 0,0, 100, 90)
        section.tag = self.get_tag()
        self.pending_layouts = self.pending_layouts = []
        self.pending_row = self.pending_row = Row()
        self.pending_row.tag = self.get_tag()
        self.pending_tag_map = {}
        self.tag_map = {}
        self.pending_gui = True
        # Active gui_grid() contexts (a stack, so grids can nest). Each entry is
        # {"columns": N, "count": M}; add_content auto-breaks to a new row every N.
        self._grid_stack = []

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
        # Optional overrides used by web-page sessions (Gui.web_page_open):
        # when set, start_story starts the GUI task at this label with these
        # variables instead of the default main/main_client label.
        self.start_label = None
        self.start_data = None
        self.web_path = None
        self.change_console_label = None
        self.main_screen_change_label = None
        self.disconnected = False
        self.gui_promise = None
        self.info_panel = None
        self.pending_info_panel = None
        # Overlay slots (drawn on top of the page, independent of the layout tree).
        # Lazily imported to avoid a circular import with procedural.gui.
        from ..procedural.gui.overlay import OverlayManager
        self.overlays = OverlayManager(self)

        
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
                    cls.story.compiler_errors = self.errors
                    #if len(self.errors)>0:
                    #    cls.story = None
        
                    
        self.story = cls.story
        self.compiler_errors = self.story.compiler_errors
        self.main = cls.__dict__.get("main", "main")
        self.main_server = cls.__dict__.get("main_server", self.main)
        self.main_client = cls.__dict__.get("main_client", self.main)
        

    def start_story(self, client_id):
        if self.story_scheduler is not None:
            return
        cls = self.__class__
        self.client_id = client_id
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

            # Web-page sessions start at a specific //web/<path> route label
            if self.start_label is not None:
                label = self.start_label

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
            # Seed web-page query/data variables before the first tick
            if self.start_data:
                for k in self.start_data:
                    self.gui_task.set_variable(k, self.start_data[k])
            set_inventory_value(self.client_id, "GUI_TASK", self.gui_task)
            set_inventory_value(self.client_id, "GUI_PAGE", self)

            # Use a Fake event so the client_id and client page are correct
            e_restore = FrameContext.context.event
            e = FakeEvent(client_id, "__STORY_PAGE_INIT")
            FrameContext.context.event = e
            self.gui_task.tick_in_context()
            FrameContext.context.event = e_restore


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

    def on_end_presenting(self):
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.on_end_presenting(self.client_id)

    def on_begin_presenting(self):
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.on_begin_presenting(self.client_id)


    def swap_layout(self):
        # self.on_change_items= self.pending_on_change_items
        # self.pending_on_change_items = []
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.on_end_presenting(self.client_id)


        self.gui_task.swap_on_change()
        self.on_click = self.pending_on_click
        self.pending_on_click = []
        self.layouts = self.pending_layouts
        self.tag_map = self.pending_tag_map
        self.console = self.pending_console
        self.info_panel = self.pending_info_panel
        # This forces them is a certain order
        self.add_console_widget("")
        self.widgets = self.pending_widgets

        # TODO: this should be one thing
        # convert console tabs to procedural
        self.gui_queue_console_tabs()
        
        
        
        self.tag = self.rebuild_tag + 100 % 100000
        self.rebuild_tag = self.tag + 2000
        
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.calc(self.client_id)
                layout_obj.on_begin_presenting(self.client_id)
            
            section = Layout(None, None, 0,0, 100, 90)
            section.tag = self.get_tag()
            self.pending_layouts = [section]
            self.pending_row = Row()
            self.pending_row.tag = self.get_tag()
            self.pending_tag_map = {}
            self.pending_console = ""
            self.pending_widgets = ""
            self.pending_info_panel = None
            self.pending_gui = True
        
        self.gui_state = 'repaint'
        Gui.dirty(self.client_id)

    def on_new_gui(self):
        # print("NEW GUI")
        self.pending_gui = False
        from ..procedural.gui.property_listbox import gui_reset_variables
        gui_reset_variables(self.gui_task)
        # Restore the options button to what the MISSION asked for, not to a
        # hardcoded 0. This fires on every new GUI (from add_tag, on the first
        # tagged widget of a build), so a hardcoded restore made it impossible
        # for a story page to hold the button transparent -- the setting was
        # always taken away a moment after it was made. Defaults to 0, so a
        # mission that never calls gui_options_button() is unaffected.
        from ..procedural.gui.options_button import gui_options_button_flag
        FrameContext.context.sbs.transparent_options_button(
            self.client_id, gui_options_button_flag(self.client_id))
        for sub_task in self.gui_task.sub_tasks:
            if sub_task.has_role("end_on_new_gui"):
                sub_task.end()
        # 
        # Clear tags
        #
        # Need to purge any "on signal" commands
        #
        self.story.signal_unregister_all_inline(self.gui_task)



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
            self.pending_gui = True
        self.pending_row = Row()
        # Rows have tags for background and/or clickable
        self.pending_row.tag = self.get_tag()

    def add_tag(self, layout_item, runtime_node):
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
            self.pending_gui = True

        if self.pending_gui == True:
            self.on_new_gui()
        

        if hasattr(layout_item, 'tag'):
            self.pending_tag_map[layout_item.tag] = (layout_item, runtime_node)
        if hasattr(layout_item, 'click_tag'):
            if layout_item.click_tag is not None:
                self.pending_tag_map[layout_item.click_tag] = (layout_item, runtime_node)

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
        if self.pending_row is None:
            self.add_row()
        self.add_tag(layout_item, runtime_node)

        self.pending_row.add(layout_item)

        # gui_grid() auto-flow: after every N cells, break to a fresh row so
        # items lay out as an N-column grid. Inert unless a grid is active.
        if self._grid_stack:
            grid = self._grid_stack[-1]
            grid["count"] += 1
            if grid["count"] % grid["columns"] == 0:
                self.add_row()

    def grid_begin(self, columns):
        """Enter a gui_grid() context: subsequent add_content()s flow into an
        ``columns``-wide grid, auto-breaking rows. Nestable."""
        columns = max(1, int(columns))
        self.add_row()                       # start the grid on a clean row
        self._grid_stack.append({"columns": columns, "count": 0})

    def grid_end(self):
        """Leave the current gui_grid() context, padding the final row with Hole
        spacers so its columns stay aligned, then start a fresh row."""
        if not self._grid_stack:
            return
        grid = self._grid_stack.pop()
        row = self.pending_row
        if row is not None and 0 < len(row.columns) < grid["columns"]:
            from ..pages.layout.hole import Hole
            while len(row.columns) < grid["columns"]:
                row.add(Hole())
        self.add_row()                       # content after the grid isn't in it

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
        enabled_tabs = get_inventory_value(self.client_id, "console_tabs", {})

        back_tab = get_inventory_value(self.client_id, "__back_tab__")
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

        # Collect FIRST, emit second. The strip has to know how many tabs there are before
        # it can decide which of them fit, and the old loop added each one as it went.
        entries = []          # (text, label) in registration order
        back_entry = None
        tabs = set()
        for tab in GuiTabDecoratorLabel.all:
            # Only use enabled tabs
            if not enabled_tabs.get(tab):
                continue
            tab_label = GuiTabDecoratorLabel.all[tab]
            if isinstance(tab_label, GuiTabDecoratorLabel):
                if not tab_label.test(self.gui_task):
                    continue

            tab_text = tab
            if tab == back_tab:
                tab_text = back_tab
            if tab_text in tabs:
                continue
            tabs.add(tab_text)
            if tab_text == back_tab:
                back_entry = (tab_text, tab_label)
            else:
                entries.append((tab_text, tab_label))

        def _button(text, label, is_back):
            msg = f"justify:center;color:black;$text:{text};"
            button = TabControl(self.get_tag(), msg, label, self)
            button.click_text = text
            button.click_color = "#FFF"
            button.click_tag = self.get_tag()
            button.background_color = "#999" if is_back else "#333"
            return button

        # More than fits? Keep the first few and put the rest behind one menu. The BACK
        # tab is never overflowed - it is how you leave, so it stays where it always is.
        visible, overflow = entries, []
        reserved = (1 if back_entry else 0) + 1        # back tab + the menu itself
        if len(entries) + (1 if back_entry else 0) > TAB_MAX_VISIBLE:
            keep = max(1, TAB_MAX_VISIBLE - reserved)
            visible, overflow = entries[:keep], entries[keep:]

        for text, label in visible:
            _row.add_front(_button(text, label, False))
        if overflow:
            names = ", ".join(t for t, _ in overflow)
            menu = TabOverflow(self.get_tag(),
                               f"text: More ({len(overflow)}); list: {names}",
                               {t: l for t, l in overflow}, self)
            _row.add_front(menu)
        if back_entry:
            _row.add(_button(back_entry[0], back_entry[1], True))

        count = len(visible) + (1 if back_entry else 0) + (1 if overflow else 0)
        # Pad to six so a console with only a few tabs keeps them the size they have
        # always been rather than stretching each across the whole strip.
        spots = 6
        blanks = spots-count
        if blanks <0: blanks = 0
        for _ in range(blanks):
            _row.add_front(Blank())

        #_layout.calc()
        self.pending_layouts.append(_layout)
        # Clear up tabs for the next GUI
        set_inventory_value(self.client_id, "console_tabs", {})
        set_inventory_value(self.client_id, "__back_tab__", None)




    def update_props_by_tag(self, tag, props, test):
        # get item by tag
        item = self.tag_map.get(tag)
        present = True
        # call update
        if item is None:
            present = False
            item = self.pending_tag_map.get(tag)
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
        if present:
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
            Gui.root_clear(my_sbs, event.client_id)
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
                    if is_dev_build():
                        raise Exception("EDGE CASE: Did you set END or Yield the last GUI Task?")
                    else:
                        Gui.pop(event.client_id)
                        return
            

        if len(self.errors) > 0:
            message = "".join(self.errors)
            message = message.replace(";", "~")
            message = "$text: Mast Compiler Errors\n" + message.replace(",", ".")
            Gui.root_clear(my_sbs, event.client_id)
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
        
        
        # An overlay slot holding content whose sub-region was revoked by a root
        # clear from outside this page's own repaint (a page pop, an error
        # screen). Only "repaint"/"refresh" run present_all, so any other state
        # would leave the card gone for the rest of its life.
        if (self.overlays.slots and self.gui_state not in ("repaint", "refresh")
                and self.overlays.needs_repaint()):
            self.gui_state = "repaint"

        match self.gui_state:

            case  "repaint":
                # Bumps the root epoch BEFORE present_all below, so the slots
                # establish into the epoch they will be checked against.
                Gui.root_clear(my_sbs, event.client_id)
                #
                # Only when it CHANGED. This call is how the ENGINE learns which
                # native widgets a console has, and acting on it means building
                # them (2d view, waterfall, ship_data, grid...). swap_layout sets
                # gui_state='repaint' on EVERY gui rebuild, so re-sending
                # unconditionally asked the engine to redo that work every time a
                # console's MAST screen rebuilt. Redundant either way; whether it
                # was also what made consoles slow to appear was NOT settled -
                # the cost may simply be having widgets up at all, which is the
                # engine's side of the line and not something we can send our
                # way out of.
                #
                # Safe to skip: send_gui_clear does NOT drop the engine's
                # widgets. The "refresh" branch below clears and re-presents
                # without ever re-sending the list, and consoles keep their
                # widgets across a resize, which is proof of it.
                #
                widget_list = (self.console, self.widgets)
                if Gui.widget_list_sent.get(event.client_id) != widget_list:
                    Gui.widget_list_sent[event.client_id] = widget_list
                    my_sbs.send_client_widget_list(event.client_id, self.console, self.widgets)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed

                for layout_obj in self.layouts:
                    layout_obj.present(event)
                # Overlays draw last (on top), re-emitted every repaint so they
                # survive the page's root clear.
                self.overlays.present_all(event)
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
                my_sbs.send_gui_complete(event.client_id,"")
            case  "refresh":
                Gui.root_clear(my_sbs, event.client_id)
                for layout_obj in self.layouts:
                    #layout_obj.calc(self.client_id)
                    layout_obj.invalidate_all()
                    layout_obj.represent(event)
                self.overlays.present_all(event)
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
        with FrameContextOverride(self.gui_task, self):
            for section in self.layouts:
                section.on_message(event)

        clicked = Layout.clicked.get(self.client_id)

        runtime_node = self.tag_map.get(message_tag)

        refresh = False
        if runtime_node is not None and runtime_node[1] is not None:
            # tuple layout and runtime node
            runtime_node = runtime_node[1]
            with FrameContextOverride(self.gui_task, self):
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
            signal_emit("client_disconnect", {"client_id": self.client_id})
            self.disconnected = True
            self.tick_gui_task()
            # remove scheduler
            self.story_scheduler.mast.remove_scheduler(self.story_scheduler)
        elif event.tag == "client_change":
            if event.sub_tag == "change_console":
                if self.change_console_label:
                    # This is a bit of a hack to clear the properties
                    # List box
                    _ship = FrameContext.context.sbs.get_ship_of_client(self.client_id)
                    if _ship is not None and _ship != 0:
                        FrameContext.context.sbs.send_comms_selection_info(_ship, "", "white", "static")
                    from ..procedural.gui.property_listbox import gui_reset_variables
                    with FrameContextOverride(self.gui_task, self):
                        gui_reset_variables(self.gui_task)
                        self.gui_task.jump(self.change_console_label)
                        self.gui_task.tick_in_context()
                        self.present(event)
        elif event.tag == "main_screen_change":
            if self.main_screen_change_label:
                # get_inventory_value(self.client_id,"assigned_ship")
                _ship = FrameContext.context.sbs.get_ship_of_client(self.client_id)
                ms =  linked_to(_ship, "consoles") & (has_inventory_value("CONSOLE_TYPE", "mainscreen")) # | has_inventory_value("CONSOLE_TYPE", "normal_main"))
                # 3d_view, info, data - affects layout
                # front, left, right, back - engine controlled
                # 3d (chase, first_person, tracking) 2d (short, long) - engine controlled
                
                for m in ms:
                    #t = get_inventory_value(m, "CONSOLE_TYPE", "not set")
                    #log(f"Got here {len(ms)} {t}", "mast:internal")
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
            
