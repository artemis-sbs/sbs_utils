from sbs_utils.helpers import FrameContext
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3
def _arm ():
    """Start the janitor and the destroy hook once there is anything to look after.
    
    Lazily, never at import: LifetimeDispatcher.clear() and TickDispatcher.clear()
    both run on mission reset, so anything registered at import time is silently
    dropped from run 2 onward. Re-arming on the first attach after a reset is
    self-healing."""
def _as_point (where):
    """A Vec3 / 3-tuple -> an sbs.vec3, else None (meaning: it is an object)."""
def _budget_admit (priority, key):
    """Room for one more? Evict a lower-priority row if that is what it takes.
    
    Refuse-by-default rather than always-evict: silently eating another system's
    effect is a haunting bug, so priority has to be asked for explicitly."""
def _charge_fields (spec, f, color=None):
    """The descriptor kwargs for ramp position ``f`` (0.0 -> 1.0)."""
def _descriptor_for (preset, kw):
    """Shared resolution: a preset name plus overrides, or bare kwargs."""
def _detach (key):
    """Delete one emitter in the engine and drop its row. Safe if either is gone."""
def _disarm ():
    ...
def _engine_object (obj):
    """The C++ engine object for an id / Agent, or the thing itself if it is one."""
def _janitor (t=None):
    """Layer 2: reconcile against reality.
    
    NOT optional. A box delete (OU's ``universe_clear_cell``) and standby culling
    both remove objects without routing a destroy event - and a warp jump does
    exactly that one line after a charge-up. This also reconciles the other
    direction: if the engine reaps an emitter itself, ``particle_emittor_exists``
    goes False and the row goes with it, so the count never over-reports."""
def _lerp (a, b, f):
    """Interpolate numbers, or tuples element-wise (so `offset` ramps too)."""
def _now ():
    """Sim seconds. sim_seconds lives on FrameContext, not on the Context object."""
def _on_destroy (agent, event=None):
    """Layer 1: a routed destruction. Prompt, but does not catch everything."""
def _spill (oid, spill, fields, f):
    """Throw a few arcs clear of the hull (the `arc` look's off-hull discharges)."""
def _val (v):
    """One descriptor value, in the engine's own spelling."""
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
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def particle_budget (max_live=None):
    """Get, or set, the ceiling on LIVE attached emitters. Bursts are not counted."""
def particle_budget_refused ():
    """How many attach attempts the budget has turned away this mission."""
def particle_burst (where, preset=None, **kw):
    """Emit a one-shot burst at an object or a point.
    
    ``where`` may be an agent id / Agent / engine object (routed to
    ``sbs.particle_on``) or a ``Vec3`` / ``(x, y, z)`` (routed to
    ``sbs.particle_at``). Callers should not have to know which of the two engine
    calls their subject needs.
    
    Returns:
        bool: True if something was emitted."""
def particle_charge_count ():
    """Ledger probe: build-ups in flight."""
def particle_charge_looks ():
    """Every charge look name."""
def particle_charge_start (obj, look=None, seconds=None, color=None, slot='warp_charge', priority=10, steps=None):
    """Ramp a build-up on an object's hull, so a jump reads as a wind-up.
    
    Stepped ``add_particle_emittor``, not a per-tick burst loop: a burst is
    one-shot, so driving several seconds of glow with it means hundreds of bursts
    whose appearance depends on the frame rate. This is ~``steps`` engine calls, at
    most ONE live emitter (slot replacement deletes the previous stage for free),
    and every stage is a descriptor string a test can assert on.
    
    SELF-LIMITING: it tears itself down after ``seconds`` whether or not anyone
    calls ``particle_charge_stop``. So an aborted jump, a destroyed ship or a culled
    cell cannot leave it burning, and no caller needs a guard.
    
    If the budget refuses the emitter it falls back to the ``pulse`` look, which
    holds no emitter - going silent would read as a bug rather than as restraint.
    
    Args:
        obj: the ship winding up.
        look (str): a name from ``particle_charge_looks()``. Default ``coil``.
        seconds (float): how long the build-up runs. Default 3.5. **0 disables it**,
            which is the valve that restores a hard cut.
        color (str): tint for looks that use ``{side}`` - pass the side's own color.
        slot (str): the registry slot to occupy.
        priority (int): default 10, so a story beat outranks ambient decoration.
        steps (int): how many stages the ramp is drawn in. Default 6.
    
    Returns:
        bool: True if a build-up is running."""
def particle_charge_stop (obj, slot='warp_charge', flash=True):
    """End a build-up. With ``flash``, snap a ring burst as it lets go.
    
    Safe when nothing is charging, and safe to call twice."""
def particle_charging (obj, slot='warp_charge'):
    """Is a build-up running on this object?"""
def particle_clear_all ():
    """Delete every live emitter IN THE ENGINE, then forget them. The reset hook.
    
    Deleting in the engine is the half that is easy to skip: emptying ``_LIVE``
    alone passes the reset audit and still leaks, which is why the test asserts on
    the mock's emitter table rather than on this dict."""
def particle_count ():
    """How many attached emitters are live. Ledger probe."""
def particle_descriptor (color=None, lifespan=None, image_cell=None, size=None, speed=None, count=None, align=None, shape=None, offset=None, smoke=None, delay=None, **extra):
    """Build a descriptor string from keyword arguments.
    
    ``None`` values are omitted. Unknown keys in ``extra`` are passed through - the
    grammar is only partly documented and refusing unknowns would freeze it - but
    each unknown name is logged once so a typo is still discoverable.
    
    Args:
        color: named, ``#RGB``, ``#RRGGBB``, or a 2-tuple/comma pair for "random between".
        lifespan (int): frames (30/sec) each particle lives.
        image_cell: sprite cell 0-15, or a pair for a random range.
        size (float): 0.1 - 100.0.
        speed (float): 0.1 - 10.0.
        count: particles per event, or a pair for a random range.
        align (bool): are ``offset`` values relative to the object's front.
        shape (str): ``hull``, ``line_x/y/z``, ``cone_x/y/z``, ``ring_x/y/z``.
        offset: ``(x, y, z)`` from the emit point.
        smoke (bool): True = smoke, False = additive "hot" particles.
        delay (int): frames before the particle appears.
    
    Returns:
        str: e.g. ``"align: True; shape: hull; color: black; lifespan: 60"``"""
def particle_effect (obj, preset=None, slot=None, priority=0, **kw):
    """Attach a persistent emitter to ``obj`` in a named slot.
    
    ``slot`` defaults to the preset name, so ``particle_effect(ship, "smoke")``
    occupies slot ``"smoke"`` and re-issuing it REPLACES rather than doubles. That
    one rule is what makes this safe to call from a loop or a watcher.
    
    ``priority`` decides who wins when the budget is full: a higher-priority effect
    evicts the oldest strictly-lower-priority one. A story beat should outrank
    ambient decoration.
    
    The engine ``lifeSpan`` is always -1 (never expires). Its units are unverified,
    so Python owns the lifetime instead: ``seconds`` then means the same thing on
    every machine and this registry is the single truth.
    
    Returns:
        int | None: the engine emitter id, or None if unknown preset / no engine
        object / the budget refused it."""
def particle_effect_active (obj, slot=None):
    """Is this object carrying that slot (or any slot, if slot is None)?"""
def particle_effect_clear (obj, slot=None):
    """Clear one slot, or every slot on the object. Returns how many were cleared."""
def particle_effect_for (obj, seconds, preset=None, slot=None, priority=0, **kw):
    """Attach an emitter and clear it after ``seconds``.
    
    The teardown is a tick task, so it survives the caller returning - but it is
    also keyed on the slot, so a replacement in the meantime is not clobbered."""
def particle_effect_slots (obj):
    """The slot names live on this object."""
def particle_preset (name, **overrides):
    """Resolve a preset (plus overrides) to a descriptor string, or None if unknown.
    
    Never raises and never emits. A missing look must not take a mission down - it
    logs and the caller does nothing."""
def particle_preset_define (name, **fields):
    """Declare a mission's or addon's own look. Cleared on mission reset."""
def particle_preset_get (name):
    """The raw kwargs dict for a preset, or None. Mission presets shadow built-ins."""
def particle_preset_names ():
    """Every preset name currently resolvable."""
def particle_presets_mission_count ():
    """Ledger probe: how many mission-defined presets are live."""
def to_engine_object (id_or_obj):
    """Return the C++ engine-object pointer for an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        pointer | None: The underlying C++ engine-object, or ``None`` if the
            agent does not exist."""
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
