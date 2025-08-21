from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.pages.widgets.layout_listbox import LayoutListBoxHeader
def _get_property_list (values):
    """flatten a tree to a list
        """
def _gui_properties_items (values=None):
    ...
def _property_lb_item_template_one_line (item):
    ...
def _property_lb_item_template_two_line (item):
    ...
def get_inventory_value (id_or_object, key, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data"""
def gui_hole (count=1, style=None):
    """adds an empty column that is used by the next item
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    ...
def gui_properties_set (p=None, tag=None):
    ...
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x00000281904F44A0>):
    ...
def gui_property_list_box_stacked (name=None, tag=None):
    ...
def gui_represent (layout_item):
    """redraw an item
    
    ??? Note
        For sections it will recalculate the layout and redraw all items
    
    Args:
        layout_item (layout_item): """
def gui_reset_variables (task):
    ...
def gui_reset_variables_add (task, var_name):
    ...
def gui_row (style=None):
    """queue a gui row
    
    Args:
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_text (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def set_inventory_value (so, key, value):
    """set inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (agent): The agent id or object to check
        key (str): The key/name of the inventory item
        value (any): the value"""
class PropertyControlItem(object):
    """class PropertyControlItem"""
    def __init__ (self, label, control):
        """Initialize self.  See help(type(self)) for accurate signature."""
