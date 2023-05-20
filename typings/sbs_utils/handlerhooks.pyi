from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.gui import Context
from sbs_utils.gui import Gui
from sbs_utils.gui import Page
from sbs_utils.damagedispatcher import DamageDispatcher
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
def cosmos_event_handler (sim, event):
    ...
class ErrorPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self, msg) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_message (self, ctx, event):
        """on_message
        
        Called when the option pages page has been interacted with
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation
        :param event: The event data
        :type event: event"""
    def present (self, ctx, event):
        """present
        
        Called to have the page create and update the gui content it is presenting
        
        :param ctx:
        :type ctx: Artemis Cosmos simulation"""
