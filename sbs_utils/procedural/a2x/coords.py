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
