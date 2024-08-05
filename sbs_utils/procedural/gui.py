from ..mast.mast import Scope, Button
from .query import to_id
from .inventory import get_inventory_value, set_inventory_value
from ..helpers import FrameContext, FakeEvent, DictionaryToObject
from ..pages.layout import layout
from ..mast.parsers import StyleDefinition
from ..futures import Trigger, AwaitBlockPromise
from ..gui import get_client_aspect_ratio
from .style import apply_control_styles
from ..mast.pollresults import PollResults
from ..pages.widgets.layout_listbox import LayoutListbox
from ..pages.layout.text_area import TextArea
from .execution import task_all, AWAIT
from ..agent import Agent
import re
import sbs
from . import screen_shot 

gui_screenshot = screen_shot.gui_screenshot



def text_sanitize(text):
    text = text.replace(",", "_")
    #text = text.replace(":", "_")
    return text


def gui_add_console_tab(id_or_obj, console, tab_name, label):
    """adds a tab definition 

    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected
    """    
    ship_id = to_id(id_or_obj)
    console = console.lower()
    tabs = get_inventory_value(ship_id, "console_tabs", {})
    console_tabs = tabs.get(console, {})
    console_tabs[tab_name] = label
    tabs[console] = console_tabs
    #print(f"set {ship_id} {console} {tabs}")
    # set just in case this is the first time
    set_inventory_value(ship_id, "console_tabs", tabs)

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
        print(f"Possible duplicate console {path}")
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
    if len(consoles)==0:
        return [{"display_name": "No consoles found", "description": "The script did not define consoles", "path": "none", "label": None}]
    ret = []
    for k in consoles:
        console  = DictionaryToObject(consoles[k], path = k)
        if console.description is None:
            console.description = console.label.desc
        ret.append(console)
    return ret



def gui_remove_console_tab(id_or_obj, console, tab_name):
    """removes a tab definition 

    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
    """        
    ship_id = to_id(id_or_obj)
    tabs = get_inventory_value(ship_id, "console_tabs", None)
    if tabs is None: return
    console_tabs = tabs.get(console, None)
    if console_tabs is None: return
    console_tabs.pop(tab_name)
    if len(console_tabs) == 0:
        tabs.pop(console)
    #set_inventory_value(ship_id, "console_tabs", tabs)


def gui_face(face, style=None):
    """queue a gui face element

    Args:
        face (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = layout.Face(tag,face)
    apply_control_styles(".face", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_icon(props, style=None):
    """queue a gui icon element

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """        
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = layout.Icon(tag,props)
    apply_control_styles(".icon", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_icon_button(props, style=None):
    """queue a gui icon element

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """        
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = layout.IconButton(tag,props)
    apply_control_styles(".icon_button", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_image_stretch(props, style=None):
    """queue a gui image element that stretches to fit

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """            
    return gui_image(props, style=style, fit=0)

def gui_image_absolute(props, style=None):
    """queue a gui image element that draw the absolute pixels dimensions

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=1)

def gui_image_keep_aspect_ratio(props, style=None):
    """queue a gui image element that draw keeping the same aspect ratio, left top justified

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=2)

def gui_image_keep_aspect_ratio_center(props, style=None):
    """queue a gui image element that keeps the aspect ratio and centers when there is extra

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=3)

def gui_image(props, style=None, fit=0):
    """queue a gui image element that draw based on the fit argument. Default is stretch

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
        fit (int): The type of fill, 

    Returns:
        layout object: The Layout object created
    """                    
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    if "image:" not in props:
        props = f"image:{props};"

    if "color:" not in props:
        props+="color:white;"
    
    tag = page.get_tag()
    layout_item = layout.Image(tag,props, fit)
    apply_control_styles(".image", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_ship(props, style=None):
    """renders a 3d image of the ship 

    Args:
        props (str): The ship key
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
        
    
    # Log warning
    tag = page.get_tag()
    layout_item = layout.Ship(tag,props)
    apply_control_styles(".ship", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_row(style=None):
    """queue a gui row

    Args:
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    page = FrameContext.page
    task = FrameContext.task
        
    if page is None:
        return None
    
    page.add_row()
    layout_item = page.get_pending_row()
    apply_control_styles(".row", style, layout_item, task)
    return layout_item

def gui_blank(count=1, style=None):
    """adds an empty column to the current gui ow

    Args:
        style (_type_, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    for _ in range(count):
        layout_item = layout.Blank()
        apply_control_styles(".blank", style, layout_item, task)
        # Last in case tag changed in style
        page.add_content(layout_item, None)
    return layout_item

def gui_hole(count=1, style=None):
    """adds an empty column that is used by the next item

    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """        
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    layout_item = None
    for _ in range(count):
        # Log warning
        layout_item = layout.Hole()
        apply_control_styles(".hole", style, layout_item, task)
        # Last in case tag changed in style
        page.add_content(layout_item, None)
    return layout_item

class MessageHandler:
    def __init__(self, layout_item, task, label, jump=False) -> None:
        self.layout_item = layout_item
        self.label = label
        self.task = task
        self.jump = jump

    def on_message(self, event):
        if event.sub_tag == self.layout_item.tag:
            restore = FrameContext.task
            FrameContext.task = self.task
            self.task.set_variable("__ITEM__", self.layout_item)
            if self.jump:
                self.task.jump(self.label)
            else:
                self.label()
                
            FrameContext.task = restore

def gui_button(props, style=None, data=None, on_message=None, jump=None ):
    """Add a gui button

    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
        data (object): The data to pass to the button's label
        on_message (label): A label to handle a button press
        jump (label): A label to jump to a button press, ending the Await gui

    Returns:
        layout object: The Layout object created
    """        

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    props = task.compile_and_format_string(props)
    layout_item = layout.Button(tag, props)
    layout_item.data = data
    apply_control_styles(".button", style, layout_item, task)
    # Last in case tag changed in style
    runtime_item = None
    if on_message is not None:
        runtime_item = MessageHandler(layout_item, task, on_message)
    elif jump is not None:
        runtime_item = MessageHandler(layout_item, task, jump, True)

    page.add_content(layout_item, runtime_item)
    return layout_item


def gui_drop_down(props, style=None, var=None, data=None):
    """ Draw a gui drop down list 

    Args:
        props (str): 
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    props = task.compile_and_format_string(props)
    layout_item = layout.Dropdown(tag, props)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()
    apply_control_styles(".dropdown", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_checkbox(msg, style=None, var=None, data=None):
    """ Draw a checkbox 

    Args:
        props (str): 
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the value to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)

    layout_item = layout.Checkbox(tag, msg)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()
        layout_item.update_variable()

    apply_control_styles(".checkbox", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_radio(msg, style=None, var=None, data=None, vertical=False):
    """ Draw a radio button list 

    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        vertical (bool): Layout vertical if True, default False means horizontal

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)
    val = ""
    if var is not None:
        val = task.get_variable(var, "")

    layout_item = layout.RadioButtonGroup(tag, msg, val, vertical)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    
    apply_control_styles(".radio", style, layout_item.group_layout, task)
    apply_control_styles(".radio", style, layout_item, task)
    layout_item.group_layout.tag = layout_item.tag+":group"
    # Last in case tag changed in style
    page.add_content(layout_item, None)

    return layout_item

def gui_vradio(msg, style=None, var=None, data=None):
    """ Draw a vertical radio button list 

    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.

    Returns:
        layout object: The Layout object created
    """        
    return gui_radio(msg, style, var, data, True)

def gui_slider(msg, style=None, var=None, data=None, is_int=False):
    """ Draw a slider control

    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        is_int (bool): Use only integers values

    Returns:
        layout object: The Layout object created
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)
    val = 0
    if var is not None:
        val = task.get_variable(var, 0)

    layout_item = layout.Slider(tag, val, msg, is_int)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    if is_int:
        apply_control_styles(".intslider", style, layout_item, task)
    else:
        apply_control_styles(".slider", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_int_slider(msg, style=None, var=None, data=None):
    """ Draw an integer slider control

    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created
    """    
    return gui_slider(msg, style, var,  data, True)


def gui_input(props, style=None, var=None, data=None):
    """ Draw a text type in

    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    if props is not None:
        props = task.compile_and_format_string(props)
    else:
        props = ""

    val = ""
    if var is not None:
        val = task.get_variable(var, "")

    if "text:" not in props:
        props = f"text:{val};{props}"

    layout_item = layout.TextInput(tag, props)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    apply_control_styles(".input", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_section(style=None):
    """ Create a new gui section that uses the area specified in the style

    Args:
        style (style, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    
    page.add_section()
    layout_item = page.get_pending_layout() 
    apply_control_styles(".section", style, layout_item, task)
    return layout_item



def gui_list_box(items, style, 
                 item_template=None, title_template=None, 
                 section_style=None, title_section_style=None,
                 select=False, multi=False, carousel=False):
    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    # The gui_content sets the values
    layout_item = LayoutListbox(0, 0, tag, items,
                 item_template, title_template, 
                 section_style, title_section_style,
                 select,multi, carousel)
    # #layout_item.data = data
    # if var is not None:
    #     layout_item.var_name = var
    #     layout_item.var_scope_id = task.get_id()
    #     layout_item.update_variable()

    apply_control_styles(".listbox", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

    


class PageSubSection:
    def __init__(self, style) -> None:
        page = FrameContext.page
        self.sub_section = None
        if page is None:
            return None
        self.page = page
        self.style = style
        self.add = True

    def __enter__(self):
        # Allow reentering
        self.sub_section = self.page.push_sub_section(self.style, self.sub_section, False)
        

    # Pythons expects 4 args, mast only 1
    # Python's are exception related
    def __exit__(self, ex=None, value=None, tb=None):
        self.page.pop_sub_section(self.add, False)
        self.add = False


def gui_sub_section(style=None):
    """ Create a new gui section that uses the area specified in the style

    Args:
        style (style, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    return PageSubSection(style)


class PageRegion:
    def __init__(self, style) -> None:
        page = FrameContext.page
        if page is None:
            return None
        self.page = page
        self.style = style
        self.sub_section = None
        # Create  top level layout        
        self.sub_section  = gui_section(style)
        

    def __enter__(self):
        # Allow reentering
        self.sub_section = self.page.push_sub_section(self.style, self.sub_section, self.sub_section.region)
        self.sub_section.region_type = layout.RegionType.REGION_ABSOLUTE
        

    # Pythons expects 4 args, mast only 1
    # Python's are exception related
    def __exit__(self, ex=None, value=None, tb=None):
        self.page.pop_sub_section(False, self.sub_section.region)
        if self.sub_section.region:
            gui_represent(self.sub_section)

    def show(self, _show):
        self.sub_section.show(_show)

    @property
    def is_hidden(self):
        return self.sub_section.is_hidden

    def represent(self, e):
        self.sub_section.represent(e)




def gui_region(style=None):
    """ Create a new gui section that uses the area specified in the style

    Args:
        style (style, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """    
    return PageRegion(style)


def gui_rebuild(region):
    """ prepares a section/region to be build a new layout

    Args:
        region (layout_item): a layout/Layout item

    Returns:
        layout object: The Layout object created
    """
    region.sub_section.rebuild()
    return region


def gui_style_def(style):
    return StyleDefinition.parse(style)

def gui_set_style_def(name, style):
    style_def = StyleDefinition.parse(style)
    StyleDefinition.styles[name] = style_def
    return style_def


def gui_widget_list(console, widgets):
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    page = FrameContext.page
    if page is None:
        return None
    page.set_widget_list(console, widgets)

order_first_widgets = ["2dview","3dview", "comms_2d_view", "ship_internal_view", "weapon_2d_view", "science_2d_view"]
def gui_update_widget_list(add_widgets=None, remove_widgets= None):
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    page = FrameContext.page
    if page is None:
        return None
    
    if add_widgets is None and remove_widgets is None:
        return
    if add_widgets is None:
        add_widgets = ""
    if remove_widgets is None:
        remove_widgets = ""

    widgets = set(page.widgets.split("^"))
    #print(f"GUI {page.widgets} {add_widgets} {remove_widgets}")
    add_widgets = set(add_widgets.split("^"))
    remove_widgets = set(remove_widgets.split("^"))
    widgets = (widgets | add_widgets) - remove_widgets
    new_widgets = ""
    delim = ""
    for widget in widgets:
        if widget in order_first_widgets:
            new_widgets = widget + delim + new_widgets
            delim = "^"
        else:
            new_widgets = new_widgets + delim + widget
            delim = "^"
    print(f"GUI {new_widgets} {widgets} {add_widgets} {remove_widgets}")
    sbs.send_client_widget_list(page.client_id, page.console, new_widgets)



def gui_update_widgets(add_widgets, remove_widgets):
    """ Set the engine widget list. i.e. controls engine controls

    Args:
        console (str): The console type name
        widgets (str): The list of widgets

    """    
    page = FrameContext.page
    if page is None:
        return None

    widgets = set(page.pending_widgets.split("^"))
    add_widgets = set(add_widgets.split("^"))
    remove_widgets = set(remove_widgets.split("^"))
    widgets = (widgets | add_widgets) - remove_widgets
    new_widgets = ""
    delim = ""
    for widget in widgets:
        if widget in order_first_widgets:
            new_widgets = widget + delim + new_widgets
            delim = "^"
        else:
            new_widgets = new_widgets + delim + widget
            delim = "^"
    
    page.pending_widgets = new_widgets



def gui_widget_list_clear():
    """clear the widet list on the client
    """    
    gui_widget_list("","")

def gui_activate_console(console):
    """set the console name for the client

    Args:
        console (str): The console name

    """    
    page = FrameContext.page
    if page is None:
        return None
    page.activate_console(console)
        
def gui_layout_widget(widget):
    """Places a specific console widget in the a layout section. Placing it at a specific location

    Args:
        widget (str): The gui widget

    Returns:
        layout element: The layout element
    """    
    page = FrameContext.page
    if page is None:
        return None
    
    page.add_console_widget(widget)
    control = layout.ConsoleWidget(widget)
    page.add_content(control, None)
    return control
    

def gui_console(console, is_jump=False):
    """Activates a console using the default set of widgets

    Args:
        console (str): The console name

    """    
    page = FrameContext.page
    if page is None:
        return None
    widgets = ""
    match console.lower():
        case "helm":
            console =  "normal_helm"
            if is_jump:
                widgets = "2dview^helm_movement^helm_jump^quick_jump^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
            else:
                widgets = "2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
        case "weapons":
            console =  "normal_weap"
            widgets = "weapon_2d_view^weapon_control^weap_beam_freq^weap_beam_speed^weap_torp_conversion^ship_data^shield_control^text_waterfall^main_screen_control"
        case "science":
            console =  "normal_sci"
            widgets = "science_2d_view^ship_data^text_waterfall^science_data^science_sorted_list"
        case "engineering":
            console =  "normal_engi"
            widgets = "ship_internal_view^grid_object_list^grid_face^grid_control^text_waterfall^eng_heat_controls^eng_power_controls^ship_data"
        case "comms":
            console =  "normal_comm"
            widgets = "2dview^text_waterfall^comms_waterfall^comms_control^comms_face^comms_sorted_list^ship_data^red_alert"
        case "cinematic":
            console =  "cinematic"
            widgets = "3dview"
        case "mainscreen":
            console =  "normal_main"
            view = page.gui_task.get_variable("MAIN_SCREEN_VIEW", "3d_view")
            if view == "lrs":
                #console =  "normal_main_lrs"
                widgets = "2dview^ship_data^text_waterfall"
            elif view == "tactical":
                #console =  "normal_main_tact"
                widgets = "2dview^ship_data^text_waterfall"
            elif view == "data":
                #console =  "normal_main_data"
                widgets = "ship_internal_view^ship_data^text_waterfall"
            else:
                widgets = "3dview^ship_data^text_waterfall"
        case "cockpit":
            widgets = "3dview^2dview^helm_free_3d^text_waterfall^fighter_control^ship_internal_view^ship_data^grid_face^grid_control"
        

    page.set_widget_list(console, widgets)


def gui_content(content, style=None, var=None):
    """Place a python code widget e.g. list box using the layout system

    Args:
        content (widget): A gui widget code in python
        style (str, optional): Style. Defaults to None.
        var (str, optional): The variable to set the widget's value to. Defaults to None.

    Returns:
        layout object: The layout object
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None

    tag = page.get_tag()
    # gui control ShipPicker(0,0,"mast", "Your Ship")
    layout_item = layout.GuiControl(tag, content)
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()
        v = task.get_variable(var)
        layout_item.value =v

    apply_control_styles(None, style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_text(props, style=None):
    """ Add a gui text object

    valid properties 
        text
        color
        font


    props (str): property string 
    style (style, optional): The style
    """
    page = FrameContext.page
    task = FrameContext.task

    if page is None:
        return
    if style is None: 
        style = ""
    layout_item = layout.Text(page.get_tag(), props)
    apply_control_styles(".text", style, layout_item, task)

    page.add_content(layout_item, None)
    return layout_item


def gui_text_area(props, style=None):
    """ Add a gui text object

    valid properties 
        text
        color
        font


    props (str): property string 
    style (style, optional): The style
    """
    page = FrameContext.page
    task = FrameContext.task

    if page is None:
        return
    if style is None: 
        style = ""
    layout_item = TextArea(page.get_tag(), text_sanitize(props))
    apply_control_styles(".textarea", style, layout_item, task)

    page.add_content(layout_item, None)
    return layout_item

def gui_update(tag, props, shared=False, test=None):
    """Update the properties of a current gui element

    Args:
        tag (str): 
        props (str): The new properties to use
        shared (bool, optional): Update all gui screen if true. Defaults to False.
        test (dict, optional): Check the variable (key) update if any value is different than the test. Defaults to None.
    """    
    page = FrameContext.page
    task = FrameContext.task

    tag = task.compile_and_format_string(tag)
    props = task.compile_and_format_string(props)
    if shared:
        task.main.mast.update_shared_props_by_tag(tag, props, test)
    else:
        page.update_props_by_tag(tag, props, test)

def gui_update_shared(tag, props, test=None):
    gui_update(tag, props, True, test)



def gui_represent(layout_item):
    """redraw an item

    ??? Note
        For sections it will recalculate the layout and redraw all items

    Args:
        layout_item (layout_item): 
    """    
    page = FrameContext.page
    if page is None:
        return
    event = FakeEvent(page.client_id)
    #print(f"Page {event.client_id}")
    #sbs.target_gui_sub_region(page.client_id, "FULL")
    layout_item.represent(event)
    #sbs.send_gui_complete(event.client_id)

def gui_show(layout_item):
    """gui show. If the item is hidden it will make it visible again

    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout. 
        so you may also need to pair this with a gui_represent of a section

    Args:
        layout_item (layout_item): 
    """    
    if layout_item is None:
        return
    if not layout_item.is_hidden:
        return
    layout_item.show(True)
    page = FrameContext.page
    if page is None:
        return
    event = FakeEvent(page.client_id)
    layout_item.represent(event)

def gui_hide(layout_item):
    """If the item is visible it will make it hidden

    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout. 
        so you may also need to pair this with a gui_represent of a section

    Args:
        layout_item (layout_item): 
    """    
    if layout_item is None:
        return
    if layout_item.is_hidden:
        return
    layout_item.show(False)
    page = FrameContext.page
    if page is None:
        return
    event = FakeEvent(page.client_id)
    layout_item.represent(event)




def gui_refresh(label):
    """refresh any gui running the specified label

    Args:
        label (label): A mast label
    """    
    task = FrameContext.task
    if label is None:
        task.main.refresh(label)
    else:
        task.main.mast.refresh_schedulers(task.main, label)


def gui_history_store(back_text, back_label=None):
    """store the current 

    Args:
        label (label): A mast label
    """    
    page = FrameContext.page
    if page is None:
        return
    if back_label is None:
        back_label = page.gui_task.active_label
    
def gui_history_back():
    """returns the back label pair this with a jump

    Returns:
        label (label, None): A mast label
    """    
    page = FrameContext.page
    if page is None:
        return
    


def _gui_reroute_main(label, server):
    task = FrameContext.task
    #
    # RerouteGui in main defers to the end of main
    #
    if task.active_label!="main":
        return False
    
    client_id = task.get_variable("client_id")
    if client_id is None:
        # Run on Non-gui task?
        return True
    if server and client_id!= 0:
        # Run on client skips setting server
        return True
    if not server and client_id== 0:
        return True
    #
    # A jump in main set the label's next
    # label so it runs at the end of main
    #
    main_label_obj = task.main.mast.labels.get("main")
    jump_label_obj = task.main.mast.labels.get(label, label)
    #
    # TODO: This should change something task specific
    #
    main_label_obj.next = jump_label_obj
    return True

from ..gui import Gui
def gui_reroute_client(client_id, label, data=None):
    client = Gui.clients.get(client_id, None)
    if client is None:
        return
    if len(client.page_stack) == 0:
        return
    
    page = client.page_stack[-1]
    if page is None: 
        return
    
    if page is not None and page.gui_task:
        if data:
            for k in data:
                page.gui_task.set_variable(k, data[k])
        page.gui_task.jump(label)
        page.gui_task.tick_in_context()

def gui_reroute_server(label, data=None):
    """reroute server gui to run the specified label

    Args:
        label (label): Label to jump to
    """    
    if _gui_reroute_main(label, True):
        return
    gui_reroute_client(0,label, data)


def gui_reroute_clients(label, data=None, exclude=None):
    """reroute client guis to run the specified label

    Args:
        label (label): Label to jump to
        exclude (set, optional): set client_id values to exclude. Defaults to None.
    """    
    if _gui_reroute_main(label, False):
        return
    if exclude is None:
        exclude = set()
    #
    """Walk all the clients (not server) and send them to a new flow"""
    for id, client in Gui.clients.items():
        if id != 0 and client is not None and id not in exclude:
            gui_reroute_client(id, label, data)


    
class MessageTrigger(Trigger):
    def __init__(self, task, layout_item, label=None):
        # This will remap to include this as the message handler
        task.main.page.add_tag(layout_item, self)
        self.task = task
        self.layout_item = layout_item
        # Needs to be set by Mast
        # Pure mast this is active Label
        # Python ith should be a callable
        self.label = label
        if label is None:
            self.label = task.active_label 
        # 0 for python the node loc of the on in Mast
        self.loc = 0


    def on_message(self, event):
        if event.sub_tag == self.layout_item.tag:
            # print(f"ON MESSAGE: {event.sub_tag} {self.label} {self.loc} {self.task.is_sub_task}")
            self.task.set_value_keep_scope("__ITEM__", self.layout_item)
            data = self.layout_item.data
            self.task.push_inline_block(self.label, self.loc, data)
            self.task.tick_in_context()

def gui_message(layout_item):
    """Trigger to watch when the specified layout element has a message

    Args:
        layout_item (layout object): The object to watch

    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached
    """    
    task = FrameContext.task
    return MessageTrigger(task, layout_item)

class ClickableTrigger(Trigger):
    def __init__(self, task, name):
        self.name = name
        self.task = task
        # Needs to be set by Mast
        # Pure mast this is active Label
        # Python ith should be a callable
        self.label = None 
        # 0 for python the node loc of the on in Mast
        self.loc = 0
        task.main.page.add_on_click(self)

    def click(self, click_tag):
        if self.name is not None:     
            if click_tag != self.name:
                    return False
        #print(click_tag)
        self.task.set_value("__CLICKED__", click_tag, Scope.TEMP)
        self.task.push_inline_block(self.label, self.loc)
        self.task.tick_in_context()
        return True

def gui_click(name_or_layout_item=None):
    """Trigger to watch when the specified layout element is clicked

    Args:
        layout_item (layout object): The object to watch

    Returns:
        trigger: A trigger watches something and runs something when the element is clicked
    """    
    task = FrameContext.task
    name = name_or_layout_item
    if name is not None:
        if not isinstance(name_or_layout_item, str):
            name = name_or_layout_item.click_tag
    return ClickableTrigger(task, name)


class ChangeTrigger(Trigger):
    rule = re.compile(r"change[ \t]+(?P<val>.+)")
    def __init__(self, task, node, label=None):
        self.task = task
        if isinstance(node, str):
            val = node
            node = None
        else:
            match_obj = ChangeTrigger.rule.match(node.inline)
            val = None
            if match_obj:
                data = match_obj.groupdict()
                val = data['val']

        if val is None:
            self.value = False
            self.code = compile("True", "<string>", "eval")
        else:
            self.code = compile(val, "<string>", "eval")
            self.value = self.task.eval_code(self.code) 

        # What to jump to one past the inline node
        self.node = node
        
        if label is None:
            self.label = task.active_label
        else:
            self.label = label

    def test(self):
        prev = self.value
        self.value = self.task.eval_code(self.code) 
        return prev!=self.value
    
    def run(self):
        loc = 0
        if self.node:
            loc = self.node.loc + 1
        self.task.push_inline_block(self.label, loc)
        self.task.tick_in_context()

def gui_change(code, label):
    """Trigger to watch when the specified value changes
    This is the python version of the mast on change construct

    Args:
        code (str): Code to evaluate
        label (label): The label to jump to run when the value changes

    Returns:
        trigger: A trigger watches something and runs something when the element is clicked
    """    

    task = FrameContext.task
    page = FrameContext.page
    if task is None:
        return
    if page is None:
        return

    handler = ChangeTrigger(task, code, label)
    task.queue_on_change(handler)



class ChoiceButtonRuntimeNode:
    def __init__(self, promise, button, tag):
        self.promise = promise
        self.button = button
        self.tag = tag
                
    def on_message(self, event):
        #
        # The 'right' page already filtered 
        # event to know it is for this client
        #
        if event.sub_tag == self.tag:
            self.promise.press_button(self.button)

import re
class ButtonPromise(AwaitBlockPromise):
    focus_rule = re.compile(r'focus')
    disconnect_rule = re.compile(r'disconnect')
    fail_rule = re.compile(r'fail')

    navigation_map = {}

    def __init__(self, path, task, timeout=None) -> None:
        super().__init__(timeout)

        self.path = path if path is not None else ""
        self.path_root = "gui"
        self.buttons = []
        self.nav_buttons = []
        self.nav_button_map = {}
        self.inlines = []
        self.button = None
        self.var = None
        self.task = task
        self.disconnect_label = None
        self.on_change = None
        self.focus_label = None
        self.run_focus = False
        self.running_button = None
        self.sub_task = None
        #print("INit ")
        
    def initial_poll(self):
        if self._initial_poll:
            return
        # Will Build buttons
        #print("INit pool")
        self.expand_inlines()
        #self.show_buttons()
        super().initial_poll()

    def set_path(self, path):
        if path is None:
            path = self.path_root
        if path.startswith("//"):
            path = path[2:]
        if path.startswith(self.path_root):
            # typically this is overridden
            self.path = path
            self.show_buttons()
        else:

            print(f"possible wrong path SET {self.path_root} path= {path}")


    def check_for_button_done(self):
        #
        # THIS sets the promise to finish 
        # after you let the button process
        # science will override this to 
        # keep going until all scanned
        #
        # if self.running_button:
        #    self.set_result(self.running_button)
        pass

    def pressed_set_values(self):
        pass

    def pressed_test(self):
        return True


    def poll(self):
        super().poll()
        if self.sub_task is not None:
            self.sub_task.poll()
            if self.sub_task.done:
                self.show_buttons()
                self.sub_task= None
            else:
                return PollResults.OK_RUN_AGAIN

        if not self.pressed_test():
            # If the test fails, this is no longer needed
            self.task.end()
            
            
            

        self.check_for_button_done()

        task = self.task
        if self.task is None:
            self.task = self.page.gui_task
            # First run could have no gui_task
            if self.task is None:
                self.task = FrameContext.task

        if self.button is not None:
            if self.var:
                task.set_value_keep_scope(self.var, self.button.index)
             
            # self.button.node.visit(self.button.client_id)
            # button = self.buttons[self.button.index]
            button = self.button
            # if button.for_name:
            #     task.set_value(button.for_name, button.data, Scope.TEMP)

            self.pressed_set_values()
            task.set_value("BUTTON_PROMISE", self, Scope.TEMP)

            #
            # If the button doesn't jump, make sure the 
            # promise has a chance to finish
            #
            self.running_button = self.button
            self.button = None
            #
            # Code to run the button is now with the button 
            # so the code is closer to the data
            #
            if self.running_button.path is not None:
                self.set_path(self.running_button.path)
                print(f"PATH {self.running_button.path}")
                self.running_button = None
                return PollResults.OK_JUMP
            else:   
                sub_task = self.running_button.run(self.task, self)
                if sub_task is not None:
                    self.sub_task = sub_task
            return PollResults.OK_JUMP

        if self.disconnect_label is not None:
            page = task.main.page
            if page is not None and page.disconnected:
                # Await use a jump back to the await, so jump here is OK
                task.jump(task.active_label,self.disconnect_label.loc+1)
                #return PollResults.OK_JUMP
                self.set_result(True)
                return PollResults.OK_JUMP

        if self.on_change:
            for change in self.on_change:
                if change.test():
                    # Await use a jump back to the await, so jump here is OK
                    self.task.jump(change.label,change.node.loc+1)
                    return PollResults.OK_JUMP
                    
        if self.focus_label and self.run_focus:
            self.run_focus = False
            # Await use a jump back to the await, so jump here is OK
            self.task.jump(self.task.active_label,self.focus_label.loc+1)
            return PollResults.OK_JUMP

        return PollResults.OK_RUN_AGAIN

    def press_button(self, button):
        self.button = button
        self.poll()

    def expand_button(self, button):
        buttons = []
        # if button.for_code is not None:
        #     iter_value = self.task.eval_code(button.for_code)
        #     for data in iter_value:
        #         self.task.set_value(button.for_name, data, Scope.TEMP)
        #         clone = button.clone()
        #         clone.data = data
        #         clone.message = self.task.format_string(clone.message)
        #         if clone.color:
        #             clone.color = self.task.format_string(clone.color)
        #         buttons.append(clone)

        return buttons

    def get_expanded_buttons(self):
        buttons = []
        #
        # Note: Always use clones in layouts
        # So we can have access to the layout item
        #
        # Expand all the 'for' buttons
        for button in self.buttons:
            if button.__class__.__name__ != "Button":
                buttons.append(button)
            else:
                buttons.append(button.clone())
            # else:
            #     buttons.extend(self.expand_button(button))
        self.build_navigation_buttons()
        buttons.extend(self.nav_buttons)
        return buttons
    
    def expand_inline(self, inline):
        if inline.inline is  None:
            return
        #print(f"__{inline.inline}__")
        # Handle =disconnect:
        if ButtonPromise.disconnect_rule.match(inline.inline):
            self.disconnect_label = inline
        # Handle focus
        if ButtonPromise.focus_rule.match(inline.inline):
            self.focus_label = inline
        # Handle Fail () maybe only for behaviors?
        if ButtonPromise.fail_rule.match(inline.inline):
            self.fail_label = inline
        # Handle change
        if inline.inline.startswith("change"):
            if self.on_change is None:
                self.on_change = []
            self.on_change.append(ChangeTrigger(self.task, inline))
        # Handle timeout
        #if ButtonPromise.focus_rule.match(inline.inline):
        #    self.focus_label = inline

    def expand_inlines(self):
        # Expand all the 'for' buttons
        for inline in self.inlines:
            self.expand_inline(inline)

    def add_nav_button(self, button):
        dup = self.nav_button_map.get(button.message)
        if dup is not None and not dup.is_block:
            if dup.path is not None and dup.path == button.path:
                return
            if dup.label is not None and dup.label == button.label:
                return

        self.nav_buttons.append(button)
        self.nav_button_map[button.message] = button


    def build_navigation_buttons(self):
        self.nav_buttons = []
        self.nav_button_map = {}
        #print(f"gui Build Nav Buttons {self.path}")
        path_labels = ButtonPromise.navigation_map.get(self.path)
        if path_labels is None:
            return
        
        ButtonPromise.navigating_promise = self
        #
        # Make sure to use the right task
        #
        t = FrameContext.task 
        FrameContext.task = self.task
        p = task_all(*path_labels, sub_tasks=True)
        FrameContext.task = t

        p.poll()
        #
        # This could get into a lock
        # but the expectation is this runs in one pass
        #
        count = 0
        while not p.done():
            p.poll()
            if count > 100000:
                print(f"Comms path {self.path} caused hang")
                break
            count += 1
        ButtonPromise.navigating_promise = None
        
    

        
        
    
    

class GuiPromise(ButtonPromise):
    button_height_px = 40

    def __init__(self, page, timeout=None) -> None:
        path = page.get_path()
        super().__init__(path, page.gui_task, timeout)

        self.page = page
        self.button_layout = None

    def initial_poll(self):
        if self._initial_poll:
            return
        
        super().initial_poll()
        self.show_buttons()
        self.page.set_button_layout(self.button_layout, self)

    #
    # This 
    #
    def show_buttons(self):
        if self.task is None:
            self.task = self.page.gui_task
            # First run could have no gui_task
            if self.task is None:
                self.task = FrameContext.task
        task = self.task
        aspect_ratio = get_client_aspect_ratio(task.main.page.client_id)

        #
        # Create button Row
        #
        top = ((aspect_ratio.y - GuiPromise.button_height_px)/aspect_ratio.y)*100

        button_layout = layout.Layout(None, None, 0,top,100,100)
        button_layout.tag = task.main.page.get_tag()

        active = 0
        index = 0
        layout_row: layout.Row
        layout_row = layout.Row()
        layout_row.tag = task.main.page.get_tag()

        buttons = self.get_expanded_buttons()
        
        if len(buttons) == 0:
            return
        
        
        for button in buttons:
            match button.__class__.__name__:
                case "Button":
                    value = True
                    #button.end_await_node = node.end_await_node
                    if button.code is not None:
                        value = task.eval_code(button.code)
                    if value and button.should_present(0):#task.main.client_id):
                        runtime_node = ChoiceButtonRuntimeNode(self, button, task.main.page.get_tag())
                        #runtime_node.enter(mast, task, button)
                        msg = task.format_string(button.message)
                        layout_button = layout.Button(runtime_node.tag, msg)
                        button.layout_item = layout_button
                        layout_row.add(layout_button)

                        apply_control_styles(".choice", None, layout_button, task)
                        
                        # After style could change tag
                        task.main.page.add_tag(layout_button, runtime_node)
                        active += 1
                case "Separator":
                    # Handle face expression
                    layout_row.add(layout.Blank())
            index+=1
        
        if active>0:
            button_layout.add(layout_row)
            self.button_layout = button_layout
            #task.main.page.set_button_layout(button_layout)
        else:
            self.button_layout = None
            #task.main.page.set_button_layout(None)

        self.active_buttons = active
        self.buttons = buttons
        self.button = None



def gui(buttons=None, timeout=None):
    """present the gui that has been queued up

    Args:
        buttons (dict, optional): _description_. Defaults to None.
        timeout (promise, optional): A promise that ends the gui. Typically a timeout. Defaults to None.

    Returns:
        Promise: The promise for the gui, promise is done when a button is selected
    """    
    page = FrameContext.page
    #sbs.send_gui_sub_region(page.client_id, "FULL", "", 0, 0, 100, 100)
    #sbs.target_gui_sub_region(page.client_id, "FULL")
    ret = GuiPromise(page, timeout)
    if buttons is not None:
        for k in buttons:
            ret .buttons.append(Button(k, label=buttons[k],loc=0))
        
    return ret
    
def gui_history_jump(to_label, back_name=None, back_label=None, back_data=None):
    """Jump to a new gui label, but remember how to return to the current state

    Args:
        to_label (label): Where to jump to
        back_name (str): A name to use if displayed
        back_label (label, optional): The label to return to defaults to the label active when called
        back_data (dict, optional): A set of value to set when returning back

    ??? Note:
        If there is forward history it will be cleared

    Returns:
        results (PollResults): PollResults of the jump
    """    
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    
    if back_label is None:
        back_label = task.active_label

    if back_name is  None:
        back_name = "BACK"

    history = task.get_variable("GUI_HISTORY")
    if history is None:
        history = []

    history_pos = task.get_variable("GUI_HISTORY_POS", 0)
    # Clear forward
    history = history[:history_pos]
    history.append( (back_name, back_label, back_data))
    task.set_variable("GUI_HISTORY_POS", len(history)-1)
    task.set_variable("GUI_HISTORY", history)


    return task.jump(to_label)

def gui_history_back():
    """Jump back in history

    """    
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    
    history = task.get_variable("GUI_HISTORY")
    if history is None:
        return

    history_pos = task.get_variable("GUI_HISTORY_POS", 0)
    # Clear forward
    history = history[history_pos]
    history_pos = max(0, history_pos-1)

    back_label = history[1]
    back_data = history[2]
    if back_data is not None:
        for k in back_data:
            task.set_value_keep_scope(k, back_data[k])
    
    task.set_variable("GUI_HISTORY_POS", history_pos)

    return task.jump(back_label)


def gui_history_forward():
    """Jump forward in history
    """    
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    
    history = task.get_variable("GUI_HISTORY")
    if history is None:
        return

    history_pos = task.get_variable("GUI_HISTORY_POS", 0)
    
    history_pos = (history_pos+1) % len(history)
    history = history[history_pos]
    
    back_label = history[1]
    back_data = history[2]

    if back_data is not None:
        for k in back_data:
            task.set_value_keep_scope(k, back_data[k])
    
    task.set_variable("GUI_HISTORY_POS", history_pos)

    return task.jump(back_label)

def gui_history_clear():
    """Clears the history for the given page
    """
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    task.set_variable("GUI_HISTORY", None)
    task.set_variable("GUI_HISTORY_POS", None)

def gui_cinematic_auto(client_id):
    """Will automatically track the consoles assigned ship

    ??? Note:
        The tracked ship needs to have excitement values 
        player ships automatically have that set    
    
    Args:
        client_id (id): the console's client ID
    """
    no_offset = sbs.vec3()
    sbs.set_main_view_modes(client_id, "3dview", "front", "cinematic")
    sbs.cinematic_control(client_id, 0, 0, no_offset, 0, no_offset)

def gui_cinematic_full_control(client_id, camera_id, camera_offset, tracked_id, tracked_offset):
    if camera_offset is not None:
        _camera_offset = sbs.vec3()
        _camera_offset.x = camera_offset.x
        _camera_offset.y = camera_offset.y
        _camera_offset.z = camera_offset.z
        camera_offset = _camera_offset
    #else:
    #     camera_offset = sbs.vec3()
    if tracked_offset is not None:
        _offset = sbs.vec3()
        _offset.x = tracked_offset.x
        _offset.y = tracked_offset.y
        _offset.z = tracked_offset.z
        tracked_offset = _offset
    # else:
    #     tracked_offset = sbs.vec3()

    sbs.set_main_view_modes(client_id, "3dview", "front", "cinematic")
    sbs.cinematic_control(client_id, 1, camera_id, camera_offset, tracked_id, tracked_offset)


    
def gui_history_redirect(back_name=None, back_label=None, back_data=None):
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    
    if back_label is None:
        back_label = task.active_label

    if back_name is  None:
        back_name = "BACK"

    history = task.get_variable("GUI_HISTORY")
    if history is None:
        history = []

    history_pos = task.get_variable("GUI_HISTORY_POS", 0)
    # Clear forward
    history = history[:history_pos]
    history.append( (back_name, back_label, back_data))
    task.set_variable("GUI_HISTORY_POS", len(history)-1)
    task.set_variable("GUI_HISTORY", history)



def gui_hide_choice():
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    
    promise = task.get_variable("BUTTON_PROMISE")
    if promise is None:
        return
    button_item = promise.running_button.layout_item
    button_layout = promise.button_layout

    gui_hide(button_item)
    gui_represent(button_layout)



import ctypes
from ctypes import wintypes
CF_UNICODETEXT = 13

user32 = ctypes.WinDLL('user32')
kernel32 = ctypes.WinDLL('kernel32')

OpenClipboard = user32.OpenClipboard
OpenClipboard.argtypes = wintypes.HWND,
OpenClipboard.restype = wintypes.BOOL
CloseClipboard = user32.CloseClipboard
CloseClipboard.restype = wintypes.BOOL
EmptyClipboard = user32.EmptyClipboard
EmptyClipboard.restype = wintypes.BOOL
GetClipboardData = user32.GetClipboardData
GetClipboardData.argtypes = wintypes.UINT,
GetClipboardData.restype = wintypes.HANDLE
SetClipboardData = user32.SetClipboardData
SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
SetClipboardData.restype = wintypes.HANDLE

GlobalLock = kernel32.GlobalLock
GlobalLock.argtypes = wintypes.HGLOBAL,
GlobalLock.restype = wintypes.LPVOID
GlobalUnlock = kernel32.GlobalUnlock
GlobalUnlock.argtypes = wintypes.HGLOBAL,
GlobalUnlock.restype = wintypes.BOOL
GlobalAlloc = kernel32.GlobalAlloc
GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
GlobalAlloc.restype = wintypes.HGLOBAL
GlobalSize = kernel32.GlobalSize
GlobalSize.argtypes = wintypes.HGLOBAL,
GlobalSize.restype = ctypes.c_size_t

GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040

unicode_type = type(u'')

def gui_clipboard_get():
    text = None
    OpenClipboard(None)
    handle = GetClipboardData(CF_UNICODETEXT)
    pcontents = GlobalLock(handle)
    size = GlobalSize(handle)
    if pcontents and size:
        raw_data = ctypes.create_string_buffer(size)
        ctypes.memmove(raw_data, pcontents, size)
        text = raw_data.raw.decode('utf-16le').rstrip(u'\0')
    GlobalUnlock(handle)
    CloseClipboard()
    return text

def gui_clipboard_put(s):
    if not isinstance(s, unicode_type):
        s = s.decode('mbcs')
    data = s.encode('utf-16le')
    OpenClipboard(None)
    EmptyClipboard()
    handle = GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(data) + 2)
    pcontents = GlobalLock(handle)
    ctypes.memmove(pcontents, data, len(data))
    GlobalUnlock(handle)
    SetClipboardData(CF_UNICODETEXT, handle)
    CloseClipboard()

gui_clipboard_copy = gui_clipboard_put