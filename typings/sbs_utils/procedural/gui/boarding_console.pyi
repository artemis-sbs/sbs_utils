from sbs_utils.helpers import FrameContext
def _client (client_id=None):
    ...
def boarding_app_area ():
    """The app area's absolute area - the bar's bottom edge, down to the screen's.
    
    Paired with :func:`boarding_identity_area` by construction: they share `APP_TOP_PX`,
    so they are adjacent and cannot overlap however the screen is sized. The old pair of
    regions needed a reserve row to keep the flow out of them; this one has no flow under
    it to keep out."""
def boarding_console_revision (client_id=None):
    """A value that changes when anything on this console's screen should change.
    
    What an `on change` watches. Per CONSOLE, not global: one crew member answering a
    choice must not repaint the other five screens, and a shared counter would.
    
    THE DEVICE IS PART OF THIS SCREEN. Without its revision here, opening an app changed
    the stored state and nothing ever repainted - the `on change` never moved, so the
    tick never ran and the tiles "did nothing"."""
def boarding_identity_area ():
    """The identity bar's absolute area."""
def boarding_panel_width (map_width):
    """Set how much of the screen the map takes, and return the device's left edge.
    
    Public because there is more than one console now: the EVA console puts a `3dview`
    where this one puts `ship_internal_view`, and both hand their width to the SAME two
    area functions the device reads. Without one call that sets it, the second console
    draws its map at one width and its device at the other's."""
def gui_boarding_console (client_id=None, map_width=66, on_leave=None):
    """Build the crew console: the interior on the left, the xESS on the right.
    
    Args:
        client_id (optional): the console. Defaults to the page's own.
        map_width (int, optional): how much of the screen the interior takes, in percent.
        on_leave (optional): ignored, and kept so a mission that passed it still runs.
            Leaving is the CREW app's Beam up now, which calls `boarding_go_up` - there
            is no longer a button on every screen to hand a handler to.
    
    Returns:
        dict: the held widgets, also stored on the page for
        :func:`gui_boarding_console_tick`."""
def gui_boarding_console_tick ():
    """Refresh the crew console in place. What an `on change` should CALL.
    
    Never `jump` back to the screen label instead: that re-sends every widget on the
    screen over the network to that console, and does it again on the next change,
    forever.
    
    Returns:
        bool: False when the screen is gone - a handler can outlive the page that
        registered it, and this is called from one."""
def panel_left ():
    """The device column's left edge, matching whatever map width was last built."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def where_text (client_id):
    """The room this console's character is standing in, in words.
    
    Public because the device's identity bar shows it and the two must not each work it
    out - a bar that disagrees with the map about which room you are in is worse than one
    that says nothing."""
