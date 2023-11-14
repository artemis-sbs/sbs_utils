from .query import to_id
from .inventory import get_inventory_value, set_inventory_value
from ..helpers import FrameContext
from ..pages import layout
from ..mast.parsers import LayoutAreaParser, StyleDefinition

def show_warning(t):
    print(t)


def gui_add_console_tab(id_or_obj, console, tab_name, label):
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
    if message is None:
        return message
    if "{" in message:
        message = f'''f"""{message}"""'''
        code = compile(message, "<string>", "eval")
        return code
    else:
        return message
    



def apply_style_name(style_name, layout_item, task):
    style_def = StyleDefinition.styles.get(style_name)
    apply_style_def(style_def, layout_item, task)

def apply_style_def(style_def, layout_item, task):
    if style_def is None:
        return
    aspect_ratio = task.main.page.aspect_ratio
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
        width = LayoutAreaParser.compute(height, task.get_symbols(),aspect_ratio.x)
        layout_item.set_col_width(height)        
    padding = style_def.get("padding")
    if padding is not None:
        aspect_ratio = task.main.page.aspect_ratio
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
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
        return None
    
    tag = page.get_tag()
    layout_item = layout.Face(tag,face)
    apply_control_styles(".face", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_icon(props, style=None):
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        show_warning("No Page")
        return None
    
    tag = page.get_tag()
    layout_item = layout.Icon(tag,props)
    apply_control_styles(".icon", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_image(props, style=None):
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        show_warning("No Page")
        return None
    
    if "image:" not in props:
        props = f"image:{props};"

    if "color:" not in props:
        props+="color:white;"
    
    tag = page.get_tag()
    layout_item = layout.Image(tag,props)
    apply_control_styles(".image", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_ship(props, style=None):
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        show_warning("No Page")
        return None
        
    
    # Log warning
    tag = page.get_tag()
    layout_item = layout.Ship(tag,props)
    apply_control_styles(".ship", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_row(style=None):
    page = FrameContext.page
    task = FrameContext.task
        
    if page is None:
        show_warning("No Page")
        return None
    
    task.main.page.add_row()
    layout_item = page.get_pending_row()
    apply_control_styles(".row", style, layout_item, task)
    return layout_item

def gui_blank(style=None):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
        return None
    
    layout_item = layout.Blank()
    apply_control_styles(".blank", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_hole(style=None):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
        return None
    # Log warning
    layout_item = layout.Hole()
    apply_control_styles(".hole", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_button(msg, style=None, data=None):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)
    layout_item = layout.Button(tag, msg)
    layout_item.data = data
    apply_control_styles(".button", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_drop_down(msg, style=None, var=None, data=None):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
        return None
    tag = page.get_tag()
    msg = task.compile_and_format_string(msg)
    layout_item = layout.Dropdown(tag, msg)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()
    apply_control_styles(".dropdown", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_checkbox(msg, style=None, var=None, data=None):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
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
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
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

    apply_control_styles(".radio", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)

    return layout_item

def gui_vradio(msg, style=None, var=None, data=None, vertical=False):
    return gui_radio(msg, style, var, data, True)

def gui_slider(msg, style=None, var=None, data=None, is_int=False):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
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
    return gui_slider(msg, style, var, True, data)


def gui_input(label, style=None, var=None, data=None):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
        return None
    tag = page.get_tag()
    if label is not None:
        label = task.compile_and_format_string(label)
    else:
        label = ""

    val = ""
    if var is not None:
        val = task.get_variable(var, "")

    if "text:" not in label:
        label = f"text:{val};{label}"

    layout_item = layout.TextInput(tag, label)
    layout_item.data = data
    if var is not None:
        layout_item.var_name = var
        layout_item.var_scope_id = task.get_id()

    apply_control_styles(".input", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_section(style=None):
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        show_warning("No Page")
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
    page = FrameContext.page
    if page is None:
        show_warning("No Page")
        return None
    page.set_widget_list(console, widgets)


def gui_widget_list_clear():
    gui_widget_list("","")

def gui_activate_console(console):
    page = FrameContext.page
    if page is None:
        show_warning("No Page")
        return None
    page.activate_console(console)
        
def gui_layout_widget(widget):
    page = FrameContext.page
    if page is None:
        show_warning("No Page")
        return None
    
    page.add_console_widget(widget)
    control = layout.ConsoleWidget(widget)
    page.add_content(control, None)
    return control
    

def gui_console(console):
    page = FrameContext.page
    if page is None:
        show_warning("No Page")
        return None
    widgets = ""
    match console.lower():
        case "helm":
            console =  "normal_helm"
            widgets = "2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
        case "weapons":
            console =  "normal_weap"
            widgets = "2dview^weapon_control^weap_beam_freq^weap_beam_speed^ship_data^shield_control^text_waterfall^main_screen_control"
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
            widgets = "3dview^ship_data^text_waterfall"
    page.set_widget_list(console, widgets)
