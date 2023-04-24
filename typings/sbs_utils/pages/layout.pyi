from sbs_utils.gui import Page
from sbs_utils.widgets.shippicker import ShipPicker
def merge_props (d):
    ...
def split_props (s, def_key):
    ...
class Blank(Column):
    """class Blank"""
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
class Bounds(object):
    """class Bounds"""
    def __init__ (self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def height (self):
        ...
    @property
    def width (self):
        ...
class Button(Column):
    """class Button"""
    def __init__ (self, tag, message) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Checkbox(Column):
    """class Checkbox"""
    def __init__ (self, tag, message, value=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Column(object):
    """class Column"""
    def __init__ (self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def set_bounds (self, bounds) -> None:
        ...
    def set_col_width (self, width):
        ...
    def set_padding (self, padding):
        ...
    def set_row_height (self, height):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, a):
        ...
class ConsoleWidget(Column):
    """class ConsoleWidget"""
    def __init__ (self, widget) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class Dropdown(Column):
    """class Dropdown"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Face(Column):
    """class Face"""
    def __init__ (self, tag, face) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class GuiControl(Column):
    """class GuiControl"""
    def __init__ (self, tag, content) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    def set_bounds (self, bounds) -> None:
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Hole(Column):
    """class Hole"""
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
class Icon(Column):
    """class Icon"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class IconButton(Column):
    """class IconButton"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Image(Column):
    """class Image"""
    def __init__ (self, tag, file) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def get_image_size (self):
        ...
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Layout(object):
    """class Layout"""
    def __init__ (self, click_props=None, rows=None, left=0, top=0, right=100, bottom=100, left_pixels=False, top_pixels=False, right_pixels=False, bottom_pixels=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, row: sbs_utils.pages.layout.Row):
        ...
    def calc (self):
        ...
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    def set_bounds (self, bounds):
        ...
    def set_col_width (self, width):
        ...
    def set_row_height (self, height):
        ...
class LayoutPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        """Present the gui """
class RadioButton(Column):
    """class RadioButton"""
    def __init__ (self, tag, message, group, value=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class RadioButtonGroup(Column):
    """class RadioButtonGroup"""
    def __init__ (self, tag, buttons, value, vertical) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    def set_bounds (self, bounds) -> None:
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Row(object):
    """class Row"""
    def __init__ (self, cols=None, width=0, height=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, col):
        ...
    def clear (self):
        ...
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    def set_col_width (self, width):
        ...
    def set_row_height (self, height):
        ...
class Ship(Column):
    """class Ship"""
    def __init__ (self, tag, ship) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Slider(Column):
    """class Slider"""
    def __init__ (self, tag, value, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class Text(Column):
    """class Text"""
    def __init__ (self, tag, message) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class TextInput(Column):
    """class TextInput"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        ...
    def present (self, sim, event):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
