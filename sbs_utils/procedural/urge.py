"""Urges - what an actor keeps asking for, said out loud.

An **urge** is a recurring want held by any agent (a lifeform, a station, a side): a
condition, a cooldown, a pool of authored lines, and optionally an ``Action:`` block. One
shared ticker walks every agent that has urges, picks at most one, and says it.

    ## [DS1 calls for resupply](ds1_calling)
    ---
    Urge
    Actor: DS1
    Whenever: quest ds1_resupply active
    Every: 5m
    ---
    % DS1 requests a resupply run when someone has the tonnage.
    % DS1 is below reserve. We need that shipment.

**An urge carries no stakes of its own.** The consequence belongs to the quest it watches
(`Fails when: after 30m`, `Penalty:`), so there is one deadline and one place to tune, and
deleting an urge costs the drama but not the mechanics. See URGE_PLAN.md.

**Not a brain.** A behavior tree re-decides continuously because the world moved; an
urge's world changes on clocks and events. A brain node spawns a MAST task per node per
pass; an urge evaluates a condition. Grid lifeforms (damcons) keep their brains - they
have position and paths, and are correctly a tree.

**Not a goal selector.** ``Weight:`` arbitrates one actor's OWN urges - the same
fixed-priority fallback every brain root already does. It never arbitrates between two
actors; that is the contest ``NPC_MOTIVATION_PLAN.md`` s8 surveyed and rejected.
"""
import random

from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher, RollingSlicer
from sbs_utils.procedural.inventory import (get_inventory_value, set_inventory_value,
                                            has_inventory)
from sbs_utils.procedural.query import to_object, to_id, to_object_list
from sbs_utils.agent import Agent


# A full pass over every actor takes about this many sim seconds. Minute-scale wants, so
# a slow walk is the point - brains run a 3s pass and cost far more per visit.
URGE_PASS_SECONDS = 30

_urge_slicer = RollingSlicer()
__urge_tick_task = None

# phrase -> {"fn", "operand"}; fn(actor_id, operand) -> bool
_CONDITIONS = {}


def _urge_log(message, level="warning"):
    """Never raise out of the ticker - a bad line must not stop every other actor."""
    try:
        from .execution import log
        log(message, "urge", level)
    except Exception:
        pass


def _norm(text):
    return " ".join(str(text).strip().lower().split())


# --- conditions ---------------------------------------------------------------
def urge_register_condition(phrase, fn, operand="required", domain=None):
    """Declare a ``Whenever:`` phrase.

    ``fn(actor_id, operand)`` returns truthy when the urge is eligible. A fixed
    vocabulary plus this registry, rather than a bare python expression: an expression is
    powerful and untypeable by the linter, and the whole point of the AMD layer is that
    the tooling can check what an author wrote. Same contract as
    ``amd_action_register`` - re-registering a phrase with a different function raises,
    re-registering the identical one is a no-op so reloading is safe.
    """
    key = _norm(phrase)
    if not key:
        raise ValueError("an urge condition needs a phrase")
    prior = _CONDITIONS.get(key)
    if prior is not None and prior["fn"] is not fn:
        who = f" (from {domain})" if domain else ""
        raise ValueError(f"urge condition {phrase!r}{who} is already registered by "
                         f"something else")
    _CONDITIONS[key] = {"fn": fn, "operand": operand}
    return key


def urge_conditions():
    """Every registered phrase, longest first - the order the parser matches in."""
    return sorted(_CONDITIONS, key=lambda p: (-len(p.split()), p))


def urge_clear_conditions():
    """Test-only: drop every registered condition (then re-install the built-ins)."""
    _CONDITIONS.clear()


def urge_condition_eval(actor_id, text):
    """Evaluate a ``Whenever:`` / ``Until:`` line. Unknown phrasing is FALSE and logged -
    an urge nobody can trigger is a bug, and a silently-true one would talk forever.

    A leading ``not`` negates, so the vocabulary does not need a second phrase for every
    inverse.
    """
    line = _norm(text)
    if not line:
        return False
    if line.startswith("not "):
        return not urge_condition_eval(actor_id, line[4:])
    for phrase in urge_conditions():
        if line == phrase:
            operand = ""
        elif line.startswith(phrase + " "):
            operand = line[len(phrase) + 1:].strip()
        else:
            continue
        spec = _CONDITIONS[phrase]
        if spec["operand"] == "required" and not operand:
            _urge_log(f"{phrase!r} needs something after it: {text!r}")
            return False
        try:
            return bool(spec["fn"](actor_id, operand))
        except Exception as e:
            _urge_log(f"condition {text!r} failed: {e}")
            return False
    _urge_log(f"no urge condition in {text!r} - known: {', '.join(urge_conditions())}")
    return False


def _cond_always(actor_id, operand):
    """`always` - eligible whenever the cooldown allows. The heartbeat form."""
    return True


def _cond_quest(actor_id, operand):
    """`quest <id> <state>` - true while ANY holder has that quest in that state.

    Any holder, not the actor's own: the diplomat's urge watches the delivery quest the
    PLAYER accepted, while a station's urge watches one it holds itself. Making the
    author say which would be a distinction with no payoff - a quest id is unique.
    """
    from sbs_utils.procedural.quest import quest_get_state, QuestState
    parts = operand.split()
    if len(parts) < 2:
        _urge_log(f"'quest' reads 'quest <id> <state>', got {operand!r}")
        return False
    qid, want = " ".join(parts[:-1]), parts[-1]
    state = getattr(QuestState, want.upper(), None)
    if state is None:
        _urge_log(f"{want!r} is not a quest state: idle/active/complete/failed/secret")
        return False
    from sbs_utils.procedural.quest_driver import _quest_holders
    for holder in _quest_holders():
        if int(quest_get_state(holder, qid) or 0) == int(state):
            return True
    return False


def _cond_has_role(actor_id, operand):
    """`has role <role>` - the actor carries a role. The escape hatch for mission state
    that is already expressed as a role, which most of it is."""
    from sbs_utils.procedural.roles import has_role
    return has_role(actor_id, operand)


def _install_conditions():
    urge_register_condition("always", _cond_always, operand="none", domain="core")
    urge_register_condition("quest", _cond_quest, domain="core")
    urge_register_condition("has role", _cond_has_role, domain="core")


_install_conditions()


# --- the record ---------------------------------------------------------------
def urge_record(key=None, whenever="always", every=60, until=None, weight=0,
                pool=None, action=None, actor=None, stages=None, escalates=None):
    """One urge, as plain data. ``every`` is seconds; ``pool`` is the flat line list.

    ``stages`` is the optional ``{1: [...], 2: [...]}`` map built from ``%`` markers, and
    ``escalates`` is ``"deadline"`` | ``"firing"`` | None. With neither, an urge behaves
    exactly as it did before escalation existed.
    """
    return {"key": key, "whenever": whenever, "every": float(every or 0),
            "until": until, "weight": int(weight or 0), "pool": list(pool or []),
            "action": action, "actor": actor,
            "stages": dict(stages) if stages else None, "escalates": escalates}


def urge_add(agents, record):
    """Give one urge to one or more agents. Idempotent per (agent, urge key): re-running
    a section does not give an actor the same want twice."""
    from sbs_utils.procedural.query import to_id_list
    urge_schedule()
    for agent_id in to_id_list(agents):
        states = get_inventory_value(agent_id, "__URGES__", None)
        if states is None:
            states = []
            set_inventory_value(agent_id, "__URGES__", states)
        key = record.get("key")
        if key is not None and any(s["rec"].get("key") == key for s in states):
            continue
        states.append({"rec": record, "last": None, "stage": 0, "retired": False})


def urge_clear(agents):
    """Drop every urge from one or more agents (they stop being visited)."""
    from sbs_utils.procedural.query import to_id_list
    for agent_id in to_id_list(agents):
        set_inventory_value(agent_id, "__URGES__", None)


# --- selection ----------------------------------------------------------------
# The speech budget. Not an optimization - it is what decides whether autonomous speech
# is pleasant or unbearable, so it is a first-class part of the feature.
#
#   per-urge   `Every:`   authored     this specific thing should not repeat
#   per-actor  FLOOR      45s          one actor should not monologue across its urges
#   global     FLOOR      20s          five actors should not pile up after a jump
#
# A `Weight: 90`+ urge bypasses the GLOBAL floor only: an actor leaving forever outranks
# politeness towards other speakers, but not its own self-restraint - back-to-back lines
# from one mouth read as a bug no matter how urgent they are.
URGE_ACTOR_FLOOR = 45
URGE_GLOBAL_FLOOR = 20
URGE_URGENT_WEIGHT = 90

_last_actor_spoke = {}          # actor_id -> sim seconds


def urge_budget_allows(actor_id, state, now=None):
    """Whether this actor may speak right now.

    A refusal here must NOT stamp the urge's cooldown - the caller retries next pass, so
    a floor never costs an urge its turn. (A speech FAILURE is the opposite case and does
    stamp; see ``urge_run_one``.)
    """
    if now is None:
        now = FrameContext.sim_seconds
    mine = _last_actor_spoke.get(actor_id)
    if mine is not None and (now - mine) < URGE_ACTOR_FLOOR:
        return False
    if int(state["rec"].get("weight", 0)) >= URGE_URGENT_WEIGHT:
        return True
    from sbs_utils.procedural.announce import announce_last_traffic
    last = announce_last_traffic()
    return last is None or (now - last) >= URGE_GLOBAL_FLOOR


def urge_note_spoke(actor_id, now=None):
    """Record that this actor just spoke - feeding both floors.

    The global clock lives in ``announce`` because an urge and a mission announcement are
    the same thing from the bridge's side: an unprompted voice.
    """
    from sbs_utils.procedural.announce import announce_note_traffic
    if now is None:
        now = FrameContext.sim_seconds
    _last_actor_spoke[actor_id] = now
    announce_note_traffic(now)


def urge_budget_reset():
    """Drop the per-actor speech clocks (called by reset_mission_state)."""
    _last_actor_spoke.clear()


def urge_pick(actor_id, now=None):
    """The urge this actor should act on now, or None.

    Retires anything whose ``Until:`` is true, skips anything still cooling, evaluates
    the rest, and takes the highest ``Weight:`` (ties at random). Pure apart from the
    retire stamp, so it is testable without a tick.
    """
    states = get_inventory_value(actor_id, "__URGES__", None)
    if not states:
        return None
    if now is None:
        now = FrameContext.sim_seconds
    eligible = []
    for st in states:
        if st.get("retired"):
            continue
        rec = st["rec"]
        until = rec.get("until")
        if until and urge_condition_eval(actor_id, until):
            st["retired"] = True        # permanent - not merely cooled down
            continue
        last = st.get("last")
        if last is not None and (now - last) < rec.get("every", 0):
            continue
        if not urge_condition_eval(actor_id, rec.get("whenever") or "always"):
            continue
        eligible.append(st)
    if not eligible:
        return None
    top = max(s["rec"].get("weight", 0) for s in eligible)
    return random.choice([s for s in eligible if s["rec"].get("weight", 0) == top])


_QUEST_WHENEVER = None      # lazily compiled; `quest <id> <state>`


def urge_bound_quest(rec):
    """The quest id this urge watches, read out of its ``Whenever:``, or None.

    No separate field: the bound quest IS the one the urge is conditional on, and a
    second field would be one more thing to keep in agreement with the first.
    """
    line = _norm(rec.get("whenever") or "")
    if line.startswith("not "):
        line = line[4:]
    if not line.startswith("quest "):
        return None
    parts = line.split()
    return " ".join(parts[1:-1]) if len(parts) >= 3 else None


def urge_deadline_fraction(rec):
    """How much of the bound quest's clock is GONE, 0.0 -> 1.0, or None if there is no
    deadline to read.

    Uses the same timer `quest_tick_fail_after` anchors (``qfail:<id>``), so the urge's
    escalation and the quest's failure are reading one clock rather than two that can
    disagree. Before the watcher anchors it, nothing has elapsed - which is correct, and
    is why an un-anchored timer reads 0.0 rather than None.
    """
    qid = urge_bound_quest(rec)
    if not qid:
        return None
    from sbs_utils.procedural.quest import quest_get_data, quest_get_state, QuestState
    from sbs_utils.procedural.quest_driver import _quest_holders
    from sbs_utils.procedural.timers import is_timer_set, get_time_remaining
    for holder in _quest_holders():
        if int(quest_get_state(holder, qid) or 0) != int(QuestState.ACTIVE):
            continue
        data = quest_get_data(holder, qid) or {}
        trig = data.get("fail_after")
        if not isinstance(trig, dict):
            continue
        total = int(trig.get("seconds", 0) or 0) + int(trig.get("minutes", 0) or 0) * 60
        if total <= 0:
            continue
        name = "qfail:" + str(qid)
        if not is_timer_set(holder, name):
            return 0.0          # active, but the watcher has not anchored it yet
        left = max(0, int(get_time_remaining(holder, name)))
        return min(1.0, max(0.0, 1.0 - (left / float(total))))
    return None


def urge_stage(state):
    """Which stage this urge should speak at (1-based), clamped to what was authored."""
    rec = state["rec"]
    stages = rec.get("stages")
    if not stages:
        return 1
    top = max(stages)
    mode = rec.get("escalates")
    if mode == "deadline":
        gone = urge_deadline_fraction(rec)
        if gone is None:
            # `with deadline` on an urge whose quest has no clock. Fall back to
            # per-firing rather than freezing at stage 1, and say so ONCE - a warning
            # every pass would be its own kind of noise.
            if not state.get("_warned_no_deadline"):
                state["_warned_no_deadline"] = True
                _urge_log(f"urge {rec.get('key')!r} escalates 'with deadline' but "
                          f"{urge_bound_quest(rec) or 'its condition'} has no deadline "
                          f"- escalating per firing instead")
            mode = "firing"
        else:
            # Split the clock evenly across the authored stages: with 3 stages, the last
            # third of the countdown speaks stage 3.
            return min(top, max(1, int(gone * top) + 1))
    if mode == "firing":
        return min(top, state.get("stage", 0) + 1)
    return 1


def urge_line(state):
    """A line for this urge - random within its current stage, or "" if it has none.

    A stage with no lines of its own falls back to the nearest LOWER stage that has
    some, so an author can write three stage-1 lines and one stage-3 line without the
    middle silently going quiet.
    """
    rec = state["rec"]
    stages = rec.get("stages")
    if not stages or not rec.get("escalates"):
        pool = rec.get("pool") or []
        return random.choice(pool) if pool else ""
    want = urge_stage(state)
    for s in range(want, 0, -1):
        lines = stages.get(s)
        if lines:
            return random.choice(lines)
    pool = rec.get("pool") or []
    return random.choice(pool) if pool else ""


# --- speaking -----------------------------------------------------------------
def urge_speak(actor_id, line):
    """Say one line as this actor, routed by where the actor IS (URGE_PLAN.md s6).

    * hosted on a player ship -> an internal crew message from the actor
    * hosted elsewhere        -> a comms message from the host to the player ships
    * unhosted                -> a comms message from the actor itself (galaxy-wide,
      the way Open Universe's news voice already works)

    Defensive by design: comms runs the message through
    ``compile_and_format_string``, so a stray ``{`` in authored prose raises there rather
    than here. One bad line must not stop the ticker for every other actor, so it is
    caught and logged against the actor.
    """
    if not line:
        return False
    from sbs_utils.procedural.comms import comms_message, comms_receive_internal
    from sbs_utils.procedural.roles import has_role, role
    actor = to_object(actor_id)
    if actor is None:
        return False
    name = getattr(actor, "name", None)
    color = get_inventory_value(actor_id, "lf_color", None)
    host_id = get_inventory_value(actor_id, "host", 0)
    try:
        if host_id and has_role(host_id, "__player__"):
            comms_receive_internal(line, host_id, from_name=name, title=name,
                                   title_color=color)
        elif host_id:
            comms_message(line, host_id, role("__player__"), title=name,
                          title_color=color, from_name=name)
        else:
            comms_message(line, actor_id, role("__player__"), title=name,
                          title_color=color, from_name=name)
    except Exception as e:
        _urge_log(f"{name or actor_id} could not speak {line!r}: {e}")
        return False
    return True


# --- the ticker ---------------------------------------------------------------
def urge_schedule():
    """Ensure the background tick task driving urges is running."""
    global __urge_tick_task
    if __urge_tick_task is None:
        __urge_tick_task = TickDispatcher.do_interval(_urges_tick, 0)


def _urges_tick(tick_task):
    urges_run_all(tick_task, pass_seconds=URGE_PASS_SECONDS)


def urge_reset():
    """Forget the scheduled tick task so the next mission re-registers it.

    The same latch that made `objective_reset` necessary: a restart calls
    TickDispatcher.clear(), which throws the task away, but a still-set global would
    make urge_schedule() decide there was nothing to do - and no actor would ever speak
    again, silently, from run 2 onward.
    """
    global __urge_tick_task
    __urge_tick_task = None
    _urge_slicer.__init__()
    urge_budget_reset()
    # NOTE the announce traffic clock is reset by reset_mission_state directly, NOT from
    # here. Importing announce (and through it gui.overlay + comms) from inside the reset
    # path adds an import chain to a function that runs while the world is half torn
    # down. Cheap to avoid, and reset is the wrong place to discover an import cycle.


def urge_ticks_stale():
    """True if we think the tick task is scheduled but the dispatcher has lost it."""
    if __urge_tick_task is None:
        return False
    return (__urge_tick_task not in TickDispatcher._dispatch_tick
            and __urge_tick_task not in TickDispatcher._new_this_tick)


def urge_actors():
    """Every agent holding urges, as a LIST.

    A list, not the live set: running an urge's ``Action:`` can give another agent its
    first urge, and mutating the registry mid-iteration raises "Set changed size during
    iteration" - the lesson `brain.py` s396-400 already paid for.
    """
    return list(has_inventory("__URGES__"))


def urges_run_all(tick_task=None, pass_seconds=None):
    """Run one pass (or a rolling slice of one) over every actor with urges."""
    ids = urge_actors()
    seq = ids if pass_seconds is None else _urge_slicer.slice(ids, pass_seconds)
    stale = None
    for actor_id in seq:
        try:
            actor = Agent.get(actor_id)
            if actor is None:
                # The agent is gone but its id lingers in the registry (or was recycled
                # to something with no urges). Unschedule after the loop, never during.
                if stale is None:
                    stale = []
                stale.append(actor_id)
                continue
            urge_run_one(actor_id)
        except Exception as e:
            _urge_log(f"urge processing failed for {actor_id}: {e}")
    if stale:
        urge_clear(stale)


def urge_run_one(actor_id, now=None):
    """Pick and act on at most one urge for this actor. Returns the urge acted on."""
    state = urge_pick(actor_id, now)
    if state is None:
        return None
    if not urge_budget_allows(actor_id, state, now):
        # Deliberately NOT stamped: a refused urge retries next pass rather than losing
        # its turn to a floor it had no say in.
        return None
    if urge_speak(actor_id, urge_line(state)):
        urge_note_spoke(actor_id, now)
    action = state["rec"].get("action")
    if action:
        from sbs_utils.procedural.amd_action import amd_action_run
        amd_action_run(action, where=f"urge {state['rec'].get('key') or '?'!r}: ")
    # Stamp even when the line FAILED to speak. A failure here is almost always a
    # permanent authoring fault (a stray brace, a dead host), not a transient one, and
    # not stamping would retry it - and log it - every single pass, forever. The budget
    # refusal above is the deliberate exception: that one is transient by definition, so
    # it returns before this and keeps its turn.
    state["last"] = FrameContext.sim_seconds if now is None else now
    state["stage"] = state.get("stage", 0) + 1
    return state
