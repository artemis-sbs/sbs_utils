from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def _grid_begin (ship_id, layout):
    """Resolve what a build needs and clear whatever is standing there.
    
    Shared by the inline build and the phased one so the two can never drift. Returns
    ``(so, blob, SBS, items, theme_name, layout)``, or ``None`` when there is nothing to
    build - having already said why."""
def _grid_damcon_decl (ship_id, layout=None):
    """The hull's damcon declaration, or ``None`` when it declares nothing."""
def _grid_finish (ship_id, so, SBS, counts, layout):
    """Everything that must happen once the last room is in.
    
    Kept apart from the spawning so a PHASED build can run it after the final slice - a
    ship must not sit with a damage model that counts only the rooms created so far.
    
    RESOLVE THE BLOB HERE, NEVER CARRY ONE IN. `Agent.data_set` returns None once the
    agent is dead (`agent.py`, "Every crashing write went through here"), and that guard
    is the whole defense against the ObjectDataBlob use-after-free. A phased build runs
    this up to `over` seconds after `_grid_begin` resolved things, so a blob captured
    back then walks straight past the guard and writes into freed engine memory - which
    is a server crash to desktop, not an exception. Measured 2026-08-25: fault in
    `ObjectDataBlob::operator[]` under `ObjectDataBlob::Set`, from `Simulation::Tick`."""
def _grid_interior_done (ship_id, so, SBS, counts, layout):
    """Finish one ship's phased build and let it be requested again."""
def _grid_interior_enqueue (ship_id, layout):
    ...
def _grid_interior_focus (ship_id):
    ...
def _grid_interior_skip (ship_id):
    """Should this build be dropped rather than run? Says why, quietly.
    
    Reading the hull at build time collapses the re-hulling churn, but it does not answer
    the other half: a ship may not be FLOWN at all. The roster parks every slot past
    PLAYER_COUNT - suspended to standby, hull blanked to `invisible` - and building an
    interior for one means walking the whole layout lookup to discover there is no
    floor plan for `invisible`, then saying so loudly, once per parked hull. Seven of
    those per run on a default roster, and every one of them is noise.
    
    Standby is the test rather than `__player__`, because it is what "not in play" means
    to the engine and it keeps this general - the roster is not the only thing that parks."""
def _grid_interior_start (ship_id, layout):
    """Resolve the hull NOW - not when it was requested - and queue its rooms in slices."""
def _grid_promote_maintenance_to_repair (node_id):
    """A node under a TUNE order just broke - the order becomes a REPAIR order.
    
    Local import: work_orders imports this module for grid_node_state, so a
    top-level import would be a cycle.
    
    Without this the order keeps its `maintain` kind, and `work_order_is_satisfied`
    for maintenance asks "is it tuned" - which a broken node never is - so the team
    keeps walking to it and `ai_tune_node` tries to tune something in pieces."""
def _grid_resolve_point (SBS, ship_id, hm, declared, used=None, prefer_empty=True, who=''):
    """Where to put one grid object: the declared cell if it is usable, else the engine's.
    
    ``None`` only when the hull has no usable cell at all.
    
    A DECLARED cell that is occupied is accepted without comment - that is the entire
    point of an interior with no hallway (LM #381), and damcons walk over room cells
    constantly. A declared cell that is off the hull is a WARNING and falls through to the
    finder: one bad coordinate must never leave a ship without damage control, and a
    shipData resize can invalidate a good declaration without anyone touching the floor
    plan. ``grid_ascii_validate`` is where an author is told loudly.
    
    Args:
        SBS: The sbs module.
        ship_id (int): The host ship.
        hm: Its hull map.
        declared (list | None): ``[x, y]`` the interior asked for, if any.
        used (set, optional): ``(x, y)`` cells already taken in this pass, to spread.
        prefer_empty (bool): Try the unoccupied finder before the tolerant one.
        who (str): Name for the warning, e.g. ``"DC2"``.
    
    Returns:
        list[int] | None: ``[x, y]``."""
def _grid_retire_extra_damcons (hm, ship_id, count):
    """Delete DC teams above ``count`` - a hull whose declaration shrank, or a refit.
    
    Matches ``DC<n>`` carrying the ``damcons`` role only, so nothing else on the grid can
    be caught by a name that happens to look like one."""
def _grid_say (msg, level='warning'):
    """Say something about the engineering grid, on a channel the ENGINE actually shows.
    
    Every failure on this path used to be a bare ``return``. A hull that was never
    merged, a floor plan that was rejected, and a misspelled ``ship:`` key all present
    identically - as a dead Engineering console with nothing written anywhere. That cost
    a full engine session to diagnose once, and it would have cost the same every time.
    
    Two channels on purpose. ``log()`` is the library convention and is what a headless
    run and the test suite read, but in the engine it goes to a Python logger with NO
    handler attached, so it is invisible exactly where this class of bug lives. ``DEBUG``
    writes ``debug.log`` beside the executable, which survives the session.
    
    ASCII only - these strings can reach engine-rendered surfaces."""
def _grid_spawn_chunk (ship_id, so, theme_name, chunk, counts):
    """Spawn one slice of a hull's rooms. Returns False if the engine refused one.
    
    A PHASED build queues its slices ahead of time, so once one fails the rest are
    already scheduled - they check this and do nothing rather than half-filling a hull."""
def _grid_unused_point (hm, point, used):
    """The nearest open cell to ``point`` that is not already in ``used``.
    
    ``point`` itself when it is free, and ``point`` again when the hull has no free cell
    left - a ship with fewer open cells than damcon teams still gets its teams, stacked,
    rather than losing one.
    
    Only reached when the occupancy-tolerant finder had to be used, i.e. on a hull with no
    empty cell. The engine's finders take no "avoid these" argument and have no memory
    across a loop, so spreading the teams is the caller's job.
    
    Args:
        hm: The ship's hull map.
        point (list[int]): ``[x, y]`` the engine chose.
        used (set): ``(x, y)`` cells already taken in this pass.
    
    Returns:
        list[int]: ``[x, y]``."""
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
def all_roles (roles: str):
    """Return the set of agent IDs that hold every one of the given roles.
    
    Args:
        roles (str): A comma-separated list of role names.
    
    Returns:
        set[int]: IDs of agents that have all specified roles."""
def comms_broadcast (ids_or_obj, msg, color=None, category=None, severity=None) -> None:
    """Send a text message to the text waterfall of one or more targets.
    
    Accepts player ship IDs or client/console IDs. Ship IDs use
    ``send_message_to_player_ship``; client IDs use
    ``send_message_to_client``.
    
    ALSO appends to the ship's log (``procedural.log_panel``), which is the waterfall's
    replacement - see mkdocs build/messages.md. Both surfaces are written during the changeover
    so they can be compared side by side; retiring the waterfall is then deleting the
    engine half of this function.
    
    Args:
        ids_or_obj: Agent ID, client ID, or set/list of either to send to.
            Pass ``None`` to send to the event's ``parent_id``.
        msg (str): The message text. Supports ``{var}`` interpolation.
        color (str, optional): Text color as a name or hex string, e.g.
            ``"red"`` or ``"#3ff"``. Defaults to ``"#fff"``.
        category (str, optional): Which log TAB this belongs in - ``"ship"`` or
            ``"mission"``. Omitted (the default) means it appears in the Log tab, which
            shows everything, and in no subset tab. That is what makes tagging
            incremental: nothing is lost by not being tagged.
        severity (str, optional): ``"tip"`` / ``"warning"`` / ``"danger"``. Draws the
            entry as a callout. Reserved for things that matter - a box costs two rows,
            so one per line would halve how much log fits on screen.
    
    Example:
        comms_broadcast(SHIP_ID, "Red alert!", color="red", severity="danger")"""
def convert_system_to_string (the_system):
    """Convert a ship system enum or integer to its role-name string.
    
    Args:
        the_system (sbs.SHPSYS | int | str): The system enum, integer index,
            or role-name string.
    
    Returns:
        str: Role name for the system (``"weapon"``, ``"engine"``,
            ``"sensor"``, or ``"shield"``)."""
def explode_player_ship (id_or_obj):
    """Mark a player ship as destroyed and emit the ``player_ship_destroyed`` signal.
    
    The ship is made invisible and tagged ``"exploded"`` rather than deleted
    immediately, allowing scripts to react before removal.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_pos (id_or_obj):
    """Return the current position of an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        Vec3 | None: The agent's position, or ``None`` if it does not exist."""
def grid_add_node_wear (id_or_obj, amount, ship_id=None):
    """Add to a node's wear. Negative restores it."""
def grid_apply_system_damage (id_or_obj):
    """Update system-damage counts and coefficients; explode the ship if all nodes are damaged.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
    
    Returns:
        bool: ``True`` if the ship has been destroyed, ``False`` otherwise."""
def grid_closest (grid_obj, target_set=None, max_dist=None, filter_func=None) -> sbs_utils.agent.CloseData:
    """Find and target the closest object matching the criteria
    
    Args:
        grid_obj (Agent | int): The agent or id
        target_set (set[Agent], optional): The items to test. Defaults to None.
        max_dist (float, optional): max distance. Defaults to None.
        filter_func (Callable, optional): additional filer function. Defaults to None.
    
    Returns:
        CloseData: The gird close data of the closest object"""
def grid_count_grid_data (ship_key, role, default=0):
    """Count the number of grid items that have a given role in the ship's JSON data.
    
    Args:
        ship_key (str): The ship art-ID key to look up in the grid data.
        role (str): Role name to match against each grid item's role list.
        default (int, optional): Value returned if the ship key is not found in
            the grid data. Defaults to 0.
    
    Returns:
        int: Number of grid items with the specified role."""
def grid_damage_grid_object (ship_id, grid_id, damage_color):
    """Mark a grid object as damaged and apply a damage color to its icon.
    
    Tools, markers, and rally-point objects are ignored.
    
    Args:
        ship_id (Agent | int): The player ship agent ID or object.
        grid_id (Agent | int): The grid object to damage.
        damage_color (str): Color to apply to the damaged grid-object icon."""
def grid_damage_hallway (id_or_obj, loc_x, loc_y, damage_color):
    """Spawn a fire/damage marker at an empty hallway grid cell.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        loc_x (int): Grid column of the hallway cell.
        loc_y (int): Grid row of the hallway cell.
        damage_color (str): Color to apply to the damage marker icon."""
def grid_damage_pos (id_or_obj, loc_x, loc_y):
    """Apply internal damage at a specific grid cell.
    
    If no grid object occupies the cell a hallway-fire marker is placed
    instead.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        loc_x (int): Grid column to damage.
        loc_y (int): Grid row to damage."""
def grid_damage_system (id_or_obj, the_system=None):
    """Damage a random undamaged grid node for the specified ship system.
    
    Args:
        id_or_obj (Agent | int | CloseData | SpawnData): The player ship.
        the_system (sbs.SHPSYS | int | str, optional): The system to damage.
            If ``None``, a system is chosen at random. Defaults to None.
    
    Returns:
        bool: ``True`` if a node was damaged; ``False`` if no undamaged nodes
            remain or the ship has already exploded."""
def grid_damcon_count (id_or_obj, layout=None):
    """How many damcon teams this ship's interior declares.
    
    ``3`` for every hull that declares nothing, which is nearly all of them.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        layout (str, optional): Layout name. Defaults to the ship's ``grid_layout``.
    
    Returns:
        int: The team count."""
def grid_delete_object (host_id_or_obj, id_or_obj):
    """Delete a single grid object, deferring the native free.
    
    Tombstones the grid agent now (dropped from ``Agent.all``/roles, so
    ``object_exists()``/``to_object()`` report it gone this instant) and enqueues
    the native ``sbs.delete_grid_object(host_id, id)`` to run at the end of the
    event handler. Mirrors ``SpaceObject.delete_object`` for grid objects, closing
    the same-tick use-after-free window. See ``DeleteQueue``.
    
    Args:
        host_id_or_obj (Agent | int): The host ship the grid object lives on.
        id_or_obj (Agent | int): The grid object (or its id) to delete."""
def grid_get_damcons (ship_key, layout=None):
    """The damcon-team declaration for a hull (or one of its layouts), or ``None``.
    
    ``None`` - which is what every hull that says nothing returns, and that is nearly all
    of them - means "three teams, wherever the engine puts them", exactly as before. That
    sentinel is what keeps the shipped floor plans and every third-party hull working
    unchanged.
    
    Otherwise ``{"count": int, "posts": [[x, y], ...]}``: how many damage-control teams
    this interior has, and where they are stationed. Fewer posts than teams is fine - the
    rest are engine-placed. A post is also the team's permanent rally point, because the
    prefab spawns the rally marker on the cell it is given, so posting a team by the
    nacelles is all it takes to keep it there.
    
    Read as a sibling of ``grid_objects``/``theme``, at the entry level or inside a named
    layout, most specific winning - the same shape :func:`grid_get_theme_name` uses. A
    layout expressed as a bare list has nowhere to hold one and falls back to the entry.
    
    Args:
        ship_key (str): Ship key as defined in shipData.
        layout (str, optional): Layout name. Defaults to ``"default"``.
    
    Returns:
        dict | None: Normalized declaration, or ``None`` when the hull declares nothing."""
def grid_get_grid_current_theme ():
    """Get the currently active grid theme data.
    
    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc."""
def grid_get_grid_data () -> dict:
    """Get the grid data from all the grid_data.json files
    
    Returns:
        dict: a dictionary of grid data objects.
        * key (str): The key of the dict, which is a ship key as defined in shipData.
        * value (dict): A dict with `grid_objects` as a key, and a list of grid object data as the value."""
def grid_get_grid_named_theme (name):
    """Get a grid theme by name, falling back to the current theme if not found.
    
    Args:
        name (str | None): Theme name to look up (case-insensitive), or
            ``None`` to return the current theme.
    
    Returns:
        dict: Theme dict with keys such as ``name``, ``colors``, ``icons``,
            ``damage_colors``, etc."""
def grid_get_item_theme_data (roles, name=None):
    """Get icon, scale, color, and damage color for a set of roles from the grid theme.
    
    Roles are matched in reverse priority order so the last role in the list
    takes precedence. Falls back to ``"default"`` entries when no role matches.
    
    Args:
        roles (str): Comma-separated role names.
        name (str | None, optional): Theme name to use. ``None`` uses the
            current theme. Defaults to None.
    
    Returns:
        RetVal: Object with ``.icon`` (int), ``.scale`` (float), ``.color``
            (str), and ``.damage_color`` (str) attributes."""
def grid_get_layout (ship_key, layout=None):
    """The grid-object list for one hull's layout.
    
    A hull has N named LAYOUTS, not one interior - a full authored interior, a cheap
    systems-only one, a jump-drive refit of the same hull. ``grid_objects`` at the top
    level is still read as the default, so every existing entry keeps working::
    
        {"tsn_light_cruiser": {"grid_objects": [...]}}                    # still valid
        {"pirate_brigantine": {"layouts": {"default": {...},
                                           "systems": {...}}}}
    
    A layout may be either ``{"grid_objects": [...]}`` or a bare list.
    
    Args:
        ship_key (str): Ship key as defined in shipData.
        layout (str, optional): Layout name. Defaults to ``"default"``, then to the
            top-level ``grid_objects``.
    
    Returns:
        list | None: The grid object dicts, or ``None`` when there is no such interior."""
def grid_get_max_hp ():
    """Return the current global maximum HP value for damcon-team grid objects.
    
    Returns:
        int: The max HP setting (default 6)."""
def grid_get_theme_name (ship_key, layout=None):
    """The theme a hull (or one of its layouts) asks for, or ``None`` for the current one.
    
    Theme selection used to be a single module-level index - a whole-game setting - which
    made per-race themes impossible. A hull, or a single layout of it, can now name its
    own: a captured TSN hull refitted by pirates is the same mesh with a different
    interior AND a different vocabulary."""
def grid_interior_arm (over=None, chunk=None):
    """The hulls are final: build every interior that was asked for, phased over ticks.
    
    Call this once a map has settled - past the roster cull and past whatever re-hulling
    the map does for itself. Requests made after this point are queued immediately, so a
    mid-game refit still gets an interior without anyone re-arming anything.
    
    Args:
        over (float, optional): sim-seconds to spread the work across (default 4).
        chunk (int, optional): rooms created per slice (default 16).
    
    Returns:
        int: how many ships were released to build."""
def grid_interior_flush ():
    """Build everything outstanding right now.
    
    For a test, a headless conformance run, or anything that cannot wait for the drip."""
def grid_interior_is_armed ():
    """Whether interiors are being built as they are requested."""
def grid_interior_pending ():
    """Ships recorded but not yet built, plus queued work still to run."""
def grid_interior_request (id_or_obj, layout=None):
    """Ask for this ship's engineering interior. Built ONCE, when the hull has settled.
    
    The call a ``//spawn`` route should make. Nothing is created here: before
    :func:`grid_interior_arm` the ship is simply recorded, and after it the build is
    queued and dripped over ticks. Either way the hull is read when the build RUNS, so a
    ship re-hulled between the request and the build gets the interior it ends up
    needing - not the one it had when it spawned.
    
    Idempotent by ship: requesting the same ship repeatedly produces one build.
    
    Args:
        id_or_obj (Agent | int): the ship.
        layout (str, optional): a named layout; defaults to the ship's own.
    
    Returns:
        bool: whether the request was recorded."""
def grid_interior_reset ():
    """Drop queued interior work and disarm (mission reset)."""
def grid_node_apply_color (id_or_obj, theme_name=None):
    """THE place a grid node's icon color is decided.
    
    Four tiers, one write point - so a node can never be drawn in a color that
    disagrees with its condition:
    
    * damaged -> the theme's ``damage_colors``
    * worn    -> the theme's ``worn_colors`` (Gold by default)
    * tuned   -> the theme's ``tuned_colors`` (cyan by default)
    * nominal -> the node's OWN cached healthy color, from inventory ``color``,
      written at spawn - so a re-skinned room keeps its own hue instead of being
      flattened to a theme default.
    
    Args:
        id_or_obj: the grid node.
        theme_name (str, optional): theme to read; None uses the current one.
    
    Returns:
        str | None: the color written, or None if there was no blob to write to."""
def grid_node_efficiency (id_or_obj):
    """What this node contributes to its system's effectiveness.
    
    damaged 0.0 | worn WEAR_WORN_FACTOR | nominal 1.0 | tuned 1.0 + WEAR_TUNED_BONUS.
    
    A node nothing has ever worn reads WEAR_NOMINAL and so weighs exactly 1.0 - which
    is what makes the whole idea inert until something writes wear, and why
    set_damage_coefficients produces numbers identical to the old undamaged/total
    fraction on a ship that has never worn anything."""
def grid_node_is_system (id_or_obj):
    """Is this node part of a ship SYSTEM - the only kind of node that wears?
    
    Every shipped interior says so in its own roles: a system room's roles begin with
    ``system`` (``system,weapon,beam``, ``system,ENGINE,impulse``, ``system,shield,fwd``)
    and a crew space's begin with ``room`` (``room,cabin,gym``, ``room,cabin,quarters``,
    ``room,bay,cargo``). Measured across `data/grid_data.json`: 38 rolesets, 11 of them
    systems, and not one where `system` appears anywhere but first. LegendaryMissions'
    docking repair and the EPad room list already read the same role.
    
    Wear is a SYSTEM idea - a tuned beam array fires harder, a worn impulse drive pushes
    less - and none of that means anything for a gymnasium. Before this, upkeep aged
    every node on the ship, so the gym went worn on schedule and Engineering offered a
    damage-control team to go and tune it.
    
    Damage is different and is deliberately NOT gated: a fire in the galley is a real
    fire, and a team still goes and puts it out."""
def grid_node_state (id_or_obj):
    """The node's condition as one word.
    
    Damage wins over wear - a broken node is "damaged" whatever its wear says,
    which is why grid_damage_grid_object clears `__worn__`.
    
    Args:
        id_or_obj: The grid node (id or Agent).
    
    Returns:
        str: "damaged", "worn", "tuned" or "nominal"."""
def grid_node_wear (id_or_obj):
    """How worn a grid node is, 0.0 (perfect) to 1.0 (worn out).
    
    A node nothing has ever worn reads WEAR_NOMINAL, so callers never have to
    special-case "no wear recorded".
    
    Args:
        id_or_obj: The grid node (id or Agent).
    
    Returns:
        float: the node's wear."""
def grid_objects (so_id) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship
    
    Args:
        so_id (Agent | int): agent id or object
    
    Returns:
        set[int]: a set of agent ids"""
def grid_objects_at (so_id, x, y) -> set[int]:
    """Get a set of agent ids of the grid objects on the specified ship, at the location specified
    
    Args:
        so_id (Agent | int): agent id or object
        x (int): The x grid location
        y (int): The y grid location
    
    Returns:
        set[int]: A set of agent ids"""
def grid_rebuild_grid_objects (id_or_obj, grid_data=None, layout=None):
    """Rebuild all engineering-grid objects on a ship, NOW, in this frame.
    
    Deletes any existing grid objects, re-creates them from the layout registered for the
    ship's shipData key, and re-creates the damcon teams, the position marker and the
    EPad.
    
    Prefer :func:`grid_interior_request` for a ship that is being set up. This builds
    immediately, which is right for a mid-game refit a player is watching, and wrong at
    game start - see that function for why.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        grid_data (dict, optional): **Accepted and deliberately ignored.** Kept because
            missions pass it positionally (``LegendaryMissions/ai/grid_ai.mast``) and
            removing it would break them.
        layout (str, optional): Which named layout to build. Defaults to the ship's own
            ``grid_layout`` inventory value, then ``"default"``.
    
    ``grid_data`` stopped being read when the lookup moved to :func:`grid_get_layout`,
    which resolves the module-level store itself. That is not an oversight to tidy up -
    honoring the argument again would REINTRODUCE a restart bug. The one caller that
    passes it captures it once, at top level, into a MAST ``shared`` variable; but
    ``grid_reset_caches()`` rebinds the store to a fresh dict on a mission restart, so
    that snapshot pins run 1's dict while every floor plan merged for run 2 lands in the
    new one. Reading the global each time is what keeps the two in step."""
def grid_repair_grid_objects (player_ship, id_or_set, who_repaired=None):
    """Repair one or more grid objects and update the ship's damage state.
    
    Hallway-fire markers are deleted; system nodes have their icon color
    restored and the system-damage count decremented. Recomputes damage
    coefficients if any system node was healed.
    
    Args:
        player_ship (Agent | int): The player ship agent ID or object.
        id_or_set (Agent | int | set[Agent | int]): Grid object(s) to repair.
        who_repaired (Agent | int, optional): The damcon-team agent that
            performed the repair (used to remove work-order links). Defaults
            to None."""
def grid_repair_system_damage (id_or_obj, the_system=None):
    """Repair a single damaged grid node for the specified system.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        the_system (sbs.SHPSYS | int | str, optional): The system to repair.
            If ``None``, a system is chosen at random. Defaults to None.
    
    Returns:
        bool: ``True`` if a node was repaired; ``False`` if no damaged nodes
            remain for that system."""
def grid_restore_damcons (id_or_obj, layout=None):
    """Restore all damcon teams on a ship to full health, creating them if missing.
    
    How many teams there are, and where they stand, come from the hull's interior data
    when it says (``grid_get_damcons``); otherwise three teams wherever the engine puts
    them, exactly as before. A declared post is also the team's permanent rally point,
    because the prefab spawns the rally marker on the cell it is handed.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        layout (str, optional): Layout name. Defaults to the ship's ``grid_layout``
            inventory value. Pass it explicitly when rebuilding into a layout the ship has
            not been switched to yet."""
def grid_set_hp (ship_id, GRID_OBJECT_ID, hp):
    """Set the HP of a damcon-team grid object and emit the ``life_form_hp_changed`` signal.
    
    Args:
        ship_id (Agent | int): The player ship agent ID or object.
        GRID_OBJECT_ID (Agent | int): The damcon-team grid object ID or agent.
        hp (int): The new HP value to assign."""
def grid_set_max_hp (max_hp):
    """Set the global maximum hit-point value for damcon-team grid objects.
    
    Args:
        max_hp (int): New maximum HP value. Defaults to 6 at module load."""
def grid_set_node_wear (id_or_obj, value, ship_id=None):
    """Set a node's wear, reconciling everything that follows from it.
    
    The ONLY writer. It clamps, stores, adds or removes ``__worn__``, repaints
    through grid_node_apply_color, and recomputes the ship's coefficients - but only
    when the TIER actually changed, so wear moving within a band costs one dict write
    and nothing else.
    
    Only a SYSTEM node carries wear at all (see ``grid_node_is_system``); on anything
    else this is a no-op that answers with the nominal reading. Gating the one writer
    rather than each caller is what makes the whole model system-only: upkeep, the
    wear a damcon patch leaves behind, a mission's own call, all of it.
    
    ``__worn__`` never coexists with ``__damaged__``: damage supersedes wear, and a
    worn node keeps ``__undamaged__`` so nothing that counts undamaged system nodes
    changes meaning because a node got tired.
    
    Args:
        id_or_obj: the grid node.
        value (float): the new wear, clamped to 0.0 - 1.0.
        ship_id (optional): the host, for the coefficient recompute. Read from the
            node when not given.
    
    Returns:
        float: the wear actually stored."""
def grid_set_wear_tuning (worn_factor=None, tuned_bonus=None, worn_min=None, tuned_max=None, upkeep_rate=None, **rates):
    """Retune the wear model for a mission that wants different numbers.
    
    ``grid_set_wear_tuning(tuned_bonus=0.0)`` gives strict parity with the old
    coefficients even on a ship with tuned nodes - the escape hatch for a mission
    that wants the maintenance loop without any over-unity.
    
    Any arrival RATE can be passed by its short name as a keyword, so a mission tunes
    the feel without touching the library::
    
        grid_set_wear_tuning(beam_hit=0.0005, warp_minute=0.05)
        grid_set_wear_tuning(upkeep_rate=0)     # no time-based upkeep at all
    
    An unknown rate name is a warning, not a silent no-op - a typo here would look
    exactly like "the dial does nothing"."""
def grid_spawn (id, name, tag, x, y, icon_index, color, roles):
    """Spawn a grid object (engineering component) onto a ship's grid.
    
    Args:
        id (Agent | int): The ship agent ID or object to attach the grid object
            to.
        name (str): Display name of the grid object.
        tag (str): Tag identifying the grid object's side or type.
        x (int): Column position on the engineering grid.
        y (int): Row position on the engineering grid.
        icon_index (int): Icon index for the grid display.
        color (str): Display color string.
        roles (str): Comma-separated roles to assign to the grid object.
    
    Returns:
        GridObject: The newly created grid object."""
def grid_system_signature (id_or_obj):
    """A value that CHANGES whenever an indicator row should be redrawn.
    
    For ``on change grid_system_signature(ship_id):`` - the polling form, which is
    what a console layout can actually use. A ``//damage/internal`` route fires on
    the SERVER and would not repaint a client's panel; ``on change`` re-evaluates on
    the console itself and so cannot miss a hit.
    
    Args:
        id_or_obj: The ship (id, Agent or SpaceObject).
    
    Returns:
        str: e.g. ``"weapon1/0/0/6,engine0/1/0/4"`` - hurt/worn/tuned/total per pool."""
def grid_system_states (id_or_obj):
    """What each of the ship's system pools is worth right now.
    
    Only pools the ship actually HAS are returned - a fighter with no shield rooms
    gets no shield light rather than a permanently-green one for a system it cannot
    lose. Order is fixed by GRID_SYSTEM_ICONS so a row built from this never
    reshuffles under the player between repaints.
    
    Args:
        id_or_obj: The ship (id, Agent or SpaceObject).
    
    Returns:
        list[dict]: one per pool, with ``role``, ``icon``, ``hurt``, ``worn``,
        ``tuned``, ``total``, ``state`` ("hurt"/"worn"/"tuned"/"ok") and the theme
        ``color`` to draw it in."""
def grid_take_internal_damage_at (id_or_obj, source_point, system_hit=None, damage_amount=None):
    """Apply internal damage to a ship at a 3D world position.
    
    Maps the 3D position to the nearest grid cell, then damages the grid
    objects at that cell (or a hallway marker if the cell is empty). Also
    injures any damcon-team lifeforms at the impact location.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        source_point (Vec3): 3D position of the hit.
        system_hit (sbs.SHPSYS | int | str, optional): Unused. Defaults to
            None.
        damage_amount (int, optional): Unused. Defaults to None.
    
    Returns:
        bool: ``True`` if the ship was destroyed by this damage."""
def grid_tune_grid_object (ship_id, node_id, who=None):
    """A node brought back to spec - what a maintenance order delivers.
    
    Wear to zero, ``__worn__`` off, drawn in the tuned color, coefficients
    recomputed, and the order closed for EVERY team on it rather than just whoever
    happened to be standing there.
    
    Args:
        ship_id: the host ship.
        node_id: the node to tune.
        who (optional): the team that did it, carried on the signal.
    
    Returns:
        bool: whether anything was tuned."""
def grid_valid_blob (id_or_obj):
    """Return a grid object's engine blob only if its backing space object is
    still valid, otherwise ``None``.
    
    A destroyed host ship leaves the grid object's ``Agent`` and its cached blob
    wrapper in place, so ``to_blob`` still returns a non-``None`` wrapper -- but
    the engine raises ``ValueError: invalid space object`` on any ``get``/``set``
    of that wrapper. This probes cheaply so callers can guard the dead-object
    case with a plain ``is None`` check, the same as a missing object.
    
    Args:
        id_or_obj (Agent | int): Agent id or object.
    
    Returns:
        data_set | None: The live blob, or ``None`` if the object is gone or its
            host space object has been destroyed."""
def grid_wear_beam_hit (ship_id, count=1):
    """Wear a ship's beam systems for landing `count` beam hits.
    
    THE AMOUNT IS LOOKED UP HERE, which is the whole reason this exists. `WEAR_PER_*` are
    module-level constants, and only FUNCTIONS become MAST globals - a constant named in
    a `.mast` expression is a NameError, every time, at the moment the route fires. So
    `grid_wear_system(id, "beam", WEAR_PER_BEAM_HIT)` in a route reads perfectly and
    crashes on the first shot.
    
    `grid_wear_shield_hit` and `grid_wear_travel` already had this shape; beams and tubes
    did not, and those were the two routes that fired.
    
    Args:
        ship_id: the ship that fired.
        count (int, optional): how many hits to charge for. Defaults to 1.
    
    Returns:
        int: how many nodes were worn."""
def grid_wear_shield_hit (ship_id, face):
    """Wear the shield facing that took a hit.
    
    Args:
        ship_id: the ship that was hit.
        face (int): 0 forward, anything else aft - the same two pools
            set_damage_coefficients writes as shield_damage_coeff[0] and [1].
    
    Returns:
        int: how many nodes were worn."""
def grid_wear_system (ship_id, sys_role, amount, count=1):
    """Wear `count` random working nodes of a system.
    
    Random rather than spread evenly: wearing every node a hair each time would move
    a whole pool across the threshold together, so the ship would go from fine to
    fully worn in one tick with nothing in between.
    
    Damaged nodes are skipped - they are already at zero effectiveness, so wear on
    them would mean nothing and would be lost the moment they were repaired.
    
    Args:
        ship_id: the ship.
        sys_role (str): a role or comma-separated roles, e.g. "beam", "shield,fwd".
        amount (float): wear to add to each chosen node.
        count (int, optional): how many nodes. Defaults to 1.
    
    Returns:
        int: how many nodes were worn."""
def grid_wear_travel (ship_id, throttle=None):
    """Wear the drive a ship is actually using, for one minute of travel.
    
    ``playerThrottle`` is <= 1.0 for impulse and > 1.0 for warp (the mock's model is
    calibrated against the engine's own speed capture), so this splits the wear
    between the impulse and warp pools rather than charging both.
    
    The read is coalesced because **the engine answers None for a blob field nothing
    has set** - a ship sitting still since spawn has never had a throttle written.
    An unguarded compare is ``None > 1.0`` on a real bridge, and since a failing
    expression stops the command, the caller would simply stop working with no
    symptom beyond "wear stopped happening".
    
    Args:
        ship_id: the ship.
        throttle (float, optional): override, for tests. Read from the blob when None.
    
    Returns:
        str | None: which pool was worn - "warp", "impulse", or None when stopped."""
def grid_wear_tube_shot (ship_id, count=1):
    """Wear a ship's torpedo systems for launching `count` rounds.
    
    See `grid_wear_beam_hit` for why the amount is looked up here rather than passed in
    from MAST.
    
    Args:
        ship_id: the ship that launched.
        count (int, optional): how many launches to charge for. Defaults to 1.
    
    Returns:
        int: how many nodes were worn."""
def grid_wear_upkeep (ship_id, amount=None):
    """Age every working SYSTEM node on a ship by one upkeep step.
    
    Crew spaces are left alone: a gymnasium does not drift out of tune, and one that
    read `worn` put a tuning job for it on the Engineering board.
    
    Args:
        ship_id: the ship.
        amount (float, optional): defaults to WEAR_UPKEEP_RATE.
    
    Returns:
        int: how many nodes were aged."""
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
def is_dev_build ():
    """Check if the current mission is a development build.
    
    Returns True if a .git directory exists in the mission folder.
    
    Returns:
        bool: True if running in development mode, False otherwise."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
def prefab_spawn (label, data=None, OFFSET_X=None, OFFSET_Y=None, OFFSET_Z=None):
    """Spawn a prefab label as an independent task and return it.
    
    Positional keys ``START_X``, ``START_Y``, ``START_Z`` inside ``data``
    set the spawn origin (default 0). The ``OFFSET_*`` params shift that
    origin without modifying the original ``data`` dict. If ``data`` contains
    a ``NAME`` key with a ``#`` placeholder, ``prefab_autoname`` is applied
    to generate a unique name.
    
    Args:
        label (str | Label): The label to spawn.
        data (dict, optional): Variables passed into the prefab task. May
            include ``START_X``, ``START_Y``, ``START_Z``, and ``NAME``.
            Defaults to None.
        OFFSET_X (float, optional): X offset added to ``START_X``. Defaults
            to None (no offset).
        OFFSET_Y (float, optional): Y offset added to ``START_Y``. Defaults
            to None (no offset).
        OFFSET_Z (float, optional): Z offset added to ``START_Z``. Defaults
            to None (no offset).
    
    Returns:
        MastAsyncTask: The running prefab task, or ``None`` if the label is
            invalid."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Reaches the server console, for the same reason :func:`add_role` does - and it has
    to be the same set, or a console that could gain a role could never lose it.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def respawn_player_ship (id_or_obj):
    """Respawn a previously destroyed player ship at its original spawn position.
    
    Restores the ship's art ID, repositions it to the spawn point, and removes
    the ``"exploded"`` role.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_damage_coefficients (id_or_obj):
    """Recalculate and write the damage coefficients for all ship systems.
    
    For each system (beam, torpedo, impulse, warp, maneuver, sensors, shields)
    computes the ratio of undamaged to total nodes and writes it to the blob.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def settings_get_defaults ():
    """Return the merged default settings dict, loading ``settings.yaml`` or ``setup.json`` if present.
    
    Results are cached after the first call. Mission-specific values from the
    YAML/JSON file override the built-in defaults.
    
    Returns:
        dict: The default settings mapping."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a list.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        list: A list containing whatever was passed in; ``None`` becomes ``[]``."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
