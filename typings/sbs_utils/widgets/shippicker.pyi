from sbs_utils.gui import Widget
def filter_ship (ship):
    ...
class ShipPicker(Widget):
    """A widget to select a ship"""
    def __init__ (self, left, top, tag_prefix, title_prefix='Ship:') -> None:
        """Ship Picker widget
        
        A widget the combines a title, ship viewer, next and previous buttons for selecting ships
        
        :param left: left coordinate
        :type left: float
        :param top: top coordinate
        :type top: float
        :param tag_prefix: Prefix to use in message tags to mak this component unique
        :type tag_prefix: str"""
    def get_selected (self):
        """get selected
        
        :return: None or string of ship selected
        :rtype: None or string of ship selected"""
    def on_message (self, sim, event):
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
    def present (self, sim, event):
        """present
        
        builds/manages the content of the widget
        
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int"""
