from sbs_utils.agent import Agent
def _alignment (suit, here, aim):
    """Cosine of the angle between the suit's nose and the way it wants to go.
    
    1.0 when the heading cannot be read - an unknown alignment must not stop the suit,
    or a hull whose facing this cannot see would never move at all."""
def _client (client_id=None):
    ...
def _dist (a, b):
    ...
def _eva_drift (suit, here, aim, volume, room):
    """Nudge the aim to one side, the same way for this suit every tick.
    
    No RNG object and no state: the offset is a pure function of the suit's id, so it
    cannot drift between ticks, does not need seeding, and has nothing to reset. Two
    suits get different angles; one suit gets the same angle for the whole trip."""
def _eva_frame (d):
    """Two unit axes perpendicular to `d`, or None if `d` is too short to have a
    direction. The helper axis is swapped near vertical, or a shaft gets a degenerate
    frame and the whole drift collapses onto one line."""
def _eva_leg_clearance (volume, a, b, samples=7):
    """The tightest clearance along one leg, or None when it cannot be measured.
    
    MEASURED ONCE PER LEG, never per tick. The rail web exists precisely so that flying
    does no geometry, so this is called when a waypoint is reached and the answer is kept
    in inventory until the next one."""
def _eva_places (key, role_name, rail_nodes, relic_rails_ensure, relic_points, relic_point_display, client_id):
    """``[(name, pos, display)]`` - the relic's destinations, from its rail web.
    
    THE WEB, NOT THE AUTHORED POINT LIST, and the difference is the whole of "access to
    other things": a cache placed by a `Starts when:` trigger joins the web when it
    appears (`rail_attach`), so it becomes somewhere the crew can be SENT rather than
    something they have to happen to fly past. `Hidden:` places are left out until they
    are found, and derived waypoints - the stations through a hall, a doorway, the way
    round a pillar - are never offered: they are how you get somewhere, not somewhere to
    go.
    
    Falls back to the authored points when there is no web, which is a relic built in code
    with no volume yet rather than a failure."""
def _eva_room (client_id, ceiling, fraction):
    """A ceiling scaled down to what the CURRENT leg can actually afford.
    
    Falls back to the ceiling when the leg was never measured - a route flown before a
    web existed, or a relic built in code - so this can never make an unmeasured flight
    worse than it was."""
def _eva_rope (here, aim, leg_start, rope=140.0):
    """Pull the aim back toward the leg the suit is supposed to be flying.
    
    A rail leg is KNOWN clear, so it is a far stronger guarantee than "inside the volume
    somewhere" and much cheaper to test. Beyond `RAIL_ROPE` from it, the aim blends toward
    the nearest point ON the leg, so a suit that got knocked wide comes back to the rail
    before it tries to take the next corner from where it ended up."""
def _eva_set_leg (client_id, start, goal, volume):
    """Record the leg being flown AND how much room it has."""
def _pos (thing):
    """An (x, y, z) tuple from an object, an id, a Vec3, or an (x, y, z) already.
    
    Tuples on the way IN as well as out, because a route is a list of them and
    `helm_position` only understands things with `.x` - it would answer None for a
    waypoint, silently, and the suit would simply never move."""
def eva_clear (relic_key=None):
    """Take the party out of its suits - one relic's, or every one.
    
    The LIFEFORMS belong to `boarding.py` and are left alone; this owns only the suits."""
def eva_dest (client_id):
    """The point name this console is flying to, or None."""
def eva_drivers ():
    """Every console that has ever been handed a suit.
    
    The camera's pass walks this rather than `eva_flying`: a console holding station still
    has a camera, and one that stopped mid-relic is exactly when somebody wants to look
    round. Kept on SHARED rather than at module level so the same machinery clears and
    audits it."""
def eva_entry (relic_key=None, offer=None):
    """Where a suit materialises, as (x, y, z).
    
    In order: what the offer said; else the relic's `entrance` point, which is the role
    `universe_relic_contact` already uses for the way in; else the first chamber of its
    volume; else the relic's own origin. Every step is somewhere a suit can legitimately
    be, so this never hands back a spot inside the rock."""
def eva_flying ():
    """Every console with a route running. What the autopilot walks."""
def eva_goto (client_id, point_name, _replan=False):
    """Fly this console's suit to a named place in its relic.
    
    Walks the relic's rail web, which was solved once when the ruin was built, and ends at
    the PLACE rather than at the middle of the room holding it.
    
    Returns:
        bool: False is ordinary - no suit, a name this relic does not have, somewhere the
        suit already is, or a way that is currently barred. `eva_no_way` is what the
        screen shows for the last of those."""
def eva_lifeform_of (suit):
    """Who is inside a suit, or None."""
def eva_my_home (client_id):
    """The ship this console came from, or None."""
def eva_my_relic (client_id):
    """The relic key THIS console is inside, or None."""
def eva_my_suit (client_id):
    """The ship THIS console is flying, or None.
    
    Takes the console explicitly and always will, for the reason `boarding_my_figure`
    does: a signal route runs on the SERVER task, so a fallback to the ambient page would
    answer for the server on every call, silently, for every console at once."""
def eva_my_volume (client_id):
    """The volume name THIS console's relic was built under, or None.
    
    Not the relic key, necessarily. A mission may build a relic under a name of its own,
    and anything that guesses the key instead addresses a volume that does not exist and
    does nothing at all - the defect `relic_volume_name` exists to prevent."""
def eva_no_way (client_id):
    """The place this console last asked for and could not be routed to, or None.
    
    Cleared by the next accepted destination. The Nav app shows it, because a button that
    does nothing when pressed is indistinguishable from a broken screen."""
def eva_offer (relic_key, volume=None, entry=None, side=None, hull=None):
    """Declare the relic a boarding party will suit up into.
    
    Args:
        relic_key: the relic's key, as `relics_load` registered it.
        volume (optional): the volume name, when the mission built it under one of its
            own. **Pass `relic_volume_name(record)` rather than guessing** - a volume
            addressed by the wrong name silently does nothing at all.
        entry (optional): where suits appear. Defaults to the relic's `entrance` point.
        side (optional): the side the suits belong to. Give it one.
        hull (optional): the ship-data key suits are drawn as."""
def eva_offer_clear ():
    """Nobody is going into a relic any more."""
def eva_offered ():
    """The relic on offer, or None. What `eva_relevant` and the suit-up door read."""
def eva_points (client_id, role_name=None, revealed_only=False):
    """The places this console may fly to: ``[(name, display, (x, y, z)), ...]``.
    
    A THREE-TUPLE, and it stays one. Callers DESTRUCTURE this - `for name, label, pos in
    places` - so growing it is not the additive change it looks like; appending two flags
    here broke the Nav app and five tests at once. Where the crew has BEEN is asked for
    separately, with `eva_visited` and `eva_seen`.
    
    Sorted by distance, nearest first - the list is a menu of somewhere to go next, and
    the next place is nearly always a near one.
    
    Args:
        role_name (optional): only points carrying this role.
        revealed_only (bool, optional): hide points the crew has not found yet. **OFF by
            default, and that is a fix rather than a preference** - see below.
    
    HIDING THE UNREVEALED DEADLOCKS THE WHOLE MODE. A marker lights when somebody comes
    within `RELIC_REVEAL_RANGE` (1200) of it, and a shipped relic puts its rooms ~3000
    apart. So the only revealed point is the mouth the SHIP passed on its way in, the Nav
    app offers that one place, and the only way to reveal a second is to fly to it - which
    Nav will not offer. Reported from a bridge twice, as "the nav still only lists the
    mouth" and then "nav Option: The mouth".
    
    The unit tests never saw it: a relic whose contents were never armed has no markers at
    all, `relic_point_revealed` answers True for those, and every test relic is one of
    them. Only an armed, shipped relic deadlocks - which is every relic in Storm's Beacon.
    
    Reveal is still the record of where the crew has BEEN - it is what lights the marker on
    the radar - it is simply not a gate on where they may GO. A suit inside a ruin can see
    the shape of it; that is what sensors are."""
def eva_release (client_id):
    """This console flies nothing."""
def eva_relevant (client_id=None):
    """Whether this console has anything to suit up for.
    
    True while a relic is on offer, or once this console is already out in one. Put it on
    the ROUTE, the way `boarding_relevant` is used - a route's own condition is what ePADD
    tests when it builds the app list."""
def eva_route (client_id):
    """``(destination, waypoints_remaining, distance_to_go)``.
    
    ``(None, 0, 0.0)`` when holding station."""
def eva_route_count ():
    """Reset-ledger probe: consoles still flying a route."""
def eva_seen (client_id, name, relic_key=None):
    """Has this place's marker lit - the crew came near it, without necessarily entering.
    
    Only true for a point that HAS a marker: `relic_point_revealed` answers True for one
    that does not, which would make every place in an unarmed relic read as seen."""
def eva_set_suit_hull (hull):
    """Draw suits as this ship-data key from now on."""
def eva_speed (client_id, name=None):
    """Read, or set, how hard this console flies.
    
    PER CONSOLE, like everything else a boarder owns: six suits in one ruin are six
    people making their own choices about how fast to take a corner.
    
    Args:
        name (str, optional): one of :func:`eva_speeds`. Omit to read.
    
    Returns:
        str: the speed in force."""
def eva_speed_value (client_id):
    """That speed as a throttle."""
def eva_speeds ():
    """The speed names the Nav app offers, slowest first."""
def eva_stop (client_id):
    """Cancel the route and hold station."""
def eva_suit_count ():
    """Reset-ledger probe: suits still in the world."""
def eva_suit_hull ():
    """The ship-data key a suit is drawn as.
    
    A FUNCTION because MAST only sees functions, and overridable because the custom suit
    hull is registered by a mod: a mission that has not declared one still gets a flyable
    suit, drawn as whatever this says."""
def eva_suit_of (lifeform):
    """The suit a party member is flying, or None."""
def eva_suit_spawn (lifeform, relic_key, x, y, z, hull=None, name=None, side=None, volume=None):
    """Put a crew member in a suit, inside a relic, and hand the suit back.
    
    The suit is a PLAYER ship - that is what gets it a 3D view and lets a console be
    assigned to it - but it is not a player.
    
    Args:
        lifeform: the party member wearing it. Cross-linked, both ways.
        relic_key: which relic they are in. Stored so the nav can find its points.
        x, y, z: where to put them. Usually the relic's entrance point.
        hull (optional): the ship-data key the suit is drawn as. Defaults to
            :func:`eva_suit_hull`.
        name (optional): what the suit is called. Defaults to the lifeform's name.
        side (optional): the side it belongs to. **Give it one** - see below.
        volume (optional): the volume name, when it is not the relic key.
    
    Returns:
        The suit object, or None if it could not be spawned."""
def eva_suits (relic_key=None):
    """Every suit, or only the ones in one relic."""
def eva_take (client_id, suit, relic_key, volume=None, home=None):
    """Give this console a suit to fly, in this relic.
    
    Stored on the CLIENT. Read the module docstring before moving it anywhere else."""
def eva_tick (t=None):
    """One steering pass over every routed suit. The autopilot, and all of it.
    
    Runs on ONE shared tick for the whole party rather than a brain per suit - the idiom
    `docking_run_all` and `volume_containment_tick` already use."""
def eva_unwatch ():
    """Stop the autopilot tick."""
def eva_visit_note (client_id, name, relic_key=None):
    """Record that this console's suit has actually been to a place."""
def eva_visited (client_id, name, relic_key=None):
    """Has this console's suit been to this place."""
def eva_visited_names (client_id, relic_key=None):
    """Everywhere this console has been in a relic, in the order it got there."""
def eva_watch (seconds=0.2):
    """Start the autopilot tick. Idempotent - asking twice watches once."""
def eva_where (client_id):
    """The chamber this console's suit is in, in words. "adrift" when there is no suit."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Reaches the server console, for the same reason :func:`add_role` does - and it has
    to be the same set, or a console that could gain a role could never lose it.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
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
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
