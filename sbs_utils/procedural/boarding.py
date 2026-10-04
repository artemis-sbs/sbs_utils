"""Boarding parties - a scene played by several consoles at once, one character each.

An boarding mission is a shared conversation with a divided audience. Every console is looking
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
                           dialogue_set_metric_resolver, dialogue_guard_ok)
from ..mast.mast_node import MastDataObject
import re

from ..agent import Agent
from .query import to_id
from .roles import has_role, get_role_list
from .signal import signal_emit, signal_observe, signal_unobserve
from .inventory import get_inventory_value, set_inventory_value


# --- The team ---------------------------------------------------------------
#
# client_id -> lifeform id. Keyed by CLIENT for the same reason crew seats are: two clients
# can sit at the same console type, and keying the other way makes the second evict the first.
_TEAM = {}


def boarding_assign(client_id, lifeform):
    """Put this client in control of this character. Returns the character's id.

    REPLACES whatever the console was holding, so this is still "you are Sorel". Passing
    ``None`` releases the console entirely, which is what beaming one person back up is.
    Use :func:`boarding_assign_also` to add a second character to the same console.
    """
    cid = to_id(client_id)
    lf_id = to_id(lifeform)
    if lf_id is None:
        _TEAM.pop(cid, None)
        return None
    _TEAM[cid] = [lf_id]
    return lf_id


def boarding_assign_also(client_id, lifeform):
    """Give this console ANOTHER character to speak for. Returns the character's id.

    A landing party smaller than its cast would otherwise leave characters standing on the
    surface that nobody controls - in nobody's :func:`boarding_team`, with the readings only
    they can take unreachable. Doubling up keeps every reading in play AND keeps it
    attached to a named person, which is the difference between a party game and one menu.

    Idempotent per character, and a no-op for a character another console already holds:
    two consoles answering as one person is worse than a console with nothing to answer.
    """
    cid = to_id(client_id)
    lf_id = to_id(lifeform)
    if lf_id is None:
        return None
    if lf_id in boarding_team():
        return None
    _TEAM.setdefault(cid, []).append(lf_id)
    return lf_id


def boarding_me(client_id):
    """The character this client is playing - the PRIMARY, when it holds several.

    Stays the answer to "whose face and name is on this screen", which is what every
    caller wants it for. :func:`boarding_held` is the whole list.
    """
    held = _TEAM.get(to_id(client_id))
    return held[0] if held else None


def boarding_held(client_id):
    """Every character this console speaks for, primary first."""
    return list(_TEAM.get(to_id(client_id)) or ())


def boarding_team():
    """Every character currently under a console's control, as a set of ids.

    A set rather than a list: callers intersect it with role queries, and the same character
    must never appear twice however many clients were bound to it.
    """
    out = set()
    for held in _TEAM.values():
        out.update(held)
    return out


def boarding_clients():
    """Every client currently controlling a character."""
    return set(_TEAM)


# Roles a player must never be shown. `ultra_beam` is added automatically to any lifeform
# with no space-object host - i.e. to every away-team member, the moment they beam down -
# and `amd_lifeform:<key>` is bookkeeping the AMD loader stamps on. Neither describes the
# character; both look exactly like a job when a screen prints the role list raw.
_NOT_A_JOB = ("boarding", "lifeform", "ultra_beam", "__player__", "__npc__")

#: On the BODY. The roles it was cast with, so a role added later can be told apart
#: from one it has always had.
JOBS_KEY = "BOARDING_JOBS"


def boarding_jobs(lifeform):
    """What this character is FOR, as a sorted list of role words.

    The guards in a scene read exactly these words, so a screen showing them is not
    decorating - it is telling the player why they can act where the next console cannot.

    Filtered and SORTED, and both matter:

    * A lifeform carries machinery beside its job (see ``_NOT_A_JOB``, plus anything
      namespaced with ``:`` or dunder-ish). Printed raw, a medic reads
      ``medical, ultra_beam, amd_lifeform:sorel``.
    * Roles are a **set**, so the unsorted order is not stable - the same character reads
      differently on each repaint, which looks like a bug in the mission.

    **A JOB IS WHAT YOU WERE CAST AS. A ROLE ADDED LATER IS SOMETHING THAT HAPPENED.**
    A mission adds roles to an away body to carry state a scene guards on -
    LandingParty does `add_role(lp_body, "briefed")` so its AMD can ask
    `if briefed >= 1`. Those are guard words, not jobs, and printed as jobs they read
    as nonsense: the crew console said "briefed, helm" under a crew member's name.

    So when the body recorded what it was cast with (`_body_for` does), that is the
    answer and later additions are ignored. A body spawned some other way has no such
    record and falls back to the filtered role list, exactly as before - no mission
    has to do anything, and nothing that worked stops working.

    Guards are UNAFFECTED: `dialogue_guard_ok` reads ROLES, never this.
    """
    cast = get_inventory_value(to_id(lifeform), JOBS_KEY, None)
    if cast:
        return sorted({str(w).strip() for w in cast
                       if str(w).strip() and str(w).strip() not in _NOT_A_JOB})
    out = []
    for role_name in get_role_list(to_id(lifeform)) or ():
        name = str(role_name).strip()
        if not name or name in _NOT_A_JOB or ":" in name or name.startswith("__"):
            continue
        out.append(name)
    return sorted(set(out))


def boarding_job_text(lifeform, default=""):
    """:func:`boarding_jobs` as one line, ready for a widget. ``default`` when there is none."""
    jobs = boarding_jobs(lifeform)
    return ", ".join(jobs) if jobs else default


def boarding_client_of(lifeform):
    """Which client is playing this character, or None. The reverse of :func:`boarding_me`."""
    lf_id = to_id(lifeform)
    for cid, held in _TEAM.items():
        if lf_id in held:
            return cid
    return None


def boarding_team_clear():
    """Drop the whole team - beam-up, or the per-mission reset."""
    _TEAM.clear()


def boarding_team_count():
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
#
# AND THE PLACE'S, not the mission's. This was one set for the whole mission, so a
# second place started with everything the first had taught: a site gated on
# `learned >= 3` opened on arrival for a crew that had read three things somewhere else,
# and a return to the same place could not be told from a first visit to another. Each
# place keeps its own, for the length of the mission - come back and the party still
# knows what it worked out there; go somewhere new and it knows nothing yet.
_FACTS = {}                       # place -> the set of things worked out there

#: The pool a scene writes to when it has no place at all: no visit, and no invitation
#: with a title. A mission that drives scenes by hand and never named one gets exactly
#: the single pool it always had.
_NO_PLACE = ""


def boarding_place():
    """Where the party is, as the key its facts are filed under.

    The visit's place; else the open invitation's title; else ``""``.
    """
    visit = Agent.SHARED.get_inventory_value(VISIT_KEY, None)
    if isinstance(visit, dict) and visit.get("place"):
        return str(visit.get("place"))
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    if isinstance(invite, dict) and invite.get("open") and invite.get("title"):
        return str(invite.get("title"))
    return _NO_PLACE


def _facts_of(place=None):
    return _FACTS.get(boarding_place() if place is None else str(place), ())


def boarding_facts(place=None):
    """Everything the party has worked out HERE, as a sorted list.

    ``place`` asks about somewhere else - after a visit has ended, say, with the
    ``BOARDING_PLACE`` that ``boarding_visit_ended`` carries.
    """
    return sorted(_facts_of(place))


def boarding_learned(fact=None, place=None):
    """How many distinct things the party knows here - or whether it knows a given one."""
    facts = _facts_of(place)
    if fact is None:
        return len(facts)
    return 1 if str(fact).strip() in facts else 0


def boarding_facts_count():
    """Reset-ledger probe: how many facts are held, across every place."""
    return sum(len(facts) for facts in _FACTS.values())


def boarding_facts_forget(place=None):
    """Forget what was worked out at ``place`` - or everywhere, with no argument.

    For a place that RESETS: a wreck that is a different wreck each time it is found.
    """
    if place is None:
        _FACTS.clear()
    else:
        _FACTS.pop(str(place), None)


def _boarding_learn_outcome(agent_id, speaker, tokens):
    """The `learn` outcome verb: `- [Read the panel](panel) if engineering >= 1 ; learn cold`

    DECLARED IN THE FILE, counted here. The alternative a mission reaches for first is a
    signal per fact plus a route per signal plus a role granted at the threshold - four
    moving parts, in three files, to express "they worked something out". And it cannot
    dedupe: a `signal` outcome carries no data but its NAME, and by the time a route sees
    it the choice that fired it is gone, so a reading taken twice counts twice.
    """
    if not tokens:
        return None
    _FACTS.setdefault(boarding_place(), set()).add(" ".join(str(t) for t in tokens).strip())
    return None


# Registered AT IMPORT, not inside `boarding_metric_install`. `dialogue_outcome_verbs()` is
# what `sbs lint` reads to decide whether an authored verb exists, and the linter does
# not run a mission - so a verb registered at install time is one the linter reports as
# unknown on a file that works perfectly. Registering is also harmless on its own: the
# verb only records, and it is `boarding_metric_install` that makes `learned` answerable.
dialogue_register_outcome("learn", _boarding_learn_outcome)

def _boarding_metric(name, agent_id, speaker):
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
        return len(_facts_of())
    # A WORD AND AN ARGUMENT - `skill engineering`, `holding medkit`, `party coil` - owned
    # by the module that knows the answer (checks, the pack), registered with
    # `boarding_metric_word`, so this resolver stays one lookup.
    word, _, rest = str(name).strip().partition(" ")
    fn = _METRIC_WORDS.get(word.lower())
    if fn is not None and rest.strip():
        return fn(rest.strip(), agent_id)
    if agent_id is not None and has_role(agent_id, str(name).strip()):
        return 1
    if _PREV_METRIC is not None:
        return _PREV_METRIC(name, agent_id, speaker)
    return 0


_METRIC_WORDS = {}


def boarding_metric_word(word, fn):
    """Answer guards of the form ``<word> <argument>`` - ``if holding medkit >= 1``.

    ``fn(argument, agent_id)`` returns a number. The word is the first token of the
    guard's left side; a guard that is only the word (no argument) is still a role.
    """
    _METRIC_WORDS[str(word).strip().lower()] = fn


def _skill_metric(rest, agent_id):
    from .boarding_checks import boarding_skill
    return boarding_skill(agent_id, rest) if agent_id is not None else 0


boarding_metric_word("skill", _skill_metric)


def boarding_metric_install():
    """Install the away guard resolver in front of whatever is already there.

    Idempotent: calling it twice does not chain the resolver to itself, which would recurse
    forever the first time a guard asked about a name nobody owned.
    """
    global _PREV_METRIC, _INSTALLED
    if _INSTALLED:
        return False
    from . import amd_dialogue
    incumbent = amd_dialogue._METRIC_RESOLVER
    _PREV_METRIC = None if incumbent is _boarding_metric else incumbent
    dialogue_set_metric_resolver(_boarding_metric)
    _INSTALLED = True
    return True


def boarding_metric_uninstall():
    """Put the previous resolver back.

    For tests, and for a mission that tears an away layer down; the per-mission reset calls
    it through :func:`boarding_clear`.
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
# ONE SCENE PER CHANNEL. A channel is a group of consoles in the same conversation. The
# party as a whole is the `PARTY` channel, and a console that was never put anywhere else
# is in it - so a mission that never opens a channel has exactly the one scene it always
# had, and every function below defaults to it.
#
# A party spread across an open world needs more than one: the medic talking to a
# survivor in the caves while the engineer argues with a deputy in the colony. So a
# mission (or `boarding_encounter`) opens a channel for a group, and each console reads
# and answers the scene of the channel it is in.
#
# THE SEQ IS GLOBAL. Every channel draws its token from one counter, so no two beats
# anywhere ever share a seq - a button rendered in one channel can never be accepted by
# another, and the arbitration stays exactly as safe as it was with one scene.
PARTY = "party"

_SCENE = {}                         # the PARTY channel - kept as the same dict object
_SCENES = {PARTY: _SCENE}           # channel -> scene record
_CLIENT_CHANNEL = {}                # client_id -> channel (absent means PARTY)
_STICKY = set()                     # channels that outlive their scene ending
_SEQ = [0]


def _next_seq():
    _SEQ[0] += 1
    return _SEQ[0]


def _record(channel=None, create=False):
    """The scene record for a channel. PARTY always exists; another is made on demand."""
    ch = channel or PARTY
    rec = _SCENES.get(ch)
    if rec is None and create:
        rec = _SCENES[ch] = {}
    return rec if rec is not None else {}


def boarding_party_channel():
    """The name of the channel every console starts in."""
    return PARTY


def boarding_channel_of(client_id):
    """The channel this console is in - PARTY unless it was put somewhere else."""
    return _CLIENT_CHANNEL.get(to_id(client_id), PARTY)


def boarding_channel_open(channel, members=(), sticky=False):
    """Make a channel for a group of consoles and move them into it. Returns its name.

    Opening an existing channel only adds the members. ``sticky`` keeps the channel (and
    its members in it) after its scene ends; by default an ended side scene sends its
    members back to the party.
    """
    ch = str(channel or PARTY)
    _record(ch, create=True)
    if sticky:
        _STICKY.add(ch)
    for cid in members or ():
        boarding_channel_join(cid, ch)
    return ch


def boarding_channel_join(client_id, channel):
    """Move one console into a channel. Its reader picks up that channel's beat."""
    cid = to_id(client_id)
    ch = str(channel or PARTY)
    _record(ch, create=True)
    if ch == PARTY:
        _CLIENT_CHANNEL.pop(cid, None)
    else:
        _CLIENT_CHANNEL[cid] = ch
    return ch


def boarding_channel_leave(client_id):
    """Put one console back in the party channel."""
    return boarding_channel_join(client_id, PARTY)


def boarding_channel_members(channel=None):
    """The consoles in a channel, as a set. For PARTY: every console not elsewhere."""
    ch = channel or PARTY
    if ch == PARTY:
        return {c for c in boarding_clients() if c not in _CLIENT_CHANNEL}
    return {c for c, where in _CLIENT_CHANNEL.items() if where == ch}


def boarding_channels():
    """Every channel with a scene open, PARTY first when it has one."""
    out = [ch for ch, rec in _SCENES.items() if rec.get("parsed") is not None]
    out.sort(key=lambda c: (c != PARTY, c))
    return out


def boarding_channel_close(channel):
    """End a channel's scene and send its members back to the party."""
    ch = channel or PARTY
    boarding_scene_end(ch)
    if ch == PARTY:
        return
    for cid in list(boarding_channel_members(ch)):
        _CLIENT_CHANNEL.pop(cid, None)
    _STICKY.discard(ch)
    _SCENES.pop(ch, None)


def boarding_any_open():
    """True when any channel has a beat open."""
    return any(rec.get("parsed") is not None for rec in _SCENES.values())


def boarding_scene_begin(scenes, key, speaker=None, channel=None):
    """Open a beat: parse the scene, pick ONE line for everybody, bump the token.

    Returns the scene key actually opened, or None when the key names no scene - which is how
    a choice pointing at a missing target ends the conversation instead of hanging on it.

    ``channel`` is whose scene this is; the default is the whole party.
    """
    ch = channel or PARTY
    node = dialogue_get(scenes, key) if key else None
    if node is None:
        boarding_scene_end(ch)
        return None
    rec = _record(ch, create=True)
    parsed = dialogue_parse(node)
    rec.update({
        "scenes": scenes,
        "key": key,
        "parsed": parsed,
        "speaker": speaker if speaker is not None else rec.get("speaker"),
        "seq": _next_seq(),
        "channel": ch,
    })
    # Picked ONCE, here, so every console is told the same thing. See the module docstring.
    rec["line"] = dialogue_pick_line(parsed, None, rec["speaker"])
    if ch == PARTY:
        # The inbox is the WHOLE party's transcript, so only the party's beats go there.
        # A side scene is private to its channel and lives in that channel's reader.
        _mirror_to_inbox()
    return key


def boarding_encounter(scenes, key, client_id, speaker=None, channel=None, members=()):
    """Start a scene for ONE group - this console and whoever is with it.

    The everyday way into a side conversation: somebody walks up to the deputy, and the
    deputy's scene opens for them (and anyone else in ``members``) while the rest of the
    party carries on with whatever they are doing. If the channel already has a beat open
    the console simply joins it, so two people walking up to the same person share one
    conversation instead of starting two.

    Returns the channel name, or None when ``key`` names no scene.
    """
    ch = str(channel or key)
    rec = _record(ch)
    boarding_channel_open(ch, [client_id] + list(members or ()))
    if rec.get("parsed") is not None:
        return ch
    if boarding_scene_begin(scenes, key, speaker, channel=ch) is None:
        boarding_channel_close(ch)
        return None
    return ch


# The boarding party's only channel to the ship has always been the shared main screen,
# read-only. Mirroring each beat into the inbox gives them a transcript they can scroll
# and, through the reply strip, a place to answer from - without touching the away
# console, which keeps rendering the scene exactly as it did.
MIRROR_TO_INBOX = True


def boarding_mirror_to_inbox(on=True):
    """Whether each beat also arrives as a message. On by default; a mission whose
    boarding play is entirely on the crew console can turn it off."""
    global MIRROR_TO_INBOX
    MIRROR_TO_INBOX = bool(on)


def _mirror_to_inbox():
    """Post the current beat to the boarding party's inbox.

    The message carries the LINE only. Its replies are asked of `boarding_choices` when
    the inbox draws them, because they differ per character and `boarding_answer` already
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
        message_send(str(line), to="boarding", kind="scene",
                     sender=_beat_sender(), subject=_beat_subject(),
                     scene=_SCENE.get("key"))
    except Exception:
        from .execution import log
        log("could not mirror an boarding beat to the inbox", "boarding", "warning")


def boarding_room_title(client_id=None):
    """The NAME of the room this console's party is in - `The Airlock` - or None.

    The heading the author wrote, not the key the room is filed under. None when no
    scene is open for that console.
    """
    rec = _record(boarding_channel_of(client_id) if client_id is not None else None)
    key = rec.get("key")
    if not key:
        return None
    node = dialogue_get(rec.get("scenes") or {}, key)
    name = (node.get("display_text") if hasattr(node, "get") else None) or ""
    return str(name).strip() or str(key)


def _beat_subject():
    """What the inbox calls this beat: the room's NAME, as the author wrote it.

    It was the room's key - `airlock` under a heading that says `The Airlock` - because
    the key is what the scene is filed under. A key is the author's handle, lower case
    and one word; the crew should read the name.
    """
    return boarding_room_title() or _SCENE.get("key")


def _beat_sender():
    """Who the inbox says a beat is from: its speaker, else the PLACE.

    A room with no `Speaker:` is narration, and it was signed "Away" - which is this
    module's old name, not anything the crew was told. The place they went to is.
    """
    speaker = _SCENE.get("speaker")
    if speaker:
        return speaker
    if boarding_invitation() is not None or boarding_team():
        title = boarding_invite_title()
        if title and title != "BOARDING PARTY":
            return title
    return "The party"


def boarding_scene_end(channel=None):
    """Close the conversation, leaving the token moved on so a late press still refuses."""
    rec = _record(channel, create=True)
    rec.clear()
    rec["seq"] = _next_seq()


def boarding_scene(channel=None):
    """The current scene key, or None when nothing is open."""
    return _record(channel).get("key")


def boarding_is_open(channel=None):
    """True while a beat is open and answerable."""
    return _record(channel).get("parsed") is not None


def boarding_seq(channel=None):
    """The arbitration token. A console stamps this onto every button it renders."""
    return _record(channel).get("seq", 0)


def boarding_seq_for(client_id):
    """The token of the channel THIS console is in - what its screen should poll."""
    return boarding_seq(boarding_channel_of(client_id))


def boarding_line(channel=None):
    """The spoken line for this beat - the same one for every console."""
    return _record(channel).get("line", "")


def boarding_speaker(channel=None):
    """The opaque speaker record this beat is spoken by."""
    return _record(channel).get("speaker")


def boarding_line_face(channel=None):
    """The face of whoever says this beat's line, or None - so a transcript can show who
    is talking, and show nobody when nobody in particular is.

    In order: the person a ``talk:<key>`` channel is a conversation with (their
    ``Face:``); the speaker the scene was opened with, when that is someone with a face;
    the scene's ``Speaker:``, resolved the way a hail's is (``hail_speaker``). A
    narrator, a prop or a crowd has no face, and gets none.
    """
    ch = channel or PARTY
    rec = _record(ch)
    if rec.get("parsed") is None:
        return None
    if ch.startswith("talk:"):
        from .boarding_combat import boarding_hostile
        person = boarding_hostile(ch[len("talk:"):])
        if person is not None and person.get("face"):
            return person["face"]
    speaker = rec.get("speaker")
    if speaker is not None:
        try:
            from ..faces import get_face
            face = get_face(to_id(speaker))
            if face:
                return face
        except Exception:                                # noqa: BLE001
            pass
    key = (rec.get("parsed") or {}).get("speaker")
    if key:
        try:
            from .hail import hail_speaker
            return hail_speaker(key).get("face") or None
        except Exception:                                # noqa: BLE001
            return None
    return None


def boarding_line_image(channel=None):
    """The picture of what a beat is about when nobody's FACE is (``boarding_line_face``):
    an atlas key, or None.

    A prop's scene shows the prop - its open look once opened - and a person with no
    ``Face:`` shows the figure the map draws them with, facing the camera: the aliens
    the face art cannot draw still get a portrait. Only a key the art has registered
    counts, so a mission without the art shows nothing rather than a broken picture.
    """
    ch = channel or PARTY
    rec = _record(ch)
    if rec.get("parsed") is None:
        return None
    # THE SCENE'S OWN PICTURE FIRST. A scene that names a `Backdrop:` has said what it is
    # about, whatever opened it - a relic place, a prop, a site. Only a key the art has
    # registered counts, so a scene written against a pack the mission does not load
    # falls through to the rest instead of drawing a broken picture.
    try:
        node = dialogue_get(rec.get("scenes") or {}, rec.get("key"))
        backdrop = ((node or {}).get("data") or {}).get("backdrop")
    except Exception:                                    # noqa: BLE001
        backdrop = None
    if _drawable(backdrop):
        return backdrop
    key = None
    if ch.startswith("prop:"):
        from .boarding_props import boarding_prop
        prop = boarding_prop(ch[len("prop:"):])
        if prop is not None:
            key = prop.get("open_sprite") if (prop.get("opens") and prop.get("open")
                                              and prop.get("open_sprite")) else prop.get("sprite")
    elif ch.startswith("talk:"):
        from .boarding_combat import boarding_hostile
        person = boarding_hostile(ch[len("talk:"):])
        if person is not None and person.get("sprite"):
            from .tilemap import tilemap_sprite_look
            key = tilemap_sprite_look({"sprite": person["sprite"], "facing": "s", "stride": 0})
    return _drawable(key)


def _drawable(key):
    from .gui.image import ImageAtlas
    return key if key and key in ImageAtlas.all else None


def _image_md(key, size):
    """A lead picture from the image atlas, made safe to sit inside `image://...)`."""
    safe = str(key).strip().replace(")", "").replace("?", "").replace("]", "")
    return f"![](image://{safe}?size={size})" if safe else ""


def _face_md(face, size):
    """A lead face for a transcript line, made safe to sit inside `face://...)`: a `)`
    or `?` in the string would end the reference or start its options."""
    safe = str(face).strip().replace(")", "").replace("?", "").replace("]", "")
    return f"![](face://{safe}?size={size})" if safe else ""


def boarding_choices(client_id):
    """The choices THIS client's character may take, in authored order.

    The whole feature is here: the same parsed scene, evaluated against a different agent,
    yields a different list. A client with no character gets the unguarded choices only,
    which is the right answer for an observer rather than an error.
    """
    ch = boarding_channel_of(client_id)
    rec = _record(ch)
    parsed = rec.get("parsed")
    if parsed is None:
        return []
    speaker = rec.get("speaker")
    held = boarding_held(client_id)
    if not held:
        # No character: the unguarded choices only, which is the right answer for an
        # observer rather than an error.
        return dialogue_choices(parsed, None, speaker)

    out = []
    seen = set()
    for lf_id in held:
        for c in dialogue_choices(parsed, lf_id, speaker):
            # DEDUPE. An ungated choice - "Beam back up", "Walk in with her" - is offered
            # to EVERY character, so a plain union shows it once per body held. Keep the
            # first, which belongs to the primary because the primary is iterated first;
            # each later character then contributes only what is exclusively theirs, and
            # that ordering is what makes the grouping on screen read.
            mark = (c.get("label"), c.get("target"))
            if mark in seen:
                continue
            seen.add(mark)
            # WHO IS ACTING, carried on the choice. Guards and outcomes are per character,
            # so `boarding_answer` cannot ask the console - the console has several. A
            # MastDataObject stores values as ATTRIBUTES, so `ch["agent"] = ...` raises.
            setattr(c, "agent", lf_id)
            out.append(c)
    # FORWARDED WORK, on one console only. See `boarding_orphan_choices`: a party short of
    # a medic still has to be able to treat her, and the duty console is the stable
    # answer to "who catches it" that every console computes identically.
    if client_id == boarding_duty_client(ch):
        seen_labels = {(c.get("label"), c.get("target")) for c in out}
        for c in boarding_orphan_choices(ch):
            if (c.get("label"), c.get("target")) not in seen_labels:
                out.append(c)
    return out


def boarding_choices_for(client_id, lifeform):
    """Just THIS character's choices, tagged, for a console holding several.

    A doubled-up console shows one character at a time - a roster listbox picks who, and
    this is the detail panel's half of that. Not a filter over :func:`boarding_choices`: the
    shared, ungated choices are deduped onto the PRIMARY there, so filtering by tag would
    hide "Beam back up" from everybody except the first character. Asked directly, every
    character offers the open choices as well as its own.

    Falls back to the console's whole list when it is not holding this character, which
    is what a stale selection looks like after somebody else took a body over.
    """
    ch = boarding_channel_of(client_id)
    rec = _record(ch)
    parsed = rec.get("parsed")
    if parsed is None:
        return []
    lf_id = to_id(lifeform)
    if lf_id is None or lf_id not in boarding_held(client_id):
        return boarding_choices(client_id)
    out = dialogue_choices(parsed, lf_id, rec.get("speaker"))
    for c in out:
        setattr(c, "agent", lf_id)
    # The SAME forwarded tail `boarding_choices` appends, and for the same console. It has
    # to be here too, not only there: the inbox reply strip asks this function whenever
    # a character is active, which is the boarding party's main surface - so forwarding that
    # lived only in `boarding_choices` would be invisible exactly where it is needed. Both
    # lists must also agree, because `boarding_answer` re-derives one of them to read the
    # index back.
    if client_id == boarding_duty_client(ch):
        seen = {(c.get("label"), c.get("target")) for c in out}
        for c in boarding_orphan_choices(ch):
            if (c.get("label"), c.get("target")) not in seen:
                out.append(c)
    return out

def boarding_answer(client_id, index, seq=None, agent=None):
    """Take one console's pick. True when it was accepted and the scene moved.

    ``agent`` names the character whose list the console RENDERED, for a doubled-up
    console showing one character at a time. Without it the index would be read against
    the console's full list and press the wrong thing - the lists are different lengths
    and in a different order.

    The pick is read against the scene of the channel the console is IN. Seqs are unique
    across channels, so a button left over from a channel the console has since left is
    refused like any other stale press.

    REFUSES, changing nothing, when: no beat is open; the token has moved on (somebody else
    already answered this beat); the index names no choice THIS character may take; or an
    outcome handler refuses the pick.

    The token is bumped BEFORE the outcomes run, exactly as ``hail_answer`` does it, so a
    second press arriving in the same frame is already carrying a stale token by the time it
    gets here.
    """
    cid = to_id(client_id)
    ch = boarding_channel_of(cid)
    rec = _record(ch)
    parsed = rec.get("parsed")
    if parsed is None:
        return False
    if seq is not None and seq != rec.get("seq", 0):
        return False
    choices = boarding_choices_for(cid, agent) if agent is not None else boarding_choices(cid)
    if not isinstance(index, int) or index < 0 or index >= len(choices):
        return False
    choice = choices[index]

    from_key = rec.get("key")
    rec["seq"] = _next_seq()

    speaker = rec.get("speaker")
    # The character that OWNS the choice, not the console's primary. With a doubled-up
    # console those differ, and applying as the primary would credit the wrong body -
    # and evaluate a cost or a refusal against someone who was not acting.
    actor = choice.get("agent") or boarding_me(cid)
    _REDIRECT.clear()
    _ANSWERED["actor"] = actor          # who answered: the reader credits them
    _ANSWERED["label"] = choice.label   # and with what, whatever words the press sent
    if dialogue_apply(actor, speaker, choice.outcomes) is False:
        # A handler refused (a cost that cannot be paid). The token has ALREADY moved, so
        # every console is holding a stale one and the beat is briefly unanswerable - which
        # is correct, not a deadlock: consoles repaint off the token, re-render with the new
        # one, and the same person can try something else. Bumping after the outcome instead
        # would reopen the same-frame race this exists to close.
        _REDIRECT.clear()
        return False
    # An outcome may send the scene somewhere other than the authored target - a failed
    # check (`check engineering 8 else botched`). Read and cleared in this one call.
    target = _REDIRECT.pop("target", choice.target)

    # Tell the transcript what was said, and what was not. The beat's replies live
    # here rather than on the message, so the inbox cannot work this out on its own -
    # and an answered beat showing nothing is the transcript losing the half that
    # matters. Best effort: a mission running without the inbox is unaffected.
    if ch == PARTY:
        try:
            from .messages import message_answer_scene
            message_answer_scene(from_key, choice.label,
                                 by=_name_of(actor),
                                 others=[c.label for c in choices
                                         if c.label != choice.label])
        except Exception:
            pass

    scenes = rec.get("scenes")
    if not target:
        members = sorted(boarding_channel_members(ch))
        if ch != PARTY and ch not in _STICKY:
            boarding_channel_close(ch)
        else:
            boarding_scene_end(ch)
        signal_emit("boarding_scene_ended", {"BOARDING_FROM": from_key,
                                             "BOARDING_CHANNEL": ch,
                                             "BOARDING_CLIENTS": members,
                                             "BOARDING_WHO": actor})
        return True
    boarding_scene_begin(scenes, target, speaker, channel=ch)
    return True


# Set by an outcome verb to send the scene to another target than the authored one.
# See `boarding_redirect`.
_REDIRECT = {}
# The character the last accepted answer was credited to - the one `boarding_answer`
# applied the outcomes as, which on a doubled-up console is not the primary.
_ANSWERED = {}


def boarding_redirect(target):
    """From inside an outcome handler: go to ``target`` instead of the choice's own.

    Only meaningful while ``boarding_answer`` is applying outcomes; it is cleared around
    every answer, so a stray call cannot leak into the next one.
    """
    _REDIRECT["target"] = target


def _chooser_line(actor):
    """`![](face://...) Name` - who made a choice, for the line above it in a
    transcript. Just the name when they have no face; None when there is nobody.

    Plain words: the text beside a lead face is drawn as written, so `**bold**` would
    show its asterisks (engine-seen)."""
    if actor is None:
        return None
    name = _name_of(actor)
    try:
        from ..faces import get_face
        face = get_face(to_id(actor))
    except Exception:                                    # noqa: BLE001
        face = None
    lead = _face_md(face, READER_CHOOSER_FACE_LINES) if face else ""
    return f"{lead} {name}" if lead else name


def _name_of(lifeform_id):
    """Who answered, for the transcript. The character, not the console - a console
    speaking for two bodies would otherwise credit both to the primary."""
    try:
        from .query import to_object
        who = to_object(lifeform_id)
        return who.name if who is not None else "the boarding party"
    except Exception:
        return "the boarding party"


def boarding_scene_count():
    """Reset-ledger probe: how many channels are holding a beat."""
    return sum(1 for rec in _SCENES.values() if rec.get("parsed") is not None)


def _boarding_scenes_clear():
    """Every channel gone, the party channel emptied, the token reset."""
    _SCENE.clear()
    _SCENES.clear()
    _SCENES[PARTY] = _SCENE
    _CLIENT_CHANNEL.clear()
    _STICKY.clear()
    _REDIRECT.clear()
    _SEQ[0] = 0


# --- The reader: the scene as a document ----------------------------------------------
#
# The same beats, read as a transcript instead of a card: each beat's line, then this
# console's choices as flat buttons (`signal://` lines in a gui_text_area). Picking one
# leaves the choice in the text and the next beat is added below it, so the console
# reads as the story so far.
#
# The transcript lives HERE, per console, not in the widget: a boarding screen repaints
# on every beat (`on change boarding_seq()`), and a rebuilt text area starts empty. The
# widget is only where the transcript is shown.
BOARDING_PICK_SIGNAL = "boarding_pick"
_READERS = {}       # client_id -> {"text", "seq", "agent", "area"}


#: How tall the faces in a transcript are, in text lines: the speaker's beside their
#: line, and the crew member's above the choice they made.
READER_SPEAKER_FACE_LINES = 3
READER_CHOOSER_FACE_LINES = 2


def _boarding_beat_text(client_id, agent=None):
    """This beat as markdown: the line - with the face of whoever says it, when someone
    in particular does - then this console's choices as signal lines."""
    from .amd import amd_choice_label
    ch = boarding_channel_of(client_id)
    if not boarding_is_open(ch):
        return "The conversation is over."
    seq = boarding_seq(ch)
    choices = (boarding_choices_for(client_id, agent) if agent is not None
               else boarding_choices(client_id))
    line = str(boarding_line(ch) or "")
    lead = ""
    if line.strip():
        face = boarding_line_face(ch)
        if face:
            lead = _face_md(face, READER_SPEAKER_FACE_LINES)
        else:
            image = boarding_line_image(ch)
            lead = _image_md(image, READER_SPEAKER_FACE_LINES) if image else ""
    lines = [f"{lead} {line}" if lead else line]
    if choices:
        lines.append("")
    agent_q = f"&agent={to_id(agent)}" if agent is not None else ""
    for i, ch in enumerate(choices):
        label = amd_choice_label(ch.get('label'))
        # SOMEBODY ELSE'S JOB, said so. A party short of a medic is still offered the
        # medic's line, on one console - and unmarked it reads as though this character
        # were qualified. The list form of this app and the inbox both say it; the story
        # form, which is the one on screen by default, did not.
        covering = getattr(ch, "forwarded", None)
        if covering:
            label = "%s (covering for %s)" % (label, str(covering).split(">=")[0].strip())
        lines.append(f"[{label}]"
                     f"(signal://{BOARDING_PICK_SIGNAL}?i={i}&seq={seq}{agent_q})")
    return "\n".join(lines)


def _boarding_reader_sync(client_id, chosen=None, by=None):
    """Bring one console's transcript up to the current beat. Returns its text.

    Any choices still live in it are settled first - to `chosen` where that was one of
    them, otherwise dropped, because the beat they belonged to has moved on. `by` is a
    line saying who chose, put just above the choice made.
    """
    from .amd import amd_choices_settle
    state = _READERS.setdefault(client_id, {"text": "", "seq": None, "agent": None,
                                            "area": None})
    ch = boarding_channel_of(client_id)
    seq = boarding_seq(ch)
    if state["seq"] != seq or chosen is not None:
        text = amd_choices_settle(state["text"], chosen, before=by) if state["text"] else ""
        if state["seq"] != seq:
            beat = _boarding_beat_text(client_id, state["agent"])
            # A CHANGE OF CHANNEL is marked, so a console that walked into a side
            # conversation - or came back out of one - can see where the transcript
            # stopped being about the last thing.
            # Plain words, not `---`: a text area has no rule and drew it as "- ---".
            if text and state.get("channel", PARTY) != ch:
                text = f"{text}\n\n~ ~ ~"
            text = f"{text}\n\n{beat}" if text else beat
            state["seq"] = seq
        state["channel"] = ch
        state["text"] = text
    return state["text"]


def boarding_reader_text(client_id, agent=None):
    """The transcript for one console, up to and including the current beat.

    ``agent`` is the character whose choices this console shows, for a console holding
    several; None shows the console's whole list, as ``boarding_choices`` does.
    """
    signal_observe(_boarding_reader_on_pick)
    state = _READERS.setdefault(client_id, {"text": "", "seq": None, "agent": None,
                                            "area": None})
    if agent is not None and to_id(agent) != state["agent"]:
        # Another character's turn: its choices, not the last one's, from here on.
        state["agent"] = to_id(agent)
        state["seq"] = None
    return _boarding_reader_sync(client_id)


def boarding_reader_note(client_id, text):
    """Add a line to this console's transcript that is not a beat - something picked up.

    It goes below whatever is there, and the Act app then has something to show. A
    console with no transcript yet starts one at the beat it is on, so the next sync
    does not add a beat that is not happening."""
    if not text:
        return
    state = _READERS.get(client_id)
    if state is None:
        ch = boarding_channel_of(client_id)
        state = _READERS[client_id] = {"text": "", "seq": boarding_seq(ch), "agent": None,
                                       "area": None, "channel": ch}
    state["text"] = f"{state['text']}\n\n{text}" if state["text"] else text
    # The revision moves either way: an xESS Act app polls it, and one showing nothing
    # yet has no area here to write to.
    state["rev"] = state.get("rev", 0) + 1
    if not state.get("in_region") and state.get("area") is not None:
        state["area"].value = state["text"]


def boarding_find_note(client_id, who, text, sprite=None):
    """A transcript line about something found - `who` did `text` - led by its picture
    when the art has one. Shared by the ground's pickups and a suit's hauls, so a find
    reads the same whichever body found it."""
    image = _drawable(sprite)
    lead = _image_md(image, READER_CHOOSER_FACE_LINES) if image else ""
    line = f"{_name_of(who)} {text}" if who is not None else str(text)
    boarding_reader_note(client_id, f"{lead} {line}" if lead else line)


def boarding_reader_has_text(client_id):
    """Whether this console has a transcript to show - a conversation now, or one it has
    had. The Act app keeps showing it after the conversation ends."""
    return bool((_READERS.get(client_id) or {}).get("text"))


def boarding_reader_revision(client_id):
    """Moves when a reader inside a REGION needs its owner to repaint it (a scroll, a
    pick). Put it in the revision the owner already polls - see ``in_region``."""
    return (_READERS.get(client_id) or {}).get("rev", 0)


def _boarding_reader_repaint(client_id, area):
    """The area asked to be redrawn: keep where it is scrolled to, and move the revision
    so the region's owner rebuilds - the only repaint the engine draws right there."""
    state = _READERS.get(client_id)
    if state is None:
        return
    state["scroll"] = (area.scroll_line, area.follow_tail)
    state["rev"] = state.get("rev", 0) + 1


def boarding_reader(text_area, client_id, agent=None, in_region=False):
    """Show the scene as a transcript in ``text_area`` and keep it there.

    Call it each time the screen is built, with the area just made. The area shows the
    story so far, ending in this console's choices; picking one answers the beat through
    ``boarding_answer`` - so the same arbitration applies - and every console reading
    the scene gets the next beat added.

    ``in_region``: the area sits inside a ``gui_region`` (an ePADD or xESS app). A text
    area there cannot redraw ITSELF - the engine paints the new frame over the old, so a
    scroll shows both. With this set it leaves the redraw to the region's owner, which
    must poll :func:`boarding_reader_revision` and rebuild when it moves; the scroll
    position carries over to the rebuilt area.

    Example (MAST)::

        story = gui_text_area("")
        boarding_reader(story, client_id, boarding_ui_active)
    """
    text = boarding_reader_text(client_id, agent)
    state = _READERS[client_id]
    state["area"] = text_area
    state["in_region"] = bool(in_region)
    if text_area is not None:
        text_area.value = text
        # A transcript grows at the end, so that is the end it follows.
        text_area.anchor = "bottom"
        if in_region:
            text_area.repaint_cb = lambda area, _cid=client_id: _boarding_reader_repaint(_cid, area)
            text_area.restore_scroll = state.pop("scroll", None)
    return text_area


def _boarding_reader_on_pick(name, data):
    """A reader's choice: answer the beat, then bring every reader up to date."""
    if name != BOARDING_PICK_SIGNAL or not isinstance(data, dict):
        return
    cid = data.get("SIGNAL_CLIENT_ID")
    try:
        index = int(data.get("i"))
        seq = int(data.get("seq"))
    except (TypeError, ValueError):
        return
    agent = data.get("agent")
    agent = int(agent) if agent not in (None, "") else None
    chosen = data.get("SIGNAL_CHOICE")
    # WHO SHARED THAT BEAT, taken before answering - an answer that ends a side scene
    # sends its members back to the party, and they still need the pick settled.
    audience = boarding_channel_members(boarding_channel_of(cid)) | {cid}
    _ANSWERED.clear()
    accepted = boarding_answer(cid, index, seq, agent=agent)
    # WHO CHOSE, above the choice, for every reader - in a party of several consoles
    # the chip alone does not say. Only for a pick that was taken: a stale press
    # changed nothing, so it credits nobody.
    by = _chooser_line(_ANSWERED.get("actor")) if accepted else None
    if accepted and _ANSWERED.get("label"):
        # The words of the choice TAKEN, not whatever the press carried: they are what
        # every reader writes down, including ones that were never offered it.
        from .amd import amd_choice_label
        chosen = amd_choice_label(_ANSWERED["label"])
    # Every reader in that channel, the one that pressed included: whoever answered, the
    # beat moved on for all of them. A refused press (stale seq) still resyncs, which
    # shows the presser the beat somebody else moved to. A reader in ANOTHER channel is
    # left alone - its live choices belong to a different conversation, and settling
    # them against this pick would drop them.
    for client_id, state in list(_READERS.items()):
        if client_id not in audience:
            continue
        text = _boarding_reader_sync(client_id, chosen, by)
        if state.get("in_region"):
            # NEVER write a region's area out of band. It draws OVER whatever the region
            # holds now - engine-seen: a pick that ended a side scene rebuilt the xESS Act
            # app as "Nothing to decide here", and this write then painted the transcript
            # on top of it. The owner polls the revision and rebuilds in band.
            state["rev"] = state.get("rev", 0) + 1
            continue
        area = state.get("area")
        if area is not None:
            area.value = text


def boarding_reader_count():
    """Reset-ledger probe: consoles with a transcript."""
    return len(_READERS)


def boarding_clear():
    """The per-mission reset: no team, no beat, resolver handed back."""
    boarding_team_clear()
    _READERS.clear()
    _ANSWERED.clear()
    signal_unobserve(_boarding_reader_on_pick)
    _boarding_scenes_clear()
    _FACTS.clear()
    _REGISTERED_JOBS.clear()
    boarding_invite_clear()
    boarding_latecomers_unwatch()
    boarding_visit_clear()
    boarding_metric_uninstall()


# --- the invitation: a party you JOIN, rather than one you are dealt ----------------
#
# The original flow dealt characters round-robin across every console on the ship and
# rerouted all of them in one go. That works, and it takes the choice away: a console
# was on the surface before anybody at it had agreed to go, playing whoever the loop
# reached. An invitation is the same information, offered instead of applied - the
# mission says a party is forming and who is available, and each console decides.
#
# It also makes the surplus honest. Dealing had to double consoles up or strand
# characters; with an invitation, whoever wants to go takes somebody, and anyone left
# at their post simply stays there.

INVITE_KEY = "__BOARDING_INVITE__"


def boarding_invite(ship, roster, title=None, site=None, area=None):
    """Open a boarding party. Nobody moves until a console beams down.

    Args:
        ship: the ship the party leaves from.
        roster (list): the lifeforms available to play, in offer order.
        title (str, optional): what this place is called on screen.
        site (optional): the ship or station they are boarding. Given one, going down
            also puts each character on its interior with a body to walk - and the
            shipped BEAM DOWN button does that without knowing anything about it, which
            is the point of carrying it here rather than at the call site. Without one
            this is the dialogue-only party, which is still a valid way to play.
        area (str, optional): a TILE area to beam down into instead of an interior -
            the ground as data (``procedural/tilemap.py``). Going down stands each
            character there and the crew console draws the tile map.

    Returns:
        dict: the invitation.
    """
    invite = {
        "ship": to_id(ship),
        "roster": [to_id(m) for m in (roster or []) if to_id(m)],
        "title": title or "BOARDING PARTY",
        "site": to_id(site) if site is not None else None,
        "area": area,
        "open": True,
    }
    Agent.SHARED.set_inventory_value(INVITE_KEY, invite)
    return invite


def boarding_invitation():
    """The open invitation, or None."""
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    return invite if isinstance(invite, dict) and invite.get("open") else None


def boarding_invite_close():
    """Stop offering places. Anyone already down stays down."""
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    if isinstance(invite, dict):
        invite["open"] = False
        Agent.SHARED.set_inventory_value(INVITE_KEY, invite)


def boarding_invite_title():
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    return (invite or {}).get("title") or "BOARDING PARTY"


def boarding_invite_ship():
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    return (invite or {}).get("ship")


def boarding_invite_site():
    """The interior this party is boarding, or None for a dialogue-only party."""
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    return (invite or {}).get("site")


def boarding_invite_area():
    """The tile area this party beams down into, or None."""
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    return (invite or {}).get("area")


def boarding_open_roster(client_id=None):
    """The characters this console may still take, in the order they were offered.

    A body RESERVED for another console is not on offer - a crew-derived party knows
    who everybody is, and offering Lt Marek to the person who is not Lt Marek is how
    two consoles end up fighting over one body. Asked without a console, this is the
    unreserved remainder, which is what "who is still free" means to a script.
    """
    invite = boarding_invitation()
    if invite is None:
        return []
    taken = boarding_team()
    held_for_others = {lf for cid, lf in (invite.get("reserved") or {}).items()
                       if cid != client_id}
    return [m for m in invite.get("roster") or []
            if m not in taken and m not in held_for_others]


def boarding_beam_down(client_id, lifeform=None):
    """Take a place in the landing party.

    Args:
        client_id: the console volunteering.
        lifeform (optional): who to play. Defaults to the first character still free,
            so a console can simply say yes.

    Returns:
        The lifeform taken, or None when the invitation is closed or nobody is left -
        which a caller shows as "the party is full" rather than treating as an error.
    """
    if boarding_invitation() is None:
        return None
    free = boarding_open_roster(client_id)
    if lifeform is None:
        # THEIR OWN CHARACTER FIRST. A crew-derived party has one held for this
        # console, so "yes" means "go as myself" rather than "go as whoever is next".
        reserved = boarding_reserved(client_id)
        lifeform = reserved if reserved in free else (free[0] if free else None)
    else:
        lifeform = to_id(lifeform)
        if lifeform not in free:
            return None                  # somebody else took them first
    if lifeform is None:
        return None
    boarding_assign(client_id, lifeform)
    return lifeform


def boarding_beam_up(client_id):
    """Leave the surface. The console's own screen is the caller's business - this
    releases the character so somebody else could take them."""
    if not boarding_held(client_id):
        return False
    boarding_assign(client_id, None)
    return True


def boarding_invite_clear():
    Agent.SHARED.set_inventory_value(INVITE_KEY, None)


def boarding_invite_count():
    """Reset-ledger probe."""
    return 1 if Agent.SHARED.get_inventory_value(INVITE_KEY, None) else 0

# --- the party is the CREW -----------------------------------------------------------
#
# The older shape asked a mission for a separate cast: a crew post was "a label on a
# seat occupied by a human" and an away character "a body in the world", declared in
# two files. It works, and it means the person who has been Lt Marek all evening beams
# down as a stranger.
#
# Deriving the party from the crew makes you play YOURSELF, and it removes the step
# where a mission has to keep two rosters in step with each other.

CREW_ROLE = "boarding"

# The CONSOLE TYPE a boarded console wears. THREE words are in play here and no two of
# them may be the same:
#
#   CREW_ROLE        "boarding"       the boarder's LIFEFORM BODY
#   BOARDING_CONSOLE "boarding_crew"  the CLIENT sitting at a crew console
#   (already taken)  "crew"           every DAMCON TEAM on every ship
#
# That last one is why this is not simply "crew", and it cost an engine run to find.
# LegendaryMissions spawns damcon teams as `grid_spawn(..., "crew,damcons,lifeform")`
# (ai/grid_brains.mast), so `role("crew")` already means "damcon teams" and a nine-ship
# session has dozens of them. A console wearing the same word would join that set: an
# audience narrowed with `any_role("crew")` - announce(), overlays, comms - would try to
# address damcon grid objects, and a mission asking "which consoles are boarded" would
# get 29 answers, which is exactly what the probe logged.
#
# Grepping for READERS of `role("crew")` found nothing and was not enough; the role is
# created in a mastlib, so only grepping for what CREATES it shows the collision.
# The player still sees "Crew" - this is the internal name, not the label.
BOARDING_CONSOLE = "boarding_crew"


def _crew_bodies(ship_id, consoles=None, assign_missing=True):
    """[(client_id, lifeform)] - one body per console, from that console's crew post.

    A console that ALREADY HAS A BODY KEEPS IT. `_body_for` spawns a new lifeform every
    time it is called, so without this a mission that re-derives its party - to deal in a
    console that connected late, which is the ordinary reason - spawns a fresh crew on
    every pass and abandons the last one. Storm's Beacon re-invited every three seconds
    and so leaked one lifeform per console per tick, and a console that had already gone
    down found the body it was playing was no longer on the roster.

    So this is IDENTITY, the same rule `player_ensure` follows: ask for the party again
    and you get the same people back.
    """
    from .links import linked_to
    from .crew import crew_post_of
    from .roles import has_role

    if consoles is None:
        consoles = sorted(linked_to(ship_id, "consoles"))
    out = []
    for client_id in consoles:
        # The main screen is the whole room's view, not a person. It takes no body.
        if has_role(client_id, "mainscreen"):
            continue
        already = _body_already(client_id)
        if already is not None:
            out.append((client_id, already))
            continue
        post = crew_post_of(client_id)
        if post is None and assign_missing:
            post = _assign_a_crew_member(ship_id, client_id)
        if post is None:
            continue
        body = _body_for(post, client_id)
        if body is not None:
            out.append((client_id, body))
    return out


def _body_already(client_id):
    """The body this console is already playing or holding a place for, if it still is.

    Held first, reserved second: a console that has gone down is playing that character
    now, and its reservation is only the promise that got it there.
    """
    from .query import to_object
    for lf in list(boarding_held(client_id) or []):
        if to_object(lf) is not None:
            return lf
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    if isinstance(invite, dict):
        lf = (invite.get("reserved") or {}).get(client_id)
        if lf is not None and to_object(lf) is not None:
            return lf
    return None


def boarding_crew_roster(ship, consoles=None, assign_missing=True):
    """A landing party built from the people already at the consoles.

    One character per console, spawned from that console's crew post - their name,
    their face, their roles. A console that never picked somebody is ASSIGNED the next
    free member of the ship's roster, the way the picker would have, so skipping the
    crew screen does not lock a player out of the boarding mission.

    WHAT A SCENE GUARD READS. `Roles:` on the crew record when it has one; otherwise
    the CONSOLE they came from, added as a role here so `if science` gates a scan
    without the guard needing a second rule. A mission that already writes
    `Roles: medical` keeps working unchanged, and one that writes none still gates.
    """
    return [body for _cid, body in _crew_bodies(to_id(ship), consoles, assign_missing)]


def _assign_a_crew_member(ship_id, client_id):
    """Give a console that skipped the picker somebody to be."""
    from .crew import crew_choices_for, crew_pick_for, crew_assign, crew_post_of
    from .inventory import get_inventory_value
    console = get_inventory_value(client_id, "CONSOLE_TYPE", None)
    free = (crew_choices_for(ship_id, console, client_id)
            or crew_choices_for(ship_id, None, client_id))
    if not free:
        return None
    member = free[0]
    try:
        crew_assign(client_id, ship_id, console or "",
                    own_pick=crew_pick_for(ship_id, member.get("name"), client_id))
    except Exception:
        return None
    return crew_post_of(client_id)


def _body_for(post, client_id):
    """One crew post as a body on the ground."""
    from .lifeform import lifeform_spawn
    from .inventory import get_inventory_value
    name = getattr(post, "name", None) or "Crew"
    rank = getattr(post, "rank", "") or ""
    face = getattr(post, "face", "") or ""
    roles = getattr(post, "roles", "") or ""
    if not roles:
        # THE FALLBACK. No Roles on the record, so the seat they left is who they are -
        # added as a role rather than handled as a second rule at guard time, which
        # keeps `dialogue_guard_ok` one thing.
        roles = get_inventory_value(client_id, "CONSOLE_TYPE", "") or ""
    full = boarding_full_name(name, rank)
    words = [CREW_ROLE] + [w.strip() for w in str(roles).split(",")]
    body = lifeform_spawn(full, face, ", ".join([w for w in words if w]))
    # WHAT THEY WERE CAST AS, recorded at spawn. See `boarding_jobs`: roles added
    # later are things that HAPPENED to this person, not what they are for.
    set_inventory_value(body, JOBS_KEY,
                        [w for w in words if w and w != CREW_ROLE])
    # HOW GOOD THEY ARE, from the roster member this post was cast from - looked up by
    # the post's roster and key, NOT by the body's name. A name is what the player
    # typed: a member who renamed themselves kept their job (it rides on the post) and
    # lost every skill number, on the one machine at the table that had a saved name.
    skills = _post_skills(post)
    if skills:
        from .boarding_checks import boarding_skills_set
        boarding_skills_set(body, skills)
    return body


def _post_skills(post):
    """The `Skills:` of the roster member a post was cast from, as {skill: n}. {} for a
    post that came from no roster, or a member with no `Skills:` line."""
    try:
        from .crew import crew_roster
        from .boarding_checks import boarding_skills_parse
        roster = crew_roster(getattr(post, "roster", "") or "")
        key = str(getattr(post, "key", "") or "")
        if roster is None or not key:
            return {}
        for member in roster.get("members") or ():
            if str(member.get("key")) == key:
                return boarding_skills_parse(member.get("skills") or "")
    except Exception:                                   # noqa: BLE001
        pass
    return {}


def boarding_full_name(name, rank):
    """A crew member's name with their rank, WITHOUT saying the rank twice.

    A roster carries `rank` and `name` as separate fields, and a mission is free to
    put a short rank in the name as well - "Lt Mira Okonkwo" reads correctly on a
    bridge and is exactly what a person would type. Prefixing the long rank onto it
    gave "Lieutenant Lt Mira Okonkwo".

    NO TABLE OF RANKS, because there cannot be one: `rank` is free text a mission
    writes (`amd_schema`: "Captain, Lt. Commander - display only"), so a mod may use
    any rank in any service. The rule is a SUBSEQUENCE test - the name's first word
    abbreviates the rank when its letters appear in the rank, in order, starting from
    the same letter. "Lt" in "Lieutenant", "Cmdr" in "Commander", "Capt" in "Captain",
    "Ens" in "Ensign", and the rank written out in full.

    A PREFIX TEST DOES NOT WORK and was the first thing tried: naval abbreviations
    drop internal letters, so "Lt" is not a prefix of "Lieutenant" and nothing matched.

    **The known limit, stated rather than hidden:** a given name that happens to
    abbreviate the rank collides - "Lena" is a subsequence of "Lieutenant", so
    Lieutenant Lena would display without her rank. The failure is a MISSING rank
    rather than a doubled one, which is the quieter of the two, and a mission that
    minds can leave `rank` empty and write the name it wants.
    """
    name = (name or "").strip()
    rank = (rank or "").strip()
    if not rank:
        return name
    if not name:
        return rank
    if _abbreviates(name.split()[0], rank):
        return name
    return "%s %s" % (rank, name)


def _abbreviates(word, rank):
    """Whether `word` is `rank` with letters dropped - same first letter, in order."""
    word = "".join(c for c in word.lower() if c.isalnum())
    rank = "".join(c for c in rank.lower() if c.isalnum())
    if not word or not rank or word[0] != rank[0] or len(word) > len(rank):
        return False
    it = iter(rank)
    return all(c in it for c in word)


def boarding_invite_crew(ship, title=None, consoles=None, assign_missing=True,
                         site=None, area=None):
    """Open a landing party made of the crew, each body RESERVED to its own console.

    The difference from :func:`boarding_invite` is the reservation. A crew-derived party
    already knows who everybody is - the person has been Lt Marek all evening - so
    beaming down is a confirmation, not a casting call, and the crew console shows the
    character instead of a roster.
    """
    ship_id = to_id(ship)
    pairs = _crew_bodies(ship_id, consoles, assign_missing)
    invite = boarding_invite(ship, [body for _cid, body in pairs], title, site=site,
                             area=area)
    # CREW-DERIVED, recorded on the invitation. A party cast by a MISSION is deliberate -
    # three named people and no more - and must never grow a fourth because somebody sat
    # down. A party cast from the bridge is the opposite: it is "whoever is here", so
    # whoever arrives later belongs in it. Only this kind takes latecomers.
    invite["crew"] = True
    Agent.SHARED.set_inventory_value(INVITE_KEY, invite)
    for client_id, body in pairs:
        boarding_reserve(client_id, body)
    # And KEEP taking them, for as long as the invitation is open.
    boarding_latecomers_watch()
    # A crew party is whoever was on the bridge, so a missing job is an accident of
    # seating rather than the mission saying something. See `boarding_forwarding`. Only
    # when there IS one: a ship with no crew assigned at all falls back to whatever
    # cast the mission authored, and that cast is deliberate.
    if pairs:
        boarding_forwarding(True)
    return invite


# --- consoles that arrive after the party opened --------------------------------------
#
# THE WINDOW WAS A MOMENT WIDE, and that is the bug. `boarding_invite_crew` casts from the
# consoles linked to the ship AT THE INSTANT IT RUNS. A mission opens its party when the
# world says so - Storm's Beacon opens one the moment a relic finishes building, which is
# usually before anybody has finished picking a station - so the party was cast from an
# almost empty bridge, every body was reserved to one of those consoles, and everyone who
# connected afterwards was told "The party is full". Owner-reported twice: "consoles that
# connect late need to be able to", "the window is way too tight for clients connecting."
#
# Re-inviting on a loop was the mission-side workaround and it was worse than it looked:
# it stopped the moment somebody went out (so a truly late console still got nothing), and
# it re-spawned the whole cast every pass. The fix belongs here, where the invitation is.

_LATE_KEY = "__BOARDING_LATE_TASK__"


def boarding_latecomers():
    """Deal in every console that has appeared since the party opened.

    Safe to call as often as you like: a console with a body already keeps it, so this
    only ever spawns somebody for a console that has nobody.

    Returns:
        list: the (client_id, lifeform) pairs added this pass.
    """
    from .links import linked_to
    from .roles import has_role
    invite = boarding_invitation()
    if invite is None or not invite.get("crew"):
        return []
    ship_id = invite.get("ship")
    if ship_id is None:
        return []
    known = set((invite.get("reserved") or {}).keys())
    fresh = [cid for cid in sorted(linked_to(ship_id, "consoles"))
             if cid not in known and not has_role(cid, "mainscreen")
             and not boarding_held(cid)]
    if not fresh:
        return []
    added = []
    for client_id, body in _crew_bodies(ship_id, fresh, True):
        lf = to_id(body)
        if lf is None:
            continue
        roster = invite.setdefault("roster", [])
        if lf not in roster:
            roster.append(lf)
        added.append((client_id, body))
    if not added:
        return []
    Agent.SHARED.set_inventory_value(INVITE_KEY, invite)
    for client_id, body in added:
        boarding_reserve(client_id, body)
    return added


def boarding_latecomers_watch(seconds=2.0):
    """Keep dealing latecomers in while an invitation is open. Idempotent.

    A TICK RATHER THAN A HOOK ON THE SCREEN, because the Boarding Party app is not the
    only way a console learns there is a party - the xESS asks, a comms route can ask, a
    mission can ask - and a body that only exists once somebody opens the right app is a
    place that is there or not depending on where you were looking.

    Returns:
        The tick task, so a mission can hold it.
    """
    from ..tickdispatcher import TickDispatcher
    task = Agent.SHARED.get_inventory_value(_LATE_KEY, None)
    if task is not None:
        return task
    task = TickDispatcher.do_interval(_boarding_latecomers_tick, seconds)
    Agent.SHARED.set_inventory_value(_LATE_KEY, task)
    return task


def boarding_latecomers_unwatch():
    """Stop dealing people in. The party is what it is."""
    task = Agent.SHARED.get_inventory_value(_LATE_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:                                # noqa: BLE001
            pass            # already dropped by a reset or the end of the mission
    Agent.SHARED.set_inventory_value(_LATE_KEY, None)


def _boarding_latecomers_tick(t=None):
    """One pass, and it STOPS ITSELF once the invitation closes."""
    if boarding_invitation() is None:
        boarding_latecomers_unwatch()
        return
    boarding_latecomers()


# --- a place held for one console ----------------------------------------------------

def boarding_reserve(client_id, lifeform):
    """Hold one character for one console. Nobody else is offered them."""
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    if not isinstance(invite, dict):
        return False
    lf_id = to_id(lifeform)
    if lf_id is None:
        return False
    invite.setdefault("reserved", {})[client_id] = lf_id
    Agent.SHARED.set_inventory_value(INVITE_KEY, invite)
    return True


def boarding_reserved(client_id):
    """The character held for this console, or None."""
    invite = boarding_invitation()
    if invite is None:
        return None
    lf_id = (invite.get("reserved") or {}).get(client_id)
    return lf_id if lf_id in (invite.get("roster") or []) else None


# --- a party that is short of people --------------------------------------------------
#
# A scene guards its choices on job words - `if medical`, `if security` - and a crew
# party is whoever happened to be on the bridge. So a beat can carry a choice NOBODY
# present is qualified for, and that content is simply lost: the medic's line never
# appears, and a beat whose only way onward is guarded dead-ends.
#
# FORWARDING is the answer the crew already expect from a ship: the job goes to whoever
# is there. The choice is still offered, marked as forwarded so the player knows they
# are covering for somebody, and it goes to exactly ONE console - otherwise two people
# are offered the same orphaned job and the first press wins a race nobody knew about.

FORWARDING = False

#: A guard that is a JOB - `if medical`, which the parser normalizes to `medical >= 1`.
#: Anything else is the story's own lock and is never forwarded: `learned >= 3` is not
#: "we are short a medic", it is "you have not worked it out yet", and handing that over
#: because nobody qualifies would give away the answer.
#:
#: THE SHAPE IS NOT ENOUGH. A mission marks progress with roles too - LandingParty added
#: `briefed` to every body once the party had compared notes, and guarded its ending on
#: `if briefed >= 1`. That has the shape of a job, so it was forwarded to the duty console
#: before anybody had been briefed, handing over the ending. So a word is a job only when
#: it is one of the JOB WORDS: the stock jobs, whatever a body was cast with
#: (`JOBS_KEY`, which `_body_for` records from the crew record's `Roles:`), and whatever
#: a mission registers with `boarding_register_jobs`.
_JOB_GUARD = re.compile(r"^(?P<word>[\w ]+?)\s*>=\s*1$")
_NOT_A_JOB_GUARD = ("learned",)
_STOCK_JOBS = frozenset({"medical", "engineering", "security", "science", "helm",
                         "weapons", "comms", "captain", "command", "pilot", "doctor",
                         "tactical", "operations"})
_REGISTERED_JOBS = set()


def boarding_register_jobs(words):
    """Declare more words that are JOBS, so a guard on one can be forwarded.

    Args:
        words (str | list): a comma-separated string or a list of words.
    """
    if isinstance(words, str):
        words = words.split(",")
    for w in words or ():
        w = str(w).strip().lower()
        if w:
            _REGISTERED_JOBS.add(w)


def boarding_job_vocabulary():
    """Every word that counts as a job, as a set: stock, registered, and cast."""
    out = set(_STOCK_JOBS) | _REGISTERED_JOBS
    lifeforms = set(boarding_team())
    invite = Agent.SHARED.get_inventory_value(INVITE_KEY, None)
    if isinstance(invite, dict):
        lifeforms.update(invite.get("roster") or ())
    # And every boarding body, down or not: a job is a job before its holder beams down.
    from .roles import role
    lifeforms.update(role(CREW_ROLE))
    for lf in lifeforms:
        for w in get_inventory_value(lf, JOBS_KEY, None) or ():
            w = str(w).strip().lower()
            if w:
                out.add(w)
    # And the WHOLE roster of a crew party, seated or not. A body exists only for a console
    # somebody is sitting at, so a job the author wrote for an empty seat - `Roles:
    # quartermaster` on the helm officer, with nobody at helm - was not a job at all: the
    # quartermaster's choice was never forwarded and a short crew could not reach it,
    # while the surgeon's was, because `medical` happens to be a stock word.
    if isinstance(invite, dict) and invite.get("crew"):
        out |= _roster_jobs(invite.get("ship"))
    return out


def _roster_jobs(ship_id):
    """Every `Roles:` word on the roster that crews this ship, as a set."""
    try:
        from .crew import crew_roster_for
        roster, _why = crew_roster_for(ship_id)
    except Exception:                                    # noqa: BLE001
        return set()
    out = set()
    for member in (roster or {}).get("members") or ():
        roles = member.get("roles") or ()
        if isinstance(roles, str):
            roles = roles.split(",")
        for w in roles:
            w = str(w).strip().lower()
            if w and w not in _NOT_A_JOB:
                out.add(w)
    return out


def boarding_forwarding(on=True):
    """Whether orphaned job choices are offered to somebody who is not qualified.

    OFF by default, and `boarding_invite_crew` turns it ON. That split is the whole
    judgement: a hand-authored roster is CAST, so a party with no medic is the mission
    saying something, and quietly handing the medic's line to a pilot would undo it. A
    crew-derived party is just whoever was on the bridge when it happened, so the same
    gap is an accident of seating and the crew rightly expect the job to go to
    somebody.
    """
    global FORWARDING
    FORWARDING = bool(on)


def _is_job_guard(guard):
    """Whether a guard names a JOB rather than the story's own progress."""
    text = str(guard).strip()
    if re.match(r"^[A-Za-z_][\w ]*$", text):
        text = f"{text} >= 1"            # `if medical` is `medical >= 1`
    m = _JOB_GUARD.match(text)
    if not m:
        return False
    word = m.group("word").strip().lower()
    return word not in _NOT_A_JOB_GUARD and word in boarding_job_vocabulary()


def boarding_duty_client(channel=None):
    """The console that catches what nobody else can take.

    The lowest client id in the channel - an arbitrary rule, but a STABLE one, which
    is the property that matters: every console computes the same answer, so a
    forwarded choice appears once rather than on whichever screen repainted last.
    """
    down = sorted(c for c in boarding_channel_members(channel) if boarding_held(c))
    return down[0] if down else None


def boarding_orphan_choices(channel=None):
    """Choices in a channel's open beat that nobody in that channel can take."""
    rec = _record(channel)
    parsed = rec.get("parsed")
    if parsed is None or not FORWARDING:
        return []
    speaker = rec.get("speaker")
    team = set()
    for cid in boarding_channel_members(channel):
        team.update(boarding_held(cid))
    if not team:
        return []
    out = []
    for c in parsed.get("choices") or []:
        guard = c.get("guard")
        if not guard or not _is_job_guard(guard):
            continue                     # open to everybody, or not a job at all
        if any(dialogue_guard_ok(guard, lf, speaker) for lf in team):
            continue                     # somebody here is qualified
        obj = MastDataObject({"label": c["label"], "target": c["target"],
                              "outcomes": c.get("outcomes") or []})
        # WHAT IT IS FOR, so the screen can say "nobody here is a medic" rather than
        # silently handing over a job. The guard text is what the author wrote.
        setattr(obj, "forwarded", str(guard))
        out.append(obj)
    return out


# --- a visit: the party, its scene and the way home, as one thing ---------------------
#
# A boarding scene had a beginning and no end. A mission opened a party, began a scene, and
# when the last room closed nothing happened: the invitation stayed open, every console
# kept the character it was playing, and a console that went down late arrived in a room
# with nothing in it. Open Universe's sites had it worse - the scene they began was never
# closed either, and "is a scene open" is what every later arrival asked first, so one
# visit ended boarding for the session.
#
# Each mission could write its own watcher, and each would get one of the four steps
# wrong. So the whole visit is one call: open, begin, and - when the scene closes - shut
# the party, bring everybody home, and say so.

VISIT_KEY = "__BOARDING_VISIT__"
_VISIT_TASK_KEY = "__BOARDING_VISIT_TASK__"

#: Things already said this mission, so a visit opened ten times complains once.
_VISIT_SAID = set()


def _visit_say(message, once=None):
    """Report a visit that cannot work where the author will see it.

    `log(msg, "boarding", "warning")` alone goes NOWHERE - a named category has no
    handler unless the mission attached one - and that is how "the quest completed and
    no party formed" came to have a clean log beside it. The same line goes to
    `mast.runtime`, which is the log everybody reads and the one a headless test fails
    on.
    """
    if once is not None:
        if once in _VISIT_SAID:
            return
        _VISIT_SAID.add(once)
    from .execution import log
    log(message, "boarding", "warning")
    import logging
    logging.getLogger("mast.runtime").warning("boarding_visit: " + message)


def boarding_visit(ship, scenes, first, title=None, cast=None, site=None, area=None,
                   place=None, stories=None):
    """Run one boarding visit from start to finish.

    Opens the party, begins the room ``first``, and from then on watches the scene: when it
    closes - a choice that leads nowhere, ``- [Return to the ship]()`` - the party is shut,
    every console that went is put back at its station, and ``boarding_visit_ended`` is
    emitted with ``BOARDING_SHIP`` and ``BOARDING_TITLE``.

    Args:
        ship: the ship the party leaves from.
        scenes: the rooms - what ``dialogue_scenes(amd_section(doc, "boarding"))`` returns.
        first (str): the key of the room the party arrives in.
        title (str, optional): what the crew sees as the name of the place.
        cast (list, optional): lifeforms to offer INSTEAD of the crew. Leave it out and the
            party is the crew as themselves - the name, face and ``Roles:`` each console
            already has, one body held for each (see :func:`boarding_invite_crew`). That is
            the default because it is one identity: who you are on the bridge is who goes
            aboard. Hand in a cast only when the people going are deliberately not the crew.
        site, area (optional): as :func:`boarding_invite` - an interior or a tile area to
            stand the party in. Without either this is the dialogue-only party.
        place (str, optional): the key this place's ``learn`` facts are kept under.
            Defaults to ``title``, then to ``first``. Each place counts only its own, and
            keeps them for the mission, so a return visit finds what was learned before.
        stories (optional): a section of quests that each belong to ONE person -
            ``amd_section(doc, "side_stories")``, each record saying ``For: medical`` (a
            job), or a roster member's key or name. Each is handed to its person as they
            come aboard. One nobody aboard answers to is handed to nobody.
            Give two places the same key only if they really are one place.

    Returns:
        dict: the invitation - or None, with nothing opened, when a party or a scene is
        already open, or ``first`` names no room. Checked BEFORE the party opens: a crew
        offered a place with no room in it has no way to find out why. That, and a
        mission with no boarding console to show the scene on, is said in
        ``mast.runtime.log``.
    """
    if boarding_visiting() is not None or boarding_invitation() is not None or boarding_is_open():
        return None
    if not first or dialogue_get(scenes or {}, first) is None:
        rooms = ", ".join(sorted(str(k) for k in (scenes or {}))) or "none at all"
        _visit_say("there is no room '%s', so nothing was opened. The rooms it was given: "
                   "%s. Check the key of the first room, and that the section holding "
                   "the rooms is the one the map body reads." % (first, rooms))
        return None
    # THE SCREEN A BOARDED CONSOLE BECOMES is a MAST label, and the library has none: the
    # `boarding` addon declares it. Without that addon a crew member presses BEAM DOWN and
    # is left on the app that offered it, with the room and its choices nowhere on screen.
    from .gui.console_tab import gui_tab_boarded_back_tab
    if gui_tab_boarded_back_tab() is None:
        _visit_say("no boarding console is loaded, so a crew member who beams down has no "
                   "screen for the scene. Add the LegendaryMissions `boarding` addon to "
                   "this mission's story.json.", once="no-console")
    # `if medical` is answered against the answering character's roles. Composes with
    # whatever resolver a mission already installed, so calling it here is always safe.
    boarding_metric_install()
    if cast:
        invite = boarding_invite(ship, cast, title, site=site, area=area)
    else:
        invite = boarding_invite_crew(ship, title, site=site, area=area)
    # BEFORE the first room is begun: beginning it picks its line, and a line gated on
    # `learned` has to be asked about THIS place.
    # `stories`: a section of quests that each belong to ONE person (`For: medical`).
    # Handing them out was a second call a mission had to make, in a route of its own -
    # under `boarding_visit(...)` it found nobody aboard yet and handed out nothing. The
    # visit hands each one to its person as they arrive (see the tick below).
    Agent.SHARED.set_inventory_value(VISIT_KEY, {
        "ship": to_id(ship), "title": boarding_invite_title(), "first": first,
        "place": str(place or title or first), "stories": stories})
    boarding_scene_begin(scenes, first)
    _visit_watch()
    return invite


def boarding_visiting():
    """The visit in progress - ``{"ship", "title", "first", "place", "stories"}`` - or None."""
    visit = Agent.SHARED.get_inventory_value(VISIT_KEY, None)
    return visit if isinstance(visit, dict) else None


def _visit_bring_home(client_id):
    """Put one console back at the station it left.

    Its own function so the end of a visit has one place where the screen is touched: the
    door rebuilds a console, and everything else about ending a visit is bookkeeping that
    must still happen if the door cannot.
    """
    from .gui.boarding_gui import boarding_go_up
    return boarding_go_up(client_id)


def boarding_visit_end():
    """End the visit now: close the scene and the party, bring everybody home, say so.

    What the watcher calls when the scene closes, and what a mission calls to cut a visit
    short - the ship is under fire, the clock ran out. Safe to call with no visit open.

    Returns:
        bool: True if there was a visit to end.
    """
    visit = boarding_visiting()
    if visit is None:
        return False
    # FIRST, so nothing below can come back in. Bringing a console home emits
    # `boarding_came_back`, and a route on that which ends the visit must find it ended.
    Agent.SHARED.set_inventory_value(VISIT_KEY, None)
    _visit_unwatch()
    boarding_scene_end()
    boarding_invite_close()
    boarding_latecomers_unwatch()
    for client_id in sorted(boarding_clients()):
        try:
            _visit_bring_home(client_id)
        except Exception as e:                           # noqa: BLE001
            from .execution import log
            log("boarding_visit: console %s could not be brought home: %s" % (client_id, e),
                "boarding", "warning")
        if boarding_held(client_id):
            # THE CHARACTER IS LET GO EITHER WAY. A console whose screen could not be
            # rebuilt must not be left playing somebody in a party that no longer exists.
            boarding_assign(client_id, None)
    signal_emit("boarding_visit_ended", {"BOARDING_SHIP": visit.get("ship"),
                                         "BOARDING_TITLE": visit.get("title"),
                                         "BOARDING_PLACE": visit.get("place")})
    return True


def _visit_watch():
    """Start looking for the end of the scene. Idempotent."""
    from ..tickdispatcher import TickDispatcher
    if Agent.SHARED.get_inventory_value(_VISIT_TASK_KEY, None) is not None:
        return
    Agent.SHARED.set_inventory_value(_VISIT_TASK_KEY,
                                     TickDispatcher.do_interval(_boarding_visit_tick, 1.0))


def _visit_unwatch():
    task = Agent.SHARED.get_inventory_value(_VISIT_TASK_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:                                # noqa: BLE001
            pass            # already dropped by a reset or the end of the mission
    Agent.SHARED.set_inventory_value(_VISIT_TASK_KEY, None)


def _boarding_visit_tick(t=None):
    """One look at the scene. NEVER RAISES.

    A raising interval callback pauses the sim and cannot be resumed - the dispatcher
    re-fires the same task the moment it is un-paused. Whatever goes wrong in here, the
    watcher stops and the mission carries on.
    """
    try:
        visit = boarding_visiting()
        if visit is None:
            _visit_unwatch()
            return
        if boarding_is_open():
            # The party's scene is still playing. Anyone who has come aboard since the
            # last look gets the personal quest that is theirs: the grant leaves a quest
            # already handed out where it went, so asking again each second is free.
            if visit.get("stories") is not None:
                from .boarding_quests import boarding_quests_grant
                boarding_quests_grant(visit.get("stories"))
            return
        boarding_visit_end()
    except Exception as e:                               # noqa: BLE001
        try:
            from .execution import log
            log("boarding_visit: the watcher stopped: %s" % (e,), "boarding", "warning")
        finally:
            _visit_unwatch()


def boarding_visit_said_count():
    """Reset-ledger probe: how many once-only visit notices have been used up."""
    return len(_VISIT_SAID)


def boarding_visit_clear():
    """The per-mission reset: no visit, no watcher. Emits nothing and moves nobody."""
    _visit_unwatch()
    Agent.SHARED.set_inventory_value(VISIT_KEY, None)
    _VISIT_SAID.clear()
