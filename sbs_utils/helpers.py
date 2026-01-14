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
    mast = None #Set by the tick in a MastScheduler, No need to restore
    _page = None
    _task = None
    shared_id = -1
    aspect_ratios = {}
    error_message = ""

    @property
    def page(self):
        if self._page is None:
            gui = Agent.get(self.client_id)
            if gui is not None:
                return gui.page
        return self._page
    
    @property
    def server_page(self):
        gui = Agent.get(0)
        if gui is not None:
            return gui.page
        return None
    
    @property
    def client_page(self):
        gui = Agent.get(self.client_id)
        if gui is not None:
            return gui.page
        return None
    
    @property
    def server_task(self):
        gui = Agent.get(0)
        if gui is not None:
            return gui.page.gui_task
        return None
    
    @property
    def client_task(self):
        gui = Agent.get(self.client_id)
        if gui is not None and gui.page is not None:
            return gui.page.gui_task
        return None
    
    @property
    def client_id(self):
        if self.context is None or self.context.event is None:
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

class FrameContextOverride:
    def __init__(self, task=None, page=None):
        self.task = task
        self.page = page

        self.restore_task = None
        self.restore_page = None

    def __enter__(self):
        self.restore_task = FrameContext.task
        self.restore_page = FrameContext.page

        FrameContext.task = self.task
        FrameContext.page = self.page
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        FrameContext.task = self.restore_task
        FrameContext.page = self.restore_page
        if exc_type:
            return False #Reraise the exception
        return True


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
        self.extra_extra_tag = ""
        self.source_point = Vec3()

def format_exception(message, source):
    error_type, error, tb = sys.exc_info()
    lines = traceback.extract_tb(tb)
    if len(lines)>0:
        filename, lineno, func_name, line = lines[-1]
        return f"{source}\n\n{message}\n{error}\n{line}\nfunction: {func_name}\nline: {lineno}\nFile: {filename}"
    return f"{source}\n\n{message}\n"


class DictionaryToObject(object):
    def __init__(self, *initial_data, **kwargs):
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self) -> str:
        return repr(self.__dict__)


def split_props(s, def_key):
    ret = {}

    # get key
    start = 0
    key = -1
    end = -1
    while start < len(s):
        key = s.find(":", start)
        if key == -1:
            ret[def_key] = s
            return ret
        s_key = s[start:key]
        key += 1
        end = s.find(";", key)
        if end ==-1:
            s_value = s[key:]
            start = len(s)
        else:
            s_value = s[key:end]
            start = end+1
        ret[s_key] = s_value
    return ret
        
def merge_props(d):
    s=""
    for k,v in d.items():
        s += f"{k}:{v};"
    return s  