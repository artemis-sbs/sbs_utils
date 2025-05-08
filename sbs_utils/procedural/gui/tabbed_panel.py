from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.tabbed_panel import TabbedPanel
from sbs_utils.procedural.gui import gui_task_for_client
from .update import gui_represent


def gui_tabbed_panel(items=None, style=None, tab=0, tab_location=0, icon_size=0):
    
    page = FrameContext.client_page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    # The gui_content sets the values
    layout_item = TabbedPanel(0, 0, 10,10, tag, items, tab, tab_location, icon_size)

    apply_control_styles(".panel", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_info_panel(tab=0, tab_location=0, icon_size=0, var=None):
    page = FrameContext.page

    panels =  [
                {"path": "hide", "icon": 121, "show": None, "hide": None}, # off
                {"path": "ship_data", "icon": 140, 
                    "show": lambda c,l,t,w,h: panel_widget_show(c,l,t,w,h, "ship_data"), 
                    "hide":  lambda c,l,t,w,h: panel_widget_hide(c,l,t,w,h, "ship_data")}, 
                {"path": "message", "icon": 83, 
                    "show": panel_console_message, 
                    "hide":  None} 
            ]
    tp =  gui_tabbed_panel(panels, tab=tab, tab_location=tab_location, icon_size=icon_size)
    if var is None:
        var = "__INFO_PANEL__"

    page.gui_task.set_variable(var, tp)

    page.pending_info_panel = tp
    return tp


def gui_info_panel_add(path, icon_index, show, hide=None, var=None):
    page = FrameContext.page
    if var is None:
        var = "__INFO_PANEL__"

    tp = page.gui_task.get_variable(var)
    if tp is None:
        return
    panel =  {"path": path, "icon": icon_index, "show": show, "hide": hide}
    tp.panels.append(panel)
    #
    # If this panel is the active panel it needs to be represented
    #
    if page.info_panel == tp:
        gui_represent(tp)

    return tp


def gui_info_panel_remove(path):
    page = FrameContext.page
    if var is None:
        var = "__INFO_PANEL__"

    tp = page.gui_task.get_variable(var)
    if tp is None:
        return
    st = len(tp.panels)
    panels = [panel for panel in tp.panels if panel.get("path") != path]
    tp.panels = panels
    #
    # If this panel is the active panel it needs to be represented
    #
    if page.info_panel == tp and st > len(tp.panels):
        gui_represent(tp)

    return tp





from .section import gui_sub_section
from .text import gui_text
from .icon import gui_icon
from .face import gui_face
from .row import gui_row
from .button import gui_button
from .message import gui_message
from .blank import gui_blank



def gui_info_panel_send_message(client_id, message=None, message_color=None, title=None, title_color=None, face=None, icon_index=None, icon_color=None, button=None, button_label=None, history=True, time=-1):
    task = gui_task_for_client(client_id)
    if task is None:
        return
    if message:
        message = {"message": message}
    if message_color:
        message["message_color"] = message_color
    if title:
        message["title"] = title
    if title_color:
        message["title_color"] = title_color
    if icon_index:
        message["icon_index"] = icon_index
    if icon_color:
        message["icon_color"] = icon_color
    if face:
        message["face"] = face
    if button:
        message["button"] = button
    if button_label:
        message["button_label"] = button_label
    if history:
        message["history"] = history

    task.set_variable("$MESSAGE", message)
    if time>=0:
        info_panel = task.main.page.info_panel
        if info_panel is not None:
            info_panel.flash_tab("message",time)
    


def panel_console_message(cid, left, top, width, height):
    task = gui_task_for_client(cid)
    
    if task is None:
        return
    message_obj = task.get_variable("$MESSAGE") #, {"icon_index":69, "face": random_terran(civilian=True), "title": "Title", "message": "This will be the message"})
    if message_obj is None:
        return
    
    
    icon = message_obj.get("icon_index")
    color = message_obj.get("icon_color", "white")
    face = message_obj.get("face")
    title = message_obj.get("title")
    title = task.compile_and_format_string(title)
    message = message_obj.get("message")
    message = task.compile_and_format_string(message)
    buttons = message_obj.get("button", [])
    button_label = message_obj.get("button_label")

    gui_row(style="row-height:4em;")
    if icon is not None:
        gui_icon(f"icon_index:{icon};color:{color};")
    if face is not None:
        gui_face(face)

    if title:
        gui_row(style="row-height:2em;")
        gui_text(f"$text: {title};font:gui-4")

    if message:
        gui_row()
        gui_text(f"$text: {message};font:gui-2")

    if buttons and button_label and not isinstance(buttons, list):
        buttons = [(buttons, button_label)]
    
    for button in buttons:
        gui_row(style="row-height:2em;")
        gui_button(button[0],data={"__MESSAGE__": message_obj}, jump=button[1])
        gui_blank(style="col-width:1.5em")
        
    if buttons:
        gui_row(style="row-height:1em;")
        gui_blank()
    




    


def panel_widget_show(cid, left, top, width, height, widget):
    ctx = FrameContext.context
    ctx.sbs.send_client_widget_rects(cid, 
                widget, 
                left, top, left+width, top+height, 
                left, top, left+width, top+height ) 

def panel_widget_hide(cid, left, top, width, height, widget):
    ctx = FrameContext.context
    left = 100
    top = 100
    ctx.sbs.send_client_widget_rects(cid, 
                widget, 
                left, top, left+width, top+height, 
                left, top, left+width, top+height ) 

