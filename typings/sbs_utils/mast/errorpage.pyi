from sbs_utils.gui import Gui
from sbs_utils.gui import Page
class ErrorPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self, msg) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, sim, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def present (self, sim, event):
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation"""
