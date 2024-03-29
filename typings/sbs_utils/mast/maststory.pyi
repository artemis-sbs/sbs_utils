from sbs_utils.mast.mast import EndAwait
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast import MastNode
from sbs_utils.mast.mastsbs import MastSbs
from sbs_utils.mast.parsers import StyleDefinition
class AppendText(MastNode):
    """class AppendText"""
    def __init__ (self, message, if_exp, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class AwaitGui(MastNode):
    """class AwaitGui"""
    def __init__ (self, assign=None, minutes=None, seconds=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class AwaitSelect(MastNode):
    """class AwaitSelect"""
    def __init__ (self, console=None, minutes=None, seconds=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Blank(MastNode):
    """class Blank"""
    def __init__ (self, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class BuildaConsole(MastNode):
    """class BuildaConsole"""
    def __init__ (self, console, widget, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class ButtonControl(MastNode):
    """class ButtonControl"""
    def __init__ (self, message, q, data=None, py=None, if_exp=None, end=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class CheckboxControl(MastNode):
    """class CheckboxControl"""
    def __init__ (self, var=None, message=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Choose(MastNode):
    """class Choose"""
    def __init__ (self, assign=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Console(MastNode):
    """class Console"""
    def __init__ (self, console, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Disconnect(MastNode):
    """class Disconnect"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class DropdownControl(MastNode):
    """class DropdownControl"""
    def __init__ (self, var=None, values=None, q=None, end=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Face(MastNode):
    """class Face"""
    def __init__ (self, face=None, face_exp=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class GuiContent(MastNode):
    """class GuiContent"""
    def __init__ (self, gui=None, var=None, exp=None, py=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Hole(MastNode):
    """class Hole"""
    def __init__ (self, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Icon(MastNode):
    """class Icon"""
    def __init__ (self, props=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class ImageControl(MastNode):
    """class ImageControl"""
    def __init__ (self, file, q, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class MastStory(MastSbs):
    """class MastStory"""
    def _add (id, obj):
        ...
    def _remove (id):
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
    def resolve_id (other: 'EngineObject | CloseData | int'):
        ...
    def resolve_py_object (other: 'EngineObject | CloseData | int'):
        ...
class OnChange(MastNode):
    """class OnChange"""
    def __init__ (self, end=None, val=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class OnClick(MastNode):
    """class OnClick"""
    def __init__ (self, end=None, name=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class RadioControl(MastNode):
    """class RadioControl"""
    def __init__ (self, radio, var=None, message=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Refresh(MastNode):
    """class Refresh"""
    def __init__ (self, label, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class RerouteGui(MastNode):
    """class RerouteGui"""
    def __init__ (self, gui, var=None, label=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Row(MastNode):
    """class Row"""
    def __init__ (self, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Section(MastNode):
    """class Section"""
    def __init__ (self, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Ship(MastNode):
    """class Ship"""
    def __init__ (self, ship=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class SliderControl(MastNode):
    """class SliderControl"""
    def __init__ (self, is_int=None, var=None, q=None, props=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Style(MastNode):
    """class Style"""
    def __init__ (self, name, style=None, q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Text(MastNode):
    """class Text"""
    def __init__ (self, message, if_exp, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class TextInputControl(MastNode):
    """class TextInputControl"""
    def __init__ (self, var=None, label=None, q=None, style_name=None, style=None, style_q=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Update(MastNode):
    """class Update"""
    def __init__ (self, props=None, tag=None, shared=None, q=None, qp=None, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class WidgetList(MastNode):
    """class WidgetList"""
    def __init__ (self, clear, console, widgets, q, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
