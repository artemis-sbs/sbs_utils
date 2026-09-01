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


MESSAGES_KEY = "__MESSAGES__"
READ_KEY = "__MESSAGES_READ__"

# Long enough for a note, short enough that the inbox stays a list of messages rather
# than a document viewer. Text past this is cut with an ellipsis at send time, where
# the sender can still see what happened.
MAX_TEXT = 600
# Oldest are dropped past this. A party runs for hours and nothing prunes otherwise.
MAX_KEPT = 200


def _all():
    return Agent.SHARED.get_inventory_value(MESSAGES_KEY, [])


def _save(msgs):
    Agent.SHARED.set_inventory_value(MESSAGES_KEY, msgs)


def _console_name(console):
    """Whatever the caller said, as the name a script would use."""
    from .gui.epadd import epadd_console_name
    return epadd_console_name(console)


def _here():
    """The console reading right now, off the page."""
    page = FrameContext.page
    return _console_name(getattr(page, "console", None) if page is not None else None)


def _audience(to):
    """`to` as a set of console names, or None meaning everyone."""
    if to is None:
        return None
    if not isinstance(to, str):
        to = ",".join(str(t) for t in to)
    to = to.strip()
    if to in ("", "*", "all"):
        return None
    return {_console_name(t) for t in to.split(",") if t.strip()}


def message_send(text, to="*", sender=None, subject=None, kind="crew"):
    """Put a message in an inbox.

    Args:
        text (str): the body. Trimmed to MAX_TEXT.
        to (str, optional): console name, comma list, or "*" for everyone.
        sender (str, optional): who it is from. A crew message defaults to the console
            that sent it; a story message should always say.
        subject (str, optional): a short line for the list.
        kind (str, optional): "crew" or "mail" - what a story sends. The inbox shows
            them differently; nothing else depends on it.

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
    }
    msgs.append(msg)
    if len(msgs) > MAX_KEPT:
        del msgs[:len(msgs) - MAX_KEPT]
    _save(msgs)
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
    out = [m for m in _all()
           if m.get("to") is None or (console and console in m["to"])]
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
        body = (n.get("description") or "").strip()
        pending.append({
            "key": n.get("key") or data.get("key"),
            "text": body,
            "subject": n.get("display_text") or data.get("subject"),
            "from": sender,
            "to": data.get("to") or to or "*",
            "after": _seconds(data.get("after")),
        })
        n_loaded += 1
    _save_pending(pending)
    return n_loaded


PENDING_KEY = "__MESSAGES_PENDING__"


def _pending():
    return Agent.SHARED.get_inventory_value(PENDING_KEY, [])


def _save_pending(items):
    Agent.SHARED.set_inventory_value(PENDING_KEY, items)


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
        message_mail(m["text"], to=m["to"], sender=m["from"], subject=m["subject"])
    _save_pending([m for m in pending if m["after"] > now])
    return len(due)


def message_pending_count():
    """Reset-ledger probe for the undelivered pile."""
    try:
        return len(_pending())
    except Exception:
        return 0
