from sbs_utils.helpers import FrameContext
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def gui_cinematic_auto (client_id):
    """Switch a client to cinematic view, automatically tracking its assigned ship.
    
    Sets the client's view mode to ``"3dview/front/cinematic"`` with automatic
    camera control. The tracked ship must expose excitement values; player ships
    have these set automatically.
    
    Args:
        client_id (int): The client to switch to cinematic view.
    
    Example:
        gui_cinematic_auto(CLIENT_ID)"""
def gui_cinematic_full_control (client_id, camera_id, camera_offset, tracked_id, tracked_offset):
    """Switch a client to cinematic view with explicit camera and target control.
    
    Sets the view mode to ``"3dview/front/cinematic"`` and hands full camera
    control to the caller. Both offset vectors are converted to engine
    ``vec3`` objects before being passed to ``cinematic_control``.
    
    Args:
        client_id (int): The client to switch to cinematic view.
        camera_id (int): Object ID to use as the camera position anchor.
        camera_offset (Vec3 | None): Offset from ``camera_id`` in world units.
            Pass ``None`` to use the object's origin.
        tracked_id (int): Object ID for the camera to look at.
        tracked_offset (Vec3 | None): Offset from ``tracked_id`` to look at.
            Pass ``None`` to use the object's origin.
    
    Example:
        gui_cinematic_full_control(CLIENT_ID, camera_ship_id, Vec3(0,50,0), target_id, None)"""
