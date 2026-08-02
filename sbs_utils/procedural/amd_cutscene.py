"""Declarative cutscenes and rundowns from AMD - a shot is a RECORD.

One heading per shot, grouped by ``Scene:`` (a cutscene) or ``Rundown:`` (a set the
director punches between). A shot is an ordinary AMD record, so the existing reader,
lint, schema and typed widgets all work on it unchanged - and because Phase 3 and
Phase 4 already share one ``shot_apply``, both get AMD from this one loader::

    # [Chapter One](intro)
    ---
    Kind: cutscene
    Letterbox: yes
    Skippable: yes
    ---

    ## [Establish Phoenix](intro_1)
    ---
    Scene: intro
    Subject: station
    Eye: 0, 900, -4000
    Seconds: 4
    Overlay: lower_third
    Name: Phoenix Control
    ---
    All quiet on the belt.

    ## [Push in on Artemis](intro_2)
    ---
    Scene: intro
    Subject: hero
    Move: 0,400,-3000 -> 0,120,-600
    Seconds: 6
    ---

Shots play in DOCUMENT ORDER unless they carry ``Order:``; the body is the overlay's
primary text, exactly as in ``amd_overlay``.

**Subjects resolve late, and that is the whole difficulty.** A shot names a live
object, and no object exists when the ``.amd`` loads - so ``Subject: hero`` is looked
up as, in order:

1. a **cast** the mission bound (``cutscene_cast("hero", artemis)``) - the film idiom,
   and the one that survives a scene being reused with a different ship;
2. failing that, the **role** ``hero``, for the ad-hoc case;
3. failing both, the shot is dropped and the reason is logged NAMING THE SHOT - a
   cutscene that silently skipped a shot is far worse than one that says why.
"""
from ..helpers import FrameContext
from .amd_doc import amd_records
from .gui.cutscene import cutscene_define, cutscene_play
from .gui.rundown import rundown_add
from .gui.overlay import _KIND_PRIMARY_FIELD


# key -> {"key", "bed", "shots": [...], "display"} for a cutscene
CUTSCENE_AMD = {}
# key -> [shot, ...] for a rundown
RUNDOWN_AMD = {}
# cast name -> object/id, bound by the mission before it plays anything
CUTSCENE_CAST = {}


def cutscene_cast(name, obj=None):
    """Bind (or read) a cast name used by ``Subject:`` in AMD shots.

    The film idiom: the script says "hero", the production decides who that is. It
    also means one scene can be replayed with a different ship without touching the
    ``.amd``.
    """
    if obj is not None:
        CUTSCENE_CAST[str(name)] = obj
    return CUTSCENE_CAST.get(str(name))


def cutscene_cast_clear():
    CUTSCENE_CAST.clear()


def _log(message):
    try:
        from .execution import log
        log(message, "cutscene", "warning")
    except Exception:
        pass


def _resolve_subject(name, shot_key=""):
    """Cast first, then a role, else None (and say which shot, and why)."""
    if not name:
        _log(f"cutscene shot {shot_key!r} has no Subject - shot dropped")
        return None
    key = str(name).strip()
    if key in CUTSCENE_CAST:
        return CUTSCENE_CAST[key]
    from .roles import role
    from .query import to_object_list
    members = to_object_list(role(key))
    if members:
        return members[0].id
    _log(f"cutscene shot {shot_key!r}: Subject {key!r} is neither cast nor a role "
         f"- shot dropped")
    return None


def _vec(text):
    """`0, 900, -4000` -> (0.0, 900.0, -4000.0). None when it will not parse."""
    if text is None:
        return None
    if isinstance(text, (list, tuple)):
        return tuple(float(v) for v in text[:3])
    parts = [p for p in str(text).replace(";", ",").split(",") if p.strip()]
    if len(parts) != 3:
        return None
    try:
        return tuple(float(p.strip()) for p in parts)
    except ValueError:
        return None


def _move(text):
    """`0,400,-3000 -> 0,120,-600` -> [from, to]. None when it will not parse."""
    if text is None:
        return None
    if isinstance(text, (list, tuple)) and len(text) == 2:
        return [_vec(text[0]), _vec(text[1])]
    for sep in ("->", "=>", " to "):
        if sep in str(text):
            a, b = str(text).split(sep, 1)
            va, vb = _vec(a), _vec(b)
            return [va, vb] if va and vb else None
    return None


def _num(v, default=None):
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return default


_SHOT_FIELDS = ("scene", "rundown", "subject", "eye", "move", "seconds", "ease",
                "order", "overlay", "slot", "label")


def _shot_from(rec):
    """Build a shot dict from an AMD record. Subject stays a NAME here and is
    resolved at play time - the object does not exist at load."""
    data = rec.get("data") or {}
    shot = {
        "key": rec.get("key"),
        "label": data.get("label") or rec.get("display") or rec.get("key"),
        "subject_name": data.get("subject"),
        "eye": _vec(data.get("eye")),
        "move": _move(data.get("move")),
        "seconds": _num(data.get("seconds"), 4),
        "ease": (data.get("ease") or "in_out").strip(),
        "order": _num(data.get("order")),
    }
    kind = data.get("overlay")
    if kind:
        kind = str(kind).strip().lower()
        # Everything not a shot field belongs to the overlay, so a kind's own
        # fields (Name:, Color:, Face:) are authored right beside the shot.
        fields = {k: v for k, v in data.items() if k not in _SHOT_FIELDS}
        prim = _KIND_PRIMARY_FIELD.get(kind, "title")
        body = (rec.get("body") or "").strip()
        if prim not in fields and body:
            fields[prim] = body
        fields["kind"] = kind
        if data.get("slot"):
            fields["slot"] = data.get("slot")
        shot["overlay"] = fields
    return shot


def amd_cutscenes(section):
    """Load every cutscene, shot and rundown in ``section``.

    Returns ``{"cutscenes": {...}, "rundowns": {...}}``. A record with
    ``Kind: cutscene`` is a bed; a record with ``Scene:`` or ``Rundown:`` is a shot.
    """
    beds = {}
    scenes = {}
    rundowns = {}
    for rec in amd_records(section):
        data = rec.get("data") or {}
        key = rec.get("key")
        if not key:
            continue
        kind = str(data.get("kind") or "").strip().lower()
        if kind == "cutscene":
            beds[key] = {
                "letterbox": _truthy(data.get("letterbox"), True),
                "skippable": _truthy(data.get("skippable"), True),
                "release": _truthy(data.get("release"), True),
                "bar": _num(data.get("bar"), 4),
                "display": rec.get("display"),
            }
            continue
        shot = _shot_from(rec)
        if data.get("scene"):
            scenes.setdefault(str(data["scene"]).strip(), []).append(shot)
        elif data.get("rundown"):
            rundowns.setdefault(str(data["rundown"]).strip(), []).append(shot)

    for name, shots in scenes.items():
        # DOCUMENT ORDER unless a shot says otherwise. Sorting is stable, so shots
        # without an Order keep their position relative to each other.
        shots.sort(key=lambda s: s["order"] if s["order"] is not None else 1e9)
        bed = beds.get(name, {})
        CUTSCENE_AMD[name] = {"key": name, "shots": shots, "bed": bed,
                              "display": bed.get("display") or name}
    for name, shots in rundowns.items():
        shots.sort(key=lambda s: s["order"] if s["order"] is not None else 1e9)
        RUNDOWN_AMD[name] = shots
    return {"cutscenes": dict(CUTSCENE_AMD), "rundowns": dict(RUNDOWN_AMD)}


def _truthy(v, default):
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "yes", "y", "true", "on")


def _playable(shots):
    """Resolve subjects NOW (the objects exist by the time we play) and drop the
    shots that cannot be resolved, each with a reason."""
    out = []
    for shot in shots:
        subject = _resolve_subject(shot.get("subject_name"), shot.get("key"))
        if subject is None:
            continue
        playable = {k: v for k, v in shot.items()
                    if k in ("eye", "move", "seconds", "ease", "overlay", "label")}
        playable["subject"] = subject
        out.append(playable)
    return out


def cutscene_amd(key, to=None, consoles=None, **overrides):
    """Play a cutscene declared in AMD. Returns the Promise, or None if unknown."""
    rec = CUTSCENE_AMD.get(key)
    if rec is None:
        _log(f"cutscene {key!r} is not declared in any loaded AMD")
        return None
    shots = _playable(rec["shots"])
    bed = dict(rec["bed"])
    bed.pop("display", None)
    bed.update(overrides)
    cutscene_define(key, shots, **bed)
    return cutscene_play(key, to=to, consoles=consoles)


def rundown_amd(key):
    """Load a declared rundown's shots into the live rundown. Returns how many."""
    shots = RUNDOWN_AMD.get(key)
    if shots is None:
        _log(f"rundown {key!r} is not declared in any loaded AMD")
        return 0
    n = 0
    for shot in _playable(shots):
        rundown_add(shot.get("label") or f"shot{n}", shot["subject"],
                    eye=shot.get("eye"), move=shot.get("move"),
                    seconds=shot.get("seconds", 4), ease=shot.get("ease", "in_out"),
                    label=shot.get("label"), overlay=shot.get("overlay"))
        n += 1
    return n


def amd_cutscene_clear():
    """Drop every loaded cutscene/rundown/cast - the per-mission reset."""
    CUTSCENE_AMD.clear()
    RUNDOWN_AMD.clear()
    CUTSCENE_CAST.clear()
