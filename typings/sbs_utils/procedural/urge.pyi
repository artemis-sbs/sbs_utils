from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import RollingSlicer
from sbs_utils.tickdispatcher import TickDispatcher
def _cond_always (actor_id, operand):
    """`always` - eligible whenever the cooldown allows. The heartbeat form."""
def _cond_has_role (actor_id, operand):
    """`has role <role>` - the actor carries a role. The escape hatch for mission state
    that is already expressed as a role, which most of it is."""
def _cond_quest (actor_id, operand):
    """`quest <id> <state>` - true while ANY holder has that quest in that state.
    
    Any holder, not the actor's own: the diplomat's urge watches the delivery quest the
    PLAYER accepted, while a station's urge watches one it holds itself. Making the
    author say which would be a distinction with no payoff - a quest id is unique."""
def _install_conditions ():
    ...
def _norm (text):
    ...
def _urge_log (message, level='warning'):
    """Never raise out of the ticker - a bad line must not stop every other actor."""
def _urges_tick (tick_task):
    ...
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def has_inventory (key: str):
    """Return the set of agent IDs that have an inventory entry for the given key.
    
    Args:
        key (str): The inventory key to look for.
    
    Returns:
        set[int]: IDs of all agents that have this key set."""
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
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def urge_actors ():
    """Every agent holding urges, as a LIST.
    
    A list, not the live set: running an urge's ``Action:`` can give another agent its
    first urge, and mutating the registry mid-iteration raises "Set changed size during
    iteration" - the lesson `brain.py` s396-400 already paid for."""
def urge_add (agents, record):
    """Give one urge to one or more agents. Idempotent per (agent, urge key): re-running
    a section does not give an actor the same want twice."""
def urge_bound_quest (rec):
    """The quest id this urge watches, read out of its ``Whenever:``, or None.
    
    No separate field: the bound quest IS the one the urge is conditional on, and a
    second field would be one more thing to keep in agreement with the first."""
def urge_budget_allows (actor_id, state, now=None):
    """Whether this actor may speak right now.
    
    A refusal here must NOT stamp the urge's cooldown - the caller retries next pass, so
    a floor never costs an urge its turn. (A speech FAILURE is the opposite case and does
    stamp; see ``urge_run_one``.)"""
def urge_budget_reset ():
    """Drop the per-actor speech clocks (called by reset_mission_state)."""
def urge_clear (agents):
    """Drop every urge from one or more agents (they stop being visited)."""
def urge_clear_conditions ():
    """Test-only: drop every registered condition (then re-install the built-ins)."""
def urge_condition_eval (actor_id, text):
    """Evaluate a ``Whenever:`` / ``Until:`` line. Unknown phrasing is FALSE and logged -
    an urge nobody can trigger is a bug, and a silently-true one would talk forever.
    
    A leading ``not`` negates, so the vocabulary does not need a second phrase for every
    inverse."""
def urge_conditions ():
    """Every registered phrase, longest first - the order the parser matches in."""
def urge_deadline_fraction (rec):
    """How much of the bound quest's clock is GONE, 0.0 -> 1.0, or None if there is no
    deadline to read.
    
    Uses the same timer `quest_tick_fail_after` anchors (``qfail:<id>``), so the urge's
    escalation and the quest's failure are reading one clock rather than two that can
    disagree. Before the watcher anchors it, nothing has elapsed - which is correct, and
    is why an un-anchored timer reads 0.0 rather than None."""
def urge_every (rec):
    """The cooldown to apply after a firing, in seconds.
    
    ``every`` is either a number or a ``(low, high)`` range, in which case each firing
    picks afresh. Jitter is not decoration: a character who speaks on an exact metronome
    reads as a machine, and the one shipped nagger in the corpus (LM's Florbin) was
    written as ``random.randint(180, 300)`` for exactly that reason."""
def urge_line (state):
    """A line for this urge - random within its current stage, or "" if it has none.
    
    A stage with no lines of its own falls back to the nearest LOWER stage that has
    some, so an author can write three stage-1 lines and one stage-3 line without the
    middle silently going quiet."""
def urge_note_spoke (actor_id, now=None):
    """Record that this actor just spoke - feeding both floors.
    
    The global clock lives in ``announce`` because an urge and a mission announcement are
    the same thing from the bridge's side: an unprompted voice."""
def urge_pick (actor_id, now=None):
    """The urge this actor should act on now, or None.
    
    Retires anything whose ``Until:`` is true, skips anything still cooling, evaluates
    the rest, and takes the highest ``Weight:`` (ties at random). Pure apart from the
    retire stamp, so it is testable without a tick."""
def urge_record (key=None, whenever='always', every=60, until=None, weight=0, pool=None, action=None, actor=None, stages=None, escalates=None, title=None):
    """One urge, as plain data. ``every`` is seconds; ``pool`` is the flat line list.
    
    ``stages`` is the optional ``{1: [...], 2: [...]}`` map built from ``%`` markers, and
    ``escalates`` is ``"deadline"`` | ``"firing"`` | None. With neither, an urge behaves
    exactly as it did before escalation existed."""
def urge_register_condition (phrase, fn, operand='required', domain=None):
    """Declare a ``Whenever:`` phrase.
    
    ``fn(actor_id, operand)`` returns truthy when the urge is eligible. A fixed
    vocabulary plus this registry, rather than a bare python expression: an expression is
    powerful and untypeable by the linter, and the whole point of the AMD layer is that
    the tooling can check what an author wrote. Same contract as
    ``amd_action_register`` - re-registering a phrase with a different function raises,
    re-registering the identical one is a no-op so reloading is safe."""
def urge_reset ():
    """Forget the scheduled tick task so the next mission re-registers it.
    
    The same latch that made `objective_reset` necessary: a restart calls
    TickDispatcher.clear(), which throws the task away, but a still-set global would
    make urge_schedule() decide there was nothing to do - and no actor would ever speak
    again, silently, from run 2 onward."""
def urge_run_one (actor_id, now=None):
    """Pick and act on at most one urge for this actor. Returns the urge acted on."""
def urge_schedule ():
    """Ensure the background tick task driving urges is running."""
def urge_speak (actor_id, line, title=None):
    """Say one line as this actor, routed by where the actor IS (DESIGN_RECORD.md s4).
    
    * hosted on a player ship -> an internal crew message from the actor
    * hosted elsewhere        -> a comms message from the host to the player ships
    * unhosted                -> a comms message from the actor itself (galaxy-wide,
      the way Open Universe's news voice already works)
    
    Defensive by design: comms runs the message through
    ``compile_and_format_string``, so a stray ``{`` in authored prose raises there rather
    than here. One bad line must not stop the ticker for every other actor, so it is
    caught and logged against the actor."""
def urge_stage (state):
    """Which stage this urge should speak at (1-based), clamped to what was authored."""
def urge_ticks_stale ():
    """True if we think the tick task is scheduled but the dispatcher has lost it."""
def urges_run_all (tick_task=None, pass_seconds=None):
    """Run one pass (or a rolling slice of one) over every actor with urges."""
