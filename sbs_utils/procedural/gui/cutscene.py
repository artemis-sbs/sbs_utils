"""Phase 3 — shots and cutscenes, as DATA.

A **shot** is a subject, where the lens sits, how long it holds, and optionally some
furniture. A **cutscene** is an ordered list of shots plus a bed (letterbox, skip).
Both are plain dicts, matching where this project has gone with AMD: the movie-script
stays a movie-script and the timeline *consumes* it rather than growing control flow
into it.

This phase adds **no drawing**. The furniture is the existing overlay kinds, and the
camera work is Phase 2's mover. All it contributes is sequencing — which is exactly
where the engine's shape has to be respected:

* **Cuts SNAP** (engine-observed). There is no blend to wait out, so a shot change is
  a single call and a skip is instant.
* **A deleted dolly drops the view on the engine's default** (a top-down on a
  station), so teardown order is a rule: the camera is released BEFORE anything the
  caller is about to delete. `camera_move` also ends early if its subject dies, and a
  cutscene treats that as "this shot is over" rather than stalling on a dead id.
* **Skip is a first-class path.** A cutscene a bridge crew cannot skip is a bug
  report, so it is a parameter, not something a caller races by hand.

    cutscene_define("intro", [
        {"subject": station, "eye": (0, 900, -4000), "seconds": 4,
         "overlay": {"kind": "lower_third", "name": "Phoenix", "line": "Standing by."}},
        {"subject": hero, "move": [(0, 400, -3000), (0, 120, -600)], "seconds": 6},
    ])
    result = await cutscene_play("intro", to=role("mainscreen"))
    if result["skipped"]:
        ...
"""
from ...helpers import FrameContext
from .camera import camera_auto, camera_move, camera_move_stop, camera_shot
from .overlay import consoles_of, overlay_clear, overlay_kind


# name -> cutscene dict. Authoring data, but still per-mission: a reload must not
# inherit the previous story's scenes.
_CUTSCENES = {}

# client_id -> the _Playing driving that console.
_PLAYING = {}


def cutscene_define(name, shots, letterbox=True, skippable=True, bar=4,
                    release=True):
    """Register a cutscene under ``name``.

    Args:
        name (str): what ``cutscene_play`` will look up.
        shots (list[dict]): in order. Per shot:
            ``subject`` (required) - what the shot looks at, and necessarily what
            the lens rides; ``eye`` (world position) OR ``move`` ([from, to]);
            ``seconds`` (default 4); ``ease``; ``overlay`` ({"kind": ..., plus that
            kind's fields}).
        letterbox (bool): black bars for the duration.
        skippable (bool): whether ``cutscene_skip`` ends it.
        bar (float): letterbox bar height in em.
        release (bool): hand the camera back to the engine's director at the end.
            Leave it True unless the next thing the story does is set its own shot -
            a cutscene that ends still holding a dolly will drop to the engine
            default the moment that object is deleted.

    Returns:
        dict: the stored cutscene.
    """
    scene = {"name": name, "shots": list(shots or []), "letterbox": letterbox,
             "skippable": skippable, "bar": bar, "release": release}
    _CUTSCENES[name] = scene
    return scene


def cutscene_get(name):
    """The stored cutscene, or None."""
    return _CUTSCENES.get(name)


def shot_apply(cids, shot):
    """Put one shot on these consoles. Returns its move Promise, or None.

    THE definition of a shot, shared by the cutscene sequencer and the rundown, so
    "a shot" means one thing in both: a subject, where the lens sits (or travels),
    and optional furniture. The slots it used come back on the returned set so a
    caller can clear exactly what it put up.
    """
    seconds = float(shot.get("seconds", 4))
    subject = shot.get("subject")
    move = None
    if shot.get("move"):
        a, b = shot["move"][0], shot["move"][1]
        move = camera_move(cids, subject, a, b, seconds,
                           ease=shot.get("ease", "in_out"))
    elif shot.get("eye") is not None:
        camera_shot(cids, subject, shot["eye"])
    return move


def shot_furniture(cids, shot):
    """Show a shot's overlay, if it has one. Returns the slots it used."""
    slots = set()
    furniture = shot.get("overlay")
    if not furniture:
        return slots
    fields = dict(furniture)
    kind = fields.pop("kind", None)
    slot = fields.pop("slot", None)
    if kind:
        from .overlay import _KIND_DEFAULT_SLOT
        slots.add(slot or _KIND_DEFAULT_SLOT.get(kind, "center_hero"))
        overlay_kind(kind, to=cids, slot=slot, **fields)
    return slots


class _Playing:
    """One cutscene running on one set of consoles."""

    def __init__(self, scene, cids, prom):
        self.scene = scene
        self.cids = cids
        self.prom = prom
        self.index = -1
        self.until = 0.0
        self.move = None
        self.skipped = False
        self.task = None
        self.slots = set()

    # --- shots ----------------------------------------------------------
    def start_shot(self, shot):
        self.move = shot_apply(self.cids, shot)
        # Remembered so teardown clears exactly what the cutscene put up, and
        # nothing a console had of its own.
        self.slots |= shot_furniture(self.cids, shot)
        self.until = FrameContext.sim_seconds + float(shot.get("seconds", 4))

    def advance(self):
        self.index += 1
        shots = self.scene["shots"]
        if self.index >= len(shots):
            self.finish(skipped=False)
            return
        self.start_shot(shots[self.index])

    def tick(self, _t):
        if self.skipped:
            self.finish(skipped=True)
            return
        # A move that resolved EARLY means its subject died - that shot is over,
        # whatever the clock says. Waiting out its remaining seconds would hold the
        # story on a frame the engine has already thrown away.
        if self.move is not None and self.move.done():
            self.advance()
            return
        if FrameContext.sim_seconds >= self.until:
            self.advance()

    def finish(self, skipped):
        if self.task is not None:
            self.task.stop()
            self.task = None
        camera_move_stop(self.cids)
        for slot in self.slots:
            overlay_clear(slot, to=self.cids)
        if self.scene["letterbox"]:
            overlay_clear("fullscreen", to=self.cids)
        # BEFORE the caller deletes anything: a dolly deleted while the camera is
        # still on it drops the view to the engine default.
        if self.scene["release"]:
            camera_auto(self.cids)
        for cid in self.cids:
            if _PLAYING.get(cid) is self:
                _PLAYING.pop(cid, None)
        if not self.prom.done():
            # Never None - Promise.done() tests `_result is not None`, so a None
            # result is indistinguishable from never having resolved.
            self.prom.set_result({"skipped": bool(skipped),
                                  "shots": max(0, self.index),
                                  "name": self.scene["name"]})


def cutscene_play(name_or_shots, to=None, consoles=None, **overrides):
    """Play a cutscene and return a Promise that resolves when it ends.

    Args:
        name_or_shots: a name from ``cutscene_define``, or a list of shots to play
            without registering one.
        to: audience (see ``consoles_of``).
        **overrides: any ``cutscene_define`` field, for this run only.

    Returns:
        Promise: resolves with ``{"skipped": bool, "shots": int, "name": str}``.
    """
    from ...futures import Promise
    from ...tickdispatcher import TickDispatcher

    if isinstance(name_or_shots, str):
        scene = _CUTSCENES.get(name_or_shots)
        if scene is None:
            scene = cutscene_define(name_or_shots, [])
    else:
        scene = cutscene_define("", name_or_shots)
    if overrides:
        scene = dict(scene)
        scene.update(overrides)

    prom = Promise()
    cids = list(consoles_of(to, consoles))
    if not cids:
        prom.set_result({"skipped": False, "shots": 0, "name": scene["name"]})
        return prom

    # One cutscene per console: a second would fight the first for the camera, and
    # the loser's teardown would clear the winner's furniture.
    cutscene_stop(cids)

    play = _Playing(scene, cids, prom)
    for cid in cids:
        _PLAYING[cid] = play
    if scene["letterbox"]:
        overlay_kind("letterbox", to=cids, slot="fullscreen", bar=scene["bar"])
    play.task = TickDispatcher.do_interval(play.tick, 0)
    play.advance()          # the first shot starts NOW, not a tick from now
    return prom


def cutscene_skip(to=None, consoles=None):
    """Skip a running cutscene. Returns how many consoles were skipped.

    A no-op on a cutscene defined as unskippable, so a global skip button can be
    wired once and left alone.
    """
    n = 0
    seen = set()
    for cid in consoles_of(to, consoles):
        play = _PLAYING.get(cid)
        if play is None or id(play) in seen:
            continue
        seen.add(id(play))
        if not play.scene["skippable"]:
            continue
        play.skipped = True
        play.finish(skipped=True)
        n += 1
    return n


def cutscene_stop(to=None, consoles=None):
    """Stop a running cutscene without honouring ``skippable`` - the teardown path.

    Resolves its promise as skipped, so a story awaiting it still continues.
    """
    n = 0
    seen = set()
    for cid in consoles_of(to, consoles):
        play = _PLAYING.get(cid)
        if play is None or id(play) in seen:
            continue
        seen.add(id(play))
        play.finish(skipped=True)
        n += 1
    return n


def cutscene_playing(to=None, consoles=None):
    """Whether a cutscene is running on any of these consoles."""
    for cid in consoles_of(to, consoles):
        if _PLAYING.get(cid) is not None:
            return True
    return False
