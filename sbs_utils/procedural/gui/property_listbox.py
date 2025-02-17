from ...helpers import FrameContext
from ..inventory import get_inventory_value, set_inventory_value
from ... import yaml
from .hole import gui_hole
from .row import gui_row
from .listbox import gui_list_box
from .text import gui_text
from .update import gui_represent



def _get_property_list(values):
    """ flatten a tree to a list
    """
    ret = []
    for k in values:
        v = values[k]
        if isinstance(v,dict):
            item = {}
            item['label'] = k
            item['control'] = 0 # is basically 
            item['collapse'] = False
            ret.append(item)
            ret.extend(_get_property_list(v))
            continue

        item = {}
        item['label'] = k
        item['control'] = v
        ret.append(item)

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
    client_id = FrameContext.client_id
    tag = tag if tag is not None else "__PROPS_LB__"

    props_lb = get_inventory_value(client_id, tag)
    if props_lb is None:
        return
    
    props_lb.items = _gui_properties_items(p)
    gui_represent(props_lb)


def _property_lb_item_template_one_line(item):
    
    gui_c = item['control']
    if gui_c == 0:
        gui_row("row-height: 1em;padding:5px,0,5px,0;")
        #gui_row("row-height: 1.2em;padding:13px;")
        collapsable =  "collapse" in item
        
        if not collapsable:
            gui_text(f"$text:{item['label']};justify: center;color:#02FF;", "background: #FFFC")
        else:
            if not item.get("collapse"):
                gui_text(f"$text:{item['label']};justify: center;color:#02FF;", "background: #FFFC")
            else:
                gui_text(f"$text:{item['label']};justify: center;color:#FFF;", "background: #0173")
    else:
        gui_row("row-height: 1.5em;padding:5px,0,5px,0;")
        #gui_row("row-height: 1.2em;padding:13px;")
        gui_text(f"$text:{item['label']};justify: right;","padding:0,0,1em,0;")
        gui_hole()
        gui_c = FrameContext.task.eval_code(gui_c, False)
        if gui_c is None:
            gui_text(f"Invalid code")
    

def _property_lb_item_template_two_line(item):
    gui_c = item['control']
    if gui_c == 0:
        gui_row("row-height: 1.2em;")
        gui_text(f"$text:{item['label']};justify: center;color:#02FF;", "background: #FFFC")
    else:
        gui_row("row-height: 1.2em;")
        gui_text(f"$text:{item['label']};justify: left;")
        gui_row("row-height: 2em;")

        gui_c = FrameContext.task.eval_code(gui_c, False)
        if gui_c is None:
            gui_text(f"Invalid code")
    
def gui_property_list_box_stacked(name=None, tag=None):
    page = FrameContext.page
    tag = tag if tag is not None else "__PROPS_LB__"
    name = name if name is not None else "Properties"

    props_lb = gui_list_box([],
                "row-height: 0.5em; background:#1572;", 
                item_template=_property_lb_item_template_two_line, title_template=name, collapsible=True)
    
    props_lb.title_section_style += "background:#1578;"
    set_inventory_value(page.client_id, tag, props_lb)    
    return props_lb

def gui_property_list_box(name=None, tag=None, temp = _property_lb_item_template_one_line):
    page = FrameContext.page
    tag = tag if tag is not None else "__PROPS_LB__"
    name = name if name is not None else "Properties"

    props_lb = gui_list_box([],
                "row-height: 0.5em; background:#1572;", 
                item_template=temp, title_template=name, collapsible=True)
    
    props_lb.title_section_style += "background:#1578;"
    set_inventory_value(page.client_id, tag, props_lb)    
    return props_lb
