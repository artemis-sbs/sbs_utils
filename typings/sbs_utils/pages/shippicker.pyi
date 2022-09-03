from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.widgets.shippicker import WShipPicker
class ShipPicker(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def get_selected (self):
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
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param sim:
        :type sim: Artemis Cosmos simulation"""
