from sbs_utils.helpers import FrameContext
def _side_csv_list (value):
    """A comma string OR a list/set -> a stripped list of non-empty items."""
def _warn_missing_side (key):
    """Emit "Side not found" AT MOST ONCE per genuinely-unknown NAMED side.
    
    This is the SINGLE gate for the message: every unresolved side lookup routes
    here, and this alone decides whether the miss is worth surfacing. A miss is
    NOT worth reporting when it isn't really a missing side:
    
    - ``""`` / an all-``#`` hidden marker -> the object has NO side (asteroids,
      cambots, hidden objects). A legitimate state, not a lookup failure.
    - a ``monster`` feral side -> monsters intentionally ride an unregistered
      side; the brain drives their aggression, so this is expected.
    - already reported -> deduped, so a per-tick diplomacy sweep over an unknown
      side warns once, not on every evaluation.
    
    Keeping the whole policy here means callers never have to special-case any of
    it: ``to_side_id`` just hands every miss to this function."""
def get_data_set_value (id_or_obj, key, index=0):
    """Get a value from the engine data-set (blob) of a space or grid object.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
    
    Returns:
        any: The stored value, or ``None`` if the object or key is not found."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def has_link (link_name: str):
    """Return the set of agent IDs that have at least one link under a given name.
    
    Despite the ``has_`` prefix this returns a set, not a bool. Use the result
    to iterate or test membership.
    
    Args:
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all agents that own a link entry with this name."""
def has_link_to (link_source, link_name: str, link_target) -> bool:
    """Return whether a source agent has a specific link to a target.
    
    Args:
        link_source (Agent | int): The agent ID or object hosting the link.
        link_name (str): The link key name.
        link_target (Agent | int): The target agent ID or object to check.
    
    Returns:
        bool: ``True`` if the link from source to target exists."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def is_allied_to_players (target, scope_role=None) -> bool:
    """Return whether ``target`` is friendly to some player side (same side or
    allied), optionally requiring a class role. The friend analog of
    :func:`is_hostile_to_players`.
    
    Args:
        target (str | int | Agent): The candidate to test.
        scope_role (str, optional): A role the target must hold. Defaults to None.
    
    Returns:
        bool: ``True`` if ``target`` is friendly to any player side."""
def is_hostile_combatant (observer, target, scope_role=None) -> bool:
    """Return whether ``target`` is a hostile combatant relative to ``observer``.
    
    The boolean single source of truth for "may I treat this as an enemy": ``target``
    is diplomatically HOSTILE to ``observer``'s side AND still carries the combat
    class role ``scope_role``. This honours both "no longer my enemy" conventions at
    once — a ceasefired/neutral side fails :func:`side_are_enemies`, and a
    surrendered/defected ship has had ``scope_role`` removed. Pass
    ``scope_role=None`` for a pure diplomacy test.
    
    Args:
        observer (str | int | Agent): The point-of-view side/agent.
        target (str | int | Agent): The candidate to test.
        scope_role (str, optional): Combat-class role the target must still hold.
            Defaults to ``"raider"``.
    
    Returns:
        bool: ``True`` if ``target`` is a hostile combatant to ``observer``."""
def is_hostile_to_players (target, scope_role=None) -> bool:
    """Return whether ``target`` is a hostile combatant to at least one player side.
    
    The player-perspective boolean (see :func:`is_hostile_combatant`): ``target``
    still carries the combat class role ``scope_role`` AND is diplomatically HOSTILE
    to some current player side. A ceasefired/neutral or surrendered ship is False.
    Pass ``scope_role=None`` for a pure diplomacy test.
    
    Args:
        target (str | int | Agent): The candidate to test.
        scope_role (str, optional): Combat-class role the target must hold. Defaults
            to ``"raider"``.
    
    Returns:
        bool: ``True`` if ``target`` is a hostile combatant to any player side."""
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
def players_allied_members (scope_role=None):
    """Return the agent IDs on a PLAYER side or a side ALLIED to one (the "friendly
    to the players" set), optionally intersected with a class role.
    
    The player-perspective ally set (friend analog of :func:`players_hostile_members`)
    — for friendly-base / friendly-ship checks not tied to a single observer, e.g.
    "all our stations are gone" lose conditions. Covers every player side and their
    allies, so it works with a second player side or an allied faction instead of a
    hardcoded side role like ``role("tsn")``.
    
    Args:
        scope_role (str, optional): A role to intersect with (e.g. ``"station"``).
            Defaults to None. Prefer a scope role (the raw set includes clients).
    
    Returns:
        set[int]: IDs friendly to the players, optionally scoped to ``scope_role``."""
def players_ceasefire (relation=None):
    """End the attack: make every side currently HOSTILE to a player side NEUTRAL.
    
    The diplomacy expression of "call off the enemies" at the end of a game. The older
    way to do this was to strip a shared combat tag from every ship
    (``remove_role(role("raider"), "raider")``), which only stopped the consumers that
    happened to scope by that tag -- the ships stayed diplomatically hostile, so brains
    still shot and sensor contacts stayed red. Changing the RELATION stops all of them
    at once, and is reversible (re-declare HOSTILE to resume).
    
    Applies to whole sides, not individual ships; a single ship leaving the fight is
    :func:`side_surrender`.
    
    NOT self-inverse, and not idempotent in the useful direction: it reads the CURRENT
    hostile pairs and neutralizes them, so a second call finds nothing hostile and
    changes nothing. It does not remember what was hostile, so "undo" means
    re-declaring HOSTILE (``side_set_relations`` / re-running your side declaration),
    not calling this again. Unlike :func:`side_ensure` / :func:`side_create`, replaying
    it is therefore not a repair.
    
    Args:
        relation (sbs.DIPLOMACY, optional): Relation to set. Defaults to ``NEUTRAL``.
    
    Returns:
        int: The number of side pairs changed."""
def players_hostile_members (scope_role=None):
    """Return the agent IDs on a side HOSTILE to at least one current player ship's
    side, optionally intersected with a combat-class role.
    
    The player-perspective form of :func:`side_hostile_members` — for checks that are
    not tied to a single observer: "are there enemies left" (victory), "count the
    threat", "was an enemy killed" (reward). Diplomacy-driven, so ceasefired/neutral
    sides drop out and multiple player sides are all accounted for. Empty when there
    are no player ships with a side.
    
    Args:
        scope_role (str, optional): A combat-class role (e.g. ``"raider"``) to
            intersect the result with. Defaults to None.
    
    Returns:
        set[int]: IDs hostile to some player side, optionally scoped to ``scope_role``."""
def players_hostile_ships ():
    """Space objects hostile to at least one current PLAYER side and still in the fight.
    
    Player-perspective form of :func:`side_hostile_ships` — for checks not tied to one
    observer ("are there enemies left", "count the threat"). Replaces
    ``players_hostile_members("raider")`` and the bare ``role("raider")`` sweeps.
    
    Returns:
        set[int]: IDs hostile to some player side."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_data_set_value (to_update, key, value, index=0):
    """Set a value in the engine data-set (blob) for one or more space or grid objects.
    
    If ``to_update`` is a set or list, the value is applied to each member.
    
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The
            agent(s) to update.
        key (str): The data-set key.
        value (any): The value to store.
        index (int, optional): The slot index within that key. Defaults to 0."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def side_allied_members (observer, scope_role=None):
    """Return the agent IDs on ``observer``'s OWN side or a side ALLIED to it (the
    "friendly" set from observer's point of view), optionally intersected with a
    class role. The ally analog of :func:`side_hostile_members`.
    
    Args:
        observer (str | int | Agent): Side key, side agent ID, or any object whose
            side is used as the point of view.
        scope_role (str, optional): A role to intersect the result with (e.g.
            ``"station"``). Defaults to None (all own+allied members). Prefer a
            scope role, as the raw set includes non-ship side members (clients).
    
    Returns:
        set[int]: IDs of own-side and allied-side agents, optionally scoped."""
def side_ally_members_set (side):
    """Return the set of agent IDs from all sides allied with the given side.
    
    Args:
        side (str | int | Agent): Side key, side agent ID, or any space object
            whose side will be used.
    
    Returns:
        set[int]: IDs of all space objects on allied sides."""
def side_are_allies (side1, side2) -> bool:
    """Return whether two sides are allied.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides have a ``side_ally`` link."""
def side_are_enemies (side1, side2) -> bool:
    """Return whether two sides are hostile to each other.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides have a ``side_hostile`` link."""
def side_are_friendly (side1, side2) -> bool:
    """Return whether two sides are friendly — the SAME side, or ALLIED.
    
    The friendly counterpart of :func:`side_are_enemies`. Use this for "is this one
    of ours" checks: :func:`side_are_allies` alone is not enough because a side is
    not recorded as allied to itself, so a same-side ship would read as non-friendly.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides are the same or allied."""
def side_are_neutral (side1, side2) -> bool:
    """Return whether two sides are neutral toward each other.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides have a ``side_neutral`` link."""
def side_are_same_side (side1, side2) -> bool:
    """Return whether two references resolve to the same side.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if both resolve to the same side agent."""
def side_capture (ship, captor):
    """A surrendered ship JOINS its captor: move it onto the captor's side, so it is
    now friendly to the captor and hostile to the captor's enemies (by diplomacy), and
    clear the surrendered state.
    
    The ship keeps its race/clan role for identity and is marked with a ``captured``
    role (so ``take_surrendered_home``, which flies ``surrendered`` ships off and
    deletes them, leaves it alone — it is a prize now, not a fugitive). Give it a
    brain/objective afterwards if you want it to actively fight for you.
    
    Args:
        ship (Agent | int): The surrendered ship being taken as a prize.
        captor (Agent | int | str): The capturing ship/console (its side is used), or
            a side key directly."""
def side_create (key, name=None, desc=None, color=None, icon_index=None, races=None, allies=None, enemies=None):
    """Create and configure a faction SIDE from data - the Python port of the
    ``prefab_side_generic`` MAST prefab, so the same setup is callable from Python or a
    declarative loader without the mast prefab.
    
    Sets side_name / side_key / side_desc / side_races inventory, icon color + index, and
    applies ally/enemy diplomacy (plus the self-ally that ``side_ensure`` seeds). Idempotent:
    if the side already exists it is reconfigured in place (``side_ensure`` returns the
    existing id). ``races``/``allies``/``enemies`` accept a comma string or a list.
    
    Returns the side agent id (None if ``key`` is falsy)."""
def side_diplomacy_apply (overrides):
    """Re-apply saved per-pair diplomacy overrides via side_set_relations (call after the
    sides exist, e.g. on load)."""
def side_diplomacy_key (a, b):
    """Order-independent key for a side PAIR.
    
    Safe because overrides are re-applied via ``side_set_relations``, which writes both
    directions -- not because the engine treats a pair as unordered."""
def side_diplomacy_set (overrides, a, b, relation):
    """Record a per-pair diplomacy override in ``overrides`` (created if not a dict);
    returns the dict. Persist it to carry live relation changes across saves."""
def side_display_name (key):
    """Return the display name of a side.
    
    Args:
        key (str | int | Agent): Side key, agent ID, or agent.
    
    Returns:
        str: The side's display name, or ``None`` if not found."""
def side_enemy_members_set (side):
    """Return the set of agent IDs from all sides hostile to the given side.
    
    Args:
        side (str | int | Agent): Side key, side agent ID, or any space object
            whose side will be used.
    
    Returns:
        set[int]: IDs of all space objects on hostile sides."""
def side_ensure (key, name=None):
    """Ensure a side with ``key`` exists, creating a minimal one if missing, and
    return its side-agent ID.
    
    The programmatic (Python) counterpart of the ``prefab_side_generic`` MAST prefab
    — use it before spawning ships on a new faction side so diplomacy can resolve
    that side. Idempotent: returns the existing side's ID if already registered. The
    new side is allied to itself (matching ``prefab_side_generic``), so a same-side
    pair reads friendly via :func:`side_are_allies` as well.
    
    Args:
        key (str): The side key (e.g. ``"kralien"``).
        name (str, optional): Display name. Defaults to ``key``.
    
    Returns:
        int: The side agent's ID."""
def side_get_description (key_or_id) -> str:
    """Return the description text of a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
    
    Returns:
        str: The side description, or ``""`` if not set."""
def side_get_display_name (key_or_id) -> str:
    """Return the display name of a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
    
    Returns:
        str: The side's display name, or ``""`` if not set."""
def side_get_relations (side1, side2):
    """Return the current diplomatic relationship between two sides.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        sbs.DIPLOMACY: One of ``ALLIED``, ``HOSTILE``, ``NEUTRAL``, or
            ``UNKNOWN``."""
def side_get_side_color (key_or_id, default='#0F0') -> str:
    """Return the icon color assigned to a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        default (str, optional): Color to return if the side has no color set.
            Defaults to ``"#0F0"`` (green).
    
    Returns:
        str: The hex color code assigned to the side, or ``default``."""
def side_get_side_icon_index (key_or_id) -> int:
    """Return the icon index for a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
    
    Returns:
        int: The icon index, or ``-1`` if not found."""
def side_hostile_members (observer, scope_role=None):
    """Return the agent IDs on any side HOSTILE to ``observer``, optionally
    intersected with a combat-class role.
    
    The canonical "who may I fight" set: diplomacy decides allegiance (a side that
    is neutral/allied — e.g. one you have ceasefired — drops out), and the optional
    ``scope_role`` (such as ``"raider"``) scopes the result to combat ships. Because
    a role like ``raider`` is removed on surrender/defection, scoping by it also
    drops ships that have already struck their colours. Prefer this over a bare
    ``role("raider")`` anywhere a set is tested for "is there an enemy".
    
    Args:
        observer (str | int | Agent): Side key, side agent ID, or any object whose
            side is used as the point of view.
        scope_role (str, optional): A role to intersect the result with (combat-ship
            scope). Defaults to None (all hostile-side members).
    
    Returns:
        set[int]: IDs of hostile-side agents, optionally scoped to ``scope_role``."""
def side_hostile_ships (observer):
    """Space objects HOSTILE to ``observer`` that are still in the fight.
    
    The diplomacy-only answer to "who may I fight" — the replacement for scoping a
    hostile set by a faction tag such as ``role("raider")``. Allegiance comes from the
    side relations alone, so a ceasefired or defected side drops out the moment its
    diplomacy changes, with no tag to keep in sync; wrecks and surrendered ships are
    excluded because they are not combatants, not because of who they belong to.
    
    Includes hostile stations (they are on a hostile side like anything else). Intersect
    with a CLASS role when you want a narrower kind, e.g.
    ``side_hostile_ships(x) & role("station")`` or ``- role("station")``.
    
    Args:
        observer (str | int | Agent): Side key, side agent ID, or any object whose side
            is the point of view.
    
    Returns:
        set[int]: IDs of hostile, in-the-fight space objects."""
def side_is_color_used (color) -> bool:
    """Return whether any side is currently using a given icon color.
    
    Args:
        color (str): Hex color code to check for.
    
    Returns:
        bool: ``True`` if at least one side uses that color."""
def side_keys_set ():
    """Return the set of key strings for all registered sides.
    
    Returns:
        set[str]: Side key strings (e.g. ``"player"``, ``"enemy"``)."""
def side_members_set (side):
    """Return the set of agent IDs that belong to a given side.
    
    Prefer this over ``role(side)`` as it correctly excludes the side agent
    itself from the result.
    
    Args:
        side (str | int | Agent): Side key, side agent ID, side agent, or any
            space object whose side will be used.
    
    Returns:
        set[int]: IDs of all space objects on the specified side."""
def side_set_description (key_or_id, desc) -> None:
    """Set the description text for a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        desc (str): The new description text."""
def side_set_display_name (key_or_id, name) -> None:
    """Set the display name for a side and update all ships on that side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        name (str): The new display name."""
def side_set_hostile_to_players (faction_key, relation=None):
    """Make ``faction_key`` HOSTILE to every current player side (creating the
    faction side if needed).
    
    The programmatic generalisation of a mission's single ``side_set_relations``
    line: instead of lumping every enemy on one shared ``"raider"`` side, spawn a
    faction on its OWN side and call this, so hostility is expressed by diplomacy —
    which the migrated targeting / victory / quest consumers already honour, and
    which a runtime ceasefire can flip. Applies the relation once per distinct side
    among the current ``role("__player__")`` ships.
    
    Args:
        faction_key (str): The enemy faction's side key.
        relation (sbs.DIPLOMACY, optional): Defaults to ``HOSTILE``."""
def side_set_icon_color (key_or_id, color) -> None:
    """Set the icon color for a side, changing how its ships appear on the 2D map.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        color (str): Hex color code or named color (e.g. ``"#FF0000"`` or
            ``"red"``)."""
def side_set_object_side (id_or_obj, key) -> None:
    """Assign a side to one or more space objects.
    
    Updates both the ``side`` (key) and ``side_display`` (name) attributes on
    each object.
    
    Args:
        id_or_obj (int | Agent | list[int | Agent] | set[int | Agent]):
            The object(s) to update.
        key (str | int | Agent): The target side — a key string, side agent ID,
            or any object whose side will be used."""
def side_set_relations (side1, side2, relation):
    """Set the diplomatic relationship between two sides.
    
    Updates both the link-based relationship used by the scripting API and the
    engine's own side relationship table for 2D map rendering. Emits the
    ``side_relations_updated`` signal.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
        relation (sbs.DIPLOMACY): New relationship value. Use
            ``sbs.DIPLOMACY.ALLIED``, ``HOSTILE``, ``NEUTRAL``, or
            ``UNKNOWN``."""
def side_set_ship_allies_and_enemies (ship):
    """No-op placeholder — deprecated as of v1.3.0, to be removed in a future version.
    
    Args:
        ship (Agent | int): Unused."""
def side_set_side_icon_index (key_or_id, icon_index) -> None:
    """Set the icon index for a side, changing how its ships appear on the 2D map.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        icon_index (int): The icon index to use."""
def side_surrender (ship, combat_role=None):
    """Move a ship to the neutral ``surrendered`` side (creating it if needed) and
    mark it surrendered, recording its origin side for a later
    :func:`side_unsurrender`.
    
    Changing the SIDE (not merely stripping a combat role) makes the ship non-hostile
    by diplomacy itself, so every side/relation consumer treats it as out of the fight
    — not only the ones that scope by the combat role. The ``surrendered`` side is
    created with no hostile links, so it is neutral to everyone. The ship keeps its
    race/clan role, so its faction identity is preserved.
    
    Args:
        ship (Agent | int): The surrendering ship.
        combat_role (str, optional): Legacy compat only -- a combat-class role to drop
            as well, for a mission that still scopes its own queries by one. Defaults
            to ``None``: the side change alone is what takes the ship out of the fight,
            and the library's own consumers read diplomacy."""
def side_unsurrender (ship, combat_role=None):
    """Reverse :func:`side_surrender` — restore the ship's origin side and re-arm it
    (drop ``surrendered``, restore the origin side, clear ``surrender_flag``).
    
    Args:
        ship (Agent | int): The ship to re-arm.
        combat_role (str, optional): Legacy compat only -- a combat-class role to
            restore, matching whatever was passed to :func:`side_surrender`. Defaults
            to ``None``; restoring the side is what puts the ship back in the fight."""
def sides_set ():
    """Return the set of IDs for all registered sides (agents with the ``__side__`` role).
    
    Returns:
        set[int]: IDs of all side agents."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
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
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_side_id (key_or_id_or_object, warn=True):
    """Resolve any side reference to the side agent's ID.
    
    Accepts a side key string, a side agent ID, a side agent object, or any
    space object (in which case its side property is used).
    
    A leading ``#`` on a side key is a display-hide marker only (it tells the
    engine not to draw the side name); it is not part of the side identity, so
    ``"#raider"`` resolves to the ``"raider"`` side. An empty or all-``#`` key
    means the object has NO side (asteroids, cambots, hidden objects) and
    resolves to ``None`` silently — that is a legitimate state, not a miss.
    
    Args:
        key_or_id_or_object (str | int | Agent): Side key, side agent ID, side
            agent, or a space object whose side should be resolved.
        warn (bool): Warn (once per distinct key) when a genuinely-named side
            can't be resolved. Pass ``False`` for existence probes (e.g. a
            create-if-missing check) where a miss is expected, not an error.
    
    Returns:
        int | None: The side agent ID, or ``None`` if not found."""
def to_side_object (key_or_id):
    """Resolve any side reference to the side agent object.
    
    Args:
        key_or_id (str | int | Agent): Side key, side agent ID, or any space
            object whose side will be resolved.
    
    Returns:
        Agent | None: The side agent, or ``None`` if not found."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).
    
    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The space-object agent, or ``None``."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
