from ...helpers import FrameContext

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

