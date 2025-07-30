from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
def gui_hide (layout_item):
    """If the item is visible it will make it hidden
    
    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout.
        so you may also need to pair this with a gui_represent of a section
    
    Args:
        layout_item (layout_item): """
def gui_rebuild (region):
    """prepares a section/region to be build a new layout
    
    Args:
        region (layout_item): a layout/Layout item
    
    Returns:
        layout object: The Layout object created"""
def gui_refresh (label):
    """refresh any gui running the specified label
    
    Args:
        label (label): A mast label"""
def gui_represent (layout_item):
    """redraw an item
    
    ??? Note
        For sections it will recalculate the layout and redraw all items
    
    Args:
        layout_item (layout_item): """
def gui_show (layout_item):
    """gui show. If the item is hidden it will make it visible again
    
    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout.
        so you may also need to pair this with a gui_represent of a section
    
    Args:
        layout_item (layout_item): """
def gui_update (tag, props, shared=False, test=None):
    """Update the properties of a current gui element
    
    Args:
        tag (str):
        props (str): The new properties to use
        shared (bool, optional): Update all gui screen if true. Defaults to False.
        test (dict, optional): Check the variable (key) update if any value is different than the test. Defaults to None."""
def gui_update_shared (tag, props, test=None):
    ...
