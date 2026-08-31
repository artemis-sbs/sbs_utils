"""Orbit capture: hold a ship on a circle around a body, and let the engine carry it.

The mechanism is the Blender empty-parent: an invisible **carrier** flies the circle, the
ship is rigidly welded into the carrier's frame, and the engine holds the weld. The ship
does not steer, does not accelerate, and cannot be driven - it is furniture on a moving
platform. Written for docking with a gas giant, where "docked" means orbiting rather than
sitting against a hull, but there is nothing gas-giant-specific here.

WHY A CARRIER AND NOT THE BODY ITSELF. Welding the ship straight to the gas giant at a
body-frame offset would be the tidier drawing, and it does not work twice over: a planet
does not rotate (so the offset never sweeps), and the mock's ``_physics_tractors`` floors
every pull at the SOURCE's exclusion radius - which for a body whose exclusion radius is
``planet_radius * 2`` is the whole orbit. The carrier is small, so neither applies.

WHY NOT ``mount.py``, WHICH IS THE SAME ENGINE CALL. ``mount_attach`` puts its target into
``MOUNT_ROLE`` and honors ``delete_with_host``; a host lost mid-orbit would therefore
delete the PLAYER SHIP. Same call, opposite intent, and they must not share a registry -
the argument ``mount.py`` itself makes about not reusing ``grav_tether_lock``. We also must
not reuse grav_tether, whose ``_enforce_impulse`` caps the SOURCE, i.e. our carrier.

ENGINE-MEASURED, and the reason no per-frame script work is needed
(``mount.py:9-22``, ``LM_TestRange/maps/test_tractor_mount.mast``)::

    sim.AddTractorConnection(host, target, sbs.vec3(0, 0, 200), 0)

held the target at exactly 200.0u and exactly 0.0 deg off the host's nose through a 51 deg
heading swing. The ENGINE maintains that every frame. So the carrier is moved once a
second by ordinary NPC steering - which the engine integrates at 30 Hz - and the ship
follows smoothly, with no reposition, no interpolation and no one-frame lag of ours.

We weld at offset (0,0,0), where body-frame and world-frame coincide. That matters for
testing: the mock's tractor model uses a WORLD offset, so at zero offset the mock and the
engine agree exactly, and a headless test of the weld is not testing a divergence.

WHY THE CARRIER'S SPEED IS WRITTEN AND NOT INHERITED. An NPC's top speed is
``throttle * 36 * speed_coeff``, so a stock hull tops out around 36 u/s - a nine-minute lap
of a modest gas giant, which reads as drifting, not orbiting. ``orbit_capture`` therefore
computes the speed the requested orbit needs and writes ``speed_coeff`` / ``turn_rate`` on
the carrier to match. ``turn_rate`` is not cosmetic: the steering model brakes on approach
within ``2 * (speed / turn_rate)``, so a carrier that turns too slowly for its circle would
crawl to a halt instead of coming round.

NO PER-ORBIT MODULE CONTAINER, deliberately, following ``mount.py``. The live state is a
role, two dedicated links and the carrier's own inventory, so ``Agent.clear()`` takes it
and there is nothing for a restart to miss. The one module global is the tick handle.

Every module-level function is prefixed ``orbit_``, private ones included: MAST imports a
module's functions into one flat, mission-wide namespace with no underscore filtering, so a
helper named ``_key`` would turn any script's ``_key = ...`` into a compile error that
empties the whole story.
"""

import math

from ..helpers import FrameContext
from ..lifetimedispatcher import LifetimeDispatcher
from ..tickdispatcher import TickDispatcher
from ..vec import Vec3
from .inventory import get_inventory_value, set_inventory_value
from .links import get_dedicated_link, set_dedicated_link
from .query import object_exists, to_id, to_object
from .roles import add_role, has_role, remove_role, role
from .signal import signal_emit
from .space_objects import delete_object, target_pos
from .spawn import npc_spawn


#: Role every carrier carries. The live-orbit set is derived from this rather than kept in
#: a module dict, so an agent reset takes it with everything else.
ORBIT_CARRIER_ROLE = "__ORBIT_CARRIER__"

#: Dedicated (1-to-1) link on the SHIP pointing at its carrier.
ORBIT_CARRIER_LINK = "__ORBIT_CARRIER__"

#: Dedicated (1-to-1) link on the CARRIER pointing back at its ship.
ORBIT_RIDER_LINK = "__ORBIT_RIDER__"

#: pull_distance for the weld. 0 is the typings' "infinite pull, target locked to boss",
#: which is what makes it rigid rather than springy - the same constant ``mount.py`` uses.
ORBIT_RIGID_PULL = 0.0

#: NPC impulse top speed at throttle 1.0 and speed_coeff 1.0, engine-calibrated
#: (``data_capture`` mission / ``capture_speed.json``). We divide by it to turn a wanted
#: orbital speed into the coefficient the steering model actually reads.
ORBIT_BASE_TOP_SPEED = 36.0

#: Default orbital speed when the caller names neither a speed nor a period. A little
#: under a player's impulse cruise: fast enough that the cloud tops visibly move, slow
#: enough to look like weather rather than a fairground ride.
ORBIT_DEFAULT_SPEED = 120.0

#: How far AHEAD around the circle the carrier is aimed, in radians. The carrier must never
#: reach what it is chasing: arrival braking would stop it dead. Big enough to stay clear of
#: the braking band (see ORBIT_TURN_MARGIN), small enough that the pursuit still cuts a
#: circle rather than a chord.
ORBIT_LEAD_ANGLE = 0.5

#: Multiple of the orbit's own angular rate the carrier is told it can turn at. The braking
#: band is 2*(speed/turn_rate) = 2*radius*w/turn_rate; at 6w that is radius/3, comfortably
#: inside the lead distance of radius*0.5. Also keeps the pure-pursuit controller well
#: ahead of the rate it has to track, so the circle does not sag into a spiral.
ORBIT_TURN_MARGIN = 6.0

#: Floor on the carrier's turn rate, for orbits so slow that 6w rounds to nothing.
ORBIT_MIN_TURN_RATE = 0.2

#: Proportional gain on the radius error when placing the aim point.
#:
#: Chasing a point further round the circle cuts the chord, so an uncorrected carrier flies
#: INSIDE the circle it was asked for - which put a ship inside the exclusion radius of the
#: very body it was orbiting. Rather than model the chord and the steering lag separately,
#: the aim point is pushed out by the error we can actually see.
ORBIT_RADIUS_GAIN = 4.0

#: Integral gain on the accumulated radius error.
#:
#: THE PROPORTIONAL TERM ALONE IS NOT ENOUGH, and the mock hid that. Against cosmos_dev's
#: steering the radius settled and recovered (8972 low, climbing back); measured against
#: the REAL ENGINE (LM_TestRange/maps/test_gas_giant_dock, 1.3.5) the same code fell
#: monotonically 8997 -> 8759 over 75s with no settle - a slow spiral that reaches the
#: cloud tops in under four minutes.
#:
#: That is the signature of standing error under a persistent bias, which no proportional
#: gain removes: raising Kp shrinks it and re-fits the constant to whichever steering model
#: was measured last. The integral term drives the offset out regardless of what is
#: underneath, so the primitive no longer depends on knowing whose steering it is flying.
ORBIT_RADIUS_INTEGRAL_GAIN = 0.6

#: Anti-windup clamp on the accumulated error, as a fraction of the orbit radius. Bounds
#: how far the integral alone can push the aim point, so a transient cannot wind up a
#: correction that then takes a whole lap to unwind.
ORBIT_INTEGRAL_LIMIT = 0.4

#: Gain on the measured heading error when leading the commanded tangent.
#:
#: Commanding the tangent at the ship's CURRENT bearing is always a little behind, because
#: the hull takes time to turn and the tangent never stops moving. Engine-measured, the lag
#: did not settle - it grew steadily at ~0.12 deg/s (2.2 -> 11.4 deg over 75s) and would
#: have kept going, because the hull's turn rate is the limit, not a spring that finds
#: equilibrium. So the commanded direction is led by an angle the loop grows from the error
#: it can actually see, exactly as the radius corrector does. Self-tuning: a nimble hull
#: settles at a small lead, a heavy one at a larger, and neither number is written here.
ORBIT_HEADING_GAIN = 0.35

#: Clamp on that lead, in radians. A quarter turn is far more than any real lag; past it
#: something else is wrong and pointing the ship further round would only look strange.
ORBIT_HEADING_LEAD_MAX = 0.8

#: Clamp on the corrected aim radius, as a multiple of the wanted one. Stops a transient
#: (a carrier still being dragged into place on the first tick) from flinging the aim point
#: somewhere absurd.
ORBIT_AIM_MIN = 0.75
ORBIT_AIM_MAX = 1.75

#: How much clearance the default radius keeps above the body's exclusion radius. Only a
#: floor - a caller asking for a wider orbit gets it.
#:
#: 1.15 rather than a hair over 1.0 because the flown radius sits a few percent inside the
#: commanded one even with the corrector, and "a few percent inside" of a bare 1.05 puts a
#: ship in the cloud tops. Measured settle with the corrector is ~1.5% low.
ORBIT_RADIUS_CLEARANCE = 1.15

#: Inventory keys on the carrier.
ORBIT_KEY_CENTER = "orbit:center"
ORBIT_KEY_RADIUS = "orbit:radius"
ORBIT_KEY_SPEED = "orbit:speed"
ORBIT_KEY_ANGLE = "orbit:angle"
ORBIT_KEY_SWEPT = "orbit:swept"        # total radians flown, NOT wrapped - see orbit_swept_of
ORBIT_KEY_RADIAL = "orbit:radial"      # r_hat at capture, as a plain tuple
ORBIT_KEY_TANGENT = "orbit:tangent"    # t_hat at capture, as a plain tuple
ORBIT_KEY_INTEGRAL = "orbit:integral"  # accumulated radius error, for the corrector
ORBIT_KEY_LEAD = "orbit:heading_lead"  # how far ahead of the tangent the nose is aimed

#: Inventory key on the SHIP holding the helm state we took away, so release can give it
#: back exactly rather than guess a default.
ORBIT_KEY_HELM = "orbit:helm"

#: Inventory key on the carrier: does undocking end this orbit? True for the docking case
#: this module was written for, False for an orbit a ship flew into rather than docked in.
ORBIT_KEY_UNDOCK = "orbit:release_on_undock"

_orbit_tick_task = None

#: How often the carrier is re-aimed, at MOST. The engine integrates its motion at 30 Hz
#: between our passes, so this only has to keep the aim point ahead - it is not the frame
#: rate of the orbit.
ORBIT_TICK_SECONDS = 1.0

#: Floor on the re-aim period, for orbits fast enough to need more than a pass a second.
ORBIT_TICK_MIN_SECONDS = 0.1

#: How far the carrier may sweep between re-aims, in radians.
#:
#: THE CADENCE IS A PROPERTY OF THE ORBIT, NOT OF THE CLOCK. A fixed second was sized for
#: ORBIT_DEFAULT_SPEED on a wide circle, where it is plenty. Ask for a fast orbit on a
#: tight one and the same second is a third of a lap: the carrier sails past the aim point
#: it was given and then chases it BACKWARDS, and the circle collapses. Half the lead
#: angle keeps the aim point still ahead whenever we move it, at any speed and radius.
ORBIT_AIM_SWEEP = ORBIT_LEAD_ANGLE / 2.0


def _orbit_sim():
    ctx = FrameContext.context
    return None if ctx is None else ctx.sim


def _orbit_sbs():
    ctx = FrameContext.context
    return None if ctx is None else ctx.sbs


def _orbit_exclusion(obj):
    """An object's exclusion radius, or 0.0 when the engine object cannot be asked."""
    try:
        return float(obj.engine_object.exclusion_radius) or 0.0
    except Exception:
        return 0.0


def _orbit_perpendicular(v):
    """Any unit vector perpendicular to ``v``, chosen stably.

    Crossing with the world axis ``v`` leans on least keeps the result well conditioned;
    crossing with a fixed axis would degenerate exactly when the ship arrives along it.
    """
    ax, ay, az = abs(v.x), abs(v.y), abs(v.z)
    if ax <= ay and ax <= az:
        axis = Vec3(1.0, 0.0, 0.0)
    elif ay <= az:
        axis = Vec3(0.0, 1.0, 0.0)
    else:
        axis = Vec3(0.0, 0.0, 1.0)
    return v.cross(axis).unit()


def _orbit_frame(ship_obj, center_obj):
    """The orbit plane, built from how the ship actually arrived.

    Returns ``(r_hat, t_hat)``: the radial unit vector out to the ship, and the unit
    tangent it will travel along. The tangent is the ship's own heading with its radial
    component removed, so the orbit keeps both the plane the ship was flying in and its
    direction of travel. A ship arriving dead-on has no tangential component to keep, and
    gets an arbitrary but stable perpendicular instead of a zero vector.
    """
    r = Vec3(ship_obj.pos.x - center_obj.pos.x,
             ship_obj.pos.y - center_obj.pos.y,
             ship_obj.pos.z - center_obj.pos.z)
    if r.length() < 1e-6:
        r = Vec3(0.0, 0.0, 1.0)
    r_hat = r.unit()

    fwd = None
    try:
        f = ship_obj.engine_object.forward_vector()
        fwd = Vec3(f.x, f.y, f.z)
    except Exception:
        fwd = None

    if fwd is not None and fwd.length() > 1e-6:
        fwd = fwd.unit()
        radial_part = r_hat * fwd.dot(r_hat)
        t = fwd - radial_part
        if t.length() > 1e-3:
            return r_hat, t.unit()

    # Straight-in (or no heading to read): any perpendicular will do, but it must be the
    # same one every time for the same approach, or a re-capture would flip the plane.
    return r_hat, _orbit_perpendicular(r_hat)


def _orbit_point(center_obj, radius, r_hat, t_hat, angle):
    """The world position at ``angle`` around the circle."""
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(center_obj.pos.x + radius * (c * r_hat.x + s * t_hat.x),
                center_obj.pos.y + radius * (c * r_hat.y + s * t_hat.y),
                center_obj.pos.z + radius * (c * r_hat.z + s * t_hat.z))


def _orbit_heading(r_hat, t_hat, angle):
    """The unit tangent at ``angle`` - which way a ship flying this circle is pointing.

    The position is ``cos(a)*r_hat + sin(a)*t_hat``, so the direction of travel is its
    derivative, ``-sin(a)*r_hat + cos(a)*t_hat``. Nothing about the tractor rotates the
    hull, so without this a captured ship keeps the heading it arrived with and slides
    round the curve sideways.
    """
    c, s = math.cos(angle), math.sin(angle)
    return Vec3(-s * r_hat.x + c * t_hat.x,
                -s * r_hat.y + c * t_hat.y,
                -s * r_hat.z + c * t_hat.z).unit()


def _orbit_wrap_pi(a):
    """Fold an angle into (-pi, pi] so an error either side of the wrap reads small."""
    while a > math.pi:
        a -= 2.0 * math.pi
    while a <= -math.pi:
        a += 2.0 * math.pi
    return a


def _orbit_bearing(obj, center_obj, r_hat, t_hat):
    """Where round the circle something ACTUALLY is, as an angle in the orbit frame.

    The tracked angle is bookkeeping - it advances at the commanded rate and the carrier is
    always somewhere slightly else, because it is chasing an aim point placed ahead of it.
    Steering to the tangent at the tracked angle therefore aims the nose systematically past
    the real direction of travel: engine-measured, that put the hull 7-12 deg AHEAD of where
    it was going, which reads as a ship drifting nose-out through the turn. The tangent has
    to come from where the thing actually is.
    """
    d = Vec3(obj.pos.x - center_obj.pos.x,
             obj.pos.y - center_obj.pos.y,
             obj.pos.z - center_obj.pos.z)
    if d.length() < 1e-6:
        return None
    return math.atan2(d.dot(t_hat), d.dot(r_hat))


def _orbit_heading_error(ship_obj, r_hat, t_hat, angle):
    """Signed angle from where the nose points to where the orbit wants it, in radians.

    Both vectors are projected onto the orbit plane, so this measures the turn the ship
    still owes and ignores any pitch the hull happens to carry.
    """
    try:
        f = ship_obj.engine_object.forward_vector()
        fwd = Vec3(f.x, f.y, f.z)
    except Exception:
        return None
    if fwd.length() < 1e-6:
        return None
    facing = math.atan2(fwd.dot(t_hat), fwd.dot(r_hat))
    return _orbit_wrap_pi((angle + math.pi / 2.0) - facing)


def _orbit_lead(carrier_id, ship_obj, r_hat, t_hat, angle):
    """Grow the commanded lead from the heading error the ship is actually showing."""
    lead = get_inventory_value(carrier_id, ORBIT_KEY_LEAD, 0.0) or 0.0
    err = _orbit_heading_error(ship_obj, r_hat, t_hat, angle)
    if err is not None:
        lead = min(max(lead + err * ORBIT_HEADING_GAIN, -ORBIT_HEADING_LEAD_MAX),
                   ORBIT_HEADING_LEAD_MAX)
        set_inventory_value(carrier_id, ORBIT_KEY_LEAD, lead)
    return lead


def _orbit_connect(carrier_id, ship_id):
    """The one place the raw engine call is made."""
    sim, sbs = _orbit_sim(), _orbit_sbs()
    if sim is None or sbs is None:
        return False
    try:
        sim.AddTractorConnection(carrier_id, ship_id, sbs.vec3(0.0, 0.0, 0.0),
                                 ORBIT_RIGID_PULL)
        return True
    except Exception:
        return False


def _orbit_disconnect(a_id, b_id):
    sim = _orbit_sim()
    if sim is None:
        return False
    try:
        sim.DeleteTractorConnection(a_id, b_id)
        return True
    except Exception:
        return False


def _orbit_take_helm(ship_obj, heading=None):
    """Stop the ship being driven, remembering what we took.

    Throttle and steering are re-asserted every tick as well: the helm widget writes them
    too, and last writer wins. Withdrawing ``warp`` matters more than it looks - a tractor
    holds a hull at impulse but is outrun at warp (measured, GRAV_TETHER_PLAN.md), and the
    engine only offers the WARP control when ``warp`` reads 1.0.

    Caveat, engine-measured 1.3.5: a ``tsn_battle_cruiser`` has NO ``warp`` key at all -
    it reads None both before and after capture - so on that hull this step does nothing
    and the throttle clamp is the only thing holding the ship. One hull is not every hull,
    so the withdraw stays (it is free where the key exists); it is simply not the guarantee.
    """
    ds = ship_obj.data_set
    # Only touch `warp` if the hull actually has it. A ship with no warp key has nothing
    # to withdraw, and writing one would restore a None over a value the engine owns.
    # NB: data_set.get's second argument is the INDEX, not a default - it reads back None
    # when the hull has no such key.
    warp = ds.get("warp", 0)
    set_inventory_value(ship_obj.id, ORBIT_KEY_HELM,
                        {"warp": warp, "steer_flag": ds.get("steeringToDirFlag", 0)})
    if warp is not None:
        ds.set("warp", 0, 0)
    _orbit_hold_helm(ship_obj, heading)


def _orbit_hold_helm(ship_obj, heading=None):
    """Pin the throttle and point the nose along the orbit.

    The steering is COMMANDEERED rather than switched off. Zeroing the flag would leave the
    hull frozen on the heading it arrived with, sliding round the curve sideways - the
    tractor holds position and nothing about it rotates anything. Writing the tangent
    instead makes the ship fly the curve, and still leaves the helm unable to drive: these
    are the same keys the helm widget writes, rewritten every tick, and the throttle is
    held at zero regardless.
    """
    ds = ship_obj.data_set
    ds.set("playerThrottle", 0, 0)
    if heading is None:
        return
    ds.set("steerToDirDX", heading.x, 0)
    ds.set("steerToDirDY", heading.y, 0)
    ds.set("steerToDirDZ", heading.z, 0)
    ds.set("steeringToDirFlag", 1, 0)


def _orbit_give_back_helm(ship_obj):
    saved = get_inventory_value(ship_obj.id, ORBIT_KEY_HELM, None)
    if saved is not None and saved.get("warp", None) is not None:
        ship_obj.data_set.set("warp", saved.get("warp"), 0)
    # Hand the steering back. Left at 1, the ship would keep flying the last tangent we
    # wrote and the helm's own ring would fight a direction nobody asked for.
    ship_obj.data_set.set("steeringToDirFlag", (saved or {}).get("steer_flag", 0) or 0, 0)
    set_inventory_value(ship_obj.id, ORBIT_KEY_HELM, None)


def orbit_capture(ship, center, radius=None, speed=None, seconds=None,
                  release_on_undock=True):
    """Put ``ship`` into a held orbit around ``center``.

    Idempotent: a ship already orbiting the same center keeps the orbit it has and the
    existing carrier id comes back. Callers are docking sections that may run more than
    once, so re-capturing must not build a second carrier.

    Args:
        ship (Agent | int): The ship to capture. Normally a player ship.
        center (Agent | int): What to orbit - a gas giant, a planet, anything with a
            position.
        radius (float, optional): Orbit radius. Defaults to the ship's current distance
            from the center, and is floored just clear of the center's exclusion radius so
            it can never be asked to orbit inside the body.
        speed (float, optional): Orbital speed in units/sec. Defaults to
            ``ORBIT_DEFAULT_SPEED``. Ignored when ``seconds`` is given.
        seconds (float, optional): Wanted period for one full lap. Overrides ``speed``.
        release_on_undock (bool): End the orbit when the ship reads as undocked. True is
            the docking case this module was written for. **A ship that flew here rather
            than docked is undocked the whole time**, so a free-flying capture - a
            slingshot round a black hole, a scripted flyby - is released on its very
            first tick unless this is False.

    Returns:
        int | None: The carrier's id, or None if either object is missing or the engine
            refused the weld.
    """
    ship_id, center_id = to_id(ship), to_id(center)
    if ship_id is None or center_id is None or ship_id == center_id:
        return None
    ship_obj, center_obj = to_object(ship_id), to_object(center_id)
    if ship_obj is None or center_obj is None:
        return None

    existing = orbit_carrier_of(ship_id)
    if existing is not None:
        return existing

    # The engine tractors the pair itself while docking (ENGINE_WIDGETS.md, request_dock)
    # and the script is expected to delete it - docking.py does the same on cancel. Two
    # tractors arguing over one hull is the failure mode this line exists to prevent.
    _orbit_disconnect(center_id, ship_id)

    r_hat, t_hat = _orbit_frame(ship_obj, center_obj)

    floor = _orbit_exclusion(center_obj) * ORBIT_RADIUS_CLEARANCE
    if radius is None:
        radius = Vec3(ship_obj.pos.x - center_obj.pos.x,
                      ship_obj.pos.y - center_obj.pos.y,
                      ship_obj.pos.z - center_obj.pos.z).length()
    radius = max(float(radius), floor, 1.0)

    if seconds is not None and float(seconds) > 0.0:
        speed = (2.0 * math.pi * radius) / float(seconds)
    elif speed is None:
        speed = ORBIT_DEFAULT_SPEED
    speed = max(float(speed), 1.0)

    start = _orbit_point(center_obj, radius, r_hat, t_hat, 0.0)
    carrier = npc_spawn(start.x, start.y, start.z, "", "#", "invisible", "behav_npcship")
    carrier_id = to_id(carrier)
    if carrier_id is None:
        return None

    if not _orbit_connect(carrier_id, ship_id):
        delete_object(carrier_id)
        return None

    # Write the carrier's own performance rather than inherit a stock hull's: see the
    # module docstring. turn_rate is scaled to the orbit so the arrival-braking band stays
    # well inside the lead distance and the carrier never brakes for its own aim point.
    omega = speed / radius
    ds = carrier.data_set
    ds.set("throttle", 1.0, 0)
    ds.set("speed_coeff", speed / ORBIT_BASE_TOP_SPEED, 0)
    ds.set("total_speed_coeff", speed / ORBIT_BASE_TOP_SPEED, 0)
    ds.set("turn_rate", max(ORBIT_TURN_MARGIN * omega, ORBIT_MIN_TURN_RATE), 0)

    add_role(carrier_id, ORBIT_CARRIER_ROLE)
    set_dedicated_link(ship_id, ORBIT_CARRIER_LINK, carrier_id)
    set_dedicated_link(carrier_id, ORBIT_RIDER_LINK, ship_id)
    set_inventory_value(carrier_id, ORBIT_KEY_CENTER, center_id)
    set_inventory_value(carrier_id, ORBIT_KEY_RADIUS, radius)
    set_inventory_value(carrier_id, ORBIT_KEY_SPEED, speed)
    set_inventory_value(carrier_id, ORBIT_KEY_ANGLE, 0.0)
    set_inventory_value(carrier_id, ORBIT_KEY_SWEPT, 0.0)
    set_inventory_value(carrier_id, ORBIT_KEY_INTEGRAL, 0.0)
    set_inventory_value(carrier_id, ORBIT_KEY_LEAD, 0.0)
    set_inventory_value(carrier_id, ORBIT_KEY_UNDOCK, bool(release_on_undock))
    set_inventory_value(carrier_id, ORBIT_KEY_RADIAL, (r_hat.x, r_hat.y, r_hat.z))
    set_inventory_value(carrier_id, ORBIT_KEY_TANGENT, (t_hat.x, t_hat.y, t_hat.z))

    _orbit_take_helm(ship_obj, _orbit_heading(r_hat, t_hat, 0.0))
    _orbit_aim(carrier_id, 0.0, dt=0.0)
    _orbit_ensure_tick(_orbit_aim_period(radius, speed))
    signal_emit("orbit_captured", {"ORBIT_SHIP_ID": ship_id,
                                   "ORBIT_CENTER_ID": center_id,
                                   "ORBIT_RADIUS": radius,
                                   "ORBIT_SECONDS": (2.0 * math.pi * radius) / speed})
    return carrier_id


def orbit_release(ship, delete_carrier=True):
    """Take ``ship`` out of orbit: drop the weld, hand the helm back, drop the carrier.

    Args:
        ship (Agent | int): The orbiting ship.
        delete_carrier (bool): Delete the carrier object too (default). Pass False during
            a mission teardown, where the agents are about to be cleared wholesale and a
            DEFERRED delete would only re-fill the delete queue after it was emptied.

    Returns:
        bool: True if the ship was orbiting.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    carrier_id = get_dedicated_link(ship_id, ORBIT_CARRIER_LINK)
    if carrier_id is None:
        return False

    center_id = get_inventory_value(carrier_id, ORBIT_KEY_CENTER, None)
    _orbit_disconnect(carrier_id, ship_id)
    set_dedicated_link(ship_id, ORBIT_CARRIER_LINK, None)

    ship_obj = to_object(ship_id)
    if ship_obj is not None:
        _orbit_give_back_helm(ship_obj)

    if object_exists(carrier_id):
        set_dedicated_link(carrier_id, ORBIT_RIDER_LINK, None)
        remove_role(carrier_id, ORBIT_CARRIER_ROLE)
        if delete_carrier:
            # Deferred, not the engine call: delete_object frees the C++ object
            # synchronously and anything still holding it would be pointing at freed
            # memory.
            delete_object(carrier_id)

    _orbit_maybe_stop_tick()
    signal_emit("orbit_released", {"ORBIT_SHIP_ID": ship_id,
                                   "ORBIT_CENTER_ID": center_id})
    return True


def orbit_is(ship):
    """Whether a ship is currently held in an orbit."""
    return orbit_carrier_of(ship) is not None


def orbit_carrier_of(ship):
    """The carrier a ship rides, or None.

    A carrier that no longer exists reads as None rather than a dangling id - a link can
    outlive the object it points at.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return None
    carrier_id = get_dedicated_link(ship_id, ORBIT_CARRIER_LINK)
    if carrier_id is None or not object_exists(carrier_id):
        return None
    return carrier_id


def orbit_center_of(ship):
    """What a ship is orbiting, or None."""
    carrier_id = orbit_carrier_of(ship)
    if carrier_id is None:
        return None
    center_id = get_inventory_value(carrier_id, ORBIT_KEY_CENTER, None)
    if center_id is None or not object_exists(center_id):
        return None
    return center_id


def orbit_radius_of(ship):
    """The radius a ship is orbiting at, or None."""
    carrier_id = orbit_carrier_of(ship)
    if carrier_id is None:
        return None
    return get_inventory_value(carrier_id, ORBIT_KEY_RADIUS, None)


def orbit_swept_of(ship):
    """Total radians this ship has flown since capture, or None if it is not orbiting.

    Cumulative, deliberately NOT wrapped to a turn: a caller ending a maneuver after half
    a lap has to be able to tell half a lap from one and a half. ``math.pi`` is the far
    side of the body, ``2*math.pi`` is all the way round.
    """
    carrier_id = orbit_carrier_of(ship)
    if carrier_id is None:
        return None
    return get_inventory_value(carrier_id, ORBIT_KEY_SWEPT, 0.0) or 0.0


def orbit_riders():
    """Every ship currently held in an orbit, as a set of ids."""
    out = set()
    for carrier_id in role(ORBIT_CARRIER_ROLE):
        if not object_exists(carrier_id):
            continue
        ship_id = get_dedicated_link(carrier_id, ORBIT_RIDER_LINK)
        if ship_id is not None and object_exists(ship_id):
            out.add(ship_id)
    return out


def orbit_count():
    """How many orbits are live. Cheap probe for tests, diagnostics and the reset ledger."""
    return len(orbit_riders())


def orbit_release_all():
    """Release every orbit without deleting any ship.

    For tests, for a mid-mission clean slate, and for reset_mission_state to drop the
    ENGINE-side welds deliberately - they are the engine's, not ours, so an agent reset
    alone would leave them behind.

    The carriers are released but NOT deleted, exactly as ``mount_clear_all`` does: the
    delete is deferred, so deleting here would re-fill a delete queue the reset had
    already emptied, and the agents are about to be cleared anyway.
    """
    try:
        riders = list(orbit_riders())
    except Exception:
        return
    for ship_id in riders:
        try:
            orbit_release(ship_id, delete_carrier=False)
        except Exception:
            pass
    _orbit_maybe_stop_tick()


# --- the tick -------------------------------------------------------------------------

def _orbit_aim_period(radius, speed):
    """How often THIS orbit needs re-aiming, in seconds. See ORBIT_AIM_SWEEP."""
    omega = float(speed) / max(float(radius), 1.0)
    if omega <= 0.0:
        return ORBIT_TICK_SECONDS
    return min(ORBIT_TICK_SECONDS, max(ORBIT_TICK_MIN_SECONDS, ORBIT_AIM_SWEEP / omega))


def _orbit_ensure_tick(period=None):
    """One shared pass, run at whatever the FASTEST live orbit needs.

    Aiming a slow orbit more often than it asked for is harmless - every rate in here is
    multiplied by the real dt - while aiming a fast one too rarely collapses its circle.
    So the period only ever ratchets DOWN while orbits are live; it goes back to the
    default when the last one ends and the task is dropped.
    """
    global _orbit_tick_task
    if FrameContext.context is None:
        return
    want = ORBIT_TICK_SECONDS if period is None else float(period)
    if _orbit_tick_task is None:
        _orbit_tick_task = TickDispatcher.do_interval(orbit_tick, want)
    elif want < _orbit_tick_task.delay:
        _orbit_tick_task.delay = want


def _orbit_maybe_stop_tick():
    global _orbit_tick_task
    if _orbit_tick_task is not None and orbit_count() == 0:
        _orbit_tick_task.stop()
        _orbit_tick_task = None


def _orbit_aim(carrier_id, angle, dt=None):
    """Point the carrier at a spot further round the circle and let it fly there.

    It is aimed AHEAD rather than at where it should be: a carrier told to go where it
    already is would brake to a stop, and the whole orbit with it.
    """
    center_id = get_inventory_value(carrier_id, ORBIT_KEY_CENTER, None)
    center_obj = to_object(center_id) if center_id is not None else None
    if center_obj is None:
        return False
    radius = get_inventory_value(carrier_id, ORBIT_KEY_RADIUS, 0.0)
    r = get_inventory_value(carrier_id, ORBIT_KEY_RADIAL, (0.0, 0.0, 1.0))
    t = get_inventory_value(carrier_id, ORBIT_KEY_TANGENT, (1.0, 0.0, 0.0))
    aim_radius = _orbit_aim_radius(carrier_id, center_obj, radius, dt=dt)
    aim = _orbit_point(center_obj, aim_radius, Vec3(*r), Vec3(*t), angle + ORBIT_LEAD_ANGLE)
    target_pos(carrier_id, aim.x, aim.y, aim.z, 1.0)
    return True


def _orbit_aim_radius(carrier_id, center_obj, radius, accumulate=True, dt=None):
    """Where to put the aim point so the carrier's PATH ends up at ``radius``.

    A PI controller on the radius error. See ORBIT_RADIUS_GAIN for why aiming at the wanted
    radius flies a smaller one, and ORBIT_RADIUS_INTEGRAL_GAIN for why the proportional
    half alone lets the engine spiral.

    Args:
        accumulate (bool): advance the integrator. False makes this a pure query, so a
            caller can ask "where would you aim?" without perturbing the loop.
    """
    carrier = to_object(carrier_id)
    if carrier is None or radius <= 0.0:
        return radius
    current = Vec3(carrier.pos.x - center_obj.pos.x,
                   carrier.pos.y - center_obj.pos.y,
                   carrier.pos.z - center_obj.pos.z).length()
    err = radius - current

    acc = get_inventory_value(carrier_id, ORBIT_KEY_INTEGRAL, 0.0) or 0.0
    if accumulate:
        # The REAL elapsed time, not the default period: a fast orbit is aimed several
        # times a second, and an integrator fed a fixed second would wind up that much
        # faster than the error it is integrating.
        acc = acc + err * (ORBIT_TICK_SECONDS if dt is None else float(dt))
        # Anti-windup: clamp the accumulator itself, not just its effect, or it keeps
        # growing while the output is clamped and then overshoots when the error flips.
        limit = radius * ORBIT_INTEGRAL_LIMIT / max(ORBIT_RADIUS_INTEGRAL_GAIN, 1e-6)
        acc = min(max(acc, -limit), limit)
        set_inventory_value(carrier_id, ORBIT_KEY_INTEGRAL, acc)

    aim = radius + err * ORBIT_RADIUS_GAIN + acc * ORBIT_RADIUS_INTEGRAL_GAIN
    return min(max(aim, radius * ORBIT_AIM_MIN), radius * ORBIT_AIM_MAX)


def orbit_tick(tick_task=None):
    """Advance every live orbit, and clean up the ones that have ended.

    Also re-asserts the helm freeze. The helm widget writes throttle and steering too, so
    holding a ship still is a thing that has to be done repeatedly, not once - the same
    reason grav_tether re-applies its impulse cap every pass.
    """
    dt = ORBIT_TICK_SECONDS if tick_task is None else float(tick_task.delay)
    for carrier_id in list(role(ORBIT_CARRIER_ROLE)):
        if not object_exists(carrier_id):
            continue
        ship_id = get_dedicated_link(carrier_id, ORBIT_RIDER_LINK)
        ship_obj = to_object(ship_id) if ship_id is not None else None

        # Self-heal. The `undocking` section only runs on the engine's docking_change
        # event, so an undock that came from a section returning FAIL_END would otherwise
        # leave a carrier flying an empty circle forever.
        if ship_obj is None:
            _orbit_orphan(carrier_id)
            continue
        center_id = get_inventory_value(carrier_id, ORBIT_KEY_CENTER, None)
        if center_id is None or not object_exists(center_id):
            orbit_release(ship_id)
            continue
        if (get_inventory_value(carrier_id, ORBIT_KEY_UNDOCK, True)
                and ship_obj.data_set.get("dock_state", 0) == "undocked"):
            orbit_release(ship_id)
            continue

        radius = get_inventory_value(carrier_id, ORBIT_KEY_RADIUS, 0.0)
        speed = get_inventory_value(carrier_id, ORBIT_KEY_SPEED, ORBIT_DEFAULT_SPEED)
        angle = get_inventory_value(carrier_id, ORBIT_KEY_ANGLE, 0.0)
        r_hat = Vec3(*get_inventory_value(carrier_id, ORBIT_KEY_RADIAL, (0.0, 0.0, 1.0)))
        t_hat = Vec3(*get_inventory_value(carrier_id, ORBIT_KEY_TANGENT, (1.0, 0.0, 0.0)))
        carrier = to_object(carrier_id)
        center_obj = to_object(center_id)
        bearing = _orbit_bearing(carrier, center_obj, r_hat, t_hat) if carrier else None

        if radius > 0.0:
            prev = angle
            angle = angle + (speed / radius) * dt
            # THE COMMAND MAY NEVER GET FURTHER AHEAD THAN THE LEAD IT IS SUPPOSED TO BE.
            #
            # The advance is a clock, and a carrier that cannot keep up with it - which is
            # every carrier for its first second, since speed approaches its target with a
            # lag - ends up chasing a point that keeps running away. It stops flying a
            # circle and flies the chord to wherever the aim has got to. Measured on a fast
            # wide arc before this bound: the radius sagged 8000 -> 5494 and the ship came
            # round 149 of the 180 degrees it was promised. Clamping to the truth plus the
            # lead costs the gas-giant case nothing, because there the carrier keeps up and
            # the clamp never binds.
            if bearing is not None:
                ahead = (angle - bearing) % (2.0 * math.pi)
                if ORBIT_LEAD_ANGLE < ahead < math.pi:
                    angle = bearing + ORBIT_LEAD_ANGLE
            angle = angle % (2.0 * math.pi)
            step = (angle - prev) % (2.0 * math.pi)
            if step > math.pi:
                step -= 2.0 * math.pi
            set_inventory_value(carrier_id, ORBIT_KEY_ANGLE, angle)
            swept = (get_inventory_value(carrier_id, ORBIT_KEY_SWEPT, 0.0) or 0.0)
            set_inventory_value(carrier_id, ORBIT_KEY_SWEPT, swept + max(step, 0.0))
        _orbit_aim(carrier_id, angle, dt=dt)
        # Point the nose along the tangent at where the carrier REALLY is, then lead that
        # by however far the hull is measurably still behind.
        if bearing is None:
            bearing = angle
        lead = _orbit_lead(carrier_id, ship_obj, r_hat, t_hat, bearing)
        _orbit_hold_helm(ship_obj, _orbit_heading(r_hat, t_hat, bearing + lead))

    _orbit_maybe_stop_tick()


def _orbit_orphan(carrier_id):
    """A carrier whose rider is gone: drop it, quietly."""
    remove_role(carrier_id, ORBIT_CARRIER_ROLE)
    set_dedicated_link(carrier_id, ORBIT_RIDER_LINK, None)
    delete_object(carrier_id)


def _orbit_on_destroy(destroyed, damage_event=None):
    """A destroyed ship or center ends the orbit in the same handler, not a tick later.

    Covers the ship (release), the center (release), and the carrier itself being caught
    in something (release, so the ship is not left welded to a corpse).
    """
    dead_id = to_id(destroyed)
    if dead_id is None:
        return
    if has_role(dead_id, ORBIT_CARRIER_ROLE):
        ship_id = get_dedicated_link(dead_id, ORBIT_RIDER_LINK)
        if ship_id is not None:
            orbit_release(ship_id)
        return
    if orbit_carrier_of(dead_id) is not None:
        orbit_release(dead_id)
        return
    for ship_id in list(orbit_riders()):
        if orbit_center_of(ship_id) is None:
            orbit_release(ship_id)


LifetimeDispatcher.add_destroy(_orbit_on_destroy)
