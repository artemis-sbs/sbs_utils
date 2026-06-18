from ...helpers import FrameContext, FrameContextOverride, FakeEvent

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

from ...gui import Gui
def gui_reroute_client(client_id, label, data=None):
    """Jump a specific client's GUI task to a new label immediately.

    Finds the client's active page, optionally sets variables from ``data``,
    then jumps the page's GUI task to ``label`` and ticks it in the current
    frame context.

    Args:
        client_id (int): The client to reroute.
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.

    Example:
        gui_reroute_client(CLIENT_ID, briefing_screen)
    """
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
        # This needs to look like the client is being told to repaint
        fe = FakeEvent(page.client_id, "mission_tick")
        with FrameContextOverride(page.gui_task, page, fe):
            page.gui_task.jump(label)
            page.gui_task.tick_in_context()

def gui_reroute_server(label, data=None):
    """Jump the server GUI task to a new label.

    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.

    Example:
        gui_reroute_server(server_status_page)
    """    
    if _gui_reroute_main(label, True):
        return
    gui_reroute_client(0,label, data)


def gui_reroute_clients(label, data=None, exclude=None):
    """Jump all connected client GUI tasks to a new label.

    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on each task before
            jumping. Defaults to None.
        exclude (set | None, optional): Set of client IDs to skip. Defaults
            to None (no exclusions).

    Example:
        gui_reroute_clients(mission_end_screen, exclude={spectator_id})
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

def gui_history_store(back_text, back_label=None):
    """Record the current label as a history entry (back destination).

    Stores the active label (or ``back_label``) so that ``gui_history_back``
    can return to it later. Use ``gui_history_jump`` instead when also
    navigating forward.

    Args:
        back_text (str): Display name for this history entry (shown in back
            buttons or breadcrumbs).
        back_label (label, optional): Label to return to. Defaults to the
            currently active label.
    """    
    page = FrameContext.page
    if page is None:
        return
    if back_label is None:
        back_label = page.gui_task.active_label
    

def gui_history_jump(to_label, back_name=None, back_label=None, back_data=None):
    """Jump to a new GUI label and record the current position in navigation history.

    Appends the current position to the back-stack (clearing any forward
    history) then jumps to ``to_label``. Call ``gui_history_back`` to return.

    Args:
        to_label (label): Label to navigate to.
        back_name (str | None, optional): Display name for the back entry.
            Defaults to ``"BACK"``.
        back_label (label | None, optional): Label to return to. Defaults to
            the currently active label.
        back_data (dict | None, optional): Variables to restore when returning
            back. Defaults to None.

    Returns:
        PollResults: Result of the jump.

    Example:
        gui_history_jump(ship_detail_screen, back_name="Ship List")
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
    """Jump back to the previous navigation history entry.

    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no history.

    Example:
        * "Back"
            gui_history_back()
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
    """Jump forward to the next navigation history entry.

    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no forward history.

    Example:
        * "Forward"
            gui_history_forward()
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
    """Clear the navigation history for the current page.

    Removes all back and forward history entries. Call this when entering a
    top-level screen where back-navigation should not be available.

    Example:
        gui_history_clear()
    """
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    task.set_variable("GUI_HISTORY", None)
    task.set_variable("GUI_HISTORY_POS", None)
def gui_history_redirect(back_name=None, back_label=None, back_data=None):
    """Append to navigation history without jumping forward.

    Adds a history entry so the current location can be returned to via
    ``gui_history_back``, but does not change the active label. Use when you
    need to update the back-stack from within a label that was jumped to
    externally (e.g. from a route).

    Args:
        back_name (str | None, optional): Display name for the history entry.
            Defaults to ``"BACK"``.
        back_label (label | None, optional): Label to return to. Defaults to
            the currently active label.
        back_data (dict | None, optional): Variables to restore when returning
            back. Defaults to None.
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

