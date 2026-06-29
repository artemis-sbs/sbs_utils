"""Legacy-style condition helpers for 2.8 ``if_*`` tests that have no one-line core
equivalent.

Most 2.8 conditions map directly to existing core functions in the generated MAST
(``if_distance`` -> ``distance_less``, ``if_inside_sphere`` -> ``distance_point_less``
with ``a2x_pos`` on the centre, ``if_exists`` -> ``object_exists``), so they need no
helper here. ``if_docked`` is the exception: it reads the ship's ``dock_state``.
"""

from .coords import pos  # noqa: F401  (re-exported convenience for callers)


def is_docked(ship, station=None):
    """2.8 ``if_docked``: True if ``ship`` is currently docked.

    The engine stores ``dock_state`` as ``"undocked"`` when not docked (otherwise a
    docked marker / station). ``station`` is accepted for call-site parity with 2.8
    but not matched -- Cosmos dock state is effectively boolean here.
    """
    from sbs_utils.procedural.query import get_data_set_value, to_id

    ds = get_data_set_value(to_id(ship), "dock_state")
    # docked == a non-empty docked marker; unset (None/0/"") or "undocked" => not docked
    return isinstance(ds, str) and ds not in ("", "undocked")


def in_box(obj, least_x, least_z, most_x, most_z, inside=True):
    """2.8 ``if_inside_box`` / ``if_outside_box`` (an XZ rectangle).

    The corners are converted from 2.8 to Cosmos coordinates (the 180-degree XZ
    mirror), so the test is correct in Cosmos space. Returns ``inside`` semantics
    by default; pass ``inside=False`` for the outside test.
    """
    from sbs_utils.procedural.query import to_space_object

    o = to_space_object(obj)
    if o is None:
        return not inside
    p = o.engine_object.pos
    c1 = pos(least_x, 0, least_z)
    c2 = pos(most_x, 0, most_z)
    lo_x, hi_x = min(c1.x, c2.x), max(c1.x, c2.x)
    lo_z, hi_z = min(c1.z, c2.z), max(c1.z, c2.z)
    within = (lo_x <= p.x <= hi_x) and (lo_z <= p.z <= hi_z)
    return within if inside else not within
