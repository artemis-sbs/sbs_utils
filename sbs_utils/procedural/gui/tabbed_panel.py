from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.tabbed_panel import TabbedPanel
from sbs_utils.procedural.gui import gui_task_for_client


def gui_tabbed_panel(items=None, style=None, tab=0, tab_location=0, icon_size=0):
    
    page = FrameContext.page
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


def gui_info_panel(tab=0, tab_location=0, icon_size=0):
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
    page.pending_info_panel = tp
    return tp
        

from .section import gui_sub_section
from .text import gui_text
from .icon import gui_icon
from .face import gui_face
from .row import gui_row


def tabbed_panel_send_message(client_id, message, title=None, face=None, icon_index=None, icon_color=None, time=-1):
    task = gui_task_for_client(client_id)
    if task is None:
        return
    message = {"message": message}
    if title:
        message["title"] = title
    if icon_index:
        message["icon_index"] = icon_index
    if icon_color:
        message["icon_color"] = icon_color
    if face:
        message["face"] = face
    task.set_variable("$MESSAGE", message)
    if time>=0:
        info_panel = task.main.page.info_panel
        if info_panel is not None:
            info_panel.flash_tab("message",time)
    


def panel_console_message(cid, left, top, width, height):
    task = gui_task_for_client(cid)
    if task is None:
        return
    message = task.get_variable("$MESSAGE") #, {"icon_index":69, "face": random_terran(civilian=True), "title": "Title", "message": "This will be the message"})

    if message is None:
        return
    icon = message.get("icon_index")
    color = message.get("icon_color", "white")
    face = message.get("face")
    title = message.get("title")
    message = message.get("message")
    gui_row(style="row-height:4em;")
    if icon is not None:
        gui_icon(f"icon_index:{icon};color:{color};")
    if face is not None:
        gui_face(face)

    if title:
        gui_row(style="row-height:2em;")
        gui_text(f"$text: {title};font:gui-4")
    gui_row()
    gui_text(f"$text: {message};font:gui-2")

    


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

