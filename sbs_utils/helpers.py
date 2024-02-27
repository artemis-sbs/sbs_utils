from .vec import Vec3
import time as time
import traceback
import sys
from  .agent import Agent

class Context:
    def __init__(self, sim, _sbs, _event):
        self.sim = sim
        self.sbs = _sbs
        self.event = _event

def show_warning(t):
    print(t)


_TPS = 30.0
class FrameContextMeta(type):
    context = None
    _page = None
    _task = None
    shared_id = -1

    @property
    def page(self):
        if self._page is None:
            gui = Agent.get(self.client_id)
            if gui is not None:
                return gui.page
        return self._page
    
    @property
    def client_id(self):
        if self.context is None:
            return 0
        return self.context.event.client_id
    
    @page.setter
    def page(self,value):
        self._page = value

    @property
    def task(self):
        if self._task is None:
            page = self.page
            if page is not None:
                return page.gui_task
        return self._task
    
    @task.setter
    def task(self,value):
        self._task = value


    @property
    def sim(self):
        return self.context.sim

    @property
    def sim_seconds(self):
        return float(self.context.sim.time_tick_counter) / _TPS

    @property
    def app_seconds(self):
        return time.time() 

class FrameContext(metaclass=FrameContextMeta):
    pass

class FakeEvent:
    def __init__(self, client_id=0, tag="", sub_tag="", origin_id=0, selected_id=0, parent_id=0, extra_tag="", value_tag=""):
        self.tag = tag
        self.sub_tag = sub_tag
        self.client_id = client_id
        self.parent_id = parent_id
        self.origin_id = origin_id
        self.extra_tag = extra_tag
        self.value_tag = value_tag
        self.selected_id = selected_id
        self.source_point = Vec3()

def format_exception(message, source):
    error_type, error, tb = sys.exc_info()
    lines = traceback.extract_tb(tb)
    if len(lines)>0:
        filename, lineno, func_name, line = lines[-1]
        return f"{source}\n\n{message}\n{error}\n{line}\nfunction: {func_name}\nline: {lineno}\nFile: {filename}"
    return f"{source}\n\n{message}\n"