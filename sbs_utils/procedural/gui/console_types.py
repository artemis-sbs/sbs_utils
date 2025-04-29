from ...agent import Agent
from ...helpers import FrameContext, DictionaryToObject

def gui_add_console_type(path, display_name, description, label):
    """adds a tab definition 

    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected
    """    
    consoles = Agent.SHARED.get_inventory_value("__CONSOLE_TYPES__", {})
    console = {"display_name": display_name, "label":label, "description": description}
    if path in consoles:
        dup = consoles.get(path)
        if console.label.priority > console.label.priority:
            pass
        if dup.label.priority > console.label.priority:
            return
        else: 
            print(f"Possible duplicate console same priority {path}")
    consoles[path] = console
    Agent.SHARED.set_inventory_value("__CONSOLE_TYPES__", consoles)

def gui_remove_console_type(path, display_name, label):
    """adds a tab definition 

    Args:
        path (str): Console path
        display_name (str): Display name
        label (label): Label to run when tab selected
    """    
    consoles = Agent.SHARED.get_inventory_value("__CONSOLE_TYPES__", {})
    if path not in consoles:
        return
    consoles.pop(path)
    Agent.SHARED.set_inventory_value("__CONSOLE_TYPES__", consoles)


def gui_get_console_types():
    """ Get the list of consoles defined by @console decorator labels

    """    
    return Agent.SHARED.get_inventory_value("__CONSOLE_TYPES__", {})

def gui_get_console_type(key):
    """ Get the list of consoles defined by @console decorator labels

    """    
    consoles = Agent.SHARED.get_inventory_value("__CONSOLE_TYPES__", {})
    console = consoles.get(key, None)
    if console is None:
        DictionaryToObject({"display_name": "No consoles found", "description": "The script did not define consoles", "path": "none", "label": None})
    else:
        console = DictionaryToObject(console)
        # Try using the label description if not supplied
    if console.description is None:
        console.description = console.label.desc

    return console


def gui_get_console_type_list():
    """ Get the list of consoles defined by @console decorator labels
        path is added as a value
    """    
    consoles = Agent.SHARED.get_inventory_value("__CONSOLE_TYPES__", {})
    task = FrameContext.task
    if len(consoles)==0:
        return [{"display_name": "No consoles found", "description": "The script did not define consoles", "path": "none", "label": None}]
    ret = []
    for k in consoles:
        console  = DictionaryToObject(consoles[k], path = k)
        if task and not console.label.test(task):
            continue
        
        if console.description is None:
            console.description = console.label.desc
        ret.append(console)
    ret.sort(key=lambda c: c.label.raw_weight)
    return ret
