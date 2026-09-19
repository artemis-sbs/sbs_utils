def _rail_attach_points (vol, web, pos, margin, open_only, recover=True):
    """The nodes a route may start from: the nearest few that can actually be seen.
    
    ``recover`` IS WHAT MAKES A SUIT IN A WALL RESCUABLE. Visibility is measured from
    where the ship is, and from inside solid rock nothing is visible at all - so a suit
    that ended up in the plating attached to nothing, got an empty route, and was told
    "no way through". That was survivable only because containment dragged it out.
    Containment no longer watches suits (see `_vol_default_agents`), so the router has to
    answer instead: project the position to the nearest legal point and attach from
    there, which makes the first leg fly OUT of the rock.
    
    Tried only after the honest attempt fails, so a normal route is unaffected and pays
    nothing for it."""
def _rail_bridge (vol, web, comps, margin, tries=40):
    """Join split components with the closest cross pair that can actually see each other.
    
    A denser web that is not JOINED UP is worse than the coarse one it replaces, and the
    bucketed edge pass deliberately refuses long edges - so a legitimate long hop (a
    doorway a room away from anything else) can be missed. This looks for one explicitly,
    and only between components, so it costs nothing on a relic that is already whole."""
def _rail_bucket (nodes, order, span):
    """Uniform grid over the nodes, keyed on the edge span.
    
    This is what makes the edge pass affordable: a node only ever looks at its own bucket
    and the twenty-six around it, so the pass is linear in node count rather than square."""
def _rail_cell (pos, grid):
    ...
def _rail_center (vol, pos, lane, rounds=4):
    """Walk a node toward the middle of the space it is in.
    
    A spine seed is a point on a LATTICE through a room, and `volume_nearest_inside` only
    guarantees it is legal - so a seed that lands in a pillar comes back pressed against
    that pillar's surface, and a seed near a face stays near the face. Routes then run
    through those nodes, which is half of why they hug the geometry.
    
    A coarse hill-climb, not a medial-axis transform: six axis probes, best one wins, reach
    halves each round. It cannot leave the volume, because a probe is only taken when it is
    an improvement and the clearance of an outside point is negative.
    
    STOPS AT `lane` RATHER THAN MAXIMISING. The middle of a big hall is not a better
    station than a point comfortably clear of everything - it is just further from where
    anyone wants to go, and pushing every node to the centroid collapses a wide room back
    to the single crossing this web exists to avoid."""
def _rail_clearance (vol, pos):
    """How far this point is from the rock. Positive inside, negative in the wall.
    
    `Volume.depth` is signed the other way round - negative inside - and reading it
    backwards is the kind of mistake that silently inverts a whole pass, so it is named
    once here and never re-derived."""
def _rail_components (edges, order):
    """Connected components, as a list of sets of keys."""
def _rail_crosses_shut (web, a, b):
    """Whether a straight leg passes through a barrier that is still closed."""
def _rail_leg_clearance (vol, a, b, samples=9):
    """The TIGHTEST point along a leg. What decides whether it is a comfortable run.
    
    Both ends are already known clear - they are nodes - so this is looking for the pinch
    in the middle: the corner a straight line clips on its way past."""
def _rail_neighbors (grid, pos, span):
    ...
def _rail_prune (edges):
    """Drop an edge that a two-leg path already covers.
    
    A dense web is full of redundant diagonals - a to c when a to b to c is the same
    journey. They cost a relaxation each and they make the editor overlay unreadable, and
    removing one cannot disconnect anything: the path that justified the removal is still
    there. Longest first, so the worst offenders go and the short legs survive."""
def _rail_seed (vol, step):
    """Every spine candidate. Not yet projected inside or deduplicated."""
def _rail_spine (prim, step):
    """Stations through one primitive, along its OWN axes.
    
    A room's center is one point, and one point is one route. Subdividing is what gives a
    hall two ways across it - and it is measured off the room rather than off a global
    lattice, so a long thin corridor gets a line of nodes and a cube gets a cube of them."""
def _rail_tightness (clear, lane):
    """A leg's cost multiplier, from how much room it has. 1.0 when it is comfortable.
    
    THE WHOLE ANSWER TO "THE ROUTES CUT CORNERS". Every leg used to cost exactly its
    length, so a shortest-path search had no reason to prefer the middle of a hall over
    the inside of a corner - and the inside of a corner is shorter, so it always won.
    Scaling the cost by how tight a leg is makes open space genuinely cheaper, and the
    route moves off the wall on its own.
    
    It is a COST, never a refusal: a tight leg a relic depends on is still there, just
    expensive, so connectivity cannot change. `false_choir`'s 50-unit throat still flies."""
def _vol_dist (p, q):
    ...
def _vol_resolve (volume):
    ...
def _vol_seg_closest (p, a, b):
    """Closest point on segment AB to P. Returns (distance, (cx, cy, cz)).
    
    Clamped to the segment - that is what makes a capsule a capsule rather than an
    infinite cylinder."""
def _vol_xyz (p):
    """Coerce a position: Vec3, tuple/list, engine vec3, Agent, or agent id."""
def rail_attach (name, key, pos, kind='content', roles=None, display=None, hidden=False):
    """Add a node to a web that is already built, and wire it in.
    
    A relic's contents do not all exist when it is built - `Starts when: reach ...` places
    a cache the first time somebody gets near the room holding it. Rebuilding the whole
    web for one new thing would be absurd, so a late node tests visibility against its own
    neighborhood only, exactly as the build pass does."""
def rail_barrier (name, key, pos, radius, display=None, is_open=False):
    """A sphere that severs every rail edge crossing it.
    
    This is how a relic gets a shut door WITHOUT anything authoring an edge. A barrier is
    a thing in the world - a seized hatch, a fall of rock - so it has a position and a
    size, it can be dressed with a prop and the weapons app can be pointed at it. What it
    does to the graph is derived, like everything else here."""
def rail_barrier_approach (name, key, from_pos=None):
    """The node to fly to in order to work on a barrier, or None.
    
    A barrier sits IN the way, so it is not a place - the node beside it is. This answers
    with the nearest end of an edge the barrier is currently severing, which is by
    construction both somewhere a route can reach and somewhere the barrier is in reach
    of."""
def rail_barrier_is_open (name, key):
    """True only for a barrier that exists and is open."""
def rail_barrier_object (name, key):
    """The space object standing in for this barrier, or None."""
def rail_barrier_of_object (name, obj_id):
    """Which barrier this object stands in for, or None. What a damage route asks."""
def rail_barrier_open (name, key):
    """Open one. False when there is no such barrier, or it was open already."""
def rail_barrier_set_object (name, key, obj_id):
    """Bind a barrier to the SPACE OBJECT standing in for it.
    
    A barrier is a sphere in this graph, and a sphere is not something a beam can hit -
    which is why cutting one was scripted. Give it a real object and the engine's own
    weapons work on it: the crew point the suit at a thing, the beam draws, and the
    barrier opens when the thing dies."""
def rail_barrier_shut (name, key):
    """Close one again."""
def rail_barriers (name, shut_only=False):
    """``[(key, record)]`` - what the weapons app lists and the editor draws."""
def rail_build (volume, places=None, margin=None, step=None, name=None, lane=None):
    """Solve a volume's rail web and register it. Returns the stats dict, or None.
    
    Args:
        volume: a `Volume` or its registered name.
        places (dict, optional): the authored destinations, `key -> (x, y, z)` or
            `key -> {"pos", "roles", "display", "hidden", "kind"}`. These keep their own
            keys, so a route can end at a name a person chose.
        margin (float, optional): how far inside the wall a node and a leg must stay.
            Defaults to `RAIL_MARGIN`, which explains why it is the ship's number rather
            than the relic's.
        step (float, optional): spine spacing. Defaults to `RAIL_STEP`, and GROWS from
            there until the web fits `RAIL_MAX_NODES`.
        name (str, optional): register under this name instead of the volume's.
    
    Derived nodes are keyed with an ``@`` prefix (``@spine:14``), which no authored key
    can spell - so an authored place can never be shadowed by one."""
def rail_clear ():
    """Drop every web. On the reset ledger beside `volumes`."""
def rail_count ():
    """Reset-ledger probe. Must NOT create anything by asking."""
def rail_detach (name, key):
    """Remove a node and every edge touching it."""
def rail_dump (name):
    """The whole web as plain data - the editor overlay's source, and a test's eyes."""
def rail_get (name):
    """The web registered under `name`, or None."""
def rail_hide (name, key):
    """Take a node off the destination list without taking it out of the graph.
    
    A secret is still somewhere a route may pass THROUGH - stumbling into a hidden room on
    the way somewhere else is the point of having one."""
def rail_is_hidden (name, key):
    """True only for a node that exists and is hidden."""
def rail_lane (name):
    """The clearance this web was built to aim for. None when there is no such web."""
def rail_leg (name, a, b):
    """The two ends of one edge, for a rope or a drift frame. None if there is no edge."""
def rail_leg_clearance (name, a, b):
    """How much room the leg between two nodes has at its tightest, or None.
    
    Measured once at build time and cached, so the flight layer can size a rope, a drift
    or an arrival radius against the leg it is actually on rather than against a constant
    that assumes a wide hall. That mismatch is the whole of "it drives into walls": the
    planner proved 20 units and the flight helped itself to 140."""
def rail_names ():
    """Every registered web."""
def rail_node (name, key):
    """One node's record, or None."""
def rail_node_pos (name, key):
    """One node's position, or None."""
def rail_nodes (name, kind=None, role=None, listed=None):
    """``[(key, record)]``, in seed order.
    
    Args:
        kind (str, optional): one of the ``KIND_*`` values.
        role (str, optional): only nodes carrying this role.
        listed (bool, optional): True for nodes a destination list should offer - not
            hidden, and not a derived waypoint. False for the rest."""
def rail_reachable (name, start_key, open_only=True):
    """Every node reachable from one, as a set of keys. What the lint counts."""
def rail_remove (name):
    """Drop one web - the galaxy-safe counterpart to `rail_clear`, which would take the
    ruin the crew is standing in."""
def rail_reveal (name, key):
    """Put a hidden node back on the destination list."""
def rail_route (name, start, goal, open_only=True):
    """Waypoints from a position to a node key (or to a position), along the web.
    
    Returns ``[]`` when there is no way - **never a straight line**. A relic has no engine
    collision at all, so answering with the direct line when the route could not be found
    means flying THROUGH the rock, which is the one thing this whole layer exists to
    prevent.
    
    Args:
        start: where the ship is.
        goal: a node key, or a position.
        open_only (bool): refuse to route through a shut barrier. Turn it off to ask
            "would there be a way if this opened", which is what the lint uses."""
def rail_stats (name):
    """What the solve produced: nodes, edges, components, build time. A dict, or None.
    
    `components` is the number worth watching. More than one means part of the ruin
    cannot be flown to from the rest, which is the difference between "my router is
    wrong" and "this relic is not joined up"."""
def volume_doorways (volume):
    """Every point where two navigable primitives meet - the openings between rooms.
    
    Waypoint material for :func:`volume_route`, not a route in itself."""
def volume_nearest_inside (volume, pos, margin=0.0):
    """Closest point inside by at least `margin`; the position itself if already so."""
def volume_skirts (volume, per_solid=14, clearance=None):
    """Points that let a route get AROUND each subtracted mass.
    
    Doorways connect one room to the next; nothing connects one side of a pillar to the
    other. `voice.amd`'s transmitter bay holds a subtracted cradle, and with doorways
    alone the bay's own places could see nothing at all - the route into the deepest room
    of the relic simply did not exist, and the router fell back to a straight line through
    the ruin.
    
    Each solid gets a ring of candidates just clear of its surface, kept only where they
    are really navigable. They are waypoint material for :func:`volume_route`; a solid a
    route never needs to pass contributes nodes nobody visits, which costs one visibility
    test each."""
def volume_visible (volume, a, b, margin=0.0, step=30.0):
    """Whether the straight line from a to b stays inside the volume.
    
    Samples along the segment, so a passage narrower than `step` can be missed - the
    default is well under the tightest thing the shipped relics are built from."""
class _Web(object):
    """One relic's rail web. Not exported - reach it through the `rail_*` functions."""
    def __init__ (self, name, volume, margin, step):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def cut (self):
        """Every edge a SHUT barrier is currently severing, both directions.
        
        Rebuilt lazily rather than on each barrier write, because a barrier opening is
        the rare event and a route reading the set is the common one."""
    def dirty (self):
        ...
