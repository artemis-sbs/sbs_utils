"""The survey log - what a boarding party learned, kept for them.

    THE xESS ACTS. THE ePADD READS.

The device is a column beside a map somebody is watching, so it shows the LAST reading
and a count. The whole record is the ePADD's, which has the screen for it. This module
is the store in between: one entry per thing scanned, written by the act of scanning.

**SCANNING FILES THE ENTRY. THERE IS NO RECORD BUTTON.** The party's record fills in as
they explore and nobody has to remember to keep it. The cost is accepted deliberately -
the log is a record of WHERE THEY WENT rather than of what somebody judged worth
keeping - and it is what makes the pair work: a crew member who never opens the ePADD
still plays the mission, and one who does gets the thing the party has been assembling.

**KEYED BY (site, kind, subject), SO A ROOM VISITED TWICE UPDATES.** A party walking
back through the corridor it entered by would otherwise file the corridor again, and
again, until the log was mostly corridor. The same identity rule the room-entry trigger
already uses, for the same reason.

**THE MODULE IS `survey_log`, THE FUNCTION IS `xess_log`.** A submodule that shares a
name with a function the package exports is SHADOWED by it - `procedural.xess_log`
would be the function, not the module - which is why `hail_gui` is not called
`hail_view`. The comment in `gui/__init__.py` records that one.

Deliberately the same SHAPE as `messages.py` - a list of records with a kind, a sender
and a body, read through a listbox and a detail pane - so the ePADD's Survey app reuses
the inbox's proven layout rather than inventing a second one.
"""
from ..agent import Agent
from .query import to_id

#: On the SHARED agent: one log for the whole party, not one per console. Everybody
#: down there is taking readings for the same expedition.
LOG_KEY = "__XESS_LOG__"

#: What a log entry may cost us. A mission that scans every cell of a big interior
#: should lose its oldest readings rather than its frame rate.
MAX_KEPT = 300
MAX_TEXT = 2000


def _all():
    """Every entry. **READ-ONLY - this must never write.**

    It used to create the list lazily when it was missing, which meant the reset
    ledger's own probe (`xess_log_count`) gave `Agent.SHARED` an inventory by ASKING
    whether it had one. `test_restart_reset` reported `Agent._has_inventory: 1`
    surviving a reset with nothing running - state conjured by measuring it. A reader
    that writes is the one thing an audit cannot see past.
    """
    log = Agent.SHARED.get_inventory_value(LOG_KEY, None)
    return log if isinstance(log, list) else []


def _save(log):
    Agent.SHARED.set_inventory_value(LOG_KEY, log)


def xess_log(kind, subject, text, by=None, site=None):
    """File one reading, or update the one already filed for this subject.

    Args:
        kind (str): what sort of reading - "scan", "shot", whatever a mission files.
        subject (str): what was read. The room's node name, a body, a console.
        text (str): the reading itself.
        by (optional): the CLIENT that took it. Stored as the crew member's name,
            because a client id means nothing to somebody reading the log later.
        site (optional): the interior it was taken on. Defaults to the party's.

    Returns:
        dict: the entry, new or updated.
    """
    kind = str(kind or "scan").strip().lower()
    subject = str(subject or "").strip()
    text = str(text or "")
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT - 3] + "..."      # ASCII: the engine draws no ellipsis
    if site is None:
        site = _site_of(by)
    who = _name_of(by)

    log = list(_all())
    key = (str(site), kind, subject)
    for entry in log:
        if (str(entry.get("site")), entry.get("kind"), entry.get("subject")) == key:
            # UPDATED, NOT APPENDED. A revisit is the same fact, read again.
            entry["text"] = text
            entry["by"] = who or entry.get("by")
            entry["count"] = int(entry.get("count", 1)) + 1
            entry["at"] = _stamp()
            _save(log)
            xess_log_bump()
            return entry

    entry = {
        "id": 1 + max((e.get("id", 0) for e in log), default=0),
        "kind": kind, "subject": subject, "text": text,
        "by": who, "site": site, "count": 1, "at": _stamp(),
    }
    log.append(entry)
    if len(log) > MAX_KEPT:
        del log[:len(log) - MAX_KEPT]
    _save(log)
    xess_log_bump()
    return entry


def xess_log_entries(kind=None, site=None):
    """Every reading, newest first. Filtered by kind or site when asked."""
    out = [e for e in _all()
           if (kind is None or e.get("kind") == str(kind).strip().lower())
           and (site is None or str(e.get("site")) == str(to_id(site) or site))]
    out.reverse()
    return out


def xess_log_last(kind=None):
    """The newest reading, which is what the DEVICE shows. None when there are none."""
    entries = xess_log_entries(kind)
    return entries[0] if entries else None


def xess_log_count(kind=None):
    """How many readings there are. What the tile's badge says."""
    return len(xess_log_entries(kind))


def xess_log_get(entry_id):
    for e in _all():
        if e.get("id") == entry_id:
            return e
    return None


def xess_log_clear():
    """Forget the whole log. The mission reset calls this.

    Only writes when there is something to forget, so a reset on a mission that never
    boarded anything does not hand `Agent.SHARED` an inventory it did not have. The
    reset ledger reports exactly that as leftover state.
    """
    if Agent.SHARED.get_inventory_value(LOG_KEY, None) is None:
        return
    Agent.SHARED.set_inventory_value(LOG_KEY, [])
    xess_log_bump()


#: Bumped on every write, so a screen's `on change` has one number to watch rather
#: than walking the list. The same shape `message_revision` uses.
REVISION_KEY = "__XESS_LOG_REV__"


def xess_log_revision():
    return Agent.SHARED.get_inventory_value(REVISION_KEY, 0) or 0


def xess_log_bump():
    Agent.SHARED.set_inventory_value(REVISION_KEY, xess_log_revision() + 1)


def _stamp():
    from .timers import mission_elapsed_text
    try:
        return mission_elapsed_text()
    except Exception:                                    # noqa: BLE001
        return ""


def _name_of(client_id):
    """The crew member who took the reading, by NAME.

    A client id means nothing to somebody reading this later, and the console that
    took a reading may be holding somebody else by then.
    """
    if client_id is None:
        return None
    try:
        from .boarding import boarding_me
        from .query import to_object
        who = to_object(boarding_me(client_id))
        return getattr(who, "name", None)
    except Exception:                                    # noqa: BLE001
        return None


def _site_of(client_id):
    if client_id is None:
        return 0
    try:
        from .boarding_site import boarding_my_host
        return to_id(boarding_my_host(client_id)) or 0
    except Exception:                                    # noqa: BLE001
        return 0
