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
def get_inventory_value (id_or_object, key: str, default=None):
    """get inventory value with the given key the the agent  has
        this is the way to create a collection in inventory
    
    Args:
        id_or_obj (Agent | int): The agent id or object to check
        key (str): The key/name of the inventory item
        default (any): the default value data
    Returns:
        any: The inventory value associated with the provided key, or the default value if it doesn't exist."""
def gui_hole (count=1, style=None):
    """adds an empty column that is used by the next item
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    """Build a LayoutListBox gui element
    
    Args:
        items: A list of the items that should be included
        style (str): Custom style attributes
        item_template (list(str|LayoutListBoxHeader)): A list of strings, or, if a header is desired, then that item should be a LayoutListBoxHeader object
        title_template (str|callable): if a callable, will call the function to build the title. If a string, then title_template will be used as the title of the listbox
        section_style (str): Style attributes for each section
        title_section_style (str): Style attributes for the title
        select (boolean): If true, item(s) within the listbox can be selected.
        multi (boolean): If true, multiple items can be selected. Ignored if `select` is None
        carousel (boolean): If true, will use the carousel styling, e.g. the ship type selection menu
        collapsible (boolean): If true, clicking on a header will collapse everything until the next header
        read_only (boolean): Can the items be modified
    Returns:
        The LayoutListBox layout object"""
def gui_properties_set (p=None, tag=None):
    ...
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x0000029CAC5787C0>):
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
def set_inventory_value (so, key: str, value):
    """Set inventory value with the given key the the agent has.
    This is the way to create a collection in inventory.
    `so` can be a set. If it is, the inventory value is set for each member in the set.
    
    Args:
        id_or_obj (Agent | int | set[Agent | int]): The agent id or object or set to check
        key (str): The key/name of the inventory item
        value (any): the value"""
class PropertyControlItem(object):
    """class PropertyControlItem"""
    def __init__ (self, label, control):
        """Initialize self.  See help(type(self)) for accurate signature."""
