"""Flying a PLAYER ship from script: throttle, steering, docking, shields, power.

WHY THIS EXISTS. Nothing in the library could steer a player. `target()` and
`target_pos()` (`space_objects.py`) write the NPC keys - `target_pos_x/y/z`, `throttle` -
so every brain movement leaf is unusable on a player ship, and anything that wanted to fly
one hand-rolled the `data_set` writes. LegendaryMissions' autoplay does, and so did
`cosmos_dev`'s quest pilot, in two different styles.

The engine semantics these wrap are documented in `ENGINE_WIDGETS.md` and are easy to get
subtly wrong:

* `playerThrottle` is the throttle bar. **-1 is reverse**, and **warp is only available
  when `data_set warp == 1.0`** - a hull without a warp drive ignores a warp throttle, so
  a bot that asks for one just flies at impulse while believing it is at warp.
* Steering is `steerToDirD{X,Y,Z}` plus `steeringToDirFlag`. These were added FOR autoplay
  and are honored by the engine, so this is a real control path and not an emulation.
* Docking starts by writing `dock_base_id`, then the state walks
  `unknown -> docking -> docking_start -> docked`. Cancelling needs `dock_base_id = 0` AND
  `dock_state = unknown` - and the engine holds the dock with a *tractor*, so a cancel that
  does not delete it leaves the ship attached.

ENERGY IS THE INTERESTING PART. The tank drains only while the throttle is up -
`min(thr,1) * ship_energy_cost + max(0, thr-1) * warp_energy_cost`, warp weighted about
double - and the auxiliary power unit trickles it back **unconditionally** whenever energy
is below `ship_apu_ceiling`. Docking refills fast on top of that.

> **There is no unrecoverable energy state. A ship that strands is a ship that never
> stopped burning.**

That is why `helm_throttle` consults a reserve before allowing warp, and why
`helm_energy_reserve` exists at all. A bot that respects them cannot strand itself, which
means the "refill the tank so the test doesn't stall" cheat can be deleted rather than
hidden. Everything here is a real control write, so the same calls serve an attract bot and
a conformance run; what differs is the policy above them, not the actuation.
"""
import math

from ..helpers import FrameContext
from .query import to_id, to_object

# The engine exposes its power/heat table as parallel arrays addressed by index, with an
# empty label marking the end. 30 is what every existing walk uses.
ENG_CONTROL_SLOTS = 30

# Throttle 1.0 is full impulse; above that is warp. The engine's own bar tops out at 5.
IMPULSE_MAX = 1.0
THROTTLE_MAX = 5.0
REVERSE = -1.0

# Below this fraction of turn capability a ship cannot meaningfully steer, so burning
# straight ahead only commits it further. Taken from autoplay, which had both numbers.
TURN_COEFF_FLOOR = 0.35
MANEUVER_DAMAGE_CEILING = 0.75

# How much energy to keep in hand before spending any on warp. Warp is the only way to
# drain the tank faster than the APU refills it, so this is the whole anti-strand budget.
DEFAULT_ENERGY_RESERVE = 400.0


def _ds(ship):
    """The ship's data_set, or None. Accepts an id or an object."""
    so = to_object(ship)
    return getattr(so, "data_set", None) if so is not None else None


def _raw(ds, key, index=0):
    """The field as the engine gave it - None when it was never set.

    `_num` coalesces None to a number, which is right for arithmetic and WRONG for a
    capability question: "unset" and "zero" are different answers and only one of them
    means "this ship cannot do that".
    """
    if ds is None:
        return None
    try:
        return ds.get(key, index)
    except Exception:
        return None


def _num(ds, key, index=0, default=0.0):
    """Read a numeric data_set field, coalescing the engine's None.

    THE ENGINE ANSWERS None for a field nobody ever set, and the third argument of
    `data_set.get` is a SLOT INDEX, not a default - so it does not save you. The mock
    answers a typed default instead, which is how code like this runs clean headless for
    years and raises `'NoneType' < float` the first time it meets a real bridge.
    """
    if ds is None:
        return default
    try:
        val = ds.get(key, index)
    except Exception:
        return default
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# --- power / heat table -------------------------------------------------------------

def helm_eng_controls(ship):
    """Yield ``(index, label, system_index)`` for each engineering control the ship has.

    One walk of the `eng_control_label` array, which was written out by hand in three
    places: autoplay's can-turn check and its power loop, and `set_engineering_value`.
    Stops at the first empty label, which is how the engine marks the end.
    """
    ds = _ds(ship)
    if ds is None:
        return
    for i in range(ENG_CONTROL_SLOTS):
        try:
            label = ds.get("eng_control_label", i)
        except Exception:
            return
        if label is None or label == "":
            return
        yield i, str(label), int(_num(ds, "eng_control_type_index", i))


def helm_system_damage(ship, name):
    """Damage fraction (0..1) of the ship system a named control feeds, or 0.

    `name` matches case-insensitively as a substring, because the engine's labels are
    display text ("Maneuver", "Impulse Drive") rather than keys.
    """
    ds = _ds(ship)
    want = str(name).lower()
    worst = 0.0
    for _i, label, sysi in helm_eng_controls(ship):
        if want not in label.lower():
            continue
        mx = _num(ds, "system_max_damage", sysi)
        if mx > 0:
            worst = max(worst, _num(ds, "system_damage", sysi) / mx)
    return worst


def helm_system_heat(ship, name):
    """Heat (0..1-ish) of the ship system a named control feeds, or 0."""
    ds = _ds(ship)
    want = str(name).lower()
    hottest = 0.0
    for _i, label, sysi in helm_eng_controls(ship):
        if want in label.lower():
            hottest = max(hottest, _num(ds, "system_cur_heat", sysi))
    return hottest


def helm_set_power(ship, name, value):
    """Set the power level of every control whose label matches `name`. Returns how many.

    Unlike `set_engineering_value`, which stops at the first match, this sets all of them -
    a hull can expose more than one control feeding the same system.
    """
    ds = _ds(ship)
    if ds is None:
        return 0
    n = 0
    for i, label, _sysi in helm_eng_controls(ship):
        if str(name).lower() in label.lower():
            ds.set("eng_control_value", float(value), i)
            n += 1
    return n


def helm_can_turn(ship):
    """Whether the ship can still steer meaningfully.

    Consults BOTH the turn damage coefficient and the maneuver system's damage: a wrecked
    maneuver system stops the ship turning before the coefficient bottoms out. A ship that
    cannot turn must not burn straight ahead - that only commits it further - so callers
    use this to decide to hold station instead.
    """
    ds = _ds(ship)
    if ds is None:
        return False
    coeff = _num(ds, "turn_damage_coeff", 0, default=1.0) or 1.0
    return coeff >= TURN_COEFF_FLOOR and \
        helm_system_damage(ship, "maneuver") < MANEUVER_DAMAGE_CEILING


# --- energy -------------------------------------------------------------------------

def helm_energy(ship):
    """Current energy in the tank."""
    return _num(_ds(ship), "energy")


def helm_warp_available(ship):
    """Whether this hull may use warp. Unknown counts as YES - see below.

    The engine gates the throttle bar's WARP band on `data_set warp == 1.0`, so checking
    it stops a bot believing it is at warp on a hull that has no drive.

    BUT THE POLARITY MATTERS MORE THAN THE CHECK. The engine returns None for a field
    nobody set, and treating that as 0 means "I have no information" silently becomes
    "you may never warp" - a capability disabled forever, with no error, on a ship that
    flies perfectly well. That is strictly worse than the thing the check was guarding
    against, which merely wastes a throttle write the engine ignores.

    So this refuses only on POSITIVE evidence of no drive: the flag says 0 AND the hull
    costs nothing to warp. Anything unknown is allowed through, which is exactly how
    every autoplayer behaved before this function existed.
    """
    ds = _ds(ship)
    flag = _raw(ds, "warp")
    cost = _raw(ds, "warp_energy_cost")
    if flag is not None and float(flag or 0) >= 1.0:
        return True
    if cost is not None and float(cost or 0) > 0:
        return True
    # Both unknown -> allow. Both known and zero -> this hull really has no warp drive.
    return flag is None and cost is None


def helm_energy_cost(ship, throttle, seconds):
    """Energy this ship would spend holding `throttle` for `seconds`.

    Mirrors the engine's drain: impulse is charged on the part of the throttle up to 1.0
    and warp on the excess, at the hull's own `ship_energy_cost` / `warp_energy_cost`.
    Warp costs roughly double per unit, which is why sustained warp is the only thing that
    outruns the auxiliary power unit.
    """
    ds = _ds(ship)
    thr = max(0.0, float(throttle))
    impulse = min(thr, IMPULSE_MAX) * _num(ds, "ship_energy_cost")
    warp = max(0.0, thr - IMPULSE_MAX) * _num(ds, "warp_energy_cost") * 2.0
    return (impulse + warp) * max(0.0, float(seconds))


def helm_energy_reserve(ship, target=None, throttle=IMPULSE_MAX, reserve=None):
    """Whether the ship can afford to run, and still have something left.

    With a `target`, this asks the question that matters: *can I get there and not be
    stranded when I arrive?* It compares the tank against the cost of the trip at
    `throttle` plus a flat reserve. Without a target it is just "am I above the reserve".

    This is what replaces a flat "dock below 300": 300 says nothing about whether the
    nearest station is 2,000 units away or 40,000.
    """
    if reserve is None:
        reserve = DEFAULT_ENERGY_RESERVE
    energy = helm_energy(ship)
    if target is None:
        return energy >= reserve
    dist = helm_distance(ship, target)
    if dist is None or dist == float("inf"):
        return energy >= reserve
    speed = helm_speed_for(ship, throttle)
    if speed <= 0:
        return energy >= reserve
    return energy - helm_energy_cost(ship, throttle, dist / speed) >= reserve


def helm_speed_for(ship, throttle):
    """Approximate speed (units/second) this ship would make at `throttle`.

    Player speed is hull-INDEPENDENT in Cosmos: impulse tops out the same for every hull,
    and warp adds a per-factor bonus on top. Used only to turn a distance into a duration
    for the energy estimate, so approximate is enough.
    """
    thr = max(0.0, float(throttle))
    if thr <= IMPULSE_MAX:
        return thr * 180.0
    return 180.0 + (thr - IMPULSE_MAX) * 450.0


# --- geometry -----------------------------------------------------------------------

def helm_position(thing):
    """Position of a ship, an object, or a point-like value. None when there is none."""
    pos = getattr(thing, "x", None)
    if pos is not None and getattr(thing, "z", None) is not None:
        return thing
    so = to_object(thing)
    return getattr(so, "pos", None) if so is not None else None


def helm_distance(ship, target):
    """Distance between a ship and a target (object, id, or point), or inf."""
    a = helm_position(ship)
    b = helm_position(target)
    if a is None or b is None:
        return float("inf")
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


# --- flying -------------------------------------------------------------------------

def helm_throttle(ship, level, allow_warp=True, reserve=None):
    """Set the throttle, refusing a warp the ship cannot actually sustain.

    Returns the throttle actually set, which may be lower than asked. Two reasons it
    clamps, and both are silent failures otherwise:

    * the hull has no warp drive (`warp != 1.0`), so the engine ignores the warp band;
    * the tank is below the reserve, and warp is the one thing that drains faster than
      the auxiliary power unit refills. Clamping to impulse lets the APU win.

    Pass `allow_warp=False` to hold impulse regardless - a caller that has decided to
    conserve does not need to restate why.
    """
    ds = _ds(ship)
    if ds is None:
        return 0.0
    thr = float(level)
    if thr < 0:
        thr = max(REVERSE, thr)         # -1 is reverse; nothing below it means anything
    else:
        thr = min(THROTTLE_MAX, thr)
    if thr > IMPULSE_MAX:
        if not allow_warp or not helm_warp_available(ship):
            thr = IMPULSE_MAX
        elif _raw(ds, "energy") is not None and not helm_energy_reserve(ship, reserve=reserve):
            # Same polarity rule as the warp flag: an energy field the engine never set
            # reads as None, and treating that as an empty tank would refuse warp for the
            # whole mission on a ship that has plenty.
            thr = IMPULSE_MAX
    ds.set("playerThrottle", thr, 0)
    return thr


def helm_stop(ship):
    """Cut the throttle and drop direction steering.

    Also the recovery move: with the throttle at zero nothing drains the tank, so the
    auxiliary power unit refills it. Stopping is always a way out.
    """
    ds = _ds(ship)
    if ds is None:
        return
    ds.set("playerThrottle", 0.0, 0)
    ds.set("steeringToDirFlag", 0, 0)


def helm_steer_to_vec(ship, x, y=None, z=None):
    """Steer along a direction vector. Accepts (vec) or (x, y, z)."""
    ds = _ds(ship)
    if ds is None:
        return False
    if y is None and z is None:
        vec = x
        x, y, z = getattr(vec, "x", 0.0), getattr(vec, "y", 0.0), getattr(vec, "z", 0.0)
    length = math.sqrt(x * x + y * y + z * z)
    if length <= 0.0001:
        return False
    ds.set("steerToDirDX", x / length, 0)
    ds.set("steerToDirDY", y / length, 0)
    ds.set("steerToDirDZ", z / length, 0)
    ds.set("steeringToDirFlag", 1, 0)
    return True


def helm_steer_to_point(ship, target):
    """Steer toward an object, id, or point. False when either position is unknown."""
    here = helm_position(ship)
    there = helm_position(target)
    if here is None or there is None:
        return False
    return helm_steer_to_vec(ship, there.x - here.x, there.y - here.y, there.z - here.z)


# --- docking ------------------------------------------------------------------------

def helm_dock_request(ship, station):
    """Ask to dock: name the base, then start the state walk if it has not started.

    The engine takes it from `dock_start` through to `docked` on its own. Docking refills
    the tank fast, which makes it the quick way out of a low-energy situation when a
    friendly station is in reach.
    """
    ds = _ds(ship)
    base = to_id(station)
    if ds is None or base is None:
        return False
    ds.set("dock_base_id", base, 0)
    state = ds.get("dock_state", 0)
    if state not in ("docked", "dock_start"):
        ds.set("dock_state", "dock_start", 0)
    ds.set("playerThrottle", 0.0, 0)
    return True


def helm_undock(ship):
    """Release the dock.

    Clears `dock_base_id` as well as the state: the engine holds a docked ship with a
    TRACTOR, and a cancel that only rewrites the state leaves the ship attached to a base
    it believes it has left.
    """
    ds = _ds(ship)
    if ds is None:
        return False
    ds.set("dock_state", "undocked", 0)
    ds.set("dock_base_id", 0, 0)
    try:
        sim = FrameContext.context.sim
        if sim is not None:
            sim.ClearTractorConnections()
    except Exception:
        pass
    return True


def helm_is_docked(ship):
    """True while the ship is docked."""
    ds = _ds(ship)
    if ds is None:
        return False
    return ds.get("dock_state", 0) == "docked"


# --- shields ------------------------------------------------------------------------

def helm_shields(ship, up=True):
    """Raise or lower shields."""
    ds = _ds(ship)
    if ds is None:
        return False
    ds.set("shields_raised_flag", 1 if up else 0, 0)
    return True


def helm_shield_fraction(ship, facing=0):
    """How full one shield facing is, 0..1. 0 when the ship has no shields."""
    ds = _ds(ship)
    mx = _num(ds, "shield_max_val", facing)
    if mx <= 0:
        return 0.0
    return _num(ds, "shield_val", facing) / mx
