from sbs_utils.pages.widgets.control import Control
from sbs_utils.gui import Widget
def ship_picker_control (title_prefix='Ship:', cur=None, ship_keys=None, roles=None, sides=None, show_desc=True):
    ...
class ShipPicker(Control):
    """A widget to select a ship"""
    def __init__ (self, left, top, tag_prefix, title_prefix='Ship:', cur=None, ship_keys=None, roles=None, sides=None, show_desc=True) -> None:
        """Ship Picker widget
        
        A widget the combines a title, ship viewer, next and previous buttons for selecting ships
        
        :param left: left coordinate
        :type left: float
        :param top: top coordinate
        :type top: float
        :param tag: Prefix to use in message tags to mak this component unique
        :type tag: str"""
    def _present (self, event):
        """present
        
        builds/manages the content of the widget
        
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int"""
    def get_selected (self):
        """get selected
        
        :return: None or string of ship selected
        :rtype: None or string of ship selected"""
    def get_selected_name (self):
        """get selected
        
        :return: None or string of ship selected
        :rtype: None or string of ship selected"""
    def get_value (self):
        ...
    def on_message (self, event):
        """on_message
        
        handles messages this will look for components owned by this control and react accordingly
        components owned will have the tag_prefix
        
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param message_tag: Tag of the component
        :type message_tag: str
        :param CID: Client ID
        :type CID: int
        :param data: unused no component use data
        :type data: any"""
    @property
    def read_only (self):
        ...
    @read_only.setter
    def read_only (self, value):
        ...
    def set_selected (self, key):
        """set selected
        
        :return: None or string of ship selected
        :rtype: None or string of ship selected"""
    def set_value (self, value):
        ...
    def update (self, props):
        ...
