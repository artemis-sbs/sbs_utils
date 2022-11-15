from sbs_utils.mast.maststory import AppendText
from sbs_utils.mast.maststory import AwaitGui
from sbs_utils.mast.maststory import Blank
from sbs_utils.mast.maststory import ButtonControl
from sbs_utils.mast.maststory import CheckboxControl
from sbs_utils.mast.maststory import Choose
from sbs_utils.mast.maststory import DropdownControl
from sbs_utils.mast.maststory import Face
from sbs_utils.mast.maststory import Hole
from sbs_utils.mast.maststory import ImageControl
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.maststory import Refresh
from sbs_utils.mast.maststory import Row
from sbs_utils.mast.maststory import Section
from sbs_utils.mast.maststory import Ship
from sbs_utils.mast.maststory import SliderControl
from sbs_utils.mast.maststory import Style
from sbs_utils.mast.maststory import Text
from sbs_utils.mast.maststory import TextInputControl
from sbs_utils.mast.maststory import WidgetList
from sbs_utils.mast.errorpage import ErrorPage
from sbs_utils.gui import FakeEvent
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.mast.parsers import LayoutAreaParser
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastRuntimeNode
from sbs_utils.mast.mastscheduler import PollResults
from sbs_utils.mast.mastsbsscheduler import MastSbsScheduler
from sbs_utils.tickdispatcher import TickDispatcher
class AppendTextRuntimeNode(StoryRuntimeNode):
    """class AppendTextRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.AppendText):
        ...
class AwaitGuiRuntimeNode(StoryRuntimeNode):
    """class AwaitGuiRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.AwaitGui):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.AwaitGui):
        ...
class BlankRuntimeNode(StoryRuntimeNode):
    """class BlankRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Blank):
        ...
class ButtonControlRuntimeNode(StoryRuntimeNode):
    """class ButtonControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.ButtonControl):
        ...
    def on_message (self, sim, event):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.ButtonControl):
        ...
class CheckboxControlRuntimeNode(StoryRuntimeNode):
    """class CheckboxControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.SliderControl):
        ...
    def on_message (self, sim, event):
        ...
class ChoiceButtonRuntimeNode(StoryRuntimeNode):
    """class ChoiceButtonRuntimeNode"""
    def __init__ (self, choice, index, tag, node):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
class ChooseRuntimeNode(StoryRuntimeNode):
    """class ChooseRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Choose):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Choose):
        ...
class DropdownControlRuntimeNode(StoryRuntimeNode):
    """class DropdownControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.DropdownControl):
        ...
    def on_message (self, sim, event):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.DropdownControl):
        ...
class FaceRuntimeNode(StoryRuntimeNode):
    """class FaceRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Face):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.maststory.Face):
        ...
class HoleRuntimeNode(StoryRuntimeNode):
    """class HoleRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Hole):
        ...
class ImageControlRuntimeNode(StoryRuntimeNode):
    """class ImageControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.ImageControl):
        ...
class RefreshRuntimeNode(StoryRuntimeNode):
    """class RefreshRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Refresh):
        ...
class RowRuntimeNode(StoryRuntimeNode):
    """class RowRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Row):
        ...
class SectionRuntimeNode(StoryRuntimeNode):
    """class SectionRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Section):
        ...
class ShipRuntimeNode(StoryRuntimeNode):
    """class ShipRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Ship):
        ...
class SliderControlRuntimeNode(StoryRuntimeNode):
    """class SliderControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.SliderControl):
        ...
    def on_message (self, sim, event):
        ...
class StoryPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_content (self, layout_item, runtime_node):
        ...
    def add_row (self):
        ...
    def add_section (self):
        ...
    def add_tag (self, layout_item):
        ...
    def get_tag (self):
        ...
    def on_event (self, sim, event):
        """on_event
        
        Called when the option pages page has been interacted with
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def on_message (self, sim, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def present (self, sim, event):
        """Present the gui """
    def set_button_layout (self, layout):
        ...
    def set_default_height (self, height):
        ...
    def set_section_size (self, values):
        ...
    def set_widget_list (self, console, widgets):
        ...
    def start_story (self, sim, client_id):
        ...
    def swap_layout (self):
        ...
    def tick_mast (self, sim, t):
        ...
class StoryRuntimeNode(MastRuntimeNode):
    """class StoryRuntimeNode"""
    def databind (self):
        ...
    def on_message (self, sim, event):
        ...
class StoryScheduler(MastSbsScheduler):
    """class StoryScheduler"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_event (self, sim, event):
        ...
    def refresh (self, label):
        ...
    def run (self, sim, client_id, page, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def story_tick_tasks (self, sim, client_id):
        ...
class SyleRuntimeNode(StoryRuntimeNode):
    """class SyleRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Style):
        ...
class TextInputControlRuntimeNode(StoryRuntimeNode):
    """class TextInputControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.TextInputControl):
        ...
    def on_message (self, sim, event):
        ...
class TextRuntimeNode(StoryRuntimeNode):
    """class TextRuntimeNode"""
    def databind (self):
        ...
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Text):
        ...
class WidgetListRuntimeNode(MastRuntimeNode):
    """class WidgetListRuntimeNode"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.WidgetList):
        ...
