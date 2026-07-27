from .vec import Vec3
import time as time
import traceback
import sys
import re
from  .agent import Agent

class Context:
    """Context for a given event frame
    Allows the system to be abstracted or overridden
    For example, Mock sim and sbs for testing
    """
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
        """returns the GUI Page related to the currently executing task.

        The can change can change often for a given frame. As each task is ticked. It set the FrameContext Page.
        Other parts of the system may also temporary set the FrameContext.task and FrameContext.page during execution.
        """
        if self._page is None:
            gui = Agent.get(self.client_id)
            if gui is not None:
                return gui.page
        return self._page
    
    @property
    def server_page(self):
        """returns the GUI Page related to the server i.e. client_id==0.
        This should always return the server's page
        """
        gui = Agent.get(0)
        if gui is not None:
            return gui.page
        return None
    
    @property
    def client_page(self):
        """returns the GUI Page related to the current event's client_id.
        This should always return the that client's page.
        This can be different from the FrameContext.page
        """

        gui = Agent.get(self.client_id)
        if gui is not None:
            return gui.page
        return None
    
    @property
    def server_task(self):
        """returns the main task for GUI Page related to the server i.e. client_id==0.
        This should always return the server's main task
        """
        gui = Agent.get(0)
        if gui is not None:
            return gui.page.gui_task
        return None
    
    @property
    def client_task(self):
        """returns the main task for GUI Page related to this frame event's client_id.
        """
        gui = Agent.get(self.client_id)
        if gui is not None and gui.page is not None:
            return gui.page.gui_task
        return None
    
    @property
    def client_id(self):
        """returns the frame event's client_id.
        """
        if self.context is None or self.context.event is None:
            return 0
        return self.context.event.client_id
    
    @page.setter
    def page(self,value):
        """ Allows overriding the page, set internally
        e.g. when a new task is executing the FrameContext.page should be the page for that task.
        """
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
        """ Allows overriding the task, set internally
        e.g. when a new task is executing the FrameContext.task is set to that task.
        """
        self._task = value


    @property
    def sim(self):
        """ Returns the sim for the from
        This abstract exist to allow testing, etc.
        """
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
    def __init__(self, task=None, page=None, event=None):
        self.task = task
        self.page = page
        self.event = event

        self.restore_task = None
        self.restore_page = None
        self.restore_event = None

    def __enter__(self):
        self.restore_task = FrameContext.task
        self.restore_page = FrameContext.page
        self.restore_event = FrameContext.context.event

        FrameContext.task = self.task
        FrameContext.page = self.page
        if self.event is not None:
            FrameContext.context.event = self.event 
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        FrameContext.task = self.restore_task
        FrameContext.page = self.restore_page
        FrameContext.context.event = self.restore_event 
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
        self.sub_float = 0.0
        self.event_time = 0

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


# A colon starts a style prop only when the text before it is a real style
# key: an optional '$' then a lowercase identifier (word chars / hyphens).
# Every engine and layout style key is lowercase or '$'-prefixed, so anything
# else -- a capitalized word ("Score:", "Upgrades:"), a sentence ("Clicks: 0"),
# punctuation -- is plain text, not a key. This can never reclassify a working
# style string (no real key starts with a capital), so it only rescues text
# that previously misparsed. Residual gap: all-lowercase text like "ready: go"
# still reads as a key -- prefix it with "$text:" if needed.
_STYLE_KEY_RE = re.compile(r"\$?[a-z][\w-]*")


def split_props(s, def_key):
    ret = {}
    start = 0
    while start < len(s):
        colon = s.find(":", start)
        if colon == -1:
            ret[def_key] = s[start:]
            return ret
        s_key = s[start:colon].strip()
        if not _STYLE_KEY_RE.fullmatch(s_key):
            ret[def_key] = s[start:]
            return ret
        colon += 1
        # A backtick-quoted value is opaque: the ':' and ';' inside it are
        # literal text, not delimiters (issue #569). Read past the closing
        # backtick before looking for the terminating ';'. Only values that
        # actually start (after optional spaces) with a backtick take this
        # path, so unquoted props parse exactly as before.
        vstart = colon
        while vstart < len(s) and s[vstart] == ' ':
            vstart += 1
        if vstart < len(s) and s[vstart] == '`':
            close = s.find('`', vstart + 1)
            end = s.find(";", close + 1) if close != -1 else -1
        else:
            end = s.find(";", colon)
        if end == -1:
            ret[s_key] = s[colon:]
            start = len(s)
        else:
            ret[s_key] = s[colon:end]
            start = end + 1
    return ret
        
def merge_props(d):
    s=""
    for k,v in d.items():
        s += f"{k}:{v};"
    return s

def gui_text_escape(s):
    """Quote a dynamic value for safe inclusion as a ``$text:`` style value.

    Wraps ``s`` in backticks so any ``:`` or ``;`` it contains is treated as
    literal text by the style parser rather than a style property (issue #569).
    A literal backtick -- the quoting delimiter itself -- is stripped. An empty
    or ``None`` value returns ``""`` so the caller emits ``$text:;`` with no
    stray backtick in the box (issue #641).

    Use this ONLY on the dynamic value, e.g. ``f"$text:{gui_text_escape(name)};color:red;"``
    -- never on a whole authored props string, so the author's own ``:``/``;``
    styling is left untouched.
    """
    if s is None:
        return ""
    s = str(s)
    if "`" in s:
        s = s.replace("`", "")
    if not s:
        return ""
    return "`" + s + "`"
