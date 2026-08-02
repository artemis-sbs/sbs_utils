"""Phase 4 — the rundown and the director punch (the streaming layer).

A rundown is **not** a cutscene. A cutscene is a sequence that plays itself; a rundown
is a named set of *available* shots that a human chooses between, live. Same shot dicts
(``shot_apply``), so a shot means one thing everywhere.

The broadcast idiom, which maps onto what the engine gives us with nothing left over:

* **PROGRAM** — the feed the audience/stream sees.
* **PREVIEW** — what the director is lining up next, on their own console.
* **TAKE** — put preview on program. Cuts SNAP (engine-observed), so a take is one
  call and needs no hold-off; anything fancier is faked with a one-frame ``flash``,
  because the engine cannot dissolve.
* **TALLY** — which shot is live, so the director's list can mark it. Without this a
  punch is ambiguous the moment two shots look alike.

**Auto-suggest is director assist, not autopilot.** The engine's own cinematic camera
follows an "excitement" value, and that value lives on the object as the data_set key
``exciting`` — so a rundown can RANK its shots by how interesting their subjects are and
highlight the one worth punching to. It never punches on its own: the whole point of a
rundown is that a person is choosing.

    rundown_add("wide",  station, eye=(0, 4000, -9000))
    rundown_add("hero",  artemis, eye=(0, 120, -420))
    rundown_program(role("mainscreen"))
    rundown_punch("hero")            # live now
    rundown_suggest()                # -> "wide", if the station is where the action is

The director's CONSOLE is a mission's job, not the library's - `rundown_tiles()` returns
everything such a screen needs (label, live, staged, excitement) so it can be drawn with
ordinary widgets.
"""
from .camera import camera_auto
from .cutscene import shot_apply, shot_furniture
from .overlay import consoles_of, overlay_clear, overlay_kind


# name -> shot dict (plus "label"). Insertion-ordered, which IS the rundown order.
_SHOTS = {}

# The desks. Audiences, not client ids, so a rundown can feed a role.
_DESK = {"program": None, "preview": None, "live": None, "staged": None,
         "slots": set()}


def rundown_add(name, subject, eye=None, move=None, seconds=4, ease="in_out",
                label=None, overlay=None):
    """Add (or replace) a shot in the rundown.

    Args:
        name (str): how the director refers to it.
        subject: what the shot looks at - and necessarily what the lens rides.
        eye: world position for a static shot.
        move: ``[from, to]`` world positions for a moving one.
        seconds (float): duration of a ``move`` (a static shot holds until punched away).
        label (str, optional): what the director's tile says. Defaults to ``name``.
        overlay (dict, optional): furniture to show with it, ``{"kind": ..., ...}``.

    Returns:
        dict: the stored shot.
    """
    shot = {"name": name, "label": label or name, "subject": subject,
            "eye": eye, "move": move, "seconds": seconds, "ease": ease,
            "overlay": overlay}
    _SHOTS[name] = shot
    return shot


def rundown_remove(name):
    """Drop a shot. If it was live, the tally is cleared - the feed does not change,
    because pulling a shot out of a list is not a directing decision."""
    if _DESK["live"] == name:
        _DESK["live"] = None
    if _DESK["staged"] == name:
        _DESK["staged"] = None
    return _SHOTS.pop(name, None) is not None


def rundown_clear():
    """Empty the rundown and both desks."""
    _SHOTS.clear()
    _DESK.update({"program": None, "preview": None, "live": None,
                  "staged": None, "slots": set()})


def rundown_shots():
    """Every shot, in rundown order."""
    return list(_SHOTS.values())


def rundown_get(name):
    return _SHOTS.get(name)


def rundown_program(to=None, consoles=None):
    """Set (or read) the PROGRAM audience - the feed everyone sees."""
    if to is not None:
        _DESK["program"] = list(consoles_of(to, consoles))
    return _DESK["program"]


def rundown_preview(to=None, consoles=None):
    """Set (or read) the PREVIEW audience - the director's own console."""
    if to is not None:
        _DESK["preview"] = list(consoles_of(to, consoles))
    return _DESK["preview"]


def rundown_live():
    """The name of the shot on PROGRAM, or None. This is the tally."""
    return _DESK["live"]


def rundown_staged():
    """The name of the shot on PREVIEW, or None."""
    return _DESK["staged"]


def _apply(cids, shot, clear_slots):
    if clear_slots:
        for slot in _DESK["slots"]:
            overlay_clear(slot, to=cids)
        _DESK["slots"] = set()
    shot_apply(cids, shot)
    _DESK["slots"] |= shot_furniture(cids, shot)


def rundown_punch(name, flash=False):
    """Put a shot on PROGRAM. Returns True if it went live.

    A cut, because the engine only cuts. ``flash`` fakes a transition with a
    one-frame flash overlay - the only "effect" available, and it is honest about
    being a fake rather than pretending to dissolve.
    """
    shot = _SHOTS.get(name)
    cids = _DESK["program"]
    if shot is None or not cids:
        return False
    if flash:
        overlay_kind("flash", to=cids, seconds=0.25)
    _apply(cids, shot, clear_slots=True)
    _DESK["live"] = name
    return True


def rundown_stage(name):
    """Line a shot up on PREVIEW without touching PROGRAM. Returns True if staged."""
    shot = _SHOTS.get(name)
    if shot is None:
        return False
    _DESK["staged"] = name
    cids = _DESK["preview"]
    if cids:
        # Preview gets the camera but NOT the furniture: a director wants to see the
        # framing, and duplicating the lower third onto their screen tells them
        # nothing they do not already know from the tile.
        shot_apply(cids, shot)
    return True


def rundown_take(flash=False):
    """Punch what is on PREVIEW. The broadcast take. Returns the name, or None."""
    name = _DESK["staged"]
    if name is None:
        return None
    if not rundown_punch(name, flash=flash):
        return None
    return name


def rundown_release():
    """Hand PROGRAM back to the engine's own director and clear the tally.

    The end-of-show path - and the one to call BEFORE deleting anything a shot was
    riding, since a deleted dolly drops the view to the engine default.
    """
    cids = _DESK["program"]
    if not cids:
        return 0
    for slot in _DESK["slots"]:
        overlay_clear(slot, to=cids)
    _DESK["slots"] = set()
    _DESK["live"] = None
    return camera_auto(cids)


def rundown_excitement(name):
    """How interesting this shot's subject is right now.

    Reads the engine's own ``exciting`` value - the same notion its automatic
    cinematic camera follows - so a suggestion agrees with what the engine would
    have picked, rather than being a second opinion invented here.
    """
    from ..query import to_object
    shot = _SHOTS.get(name)
    if shot is None:
        return 0.0
    obj = to_object(shot.get("subject"))
    if obj is None:
        return 0.0
    try:
        return float(obj.data_set.get("exciting", 0) or 0.0)
    except Exception:
        return 0.0


def rundown_suggest(exclude_live=True):
    """The shot worth punching to, or None. **Assist, never autopilot.**

    Args:
        exclude_live (bool): skip whatever is already live, since suggesting the
            shot the director is already on is noise.
    """
    best, best_v = None, 0.0
    for name in _SHOTS:
        if exclude_live and name == _DESK["live"]:
            continue
        v = rundown_excitement(name)
        if v > best_v:
            best, best_v = name, v
    return best


def rundown_tiles():
    """Everything a director's console needs to draw the rundown.

    A list of ``{name, label, live, staged, suggested, excitement}`` in rundown
    order. Returned as DATA so the console is a mission's to design - this layer
    has no opinion about what a tile looks like.
    """
    suggested = rundown_suggest()
    out = []
    for name, shot in _SHOTS.items():
        out.append({
            "name": name,
            "label": shot.get("label") or name,
            "live": name == _DESK["live"],
            "staged": name == _DESK["staged"],
            "suggested": name == suggested,
            "excitement": rundown_excitement(name),
        })
    return out
