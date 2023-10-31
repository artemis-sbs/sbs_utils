from sbs_utils.mast.maststory import AppendText
from sbs_utils.mast.maststory import AwaitGui
from sbs_utils.mast.maststory import AwaitSelect
from sbs_utils.mast.maststory import Blank
from sbs_utils.mast.maststory import BuildaConsole
from sbs_utils.mast.maststory import ButtonControl
from sbs_utils.mast.maststory import CheckboxControl
from sbs_utils.mast.maststory import Choose
from sbs_utils.mast.maststory import Console
from sbs_utils.mast.maststory import Disconnect
from sbs_utils.mast.maststory import DropdownControl
from sbs_utils.mast.maststory import Face
from sbs_utils.mast.maststory import GuiContent
from sbs_utils.mast.maststory import Hole
from sbs_utils.mast.maststory import Icon
from sbs_utils.mast.maststory import ImageControl
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.maststory import OnChange
from sbs_utils.mast.maststory import OnClick
from sbs_utils.mast.maststory import RadioControl
from sbs_utils.mast.maststory import Refresh
from sbs_utils.mast.maststory import RerouteGui
from sbs_utils.mast.maststory import Row
from sbs_utils.mast.maststory import Section
from sbs_utils.mast.maststory import Ship
from sbs_utils.mast.maststory import SliderControl
from sbs_utils.mast.maststory import Style
from sbs_utils.mast.maststory import Text
from sbs_utils.mast.maststory import TextInputControl
from sbs_utils.mast.maststory import Update
from sbs_utils.mast.maststory import WidgetList
from sbs_utils.mast.mastsbs import Button
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.mast.parsers import LayoutAreaParser
from sbs_utils.mast.parsers import StyleDefinition
from sbs_utils.widgets.listbox import Listbox
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import Scope
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastRuntimeNode
from sbs_utils.mast.mastscheduler import PollResults
from sbs_utils.mast.mastsbsscheduler import MastSbsScheduler
from sbs_utils.widgets.shippicker import ShipPicker
def get_inventory_value (so, link, default=None):
    ...
def set_inventory_value (so, name, value):
    ...
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
class AwaitSelectRuntimeNode(StoryRuntimeNode):
    """class AwaitSelectRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.AwaitSelect):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.AwaitGui):
        ...
    def selected (self, __, event):
        ...
class BlankRuntimeNode(StoryRuntimeNode):
    """class BlankRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Blank):
        ...
class BuildaConsoleRuntimeNode(MastRuntimeNode):
    """Lower level console building command to allow layout"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.BuildaConsole):
        ...
class ButtonControlRuntimeNode(StoryRuntimeNode):
    """class ButtonControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.ButtonControl):
        ...
    def on_message (self, event):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.ButtonControl):
        ...
class CheckboxControlRuntimeNode(StoryRuntimeNode):
    """class CheckboxControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.CheckboxControl):
        ...
    def on_message (self, event):
        ...
class ChoiceButtonRuntimeNode(StoryRuntimeNode):
    """class ChoiceButtonRuntimeNode"""
    def __init__ (self, choice, index, tag, node):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
class ChooseRuntimeNode(StoryRuntimeNode):
    """class ChooseRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Choose):
        ...
    def expand (self, button: sbs_utils.mast.mastsbs.Button, task: sbs_utils.mast.mastscheduler.MastAsyncTask):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Choose):
        ...
class ConsoleRuntimeNode(MastRuntimeNode):
    """class ConsoleRuntimeNode"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Console):
        ...
class DisconnectRuntimeNode(MastRuntimeNode):
    """class DisconnectRuntimeNode"""
    def poll (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Disconnect):
        ...
class DropdownControlRuntimeNode(StoryRuntimeNode):
    """class DropdownControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.DropdownControl):
        ...
    def on_message (self, event):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.DropdownControl):
        ...
class FaceRuntimeNode(StoryRuntimeNode):
    """class FaceRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Face):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.maststory.Face):
        ...
class GuiContentRuntimeNode(StoryRuntimeNode):
    """class GuiContentRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.GuiContent):
        ...
class HoleRuntimeNode(StoryRuntimeNode):
    """class HoleRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Hole):
        ...
class IconRuntimeNode(StoryRuntimeNode):
    """class IconRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Icon):
        ...
    def poll (self, mast, task, node: sbs_utils.mast.maststory.Face):
        ...
class ImageControlRuntimeNode(StoryRuntimeNode):
    """class ImageControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.ImageControl):
        ...
class OnChangeRuntimeNode(StoryRuntimeNode):
    """class OnChangeRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.OnChange):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.OnChange):
        ...
    def test (self):
        ...
class OnClickRuntimeNode(StoryRuntimeNode):
    """class OnClickRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.OnClick):
        ...
    def poll (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.OnClick):
        ...
    def test (self, click_tag):
        ...
class RadioControlRuntimeNode(StoryRuntimeNode):
    """class RadioControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.RadioControl):
        ...
    def on_message (self, event):
        ...
class RefreshRuntimeNode(StoryRuntimeNode):
    """class RefreshRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Refresh):
        ...
class RerouteGuiRuntimeNode(StoryRuntimeNode):
    """class RerouteGuiRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.RerouteGui):
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
    def on_message (self, event):
        ...
class StoryPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def activate_console (self, console):
        ...
    def add_console_widget (self, widget):
        ...
    def add_content (self, layout_item, runtime_node):
        ...
    def add_on_change (self, runtime_node):
        ...
    def add_on_click (self, runtime_node):
        ...
    def add_row (self):
        ...
    def add_section (self, tag=None):
        ...
    def add_tag (self, layout_item, runtime_node):
        ...
    def get_pending_layout (self):
        ...
    def get_pending_row (self):
        ...
    def get_tag (self):
        ...
    def gui_queue_console_tabs (self):
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
    def present (self, event):
        """Present the gui """
    def set_button_layout (self, layout):
        ...
    def set_widget_list (self, console, widgets):
        ...
    def start_story (self, client_id):
        ...
    def swap_layout (self):
        ...
    def tick_gui_task (self):
        """tick_gui_task
        
        Called to have the page run any tasks they have prior to present"""
    def update_props_by_tag (self, tag, props):
        ...
class StoryRuntimeNode(MastRuntimeNode):
    """class StoryRuntimeNode"""
    def apply_style_def (self, style_def, layout_item, task):
        ...
    def apply_style_name (self, style_name, layout_item, task):
        ...
    def compile_formatted_string (self, message):
        ...
    def databind (self):
        ...
    def on_message (self, event):
        ...
class StoryScheduler(MastSbsScheduler):
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
    def resolve_id (other: 'EngineObject | CloseData | int'):
        ...
    def resolve_py_object (other: 'EngineObject | CloseData | int'):
        ...
    def run (self, client_id, page, label='main', inputs=None):
        ...
    def runtime_error (self, message):
        ...
    def story_tick_tasks (self, client_id):
        ...
class TabControl(Text):
    """class TabControl"""
    def __init__ (self, tag, message, label, page) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        ...
class TextInputControlRuntimeNode(StoryRuntimeNode):
    """class TextInputControlRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.TextInputControl):
        ...
    def on_message (self, event):
        ...
class TextRuntimeNode(StoryRuntimeNode):
    """class TextRuntimeNode"""
    def databind (self):
        ...
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Text):
        ...
class UpdateRuntimeNode(StoryRuntimeNode):
    """class UpdateRuntimeNode"""
    def enter (self, mast: sbs_utils.mast.mast.Mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.Update):
        ...
class WidgetListRuntimeNode(MastRuntimeNode):
    """class WidgetListRuntimeNode"""
    def enter (self, mast, task: sbs_utils.mast.mastscheduler.MastAsyncTask, node: sbs_utils.mast.maststory.WidgetList):
        ...
