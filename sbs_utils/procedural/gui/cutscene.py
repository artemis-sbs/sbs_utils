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
        {"subject": station, "lens": (0, 900, -4000), "seconds": 4,
         "overlay": {"kind": "lower_third", "name": "Phoenix", "line": "Standing by."}},
        {"subject": hero, "move": [(0, 400, -3000), (0, 120, -600)], "seconds": 6},
    ])
    result = await cutscene_play("intro", to=role("mainscreen"))
    if result["skipped"]:
        ...
"""
from ...helpers import FrameContext
from .viewscreen import viewscreen_restore, viewscreen_take
from .camera import (camera_assignment, camera_auto, camera_dolly, camera_move,
                     camera_move_stop, camera_orbit_lens, camera_restore, camera_shot)
from .overlay import consoles_of, overlay_clear, overlay_kind
from .viewscreen_claims import TIER_STORY

# Bare, not per-console: a cutscene is a beat the whole bridge is watching, and
# cutscene_play already stops any other cutscene on the same consoles first.
CUTSCENE_OWNER = "cutscene"


def _cutscene_bridges(cids):
    """The PLAYER SHIPS whose main screens this cutscene is playing to.

    viewscreen_home_ship, not get_ship_of_client - a console mid-shot is riding the
    contact it is filming. And player ships only: a Game Master or Director console
    rides a detached camera object deliberately, and a claim on one of those would
    be bookkeeping about a bridge that does not exist.
    """
    from ..roles import has_role
    from .viewscreen import viewscreen_home_ship
    ships = set()
    for cid in cids:
        try:
            home = viewscreen_home_ship(cid)
        except Exception:                                   # noqa: BLE001
            continue
        if home and has_role(home, "__player__"):
            ships.add(home)
    return ships
from .viewscreen import ORBIT_PITCH, viewscreen_framing


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
            the lens rides; ``framing`` (``close``/``medium``/``wide``, or a two-item
            list for a move) OR ``lens`` (world position) OR ``move`` ([from, to]);
            ``seconds`` (default 4); ``ease``; ``yaw``/``pitch``; ``overlay``
            ({"kind": ..., plus that kind's fields}).
            Prefer ``framing``: it scales to the subject's hull, so one shot frames a
            runabout and a starbase alike. ``lens``/``move`` are world POSITIONS and
            so also depend on where the subject is parked.
        letterbox (bool): black bars for the duration.
        skippable (bool): whether ``cutscene_skip`` ends it.
        bar (float): letterbox bar height in em.
        release (bool): at the end, put each console back on the object it was riding
            and hand the camera to the engine's director.
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


#: Every key a shot may carry. A shot built in PYTHON gets no lint and no schema - the
#: AMD loader validates its own records, but `cutscene_play([{...}])` from a mission .py
#: is checked by nothing at all. That is the path the framing bug travelled: a camera
#: field the library did not implement would have been ignored in silence.
SHOT_KEYS = frozenset(("subject", "framing", "yaw", "pitch", "lens", "move", "seconds",
                       "ease", "overlay", "label", "name", "key", "order",
                       "transition", "subject_name"))


def _warn_unknown_shot_keys(shot):
    """One warning naming any key `shot_apply` will ignore."""
    stray = sorted(k for k in shot if k not in SHOT_KEYS)
    if not stray:
        return
    from ..execution import log
    who = shot.get("label") or shot.get("name") or shot.get("key") or "?"
    log(f"shot {who}: {stray} is not a shot field, so it was ignored. To frame a shot "
        f"use framing=close/medium/wide, which sizes itself to the subject.",
        "cutscene", "warning")


#: What a named shot size means, in the subject's own hull radii. The numbers are not
#: here - they come from `viewscreen_framing`, which is where they already lived.
SHOT_SIZES = ("close", "medium", "wide")


def cutscene_framing(subject, size="medium"):
    """How far the lens sits for a named shot size, scaled to the subject's own hull.

    A DISTANCE TYPED BY HAND FRAMES EXACTLY ONE SHIP. The subjects a mission points a
    camera at are not one size: across the TNG pack a B'Rel is 25 units of hull radius
    and Deep Space Nine is 220, and a planet is 10,000. One coordinate triple makes the
    big one overflow the frame and the small one a speck, which is precisely the report
    this exists to answer.

    So the distance is read off the subject instead. `viewscreen_framing` already does
    that arithmetic - 6 hull radii at the closest, 16 at the widest, floored at 250 so
    the engine reporting a tiny hull cannot put the lens inside it - and the Director
    has framed its shots that way since it deleted its own distance sliders, on the
    grounds that "a fixed number framed a starbase and a fighter equally badly".

    `medium` is the midpoint rather than a fourth constant, so there is still exactly
    one place these numbers are written down.

    Args:
        subject: the object the shot looks at.
        size (str): ``close``, ``medium`` or ``wide``. Anything else is treated as
            ``medium`` - a misspelled size should give a usable shot, not no shot.

    Returns:
        float: distance from the subject, in world units.
    """
    near, far = viewscreen_framing(subject)
    if size == "close":
        return near
    if size == "wide":
        return far
    return (near + far) / 2.0


def shot_apply(cids, shot):
    """Put one shot on these consoles. Returns its move Promise, or None.

    THE definition of a shot, shared by the cutscene sequencer and the rundown, so
    "a shot" means one thing in both: a subject, where the lens sits (or travels),
    and optional furniture. The slots it used come back on the returned set so a
    caller can clear exactly what it put up.

    A shot says where the lens goes in ONE of two ways:

    * ``framing`` - a named size (``close``/``medium``/``wide``), or a two-item list
      for a move (``["wide", "close"]`` is a push in). The distance is derived from the
      subject's hull, so the same shot frames a runabout and a starbase alike, and it
      does not depend on where either happens to be parked.
    * ``lens`` / ``move`` - literal WORLD POSITIONS, unchanged and still supported.
      Note these are positions, not offsets: a subject sitting 7,000 units from the
      origin is framed 7,000 units differently than the same shot at the origin, which
      is the trap `framing` exists to close.
    """
    _warn_unknown_shot_keys(shot)
    seconds = float(shot.get("seconds", 4))
    subject = shot.get("subject")
    framing = shot.get("framing")
    move = None
    if framing:
        yaw = float(shot.get("yaw", 0.0))
        pitch = float(shot.get("pitch", ORBIT_PITCH))
        if isinstance(framing, (list, tuple)):
            # A MOVE, through camera_dolly rather than camera_move. Dolly holds the angle
            # and changes only the distance, recomputing from wherever the subject is each
            # tick; camera_move interpolates between two fixed world points, so a subject
            # under way outruns the shot and a push in ends as a fly past.
            a = cutscene_framing(subject, framing[0])
            b = cutscene_framing(subject, framing[-1])
            move = camera_dolly(cids, subject, a, b, yaw=yaw, pitch=pitch,
                                seconds=seconds, ease=shot.get("ease", "in_out"))
        else:
            # A held shot. camera_shot wants a world position, so turn the distance into
            # one at apply time - it stores the difference as an offset, which is what
            # keeps the framing while the subject moves.
            from ..query import to_object
            subj = to_object(subject)
            offset = camera_orbit_lens(cutscene_framing(subject, framing), yaw, pitch)
            base = subj.pos if subj is not None else None
            if base is None:
                camera_shot(cids, subject, offset)
            else:
                camera_shot(cids, subject,
                            (base.x + offset.x, base.y + offset.y, base.z + offset.z))
    elif shot.get("move"):
        a, b = shot["move"][0], shot["move"][1]
        move = camera_move(cids, subject, a, b, seconds,
                           ease=shot.get("ease", "in_out"))
    elif shot.get("lens") is not None:
        camera_shot(cids, subject, shot["lens"])
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
        # WHAT EACH CONSOLE WAS RIDING BEFORE THE FIRST SHOT TOOK IT.
        #
        # Captured here, before start_shot assigns anything. A shot ASSIGNS its
        # console to the object the lens rides, and that assignment outlives the
        # cutscene: releasing to the engine director afterwards leaves it following
        # whatever the last shot was on. A trial whose reveal held on a station ended
        # with the mainscreen watching the station instead of the crew ship, while
        # the trials whose reveal fell back to the hero looked fine - which is why it
        # read as one broken mission rather than a missing rule.
        self.held = camera_assignment(cids)
        # AND the claim, per bridge. A cutscene is a story beat: while it runs, a
        # science or weapons "on screen" pick is parked rather than applied, and
        # helm's main-screen control does not cut it short. Claimed per SHIP because
        # one cutscene can play to several bridges at once and each one's crew had
        # its own view to go back to.
        #
        # This is also what makes `camera_assignment` above correct: taking the claim
        # captures each console's home ship, so a cutscene starting during a viewer
        # shot restores the bridge rather than leaving it on the contact science was
        # filming.
        self.ships = _cutscene_bridges(cids)
        for ship_id in self.ships:
            viewscreen_take(ship_id, CUTSCENE_OWNER, TIER_STORY)

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
            # Give the console its own ship back, THEN release. camera_auto alone
            # hands control to a director that keeps following the shot subject.
            if not camera_restore(self.held):
                camera_auto(self.cids)
        # Release AFTER the camera is back: restoring puts each bridge's recorded
        # view on the record, and a parked crew request fires off the back of it.
        # Refused for any bridge something else has since claimed, which is the point
        # of naming the owner.
        for ship_id in getattr(self, "ships", ()):
            viewscreen_restore(ship_id, CUTSCENE_OWNER)
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
