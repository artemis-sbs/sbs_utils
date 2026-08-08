"""Naming a PLACE, so a job can say where its work is.

"I have no idea what asteroids this refers to, or where the shipping lane is" (PRM-10).
The description could not say, because nothing knew: targets are scattered at runtime, so
prose written at authoring time can only name coordinates that go stale the moment the
spawn changes - and there is no position-to-sector-name helper anywhere.

The answer is to put a real object in the world rather than a phrase in the text, so the
place is on the map where the crew is already looking. Three kinds, because they answer
different questions:

    marker_area    a REGION - "the shipping lane", "the asteroid field". A navarea, drawn
                   as a quad on the 2D map.
    marker_point   a SPOT - "the rendezvous". A navpoint, a labelled dot.
    marker_object  a spot the crew must SELECT (to scan it, to comms it, to fly to it).
                   A real space object, built the way the nebula cluster marker is:
                   invisible on the main screen, gold on radar, `behav_selection`.

Nothing here is per-mission module state: navpoints live in the sim (rebuilt per mission)
and marker objects are agents (cleared with every other agent), so there is nothing for
the reset ledger to hold.
"""
from ..helpers import FrameContext
from .query import to_id, to_object


MARKER_COLOR = "#0cf"
# What a selectable marker looks like on radar. Gold because that is what the nebula
# cluster marker already uses, and two kinds of map furniture that mean "look here"
# should not disagree about their color.
MARKER_RADAR_COLOR = "gold"


def marker_point(x, y, z, text, color=MARKER_COLOR):
    """A labelled dot on the map. Returns its navpoint id."""
    sim = FrameContext.context.sim
    return sim.add_navpoint(x, y, z, str(text), color)


def marker_area(x, y, z, size_x, size_z=None, text="", color="#0cf4"):
    """A labelled REGION on the map, centered on (x, z) - the shape a job means by "the
    shipping lane" or "the asteroid field". Returns its navarea id.

    `size_x`/`size_z` are the FULL width and depth, not half-extents, so they match the
    scatter box a job spawns its targets into: pass the same numbers and the marker
    covers exactly what was placed inside it.

    The four corners are given in the order the engine expects; the y coordinate is
    unused (a navarea is a ground-plane quad) and is accepted only so the call site can
    pass the same centre it spawned around.
    """
    sim = FrameContext.context.sim
    if size_z is None:
        size_z = size_x
    hx, hz = size_x / 2.0, size_z / 2.0
    return sim.add_navarea(x - hx, z - hz, x + hx, z - hz,
                           x - hx, z + hz, x + hx, z + hz, str(text), color)


def marker_object(x, y, z, text, roles="", color=MARKER_RADAR_COLOR):
    """A SELECTABLE marker - a real object the crew can click, scan or hail.

    Built the way the nebula cluster marker is (terrain.py): `behav_selection` so it can
    be selected, `elite_main_scn_invis` so it does not hang in space on the main screen,
    and a radar color so it reads as map furniture rather than as a contact.

    `roles` are added on top of `map,marker` - a job marks its own with its own role so
    it can find and remove them later.
    """
    from .spawn import terrain_spawn
    extra = ("," + str(roles).strip(",").strip()) if roles else ""
    obj = terrain_spawn(x, y, z, str(text), f"#,map,marker{extra}",
                        "generic-sphere", "behav_selection")
    obj.data_set.set("elite_main_scn_invis", 1, 0)
    obj.data_set.set("radar_color_override", color, 0)
    return obj


def marker_delete(handle):
    """Remove a marker: the id from marker_point/marker_area, or what marker_object
    returned. Safe to call twice, and safe on either kind.

    A navpoint id and an agent id are both plain ints, so this tries the navpoint
    registry first and falls through to the object - guessing from the type would delete
    the wrong thing exactly when a mission holds both.
    """
    if handle is None:
        return
    sim = FrameContext.context.sim
    ident = getattr(handle, "id", handle)
    if isinstance(ident, int):
        try:
            if sim.navpoint_exists(ident):
                sim.delete_navpoint_by_id(ident)
                return
        except Exception:
            pass
    obj = to_object(ident)
    if obj is not None:
        obj.delete_object()


def marker_delete_role(role_name):
    """Remove every marker OBJECT carrying `role_name` - how a job clears its own
    markers when it completes. Navpoints are not roles and are removed by id."""
    from .roles import role
    from .query import to_object_list
    count = 0
    for obj in to_object_list(role(role_name)):
        obj.delete_object()
        count += 1
    return count
