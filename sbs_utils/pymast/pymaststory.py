from ..tickdispatcher import TickDispatcher
from ..consoledispatcher import ConsoleDispatcher
from ..lifetimedispatcher import LifetimeDispatcher
from ..damagedispatcher import DamageDispatcher
from ..engineobject import EngineObject
from ..gui import Page, Gui
from sbs_utils import faces
from ..pages import layout
from .. import query
import sbs
import inspect
from .pollresults import PollResults
from .pymastscience import PyMastScience
from .pymastcomms import PyMastComms
from .pymasttask import PyMastTask, DataHolder
from .pymastscheduler import PyMastScheduler
from .pymaststorypage import CodePusher
import logging
from io import StringIO
from ..engineobject import EngineObject, get_story_id



class PyMastStory(EngineObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # This style of init makes it more mixin friendly
        self.schedulers = []
        self.remove_scheduler = set()
        self.shared = self #Alias for scoping
        self.tick_task = None
        self.vars = DataHolder()
        self.id = get_story_id()
        self.add()


    def enable(self, ctx, delay=0, count=None):
        if self.tick_task is None:
            self.tick_task = TickDispatcher.do_interval(ctx, self, delay, count)

    def add_scheduler(self, ctx, label):
        self.enable(ctx)
        sched = PyMastScheduler(self, label)
        self.schedulers.append(sched)
        return sched


    def delay(self,  seconds=0, minutes=0, use_sim=False):
        return self.task.delay(seconds, minutes, use_sim)
    
    
    def await_science(self, player, npc, scans):
        return self.task.await_science(player, npc, scans)
    
    
    def schedule_task(self, label):
        return self.scheduler.schedule_task(label)


    def jump(self, label):
        return self.task.jump(label)
    def push(self, label):
        return self.task.push(label)
    def pop(self):
        return self.task.pop()

    def disable(self):
        if self.tick_task is not None:
            self.tick_task.stop()
            self.tick_task = None

    def is_running(self):
        return len(self.schedulers)!=0

    def __call__(self, ctx, sched=None):
        self.sim = ctx.sim
        self.ctx = ctx
        for sched in self.schedulers:
            self.scheduler = sched
            sched.tick(ctx)
            if len(sched.tasks) == 0:
                self.remove_scheduler.add(sched)
        for finished in self.remove_scheduler:
            self.schedulers.remove(finished)
        self.remove_scheduler.clear()
        if len(self.schedulers)==0:
            self.disable()
        self.sim = None
        self.ctx = None


    def END(self):
        if self.task is not None:
            self.task.end()
            
    # Having this confused mixins
    # def start(self):
    #     pass
    # Having this confused mixins
    # def start_server(self):
    #     pass
    # Having this confused mixins
    # def start_client(self):
    #     pass

    #
    # Routing
    #
    def route_change_console(self, label):
        if self.task and self.task.page:
            self.task.page.change_console_label = label

    def route_comms_select(self, label):
        """
        route_comms

        define a label to use with a new task if the comms is not handled
        """

        story = self
        def handle_dispatch(ctx, an_id, event):
            console = "comms_target_UID"
            if query.has_link_to(event.origin_id, f"__route{console}", event.selected_id):
                return

            # I it reaches this, there are no pending comms handler
            # Create a new task and jump to the routing label
            task = story.schedule_task(label)
            task.COMMS_ORIGIN_ID = event.origin_id
            task.COMMS_SELECTED_ID = event.selected_id
            #
            # Kick the tick
            #
            task.tick(ctx)
            if not task.done:
                query.link(event.origin_id, f"__route{console}", event.selected_id)
            #
            #
        ConsoleDispatcher.add_default_select("comms_target_UID", handle_dispatch)
            
    def route_grid_select(self, label):
        """
        route_comms

        define a label to use with a new task if the comms is not handled
        """
        story = self
        def handle_dispatch(sim, an_id, event):
            console = "grid_target_UID"
            if query.has_link_to(event.origin_id, f"__route{console}", event.selected_id):
                return
            # I it reaches this, there are no pending comms handler
            # Create a new task and jump to the routing label
            task = story.schedule_task(label)
            task.COMMS_ORIGIN_ID = event.origin_id
            task.COMMS_SELECTED_ID = event.selected_id
            task.COMMS_ROUTED = True
            #
            # Kick the tick
            #
            task.tick(sim)
            #
            #
            if not task.done:
                query.link(event.origin_id, f"__route{console}", event.selected_id)

        ConsoleDispatcher.add_default_select("grid_selected_UID", handle_dispatch)

    def route_science_select(self, label):
        """
        route_comms

        define a label to use with a new task if the comms is not handled
        """
        story = self
        def handle_dispatch(sim, an_id, event):
            console = "science_target_UID"
            if query.has_link_to(event.origin_id, f"__route{console}", event.selected_id):
                return
            # I it reaches this, there are no pending comms handler
            # Create a new task and jump to the routing label
            task = story.schedule_task(label)
            task.SCIENCE_ORIGIN_ID = event.origin_id
            task.SCIENCE_SELECTED_ID = event.selected_id
            task.SCIENCE_ROUTED = True
            #
            # Kick the tick
            #
            task.tick(sim)
            #
            #
            if not task.done:
                query.link(event.origin_id, f"__route{console}", event.selected_id)
        ConsoleDispatcher.add_default_select("science_target_UID", handle_dispatch)

    def route_spawn(self, label):
        """
        route_spawn

        define a label to use with a new task items are spawned
        """
        story = self
        def handle_dispatch(ctx, so):
            # I it reaches this, there are no pending comms handler
            # Create a new task and jump to the routing label
            task = story.schedule_task(label)
            task.SPAWNED_ID = so.id
            task.SPAWNED_ROUTED = True
            #
            # Kick the tick
            #
            task.tick(ctx)
            #
            #
        LifetimeDispatcher.add_spawn(handle_dispatch)

    def route_grid_spawn(self, label):
        """
        route_spawn

        define a label to use with a new task items are spawned
        """
        story = self
        def handle_dispatch(ctx, so):
            # I it reaches this, there are no pending comms handler
            # Create a new task and jump to the routing label
            task = story.schedule_task(label)
            task.SPAWNED_ID = so.id
            task.SPAWNED_ROUTED = True
            #
            # Kick the tick
            #
            task.tick(ctx)
            #
            #
        LifetimeDispatcher.add_spawn_grid(handle_dispatch)

    def route_damage_source(self, label):
        """
        route_damage_source

        define a label to use with a new task items are spawned
        """
        story = self
        
        def handle_damage(ctx, event):
            # Need point? amount
            task = story.schedule_task(label)
            task.DAMAGE_SOURCE_ID = event.origin_id
            task.DAMAGE_TARGET_ID = event.selected_id
            task.DAMAGE_ORIGIN_ID = event.origin_id
            task.DAMAGE_SELECTED_ID = event.selected_id
            task.EVENT = event
            task.DAMAGE_ROUTED = True
            
            #
            # Kick the tick
            #
            task.tick(ctx)
            #
            #
        DamageDispatcher.add_source(handle_damage)


    def route_damage_target(self, label):
        """
        route_damage_source

        define a label to use with a new task items are spawned
        """
        story = self
        
        def handle_damage(ctx, event):
            # Need point? amount
            task = story.schedule_task(label)
            task.DAMAGE_SOURCE_ID = event.origin_id
            task.DAMAGE_TARGET_ID = event.selected_id
            task.DAMAGE_ORIGIN_ID = event.origin_id
            task.DAMAGE_SELECTED_ID = event.selected_id
            task.EVENT = event
            task.DAMAGE_ROUTED = True
            
            #
            # Kick the tick
            #
            task.tick(ctx)
            #
            #
        DamageDispatcher.add_target(handle_damage)

    def route_damage_internal(self, label):
        """
        route_damage_source

        define a label to use with a new task items are spawned
        """
        story = self
        
        def handle_damage(ctx, event):
            # Need point? amount
            task = story.schedule_task(label)
            task.DAMAGE_SOURCE_ID = event.origin_id
            task.DAMAGE_TARGET_ID = event.selected_id
            task.DAMAGE_ORIGIN_ID = event.origin_id
            task.DAMAGE_SELECTED_ID = event.selected_id
            task.EVENT = event
            task.DAMAGE_ROUTED = True
            
            #
            # Kick the tick
            #
            task.tick(ctx)
            #
            #
        DamageDispatcher.add_any_internal(handle_damage)

    def route_destroyed(self, label):
        """
        route_damage_source

        define a label to use with a new task items are spawned
        """
        story = self
        
        def handle_destroyed(ctx, so):
            # Need point? amount
            task = story.schedule_task(label)
            task.DESTROYED_ID = so.id
            task.DESTROYED_ROUTED = True
            #
            # Kick the tick
            #
            task.tick(ctx)
            #
            #
        LifetimeDispatcher.add_destroy(handle_destroyed)


    ###########
    # SBS Strory
    def await_science(self, buttons, player=None, npc=None):
        return self.task.await_science(buttons, player, npc)
    
    
    def await_comms(self, buttons, player=None, npc=None):
        return self.task.await_comms(buttons, player, npc)
    
    
    ###################
    ## Behavior stuff
    def behave_until(self, poll_result, label):
        return self.task.behave_until(poll_result, label)
    
    def behave_invert(self, label):
        return self.task.behave_invert(label)
    
    def behave_seq(self,*labels):
        return self.task.behave_seq(*labels)
    
    def behave_sel(self,*labels):
        return self.task.behave_sel(*labels)


    ###############
    ## GUI STUFF
    def get_page(self):
        return self.task.page
    
    @property
    def client_id(self):
        if self.task and self.task.page:
            return self.task.page.client_id
        return 0
    
    def await_gui(self, buttons= None, timeout=None, on_message=None, test_refresh=None,  test_end_await=None, on_disconnect=None):
        return self.task.await_gui(buttons, timeout, on_message, test_refresh, test_end_await, on_disconnect)
    
    def reroute_gui_server(self, label):
        self.reroute_gui_client(0, label)
        return PollResults.OK_ADVANCE_TRUE
    
    def reroute_gui_clients(self, label):
        for id, client in Gui.clients.items():
            if id != 0 and client is not None:
                client_page = client.page_stack[-1]
                if client_page:
                    client_page.reroute_gui(label)
        return PollResults.OK_ADVANCE_TRUE

    def reroute_gui_all(self, label):
        for client in Gui.clients.values():
            if  client is not None:
                client_page = client.page_stack[-1]
                if client_page:
                    client_page.reroute_gui(label)
        return PollResults.OK_ADVANCE_TRUE


    def reroute_gui_client(self, client_id, label):
        page = Gui.clients.get(client_id)
        if page:
            page.reroute_gui(label)
    

    def gui_face(self, face, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Face(page.get_tag(), face)
        page.apply_style_name(".face", control)
        if style is not None:
            page.apply_style_def(style,  control)
        page.add_content(control, None)
        return control
    def gui_ship(self, ship, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Ship(page.get_tag(),ship)
        page.add_content(control, None)
        return control
    # Widgets
    def gui_content(self, content, label, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.GuiControl(page.get_tag(), content)
        page.add_content(control, label)
        return control
    
    def gui_text(self, props, style=None):
        """ Gets the simulation space object

        valid properties 
           text
           color
           font


        :param props: property string 
        :type props: str
        :param layout: property string 
        :type layout: str
        """
        if self.get_page() is None:
            return
        if style is None: 
            style = ""
        page = self.get_page()
        control = layout.Text(page.get_tag(), props)
        page.apply_style_name(".button", control)
        if style is not None:
            page.apply_style_def(style,  control)
        page.add_content(control, None)
        return control
    
    def gui_button(self, message, label, style=None):
        if self.get_page() is None:
            return
        if style is None: 
            style = ""

        page = self.get_page()
        control = layout.Button(page.get_tag(), message)
        # CodePusher(self, value)
        page.add_content(control, CodePusher(page, label))
        page.apply_style_name(".button", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    
    def gui_icon_button(self, message, label, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.IconButton(page.get_tag(), message)
        page.add_content(control, label)
        page.apply_style_name(".iconbutton", control)
        if style is not None:
            page.apply_style_def(style,  control)
    
        return control
    
    def gui_row(self, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        row = page.add_row()
        page.apply_style_name(".row", row)
        if style is not None:
            page.apply_style_def(style,  row)
        
        
        

    def gui_blank(self, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Blank()
        
        page.add_content(control, None)
        return control

    def gui_hole(self, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Hole()
        page.add_content(control, None)
        return control
    def gui_section(self, style=None, click_props=None, label=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        tag = None
        if click_props:
            tag = page.get_tag()
        
        control = page.add_section(tag, click_props)
        if label:
            # Don't add content, just register the tag for callback
            page.add_tag(control, CodePusher(page, label))

        page.apply_style_name(".section", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    
    def gui_slider(self, val, props, label=None, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Slider(page.get_tag(), val, props)
        page.add_content(control, label)
        page.apply_style_name(".slider", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_checkbox(self, message, value, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Checkbox(page.get_tag(), message, value)
        page.add_content(control, None)
        page.apply_style_name(".checkbox", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_drop_down(self, props, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Dropdown(page.get_tag(),  props)
        page.add_content(control, None)
        page.apply_style_name(".dropdown", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    
    def gui_radio(self, message, value, vertical=False, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        tag = page.get_tag()
        radio =layout.RadioButtonGroup(tag, message, value, vertical)
        page.apply_style_name(".radio", radio)
        if style is not None:
            page.apply_style_def(style, radio)
        page.add_content(radio, None)
        return radio
        
    def gui_text_input(self, props, label, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.TextInput(page.get_tag(), props )
        page.add_content(control, label)
        page.apply_style_name(".textinput", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    
    def gui_icon(self, icon, color, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Icon(page.get_tag(), icon, color)
        page.add_content(control, None)
        page.apply_style_name(".icon", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    
    def gui_iconbutton(self, icon, color, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.IconButton(page.get_tag(), icon, color)
        page.add_content(control, None)
        page.apply_style_name(".iconbutton", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    
    def gui_activate_console(self, console):
        if self.get_page() is None:
            return
        page = self.get_page()
        page.activate_console(console)

    def gui_console(self, console, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        page.activate_console_widgets(console.lower())


    def gui_console_widget_list(self, console, widgets, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        page.set_widget_list(console, widgets)

    def gui_console_widget(self, widget, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        page.add_console_widget(widget)
        control = layout.ConsoleWidget(widget)
        if style is not None:
            page.apply_style_def(style,  control)
        page.add_content(control, None)
        return control
    

    def assign_player_ship(self, player):
        if self.get_page() is None:
            return
        self.get_page().assign_player_ship(player)
        
    def gui_image(self, file, color, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Image(page.get_tag(), file, color)
        page.add_content(control, None)
        return control
    
    def watch_event(self, event_tag, label):
        self.task.watch_event(event_tag, label)

    def log(self, message, logger_name="pytmast", level="info"):
        logger = logging.getLogger(logger_name)
        match level:
            case "info":
                logger.info(message)
            case "debug":
                logger.debug(message)
            case "warning":
                logger.warning(message)
            case "error":
                logger.error(message)
            case "critical":
                logger.critical(message)
            case _:
                logger.debug(message)

    def logger(self, logger_name="pymast"):
        logger = logging.getLogger(logger_name)
        logging.basicConfig(level=logging.NOTSET)
        logger.setLevel(logging.NOTSET)

    def string_logger(self, logger_name="pymast"):
        logger = logging.getLogger(logger_name)
        logging.basicConfig(level=logging.NOTSET)
        logger.setLevel(logging.NOTSET)
   
        streamer = StringIO()
        handler = logging.StreamHandler(stream=streamer)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.NOTSET)
        logger.addHandler(handler)
        return streamer
    
    def file_logger(self, filename, logger_name="pymast"):
        logger = logging.getLogger(logger_name)
        logging.basicConfig(level=logging.NOTSET)
        logger.setLevel(logging.NOTSET)
       
        handler = logging.FileHandler(filename,mode='w',)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.setLevel(logging.NOTSET)
        logger.addHandler(handler)


