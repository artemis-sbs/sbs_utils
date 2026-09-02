"""Messages a crew can read and send: from each other, and from home.

Two things arrive in the same inbox, deliberately:

- **Crew to crew.** Helm texts Engineering. It is a bridge simulator with people sat
  at separate screens who cannot see each other, and passing a note is half of what
  they would do if they could.
- **From content.** A mission, a quest beat or a map sends a letter from a character -
  family, a friend, a commanding officer. `message_send` is the same call either way,
  so a story never needs to know how the inbox works.

    message_send("Made it to the outer colonies. Mum sends her love.",
                 to="helm", sender="Your brother")
    message_send("All hands: contact in ten minutes.", sender="The Captain")

ADDRESSED TO A CONSOLE, not to a person. A console is what ePADD knows, what a client
is sitting at, and what survives a player disconnecting and coming back - a crew name
does none of those. `to="*"` is everyone, and is the default, because the common case
from a story is an announcement.

READ STATE IS PER CONSOLE, and kept beside the messages rather than on the client:
consoles get reassigned to different clients, and an inbox that forgot what it had
read every time someone swapped seats would be worse than not tracking it at all.

Everything lives on `Agent.SHARED`, which `clear_shared()` rebuilds per mission, so an
inbox does not survive into the next mission.
"""
from ..agent import Agent
from ..helpers import FrameContext
from .inventory import get_inventory_value as _client_value


# A counter the inbox screen watches. A signal does NOT wake `await gui()`, so a live
# panel has to poll something that changes - the same shape as `away_seq()`, which the
# away console has used for exactly this since it was written. Bumped by anything the
# screen would want to redraw for: new mail, an answer, a read mark, a new selection.
REVISION_KEY = "__MESSAGES_REV__"
MESSAGES_KEY = "__MESSAGES__"
READ_KEY = "__MESSAGES_READ__"
SELECT_KEY = "__MESSAGES_SEL__"   # console -> the message it is reading

# Long enough for a note, short enough that the inbox stays a list of messages rather
# than a document viewer. Text past this is cut with an ellipsis at send time, where
# the sender can still see what happened.
MAX_TEXT = 600
# Oldest are dropped past this. A party runs for hours and nothing prunes otherwise.
MAX_KEPT = 200
# Four is what a hail offers (hail.py HAIL_MAX_CHOICES) and the reason is the same: a
# reply strip wider than that stops being a decision and starts being a menu.
MAX_CHOICES = 4


def message_revision(console=None):
    """What the inbox screen watches to know it must repaint.

    Combines the mail itself with THIS console's selection, because both change what
    is on screen and neither wakes `await gui()` on its own. Two consoles reading
    different messages therefore repaint independently.
    """
    console = _console_name(console) if console else _here()
    rev = Agent.SHARED.get_inventory_value(REVISION_KEY, 0) or 0
    if not console:
        return rev * 1000000
    # Per console, so one crew member picking a message does not repaint the other
    # five screens. Read state is already per console; so is the selection.
    seen = len(_read_map().get(console) or ())
    sel = int(message_selected(console) or 0)
    return rev * 1000000 + seen * 1000 + sel


def message_bump():
    """Say that something the inbox draws has changed."""
    Agent.SHARED.set_inventory_value(
        REVISION_KEY, (Agent.SHARED.get_inventory_value(REVISION_KEY, 0) or 0) + 1)


def message_select(mid, console=None):
    """Remember which message this console is reading, so it survives the repaint.

    A rebuild makes a NEW listbox whose selection starts empty; without this the
    reading pane would snap back to the newest message every time anything arrived.
    """
    console = _console_name(console) if console else _here()
    if not console:
        return
    sel = dict(Agent.SHARED.get_inventory_value(SELECT_KEY, {}) or {})
    sel[console] = int(mid or 0)
    Agent.SHARED.set_inventory_value(SELECT_KEY, sel)


def message_selected(console=None):
    """The message id this console is reading, or None."""
    console = _console_name(console) if console else _here()
    if not console:
        return None
    return (Agent.SHARED.get_inventory_value(SELECT_KEY, {}) or {}).get(console) or None


def _all():
    return Agent.SHARED.get_inventory_value(MESSAGES_KEY, [])


def _save(msgs):
    Agent.SHARED.set_inventory_value(MESSAGES_KEY, msgs)


def _console_name(console):
    """Whatever the caller said, as the name a script would use."""
    from .gui.epadd import epadd_console_name
    return epadd_console_name(console)


def _here():
    """The console reading right now.

    `page.console` is set by `gui_console()` at swap time and is NOT what a morphed
    console answers: `gui_console_enter` - the one door, and how the away console is
    entered - writes CONSOLE_TYPE into the client's inventory and never touches
    `page.console`. So an away console reported no console at all, `message_select`
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
    next resolved read.
    """
    page = FrameContext.page
    client_id = getattr(page, "client_id", None) if page is not None else None
    if client_id is None:
        client_id = FrameContext.client_id
    if client_id is not None:
        typed = _client_value(client_id, "CONSOLE_TYPE", None)
        if typed:
            return _remember_console(client_id, _console_name(typed))
    named = _console_name(getattr(page, "console", None)) if page is not None else None
    if named:
        return _remember_console(client_id, named)
    return _last_console(client_id)


#: Where the last resolved console is kept, per client.
LAST_CONSOLE_KEY = "epadd_msg_console"


def _remember_console(client_id, console):
    """Record a console that DID resolve, and hand it back."""
    if console and client_id is not None:
        from .inventory import set_inventory_value
        if _client_value(client_id, LAST_CONSOLE_KEY, None) != console:
            set_inventory_value(client_id, LAST_CONSOLE_KEY, console)
    return console


def _last_console(client_id):
    """The console this client last resolved to, or None if it never has."""
    if client_id is None:
        return None
    return _client_value(client_id, LAST_CONSOLE_KEY, None)


# Audiences that are a QUESTION, not a name. Who is away changes during a mission, so
# these are resolved when the inbox is read rather than when the message is sent - a
# note addressed to the away team must reach whoever is down there when they read it,
# not whoever was down there when it was written.
LIVE_AUDIENCES = ("away", "ship")


def _audience(to):
    """`to` as a set of console names, or None meaning everyone.

    A live token (`away`, `ship`) is kept as-is and answered at read time."""
    if to is None:
        return None
    if not isinstance(to, str):
        to = ",".join(str(t) for t in to)
    to = to.strip()
    if to in ("", "*", "all"):
        return None
    out = set()
    for t in to.split(","):
        t = t.strip()
        if not t:
            continue
        out.add(t.lower() if t.strip().lower() in LIVE_AUDIENCES else _console_name(t))
    return out


def _is_away(console, client_id=None):
    """Whether this reader is on the away team.

    Asked of the CLIENT, because that is what away.py tracks - a console name cannot
    answer it. Falls back to the console name, which `gui_console_enter` sets to
    "away" when it morphs a console into a character.
    """
    if console == "away":
        return True
    try:
        from .away import away_clients
    except Exception:
        return False
    if client_id is None:
        page = FrameContext.page
        client_id = getattr(page, "client_id", None) if page is not None else None
    return client_id is not None and client_id in away_clients()


def _audience_matches(want, console, client_id=None):
    """Does this reader fall inside the message's audience?"""
    if want is None:
        return True
    if console and console in want:
        return True
    if "away" in want and _is_away(console, client_id):
        return True
    if "ship" in want and not _is_away(console, client_id):
        return True
    return _forwarded_here(want, console, client_id)


# --- mail for somebody who is not at their post ---------------------------------------
#
# A mission addresses mail to a CONSOLE - `To: science` - and then the science officer
# beams down. Nobody is at science any more, so the letter is delivered to an empty
# chair: it is in the store, it matches nobody, and no one ever knows it existed. The
# same happens to a party short of people, which is what makes this the messages half
# of forwarding.
#
# A ship forwards. The letter goes to whoever is covering, marked so the reader knows
# it was not addressed to them.

FORWARD_UNSTAFFED = True


def message_forwarding(on=True):
    """Whether mail for an empty post is forwarded to somebody. On by default."""
    global FORWARD_UNSTAFFED
    FORWARD_UNSTAFFED = bool(on)


def _staffed():
    """Console names somebody is actually sitting at, as this frame sees it.

    Read from the `console` ROLE rather than from a client list, because that role
    and `CONSOLE_TYPE` are written as a pair by `gui_console_enter` - the one door -
    and are what every other console-scoped thing in the library already tests. A
    client registry would have been a second answer to the same question, and the one
    that is empty until the engine fills it.
    """
    out = set()
    try:
        from .roles import role
        from .inventory import get_inventory_value
    except Exception:
        return out
    for client_id in role("console") or ():
        typed = get_inventory_value(client_id, "CONSOLE_TYPE", None)
        if typed:
            out.add(_console_name(typed))
    return out


def _cover_console():
    """Who catches mail for an empty post.

    The away team's duty console when anybody is down - the same console `away.py`
    hands a forwarded job to, deliberately, so one person is covering rather than two
    halves of the job landing in different places. Nobody away means nobody is
    missing, and nothing is forwarded.
    """
    try:
        from .away import away_duty_client
    except Exception:
        return None, None
    cid = away_duty_client()
    if cid is None:
        return None, None
    from .inventory import get_inventory_value
    return cid, _console_name(get_inventory_value(cid, "CONSOLE_TYPE", "away") or "away")


def _forwarded_here(want, console, client_id=None):
    """Whether this reader is covering for the post this message was sent to."""
    if not FORWARD_UNSTAFFED or not want:
        return False
    # A live token addresses whoever is there by definition, so it can never be
    # orphaned - and forwarding one would deliver every away broadcast twice.
    posts = {w for w in want if w not in LIVE_AUDIENCES}
    if not posts or posts & _staffed():
        return False
    cover_id, cover_console = _cover_console()
    if cover_id is None:
        return False
    if client_id is None:
        page = FrameContext.page
        client_id = getattr(page, "client_id", None) if page is not None else None
    if client_id is not None:
        return client_id == cover_id
    return bool(console) and console == cover_console


def message_forwarded_from(msg, console=None, client_id=None):
    """The post this message was really addressed to, when the reader is covering.

    None when it is their own mail - so a screen can label a forwarded letter without
    having to work out the addressing a second time.
    """
    want = msg.get("to") if isinstance(msg, dict) else None
    if not want:
        return None
    if console is None:
        console = _here()
    if console and console in want:
        return None
    if not _forwarded_here(want, console, client_id):
        return None
    posts = sorted(w for w in want if w not in LIVE_AUDIENCES)
    return ", ".join(posts) if posts else None


def message_send(text, to="*", sender=None, subject=None, kind="crew",
                 choices=None, scene=None):
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
        dict: the stored message.
    """
    text = "" if text is None else str(text)
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT - 3] + "..."   # ASCII: the engine draws no ellipsis
    msgs = _all()
    msg = {
        "id": _next_id(msgs),
        "text": text,
        "to": _audience(to),
        "from": sender if sender else (_here() or "unknown"),
        "subject": subject,
        "kind": kind,
        "at": _stamp(),
        # A message can ask a question. `seq` is the arbitration token - see
        # message_answer - and is bumped on every answer so a second press landing in
        # the same frame is already stale.
        # Normalised HERE, at the one door, so every caller agrees: labels, pairs
        # and dicts all arrive as dicts and nothing downstream has to ask which.
        "choices": _choices_from(choices),
        "seq": 1,
        "answered": None,
        # An away scene's beat. The message carries the LINE; the replies are asked
        # of away.py at draw time, because they are per character and it already
        # arbitrates them. Two arbitration paths over one scene is a bug waiting.
        "scene": scene,
    }
    msg["choices"] = msg["choices"][:MAX_CHOICES]
    msgs.append(msg)
    if len(msgs) > MAX_KEPT:
        del msgs[:len(msgs) - MAX_KEPT]
    _save(msgs)
    message_bump()
    return msg


def message_mail(text, to="*", sender=None, subject=None):
    """A message from content - a letter from family, a friend, an admiral. Exactly
    `message_send(kind="mail")`, named so a story reads as what it is."""
    return message_send(text, to=to, sender=sender, subject=subject, kind="mail")


def _next_id(msgs):
    return 1 + max((m.get("id", 0) for m in msgs), default=0)


def _stamp():
    """Sim seconds, as a plain number. The inbox formats it; a story never sees it."""
    try:
        return int(FrameContext.sim_seconds or 0)
    except Exception:
        return 0


def message_inbox(console=None):
    """Messages this console can see, newest first."""
    console = _console_name(console) if console else _here()
    out = [m for m in _all() if _audience_matches(m.get("to"), console)]
    out.reverse()
    return out


def message_get(mid):
    for m in _all():
        if m.get("id") == mid:
            return m
    return None


def _read_map():
    return Agent.SHARED.get_inventory_value(READ_KEY, {})


def message_mark_read(mid=None, console=None):
    """Mark one message read for a console, or the whole inbox when `mid` is None."""
    console = _console_name(console) if console else _here()
    if not console:
        return
    seen = _read_map()
    mine = set(seen.get(console) or set())
    if mid is None:
        mine |= {m["id"] for m in message_inbox(console)}
    else:
        mine.add(mid)
    seen[console] = mine
    Agent.SHARED.set_inventory_value(READ_KEY, seen)


def message_is_read(mid, console=None):
    console = _console_name(console) if console else _here()
    if not console:
        return False
    return mid in (_read_map().get(console) or set())


def message_unread(console=None):
    """How many this console has not read. This is what the app badge shows."""
    console = _console_name(console) if console else _here()
    if not console:
        return 0
    seen = _read_map().get(console) or set()
    return sum(1 for m in message_inbox(console) if m["id"] not in seen)


def message_clear():
    """Drop every message and every read mark. For a mission that wants a clean
    inbox mid-game; the mission reset already does this on its own."""
    Agent.SHARED.set_inventory_value(MESSAGES_KEY, [])
    Agent.SHARED.set_inventory_value(READ_KEY, {})
    Agent.SHARED.set_inventory_value(SELECT_KEY, {})
    message_bump()


def messages_count():
    """Reset-ledger probe."""
    try:
        return len(_all())
    except Exception:
        return 0


# --- messages authored as content -------------------------------------------------
#
# A mission writes its mail in an `.amd` file and hands that file to whoever is good at
# writing, who never has to see any of the code above. One heading per message:
#
#     ## [A parcel, eventually](mail_parcel)
#     ---
#     From: Your sister, Mira
#     To: helm
#     After: 240
#     ---
#     The socks are in the post. They have been in the post for eight months.
#
# `Kind:` is deliberately NOT one of the fields - it is a reserved landmark domain
# field in AMD, and using it here would type every record `landmark` and quietly pass
# that down the whole tree.

def _msg_nodes(node):
    for n in (node.get("children") or []):
        yield n
        for c in _msg_nodes(n):
            yield c


def message_load_amd(doc, to=None):
    """Read messages out of a parsed AMD document into the pending pile.

    A heading is a message when its fence has a `From`. The section heading, which
    has none, is skipped - the same rule the recipe loader uses.

    Args:
        doc: a parsed AMD document (`document_get_amd_file`, or `amd_mission_data` +
            `amd_section`).
        to (str, optional): who they are for when a message does not say. Defaults to
            everyone.

    Returns:
        int: how many were loaded.
    """
    if doc is None:
        return 0
    pending = _pending()
    n_loaded = 0
    for n in _msg_nodes(doc):
        data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
        sender = data.get("from")
        if not sender:
            continue
        body, choices = _split_choices(n.get("description") or "")
        pending.append({
            "key": n.get("key") or data.get("key"),
            "text": body,
            "subject": n.get("display_text") or data.get("subject"),
            "from": sender,
            "to": data.get("to") or to or "*",
            "after": _seconds(data.get("after")),
            "choices": choices,
        })
        n_loaded += 1
    _save_pending(pending)
    return n_loaded


PENDING_KEY = "__MESSAGES_PENDING__"


def _pending():
    return Agent.SHARED.get_inventory_value(PENDING_KEY, [])


def _save_pending(items):
    Agent.SHARED.set_inventory_value(PENDING_KEY, items)


def _split_choices(body):
    """A message body -> (prose, choices).

    A `- [label](target) if guard ; outcomes` line is a reply, anything else is the
    message. The grammar is `amd_choice`'s, unchanged - it is what OU dialogue, hails
    and away scenes already use, so a writer who has authored any of those has
    nothing new to learn and `sbs lint` already understands the line.
    """
    from .amd import amd_choice
    prose, choices = [], []
    for line in str(body or "").splitlines():
        ch = amd_choice(line)
        if ch is None:
            prose.append(line)
        else:
            choices.append(ch)
    return "\n".join(prose).strip(), choices[:MAX_CHOICES]


def _seconds(value):
    """`After:` in seconds. Absent means 0 - delivered the moment the pile is drained."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def message_deliver_due(now=None):
    """Send every loaded message whose `After:` has passed, and forget it.

    A mission ticks this (a `do_interval`, or its own loop). Mail that arrives while
    the crew is flying is the point - a pile that all landed at t=0 would be a
    document, not a message.

    Returns:
        int: how many were delivered this call.
    """
    pending = _pending()
    if not pending:
        return 0
    now = _stamp() if now is None else int(now)
    due = [m for m in pending if m["after"] <= now]
    if not due:
        return 0
    for m in due:
        message_send(m["text"], to=m["to"], sender=m["from"], subject=m["subject"],
                     kind="mail", choices=m.get("choices"))
    _save_pending([m for m in pending if m["after"] > now])
    return len(due)


def message_pending_count():
    """Reset-ledger probe for the undelivered pile."""
    try:
        return len(_pending())
    except Exception:
        return 0


# --- a message that asks a question ------------------------------------------------
#
# The architecture is `hail.py`'s, because a hail is already exactly this: something a
# script starts, that waits until a person opens it, and then offers replies. What is
# borrowed, specifically:
#
#   * choices cached ON the message, not recomputed per draw (hail.py:597)
#   * the seq bumped BEFORE outcomes run (hail.py:826), so a second press landing in
#     the same frame is already stale rather than racing
#   * both a signal AND a promise settled on an answer, the way _reply_emitter does
#     for overlays (overlay.py:1389) - a route can react, or a task can await
#
# What is NOT borrowed: a hail belongs to a ship and blocks on being accepted. A
# message sits in an inbox, is addressed per console, and several can be open at once.

REPLY_SIGNAL = "message_reply"


def _guard_agent():
    """Whose state a choice guard is asked about.

    The shared agent, not the reader's ship: a message is addressed to a CONSOLE and
    consoles do not own state - the mission does. A caller that wants a ship's own
    guards passes the message a pre-filtered choice list instead.
    """
    return Agent.SHARED_ID


def message_choices(mid, console=None):
    """The replies this console is offered on this message, guards applied.

    Empty once the message is answered - a decision that has been taken is not still
    on offer, and leaving the buttons up invites a second press that can only be
    refused.
    """
    from .amd_dialogue import dialogue_guard_ok
    msg = message_get(mid)
    if msg is None or msg.get("answered") is not None:
        return []
    console = _console_name(console) if console else _here()
    out = []
    for ch in (msg.get("choices") or []):
        if dialogue_guard_ok(ch.get("guard"), _guard_agent(), msg.get("from")):
            out.append(dict(ch, index=len(out), seq=msg.get("seq", 1)))
    return out


def message_answer(mid, index, console=None, seq=None):
    """Take one of a message's replies.

    Returns the chosen dict, or None when the answer is refused - a stale seq, an
    already-answered message, an index that is not on offer for this console, or an
    outcome handler that says no (an unaffordable cost, say).

    The seq moves BEFORE the outcomes run, so a second console pressing in the same
    frame is refused rather than applying the outcome twice. That is hail.py's
    discipline and the reason is the same: the outcomes are the part that cannot be
    undone.
    """
    from .amd_dialogue import dialogue_apply
    from .signal import signal_emit
    msgs = _all()
    msg = next((m for m in msgs if m.get("id") == mid), None)
    if msg is None or msg.get("answered") is not None:
        return None
    if seq is not None and seq != msg.get("seq", 1):
        return None                      # somebody already answered this one
    console = _console_name(console) if console else _here()
    offered = message_choices(mid, console)
    if not (0 <= int(index) < len(offered)):
        return None
    chosen = offered[int(index)]

    msg["seq"] = msg.get("seq", 1) + 1
    if dialogue_apply(_guard_agent(), msg.get("from"), chosen.get("outcomes")) is False:
        _save(msgs)                      # the token still moved; hail.py:451 does this
        return None
    msg["answered"] = {"label": chosen["label"], "by": console or "unknown",
                       "at": _stamp(),
                       # What was NOT said. A decision reads better beside the
                       # options it was made against.
                       "others": [c["label"] for c in offered
                                  if c["label"] != chosen["label"]]}
    _save(msgs)
    message_bump()

    # The reply goes back into the inbox as a message of its own, which is what makes
    # a thread read as a conversation rather than as a form that was filled in.
    message_send(chosen["label"], to=_reply_to(msg), sender=(console or "unknown"),
                 subject=f"Re: {msg.get('subject') or ''}".strip().rstrip(":"),
                 kind="reply")

    signal_emit(REPLY_SIGNAL, {
        "MESSAGE_ID": mid, "MESSAGE_CHOICE": chosen["label"],
        "MESSAGE_TARGET": chosen.get("target"), "MESSAGE_CONSOLE": console,
        "MESSAGE_FROM": msg.get("from"),
    })
    prom = _PROMISES.pop(mid, None)
    if prom is not None:
        prom.set_result(chosen)
    return chosen


def _reply_to(msg):
    """Who a reply is addressed to: whoever the message was addressed to, so the
    thread stays with the same people. An announcement is replied to in public."""
    to = msg.get("to")
    return "*" if to is None else ",".join(sorted(to))


def message_answer_scene(scene_key, label, by=None, others=None):
    """Record what an away beat was answered with.

    The beat's replies live in away.py, not on the message, so the message cannot
    know on its own that it has been settled - and an answered beat that still showed
    live buttons, or showed nothing at all, is the transcript losing the half that
    matters. Called by `away_answer` once a pick has actually been applied.
    """
    msgs = _all()
    msg = next((m for m in reversed(msgs) if m.get("scene") == scene_key), None)
    if msg is None or msg.get("answered") is not None:
        return None
    msg["answered"] = {"label": label, "by": by or "the away team", "at": _stamp(),
                       "others": list(others or [])}
    _save(msgs)
    message_bump()
    return msg


def message_answered(mid):
    """What was chosen, or None. A console that arrives late reads the decision."""
    msg = message_get(mid)
    return None if msg is None else msg.get("answered")


# Story tasks awaiting a reply, by message id. Not on Agent.SHARED: a promise is a
# live Python object belonging to one task, and nothing about it survives a reload.
_PROMISES = {}


def message_ask(text, to="*", sender=None, subject=None, choices=None, kind="mail"):
    """Send a message and wait for its reply.

        answer = await message_ask("Do we hold?", to="helm",
                                   sender="The Captain", choices=["Hold", "Break off"])

    Resolves with the chosen dict. A message nobody answers keeps the task waiting -
    compose it with a timeout when that matters:
    `promise_any(message_ask(...), delay_sim(60))`.
    """
    from ..futures import Promise
    msg = message_send(text, to=to, sender=sender, subject=subject, kind=kind,
                       choices=choices)
    prom = Promise()
    _PROMISES[msg["id"]] = prom
    return prom


def _choices_from(choices):
    """Labels, `(label, target)` pairs or full dicts -> choice dicts.

    The same shape hail.py accepts (`_hail_choices_from`), so a story that offers a
    hail and a story that sends a message are written the same way.
    """
    out = []
    for ch in (choices or []):
        if isinstance(ch, dict):
            out.append({"label": ch.get("label", ""), "target": ch.get("target"),
                        "guard": ch.get("guard"), "outcomes": ch.get("outcomes") or []})
        elif isinstance(ch, (tuple, list)) and len(ch) >= 2:
            out.append({"label": str(ch[0]), "target": str(ch[1]),
                        "guard": None, "outcomes": []})
        else:
            out.append({"label": str(ch), "target": None,
                        "guard": None, "outcomes": []})
    return out


def message_promise_count():
    """Reset-ledger probe: a task waiting on a reply that a reload will never bring."""
    return len(_PROMISES)
