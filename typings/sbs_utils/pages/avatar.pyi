from sbs_utils.gui import Gui
from sbs_utils.gui import Page
class AvatarEditor(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param event: The event data
        :type event: event"""
    def present (self, event):
        """present
        
        Called to have the page create and update the gui content it is presenting"""
    def reset_values (self):
        ...
