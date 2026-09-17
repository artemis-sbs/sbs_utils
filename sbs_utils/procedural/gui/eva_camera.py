"""The EVA console's camera: third person, close behind, and never in the rock.

WHY THIS IS NOT `set_main_view_modes`. That call is the whole of the engine's own camera
vocabulary - four angles (`front`/`back`/`left`/`right`) and three modes (`first_person`/
`chase`/`tracking`) - and it exposes **no distance, no orbit and no clamp**. The engine
picks the shot. Outside, framing a cruiser, that is fine. Inside a relic it is not: a
chase lens holds station some way behind its subject, a relic shaft is 380 units across,
and the lens spends the flight inside the wall looking at the back of a rock.

So the lens is ours. `camera_follow` puts it where we say, on the console's own tick, and
three things decide where that is:

* **the heading**, so it reads as third person and you can see where you are going;
* **the room actually available**, measured with the relic's own SDF - the same geometry
  the autopilot flies by. In a hall the lens sits well back; in a shaft it comes in over
  the suit's shoulder, because there is nowhere else for it to be;
* **speed**, so it dollies IN as the suit gets going. A camera that hangs back while
  something accelerates reads as slow; one that closes reads as fast, and it is free.

And a hard backstop under all of it: whatever the angles ask for, the lens is walked back
along its own sightline until it is inside the volume. That is the one thing the engine's
chase cannot do, and it is the reason this file exists.

Per console, always. Six consoles fly six suits in one relic, so orbit and dolly belong to
the client exactly as the suit does.
"""
from ..inventory import get_inventory_value, set_inventory_value
from ..query import to_object
from ..volume import volume_depth, volume_inside, volume_nearest_inside
from .camera import camera_auto, camera_follow

#: Per-console camera state, beside the other `EVA_*` client keys.
KEY_YAW = "EVA_CAM_YAW"
KEY_PITCH = "EVA_CAM_PITCH"
KEY_DIST = "EVA_CAM_DIST"      # a manual override, or None for the automatic distance
KEY_FREE = "EVA_CAM_FREE"      # True once a console has orbited deliberately

#: How far behind the suit the lens sits with everything wide open, and the range the
#: automatic distance is allowed to move it through.
#:
#: A SUIT IS A PERSON, so these are small. The old engine chase framed a ship.
CAM_BASE = 90.0
CAM_MIN = 26.0
CAM_MAX = 190.0

#: How far above the suit the lens rides, as a fraction of the distance. Enough to look
#: down the line of flight rather than at the back of the helmet.
CAM_RISE = 0.22

#: The clearance at which the lens is allowed its full distance. Below it the lens comes
#: in proportionally - which is what keeps it out of a shaft wall before the hard clamp
#: has to.
CAM_ROOM_FULL = 320.0

#: How far inside the wall the lens must stay. Smaller than the suit's own route margin:
#: a camera clipping a wall looks wrong, but a camera that refuses to come close enough
#: to see anything is worse.
CAM_MARGIN = 8.0

#: How much of the distance speed takes away. At full cruise the lens sits this fraction
#: closer than it would standing still.
CAM_SPEED_PULL = 0.35

#: How far one press of the orbit control turns the lens, and one press of the dolly
#: control moves it.
CAM_YAW_STEP = 24.0
CAM_DOLLY_STEP = 30.0

#: Default tilt, above the suit's own plane.
CAM_PITCH = 10.0

#: How quickly a manual yaw washes out once the suit is under way again, in degrees per
#: tick. A console that orbited to look at something should not have to put the camera
#: back by hand before it can fly - but one that LOCKED the view has said it means it.
CAM_YAW_DECAY = 3.0

#: How many steps the lens clamp takes walking itself back inside. Eight halvings resolve
#: a 200-unit pull to under a unit, which is far finer than anybody can see.
CAM_CLAMP_STEPS = 8


def eva_camera_state(client_id):
    """``(yaw, pitch, distance_or_None, free)`` for one console."""
    return (float(get_inventory_value(client_id, KEY_YAW, 0.0) or 0.0),
            float(get_inventory_value(client_id, KEY_PITCH, CAM_PITCH) or 0.0),
            get_inventory_value(client_id, KEY_DIST, None),
            bool(get_inventory_value(client_id, KEY_FREE, False)))


def eva_camera_orbit(client_id, degrees=CAM_YAW_STEP):
    """Turn the lens around the suit. Marks the view as deliberately placed, so it stops
    washing back to dead astern on its own."""
    yaw = float(get_inventory_value(client_id, KEY_YAW, 0.0) or 0.0) + float(degrees)
    yaw = ((yaw + 180.0) % 360.0) - 180.0
    set_inventory_value(client_id, KEY_YAW, yaw)
    set_inventory_value(client_id, KEY_FREE, True)
    return yaw


def eva_camera_tilt(client_id, degrees=8.0):
    """Raise or lower the lens. Clamped short of straight up or down, where a chase has no
    usable horizon and the shot reads as a map."""
    pitch = float(get_inventory_value(client_id, KEY_PITCH, CAM_PITCH) or 0.0) + \
        float(degrees)
    pitch = max(-60.0, min(75.0, pitch))
    set_inventory_value(client_id, KEY_PITCH, pitch)
    set_inventory_value(client_id, KEY_FREE, True)
    return pitch


def eva_camera_dolly(client_id, amount=CAM_DOLLY_STEP):
    """Push the lens in or pull it out, and hold it there.

    Taking manual control of the distance turns OFF the automatic framing - a console that
    asked for a distance should get it, not have the clearance rule quietly argue with it.
    `eva_camera_recenter` gives the automatic framing back.
    """
    now = get_inventory_value(client_id, KEY_DIST, None)
    if now is None:
        now = CAM_BASE
    dist = max(CAM_MIN, min(CAM_MAX, float(now) + float(amount)))
    set_inventory_value(client_id, KEY_DIST, dist)
    set_inventory_value(client_id, KEY_FREE, True)
    return dist


def eva_camera_recenter(client_id):
    """Put the lens back behind the suit and hand the framing back to the automatic rule.

    One control, because "the camera is somewhere odd" is one problem however it got
    there - a stray orbit, a dolly left in, or both.
    """
    set_inventory_value(client_id, KEY_YAW, 0.0)
    set_inventory_value(client_id, KEY_PITCH, CAM_PITCH)
    set_inventory_value(client_id, KEY_DIST, None)
    set_inventory_value(client_id, KEY_FREE, False)
    return True


def eva_camera_distance(client_id, suit=None, volume=None):
    """How far back the lens should sit right now.

    Manual wins outright. Otherwise: as far back as the room allows, then closer again the
    faster the suit is going.
    """
    manual = get_inventory_value(client_id, KEY_DIST, None)
    if manual is not None:
        return float(manual)
    dist = CAM_BASE
    obj = to_object(suit) if suit is not None else None
    if obj is not None and volume:
        room = -volume_depth(volume, (obj.pos.x, obj.pos.y, obj.pos.z))
        if room < CAM_ROOM_FULL:
            dist *= max(0.0, room) / CAM_ROOM_FULL
    if obj is not None:
        try:
            from ..eva import CRUISE
            from ..query import get_data_set_value
            throttle = float(get_data_set_value(obj.id, "playerThrottle", default=0.0)
                             or 0.0)
            dist *= 1.0 - CAM_SPEED_PULL * min(1.0, throttle / max(0.01, CRUISE))
        except Exception:
            # A hull that will not answer for its throttle still gets a camera.
            pass
    return max(CAM_MIN, min(CAM_MAX, dist))


def eva_camera_clamp(volume):
    """A `lens_filter` for `camera_follow` that keeps the lens inside `volume`.

    Walks the lens back along its own sightline toward the subject until it is inside -
    a bisection, because the subject is known inside and the wanted lens may not be, so
    the crossing is somewhere between them and eight halvings find it to under a unit.

    THE ONE THING THE ENGINE'S CHASE CANNOT DO. A relic has no collision at all, so
    nothing stops a camera ending up in the rock; and once it is there the frame is the
    inside of a wall, which reads as the console being broken rather than as the camera
    being wrong.
    """
    def _filter(base, want):
        if not volume:
            return want
        b = (base.x, base.y, base.z)
        w = (want.x, want.y, want.z)
        if volume_inside(volume, w, CAM_MARGIN):
            return want
        lo, hi = 0.0, 1.0          # lo is known good (at the subject), hi is not
        for _ in range(CAM_CLAMP_STEPS):
            mid = (lo + hi) * 0.5
            p = (b[0] + (w[0] - b[0]) * mid,
                 b[1] + (w[1] - b[1]) * mid,
                 b[2] + (w[2] - b[2]) * mid)
            if volume_inside(volume, p, CAM_MARGIN):
                lo = mid
            else:
                hi = mid
        if lo <= 0.0:
            # Even the subject's own position is not clear by the camera margin - it is
            # scraping a wall. Put the lens on the nearest point that IS, rather than
            # inside the hull, where the frame is black.
            got = volume_nearest_inside(volume, w, CAM_MARGIN)
            return got if got is not None else want
        return (b[0] + (w[0] - b[0]) * lo,
                b[1] + (w[1] - b[1]) * lo,
                b[2] + (w[2] - b[2]) * lo)
    return _filter


def eva_camera_aim(client_id, suit=None, volume=None):
    """Re-aim ONE console's camera. Returns where the lens went, or None.

    Called every tick by `eva_camera_tick`. Cheap on purpose: one `camera_follow`, one
    depth read for the distance, and at most eight `volume_inside` tests for the clamp -
    all of which the autopilot is paying for anyway.
    """
    from ..eva import eva_my_suit, eva_my_volume
    if suit is None:
        suit = eva_my_suit(client_id)
    if not suit:
        return None
    if volume is None:
        volume = eva_my_volume(client_id)
    yaw, pitch, _dist, free = eva_camera_state(client_id)
    if yaw and not free:
        # Wash a stray yaw out rather than leaving the console flying sideways forever.
        step = CAM_YAW_DECAY if yaw < 0 else -CAM_YAW_DECAY
        yaw = 0.0 if abs(yaw) <= CAM_YAW_DECAY else yaw + step
        set_inventory_value(client_id, KEY_YAW, yaw)
    distance = eva_camera_distance(client_id, suit, volume)
    return camera_follow(client_id, suit, distance,
                         height=distance * CAM_RISE, yaw=yaw, pitch=pitch,
                         lens_filter=eva_camera_clamp(volume))


#: Where the camera pass's task is kept. On `Agent.SHARED`, not at module level, so the
#: same machinery that clears and AUDITS the rest of the mission's per-mission state
#: reaches it - a task handle that survives a reset is how a tick stops running on every
#: run after the first.
_CAM_TICK_KEY = "__EVA_CAM_TICK__"

#: How often the camera re-aims. FASTER THAN THE AUTOPILOT, deliberately: the engine has
#: no interpolation, so following IS re-aiming and every missed frame is a step the eye
#: can see. The autopilot at 0.2s is a control loop; this is animation.
CAM_TICK_SECONDS = 0.0


def eva_camera_watch(seconds=CAM_TICK_SECONDS):
    """Start the camera pass. Idempotent - asking twice watches once."""
    from ...agent import Agent
    from ...tickdispatcher import TickDispatcher
    task = Agent.SHARED.get_inventory_value(_CAM_TICK_KEY, None)
    if task is not None:
        return task
    task = TickDispatcher.do_interval(eva_camera_tick, seconds)
    Agent.SHARED.set_inventory_value(_CAM_TICK_KEY, task)
    return task


def eva_camera_unwatch():
    """Stop the camera pass."""
    from ...agent import Agent
    task = Agent.SHARED.get_inventory_value(_CAM_TICK_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:
            # Already dropped by a reset or the end of a mission. Nothing to say.
            pass
    Agent.SHARED.set_inventory_value(_CAM_TICK_KEY, None)


def eva_camera_watching():
    """Reset-ledger probe. Must NOT create anything by asking."""
    from ...agent import Agent
    return 1 if Agent.SHARED.get_inventory_value(_CAM_TICK_KEY, None) is not None else 0


def eva_camera_tick(t=None):
    """Re-aim every console flying a suit. ONE shared pass, not a task per console.

    The same idiom `eva_tick` and `volume_containment_tick` use, and for the same reason:
    six consoles is six of everything otherwise, and the work per console is small enough
    that the scheduling would cost more than the aiming.
    """
    from ..eva import eva_drivers, eva_my_suit
    if eva_camera_mode() != MODE_THIRD:
        return True
    for cid in eva_drivers():
        if not eva_my_suit(cid):
            continue
        try:
            eva_camera_aim(cid)
        except Exception:
            # One console's camera must never take the pass down: the others are still
            # flying, and a missed frame is invisible where a dead tick is not.
            pass
    return True


def eva_camera_release(client_id):
    """Give the camera back to the engine's own director and forget this console's view.

    Called when a suit is put away. Without it a console that came back aboard would keep
    a script-driven lens pointed at a ship it is no longer flying.
    """
    set_inventory_value(client_id, KEY_YAW, None)
    set_inventory_value(client_id, KEY_PITCH, None)
    set_inventory_value(client_id, KEY_DIST, None)
    set_inventory_value(client_id, KEY_FREE, None)
    try:
        camera_auto(client_id)
    except Exception:
        pass
    return True


#: The camera mode this file implements, as `eva_camera_mode` names it.
MODE_THIRD = "third"


def eva_camera_mode(mode=None):
    """Read or set the EVA camera mode - re-exported from `eva_console` so a caller does
    not have to know which file owns which half."""
    from .eva_console import eva_camera_mode as _mode
    return _mode(mode)
