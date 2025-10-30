from sbs_utils.pages.widgets.control import Control
from sbs_utils.helpers import FrameContext
def ship_picker_control (title_prefix='Ship:', cur=None, ship_keys=None, roles=None, sides=None, show_desc=True):
    """Build a ShipPicker widget, which allows players to choose what ship they wish to crew.
    Args:
        tag_prefix (str): Prefix to use in message tags to make this component unique
        title_prefix (str): Prefix to use in the title. Optional, default 'Ship'.
        cur (int): The current selected index. Optional, default is None.
        ship_keys (list[str]): The list of ship keys with which the ShipPicker is populated. Optional, default is None.
        roles (list[str]): The roles by which ship keys are filtered. Optional, default is None.
        sides (list[str]): The sides by which ship keys are filtered. Optional, default is None.
        show_desc (bool): Should the ShipPicker include the description of the ship? Optional, default is True."""
class ShipPicker(Control):
    """A widget to select a ship"""
    def __init__ (self, left, top, tag_prefix, title_prefix='Ship:', cur=None, ship_keys=None, roles=None, sides=None, show_desc=True) -> None:
        """Ship Picker widget
        
        A widget the combines a title, ship viewer, next and previous buttons for selecting ships
        
        Args:
            left (float): left coordinate
            top (float): top coordinate
            tag_prefix (str): Prefix to use in message tags to make this component unique
            title_prefix (str): Prefix to use in the title. Optional, default 'Ship'.
            cur (int): The current selected index. Optional, default is None.
            ship_keys (list[str]): The list of ship keys with which the ShipPicker is populated. Optional, default is None.
            roles (list[str]): The roles by which ship keys are filtered. Optional, default is None.
            sides (list[str]): The sides by which ship keys are filtered. Optional, default is None.
            show_desc (bool): Should the ShipPicker include the description of the ship? Optional, default is True."""
    def _present (self, event):
        """present
        
        builds/manages the content of the widget
        
        Args:
            event (event): The event that triggered the gui to update."""
    def get_selected (self):
        """Get the key of the selected ship.
        
        Returns:
            str|None: The selected ship key."""
    def get_selected_name (self):
        """Get the name of the selected ship.
        
        Returns:
            str|None: The name of the selected ship as defined in the shipData."""
    def get_value (self):
        ...
    def on_message (self, event):
        """on_message
        
        handles messages this will look for components owned by this control and react accordingly
        components owned will have the tag_prefix
        
        Args:
            event (event): The event that triggered the update"""
    @property
    def read_only (self):
        ...
    @read_only.setter
    def read_only (self, value):
        ...
    def set_selected (self, key):
        """Set the selected ship by key as defined in the shipData.
        Args:
            key (str): The key of the ship which should be selected."""
    def set_value (self, value):
        ...
    def update (self, props):
        ...
