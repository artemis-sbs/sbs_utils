def _mission_dir ():
    ...
def _pinned_packs ():
    """The pack zips this mission declared, in `story.json` order. A mission that
    declares none simply has none - that is not an error, it just means its art is its
    own.
    
    TWO WAYS TO DECLARE ONE, and the difference is who holds the copy:
    
        "resources":    {"media": "...zip"}     the ENGINE unpacks it into this mission
        "shared_media": ["...zip"]              nobody does; it is read from __lib__
    
    `resources` is the engine's key: it copies the pack into `<mission>/media/` at load,
    which is where the per-mission duplicates come from. A mission that only needs
    GRAPHICS out of a pack (resolved here, through the image atlas) can declare it under
    `shared_media` instead and read the one shared copy. A mission that needs
    engine-resolved media from the pack - a `@media/skybox/...` label, music, audio -
    still needs `resources`, because the engine resolves those itself and only looks in
    the mission folder."""
def get_artemis_dir ():
    """Get the path to the root Artemis Cosmos installation directory.
    
    Returns:
        str: The parent directory of the data folder."""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
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
