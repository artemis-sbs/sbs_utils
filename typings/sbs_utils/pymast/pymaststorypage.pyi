from sbs_utils.helpers import Context
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.parsers import LayoutAreaParser
from sbs_utils.mast.parsers import StyleDefinition
from sbs_utils.gui import Page
from sbs_utils.pymast.pollresults import PollResults
from sbs_utils.pymast.pymastscheduler import PyMastScheduler
class CodePusher(object):
    """class CodePusher"""
    def __init__ (self, page, func_or_tuple, end_await=True) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
class PyMastStoryPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _run (self, time_out):
        ...
    def activate_console (self, console):
        ...
    def activate_console_widgets (self, console):
        ...
    def add_console_widget (self, widget):
        ...
    def add_content (self, layout_item, runtime_node):
        ...
    def add_row (self):
        ...
    def add_section (self, click_tag, click_props):
        ...
    def add_tag (self, layout_item, runtime_node):
        ...
    def apply_style_def (self, style_def, layout_item):
        ...
    def apply_style_name (self, style_name, layout_item):
        ...
    def assign_player_ship (self, player):
        ...
    def get_pending_layout (self):
        ...
    def get_pending_row (self):
        ...
    def get_tag (self):
        ...
    def on_event (self, event):
        """on_event
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def on_message (self, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def on_pop (self):
        ...
    def present (self, event):
        """present
        
        Called to have the page create and update the gui content it is presenting"""
    def reroute_gui (self, label):
        ...
    def run (self, time_out):
        ...
    def set_button_layout (self, layout):
        ...
    def set_buttons (self, buttons):
        ...
    def set_widget_list (self, console, widgets):
        ...
    def swap_layout (self):
        ...
    def tick_gui_task (self):
        """tick_gui_task
        
        Called to have the page run any tasks they have prior to present"""
