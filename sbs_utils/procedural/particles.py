"""particles - named, budgeted particle effects on hulls and in space.

Thin wrappers over the five engine calls (``sbs.add_particle_emittor`` /
``delete_particle_emittor`` / ``particle_emittor_exists`` / ``particle_on`` /
``particle_at``) plus the three things the raw API does not provide: a NAME for a
look, a place to keep the handle so it gets deleted, and a ceiling.

THE DOCTRINE. Particles are a limited-use tool, and the limit is structural rather
than advisory:

    One emitter per SUBJECT, not per event. One subject per REASON.
    A reason must be able to say when it is finished.

Three mechanisms carry that. Named **slots** - re-issuing a slot replaces, so a
call in a loop cannot double up. A global **budget** that refuses rather than
sprinkles. A **janitor** that reconciles against the engine, so an object deleted
by a box-delete (which routes no destroy event) cannot leak its emitter.

WHAT THIS MODULE MUST NEVER GROW. The engine already does **explosions and ship
destruction, engine exhaust, and shield-hit / impact flashes**, automatically, on
the event - there is nothing to call and nothing to wrap. Hand-rolling any of them
out of particles produces a worse copy layered on top of the real one. The
temptation is concrete: the mission corpus contains a particle "explosion"
(LM ``damage/damage.mast:57``) and a particle "thruster wash"
(``fleets/elite_abilities_prefabs.mast:34``) that both look like presets worth
lifting. They are deliberately NOT in the table below. This module is for looks the
engine has no opinion about - a charging drive, a smoldering hull, a leaking coolant
line, an investigate-me beacon.

THE DESCRIPTOR GRAMMAR is documented in the engine's own reference,
``data/widget_stylestring_documentation.txt`` under the ``particle_event`` tag:

    align       True/False - are offsets relative to the object's front
    color       named / #RGB / #RRGGBB / rgb() / hsl(); a comma PAIR = random between
    count       particles created in this event
    delay       frames (30/sec) before the particle appears and starts aging
    image_cell  index into the particle sprite sheet, 0-15
    lifespan    frames (30/sec) each particle lives
    offset      x,y,z from the emit point
    shape       hull, line_x/y/z, cone_x/y/z, ring_x/y/z
    size        0.1 - 100.0
    smoke       True = alpha-blended smoke, False = additive "hot" particles
    speed       0.1 - 10.0

Hot (non-smoke) particles are ADDITIVE, so overlapping colors pile toward white -
which is why ramping a color toward white reads as "charging" for free.

MOCK NOTE: the cosmos_dev mock draws nothing (particles are client-render-only), but
it does model the handle contract - real ids, working delete/exists - so the
registry, budget and janitor below ARE unit-tested. The APPEARANCE is engine-only;
judge it in the Visual Test Range (``--map visual_particles``), never in the browser
mock.
"""

from ..helpers import FrameContext
from ..tickdispatcher import TickDispatcher
from ..lifetimedispatcher import LifetimeDispatcher
from ..vec import Vec3
from .query import to_id, to_object, to_engine_object, object_exists
from .execution import log


# ---------------------------------------------------------------------------
# The descriptor string
# ---------------------------------------------------------------------------

# Fixed order, so two authors writing the same look produce the same string and a
# test can assert on it. NOT dict order - that would make the output depend on which
# keyword happened to be typed first.
_KEY_ORDER = ("align", "smoke", "shape", "color", "lifespan",
              "image_cell", "size", "speed", "count", "offset", "delay")

_warned_keys = set()


def _val(v):
    """One descriptor value, in the engine's own spelling."""
    if v is True or v is False:
        return "True" if v else "False"      # engine spells them capitalized
    if isinstance(v, (tuple, list)):
        return ",".join(_val(x) for x in v)  # ranges and offsets: `0,3`, `0,0,200`
    if isinstance(v, float):
        return "%g" % v                      # 0.8, never 0.8000000000000000444
    return str(v)


def particle_descriptor(color=None, lifespan=None, image_cell=None, size=None,
                        speed=None, count=None, align=None, shape=None,
                        offset=None, smoke=None, delay=None, **extra):
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
        str: e.g. ``"align: True; shape: hull; color: black; lifespan: 60"``
    """
    fields = {
        "color": color, "lifespan": lifespan, "image_cell": image_cell,
        "size": size, "speed": speed, "count": count, "align": align,
        "shape": shape, "offset": offset, "smoke": smoke, "delay": delay,
    }
    for k, v in (extra or {}).items():
        if k not in _KEY_ORDER and k not in _warned_keys:
            _warned_keys.add(k)
            log(f"unknown particle descriptor key {k!r} - passed through", "particles")
        fields[k] = v
    parts = []
    for key in _KEY_ORDER:
        v = fields.pop(key, None)
        if v is not None:
            parts.append(f"{key}: {_val(v)}")
    for key in sorted(fields):                 # anything unrecognized, after the known
        if fields[key] is not None:
            parts.append(f"{key}: {_val(fields[key])}")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Named presets
# ---------------------------------------------------------------------------

# Kwargs dicts, not pre-built strings, so an override composes:
#   particle_preset("smoke", count=8)
#
# Two tables on purpose. BUILTIN is the shipped library and is never cleared;
# MISSION is whatever particle_preset_define() added and IS cleared on mission
# reset, because a look declared by one mission must not survive into the next.
_PRESETS_BUILTIN = {
    # --- lifted verbatim from the corpus, so those sites become one-liners with
    # --- byte-identical output.
    "sparks": dict(align=True, shape="hull", color="green,white", lifespan=4,
                   image_cell=(0, 3), size=0.8, speed=5, count=10),
    "smoke": dict(align=True, smoke=True, shape="hull", color="black", lifespan=60,
                  image_cell=4, size=12, speed=0, count=50),
    "hull_glow": dict(align=True, shape="hull", color="purple,pink", lifespan=5,
                      image_cell=(0, 3), size=20, speed=0, count=50),
    "pickup": dict(color="#01F,#505", lifespan=30, image_cell=9, size=20, speed=1,
                   count=(100, 1000)),

    # --- new. Counts are deliberately small: these are the ones that get attached
    # --- to MANY objects, so they are the ones that have to be cheap.
    "charge": dict(align=True, shape="hull", color="#8cf,white", lifespan=5,
                   image_cell=(0, 3), size=0.6, speed=0.5, count=10),
    "ember": dict(align=True, shape="hull", color="#f80,#600", lifespan=60,
                  image_cell=12, size=2, speed=0, count=6),
    "smolder": dict(align=True, smoke=True, shape="hull", color="#222,#000",
                    lifespan=60, image_cell=4, size=6, speed=0.5, count=12),
    "coolant_leak": dict(align=True, shape="hull", color="#9ef,white", lifespan=50,
                         image_cell=9, size=6, speed=2, count=20),
    "dust": dict(color="#987,#654", lifespan=60, image_cell=4, size=8, speed=1,
                 count=30),
    "scan_ping": dict(color="#4f8,white", lifespan=30, image_cell=9, size=8, speed=1,
                      count=60),
}

_PRESETS_MISSION = {}


def particle_preset_define(name, **fields):
    """Declare a mission's or addon's own look. Cleared on mission reset."""
    _PRESETS_MISSION[str(name)] = dict(fields)


def particle_preset_get(name):
    """The raw kwargs dict for a preset, or None. Mission presets shadow built-ins."""
    key = str(name)
    got = _PRESETS_MISSION.get(key)
    if got is None:
        got = _PRESETS_BUILTIN.get(key)
    return dict(got) if got is not None else None


def particle_preset(name, **overrides):
    """Resolve a preset (plus overrides) to a descriptor string, or None if unknown.

    Never raises and never emits. A missing look must not take a mission down - it
    logs and the caller does nothing.
    """
    fields = particle_preset_get(name)
    if fields is None:
        log(f"unknown particle preset {name!r}", "particles", "warning")
        return None
    fields.update({k: v for k, v in overrides.items() if v is not None})
    return particle_descriptor(**fields)


def particle_preset_names():
    """Every preset name currently resolvable."""
    return sorted(set(_PRESETS_BUILTIN) | set(_PRESETS_MISSION))


def particle_presets_mission_count():
    """Ledger probe: how many mission-defined presets are live."""
    return len(_PRESETS_MISSION)


def _descriptor_for(preset, kw):
    """Shared resolution: a preset name plus overrides, or bare kwargs."""
    if preset is not None:
        return particle_preset(preset, **kw)
    return particle_descriptor(**kw)


# ---------------------------------------------------------------------------
# One-shot bursts - free. No handle, no registry, no budget: by the time the call
# returns the burst has already happened and there is nothing to clean up.
# ---------------------------------------------------------------------------

def particle_burst(where, preset=None, **kw):
    """Emit a one-shot burst at an object or a point.

    ``where`` may be an agent id / Agent / engine object (routed to
    ``sbs.particle_on``) or a ``Vec3`` / ``(x, y, z)`` (routed to
    ``sbs.particle_at``). Callers should not have to know which of the two engine
    calls their subject needs.

    Returns:
        bool: True if something was emitted.
    """
    ctx = FrameContext.context
    if ctx is None:
        return False
    desc = _descriptor_for(preset, kw)
    if not desc:
        return False

    point = _as_point(where)
    if point is not None:
        ctx.sbs.particle_at(point, desc)
        return True

    eo = _engine_object(where)
    if eo is None:
        return False
    ctx.sbs.particle_on(eo, desc)
    return True


def _as_point(where):
    """A Vec3 / 3-tuple -> an sbs.vec3, else None (meaning: it is an object)."""
    ctx = FrameContext.context
    if isinstance(where, Vec3):
        return ctx.sbs.vec3(where.x, where.y, where.z)
    if isinstance(where, (tuple, list)) and len(where) == 3:
        return ctx.sbs.vec3(where[0], where[1], where[2])
    if hasattr(where, "x") and hasattr(where, "y") and hasattr(where, "z"):
        return where                      # already an sbs.vec3
    return None


def _engine_object(obj):
    """The C++ engine object for an id / Agent, or the thing itself if it is one."""
    eo = to_engine_object(obj)
    if eo is not None:
        return eo
    # A raw engine object handed straight in (what the corpus does today).
    if hasattr(obj, "unique_ID"):
        return obj
    return None


# ---------------------------------------------------------------------------
# Attached emitters - the slot registry
# ---------------------------------------------------------------------------

# (obj_id, slot) -> {"eid", "obj_id", "slot", "desc", "t", "priority"}
#
# ONE container, not a second by-object index: the budget keeps the live count in
# the tens, so a linear scan for "every slot on this object" is free - and one
# container is one reset-ledger entry, which is what keeps the audit honest.
_LIVE = {}
_janitor_task = None
_hooked_destroy = False

_JANITOR_SECONDS = 5


def particle_count():
    """How many attached emitters are live. Ledger probe."""
    return len(_LIVE)


def particle_effect(obj, preset=None, slot=None, priority=0, **kw):
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
        object / the budget refused it.
    """
    ctx = FrameContext.context
    if ctx is None:
        return None
    desc = _descriptor_for(preset, kw)
    if not desc:
        return None

    oid = to_id(obj)
    if oid is None:
        return None
    eo = _engine_object(obj)
    if eo is None:
        log(f"particle_effect: no engine object for {oid}", "particles")
        return None

    key = (oid, str(slot) if slot is not None else str(preset or "effect"))
    if key in _LIVE:
        _detach(key)                       # slot replacement: never doubles
    elif not _budget_admit(priority, key):
        return None

    eid = ctx.sbs.add_particle_emittor(eo, -1, desc)
    _LIVE[key] = {"eid": eid, "obj_id": oid, "slot": key[1], "desc": desc,
                  "t": _now(), "priority": priority}
    _arm()
    return eid


def particle_effect_for(obj, seconds, preset=None, slot=None, priority=0, **kw):
    """Attach an emitter and clear it after ``seconds``.

    The teardown is a tick task, so it survives the caller returning - but it is
    also keyed on the slot, so a replacement in the meantime is not clobbered.
    """
    key_slot = str(slot) if slot is not None else str(preset or "effect")
    eid = particle_effect(obj, preset, slot=key_slot, priority=priority, **kw)
    if eid is None:
        return None
    oid = to_id(obj)

    def _expire(t=None):
        row = _LIVE.get((oid, key_slot))
        if row is not None and row["eid"] == eid:     # not someone else's replacement
            particle_effect_clear(oid, key_slot)
    TickDispatcher.do_once(_expire, seconds)
    return eid


def particle_effect_active(obj, slot=None):
    """Is this object carrying that slot (or any slot, if slot is None)?"""
    oid = to_id(obj)
    if slot is not None:
        return (oid, str(slot)) in _LIVE
    return any(k[0] == oid for k in _LIVE)


def particle_effect_slots(obj):
    """The slot names live on this object."""
    oid = to_id(obj)
    return sorted(k[1] for k in _LIVE if k[0] == oid)


def particle_effect_clear(obj, slot=None):
    """Clear one slot, or every slot on the object. Returns how many were cleared."""
    oid = to_id(obj)
    if slot is not None:
        keys = [(oid, str(slot))] if (oid, str(slot)) in _LIVE else []
    else:
        keys = [k for k in _LIVE if k[0] == oid]
    for k in keys:
        _detach(k)
    _disarm()
    return len(keys)


def particle_clear_all():
    """Delete every live emitter IN THE ENGINE, then forget them. The reset hook.

    Deleting in the engine is the half that is easy to skip: emptying ``_LIVE``
    alone passes the reset audit and still leaks, which is why the test asserts on
    the mock's emitter table rather than on this dict.
    """
    n = len(_LIVE)
    for key in list(_LIVE):
        _detach(key)
    # Build-ups in flight. Their tick tasks are dropped by TickDispatcher.clear(),
    # but this dict outlives it - and a stale row makes the next mission's first
    # charge think one is already running on a recycled id, so it stops it instead
    # of starting one. Same shape as the objective/urge "already scheduled" latches.
    _CHARGING.clear()
    _PRESETS_MISSION.clear()
    _BUDGET["refused"] = 0
    _BUDGET["last_log"] = 0.0
    _disarm()
    return n


def _detach(key):
    """Delete one emitter in the engine and drop its row. Safe if either is gone."""
    row = _LIVE.pop(key, None)
    if row is None:
        return
    ctx = FrameContext.context
    if ctx is None:
        return
    try:
        ctx.sbs.delete_particle_emittor(row["eid"])
    except Exception as e:
        log(f"delete_particle_emittor({row['eid']}) failed: {e}", "particles")


def _now():
    """Sim seconds. sim_seconds lives on FrameContext, not on the Context object."""
    if FrameContext.context is None:
        return 0.0
    return FrameContext.sim_seconds


# ---------------------------------------------------------------------------
# The budget - the "limited use tool" made structural
# ---------------------------------------------------------------------------

_BUDGET = {"max": 24, "refused": 0, "last_log": 0.0}
_REFUSE_LOG_SECONDS = 5.0


def particle_budget(max_live=None):
    """Get, or set, the ceiling on LIVE attached emitters. Bursts are not counted."""
    if max_live is not None:
        _BUDGET["max"] = int(max_live)
    return _BUDGET["max"]


def particle_budget_refused():
    """How many attach attempts the budget has turned away this mission."""
    return _BUDGET["refused"]


def _budget_admit(priority, key):
    """Room for one more? Evict a lower-priority row if that is what it takes.

    Refuse-by-default rather than always-evict: silently eating another system's
    effect is a haunting bug, so priority has to be asked for explicitly.
    """
    if len(_LIVE) < _BUDGET["max"]:
        return True
    lower = [k for k, r in _LIVE.items() if r["priority"] < priority]
    if lower:
        oldest = min(lower, key=lambda k: _LIVE[k]["t"])
        log(f"particle budget full - evicting {_LIVE[oldest]['slot']!r} on "
            f"{_LIVE[oldest]['obj_id']} for a priority-{priority} effect", "particles")
        _detach(oldest)
        return True

    _BUDGET["refused"] += 1
    now = _now()
    if now - _BUDGET["last_log"] >= _REFUSE_LOG_SECONDS:
        _BUDGET["last_log"] = now
        log(f"particle budget full ({_BUDGET['max']}) - refused {key[1]!r} on {key[0]}; "
            f"{_BUDGET['refused']} refused so far", "particles", "warning")
    return False


# ---------------------------------------------------------------------------
# Cleanup - two layers, both needed
# ---------------------------------------------------------------------------

def _arm():
    """Start the janitor and the destroy hook once there is anything to look after.

    Lazily, never at import: LifetimeDispatcher.clear() and TickDispatcher.clear()
    both run on mission reset, so anything registered at import time is silently
    dropped from run 2 onward. Re-arming on the first attach after a reset is
    self-healing.
    """
    global _janitor_task, _hooked_destroy
    if not _LIVE or FrameContext.context is None:
        return
    if not _hooked_destroy:
        LifetimeDispatcher.add_destroy(_on_destroy)
        _hooked_destroy = True
    if _janitor_task is None:
        _janitor_task = TickDispatcher.do_interval(_janitor, _JANITOR_SECONDS)


def _disarm():
    global _janitor_task, _hooked_destroy
    if _janitor_task is not None and not _LIVE:
        _janitor_task.stop()
        _janitor_task = None
    if _hooked_destroy and not _LIVE:
        LifetimeDispatcher.remove_destroy(_on_destroy)
        _hooked_destroy = False


def _on_destroy(agent, event=None):
    """Layer 1: a routed destruction. Prompt, but does not catch everything."""
    particle_effect_clear(getattr(agent, "id", agent))


def _janitor(t=None):
    """Layer 2: reconcile against reality.

    NOT optional. A box delete (OU's ``universe_clear_cell``) and standby culling
    both remove objects without routing a destroy event - and a warp jump does
    exactly that one line after a charge-up. This also reconciles the other
    direction: if the engine reaps an emitter itself, ``particle_emittor_exists``
    goes False and the row goes with it, so the count never over-reports.
    """
    ctx = FrameContext.context
    if ctx is None:
        return
    for key, row in list(_LIVE.items()):
        gone = not object_exists(row["obj_id"])
        if not gone:
            try:
                gone = not ctx.sbs.particle_emittor_exists(row["eid"])
            except Exception:
                gone = False
            if gone:
                _LIVE.pop(key, None)      # the engine already dropped it
                continue
        if gone:
            _detach(key)
    _disarm()


# ---------------------------------------------------------------------------
# Charge-up - a look that BUILDS, so a human can read it as a wind-up
# ---------------------------------------------------------------------------

# A charge look is a ramp spec: where each field starts and where it ends. The
# driver interpolates numbers AND tuples, so `offset` ramps exactly like `count`
# does - which is what lets "a field collapsing onto the hull" be ONE emitter in
# ONE slot rather than three.
#
# `colors` is taken at even fractions rather than interpolated: blending hex is not
# something the descriptor grammar can express, and stepped color reads as stages,
# which is what a charge-up wants. "{side}" is filled in with the caller's color, so
# an unauthored faction still winds up in its own color for free.
_CHARGE_LOOKS = {
    # THE DEFAULT. Sparks over the whole hull, denser, bigger and faster, color
    # walking from the side's own toward white. Hull-surface with a low starting
    # speed is the only mode the corpus confirms reads as the ship doing this to
    # ITSELF rather than something being done to it.
    "coil": dict(preset="charge",
                 count=(10, 80), size=(0.6, 2.0), speed=(0.5, 3.0),
                 colors=("{side}", "{side},white", "white")),

    # Electrical instability - short-lived, fast, blue-white, throwing arcs clear of
    # the hull. Reserved for a jump that FAILS or is interrupted.
    "arc": dict(preset="charge", lifespan=4,
                count=(10, 80), size=(1.0, 2.5), speed=(3.0, 7.0),
                colors=("#48f", "#cff,#48f", "white"),
                spill=(300.0, 2)),      # (distance off the hull, bursts per step)

    # Purge, then ignite. Heavy smoke that thins as a hot core comes up under it.
    # The trader / industrial read.
    "preburn": dict(preset="smoke",
                    count=(50, 12), size=(12.0, 3.0), speed=(0.0, 2.0),
                    colors=("black", "#333,#8cf", "#fff,#8cf")),

    # A field closing onto the ship: a wide dim cloud standing off the hull whose
    # offset walks to zero as it tightens and brightens. Reads best to a BYSTANDER,
    # less so from your own bridge.
    "implode": dict(preset="charge",
                    count=(20, 120), size=(12.0, 2.0), speed=(0.5, 0.5),
                    offset=((0.0, 0.0, 400.0), (0.0, 0.0, 0.0)),
                    colors=("{side}", "{side},white", "white")),

    # THE DEGRADE PATH. One-shot bursts, each bigger than the last. Holds no emitter
    # at all, so it costs nothing and cannot leak - which is why it is what a budget
    # refusal falls back to. A jump with no wind-up looks like a bug.
    "pulse": dict(preset="charge", burst_only=True,
                  count=(60, 400), size=(4.0, 16.0), speed=(1.0, 4.0),
                  colors=("{side}", "{side},white", "white")),
}

DEFAULT_CHARGE_LOOK = "coil"
DEFAULT_CHARGE_SECONDS = 3.5
DEFAULT_CHARGE_STEPS = 6

_CHARGING = {}          # (obj_id, slot) -> ramp state, so stop() can cancel its ticks


def particle_charge_looks():
    """Every charge look name."""
    return sorted(_CHARGE_LOOKS)


def _lerp(a, b, f):
    """Interpolate numbers, or tuples element-wise (so `offset` ramps too)."""
    if isinstance(a, (tuple, list)):
        return tuple(_lerp(x, y, f) for x, y in zip(a, b))
    v = a + (b - a) * f
    return v if isinstance(a, float) or isinstance(b, float) else int(round(v))


def _charge_fields(spec, f, color=None):
    """The descriptor kwargs for ramp position ``f`` (0.0 -> 1.0)."""
    out = {}
    for key, val in spec.items():
        if key in ("preset", "colors", "burst_only", "spill"):
            continue
        # A 2-tuple is a RAMP (start, end) - including `offset`, whose ends are
        # themselves 3-tuples, so a static `offset=(x, y, z)` is length 3 and falls
        # through untouched. `image_cell` is exempt: a pair there is the grammar's
        # "random between two cells", not something to interpolate.
        if key != "image_cell" and isinstance(val, tuple) and len(val) == 2:
            out[key] = _lerp(val[0], val[1], f)
        elif val is not None:
            out[key] = val
    colors = spec.get("colors")
    if colors:
        idx = min(int(f * len(colors)), len(colors) - 1)
        out["color"] = colors[idx].replace("{side}", color or "#8cf")
    return out


def particle_charge_start(obj, look=None, seconds=None, color=None,
                          slot="warp_charge", priority=10, steps=None):
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
        bool: True if a build-up is running.
    """
    ctx = FrameContext.context
    if ctx is None:
        return False
    oid = to_id(obj)
    if oid is None or not object_exists(oid):
        return False

    name = str(look or DEFAULT_CHARGE_LOOK)
    spec = _CHARGE_LOOKS.get(name)
    if spec is None:
        log(f"unknown charge look {name!r} - using {DEFAULT_CHARGE_LOOK!r}",
            "particles", "warning")
        spec = _CHARGE_LOOKS[DEFAULT_CHARGE_LOOK]
    seconds = float(DEFAULT_CHARGE_SECONDS if seconds is None else seconds)
    steps = int(DEFAULT_CHARGE_STEPS if steps is None else steps)
    if seconds <= 0 or steps <= 0:
        return False

    particle_charge_stop(obj, slot, flash=False)   # never stack two build-ups
    key = (oid, str(slot))
    state = {"i": 0, "burst": bool(spec.get("burst_only")), "tasks": []}
    _CHARGING[key] = state
    every = seconds / steps

    def _step(t=None):
        f = state["i"] / max(steps - 1, 1)
        state["i"] += 1
        if not object_exists(oid):
            particle_charge_stop(oid, slot, flash=False)
            return
        fields = _charge_fields(spec, f, color)
        if state["burst"]:
            particle_burst(oid, spec.get("preset"), shape="hull", align=True, **fields)
            return
        eid = particle_effect(oid, spec.get("preset"), slot=slot,
                              priority=priority, **fields)
        if eid is None:
            state["burst"] = True     # budget refused - keep the beat, drop the handle
            return
        spill = spec.get("spill")
        if spill:
            _spill(oid, spill, fields, f)

    _step()
    if steps > 1:
        state["tasks"].append(TickDispatcher.do_interval(_step, every, count=steps - 1))
    state["tasks"].append(TickDispatcher.do_once(
        lambda t=None: particle_charge_stop(oid, slot), seconds))
    return True


def _spill(oid, spill, fields, f):
    """Throw a few arcs clear of the hull (the `arc` look's off-hull discharges)."""
    obj = to_object(oid)
    if obj is None:
        return
    dist, per_step = spill
    pos = obj.pos
    for i in range(int(per_step)):
        d = dist * (0.4 + 0.6 * f)
        off = d if i % 2 == 0 else -d
        particle_burst((pos.x + off, pos.y, pos.z - off),
                       count=20, size=fields.get("size", 2), speed=4,
                       lifespan=4, image_cell=(0, 3),
                       color=fields.get("color", "white"))


def particle_charge_stop(obj, slot="warp_charge", flash=True):
    """End a build-up. With ``flash``, snap a ring burst as it lets go.

    Safe when nothing is charging, and safe to call twice.
    """
    oid = to_id(obj)
    key = (oid, str(slot))
    state = _CHARGING.pop(key, None)
    if state is not None:
        for t in state["tasks"]:
            try:
                t.stop()
            except Exception:
                pass
    had = particle_effect_clear(oid, slot)
    if flash and (state is not None or had) and object_exists(oid):
        particle_burst(oid, shape="ring_z", align=True, color="white",
                       lifespan=10, image_cell=(0, 3), size=20, speed=4, count=400)
    return state is not None


def particle_charging(obj, slot="warp_charge"):
    """Is a build-up running on this object?"""
    return (to_id(obj), str(slot)) in _CHARGING


def particle_charge_count():
    """Ledger probe: build-ups in flight."""
    return len(_CHARGING)
