from ..tickdispatcher import TickDispatcher
from ..consoledispatcher import ConsoleDispatcher
from ..engineobject import EngineObject
from ..gui import Page, Gui
from sbs_utils import faces
from ..pages import layout
import sbs
import inspect
from .pollresults import PollResults
from .pymastscience import PyMastScience
from .pymastcomms import PyMastComms
from .pymasttask import PyMastTask, DataHolder
from .pymastscheduler import PyMastScheduler



class PyMastStory:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # This style of init makes it more mixin friendly
        self.schedulers = []
        self.remove_scheduler = []
        self.shared = self #Alias for scoping
        self.tick_task = None
        self.vars = DataHolder()


    def enable(self, sim, delay=0, count=None):
        if self.tick_task is None:
            self.tick_task = TickDispatcher.do_interval(sim, self, delay, count)

    def add_scheduler(self, sim, label):
        self.enable(sim)
        sched = PyMastScheduler(self, label)
        self.schedulers.append(sched)
        return sched


    def delay(self,  delay):
        return self.task.delay(delay)
    
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

    def __call__(self, sim, sched=None):
        self.sim = sim
        for sched in self.schedulers:
            self.scheduler = sched
            sched.tick(sim)
            if len(sched.tasks) == 0:
                self.remove_scheduler.append(sched)
        for finished in self.remove_scheduler:
            self.schedulers.remove(finished)
        self.remove_scheduler.clear()
        if len(self.schedulers)==0:
            self.disable()
        self.sim = None


    def END(self):
        self.remove_tasks.add(self.task)

    def start(self):
        pass

    def start_server(self):
        pass

    def start_client(self):
        pass

    ###########
    # SBS Strory
    def schedule_science(self, player, npc, scans):
        task = PyMastTask(self,self.scheduler, None)
        science = PyMastScience(task, player, npc, scans)
        task.current_gen = science.run()
        return self.scheduler.schedule_a_task(task)

    def await_comms(self, player, npc, buttons):
        return self.task.await_comms(player, npc, buttons, False)
    
    def schedule_comms(self, player, npc, buttons):
        task = PyMastTask(self,self.scheduler, None)
        comms = PyMastComms(task, player, npc, buttons, True)
        task.current_gen = comms.run()
        return self.scheduler.schedule_a_task(task)
    
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
    
    def await_gui(self, buttons= None, timeout=None, on_message=None, test_refresh=None,  test_end_await=None, on_disconnect=None):
        return self.task.await_gui(buttons, timeout, on_message, test_refresh, test_end_await, on_disconnect)
    
    def gui_face(self, face, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Face(face, page.get_tag())
        page.apply_style_name(".face", control)
        if style is not None:
            page.apply_style_def(style,  control)
        page.add_content(control, None)
        return control
    def gui_ship(self, ship, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Ship(ship, page.get_tag())
        page.add_content(control, None)
        return control
    # Widgets
    def gui_content(self, content, label, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.GuiControl(content, page.get_tag())
        page.add_content(control, label)
        return control
    
    def gui_text(self, message, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Text(message, page.get_tag())
        page.add_content(control, None)
        return control
    def gui_button(self, message, label, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Button(message, page.get_tag())
        page.add_content(control, label)
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
    def gui_section(self, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = page.add_section()

        page.apply_style_name(".section", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_slider(self, val, low, high, show_number=True, label=None, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Slider(val, low, high, show_number, page.get_tag())
        page.add_content(control, label)
        page.apply_style_name(".slider", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_checkbox(self, message, value, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Checkbox(message,page.get_tag(), value)
        page.add_content(control, None)
        page.apply_style_name(".checkbox", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_drop_down(self, value, values, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Dropdown(value, values, page.get_tag())
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
        radio =layout.RadioButtonGroup(message, value, True, tag)
        page.apply_style_name(".radio", radio)
        if style is not None:
            page.apply_style_def(style, radio)
        page.add_content(radio, None)
        return radio
        
    def gui_text_input(self, val, label_message, label, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.TextInput(val, label_message, page.get_tag())
        page.add_content(control, label)
        page.apply_style_name(".textinput", control)
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
        
    def gui_image(self, file, color, label, style=None):
        if self.get_page() is None:
            return
        page = self.get_page()
        control = layout.Image(file, color, page.get_tag())
        page.add_content(control, label)
        return control
    
    def watch_event(self, event_tag, label):
        self.task.watch_event(event_tag, label)


    
