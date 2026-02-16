from sbs_utils.agent import Agent
from sbs_utils.vec import Vec3
def format_exception (message, source):
    ...
def merge_props (d):
    ...
def show_warning (t):
    ...
def split_props (s, def_key):
    ...
class Context(object):
    """class Context"""
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
        ...
    @property
    def client_page (self):
        ...
    @property
    def client_task (self):
        ...
    @property
    def page (self):
        ...
    @page.setter
    def page (self, value):
        ...
    @property
    def server_page (self):
        ...
    @property
    def server_task (self):
        ...
    @property
    def sim (self):
        ...
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
    def __init__ (self, task=None, page=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
