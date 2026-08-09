"""Mounts: weld an object into another object's BODY frame, and let the engine hold it.

A mount is any space object rigidly attached to a host at a fixed offset in the host's own
frame - a weapon turret on a hull, a sensor pod, a parasite craft. Pair it with
:mod:`sbs_utils.procedural.turret` and you have an autonomous weapon mount: the turret
half decides what to shoot, this half decides where it rides. Neither knows about the
other, which is why a tower, a station bolt-on and a ship mount are all the same code.

ENGINE-MEASURED (1.3.5, ``LM_TestRange/maps/test_tractor_mount.mast``): the raw tractor
API holds the target in the source's BODY frame::

    sim.AddTractorConnection(host, mount, sbs.vec3(0, 0, 200), 0)

held a mount at **exactly 200.0u and exactly 0.0 deg off the host's nose while the host's
heading swung 51 deg** - the separation vector rotated with the hull, (0,0,200) ->
(155.5, 0, 125.8). So the ENGINE does the work every frame: no per-tick reposition, no
tick task, and none of the one-frame lag a script-side transform suffers.

**Do not infer this from grav_tether's prose.** It called the offset point "world-fixed",
which was only ever true of the case that module uses - a tow passes no offset, so its
load reels to the host's own position. (`grav_tether_attach`'s own parameter doc said
"point (relative to source)" all along and was right; the surrounding prose was not.)

**Why this does not just wrap ``grav_tether_lock``.** It could: that function passes an
offset straight through with stiffness 0, which is the same weld. But grav_tether runs
``_enforce_impulse`` over every live tether, capping the SOURCE ship back to impulse - so
a ship carrying bolted turrets could never warp. A mount is part of the ship; a tether is
a thing the ship is dragging. Same engine call, opposite intent, and they must not share
a registry: a global ``ClearTractorConnections`` silently unwelded every mount until
``grav_tether_clear_all`` was made to delete only its own connections.

**No module-level state**, deliberately. The engine owns the connection; the host->mount
relationship is an Agent LINK and the per-mount settings live in the mount's own
inventory. ``Agent._remove`` purges both on delete, so nothing here can outlive its
objects and nothing needs a ``register_reset_state`` entry.

Every module-level function is prefixed, private ones included: MAST imports a module's
functions into one flat, mission-wide namespace with no underscore filtering, so a helper
named ``_key`` would turn any script's ``_key = ...`` into a compile error that empties the
whole story.
"""

from ..helpers import FrameContext
from ..lifetimedispatcher import LifetimeDispatcher
from .inventory import get_inventory_value, set_inventory_value
from .links import get_dedicated_link, link, linked_to, set_dedicated_link, unlink
from .query import object_exists, to_id
from .roles import add_role, has_role, role
from .space_objects import delete_object
from .spawn import npc_spawn
from ..vec import Vec3


#: Role every mounted object carries.
MOUNT_ROLE = "__MOUNT__"

#: Link name on the HOST holding all of its mounts (many-to-many).
MOUNT_LINK = "__MOUNT_LIST__"

#: Dedicated (1-to-1) link on the MOUNT pointing back at its host.
MOUNT_HOST_LINK = "__MOUNT_HOST__"

#: pull_distance for the weld. 0 is the typings' "infinite pull, target locked to boss",
#: which is what makes the attachment rigid rather than springy.
MOUNT_RIGID_PULL = 0.0


def _mount_key(name):
    return "mount:" + name


def _mount_sim():
    ctx = FrameContext.context
    return None if ctx is None else ctx.sim


def _mount_vec3(offset):
    """Accept a Vec3, an (x, y, z) tuple, or None -> origin."""
    if offset is None:
        return (0.0, 0.0, 0.0)
    x = getattr(offset, "x", None)
    if x is not None:
        return (float(x), float(getattr(offset, "y", 0.0)), float(getattr(offset, "z", 0.0)))
    return (float(offset[0]), float(offset[1]), float(offset[2]))


def _mount_connect(host_id, mount_id, off):
    """The one place the raw engine call is made."""
    sim = _mount_sim()
    ctx = FrameContext.context
    if sim is None or ctx is None:
        return False
    try:
        sim.AddTractorConnection(host_id, mount_id,
                                 ctx.sbs.vec3(off[0], off[1], off[2]),
                                 MOUNT_RIGID_PULL)
        return True
    except Exception:
        return False


def _mount_disconnect(host_id, mount_id):
    sim = _mount_sim()
    if sim is None:
        return False
    try:
        sim.DeleteTractorConnection(host_id, mount_id)
        return True
    except Exception:
        return False


def mount_attach(host, mount, offset=None, delete_with_host=True):
    """Weld an existing object into the host's body frame.

    Args:
        host (Agent | int): The object to ride on.
        mount (Agent | int): The object to attach.
        offset (Vec3 | tuple, optional): Position in the HOST's own frame -
            ``+z`` forward, ``+x`` right, ``+y`` up. Defaults to the host's center.
        delete_with_host (bool): Delete this mount when the host is destroyed
            (default). Pass False to leave it floating as debris - a blown-off
            turret that can be salvaged.

    Returns:
        int | None: The mount's id, or None if either object is missing or the
            engine refused the connection.
    """
    hid, mid = to_id(host), to_id(mount)
    if hid is None or mid is None or hid == mid:
        return None
    if not object_exists(hid) or not object_exists(mid):
        return None

    off = _mount_vec3(offset)
    if not _mount_connect(hid, mid, off):
        return None

    add_role(mid, MOUNT_ROLE)
    link(hid, MOUNT_LINK, mid)
    set_dedicated_link(mid, MOUNT_HOST_LINK, hid)
    set_inventory_value(mid, _mount_key("offset"), off)
    set_inventory_value(mid, _mount_key("delete_with_host"), bool(delete_with_host))
    return mid


def mount_spawn(host, ship_key, offset=None, name="", side=None,
                behave_id="behav_station", delete_with_host=True):
    """Spawn a new object already welded to the host.

    Spawns at the host's position and lets the weld pull it into place, so the caller
    never has to compute a world position - that is the engine's job now.

    ``behav_station`` is the default because a mount must not steer: a ``behav_npcship``
    would fight the tractor with its own helm.

    Returns:
        int | None: The new mount's id, or None.
    """
    hid = to_id(host)
    if hid is None or not object_exists(hid):
        return None
    sim = _mount_sim()
    if sim is None:
        return None
    try:
        pos = sim.get_space_object(hid).pos
    except Exception:
        return None
    if side is None:
        side = getattr(FrameContext.context.sim.get_space_object(hid), "side", None) or "tsn"
    obj = npc_spawn(pos.x, pos.y, pos.z, name, side, ship_key, behave_id)
    mid = to_id(obj)
    if mid is None:
        return None
    if mount_attach(hid, mid, offset, delete_with_host) is None:
        delete_object(mid)
        return None
    return mid


def mount_ring(host, ship_key, count, radius=None, y=0.0, **kwargs):
    """Spawn ``count`` mounts evenly spaced on a ring in the host's body XZ plane.

    The common case for bolting turrets onto a hull or a station. Because the offsets are
    body-frame, a station host and a maneuvering ship host behave identically.

    Args:
        radius (float, optional): Ring radius. Defaults to a little outside the host's
            exclusion radius so the mounts sit clear of the hull.

    Returns:
        list[int]: The ids created (may be shorter than ``count`` if any failed).
    """
    import math
    hid = to_id(host)
    if hid is None or count <= 0:
        return []
    if radius is None:
        radius = 60.0
        try:
            er = _mount_sim().get_space_object(hid).exclusion_radius
            if er:
                radius = float(er) * 1.2
        except Exception:
            pass
    out = []
    for i in range(int(count)):
        a = (2.0 * math.pi * i) / float(count)
        off = (radius * math.sin(a), y, radius * math.cos(a))
        mid = mount_spawn(hid, ship_key, off, **kwargs)
        if mid is not None:
            out.append(mid)
    return out


def mount_detach(host, mount, delete=False):
    """Release a mount. Optionally delete it.

    Deletion goes through the procedural ``delete_object`` (deferred) rather than the
    engine call, which frees the C++ object synchronously and would leave anything still
    holding it pointing at freed memory.
    """
    hid, mid = to_id(host), to_id(mount)
    if mid is None:
        return None
    if hid is None:
        hid = mount_host_of(mid)
    if hid is not None:
        _mount_disconnect(hid, mid)
        unlink(hid, MOUNT_LINK, mid)
    set_dedicated_link(mid, MOUNT_HOST_LINK, None)
    if delete:
        delete_object(mid)
    return mid


def mount_detach_all(host, delete=None):
    """Release every mount on a host.

    Args:
        delete (bool, optional): Force-delete (True) or force-keep (False) every mount.
            Defaults to None, meaning honor each mount's own ``delete_with_host``
            setting - which is what the host-destroyed path wants.

    Returns:
        list[int]: The mounts released.
    """
    hid = to_id(host)
    if hid is None:
        return []
    out = []
    for mid in list(mount_list(hid)):
        want = delete
        if want is None:
            want = bool(get_inventory_value(mid, _mount_key("delete_with_host"), True))
        mount_detach(hid, mid, want)
        out.append(mid)
    return out


def mount_list(host):
    """Every mount currently welded to a host, as a list of ids."""
    hid = to_id(host)
    if hid is None:
        return []
    # Filter dead ids: a link can outlive the object it points at, and handing a freed id
    # back to a caller that then repositions or deletes it is the synchronous-UAF trap.
    return [mid for mid in (linked_to(hid, MOUNT_LINK) or ()) if object_exists(mid)]


def mount_host_of(mount):
    """The host a mount rides on, or None.

    A host that no longer exists reads as None rather than a dangling id. The destroy
    dispatch cleans up ships killed in COMBAT, but a script can also just delete a ship
    outright, and that path fires no destroy event - so "my host is gone" has to be
    answerable from the link alone.
    """
    mid = to_id(mount)
    if mid is None:
        return None
    hid = get_dedicated_link(mid, MOUNT_HOST_LINK)
    if hid is None or not object_exists(hid):
        return None
    return hid


def mount_prune_orphans(delete=None):
    """Release mounts whose host is gone, honoring each one's ``delete_with_host``.

    The destroy dispatch covers a host killed in combat. This covers the other way a host
    vanishes - a script deleting it - which fires no destroy event and would otherwise
    leave armed objects welded to nothing.

    Returns:
        list[int]: The orphans dealt with.
    """
    out = []
    for mid in list(role(MOUNT_ROLE)):
        if not object_exists(mid):
            continue
        hid = get_dedicated_link(mid, MOUNT_HOST_LINK)
        if hid is None or object_exists(hid):
            continue
        want = delete
        if want is None:
            want = bool(get_inventory_value(mid, _mount_key("delete_with_host"), True))
        set_dedicated_link(mid, MOUNT_HOST_LINK, None)
        if want:
            delete_object(mid)
        out.append(mid)
    return out


def mount_is(obj):
    """Whether an object is currently mounted on something."""
    return has_role(obj, MOUNT_ROLE) and mount_host_of(obj) is not None


def mount_offset(host, mount):
    """The body-frame offset a mount was welded at, as a Vec3."""
    mid = to_id(mount)
    if mid is None:
        return None
    off = get_inventory_value(mid, _mount_key("offset"), None)
    return None if off is None else Vec3(off[0], off[1], off[2])


def mount_set_offset(host, mount, offset):
    """Move a mount to a new body-frame offset.

    The engine's connection carries its offset point from creation, so this deletes and
    re-adds it - cheap, and the only way to change where a mount rides.
    """
    hid, mid = to_id(host), to_id(mount)
    if mid is None:
        return None
    if hid is None:
        hid = mount_host_of(mid)
    if hid is None or not object_exists(hid) or not object_exists(mid):
        return None
    off = _mount_vec3(offset)
    _mount_disconnect(hid, mid)
    if not _mount_connect(hid, mid, off):
        return None
    set_inventory_value(mid, _mount_key("offset"), off)
    return Vec3(off[0], off[1], off[2])


def mount_count():
    """How many welded mounts exist. Cheap probe for tests and diagnostics."""
    return len(_mount_all_mounted())


def _mount_all_mounted():
    # object_exists as well as the link: an object freed by the engine can leave a stale
    # entry in the class-level role registry, and counting that would report a weld that
    # is not holding anything. Same hazard the brain runner guards against by id.
    return {mid for mid in role(MOUNT_ROLE)
            if object_exists(mid) and mount_host_of(mid) is not None}


def mount_clear_all():
    """Release every mount without deleting anything.

    There is no module-level registry to clear - the relationships live on the agents
    themselves and are purged with them - so this is for tests, for a mid-mission clean
    slate, and for reset_mission_state to drop the ENGINE-side welds deliberately.

    Tolerates having no frame context: a reset can fire with none, and dropping our own
    state must never depend on the engine being there.
    """
    try:
        mounted = list(_mount_all_mounted())
    except Exception:
        return
    for mid in mounted:
        try:
            mount_detach(None, mid, delete=False)
        except Exception:
            pass


def _mount_on_destroy(destroyed, damage_event=None):
    """Host destroyed -> release its mounts, honoring each one's delete_with_host.

    Registered with LifetimeDispatcher so it reacts in the same handler the destruction
    is routed in, rather than a tick later with a dangling weld.
    """
    hid = to_id(destroyed)
    if hid is None:
        return
    if mount_list(hid):
        mount_detach_all(hid, delete=None)
    # A destroyed MOUNT just stops being one; its links go with the agent.
    host = mount_host_of(hid)
    if host is not None:
        unlink(host, MOUNT_LINK, hid)


LifetimeDispatcher.add_destroy(_mount_on_destroy)
