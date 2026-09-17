"""A boarding party's SUITS: the body you wear when the place you boarded has no floor.

`boarding_site.py` is the other body model, and the two are deliberately the same shape.
A ship's interior is a grid, so a boarder there is a grid object walking cells. A RELIC has
no interior in that sense - it is a navigable volume of chambers, passages and boxes,
kilometres across, with no engine collision anywhere in it - so there is nothing to walk
on and no grid to build. A boarder there wears a suit, and the suit is a ship they fly.

    boarding_site.py                    eva.py
    ----------------------------        ----------------------------
    a grid object on an interior        a player ship inside a volume
    boarding_walk -> grid_target_pos    eva_goto -> a route through the volume
    the engine pathfinds the cells      eva_tick steers, one waypoint at a time

THE RULE IS THE SAME ONE, and for the same reason: **the body a console is driving lives
on the CLIENT.** Several consoles are in one relic at once, each flying their own suit, and
nothing here is keyed by the relic.

WHY THERE IS NO MANUAL STICK
----------------------------
Flying is by DESTINATION: the device lists the places this relic has, and picking one
flies you there. That is not a simplification of a flight model, it is the answer to the
problem the mode exists to solve. A relic's walls are not walls - `exclusion_radius` is
zero on every prop, so the engine will happily fly a ship straight through the geometry,
and `volume.py`'s containment is a graded RESPONSE to that (scrape, then a throttle
governor, then a tractor hold) rather than a barrier. Steering a route that stays inside
the volume means the response never has to fire.

Two things make the route safe rather than merely reasonable:

* it is planned on the relic's own chamber graph (`volume_path`), so it goes the way the
  ruin actually connects rather than through the rock between two rooms; and
* **every tick the aim point is projected back inside** with `volume_nearest_inside`. The
  plan can be wrong - a relic made of overlapping boxes has no chamber graph to speak of -
  and the projection does not care. It is a hard geometric clamp, not a nudge, so it is
  safe to run on every tick and it is what carries the cases the plan does not.
"""
from ..agent import Agent
from .inventory import get_inventory_value, set_inventory_value
from .links import link, linked_to, unlink
from .query import to_id, to_object
from .roles import remove_role, role

#: The role a suit wears, so a route or a query can tell one from a real player ship.
SUIT_ROLE = "eva_suit"

# On the CLIENT. The whole design is these keys not being on the relic.
KEY_SUIT = "EVA_SUIT"        # the ship this console is flying
KEY_RELIC = "EVA_RELIC"      # the relic key it is flying inside
KEY_VOLUME = "EVA_VOLUME"    # that relic's volume name - resolved once, not guessed
KEY_ROUTE = "EVA_ROUTE"      # waypoints still to fly, world (x, y, z)
KEY_DEST = "EVA_DEST"        # the point name that route is heading for
KEY_HOME = "EVA_HOME"        # the ship to put the console back on
KEY_STALL = "EVA_STALL"      # ticks since the gap to the next waypoint last shrank
KEY_GAP = "EVA_GAP"          # what that gap was
KEY_REPLAN = "EVA_REPLAN"    # how many times this route has been re-planned
KEY_NOWAY = "EVA_NOWAY"      # a place the router could not reach, so the app can say so
KEY_SPEED = "EVA_SPEED"      # how hard this console flies: a key into SPEEDS

# Consoles ever handed a suit, so a reset can let go of all of them without walking every
# agent. On SHARED rather than at module level, so the same machinery clears and audits it.
_DRIVERS_KEY = "__EVA_DRIVERS__"
_TICK_KEY = "__EVA_TICK__"
_OFFER_KEY = "__EVA_OFFER__"

#: How close counts as arrived at a waypoint. Generous, because a waypoint is a chamber
#: CENTRE and the point of it is the doorway it leads to, not the spot itself.
ARRIVE_RADIUS = 120.0

#: How close counts as arrived at the actual destination.
DEST_RADIUS = 60.0

#: How far inside the wall the route keeps its aim point, and how much clearance a leg
#: must have to count as flyable.
#:
#: A SUIT IS A PERSON, NOT A CRUISER, and this was set at a cruiser's 40 out of habit. A
#: relic doorway can be thin: `false_choir`'s throat meets its concourse in a slab 50
#: units deep, and asking for 40 of clearance inside a 50-unit slab asks for a point that
#: cannot exist - the router then declared the way in impassable and flew the straight
#: line instead. 20 is still most of a suit's length clear of the wall.
ROUTE_MARGIN = 20.0

#: How little clearance counts as "against the wall", at which point the autopilot stops
#: flying the route and starts flying away from the rock. Below this the aim is bent
#: toward the inside of the volume in proportion to how close the wall is.
CLEAR_MIN = 45.0

#: Throttle for a suit under way, and the distance over which it eases off. A suit is not
#: a cruiser: `helm_throttle` is hull-independent on the player path, so this is the whole
#: speed control there is.
CRUISE = 0.25
APPROACH = 400.0

#: What the Nav app's speed control offers, slowest first: ``name -> throttle``.
#:
#: THREE, NOT A SLIDER. The choice a boarder actually makes is "pick through this" or
#: "get there" - a continuous control invites fiddling with a number whose units mean
#: nothing to anyone. Owner-asked from a bridge: "NAV may need a few speeds."
#:
#: `Cruise` IS `CRUISE`, so a console that never touches the control flies exactly as it
#: always did. `Careful` is for a tight passage and a relic you do not trust; `Fast` is
#: the long empty run back down a shaft you have already flown, and it is deliberately
#: not double - the turn cap still governs the corners, and a suit that arrives at a
#: doorway too fast simply spends the time turning instead.
SPEEDS = (("Careful", 0.12), ("Cruise", CRUISE), ("Fast", 0.45))

#: How well the nose must already be pointed before the throttle opens up, as the cosine
#: of the angle to the aim: 1.0 is dead ahead, 0.0 is square on.
#:
#: THIS IS WHAT KEEPS A SUIT OFF THE WALLS, and it was not obvious. Planning a route
#: through the chambers is not enough on its own, because a ship does not turn instantly:
#: measured in the mock, a suit leaving the entrance chamber under full route throttle
#: ARCED while it came round to its first waypoint and left the volume entirely
#: (`volume_depth` +41 at 20s, in a 160-unit passage). It was flying a perfectly correct
#: course and still ended up outside.
#:
#: So the throttle is scaled by alignment, which is how anybody flies a tunnel: point
#: first, then accelerate. Below the threshold the suit creeps at `TURN_CREEP` and spends
#: the time turning - steering is independent of speed, so it comes round on the spot.
#: A SMOOTH CURVE, NOT A GATE. The first version refused to open the throttle at all below
#: 0.86 and crept at a flat 0.04 - which is right for a gentle elbow and wrong for a real
#: ruin: flown down `voice.amd`'s vertical shaft the suit had to point almost straight
#: down, never satisfied the gate, and crawled 150 units a minute without ever arriving.
#: Squaring the alignment keeps the important half (badly pointed means slow) without the
#: cliff, and the floor is what guarantees it always makes way while it comes round.
#: The absolute floor, and it is tiny on purpose - enough that a suit which genuinely
#: cannot point at its waypoint (a near-vertical shaft against a slow pitch rate) still
#: creeps there instead of hanging forever, slow enough that the creep cannot cross a
#: passage sideways while it happens.
THROTTLE_FLOOR = 0.02

#: How well pointed a suit must be before it moves AT ALL. Not a refinement - it is the
#: whole of not clipping a corner. A ship traces an ARC while it turns, and a shuttle
#: takes about 25 seconds to come through a right angle: even the anti-deadlock creep of
#: 3.6 units a second carries it 90 units sideways in that time, which is more than the
#: half-width of every passage in the shipped relics. Steering costs no throttle, so the
#: suit simply turns on the spot and then goes.
ALIGN_GO = 0.9

#: Speed is also capped by how much room there is: never outrun your clearance. Distance
#: to the nearest wall, over this, is the cap - so a suit is quick down the middle of a
#: hall and careful in a passage, without knowing which it is in. This is the half that
#: replaces the hard alignment gate as the thing keeping it off the walls.
CLEAR_FULL = 260.0

#: A ROUTE CAN GO STALE UNDER THE SHIP. Containment is a graded response, not a barrier,
#: so a suit that grazes a wall is clamped back inside - and it can land in a different
#: part of the volume from the one the route was planned through. It then flies at a
#: waypoint on the far side of a wall forever, held off it by the clamp, making no
#: progress and reporting no error. Re-planning from where it ACTUALLY is costs one BFS
#: and is what an autopilot is supposed to do when the world has moved.
#: Progress is measured against the BEST gap seen since the counter last reset, not
#: against the previous tick. A suit covers about a unit per tick, so a per-tick test
#: reads as permanently stalled and re-plans a perfectly good route to death.
#: Stalled means NO progress at all, not slow progress. A suit closes about a unit a
#: tick, so a threshold of any size re-plans perfectly good flying to death - which it
#: did, four times on a two-legged route. One unit in ten seconds is the difference
#: between "crawling" and "held off a wall".
STALL_TICKS = 50             # ~10s at the 0.2s tick
STALL_EPS = 1.0
REPLAN_LIMIT = 6


def _client(client_id=None):
    from ..helpers import FrameContext
    if client_id is not None:
        return client_id
    page = FrameContext.page
    return getattr(page, "client_id", None) if page is not None else None


def _pos(thing):
    """An (x, y, z) tuple from an object, an id, a Vec3, or an (x, y, z) already.

    Tuples on the way IN as well as out, because a route is a list of them and
    `helm_position` only understands things with `.x` - it would answer None for a
    waypoint, silently, and the suit would simply never move.
    """
    from .helm import helm_position
    if isinstance(thing, (tuple, list)) and len(thing) >= 3:
        return (float(thing[0]), float(thing[1]), float(thing[2]))
    p = helm_position(thing)
    if p is None:
        return None
    return (float(p.x), float(p.y), float(p.z))


def _alignment(suit, here, aim):
    """Cosine of the angle between the suit's nose and the way it wants to go.

    1.0 when the heading cannot be read - an unknown alignment must not stop the suit,
    or a hull whose facing this cannot see would never move at all.
    """
    from .query import to_object
    obj = to_object(suit)
    try:
        f = obj.engine_object.forward_vector()
        fwd = (f.x, f.y, f.z)
    except Exception:                                    # noqa: BLE001
        return 1.0
    want = (aim[0] - here[0], aim[1] - here[1], aim[2] - here[2])
    fl = (fwd[0] ** 2 + fwd[1] ** 2 + fwd[2] ** 2) ** 0.5
    wl = (want[0] ** 2 + want[1] ** 2 + want[2] ** 2) ** 0.5
    if fl < 1e-6 or wl < 1e-6:
        return 1.0
    dot = (fwd[0] * want[0] + fwd[1] * want[1] + fwd[2] * want[2]) / (fl * wl)
    return max(-1.0, min(1.0, dot))


def _dist(a, b):
    if a is None or b is None:
        return float("inf")
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


# --- the relic on offer -----------------------------------------------------------------
#
# `boarding.py`'s invitation carries a `site=` - the interior the party will walk - which
# is what lets the shipped BEAM DOWN button put somebody on a floor without knowing a
# floor exists. A relic is not an object with an interior, it is a VOLUME and a key, so it
# needs its own word. This is that word, and it is deliberately the same shape: the
# mission says where once, and every console suiting up reads it.

def eva_offer(relic_key, volume=None, entry=None, side=None, hull=None):
    """Declare the relic a boarding party will suit up into.

    Args:
        relic_key: the relic's key, as `relics_load` registered it.
        volume (optional): the volume name, when the mission built it under one of its
            own. **Pass `relic_volume_name(record)` rather than guessing** - a volume
            addressed by the wrong name silently does nothing at all.
        entry (optional): where suits appear. Defaults to the relic's `entrance` point.
        side (optional): the side the suits belong to. Give it one.
        hull (optional): the ship-data key suits are drawn as.
    """
    Agent.SHARED.set_inventory_value(_OFFER_KEY, {
        "relic": relic_key, "volume": volume or relic_key,
        "entry": tuple(entry) if entry else None, "side": side, "hull": hull})
    return relic_key


def eva_offered():
    """The relic on offer, or None. What `eva_relevant` and the suit-up door read."""
    return Agent.SHARED.get_inventory_value(_OFFER_KEY, None)


def eva_offer_clear():
    """Nobody is going into a relic any more."""
    Agent.SHARED.set_inventory_value(_OFFER_KEY, None)


def eva_relevant(client_id=None):
    """Whether this console has anything to suit up for.

    True while a relic is on offer, or once this console is already out in one. Put it on
    the ROUTE, the way `boarding_relevant` is used - a route's own condition is what ePADD
    tests when it builds the app list.
    """
    if eva_offered() is not None:
        return True
    cid = _client(client_id)
    return bool(cid is not None and eva_my_suit(cid) is not None)


def eva_entry(relic_key=None, offer=None):
    """Where a suit materialises, as (x, y, z).

    In order: what the offer said; else the relic's `entrance` point, which is the role
    `universe_relic_contact` already uses for the way in; else the first chamber of its
    volume; else the relic's own origin. Every step is somewhere a suit can legitimately
    be, so this never hands back a spot inside the rock.
    """
    from .amd_relics import relic_pos, relic_record, relic_points
    from .volume import volume_chamber_pos, volume_get
    from .volume import volume_nearest_inside
    offer = offer if offer is not None else (eva_offered() or {})
    key = relic_key or offer.get("relic")

    def _inside(p):
        """Nudge a point into the navigable space before anybody is put there.

        THE AUTHORED `entrance` IS OUTSIDE THE RELIC, and that is correct - it is the
        sensor contact at the mouth, what the crew see first from a long way off.
        Measured across Storm's Beacon's seven relics, every one of them sits 100 to 300
        units out in the rock. Taking it literally materialises a suit inside a wall.
        """
        vol = offer.get("volume") or key
        return tuple(volume_nearest_inside(vol, p, ROUTE_MARGIN) or p)

    if offer.get("entry"):
        return _inside(tuple(offer["entry"]))
    if not key:
        return (0.0, 0.0, 0.0)
    ways_in = relic_points(key, "entrance") or {}
    if ways_in:
        return _inside(tuple(next(iter(ways_in.values()))))
    vol = volume_get(offer.get("volume") or key)
    if vol is not None and getattr(vol, "chambers", None):
        pos = volume_chamber_pos(vol, next(iter(vol.chambers)))
        if pos is not None:
            return _inside(tuple(pos))
    rec = relic_record(key)
    return tuple(relic_pos(rec)) if rec is not None else (0.0, 0.0, 0.0)


# --- the suit -------------------------------------------------------------------------

def eva_suit_spawn(lifeform, relic_key, x, y, z, hull=None, name=None, side=None,
                   volume=None):
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
        The suit object, or None if it could not be spawned.
    """
    from .spawn import player_spawn
    who = to_object(lifeform)
    label = name or (getattr(who, "name", None) if who is not None else None) or "EVA"
    suit = to_object(player_spawn(x, y, z, label, "#," + SUIT_ROLE,
                                  hull or eva_suit_hull()))
    if suit is None:
        return None

    # THE ONE THING KEEPING A SUIT OUT OF EVERY role("__player__") QUERY - NPC targeting,
    # scoring, the end-game conditions, the ship pickers. Six boarders would otherwise read
    # as six more player ships that the enemy will shoot at and the win condition counts.
    # (`director_cam.py` carries the same line for the same reason.)
    remove_role(suit, "__player__")

    # A SIDE, OR SCANS AND DIPLOMACY SILENTLY DO NOTHING. `player_spawn(..., "#,...")`
    # means roles only, no side; with an empty side there is no relation to compare, so
    # every contact draws unknown and scan data lands in a slot nothing reads back.
    if side:
        suit.side = side

    if who is not None:
        link(to_id(who), "suit", to_id(suit))
        link(to_id(suit), "lifeform", to_id(who))
    set_inventory_value(to_id(suit), KEY_RELIC, relic_key)
    set_inventory_value(to_id(suit), KEY_VOLUME, volume or relic_key)
    return suit


def eva_suit_hull():
    """The ship-data key a suit is drawn as.

    A FUNCTION because MAST only sees functions, and overridable because the custom suit
    hull is registered by a mod: a mission that has not declared one still gets a flyable
    suit, drawn as whatever this says.
    """
    # `tsn_shuttle`, NOT "shuttle" - the latter is not a ship-data key, and a hull key the
    # engine does not know draws the unknown placeholder rather than failing.
    return Agent.SHARED.get_inventory_value("__EVA_HULL__", None) or "tsn_shuttle"


def eva_set_suit_hull(hull):
    """Draw suits as this ship-data key from now on."""
    Agent.SHARED.set_inventory_value("__EVA_HULL__", hull)
    return hull


def eva_suit_of(lifeform):
    """The suit a party member is flying, or None."""
    for suit in linked_to(lifeform, "suit"):
        return suit
    return None


def eva_lifeform_of(suit):
    """Who is inside a suit, or None."""
    for who in linked_to(suit, "lifeform"):
        return who
    return None


# --- which console flies which suit ---------------------------------------------------

def eva_take(client_id, suit, relic_key, volume=None, home=None):
    """Give this console a suit to fly, in this relic.

    Stored on the CLIENT. Read the module docstring before moving it anywhere else.
    """
    set_inventory_value(client_id, KEY_SUIT, to_id(suit))
    set_inventory_value(client_id, KEY_RELIC, relic_key)
    set_inventory_value(client_id, KEY_VOLUME, volume or relic_key)
    if home is not None:
        set_inventory_value(client_id, KEY_HOME, to_id(home))
    seen = set(Agent.SHARED.get_inventory_value(_DRIVERS_KEY, set()) or set())
    seen.add(to_id(client_id))
    Agent.SHARED.set_inventory_value(_DRIVERS_KEY, seen)


def eva_release(client_id):
    """This console flies nothing."""
    eva_stop(client_id)
    # EVERY per-console key, the choices included. A console's speed and its last refused
    # destination are decisions it made about THIS trip into THIS ruin - carrying either
    # into the next one hands somebody a suit that flies differently for no reason they
    # can see, and the reused-interpreter trap makes that a run-2 mystery.
    for key in (KEY_SUIT, KEY_RELIC, KEY_VOLUME, KEY_HOME, KEY_STALL, KEY_GAP,
                KEY_REPLAN, KEY_NOWAY, KEY_SPEED):
        set_inventory_value(client_id, key, None)


def eva_my_suit(client_id):
    """The ship THIS console is flying, or None.

    Takes the console explicitly and always will, for the reason `boarding_my_figure`
    does: a signal route runs on the SERVER task, so a fallback to the ambient page would
    answer for the server on every call, silently, for every console at once.
    """
    return get_inventory_value(client_id, KEY_SUIT, None)


def eva_my_relic(client_id):
    """The relic key THIS console is inside, or None."""
    return get_inventory_value(client_id, KEY_RELIC, None)


def eva_my_volume(client_id):
    """The volume name THIS console's relic was built under, or None.

    Not the relic key, necessarily. A mission may build a relic under a name of its own,
    and anything that guesses the key instead addresses a volume that does not exist and
    does nothing at all - the defect `relic_volume_name` exists to prevent.
    """
    return get_inventory_value(client_id, KEY_VOLUME, None)


def eva_my_home(client_id):
    """The ship this console came from, or None."""
    return get_inventory_value(client_id, KEY_HOME, None)


def eva_suits(relic_key=None):
    """Every suit, or only the ones in one relic."""
    suits = set(role(SUIT_ROLE))
    if relic_key is None:
        return suits
    return {s for s in suits if get_inventory_value(s, KEY_RELIC, None) == relic_key}


# --- where you can go -----------------------------------------------------------------

def eva_points(client_id, role_name=None, revealed_only=False):
    """The places this console may fly to: ``[(name, display, (x, y, z)), ...]``.

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
    the shape of it; that is what sensors are.
    """
    from .amd_relics import relic_point_display, relic_point_revealed, relic_points
    key = eva_my_relic(client_id)
    if not key:
        return []
    here = _pos(eva_my_suit(client_id))
    out = []
    for name, pos in (relic_points(key, role_name) or {}).items():
        if revealed_only and not relic_point_revealed(key, name):
            continue
        # NOT WHERE YOU ALREADY ARE. Offering it reads as a destination and behaves like
        # a glitch: picking it sets a course, the screen grows an "Under way" row and a
        # Hold station button, and the very next tick notices you are inside the arrival
        # radius and takes them away again. Two buttons, then one, for no reason a player
        # can see. You cannot fly to where you are standing.
        if here is not None and _dist(here, pos) <= DEST_RADIUS:
            continue
        out.append((name, relic_point_display(key, name), pos))
    out.sort(key=lambda row: _dist(here, row[2]))
    return out


def eva_where(client_id):
    """The chamber this console's suit is in, in words. "adrift" when there is no suit."""
    from .volume import volume_chamber_at
    here = _pos(eva_my_suit(client_id))
    if here is None:
        return "adrift"
    return volume_chamber_at(eva_my_volume(client_id), here) or "open space"


# --- flying there ---------------------------------------------------------------------

def eva_goto(client_id, point_name, _replan=False):
    """Fly this console's suit to a named point in its relic.

    Plans on the relic's chamber graph, then keeps the destination as the last waypoint so
    the route ends at the PLACE rather than at the middle of the room holding it.

    Returns:
        bool: False is ordinary - no suit, or a name this relic does not have.
    """
    from .amd_relics import relic_point, relic_points
    from .volume import (volume_doorways, volume_nearest_inside, volume_route,
                     volume_skirts)
    suit = eva_my_suit(client_id)
    key = eva_my_relic(client_id)
    if not suit or not key:
        return False
    goal = relic_point(key, point_name)
    if goal is None:
        return False
    here = _pos(suit)
    # Already there: say so rather than flapping a one-tick route through the screen.
    if here is not None and _dist(here, goal) <= DEST_RADIUS:
        return False

    # THE RELIC'S OWN PLACES ARE THE ROUTE. Every relic names its rooms with `Point:`,
    # one to a room, chosen by somebody who knows the ruin - so the router flies between
    # those rather than trying to infer a path from the geometry. Two geometric routers
    # were tried first (the authored chamber graph, then measured doorways between every
    # primitive) and the ruins beat both: long thin boxes, vertical shafts and subtracted
    # masses. This also makes a route explicable - "the shaft head, then the bay floor".
    # PROJECT EVERY PLACE INSIDE FIRST. An authored point is a label on a room, not a
    # promise that a ship fits there: the `entrance` markers sit out in open space by
    # design, and others sit on a wall. A waypoint outside the volume can see nothing, so
    # it contributes no edges and the graph silently collapses to a straight line.
    vol = eva_my_volume(client_id)
    # PLACES AND DOORWAYS BOTH. The places are where a person wants to go; the doorways
    # are the only spots from which the next room is in view. Measured on `voice.amd`:
    # eight authored rooms whose places see one another exactly once, because neighbours
    # meet in a slab a hundred units deep that the line between two room centres clips the
    # corner of. With both, every leg is short and straight - room, door, next room.
    places = []
    # PLACES, DOORWAYS AND SKIRTS. Places are where a person wants to go; doorways are
    # the only spots from which the next room is in view; skirts get a route around a
    # subtracted mass standing in the middle of a room. Leave any one out and some part of
    # a real ruin becomes unreachable - each of the three was added because a Storm's
    # Beacon relic could not be flown without it.
    for p in (list((relic_points(key) or {}).values())
              + list(volume_doorways(vol)) + list(volume_skirts(vol))):
        inside = volume_nearest_inside(vol, p, ROUTE_MARGIN)
        if inside is not None:
            places.append(tuple(inside))
    # THE DESTINATION GETS PROJECTED IN TOO. An authored point is a label on a room and
    # several of them sit in the wall - a marker off the room's centre, a cache against a
    # face. Nothing inside the volume can see a point outside it, so an unprojected goal
    # leaves the router with nowhere to finish and it falls back to a straight line
    # through the ruin. Measured: five of Storm's Beacon's seven relics did exactly that.
    goal = tuple(volume_nearest_inside(vol, goal, ROUTE_MARGIN) or goal)
    # THE START GETS PROJECTED IN TOO. A suit is allowed to scrape - the containment
    # governor lets it touch a wall and pulls it back - so `here` is sometimes a few units
    # OUTSIDE, and a start outside the volume can see no waypoint at all. The router then
    # had nothing to begin from and answered with the straight line.
    start = tuple(volume_nearest_inside(vol, here, ROUTE_MARGIN) or here)
    route = [tuple(p) for p in volume_route(vol, start, goal, waypoints=places,
                                            margin=ROUTE_MARGIN, strict=True)]
    if not route:
        # NO ROUTE MEANS NO TRIP. A relic has no engine collision, so flying the straight
        # line to an unreachable room means flying THROUGH the ruin - which is the one
        # failure this whole mode exists to prevent, and it looked from the bridge like
        # the router was simply not being used. Refusing is honest and visible: the Nav
        # app says so, and the suit stays where it is.
        set_inventory_value(client_id, KEY_NOWAY, point_name)
        from .execution import log
        log(f"no route to '{point_name}' in relic '{key}' - the suit stays put. Either "
            f"the relic is not joined up there, or the doorway is tighter than the "
            f"{ROUTE_MARGIN:.0f}-unit margin a suit asks for.", "eva", "warning")
        return False
    set_inventory_value(client_id, KEY_NOWAY, None)
    # DROP A WAYPOINT WE ARE ALREADY STANDING ON. A degenerate first leg makes the aim
    # vector zero-length, and `_alignment` answers its neutral 1.0 for that - so the turn
    # cap silently switched itself off for exactly the moment the suit was turning, and it
    # drifted out of the chamber sideways while reporting perfect alignment.
    while len(route) > 1 and _dist(here, route[0]) < ARRIVE_RADIUS:
        route.pop(0)

    set_inventory_value(client_id, KEY_ROUTE, route)
    set_inventory_value(client_id, KEY_DEST, point_name)
    set_inventory_value(client_id, KEY_STALL, 0)
    set_inventory_value(client_id, KEY_GAP, None)
    if not _replan:
        set_inventory_value(client_id, KEY_REPLAN, 0)
    eva_watch()
    return True


def eva_stop(client_id):
    """Cancel the route and hold station."""
    from .helm import helm_stop
    set_inventory_value(client_id, KEY_ROUTE, None)
    set_inventory_value(client_id, KEY_DEST, None)
    set_inventory_value(client_id, KEY_STALL, 0)
    set_inventory_value(client_id, KEY_GAP, None)
    suit = eva_my_suit(client_id)
    if suit:
        helm_stop(suit)
    return True


def eva_dest(client_id):
    """The point name this console is flying to, or None."""
    return get_inventory_value(client_id, KEY_DEST, None)


def eva_route(client_id):
    """``(destination, waypoints_remaining, distance_to_go)``.

    ``(None, 0, 0.0)`` when holding station.
    """
    dest = eva_dest(client_id)
    route = get_inventory_value(client_id, KEY_ROUTE, None) or []
    if not dest or not route:
        return (None, 0, 0.0)
    return (dest, len(route), _dist(_pos(eva_my_suit(client_id)), route[-1]))


def eva_flying():
    """Every console with a route running. What the tick walks."""
    out = []
    for cid in list(Agent.SHARED.get_inventory_value(_DRIVERS_KEY, set()) or set()):
        if get_inventory_value(cid, KEY_ROUTE, None):
            out.append(cid)
    return out


def eva_tick(t=None):
    """One steering pass over every routed suit. The autopilot, and all of it.

    Runs on ONE shared tick for the whole party rather than a brain per suit - the idiom
    `docking_run_all` and `volume_containment_tick` already use.
    """
    from .helm import helm_steer_to_vec, helm_stop, helm_throttle
    from .signal import signal_emit
    from .volume import volume_depth, volume_nearest_inside
    for cid in eva_flying():
        suit = eva_my_suit(cid)
        here = _pos(suit)
        route = list(get_inventory_value(cid, KEY_ROUTE, None) or [])
        if suit is None or here is None or not route:
            eva_stop(cid)
            continue

        last = len(route) == 1
        gap = _dist(here, route[0])

        # HOLDING STATION TO TURN IS NOT A STALL, and conflating the two re-planned a
        # perfectly good route every time the suit stopped to come round a corner. The
        # counter only runs while the suit is actually trying to fly.
        flying = _alignment(suit, here, route[0]) >= ALIGN_GO
        best = get_inventory_value(cid, KEY_GAP, None)
        if not flying:
            stalled = (get_inventory_value(cid, KEY_STALL, 0) or 0) + 1
            set_inventory_value(cid, KEY_STALL, stalled)
            turning = stalled
            stalled = 0
        elif best is None or best - gap >= STALL_EPS:
            stalled = turning = 0
            set_inventory_value(cid, KEY_GAP, gap)
            set_inventory_value(cid, KEY_STALL, 0)
        else:
            stalled = turning = (get_inventory_value(cid, KEY_STALL, 0) or 0) + 1
            set_inventory_value(cid, KEY_STALL, stalled)
        if stalled >= STALL_TICKS:
            tries = (get_inventory_value(cid, KEY_REPLAN, 0) or 0)
            dest = eva_dest(cid)
            set_inventory_value(cid, KEY_STALL, 0)
            if dest and tries < REPLAN_LIMIT:
                set_inventory_value(cid, KEY_REPLAN, tries + 1)
                eva_goto(cid, dest, _replan=True)
                continue
            # Out of tries: stop rather than grind at a wall forever, and say so.
            signal_emit("eva_stuck", {"EVA_CLIENT": cid, "EVA_SUIT": suit,
                                      "EVA_RELIC": eva_my_relic(cid),
                                      "EVA_POINT": dest})
            eva_stop(cid)
            continue

        if gap <= (DEST_RADIUS if last else ARRIVE_RADIUS):
            route.pop(0)
            set_inventory_value(cid, KEY_ROUTE, route)
            if not route:
                dest = eva_dest(cid)
                helm_stop(suit)
                set_inventory_value(cid, KEY_DEST, None)
                signal_emit("eva_arrived", {"EVA_CLIENT": cid, "EVA_SUIT": suit,
                                            "EVA_RELIC": eva_my_relic(cid),
                                            "EVA_POINT": dest})
                continue
            gap = _dist(here, route[0])

        # THE CLAMP, AND IT IS THE SAFETY. Aim at the waypoint, but project the aim back
        # inside the volume first: the plan can be wrong - a relic of overlapping boxes has
        # no chamber graph worth the name - and this does not depend on the plan being
        # right. `volume_nearest_inside` is a hard geometric projection and returns the
        # point unchanged when it is already inside, so it is safe every tick.
        aim = _pos(volume_nearest_inside(eva_my_volume(cid), route[0],
                                         ROUTE_MARGIN)) or route[0]

        # AND WHEN THE WALL IS CLOSE, AIM OFF IT. The projection above fixes a bad
        # waypoint; it does nothing about a suit that is on a perfectly good course and
        # simply carrying too much way through a corner. A suit does not stop dead - the
        # engine eases speed with a lag - so cutting the throttle at the turn still lets
        # it coast wide, and a relic passage is 60 units of radius. Measured on the elbow
        # arena: out of the volume at the hall-to-cradle corner, on a correct two-leg
        # route, 105 seconds in.
        #
        # So the aim BENDS toward the inside as clearance runs out: full waypoint out in
        # the open, mostly-inward against a wall. It is the same `volume_nearest_inside`
        # projection, applied to where the suit IS rather than to where it is going, which
        # keeps this one geometric idea rather than two.
        room_now = -volume_depth(eva_my_volume(cid), here)
        if room_now < CLEAR_MIN:
            safe = _pos(volume_nearest_inside(eva_my_volume(cid), here, CLEAR_FULL))
            if safe is not None and _dist(safe, here) > 1.0:
                # 0 at CLEAR_MIN, 1 when the hull is on the wall.
                w = min(1.0, max(0.0, (CLEAR_MIN - room_now) / max(1.0, CLEAR_MIN)))
                aim = tuple(aim[i] * (1.0 - w) + safe[i] * w for i in range(3))
        # `helm_steer_to_vec` with the delta, not `helm_steer_to_point` with the point:
        # the aim is a tuple, and `helm_position` only understands things with `.x`.
        helm_steer_to_vec(suit, aim[0] - here[0], aim[1] - here[1], aim[2] - here[2])

        # THREE CAPS, AND THE SLOWEST WINS. Distance left is the obvious one; the other
        # two are what keep a suit off the walls of a real ruin.
        #
        #   near  - ease off as the waypoint comes up
        #   turn  - point first, then accelerate. A ship does not turn instantly, and at
        #           speed its arc is wider than a relic passage.
        #   clear - never outrun your clearance. `volume_depth` is negative inside, so
        #           this is simply how much room there is on the nearest side.
        # THEY MULTIPLY, they do not compete. Taking the smallest of the three let a suit
        # that was badly pointed AND in a tight passage still run at the better of the two
        # - which is exactly the case that puts it through a wall. Compounding them means
        # the worst case is slowest, which is the behaviour wanted.
        near = min(1.0, max(0.15, gap / APPROACH))
        align = _alignment(suit, here, aim)
        turn = max(0.0, align) ** 2
        room = -volume_depth(eva_my_volume(cid), here)
        clear = min(1.0, max(0.0, room) / CLEAR_FULL)
        # THE CONSOLE'S CHOSEN SPEED SCALES ALL THREE CAPS - it does not bypass them. A
        # `Fast` suit still points before it accelerates and still slows for a tight
        # passage; it simply covers a cleared run quicker.
        cruise = eva_speed_value(cid)
        if align >= ALIGN_GO:
            helm_throttle(suit, cruise * max(THROTTLE_FLOOR, near * turn * clear),
                          allow_warp=False)
        elif turning > STALL_TICKS:
            # It has been trying to come round for a while and cannot - a near-vertical
            # shaft against a slow pitch rate. Creep, rather than hang here forever.
            helm_throttle(suit, cruise * THROTTLE_FLOOR, allow_warp=False)
        else:
            helm_throttle(suit, 0.0, allow_warp=False)
    return True


def eva_speeds():
    """The speed names the Nav app offers, slowest first."""
    return [name for name, _v in SPEEDS]


def eva_speed(client_id, name=None):
    """Read, or set, how hard this console flies.

    PER CONSOLE, like everything else a boarder owns: six suits in one ruin are six
    people making their own choices about how fast to take a corner.

    Args:
        name (str, optional): one of :func:`eva_speeds`. Omit to read.

    Returns:
        str: the speed in force.
    """
    if name is not None:
        for known, _v in SPEEDS:
            if str(name).lower() == known.lower():
                set_inventory_value(client_id, KEY_SPEED, known)
                break
    got = get_inventory_value(client_id, KEY_SPEED, None)
    return got if got in eva_speeds() else SPEEDS[1][0]


def eva_speed_value(client_id):
    """That speed as a throttle."""
    want = eva_speed(client_id)
    for name, value in SPEEDS:
        if name == want:
            return value
    return CRUISE


def eva_no_way(client_id):
    """The place this console last asked for and could not be routed to, or None.

    Cleared by the next accepted destination. The Nav app shows it, because a button that
    does nothing when pressed is indistinguishable from a broken screen.
    """
    return get_inventory_value(client_id, KEY_NOWAY, None)


def eva_watch(seconds=0.2):
    """Start the autopilot tick. Idempotent - asking twice watches once."""
    from ..tickdispatcher import TickDispatcher
    task = Agent.SHARED.get_inventory_value(_TICK_KEY, None)
    if task is not None:
        return task
    task = TickDispatcher.do_interval(eva_tick, seconds)
    Agent.SHARED.set_inventory_value(_TICK_KEY, task)
    return task


def eva_unwatch():
    """Stop the autopilot tick."""
    task = Agent.SHARED.get_inventory_value(_TICK_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:
            # A task the dispatcher already dropped is not an error - the mission ended,
            # or a reset took it. Nothing to stop and nothing to say.
            pass
    Agent.SHARED.set_inventory_value(_TICK_KEY, None)


# --- teardown -------------------------------------------------------------------------

def eva_clear(relic_key=None):
    """Take the party out of its suits - one relic's, or every one.

    The LIFEFORMS belong to `boarding.py` and are left alone; this owns only the suits.
    """
    from .space_objects import delete_object
    for suit in list(eva_suits(relic_key)):
        who = eva_lifeform_of(suit)
        if who:
            # Both directions. The suit is about to go, but the lifeform survives - it is
            # `boarding.py`'s - and a stale "suit" link on it would hand the next screen a
            # dead ship id.
            unlink(who, "suit", suit)
            unlink(suit, "lifeform", who)
        try:
            delete_object(suit)
        except Exception:
            pass
    if relic_key is None:
        for cid in list(Agent.SHARED.get_inventory_value(_DRIVERS_KEY, set()) or set()):
            eva_release(cid)
        Agent.SHARED.set_inventory_value(_DRIVERS_KEY, set())
        eva_offer_clear()
        eva_unwatch()


def eva_suit_count():
    """Reset-ledger probe: suits still in the world."""
    return len(role(SUIT_ROLE))


def eva_route_count():
    """Reset-ledger probe: consoles still flying a route."""
    return len(eva_flying())
