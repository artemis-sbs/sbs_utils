from sbs_utils.helpers import FrameContext
def gui_options_button (transparent=True, client_id=None):
    """Make the engine Options button transparent (or normal) for a client, and
    keep it that way across page rebuilds.
    
    Prefer this over calling ``sbs.transparent_options_button`` directly: the raw
    call is undone by the next page build.
    
    Args:
        transparent (bool, optional): ``True`` to make the button transparent,
            ``False`` to restore it. Defaults to ``True``.
        client_id (int, optional): The client to set it for. Defaults to the
            client of the current frame.
    
    Example:
        gui_options_button()            # this console's button, transparent
        gui_options_button(False)       # put it back"""
def gui_options_button_clear (client_id=None):
    """Forget the recorded intent (all clients when client_id is None), so the
    button returns to the default on the next rebuild. For a client that
    disconnected, and for tests."""
def gui_options_button_flag (client_id):
    """The flag a mission last asked for on this client, or 0 if it never did.
    
    Used by StoryPage.on_new_gui to restore the button to what the mission
    wanted rather than to a hardcoded 0."""
