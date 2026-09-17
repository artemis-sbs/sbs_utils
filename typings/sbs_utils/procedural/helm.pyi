from sbs_utils.helpers import FrameContext
def _ds (ship):
    """The ship's data_set, or None. Accepts an id or an object."""
def _num (ds, key, index=0, default=0.0):
    """Read a numeric data_set field, coalescing the engine's None.
    
    THE ENGINE ANSWERS None for a field nobody ever set, and the third argument of
    `data_set.get` is a SLOT INDEX, not a default - so it does not save you. The mock
    answers a typed default instead, which is how code like this runs clean headless for
    years and raises `'NoneType' < float` the first time it meets a real bridge."""
def _raw (ds, key, index=0):
    """The field as the engine gave it - None when it was never set.
    
    `_num` coalesces None to a number, which is right for arithmetic and WRONG for a
    capability question: "unset" and "zero" are different answers and only one of them
    means "this ship cannot do that"."""
def helm_apu_ceiling (ship):
    """The energy the auxiliary power unit refills to - and so the most waiting can reach.
    
    Reads `ship_apu_ceiling` when the ship carries a positive one, otherwise the engine's
    global `ship_apu_assistance_ceiling` (200). Anything that parks a ship "until energy
    recovers" has to aim below this, or it waits forever."""
def helm_can_turn (ship):
    """Whether the ship can still steer meaningfully.
    
    Consults BOTH the turn damage coefficient and the maneuver system's damage: a wrecked
    maneuver system stops the ship turning before the coefficient bottoms out. A ship that
    cannot turn must not burn straight ahead - that only commits it further - so callers
    use this to decide to hold station instead."""
def helm_distance (ship, target):
    """Distance between a ship and a target (object, id, or point), or inf."""
def helm_dock_request (ship, station):
    """Ask to dock: name the base, then start the state walk if it has not started.
    
    The engine takes it from `dock_start` through to `docked` on its own. Docking refills
    the tank fast, which makes it the quick way out of a low-energy situation when a
    friendly station is in reach."""
def helm_energy (ship):
    """Current energy in the tank."""
def helm_energy_cost (ship, throttle, seconds):
    """Energy this ship would spend holding `throttle` for `seconds`.
    
    Mirrors the engine's drain: impulse is charged on the part of the throttle up to 1.0
    and warp on the excess, at the hull's own `ship_energy_cost` / `warp_energy_cost`.
    Warp costs roughly double per unit. An ESTIMATE for trip planning: the engine really
    charges by speed and slider power (see the module docstring), not these fields."""
def helm_energy_reserve (ship, target=None, throttle=1.0, reserve=None):
    """Whether the ship can afford to run, and still have something left.
    
    With a `target`, this asks the question that matters: *can I get there and not be
    stranded when I arrive?* It compares the tank against the cost of the trip at
    `throttle` plus a flat reserve. Without a target it is just "am I above the reserve".
    
    This is what replaces a flat "dock below 300": 300 says nothing about whether the
    nearest station is 2,000 units away or 40,000."""
def helm_eng_controls (ship):
    """Yield ``(index, label, system_index)`` for each engineering control the ship has.
    
    One walk of the `eng_control_label` array, which was written out by hand in three
    places: autoplay's can-turn check and its power loop, and `set_engineering_value`.
    Stops at the first empty label, which is how the engine marks the end."""
def helm_is_docked (ship):
    """True while the ship is docked."""
def helm_position (thing):
    """Position of a ship, an object, or a point-like value. None when there is none.
    
    A PLAIN (x, y, z) COUNTS, and leaving it out was a real bug rather than a nicety.
    Everything geometric in the library hands positions round as TUPLES - `volume_route`
    returns them, `relic_points` stores them, `eva_points` lists them - so
    `helm_distance(suit, place)` against any of those answered `inf` for want of a `.x`.
    The EVA Nav app showed every destination at distance 0."""
def helm_set_power (ship, name, value):
    """Set the power level of every control whose label matches `name`. Returns how many.
    
    Unlike `set_engineering_value`, which stops at the first match, this sets all of them -
    a hull can expose more than one control feeding the same system."""
def helm_shield_fraction (ship, facing=0):
    """How full one shield facing is, 0..1. 0 when the ship has no shields."""
def helm_shields (ship, up=True):
    """Raise or lower shields."""
def helm_speed_for (ship, throttle):
    """Approximate speed (units/second) this ship would make at `throttle`.
    
    Player speed is hull-INDEPENDENT in Cosmos: impulse tops out the same for every hull,
    and warp adds a per-factor bonus on top. Used only to turn a distance into a duration
    for the energy estimate, so approximate is enough."""
def helm_steer_to_point (ship, target):
    """Steer toward an object, id, or point. False when either position is unknown."""
def helm_steer_to_vec (ship, x, y=None, z=None):
    """Steer along a direction vector. Accepts (vec) or (x, y, z)."""
def helm_stop (ship):
    """Cut the throttle and drop direction steering.
    
    Stopping cuts the speed drain, but the sliders and shields still draw, and the auxiliary
    power unit only refills to `helm_apu_ceiling` (~200). It buys a trickle, not a full tank."""
def helm_system_damage (ship, name):
    """Damage fraction (0..1) of the ship system a named control feeds, or 0.
    
    `name` matches case-insensitively as a substring, because the engine's labels are
    display text ("Maneuver", "Impulse Drive") rather than keys."""
def helm_system_heat (ship, name):
    """Heat (0..1-ish) of the ship system a named control feeds, or 0."""
def helm_throttle (ship, level, allow_warp=True, reserve=None):
    """Set the throttle, refusing a warp the ship cannot actually sustain.
    
    Returns the throttle actually set, which may be lower than asked. Two reasons it
    clamps, and both are silent failures otherwise:
    
    * the hull has no warp drive (`warp != 1.0`), so the engine ignores the warp band;
    * the tank is below the reserve, and warp burns it fastest. Clamping to impulse keeps
      enough in hand to reach a station.
    
    Pass `allow_warp=False` to hold impulse regardless - a caller that has decided to
    conserve does not need to restate why."""
def helm_undock (ship):
    """Release the dock.
    
    Clears `dock_base_id` as well as the state: the engine holds a docked ship with a
    TRACTOR, and a cancel that only rewrites the state leaves the ship attached to a base
    it believes it has left."""
def helm_warp_available (ship):
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
    every autoplayer behaved before this function existed."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
