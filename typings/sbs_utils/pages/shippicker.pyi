from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.pages.widgets.shippicker import WShipPicker
class ShipPicker(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def get_selected (self):
        ...
    def on_message (self, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def present (self, event):
        """present
        
        Called to have the page create and update the gui content it is presenting"""
