from sbs_utils.agent import Agent
from sbs_utils.vec import Vec3
def format_exception (message, source):
    ...
def gui_text_escape (s):
    """Quote a dynamic value for safe inclusion as a ``$text:`` style value.
    
    Wraps ``s`` in backticks so any ``:`` or ``;`` it contains is treated as
    literal text by the style parser rather than a style property (issue #569).
    A literal backtick -- the quoting delimiter itself -- is stripped. An empty
    or ``None`` value returns ``""`` so the caller emits ``$text:;`` with no
    stray backtick in the box (issue #641).
    
    Use this ONLY on the dynamic value, e.g. ``f"$text:{gui_text_escape(name)};color:red;"``
    -- never on a whole authored props string, so the author's own ``:``/``;``
    styling is left untouched."""
def merge_props (d):
    ...
def props_display_text (props, def_key='$text'):
    """Extract the plain display text from a widget props string.
    
    The inverse of the ``$text:`...`;`` quoting that ``gui_text_escape`` and
    ``Text.update`` apply. Given ``"$text:`Hello`;font:gui-2;"`` this returns
    ``"Hello"``. Handles the unquoted form, the bare ``text:`` spelling, and a
    props string that is really just a bare label (no colon at all).
    
    This is what a measurement needs: the glyphs the engine will actually draw,
    with the style props stripped off. Returns ``""`` when there is no text."""
def props_font (props, default=None):
    """Effective font for a widget props string.
    
    A ``font:`` inside the widget's own props WINS over the cascaded font,
    because ``present()`` appends the cascade props *after* the message, so the
    engine sees the widget's own value last. Measurement has to agree with that
    or it measures in a different font than it renders."""
def show_warning (t):
    ...
def split_props (s, def_key):
    ...
class Context(object):
    """Context for a given event frame
    Allows the system to be abstracted or overridden
    For example, Mock sim and sbs for testing"""
    def __init__ (self, sim, _sbs, _event):
        """Initialize self.  See help(type(self)) for accurate signature."""
class DictionaryToObject(object):
    """class DictionaryToObject"""
    def __init__ (self, *initial_data, **kwargs):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self) -> str:
        """Return repr(self)."""
class FakeEvent(object):
    """class FakeEvent"""
    def __init__ (self, client_id=0, tag='', sub_tag='', origin_id=0, selected_id=0, parent_id=0, extra_tag='', value_tag=''):
        """Initialize self.  See help(type(self)) for accurate signature."""
class FrameContext(object):
    """class FrameContext"""
class FrameContextMeta(type):
    """type(object) -> the object's type
    type(name, bases, dict, **kwds) -> a new type"""
    __abstractmethods__ : getset_descriptor
    ...
    def __prepare__() -> dict:
        """used to create the namespace for the class statement"""
    @property
    def app_seconds (self):
        ...
    @property
    def client_id (self):
        """returns the frame event's client_id.
                """
    @property
    def client_page (self):
        """returns the GUI Page related to the current event's client_id.
        This should always return the that client's page.
        This can be different from the FrameContext.page"""
    @property
    def client_task (self):
        """returns the main task for GUI Page related to this frame event's client_id.
                """
    @property
    def page (self):
        """returns the GUI Page related to the currently executing task.
        
        The can change can change often for a given frame. As each task is ticked. It set the FrameContext Page.
        Other parts of the system may also temporary set the FrameContext.task and FrameContext.page during execution."""
    @page.setter
    def page (self, value):
        """returns the GUI Page related to the currently executing task.
        
        The can change can change often for a given frame. As each task is ticked. It set the FrameContext Page.
        Other parts of the system may also temporary set the FrameContext.task and FrameContext.page during execution."""
    @property
    def server_page (self):
        """returns the GUI Page related to the server i.e. client_id==0.
        This should always return the server's page"""
    @property
    def server_task (self):
        """returns the main task for GUI Page related to the server i.e. client_id==0.
        This should always return the server's main task"""
    @property
    def sim (self):
        """Returns the sim for the from
        This abstract exist to allow testing, etc."""
    @property
    def sim_seconds (self):
        ...
    @property
    def task (self):
        ...
    @task.setter
    def task (self, value):
        ...
class FrameContextOverride(object):
    """class FrameContextOverride"""
    def __enter__ (self):
        ...
    def __exit__ (self, exc_type, exc_val, exc_tb):
        ...
    def __init__ (self, task=None, page=None, event=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
