from sbs_utils.vec import Vec3
def _cosmos_yaw (o):
    """The object's current Cosmos yaw (radians) from its forward vector."""
def _quat_mul (a, b):
    """Hamilton product a*b of two sbs.quaternions (a applied first in world, b in a's local
    frame -- so post-multiplying by a local-axis rotation composes it onto the object)."""
def _rad (v):
    """A 2.8 orientation value in radians -- but authors often entered DEGREES by mistake
    (the scripting parser is degrees everywhere else). Documented radians are -pi..pi; the
    degree mistakes in the corpus are all >= 10, so a magnitude beyond 2*pi (~6.28, safely
    above any pi-rounding like 3.1416) is treated as degrees and converted."""
def _yaw_quat (theta):
    """A pure-yaw rotation quaternion (about +Y) for ``theta`` radians."""
def add_angle (o, d28):
    """2.8 ``addto angle += d``: nudge the facing. The mirror reverses the turn sense, so a
    2.8 clockwise delta ``d`` is a Cosmos yaw of ``-d``."""
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
def copy_angle (src, dst):
    """2.8 ``copy angle src->dst``: copy the (yaw) facing. Both are already in Cosmos space,
    so this copies the Cosmos yaw directly -- no 2.8 conversion."""
def get_angle (o):
    """Read ``o``'s facing back as a 2.8 ``angle`` (radians), inverse of :func:`set_angle`."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
def set_angle (o, a28):
    """Set object ``o``'s facing from a 2.8 ``angle`` (radians): Cosmos yaw = ``pi - a28``."""
def set_pitch (o, p28):
    """2.8 ``pitch`` (nose up/down) -> a pitch composed onto the orientation, about the
    object's LOCAL right (X) axis, preserving facing.
    
    Documented as radians (-pi..pi), but the corpus uses magnitudes beyond pi (10/20/90/120)
    -- the scripting parser is degrees everywhere else, so a magnitude > pi is treated as
    degrees. The X/Z map mirror preserves the vertical (Y is unchanged), so the pitch carries
    over directly."""
def set_roll (o, r28):
    """2.8 ``roll`` (radians, about the forward/nose axis) -> add that roll to the object's
    orientation, about its LOCAL forward (Z) axis, preserving its facing. The X/Z map mirror
    flips the roll sense, so the applied roll is ``-r28`` (pi is sign-invariant -- which is
    all the corpus uses: 180-degree warpgate flips)."""
