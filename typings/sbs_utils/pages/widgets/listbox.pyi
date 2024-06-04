from sbs_utils.pages.widgets.control import Control
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Widget
def get_client_aspect_ratio (cid):
    ...
def list_box_control (items, text=None, face=None, ship=None, icon=None, image=None, title=None, background=None, title_background=None, select=False, multi=False, item_height=5, convert_value=None):
    ...
class Listbox(Control):
    """A widget to list things passing function/lamdas to get the data needed for option display of
    - face
    - ship
    - icon
    - text"""
    def __init__ (self, left, top, tag_prefix, items, text=None, face=None, ship=None, icon=None, image=None, title=None, background=None, title_background=None, select=False, multi=False, item_height=5, convert_value=None) -> None:
        """Listbox
        
        A widget Shows a list of things
        
        :param left: left coordinate
        :type left: float
        :param top: top coordinate
        :type top: float
        :param tag_prefix: Prefix to use in message tags to mak this component unique
        :type tag_prefix: str"""
    def _present (self, event):
        """present
        
        builds/manages the content of the widget
        
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int"""
    def get_image_size (self, file):
        ...
    def get_selected (self):
        ...
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
    def select_all (self):
        ...
    def select_none (self):
        ...
    def set_value (self, value):
        ...
    def update (self, props):
        ...
