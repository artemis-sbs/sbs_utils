from sbs_utils.agent import Agent
from sbs_utils.mast.mast_node import MastDataObject
def _abbreviates (word, rank):
    """Whether `word` is `rank` with letters dropped - same first letter, in order."""
def _asked_on_the_bridge (agent_id):
    """True when a choice is being taken, or a condition asked, ON THE BRIDGE - by a
    ship (a hail) or by the story itself (a message reply) - rather than by somebody in
    a boarding party.
    
    WHO IS ASKING decides which pool `learn` writes to and `learned` counts, not where
    the ship happens to be parked. It used to be the place alone: with a party on offer
    at a ruin's door, a hail answered on the bridge filed its fact under that RUIN, and
    the same question asked two systems later - no party on offer - looked in the
    campaign's pool and found nothing. Lint clean, no log, and the answer never offered.
    
    A boarding scene asks for a body (a lifeform, which is never `__player__`) or for
    nobody at all (the room's line is the party's), so `None` is not the bridge."""
def _assign_a_crew_member (ship_id, client_id):
    """Give a console that skipped the picker somebody to be."""
def _beat_sender ():
    """Who the inbox says a beat is from: its speaker, else the PLACE.
    
    A room with no `Speaker:` is narration, and it was signed "Away" - which is this
    module's old name, not anything the crew was told. The place they went to is."""
def _beat_subject ():
    """What the inbox calls this beat: the room's NAME, as the author wrote it.
    
    It was the room's key - `airlock` under a heading that says `The Airlock` - because
    the key is what the scene is filed under. A key is the author's handle, lower case
    and one word; the crew should read the name."""
def _boarding_beat_text (client_id, agent=None):
    """This beat as markdown: the line - with the face of whoever says it, when someone
    in particular does - then this console's choices as signal lines."""
def _boarding_facts_restore (blob):
    """REPLACE what is known with what the save says. Nothing is announced."""
def _boarding_facts_snapshot ():
    ...
def _boarding_latecomers_tick (t=None):
    """One pass, and it STOPS ITSELF once the invitation closes."""
def _boarding_learn_outcome (agent_id, speaker, tokens):
    """The `learn` outcome verb: `- [Read the panel](panel) if engineering >= 1 ; learn cold`
    
    ASKED ABOUT TWO WAYS: `if learned >= 2` counts what the party knows here, and
    `if learned cold` asks for this one fact by name (see `_boarding_metric`).
    
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
def _boarding_reader_on_pick (name, data):
    """A reader's choice: answer the beat, then bring every reader up to date."""
def _boarding_reader_repaint (client_id, area):
    """The area asked to be redrawn: keep where it is scrolled to, and move the revision
    so the region's owner rebuilds - the only repaint the engine draws right there."""
def _boarding_reader_sync (client_id, chosen=None, by=None):
    """Bring one console's transcript up to the current beat. Returns its text.
    
    Any choices still live in it are settled first - to `chosen` where that was one of
    them, otherwise dropped, because the beat they belonged to has moved on. `by` is a
    line saying who chose, put just above the choice made."""
def _boarding_scenes_clear ():
    """Every channel gone, the party channel emptied, the token reset."""
def _boarding_visit_tick (t=None):
    """One look at the scene. NEVER RAISES.
    
    A raising interval callback pauses the sim and cannot be resumed - the dispatcher
    re-fires the same task the moment it is un-paused. Whatever goes wrong in here, the
    watcher stops and the mission carries on."""
def _body_already (client_id):
    """The body this console is already playing or holding a place for, if it still is.
    
    Held first, reserved second: a console that has gone down is playing that character
    now, and its reservation is only the promise that got it there."""
def _body_for (post, client_id):
    """One crew post as a body on the ground."""
def _chooser_line (actor):
    """`![](face://...) Name` - who made a choice, for the line above it in a
    transcript. Just the name when they have no face; None when there is nobody.
    
    Plain words: the text beside a lead face is drawn as written, so `**bold**` would
    show its asterisks (engine-seen)."""
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
def _drawable (key):
    ...
def _face_md (face, size):
    """A lead face for a transcript line, made safe to sit inside `face://...)`: a `)`
    or `?` in the string would end the reference or start its options."""
def _fact_fold (fact):
    """A fact as it is COMPARED: capitals and spacing do not matter."""
def _facts_of (place=None):
    ...
def _image_md (key, size):
    """A lead picture from the image atlas, made safe to sit inside `image://...)`."""
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
def _next_seq ():
    ...
def _persist_provider_register (name, snapshot_fn, restore_fn, library=False):
    """Register a state provider under `name`. Re-registering a name replaces it.
    
    If a save was already restored this mission and it held a blob under this name,
    the new provider is handed it at once - so a provider that registers late (an
    addon that loads after the campaign was opened) is not left empty.
    
    `library=True` is for sbs_utils' own modules, which register once as they
    import: the per-mission reset keeps those and drops the rest."""
def _post_skills (post):
    """The `Skills:` of the roster member a post was cast from, as {skill: n}. {} for a
    post that came from no roster, or a member with no `Skills:` line."""
def _record (channel=None, create=False):
    """The scene record for a channel. PARTY always exists; another is made on demand."""
def _roster_jobs (ship_id):
    """Every `Roles:` word on the roster that crews this ship, as a set."""
def _skill_metric (rest, agent_id):
    ...
def _visit_auto_beam (visit):
    """`BOARDING_AUTO_BEAM`: send every console on the ship down without anyone pressing
    BEAM DOWN - once each, so a console that beams up afterwards stays up.
    
    A SETTING, OFF BY DEFAULT, for a run with nobody at the consoles: a headless test
    that should reach the ground, an engine check with no mouse. It runs here, on the
    visit's own tick, so it needs no route in the mission and catches a console that
    connects after the party opened."""
def _visit_bring_home (client_id):
    """Put one console back at the station it left.
    
    Its own function so the end of a visit has one place where the screen is touched: the
    door rebuilds a console, and everything else about ending a visit is bookkeeping that
    must still happen if the door cannot."""
def _visit_on_signal (name, data):
    """The game is over, so the visit is. Observed only while a tile-map visit is open.
    
    `game_over` is what a quest carrying `Win:` / `Lose:` emits when it is completed or
    failed - from a scene's `; completes held`, a `Fails when:`, anything.
    
    ENDED HERE, NOT ON THE NEXT TICK. The results screen pauses the sim, and a paused sim
    ticks nothing: a visit left for its watcher to close stayed open behind the results,
    every console still wearing the character it went down as. This can run in the
    middle of the answer that ended the game, so `boarding_answer` checks for it and
    stops there rather than beginning the choice's next scene."""
def _visit_say (message, once=None):
    """Report a visit that cannot work where the author will see it.
    
    `log(msg, "boarding", "warning")` alone goes NOWHERE - a named category has no
    handler unless the mission attached one - and that is how "the quest completed and
    no party formed" came to have a clean log beside it. The same line goes to
    `mast.runtime`, which is the log everybody reads and the one a headless test fails
    on."""
def _visit_tile_tick (visit):
    """One look at a tile-map visit. There is no party scene to wait on, so this never
    ends the visit - the game ending does (`_visit_on_signal`), or the mission."""
def _visit_unwatch ():
    ...
def _visit_watch ():
    """Start looking for the end of the scene. Idempotent."""
def boarding_answer (client_id, index, seq=None, agent=None):
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
    gets here."""
def boarding_any_open ():
    """True when any channel has a beat open."""
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
def boarding_channel_close (channel):
    """End a channel's scene and send its members back to the party."""
def boarding_channel_join (client_id, channel):
    """Move one console into a channel. Its reader picks up that channel's beat."""
def boarding_channel_leave (client_id):
    """Put one console back in the party channel."""
def boarding_channel_members (channel=None):
    """The consoles in a channel, as a set. For PARTY: every console not elsewhere."""
def boarding_channel_of (client_id):
    """The channel this console is in - PARTY unless it was put somewhere else."""
def boarding_channel_open (channel, members=(), sticky=False):
    """Make a channel for a group of consoles and move them into it. Returns its name.
    
    Opening an existing channel only adds the members. ``sticky`` keeps the channel (and
    its members in it) after its scene ends; by default an ended side scene sends its
    members back to the party."""
def boarding_channels ():
    """Every channel with a scene open, PARTY first when it has one."""
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
def boarding_duty_client (channel=None):
    """The console that catches what nobody else can take.
    
    The lowest client id in the channel - an arbitrary rule, but a STABLE one, which
    is the property that matters: every console computes the same answer, so a
    forwarded choice appears once rather than on whichever screen repainted last."""
def boarding_encounter (scenes, key, client_id, speaker=None, channel=None, members=()):
    """Start a scene for ONE group - this console and whoever is with it.
    
    The everyday way into a side conversation: somebody walks up to the deputy, and the
    deputy's scene opens for them (and anyone else in ``members``) while the rest of the
    party carries on with whatever they are doing. If the channel already has a beat open
    the console simply joins it, so two people walking up to the same person share one
    conversation instead of starting two.
    
    Returns the channel name, or None when ``key`` names no scene."""
def boarding_facts (place=None):
    """Everything the party has worked out HERE, as a sorted list.
    
    ``place`` asks about somewhere else - after a visit has ended, say, with the
    ``BOARDING_PLACE`` that ``boarding_visit_ended`` carries."""
def boarding_facts_count ():
    """Reset-ledger probe: how many facts are held, across every place."""
def boarding_facts_forget (place=None):
    """Forget what was worked out at ``place`` - or everywhere, with no argument.
    
    For a place that RESETS: a wreck that is a different wreck each time it is found."""
def boarding_find_note (client_id, who, text, sprite=None):
    """A transcript line about something found - `who` did `text` - led by its picture
    when the art has one. Shared by the ground's pickups and a suit's hauls, so a find
    reads the same whichever body found it."""
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
def boarding_invite (ship, roster, title=None, site=None, area=None):
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
        dict: the invitation."""
def boarding_invite_area ():
    """The tile area this party beams down into, or None."""
def boarding_invite_clear ():
    ...
def boarding_invite_close ():
    """Stop offering places. Anyone already down stays down."""
def boarding_invite_count ():
    """Reset-ledger probe."""
def boarding_invite_crew (ship, title=None, consoles=None, assign_missing=True, site=None, area=None):
    """Open a landing party made of the crew, each body RESERVED to its own console.
    
    The difference from :func:`boarding_invite` is the reservation. A crew-derived party
    already knows who everybody is - the person has been Lt Marek all evening - so
    beaming down is a confirmation, not a casting call, and the crew console shows the
    character instead of a roster."""
def boarding_invite_crew_add (ship):
    """Bring another ship's crew into the open CREW party.
    
    Identity, like the rest of the party: a ship already in it changes nothing, and a
    console that already has a body keeps it.
    
    Returns:
        bool: True when that ship's crew is in the party afterwards. False with no party
        open, or when the open one was cast by a mission rather than from a bridge."""
def boarding_invite_crew_drop (ship):
    """Take one ship's crew back out of the open CREW party. Anyone already down stays.
    
    The bodies held for that ship's consoles are let go unless somebody is playing them,
    so a console of that ship is no longer offered a place. The party itself is left
    open for the ships still in it; with none left it is closed.
    
    Returns:
        bool: True when the ship was in the party."""
def boarding_invite_ship ():
    ...
def boarding_invite_ships ():
    """Every ship whose crew the open party is cast from: the one it was opened for,
    then any that joined. [] with no party open."""
def boarding_invite_site ():
    """The interior this party is boarding, or None for a dialogue-only party."""
def boarding_invite_title ():
    ...
def boarding_invited (client_id):
    """Whether the open party has a place for THIS console to ask for.
    
    A party a mission cast is open to every console, as it always was. A CREW party is
    the crews of particular ships, so a console of some other ship is not in it - and is
    told there is no party rather than that a party it was never part of is full."""
def boarding_is_open (channel=None):
    """True while a beat is open and answerable."""
def boarding_job_text (lifeform, default=''):
    """:func:`boarding_jobs` as one line, ready for a widget. ``default`` when there is none."""
def boarding_job_vocabulary ():
    """Every word that counts as a job, as a set: stock, registered, and cast."""
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
def boarding_learn (fact, place=None):
    """Record one fact. ``place`` is where it is filed: None for wherever the party is
    (:func:`boarding_place`), ``""`` for the CAMPAIGN - known everywhere.
    
    What ``; learn x`` and a quest step's ``Then: learn x`` both end in. True when the
    fact is new there. A set, so learning the same thing twice is learning it once."""
def boarding_learned (fact=None, place=None):
    """How many distinct things the party knows here - or whether it knows a given one."""
def boarding_learned_guard (name, agent_id=None):
    """Answer a guard's left side when it is about what is KNOWN, else None.
    
    ``learned`` is a count - of the campaign's facts when ``agent_id`` is a ship or the
    story (a hail on the bridge), of the place's otherwise. ``learned <fact>`` is one
    named fact, 1 or 0, asked of the place and then of the campaign. Anything else is
    not this module's word, and the caller's own resolver carries on. For a mission that
    installs a guard resolver of its own (Open Universe does) and still wants these two
    to answer."""
def boarding_learned_named (fact, place=None):
    """1 when the party knows this ONE fact - here, or as something the campaign knows.
    
    The named form of the guard: ``if learned manifest``. It asks the place the party is
    in and then the campaign's pool, so a fact learned in a bridge hail is known inside
    every site. (The count form never looks past the place.)"""
def boarding_line (channel=None):
    """The spoken line for this beat - the same one for every console."""
def boarding_line_face (channel=None):
    """The face of whoever says this beat's line, or None - so a transcript can show who
    is talking, and show nobody when nobody in particular is.
    
    In order: the person a ``talk:<key>`` channel is a conversation with (their
    ``Face:``); the speaker the scene was opened with, when that is someone with a face;
    the scene's ``Speaker:``, resolved the way a hail's is (``hail_speaker``). A
    narrator, a prop or a crowd has no face, and gets none."""
def boarding_line_image (channel=None):
    """The picture of what a beat is about when nobody's FACE is (``boarding_line_face``):
    an atlas key, or None.
    
    A prop's scene shows the prop - its open look once opened - and a person with no
    ``Face:`` shows the figure the map draws them with, facing the camera: the aliens
    the face art cannot draw still get a portrait. Only a key the art has registered
    counts, so a mission without the art shows nothing rather than a broken picture."""
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
def boarding_metric_word (word, fn):
    """Answer guards of the form ``<word> <argument>`` - ``if holding medkit >= 1``.
    
    ``fn(argument, agent_id)`` returns a number. The word is the first token of the
    guard's left side; a guard that is only the word (no argument) is still a role."""
def boarding_mirror_to_inbox (on=True):
    """Whether each beat also arrives as a message. On by default; a mission whose
    boarding play is entirely on the crew console can turn it off."""
def boarding_open_roster (client_id=None):
    """The characters this console may still take, in the order they were offered.
    
    A body RESERVED for another console is not on offer - a crew-derived party knows
    who everybody is, and offering Lt Marek to the person who is not Lt Marek is how
    two consoles end up fighting over one body. Asked without a console, this is the
    unreserved remainder, which is what "who is still free" means to a script."""
def boarding_orphan_choices (channel=None):
    """Choices in a channel's open beat that nobody in that channel can take."""
def boarding_party_channel ():
    """The name of the channel every console starts in."""
def boarding_place ():
    """Where the party is, as the key its facts are filed under.
    
    The visit's place; else the open invitation's title; else ``""``."""
def boarding_reader (text_area, client_id, agent=None, in_region=False):
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
        boarding_reader(story, client_id, boarding_ui_active)"""
def boarding_reader_count ():
    """Reset-ledger probe: consoles with a transcript."""
def boarding_reader_has_text (client_id):
    """Whether this console has a transcript to show - a conversation now, or one it has
    had. The Act app keeps showing it after the conversation ends."""
def boarding_reader_note (client_id, text):
    """Add a line to this console's transcript that is not a beat - something picked up.
    
    It goes below whatever is there, and the Act app then has something to show. A
    console with no transcript yet starts one at the beat it is on, so the next sync
    does not add a beat that is not happening."""
def boarding_reader_revision (client_id):
    """Moves when a reader inside a REGION needs its owner to repaint it (a scroll, a
    pick). Put it in the revision the owner already polls - see ``in_region``."""
def boarding_reader_text (client_id, agent=None):
    """The transcript for one console, up to and including the current beat.
    
    ``agent`` is the character whose choices this console shows, for a console holding
    several; None shows the console's whole list, as ``boarding_choices`` does."""
def boarding_redirect (target):
    """From inside an outcome handler: go to ``target`` instead of the choice's own.
    
    Only meaningful while ``boarding_answer`` is applying outcomes; it is cleared around
    every answer, so a stray call cannot leak into the next one."""
def boarding_register_jobs (words):
    """Declare more words that are JOBS, so a guard on one can be forwarded.
    
    Args:
        words (str | list): a comma-separated string or a list of words."""
def boarding_reserve (client_id, lifeform):
    """Hold one character for one console. Nobody else is offered them."""
def boarding_reserved (client_id):
    """The character held for this console, or None."""
def boarding_room_title (client_id=None):
    """The NAME of the room this console's party is in - `The Airlock` - or None.
    
    The heading the author wrote, not the key the room is filed under. None when no
    scene is open for that console."""
def boarding_scene (channel=None):
    """The current scene key, or None when nothing is open."""
def boarding_scene_begin (scenes, key, speaker=None, channel=None):
    """Open a beat: parse the scene, pick ONE line for everybody, bump the token.
    
    Returns the scene key actually opened, or None when the key names no scene - which is how
    a choice pointing at a missing target ends the conversation instead of hanging on it.
    
    ``channel`` is whose scene this is; the default is the whole party."""
def boarding_scene_count ():
    """Reset-ledger probe: how many channels are holding a beat."""
def boarding_scene_end (channel=None):
    """Close the conversation, leaving the token moved on so a late press still refuses."""
def boarding_seq (channel=None):
    """The arbitration token. A console stamps this onto every button it renders."""
def boarding_seq_for (client_id):
    """The token of the channel THIS console is in - what its screen should poll."""
def boarding_speaker (channel=None):
    """The opaque speaker record this beat is spoken by."""
def boarding_team ():
    """Every character currently under a console's control, as a set of ids.
    
    A set rather than a list: callers intersect it with role queries, and the same character
    must never appear twice however many clients were bound to it."""
def boarding_team_clear ():
    """Drop the whole team - beam-up, or the per-mission reset."""
def boarding_team_count ():
    """Reset-ledger probe: how many clients are bound to a character."""
def boarding_visit (ship, scenes, first=None, title=None, cast=None, site=None, area=None, place=None, stories=None):
    """Run one boarding visit from start to finish.
    
    Opens the party, begins the room ``first``, and from then on watches the scene: when it
    closes - a choice that leads nowhere, ``- [Return to the ship]()`` - the party is shut,
    every console that went is put back at its station, and ``boarding_visit_ended`` is
    emitted with ``BOARDING_SHIP`` and ``BOARDING_TITLE``.
    
    ON A TILE MAP there is no first room: the party walks, and a scene belongs to the
    thing or the person that opens it. Give ``area`` and leave ``first`` out::
    
        boarding_visit(ship, boarding_ground_scenes(), title="Kesh Relay", area="landing")
    
    That visit begins no scene and is not ended for want of one. ``scenes`` are what a
    prop's ``Scene:`` and a person's ``Talk scene:`` name; ``stories`` are handed out as
    people arrive, exactly as below; a console may beam up and come back down, and the
    visit is still there; a party that is ALL down comes round at the entry of the area
    it fell in after ``VISIT_REVIVE_SECONDS`` (``boarding_party_revived`` says so, and
    what that costs is the mission's to say). It ends when the mission calls
    ``boarding_visit_end()`` - or when the game does: a quest that carries ``Win:`` or
    ``Lose:`` being completed or failed (``; completes held``) ends the game with that
    sentence, and the visit with it.
    
    Args:
        ship: the ship the party leaves from.
        scenes: the rooms - what ``dialogue_scenes(amd_section(doc, "boarding"))`` returns.
        first (str): the key of the room the party arrives in. None, with ``area``, for a
            tile-map visit.
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
        ``mast.runtime.log``."""
def boarding_visit_clear ():
    """The per-mission reset: no visit, no watcher. Emits nothing and moves nobody."""
def boarding_visit_end ():
    """End the visit now: close the scene and the party, bring everybody home, say so.
    
    What the watcher calls when the scene closes, and what a mission calls to cut a visit
    short - the ship is under fire, the clock ran out. Safe to call with no visit open.
    
    Returns:
        bool: True if there was a visit to end."""
def boarding_visit_said_count ():
    """Reset-ledger probe: how many once-only visit notices have been used up."""
def boarding_visiting ():
    """The visit in progress - ``{"ship", "title", "first", "place", "stories"}`` - or None.
    
    A tile-map visit also carries ``"tile": True`` and its ``"area"``."""
def dialogue_apply (agent_id, speaker, outcomes):
    """Apply a chosen line's outcomes: built-in `signal`, plus any registered verbs. Returns
    False if a handler refuses (e.g. a cost can't be afforded) - the pick is rejected.
    
    AN ANSWER WHOSE OUTCOMES CANNOT BE READ DOES NOTHING. Every verb's own check runs
    first; if one fails (`; calm sentry, give power cell` - an item key is one word)
    NONE of the outcomes is applied, one line in `mast.runtime.log` says which and why,
    and the pick is still accepted so the conversation goes on. It used to raise after
    `calm` had already been applied. A handler that raises anyway is said the same way
    and skipped; the outcomes after it still run."""
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
def dialogue_register_outcome (verb, fn, check=None):
    """Register an outcome handler: fn(agent_id, speaker, tokens) - tokens are the words
    after the verb. Returning False refuses the pick; returning ``OUTCOME_STOP`` accepts
    it but skips the outcomes after this one. (`signal` is built in.)
    
    ``check(tokens)`` may say the words after the verb cannot be read: it returns None
    when they can, or one sentence for the writer when they cannot. Every check of an
    answer runs BEFORE any of its outcomes is applied (``dialogue_apply``), so an answer
    with one bad outcome does nothing at all rather than half of what it says."""
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
def signal_observe (fn):
    """Call `fn(name, data)` on every emit. Returns `fn`, so it can be used as a
    decorator. Registering the same callable twice registers it once."""
def signal_unobserve (fn):
    """Stop calling `fn`. Safe when it was never registered."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
