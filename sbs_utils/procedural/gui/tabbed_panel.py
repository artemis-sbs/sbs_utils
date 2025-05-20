from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.tabbed_panel import TabbedPanel
from sbs_utils.procedural.gui import gui_task_for_client
from .update import gui_represent
from ..query import to_set
from ...futures import Promise


def gui_tabbed_panel(items=None, style=None, tab=0, tab_location=0, icon_size=0):

    page = FrameContext.client_page
    task = FrameContext.task
    if page is None:
        return None
    tag = page.get_tag()
    # The gui_content sets the values
    layout_item = TabbedPanel(0, 0, 10, 10, tag, items, tab, tab_location, icon_size)

    apply_control_styles(".panel", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item


def gui_info_panel(tab=0, tab_location=0, icon_size=0, var=None):
    page = FrameContext.page

    panels = []
    if var is None:
        var = "__INFO_PANEL__"

    if var == "__INFO_PANEL__":
        panels = [
            {"path": "hide", "icon": 121, "show": None, "hide": None},  # off
            {
                "path": "ship_data",
                "icon": 140,
                "show": gui_panel_ship_data_show,
                "hide": gui_panel_ship_data_hide,
            },
        ]

    tp = gui_tabbed_panel(
        panels, tab=tab, tab_location=tab_location, icon_size=icon_size
    )

    page.gui_task.set_variable(var, tp)

    page.pending_info_panel = tp
    return tp


def gui_info_panel_add(path, icon_index, show, hide=None, var=None):
    page = FrameContext.page
    if var is None:
        var = "__INFO_PANEL__"
    tp = var
    if isinstance(var, str):
        tp = page.gui_task.get_variable(var)
    if tp is None:
        return
    panel = {"path": path, "icon": icon_index, "show": show, "hide": hide}
    tp.panels.append(panel)
    #
    # If this panel is the active panel it needs to be represented
    #
    if page.info_panel == tp:
        gui_represent(tp)

    return tp


def gui_info_panel_remove(path, var = None):
    page = FrameContext.page
    if var is None:
        var = "__INFO_PANEL__"
    tp = var
    if isinstance(var, str):
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


def gui_info_panel_send_message(
    client_id,
    message=None,
    message_color=None,
    path=None,
    title=None,
    title_color=None,
    banner=None,
    banner_color=None,
    face=None,
    icon_index=None,
    icon_color=None,
    button=None,
    button_press=None, # label or promise
    history=True,
    time=-1,
):
    client_ids = to_set(client_id)

    if message:
        message = {"message": message}
    if message_color:
        message["message_color"] = message_color
    if title:
        message["title"] = title
    if title_color:
        message["title_color"] = title_color
    if banner:
        message["banner"] = banner
    if banner_color:
        message["banner_color"] = banner_color
    if icon_index:
        message["icon_index"] = icon_index
    if icon_color:
        message["icon_color"] = icon_color
    if face:
        message["face"] = face

    button_press_promise = None
    if button:
        message["button"] = button
        button_press_promise = Promise()
    if button_press:
        message["button_press"] = button_press
    if button and button_press is None:
        message["button_press"] = button_press_promise

    if path is None:
        path = "message"

    var = f"${path.upper()}"


    for client_id in client_ids:
        task = gui_task_for_client(client_id)
        if task is None:
            return
        
        if history:
            # Only keep 10 items
            all = task.get_variable(var + "S", [])
            all.append(message)
            MAX_LINES = 9
            if len(all) > MAX_LINES:
                all = all[-MAX_LINES:]
            task.set_variable(var + "S", all)

        task.set_variable(var, message)
        if time >= 0:
            info_panel = task.main.page.info_panel
            if info_panel is not None:
                info_panel.flash_tab(path, time)
    return button_press_promise


def gui_panel_console_message(cid, left, top, width, height):
    task = gui_task_for_client(cid)

    if task is None:
        return

    path = task.get_variable("$INFO_PATH")
    var = f"${path.upper()}"
    message_obj = task.get_variable(
        var
    )  # , {"icon_index":69, "face": random_terran(civilian=True), "title": "Title", "message": "This will be the message"})
    if message_obj is None:
        return

    icon = message_obj.get("icon_index")
    color = message_obj.get("icon_color", "white")
    face = message_obj.get("face")
    title = message_obj.get("title")
    title = task.compile_and_format_string(title)
    banner = message_obj.get("banner")
    banner = task.compile_and_format_string(banner)
    message = message_obj.get("message")
    message = task.compile_and_format_string(message)
    #
    title_color = message_obj.get("title_color", "white")
    title_color = task.compile_and_format_string(title_color)
    banner_color = message_obj.get("banner_color", "white")
    banner_color = task.compile_and_format_string(banner_color)
    message_color = message_obj.get("message_color", "white")
    message_color = task.compile_and_format_string(message_color)

    buttons = message_obj.get("button", [])
    button_press = message_obj.get("button_press")

    if banner:
        gui_row(style="row-height:2.1em;")
        with gui_sub_section():
            gui_row(style="row-height:2em;")
            gui_text(f"$text: {banner};font:gui-3;color:{banner_color};")

    if icon is not None or face is not None:
        gui_row(style="row-height:3em;")
        with gui_sub_section():
            gui_row()
            with gui_sub_section():
                gui_row()
                if icon is not None:
                    gui_icon(f"icon_index:{icon};color:{color};")
                if face is not None:
                    gui_face(face)

    if title:
        gui_row(style="row-height:1.1em;")
        with gui_sub_section():
            gui_row(style="row-height:1em;")
            gui_text(f"$text: {title};font:gui-2;color:{title_color}")

    if message:
        gui_row()
        gui_text(f"$text: {message};font:gui-2;color:{message_color}")

    if buttons and not isinstance(buttons, list):
        buttons = [(buttons, button_press)]


    for button_tuple in buttons:
        gui_row(style="row-height:2em;")
        button = button_tuple
        if isinstance(button_tuple, tuple):
            button = button_tuple[0]
            button_press = button_tuple[1]
            gui_button(button, data={"__MESSAGE__": message_obj}, on_press=button_press)
        
        
        gui_blank(style="col-width:1.5em")

    if buttons:
        gui_row(style="row-height:1em;")
        gui_blank()



from .gui import gui_percent_from_pixels


def gui_panel_ship_data_show(cid, left, top, width, height):
    ctx = FrameContext.context
    waterfall_size = gui_percent_from_pixels(cid, 20).y
    waterfall_size *= 4  # 4 lines

    ctx.sbs.send_client_widget_rects(
        cid,
        "ship_data",
        left,
        top,
        left + width,
        top + height - waterfall_size,
        left,
        top,
        left + width,
        top + height - waterfall_size,
    )
    ctx.sbs.send_client_widget_rects(
        cid,
        "text_waterfall",
        left,
        top + height - waterfall_size,
        left + width,
        top + height,
        left,
        top + height - waterfall_size,
        left + width,
        top + height,
    )


def gui_panel_ship_data_hide(cid, left, top, width, height):
    ctx = FrameContext.context
    waterfall_size = gui_percent_from_pixels(cid, 20).y
    waterfall_size *= 4  # 4 lines
    left = -100
    ctx.sbs.send_client_widget_rects(
        cid,
        "ship_data",
        left,
        top,
        left + width,
        top + height - waterfall_size,
        left,
        top,
        left + width,
        top + top + height - waterfall_size,
    )
    ctx.sbs.send_client_widget_rects(
        cid,
        "text_waterfall",
        left,
        top + height - waterfall_size,
        left + width,
        top + height,
        left,
        top + height - waterfall_size,
        left + width,
        top + height,
    )


# def gui_panel_widget_hide(cid, left, top, width, height, widget):
#     ctx = FrameContext.context
#     left = 100
#     top = 100
#     ctx.sbs.send_client_widget_rects(cid,
#                 widget,
#                 left, top, left+width, top+height,
#                 left, top, left+width, top+height )


def gui_panel_widget_show(cid, left, top, width, height, widget):
    ctx = FrameContext.context
    ctx.sbs.send_client_widget_rects(
        cid,
        widget,
        left,
        top,
        left + width,
        top + height,
        left,
        top,
        left + width,
        top + height,
    )


def gui_panel_widget_hide(cid, left, top, width, height, widget):
    ctx = FrameContext.context
    left = 100
    top = 100
    ctx.sbs.send_client_widget_rects(
        cid,
        widget,
        left,
        top,
        left + width,
        top + height,
        left,
        top,
        left + width,
        top + height,
    )


def gui_panel_console_message_list(cid, left, top, width, height):
    task = gui_task_for_client(cid)

    if task is None:
        return

    path = task.get_variable("$INFO_PATH")
    var = f"${path.upper()}"
    messages_objs = task.get_variable(var)
    if messages_objs is None:
        return
    gui_list_box(messages_objs, "", item_template=gui_panel_console_message_list_item, select=False)
    # avoid bleeding out 
    gui_blank(style="col-width:0.5em")


def gui_panel_console_message_list_item(message_obj):
    task = FrameContext.client_task
    if message_obj is None:
        return

    icon = message_obj.get("icon_index")
    color = message_obj.get("icon_color", "white")
    face = message_obj.get("face")
    title = message_obj.get("title")
    title = task.compile_and_format_string(title)
    message = message_obj.get("message")
    message = task.compile_and_format_string(message)

    title_color = message_obj.get("title_color", "white")
    title_color = task.compile_and_format_string(title_color)
    message_color = message_obj.get("message_color", "white")
    message_color = task.compile_and_format_string(message_color)


    # Need this for the flacky sub_section
    # if icon is not None or face is not None:

    #
    # Title
    #
    gui_row(style="row-height:2.1em;")
    with gui_sub_section():
        gui_row(style="row-height:2em;")
        if icon is not None or face is not None:
            with gui_sub_section(style="row-height:2em;col-width:2em;"):
                gui_row(style="row-height:1.8em;col-width:1.8em;")
                with gui_sub_section():
                    if icon is not None:
                        gui_row()
                        gui_icon(f"icon_index:{icon};color:{color};")
                    if face is not None:
                        gui_row()
                        gui_face(face)

        if title:
            gui_text(f"$text: {title};font:gui-2;color:{title_color};")
        elif message:
            gui_text(f"$text: {message};font:gui-2;color:{message_color};")

from .listbox import gui_list_box

def panel_upgrade_item(message_obj):
    task = FrameContext.client_task

    icon = message_obj.get("icon_index")
    color = message_obj.get("icon_color", "white")
    title = message_obj.get("title")
    title = task.compile_and_format_string(title)
    message = message_obj.get("message")
    message = task.compile_and_format_string(message)

    title_color = message_obj.get("title_color", "white")
    title_color = task.compile_and_format_string(title_color)
    message_color = message_obj.get("message_color", "white")
    message_color = task.compile_and_format_string(message_color)


    # Need this for the flacky sub_section
    # if icon is not None or face is not None:

    #
    # Title
    #
    gui_row(style="row-height:1.5em;")
    with gui_sub_section():
        gui_row(style="row-height:1.4em;")
        if icon is not None:
            with gui_sub_section(style="row-height:2em;col-width:2em;"):
                gui_row(style="row-height:1.8em;col-width:1.8em;")
                with gui_sub_section():
                    if icon is not None:
                        gui_row()
                        gui_icon(f"icon_index:{icon};color:{color};")

        if title:
            count = 1
            if title.startswith("I") or title.startswith("C"):
                count = 2
                gui_button(f"$text: {title}({count});font:gui-2;color:{title_color};")
                # Buttons leak margins
                gui_blank(style="col-width:1.5em")
            else:
                gui_text(f"$text: {title}({count})  1:30;font:gui-2;color:{title_color};")


    if message:
        gui_row(style="row-height:3.1em;")
        gui_text(f"$text: {message};font:gui-2;color:{message_color};")
            
            

        


def gui_panel_upgrade_list(cid, left, top, width, height):
    task = gui_task_for_client(cid)

    if task is None:
        return

    path = task.get_variable("$INFO_PATH")
    var = f"${path.upper()}"
    messages_objs = task.get_variable(var)
    if messages_objs is None:
        messages_objs = [{"title": "Carapaction Coil", "message":"5 min 300% shield recharge boost", "title_color": "yellow"}]
        messages_objs.append({"title": "Infusion P-Coils", "message":"5 min Impulse and Maneuver Speed boost", "title_color": "yellow"})
        messages_objs.append({"title": "Lateral Array", "message":"5 min Target Scan Triple Speed", "title_color": "green" })
        messages_objs.append({"title": "Lateral Array", "message":"5 min Target Scan Triple Speed", "title_color": "green" })
        messages_objs.append({"title": "Lateral Array", "message":"5 min Target Scan Triple Speed", "title_color": "green" })
        messages_objs.append({"title": "Lateral Array", "message":"5 min Target Scan Triple Speed", "title_color": "green" })
        messages_objs.append({"title": "Lateral Array", "message":"5 min Target Scan Triple Speed", "title_color": "green" })
        messages_objs.append({"title": "Lateral Array", "message":"5 min Target Scan Triple Speed", "title_color": "green" })
        messages_objs.append({"title": "Infusion P-Coils", "message":"5 min Impulse and Maneuver Speed boost", "title_color": "yellow"})
        messages_objs.append({"title": "Lateral Array", "message":"5 min Target Scan Triple Speed", "title_color": "green" })

    #obj_list = gui_list_box(messages_objs,"row-height: 0.1em; background:#1572;", item_template=panel_upgrade_item, select=False)
    #obj_list = gui_list_box(messages_objs,"row-height: 0.1em; background:#1572;", item_template=panel_upgrade_item, select=False)
    obj_list = gui_list_box(messages_objs, "", item_template=panel_upgrade_item, select=False)
    # avoid bleeding out 
    gui_blank(style="col-width:0.5em")

    
