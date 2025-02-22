from ...helpers import FrameContext
from ..inventory import get_inventory_value, set_inventory_value
from ... import yaml
from .hole import gui_hole
from .row import gui_row
from .listbox import gui_list_box
from .text import gui_text
from .update import gui_represent
from ...pages.widgets.layout_listbox import LayoutListBoxHeader
from ...agent import Agent

class PropertyControlItem:
    def __init__(self, label, control):
        self.label = label
        self.control = control


def _get_property_list(values):
    """ flatten a tree to a list
    """
    ret = []
    for k in values:
        v = values[k]
        if isinstance(v,dict):
            collapse = False
            if k.startswith("+"):
                k = k[1:]
            if k.startswith("-"):
                k = k[1:]
                collapse = True

            ret.append(LayoutListBoxHeader(k, collapse))
            ret.extend(_get_property_list(v))
            continue

        ret.append(PropertyControlItem(k,v))

    return ret


def _gui_properties_items(values=None):
    if values is None:
        return []
    
    try:
        if isinstance(values, str):
            values = yaml.safe_load(values)
        # Initially trying flat 
        return _get_property_list(values)
    except yaml.YAMLError:
        return []
    


def gui_properties_set(p=None, tag=None):
    # 
    # This is confusing because of COMMS
    # Comms runs on the sever task, but the GUI needs 
    # to be the client for the comms operations
    # So COMMS is setting the page to the client
    # and the server task is the task
    #
    page = FrameContext.page
    task = FrameContext.task
    FrameContext.page = None

    true_page = FrameContext.page
    if true_page is None:
        return
    gui_task = true_page.gui_task

    
    tag = tag if tag is not None else "__PROPS_LB__"
    props_lb = gui_task.get_inventory_value(tag)
    if props_lb is None:
        return
    
    props_lb.items = _gui_properties_items(p)
    gui_represent(props_lb)
    FrameContext.page = page
    FrameContext.task = task
    



def _property_lb_item_template_one_line(item):
    
    collapsable =  isinstance(item, LayoutListBoxHeader)
    if collapsable:
        gui_row("row-height: 1em;padding:5px,0,5px,0;")
        if not item.collapse:
            gui_text(f"$text:{item.label};justify: center;color:#02FF;", "background: #FFFC")
        else:
            gui_text(f"$text:{item.label};justify: center;color:#FFF;", "background: #0173")
    else:
        gui_row("row-height: 1.5em;padding:5px,0,5px,0;")
        #gui_row("row-height: 1.2em;padding:13px;")
        gui_text(f"$text:{item.label};justify: right;","padding:0,0,1em,0;")
        gui_hole()
        gui_c = FrameContext.task.eval_code(item.control, False)
        if gui_c is None:
            gui_text(f"Invalid code")
    

def _property_lb_item_template_two_line(item):
    collapsable =  isinstance(item, LayoutListBoxHeader)
    if collapsable:
        gui_row("row-height: 1em;padding:5px,0,5px,0;")
        if not item.collapse:
            gui_text(f"$text:{item.label};justify: center;color:#02FF;", "background: #FFFC")
        else:
            gui_text(f"$text:{item.label};justify: center;color:#FFF;", "background: #0173")
    else:
        gui_row("row-height: 1.2em;")
        gui_text(f"$text:{item.label};justify: left;")
        gui_row("row-height: 2em;")

        gui_c = FrameContext.task.eval_code(item.control, False)
        if gui_c is None:
            gui_text(f"Invalid code")
    
def gui_property_list_box_stacked(name=None, tag=None):
    task = FrameContext.task
    tag = tag if tag is not None else "__PROPS_LB__"
    name = name if name is not None else "Properties"

    props_lb = gui_list_box([],
                "row-height: 0.5em; background:#1572;", 
                item_template=_property_lb_item_template_two_line, title_template=name, collapsible=True)
    
    props_lb.title_section_style += "background:#1578;"
    task.set_inventory_value(tag, props_lb)    
    return props_lb

def gui_property_list_box(name=None, tag=None, temp = _property_lb_item_template_one_line):
    task = FrameContext.task
    tag = tag if tag is not None else "__PROPS_LB__"
    name = name if name is not None else "Properties"

    props_lb = gui_list_box([],
                "row-height: 0.5em; background:#1572;", 
                item_template=temp, title_template=name, collapsible=True)
    
    props_lb.title_section_style += "background:#1578;"
    task.set_inventory_value(tag, props_lb)    
    return props_lb
