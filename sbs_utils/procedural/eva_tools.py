"""What a suit can DO to the ruin it is flying through: haul, and cut.

Nav answers "where can I go". This answers "and what is in reach", with the same shape -
a list, nearest first, and the selection is the commitment. No reticle, because there is
no aiming: a suit is being flown by destination and a boarder's hands are busy.

TWO VERBS, AND THEY ARE NOT THE SAME KIND OF THING
--------------------------------------------------
* **TETHER is a real engine mechanism.** `grav_tether` wraps `sim.AddTractorConnection`,
  and nothing in it requires the source to be a player ship - so a suit can tow. Reeling a
  find in and letting the existing pickup path collect it is the whole of "take it with
  you".
* **BEAM is scripted, and it has to be.** There is NO engine call that fires a beam or
  subtracts hull or shield from a space object: the whole beam surface of the API is
  `set_beam_damages` (global tuning), `get_shield_hit_index` (which facing a hypothetical
  shot would land on) and `launch_torpedo`. The only way to make something shoot is to
  hand the engine a `target_id` and let its beam AI do it, which needs a hull whose beams
  are declared - the `turret.py` model.

  So a suit's beam does not shoot anything. It CUTS - it works on a barrier until the
  barrier opens - and that is a state change we own outright, deterministic, and testable
  without a bridge. It is also the more interesting verb: a shut way with a long way round
  is a decision, where an NPC with a health bar is arithmetic.

**NPC combat inside a relic is deliberately not here.** When it comes it goes through an
invisible `behav_npcship` escort welded to the suit (`turret_make` / `turret_engage`),
because that is the only path anybody has measured firing. Offering a FIRE button that
quietly does nothing would be worse than not offering one.

EVERY OUTCOME IS REPORTED, INCLUDING THE REFUSALS. `eva_worked` carries what happened and
why - the pattern `boarding_fire` established, and for the same reason: a verb that fails
silently is indistinguishable from a broken screen.
"""
import math

from .inventory import get_inventory_value, set_inventory_value
from .query import to_id, to_object
from .roles import any_role, role

#: How far a suit can reach. A person's working distance, not a cruiser's weapon range -
#: the point is that you fly TO a thing and then work on it.
EVA_REACH = 600.0

#: How long a cut takes, in seconds. Long enough that it is a thing the crew waits out
#: together and short enough that it is not a punishment.
CUT_SECONDS = 12.0

#: How fast a tether reels a find in. The library default is ~375 u/s, which is a cruiser
#: hauling a wreck; a boarder retrieving something wants to watch it come.
REEL_RATE = 60.0

#: How far a haul has to shift a blockage before the way counts as open.
HAUL_CLEAR = 220.0

#: Verbs.
VERB_TETHER = "tether"
VERB_BEAM = "beam"

#: Roles worth offering as a target. Markers are NAVIGATION - a post measuring where the
#: crew has been - so they are deliberately not on this list, however much they look like
#: things in the world.
HAUL_ROLES = "item,upgrade,relic_piece,salvage"

#: Per-console state.
KEY_WORK = "EVA_WORK"        # {"target","verb","until","kind"} while something is running
KEY_ARMED = "EVA_ARMED"      # which verb the console is holding

_TICK_KEY = "__EVA_TOOLS_TICK__"


def _pos(thing):
    obj = to_object(thing)
    if obj is None:
        return None
    p = getattr(obj, "pos", None)
    return None if p is None else (p.x, p.y, p.z)


def _dist(a, b):
    if a is None or b is None:
        return float("inf")
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def eva_reach(client_id=None):
    """How far this console can reach. One number, for now - a hook for a mission that
    wants a longer arm on a better suit."""
    return EVA_REACH


# --- what is in reach -------------------------------------------------------------------

def eva_targets(client_id, reach=None):
    """``[(key, display, kind, distance, verbs)]`` - what this suit can work on.

    Nearest first, the same as `eva_points`, because the same hand is picking from it.

    `kind` is `"barrier"` or `"haul"`. `verbs` is what may be done to it: a barrier says
    so itself (`Clear with:`), and anything haulable takes a tether.
    """
    from .amd_relics import relic_barriers, relic_rails_ensure
    from .eva import eva_my_relic, eva_my_suit, eva_my_volume
    from .rails import rail_barriers
    suit = eva_my_suit(client_id)
    key = eva_my_relic(client_id)
    if not suit or not key:
        return []
    here = _pos(suit)
    if here is None:
        return []
    reach = float(reach if reach is not None else eva_reach(client_id))
    vol = relic_rails_ensure(key, eva_my_volume(client_id)) or eva_my_volume(client_id)
    out = []

    authored = relic_barriers(key)
    for bkey, bar in rail_barriers(vol, shut_only=True):
        gap = _dist(here, bar["pos"])
        if gap > reach:
            continue
        spec = authored.get(bkey) or []
        verbs = tuple(spec[5]) if len(spec) > 5 and spec[5] else (VERB_BEAM,)
        out.append((bkey, bar.get("display") or bkey, "barrier", gap, verbs))

    # THE SUIT ITSELF IS IN `role()` FOR SOME OF THESE. A suit is a player hull with
    # `__player__` removed, so it is a space object like any other and a party of six is
    # five more things in reach of each other. Exclude every suit, not just this one.
    from .eva import SUIT_ROLE
    suits = set(role(SUIT_ROLE))
    for obj_id in any_role(HAUL_ROLES):
        if obj_id in suits:
            continue
        where = _pos(obj_id)
        gap = _dist(here, where)
        if gap > reach:
            continue
        obj = to_object(obj_id)
        name = getattr(obj, "name", None) or "salvage"
        out.append((obj_id, str(name), "haul", gap, (VERB_TETHER,)))

    out.sort(key=lambda row: row[3])
    return out


# --- the console's own selection --------------------------------------------------------
#
# A suit is a player ship, so it HAS the four console selections like any other - they are
# ordinary blob keys (`weapon_target_UID` and friends) that `query.set_weapons_selection`
# writes. Two things follow, and both are what a bridge already expects:
#
#   * the WEAPONS selection is the beam lock. The engine fires a hull's beams at whatever
#     that key names, which is how LegendaryMissions' manual-beams panel works, so setting
#     it is how a suit's beam fires at all.
#   * a selection the crew made elsewhere - a click on the 2D view - should BE the target,
#     rather than the app keeping a private idea of what is aimed at.


def eva_target_object(client_id, target):
    """The SPACE OBJECT for a target key, or None.

    A haul target is already an object id. A barrier is a key naming a sphere in the rail
    web - and a sphere is not something a beam can hit, which is why it now carries an
    object standing in for it.
    """
    from .amd_relics import relic_rails_ensure
    from .eva import eva_my_relic, eva_my_volume
    from .rails import rail_barrier_object
    if target is None:
        return None
    key = eva_my_relic(client_id)
    if key:
        vol = relic_rails_ensure(key, eva_my_volume(client_id)) or eva_my_volume(client_id)
        oid = rail_barrier_object(vol, target)
        if oid is not None:
            return oid
    obj = to_object(target)
    return None if obj is None else to_id(obj)


def eva_aim(client_id, target):
    """Point the suit at a target: lock its weapons and swing its 2D view to match.

    THE LOCK IS THE POINT. A hull's beams fire at whatever `weapon_target_UID` names, so
    without this the suit's beam - and `tsn_shuttle` has had one all along - never fires
    at anything. The 2D focus is so the console agrees with the handheld rather than
    showing a view the crew has to re-aim by hand.
    """
    from .eva import eva_my_suit
    from .query import set_weapons_selection
    suit = eva_my_suit(client_id)
    oid = eva_target_object(client_id, target)
    if not suit or oid is None:
        return False
    set_weapons_selection(suit, oid)
    try:
        from .science import science_set_2dview_focus
        science_set_2dview_focus(client_id, oid)
    except Exception:                                    # noqa: BLE001
        pass                                             # a view is decoration; the lock is not
    return True


def eva_aimed(client_id):
    """What this suit's weapons are locked on, or None."""
    from .eva import eva_my_suit
    from .query import get_weapons_selection
    suit = eva_my_suit(client_id)
    if not suit:
        return None
    return (get_weapons_selection(suit) or None)


def eva_selected_target(client_id):
    """The reach target matching the console's WEAPONS selection, or None.

    What makes a click on the 2D view and a row in the app the same act: whatever the
    crew selected, if it is something this suit can work on, is the target.
    """
    aimed = eva_aimed(client_id)
    if not aimed:
        return None
    for key, _display, _kind, _gap, _verbs in eva_targets(client_id):
        if eva_target_object(client_id, key) == aimed:
            return key
    return None


def eva_target_verbs(client_id, target):
    """What may be done to one target, or `()` if it is not in reach."""
    for key, _display, _kind, _gap, verbs in eva_targets(client_id):
        if key == target or str(key) == str(target):
            return verbs
    return ()


# --- arming -----------------------------------------------------------------------------

def eva_arm(client_id, verb=VERB_BEAM):
    """Hold a verb ready. Two decisions on purpose - choose, then use."""
    if verb not in (VERB_BEAM, VERB_TETHER):
        return False
    set_inventory_value(client_id, KEY_ARMED, verb)
    return True


def eva_disarm(client_id):
    """Put it away."""
    set_inventory_value(client_id, KEY_ARMED, None)
    return True


def eva_armed(client_id):
    """Which verb this console is holding, or None."""
    return get_inventory_value(client_id, KEY_ARMED, None)


# --- doing it ---------------------------------------------------------------------------

def _report(client_id, target, verb, result, detail=None):
    from .signal import signal_emit
    from .eva import eva_my_relic, eva_my_suit
    signal_emit("eva_worked", {
        "EVA_CLIENT": client_id, "EVA_SUIT": eva_my_suit(client_id),
        "EVA_RELIC": eva_my_relic(client_id), "EVA_TARGET": target,
        "EVA_VERB": verb, "EVA_RESULT": result, "EVA_DETAIL": detail})
    return result == "ok"


def eva_use(client_id, target, verb=None):
    """Use the held verb on a target. The one entry point the app calls.

    Returns True only when something actually started. **Every other outcome is reported
    too**, through `eva_worked` with a reason - a verb that fails silently is
    indistinguishable from a broken screen, and that has been reported from a bridge on
    the other body model already.
    """
    from .eva import eva_my_suit
    verb = verb or eva_armed(client_id) or VERB_BEAM
    suit = eva_my_suit(client_id)
    if not suit:
        return _report(client_id, target, verb, "no suit")
    rows = [r for r in eva_targets(client_id)
            if r[0] == target or str(r[0]) == str(target)]
    if not rows:
        return _report(client_id, target, verb, "out of reach")
    _key, display, kind, gap, verbs = rows[0]
    if verb not in verbs:
        return _report(client_id, target, verb, "wrong tool", display)
    if get_inventory_value(client_id, KEY_WORK, None):
        return _report(client_id, target, verb, "already working", display)
    # LOCK FIRST. Working on a thing and having the weapons pointed at it are the same
    # intention, and a beam that has to be aimed separately from the app that started it
    # is two controls for one act.
    eva_aim(client_id, target)
    if kind == "haul":
        return _eva_haul(client_id, target, display)
    return _eva_work(client_id, target, verb, display)


def _eva_haul(client_id, target, display):
    """Reel a find in and let the existing pickup path collect it.

    THE MASS RULE IS THE TRAP HERE. `grav_tether` silently REVERSES the engine pair when
    the target is twice the source's mass or more - the big thing pulls the small one -
    and a suit is the smallest thing in any relic. Left alone, a boarder tethering a
    cargo pod gets reeled into the pod. So the ratio is checked BEFORE the attach and a
    refusal is reported by name, rather than the crew watching a suit fly into the
    scenery with no explanation.
    """
    from .eva import eva_my_suit
    from .grav_tether import (MASS_REVERSE_RATIO, grav_tether_mass_ratio,
                              grav_tether_reel)
    suit = eva_my_suit(client_id)
    try:
        ratio = grav_tether_mass_ratio(suit, target)
    except Exception:
        ratio = 1.0
    if ratio >= MASS_REVERSE_RATIO:
        return _report(client_id, target, VERB_TETHER, "too heavy", display)
    con = grav_tether_reel(suit, target, rate=REEL_RATE)
    if con is None:
        # The library refused it - out of its own range, an anchor role, moving too fast.
        # It has already emitted its own signal saying which; this says the press landed.
        return _report(client_id, target, VERB_TETHER, "refused", display)
    # IT IS ON YOUR HOOK, SO IT IS NOT A PLACE ANY MORE. A find that joined the web when
    # it was placed (`rail_attach`) is somewhere the crew can be SENT; once it is under
    # tow it is coming with them, and leaving it on the destination list offers a course
    # to a thing that is following you. The NODE goes; the object is untouched.
    _eva_unlist(client_id, target)
    eva_tools_watch()
    return _report(client_id, target, VERB_TETHER, "ok", display)


def _eva_unlist(client_id, target):
    """Take a hauled find off the relic's destination list. Never raises."""
    from .amd_relics import relic_rails_ensure
    from .eva import eva_my_relic, eva_my_volume
    from .rails import rail_detach
    key = eva_my_relic(client_id)
    if not key:
        return False
    try:
        vol = relic_rails_ensure(key, eva_my_volume(client_id)) or eva_my_volume(client_id)
        # `relic_part` IS the node key. `_relic_mark_placed` stamps it on everything a
        # relic puts in the world, precisely so a thing can be traced back to the spot it
        # came from - no guessing from names or positions.
        part = get_inventory_value(to_id(target), "relic_part", None)
        if part:
            return bool(rail_detach(vol, part))
    except Exception as e:                                # noqa: BLE001
        from .execution import log
        log(f"could not take '{target}' off the destination list: {e}", "eva", "warning")
    return False


def _eva_work(client_id, target, verb, display):
    """Start a timed job on a barrier - a cut, or a haul on the blockage itself."""
    from ..helpers import FrameContext
    now = FrameContext.sim_seconds or 0.0
    set_inventory_value(client_id, KEY_WORK, {
        "target": target, "verb": verb, "kind": "barrier",
        "until": now + CUT_SECONDS, "display": display})
    eva_tools_watch()
    return _report(client_id, target, verb, "ok", display)


def eva_working(client_id):
    """``(target, verb, seconds_left, display)`` while a job runs, else
    ``(None, None, 0.0, None)``."""
    from ..helpers import FrameContext
    work = get_inventory_value(client_id, KEY_WORK, None)
    if not work:
        return (None, None, 0.0, None)
    left = max(0.0, float(work["until"]) - (FrameContext.sim_seconds or 0.0))
    return (work["target"], work["verb"], left, work.get("display"))


def eva_abort(client_id):
    """Stop whatever this console had running."""
    work = get_inventory_value(client_id, KEY_WORK, None)
    set_inventory_value(client_id, KEY_WORK, None)
    if work:
        _report(client_id, work["target"], work["verb"], "stopped",
                work.get("display"))
    return bool(work)


def eva_tools_tick(t=None):
    """Finish the jobs that are done. ONE shared pass, like the autopilot and the camera."""
    from ..helpers import FrameContext
    from .amd_relics import relic_open_barrier
    from .eva import eva_drivers, eva_my_relic
    now = FrameContext.sim_seconds or 0.0
    for cid in eva_drivers():
        work = get_inventory_value(cid, KEY_WORK, None)
        if not work or now < float(work["until"]):
            continue
        set_inventory_value(cid, KEY_WORK, None)
        key = eva_my_relic(cid)
        opened = relic_open_barrier(key, work["target"]) if key else False
        _report(cid, work["target"], work["verb"],
                "opened" if opened else "no effect", work.get("display"))
    return True


def eva_tools_watch(seconds=0.25):
    """Start the jobs pass. Idempotent - asking twice watches once."""
    from ..agent import Agent
    from ..tickdispatcher import TickDispatcher
    task = Agent.SHARED.get_inventory_value(_TICK_KEY, None)
    if task is not None:
        return task
    task = TickDispatcher.do_interval(eva_tools_tick, seconds)
    Agent.SHARED.set_inventory_value(_TICK_KEY, task)
    return task


def eva_tools_unwatch():
    """Stop the jobs pass."""
    from ..agent import Agent
    task = Agent.SHARED.get_inventory_value(_TICK_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:
            pass
    Agent.SHARED.set_inventory_value(_TICK_KEY, None)


def eva_tools_working():
    """Reset-ledger probe: how many consoles have a job running. Must NOT create anything
    by asking."""
    from .eva import eva_drivers
    return sum(1 for cid in eva_drivers()
               if get_inventory_value(cid, KEY_WORK, None))


def eva_tools_clear(client_id=None):
    """Put the tools away - one console's, or every one's."""
    from .eva import eva_drivers
    for cid in ([client_id] if client_id is not None else eva_drivers()):
        set_inventory_value(cid, KEY_WORK, None)
        set_inventory_value(cid, KEY_ARMED, None)
    if client_id is None:
        eva_tools_unwatch()
    return True
