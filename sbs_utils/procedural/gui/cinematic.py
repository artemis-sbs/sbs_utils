from ...helpers import FrameContext
from ..style import apply_control_styles

def gui_cinematic_auto(client_id):
    """Will automatically track the consoles assigned ship

    ??? Note:
        The tracked ship needs to have excitement values 
        player ships automatically have that set    
    
    Args:
        client_id (id): the console's client ID
    """
    SBS = FrameContext.context.sbs
    no_offset = SBS.vec3()
    SBS.set_main_view_modes(client_id, "3dview", "front", "cinematic")
    SBS.cinematic_control(client_id, 0, 0, no_offset, 0, no_offset)

def gui_cinematic_full_control(client_id, camera_id, camera_offset, tracked_id, tracked_offset):
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


