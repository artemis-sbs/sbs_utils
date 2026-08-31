from sbs_utils.helpers import FrameContext
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def _orbit_aim (carrier_id, angle):
    """Point the carrier at a spot further round the circle and let it fly there.
    
    It is aimed AHEAD rather than at where it should be: a carrier told to go where it
    already is would brake to a stop, and the whole orbit with it."""
def _orbit_aim_radius (carrier_id, center_obj, radius, accumulate=True):
    """Where to put the aim point so the carrier's PATH ends up at ``radius``.
    
    A PI controller on the radius error. See ORBIT_RADIUS_GAIN for why aiming at the wanted
    radius flies a smaller one, and ORBIT_RADIUS_INTEGRAL_GAIN for why the proportional
    half alone lets the engine spiral.
    
    Args:
        accumulate (bool): advance the integrator. False makes this a pure query, so a
            caller can ask "where would you aim?" without perturbing the loop."""
def _orbit_bearing (obj, center_obj, r_hat, t_hat):
    """Where round the circle something ACTUALLY is, as an angle in the orbit frame.
    
    The tracked angle is bookkeeping - it advances at the commanded rate and the carrier is
    always somewhere slightly else, because it is chasing an aim point placed ahead of it.
    Steering to the tangent at the tracked angle therefore aims the nose systematically past
    the real direction of travel: engine-measured, that put the hull 7-12 deg AHEAD of where
    it was going, which reads as a ship drifting nose-out through the turn. The tangent has
    to come from where the thing actually is."""
def _orbit_connect (carrier_id, ship_id):
    """The one place the raw engine call is made."""
def _orbit_disconnect (a_id, b_id):
    ...
def _orbit_ensure_tick ():
    ...
def _orbit_exclusion (obj):
    """An object's exclusion radius, or 0.0 when the engine object cannot be asked."""
def _orbit_frame (ship_obj, center_obj):
    """The orbit plane, built from how the ship actually arrived.
    
    Returns ``(r_hat, t_hat)``: the radial unit vector out to the ship, and the unit
    tangent it will travel along. The tangent is the ship's own heading with its radial
    component removed, so the orbit keeps both the plane the ship was flying in and its
    direction of travel. A ship arriving dead-on has no tangential component to keep, and
    gets an arbitrary but stable perpendicular instead of a zero vector."""
def _orbit_give_back_helm (ship_obj):
    ...
def _orbit_heading (r_hat, t_hat, angle):
    """The unit tangent at ``angle`` - which way a ship flying this circle is pointing.
    
    The position is ``cos(a)*r_hat + sin(a)*t_hat``, so the direction of travel is its
    derivative, ``-sin(a)*r_hat + cos(a)*t_hat``. Nothing about the tractor rotates the
    hull, so without this a captured ship keeps the heading it arrived with and slides
    round the curve sideways."""
def _orbit_heading_error (ship_obj, r_hat, t_hat, angle):
    """Signed angle from where the nose points to where the orbit wants it, in radians.
    
    Both vectors are projected onto the orbit plane, so this measures the turn the ship
    still owes and ignores any pitch the hull happens to carry."""
def _orbit_hold_helm (ship_obj, heading=None):
    """Pin the throttle and point the nose along the orbit.
    
    The steering is COMMANDEERED rather than switched off. Zeroing the flag would leave the
    hull frozen on the heading it arrived with, sliding round the curve sideways - the
    tractor holds position and nothing about it rotates anything. Writing the tangent
    instead makes the ship fly the curve, and still leaves the helm unable to drive: these
    are the same keys the helm widget writes, rewritten every tick, and the throttle is
    held at zero regardless."""
def _orbit_lead (carrier_id, ship_obj, r_hat, t_hat, angle):
    """Grow the commanded lead from the heading error the ship is actually showing."""
def _orbit_maybe_stop_tick ():
    ...
def _orbit_on_destroy (destroyed, damage_event=None):
    """A destroyed ship or center ends the orbit in the same handler, not a tick later.
    
    Covers the ship (release), the center (release), and the carrier itself being caught
    in something (release, so the ship is not left welded to a corpse)."""
def _orbit_orphan (carrier_id):
    """A carrier whose rider is gone: drop it, quietly."""
def _orbit_perpendicular (v):
    """Any unit vector perpendicular to ``v``, chosen stably.
    
    Crossing with the world axis ``v`` leans on least keeps the result well conditioned;
    crossing with a fixed axis would degenerate exactly when the ship arrives along it."""
def _orbit_point (center_obj, radius, r_hat, t_hat, angle):
    """The world position at ``angle`` around the circle."""
def _orbit_sbs ():
    ...
def _orbit_sim ():
    ...
def _orbit_take_helm (ship_obj, heading=None):
    """Stop the ship being driven, remembering what we took.
    
    Throttle and steering are re-asserted every tick as well: the helm widget writes them
    too, and last writer wins. Withdrawing ``warp`` matters more than it looks - a tractor
    holds a hull at impulse but is outrun at warp (measured, GRAV_TETHER_PLAN.md), and the
    engine only offers the WARP control when ``warp`` reads 1.0.
    
    Caveat, engine-measured 1.3.5: a ``tsn_battle_cruiser`` has NO ``warp`` key at all -
    it reads None both before and after capture - so on that hull this step does nothing
    and the throttle clamp is the only thing holding the ship. One hull is not every hull,
    so the withdraw stays (it is free where the key exists); it is simply not the guarantee."""
def _orbit_wrap_pi (a):
    """Fold an angle into (-pi, pi] so an error either side of the wrap reads small."""
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def delete_object (id_or_objs):
    """Delete one or more agents from the simulation.
    
    Args:
        id_or_objs (Agent | int | set[Agent | int]): Agent(s) to delete."""
def get_dedicated_link (so, link_name: str):
    """Return the single agent ID linked under a dedicated (1-to-1) link.
    
    A dedicated link stores exactly one target per source. Use ``link`` /
    ``set_dedicated_link`` for many-to-many or 1-to-1 links respectively.
    
    Args:
        so (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        int | None: The linked agent ID, or ``None`` if not set."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def npc_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a non-player (NPC) ship into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the ship belongs to.
        ship_key (str): Ship template key from shipData.
        behave_id (str): Behavior type identifier.
    
    Returns:
        SpawnData: Spawn data for the new NPC."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def orbit_capture (ship, center, radius=None, speed=None, seconds=None, release_on_undock=True):
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
    
    Returns:
        int | None: The carrier's id, or None if either object is missing or the engine
            refused the weld."""
def orbit_carrier_of (ship):
    """The carrier a ship rides, or None.
    
    A carrier that no longer exists reads as None rather than a dangling id - a link can
    outlive the object it points at."""
def orbit_center_of (ship):
    """What a ship is orbiting, or None."""
def orbit_count ():
    """How many orbits are live. Cheap probe for tests, diagnostics and the reset ledger."""
def orbit_is (ship):
    """Whether a ship is currently held in an orbit."""
def orbit_swept_of (ship):
    """Total radians this ship has flown since capture, or None if it is not orbiting.

    Cumulative, deliberately NOT wrapped to a turn: a caller ending a maneuver after half
    a lap has to be able to tell half a lap from one and a half. ``math.pi`` is the far
    side of the body, ``2*math.pi`` is all the way round."""
def orbit_radius_of (ship):
    """The radius a ship is orbiting at, or None."""
def orbit_release (ship, delete_carrier=True):
    """Take ``ship`` out of orbit: drop the weld, hand the helm back, drop the carrier.
    
    Args:
        ship (Agent | int): The orbiting ship.
        delete_carrier (bool): Delete the carrier object too (default). Pass False during
            a mission teardown, where the agents are about to be cleared wholesale and a
            DEFERRED delete would only re-fill the delete queue after it was emptied.
    
    Returns:
        bool: True if the ship was orbiting."""
def orbit_release_all ():
    """Release every orbit without deleting any ship.
    
    For tests, for a mid-mission clean slate, and for reset_mission_state to drop the
    ENGINE-side welds deliberately - they are the engine's, not ours, so an agent reset
    alone would leave them behind.
    
    The carriers are released but NOT deleted, exactly as ``mount_clear_all`` does: the
    delete is deferred, so deleting here would re-fill a delete queue the reset had
    already emptied, and the agents are about to be cleared anyway."""
def orbit_riders ():
    """Every ship currently held in an orbit, as a set of ids."""
def orbit_tick (tick_task=None):
    """Advance every live orbit, and clean up the ones that have ended.
    
    Also re-asserts the helm freeze. The helm widget writes throttle and steering too, so
    holding a ship still is a thing that has to be done repeatedly, not once - the same
    reason grav_tether re-applies its impulse cap every pass."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_dedicated_link (so, link_name: str, to):
    """Set a dedicated (1-to-1) link from a source agent to a single target.
    
    Replaces any existing link under ``link_name`` with the new target. Pass
    ``to=None`` to clear the link entirely, so that ``get_dedicated_link``
    returns ``None`` again.
    
    Args:
        so (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
        to (Agent | int | None): The target agent ID or object, or ``None`` to clear."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def target_pos (chasers: set | int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData, x: float, y: float, z: float, throttle: float = 1.0, target_id=None, stop_dist=None):
    """Direct one or more agents to move toward a position in simulation space.
    
    Args:
        chasers (Agent | int | set[Agent | int] | CloseData | SpawnData):
            Agent(s) to command.
        x (float): Target X coordinate.
        y (float): Target Y coordinate.
        z (float): Target Z coordinate.
        throttle (float, optional): Movement speed multiplier (0.0–1.0).
            Defaults to 1.0.
        target_id (Agent | int, optional): If set, agents will also fire at
            this target. Defaults to None.
        stop_dist (float, optional): Stop the agent (throttle→0) when within
            this distance of the target. Defaults to None."""
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
