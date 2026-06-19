from sbs_utils.agent import Agent
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.pages.widgets.layout_listbox import SubPage
from sbs_utils.tickdispatcher import TickDispatcher
def gui_page_for_client (client_id):
    """Return the active GUI page for a client.
    
    Args:
        client_id (int): The client to look up.
    
    Returns:
        Page | None: The client's current page, or ``None`` if unavailable.
    
    Example:
        page = gui_page_for_client(CLIENT_ID)
        if page is not None:
            ~~ page.dirty() ~~"""
def gui_percent_from_pixels (client_id, pixels):
    """Convert a pixel size to GUI percentage coordinates for a client's screen.
    
    GUI layout positions are expressed as percentages (0–100) of the screen
    dimensions. Use this to convert a fixed pixel measurement to the equivalent
    percentage for a specific client's resolution.
    
    Args:
        client_id (int): The client whose screen resolution to use.
        pixels (float): The pixel size to convert.
    
    Returns:
        Vec3: Percentage values (x=horizontal %, y=vertical %, z=0).
    
    Example:
        pct = gui_percent_from_pixels(CLIENT_ID, 40)
        gui_section(style="height:{pct.y}%;")"""
def gui_task_for_client (client_id):
    """Return the GUI task currently running for a client.
    
    Each connected client has a dedicated GUI task that drives its page layout.
    Returns ``None`` if the client has no active page.
    
    Args:
        client_id (int): The client to look up.
    
    Returns:
        MastAsyncTask | None: The client's GUI task, or ``None`` if unavailable.
    
    Example:
        task = gui_task_for_client(CLIENT_ID)
        if task is not None:
            ~~ task.set_variable("score", 10) ~~"""
def tabbed_panel_control (tag_prefix, items, tab=0, tab_location=0):
    ...
class TabbedPanel(Column):
    """class TabbedPanel"""
    def __init__ (self, left, top, right, bottom, tag_prefix, panels=None, tab=0, tab_location=0, icon_size=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def find_tab (self, tab):
        ...
    def on_end_presenting (self, client_id):
        ...
    def on_message (self, event):
        ...
    def present (self, event):
        ...
    def present_icon (self, event, icon, index, icon_size):
        ...
    def present_panel (self, event, panel, icon_size):
        ...
    def set_tab (self, tab):
        ...
    def set_tab_tick_cb (self, cb):
        ...
    def tick_tab (self, t):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
