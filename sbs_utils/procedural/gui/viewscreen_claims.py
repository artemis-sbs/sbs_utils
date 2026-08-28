"""Who holds a ship's main screen, and what the crew had before they took it.

The main screen used to have one driver. It now has several, and they did not know
about each other: science's "on screen" drop-down, the same drop-down on weapons,
an incoming hail, docking, a cutscene, the Director, and helm or weapons reaching
for the engine's own main-screen control. Each of them kept its OWN private note
of what the screen looked like before - ``VIEWER_PRIOR`` here, ``HAIL_TOOK_VIEWER``
in the hail system, ``_Playing.held`` in cutscenes, ``WEAP_VIEWER_SUBJECT`` in
LegendaryMissions' weapons console, nothing at all in the rundown. Those notes
overwrote each other, so once two of them had both taken the screen, nobody was
holding the state the crew actually started from and there was no way back.

This is that one place. Three ideas, and nothing more:

* **A named owner.** A claim carries a token - ``"science:<client_id>"``,
  ``"hail"``, ``"docking"`` - so a console can ask *"is this still mine?"* instead
  of hand-rolling a private flag, and so a console that lost the screen can repaint
  its drop-down to Off rather than lying about what is showing.
* **One baseline.** The crew's ``(view, facing, mode)`` and each main screen's home
  ship, captured ONCE on the way from unclaimed to claimed. It is the only record
  of "before" in the system, and it is what everything restores to.
* **Two tiers.** ``console`` (science, weapons, docking) and ``story`` (a cutscene,
  a hail, a mission beat). Helm's engine control drops a console claim - helm's
  choice simply IS the new state - but not a story one. A crew press that arrives
  during a story beat is PARKED and applied when the story releases, so it is
  honored late rather than lost.

**Flat, last-writer-wins - not a stack.** A new claim replaces the previous one
entirely; releasing it goes back to the crew's baseline, never to whatever the
previous claimant was showing. That is a deliberate choice and the thing most
readers assume wrong.

THE STATE LIVES ON THE SHIP, in agent inventory, for the reasons ``viewscreen``
already gives: science on the Artemis cannot touch the Intrepid's screen,
``Agent.clear()`` takes it at mission reset, and there is no new module-level
container for the restart ledger to police.

This module is a LEAF on purpose - it imports inventory, query and helpers and
nothing else. It knows who holds the screen; it does not know what a camera is.
``viewscreen.py`` is the half that makes the engine agree.

The file name is PLURAL and the function is singular, deliberately. A submodule
sharing a name with a function the package exports is SHADOWED by it, so
``from ...gui import viewscreen_claim`` would hand back the function and anything
scanning "the module" would quietly scan a function instead. ``hail_gui`` is named
that way for the same reason; ``viewscreen_pages`` is the one that got away with it.
"""
from ...mast.mast import DEBUG
from ..inventory import get_inventory_value, set_inventory_value
from ..query import to_id


# The tiers, weakest first. A tier is a string rather than a number because it is
# read back out of ship inventory and shown in logs; the ORDER lives in this tuple.
TIER_CONSOLE = "console"
TIER_STORY = "story"
VIEWSCREEN_TIERS = (TIER_CONSOLE, TIER_STORY)

# Inventory keys on the player ship.
KEY_OWNER = "VIEWER_CLAIM_OWNER"        # the token, "" when unclaimed
KEY_TIER = "VIEWER_CLAIM_TIER"          # "" | "console" | "story"
KEY_SEQ = "VIEWER_CLAIM_SEQ"            # monotonic; bumped BEFORE every outcome
KEY_BASELINE = "VIEWER_BASELINE"        # (view, facing, mode) the crew had; None = uncaptured
KEY_BASELINE_CIDS = "VIEWER_BASELINE_CIDS"   # the consoles that have a home recorded
KEY_HELD = "VIEWER_HELD"                # one parked crew request

# What an unnamed claim is called. `viewscreen_set(ship, mode, subject)` still
# works exactly as it did, and an unnamed claim is still a claim - it simply
# cannot be asked "is it mine".
OWNER_ANON = "viewscreen"


def viewscreen_owner_token(kind, client_id=None):
    """The owner token for a claimant.

    Per-CONSOLE for anything a crew member drives (``science``, ``weapons``), bare
    for anything the ship has one of (``hail``, ``docking``). Two science consoles
    on one bridge are two different claimants; one bridge has only one docking.
    """
    if client_id is None:
        return str(kind)
    return "%s:%s" % (kind, client_id)


def viewscreen_owner(ship):
    """Who holds this ship's main screen, or ``""``."""
    return get_inventory_value(to_id(ship), KEY_OWNER, "") or ""


def viewscreen_tier(ship):
    """``"console"``, ``"story"``, or ``""`` when nothing holds the screen."""
    return get_inventory_value(to_id(ship), KEY_TIER, "") or ""


def viewscreen_claimed(ship):
    """Whether anything holds this ship's main screen."""
    return bool(viewscreen_tier(ship))


def viewscreen_owns(ship, owner):
    """Is ``owner``'s claim still the live one?

    The question a console should ask before acting on the screen it thinks it is
    driving. LegendaryMissions' weapons console hand-rolled this as a private
    ``WEAP_VIEWER_SUBJECT`` inventory value, and science never asked at all - which
    is why science re-pointing on a new selection used to yank a shot weapons had
    set up.
    """
    return bool(owner) and viewscreen_owner(ship) == owner


def viewscreen_seq(ship):
    """The claim sequence, bumped on every claim and every release.

    Poll it to notice the screen changed hands. Bumped BEFORE the outcome runs, the
    same rule ``hail.py`` follows, so a second actor in the same frame is already
    carrying a stale value by the time it arrives.
    """
    return get_inventory_value(to_id(ship), KEY_SEQ, 0) or 0


def viewscreen_baseline(ship):
    """The ``(view, facing, mode)`` the crew had before anyone took the screen."""
    return get_inventory_value(to_id(ship), KEY_BASELINE, None)


def viewscreen_held(ship):
    """The crew request parked behind a story claim, or None."""
    return get_inventory_value(to_id(ship), KEY_HELD, None)


def viewscreen_bump(ship):
    """Advance the sequence. Call BEFORE the outcome, never after."""
    ship_id = to_id(ship)
    if ship_id is None:
        return 0
    seq = (get_inventory_value(ship_id, KEY_SEQ, 0) or 0) + 1
    set_inventory_value(ship_id, KEY_SEQ, seq)
    return seq


def viewscreen_claim(ship, tier=TIER_CONSOLE, owner=None, baseline=None,
                     cids=None):
    """Record that ``owner`` holds this ship's main screen.

    Bookkeeping only - it does not move a camera or write a main-screen view. The
    caller (``viewscreen_set``, a cutscene, the Director) does that; this decides
    whether it is allowed to and remembers what to go back to.

    Args:
        ship: the player ship whose screen this is.
        tier (str): ``"console"`` or ``"story"``.
        owner (str, optional): the token from ``viewscreen_owner_token``. An
            unnamed claim is still a claim.
        baseline (tuple, optional): the ``(view, facing, mode)`` to record if this
            is the first claim. Captured by the caller because only it can read the
            engine state.
        cids (iterable, optional): the main screens whose home ship the caller has
            recorded, noted alongside the baseline on the first claim.

    Returns:
        bool: True if the claim was taken. False when a STORY claim holds and this
        is a console one - the caller should park its request rather than act.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    if tier not in VIEWSCREEN_TIERS:
        # Reachable from a drop-down; a typo must not end a GUI task mid-repaint.
        DEBUG("[viewscreen] unknown tier %r; expected one of %r" % (tier, VIEWSCREEN_TIERS))
        return False

    held_tier = viewscreen_tier(ship_id)
    if held_tier == TIER_STORY and tier != TIER_STORY:
        DEBUG("[viewscreen] %s refused on %s: %r holds the screen for the story"
              % (owner or OWNER_ANON, ship_id, viewscreen_owner(ship_id)))
        return False

    viewscreen_bump(ship_id)
    _baseline_capture(ship_id, baseline, cids)
    set_inventory_value(ship_id, KEY_OWNER, owner or OWNER_ANON)
    set_inventory_value(ship_id, KEY_TIER, tier)
    return True


def viewscreen_claim_drop(ship, owner=None, keep_baseline=False):
    """Give up the claim. Bookkeeping only - see ``viewscreen_restore``.

    Args:
        owner (str, optional): refuse unless this token still holds it. ``None``
            forces, which is what a mission reset and the one-door console
            transition want.
        keep_baseline (bool): leave the baseline recorded. Only ``True`` while a
            caller is in the middle of applying it.

    Returns:
        bool: True if a claim was dropped.
    """
    ship_id = to_id(ship)
    if ship_id is None or not viewscreen_claimed(ship_id):
        return False
    if owner is not None and viewscreen_owner(ship_id) != owner:
        # A stale releaser must not take the screen off a NEWER claimant. This is
        # the same shape as hail_answer refusing a press whose seq has moved on.
        DEBUG("[viewscreen] %r tried to release %s, which %r holds"
              % (owner, ship_id, viewscreen_owner(ship_id)))
        return False
    viewscreen_bump(ship_id)
    set_inventory_value(ship_id, KEY_OWNER, "")
    set_inventory_value(ship_id, KEY_TIER, "")
    if not keep_baseline:
        _baseline_drop(ship_id)
    return True


def viewscreen_hold(ship, request):
    """Park a crew request that arrived while a story held the screen.

    ONE request, not a queue: the crew pressing three things during a cutscene
    means they want the last one, and replaying all three on release would walk the
    screen through states nobody asked to see.
    """
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    set_inventory_value(ship_id, KEY_HELD, request)
    return True


def viewscreen_hold_take(ship):
    """Take the parked request, clearing it. Returns None when there is none."""
    ship_id = to_id(ship)
    if ship_id is None:
        return None
    held = get_inventory_value(ship_id, KEY_HELD, None)
    if held is not None:
        set_inventory_value(ship_id, KEY_HELD, None)
    return held


def viewscreen_hold_drop(ship):
    """Throw the parked request away.

    What helm's control does on a console-tier claim: helm just spoke, and a stale
    drop-down pick firing later would override the officer who overrode it.
    """
    ship_id = to_id(ship)
    if ship_id is not None:
        set_inventory_value(ship_id, KEY_HELD, None)


# --- the baseline -----------------------------------------------------------
# ONE capture, ONE restore. Before this the two halves lived in different
# functions with different triggers - the triple in `viewscreen_set`, the console
# home ships in `viewscreen_apply`, and only on its 3D branch - which is a large
# part of why "what the crew had" kept going missing.

def _baseline_capture(ship_id, baseline, cids):
    """Record the crew's state, once, on the way from unclaimed to claimed.

    The sentinel is the BASELINE being unset, not ``viewscreen_is_live``. A story
    claim never sets a viewer mode, so asking whether a shot is running would let a
    second capture through - and a second capture overwrites the crew's own state
    with whatever the first claimant had put up.
    """
    if get_inventory_value(ship_id, KEY_BASELINE, None) is not None:
        return False
    if baseline is not None:
        set_inventory_value(ship_id, KEY_BASELINE, tuple(baseline))
    if cids:
        set_inventory_value(ship_id, KEY_BASELINE_CIDS, sorted(set(cids)))
    return True


def viewscreen_roster(ship):
    """The main screens that have a home recorded for this claim.

    Held on the SHIP while the home VALUE is held on each console, and that split
    is deliberate: ``viewscreen_home_ship(client_id)`` has only a client id, so the
    value has to be reachable from one - but a restore has to reach consoles that
    have since stopped being this ship's main screens, so the membership has to
    live somewhere that outlives the role.
    """
    return list(get_inventory_value(to_id(ship), KEY_BASELINE_CIDS, None) or ())


def viewscreen_roster_add(ship, client_id):
    """Note that this console has a home recorded - the late-joiner path."""
    ship_id = to_id(ship)
    if ship_id is None:
        return False
    roster = viewscreen_roster(ship_id)
    if client_id in roster:
        return False
    roster.append(client_id)
    set_inventory_value(ship_id, KEY_BASELINE_CIDS, roster)
    return True


def _baseline_drop(ship_id):
    set_inventory_value(ship_id, KEY_BASELINE, None)
    set_inventory_value(ship_id, KEY_BASELINE_CIDS, None)


def viewscreen_baseline_drop(ship):
    """Forget the baseline without restoring it.

    What a helm takeover does: helm's choice IS the new state, so there is nothing
    to go back to and leaving a stale baseline recorded would let a later,
    unrelated release put the crew's screen somewhere they left minutes ago.
    """
    ship_id = to_id(ship)
    if ship_id is not None:
        _baseline_drop(ship_id)
