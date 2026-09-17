from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def _all ():
    ...
def _audience (to):
    """`to` as a set of console names, or None meaning everyone.
    
    A live token (`away`, `ship`) is kept as-is and answered at read time."""
def _audience_matches (want, console, client_id=None):
    """Does this reader fall inside the message's audience?"""
def _choices_from (choices):
    """Labels, `(label, target)` pairs or full dicts -> choice dicts.
    
    The same shape hail.py accepts (`_hail_choices_from`), so a story that offers a
    hail and a story that sends a message are written the same way."""
def _client_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def _console_name (console):
    """Whatever the caller said, as the name a script would use."""
def _cover_console ():
    """Who catches mail for an empty post.
    
    The boarding party's duty console when anybody is down - the same console `away.py`
    hands a forwarded job to, deliberately, so one person is covering rather than two
    halves of the job landing in different places. Nobody away means nobody is
    missing, and nothing is forwarded."""
def _crew_names (tokens):
    """`crew:` tokens as the names of the people they address, ids as a last resort."""
def _forwarded_here (want, console, client_id=None):
    """Whether this reader is covering for the post this message was sent to."""
def _guard_agent ():
    """Whose state a choice guard is asked about.
    
    The shared agent, not the reader's ship: a message is addressed to a CONSOLE and
    consoles do not own state - the mission does. A caller that wants a ship's own
    guards passes the message a pre-filtered choice list instead."""
def _here ():
    """The console reading right now.
    
    `page.console` is set by `gui_console()` at swap time and is NOT what a morphed
    console answers: `gui_console_enter` - the one door, and how the crew console is
    entered - writes CONSOLE_TYPE into the client's inventory and never touches
    `page.console`. So an crew console reported no console at all, `message_select`
    returned early, and nothing a crew member picked was ever remembered.
    
    CONSOLE_TYPE is the authoritative answer; the page is the fallback for a console
    that was never entered through that door.
    
    AND IT IS STICKY, because the answer decides what the inbox CONTAINS. Every read
    here is of ambient state - the frame's page, the client's inventory - and a moment
    when neither resolves is not the same fact as "this console has no mail". It used
    to be treated as one, and both halves of the screen changed at once:
    
    * `message_inbox()` filtered to nothing, so the panel repainted EMPTY.
    * `message_revision()` dropped its per-console part, so the number MOVED - and the
      number moving is exactly what `on change message_revision()` repaints on. The
      next frame resolved the console again, the number moved back, and it repainted
      again. An unresolved frame therefore cost two repaints and showed an empty inbox
      in between (reported 2026-09-02: "change the dropdown and it repaints empty",
      "sometimes it looks like two list boxes").
    
    So a resolved console is remembered, and an unresolved read answers with the last
    one rather than with nothing. A console that genuinely changes overwrites it on its
    next resolved read."""
def _is_boarding (console, client_id=None):
    """Whether this reader is on the boarding party.
    
    Asked of the CLIENT, because that is what away.py tracks - a console name cannot
    answer it. Falls back to the console name, which `gui_console_enter` sets to the crew-console type
    "boarding" when it morphs a console into a character."""
def _last_console (client_id):
    """The console this client last resolved to, or None if it never has."""
def _msg_nodes (node):
    ...
def _next_id (msgs):
    ...
def _pending ():
    ...
def _read_map ():
    ...
def _remember_console (client_id, console):
    """Record a console that DID resolve, and hand it back."""
def _reply_to (msg):
    """Who a reply is addressed to: whoever the message was addressed to, so the
    thread stays with the same people. An announcement is replied to in public."""
def _save (msgs):
    ...
def _save_pending (items):
    ...
def _seconds (value):
    """`After:` in seconds. Absent means 0 - delivered the moment the pile is drained."""
def _split_choices (body):
    """A message body -> (prose, choices).
    
    A `- [label](target) if guard ; outcomes` line is a reply, anything else is the
    message. The grammar is `amd_choice`'s, unchanged - it is what OU dialogue, hails
    and away scenes already use, so a writer who has authored any of those has
    nothing new to learn and `sbs lint` already understands the line."""
def _staffed ():
    """Console names somebody is actually sitting at, as this frame sees it.
    
    Read from the `console` ROLE rather than from a client list, because that role
    and `CONSOLE_TYPE` are written as a pair by `gui_console_enter` - the one door -
    and are what every other console-scoped thing in the library already tests. A
    client registry would have been a second answer to the same question, and the one
    that is empty until the engine fills it."""
def _stamp ():
    """Sim seconds, as a plain number. The inbox formats it; a story never sees it."""
def _unworn_crew (want):
    """The `crew:` tokens in `want` that nobody on the surface is wearing.
    
    The person-shaped twin of an empty chair: a letter to Marek when Marek is not down
    there is exactly the case forwarding exists for, and it is the only case in which a
    direct call should reach anyone else."""
def _wears_any (want, client_id=None):
    """Whether this reader is wearing a body one of the `crew:` tokens names.
    
    HELD, not just primary: a console can hold more than one character
    (`boarding_held`), and a letter to somebody you are carrying is a letter to you."""
def message_answer (mid, index, console=None, seq=None):
    """Take one of a message's replies.
    
    Returns the chosen dict, or None when the answer is refused - a stale seq, an
    already-answered message, an index that is not on offer for this console, or an
    outcome handler that says no (an unaffordable cost, say).
    
    The seq moves BEFORE the outcomes run, so a second console pressing in the same
    frame is refused rather than applying the outcome twice. That is hail.py's
    discipline and the reason is the same: the outcomes are the part that cannot be
    undone."""
def message_answer_scene (scene_key, label, by=None, others=None):
    """Record what an boarding beat was answered with.
    
    The beat's replies live in away.py, not on the message, so the message cannot
    know on its own that it has been settled - and an answered beat that still showed
    live buttons, or showed nothing at all, is the transcript losing the half that
    matters. Called by `boarding_answer` once a pick has actually been applied."""
def message_answered (mid):
    """What was chosen, or None. A console that arrives late reads the decision."""
def message_ask (text, to='*', sender=None, subject=None, choices=None, kind='mail'):
    """Send a message and wait for its reply.
    
        answer = await message_ask("Do we hold?", to="helm",
                                   sender="The Captain", choices=["Hold", "Break off"])
    
    Resolves with the chosen dict. A message nobody answers keeps the task waiting -
    compose it with a timeout when that matters:
    `promise_any(message_ask(...), delay_sim(60))`."""
def message_bump ():
    """Say that something the inbox draws has changed."""
def message_choices (mid, console=None):
    """The replies this console is offered on this message, guards applied.
    
    Empty once the message is answered - a decision that has been taken is not still
    on offer, and leaving the buttons up invites a second press that can only be
    refused."""
def message_clear ():
    """Drop every message and every read mark. For a mission that wants a clean
    inbox mid-game; the mission reset already does this on its own."""
def message_crew_token (lifeform):
    """The audience token addressing one boarder by the body they are wearing.
    
        message_send("Watch the gallery.", to=message_crew_token(marek))
    
    Built in one place so nothing has to remember the spelling, and so a caller that
    passes an Agent gets the same token as one that passes an id."""
def message_deliver_due (now=None):
    """Send every loaded message whose `After:` has passed, and forget it.
    
    A mission ticks this (a `do_interval`, or its own loop). Mail that arrives while
    the crew is flying is the point - a pile that all landed at t=0 would be a
    document, not a message.
    
    Returns:
        int: how many were delivered this call."""
def message_forwarded_from (msg, console=None, client_id=None):
    """The post this message was really addressed to, when the reader is covering.
    
    None when it is their own mail - so a screen can label a forwarded letter without
    having to work out the addressing a second time."""
def message_forwarding (on=True):
    """Whether mail for an empty post is forwarded to somebody. On by default."""
def message_get (mid):
    ...
def message_inbox (console=None):
    """Messages this console can see, newest first."""
def message_is_read (mid, console=None):
    ...
def message_load_amd (doc, to=None):
    """Read messages out of a parsed AMD document into the pending pile.
    
    A heading is a message when its fence has a `From`. The section heading, which
    has none, is skipped - the same rule the recipe loader uses.
    
    Args:
        doc: a parsed AMD document (`document_get_amd_file`, or `amd_mission_data` +
            `amd_section`).
        to (str, optional): who they are for when a message does not say. Defaults to
            everyone.
    
    Returns:
        int: how many were loaded."""
def message_mail (text, to='*', sender=None, subject=None):
    """A message from content - a letter from family, a friend, an admiral. Exactly
    `message_send(kind="mail")`, named so a story reads as what it is."""
def message_mark_read (mid=None, console=None):
    """Mark one message read for a console, or the whole inbox when `mid` is None."""
def message_pending_count ():
    """Reset-ledger probe for the undelivered pile."""
def message_promise_count ():
    """Reset-ledger probe: a task waiting on a reply that a reload will never bring."""
def message_revision (console=None):
    """What the inbox screen watches to know it must repaint.
    
    Combines the mail itself with THIS console's selection, because both change what
    is on screen and neither wakes `await gui()` on its own. Two consoles reading
    different messages therefore repaint independently."""
def message_select (mid, console=None):
    """Remember which message this console is reading, so it survives the repaint.
    
    A rebuild makes a NEW listbox whose selection starts empty; without this the
    reading pane would snap back to the newest message every time anything arrived."""
def message_selected (console=None):
    """The message id this console is reading, or None."""
def message_send (text, to='*', sender=None, subject=None, kind='crew', choices=None, scene=None):
    """Put a message in an inbox.
    
    Args:
        text (str): the body. Trimmed to MAX_TEXT.
        to (str, optional): console name, comma list, or "*" for everyone.
        sender (str, optional): who it is from. A crew message defaults to the console
            that sent it; a story message should always say.
        subject (str, optional): a short line for the list.
        kind (str, optional): "crew" or "mail" - what a story sends. The inbox shows
            them differently; nothing else depends on it.
        choices (list, optional): replies to offer, as `amd_choice` dicts
            (`{label, target, guard, outcomes}`). Capped at MAX_CHOICES. A message
            with none behaves exactly as it always did.
        scene (str, optional): an away scene key. Marks this message as that beat, so
            the inbox asks `away.py` for the replies instead of carrying its own -
            they differ per character and away already arbitrates them.
    
    Returns:
        dict: the stored message."""
def message_unread (console=None):
    """How many this console has not read. This is what the app badge shows."""
def messages_count ():
    """Reset-ledger probe."""
