from ..tickdispatcher import TickDispatcher
from ..consoledispatcher import ConsoleDispatcher
from ..engineobject import EngineObject
from ..gui import Page, Gui
from sbs_utils import faces
from ..pages import layout
import sbs
import inspect
from . import PollResults
from .pymastscience import PyMastScience
from .pymastcomms import PyMastComms
from .pymasttask import PyMastTask, DataHolder
from .pymastscheduler import PyMastScheduler



class PyMastStory:
    def __init__(self) -> None:
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
        return self.task.await_comms(player, npc, buttons)
    
    def schedule_comms(self, player, npc, buttons):
        task = PyMastTask(self,self.scheduler, None)
        comms = PyMastComms(task, player, npc, buttons)
        task.current_gen = comms.run()
        return self.scheduler.schedule_a_task(task)

    ###############
    ## GUI STUFF
    def await_gui(self, buttons= None, timeout=None, on_message=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        page.on_message_cb = on_message
        page.set_buttons(buttons)
        page.run(timeout)
        return PollResults.OK_RUN_AGAIN
    
    def gui_face(self, face, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Face(face, page.get_tag())
        page.apply_style_name(".face", self.layout_item)
        if style is not None:
            self.apply_style_def(style,  control)
        page.add_content(control, None)
        return control
    def gui_ship(self, ship, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Ship(ship, page.get_tag())
        page.add_content(control, None)
        return control
    # Widgets
    def gui_content(self, content, label, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.GuiControl(content, page.get_tag())
        page.add_content(control, label, style=None)
        return control
    def gui_text(self, message, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Text(message, page.get_tag())
        page.add_content(control, None)
        return control
    def gui_button(self, message, label, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Button(message, page.get_tag())
        page.add_content(control, label)
        return control
    def gui_row(self, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        page.add_row()

    def gui_blank(self, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Blank()
        
        page.add_content(control, None)
        return control

    def gui_hole(self, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Hole()
        page.add_content(control, None)
        return control
    def gui_section(self, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = page.add_section()

        page.apply_style_name(".section", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_slider(self, val, low, high, label, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Slider(val, low, high, page.get_tag())
        page.add_content(control, label)
        page.apply_style_name(".slider", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_checkbox(self, message, value, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Checkbox(message,page.get_tag(), value)
        page.add_content(control, None)
        page.apply_style_name(".checkbox", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_drop_down(self, value, values, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Dropdown(value, values, page.get_tag())
        page.add_content(control, None)
        page.apply_style_name(".dropdown", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_radio(self, message, label, style=None):
        layout.
        # layout.Text(message, self.tag)
        pass
    def gui_text_input(self, val, label_message, label, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.TextInput(val, label_message, page.get_tag())
        page.add_content(control, label)
        page.apply_style_name(".textinput", control)
        if style is not None:
            page.apply_style_def(style,  control)
        return control
    def gui_console(self, message, label, style=None):
        # layout.Text(message, self.tag)
        pass

    def gui_console_widget_list(self, message, label, style=None):
        # layout.Text(message, self.tag)
        pass
    def gui_image(self, file, color, label, style=None):
        if self.scheduler.page is None:
            return
        page = self.scheduler.page
        control = layout.Image(file, color, page.get_tag())
        page.add_content(control, label)
        return control
    
