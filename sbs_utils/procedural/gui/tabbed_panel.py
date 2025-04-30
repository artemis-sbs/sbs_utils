from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.widgets.tabbed_panel import TabbedPanel


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
    panels =  [
                {"icon": 121, "show": None, "hide": None}, # off
                {"icon": 140, 
                    "show": lambda c,l,t,w,h: panel_widget_show(c,l,t,w,h, "ship_data"), 
                    "hide":  lambda c,l,t,w,h: panel_widget_hide(c,l,t,w,h, "ship_data")} 
            ]
    return gui_tabbed_panel(panels, tab=tab, tab_location=tab_location, icon_size=icon_size)
        

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

def panel_ship_date_show(cid, left, top, width, height):
    panel_widget_show(cid, left,top, width, height, "ship_data")
def panel_ship_date_hide(cid, left, top, width, height):
    panel_widget_hide(cid, left,top, width, height, "ship_data")

def panel_2dview_show(cid, left, top, width, height):
    panel_widget_show(cid, left,top, width, height, "2dview")
def panel_2dview_hide(cid, left, top, width, height):
    panel_widget_hide(cid, left,top, width, height, "2dview")

