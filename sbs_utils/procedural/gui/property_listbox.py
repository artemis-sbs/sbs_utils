from ...helpers import FrameContext, FrameContextOverride
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
        print(f"GUI Properties Invalid YAML\n     {values}")
        return []
    


def gui_properties_set(p=None, tag=None):
    # 
    # This is confusing because of COMMS
    # Comms runs on the sever task, but the GUI needs 
    # to be the client for the comms operations
    # So COMMS is setting the page to the client
    # and the server task is the task
    #
    gui_task = FrameContext.client_task
    gui_page = FrameContext.client_page
    event = FrameContext.context.event
    # This happens in a follow_route_select_comms
    # And it runs on the server not a true comms console
    if event.tag == "gui_present":
        return
    #print(f"TAG {event.tag}")
    changes = set(gui_task.get_variable("__PROP_CHANGES__", []))
    gui_task.on_change_items = [change for change in gui_task.on_change_items if change not in changes]
    gui_task.set_variable("__PROP_CHANGES__", [])


    with FrameContextOverride(FrameContext.client_task, FrameContext.client_page):
        tag = tag if tag is not None else "__PROPS_LB__"
        props_lb = gui_task.get_inventory_value(tag)
        if props_lb is None:
            print(f"No properties found {gui_page.client_id}")
            return
        props_lb.items = _gui_properties_items(p)
        # Clear the on changes
        gui_represent(props_lb)
        

def gui_properties_get_value(key, defa=None):
    # 
    # This is confusing because of COMMS
    # Comms runs on the sever task, but the GUI needs 
    # to be the client for the comms operations
    # So COMMS is setting the page to the client
    # and the server task is the task
    #
    gui_task = FrameContext.client_task
    
    if gui_task is not None:
        v = gui_task.get_variable(key, defa)
        return v
    
    return defa

def gui_properties_set_value(key, value=None):
    # 
    # This is confusing because of COMMS
    # Comms runs on the sever task, but the GUI needs 
    # to be the client for the comms operations
    # So COMMS is setting the page to the client
    # and the server task is the task
    #
    gui_task = FrameContext.client_task
    if gui_task is not None:
        return gui_task.set_variable(key, value)
    return value


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
    task = FrameContext.client_task
    tag = tag if tag is not None else "__PROPS_LB__"
    name = name if name is not None else "Properties"

    props_lb = gui_list_box([],
                "row-height: 0.5em; background:#1572;", 
                item_template=_property_lb_item_template_two_line, title_template=name, collapsible=True)
    
    props_lb.title_section_style += "background:#1578;"
    task.set_inventory_value(tag, props_lb)
    gui_reset_variables_add(task, tag)

    return props_lb

def gui_property_list_box(name=None, tag=None, temp = _property_lb_item_template_one_line):
    gui_task = FrameContext.client_task

    tag = tag if tag is not None else "__PROPS_LB__"
    name = name if name is not None else "Properties"

    props_lb = gui_list_box([],
                "row-height: 0.5em; background:#1572;", 
                item_template=temp, title_template=name, collapsible=True)
    
    props_lb.title_section_style += "background:#1578;"
    gui_task.set_inventory_value(tag, props_lb)
    gui_reset_variables_add(gui_task, tag)

    return props_lb

def gui_reset_variables_add(task, var_name):
    tags = task.get_inventory_value("__CLEAR_ON_CHANGE__", set())
    tags.add(var_name)
    task.set_inventory_value("__CLEAR_ON_CHANGE__", tags)

def gui_reset_variables(task):
    tags = task.get_inventory_value("__CLEAR_ON_CHANGE__", set())
    for tag in tags:
        task.set_inventory_value(tag, None)
    task.set_inventory_value("__CLEAR_ON_CHANGE__", set())