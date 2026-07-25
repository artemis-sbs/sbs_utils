"""Coordinate / heading conversion from Artemis 2.8 to Cosmos.

**The coordinate flip.** Artemis 2.8 uses a corner-origin map: x,z in 0..100000 with
the origin at a corner, y vertical. Cosmos uses the same 0..100000 footprint but with
x and z mirrored about the map centre (50000) -- a 180 degree rotation in the
horizontal plane. y is identical in both. This is exactly ``Vec3.from2x_coord``::

    Vec3.from2x_coord(x, y, z) -> Vec3(100000 - x, y, 100000 - z)

So every 2.8 position must be passed through :func:`pos`, and every 2.8 heading
through :func:`angle`, when porting.
"""

from sbs_utils.vec import Vec3

# The 2.8 map is a square of this size; the flip mirrors about its centre.
A2X_MAP_SIZE = 100_000


def pos(x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.

    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::

        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)

    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.

    Returns:
        Vec3: the equivalent Cosmos position.
    """
    return Vec3.from2x_coord(x, y, z)


def angle(deg):
    """Convert a 2.8 heading (degrees) to the equivalent Cosmos heading (degrees).

    The horizontal-plane mirror is a 180 degree yaw rotation, so a heading vector is
    negated -- i.e. the converted heading is ``(deg + 180) mod 360``. This accounts
    for the flip itself; if a given mission also needs a handedness correction it is
    a per-mission ``# TODO verify heading`` (Cosmos vs 2.8 zero-reference), not
    something this function can know.

    Args:
        deg (float): a heading in Artemis 2.8 degrees (0..360).

    Returns:
        float: the equivalent Cosmos heading in degrees, in [0, 360).
    """
    return (float(deg) + 180.0) % 360.0


# --- the 2.8 `angle` object property (a ship's absolute facing) ---------------------
#
# 2.8 `angle` is the yaw of a ship in RADIANS, clockwise from south (0=south, +pi/2=west,
# pi/-pi=north, -pi/2=east). Cosmos stores facing as the engine object's rotation
# quaternion; a pure yaw of theta radians gives forward_vector (sin theta, 0, cos theta).
#
# The map's X/Z mirror (see `pos`) flips a facing the same way it flips a position. Working
# it through against the CONFIRMED 2.8 axes (East=+X, North=-Z, from the dir_throttle
# check): a 2.8 facing at angle a is (-sin a, 0, cos a) in 2.8 space, which mirrors to
# (sin a, 0, -cos a) in Cosmos = a Cosmos yaw of **theta = pi - a**. Verified against the
# engine forward_vector for all four cardinals. Because the mirror reverses handedness, a
# 2.8 CW nudge (`addto angle += d`) becomes a Cosmos yaw of **-d**.


def _yaw_quat(theta):
    """A pure-yaw rotation quaternion (about +Y) for ``theta`` radians."""
    import sbs
    import math
    h = theta / 2.0
    return sbs.quaternion(math.cos(h), 0.0, math.sin(h), 0.0)


def _cosmos_yaw(o):
    """The object's current Cosmos yaw (radians) from its forward vector."""
    import math
    f = o.engine_object.forward_vector()
    return math.atan2(f.x, f.z)


def set_angle(o, a28):
    """Set object ``o``'s facing from a 2.8 ``angle`` (radians): Cosmos yaw = ``pi - a28``."""
    import math
    o.engine_object.rot_quat = _yaw_quat(math.pi - float(a28))


def get_angle(o):
    """Read ``o``'s facing back as a 2.8 ``angle`` (radians), inverse of :func:`set_angle`."""
    import math
    a = math.pi - _cosmos_yaw(o)
    return (a + math.pi) % (2 * math.pi) - math.pi   # normalize to (-pi, pi]


def add_angle(o, d28):
    """2.8 ``addto angle += d``: nudge the facing. The mirror reverses the turn sense, so a
    2.8 clockwise delta ``d`` is a Cosmos yaw of ``-d``."""
    o.engine_object.rot_quat = _yaw_quat(_cosmos_yaw(o) - float(d28))


def copy_angle(src, dst):
    """2.8 ``copy angle src->dst``: copy the (yaw) facing. Both are already in Cosmos space,
    so this copies the Cosmos yaw directly -- no 2.8 conversion."""
    dst.engine_object.rot_quat = _yaw_quat(_cosmos_yaw(src))


def _quat_mul(a, b):
    """Hamilton product a*b of two sbs.quaternions (a applied first in world, b in a's local
    frame -- so post-multiplying by a local-axis rotation composes it onto the object)."""
    import sbs
    aw, ax, ay, az = a.w, a.x, a.y, a.z
    bw, bx, by, bz = b.w, b.x, b.y, b.z
    return sbs.quaternion(
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw)


def set_roll(o, r28):
    """2.8 ``roll`` (radians, about the forward/nose axis) -> add that roll to the object's
    orientation, about its LOCAL forward (Z) axis, preserving its facing. The X/Z map mirror
    flips the roll sense, so the applied roll is ``-r28`` (pi is sign-invariant -- which is
    all the corpus uses: 180-degree warpgate flips)."""
    import sbs
    import math
    h = -float(r28) / 2.0
    roll_q = sbs.quaternion(math.cos(h), 0.0, 0.0, math.sin(h))   # about local +Z (forward)
    o.engine_object.rot_quat = _quat_mul(o.engine_object.rot_quat, roll_q)
