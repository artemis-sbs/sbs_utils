"""Legacy-style condition helpers for 2.8 ``if_*`` tests that have no one-line core
equivalent.

Many 2.8 conditions map directly to existing core functions in the generated MAST
(``if_inside_sphere`` -> ``distance_point_less`` with ``a2x_pos`` on the centre,
``if_exists`` -> ``object_exists``), so they need no helper here. The exceptions:

  * ``if_docked`` -- reads the ship's ``dock_state``.
  * ``if_distance`` in a *polling loop* -- the core ``distance_less``/``distance_greater``
    are awaitable promises, not booleans, and a raw ``sbs.distance_id`` call errors when
    an object has been destroyed. :func:`distance_less` / :func:`distance_greater` here
    are the boolean, destroyed-object-safe form.
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


def within(obj, x, y, z, radius):
    """True if ``obj`` is within ``radius`` of a 2.8-coord point (flipped internally).

    A boolean for polling loops (2.8 if_distance-to-point / if_inside_sphere).
    """
    from sbs_utils.procedural.query import to_space_object

    o = to_space_object(obj)
    if o is None:
        return False
    p = o.engine_object.pos
    c = pos(x, y, z)
    return ((p.x - c.x) ** 2 + (p.y - c.y) ** 2 + (p.z - c.z) ** 2) ** 0.5 <= radius


def _distance_between(obj1, obj2):
    """Distance between two objects, or ``None`` if either is missing/destroyed.

    ``sbs.distance_id`` errors ("was sent None") for an id that is None or refers to
    a deleted object, and ``to_id`` passes both straight through -- so resolve to live
    objects first. Callers turn ``None`` into a False condition.
    """
    from sbs_utils.procedural.query import to_space_object
    from sbs_utils.helpers import FrameContext

    a = to_space_object(obj1)
    b = to_space_object(obj2)
    if a is None or b is None:
        return None
    return FrameContext.context.sbs.distance_id(a.id, b.id)


def distance_less(obj1, obj2, radius):
    """2.8 ``if_distance`` (LESS) as a live boolean for polling loops.

    False when either object is missing or destroyed -- a 2.8 condition about an
    object that does not exist simply never fires.
    """
    d = _distance_between(obj1, obj2)
    return d is not None and d < radius


def distance_greater(obj1, obj2, radius):
    """2.8 ``if_distance`` (GREATER) as a live boolean for polling loops.

    Also False when either object is missing or destroyed: a destroyed object is
    not "infinitely far away", it is untestable, so the condition should not fire.
    """
    d = _distance_between(obj1, obj2)
    return d is not None and d > radius


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
