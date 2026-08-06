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
