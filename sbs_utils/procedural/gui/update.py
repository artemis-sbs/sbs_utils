from ...helpers import FrameContext, FakeEvent


def gui_represent(layout_item):
    """Redraw a layout item on the client screen.

    For sections and regions, recalculates the entire sub-layout and redraws
    all children. For individual items or rows, redraws that element only.

    Args:
        layout_item: The layout object to redraw.

    Example:
        gui_represent(my_section)
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
    

    event = frame_event
    event_cl = FrameContext.context.event.client_id
    page_cl = FrameContext.page.client_id
    # Sometimes the event and page don' match
    # if one is 0 the other is more likely correct
    # Example: Manual beams Event is 0, but page is right
    # Property Grid event is right, Page is wrong
    if event_cl != page_cl:
        actual_cl = max(event_cl, page_cl)
        event = FakeEvent(actual_cl)

    
    #print(f"E: {event_cl} P: {page_cl}")
    # region_cl = region.page.client_id
    layout_item.represent(event)


def gui_show(layout_item):
    """Make a hidden layout item visible.

    For sections, recalculates the layout after showing. For individual items
    or rows, shows the element but does not re-layout — pair with
    ``gui_represent`` on the parent section if the layout needs updating.

    Args:
        layout_item: The layout object to show. No-op if already visible or
            ``None``.

    Example:
        gui_show(warning_row)
        gui_represent(my_section)
    """    
    if layout_item is None:
        return
    # Removed layout_item.hidden check, since that checks both `_show` and `_is_shown`.
    # This only changes `_show`
    layout_item.show(True)
    # page = FrameContext.page
    # if page is None:
    #     return
    # event = FakeEvent(page.client_id)
    # layout_item.represent(event)

def gui_hide(layout_item):
    """Hide a visible layout item.

    For sections, recalculates the layout after hiding. For individual items
    or rows, hides the element but does not re-layout — pair with
    ``gui_represent`` on the parent section if the layout needs updating.

    Args:
        layout_item: The layout object to hide. No-op if already hidden or
            ``None``.

    Example:
        gui_hide(warning_row)
        gui_represent(my_section)
    """    
    if layout_item is None:
        return
    # Removed layout_item.hidden check, since that checks both `_show` and `_is_shown`.
    # This only changes `_show`
    layout_item.show(False)
    # page = FrameContext.page
    # if page is None:
    #     return
    # event = FakeEvent(page.client_id)
    # layout_item.represent(event)




def gui_refresh(label):
    """Re-run an ``await gui()`` block at a given label on the current task.

    Causes any scheduler running ``label`` to rebuild its GUI from scratch on
    the next tick.

    Args:
        label: MAST label whose ``await gui()`` block should be refreshed.
            Pass ``None`` to refresh the current task's active label.

    Example:
        gui_refresh(status_panel)
    """    
    task = FrameContext.task
    if label is None:
        task.main.refresh(label)
    else:
        task.main.mast.refresh_schedulers(task.main, label)

def gui_rebuild(region):
    """Mark a section or region to rebuild its layout on the next present.

    Clears the region's sub-layout so it is reconstructed from scratch the
    next time the region is rendered.

    Args:
        region: A section or region layout item.

    Returns:
        The same ``region`` object, for chaining.

    Example:
        gui_rebuild(my_region)
        gui_represent(my_region)
    """
    region.sub_section.rebuild()
    return region

def gui_update(tag, props, shared=False, test=None):
    """Update the property string of an existing GUI element by tag.

    Finds the element with the given tag on the current page (or all pages if
    ``shared=True``) and updates its properties in-place without rebuilding the
    full layout.

    Args:
        tag (str): The element tag to find and update.
        props (str): New property string for the element, e.g.
            ``"$text:Firing!;color:red;"``.
        shared (bool, optional): Apply the update to all client pages, not just
            the current one. Defaults to ``False``.
        test (dict | None, optional): Only apply the update when any variable
            in ``test`` has changed since the last update. Defaults to None
            (always update).

    Example:
        gui_update(status_tag, "$text:OK;color:green;")
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
    """Update a GUI element by tag on all client pages.

    Convenience wrapper for ``gui_update(tag, props, shared=True, test=test)``.

    Args:
        tag (str): The element tag to find and update.
        props (str): New property string for the element.
        test (dict | None, optional): Only update when any variable in
            ``test`` has changed. Defaults to None.

    Example:
        gui_update_shared(alert_tag, "$text:ALERT;color:red;")
    """
    gui_update(tag, props, True, test)



