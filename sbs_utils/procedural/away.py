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
                           dialogue_apply, dialogue_register_outcome,
                           dialogue_set_metric_resolver)
from .query import to_id
from .roles import has_role, get_role_list
from .signal import signal_emit


# --- The team ---------------------------------------------------------------
#
# client_id -> lifeform id. Keyed by CLIENT for the same reason crew seats are: two clients
# can sit at the same console type, and keying the other way makes the second evict the first.
_TEAM = {}


def away_assign(client_id, lifeform):
    """Put this client in control of this character. Returns the character's id.

    REPLACES whatever the console was holding, so this is still "you are Sorel". Passing
    ``None`` releases the console entirely, which is what beaming one person back up is.
    Use :func:`away_assign_also` to add a second character to the same console.
    """
    cid = to_id(client_id)
    lf_id = to_id(lifeform)
    if lf_id is None:
        _TEAM.pop(cid, None)
        return None
    _TEAM[cid] = [lf_id]
    return lf_id


def away_assign_also(client_id, lifeform):
    """Give this console ANOTHER character to speak for. Returns the character's id.

    A landing party smaller than its cast would otherwise leave characters standing on the
    surface that nobody controls - in nobody's :func:`away_team`, with the readings only
    they can take unreachable. Doubling up keeps every reading in play AND keeps it
    attached to a named person, which is the difference between a party game and one menu.

    Idempotent per character, and a no-op for a character another console already holds:
    two consoles answering as one person is worse than a console with nothing to answer.
    """
    cid = to_id(client_id)
    lf_id = to_id(lifeform)
    if lf_id is None:
        return None
    if lf_id in away_team():
        return None
    _TEAM.setdefault(cid, []).append(lf_id)
    return lf_id


def away_me(client_id):
    """The character this client is playing - the PRIMARY, when it holds several.

    Stays the answer to "whose face and name is on this screen", which is what every
    caller wants it for. :func:`away_held` is the whole list.
    """
    held = _TEAM.get(to_id(client_id))
    return held[0] if held else None


def away_held(client_id):
    """Every character this console speaks for, primary first."""
    return list(_TEAM.get(to_id(client_id)) or ())


def away_team():
    """Every character currently under a console's control, as a set of ids.

    A set rather than a list: callers intersect it with role queries, and the same character
    must never appear twice however many clients were bound to it.
    """
    out = set()
    for held in _TEAM.values():
        out.update(held)
    return out


def away_clients():
    """Every client currently controlling a character."""
    return set(_TEAM)


# Roles a player must never be shown. `ultra_beam` is added automatically to any lifeform
# with no space-object host - i.e. to every away-team member, the moment they beam down -
# and `amd_lifeform:<key>` is bookkeeping the AMD loader stamps on. Neither describes the
# character; both look exactly like a job when a screen prints the role list raw.
_NOT_A_JOB = ("away", "lifeform", "ultra_beam", "__player__", "__npc__")


def away_jobs(lifeform):
    """What this character is FOR, as a sorted list of role words.

    The guards in a scene read exactly these words, so a screen showing them is not
    decorating - it is telling the player why they can act where the next console cannot.

    Filtered and SORTED, and both matter:

    * A lifeform carries machinery beside its job (see ``_NOT_A_JOB``, plus anything
      namespaced with ``:`` or dunder-ish). Printed raw, a medic reads
      ``medical, ultra_beam, amd_lifeform:sorel``.
    * Roles are a **set**, so the unsorted order is not stable - the same character reads
      differently on each repaint, which looks like a bug in the mission.
    """
    out = []
    for role_name in get_role_list(to_id(lifeform)) or ():
        name = str(role_name).strip()
        if not name or name in _NOT_A_JOB or ":" in name or name.startswith("__"):
            continue
        out.append(name)
    return sorted(set(out))


def away_job_text(lifeform, default=""):
    """:func:`away_jobs` as one line, ready for a widget. ``default`` when there is none."""
    jobs = away_jobs(lifeform)
    return ", ".join(jobs) if jobs else default


def away_client_of(lifeform):
    """Which client is playing this character, or None. The reverse of :func:`away_me`."""
    lf_id = to_id(lifeform)
    for cid, held in _TEAM.items():
        if lf_id in held:
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


# What the party has WORKED OUT, by name. A set, so the same reading taken twice - and a
# scene the crew walks back into - counts once.
#
# The party's, not a character's: the whole design is that four people each see a piece
# and the picture only exists once they compare. A per-character tally would be a
# different game, and a worse one.
_FACTS = set()


def away_facts():
    """Everything the party has worked out so far, as a sorted list."""
    return sorted(_FACTS)


def away_learned(fact=None):
    """How many distinct things the party knows - or whether it knows a given one."""
    if fact is None:
        return len(_FACTS)
    return 1 if str(fact).strip() in _FACTS else 0


def _away_learn_outcome(agent_id, speaker, tokens):
    """The `learn` outcome verb: `- [Read the panel](panel) if engineering >= 1 ; learn cold`

    DECLARED IN THE FILE, counted here. The alternative a mission reaches for first is a
    signal per fact plus a route per signal plus a role granted at the threshold - four
    moving parts, in three files, to express "they worked something out". And it cannot
    dedupe: a `signal` outcome carries no data but its NAME, and by the time a route sees
    it the choice that fired it is gone, so a reading taken twice counts twice.
    """
    if not tokens:
        return None
    _FACTS.add(" ".join(str(t) for t in tokens).strip())
    return None


# Registered AT IMPORT, not inside `away_metric_install`. `dialogue_outcome_verbs()` is
# what `sbs lint` reads to decide whether an authored verb exists, and the linter does
# not run a mission - so a verb registered at install time is one the linter reports as
# unknown on a file that works perfectly. Registering is also harmless on its own: the
# verb only records, and it is `away_metric_install` that makes `learned` answerable.
dialogue_register_outcome("learn", _away_learn_outcome)

def _away_metric(name, agent_id, speaker):
    """A guard's left side, for an away scene.

    This owns exactly one idea: **does the acting character have this role?** ``medical``,
    ``security``, ``engineering``, ``captain`` - anything a lifeform was spawned with. 1 for
    yes so ``>= 1`` reads naturally.

    Anything else falls through to whatever resolver was installed before this one. A role
    the character LACKS also falls through rather than short-circuiting to 0, so a mission
    that means `credits` by a word we happen not to hold still gets the right answer.
    """
    # `learned` is the PARTY's, so it is answered before the role lookup and without an
    # agent - it is the one guard word that is not about who is asking.
    if str(name).strip() == "learned":
        return len(_FACTS)
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
    _mirror_to_inbox()
    return key


# The away team's only channel to the ship has always been the shared main screen,
# read-only. Mirroring each beat into the inbox gives them a transcript they can scroll
# and, through the reply strip, a place to answer from - without touching the away
# console, which keeps rendering the scene exactly as it did.
MIRROR_TO_INBOX = True


def away_mirror_to_inbox(on=True):
    """Whether each beat also arrives as a message. On by default; a mission whose
    away play is entirely on the away console can turn it off."""
    global MIRROR_TO_INBOX
    MIRROR_TO_INBOX = bool(on)


def _mirror_to_inbox():
    """Post the current beat to the away team's inbox.

    The message carries the LINE only. Its replies are asked of `away_choices` when
    the inbox draws them, because they differ per character and `away_answer` already
    arbitrates them - a copy on the message would be a second, competing path over
    one scene.
    """
    if not MIRROR_TO_INBOX:
        return
    line = _SCENE.get("line")
    if not line:
        return
    try:
        from .messages import message_send
        message_send(str(line), to="away", kind="scene",
                     sender=_SCENE.get("speaker") or "Away",
                     subject=_SCENE.get("key"), scene=_SCENE.get("key"))
    except Exception:
        from .execution import log
        log("could not mirror an away beat to the inbox", "away", "warning")


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
    speaker = _SCENE.get("speaker")
    held = away_held(client_id)
    if not held:
        # No character: the unguarded choices only, which is the right answer for an
        # observer rather than an error.
        return dialogue_choices(parsed, None, speaker)

    out = []
    seen = set()
    for lf_id in held:
        for ch in dialogue_choices(parsed, lf_id, speaker):
            # DEDUPE. An ungated choice - "Beam back up", "Walk in with her" - is offered
            # to EVERY character, so a plain union shows it once per body held. Keep the
            # first, which belongs to the primary because the primary is iterated first;
            # each later character then contributes only what is exclusively theirs, and
            # that ordering is what makes the grouping on screen read.
            mark = (ch.get("label"), ch.get("target"))
            if mark in seen:
                continue
            seen.add(mark)
            # WHO IS ACTING, carried on the choice. Guards and outcomes are per character,
            # so `away_answer` cannot ask the console - the console has several. A
            # MastDataObject stores values as ATTRIBUTES, so `ch["agent"] = ...` raises.
            setattr(ch, "agent", lf_id)
            out.append(ch)
    return out


def away_choices_for(client_id, lifeform):
    """Just THIS character's choices, tagged, for a console holding several.

    A doubled-up console shows one character at a time - a roster listbox picks who, and
    this is the detail panel's half of that. Not a filter over :func:`away_choices`: the
    shared, ungated choices are deduped onto the PRIMARY there, so filtering by tag would
    hide "Beam back up" from everybody except the first character. Asked directly, every
    character offers the open choices as well as its own.

    Falls back to the console's whole list when it is not holding this character, which
    is what a stale selection looks like after somebody else took a body over.
    """
    parsed = _SCENE.get("parsed")
    if parsed is None:
        return []
    lf_id = to_id(lifeform)
    if lf_id is None or lf_id not in away_held(client_id):
        return away_choices(client_id)
    out = dialogue_choices(parsed, lf_id, _SCENE.get("speaker"))
    for ch in out:
        setattr(ch, "agent", lf_id)
    return out

def away_answer(client_id, index, seq=None, agent=None):
    """Take one console's pick. True when it was accepted and the scene moved.

    ``agent`` names the character whose list the console RENDERED, for a doubled-up
    console showing one character at a time. Without it the index would be read against
    the console's full list and press the wrong thing - the lists are different lengths
    and in a different order.

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
    choices = away_choices_for(cid, agent) if agent is not None else away_choices(cid)
    if not isinstance(index, int) or index < 0 or index >= len(choices):
        return False
    choice = choices[index]

    from_key = _SCENE.get("key")
    _SCENE["seq"] = _SCENE.get("seq", 0) + 1

    speaker = _SCENE.get("speaker")
    # The character that OWNS the choice, not the console's primary. With a doubled-up
    # console those differ, and applying as the primary would credit the wrong body -
    # and evaluate a cost or a refusal against someone who was not acting.
    actor = choice.get("agent") or away_me(cid)
    if dialogue_apply(actor, speaker, choice.outcomes) is False:
        # A handler refused (a cost that cannot be paid). The token has ALREADY moved, so
        # every console is holding a stale one and the beat is briefly unanswerable - which
        # is correct, not a deadlock: consoles repaint off the token, re-render with the new
        # one, and the same person can try something else. Bumping after the outcome instead
        # would reopen the same-frame race this exists to close.
        return False

    # Tell the transcript what was said, and what was not. The beat's replies live
    # here rather than on the message, so the inbox cannot work this out on its own -
    # and an answered beat showing nothing is the transcript losing the half that
    # matters. Best effort: a mission running without the inbox is unaffected.
    try:
        from .messages import message_answer_scene
        message_answer_scene(from_key, choice.label,
                             by=_name_of(actor),
                             others=[c.label for c in choices
                                     if c.label != choice.label])
    except Exception:
        pass

    scenes = _SCENE.get("scenes")
    if not choice.target:
        away_scene_end()
        signal_emit("away_scene_ended", {"AWAY_FROM": from_key})
        return True
    away_scene_begin(scenes, choice.target, speaker)
    return True


def _name_of(lifeform_id):
    """Who answered, for the transcript. The character, not the console - a console
    speaking for two bodies would otherwise credit both to the primary."""
    try:
        from .query import to_object
        who = to_object(lifeform_id)
        return who.name if who is not None else "the away team"
    except Exception:
        return "the away team"


def away_scene_count():
    """Reset-ledger probe: whether a beat is being held."""
    return 1 if _SCENE.get("parsed") is not None else 0


def away_clear():
    """The per-mission reset: no team, no beat, resolver handed back."""
    away_team_clear()
    _SCENE.clear()
    _FACTS.clear()
    away_metric_uninstall()
