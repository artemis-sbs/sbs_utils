from sbs_utils.agent import Agent
from collections import deque
def _arrival_cell (area, came_from, where=None):
    """Where somebody walking in stands: beside the way back, never ON it - arriving on
    an exit would send them straight back out."""
def _arrive (aid, rec):
    ...
def _blocking_actor_at (area, x, y, ignore=None):
    ...
def _body_key (rec):
    """The sprite whose GROUND an actor stands on: its own, or the mirrored twin a still
    prop is drawn with on this cell (see ``tilemap_sprite_look``)."""
def _bump (area):
    ...
def _by_position (looks, x, y):
    """One look of an n x n GRID picked by where the cell is, so the pieces of one big
    texture always sit next to each other the same way. A single key is itself."""
def _cell_hash (x, y):
    """A fixed number per cell: how a cell picks among variants, the same every time."""
def _covers (a, x, y):
    """Whether an actor record covers a cell: its own, or one under its sprite's base."""
def _facing (dx, dy):
    """The compass word for a step: the larger axis wins, ties go to north/south - a
    figure seen from the 3/4 view reads best facing the camera or away from it."""
def _id_order (aid):
    """Sort key for actor ids: agent ids in number order, then any NAMED actors (a map
    token that stands for something, not an agent) - mixed, a plain sort would raise."""
def _kind_spec (rec, kind):
    ...
def _line (x0, y0, x1, y1):
    """Bresenham cells from (x0, y0) to (x1, y1), both ends included."""
def _norm (key):
    ...
def _now ():
    ...
def _see_through (rec, x, y):
    ...
def _step (aid, rec):
    """One cell along the path. False when the way ahead has closed."""
def _visible_from (rec, x, y, radius):
    ...
def _xy (value):
    ...
def tilemap_actor (agent):
    """The actor record, or None."""
def tilemap_actor_cells (agent):
    """The cells an actor covers: its own, plus any its sprite's base reaches."""
def tilemap_actor_distance (agent, x, y):
    """Steps (Manhattan) from a cell to the nearest cell an actor covers - so standing
    beside a car's bumper is beside the car. None for an unknown actor."""
def tilemap_actors (area=None):
    """Actor ids - all, or in one area - sorted."""
def tilemap_actors_at (area, x, y):
    """Actors covering a cell - standing on it, or a big prop whose base reaches it."""
def tilemap_actors_near (agent, reach=1):
    """Actors within ``reach`` steps (Manhattan) of this one, in its area - measured to
    the nearest cell each covers, so a big prop is near from any side."""
def tilemap_area (key):
    """The area record (read-only by convention), or None."""
def tilemap_areas (known_only=False, beam_only=False):
    """Area keys, in load order."""
def tilemap_block (area, cells):
    """Close cells for now: a shut door, a rockfall."""
def tilemap_cell_fringes (area, x, y):
    """The fringe strips drawn over one cell where its ground meets another: for each
    side whose neighbour is a kind that goes OVER this one (a higher ``over``) and has a
    ``fringe``, that kind's strip for this edge. Lowest first, so the one on top is
    drawn last. ``[]`` for a cell with nothing to blend.
    
    This is how two kinds of ground meet softly - salt crust spilling onto dirt, a path
    frayed at its sides - where one tile per cell could only meet in a straight seam."""
def tilemap_cell_look (spec, x, y, area=None):
    """The atlas key a kind is drawn with at one cell.
    
    With the area given, a kind's art can depend on its neighbors:
    
    - ``edges`` - ``{mask: key or [keys]}`` where the mask is which sides have the same kind
      (N=1, E=2, S=4, W=8). A wall run, a cliff edge, a pool's bank. A mask with no
      entry falls through to the plain look.
    - ``shade`` - the look of this kind lying just SOUTH of a ``tall`` kind, in its
      shadow, which is what makes a wall read as standing up. A key, or a grid.
    - ``grid`` - n x n keys cut from one texture bigger than a tile; each cell takes
      the piece for its position (x % n, y % n). Seamless, and the texture keeps a
      believable scale where squeezing it into one tile would shrink it to noise.
    
    Otherwise a fixed pick among the kind's variants, so the same cell always looks the
    same."""
def tilemap_clear ():
    """The per-mission reset: no areas, no actors, no walks, no listeners."""
def tilemap_clear_tilesets ():
    """Tilesets too. Separate: a tileset is usually declared once, by an addon."""
def tilemap_count ():
    """Reset-ledger probe: areas plus actors still held."""
def tilemap_entry (area):
    """Where somebody arriving by transporter stands: `entry:` (a mark or x,y), else the
    first walkable cell nearest the middle."""
def tilemap_exit_follow (agent, mark):
    """Take an actor through an exit mark in its area. True when it moved."""
def tilemap_exit_target (area, mark):
    """Where an exit mark leads: ``(area, arrive mark or (x, y) or None)``.
    
    The area's ``exits:`` table first; a mark called ``to_<area>`` needs no entry."""
def tilemap_explored (area, x, y):
    ...
def tilemap_face (agent, x, y):
    """Turn an actor toward a cell - someone it is talking to, or shooting at. The
    view draws the facing when the sprite has one (``<sprite>_<n|e|s|w>...``)."""
def tilemap_generate (key, w, h, cell, tileset='default', title=None):
    """Build an area from code rather than a file - or rebuild it.
    
    For a world too big or too procedural to write down: a window onto an endless galaxy,
    regenerated around whatever the console is looking at.
    
    Args:
        key (str): the area's name. Generating the same key again replaces it.
        w, h (int): its size, in cells.
        cell (callable): ``fn(x, y)`` -> a kind, ``(kind, tint)``, or None for nothing.
        tileset (str): the tileset the kinds come from.
        title (str, optional): defaults to the key.
    
    A rebuild that comes out IDENTICAL changes nothing and repaints nothing, so a caller
    may regenerate every tick and pay only when the world moved. Actors in the area stay
    where they are - moving them is the caller's business - and while the size is
    unchanged the area keeps what it held besides its tiles (explored cells, marks,
    blocked cells).
    
    Returns:
        str: the area key."""
def tilemap_is_blocked (area, x, y):
    ...
def tilemap_is_open (area, x, y, ignore=None):
    """Whether a cell can be walked: on the map, a walkable tile, not blocked, and no
    blocking actor (a boulder, a sentry holding a door) standing there."""
def tilemap_kind (area, x, y):
    """The tile kind at a cell, or None off the map or on nothing."""
def tilemap_kind_spec (area, kind):
    """The tileset entry for a kind in this area's tileset, or None."""
def tilemap_known (key):
    ...
def tilemap_listen (fn):
    """Call ``fn(area_key)`` whenever an area changes. Views use this to repaint."""
def tilemap_load (text):
    """Parse an area file and add it to the world. Returns the area key, or None.
    
    A file that cannot be read is logged and skipped - one bad area should not take a
    mission down - so the linter and the tests are what make it loud."""
def tilemap_mark (area, mark, cells):
    """Add cells to a mark after the area is loaded - how a generated map names its
    rooms without spending a legend character on each. A cell keeps the mark its file
    gave it (an exit, the entry) as the one ``tilemap_mark_at`` answers. False for an
    unknown area."""
def tilemap_mark_at (area, x, y):
    """The mark on a cell, or None."""
def tilemap_mark_cells (area, mark):
    """Every cell a mark covers, sorted."""
def tilemap_marks (area):
    ...
def tilemap_parse (text):
    """Read an area file into a record. Raises TilemapError rather than guessing."""
def tilemap_path (area, start, goal, ignore=None):
    """The cells from ``start`` to ``goal`` (after start), four-connected.
    
    When the goal cannot be reached the path ends at the reachable cell nearest it. Empty
    when already there or boxed in; None for an unknown area."""
def tilemap_place (agent, area, x=None, y=None, sprite=None, color=None, party=None, blocks=None, speed=None, exits=None, fixed=None):
    """Put an actor on a cell - or move it there, from anywhere.
    
    Args:
        agent: who (any agent id).
        area (str): the area.
        x, y (optional): the cell. Defaults to the area's entry.
        sprite (str, optional): the atlas key it is drawn with.
        color (str, optional): a tint.
        party (bool, optional): whether it is one of the crew - party actors reveal the
            map, and only they follow exits.
        blocks (bool, optional): whether others must walk round it.
        speed (float, optional): cells per second.
        exits (bool, optional): whether stopping on an exit takes it there. Defaults to
            ``party``.
        fixed (bool, optional): a thing that does not move (a prop). It stays drawn once
            its cell has been SEEN, where something that moves is drawn only while in
            sight.
    
    Returns:
        The actor record, or None for an unknown area."""
def tilemap_remove (agent):
    """Take an actor off the map."""
def tilemap_reveal (area, x, y, radius=None):
    """Mark what can be seen from a cell as explored."""
def tilemap_reveal_all (area):
    """The whole area is known (a map found, an orbital survey)."""
def tilemap_reveal_area (key, beam=None):
    """The party now knows the area exists (a scan found it)."""
def tilemap_revision (area):
    """Moves whenever anything in the area changes - an actor steps, a door opens."""
def tilemap_sees (area, x0, y0, x1, y1):
    """Whether (x1, y1) can be seen from (x0, y0): every cell BETWEEN them lets sight
    through. The far cell itself need not - you can see a wall."""
def tilemap_set_clock (now):
    """Drive time by hand (tests). ``None`` goes back to sim time."""
def tilemap_set_pose (agent, pose=None):
    """A pose the sprite set may draw instead of standing - ``"down"`` for a crew
    member at 0 HP (``<sprite>_down``). ``None`` stands it back up."""
def tilemap_set_sprite (agent, sprite=None, color=None):
    ...
def tilemap_set_tile (area, x, y, kind):
    """Change a tile: a door drawn open, rubble cleared."""
def tilemap_size (key):
    ...
def tilemap_sprite_cells (key):
    """The cells a sprite covers, as ``(dx, dy)`` offsets from its actor's own cell.
    
    Always holds ``(0, 0)``; a sprite with no ``base`` covers just that. Every other
    cell is covered when more than half of it is under the base, each way."""
def tilemap_sprite_look (rec):
    """The atlas key an actor is drawn with right now.
    
    A sprite names a BASE key; an art set may add looks named after it, and the first
    one that is registered wins::
    
        <base>_down                         when the pose is "down"
        <base>_<facing>_<idle|a|b>          a facing and a stride frame
        <base>_<facing>                     a facing
        <base>                              the one look everything has
    
    So a plain one-cell sprite draws exactly as it always did, and a set that only has
    some of the looks falls back cell by cell rather than showing nothing. A prop that
    stands still (``fixed``) and has a mirrored twin (``"mirror": true``) is drawn as the
    twin on about half the cells - the same cells every time."""
def tilemap_sprite_twin (key):
    """The mirrored twin a still prop may be drawn with (``"mirror": true``), or None."""
def tilemap_stop (agent):
    ...
def tilemap_tick (t=None):
    """Advance every walking actor. Registered by :func:`tilemap_watch`.
    
    Each actor steps when its own clock comes due, so a fast one and a slow one walk
    side by side. Guarded per actor: a bad one is dropped from its walk rather than
    raising out of the tick, which would pause the whole mission."""
def tilemap_tileset (name, kinds):
    """Declare what tile kinds look like and how they behave.
    
    Args:
        name (str): the tileset's name, as an area's ``tileset:`` names it.
        kinds (dict): ``{kind: {"cell": atlas key, "walk": bool, "see": bool,
            "color": tint, "variants": [atlas key, ...], "look": art ground name}}``.
            ``look`` names the ground an ART SET draws this kind with (see
            ``tilemap_art``) - so a map keeps its own kind names (``dust``) and still
            gets a shared pack's ground (``dirt_arid``). ``walk`` defaults True,
            ``see`` defaults to ``walk``. ``variants`` are other looks for the same
            kind, picked per cell so a field of one kind does not repeat in a grid."""
def tilemap_tileset_known (name):
    """Whether a tileset of this name has been declared."""
def tilemap_tileset_load (text):
    """Read a tileset file and declare it (``tilemap_tileset``). Returns its name, or
    None when it cannot be read - logged, like an area that cannot be."""
def tilemap_tileset_parse (text):
    """Read a tileset file. Raises TilemapError rather than guessing.
    
    A TILESET FILE::
    
        tileset: mereth
        title: Mereth surface
        kinds:
          dust:   walk see   look=dirt      # walked and seen across
          brine:  see        look=water     # seen across, never walked
          rock:              look=rock      # neither
          door:   walk       color=#a86
    
    Each word on a kind line is a rule the kind HAS, so a kind that names neither
    ``walk`` nor ``see`` blocks both - a typo is an error, never a silent wall. ``tall``
    stands up (the kind south of it takes its ``shade``). ``look=`` names the ground an
    art set draws it with, ``cell=`` a sprite key to draw without one, ``color=`` a tint,
    ``over=`` which of two kinds' fringes goes on top. A ``#`` that starts a word ends
    the line, so ``color=#a86`` is a color and ``  # note`` a comment.
    
    Returns:
        dict: ``{"name", "title", "kinds": {kind: spec}, "lines": {kind: line number}}``
        - ``kinds`` is what ``tilemap_tileset`` takes; ``lines`` is for tools."""
def tilemap_tint (area, cells, color=None):
    """Tint cells - an owner's color, a selection, a warning - over their kind's own.
    
    ``color=None`` clears the tint, back to the kind's. Repaints once, and only when a
    cell actually changed. False for an unknown area."""
def tilemap_tint_at (area, x, y):
    """A cell's own tint, or None when it wears its kind's color."""
def tilemap_title (key):
    ...
def tilemap_touch (area):
    """Say something about an area changed that the tiles do not show - a prop was used,
    a person spoken to - so views of it repaint."""
def tilemap_unblock (area, cells):
    """Open cells again."""
def tilemap_unlisten (fn):
    ...
def tilemap_unload (area):
    """Drop an area and every actor in it. False when there was no such area."""
def tilemap_unwatch ():
    ...
def tilemap_visible (area):
    """The cells some party actor in this area can see RIGHT NOW."""
def tilemap_walk (agent, x, y, intent=None):
    """Send an actor walking to a cell. Returns the path length, or -1 if it cannot.
    
    ``intent`` is a callable ``fn(agent)`` run when the walk ENDS at the goal - walking up
    to a door in order to open it. Emits ``tilemap_blocked`` (and still walks as close as
    it can) when the goal is out of reach."""
def tilemap_walking (agent):
    ...
def tilemap_watch (seconds=0.1):
    """Start walking actors. Idempotent. Returns the tick task."""
def tilemap_where (agent):
    """``(area, x, y)`` for an actor, or None."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
class TilemapError(Exception):
    """An area file that cannot be read. Carries a line number where it can."""
