from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.gui import Gui
def _gui_reroute_main (label, server):
    ...
def gui_history_back ():
    """Jump back to the previous navigation history entry.
    
    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no history.
    
    Example:
        * "Back"
            gui_history_back()"""
def gui_history_clear ():
    """Clear the navigation history for the current page.
    
    Removes all back and forward history entries. Call this when entering a
    top-level screen where back-navigation should not be available.
    
    Example:
        gui_history_clear()"""
def gui_history_forward ():
    """Jump forward to the next navigation history entry.
    
    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no forward history.
    
    Example:
        * "Forward"
            gui_history_forward()"""
def gui_history_jump (to_label, back_name=None, back_label=None, back_data=None):
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
        gui_history_jump(ship_detail_screen, back_name="Ship List")"""
def gui_history_redirect (back_name=None, back_label=None, back_data=None):
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
            back. Defaults to None."""
def gui_history_store (back_text, back_label=None):
    """Record the current label as a history entry (back destination).
    
    Stores the active label (or ``back_label``) so that ``gui_history_back``
    can return to it later. Use ``gui_history_jump`` instead when also
    navigating forward.
    
    Args:
        back_text (str): Display name for this history entry (shown in back
            buttons or breadcrumbs).
        back_label (label, optional): Label to return to. Defaults to the
            currently active label."""
def gui_reroute_client (client_id, label, data=None):
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
        gui_reroute_client(CLIENT_ID, briefing_screen)"""
def gui_reroute_clients (label, data=None, exclude=None):
    """Jump all connected client GUI tasks to a new label.
    
    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on each task before
            jumping. Defaults to None.
        exclude (set | None, optional): Set of client IDs to skip. Defaults
            to None (no exclusions).
    
    Example:
        gui_reroute_clients(mission_end_screen, exclude={spectator_id})"""
def gui_reroute_server (label, data=None):
    """Jump the server GUI task to a new label.
    
    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.
    
    Example:
        gui_reroute_server(server_status_page)"""
