from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def _break (host, node, setting):
    """Damage a node. STUN does not - a stun setting on a bulkhead should say nothing
    happened rather than quietly cutting through it.
    
    **FULL marks it red and says so; it does not DELETE it.** Deleting a structural node
    out from under an interior is the mission's call, not the library's - a hole where a
    reactor was is a thing a story decides, and the signal carries `XESS_DESTROYED` so it
    can. The colour is the icon's, so red-versus-yellow is what a crew member sees."""
def _hurt (host, target, setting):
    """What a shot does to somebody, by setting.
    
    Mirrors what internal damage already does to a damcon, rather than inventing a second
    death path: HP drops, and at zero the engine's own shape applies - `life_form_died`
    then delete, which is what anything watching for a death is already watching for.
    
    **STUN takes no hit points.** There is no stun model anywhere in the game - no
    duration, no recovery, no "stunned" state - and inventing one here before a mission
    asks is how a library grows a combat system nobody uses. So a stun shot REPORTS
    (through `xess_fired`, carrying the setting) and changes nothing, and what being
    stunned means is the mission's to write. That is the same line the rest of this
    module holds."""
def _occupied ():
    ...
def _set_occupied (table):
    ...
def _site_of_room (room_id):
    """Which interior a room belongs to. Rooms are per-site, so this is a lookup."""
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
def boarding_arm (client_id, setting='stun'):
    """Arm this console. The NEXT map click is a shot instead of a walk.
    
    The setting is chosen BEFORE the target and never inferred from what is hit: a
    cutting beam on a person and a stun on a bulkhead are both things somebody might
    mean, so both have to be sayable."""
def boarding_armed (client_id):
    """Whether the next click is a shot. The device must show this LOUDLY - nobody should
    discover they were armed by hitting a colleague."""
def boarding_click (client_id, parent_id, x, y):
    """One map click, as policy. A ``//point/grid`` route calls exactly this.
    
    **It is only ever "walk me there".** The prototype needed two modes - click a person to
    take them, click the floor to send them - because one shared figure had to be chosen
    first. A console that only ever drives its OWN character never chooses, so the
    figure-picking path, the ``set_grid_selection`` push-back and the whole ``//focus/grid``
    reconciliation route all disappear. Two figures on one cell stops being a question.
    
    The host check is not ceremony: ``//point/grid`` fires for EVERY interior, including
    the console's own ship when somebody opens Engineering. Without it a boarder who
    switched to Engineering would walk their surface body by clicking their own engine
    room.
    
    Returns:
        bool: whether this console walked somebody."""
def boarding_client_of_figure (figure):
    """The console driving this body, or None.
    
    The reverse of :func:`boarding_my_figure`, and it has to walk the drivers rather than
    read a link: the figure belongs to the SITE and the driving belongs to the CLIENT, and
    keeping the second fact off the figure is the entire point of the design."""
def boarding_console_type ():
    """The CONSOLE_TYPE a boarded console wears - `"boarding_crew"`.
    
    Deliberately not `"crew"`: that already means a damcon team, because
    LegendaryMissions spawns them `grid_spawn(..., "crew,damcons,lifeform")`."""
def boarding_disarm (client_id):
    """Back to walking."""
def boarding_entry_cell (target, roles='access'):
    """Where a party materialises on this interior, as ``(x, y)``.
    
    The AIRLOCK if the floor plan drew one - a room carrying `access` - because that is
    where an author means people to come aboard, and it puts the whole party in one place
    so they arrive together rather than scattered.
    
    Falls back to the interior's own centre cell, then to (0, 0). A fallback is not a
    failure worth refusing over: a plan with no airlock is a plan the author simply did
    not mark, and a party standing in the middle of it can still walk."""
def boarding_figure_count ():
    """Reset-ledger probe: bodies still standing on one."""
def boarding_figure_of (lifeform):
    """The body this character is walking around in, or None."""
def boarding_figure_role ():
    """The role a boarding figure wears - `"boarding_figure"`."""
def boarding_figure_spawn (target, lifeform, x, y, icon_index=100, color='#4cf'):
    """Put one character on the interior, as a body linked to its identity.
    
    Args:
        target: the interior they are standing on.
        lifeform: who they are.
        x (int): the cell x to stand on.
        y (int): the cell y to stand on.
        icon_index (int, optional): the glyph.
        color (str, optional): its color.
    
    Returns:
        The grid object, or None if the site or the person does not exist."""
def boarding_figures (target=None):
    """Every boarding figure, or only the ones on this interior."""
def boarding_fire (client_id, x, y):
    """Shoot the cell this console just clicked.
    
    **A shot disarms**, whatever the outcome - including a refusal. One click, one shot,
    back to walking. Holding a weapon armed across a room is how an accident happens, and
    re-arming is one tap.
    
    Returns:
        bool: True if something was hit. A refusal (out of range, no body, nothing there)
        is False and says why through `xess_fired`, rather than being a silent no-op that
        reads as a broken button."""
def boarding_fire_count ():
    """Reset-ledger probe: consoles left holding a live weapon."""
def boarding_lifeform_of (figure):
    """Who this body is, or None."""
def boarding_my_figure (client_id):
    """The grid object THIS console drives, or None.
    
    Takes the console explicitly and always will. A ``//point/grid`` route runs on the
    SERVER task, so a convenience fallback to ``FrameContext.page`` would answer for the
    server on every click - silently, and for every console at once."""
def boarding_my_host (client_id):
    """The interior THIS console is walking, or None."""
def boarding_release (client_id):
    """This console drives nobody."""
def boarding_room_at (target, x, y, roles=None):
    """The room object standing at this cell, or None.
    
    What a panel prints as "where you are". Asks the interior rather than the selection, so
    it costs nothing and cannot disagree with anybody else's console."""
def boarding_room_count ():
    """Reset-ledger probe: rooms the party is believed to be standing in."""
def boarding_room_name (node_name):
    """The authored room name from a grid node's name.
    
    The interior builder names every node ``"<room>:<x>,<y>"``
    (``internal_damage.py:208``), so a lab three cells across is three objects called
    ``site-lab:3,2``, ``site-lab:4,2``, ``site-lab:5,2``. The part before the colon is
    what the floor plan's legend called it, and that is the room a mission means - so it
    is the identity the entry trigger keys on. Without this, walking across one lab
    reports arriving in three different rooms."""
def boarding_room_name_of (figure):
    """``(site id, room name, node id)`` for where this body is, or None in a corridor.
    
    The NAME is the identity a mission cares about: a lab is one room however many cells
    it is drawn across."""
def boarding_room_of (figure):
    """The room node this body is standing on, or None if it is in a corridor.
    
    One NODE. A room is drawn per cell, so this is whichever cell of the lab they are on
    - use :func:`boarding_room_name_of` for the room a mission means."""
def boarding_room_roles ():
    """What counts as a room, for `any_role(...)`. See :data:`ROOM_ROLES`."""
def boarding_rooms_occupied ():
    """Which rooms the party is currently standing in: ``{room id: client id}``."""
def boarding_rooms_tick (t=None):
    """One look at where everybody is. Registered by :func:`boarding_rooms_watch`."""
def boarding_rooms_unwatch ():
    """Stop noticing. Rooms are forgotten, so a later watch starts from a clean sheet."""
def boarding_rooms_watch (seconds=0.4, roles=None):
    """Start noticing when the party enters and leaves rooms.
    
    Emits two signals, both ONCE PER ROOM:
    
    ``boarding_entered``
        the first figure to arrive in an empty room. Carries ``BOARDING_ROOM``,
        ``BOARDING_ROOM_NAME``, ``BOARDING_SITE``, and the ``BOARDING_CLIENT`` /
        ``BOARDING_WHO`` of whoever got there first.
    ``boarding_left``
        the last figure out. Carries ``BOARDING_ROOM``, ``BOARDING_ROOM_NAME`` and
        ``BOARDING_SITE``.
    
    **Route these with ``//shared/signal``, not ``//signal``.** Entering a room is one
    event in the world, not one per console: a five-console party on a ``//signal`` route
    would start the scene five times, which is the same bug the once-per-room rule exists
    to prevent, one level up.
    
    Args:
        seconds (float, optional): how often to look. The default is well under the time
            a figure takes to cross one cell, so no room is ever stepped through unseen,
            and the check is a handful of dict lookups per figure.
        roles (str, optional): what counts as a room. Defaults to :data:`ROOM_ROLES`.
    
    Returns:
        The tick task, so a mission can hold it. Idempotent - asking twice watches once."""
def boarding_setting (client_id):
    """The verb the next shot carries."""
def boarding_setting_text (setting):
    """What a setting does, in words, for the device to show BEFORE it is armed."""
def boarding_settings ():
    """The settings a device may offer, weakest first. An accessor because MAST cannot
    see a module-level tuple - only functions are registered as globals."""
def boarding_site_build (target, layout=None):
    """Build ``target``'s interior so a party can walk it, and mark it a boarding site.
    
    Works on a plain NPC - measured in the engine 2026-09-16, the same hull and the same
    named layout spawned as an NPC and as a player ship in one run: the NPC returned a real
    41x40 hull map, built the authored layout to exact room counts, pathfound a figure
    across it, and accepted ``assign_client_to_ship``. Interiors are NOT player-only. That
    belief came from LegendaryMissions' ``//spawn`` route, which REQUESTS interiors only
    for ``__player__`` - LM's policy, not an engine limit.
    
    **Uses ``grid_rebuild_grid_objects``, not ``grid_interior_request``, and not "name the
    layout and wait".** A boarding site is built MID-GAME. In that same engine run the
    deferred path measured 0 grid objects for the NPC *and* for the player ship; building
    now is exactly what ``grid_rebuild_grid_objects`` documents itself as being for.
    
    Args:
        target: the ship or station being boarded.
        layout (str, optional): a named floor plan merged with ``grid_merge_ascii``.
            Defaults to the hull's own.
    
    Returns:
        The target, or None if it does not exist."""
def boarding_site_clear (target=None):
    """Take the party's bodies off an interior - or off every interior.
    
    Called on a mission reset, and when a site is finished with. The LIFEFORMS belong to
    `boarding.py` and are left alone; this owns only the bodies."""
def boarding_site_count ():
    """Reset-ledger probe: interiors still marked as being boarded."""
def boarding_site_is (target):
    """Whether this object is currently being boarded."""
def boarding_site_role ():
    """The role an interior being boarded wears - `"boarding_site"`.
    
    LegendaryMissions' Engineering grid routes gate themselves OFF this, so it is shared
    across repos and must not be changed on one side alone."""
def boarding_take (client_id, figure, host):
    """Give this console a figure to drive, on this interior.
    
    Stored on the CLIENT. Read the module docstring before moving it anywhere else - the
    site is exactly where it must not go."""
def boarding_walk (client_id, x, y, speed=0.12):
    """Walk this console's own figure to a cell. The engine paths it.
    
    Returns:
        bool: True if somebody was sent. False is ordinary - a console that is not
        boarded, or has no body yet, clicking the map."""
def boarding_where (client_id):
    """The cell this console's figure is standing on as ``(x, y)``, or None."""
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
