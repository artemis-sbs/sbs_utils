from sbs_utils.vec import Vec3
def angle (deg):
    """Convert a 2.8 heading (degrees) to the equivalent Cosmos heading (degrees).
    
    The horizontal-plane mirror is a 180 degree yaw rotation, so a heading vector is
    negated -- i.e. the converted heading is ``(deg + 180) mod 360``. This accounts
    for the flip itself; if a given mission also needs a handedness correction it is
    a per-mission ``# TODO verify heading`` (Cosmos vs 2.8 zero-reference), not
    something this function can know.
    
    Args:
        deg (float): a heading in Artemis 2.8 degrees (0..360).
    
    Returns:
        float: the equivalent Cosmos heading in degrees, in [0, 360)."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
