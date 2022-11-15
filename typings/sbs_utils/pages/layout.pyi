from sbs_utils.gui import Page
class Blank(Column):
    """class Blank"""
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
class Button(Column):
    """class Button"""
    def __init__ (self, message, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class Checkbox(Column):
    """class Checkbox"""
    def __init__ (self, message, tag, value=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class Column(object):
    """class Column"""
    def __init__ (self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def layout (self, height=0, left=0, top=0, right=0, bottom=0) -> None:
        ...
class Dropdown(Column):
    """class Dropdown"""
    def __init__ (self, value, values, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class Face(Column):
    """class Face"""
    def __init__ (self, face, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class Hole(Column):
    """class Hole"""
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
class Image(Column):
    """class Image"""
    def __init__ (self, file, color, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def get_image_size (self):
        ...
    def present (self, sim, event):
        ...
class Layout(object):
    """class Layout"""
    def __init__ (self, rows=None, left=0, top=0, right=100, bottom=100, left_pixels=False, top_pixels=False, right_pixels=False, bottom_pixels=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, row: sbs_utils.pages.layout.Row):
        ...
    def calc (self):
        ...
    def present (self, sim, event):
        ...
    def set_default_height (self, height):
        ...
    def set_size (self, left=0, top=0, right=100, bottom=100):
        ...
class LayoutPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        """Present the gui """
class Row(object):
    """class Row"""
    def __init__ (self, cols=None, width=0, height=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, col):
        ...
    def clear (self):
        ...
    def present (self, sim, event):
        ...
class Ship(Column):
    """class Ship"""
    def __init__ (self, ship, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class Slider(Column):
    """class Slider"""
    def __init__ (self, value=0.5, low=0.0, high=1.0, tag=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class Text(Column):
    """class Text"""
    def __init__ (self, message, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
class TextInput(Column):
    """class TextInput"""
    def __init__ (self, value, label, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        ...
