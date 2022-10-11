from sbs_utils.mast.maststory import AppendText
from sbs_utils.mast.maststory import Area
from sbs_utils.mast.maststory import Blank
from sbs_utils.mast.maststory import CheckboxControl
from sbs_utils.mast.maststory import Choose
from sbs_utils.mast.maststory import Face
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.maststory import Refresh
from sbs_utils.mast.maststory import Row
from sbs_utils.mast.maststory import Section
from sbs_utils.mast.maststory import Ship
from sbs_utils.mast.maststory import SliderControl
from sbs_utils.mast.maststory import Text
from sbs_utils.mast.mastsbs import Button
from sbs_utils.mast.errorpage import ErrorPage
from sbs_utils.gui import FakeEvent
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import Scope
from sbs_utils.mast.mastrunner import MastAsync
from sbs_utils.mast.mastrunner import MastRunner
from sbs_utils.mast.mastrunner import MastRuntimeNode
from sbs_utils.mast.mastrunner import PollResults
from sbs_utils.mast.mastsbsrunner import MastSbsRunner
class AppendTextRunner(StoryRuntimeNode):
    """class AppendTextRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.AppendText):
        ...
class AreaRunner(StoryRuntimeNode):
    """class AreaRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Area):
        ...
class BlankRunner(StoryRuntimeNode):
    """class BlankRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Blank):
        ...
class ButtonControlRunner(StoryRuntimeNode):
    """class ButtonControlRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Button):
        ...
    def on_message (self, sim, event):
        ...
class CheckboxControlRunner(StoryRuntimeNode):
    """class CheckboxControlRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.SliderControl):
        ...
    def on_message (self, sim, event):
        ...
class ChoiceButtonRunner(StoryRuntimeNode):
    """class ChoiceButtonRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.mastsbs.Button):
        ...
    def on_message (self, sim, event):
        ...
class ChooseRunner(StoryRuntimeNode):
    """class ChooseRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Choose):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Choose):
        ...
class FaceRunner(StoryRuntimeNode):
    """class FaceRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Face):
        ...
    def poll (self, mast, thread, node: sbs_utils.mast.maststory.Face):
        ...
class RefreshRunner(StoryRuntimeNode):
    """class RefreshRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Refresh):
        ...
class RowRunner(StoryRuntimeNode):
    """class RowRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Row):
        ...
class SectionRunner(StoryRuntimeNode):
    """class SectionRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Section):
        ...
class ShipRunner(StoryRuntimeNode):
    """class ShipRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Ship):
        ...
class SliderControlRunner(StoryRuntimeNode):
    """class SliderControlRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.SliderControl):
        ...
    def on_message (self, sim, event):
        ...
class StoryPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_content (self, layout_item, runner):
        ...
    def add_row (self):
        ...
    def add_section (self):
        ...
    def add_tag (self, layout_item):
        ...
    def get_tag (self):
        ...
    def on_message (self, sim, event):
        """on_message
        
        Called when a control on the page has been interacted with
        
        :param sim:
        :type sim: Artemis Cosmos simulation
        :param message_tag: The tag name of the control interacted with
        :type message_tag: str
        :param clientID: The client ID that had the interaction
        :type clientID: int
        :param data: Any data associated with the control e.g. slider float value of current value
        :type clientID: None or str or float"""
    def present (self, sim, event):
        """Present the gui """
    def run (self, sim, story_script):
        ...
    def set_button_layout (self, layout):
        ...
    def set_section_size (self, left, top, right, bottom):
        ...
    def swap_layout (self):
        ...
class StoryRunner(MastSbsRunner):
    """class StoryRunner"""
    def __init__ (self, mast: sbs_utils.mast.mast.Mast, overrides=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def refresh (self, label):
        ...
    def run (self, sim, page, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def story_tick_threads (self, sim, client_id):
        ...
class StoryRuntimeNode(MastRuntimeNode):
    """class StoryRuntimeNode"""
    def on_message (self, sim, event):
        ...
class TextRunner(StoryRuntimeNode):
    """class TextRunner"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, thread: sbs_utils.mast.mastrunner.MastAsync, node: sbs_utils.mast.maststory.Text):
        ...
