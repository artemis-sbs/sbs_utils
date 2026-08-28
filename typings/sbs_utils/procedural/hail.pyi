from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.futures import Promise
def DEBUG (msg):
    ...
def _hail_apply_scene_fields (record):
    """Adopt the fields the scene we have just BRANCHED to declares.
    
    A conversation is several scenes, and each is entitled to its own `Audio:`,
    `Presentation:` and title - the confrontation can be an orbit shot and the reply a
    portrait. Without this the record keeps the ENTRY scene's fields forever, so a
    branch replays the first scene's sound and never changes how it is drawn.
    
    Only fields the new scene actually declares are taken, so a scene that says nothing
    about presentation keeps what the conversation was already using. Called on a
    branch, not on resolve - the entry scene's fields are applied by `hail_offer_amd`,
    where an explicit override is still allowed to win."""
def _hail_band_drop (ship_id):
    """Take the orbit band down. Safe to call when there never was one."""
def _hail_bump_seq (ship_id):
    ...
def _hail_choices_from (choices):
    """Normalize a `choices=` argument. Accepts labels, `(label, target)` pairs, or
    dicts - so a MAST-driven hail needs no AMD document to offer an answer."""
def _hail_emit (ship_id, state, record=None, client_id=None, beat=None, choice=None):
    """One signal for every transition, so a listener is a single route rather than one
    per verb - the shape `viewscreen` already uses.
    
    `HAIL_CLIENT` is the repaint scope: None means every console of this ship, an id
    means only that one. A dial change that moved the MAIN screen is ship-wide and so
    passes None even though one console made it."""
def _hail_expired (record, now):
    ...
def _hail_get (ship_id, key, default):
    ...
def _hail_home_ship (client_id):
    """The ship this console belongs to.
    
    `viewscreen_home_ship` rather than `sbs.get_ship_of_client`: while an orbit shot is
    running the console is ASSIGNED to the subject, so the engine would answer with the
    raider that is being filmed."""
def _hail_lines_from (lines, speaker):
    """Normalize a `lines=` argument into beat dicts. Accepts a string or a sequence."""
def _hail_may_answer (client_id):
    """Only a comms console answers a hail.
    
    Enforced HERE rather than by hiding buttons: hiding is cosmetic, and a press can
    still arrive from a console that should not have one.
    
    `is not None`, NOT `bool(client_id)`: the SERVER console is client id 0, which is
    falsy, so the truth test short-circuited before `has_role` ever ran. The host could
    see a hail and never answer it - and since the placement default became Both, a hail
    lands on the main screen, which in an ordinary setup IS the server window. Every
    caller (hail_accept, hail_advance, hail_answer, hail_defer) just returned False,
    which is indistinguishable from "no open hail"."""
def _hail_now ():
    """Sim seconds, or 0.0 with no frame context (tests, lint, tooling)."""
def _hail_play_audio (record, ship_id=None):
    """Play a scene's `Audio:` once, server-side.
    
    Silent by design when there is no engine, no file, or the ship has hail audio
    turned off: a missing sound must never end the task that opened the conversation."""
def _hail_presentation_apply (ship_id):
    """Make the main screen agree with the open hail.
    
    Only `orbit` needs the engine: `portrait` and `still` are drawn by the console
    itself. Records `HAIL_TOOK_VIEWER` so `hail_close` only stands down a shot this
    hail actually started."""
def _hail_queue (ship_id):
    ...
def _hail_record_beat (ship_id, rec):
    """Append the beat being spoken NOW to the conversation's transcript.
    
    Recorded as it is SAID, not when a scene is resolved. A scene's beats are cached at
    resolve time, but a conversation that branches resolves several scenes and a player
    who closes early never hears the rest - so resolving is the wrong moment, and
    `lines` (which each new scene overwrites) is the wrong list. This is what makes a
    replay the whole conversation rather than only its last scene."""
def _hail_resolve_scene (ship_id, record):
    """Cache this scene's beats and choices onto the record.
    
    Called once per SCENE, not per repaint: `dialogue_beats` picks a random eligible
    variant every call, so a repaint that re-resolved would make the spoken line
    flicker - and the choices a console renders have to be the same list the server
    arbitrates against."""
def _hail_scene_node (record):
    """The node for this record's current scene, or None."""
def _hail_scenes (record):
    """The scene set this hail resolves against.
    
    The record's own `scenes` when the caller supplied one, else the mission's
    registry (`dialogue_register_scenes`). The fallback is what lets a declarative
    `Action: DS1 hails ds1_brief` - which has a key and nothing else - and a bare
    `hail_offer(scene=...)` work at all.
    
    Resolved LAZILY, never snapshotted onto the record: a record lives in ship
    inventory across the whole conversation, and a copy of the registry taken at
    offer time would go stale the moment a document reloaded."""
def _hail_screen_drop (ship_id):
    """Take the conversation off the main screen. Safe when it was never there."""
def _hail_settle (record, label=None, target=None, answered=False):
    """Hand an awaiting story the outcome, once.
    
    Resolved on EVERY ending - answered, declined, closed, even cancelled - because a
    story blocked on `await hail_ask(...)` that is never resolved simply stops, and a
    mission that stops halfway is worse than one that hears the wrong answer. `.value`
    is the label chosen, or None when the hail ended without one."""
def _hail_sid (ship):
    """A ship id, or None. Accepts an Agent or an id, like every other procedural call."""
def _hail_subject_gone (record):
    """True only for a NUMERIC subject that no longer exists. A string subject is
    resolved late by the renderer (it may be a role, or a ship not spawned yet), so it
    is never grounds for dropping a hail."""
def _hail_viewer_release (ship_id):
    """Give the main screen back, if this hail is what took it.
    
    Named-owner rather than a flag: `viewscreen_clear` refuses a release from
    anyone who is not the current claimant, so this is safe to call whenever a
    conversation ends however it ended - closed, declined, deferred, or the
    placement dial turned off - without first working out whether we were the one
    driving. A hail that was superseded by a cutscene simply does not own it any
    more, and says nothing."""
def awaitable (func):
    ...
def dialogue_apply (agent_id, speaker, outcomes):
    """Apply a chosen line's outcomes: built-in `signal`, plus any registered verbs. Returns
    False if a handler refuses (e.g. a cost can't be afforded) - the pick is rejected."""
def dialogue_beats (scene, agent_id, speaker=None):
    """One playable beat per `@cue`, in script order.
    
    Each is a MastDataObject `{speaker, surface, direction, text}` where `text` is a
    random eligible variant for that beat (gates use the same metric resolver as
    everything else) and `direction` is the beat's own, or the one written directly
    above the chosen line. A beat with no eligible line is dropped, so a fully gated
    beat disappears rather than playing silence.
    
    `speaker` here is the resolved CARD for guard evaluation (the mission's own
    record), not the beat's cue key - a beat names its speaker in `.speaker`, which
    the caller resolves per beat via `lifeform_speaker`."""
def dialogue_choices (scene, agent_id, speaker):
    """Choices whose guard passes, as MastDataObject (label/target/outcomes) so a mast comms
    route can render one button each."""
def dialogue_entry_for (scenes, speaker_key, when='comms'):
    """The entry scene key whose Speaker == speaker_key and When == `when`, or None.
    
    `when=None` means "either" - a caller that just wants this speaker's entry scene
    and does not care which door it is.
    
    Both sides of the speaker test are normalized, because everything else in this
    module goes through `_dlg_norm` and this did not: `Speaker: DS 1` did not match
    an actor written `DS-1` or `ds_1`, and a scene that is there reads as missing.
    (`DS1` remains a DIFFERENT key from `DS 1` - normalization settles case, dashes
    and spaces, not whether a name has one.)"""
def dialogue_fill_slots (text, agent_id=None, speaker=None, values=None):
    """Fill `{name}` in `text` from `values` first, then the registered resolvers.
    
    Unknown braces are LEFT ALONE. A writer may have meant them literally, and a
    half-substituted line is easier to recognize than one silently emptied."""
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
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def hail_accept (ship, hail_id=None, client_id=None):
    """Open a waiting hail. Normally reached from an `Answer:` button on the strip.
    
    Takes the head of the queue unless a `hail_id` names one. Resolves and caches the
    scene, bumps the arbitration token, and plays the scene's `Audio:` once - server
    side, so five consoles do not start five copies of it.
    
    Does NOT force any screen: each console shows the conversation only if its own
    placement dial says to.
    
    Returns:
        MastDataObject | None: the opened record, or None if nothing was answerable."""
def hail_active (ship):
    """The open conversation, or None."""
def hail_advance (ship, client_id=None, seq=None):
    """Move to the next beat - the crew reading on.
    
    Arbitrated exactly like `hail_answer`, and for the same reason: two officers
    pressing Continue in the same frame must not skip a line between them. A scripted
    or timed advance passes no `client_id` and so skips the console check.
    
    Returns:
        bool: True if another beat is now speaking; False when the beats are spent and
        the choices have gone live."""
def hail_answer (ship, index, client_id=None, seq=None):
    """Take one of the offered answers. The arbitration point.
    
    Refuses - returning False and changing nothing - when there is no open hail, when
    this console is replaying (a replay can never rewrite what was chosen), when the
    console is not a comms console, when `index` is out of range, when `seq` is stale
    (another console already answered), or when an outcome handler refuses the pick
    because the player cannot afford it.
    
    A scripted answer passes no `client_id` and so skips the console check.
    
    Returns:
        bool: whether the answer was taken."""
def hail_answer_label (record):
    """The text on a waiting hail's row. ASCII, and owned here so no console can drift.
    
    Who is calling, and what about: `DS 1 - Ambassador Kidnapped`. It used to read
    `Answer DS 1`, which said the same word on every row of a list already titled
    "Incoming Hails" - the verb is what the list IS, so spending the row's width on it
    crowded out the one thing that tells two calls apart. The scene's `Title:` earns
    that space instead.
    
    No colon: a row label is a style-property string to the engine, so `:` and `;` in
    it are parsed rather than drawn."""
def hail_ask (ship, **kwargs):
    """Offer a hail and WAIT for the crew to answer it.
    
    `hail_offer` is fire-and-forget, which suits a hail that interrupts whatever is
    happening. A linear story is the other shape - it offers a message and cannot go on
    until somebody takes it - and it was the shape with no primitive:
    
        answer = await hail_ask(ship, name="TSN Command", lines=briefing,
                                choices=["Acknowledge"], audio="audio/brief")
        if answer.value == "Acknowledge":
            ...
    
    Takes exactly `hail_offer`'s arguments. Resolves with `{value, target, answered,
    id, key}` where `value` is the chosen label - and resolves on every other ending
    too, with `value` None, so the story continues rather than hanging.
    
    Returns:
        HailPromise | None: None if the ship is unknown or `key` names a hail that is
        already waiting, exactly as `hail_offer` returns None."""
def hail_audio (ship):
    """Whether hails may play their `Audio:` on this ship. Defaults to YES - a scene
    that ships a sound file expects to be heard."""
def hail_audio_set (ship, on):
    """Turn hail audio on or off for a SHIP.
    
    Ship-wide, not per console, because the sound is played once for the whole bridge
    (`sbs.play_audio_file` to client 0). One sound, one switch - a per-console mute
    would silence a speaker nobody owns. Same last-writer-wins as the main screen.
    
    Returns:
        bool: whether the setting changed."""
def hail_beat (ship):
    """The beat being spoken right now, or None when the beats are done.
    
    The card is already resolved: `speaker` is the cue key, `name`/`face`/`color` are
    what to draw with.
    
    NEVER assign `.text` to a bare MAST variable. Dialogue text may contain `{`, and
    MAST re-formats a string on assignment as an f-string - the failure is reported
    against the assignment line, not against the text. Pass it straight to a widget."""
def hail_cancel (ship, hail_id=None):
    """Withdraw an unanswered hail - the caller hung up, or the story moved on.
    
    With no `hail_id`, drops every pending hail. Does not touch an OPEN conversation;
    use `hail_close` for that."""
def hail_choices (ship):
    """The answers on offer, capped at `HAIL_MAX_CHOICES`.
    
    Empty until the beats have all been spoken, so a console can render the strip
    unconditionally and get the right thing at every moment of the conversation."""
def hail_close (ship, declined=False):
    """End the open conversation and archive it for replay.
    
    The next queued hail stays PENDING rather than opening itself, so the strip
    re-fills with an `Answer:` entry instead of the screen cutting to a stranger.
    
    Stands the main-screen shot down only if this hail is what started it
    (`HAIL_TOOK_VIEWER`) - helm may already have taken the screen back, and putting our
    idea of "before" over the top would undo their change."""
def hail_console_cares (client_id):
    """Whether a `hail` signal is worth a repaint on this console.
    
    The guard every `on signal hail:` hook uses, so four idle consoles do not rebuild
    themselves because a fifth moved its dial."""
def hail_console_revision (client_id):
    """A number that CHANGES whenever this console's hail area should be redrawn.
    
    For `on change hail_console_revision(client_id): jump <this label>` - the polling
    form, which is what a console should use. The `hail` signal is the right thing for a
    story to react to, but a GUI task waiting in `await gui()` did not repaint from it,
    and the symptom is nasty: the hail is queued, the strip WOULD draw it, and the button
    only appears when something else happens to rebuild the page (switching console and
    back). `on change` re-evaluates each tick and cannot miss a transition.
    
    Cheap by construction - a few inventory reads, no allocation - because it is polled
    per console per tick. It folds in everything the strip renders from: how many hails
    wait, which one is open and how far through it is (`HAIL_SEQ` moves on every accept,
    beat and answer), and this console's own placement and replay state."""
def hail_consoles (ship, consoles='comms'):
    """The consoles of one ship that a hail addresses."""
def hail_decline (ship, hail_id=None):
    """Dismiss a hail without answering it - the crew simply does not pick up."""
def hail_defer (ship, client_id=None, seq=None):
    """Put the open conversation back in the list, unanswered.
    
    The `Back` row. Comms can read a hail through, step back out, and re-open it later -
    on the main screen, when the captain is ready for it. That is a different act from
    declining: nothing is archived, no outcome runs, and the hail is still waiting.
    
    It goes back to the START of its scene. A hail resumed mid-sentence would show the
    captain the second half of a conversation nobody else heard, and the beats are
    already cached, so replaying them costs nothing.
    
    Arbitrated like an answer - two officers must not both step out of a hail that only
    one of them is still in.
    
    Returns:
        bool: whether a conversation was put back."""
def hail_form (ship, client_id=None):
    """How the open hail should be drawn, or None.
    
    **On a COMMS console an `orbit` always reads as `portrait`.** That is settled, not
    deferred: comms has no 3D view, and giving it one means taking the client's SHIP
    ASSIGNMENT, which is what the engine ties `comms_control` and `comms_sorted_list`
    to - the console would stop being able to do its own job in order to watch a camera
    move. A face always works, and the console still LOOKS at the caller, because its
    2D radar follows the subject (`hail_view`).
    
    The cinematic shot belongs to the main screen, which is a screen and nothing else."""
def hail_is_active (ship):
    """Whether a conversation is open on this ship."""
def hail_log (ship):
    """Archived conversations, newest first. The info-panel history reads this."""
def hail_log_entry (ship, log_id):
    """One archived conversation by hail id, or None."""
def hail_more (ship):
    """Whether the conversation has another beat waiting to be heard.
    
    What the console asks to decide between a `Continue` button and the answers. The
    LAST beat is shown together with its choices - a line and the replies to it on
    screen at once, which is how the reference conversations read - so this is false on
    the final beat and a single-beat hail is answerable the moment it opens."""
def hail_offer (ship, scene=None, speaker=None, subject=None, presentation=None, backdrop=None, audio=None, face=None, name=None, color=None, title=None, priority=0, expires=None, key=None, lines=None, choices=None, scenes=None, slots=None):
    """Offer a hail to a ship. It waits in the queue until the crew answers it.
    
    Args:
        ship (Agent | int): the player ship being hailed.
        scene (str, optional): an AMD dialogue scene key (see `hail_offer_amd`).
        speaker (str, optional): who is calling - a cast/side/captain key.
        subject (Agent | int | str, optional): what an orbit shot films. May be an id
            OR a name/role resolved LATE, because the ship is usually spawned at
            runtime - the same contract `Subject:` has in AMD.
        presentation (str, optional): one of `HAIL_FORMS`.
        lines / choices (optional): a MAST-driven hail with no AMD behind it.
        key (str, optional): an idempotency key. Offering the same key twice is a
            no-op, so a re-emitted setup signal cannot queue the same hail again.
        slots (dict, optional): values for `{name}` in the scene's body. A registered
            resolver (`dialogue_register_slot`) covers the declarative path; this is
            the one-off.
    
    Returns:
        int | None: the hail id, or None if the ship is unknown or `key` is a repeat."""
def hail_offer_amd (ship, scenes, speaker_key, when='hail', **overrides):
    """Offer the hail a speaker's AMD scenes declare - the AMD front door.
    
    Finds the scene whose `Speaker:` is `speaker_key` and whose `When:` is `hail`, then
    reads its fence for the presentation fields. Anything passed as a keyword wins over
    the document, so a mission can film a different subject without editing the script.
    
    `scenes` may be None, in which case the mission's registry answers. `when=None`
    means "this speaker's entry scene, either door".
    
    Returns:
        int | None: the hail id, or None when that speaker declares no hail entry."""
def hail_pending (ship):
    """Hails waiting to be answered, best first.
    
    Prunes expired hails and hails whose subject has been destroyed, lazily, here -
    which is why there is no ticker and no extra entry in the reset ledger."""
def hail_pending_count (ship):
    """How many hails are waiting. Drives the answer strip."""
def hail_placed_here (client_id):
    """Whether this console is SET to show hails - whether or not one is open yet.
    
    The difference from `hail_shows_here` is the whole point. That one also asks
    whether a conversation is ACTIVE, which is the right question for "should I swap
    my centre panel out for a face" and the wrong one for "should I draw the waiting
    queue at all": a console that hid its queue on `hail_shows_here` would never show
    a call ARRIVING, because a call that is merely waiting is not active.
    
    A console with a real Off state - a single-seat cockpit, where there is no other
    surface for the conversation to appear on - needs this one."""
def hail_register_surface_renderer (name, fn):
    """Register what draws a cue's delivery surface: `fn(ship_id, beat, record)`.
    
    `amd_dialogue` already declares the surface NAMES (`comms`, `over`, `card`); this
    is what makes one of them do something. An unregistered surface is not an error -
    the beat still plays on the default surface."""
def hail_repaint_needed (client_id):
    """Whether the `hail` signal being handled right now should repaint THIS console.
    
    The one guard an `on signal hail:` hook needs. It reads the signal's own payload off
    the running task rather than making the console pass it, so a console cannot get the
    test subtly wrong, and it answers no to all three ways a repaint is wasted:
    
    * the signal is about another ship;
    * the signal named ONE console (a dial moved) and it was not this one;
    * this console is neither comms nor a main screen, or has nothing to show.
    
    Without the second test, one officer moving their own dial would rebuild every
    console on the bridge."""
def hail_replay_start (client_id, log_id):
    """Show an archived conversation on this console.
    
    A replay is READ-ONLY, and that is enforced in `hail_answer` rather than by leaving
    the buttons out: there is no code path from a replay to an outcome."""
def hail_replay_stop (client_id):
    """Stop replaying on this console."""
def hail_replaying (client_id):
    """The log id this console is replaying, or None."""
def hail_reset ():
    """Drop module-level hail state for a mission reset.
    
    The per-ship records need nothing here: they live in ship inventory and go with
    `Agent.clear()`. Only the injected resolver outlives a mission, which is why it is
    a LATCH in the reset ledger rather than a container."""
def hail_seq (ship):
    """The ship's current arbitration token. A console stamps this onto every answer
    button it renders; `hail_answer` refuses a press carrying an older one."""
def hail_set_speaker_resolver (fn):
    """Set how a speaker KEY becomes a name/face/color card.
    
    `fn(speaker_key, ship_id)` returns a mapping (or MastDataObject) with any of
    `name`, `face`, `color`. Explicit fields on the hail record always win over this,
    and this wins over the library's own lifeform lookup - so a mission can name its
    cast however it likes and the engine stays domain-free."""
def hail_shows_here (client_id):
    """Whether THIS console should be drawing the conversation instead of its normal
    centre - the dial on a comms console, the ship's `HAIL_MAIN` on a main screen."""
def hail_speaker (speaker_key, ship_id=None):
    """Resolve a speaker key to a card: `{name, face, color}`.
    
    Order is deliberate - the mission's resolver, then the library's own lifeform
    lookup, then a bare card carrying just the key as a name so something always
    renders. Never raises: a hail with an unresolvable speaker is still a hail."""
def hail_speaker_resolver_clear ():
    """Drop the resolver. Called by `reset_mission_state`: one registered by the LAST
    mission resolves keys against cast that no longer exists."""
def hail_subject (ship):
    """What an orbit shot should film. May be an id OR a late-resolved name/role."""
def hail_surface_renderer (name):
    """The renderer for a surface, or None."""
def hail_where (client_id):
    """What this console's placement drop-down reads.
    
    DERIVED, not stored, and that is the whole point. The two halves live in different
    places - whether THIS console swaps its own centre is the console's own business,
    but the main screen belongs to the ship and any comms console can move it. A dial
    that only remembered its own last click would read "Off" on the second officer's
    console while the hail was plainly up on the main screen, and their "Off" would
    then be a no-op. Deriving it means every comms console agrees about the main screen
    and disagrees only about itself, which is exactly the truth."""
def hail_where_for (label):
    """The placement a drop-down label means. Unknown labels read as `off`."""
def hail_where_label_for (value):
    """The drop-down label for a placement, so a repaint re-selects what is set."""
def hail_where_props (current=None):
    """The whole property string for the placement drop-down.
    
    The list key is `list:`, NOT `items:` - a dropdown built with the wrong key has no
    options to render and the engine dies allocating for it. `text:` is what shows
    while it is closed, so pass what this console is currently set to."""
def hail_where_set (client_id, where):
    """Point this console's dial somewhere.
    
    Writes both halves of the answer: this console's own `HAIL_WHERE`, and the SHIP's
    `HAIL_MAIN` when the value includes the main screen. Last writer wins on the ship
    half - deliberately the same arbitration science's On-Screen drop-down already has.
    
    A change that moved the main screen repaints EVERY console of the ship (the signal
    carries no client), so a second officer sees their own dial move rather than
    silently disagreeing with what is on screen."""
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
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
class HailPromise(Promise):
    """Resolved when a hail is answered, deferred or closed."""
