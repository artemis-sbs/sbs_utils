"""One logical path for art, whether it lives in this mission or in a shared pack.

(The module is `media_paths`, not `media_shared`: `procedural/__init__` exports the
FUNCTION `media_shared`, which would shadow a module of the same name for anyone writing
`import sbs_utils.procedural.media_shared as m`.)

Art used to be copied into every mission that declared a media pack - 27 MB again per
mission. `sbs.pyz` now unpacks each pack ONCE beside the libraries, into a folder named
for the zip, so two missions pinning different versions of a pack each get the version
they asked for:

    <mission>/media/casino/terran_deck                            the mission's own art
    __lib__/media/artemis-sbs.LegendaryMissions.media.v1.4.0/casino/terran_deck

The version in the middle is why this function exists: an addon must not hardcode it, or
every pack release would rewrite every addon. Ask for the LOGICAL path and let this find
the physical one:

    CASINO_MEDIA = media_shared("casino")            # -> a path either way
    gui_image_add_atlas("card_back", CASINO_MEDIA + "/terran_back")

WHICH pack wins. The mission's `story.json` `resources` names the packs it pinned; they
are searched in declaration order, mission-local art first. A mission that declares no
packs (or runs from the pack's own repo, like LegendaryMissions itself) resolves against
its own `media/` and never touches `__lib__` - which is why the source layout dropped the
repeated `media/LegendaryMissions/` level: the logical path is now the same in both
places, so no code has to know where it is running from.
"""
import json
import os

from ..fs import get_mission_dir_filename, get_artemis_dir

_LIB_MEDIA = None          # cached: the unpacked roots this mission may use, in order
_MISSION = None            # ...for which mission, so a mission change re-resolves


def _mission_dir():
    return os.path.dirname(get_mission_dir_filename("story.json"))


def _pinned_packs():
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
    the mission folder.
    """
    story = get_mission_dir_filename("story.json")
    try:
        with open(story, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return []
    declared = list((data.get("resources") or {}).values())
    declared += list(data.get("shared_media") or [])
    out = []
    for value in declared:
        for v in (value if isinstance(value, list) else [value]):
            v = str(v).strip()
            if v.lower().endswith(".zip"):
                out.append(v[:-4])          # the unpacked folder is named for the zip
    return out


def media_roots():
    """Every root a logical media path may resolve against, nearest first: this mission,
    then each pack it pinned."""
    global _LIB_MEDIA, _MISSION
    mission = _mission_dir()
    if _LIB_MEDIA is not None and _MISSION == mission:
        return _LIB_MEDIA
    roots = [os.path.join(mission, "media")]
    lib_media = os.path.join(os.path.dirname(mission), "__lib__", "media")
    for pack in _pinned_packs():
        roots.append(os.path.join(lib_media, pack))
    _LIB_MEDIA, _MISSION = roots, mission
    return roots


def media_shared(path, pack=None):
    """The physical path for a logical media path, without its extension.

    `media_shared("casino")` -> `.../media/casino` or
    `../__lib__/media/<pinned pack>/casino`, whichever exists. Returns a path RELATIVE to
    the mission when it can, because that is what `gui_image_add_atlas` and friends
    expect; an absolute path would still work but reads badly in a stack trace.

    `pack` names one declared pack when two of them ship the same folder - rare enough
    that nothing needs it today, and cheap enough to have when something does.

    Returns the mission-local path unchanged when nothing matches, so a missing asset
    fails where it always did (at the image load) rather than here.
    """
    rel = str(path).strip().strip("/").replace("\\", "/")
    mission = _mission_dir()
    for root in media_roots():
        if pack and os.path.basename(root) != pack and root != os.path.join(mission, "media"):
            continue
        full = os.path.join(root, *rel.split("/"))
        # Art is addressed WITHOUT its extension (the engine appends .png), so probe for
        # the file and for the folder - a caller may ask for either.
        if os.path.exists(full) or os.path.exists(full + ".png") or os.path.isdir(full):
            try:
                return os.path.relpath(full, mission).replace("\\", "/")
            except ValueError:          # different drive - absolute is still valid
                return full
    return "media/" + rel


def media_shared_exists(path, pack=None):
    """Whether a logical media path resolves to something on disk. For lint and for a
    caller that wants to fall back rather than render nothing."""
    resolved = media_shared(path, pack)
    full = os.path.join(_mission_dir(), *resolved.split("/"))
    return os.path.exists(full) or os.path.exists(full + ".png") or os.path.isdir(full)
