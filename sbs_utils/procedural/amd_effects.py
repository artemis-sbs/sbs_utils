"""Declarative particle looks from AMD - an effect is a RECORD.

A look is a whole thing with a name that several records point AT: two sides can
share one, a derelict can wear the one a quest marker uses. So it is an archetype
of its own rather than a trait bolted onto whatever happens to want it::

    ## [Effects](effects)

    ### [Coil charge](coil)
    ---
    Effect
    Look: charge
    Color: #8cf, white
    Size: 0.6 -> 2.0
    Count: 10 -> 80
    Speed: 0.5 -> 3.0
    Grows over: 3.5 seconds
    On: hull
    ---
    Drive coils biting down - the plating lights from the inside, tighter and
    faster, until it lets go.

``Look:`` names a **Python preset** (``procedural/particles.py``) as the base; every
other field overrides it. The built-in table stays the library and this is how an
author varies it, so the two layers never duplicate each other.

``A -> B`` is a RAMP - the same arrow a cutscene ``Move:`` already uses, so it is not
a new grammar to learn. A comma pair (``Color: #8cf, white``) is the descriptor
grammar's own "random between", which is a different thing and stays that way.

THE KIND LINE IS THE BARE NOUN ``Effect``. Not ``Kind: effect`` - ``Kind:`` infers
the LANDMARK archetype (``("kind", "landmark")`` in the schema's discriminators),
which is the trap that cost the cutscene design a redesign. In a flat file with no
section to name it, carrying ``Look:`` is what types the record.

Resolution order everywhere a look is named by key: **an AMD record first, a Python
preset second.** So ``Jump Charge: coil`` works whether ``coil`` is authored or
built in, and an author can shadow a shipped look by declaring a record with its key.
"""

from .amd_doc import amd_records
from .execution import log
from .particles import (particle_descriptor, particle_preset_get, particle_burst,
                        particle_effect, particle_charge_start, particle_charge_stop,
                        DEFAULT_CHARGE_SECONDS, DEFAULT_CHARGE_STEPS)


# key -> the parsed spec dict. Ledger-registered, cleared on mission reset: a look
# declared by one mission must not resolve in the next.
EFFECT_AMD = {}

# Which AMD field names carry a value the descriptor understands, and under what
# descriptor key. `cell`/`image cell` is the schema's alias for `image_cell`.
_FIELD_KEYS = {
    "size": "size", "count": "count", "speed": "speed", "lifespan": "lifespan",
    "offset": "offset", "smoke": "smoke", "color": "color",
    "cell": "image_cell", "image cell": "image_cell", "image_cell": "image_cell",
}


def amd_effects_clear():
    """Forget every declared look. The reset hook."""
    EFFECT_AMD.clear()


def amd_effects_count():
    """Ledger probe."""
    return len(EFFECT_AMD)


def _num(v, default=None):
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return default


def _truthy(v, default=False):
    if v is None:
        return default
    return str(v).strip().lower() in ("yes", "true", "on", "1")


def _tuple_or_num(text):
    """`0, 0, 400` -> (0.0, 0.0, 400.0); a bare number -> that number; else the text."""
    s = str(text).strip()
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        nums = [_num(p) for p in parts]
        if all(n is not None for n in nums):
            return tuple(float(n) for n in nums)
        return s                      # a color pair like `#8cf, white` - leave it
    n = _num(s)
    return s if n is None else n


def _ramp(text):
    """`A -> B` -> (start, end), else None. Same arrow as a cutscene `Move:`."""
    if text is None:
        return None
    for sep in ("->", "=>", " to "):
        if sep in str(text):
            a, b = str(text).split(sep, 1)
            va, vb = _tuple_or_num(a), _tuple_or_num(b)
            if va is None or vb is None:
                return None
            return (va, vb)
    return None


def _spec_from(rec):
    """One AMD record -> the internal spec dict."""
    data = rec.get("data") or {}
    spec = {"key": rec.get("key"), "display": rec.get("display"),
            "body": rec.get("body"), "preset": None, "ramps": {}, "static": {}}

    look = data.get("look")
    if look:
        spec["preset"] = str(look).strip()

    for label, dkey in _FIELD_KEYS.items():
        if label not in data:
            continue
        raw = data[label]
        if dkey == "smoke":
            spec["static"][dkey] = _truthy(raw)
            continue
        ramp = _ramp(raw)
        if ramp is not None and dkey != "color":
            spec["ramps"][dkey] = ramp
        elif dkey == "color":
            # A comma pair is "random between", not a ramp. Strip the spaces an
            # author naturally writes (`#8cf, white`) - the corpus form is
            # `#8cf,white`, and a space inside a value is not worth risking.
            spec["static"][dkey] = ",".join(
                p.strip() for p in str(raw).split(",") if p.strip())
        else:
            spec["static"][dkey] = _tuple_or_num(raw)

    on = data.get("on")
    if on:
        on = str(on).strip().lower()
        # `point` is the absence of a shape - an emitter at one spot, offset from
        # the object - so it is not passed through as a shape word.
        spec["static"]["shape"] = None if on == "point" else on
        if spec["static"]["shape"] is None:
            spec["static"].pop("shape")

    spec["ramp_seconds"] = _num(data.get("ramp_seconds") or data.get("grows over"),
                                DEFAULT_CHARGE_SECONDS)
    spec["steps"] = int(_num(data.get("steps"), DEFAULT_CHARGE_STEPS))
    return spec


def amd_effects(section):
    """Load every effect record in ``section`` into ``EFFECT_AMD``. Returns how many."""
    n = 0
    for rec in amd_records(section):
        key = rec.get("key")
        if not key:
            continue
        EFFECT_AMD[str(key)] = _spec_from(rec)
        n += 1
    return n


def effect_amd_names():
    """Every declared look key."""
    return sorted(EFFECT_AMD)


def effect_amd_descriptor(key, at=1.0):
    """The descriptor string for a declared look at ramp position ``at`` (0.0-1.0).

    PURE - no engine, no objects, no side effects. That is deliberate: it makes the
    ramp arithmetic assertable headlessly, so the only thing left needing the engine
    is what the frame actually looks like.

    Returns None if the key is not declared.
    """
    spec = EFFECT_AMD.get(str(key))
    if spec is None:
        return None
    fields = particle_preset_get(spec["preset"]) or {} if spec["preset"] else {}
    fields.update(spec["static"])
    f = max(0.0, min(1.0, float(at)))
    for dkey, (a, b) in spec["ramps"].items():
        fields[dkey] = _lerp(a, b, f)
    return particle_descriptor(**fields)


def _lerp(a, b, f):
    """Numbers, or tuples element-wise (so `Offset: 0,0,400 -> 0,0,0` closes in)."""
    if isinstance(a, (tuple, list)):
        return tuple(_lerp(x, y, f) for x, y in zip(a, b))
    v = a + (b - a) * f
    return v if isinstance(a, float) or isinstance(b, float) else int(round(v))


def effect_amd_look(key):
    """What ``key`` resolves to, or None if the name means nothing.

    Returns ``"amd"`` (an authored record), ``"preset"`` (an attachable look from
    the built-in table) or ``"charge"`` (a built-in BUILD-UP: coil, arc, preburn,
    implode, pulse). The order is the contract - an authored record shadows a
    shipped look of the same name.

    All three are answered because all three are nameable: a side writing
    ``Jump Charge: coil`` names a charge look, and a caller asking "does this
    resolve?" has to get a truthful yes for it.
    """
    from .particles import particle_charge_looks
    k = str(key)
    if k in EFFECT_AMD:
        return "amd"
    if particle_preset_get(k) is not None:
        return "preset"
    if k in particle_charge_looks():
        return "charge"
    return None


def effect_amd(key, obj, slot=None, priority=0, at=1.0):
    """Attach a declared look to an object (at its FULL value by default).

    Falls back to a Python preset of the same name when nothing is declared, so a
    caller never has to know which layer a look came from.
    """
    desc = effect_amd_descriptor(key, at)
    if desc is None:
        return particle_effect(obj, str(key), slot=slot or str(key), priority=priority)
    return particle_effect(obj, slot=slot or str(key), priority=priority,
                           **_parse_descriptor(desc))


def effect_amd_burst(key, where, at=1.0):
    """One-shot a declared look at an object or a point."""
    desc = effect_amd_descriptor(key, at)
    if desc is None:
        return particle_burst(where, str(key))
    return particle_burst(where, **_parse_descriptor(desc))


def effect_amd_charge(key, obj, seconds=None, color=None,
                      slot="warp_charge", priority=10):
    """Run a declared look as a BUILD-UP, ramping to its full value.

    A record's own ``Grows over:`` and ``Steps:`` supply the timing unless the caller
    overrides. When the key names no record, this falls through to the built-in
    charge looks (``coil``, ``arc``, ``preburn``, ``implode``, ``pulse``), so
    ``Jump Charge: coil`` works with nothing authored at all.
    """
    spec = EFFECT_AMD.get(str(key))
    if spec is None:
        return particle_charge_start(obj, str(key), seconds=seconds, color=color,
                                     slot=slot, priority=priority)
    return particle_charge_start(
        obj, _register_declared(spec), seconds=seconds or spec["ramp_seconds"],
        color=color, slot=slot, priority=priority, steps=spec["steps"])


def _register_declared(spec):
    """Teach the charge driver a declared look, once, and return its name.

    The driver's table is keyed by name, so an authored record becomes a first-class
    charge look rather than a special case threaded through every call.
    """
    from .particles import _CHARGE_LOOKS
    name = f"amd:{spec['key']}"
    if name not in _CHARGE_LOOKS:
        entry = dict(spec["static"])
        entry["preset"] = spec["preset"]
        entry.update(spec["ramps"])
        color = entry.pop("color", None)
        if color:
            entry["colors"] = (color,)
        _CHARGE_LOOKS[name] = entry
    return name


def _parse_descriptor(desc):
    """A descriptor string back to kwargs, so a declared look can be re-emitted.

    Only ever consumes strings this module built, so it is a straight split rather
    than a parser - values stay strings, which the descriptor builder renders back
    unchanged.
    """
    out = {}
    for part in str(desc).split(";"):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        out[k.strip()] = v.strip()
    return out
