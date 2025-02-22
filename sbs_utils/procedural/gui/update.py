from ...helpers import FrameContext, FakeEvent


def gui_represent(layout_item):
    """redraw an item

    ??? Note
        For sections it will recalculate the layout and redraw all items

    Args:
        layout_item (layout_item): 
    """    
    
    #
    # This get the client ID from the event
    # To get the true client ID
    # There was confusion when comms runs on  client_id 0
    # but want to update the client's GUI
    #
    frame_event = FrameContext.context.event
    if frame_event is None:
        return
    event = FakeEvent(frame_event.client_id)
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

def gui_rebuild(region):
    """ prepares a section/region to be build a new layout

    Args:
        region (layout_item): a layout/Layout item

    Returns:
        layout object: The Layout object created
    """
    region.sub_section.rebuild()
    return region

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



