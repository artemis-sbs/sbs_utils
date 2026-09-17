from sbs_utils.agent import Agent
from sbs_utils.mast.mast_node import MastDataObject
def _abbreviates (word, rank):
    """Whether `word` is `rank` with letters dropped - same first letter, in order."""
def _assign_a_crew_member (ship_id, client_id):
    """Give a console that skipped the picker somebody to be."""
def _boarding_latecomers_tick (t=None):
    """One pass, and it STOPS ITSELF once the invitation closes."""
def _boarding_learn_outcome (agent_id, speaker, tokens):
    """The `learn` outcome verb: `- [Read the panel](panel) if engineering >= 1 ; learn cold`
    
    DECLARED IN THE FILE, counted here. The alternative a mission reaches for first is a
    signal per fact plus a route per signal plus a role granted at the threshold - four
    moving parts, in three files, to express "they worked something out". And it cannot
    dedupe: a `signal` outcome carries no data but its NAME, and by the time a route sees
    it the choice that fired it is gone, so a reading taken twice counts twice."""
def _boarding_metric (name, agent_id, speaker):
    """A guard's left side, for an away scene.
    
    This owns exactly one idea: **does the acting character have this role?** ``medical``,
    ``security``, ``engineering``, ``captain`` - anything a lifeform was spawned with. 1 for
    yes so ``>= 1`` reads naturally.
    
    Anything else falls through to whatever resolver was installed before this one. A role
    the character LACKS also falls through rather than short-circuiting to 0, so a mission
    that means `credits` by a word we happen not to hold still gets the right answer."""
def _body_already (client_id):
    """The body this console is already playing or holding a place for, if it still is.
    
    Held first, reserved second: a console that has gone down is playing that character
    now, and its reservation is only the promise that got it there."""
def _body_for (post, client_id):
    """One crew post as a body on the ground."""
def _crew_bodies (ship_id, consoles=None, assign_missing=True):
    """[(client_id, lifeform)] - one body per console, from that console's crew post.
    
    A console that ALREADY HAS A BODY KEEPS IT. `_body_for` spawns a new lifeform every
    time it is called, so without this a mission that re-derives its party - to deal in a
    console that connected late, which is the ordinary reason - spawns a fresh crew on
    every pass and abandons the last one. Storm's Beacon re-invited every three seconds
    and so leaked one lifeform per console per tick, and a console that had already gone
    down found the body it was playing was no longer on the roster.
    
    So this is IDENTITY, the same rule `player_ensure` follows: ask for the party again
    and you get the same people back."""
def _is_job_guard (guard):
    """Whether a guard names a JOB rather than the story's own progress."""
def _mirror_to_inbox ():
    """Post the current beat to the boarding party's inbox.
    
    The message carries the LINE only. Its replies are asked of `boarding_choices` when
    the inbox draws them, because they differ per character and `boarding_answer` already
    arbitrates them - a copy on the message would be a second, competing path over
    one scene."""
def _name_of (lifeform_id):
    """Who answered, for the transcript. The character, not the console - a console
    speaking for two bodies would otherwise credit both to the primary."""
def boarding_answer (client_id, index, seq=None, agent=None):
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
    gets here."""
def boarding_assign (client_id, lifeform):
    """Put this client in control of this character. Returns the character's id.
    
    REPLACES whatever the console was holding, so this is still "you are Sorel". Passing
    ``None`` releases the console entirely, which is what beaming one person back up is.
    Use :func:`boarding_assign_also` to add a second character to the same console."""
def boarding_assign_also (client_id, lifeform):
    """Give this console ANOTHER character to speak for. Returns the character's id.
    
    A landing party smaller than its cast would otherwise leave characters standing on the
    surface that nobody controls - in nobody's :func:`boarding_team`, with the readings only
    they can take unreachable. Doubling up keeps every reading in play AND keeps it
    attached to a named person, which is the difference between a party game and one menu.
    
    Idempotent per character, and a no-op for a character another console already holds:
    two consoles answering as one person is worse than a console with nothing to answer."""
def boarding_beam_down (client_id, lifeform=None):
    """Take a place in the landing party.
    
    Args:
        client_id: the console volunteering.
        lifeform (optional): who to play. Defaults to the first character still free,
            so a console can simply say yes.
    
    Returns:
        The lifeform taken, or None when the invitation is closed or nobody is left -
        which a caller shows as "the party is full" rather than treating as an error."""
def boarding_beam_up (client_id):
    """Leave the surface. The console's own screen is the caller's business - this
    releases the character so somebody else could take them."""
def boarding_choices (client_id):
    """The choices THIS client's character may take, in authored order.
    
    The whole feature is here: the same parsed scene, evaluated against a different agent,
    yields a different list. A client with no character gets the unguarded choices only,
    which is the right answer for an observer rather than an error."""
def boarding_choices_for (client_id, lifeform):
    """Just THIS character's choices, tagged, for a console holding several.
    
    A doubled-up console shows one character at a time - a roster listbox picks who, and
    this is the detail panel's half of that. Not a filter over :func:`boarding_choices`: the
    shared, ungated choices are deduped onto the PRIMARY there, so filtering by tag would
    hide "Beam back up" from everybody except the first character. Asked directly, every
    character offers the open choices as well as its own.
    
    Falls back to the console's whole list when it is not holding this character, which
    is what a stale selection looks like after somebody else took a body over."""
def boarding_clear ():
    """The per-mission reset: no team, no beat, resolver handed back."""
def boarding_client_of (lifeform):
    """Which client is playing this character, or None. The reverse of :func:`boarding_me`."""
def boarding_clients ():
    """Every client currently controlling a character."""
def boarding_crew_roster (ship, consoles=None, assign_missing=True):
    """A landing party built from the people already at the consoles.
    
    One character per console, spawned from that console's crew post - their name,
    their face, their roles. A console that never picked somebody is ASSIGNED the next
    free member of the ship's roster, the way the picker would have, so skipping the
    crew screen does not lock a player out of the boarding mission.
    
    WHAT A SCENE GUARD READS. `Roles:` on the crew record when it has one; otherwise
    the CONSOLE they came from, added as a role here so `if science` gates a scan
    without the guard needing a second rule. A mission that already writes
    `Roles: medical` keeps working unchanged, and one that writes none still gates."""
def boarding_duty_client ():
    """The console that catches what nobody else can take.
    
    The lowest client id on the surface - an arbitrary rule, but a STABLE one, which
    is the property that matters: every console computes the same answer, so a
    forwarded choice appears once rather than on whichever screen repainted last."""
def boarding_facts ():
    """Everything the party has worked out so far, as a sorted list."""
def boarding_forwarding (on=True):
    """Whether orphaned job choices are offered to somebody who is not qualified.
    
    OFF by default, and `boarding_invite_crew` turns it ON. That split is the whole
    judgement: a hand-authored roster is CAST, so a party with no medic is the mission
    saying something, and quietly handing the medic's line to a pilot would undo it. A
    crew-derived party is just whoever was on the bridge when it happened, so the same
    gap is an accident of seating and the crew rightly expect the job to go to
    somebody."""
def boarding_full_name (name, rank):
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
    minds can leave `rank` empty and write the name it wants."""
def boarding_held (client_id):
    """Every character this console speaks for, primary first."""
def boarding_invitation ():
    """The open invitation, or None."""
def boarding_invite (ship, roster, title=None, site=None):
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
    
    Returns:
        dict: the invitation."""
def boarding_invite_clear ():
    ...
def boarding_invite_close ():
    """Stop offering places. Anyone already down stays down."""
def boarding_invite_count ():
    """Reset-ledger probe."""
def boarding_invite_crew (ship, title=None, consoles=None, assign_missing=True, site=None):
    """Open a landing party made of the crew, each body RESERVED to its own console.
    
    The difference from :func:`boarding_invite` is the reservation. A crew-derived party
    already knows who everybody is - the person has been Lt Marek all evening - so
    beaming down is a confirmation, not a casting call, and the crew console shows the
    character instead of a roster."""
def boarding_invite_ship ():
    ...
def boarding_invite_site ():
    """The interior this party is boarding, or None for a dialogue-only party."""
def boarding_invite_title ():
    ...
def boarding_is_open ():
    """True while a beat is open and answerable."""
def boarding_job_text (lifeform, default=''):
    """:func:`boarding_jobs` as one line, ready for a widget. ``default`` when there is none."""
def boarding_jobs (lifeform):
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
    
    Guards are UNAFFECTED: `dialogue_guard_ok` reads ROLES, never this."""
def boarding_latecomers ():
    """Deal in every console that has appeared since the party opened.
    
    Safe to call as often as you like: a console with a body already keeps it, so this
    only ever spawns somebody for a console that has nobody.
    
    Returns:
        list: the (client_id, lifeform) pairs added this pass."""
def boarding_latecomers_unwatch ():
    """Stop dealing people in. The party is what it is."""
def boarding_latecomers_watch (seconds=2.0):
    """Keep dealing latecomers in while an invitation is open. Idempotent.
    
    A TICK RATHER THAN A HOOK ON THE SCREEN, because the Boarding Party app is not the
    only way a console learns there is a party - the xESS asks, a comms route can ask, a
    mission can ask - and a body that only exists once somebody opens the right app is a
    place that is there or not depending on where you were looking.
    
    Returns:
        The tick task, so a mission can hold it."""
def boarding_learned (fact=None):
    """How many distinct things the party knows - or whether it knows a given one."""
def boarding_line ():
    """The spoken line for this beat - the same one for every console."""
def boarding_me (client_id):
    """The character this client is playing - the PRIMARY, when it holds several.
    
    Stays the answer to "whose face and name is on this screen", which is what every
    caller wants it for. :func:`boarding_held` is the whole list."""
def boarding_metric_install ():
    """Install the away guard resolver in front of whatever is already there.
    
    Idempotent: calling it twice does not chain the resolver to itself, which would recurse
    forever the first time a guard asked about a name nobody owned."""
def boarding_metric_uninstall ():
    """Put the previous resolver back.
    
    For tests, and for a mission that tears an away layer down; the per-mission reset calls
    it through :func:`boarding_clear`."""
def boarding_mirror_to_inbox (on=True):
    """Whether each beat also arrives as a message. On by default; a mission whose
    boarding play is entirely on the crew console can turn it off."""
def boarding_open_roster (client_id=None):
    """The characters this console may still take, in the order they were offered.
    
    A body RESERVED for another console is not on offer - a crew-derived party knows
    who everybody is, and offering Lt Marek to the person who is not Lt Marek is how
    two consoles end up fighting over one body. Asked without a console, this is the
    unreserved remainder, which is what "who is still free" means to a script."""
def boarding_orphan_choices ():
    """Choices in the open beat that no character on the surface can take."""
def boarding_reserve (client_id, lifeform):
    """Hold one character for one console. Nobody else is offered them."""
def boarding_reserved (client_id):
    """The character held for this console, or None."""
def boarding_scene ():
    """The current scene key, or None when nothing is open."""
def boarding_scene_begin (scenes, key, speaker=None):
    """Open a beat: parse the scene, pick ONE line for everybody, bump the token.
    
    Returns the scene key actually opened, or None when the key names no scene - which is how
    a choice pointing at a missing target ends the conversation instead of hanging on it."""
def boarding_scene_count ():
    """Reset-ledger probe: whether a beat is being held."""
def boarding_scene_end ():
    """Close the conversation, leaving the token moved on so a late press still refuses."""
def boarding_seq ():
    """The arbitration token. A console stamps this onto every button it renders."""
def boarding_speaker ():
    """The opaque speaker record this beat is spoken by."""
def boarding_team ():
    """Every character currently under a console's control, as a set of ids.
    
    A set rather than a list: callers intersect it with role queries, and the same character
    must never appear twice however many clients were bound to it."""
def boarding_team_clear ():
    """Drop the whole team - beam-up, or the per-mission reset."""
def boarding_team_count ():
    """Reset-ledger probe: how many clients are bound to a character."""
def dialogue_apply (agent_id, speaker, outcomes):
    """Apply a chosen line's outcomes: built-in `signal`, plus any registered verbs. Returns
    False if a handler refuses (e.g. a cost can't be afforded) - the pick is rejected."""
def dialogue_choices (scene, agent_id, speaker):
    """Choices whose guard passes, as MastDataObject (label/target/outcomes) so a mast comms
    route can render one button each."""
def dialogue_get (scenes, key):
    ...
def dialogue_guard_ok (guard, agent_id, speaker):
    """Evaluate a simple `lhs op number` guard (no guard -> True). Safe: only a resolved
    metric, a comparison operator, and an integer - never arbitrary code."""
def dialogue_parse (node):
    """Parse one scene node into a plain dict. Pure - no engine calls.
    
    Returns `speaker`, `when`, `lines` [(text, gate)], `choices`, and `beats` - one
    speech block per `@cue`, each `{speaker, surface, direction, lines}` where a
    line is `(text, gate, direction)`.
    
    `lines` is the FLAT list of every spoken variant in the scene, unchanged from
    before cues existed. That is what keeps the shipped single-speaker corpus
    working: `raider_hails.amd` is 8 scenes of bare `%` lines with the speaker in
    the fence, and `dialogue_pick_line` still sees exactly what it always saw. A
    scene with no `@` at all parses to one beat whose speaker is the fence's."""
def dialogue_pick_line (scene, agent_id, speaker):
    """A random NPC line whose gate passes (gates reuse the metric resolver). '' if the
    scene has no eligible line."""
def dialogue_register_outcome (verb, fn):
    """Register an outcome handler: fn(agent_id, speaker, tokens) - tokens are the words
    after the verb. Returning False refuses the pick. (`signal` is built in.)"""
def dialogue_set_metric_resolver (fn):
    """Set the guard metric resolver: fn(name, agent_id, speaker) -> number."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_role_list (id_or_obj):
    """Return the list of role names held by an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        list[str]: Role names, or an empty list if the agent does not exist."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Answers for the SERVER console too. It used to always say False for client id 0,
    which reads exactly like "the role is not there" - so a check on the server was
    indistinguishable from a real negative and passed silently for years.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
