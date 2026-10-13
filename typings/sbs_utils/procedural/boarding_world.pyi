from sbs_utils.agent import Agent
from collections import deque
def _arrival_cell (zone, came_from):
    """Where somebody walking in from `came_from` stands: beside the way back, never ON
    it - arriving on an exit would send them straight back out."""
def _arrow_pairs (text):
    """`a -> zone 1,2, b -> other` -> [("a", "zone 1,2"), ("b", "other")]."""
def _cells_table (key):
    ...
def _drivers ():
    ...
def _exit_spec (value):
    """An `Exits:` target: `"colony"` or `"colony 20,39"` -> (zone, (x, y) | None)."""
def _find_host (name):
    """A `Host:` - an object id, or the name of a space object that exists already."""
def _hull_map (host):
    ...
def _issue_next_leg (client_id, fig):
    ...
def _norm (key):
    ...
def _open (hm, blocked, x, y):
    ...
def _scan_world_cells (host_id):
    """Read the blocker and exit cells a floor plan drew onto this host."""
def _set_zones (table):
    ...
def _spawn_hidden_host (key, title, ship_key, pos, hidden):
    ...
def _xy (value):
    """`(x, y)` from `"20, 39"`, `"20 39"`, a list or a tuple. None when unreadable."""
def _yes (value, default=True):
    ...
def _zones ():
    ...
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    THE SERVER CONSOLE COUNTS. `to_object(0)` returns None by design, so this used to
    be a silent no-op for client id 0 - and LM's main screen adds `console, mainscreen`
    to its own client id. On the server window that role was never added, so every
    audience narrowed with `any_role("mainscreen")` - a hail placed on the main screen,
    a hero card, a lower third - resolved to nobody and drew nothing, with no error.
    `to_agent_list` resolves the server the same way `get_inventory_value` always has.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def boarding_block (host, cells):
    """Close cells: a door shut, a rockfall, a hostile standing guard."""
def boarding_blocked_cells (host):
    """Every cell of this host the library will not route through, as a set."""
def boarding_exit_at (host, x, y):
    """The exit room name at a cell of this host, or None."""
def boarding_exit_cells (host):
    """``{(x, y): room name}`` for this host's exits."""
def boarding_exit_follow (client_id, room_name):
    """Take this console through an exit room. True when it moved."""
def boarding_exit_target (host, room_name):
    """Where an exit room leads: ``(zone key, (x, y) | None)``, or (None, None).
    
    The zone's `Exits:` table first; failing that a room called `to_<zone>` goes there."""
def boarding_is_blocked (host, x, y):
    ...
def boarding_legs (path, start):
    """A path as the corners where it turns, plus its end - the legs to issue one by one."""
def boarding_on_arrive (client_id, intent):
    """Remember what this console meant by walking - run when the walk finishes.
    
    ``intent`` is a callable ``fn(client_id)``. Replaced by the next call, and dropped
    when a new walk starts elsewhere (`boarding_stop`)."""
def boarding_path (host, start, goal):
    """The cells from ``start`` to ``goal``, four-connected, around every blocker.
    
    Returns:
        list: the cells to walk AFTER ``start``, ending at the goal - or, when the goal
        cannot be reached (a blocker, a closed door), ending at the reachable cell
        nearest it. Empty when already there or nothing is reachable. None when the
        host has no floor."""
def boarding_site_move (client_id, target, x=None, y=None):
    """Move this console's body to another area and point the console at it.
    
    Args:
        client_id: the console moving.
        target: a zone key, or a host object.
        x, y (optional): where to stand. Defaults to the zone's entry.
    
    Returns:
        The new figure, or None when the console is not boarded or the target is unknown."""
def boarding_stop (client_id):
    """Forget any walk in progress. The figure stops at the end of its current leg."""
def boarding_unblock (host, cells):
    """Open cells again: a door opened, a rock cut away."""
def boarding_walking (client_id):
    """Whether this console's figure still has legs to walk."""
def boarding_world_clear ():
    """The per-mission reset: no zones, no blockers, no walks."""
def boarding_world_routes (host):
    """Whether walks on this host go through the library's router (a zone, or a host
    with blockers) rather than straight to the engine."""
def boarding_world_tick (t=None):
    """One pass over every console that is driving a figure."""
def boarding_world_unwatch ():
    ...
def boarding_world_walk (client_id, x, y, speed=None):
    """Walk this console's figure to a cell, around blockers. False when not boarded.
    
    Emits ``boarding_blocked`` when the cell cannot be reached, after sending the figure
    as close as it can get - so the device can say "the way is blocked" rather than
    looking broken."""
def boarding_world_watch (seconds=0.1):
    """Start the tick that drives walks, keeps figures off blocked cells and follows
    exits. Idempotent. Returns the tick task."""
def boarding_zone_build (key, grid_text=None, host=None, title=None, entry=None, exits=None, beam=True, known=True, hidden=True, pos=None):
    """Make one area of the world. Returns its host object, or None.
    
    Args:
        key (str): the zone's name - what exits and missions call it.
        grid_text (str, optional): an ASCII floor plan (see ``grid_ascii``). Its `ship:`
            is the hull the host is spawned as and its `layout:` is merged and built.
        host (optional): an object that already exists - a ship the party can board -
            instead of spawning a hidden one.
        title (str, optional): what the area is called on screen.
        entry (optional): the cell a party arrives on, `(x, y)` or `"x, y"`. Defaults
            to the floor plan's `access` room, then the middle of the floor.
        exits (dict, optional): `{room name: "zone [x,y]"}`. A room named `to_<zone>`
            needs no entry here - the name says where it goes.
        beam (bool): whether the transporter can put people here.
        known (bool): whether the party knows the zone exists yet.
        hidden (bool): for a spawned host, whether to draw it as nothing.
        pos (optional): where to park a spawned host."""
def boarding_zone_clients (key):
    """The consoles standing in a zone right now."""
def boarding_zone_count ():
    """Reset-ledger probe: zones still declared."""
def boarding_zone_entry (key):
    """Where a party arrives in a zone: its `Entry:`, else the floor plan's airlock."""
def boarding_zone_host (key):
    """The host object id of a zone, or None."""
def boarding_zone_known (key):
    ...
def boarding_zone_of (target):
    """The zone key of a host - or of the host a CONSOLE is standing on. None if neither."""
def boarding_zone_records (section):
    """Zone records from an AMD section - plain dicts, for tests and tools."""
def boarding_zone_reveal (key, beam=None):
    """The party now knows this zone exists (a scan found it). Optionally set `beam`."""
def boarding_zone_role ():
    """The role a zone host wears - `"boarding_zone"`."""
def boarding_zone_title (key):
    ...
def boarding_zones (known_only=False, beam_only=False):
    """Zone keys, in the order they were built."""
def boarding_zones_build (section, load=None):
    """Build every zone an AMD section declares. Returns ``{zone key: host}``.
    
    One heading per zone; the heading key is the zone key and its text the title::
    
        # [Landing Ridge](ridge)
        ---
        Grid: surface/ridge.grid
        Entry: 20, 36
        Exits: to_colony -> colony 20,2
        Beam: yes
        Known: yes
        ---
    
    Args:
        section: the AMD section node (from ``document_get_amd_file``).
        load (callable, optional): reads a floor plan file. Defaults to
            ``media_read_relative_file``."""
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
    
    Answers for the SERVER console too. It used to always say False for client id 0,
    which reads exactly like "the role is not there" - so a check on the server was
    indistinguishable from a real negative and passed silently for years.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
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
