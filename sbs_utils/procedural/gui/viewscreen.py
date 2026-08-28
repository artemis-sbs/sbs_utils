"""The main screen, driven from another console - "on screen" (VIEWSCREEN_PLAN.md).

The captain says "on screen" and somebody has to make it happen. That somebody is
usually science, who already has the thing selected; this is the state layer that lets
them say it.

Two halves. The first decides *who is driving this ship's main screen and what they are
pointing it at*; the second (from "The shots" down) makes the engine agree with that.
The data column that reads out what science knows about the subject is phase 3 and is
not here yet.

THE STATE LIVES ON THE SHIP, not on a console and not in a module global. Cosmos
already keeps ``MAIN_SCREEN_VIEW`` / ``_FACING`` / ``_MODE`` in the player ship's
inventory (``handlerhooks`` writes them on ``main_screen_change``; the mainscreen
label reads them back). Putting the viewer's own keys in the same place buys three
things for free:

* **Scope.** Science on the Artemis cannot change what the Intrepid's screen shows.
* **Reset.** ``Agent.clear()`` takes it, so there is no new container for the restart
  ledger to police.
* **Arbitration.** Helm's engine ``main_screen_control`` widget writes
  ``MAIN_SCREEN_VIEW`` through the same door. Last writer wins, and helm reaching for
  the control is helm taking the screen back - see ``viewscreen_helm_override``.

The arbitration turns on WHO pressed, not on what the values are. Only helm and
weapons carry the ``main_screen_control`` widget, so a ``main_screen_change``
carrying one of this ship's main-screen client ids is that screen reporting back
what we set it to, and anything else is a crew member reaching for the control.
Comparing the reported triple against what the viewer asked for was wrong both
ways round - it swallowed a dial press that happened to match, and it read the
viewer's own cinematic camera as a takeover. See ``viewscreen_helm_override``.

A crew press also starts a short cooldown (``CREW_LOCK_SECONDS``) during which a
console claim is refused, so nothing that re-asserts on a repaint can undo the
press a frame later. A story beat is exempt.
"""
from ...helpers import FrameContext
from ...mast.mast import DEBUG
from ..inventory import get_inventory_value, set_inventory_value
from ..query import to_id, to_object, is_alt_ship_target
from ..signal import signal_emit
from .camera import camera_assign, camera_auto, camera_dolly, camera_move_stop, camera_orbit
from .overlay import (consoles_of, overlay_auto_dwell, overlay_clear, overlay_register,
                      overlay_show, overlay_slot_define)
from .viewscreen_claims import (OWNER_ANON, TIER_CONSOLE, TIER_STORY, viewscreen_baseline,
                                viewscreen_seq,
                                viewscreen_baseline_drop, viewscreen_claim,
                                viewscreen_claim_drop, viewscreen_claimed,
                                viewscreen_hold, viewscreen_hold_drop,
                                viewscreen_hold_take, viewscreen_owner,
                                viewscreen_owns, viewscreen_roster,
                                viewscreen_roster_add, viewscreen_tier,
                                viewscreen_crew_took, viewscreen_crew_holds,
                                viewscreen_crew_lock_remaining,
                                viewscreen_crew_release)
from .viewscreen_pages import viewscreen_pages


# The shots a console can ask for. "off" is not a shot - it is handing the screen back.
MODES = ("off", "dolly", "orbit", "tactical")

# The engine main-screen VIEW each mode needs. Facing and mode (chase/first_person,
# long/short) are deliberately left alone: the viewer has an opinion about WHAT the
# screen shows, not about how the crew had it framed, and a 2D "mode" value the engine
# expects for tactical is not ours to invent.
_MODE_VIEW = {
    "dolly":    "3d_view",
    "orbit":    "3d_view",
    "tactical": "tactical",
}

# Inventory keys on the player ship.
KEY_MODE = "VIEWER_MODE"        # one of MODES
KEY_SUBJECT = "VIEWER_SUBJECT"  # id of what the shot is about, 0 for none
KEY_EXPECT = "VIEWER_EXPECT"    # (view, facing, mode) the viewer last asked the engine for
# Superseded by VIEWER_BASELINE in viewscreen_claims - the ONE record of what the
# crew had. Kept, unwritten, for one release: a mission reading it back gets None
# rather than an import error.
KEY_PRIOR = "VIEWER_PRIOR"

# On the CONSOLE, not the ship - see viewscreen_home_ship.
KEY_HOME = "VIEWER_HOME_SHIP"   # the ship this console belongs to, while a shot has it
KEY_ALT = "VIEWER_ALT_PREV"     # last alt-ship handed to the engine, so we do not re-send
KEY_MY_MODE = "VIEWER_MY_MODE"  # this console's own camera mode - see viewscreen_view_modes

# The running shots: ship id -> {"task", "leg", "prom", "yaw", "cids"}. A module-level
# per-mission container, so it is cleared and audited by the reset ledger.
_VIEWERS = {}

# How the shots are framed and timed. The distances are multiples of the subject's own
# size, so a starbase and a fighter both fill the frame.
FRAME_NEAR = 6.0        # hull radii at the closest point of a push in
FRAME_FAR = 16.0        # hull radii at the widest
FRAME_MIN = 250.0       # never closer than this, whatever the engine says the hull is
DEFAULT_RADIUS = 90.0   # when the engine tells us nothing about the subject's size
DOLLY_SECONDS = 22.0    # one leg: in, then out
ORBIT_SECONDS = 48.0    # one full turn
ORBIT_PITCH = 12.0
DOLLY_YAW = -25.0

# The data column. The SAME rect in both modes: in tactical the radar is reflowed to
# leave this gutter free (LM), in a 3D shot the engine renders full-bleed and the column
# is drawn over it. One geometry to tune, and the crew's eye does not move when the mode
# changes. Layer 21000 is above the view and BELOW hero cards and cutscenes (26000+), so
# a story beat still takes the screen off the viewer.
COLUMN_SLOT = "viewer_data"
COLUMN_RECT = (72.0, 9.0, 99.0, 96.0)
COLUMN_LAYER = 21000
overlay_slot_define(COLUMN_SLOT, COLUMN_RECT, draw_layer=COLUMN_LAYER)


# What a console's drop-down says, and what each label means. Kept HERE rather than in
# the console so the two cannot drift: a console builds its list from
# viewscreen_shot_props() and hands the chosen label straight back to viewscreen_mode_for.
# ASCII only - these are engine-rendered strings.
SHOT_LABELS = (
    ("Off", "off"),
    ("On Screen - Dolly", "dolly"),
    ("On Screen - Orbit", "orbit"),
    ("Tactical 2D", "tactical"),
)


def viewscreen_shot_props(current=None):
    """The whole property string for a shot drop-down.

    The list key is ``list:``, NOT ``items:`` - a dropdown built with the wrong key has
    no options to render and the engine dies allocating for it (`MemoryError: bad
    allocation`), which does not look like a typo from the outside. ``text:`` is the
    label shown while it is closed, so pass what is currently running.
    """
    labels = ",".join(label for label, _mode in SHOT_LABELS)
    return f"text:{current or SHOT_LABELS[0][0]};list:{labels}"


def viewscreen_mode_for(label):
    """The mode a drop-down label means. Unknown labels read as ``off`` - a console
    showing something we do not recognize must not leave the screen commandeered."""
    for text, mode in SHOT_LABELS:
        if text == label:
            return mode
    return "off"


def viewscreen_label_for(mode):
    """The drop-down label for a mode, so a repaint re-selects what is running."""
    for text, m in SHOT_LABELS:
        if m == mode:
            return text
    return SHOT_LABELS[0][0]


def _main_screen_state(ship_id):
    """The engine main-screen triple currently recorded for a ship."""
    return (get_inventory_value(ship_id, "MAIN_SCREEN_VIEW", "3d_view"),
            get_inventory_value(ship_id, "MAIN_SCREEN_FACING", "front"),
            get_inventory_value(ship_id, "MAIN_SCREEN_MODE", "chase"))


def viewscreen_mode(ship):
    """The shot this ship's main screen is running, or ``"off"``."""
    return get_inventory_value(to_id(ship), KEY_MODE, "off")


def viewscreen_subject(ship):
    """The id the shot is about, or 0."""
    return get_inventory_value(to_id(ship), KEY_SUBJECT, 0)


def viewscreen_is_live(ship):
    """Whether a console is currently driving this ship's main screen."""
    return viewscreen_mode(ship) != "off"


def viewscreen_consoles(ship):
    """The main-screen consoles of one ship - the audience every shot addresses.

    Narrowed to the SHIP's own screens, which is what keeps one bridge's viewer out of
    another's. Returns an empty set when no main screen is connected, which is normal
    and not an error.
    """
    return consoles_of(to_id(ship), consoles="mainscreen")


def viewscreen_set(ship, mode, subject=None, owner=None, tier=TIER_CONSOLE):
    """Point this ship's main screen at something.

    Args:
        ship (Agent | int): the player ship whose screen this is.
        mode (str): one of ``MODES``. ``"off"`` is the same as ``viewscreen_clear``.
        subject (Agent | int, optional): what the shot is about - normally the science
            selection. ``None`` means no subject.
        owner (str, optional): the claim token, from ``viewscreen_owner_token``.
            Without one the claim is anonymous - still a claim, but nothing can
            ask whether it is still theirs.
        tier (str): ``"console"`` (the default - a crew member's pick) or
            ``"story"`` (a cutscene, a hail, a mission beat).

    Returns:
        bool: True when the state changed.

    **False now means three things.** It has always meant "already showing exactly
    that"; it also means "a STORY claim holds the screen, so your request was
    PARKED and will be applied when the story releases", and "the crew's own
    control has the screen for another moment" (``CREW_LOCK_SECONDS``). Ask
    ``viewscreen_owns(ship, owner)`` when you need to know which - that is the
    question a console actually has.

    **NEVER CALL THIS FROM A REPAINT PATH UNLESS ``viewscreen_owns`` IS TRUE.**
    The idempotent no-op above requires mode AND subject AND owner to match, so two
    consoles that both re-assert on repaint never hit it - their tokens differ - and
    they will ping-pong at GUI-tick rate, each claim bumping the sequence that makes
    the other repaint. The library cannot break that cycle for you; the crew
    cooldown damps it, but the guard is the caller's. LegendaryMissions' consoles
    are the worked example: every automatic re-point is behind ``viewscreen_owns``,
    and only a human press calls this unguarded.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    if mode not in MODES:
        # Deliberately not an exception: this is reachable from a drop-down, and a
        # console typo should not end the GUI task mid-repaint.
        DEBUG(f"[viewscreen] unknown mode {mode!r}; expected one of {MODES}")
        return False
    if mode == "off":
        return viewscreen_clear(ship_id, owner)

    subject_id = to_id(subject) or 0
    was_live = viewscreen_is_live(ship_id)
    if (was_live and viewscreen_mode(ship_id) == mode
            and viewscreen_subject(ship_id) == subject_id
            and viewscreen_owns(ship_id, owner or OWNER_ANON)):
        return False

    # The claim comes first, and it can be REFUSED - a story beat holds the screen
    # against a console pick. Park the request rather than dropping it: the crew
    # asked for something, and honoring it a few seconds late when the cutscene
    # ends is the answer, not silence.
    if not _claim_for(ship_id, tier, owner):
        viewscreen_hold(ship_id, {"kind": "set", "mode": mode,
                                  "subject": subject_id, "owner": owner,
                                  "tier": tier})
        return False

    view = _MODE_VIEW[mode]
    _view, facing, screen_mode = _main_screen_state(ship_id)
    set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", view)
    set_inventory_value(ship_id, KEY_EXPECT, (view, facing, screen_mode))
    set_inventory_value(ship_id, KEY_MODE, mode)
    set_inventory_value(ship_id, KEY_SUBJECT, subject_id)
    viewscreen_apply(ship_id)
    _announce(ship_id, mode, subject_id)
    return True


def viewscreen_take(ship, owner=None, tier=TIER_STORY):
    """Claim this ship's main screen WITHOUT starting one of the viewer's own shots.

    For anything that drives the screen its own way and still has to be arbitrated:
    a cutscene, the Director, a mission beat pointing the camera by hand. It records
    the crew's view and every main screen's home ship the same way ``viewscreen_set``
    does, so ``viewscreen_restore`` puts the bridge back afterwards - which is what
    a cutscene played during a science shot could not do before, because the only
    thing that captured a baseline was a shot starting.

    Returns:
        bool: False when a story claim already holds the screen and this is a
        console-tier request.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    return _claim_for(ship_id, tier, owner)


def _claim_for(ship_id, tier, owner):
    """Take the claim, capturing the crew's state on the way in.

    ONE capture, covering the engine triple AND every main screen's home ship.
    Those used to be recorded by two different functions on two different
    triggers - the triple here, the homes inside ``viewscreen_apply`` and only on
    its 3D branch - which is a large part of why "what the crew had" kept going
    missing.
    """
    cids = viewscreen_consoles(ship_id)
    if not viewscreen_claimed(ship_id):
        _remember_home(ship_id, cids)
    return viewscreen_claim(ship_id, tier, owner,
                            baseline=_main_screen_state(ship_id),
                            cids=cids)


def viewscreen_clear(ship, owner=None):
    """Hand the screen back, restoring the view the crew had before it was taken.

    Args:
        owner (str, optional): refuse unless this token still holds the claim, so
            a console whose shot was replaced cannot take the screen off whoever
            replaced it. ``None`` forces.

    Returns:
        bool: True if a viewer was running.
    """
    return viewscreen_restore(ship, owner)


def viewscreen_restore(ship, owner=None):
    """THE DOOR HOME. Put this ship's main screen back the way the crew had it.

    Drops the claim, stops the shot, takes the viewer's own overlays down, gives
    every main screen its own ship back, restores the baseline view, and then -
    and only then - applies whatever crew request was parked behind a story beat.

    The ORDER is load-bearing, twice:

    * **Assignments before the triple.** The assignment decides what a console can
      SEE; the triple only decides its widget list. Restore the triple first and
      the main-screen label re-runs while the console is still riding the subject,
      so it picks its widgets from the SUBJECT's ``MAIN_SCREEN_VIEW`` - the hazard
      ``gui_console`` documents.
    * **The parked request last.** Applying it claims the screen again and
      captures a baseline; it has to capture the RESTORED one, not the story's.

    Args:
        owner (str, optional): refuse unless this token still holds the claim.
            ``None`` forces - what a console transition and a reset want.

    Returns:
        bool: True if anything was holding the screen.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    if not viewscreen_claimed(ship_id) and not viewscreen_is_live(ship_id):
        return False
    if owner is not None and not viewscreen_owns(ship_id, owner):
        DEBUG(f"[viewscreen] {owner!r} tried to release {ship_id}, which "
              f"{viewscreen_owner(ship_id)!r} holds")
        return False

    # The seq bump lives inside this, and it happens BEFORE anything below runs -
    # hail.py's rule, so a second releaser in the same frame is already stale.
    # keep_baseline because the teardown is about to read it.
    viewscreen_claim_drop(ship_id, None, keep_baseline=True)
    return _stand_down(ship_id, restore=True)


def viewscreen_helm_override(ship, view, facing, mode, client_id=None):
    """Helm or weapons touched the engine's main-screen control.

    Called from the ``main_screen_change`` handler with the triple the engine just
    reported. What happens next depends on WHO holds the screen:

    * **A console claim** - science's "on screen", weapons', docking's - stands
      down, and nothing is restored: helm's choice IS the new state, and putting a
      recorded "before" back over the top would undo the very change being handled.
      Any request parked behind a story beat is thrown away too; helm just spoke,
      and a stale drop-down pick firing later would override the officer who
      overrode it.
    * **A story claim** - a cutscene, a hail, a mission beat - does NOT stand down.
      The crew's press is PARKED and applied when the story releases, so it is
      honored a few seconds late rather than lost, and the story's own triple is
      written back so the engine and the record agree again.

    **WHO pressed decides, not what the values are.** Only helm and weapons carry
    the ``main_screen_control`` widget; a main screen's widget list is
    ``3dview^ship_data`` / ``2dview^ship_data``, so a main screen cannot press one
    at all - every ``main_screen_change`` carrying a main screen's client id is
    that screen reporting back what we set it to. So an event from one of this
    ship's main screens is never a takeover, and an event from anywhere else
    always is.

    Comparing the reported triple against ``VIEWER_EXPECT`` instead was wrong in
    both directions, and each cost a real bug:

    * **The dial forces the view back to 3D.** Touching FRONT or CHASE means "show
      me that camera", so during a 3D shot it sends ``("3d_view", facing, mode)``
      - which is exactly what the shot recorded. Helm's press was read as a replay
      and swallowed; the engine moved the camera anyway (the flash), and the shot
      that was never stood down re-aimed it a moment later. Reported as science
      stealing the screen back.
    * **The shot cancelled itself.** Every shot goes through
      ``gui_cinematic_full_control``, which calls ``set_main_view_modes(cid,
      "3dview", "front", "cinematic")``. Coming back as an event that matches
      nothing, it read as a takeover - the viewer's own camera standing the viewer
      down.

    ``client_id=None`` keeps the old value comparison, for a caller that cannot say
    who pressed.

    The triple is written here as well as by the caller. ``handlerhooks`` already
    records it (issue #595) and writing it twice is harmless - but a function whose
    postcondition depends on the caller having gone first is a trap for the next
    caller, so this one leaves the ship in the state it was told about either way.
    On the story path that means writing the story's triple BACK over what the
    caller just recorded, which is the whole point.

    Returns:
        bool: True if a claim was stood down. False for a story claim that held -
        see ``viewscreen_effective_state`` for what the screen is actually showing
        afterwards, which is what the reroute has to carry.
    """
    ship_id = to_id(ship)
    # Logged unconditionally, and before the guards: "did the engine even fire one of
    # these, and carrying what" is the first question every time this misbehaves, and it
    # is unanswerable after the fact otherwise.
    DEBUG(f"[viewscreen] main_screen_change on {ship_id} from {client_id}: "
          f"{(view, facing, mode)} "
          f"(viewer={viewscreen_mode(ship_id) if ship_id else '?'}, "
          f"owner={viewscreen_owner(ship_id) if ship_id else '?'}, "
          f"tier={viewscreen_tier(ship_id) if ship_id else '?'}, "
          f"expected={get_inventory_value(ship_id, KEY_EXPECT, None) if ship_id else '?'})")
    if ship_id is None:
        return False
    if not viewscreen_claimed(ship_id) and not viewscreen_is_live(ship_id):
        return False
    expect = get_inventory_value(ship_id, KEY_EXPECT, None)
    if client_id is not None:
        if client_id in viewscreen_consoles(ship_id):
            # The screen telling us what it is showing, which is what we told it.
            return False
    elif expect is not None and tuple(expect) == (view, facing, mode):
        # No client id to judge by: fall back to the old value comparison.
        return False

    if viewscreen_tier(ship_id) == TIER_STORY:
        # Park it, and put the story's own triple back. The caller wrote the crew's
        # triple a moment ago (handlerhooks does that first, and must keep doing it
        # for issue #595), so without this write the ship's record says one thing
        # and the screen shows another.
        DEBUG(f"[viewscreen] {viewscreen_owner(ship_id)!r} holds {ship_id} for the "
              f"story; parking the crew's {(view, facing, mode)} until it releases")
        viewscreen_hold(ship_id, {"kind": "helm", "triple": (view, facing, mode)})
        if expect is not None:
            e_view, e_facing, e_mode = expect
            set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", e_view)
            set_inventory_value(ship_id, "MAIN_SCREEN_FACING", e_facing)
            set_inventory_value(ship_id, "MAIN_SCREEN_MODE", e_mode)
        return False

    # Say why. A viewer that vanishes on its own is the hardest kind of bug to report -
    # "it was working and then it stopped" - and the answer is always in this comparison.
    DEBUG(f"[viewscreen] helm override on {ship_id}: asked for {expect}, "
          f"engine reported {(view, facing, mode)}; standing down")
    viewscreen_hold_drop(ship_id)
    viewscreen_claim_drop(ship_id, None, keep_baseline=True)
    # BEFORE the stand-down, not after. _announce is synchronous - signal_emit
    # starts the task and ticks it in context - so a listener like LM's
    # `on signal viewscreen` re-runs the whole main-screen label from INSIDE
    # _stand_down. Writing the crew's triple afterwards meant that repaint read
    # whatever was there before, and it only worked at all because handlerhooks
    # happens to write the same three keys first.
    set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", view)
    set_inventory_value(ship_id, "MAIN_SCREEN_FACING", facing)
    set_inventory_value(ship_id, "MAIN_SCREEN_MODE", mode)
    viewscreen_crew_took(ship_id)
    return _stand_down(ship_id, restore=False)


def viewscreen_effective_state(ship):
    """What this ship's main screen is ACTUALLY set to, after arbitration.

    ``handlerhooks`` writes the crew's triple, then asks
    ``viewscreen_helm_override`` what to do with it, and then fans a reroute out to
    the ship's main screens carrying the EVENT's values as task variables. When a
    story claim refused the press, those values are the rejected ones - so the
    reroute has to carry this instead, or a console reading the injected
    ``MAIN_SCREEN_VIEW`` sees a view the library declined to apply.

    LegendaryMissions reads the ship's inventory rather than the injected variable,
    so LM would not show this - which is exactly what makes it easy to ship broken.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return None
    return _main_screen_state(ship_id)


def _stand_down(ship_id, restore):
    """Tear the shot down. The claim is already dropped by the time this runs."""
    if ship_id is None:
        return False
    # The consoles first: this hands back the camera, the assignment and the 2D focus,
    # and the state written below is what tells the rest of the system it is over.
    _viewer_stop(ship_id, release=False)
    _release_consoles(ship_id)
    if restore:
        baseline = viewscreen_baseline(ship_id)
        if baseline is not None:
            view, facing, mode = baseline
            set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", view)
            set_inventory_value(ship_id, "MAIN_SCREEN_FACING", facing)
            set_inventory_value(ship_id, "MAIN_SCREEN_MODE", mode)
    viewscreen_baseline_drop(ship_id)
    set_inventory_value(ship_id, KEY_MODE, "off")
    set_inventory_value(ship_id, KEY_SUBJECT, 0)
    set_inventory_value(ship_id, KEY_EXPECT, None)
    _announce(ship_id, "off", 0)
    # LAST, and only now: the screen is back the way the crew had it, so a request
    # parked behind a story beat captures THAT as its baseline.
    _apply_held(ship_id)
    return True


def _apply_held(ship_id):
    """Fire the crew request that was parked behind a story claim, if any."""
    held = viewscreen_hold_take(ship_id)
    if not held:
        return False
    kind = held.get("kind")
    if kind == "helm":
        view, facing, mode = held.get("triple")
        DEBUG(f"[viewscreen] applying the crew's parked view {(view, facing, mode)} "
              f"on {ship_id}")
        set_inventory_value(ship_id, "MAIN_SCREEN_VIEW", view)
        set_inventory_value(ship_id, "MAIN_SCREEN_FACING", facing)
        set_inventory_value(ship_id, "MAIN_SCREEN_MODE", mode)
        return True
    if kind == "set":
        subject = held.get("subject") or 0
        if subject and to_object(subject) is None:
            # The contact they asked for died during the beat. Nothing to show,
            # and picking a different one is a directing decision.
            DEBUG(f"[viewscreen] dropping a parked shot on {ship_id}: its subject "
                  f"{subject} is gone")
            return False
        return viewscreen_set(ship_id, held.get("mode"), subject,
                              owner=held.get("owner"),
                              tier=held.get("tier", TIER_CONSOLE))
    return False


# --- The shots ---------------------------------------------------------------
# Phase 2. Everything above decides WHAT the screen should be showing; this makes the
# engine agree with it.
#
# THE ASSIGNMENT IS THE THING TO KNOW. `camera_track` assigns a console to the object
# the lens rides, because the engine only honors a camera change when the two match -
# so while a shot runs, a main screen is assigned to the SUBJECT, which may well be
# somebody else's ship. Two consequences, both handled here:
#
#   * ``sbs.get_ship_of_client`` on that console no longer returns its own ship. Use
#     ``viewscreen_home_ship``.
#   * View culling follows the assigned object - which for a viewer is what you want
#     (the thing being looked at has to be rendered), but it is not nothing.
#
# Standing down puts the assignment back.

def viewscreen_home_ship(client_id):
    """The ship a console BELONGS to, even while a shot has it assigned elsewhere.

    Anything that means "this console's own ship" must ask this rather than
    ``sbs.get_ship_of_client``, which during a shot answers with the subject.
    """
    home = get_inventory_value(client_id, KEY_HOME, None)
    if home:
        return home
    return FrameContext.context.sbs.get_ship_of_client(client_id)


def viewscreen_console_enter(client_id):
    """A main screen is arriving. Record where it belongs, before anything moves it.

    THE FIRST LINE of any main-screen label. A shot ASSIGNS its console to the
    subject, so a console that takes its post while one is already running has no
    record of its own ship and nothing can give it back - and there is exactly one
    moment when the answer is still available, which is before this console is
    assigned anywhere.

    Cheap and idempotent: a console that already has a home recorded is left alone,
    so putting this at the top of a label that repaints constantly costs nothing.

    Returns:
        int | None: the ship this console belongs to.
    """
    home = viewscreen_home_ship(client_id)
    if not home:
        return None
    if viewscreen_claimed(home) or viewscreen_is_live(home):
        _remember_home(home, [client_id])
    return home


def viewscreen_view_modes(client_id, ship_id=None):
    """The ``(view, facing, mode)`` a main screen should hand ``set_main_view_modes``.

    The view and facing belong to the SHIP - one bridge, one screen state. The
    camera MODE does not, quite: the engine reports ``"cinematic"`` while a script
    is driving that client's camera, and because the three arrive together that
    value lands in the ship's record and every other main screen on the bridge then
    reads it as its own.

    So the mode is remembered PER CONSOLE and substituted whenever the ship's copy
    says ``"cinematic"``. LegendaryMissions carried this as a task-local
    ``default my_mode = "chase"``, which is per GUI TASK rather than per console -
    so every reroute reset it, and a screen the crew had put in ``first_person`` or
    ``tracking`` silently snapped back to ``chase``.

    Returns:
        tuple: ``(view, facing, mode)``, ready to pass straight through.
    """
    if ship_id is None:
        ship_id = viewscreen_home_ship(client_id)
    view, facing, mode = _main_screen_state(ship_id)
    if mode == "cinematic":
        mode = get_inventory_value(client_id, KEY_MY_MODE, "chase")
    else:
        set_inventory_value(client_id, KEY_MY_MODE, mode)
    return (view, facing, mode)


def viewscreen_dial_label(ship, owner):
    """What an "On Screen" drop-down should read, for the console that owns ``owner``.

    **The running shot only when it is OURS, otherwise "Off".** The dial is this
    console's control, not a status light for the ship: showing "On Screen - Orbit"
    because WEAPONS put something up invites science to think they are driving,
    and picking Off on it would then be refused - so the dial would be advertising
    an action it cannot take.

    One function rather than the expression written out on each console, so the two
    cannot drift, the same reason ``viewscreen_shot_props`` lives here.
    """
    if not viewscreen_owns(ship, owner):
        return viewscreen_label_for("off")
    return viewscreen_label_for(viewscreen_mode(ship))


def viewscreen_revision(client_id):
    """A number that changes whenever this console's ship hands the screen over.

    What a console watches with ``on change`` so a drop-down showing "On Screen -
    Orbit" repaints to "Off" the moment somebody else takes the screen, instead of
    lying about what is on it.

    ``on change``, not ``on signal``: a GUI task sitting in ``await gui()`` does not
    repaint because a signal fired - the same reason ``hail_console_revision``
    exists and is polled.
    """
    return viewscreen_seq(viewscreen_home_ship(client_id))


def viewscreen_framing(subject):
    """``(near, far)`` lens distances for a subject.

    Scaled off the hull's own size, so a starbase and a fighter both fill the frame
    rather than one being a speck and the other clipping the lens. ``exclusion_radius``
    is the only size the engine actually exposes; when it says nothing, a default that
    frames a mid-sized ship is better than a guess that frames nothing.
    """
    radius = DEFAULT_RADIUS
    obj = to_object(subject)
    eo = obj.space_object() if obj is not None else None
    r = getattr(eo, "exclusion_radius", 0.0) or 0.0
    if r > 0:
        radius = float(r)
    near = max(FRAME_MIN, radius * FRAME_NEAR)
    far = max(near * 1.6, radius * FRAME_FAR)
    return near, far


def viewscreen_apply(ship):
    """Make the engine match the recorded state. Safe to call repeatedly.

    This is the one place that touches cameras, so a console that connects late, a
    repaint, or a fresh ``viewscreen_set`` all arrive at the same behavior by calling it.

    Returns:
        int: how many consoles the shot is running on.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return 0
    mode = viewscreen_mode(ship_id)
    cids = viewscreen_consoles(ship_id)
    if mode == "off" or not cids:
        _viewer_stop(ship_id)
        return 0

    subject = viewscreen_subject(ship_id)
    if to_object(subject) is None and mode != "tactical":
        # Nothing to look at. Standing down is the honest answer - the library will not
        # pick a different subject, which is a directing decision it cannot make.
        viewscreen_clear(ship_id)
        return 0

    if mode == "tactical":
        # A 2D shot is not a camera move: the widget list changes (the mainscreen label
        # re-runs on the signal) and the radar is pointed at the subject. Coming from a
        # 3D shot, the console has to get its own ship back first - a radar centered on
        # the enemy is not what "tactical" means.
        _viewer_stop(ship_id)
        _restore_home(cids)
        for cid in cids:
            _alt_ship(cid, subject)
    else:
        _remember_home(ship_id, cids)
    _viewer_start(ship_id, mode, subject, cids)
    return len(cids)


def viewscreen_reset():
    """Drop every running shot WITHOUT touching the engine - for mission reset.

    The tick tasks are already gone by then (``TickDispatcher.clear()``), and the
    clients these records name belong to a sim that is being torn down, so re-assigning
    their cameras is at best pointless. This just stops the records outliving the
    mission that made them.
    """
    _VIEWERS.clear()


def _remember_home(ship_id, cids):
    """Record each console's own ship before a shot takes the assignment away.

    The VALUE goes on the console, because `viewscreen_home_ship(client_id)` has
    only a client id to work with. The MEMBERSHIP goes on the ship, because a
    restore has to reach consoles that have since stopped being this ship's main
    screens - a console that changed console mid-shot still needs its ship back.
    """
    sbs = FrameContext.context.sbs
    for cid in cids:
        if not get_inventory_value(cid, KEY_HOME, None):
            set_inventory_value(cid, KEY_HOME, sbs.get_ship_of_client(cid))
        viewscreen_roster_add(ship_id, cid)


def _restore_home(cids):
    """Give each console its own ship back.

    A home that no longer exists is dropped rather than re-assigned. It can be a
    camera object rather than a player ship - a Game Master or Director console
    rides one deliberately - and one deleted between capture and restore would be
    re-assigned in silence by the mock while the real engine falls back to its own
    default view.
    """
    for cid in cids:
        home = get_inventory_value(cid, KEY_HOME, None)
        if home:
            if to_object(home) is None:
                DEBUG(f"[viewscreen] console {cid} cannot go home: {home} is gone")
            else:
                camera_assign(cid, home)
            set_inventory_value(cid, KEY_HOME, None)
        _alt_ship(cid, 0)


def _alt_ship(cid, focus_id):
    """Point a console's 2D view at another object, at most once per change.

    Same shape as ``comms_set_2dview_focus`` - including the "did we already send this"
    latch, because the engine call is not free - but without the ``2d_follow`` gate:
    that flag is a science/comms CHECKBOX, and a main screen has no checkbox. Science
    choosing the shot is the intent.
    """
    focus_id = focus_id or 0
    if get_inventory_value(cid, KEY_ALT, 0) == focus_id:
        return
    # See is_alt_ship_target: a subject that is not a space object kills the client.
    # Imported here rather than at module scope - procedural.execution reaches back into
    # the gui package, and this module is already deep in that import chain.
    if not is_alt_ship_target(focus_id):
        from ..execution import log
        log(f"viewscreen subject {focus_id} is not a space object; not showing it", "viewscreen", "warning")
        return
    FrameContext.context.sbs.assign_client_to_alt_ship(cid, focus_id)
    set_inventory_value(cid, KEY_ALT, focus_id)


def _viewer_start(ship_id, mode, subject, cids):
    """Begin (or re-begin) the running viewer: the moving shot, and the data column.

    ONE record and ONE ticker for both, because they are one thing to the crew and
    because a tactical shot has a column but no camera - two bookkeepers would mean two
    chances to leave one of them running.
    """
    _viewer_stop(ship_id, release=False)
    from ...tickdispatcher import TickDispatcher
    record = {"ship": ship_id, "mode": mode, "subject": subject, "cids": list(cids),
              "leg": 0, "yaw": 0.0, "prom": None, "task": None,
              "page": 0, "shown": None, "page_at": 0.0, "dwell": 0.0}
    _VIEWERS[ship_id] = record
    if mode != "tactical":
        _next_leg(record)
    _column_update(record, force=True)
    # One check a second, not one a tick: this notices that a leg or a page has run out.
    # The camera move itself is driven at full rate by the camera's own driver.
    record["task"] = TickDispatcher.do_interval(lambda t: _advance(ship_id, t), 1)


def _viewer_stop(ship_id, release=True):
    """Stop the moving shot.

    ``release=False`` when one shot is REPLACING another: the new shot re-points the
    same consoles a moment later, and handing them back in between would clear the home
    ship it is about to need - which stranded a console on the subject when a dolly
    followed an orbit.
    """
    record = _VIEWERS.pop(ship_id, None)
    if record is None:
        return False
    task = record.get("task")
    if task is not None:
        task.stop()
    cids = record["cids"]
    # Both sets: the consoles the shot started on (one may have changed console
    # since and no longer answers to "mainscreen") and whoever holds that role
    # now (one may have joined mid-shot and been caught up).
    overlay_clear(COLUMN_SLOT, to=set(cids) | viewscreen_consoles(ship_id))
    camera_move_stop(cids)
    if release:
        camera_auto(cids)
    return True


def _release_consoles(ship_id):
    """Hand every one of this ship's main screens back: engine director, own ship, no
    2D focus.

    Separate from ``_shots_stop`` because a TACTICAL shot keeps no camera record at all
    and still has something to undo - the alt-ship focus. Standing down has to be one
    call that covers both, or 2D shots leak their focus.
    """
    # The ROSTER as well as the current main screens: a console that changed
    # console mid-shot is no longer in the second set and still has our assignment.
    cids = set(viewscreen_consoles(ship_id)) | set(viewscreen_roster(ship_id))
    if cids:
        camera_move_stop(cids)
        camera_auto(cids)
    _restore_home(cids)


def _advance(ship_id, task):
    """Start the next leg once the current one has run out."""
    record = _VIEWERS.get(ship_id)
    if record is None or record.get("task") not in (None, task):
        task.stop()
        return
    if to_object(record["subject"]) is None:
        # The subject was destroyed mid-shot. The engine drops to its own default view
        # rather than freezing, so there is nothing to hold on to.
        viewscreen_clear(ship_id)
        return
    if record["mode"] != "tactical":
        prom = record.get("prom")
        if prom is None or prom.done():
            _next_leg(record)
    _column_update(record)


def _next_leg(record):
    """One leg of the loop: a push in or out, or one turn of the orbit.

    Legs rather than one endless move because both shots have a natural length, and a
    loop made of finite legs recovers by itself - if a leg is cut short (subject gone,
    another console stealing the camera) the next tick just starts the next one.
    """
    near, far = viewscreen_framing(record["subject"])
    cids = record["cids"]
    if record["mode"] == "orbit":
        yaw = record["yaw"]
        record["prom"] = camera_orbit(cids, record["subject"], far, from_yaw=yaw,
                                      to_yaw=yaw + 360.0, seconds=ORBIT_SECONDS,
                                      pitch=ORBIT_PITCH)
        # Carry the angle over so the next turn starts where this one ended - a loop
        # that restarted at 0 would whip back round on every lap.
        record["yaw"] = (yaw + 360.0) % 360.0
    else:
        # Ping-pong: in, then out. A push that cut back to wide each time would read as
        # a jump cut every 22 seconds.
        a, b = (far, near) if record["leg"] % 2 == 0 else (near, far)
        record["prom"] = camera_dolly(cids, record["subject"], a, b, yaw=DOLLY_YAW,
                                      pitch=ORBIT_PITCH, seconds=DOLLY_SECONDS)
    record["leg"] += 1


# --- The data column ---------------------------------------------------------
# What science knows about the thing on screen, in the gutter beside it, paging itself
# when there is more than one screenful. The pages themselves are pure functions living
# in viewscreen_pages.py; this is only the surface and the clock.

def _column_builder(client_id, content):
    """One page of the column: a heading-and-body text area, plus a position dot row."""
    from .row import gui_row
    from .text import gui_text, gui_text_area

    text = content.get("text") or ""
    count = int(content.get("count") or 1)
    index = int(content.get("index") or 0)

    gui_row("row-height: 100-1.4em; background: #0009;")
    gui_text_area(text, "padding: 8px;")
    if count > 1:
        # Dots, not "3 / 7". It is a viewscreen, not a form - the crew needs to know
        # more is coming, not to count it.
        dots = " ".join("*" if i == index else "-" for i in range(count))
        gui_row("row-height: 1.4em; background: #0009;")
        gui_text(f"$text:{dots};justify:center;color:#8cf;")


overlay_register(COLUMN_SLOT, _column_builder)


def _column_pages(record):
    return viewscreen_pages(record["subject"], record["ship"])


def _column_update(record, force=False):
    """Re-render the column, advancing the page when the current one has had its time.

    Called once a second. Two things happen here, and they are deliberately separate:

    * the page ADVANCES when its dwell has run out and there is more than one page;
    * the current page is re-shown whenever its TEXT has changed, which is what keeps a
      live value (range, shields) live on a single-page column that never advances.

    Nothing is sent when neither happened - the guard is the text itself, so an
    unchanged column costs one page render a second and no engine traffic.
    """
    pages = _column_pages(record)
    if not pages:
        if record["shown"] is not None:
            overlay_clear(COLUMN_SLOT,
                          to=set(record["cids"]) | viewscreen_consoles(record["ship"]))
            record["shown"] = None
        return False

    now = FrameContext.sim_seconds or 0.0
    index = record["page"]
    if index >= len(pages):
        index = 0
    if (not force and len(pages) > 1
            and (now - record["page_at"]) >= record["dwell"]):
        index = (index + 1) % len(pages)

    name, text = pages[index]
    if not force and index == record["page"] and text == record["shown"]:
        return False

    if index != record["page"] or force:
        record["page_at"] = now
        record["dwell"] = overlay_auto_dwell(text)
    record["page"] = index
    record["shown"] = text
    # THE SHIP, NARROWED TO ITS MAIN SCREENS - not the frozen id list this shot
    # started with. An overlay record re-resolves its audience once a second, so
    # a bare list of ids means the catch-up keeps re-delivering the science data
    # column to a console that has since become Helm: the id is still literally
    # in the audience, whatever role it now holds, and no clear on that console
    # holds. Addressed this way the console simply drops out of the audience.
    overlay_show(COLUMN_SLOT, COLUMN_SLOT, to=record["ship"], consoles="mainscreen",
                 text=text, index=index, count=len(pages), page=name)
    return True


def _announce(ship_id, mode, subject_id):
    """Tell the mainscreen consoles the state changed.

    One signal for every transition, including standing down, so the listener is a
    single route rather than one per verb. The work it triggers (camera, column) is
    server-side, so the route that does it is ``//shared/signal/viewscreen`` - five
    consoles must not start five orbits.
    """
    signal_emit("viewscreen", {"VIEWSCREEN_SHIP": ship_id,
                               "VIEWSCREEN_MODE": mode,
                               "VIEWSCREEN_SUBJECT": subject_id})
