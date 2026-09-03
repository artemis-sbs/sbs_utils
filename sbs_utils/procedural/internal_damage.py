from .query import to_id, to_blob, to_object, to_list, to_set
from .roles import role, add_role, remove_role, all_roles,has_role
from .links import link,unlink
from .inventory import get_inventory_value, set_inventory_value
from .grid import (grid_objects, grid_objects_at, grid_closest, grid_get_grid_data,
                   grid_get_item_theme_data, grid_get_grid_current_theme,
                   grid_get_grid_named_theme, grid_get_layout, grid_get_theme_name,
                   grid_delete_object, grid_valid_blob, grid_get_damcons,
                   GRID_WORN_COLOR, GRID_TUNED_COLOR)
from .spawn import grid_spawn
from .comms import comms_broadcast
from .settings import settings_get_defaults
from .prefab import prefab_spawn

from .space_objects import get_pos
from .signal import signal_emit
from .execution import log
from ..helpers import FrameContext
from ..agent import Agent
from ..fs import is_dev_build

import random


def _grid_say(msg, level="warning"):
    """Say something about the engineering grid, on a channel the ENGINE actually shows.

    Every failure on this path used to be a bare ``return``. A hull that was never
    merged, a floor plan that was rejected, and a misspelled ``ship:`` key all present
    identically - as a dead Engineering console with nothing written anywhere. That cost
    a full engine session to diagnose once, and it would have cost the same every time.

    Two channels on purpose. ``log()`` is the library convention and is what a headless
    run and the test suite read, but in the engine it goes to a Python logger with NO
    handler attached, so it is invisible exactly where this class of bug lives. ``DEBUG``
    writes ``debug.log`` beside the executable, which survives the session.

    ASCII only - these strings can reach engine-rendered surfaces.
    """
    log(msg, "grid", level)
    try:
        from ..mast.mast import DEBUG
        DEBUG("[grid] " + msg)
    except Exception:                               # noqa: BLE001
        pass                                        # diagnostics never break a rebuild


# Teams on a hull whose interior data does not say. Every shipped floor plan and every
# third-party hull is in that case, so this is the number that must not change.
DEFAULT_DAMCON_COUNT = 3

_MAX_HP = 6
def grid_set_max_hp(max_hp):
    """Set the global maximum hit-point value for damcon-team grid objects.

    Args:
        max_hp (int): New maximum HP value. Defaults to 6 at module load.
    """
    global _MAX_HP
    _MAX_HP = max_hp

def grid_get_max_hp():
    """Return the current global maximum HP value for damcon-team grid objects.

    Returns:
        int: The max HP setting (default 6).
    """
    global _MAX_HP
    return _MAX_HP

def grid_set_hp(ship_id, GRID_OBJECT_ID, hp):
    """Set the HP of a damcon-team grid object and emit the ``life_form_hp_changed`` signal.

    Args:
        ship_id (Agent | int): The player ship agent ID or object.
        GRID_OBJECT_ID (Agent | int): The damcon-team grid object ID or agent.
        hp (int): The new HP value to assign.
    """
    set_inventory_value(GRID_OBJECT_ID, "HP",  hp)

    #@signal life_form_hp_changed data SHIP_id, LIFE_FORM_ID, HP
    signal_emit("life_form_hp_changed", {"SHIP_ID": ship_id, "LIFE_FORM_ID": GRID_OBJECT_ID, "HP": hp})    


"""
Future use hero Damcon name

Anushka
Brickwell
Cowbell
Fergus
Helga
Jenkins
Lumpy
Moose
Pliskin
Wally
"""


def _grid_begin(ship_id, layout):
    """Resolve what a build needs and clear whatever is standing there.

    Shared by the inline build and the phased one so the two can never drift. Returns
    ``(so, blob, SBS, items, theme_name, layout)``, or ``None`` when there is nothing to
    build - having already said why.
    """
    SBS = FrameContext.context.sbs
    so = to_object(ship_id)
    if so is None:
        _grid_say(f"rebuild {ship_id}: no space object - nothing to build an interior on")
        return None
    blob = to_blob(ship_id)
    if blob is None:
        _grid_say(f"rebuild {ship_id}: no data_set")
        return None

    # A hull has N named LAYOUTS - a full authored interior, a cheap systems-only one, a
    # jump-drive refit of the same hull. Most specific wins: an explicit argument, then
    # the ship's own "grid_layout" inventory value, then "default".
    if layout is None:
        layout = get_inventory_value(ship_id, "grid_layout", None)
    items = grid_get_layout(so.art_id, layout)
    if items is None:
        # THE return that swallows every mod floor-plan failure. Name the key that was
        # looked up, because the three ways to get here are indistinguishable otherwise:
        # the plan was never merged, the plan was rejected by the parser, or the plan's
        # `ship:` header does not spell the shipData key.
        key = so.art_id
        known = grid_get_grid_data() or {}
        near = [k for k in known if str(k).lower() == str(key or "").lower()]
        hint = f" Did you mean '{near[0]}'?" if near and near[0] != key else ""
        _grid_say(f"rebuild {ship_id}: no interior for ship_data_key '{key}' "
                  f"layout '{layout}'. grid_data holds {len(known)} hull(s).{hint} "
                  f"Engineering will be dead on this ship.")
        return None

    theme_name = grid_get_theme_name(so.art_id, layout)
    theme = grid_get_grid_named_theme(theme_name)
    blob.set("internal_color_ship_sillouette", theme["colors"]["silhouette"], 0)
    blob.set("internal_color_ship_lines", theme["colors"]["lines"], 0)
    blob.set("internal_color_ship_nodes", theme["colors"]["nodes"], 0)

    # Clear what is there. Deferring the FIRST build until the hull is settled means this
    # is normally a no-op, which is the point - an interior built for a hull the crew
    # never flies has to be torn down again, and the tear-down is what that avoids.
    #
    # "NORMALLY A NO-OP" IS THE CLAIM THIS COUNT EXISTS TO TEST, and it is only safe to
    # believe on a COLD start. `get_hull_map` is keyed by ship id and the sim RECYCLES
    # space-object ids across a restart (`cosmos_dev/mock/sbs.py` clears `hull_map_objects`
    # on `create_new_sim` for exactly this reason: "a new ship reuses an old id and
    # get_hull_map hands back the PREVIOUS ship's grid objects"). The engine's C++ side
    # outlives a mission restart, so on run 2 this loop may be handed run 1's objects and
    # delete them - which is a free of something this run never owned, and the shape of the
    # `ObjectDataBlob` use-after-free that kills the server minutes in.
    #
    # So: a nonzero count on a FIRST build is the finding. Silent when there is nothing to
    # clear, so a cold run stays quiet and only the interesting case speaks.
    cleared = 0
    for k in grid_objects(ship_id):
        grid_delete_object(ship_id, k)
        cleared += 1
    if cleared:
        _grid_say(f"rebuild {ship_id} '{so.art_id}': cleared {cleared} pre-existing grid "
                  f"object(s) before building - expected 0 on a first build", "info")

    # THE HULL MAP GOES STALE ACROSS A HULL CHANGE. `get_hull_map` populates on create and
    # then caches, so after a re-hull it still reports the PREVIOUS hull's dimensions -
    # measured, tsn_battle_cruiser 16x14 still being reported for a tng_fed_defiant, which
    # is 16x15. Rooms outside w x h are silently dropped, so that hull quietly loses its
    # last row. Force a rebuild only when the two disagree, so the ordinary path is
    # untouched (forceCreate also erases grid objects, hence after the delete above).
    try:
        from .ship_data import get_ship_data_for      # local: ship_data imports widely
        hm = SBS.get_hull_map(ship_id)
        data = get_ship_data_for(so.art_id) or {}
        want_w, want_h = data.get("internalmapw"), data.get("internalmaph")
        if want_w and want_h and (getattr(hm, "w", 0) != int(want_w)
                                  or getattr(hm, "h", 0) != int(want_h)):
            _grid_say(f"rebuild {ship_id} '{so.art_id}': hull map was "
                      f"{getattr(hm, 'w', 0)}x{getattr(hm, 'h', 0)}, shipData says "
                      f"{want_w}x{want_h} - rebuilding it", "info")
            SBS.get_hull_map(ship_id, True)
    except Exception:                               # noqa: BLE001
        pass                                        # never let the resize break a build

    return so, blob, SBS, items, theme_name, layout


def _grid_spawn_chunk(ship_id, so, theme_name, chunk, counts):
    """Spawn one slice of a hull's rooms. Returns False if the engine refused one.

    A PHASED build queues its slices ahead of time, so once one fails the rest are
    already scheduled - they check this and do nothing rather than half-filling a hull.
    """
    if counts.get("failed"):
        return False
    # A phased build queues its slices ahead of time, so by the time this one runs the
    # ship may have been destroyed, culled or re-hulled. Re-resolve rather than trusting
    # the captured `so` - the same reason `_grid_finish` re-resolves the blob.
    so = to_object(ship_id)
    if so is None:
        counts["failed"] = True
        return False
    for g in chunk:
        loc_x = int(g["x"])
        loc_y = int(g["y"])
        name_tag = f"{g['name']}:{loc_x},{loc_y}"

        item_theme_data = grid_get_item_theme_data(g["roles"], theme_name)
        color = item_theme_data.color
        icon = item_theme_data.icon
        # NOTE the per-object "scale" in grid_data.json is deliberately NOT read. Those
        # values are artifacts of whatever tool wrote the file, not authored intent.
        scale = item_theme_data.scale
        go = grid_spawn(ship_id, name_tag, name_tag, loc_x, loc_y, icon, color,
                        "#," + g["roles"])
        if go is None:
            _grid_say(f"rebuild {ship_id} '{so.art_id}': grid_spawn failed at "
                      f"{loc_x},{loc_y} for '{g['name']}' after {counts['made']} "
                      f"object(s) - system_max_damage NOT written, so this ship has no "
                      f"damage model.")
            counts["failed"] = True
            return False
        go.engine_object.layer = 0
        go.blob.set("icon_scale", scale / 2, 0)
        set_inventory_value(go.id, "color", color)
        set_inventory_value(go.id, "icon_index", icon)
        set_inventory_value(go.id, "icon_scale", scale)

        # Add link so query can find this relationship, e.g.
        #   linked_to(player_id, "grid_objects") & role("engine")
        link(so, "grid_objects", go)
        add_role(go, "__undamaged__")
        counts["made"] += 1

        roles = g["roles"].lower()
        if "sensor" in roles:
            counts["sensors"] += 1
        if "engine" in roles:
            counts["engines"] += 1
        if "shield" in roles:
            counts["shields"] += 1
        if "weapon" in roles:
            counts["weapons"] += 1
    return True


def _grid_finish(ship_id, so, SBS, counts, layout):
    """Everything that must happen once the last room is in.

    Kept apart from the spawning so a PHASED build can run it after the final slice - a
    ship must not sit with a damage model that counts only the rooms created so far.

    RESOLVE THE BLOB HERE, NEVER CARRY ONE IN. `Agent.data_set` returns None once the
    agent is dead (`agent.py`, "Every crashing write went through here"), and that guard
    is the whole defense against the ObjectDataBlob use-after-free. A phased build runs
    this up to `over` seconds after `_grid_begin` resolved things, so a blob captured
    back then walks straight past the guard and writes into freed engine memory - which
    is a server crash to desktop, not an exception. Measured 2026-08-25: fault in
    `ObjectDataBlob::operator[]` under `ObjectDataBlob::Set`, from `Simulation::Tick`.
    """
    blob = to_blob(ship_id)
    if blob is None:
        _grid_say(f"interior for {ship_id} finished late: the ship is gone", "info")
        return
    blob.set('system_max_damage', counts["weapons"], SBS.SHPSYS.WEAPONS)
    blob.set('system_max_damage', counts["engines"], SBS.SHPSYS.ENGINES)
    blob.set('system_max_damage', counts["sensors"], SBS.SHPSYS.SENSORS)
    blob.set('system_max_damage', counts["shields"], SBS.SHPSYS.SHIELDS)
    blob.set('system_damage', 0, SBS.SHPSYS.WEAPONS)
    blob.set('system_damage', 0, SBS.SHPSYS.ENGINES)
    blob.set('system_damage', 0, SBS.SHPSYS.SENSORS)
    blob.set('system_damage', 0, SBS.SHPSYS.SHIELDS)

    # Needed to reset the coefficients after an explosion.
    set_damage_coefficients(ship_id)
    # Pass the layout we resolved: the ship's own "grid_layout" may not be the one this
    # rebuild was asked for, and the damcon declaration lives per layout.
    grid_restore_damcons(ship_id, layout)

    hm = SBS.get_hull_map(ship_id)
    # The marker and the EPad used to make the IDENTICAL unfiltered call with no state
    # change between them, so they landed on the same cell on every hull, always. Sharing
    # the damcons' resolver keeps them apart.
    placed = set()
    loc = _grid_resolve_point(SBS, ship_id, hm, None, placed, prefer_empty=False,
                              who="marker")
    if loc is None:
        _grid_say(f"rebuild {ship_id} '{so.art_id}': the engine offered no usable cell "
                  f"for the marker, so there is no marker and no EPad. The hull map has "
                  f"no open cells - see the interior-bitmap note above.")
        return
    placed.add((loc[0], loc[1]))
    ship = ship_id & 0xFFFFFFFF
    # 23 flag, 101-filled square, 111
    marker_go = grid_spawn(ship_id, "marker", f"marker:{ship}", int(loc[0]), int(loc[1]),
                           101, "#9994", "#,marker")
    marker_go.blob.set("icon_scale", 1.5, 0)
    marker_go.engine_object.layer = 6
    set_inventory_value(ship_id, "marker_id", to_id(marker_go))

    loc = _grid_resolve_point(SBS, ship_id, hm, None, placed, prefer_empty=False,
                              who="epad")
    if loc is None:
        _grid_say(f"rebuild {ship_id} '{so.art_id}': no usable cell for the EPad - the "
                  f"grid is built but engineering has no power pad.")
        return
    epad_go = grid_spawn(ship_id, "EPad", f"epad:{ship}", int(loc[0]), int(loc[1]),
                         134, "#9994", "tools,epad")
    epad_go.engine_object.layer = 0
    epad_go.blob.set("icon_scale", 0.01, 0)
    set_inventory_value(ship_id, "epad_id", epad_go.id)

    # One line on SUCCESS too. Without it, "no line at all" means both "built perfectly"
    # and "never called" - and on this path the second is a real possibility, since
    # nothing in sbs_utils calls this function. Every caller is a mission.
    _grid_say(f"rebuild {ship_id} '{so.art_id}' layout '{layout or 'default'}': "
              f"{counts['made']} object(s), hull map "
              f"{getattr(hm, 'w', 0)}x{getattr(hm, 'h', 0)}", "info")

    # THE INTERIOR NOW EXISTS - say so, because a deferred build means nobody can assume
    # it does. Anything that reads the grid to decide something about the ship (LM sets
    # the warp/jump drive flags from whether the hull has warp or jump nodes) used to run
    # on the line after the build and now has to wait for one. SHIP_ID / GRID_OBJECTS
    # arrive as task variables; CAPS because the system emits it.
    signal_emit("grid_interior_built", {"SHIP_ID": ship_id,
                                        "GRID_OBJECTS": counts["made"],
                                        "HULL_KEY": so.art_id})


def grid_rebuild_grid_objects(id_or_obj, grid_data=None, layout=None):
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
    new one. Reading the global each time is what keeps the two in step.
    """
    ship_id = to_id(id_or_obj)
    begun = _grid_begin(ship_id, layout)
    if begun is None:
        return
    so, blob, SBS, items, theme_name, layout = begun
    counts = {"made": 0, "sensors": 0, "engines": 0, "shields": 0, "weapons": 0}
    if not _grid_spawn_chunk(ship_id, so, theme_name, items, counts):
        return
    _grid_finish(ship_id, so, SBS, counts, layout)


# --- deferred, phased interior creation ---------------------------------------------
#
# WHY A SHIP'S INTERIOR IS NOT BUILT WHEN IT SPAWNS.
#
# Player ships are created long before anyone picks a map. LegendaryMissions builds the
# whole roster at server-console start, so a `//spawn` route that builds an interior
# builds one for EVERY slot - eight of them - on whatever hull the roster happened to
# name. Then the operator starts a map and `reconcile_player_roster` culls to
# PLAYER_COUNT, parks the rest on standby and applies the game code's hull; then the map
# body may re-hull again (a Star Trek trial seats its crew in the ship the trial is
# about). Measured on one such trial: 110 objects built for a hull nobody flew, then 124
# built twice more for the hull they did - 358 creations, plus a full delete of the
# first set, to arrive at 124.
#
# Nothing needs those objects before the game runs. So a request is RECORDED, not built,
# and the build happens once the hulls are final - reading the hull at BUILD time, so all
# that churn collapses into a single build of the right interior and there is nothing to
# delete.
#
# The build itself is then PHASED, the way terrain is sown: `DripQueue` spreads the
# spawns across ticks instead of landing a hull's worth in one frame. Terrain measured
# ~280 ms in a single frame for its field; a grid is smaller but arrives at exactly the
# moment a map is already doing everything else at once.
#
# Coalesced by ship id throughout: asking twice builds once.

_INTERIOR = {"q": None, "wanted": {}, "queued": set(), "armed": False,
             "over": 4.0, "chunk": 16}


def _grid_interior_focus(ship_id):
    try:
        return get_pos(ship_id)
    except Exception:                               # noqa: BLE001
        return None


def _grid_interior_done(ship_id, so, SBS, counts, layout):
    """Finish one ship's phased build and let it be requested again."""
    _INTERIOR["queued"].discard(ship_id)
    _grid_finish(ship_id, so, SBS, counts, layout)


def _grid_interior_skip(ship_id):
    """Should this build be dropped rather than run? Says why, quietly.

    Reading the hull at build time collapses the re-hulling churn, but it does not answer
    the other half: a ship may not be FLOWN at all. The roster parks every slot past
    PLAYER_COUNT - suspended to standby, hull blanked to `invisible` - and building an
    interior for one means walking the whole layout lookup to discover there is no
    floor plan for `invisible`, then saying so loudly, once per parked hull. Seven of
    those per run on a default roster, and every one of them is noise.

    Standby is the test rather than `__player__`, because it is what "not in play" means
    to the engine and it keeps this general - the roster is not the only thing that parks.
    """
    from ..helpers import FrameContext
    so = to_object(ship_id)
    if so is None:
        return "the ship is gone"
    try:
        if FrameContext.context.sbs.in_standby_list_id(ship_id):
            return "the ship is parked in standby"
    except Exception:                               # noqa: BLE001
        pass
    return None


def _grid_interior_start(ship_id, layout):
    """Resolve the hull NOW - not when it was requested - and queue its rooms in slices."""
    skip = _grid_interior_skip(ship_id)
    if skip is not None:
        _grid_say(f"interior for {ship_id} dropped: {skip}", "info")
        _INTERIOR["queued"].discard(ship_id)
        return
    begun = _grid_begin(ship_id, layout)
    if begun is None:
        _INTERIOR["queued"].discard(ship_id)
        return
    so, blob, SBS, items, theme_name, layout = begun
    counts = {"made": 0, "sensors": 0, "engines": 0, "shields": 0, "weapons": 0}
    q = _INTERIOR["q"]
    size = max(1, int(_INTERIOR["chunk"]))
    slices = [items[i:i + size] for i in range(0, len(items), size)]
    if q is None:                                   # flushed, or never armed - inline
        for part in slices:
            if not _grid_spawn_chunk(ship_id, so, theme_name, part, counts):
                _INTERIOR["queued"].discard(ship_id)
                return
        _grid_interior_done(ship_id, so, SBS, counts, layout)
        return
    pos = _grid_interior_focus(ship_id)
    for part in slices:
        q.add(_grid_spawn_chunk, (ship_id, so, theme_name, part, counts), pos=pos)
    q.add(_grid_interior_done, (ship_id, so, SBS, counts, layout), pos=pos)


def _grid_interior_enqueue(ship_id, layout):
    if ship_id in _INTERIOR["queued"]:
        return False                                # already on its way; one build only
    _INTERIOR["queued"].add(ship_id)
    q = _INTERIOR["q"]
    if q is None:
        from ..tickdispatcher import DripQueue
        q = DripQueue(over=_INTERIOR["over"], name="grid")
        _INTERIOR["q"] = q
    q.add(_grid_interior_start, (ship_id, layout), pos=_grid_interior_focus(ship_id))
    return True


def grid_interior_request(id_or_obj, layout=None):
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
        bool: whether the request was recorded.
    """
    ship_id = to_id(id_or_obj)
    if ship_id is None:
        return False
    if not _INTERIOR["armed"]:
        # Coalesces by id, and a later request wins on layout - the most recent caller
        # knows most about what this ship is going to be.
        _INTERIOR["wanted"][ship_id] = layout
        return True
    return _grid_interior_enqueue(ship_id, layout)


def grid_interior_arm(over=None, chunk=None):
    """The hulls are final: build every interior that was asked for, phased over ticks.

    Call this once a map has settled - past the roster cull and past whatever re-hulling
    the map does for itself. Requests made after this point are queued immediately, so a
    mid-game refit still gets an interior without anyone re-arming anything.

    Args:
        over (float, optional): sim-seconds to spread the work across (default 4).
        chunk (int, optional): rooms created per slice (default 16).

    Returns:
        int: how many ships were released to build.
    """
    if over is not None:
        _INTERIOR["over"] = float(over)
    if chunk is not None:
        _INTERIOR["chunk"] = int(chunk)
    _INTERIOR["armed"] = True
    wanted = _INTERIOR["wanted"]
    _INTERIOR["wanted"] = {}
    n = 0
    for ship_id, layout in list(wanted.items()):
        if _grid_interior_enqueue(ship_id, layout):
            n += 1
    if n:
        _grid_say(f"interiors armed: {n} ship(s), spread over {_INTERIOR['over']}s", "info")
    return n


def grid_interior_pending():
    """Ships recorded but not yet built, plus queued work still to run."""
    q = _INTERIOR["q"]
    return len(_INTERIOR["wanted"]) + (0 if q is None else q.pending())


def grid_interior_is_armed():
    """Whether interiors are being built as they are requested."""
    return _INTERIOR["armed"]


def grid_interior_flush():
    """Build everything outstanding right now.

    For a test, a headless conformance run, or anything that cannot wait for the drip.
    """
    _INTERIOR["armed"] = True
    wanted = _INTERIOR["wanted"]
    _INTERIOR["wanted"] = {}
    for ship_id, layout in list(wanted.items()):
        _grid_interior_enqueue(ship_id, layout)
    q = _INTERIOR["q"]
    if q is None:
        return 0
    # DRAIN, don't flush once. The first item for a ship is `_grid_interior_start`, whose
    # whole job is to queue that hull's room slices - so a single flush runs the planner
    # and returns with all the actual work still sitting in the queue. Measured: flush
    # reported 1 item run, 8 still pending, and the ship had ZERO grid objects.
    #
    # Bounded rather than `while pending()`: a build that somehow re-queues itself would
    # otherwise hang the caller, and a test or a headless run is exactly where nobody is
    # watching. Each pass drains at least one item, so the ceiling is generous.
    total = 0
    for _ in range(64):
        n = q.flush()
        total += n
        if not q.pending():
            break
    if q.pending():
        _grid_say(f"interior flush gave up with {q.pending()} item(s) still queued", "warning")
    return total


def grid_interior_reset():
    """Drop queued interior work and disarm (mission reset)."""
    q = _INTERIOR["q"]
    if q is not None:
        try:
            q.clear()
        except Exception:                           # noqa: BLE001
            pass
    _INTERIOR["q"] = None
    _INTERIOR["wanted"] = {}
    _INTERIOR["queued"] = set()
    _INTERIOR["armed"] = False


def _grid_retire_extra_damcons(hm, ship_id, count):
    """Delete DC teams above ``count`` - a hull whose declaration shrank, or a refit.

    Matches ``DC<n>`` carrying the ``damcons`` role only, so nothing else on the grid can
    be caught by a name that happens to look like one.
    """
    n = count + 1
    while True:
        go = hm.get_grid_object_by_name(f"DC{n}")
        if go is None:
            break
        gid = go.unique_ID
        if to_object(gid) is not None and has_role(gid, "damcons"):
            grid_delete_object(ship_id, gid)
        n += 1


def _grid_resolve_point(SBS, ship_id, hm, declared, used=None, prefer_empty=True, who=""):
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
        list[int] | None: ``[x, y]``.
    """
    used = set() if used is None else used
    if declared is not None:
        x, y = int(declared[0]), int(declared[1])
        w = getattr(hm, "w", 0) or 0
        h = getattr(hm, "h", 0) or 0
        if 0 <= x < w and 0 <= y < h and hm.is_grid_point_open(x, y):
            return [x, y]
        log(f"declared damcon post {who} at {x},{y} is not on this hull "
            f"({w}x{h}) - letting the engine choose instead", "grid", "warning")

    v = SBS.vec3(0.5, 0, 0.5)
    point = []
    if prefer_empty:
        point = SBS.find_valid_unoccupied_grid_point_for_vector3(ship_id, v, 5)
    # A hull whose every open cell holds a room has no unoccupied cell at all - a
    # legitimate floor plan (LM #381), not an error - so fall back to a finder that only
    # requires the cell to be on the hull.
    if len(point) == 0:
        point = SBS.find_valid_grid_point_for_vector3(ship_id, v, 5)
    if len(point) == 0:
        return None
    return _grid_unused_point(hm, point, used)


def _grid_unused_point(hm, point, used):
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
        list[int]: ``[x, y]``.
    """
    if (point[0], point[1]) not in used:
        return point
    w = getattr(hm, "w", 0) or 0
    h = getattr(hm, "h", 0) or 0
    if w <= 0 or h <= 0:
        return point
    for r in range(1, w + h + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                # Ring only, so nearer cells win.
                if max(abs(dx), abs(dy)) != r:
                    continue
                x, y = point[0] + dx, point[1] + dy
                if x < 0 or y < 0 or x >= w or y >= h:
                    continue
                if (x, y) in used:
                    continue
                if not hm.is_grid_point_open(x, y):
                    continue
                return [x, y]
    return point


def grid_damcon_count(id_or_obj, layout=None):
    """How many damcon teams this ship's interior declares.

    ``3`` for every hull that declares nothing, which is nearly all of them.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        layout (str, optional): Layout name. Defaults to the ship's ``grid_layout``.

    Returns:
        int: The team count.
    """
    decl = _grid_damcon_decl(to_id(id_or_obj), layout)
    return DEFAULT_DAMCON_COUNT if decl is None else decl["count"]


def _grid_damcon_decl(ship_id, layout=None):
    """The hull's damcon declaration, or ``None`` when it declares nothing."""
    so = to_object(ship_id)
    if so is None:
        return None
    if layout is None:
        layout = get_inventory_value(ship_id, "grid_layout", None)
    return grid_get_damcons(so.art_id, layout)


def grid_restore_damcons(id_or_obj, layout=None):
    """Restore all damcon teams on a ship to full health, creating them if missing.

    How many teams there are, and where they stand, come from the hull's interior data
    when it says (``grid_get_damcons``); otherwise three teams wherever the engine puts
    them, exactly as before. A declared post is also the team's permanent rally point,
    because the prefab spawns the rally marker on the cell it is handed.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        layout (str, optional): Layout name. Defaults to the ship's ``grid_layout``
            inventory value. Pass it explicitly when rebuilding into a layout the ship has
            not been switched to yet.
    """
    SBS = FrameContext.context.sbs
    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "cockpit"):
        return

    hm = SBS.get_hull_map(ship_id)
    if hm is None:
        _grid_say(f"damcons {ship_id}: no hull map, so this ship gets NO damage control "
                  f"teams and can never repair itself.")
        return

    decl = _grid_damcon_decl(ship_id, layout)
    count = DEFAULT_DAMCON_COUNT if decl is None else decl["count"]
    posts = [] if decl is None else decl["posts"]

    item_theme_data = grid_get_item_theme_data("damcons")
    rally_theme_data = grid_get_item_theme_data("rally_point")
    #
    # Get Colors from theme
    # 
    colors  = item_theme_data.color
    damage_colors  = item_theme_data.damage_color
    #
    #TODO: REMOVE When Grid AI is proven
    settings = settings_get_defaults()
    interns = True # settings.get("NEW_DAMCONS", is_dev_build())
    prefab_label = get_inventory_value(ship_id, "PREFAB_DAMCONS", "prefab_lifeform_damcons")
    #
    # Create damcons/lifeforms
    #
    color_count = len(colors)
    # Cells already handed out in THIS call. The engine's finder has no memory across the
    # loop, so on a hull with no empty cell it returns the SAME cell three times and all
    # three teams (and their rally markers) stack, reading as one team on the engineering
    # display. On a hull with hallways the unoccupied finder spreads them for free, because
    # each new team occupies the cell it took.
    used = set()
    _grid_retire_extra_damcons(hm, ship_id, count)
    for i in range(count):
        # See if damcon exists
        _name = f"DC{i+1}"
        _test_go = hm.get_grid_object_by_name(_name)
        # A name lookup asks the ENGINE, which still lists a grid object whose native free
        # is only queued. grid_delete_object tombstones the Agent now and defers the free to
        # the end of the event handler, so during a REBUILD (which deletes every grid object
        # and then calls us) the old DC1..DC3 are still findable by name. Healing one of
        # those instead of creating a team leaves the ship with NO damage control at all once
        # the queue drains - every rebuild after the first: player respawn, hangar craft,
        # any mission that swaps a layout.
        if _test_go is not None and to_object(_test_go.unique_ID) is None:
            _test_go = None

        if _test_go is not None:
            # data_set.get's second argument is the INDEX, not a default - index 0 is the
            # slot everything writes curx/cury to. Asking for index -1 makes the ENGINE
            # return None (int(None) -> TypeError on the first dock); the mock's defaults
            # table answered anyway, which is why this only ever failed in the engine.
            _cx = _test_go.data_set.get("curx", 0)
            _cy = _test_go.data_set.get("cury", 0)
            if _cx is not None and _cy is not None:
                used.add((int(_cx), int(_cy)))
            _id = _test_go.unique_ID # _test_go is an object from the engine
            _blob = to_blob(_test_go.unique_ID)
            if _blob is not None:
                _blob.set("icon_color", colors[i%color_count], 0)
            # Hit points == MAX_HP
            hp = grid_get_max_hp()
            grid_set_hp(ship_id, _id, hp)
        else:
            point = _grid_resolve_point(SBS, ship_id, hm,
                                        posts[i] if i < len(posts) else None,
                                        used, prefer_empty=True, who=_name)
            if point is None:
                break
            used.add((point[0], point[1]))

            dc = None
            color = colors[i%color_count]
            damage_color = damage_colors[i%color_count]


            if interns:
                # The prefab does the whole job: it grid_spawns the team, its rally marker,
                # and seeds "blackboard:idle_pos" (LM ai/grid_brains.mast). It contains no
                # await, so its task is always done() in-frame and dc is the team.
                dc_task = prefab_spawn(prefab_label, {"ship_id": ship_id, "NAME":_name, "START_X": point[0], "START_Y": point[1], "COLOR": color, "DAMAGE_COLOR":damage_color})
                if dc_task is None:
                    # Bad PREFAB_DAMCONS override, or the LM "ai" mastlib is not loaded.
                    log(f"damcon prefab '{prefab_label}' not found - {_name} not created", "grid", "error")
                    continue
                if dc_task.done():
                    dc = dc_task.result()
                if dc is None:
                    log(f"damcon prefab '{prefab_label}' yielded no result for {_name}", "grid", "error")
                    continue
                continue

#region TODO: Old Damcons remove
            # if not interns and dc is None:
            #     icon = 2
            #     color = colors[i%color_count]
            #     dc = grid_spawn(ship_id, _name, _name, point[0],point[1],icon, color, "crew,damcons,lifeform")
            #     #
            #     # Create idle/rally point
            #     #
            #     _id = to_id(dc)
            #     _go = to_object(dc)
            #     marker_tag = f"{_go.name} rally point"
                
            #     icon =  rally_theme_data.icon
            #     rally_scale = rally_theme_data.scale

            #     idle_marker = grid_spawn(ship_id, marker_tag, marker_tag, point[0],point[1], icon, color, "#,rally_point") 
            #     _blob = to_blob(idle_marker)
            #     _blob.set("icon_scale", rally_scale, 0)
            #     set_inventory_value(_id, "idle_marker", to_id(idle_marker))
#endregion

            # Only reachable with interns off, which no longer builds anything. Say so
            # rather than leaving a ship silently without damage control.
            log(f"damcons disabled (interns off) - {_name} not created", "grid", "error")



def grid_apply_system_damage(id_or_obj):
    """Update system-damage counts and coefficients; explode the ship if all nodes are damaged.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.

    Returns:
        bool: ``True`` if the ship has been destroyed, ``False`` otherwise.
    """
    SBS = FrameContext.context.sbs

    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "exploded"):
        return
    blob = to_blob(ship_id)
    if blob is None:
        # The ship was removed (e.g. destroyed) before this internal-damage tick
        # ran, so it has no data_set. Previously a raw sbs.delete_object left the
        # agent in Agent.all with a dangling data_set pointer, masking this as a
        # silent use-after-free; with deferred delete to_blob correctly returns
        # None, so guard it.
        return

    undamaged_grid_objects = grid_objects(ship_id) & role("__undamaged__")
    damaged_grid_objects = grid_objects(ship_id) & role("__damaged__")
    the_roles =  ["weapon", "engine", "sensor", "shield"]


    for x in range(SBS.SHPSYS.MAX):
        # system_damaged = damaged_grid_objects & role(the_roles[x])
        system_damage = damaged_grid_objects & role(the_roles[x])
        cur = len(system_damage)
        blob.set('system_damage',cur, x)

    #should explode if len(undamaged_grid_objects)==0

    undamaged = undamaged_grid_objects & (role("weapon") | role("sensor") | role("shield") | role("engine")) 
    should_explode = len(undamaged) == 0
    set_damage_coefficients(ship_id)

    if should_explode:
        explode_player_ship(ship_id)


        # def _delete_ship(t):
        #     if get_shared_inventory_value("GAME_ENDED", False):
        #         return
        #     for cid in linked_to(ship_id, "consoles") -  role("mainscreen"):
        #         gui_reroute_client(cid, "show_hangar")

        #     so = to_object(t.ship_id)
        #     if so is not None:
        #         sbs.delete_object(t.ship_id)

        # t = TickDispatcher.do_once(_delete_ship, 3)
        # t.ship_id = ship_id



        # respawn_seconds = get_inventory_value(ship_id, "respawn_time", None)
        # if respawn_seconds is not None:
        #     def _do_respawn(t):
        #         respawn_player_ship(t.ship_id)    
        #         grid_rebuild_grid_objects(t.ship_id)

        #     t = TickDispatcher.do_once(_do_respawn, respawn_seconds)
        #     t.ship_id = ship_id

    return should_explode

def explode_player_ship(id_or_obj):
    """Mark a player ship as destroyed and emit the ``player_ship_destroyed`` signal.

    The ship is made invisible and tagged ``"exploded"`` rather than deleted
    immediately, allowing scripts to react before removal.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
    """
    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "exploded"):
        return
    blob = to_blob(ship_id)
    so = to_object(ship_id)
    
    pos = get_pos(ship_id)
    # if pos:
    #     sbs.create_transient(1, 0, ship_id, 0, 0, pos.x, pos.y, pos.z, "")  
    #
    # Need to replace transient

    add_role(ship_id, "exploded")
    
    art_id = so.art_id
    set_inventory_value(ship_id, "art_id", art_id)
    so.set_art_id("invisible")
    # Reset the systems to no damage
    for sys in range(4):
        blob.set('system_damage', 0, sys)
    # Send Signal that the ship has been destroyed
    signal_emit("player_ship_destroyed", {"DESTROYED_ID": ship_id})


def respawn_player_ship(id_or_obj):
    """Respawn a previously destroyed player ship at its original spawn position.

    Restores the ship's art ID, repositions it to the spawn point, and removes
    the ``"exploded"`` role.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
    """
    ship_id = to_id(id_or_obj)
    art_id = get_inventory_value(ship_id, "art_id")
    so = to_object(ship_id)
    if so is None:
        return
    engine_obj = so.space_object()
    if engine_obj is None:
        return
    FrameContext.context.sim.reposition_space_object(engine_obj, so.spawn_pos.x, so.spawn_pos.y, so.spawn_pos.z)
    so.set_art_id(art_id)
    remove_role(ship_id, "exploded")


def grid_damage_hallway(id_or_obj, loc_x, loc_y, damage_color):
    """Spawn a fire/damage marker at an empty hallway grid cell.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        loc_x (int): Grid column of the hallway cell.
        loc_y (int): Grid row of the hallway cell.
        damage_color (str): Color to apply to the damage marker icon.
    """
    ship_id = to_id(id_or_obj)
    icon = 45 #fire   # 113 - Door

    name_tag = f"hallway:{loc_x},{loc_y}"
    dam_go = grid_spawn(ship_id, name_tag, name_tag, loc_x,loc_y, icon, damage_color, "#,hallway,__damaged__") 
    link(ship_id, "damage", to_id(dam_go))


def set_damage_coefficients(id_or_obj):
    """Recalculate and write the damage coefficients for all ship systems.

    For each system (beam, torpedo, impulse, warp, maneuver, sensors, shields)
    computes the ratio of undamaged to total nodes and writes it to the blob.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
    """
    # TODO: Update this to use a more robust system of determining what systems exist and can be damaged.
    ship_id = to_id(id_or_obj)
    blob = to_blob(ship_id)
    if blob is None:
        return

    ship_gos = grid_objects(ship_id)
    # This ship's undamaged
    undamaged = ship_gos & role("__undamaged__")
    # This ships damaged
    damaged = ship_gos & role("__damaged__")
    #
    # get all eight systems damaged and undamaged
    #
    # arrays, Beam, Tube, Shield
    systems = [
        ("beam", "all_beam_damage_coeff",0), 
        ("torpedo", "all_tube_damage_coeff",0), 
        ("impulse", "impulse_damage_coeff",0), 
        ("warp", "warp_damage_coeff",0), 
        ("maneuver", "turn_damage_coeff",0),
        # "sensor", not "sensors": the role every ship actually carries is SINGULAR (92
        # uses in the shipped data, zero plural). Matching the plural meant this coeff was
        # permanently 1.0 - sensor damage never degraded sensors at all.
        ("sensor", "sensor_damage_coeff",0),
        ("shield,fwd", "shield_damage_coeff",0), 
        ("shield,aft", "shield_damage_coeff",1)
        ]


    for system in systems:
        sys_role = system[0]
        _blob_name = system[1]
        _idx = system[2]

        pool = ship_gos & all_roles(sys_role)
        total = len(pool)
        if total == 0:
            _coef = 1.0
        else:
            # A weighted mean over the pool, not a count of undamaged nodes: a
            # damaged node contributes 0, a nominal one 1, a WORN one
            # WEAR_WORN_FACTOR and a TUNED one 1 + WEAR_TUNED_BONUS - which is the
            # only place the over-unity bonus can come from, capped so a fully tuned
            # ship is exactly +10 percent and no arithmetic can make it more.
            #
            # With no wear anywhere every node weighs 1.0 or 0.0, so this is
            # NUMERICALLY IDENTICAL to the len(undamaged)/total it replaced. That is
            # what test_grid_wear pins, and it is why this is inert on every mission
            # that never wears anything.
            _coef = min(WEAR_COEFF_MAX,
                        sum(grid_node_efficiency(i) for i in pool) / total)
        # do print(f"damage {_coef} {_blob_name}")
        blob.set(_blob_name, _coef, _idx)

def _grid_promote_maintenance_to_repair(node_id):
    """A node under a TUNE order just broke - the order becomes a REPAIR order.

    Local import: work_orders imports this module for grid_node_state, so a
    top-level import would be a cycle.

    Without this the order keeps its `maintain` kind, and `work_order_is_satisfied`
    for maintenance asks "is it tuned" - which a broken node never is - so the team
    keeps walking to it and `ai_tune_node` tries to tune something in pieces.
    """
    try:
        from .work_orders import (work_order_get, work_order_set_priority,
                                  KIND_REPAIR, KIND_MAINTAIN, MAINTENANCE_ROLE,
                                  PRIORITY_NORMAL)
    except ImportError:                             # pragma: no cover
        return
    order = work_order_get(node_id)
    if order is None or order.get("kind") != KIND_MAINTAIN:
        return
    remove_role(node_id, MAINTENANCE_ROLE)
    set_inventory_value(node_id, "work_order",
                        {"kind": KIND_REPAIR,
                         # A repair on something a team was already sent to is worth
                         # at least the normal rung; maintenance defaults to LOW and
                         # would leave a live break at the bottom of the list.
                         "priority": max(order.get("priority", 0), PRIORITY_NORMAL)})


def grid_damage_grid_object(ship_id, grid_id, damage_color):
    """Mark a grid object as damaged and apply a damage color to its icon.

    Tools, markers, and rally-point objects are ignored.

    Args:
        ship_id (Agent | int): The player ship agent ID or object.
        grid_id (Agent | int): The grid object to damage.
        damage_color (str): Color to apply to the damaged grid-object icon.
    """
    # Note that ship_id and grid_id CAN be Agents; the functions that use these values convert them as needed.
    if has_role(grid_id, "tools"):
        return
    if has_role(grid_id, "marker"):
        return
    blob = to_blob(grid_id)
    blob.set("icon_color", damage_color, 0)
    link(ship_id, "damage", grid_id) 
    add_role(grid_id, "__damaged__")
    remove_role(grid_id, "__undamaged__")
    # Damage supersedes wear: a broken node is not also a tired one, and leaving
    # __worn__ on it would have it counted in the worn pool AND the damaged one.
    remove_role(grid_id, "__worn__")
    # A tune job on a node that just broke is now a REPAIR job - the work got more
    # urgent, not irrelevant. Promoting it keeps the team that was already sent here
    # walking, and stops ai_tune_node trying to tune something that is in pieces.
    _grid_promote_maintenance_to_repair(grid_id)

# def grid_mark_repaired_grid_object(ship_id, grid_id, repair_color):
#     blob = to_blob(grid_id)
#     blob.set("icon_color", repair_color, 0)
#     unlink(ship_id, "damage", grid_id) 
#     remove_role(grid_id, "__damaged__")
#     add_role(grid_id, "__undamaged__")

    


def convert_system_to_string(the_system):
    """Convert a ship system enum or integer to its role-name string.

    Args:
        the_system (sbs.SHPSYS | int | str): The system enum, integer index,
            or role-name string.

    Returns:
        str: Role name for the system (``"weapon"``, ``"engine"``,
            ``"sensor"``, or ``"shield"``).
    """
    SBS = FrameContext.context.sbs
    if isinstance(the_system, str):
        return the_system
    elif isinstance(the_system, SBS.SHPSYS):
        the_system = the_system.value
    
    the_roles =  ["weapon", "engine", "sensor", "shield"]
    hit_system = int(the_system)
    return the_roles[hit_system]

    
    

def grid_damage_system(id_or_obj, the_system=None):
    """Damage a random undamaged grid node for the specified ship system.

    Args:
        id_or_obj (Agent | int | CloseData | SpawnData): The player ship.
        the_system (sbs.SHPSYS | int | str, optional): The system to damage.
            If ``None``, a system is chosen at random. Defaults to None.

    Returns:
        bool: ``True`` if a node was damaged; ``False`` if no undamaged nodes
            remain or the ship has already exploded.
    """
    ship_id = to_id(id_or_obj)
    if has_role(ship_id, "exploded"):
        return False
    if the_system is None:
        the_system = convert_system_to_string(random.randrange(4))

    the_system = convert_system_to_string(the_system)
    hittable = to_list(grid_objects(ship_id) & role("__undamaged__") & role(the_system))
    if len(hittable) == 0:
        return False
    go_id = random.choice(hittable)
    # TODO: Maybe this should be inventory like the damcons
    damage_color = grid_get_grid_current_theme()["damage_colors"]["default"]

    grid_damage_grid_object(ship_id, go_id, damage_color)
    add_role(go_id, "__damaged__")
    grid_apply_system_damage(ship_id)
    return True


###################
def grid_damage_pos(id_or_obj, loc_x, loc_y):
    """Apply internal damage at a specific grid cell.

    If no grid object occupies the cell a hallway-fire marker is placed
    instead.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        loc_x (int): Grid column to damage.
        loc_y (int): Grid row to damage.
    """
    ship_id = to_id(id_or_obj)
    go_set_at_loc = grid_objects_at(ship_id, loc_x, loc_y)
    #
    # If empty hallway hit, Drop damage down 
    #
    if len(go_set_at_loc) == 0:
        grid_damage_hallway(ship_id, loc_x,loc_y)
        return




def grid_take_internal_damage_at(id_or_obj, source_point, system_hit=None, damage_amount=None):
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
        bool: ``True`` if the ship was destroyed by this damage.
    """
    SBS = FrameContext.context.sbs
    ship_id = to_id(id_or_obj)
    # Make sure you don't take further damage
    if has_role(ship_id, "exploded"): return
    # Host is no more 
    hm = SBS.get_hull_map(ship_id)
    if hm is None: return

    loc_x = 0
    loc_y = 0
    damage_radius = int(((hm.w+hm.h) / 2 / 2) + 2) # Average halved + 2

    loc = SBS.find_valid_grid_point_for_vector3(ship_id, source_point, damage_radius)
    # Nothing to do END
    if len(loc)== 0: return
    #
    # pick a random system 
    # this can get overridden by finding a grid object in the hit location
    #
    blob = to_blob(ship_id)

    loc_x = loc[0]
    loc_y = loc[1]
    # do print(f"{loc_x} {loc_y} {EVENT.source_point.x} {EVENT.source_point.y} {EVENT.source_point.z}")
    go_set_at_loc = grid_objects_at(ship_id, loc_x, loc_y)
    #
    # If empty hallway hit, Drop damage down 
    #
    damage_color = grid_get_grid_current_theme()["damage_colors"]["default"]
    if len(go_set_at_loc) == 0:

        grid_damage_hallway(ship_id, loc_x, loc_y, damage_color)
        return grid_apply_system_damage(ship_id)
#
    # there are things here
    #
    #
    # Try several times to apply damage
    # if damage is applied just do it once
    #
    num_retry = 3
    injured_dc = set()
    for retry in range(num_retry):
        already_damaged = False
        
        for go_id in go_set_at_loc:
            #
            # track hit lifeforms
            #
            if has_role(go_id, "marker"): continue
            if has_role(go_id, "tools"): continue
            if has_role(go_id, "rally_point"): continue
            if has_role(go_id, "lifeform"):
                injured_dc.add(go_id)
                # don't mark lifeforms as damaged
                continue

            if has_role(go_id, "__damaged__"):
                already_damaged = True
                continue

            # Skip anything the grid still lists but that is no longer usable. A
            # grid object can outlive its blob two ways: the host ship is destroyed
            # (the wrapper survives but every get/set raises), or the object was
            # deleted this tick and the hull map has not caught up. Internal damage
            # runs *while* ships are blowing up, so both are live cases here -
            # grid_valid_blob collapses them into one `is None` check, as the rest
            # of the grid layer already does.
            go = to_object(go_id)
            blob = grid_valid_blob(go_id)
            if blob is None:
                continue
            blob.set("icon_color", damage_color, 0)
            link(ship_id, "damage", go_id)
            add_role(go_id, "__damaged__")
            remove_role(go_id, "__undamaged__")
            # Damage supersedes wear, same as grid_damage_grid_object.
            remove_role(go_id, "__worn__")
            _grid_promote_maintenance_to_repair(go_id)
        #
        # I all damage was new, we are done
        #
        if not already_damaged: break
        
        #
        # otherwise
        # find closest undamaged thing, not hallways
        # Using it's x,y as the new place to try
        #
        a_go = next(iter(go_set_at_loc))
        undam = grid_closest(a_go, role("__undamaged__") & grid_objects(ship_id))
        #
        # Just need one item to get x,y
        #
        go_blob = grid_valid_blob(undam) if undam is not None else None
        if go_blob is not None:
            loc_x = int(go_blob.get("curx", 0))
            loc_y = int(go_blob.get("cury", 0))

            #do print(f"{loc_x} {loc_y}")
            go_set_at_loc = grid_objects_at(ship_id, loc_x, loc_y)


    for d in injured_dc:
        hp =  get_inventory_value(d, "HP", 0)
        hp -= 1
        set_inventory_value(d, "HP", hp)
        go = to_object(d)
        blob = grid_valid_blob(d)
        # Same guard as the damage loop above: an injured lifeform can lose its host
        # (or be deleted) between being collected and being processed here.
        if go is None or blob is None:
            continue
        dc_damage_color = get_inventory_value(d, "damage_color")
        dc_damage_color = damage_color if damage_color else damage_color

        blob.set("icon_color", dc_damage_color, 0)
        if hp <= 0:
            #@signal life_form_died data SHIP_id, LIFE_FORM_NAME
            signal_emit("life_form_died", {"SHIP_ID": ship_id, "LIFE_FORM_NAME": go.name})
            # Ship tab: a damcon death is the crew's own news, not mission traffic.
            comms_broadcast(ship_id, f"{go.name} has perished", dc_damage_color,
                            category="ship", severity="danger")
            grid_delete_object(go.host_id, d)
        else:
            comms_broadcast(ship_id, f"{go.name} has been hurt hp={hp}", "yellow",
                            category="ship", severity="warning")
            #@signal life_form_hp_changed data SHIP_id, LIFE_FORM_ID, HP
            signal_emit("life_form_hp_changed", {"SHIP_ID": ship_id, "LIFE_FORM_ID": d, "HP": hp})


    return grid_apply_system_damage(ship_id)


def grid_repair_system_damage(id_or_obj, the_system=None):
    """Repair a single damaged grid node for the specified system.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        the_system (sbs.SHPSYS | int | str, optional): The system to repair.
            If ``None``, a system is chosen at random. Defaults to None.

    Returns:
        bool: ``True`` if a node was repaired; ``False`` if no damaged nodes
            remain for that system.
    """
    ship_id = to_id(id_or_obj)
    
    if the_system is None:
        the_system = convert_system_to_string(random.randrange(4))

    the_system = convert_system_to_string(the_system)
    fixable = to_list(grid_objects(ship_id) & role("__damaged__") & role(the_system))
    if len(fixable) == 0:
        return False
    go_id = random.choice(fixable)
    grid_repair_grid_objects(ship_id, go_id)
    grid_apply_system_damage(ship_id)
    return True



def grid_repair_grid_objects(player_ship, id_or_set, who_repaired=None):
    """Repair one or more grid objects and update the ship's damage state.

    Hallway-fire markers are deleted; system nodes have their icon color
    restored and the system-damage count decremented. Recomputes damage
    coefficients if any system node was healed.

    Args:
        player_ship (Agent | int): The player ship agent ID or object.
        id_or_set (Agent | int | set[Agent | int]): Grid object(s) to repair.
        who_repaired (Agent | int, optional): The damcon-team agent that
            performed the repair (used to remove work-order links). Defaults
            to None.
    """
    SBS = FrameContext.context.sbs
    at_point = to_set(id_or_set)
    damcon_repairer = to_id(who_repaired)
    player_ship_id = to_id(player_ship)

    # Local import: work_orders imports THIS module for grid_node_state, so a
    # top-level import here would be a cycle.
    from .work_orders import work_order_cancel, work_order_cancel_all, work_order_is_satisfied

    something_healed = False
    for id in at_point:
        #
        # Remove work order, even if no longer damaged
        # 
        if damcon_repairer is not None:
            work_order_cancel(damcon_repairer, id)

        # Only deal with Damage
        if not has_role(id, "__damaged__"): continue 
        if has_role(id, "damcons"): continue
        go = to_object(id)
        if go is None: continue


        # Have to unlink this so it is no longer seen
        unlink(go.host_id, "damage", id)
        remove_role(id, "__damaged__")
        add_role(id, "__undamaged__")

        # The ORDER is done, not just this worker's part of it. Dropping only the
        # repairer's own link left a SECOND team walking to a room that was already
        # fixed: the role filter stopped them acting on it, silently, but the link
        # itself never went away.
        if work_order_is_satisfied(id):
            work_order_cancel_all(id)


        # If hallway damage delete
        # else restore color and repair system
        system_heal = None
        if has_role(id, "hallway"):
            grid_delete_object(go.host_id, id)
        #
        # This is a room, fix
        #
        else:
            # A damage-control team PATCHES; a dockyard RESTORES. `damcon_repairer`
            # is already the argument that tells the two apart - the brain passes the
            # team, while docking and grid_repair_system_damage pass nothing - so a
            # patched node comes back in service but WORN, and wants a maintenance
            # pass before it is fully itself again. That is where the whole
            # maintenance loop comes from: nothing invents work, damage does.
            #
            # grid_set_node_wear repaints through grid_node_apply_color, which is why
            # there is no icon_color write here any more.
            grid_set_node_wear(id, WEAR_AFTER_PATCH if damcon_repairer is not None
                               else WEAR_NOMINAL, player_ship_id)
            if has_role(id, "sensor"):
                system_heal = SBS.SHPSYS.SENSORS
            elif has_role(id, "weapon"):
                system_heal = SBS.SHPSYS.WEAPONS
            elif has_role(id, "engine"):
                system_heal = SBS.SHPSYS.ENGINES
            elif has_role(id, "shield"):
                system_heal = SBS.SHPSYS.SHIELDS
        #
        # 
        #
        if system_heal is not None:
            ship_blob = to_blob(player_ship_id)
            something_healed = True
        
            current = ship_blob.get('system_damage', system_heal)
            if current >0:
                ship_blob.set('system_damage', current-1 , system_heal)
            else:
                ship_blob.set('system_damage', 0 ,  system_heal)

    #
    # Update the damage coefficients if a system was healed
    # Label is in internal_damage, Expects DAMAGE_ORIGIN_ID
    #

    if something_healed:
        set_damage_coefficients(player_ship_id )
    
def grid_count_grid_data(ship_key, role, default=0):
    """Count the number of grid items that have a given role in the ship's JSON data.

    Args:
        ship_key (str): The ship art-ID key to look up in the grid data.
        role (str): Role name to match against each grid item's role list.
        default (int, optional): Value returned if the ship key is not found in
            the grid data. Defaults to 0.

    Returns:
        int: Number of grid items with the specified role.
    """
    grid_data = grid_get_grid_data()
    ship_data = grid_data.get(ship_key)
    if ship_data is None:
        return default
    
    internal_items = ship_data.get("grid_objects")
    if internal_items is None:
        return default
    count = 0
    for item in internal_items:
        role_set = set([x.strip() for x in item["roles"].split(',')])
        if role in role_set:
            count += 1
    
    return count



# --- node condition ----------------------------------------------------------
# A grid node has a CONDITION as well as a damage state. Damage is the two roles
# `__damaged__`/`__undamaged__` the engine and every existing query already use;
# condition is a wear value on top of that, and `__worn__` is its role. The two are
# deliberately orthogonal - a worn node keeps `__undamaged__`, so nothing that counts
# undamaged system nodes (the explode check, `system_damage[]`, every mission's own
# `role("__undamaged__")`) changes meaning because a node got tired.
#
# Wear runs 0.0 (perfect) to 1.0 (worn out). The DEFAULT is WEAR_NOMINAL, not 0.0:
# that is what makes the whole idea inert until something writes wear - an untouched
# node reads nominal and weighs exactly 1.0 - and it means "tuned" has to be earned
# rather than being the state everything spawns in.
WEAR_TUNED_MAX = 0.10       # <= this is TUNED
WEAR_NOMINAL = 0.25         # a fresh node, and what a DOCKYARD repair restores
WEAR_WORN_MIN = 0.60        # >= this is WORN
WEAR_AFTER_PATCH = 0.75     # a damcon patch: back in service, but worn

# How fast wear ARRIVES. A node travels WEAR_NOMINAL -> WEAR_WORN_MIN, i.e. 0.35, so
# every rate below reads as "0.35 / rate events to wear a node out". These are the
# numbers to argue about in playtest, not in code review - grid_set_wear_tuning moves
# them at runtime, and a mission can set its own in its map body.
WEAR_UPKEEP_RATE = 0.005          # per sim-minute, EVERY node   -> ~70 min
WEAR_PER_BEAM_HIT = 0.002         # per beam hit landed          -> ~175 hits
WEAR_PER_TUBE_SHOT = 0.01         # per torpedo launched         -> ~35 shots
WEAR_PER_SHIELD_HIT = 0.004       # per hit taken on that facing -> ~88 hits
WEAR_PER_IMPULSE_MINUTE = 0.004   # at full impulse              -> ~88 min
WEAR_PER_WARP_MINUTE = 0.02       # per warp factor over 1       -> ~18 min at warp 1

# Kept as this module's names for the theme fallbacks, which live with the theme.
GRID_WORN_COLOR_DEFAULT = GRID_WORN_COLOR
GRID_TUNED_COLOR_DEFAULT = GRID_TUNED_COLOR

# What each condition tier is WORTH. A worn node still works, just not as well; a
# tuned one is the reward for maintaining it, and is the only source of over-unity.
WEAR_WORN_FACTOR = 0.75
WEAR_TUNED_BONUS = 0.10
WEAR_COEFF_MAX = 1.0 + WEAR_TUNED_BONUS


def grid_node_wear(id_or_obj):
    """How worn a grid node is, 0.0 (perfect) to 1.0 (worn out).

    A node nothing has ever worn reads WEAR_NOMINAL, so callers never have to
    special-case "no wear recorded".

    Args:
        id_or_obj: The grid node (id or Agent).

    Returns:
        float: the node's wear.
    """
    return get_inventory_value(to_id(id_or_obj), "wear", WEAR_NOMINAL)


def grid_node_state(id_or_obj):
    """The node's condition as one word.

    Damage wins over wear - a broken node is "damaged" whatever its wear says,
    which is why grid_damage_grid_object clears `__worn__`.

    Args:
        id_or_obj: The grid node (id or Agent).

    Returns:
        str: "damaged", "worn", "tuned" or "nominal".
    """
    node_id = to_id(id_or_obj)
    if has_role(node_id, "__damaged__"):
        return "damaged"
    wear = grid_node_wear(node_id)
    if wear >= WEAR_WORN_MIN:
        return "worn"
    if wear <= WEAR_TUNED_MAX:
        return "tuned"
    return "nominal"

def grid_node_efficiency(id_or_obj):
    """What this node contributes to its system's effectiveness.

    damaged 0.0 | worn WEAR_WORN_FACTOR | nominal 1.0 | tuned 1.0 + WEAR_TUNED_BONUS.

    A node nothing has ever worn reads WEAR_NOMINAL and so weighs exactly 1.0 - which
    is what makes the whole idea inert until something writes wear, and why
    set_damage_coefficients produces numbers identical to the old undamaged/total
    fraction on a ship that has never worn anything.
    """
    state = grid_node_state(id_or_obj)
    if state == "damaged":
        return 0.0
    if state == "worn":
        return WEAR_WORN_FACTOR
    if state == "tuned":
        return 1.0 + WEAR_TUNED_BONUS
    return 1.0


def grid_node_apply_color(id_or_obj, theme_name=None):
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
        str | None: the color written, or None if there was no blob to write to.
    """
    node_id = to_id(id_or_obj)
    blob = to_blob(node_id)
    if blob is None:
        return None
    state = grid_node_state(node_id)
    if state == "nominal":
        color = get_inventory_value(node_id, "color", None) or "purple"
    else:
        # The node's own roles decide which shade of the tier it takes, the same way
        # its healthy color was chosen at spawn.
        agent = Agent.get(node_id)
        roles = ",".join(agent.get_roles()) if agent is not None else ""
        theme = grid_get_item_theme_data(roles, theme_name)
        if state == "damaged":
            color = get_inventory_value(node_id, "damage_color", None) or theme.damage_color
        elif state == "worn":
            color = theme.worn_color
        else:
            color = theme.tuned_color
    blob.set("icon_color", color, 0)
    return color


def grid_set_node_wear(id_or_obj, value, ship_id=None):
    """Set a node's wear, reconciling everything that follows from it.

    The ONLY writer. It clamps, stores, adds or removes ``__worn__``, repaints
    through grid_node_apply_color, and recomputes the ship's coefficients - but only
    when the ROLE actually flipped, so wear moving within a band costs one dict write
    and nothing else.

    ``__worn__`` never coexists with ``__damaged__``: damage supersedes wear, and a
    worn node keeps ``__undamaged__`` so nothing that counts undamaged system nodes
    changes meaning because a node got tired.

    Args:
        id_or_obj: the grid node.
        value (float): the new wear, clamped to 0.0 - 1.0.
        ship_id (optional): the host, for the coefficient recompute. Read from the
            node when not given.

    Returns:
        float: the wear actually stored.
    """
    node_id = to_id(id_or_obj)
    node = to_object(node_id)
    if node is None:
        return 0.0
    value = max(0.0, min(1.0, float(value)))
    set_inventory_value(node_id, "wear", value)

    was_worn = has_role(node_id, "__worn__")
    should_be_worn = value >= WEAR_WORN_MIN and not has_role(node_id, "__damaged__")
    if should_be_worn and not was_worn:
        add_role(node_id, "__worn__")
    elif was_worn and not should_be_worn:
        remove_role(node_id, "__worn__")

    grid_node_apply_color(node_id)

    # Only a tier change moves a coefficient, and this can run per node per minute.
    if was_worn != should_be_worn:
        host = ship_id if ship_id is not None else getattr(node, "host_id", None)
        if host is not None:
            set_damage_coefficients(host)
    return value


def grid_add_node_wear(id_or_obj, amount, ship_id=None):
    """Add to a node's wear. Negative restores it."""
    return grid_set_node_wear(id_or_obj, grid_node_wear(id_or_obj) + amount, ship_id)


def grid_wear_system(ship_id, sys_role, amount, count=1):
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
        int: how many nodes were worn.
    """
    pool = list(grid_objects(ship_id) & all_roles(sys_role) & role("__undamaged__"))
    if not pool:
        return 0
    count = max(1, count)
    random.shuffle(pool)
    for node_id in pool[:count]:
        grid_add_node_wear(node_id, amount, ship_id)
    return min(len(pool), count)


def grid_wear_upkeep(ship_id, amount=None):
    """Age every working node on a ship by one upkeep step.

    Args:
        ship_id: the ship.
        amount (float, optional): defaults to WEAR_UPKEEP_RATE.

    Returns:
        int: how many nodes were aged.
    """
    if amount is None:
        amount = WEAR_UPKEEP_RATE
    nodes = grid_objects(ship_id) & role("__undamaged__")
    for node_id in nodes:
        grid_add_node_wear(node_id, amount, ship_id)
    return len(nodes)


def grid_wear_travel(ship_id, throttle=None):
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
        str | None: which pool was worn - "warp", "impulse", or None when stopped.
    """
    if throttle is None:
        blob = to_blob(ship_id)
        throttle = 0 if blob is None else blob.get("playerThrottle", 0)
    throttle = throttle or 0
    if throttle > 1.0:
        grid_wear_system(ship_id, "warp", WEAR_PER_WARP_MINUTE * (throttle - 1.0))
        return "warp"
    if throttle > 0.0:
        grid_wear_system(ship_id, "impulse", WEAR_PER_IMPULSE_MINUTE * throttle)
        return "impulse"
    return None


def grid_wear_shield_hit(ship_id, face):
    """Wear the shield facing that took a hit.

    Args:
        ship_id: the ship that was hit.
        face (int): 0 forward, anything else aft - the same two pools
            set_damage_coefficients writes as shield_damage_coeff[0] and [1].

    Returns:
        int: how many nodes were worn.
    """
    pool = "shield,fwd" if face == 0 else "shield,aft"
    return grid_wear_system(ship_id, pool, WEAR_PER_SHIELD_HIT)


def grid_tune_grid_object(ship_id, node_id, who=None):
    """A node brought back to spec - what a maintenance order delivers.

    Wear to zero, ``__worn__`` off, drawn in the tuned color, coefficients
    recomputed, and the order closed for EVERY team on it rather than just whoever
    happened to be standing there.

    Args:
        ship_id: the host ship.
        node_id: the node to tune.
        who (optional): the team that did it, carried on the signal.

    Returns:
        bool: whether anything was tuned.
    """
    from .work_orders import work_order_cancel_all
    if to_object(node_id) is None:
        return False
    grid_set_node_wear(node_id, 0.0, ship_id)
    work_order_cancel_all(node_id)
    set_damage_coefficients(ship_id)
    signal_emit("grid_node_tuned", {"SHIP_ID": to_id(ship_id),
                                    "NODE_ID": to_id(node_id),
                                    "WHO_ID": to_id(who)})
    return True


def grid_set_wear_tuning(worn_factor=None, tuned_bonus=None, worn_min=None,
                         tuned_max=None, upkeep_rate=None, **rates):
    """Retune the wear model for a mission that wants different numbers.

    ``grid_set_wear_tuning(tuned_bonus=0.0)`` gives strict parity with the old
    coefficients even on a ship with tuned nodes - the escape hatch for a mission
    that wants the maintenance loop without any over-unity.

    Any arrival RATE can be passed by its short name as a keyword, so a mission tunes
    the feel without touching the library::

        grid_set_wear_tuning(beam_hit=0.0005, warp_minute=0.05)
        grid_set_wear_tuning(upkeep_rate=0)     # no time-based upkeep at all

    An unknown rate name is a warning, not a silent no-op - a typo here would look
    exactly like "the dial does nothing".
    """
    global WEAR_WORN_FACTOR, WEAR_TUNED_BONUS, WEAR_COEFF_MAX
    global WEAR_WORN_MIN, WEAR_TUNED_MAX, WEAR_UPKEEP_RATE
    global WEAR_PER_BEAM_HIT, WEAR_PER_TUBE_SHOT, WEAR_PER_SHIELD_HIT
    global WEAR_PER_IMPULSE_MINUTE, WEAR_PER_WARP_MINUTE
    if worn_factor is not None:
        WEAR_WORN_FACTOR = worn_factor
    if tuned_bonus is not None:
        WEAR_TUNED_BONUS = tuned_bonus
        WEAR_COEFF_MAX = 1.0 + tuned_bonus
    if worn_min is not None:
        WEAR_WORN_MIN = worn_min
    if tuned_max is not None:
        WEAR_TUNED_MAX = tuned_max
    if upkeep_rate is not None:
        WEAR_UPKEEP_RATE = upkeep_rate
    for _name, _value in rates.items():
        _key = _name.upper() if _name.startswith("WEAR_") else "WEAR_PER_" + _name.upper()
        if _key not in globals():
            log(f"grid_set_wear_tuning: no rate named {_name!r}", "grid", "warning")
            continue
        globals()[_key] = _value


# --- system indicators -------------------------------------------------------
# What each of a ship's system pools is worth right now, as data. The cockpit HUD
# has had this for a while (LM hangar.py) as a two-state ok/hurt row; Engineering
# needs the same answer with the wear tiers in it, and two copies of "which nodes
# count as weapons" is one too many. This is the promoted model - the GUI half
# (drawing the glyphs, recoloring them) stays with whoever draws them.
#
# Nothing here writes. An indicator that could disagree with the grid it is
# reporting on would be worse than no indicator, so this reads the same roles the
# grid draws from and the same theme colors it draws in.
#
# Icons are asked for BY NAME (procedural/gui/icon_sheet), so a mission that
# re-skins the sheet moves these with it and no caller carries a bare sheet index.
GRID_SYSTEM_ICONS = (
    ("weapon", "turret"),
    ("engine", "turbine"),
    ("sensor", "radar"),
    ("shield", "shield"),
)

# Where an indicator falls back to when the theme has nothing to say. `system` is
# the shipped cosmos theme's healthy color; the other three are the tiers.
GRID_SYSTEM_OK_COLOR = "springgreen"
GRID_SYSTEM_HURT_COLOR = "Crimson"


def grid_system_states(id_or_obj):
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
        ``color`` to draw it in.
    """
    out = []
    ship_id = to_id(id_or_obj)
    if not ship_id:
        return out
    nodes = grid_objects(ship_id)
    if not nodes:
        return out
    theme = grid_get_grid_current_theme()
    ok_color = (theme.get("colors") or {}).get("system", GRID_SYSTEM_OK_COLOR)
    hurt_color = (theme.get("damage_colors") or {}).get("default", GRID_SYSTEM_HURT_COLOR)
    worn_color = (theme.get("worn_colors") or {}).get("default", GRID_WORN_COLOR_DEFAULT)
    tuned_color = (theme.get("tuned_colors") or {}).get("default", GRID_TUNED_COLOR_DEFAULT)
    damaged = nodes & role("__damaged__")
    worn_nodes = nodes & role("__worn__")
    for role_name, icon_name in GRID_SYSTEM_ICONS:
        pool = nodes & role(role_name)
        total = len(pool)
        if total == 0:
            continue
        hurt = len(pool & damaged)
        worn = len(pool & worn_nodes)
        tuned = sum(1 for i in pool if grid_node_state(i) == "tuned")
        # Worst-first: a pool with anything broken reads broken, whatever else is
        # tuned in it. "tuned" is only claimed when the WHOLE pool is.
        if hurt:
            state, color = "hurt", hurt_color
        elif worn:
            state, color = "worn", worn_color
        elif tuned == total:
            state, color = "tuned", tuned_color
        else:
            state, color = "ok", ok_color
        out.append({"role": role_name, "icon": icon_name, "hurt": hurt,
                    "worn": worn, "tuned": tuned, "total": total,
                    "state": state, "color": color})
    return out


def grid_system_signature(id_or_obj):
    """A value that CHANGES whenever an indicator row should be redrawn.

    For ``on change grid_system_signature(ship_id):`` - the polling form, which is
    what a console layout can actually use. A ``//damage/internal`` route fires on
    the SERVER and would not repaint a client's panel; ``on change`` re-evaluates on
    the console itself and so cannot miss a hit.

    Args:
        id_or_obj: The ship (id, Agent or SpaceObject).

    Returns:
        str: e.g. ``"weapon1/0/0/6,engine0/1/0/4"`` - hurt/worn/tuned/total per pool.
    """
    return ",".join(f"{s['role']}{s['hurt']}/{s['worn']}/{s['tuned']}/{s['total']}"
                    for s in grid_system_states(id_or_obj))
