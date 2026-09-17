def media_roots ():
    """Every root a logical media path may resolve against, nearest first: this mission,
    then each pack it pinned."""
def media_shared (path, pack=None):
    """The physical path for a logical media path, without its extension.
    
    `media_shared("casino")` -> `.../media/casino` or
    `../__lib__/media/<pinned pack>/casino`, whichever exists. Returns a path RELATIVE to
    the mission when it can, because that is what `gui_image_add_atlas` and friends
    expect; an absolute path would still work but reads badly in a stack trace.
    
    `pack` names one declared pack when two of them ship the same folder - rare enough
    that nothing needs it today, and cheap enough to have when something does.
    
    Returns the mission-local path unchanged when nothing matches, so a missing asset
    fails where it always did (at the image load) rather than here."""
def media_shared_exists (path, pack=None):
    """Whether a logical media path resolves to something on disk. For lint and for a
    caller that wants to fall back rather than render nothing."""
def message_clear ():
    """Drop every message and every read mark. For a mission that wants a clean
    inbox mid-game; the mission reset already does this on its own."""
def message_deliver_due (now=None):
    """Send every loaded message whose `After:` has passed, and forget it.
    
    A mission ticks this (a `do_interval`, or its own loop). Mail that arrives while
    the crew is flying is the point - a pile that all landed at t=0 would be a
    document, not a message.
    
    Returns:
        int: how many were delivered this call."""
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
def xess_log (kind, subject, text, by=None, site=None):
    """File one reading, or update the one already filed for this subject.
    
    Args:
        kind (str): what sort of reading - "scan", "shot", whatever a mission files.
        subject (str): what was read. The room's node name, a body, a console.
        text (str): the reading itself.
        by (optional): the CLIENT that took it. Stored as the crew member's name,
            because a client id means nothing to somebody reading the log later.
        site (optional): the interior it was taken on. Defaults to the party's.
    
    Returns:
        dict: the entry, new or updated."""
def xess_log_clear ():
    """Forget the whole log. The mission reset calls this.
    
    Only writes when there is something to forget, so a reset on a mission that never
    boarded anything does not hand `Agent.SHARED` an inventory it did not have. The
    reset ledger reports exactly that as leftover state."""
def xess_log_count (kind=None):
    """How many readings there are. What the tile's badge says."""
def xess_log_entries (kind=None, site=None):
    """Every reading, newest first. Filtered by kind or site when asked."""
def xess_log_get (entry_id):
    ...
def xess_log_last (kind=None):
    """The newest reading, which is what the DEVICE shows. None when there are none."""
def xess_log_revision ():
    ...
