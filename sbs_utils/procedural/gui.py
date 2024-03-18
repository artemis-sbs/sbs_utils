from ..mast.mast import Scope, Button
from .query import to_id
from .inventory import get_inventory_value, set_inventory_value
from ..helpers import FrameContext
from ..pages import layout
from ..mast.parsers import LayoutAreaParser, StyleDefinition
from ..futures import Trigger, AwaitBlockPromise
from ..gui import get_client_aspect_ratio
from ..mast.pollresults import PollResults
import re
import sbs

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


def compile_formatted_string(message):
    """build a compiled version of the format string for faster execution

    Args:
        message (str): The format string

    Returns:
        code: compiled python eval
    """    
    if message is None:
        return message
    if "{" in message:
        message = f'''f"""{message}"""'''
        code = compile(message, "<string>", "eval")
        return code
    else:
        return message
    



def apply_style_name(style_name, layout_item, task):
    if style_name is None:
        return
    style_def = StyleDefinition.styles.get(style_name)
    apply_style_def(style_def, layout_item, task)

def apply_style_def(style_def, layout_item, task):
    if style_def is None:
        return
    aspect_ratio = get_client_aspect_ratio(task.main.page.client_id)
    # aspect_ratio = task.main.page.aspect_ratio
    if aspect_ratio.x == 0:
        aspect_ratio.x = 1
    if aspect_ratio.y == 0:
        aspect_ratio.y = 1

    area = style_def.get("area")
    if area is not None:
        i = 1
        values=[]
        for ast in area:
            if i >0:
                ratio =  aspect_ratio.x
            else:
                ratio =  aspect_ratio.y
            i=-i
            if ratio == 0:
                ratio = 1
            values.append(LayoutAreaParser.compute(ast, task.get_symbols(),ratio))
        layout_item.set_bounds(layout.Bounds(*values))

    height = style_def.get("row-height")
    if height is not None:
        height = LayoutAreaParser.compute(height, task.get_symbols(),aspect_ratio.y)
        layout_item.set_row_height(height)        
    width = style_def.get("col-width")
    if width is not None:
        width = LayoutAreaParser.compute(width, task.get_symbols(),aspect_ratio.x)
        layout_item.set_col_width(width)        
    padding = style_def.get("padding")
    if padding is not None:
        #aspect_ratio = task.main.page.aspect_ratio
        i = 1
        values=[]
        for ast in padding:
            if i >0:
                ratio =  aspect_ratio.x
            else:
                ratio =  aspect_ratio.y
            i=-i
            values.append(LayoutAreaParser.compute(ast, task.get_symbols(),ratio))
        while len(values)<4:
            values.append(0.0)
        layout_item.set_padding(layout.Bounds(*values))
    background = style_def.get("background")
    if background is not None:
        background = compile_formatted_string(background)
        layout_item.background = task.format_string(background)

    click_text = style_def.get("click_text")
    if click_text is not None:
        click_text = compile_formatted_string(click_text)
        layout_item.click_text = task.format_string(click_text)

    click_font = style_def.get("click_font")
    if click_font is not None:
        click_font = compile_formatted_string(click_font)
        layout_item.click_font = task.format_string(click_font)

    click_color = style_def.get("click_color")
    if click_color is not None:
        click_color = compile_formatted_string(click_color)
        layout_item.click_color = task.format_string(click_color)

    click_tag = style_def.get("click_tag")
    if click_tag is not None:
        click_tag = compile_formatted_string(click_tag)
        layout_item.click_tag = task.format_string(click_tag).strip()

    tag = style_def.get("tag")
    if tag is not None:
        tag = compile_formatted_string(tag)
        layout_item.tag = task.format_string(tag).strip()

def apply_control_styles(control_name, extra_style, layout_item, task):
        apply_style_name(control_name, layout_item, task)
        if extra_style is not None:
            if isinstance(extra_style,str):
                if ":" in extra_style:
                    apply_style_def(StyleDefinition.parse(extra_style),  layout_item, task)
                else:
                    apply_style_name(extra_style, layout, task)
            else:
                apply_style_def(extra_style,  layout_item, task)


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
    
    task.main.page.add_row()
    layout_item = page.get_pending_row()
    apply_control_styles(".row", style, layout_item, task)
    return layout_item

def gui_blank(style=None):
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
    

def gui_console(console):
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
            widgets = "2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
        case "weapons":
            console =  "normal_weap"
            widgets = "2dview^weapon_control^weap_beam_freq^weap_beam_speed^weap_torp_conversion^ship_data^shield_control^text_waterfall^main_screen_control"
        case "science":
            console =  "normal_sci"
            widgets = "science_2d_view^ship_data^text_waterfall^science_data^science_sorted_list"
        case "engineering":
            console =  "normal_engi"
            widgets = "ship_internal_view^grid_object_list^grid_face^grid_control^text_waterfall^eng_heat_controls^eng_power_controls^ship_data"
        case "comms":
            console =  "normal_comm"
            widgets = "text_waterfall^comms_waterfall^comms_control^comms_face^comms_sorted_list^ship_data^red_alert"
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

    tag = task.main.page.get_tag()
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
            self.task.set_value_keep_scope("__ITEM__", self.layout_item)
            data = self.layout_item.data
            self.task.push_inline_block(self.label, self.loc, data)
            restore = FrameContext.page
            FrameContext.page = self.task.main.page
            self.task.tick()
            FrameContext.page = restore

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
        restore = FrameContext.page
        FrameContext.page = self.task.main.page
        self.task.tick()
        FrameContext.page = restore
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
    page.add_on_change(handler)



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

    def __init__(self, task, timeout=None) -> None:
        super().__init__(timeout)

        self.buttons = []
        self.inlines = []
        self.button = None
        self.var = None
        self.task = task
        self.disconnect_label = None
        self.on_change = None
        self.focus_label = None
        self.run_focus = False
        self.running_button = None
        #print("INit ")
        
    def initial_poll(self):
        if self._initial_poll:
            return
        # Will Build buttons
        #print("INit pool")
        self.expand_inlines()
        self.show_buttons()
        super().initial_poll()

    def check_for_button_done(self):
        #
        # THIS sets the promise to finish 
        # after you let the button process
        # science will override this to 
        # keep going until all scanned
        if self.running_button:
            self.set_result(self.running_button)

    def poll(self):
        super().poll()
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
            if button.for_name:
                task.set_value(button.for_name, button.data, Scope.TEMP)

            
            #print(f"CHOICE {button.loc+1} ")
            #
            # If the button doesn't jump, make sure the 
            # promise has a chance to finish
            #
            self.running_button = self.button
            self.button = None
            if button.label:
                task.push_inline_block(button.label)
            else:
                task.push_inline_block(task.active_label,button.loc+1)
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
        if button.for_code is not None:
            iter_value = self.task.eval_code(button.for_code)
            for data in iter_value:
                self.task.set_value(button.for_name, data, Scope.TEMP)
                clone = button.clone()
                clone.data = data
                clone.message = self.task.format_string(clone.message)
                if clone.color:
                    clone.color = self.task.format_string(clone.color)
                buttons.append(clone)

        return buttons

    def get_expanded_buttons(self):
        buttons = []
        # Expand all the 'for' buttons
        for button in self.buttons:
            if button.__class__.__name__ != "Button":
                buttons.append(button)
            elif button.for_name is None:
                buttons.append(button)
            else:
                buttons.extend(self.expand_button(button))
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
        
    
    

class GuiPromise(ButtonPromise):
    def __init__(self, page, timeout=None) -> None:
        super().__init__(page.gui_task, timeout)

        self.page = page
        self.button_layout = None

    def initial_poll(self):
        if self._initial_poll:
            return
        super().initial_poll()
        self.page.set_button_layout(self.button_layout)

    #
    # This 
    #
    def show_buttons(self):
        if len(self.buttons) == 0:
            return
        
        if self.task is None:
            self.task = self.page.gui_task
            # First run could have no gui_task
            if self.task is None:
                self.task = FrameContext.task
        task = self.task
        aspect_ratio = get_client_aspect_ratio(task.main.page.client_id)

        top = ((aspect_ratio.y - 30)/aspect_ratio.y)*100
        button_layout = layout.Layout(None, None, 0,top,100,100)
        button_layout.tag = task.main.page.get_tag()

        active = 0
        index = 0
        layout_row: layout.Row
        layout_row = layout.Row()
        layout_row.tag = task.main.page.get_tag()

        buttons = self.get_expanded_buttons()
        
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
    ret = GuiPromise(page, timeout)
    if buttons is not None:
        for k in buttons:
            ret .buttons.append(Button(k, label=buttons[k],loc=0))
        
    return ret
    

