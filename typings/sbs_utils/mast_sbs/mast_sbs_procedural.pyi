from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mast_globals import MastGlobals
def func(*argv):
    """assign_client_to_alt_ship(clientComputerID: int, controlledShipID: int) -> None
    
    Tells a client computer that the 2d radar should focus on controlledShipID, instead of its assigned ship.  Turn this code off by providing zero as the second argument."""
def handle_purge_tasks (so):
    """This will clear out all tasks related to the destroyed item"""
def mast_assert (cond):
    ...
def mast_format_string (s):
    ...
def mast_log (message: str, name: str = None, level: str = None, use_mast_scope=True) -> None:
    """Generate a log message formatted through the current MAST task scope.
    
    Convenience wrapper around ``log`` with ``use_mast_scope=True``.
    
    Args:
        message (str): The message to log. May contain MAST format strings.
        name (str, optional): Logger name. Defaults to None.
        level (str, optional): Logging level string. Defaults to None."""
