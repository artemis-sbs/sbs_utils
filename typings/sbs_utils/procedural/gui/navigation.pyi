from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
def _gui_reroute_main (label, server):
    ...
def gui_history_back ():
    """Jump back in history
    
        """
def gui_history_clear ():
    """Clears the history for the given page
        """
def gui_history_forward ():
    """Jump forward in history
        """
def gui_history_jump (to_label, back_name=None, back_label=None, back_data=None):
    """Jump to a new gui label, but remember how to return to the current state
    
    Args:
        to_label (label): Where to jump to
        back_name (str): A name to use if displayed
        back_label (label, optional): The label to return to defaults to the label active when called
        back_data (dict, optional): A set of value to set when returning back
    
    ??? Note:
        If there is forward history it will be cleared
    
    Returns:
        results (PollResults): PollResults of the jump"""
def gui_history_redirect (back_name=None, back_label=None, back_data=None):
    ...
def gui_history_store (back_text, back_label=None):
    """store the current
    
    Args:
        label (label): A mast label"""
def gui_reroute_client (client_id, label, data=None):
    ...
def gui_reroute_clients (label, data=None, exclude=None):
    """reroute client guis to run the specified label
    
    Args:
        label (label): Label to jump to
        exclude (set, optional): set client_id values to exclude. Defaults to None."""
def gui_reroute_server (label, data=None):
    """reroute server gui to run the specified label
    
    Args:
        label (label): Label to jump to"""
