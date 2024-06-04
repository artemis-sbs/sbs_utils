from sbs_utils.mast.maststory import AppendText
from sbs_utils.mast.maststory import Text
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.mast.parsers import LayoutAreaParser
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastRuntimeNode
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.pollresults import PollResults
def format_exception (message, source):
    ...
def gui_text (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def gui_text_area (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
class AppendTextRuntimeNode(MastRuntimeNode):
    """class AppendTextRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.AppendText):
        ...
class StoryScheduler(MastScheduler):
    """class StoryScheduler"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def refresh (self, label):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def run (self, client_id, page, label='main', inputs=None, task_name=None, defer=False):
        ...
    def runtime_error (self, message):
        ...
    def story_tick_tasks (self, client_id):
        ...
class TextRuntimeNode(MastRuntimeNode):
    """class TextRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Text):
        ...
