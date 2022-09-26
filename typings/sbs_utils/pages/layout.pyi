from sbs_utils.gui import Page
class Column(object):
    """class Column"""
    def __init__ (self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def layout (self, height=0, left=0, top=0, right=0, bottom=0) -> None:
        ...
class Face(Column):
    """class Face"""
    def __init__ (self, face, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
class Layout(object):
    """class Layout"""
    def __init__ (self, rows=None, left=0, top=0, width=100, height=100) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, row: sbs_utils.pages.layout.Row):
        ...
    def calc (self):
        ...
    def present (self, sim, client_id):
        ...
class LayoutPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, event):
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param sim:
        :type sim: Artemis Cosmos simulation"""
class Row(object):
    """class Row"""
    def __init__ (self, cols=None, width=0, height=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, col):
        ...
    def clear (self):
        ...
    def present (self, sim, client_id):
        ...
class Separate(Column):
    """class Separate"""
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
class Ship(Column):
    """class Ship"""
    def __init__ (self, ship, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
class Text(Column):
    """class Text"""
    def __init__ (self, message, tag) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def present (self, sim, client_id):
        ...
