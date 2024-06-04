from sbs_utils.agent import Agent
from sbs_utils.mast.mast import Button
from sbs_utils.procedural.gui import ButtonPromise
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FrameContext
def _science_get_origin_id ():
    ...
def _science_get_selected_id ():
    ...
def has_role (so, role):
    """check if an agent has a role
    
    Args:
        so (an agent): an agent id or object
        role (str): the role to test for
    
    Returns:
        bool: if the agent has that role"""
def scan (path=None, buttons=None, timeout=None, auto_side=True):
    """Start a science scan
    
    Args:
        buttons (dict, optional): dictionary key = button, value = label. Defaults to None.
        timeout (_type_, optional): A promise typically by calling timeout(). Defaults to None.
        auto_side (bool, optional): If true quickly scans thing on the same side. Defaults to True.
    
    Returns:
        Promise: A promise to wait. Typically passed to an await/AWAIT"""
def scan_results (message, target=None, tab=None):
    """Set the scan results for the current scan. This should be called when the scan is completed.
       This is typically called as part of a scan()
       This could also be called in response to a routed science message.
       When pair with a scan() the target and tab are not need.
       Tab is the variable __SCAN_TAB__, target is track
    
    Args:
        message (str): scan text for a scan the is in progress
        tab (str): scan tab for a scan the is in progress"""
def science_add_scan (message, label=None, data=None, path=None):
    ...
def science_navigate (path):
    ...
def science_set_scan_data (player_id_or_obj, scan_target_id_or_obj, tabs):
    """Immediately set the science scan data for a scan target
       use this for things that you do not want to have scan delayed.
    
    Args:
        player_id_or_obj (agent): The player ship agent id or object
        scan_target_id_or_obj (agent): The target ship agent id or object
        tabs (dict): A dictionary to key = tab, value = scan string"""
def science_start_scan (origin_id_or_side, selected_id, tab):
    """Start the scan for a a science tab
    
    Args:
        origin_id_or_side (agent|str): If a string is passed it used as the player side, otherwise it use this as an agent to determine side
        selected_id (agent): Agent id or objects
        tab (str): The tab to start"""
def show_warning (t):
    ...
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
class ScanPromise(ButtonPromise):
    """class ScanPromise"""
    def __init__ (self, path, task, timeout=None, auto_side=True) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def cancel_if_no_longer_exists (self):
        ...
    def check_for_button_done (self):
        ...
    def initial_poll (self):
        ...
    def leave (self):
        ...
    def poll (self):
        ...
    def process_tab (self):
        ...
    def science_message (self, event):
        ...
    def science_selected (self, event):
        ...
    def set_path (self, path):
        ...
    def set_result (self, result):
        ...
    def set_scan_results (self, msg):
        ...
    def show_buttons (self):
        ...
    def start_scan (self, origin_id, selected_id, extra_tag):
        ...
