from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.mast.pollresults import PollResults
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Wrap a promise in a non-blocking waiter.
    
    Returns a ``PromiseWaiter`` whose ``done()`` method can be polled each tick
    without suspending the current task.
    
    Args:
        promise (Promise): The promise to wait on.
    
    Returns:
        PromiseWaiter: A waiter that reports completion without blocking."""
def _science_get_origin_id ():
    ...
def _science_get_selected_id ():
    ...
def awaitable (func):
    ...
def create_scan_label ():
    ...
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def labels_get_type (label_type):
    """Return all labels whose type or path starts with the given prefix.
    
    Walks every label in the current story, checking the ``type`` metadata key
    first, then the label ``path`` attribute, then the label name.
    
    Args:
        label_type (str): Prefix to match, e.g. ``"map/"`` or ``"media/"``.
    
    Returns:
        list[MastNode]: Matching label objects."""
def scan (path=None, buttons=None, timeout=None, auto_side=True):
    """Start a science scan and return a promise that resolves when scanning is complete.
    
    Args:
        path (str, optional): Route path prefix for scan button labels. Defaults
            to None.
        buttons (dict, optional): Extra buttons as ``{label_text: label}`` pairs.
            Defaults to None.
        timeout (Promise, optional): A timeout promise (e.g. from
            ``timeout()``). Defaults to None.
        auto_side (bool, optional): Instantly complete scanning for same-side
            objects. Defaults to True.
    
    Returns:
        ScanPromise: A promise to ``await``; resolves when all tabs are scanned."""
def scan_results (message, target=None, tab=None):
    """Set the scan results for the current scan. This should be called when the scan is completed.
       This is typically called as part of a scan()
       This could also be called in response to a routed science message.
       When paired with a scan() the target and tab are not needed.
       Tab is the variable __SCAN_TAB__, target is track
    
    Args:
        message (str): Scan text for a scan that is in progress.
        target (Any, optional): Not currently used. Default is None.
        tab (str, optional): Scan tab for a scan that is in progress. Default is None."""
def science_add_scan (message, label=None, data=None, path=None):
    """Add a scan button to the current science scan promise.
    
    Args:
        message (str): Button text shown in the science UI.
        label (str | Label, optional): Label to run when the button is pressed.
        data (dict, optional): Variables passed to the button's label.
        path (str, optional): Route path to navigate to when pressed."""
def science_ensure_scan (ids_or_objs, target_ids_or_objs, tabs='scan'):
    """Force a completed scan result onto all (scanner, target) pairs.
    
    Useful for scripted encounters where objects should appear pre-scanned
    without waiting for player interaction. Pass ``tabs="*"`` to populate
    every tab the target exposes.
    
    Args:
        ids_or_objs (set[Agent | int]): The scanning player ship(s).
        target_ids_or_objs (set[Agent | int]): The object(s) to mark as
            scanned.
        tabs (str): Comma-separated tab names, or ``"*"`` for all tabs.
            Defaults to ``"scan"``."""
def science_get_scan_data (origin, target, tab='scan') -> str:
    """Return the scan text on a tab as seen by the scanning ship.
    
    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object being scanned.
        tab (str): Science tab to read. Defaults to ``"scan"``.
    
    Returns:
        str: The scan text, or ``None`` if not yet scanned."""
def science_has_scan_data (origin, target, tab='scan') -> bool:
    """Return ``True`` if the target has real scan data on the given tab.
    
    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object to check.
        tab (str): Science tab to check. Defaults to ``"scan"``.
    
    Returns:
        bool: ``True`` if scan data exists and is not empty or default."""
def science_is_unknown (origin, target) -> bool:
    """Return ``True`` if the target has not been scanned by the scanning ship.
    
    Checks the ``"scan"`` tab. Use ``science_has_scan_data`` to check a
    different tab.
    
    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object to check.
    
    Returns:
        bool: ``True`` if the target is unscanned or shows default/empty data."""
def science_navigate (path):
    """Navigate the current science GUI task to a new button path.
    
    Args:
        path (str): The science route path to navigate to."""
def science_set_2dview_focus (client_id, focus_id=0):
    """Focus the science 2D view of a client console on a specific object.
    
    Args:
        client_id (int): The client console ID.
        focus_id (int, optional): ID of the object to focus on. ``0`` clears
            the focus. Defaults to 0."""
def science_set_scan_data (player_id_or_obj, scan_target_id_or_obj, tabs):
    """Set science scan data for a target immediately, bypassing the normal scan delay.
    
    Args:
        player_id_or_obj (Agent | int): The scanning player ship.
        scan_target_id_or_obj (Agent | int): The object being scanned.
        tabs (dict | str): Tab-name → scan-text mapping. A bare string is
            treated as ``{"scan": string}``."""
def science_update_scan_data (origin, target, info, tab='scan'):
    """Update (or forcibly set) the scan text on a specific tab for a scanning ship.
    
    Use when the target has already been scanned and the text needs to change, or
    to inject scan data without requiring the player to scan first.
    
    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object being scanned.
        info (str): The new scan text.
        tab (str): The science tab to update (e.g. ``"scan"``, ``"intel"``).
            Defaults to ``"scan"``."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def show_warning (t):
    """Print a warning message to the F7 debug screen.
    
    Args:
        t (str): The message to display."""
def start_science_message (event):
    """Handle a science message event, emitting a ``science_auto_scan`` signal.
    
    This is the mechanism behind the auto-scan feature. Called automatically
    by ``ConsoleDispatcher`` for ``science_target_UID`` message events.
    
    Args:
        event: Engine message event carrying the auto-scan trigger."""
def start_science_selected (event):
    """Start or resume a science scan for the given selection event.
    
    Creates a new ``ScanPromise`` for the (origin, selected) pair if none
    exists; otherwise returns the existing one. Called automatically by
    ``ConsoleDispatcher`` for ``science_target_UID`` select events.
    
    Args:
        event: Engine selection event that triggered the scan.
    
    Returns:
        ScanPromise | None: The active scan promise, or ``None`` if the origin
            or target no longer exists."""
def task_all (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Schedule a task for each label and wait until all tasks complete.
    
    Args:
        *args (label): Labels to schedule as parallel tasks.
        data (dict, optional): Keyword argument passed as initial variables to
            every task. Defaults to None.
        sub_tasks (bool, optional): Run as sub-tasks instead of top-level
            tasks. Defaults to False.
    
    Returns:
        TaskPromiseAllAny: A promise that resolves when all tasks complete.
    
    Example:
        await task_all(patrol_alpha, patrol_beta, patrol_gamma)"""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
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
