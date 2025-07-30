from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.mast.pollresults import PollResults
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Creates a entity to wait (non-blocking) for a promise to complete
    
    Args:
        Promise: A promise """
def _science_get_origin_id ():
    ...
def _science_get_selected_id ():
    ...
def awaitable (func):
    ...
def create_scan_label ():
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def labels_get_type (label_type):
    ...
def scan (*args, **kwargs):
    ...
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
def science_ensure_scan (ids_or_objs, target_ids_or_objs, tabs='scan'):
    ...
def science_get_scan_data (origin, target, tab='scan') -> str:
    """Get the science scan as seen by the ship doing the scan.
    Args:
        origin (int|Agent): The ship doing the scan
        target (int|Agent): The target space object
        tab (str): The science tab the info goes to
    Returns:
        str: The applicable scan data"""
def science_has_scan_data (origin, target, tab='scan') -> bool:
    """Check if the target is has scan data for the scanning ship.
    Args:
        origin (int|Agent): The ship doing the scan (probably a player ship)
        target (int|Agent): The target space object
        tab (str): The science tab being checked (optional, default is 'scan')
    Returns:
        bool: True if the scan data exists"""
def science_is_unknown (origin, target) -> bool:
    """Check if the target is known to the given ship.
    Based on the 'scan' tab on the science widget.
    To use a different tab, use `science_has_scan_data()` instead
    Args:
        origin (int|Agent): The ship doing the scan (probably a player ship)
        target (int|Agent): The target space object"""
def science_navigate (path):
    ...
def science_set_2dview_focus (client_id, focus_id=0):
    ...
def science_set_scan_data (player_id_or_obj, scan_target_id_or_obj, tabs):
    """Immediately set the science scan data for a scan target
       use this for things that you do not want to have scan delayed.
    
    Args:
        player_id_or_obj (agent): The player ship agent id or object
        scan_target_id_or_obj (agent): The target ship agent id or object
        tabs (dict): A dictionary to key = tab, value = scan string"""
def science_update_scan_data (origin, target, info, tab='scan'):
    """Immediately update the scan data of the target space object for the scanning ship.
    NOTE: Only use this if the scanning ship has already scanned the target, and the scan text needs to be updated,
    or if you want to forcibly add the scan info a ship even if it hasn't been scanned yet.
    Args:
        origin (int|Agent): The scanning ship (probably a player ship)
        target (int|Agent): The object being scanned
        info (str): The new scan information
        tab (str): The science tab to which the info belongs (e.g. 'scan' or 'intel')"""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
def show_warning (t):
    ...
def start_science_message (event):
    """This is how AUTOSCAN AUTO SCAN is accomplished
    
    Args:
        event (_type_): _description_"""
def start_science_selected (event):
    ...
def task_all (*args, **kwargs):
    ...
def to_blob (id_or_obj):
    """gets the engine dataset of the specified agent
    
    !!! Note
        Same as to_data_set
    
    Args:
        id_or_obj (agent): Agent id or object
    
    Returns:
        data set| None: Returns the data or None if it does not exist"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
def to_object_list (the_set):
    """to_object_list
    converts a set to a list of objects
    
    Args:
        the_set (set|list): a set of agent ids
    
    Returns:
        list: of Agents"""
class ScanPromise(ButtonPromise):
    """class ScanPromise"""
    def __init__ (self, path, task, timeout=None, auto_side=True) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def cancel_if_no_longer_exists (self):
        ...
    def check_for_button_done (self):
        ...
    def collect (self):
        ...
    def initial_poll (self):
        ...
    def leave (self):
        ...
    def message (self, event):
        ...
    def poll (self):
        ...
    def process_tab (self):
        ...
    def selected (self, event):
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
