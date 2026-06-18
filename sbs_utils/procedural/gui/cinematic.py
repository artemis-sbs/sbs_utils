from ...helpers import FrameContext
from ..style import apply_control_styles

def gui_cinematic_auto(client_id):
    """Switch a client to cinematic view, automatically tracking its assigned ship.

    Sets the client's view mode to ``"3dview/front/cinematic"`` with automatic
    camera control. The tracked ship must expose excitement values; player ships
    have these set automatically.

    Args:
        client_id (int): The client to switch to cinematic view.

    Example:
        gui_cinematic_auto(CLIENT_ID)
    """
    SBS = FrameContext.context.sbs
    no_offset = SBS.vec3()
    SBS.set_main_view_modes(client_id, "3dview", "front", "cinematic")
    SBS.cinematic_control(client_id, 0, 0, no_offset, 0, no_offset)

def gui_cinematic_full_control(client_id, camera_id, camera_offset, tracked_id, tracked_offset):
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
        gui_cinematic_full_control(CLIENT_ID, camera_ship_id, Vec3(0,50,0), target_id, None)
    """
    SBS = FrameContext.context.sbs
    if camera_offset is not None:
        _camera_offset = SBS.vec3()
        _camera_offset.x = camera_offset.x
        _camera_offset.y = camera_offset.y
        _camera_offset.z = camera_offset.z
        camera_offset = _camera_offset
    #else:
    #     camera_offset = sbs.vec3()
    if tracked_offset is not None:
        _offset = SBS.vec3()
        _offset.x = tracked_offset.x
        _offset.y = tracked_offset.y
        _offset.z = tracked_offset.z
        tracked_offset = _offset
    # else:
    #     tracked_offset = sbs.vec3()

    SBS.set_main_view_modes(client_id, "3dview", "front", "cinematic")
    SBS.cinematic_control(client_id, 1, camera_id, camera_offset, tracked_id, tracked_offset)


