from sbs_utils.helpers import FrameContext
def _assign (client_id, ship):
    """Seat the console on the suit. Quiet when there is no engine to tell."""
def _client (client_id=None):
    ...
def _ride_camera (client_id):
    """Point this console's main view at the suit it is assigned to.
    
    `cinematic` goes through `gui_cinematic_auto` because that mode needs its
    `cinematic_control` call as well as the view mode; everything else is the plain view
    mode, which is what keeps the camera still."""
def eva_camera_mode (mode=None):
    """Read, or set, the camera every EVA console rides.
    
    Args:
        mode (str, optional): `third` (ours - see `eva_camera.py`), or one of the engine's
            own: `chase`, `first_person`, `tracking`, `cinematic`. Omit to read the
            current one.
    
    Returns:
        str: the mode in force."""
def eva_console_revision (client_id=None):
    """A value that changes when anything on this console's screen should change.
    
    Per CONSOLE, not global: one boarder arriving somewhere must not repaint the other
    five screens.
    
    THE SUIT'S DESTINATION IS IN HERE through the device's own revision - `xess_revision`
    folds in every app's badge, and NAV's badge carries the distance left to run. Without
    that the screen would freeze the moment a destination was picked and never show the
    suit arriving."""
def eva_radar_area (map_width=None):
    """The corner radar's absolute area, tucked into the view's bottom-right.
    
    Measured off the SAME map width the 3D view uses, so the two cannot drift apart when
    a console is built at a different width."""
def gui_eva_console (client_id=None, map_width=66, suit=None, radar=True):
    """Build the EVA console: the relic on the left, the xESS on the right.
    
    Args:
        client_id (optional): the console. Defaults to the page's own.
        map_width (int, optional): how much of the screen the view takes, in percent.
        suit (optional): the ship to ride. Defaults to the one this console was given by
            :func:`eva_take`.
        radar (bool, optional): draw the corner 2D view over the 3D one. Defaults True.
    
    Returns:
        dict: the held widgets, also stored on the page for :func:`gui_eva_console_tick`."""
def gui_eva_console_tick ():
    """Refresh the EVA console in place. What an `on change` should CALL.
    
    Returns:
        bool: False when the screen is gone - a handler can outlive the page that
        registered it, and this is called from one."""
