"""Away missions - a scene played by several consoles at once, one character each.

An away mission is a shared conversation with a divided audience. Every console is looking
at the SAME beat of the SAME scene, but each console is a different member of the team, and
the scene offers each of them a different set of things to do::

    - [Examine the body](autopsy)     if medical >= 1
    - [Force the panel](panel_open)   if engineering >= 1
    - [Cover the doorway](cover)      if security >= 1
    - [Ask her again](press_her)

That is authored once, in ordinary dialogue AMD, with no new syntax - because
``dialogue_choices(scene, agent_id, speaker)`` already evaluates every guard against
whatever agent it is handed. LegendaryMissions' shipped driver (``comms/dialogue_cast.mast``)
passes the player SHIP, so every console sees one menu. This module passes the CHARACTER, so
they do not.

THREE THINGS THIS OWNS, and nothing else:

1. **The team** - which client is which character. A character is a ``lifeform`` (a body in
   the world); who the player IS remains a ``crew`` post (a label on a seat). The library
   already draws that line and this does not blur it.
2. **The metric resolver** - so a guard's left side can ask about the acting character.
3. **The scene loop** - one current beat, one spoken line, per-character choices, and an
   arbitrated answer.

WHY THE ANSWER NEEDS ARBITRATING. Six consoles can press at once. The pattern here is copied
from ``hail.py`` rather than reinvented: a monotonic **sequence token** is bumped on every
beat and every answer; a console renders its buttons carrying the seq it saw, and an answer
whose seq has moved on is REFUSED. That makes two people pressing different choices in the
same frame safe without a lock. Note ``overlay_choice`` is not a substitute - it hands the
whole audience one shared ``Promise``, and ``Promise.set_result`` has no already-done guard,
so two presses in the same frame are last-writer-wins.

WHY THE LINE IS CACHED. ``dialogue_pick_line`` picks a RANDOM eligible variant. Called once
per console it would tell each of them a different story, which reads as a bug in the writing
rather than in the code. The line is picked once when the beat opens and every console is
told the same one - the same reason hail resolves its choices once at accept.

Stdlib only; no threading. Safe to call with no MAST context.
"""
from .amd_dialogue import (dialogue_parse, dialogue_get, dialogue_choices, dialogue_pick_line,
                           dialogue_apply, dialogue_set_metric_resolver)
from .query import to_id
from .roles import has_role
from .signal import signal_emit


# --- The team ---------------------------------------------------------------
#
# client_id -> lifeform id. Keyed by CLIENT for the same reason crew seats are: two clients
# can sit at the same console type, and keying the other way makes the second evict the first.
_TEAM = {}


def away_assign(client_id, lifeform):
    """Put this client in control of this character. Returns the character's id.

    Passing ``None`` releases the client, which is what beaming one person back up is.
    """
    cid = to_id(client_id)
    lf_id = to_id(lifeform)
    if lf_id is None:
        _TEAM.pop(cid, None)
        return None
    _TEAM[cid] = lf_id
    return lf_id


def away_me(client_id):
    """The character this client is playing, or None if they are not on the team."""
    return _TEAM.get(to_id(client_id))


def away_team():
    """Every character currently under a console's control, as a set of ids.

    A set rather than a list: callers intersect it with role queries, and the same character
    must never appear twice however many clients were bound to it.
    """
    return set(_TEAM.values())


def away_clients():
    """Every client currently controlling a character."""
    return set(_TEAM)


def away_client_of(lifeform):
    """Which client is playing this character, or None. The reverse of :func:`away_me`."""
    lf_id = to_id(lifeform)
    for cid, held in _TEAM.items():
        if held == lf_id:
            return cid
    return None


def away_team_clear():
    """Drop the whole team - beam-up, or the per-mission reset."""
    _TEAM.clear()


def away_team_count():
    """Reset-ledger probe: how many clients are bound to a character."""
    return len(_TEAM)


# --- The metric resolver ----------------------------------------------------
#
# COMPOSES, NEVER REPLACES. `dialogue_set_metric_resolver` sets ONE module-level global, and
# Open Universe already claims it at import time (`universe_dialogue.py` -> `_ou_metric`,
# which resolves `credits`, `standing`, `carrying x` and reputation poles). Installing ours
# on top with a plain set would leave every OU guard reading 0 - `if fearsome > 20` would
# simply never open, silently, in a mission nobody thought they had changed.
#
# So the incumbent is captured and delegated to for every name this does not own. Order of
# import stops mattering, which is the point: addon load order is not deterministic.
_PREV_METRIC = None
_INSTALLED = False


def _away_metric(name, agent_id, speaker):
    """A guard's left side, for an away scene.

    This owns exactly one idea: **does the acting character have this role?** ``medical``,
    ``security``, ``engineering``, ``captain`` - anything a lifeform was spawned with. 1 for
    yes so ``>= 1`` reads naturally.

    Anything else falls through to whatever resolver was installed before this one. A role
    the character LACKS also falls through rather than short-circuiting to 0, so a mission
    that means `credits` by a word we happen not to hold still gets the right answer.
    """
    if agent_id is not None and has_role(agent_id, str(name).strip()):
        return 1
    if _PREV_METRIC is not None:
        return _PREV_METRIC(name, agent_id, speaker)
    return 0


def away_metric_install():
    """Install the away guard resolver in front of whatever is already there.

    Idempotent: calling it twice does not chain the resolver to itself, which would recurse
    forever the first time a guard asked about a name nobody owned.
    """
    global _PREV_METRIC, _INSTALLED
    if _INSTALLED:
        return False
    from . import amd_dialogue
    incumbent = amd_dialogue._METRIC_RESOLVER
    _PREV_METRIC = None if incumbent is _away_metric else incumbent
    dialogue_set_metric_resolver(_away_metric)
    _INSTALLED = True
    return True


def away_metric_uninstall():
    """Put the previous resolver back.

    For tests, and for a mission that tears an away layer down; the per-mission reset calls
    it through :func:`away_clear`.
    """
    global _PREV_METRIC, _INSTALLED
    if not _INSTALLED:
        return False
    dialogue_set_metric_resolver(_PREV_METRIC)
    _PREV_METRIC = None
    _INSTALLED = False
    return True


# --- The scene loop ---------------------------------------------------------
#
# One away mission is live at a time, so this is a single record rather than a table keyed by
# site: two simultaneous away teams would need two arbitration tokens, and nothing asks for
# that yet. It is a dict so a probe can see it and the reset can empty it.
_SCENE = {}


def away_scene_begin(scenes, key, speaker=None):
    """Open a beat: parse the scene, pick ONE line for everybody, bump the token.

    Returns the scene key actually opened, or None when the key names no scene - which is how
    a choice pointing at a missing target ends the conversation instead of hanging on it.
    """
    node = dialogue_get(scenes, key) if key else None
    if node is None:
        away_scene_end()
        return None
    parsed = dialogue_parse(node)
    _SCENE.update({
        "scenes": scenes,
        "key": key,
        "parsed": parsed,
        "speaker": speaker if speaker is not None else _SCENE.get("speaker"),
        "seq": _SCENE.get("seq", 0) + 1,
    })
    # Picked ONCE, here, so every console is told the same thing. See the module docstring.
    _SCENE["line"] = dialogue_pick_line(parsed, None, _SCENE["speaker"])
    return key


def away_scene_end():
    """Close the conversation, leaving the token moved on so a late press still refuses."""
    seq = _SCENE.get("seq", 0) + 1
    _SCENE.clear()
    _SCENE["seq"] = seq


def away_scene():
    """The current scene key, or None when nothing is open."""
    return _SCENE.get("key")


def away_is_open():
    """True while a beat is open and answerable."""
    return _SCENE.get("parsed") is not None


def away_seq():
    """The arbitration token. A console stamps this onto every button it renders."""
    return _SCENE.get("seq", 0)


def away_line():
    """The spoken line for this beat - the same one for every console."""
    return _SCENE.get("line", "")


def away_speaker():
    """The opaque speaker record this beat is spoken by."""
    return _SCENE.get("speaker")


def away_choices(client_id):
    """The choices THIS client's character may take, in authored order.

    The whole feature is here: the same parsed scene, evaluated against a different agent,
    yields a different list. A client with no character gets the unguarded choices only,
    which is the right answer for an observer rather than an error.
    """
    parsed = _SCENE.get("parsed")
    if parsed is None:
        return []
    return dialogue_choices(parsed, away_me(client_id), _SCENE.get("speaker"))


def away_answer(client_id, index, seq=None):
    """Take one console's pick. True when it was accepted and the scene moved.

    REFUSES, changing nothing, when: no beat is open; the token has moved on (somebody else
    already answered this beat); the index names no choice THIS character may take; or an
    outcome handler refuses the pick.

    The token is bumped BEFORE the outcomes run, exactly as ``hail_answer`` does it, so a
    second press arriving in the same frame is already carrying a stale token by the time it
    gets here.
    """
    parsed = _SCENE.get("parsed")
    if parsed is None:
        return False
    if seq is not None and seq != _SCENE.get("seq", 0):
        return False
    cid = to_id(client_id)
    choices = away_choices(cid)
    if not isinstance(index, int) or index < 0 or index >= len(choices):
        return False
    choice = choices[index]

    from_key = _SCENE.get("key")
    _SCENE["seq"] = _SCENE.get("seq", 0) + 1

    speaker = _SCENE.get("speaker")
    if dialogue_apply(away_me(cid), speaker, choice.outcomes) is False:
        # A handler refused (a cost that cannot be paid). The token has ALREADY moved, so
        # every console is holding a stale one and the beat is briefly unanswerable - which
        # is correct, not a deadlock: consoles repaint off the token, re-render with the new
        # one, and the same person can try something else. Bumping after the outcome instead
        # would reopen the same-frame race this exists to close.
        return False

    scenes = _SCENE.get("scenes")
    if not choice.target:
        away_scene_end()
        signal_emit("away_scene_ended", {"AWAY_FROM": from_key})
        return True
    away_scene_begin(scenes, choice.target, speaker)
    return True


def away_scene_count():
    """Reset-ledger probe: whether a beat is being held."""
    return 1 if _SCENE.get("parsed") is not None else 0


def away_clear():
    """The per-mission reset: no team, no beat, resolver handed back."""
    away_team_clear()
    _SCENE.clear()
    away_metric_uninstall()
