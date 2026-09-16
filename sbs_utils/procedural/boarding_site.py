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
from ..helpers import FrameContext
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


def boarding_entry_cell(target, roles="access"):
    """Where a party materialises on this interior, as ``(x, y)``.

    The AIRLOCK if the floor plan drew one - a room carrying `access` - because that is
    where an author means people to come aboard, and it puts the whole party in one place
    so they arrive together rather than scattered.

    Falls back to the interior's own centre cell, then to (0, 0). A fallback is not a
    failure worth refusing over: a plan with no airlock is a plan the author simply did
    not mark, and a party standing in the middle of it can still walk.
    """
    from .grid import grid_objects, grid_pos_data
    from .roles import any_role
    site = to_object(target)
    if site is None:
        return 0, 0
    doors = grid_objects(site.id) & any_role(roles)
    for node in sorted(doors):
        at = grid_pos_data(node)
        if at is not None and at[0] is not None:
            return int(at[0]), int(at[1])
    hm = FrameContext.context.sbs.get_hull_map(site.id)
    if hm is not None and hm.w and hm.h:
        cx, cy = hm.w // 2, hm.h // 2
        if hm.is_grid_point_open(cx, cy):
            return cx, cy
        for y in range(hm.h):
            for x in range(hm.w):
                if hm.is_grid_point_open(x, y):
                    return x, y
    return 0, 0


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
        # The room watcher too. A tick task that outlives its mission is how a soak
        # reports brains still ticking on run 2, and a stale occupancy table would make
        # the next mission's first room silently refuse to fire.
        boarding_rooms_unwatch()
    else:
        # One site cleared, the rest still live: forget only ITS rooms, or they stay
        # "occupied" forever and can never wake again.
        gone = "%s:" % to_id(target)
        _set_occupied({k: c for k, c in _occupied().items() if not k.startswith(gone)})


def boarding_site_count():
    """Reset-ledger probe: interiors still marked as being boarded."""
    return len(role(SITE_ROLE))


def boarding_figure_count():
    """Reset-ledger probe: bodies still standing on one."""
    return len(role(FIGURE_ROLE))


# --- rooms that notice you --------------------------------------------------------------
#
# Walking is not a game until arriving somewhere MEANS something. This is the join between
# the two halves: `boarding_site.py` knows where everybody is standing, `boarding.py` knows
# what a scene is, and until now nothing connected them - a party could walk into the lab
# and the lab did not notice.
#
# THE ROOM WAKES, NOT THE PERSON. A room fires once when the party first enters it and does
# not fire again until the last of them has left. That rule is not a preference; the probe
# paid for it. Three characters walked into one airlock, a per-PERSON trigger fired three
# times, and the scene restarted twice - re-rolling its random line in front of everybody.
# Regrouping is a normal thing for a party to do, and it must be silent.
#
# The mission decides what entering MEANS. The library emits and says nothing about scenes,
# because "arriving starts the conversation" is one mission's answer and "arriving offers
# it" is another's.

# {"<site id>:<room name>": the client whose figure woke it}
#
# KEYED BY NAME, NOT BY GRID OBJECT, and this matters more than it looks. A floor plan
# draws a room as one grid node PER CELL - a 3x3 lab is nine objects all called
# "site-lab" - so keying on the node would fire nine arrivals for one room and then
# nine departures as somebody crossed it. The authored NAME is what a mission means by
# "the lab", so that is the identity. The site is in the key because two stations can
# both have a "cargo bay".
_OCCUPIED_KEY = "__BOARDING_OCCUPIED__"

# Which grid-object roles count as somewhere you can BE. A floor plan's rooms carry these
# (see grid_rooms.py); corridors, markers and the EPad do not, so walking a hallway is
# travel rather than a dozen arrivals.
ROOM_ROLES = "room, access, science, engine, cabin, computer, bay, cargo, medical"

_WATCH_KEY = "__BOARDING_ROOM_WATCH__"


def _occupied():
    return Agent.SHARED.get_inventory_value(_OCCUPIED_KEY, {}) or {}


def _set_occupied(table):
    Agent.SHARED.set_inventory_value(_OCCUPIED_KEY, table)


def boarding_rooms_watch(seconds=0.4, roles=None):
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
        The tick task, so a mission can hold it. Idempotent - asking twice watches once.
    """
    from ..tickdispatcher import TickDispatcher
    if Agent.SHARED.get_inventory_value(_WATCH_KEY, None):
        return Agent.SHARED.get_inventory_value(_WATCH_KEY, None)
    if roles:
        Agent.SHARED.set_inventory_value("__BOARDING_ROOM_ROLES__", roles)
    task = TickDispatcher.do_interval(boarding_rooms_tick, seconds)
    Agent.SHARED.set_inventory_value(_WATCH_KEY, task)
    return task


def boarding_rooms_unwatch():
    """Stop noticing. Rooms are forgotten, so a later watch starts from a clean sheet."""
    task = Agent.SHARED.get_inventory_value(_WATCH_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:
            # A task the dispatcher has already dropped is not an error - the mission
            # ended, or a reset took it. There is nothing to stop and nothing to say.
            pass
    Agent.SHARED.set_inventory_value(_WATCH_KEY, None)
    _set_occupied({})


def boarding_room_of(figure):
    """The room node this body is standing on, or None if it is in a corridor.

    One NODE. A room is drawn per cell, so this is whichever cell of the lab they are on
    - use :func:`boarding_room_name_of` for the room a mission means.
    """
    from .grid import grid_pos_data
    from .roles import any_role
    from .grid import grid_objects_at
    fig_id = to_id(figure)
    at = grid_pos_data(fig_id)
    if at is None or at[0] is None:
        return None
    for site in set(role(SITE_ROLE)):
        here = grid_objects_at(site, int(at[0]), int(at[1]))
        if not here or fig_id not in here:
            continue
        roles = (Agent.SHARED.get_inventory_value("__BOARDING_ROOM_ROLES__", None)
                 or ROOM_ROLES)
        rooms = here & any_role(roles)
        return next(iter(rooms), None)
    return None


def boarding_room_name_of(figure):
    """``(site id, room name, node id)`` for where this body is, or None in a corridor.

    The NAME is the identity a mission cares about: a lab is one room however many cells
    it is drawn across.
    """
    node = boarding_room_of(figure)
    if node is None:
        return None
    so = to_object(node)
    if so is None:
        return None
    return _site_of_room(node), boarding_room_name(so.name), to_id(node)


def boarding_room_name(node_name):
    """The authored room name from a grid node's name.

    The interior builder names every node ``"<room>:<x>,<y>"``
    (``internal_damage.py:208``), so a lab three cells across is three objects called
    ``site-lab:3,2``, ``site-lab:4,2``, ``site-lab:5,2``. The part before the colon is
    what the floor plan's legend called it, and that is the room a mission means - so it
    is the identity the entry trigger keys on. Without this, walking across one lab
    reports arriving in three different rooms.
    """
    name = str(node_name or "")
    return name.split(":", 1)[0]


def boarding_rooms_tick(t=None):
    """One look at where everybody is. Registered by :func:`boarding_rooms_watch`."""
    from .signal import signal_emit
    from .grid import grid_object_valid
    occupied = dict(_occupied())
    # Who is in which room THIS instant, first arrival winning it.
    now = {}
    for fig in list(role(FIGURE_ROLE)):
        if not grid_object_valid(fig):
            continue
        where = boarding_room_name_of(fig)
        if where is None:
            continue                      # a corridor is travel, not arrival
        site, name, node = where
        now.setdefault("%s:%s" % (site, name), (fig, site, name, node))

    for key, (fig, site, name, node) in now.items():
        if key in occupied:
            continue                      # somebody was already here - stay quiet
        cid = boarding_client_of_figure(fig)
        occupied[key] = cid
        signal_emit("boarding_entered", {
            "BOARDING_ROOM_NAME": name,
            "BOARDING_ROOM": node,
            "BOARDING_SITE": site,
            "BOARDING_CLIENT": cid,
            "BOARDING_WHO": boarding_lifeform_of(fig),
            "BOARDING_FIGURE": to_id(fig),
        })

    for key in list(occupied):
        if key in now:
            continue                      # still somebody in it
        del occupied[key]
        site, _, name = key.partition(":")
        signal_emit("boarding_left", {
            "BOARDING_ROOM_NAME": name,
            "BOARDING_SITE": int(site) if site.isdigit() else None,
        })

    _set_occupied(occupied)


def _site_of_room(room_id):
    """Which interior a room belongs to. Rooms are per-site, so this is a lookup."""
    from .grid import grid_objects
    for site in set(role(SITE_ROLE)):
        if to_id(room_id) in grid_objects(site):
            return site
    return None


def boarding_client_of_figure(figure):
    """The console driving this body, or None.

    The reverse of :func:`boarding_my_figure`, and it has to walk the drivers rather than
    read a link: the figure belongs to the SITE and the driving belongs to the CLIENT, and
    keeping the second fact off the figure is the entire point of the design.
    """
    fig_id = to_id(figure)
    for cid in set(Agent.SHARED.get_inventory_value(_DRIVERS_KEY, set()) or set()):
        if get_inventory_value(cid, KEY_FIGURE, None) == fig_id:
            return cid
    return None


def boarding_rooms_occupied():
    """Which rooms the party is currently standing in: ``{room id: client id}``."""
    return dict(_occupied())


def boarding_room_count():
    """Reset-ledger probe: rooms the party is believed to be standing in."""
    return len(_occupied())


# --- the constants above, as functions, because MAST cannot see a constant ------------
#
# `MastGlobals.import_python_module` registers FUNCTIONS only: a module-level string or
# list is never a MAST global. So every one of the names above is invisible from a .mast
# file, and a mission writing `any_role(ROOM_ROLES)` gets `NameError: name 'ROOM_ROLES'
# is not defined` - at RUNTIME, on the line that uses it, which is how this was found.
#
# Worse, headless cannot see it: the probe's room code only runs once a console has
# boarded, and `--test` has no consoles, so it reported PASS. A mission-facing constant
# needs an accessor or it does not exist.

def boarding_room_roles():
    """What counts as a room, for `any_role(...)`. See :data:`ROOM_ROLES`."""
    return (Agent.SHARED.get_inventory_value("__BOARDING_ROOM_ROLES__", None)
            or ROOM_ROLES)


def boarding_console_type():
    """The CONSOLE_TYPE a boarded console wears - `"boarding_crew"`.

    Deliberately not `"crew"`: that already means a damcon team, because
    LegendaryMissions spawns them `grid_spawn(..., "crew,damcons,lifeform")`.
    """
    from .boarding import BOARDING_CONSOLE
    return BOARDING_CONSOLE


def boarding_figure_role():
    """The role a boarding figure wears - `"boarding_figure"`."""
    return FIGURE_ROLE


def boarding_site_role():
    """The role an interior being boarded wears - `"boarding_site"`.

    LegendaryMissions' Engineering grid routes gate themselves OFF this, so it is shared
    across repos and must not be changed on one side alone.
    """
    return SITE_ROLE
