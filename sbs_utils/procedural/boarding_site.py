"""A boarding party's BODIES: where each person is standing, and who is walking them.

`boarding.py` owns the party as a cast - who is down there, what the scene is saying,
whose menu a choice belongs to. It has no idea where anybody IS. This module is the other
half: the interior they are walking, the figure each person is, and the one rule that
makes several consoles work at once.

THE RULE, and it is the whole module: **the figure a console is driving lives on the
CLIENT.** Not on the site, not in the engine's grid selection. Everything else follows.

The prototype this replaces kept the driven figure on the SITE, so a site had exactly one
driven figure and a second console clicking only fought the first. That was not a
shortcut, it was forced: the board read the engine's ``grid_selected_UID``, and that value
is ONE PER SHIP (``consoledispatcher.do_select`` writes it on the ship's blob). Two
consoles looking at one interior are last-writer-wins, globally, and no server-side write
fixes it - ``query.inc_disable_client_selection`` documents that the engine owns the
interior view's highlight and a write-back does not stick.

So this module never reads a selection at all. A console owns its figure, a click carries
a CELL (``EVENT.source_point``), and the two never meet. That removes the constraint
rather than working around it.

A person is TWO agents pointing at each other, the shape `boarding.py` already uses:

* a **lifeform** - identity: name, face, the roles a scene's guards read.
* a **grid object** - the body on the floor, at a cell, walkable by the engine.

**The lifeform deliberately has NO host.** ``lifeform_spawn(..., host=)`` exists, and
hosting a boarder on the ship they boarded reads as correct - they ARE aboard it - but
`lifeform.py` grants ``ultra_beam`` only to a lifeform with no space-object host, and that
role is how the ship's internal comms lists the party so the bridge can talk to them.
Hosting them silently cuts that channel. Identity stays hostless; the GRID OBJECT is where
they are.
"""
from ..agent import Agent
from .inventory import get_inventory_value, set_inventory_value
from .links import link, linked_to, unlink
from .query import to_id, to_object
from .roles import add_role, has_role, role

# The role a boarding figure wears, so a route can tell one from a damcon or a room.
FIGURE_ROLE = "boarding_figure"

# The role an interior being boarded wears. LegendaryMissions' Engineering grid routes gate
# themselves OFF this (grid_comms/__init__.mast), so the word is shared across repos and
# must not be changed on one side alone.
SITE_ROLE = "boarding_site"

# On the CLIENT. The whole design is these two keys not being on the site.
KEY_FIGURE = "BOARDING_FIGURE"     # the grid object this console drives
KEY_HOST = "BOARDING_HOST"         # the interior it is walking

# How fast a figure walks a cell. The engine advances `percent` by this each 30Hz tick, so
# 0.12 is about a third of a second a cell - brisk enough to feel responsive, slow enough
# to read. The library default of 0.01 is ~3.3s a cell, which is a damcon plodding.
WALK_SPEED = 0.12

# Consoles that have ever been handed a figure, so a reset can let go of all of them
# without walking every agent. On SHARED rather than at module level, so it is cleared and
# audited by the same machinery as everything else.
_DRIVERS_KEY = "__BOARDING_DRIVERS__"


def boarding_site_build(target, layout=None):
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
        The target, or None if it does not exist.
    """
    from .internal_damage import grid_rebuild_grid_objects
    so = to_object(target)
    if so is None:
        return None
    if layout:
        set_inventory_value(so.id, "grid_layout", layout)
    add_role(so, SITE_ROLE)
    grid_rebuild_grid_objects(so, layout=layout)
    return so


def boarding_site_is(target):
    """Whether this object is currently being boarded."""
    return has_role(to_id(target), SITE_ROLE)


def boarding_figure_spawn(target, lifeform, x, y, icon_index=100, color="#4cf"):
    """Put one character on the interior, as a body linked to its identity.

    Args:
        target: the interior they are standing on.
        lifeform: who they are.
        x (int): the cell x to stand on.
        y (int): the cell y to stand on.
        icon_index (int, optional): the glyph.
        color (str, optional): its color.

    Returns:
        The grid object, or None if the site or the person does not exist.
    """
    from .spawn import grid_spawn
    site = to_object(target)
    who = to_object(lifeform)
    if site is None or who is None:
        return None
    fig = grid_spawn(site.id, who.name, "boarding", x, y, icon_index, color, FIGURE_ROLE)
    if fig is None:
        return None
    # Both ways, so either half answers for the other. A screen holds the lifeform and
    # wants the cell; a map click holds the figure and wants the name.
    link(who.id, "figure", fig.id)
    link(fig.id, "lifeform", who.id)
    return fig


def boarding_figure_of(lifeform):
    """The body this character is walking around in, or None."""
    return next(iter(linked_to(to_id(lifeform), "figure")), None)


def boarding_lifeform_of(figure):
    """Who this body is, or None."""
    return next(iter(linked_to(to_id(figure), "lifeform")), None)


def boarding_take(client_id, figure, host):
    """Give this console a figure to drive, on this interior.

    Stored on the CLIENT. Read the module docstring before moving it anywhere else - the
    site is exactly where it must not go.
    """
    set_inventory_value(client_id, KEY_FIGURE, to_id(figure))
    set_inventory_value(client_id, KEY_HOST, to_id(host))
    seen = set(Agent.SHARED.get_inventory_value(_DRIVERS_KEY, set()) or set())
    seen.add(to_id(client_id))
    Agent.SHARED.set_inventory_value(_DRIVERS_KEY, seen)


def boarding_release(client_id):
    """This console drives nobody."""
    set_inventory_value(client_id, KEY_FIGURE, None)
    set_inventory_value(client_id, KEY_HOST, None)


def boarding_my_figure(client_id):
    """The grid object THIS console drives, or None.

    Takes the console explicitly and always will. A ``//point/grid`` route runs on the
    SERVER task, so a convenience fallback to ``FrameContext.page`` would answer for the
    server on every click - silently, and for every console at once.
    """
    return get_inventory_value(client_id, KEY_FIGURE, None)


def boarding_my_host(client_id):
    """The interior THIS console is walking, or None."""
    return get_inventory_value(client_id, KEY_HOST, None)


def boarding_walk(client_id, x, y, speed=WALK_SPEED):
    """Walk this console's own figure to a cell. The engine paths it.

    Returns:
        bool: True if somebody was sent. False is ordinary - a console that is not
        boarded, or has no body yet, clicking the map.
    """
    from .grid import grid_target_pos, grid_object_valid
    fig = boarding_my_figure(client_id)
    if not fig or not grid_object_valid(fig):
        return False
    grid_target_pos(fig, x, y, speed)
    return True


def boarding_click(client_id, parent_id, x, y):
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
        bool: whether this console walked somebody.
    """
    host = boarding_my_host(client_id)
    if not host or to_id(parent_id) != to_id(host):
        return False
    return boarding_walk(client_id, int(x), int(y))


def boarding_where(client_id):
    """The cell this console's figure is standing on as ``(x, y)``, or None."""
    from .grid import grid_pos_data
    fig = boarding_my_figure(client_id)
    if not fig:
        return None
    at = grid_pos_data(fig)
    if at is None or at[0] is None:
        return None
    return int(at[0]), int(at[1])


def boarding_room_at(target, x, y, roles=None):
    """The room object standing at this cell, or None.

    What a panel prints as "where you are". Asks the interior rather than the selection, so
    it costs nothing and cannot disagree with anybody else's console.
    """
    from .grid import grid_objects_at
    from .roles import any_role
    here = grid_objects_at(to_id(target), int(x), int(y))
    if not here:
        return None
    here = here - role(FIGURE_ROLE)
    if roles:
        here = here & any_role(roles)
    return to_object(next(iter(here), None))


def boarding_figures(target=None):
    """Every boarding figure, or only the ones on this interior."""
    figs = role(FIGURE_ROLE)
    if target is None:
        return figs
    from .grid import grid_objects
    return figs & grid_objects(to_id(target))


def boarding_site_clear(target=None):
    """Take the party's bodies off an interior - or off every interior.

    Called on a mission reset, and when a site is finished with. The LIFEFORMS belong to
    `boarding.py` and are left alone; this owns only the bodies.
    """
    from .grid import grid_delete_object, grid_objects
    from .roles import remove_role
    if target is not None:
        sites = [to_object(target)]
    else:
        sites = [to_object(s) for s in set(role(SITE_ROLE))]
    for site in sites:
        if site is None:
            continue
        for fig in list(grid_objects(site.id) & role(FIGURE_ROLE)):
            who = boarding_lifeform_of(fig)
            if who:
                # Both directions. The figure agent is about to go, but the LIFEFORM
                # survives - it is `boarding.py`'s - and a stale "figure" link on it would
                # hand the next screen a dead grid object id.
                unlink(who, "figure", fig)
                unlink(fig, "lifeform", who)
            grid_delete_object(site.id, fig)
        remove_role(site, SITE_ROLE)
    if target is None:
        for cid in list(Agent.SHARED.get_inventory_value(_DRIVERS_KEY, set()) or set()):
            boarding_release(cid)
        Agent.SHARED.set_inventory_value(_DRIVERS_KEY, set())


def boarding_site_count():
    """Reset-ledger probe: interiors still marked as being boarded."""
    return len(role(SITE_ROLE))


def boarding_figure_count():
    """Reset-ledger probe: bodies still standing on one."""
    return len(role(FIGURE_ROLE))
