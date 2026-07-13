from .signal import signal_emit
from ..helpers import FrameContext
from .roles import role, has_role
from .inventory import get_inventory_value, set_inventory_value
from .query import to_object, to_space_object, to_id, set_data_set_value, get_data_set_value, to_object_list
from .links import link, linked_to, has_link, has_link_to, unlink

def sides_set():
    """Return the set of IDs for all registered sides (agents with the ``__side__`` role).

    Returns:
        set[int]: IDs of all side agents.
    """
    sides = role("__side__")
    return sides

def side_keys_set():
    """Return the set of key strings for all registered sides.

    Returns:
        set[str]: Side key strings (e.g. ``"player"``, ``"enemy"``).
    """
    sides = role("__side__")
    side_keys = set()
    for s in sides:
        key = get_inventory_value(s, "side_key", None)
        if key is not None:
            side_keys.add(key)
    return side_keys

def side_members_set(side):
    """Return the set of agent IDs that belong to a given side.

    Prefer this over ``role(side)`` as it correctly excludes the side agent
    itself from the result.

    Args:
        side (str | int | Agent): Side key, side agent ID, side agent, or any
            space object whose side will be used.

    Returns:
        set[int]: IDs of all space objects on the specified side.
    """
    # print(f"Getting set for side: {side}")
    id = to_side_id(side)
    key = get_inventory_value(id, "side_key")
    if key is None: # Should never happen, but just in case
        return set()
    objs = role(key) - role("__side__") # remove the actual side, since it's a MastAsyncTask instead of a Ship
    # If the role for the side wasn't properly updated, remove the object?
    # objs = {x for x in objs if to_object(x).side == side}
    return objs

def side_ally_members_set(side):
    """Return the set of agent IDs from all sides allied with the given side.

    Args:
        side (str | int | Agent): Side key, side agent ID, or any space object
            whose side will be used.

    Returns:
        set[int]: IDs of all space objects on allied sides.
    """
    id = to_side_id(side)
    allies = linked_to(id, "side_ally")
    
    # allies = get_inventory_value(id, "side_allies", set())
    ally_members = set()
    if allies is not None:
        for a in allies:
            ally_members = ally_members | side_members_set(a)
    return ally_members

def side_enemy_members_set(side):
    """Return the set of agent IDs from all sides hostile to the given side.

    Args:
        side (str | int | Agent): Side key, side agent ID, or any space object
            whose side will be used.

    Returns:
        set[int]: IDs of all space objects on hostile sides.
    """
    id = to_side_id(side)
    enemies = linked_to(id, "side_hostile")
    enemy_members = set()
    if enemies is not None:
        for a in enemies:
            enemy_members = enemy_members | side_members_set(a)
    return enemy_members

def to_side_id(key_or_id_or_object):
    """Resolve any side reference to the side agent's ID.

    Accepts a side key string, a side agent ID, a side agent object, or any
    space object (in which case its side property is used).

    Args:
        key_or_id_or_object (str | int | Agent): Side key, side agent ID, side
            agent, or a space object whose side should be resolved.

    Returns:
        int | None: The side agent ID, or ``None`` if not found.
    """
    # Check if it's a key
    if isinstance(key_or_id_or_object, str):
        # print(f"Side id: {key_or_id_or_object}")
        key_or_id_or_object = key_or_id_or_object.strip().lower() # Get rid of leading/trailing whitespaces
        for s in sides_set():
            if get_inventory_value(s, "side_key").strip().lower() == key_or_id_or_object:
                return s
            if get_inventory_value(s, "side_name").strip().lower() == key_or_id_or_object:
                return s
        if not "monster" in key_or_id_or_object:
            print(f"Side not found: {key_or_id_or_object}")
        return None # If it's not in sides_set() then it's not a valid side key
    id = to_id(key_or_id_or_object) # Will return key_or_id_or_object if it's not an object
    if isinstance(id, int):
        if has_role(id, "__side__"):
            return id # If it's a side prefab, we just return the ID
        # print(f"Trying again for id: {id}")
        # if it's not a side prefab, use the side of the object as the key and continue
        obj = to_space_object(id)
        if obj is not None:
            side = obj.side
            # to_side_id() should be able to return the right side based on id or display text
            return to_side_id(side)
        
    return None

def to_side_object(key_or_id):
    """Resolve any side reference to the side agent object.

    Args:
        key_or_id (str | int | Agent): Side key, side agent ID, or any space
            object whose side will be resolved.

    Returns:
        Agent | None: The side agent, or ``None`` if not found.
    """
    s = to_side_id(key_or_id)
    return to_object(s)

def side_display_name(key):
    """Return the display name of a side.

    Args:
        key (str | int | Agent): Side key, agent ID, or agent.

    Returns:
        str: The side's display name, or ``None`` if not found.
    """
    id = to_side_id(key)
    name = get_inventory_value(id, "side_name")
    return name

def side_set_object_side(id_or_obj, key)->None:
    """Assign a side to one or more space objects.

    Updates both the ``side`` (key) and ``side_display`` (name) attributes on
    each object.

    Args:
        id_or_obj (int | Agent | list[int | Agent] | set[int | Agent]):
            The object(s) to update.
        key (str | int | Agent): The target side — a key string, side agent ID,
            or any object whose side will be used.
    """
    id = to_side_id(key)
    if id is None:
        print(f"WARNING: Side not found: {key}.")
        return
    key = get_inventory_value(id, "side_key")
    display = get_inventory_value(id, "side_name")
    obj_list = to_object_list(id_or_obj)
    for obj in obj_list:
        # Update side and GUI side name
        obj.side = key
        obj.side_display = display
    

#TODO: I tried using the @deprecated annotation (so the extension could easily determine and show a warning), but `typing_extensions` wasn't found, and `warnings` needs python v3.13
def side_set_ship_allies_and_enemies(ship):
    """No-op placeholder — deprecated as of v1.3.0, to be removed in a future version.

    Args:
        ship (Agent | int): Unused.
    """
    pass

def side_set_relations(side1, side2, relation):
    """Set the diplomatic relationship between two sides.

    Updates both the link-based relationship used by the scripting API and the
    engine's own side relationship table for 2D map rendering. Emits the
    ``side_relations_updated`` signal.

    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
        relation (sbs.DIPLOMACY): New relationship value. Use
            ``sbs.DIPLOMACY.ALLIED``, ``HOSTILE``, ``NEUTRAL``, or
            ``UNKNOWN``.
    """
    
    sbs = FrameContext.context.sbs
    sim = FrameContext.context.sim

    if int(relation) < 0: # Backwards-compatibility (crash prevention) of old version that used -1 for hostile
        print(f"INVALID RELATION VALUE: {relation}. Using {sbs.DIPLOMACY.HOSTILE} instead.")
        # TODO: This could be a separate function that always prints the current stack?
        relation = sbs.DIPLOMACY.HOSTILE
    if int(relation) > int(sbs.DIPLOMACY.MAX): # Possibly also could prevent crashes.
        print(f"INVALID RELATION VALUE: {relation}. Using {sbs.DIPLOMACY.UNKNOWN} instead.")
        relation = sbs.DIPLOMACY.UNKNOWN

    o1 = to_side_id(side1)
    o2 = to_side_id(side2)

    if o1 is None or o2 is None:
        # If a side isn't initialized yet, then we just return.
        # print(f"side is None in side_set_relations()")
        # print(f"One or both sides are not valid")
        return
    
    old_relation = side_get_relations(o1, o2)
    
    # Clear the existing relationship links (if they exist), since we'll be replacing them with the new relationship.
    unlink(o1, "side_ally", o2)
    unlink(o2, "side_ally", o1)

    unlink(o1, "side_hostile", o2)
    unlink(o2, "side_hostile", o1)

    unlink(o1, "side_neutral", o2)
    unlink(o2, "side_neutral", o1)

    unlink(o1, "side_unknown", o2)
    unlink(o2, "side_unknown", o1)
    match relation:
        case sbs.DIPLOMACY.ALLIED:
            link(o1, "side_ally", o2)
            link(o2, "side_ally", o1) 
        case sbs.DIPLOMACY.HOSTILE:
            link(o1, "side_hostile", o2)
            link(o2, "side_hostile", o1)
        case sbs.DIPLOMACY.NEUTRAL:
            link(o1, "side_neutral", o2)
            link(o2, "side_neutral", o1) 
        case sbs.DIPLOMACY.UNKNOWN: # Is this strictly necessary? Probably not???
            link(o1, "side_unknown", o2)
            link(o2, "side_unknown", o1)
        case _:
            # While we could have left DIPLOMACY.UNKNOWN as its own thing,
            # for now we can safely assume that any relation value other than ALLIED, HOSTILE, or NEUTRAL is meant to be UNKNOWN, and we can just link it with "side_unknown".
            link(o1, "side_unknown", o2)
            link(o2, "side_unknown", o1)

    # Get the side keys, since the engine uses the key and doesn't even know about the side object.
    o1_key = get_inventory_value(o1, "side_key")
    o2_key = get_inventory_value(o2, "side_key")

    # Update the engine relationship for 2d map graphics
    sim.set_side_relationship(o1_key, o2_key, relation)
    signal_emit("side_relations_updated", {"side1": o1, "side2": o2, "relation": relation, "old_relation": old_relation})

def side_get_relations(side1, side2):
    """Return the current diplomatic relationship between two sides.

    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.

    Returns:
        sbs.DIPLOMACY: One of ``ALLIED``, ``HOSTILE``, ``NEUTRAL``, or
            ``UNKNOWN``.
    """
    sbs = FrameContext.context.sbs

    if side_are_allies(side1,side2):
        return sbs.DIPLOMACY.ALLIED
    if side_are_enemies(side1,side2):
        return sbs.DIPLOMACY.HOSTILE
    if side_are_neutral(side1, side2):
        return sbs.DIPLOMACY.NEUTRAL
    else:
        return sbs.DIPLOMACY.UNKNOWN

def side_are_same_side(side1, side2)->bool:
    """Return whether two references resolve to the same side.

    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.

    Returns:
        bool: ``True`` if both resolve to the same side agent.
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return o1==o2
    
def side_are_allies(side1, side2)->bool:
    """Return whether two sides are allied.

    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.

    Returns:
        bool: ``True`` if the sides have a ``side_ally`` link.
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return has_link_to(o1, "side_ally", o2)


def side_are_enemies(side1, side2)->bool:
    """Return whether two sides are hostile to each other.

    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.

    Returns:
        bool: ``True`` if the sides have a ``side_hostile`` link.
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return has_link_to(o1, "side_hostile", o2)
    
def side_are_neutral(side1, side2)->bool:
    """Return whether two sides are neutral toward each other.

    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.

    Returns:
        bool: ``True`` if the sides have a ``side_neutral`` link.
    """
    o1 = to_side_id(side1)
    o2 = to_side_id(side2)
    return has_link_to(o1, "side_neutral", o2)


def side_are_friendly(side1, side2)->bool:
    """Return whether two sides are friendly — the SAME side, or ALLIED.

    The friendly counterpart of :func:`side_are_enemies`. Use this for "is this one
    of ours" checks: :func:`side_are_allies` alone is not enough because a side is
    not recorded as allied to itself, so a same-side ship would read as non-friendly.

    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.

    Returns:
        bool: ``True`` if the sides are the same or allied.
    """
    return side_are_same_side(side1, side2) or side_are_allies(side1, side2)


def is_allied_to_players(target, scope_role=None)->bool:
    """Return whether ``target`` is friendly to some player side (same side or
    allied), optionally requiring a class role. The friend analog of
    :func:`is_hostile_to_players`.

    Args:
        target (str | int | Agent): The candidate to test.
        scope_role (str, optional): A role the target must hold. Defaults to None.

    Returns:
        bool: ``True`` if ``target`` is friendly to any player side.
    """
    if scope_role is not None and not has_role(target, scope_role):
        return False
    for p in to_object_list(role("__player__")):
        ps = getattr(p, "side", None)
        if ps and side_are_friendly(ps, target):
            return True
    return False


def side_hostile_members(observer, scope_role=None):
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
        set[int]: IDs of hostile-side agents, optionally scoped to ``scope_role``.
    """
    foes = side_enemy_members_set(observer)
    if scope_role:
        foes = foes & role(scope_role)
    return foes


def is_hostile_combatant(observer, target, scope_role="raider")->bool:
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
        bool: ``True`` if ``target`` is a hostile combatant to ``observer``.
    """
    if scope_role is not None and not has_role(target, scope_role):
        return False
    return side_are_enemies(observer, target)


def players_hostile_members(scope_role=None):
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
        set[int]: IDs hostile to some player side, optionally scoped to ``scope_role``.
    """
    foes = set()
    seen = set()
    for p in to_object_list(role("__player__")):
        s = getattr(p, "side", None)
        if s and s not in seen:
            seen.add(s)
            foes |= side_enemy_members_set(s)
    if scope_role:
        foes = foes & role(scope_role)
    return foes


def is_hostile_to_players(target, scope_role="raider")->bool:
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
        bool: ``True`` if ``target`` is a hostile combatant to any player side.
    """
    if scope_role is not None and not has_role(target, scope_role):
        return False
    for p in to_object_list(role("__player__")):
        s = getattr(p, "side", None)
        if s and side_are_enemies(s, target):
            return True
    return False


def side_allied_members(observer, scope_role=None):
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
        set[int]: IDs of own-side and allied-side agents, optionally scoped.
    """
    friends = side_members_set(observer) | side_ally_members_set(observer)
    if scope_role:
        friends = friends & role(scope_role)
    return friends


def players_allied_members(scope_role=None):
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
        set[int]: IDs friendly to the players, optionally scoped to ``scope_role``.
    """
    out = set()
    seen = set()
    for p in to_object_list(role("__player__")):
        s = getattr(p, "side", None)
        if s and s not in seen:
            seen.add(s)
            out |= side_members_set(s)
            out |= side_ally_members_set(s)
    if scope_role:
        out = out & role(scope_role)
    return out


def side_ensure(key, name=None):
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
        int: The side agent's ID.
    """
    existing = to_side_id(key)
    if existing is not None:
        return existing
    from ..agent import Agent, get_story_id
    a = Agent()
    a.id = get_story_id()
    a.add()
    a.add_role("__side__")
    a.set_inventory_value("side_key", key)
    a.set_inventory_value("side_name", name if name is not None else key)
    sbs = FrameContext.context.sbs
    if sbs is not None:
        side_set_relations(key, key, sbs.DIPLOMACY.ALLIED)
    return a.id


def side_set_hostile_to_players(faction_key, relation=None):
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
        relation (sbs.DIPLOMACY, optional): Defaults to ``HOSTILE``.
    """
    sbs = FrameContext.context.sbs
    if relation is None:
        relation = sbs.DIPLOMACY.HOSTILE
    side_ensure(faction_key)
    seen = set()
    for p in to_object_list(role("__player__")):
        ps = getattr(p, "side", None)
        if ps and ps not in seen:
            seen.add(ps)
            side_set_relations(ps, faction_key, relation)


def side_set_side_icon_index(key_or_id, icon_index)->None:
    """Set the icon index for a side, changing how its ships appear on the 2D map.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        icon_index (int): The icon index to use.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        key = get_inventory_value(id, "side_key")
        set_inventory_value(id, "side_icon_index", icon_index)
        FrameContext.context.sim.set_side_icon_index(key, icon_index)

def side_get_side_icon_index(key_or_id)->int:
    """Return the icon index for a side.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.

    Returns:
        int: The icon index, or ``-1`` if not found.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        return get_inventory_value(id, "side_icon_index", -1)
    return -1


def side_set_icon_color(key_or_id, color)->None:
    """Set the icon color for a side, changing how its ships appear on the 2D map.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        color (str): Hex color code or named color (e.g. ``"#FF0000"`` or
            ``"red"``).
    """
    # TODO: Is transparency supported in the color code? I would think not but should check.
    id = to_side_id(key_or_id)
    if id is not None:
        key = get_inventory_value(id, "side_key")
        set_inventory_value(id, "side_color", color)
        FrameContext.context.sim.set_side_icon_color(key, color)

def side_get_side_color(key_or_id, default="#0F0")->str:
    """Return the icon color assigned to a side.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        default (str, optional): Color to return if the side has no color set.
            Defaults to ``"#0F0"`` (green).

    Returns:
        str: The hex color code assigned to the side, or ``default``.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        return get_inventory_value(id, "side_color", default)
    return default
    
def side_is_color_used(color)->bool:
    """Return whether any side is currently using a given icon color.

    Args:
        color (str): Hex color code to check for.

    Returns:
        bool: ``True`` if at least one side uses that color.
    """
    for side in sides_set():
        if side_get_side_color(side, color):
            return True
    return False

def side_get_description(key_or_id)->str:
    """Return the description text of a side.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.

    Returns:
        str: The side description, or ``""`` if not set.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        return get_inventory_value(id, "side_desc","")
    return ""

def side_set_description(key_or_id, desc)->None:
    """Set the description text for a side.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        desc (str): The new description text.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        set_inventory_value(id, "side_desc", desc)

def side_get_display_name(key_or_id)->str:
    """Return the display name of a side.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.

    Returns:
        str: The side's display name, or ``""`` if not set.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        return get_inventory_value(id, "side_name","")
    return ""

def side_set_display_name(key_or_id, name)->None:
    """Set the display name for a side and update all ships on that side.

    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        name (str): The new display name.
    """
    id = to_side_id(key_or_id)
    if id is not None:
        set_inventory_value(key_or_id, "side_name", name)
        ships = side_members_set(id)
        side_set_object_side(ships, id)

