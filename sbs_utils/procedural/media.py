from ..mast_sbs.story_nodes.media import MediaLabel
from ..fs import load_json_data, get_mission_dir_filename, get_mission_audio_file
from ..mast.mast import DEBUG
from .query import to_id
from random import choice
from sbs_utils.procedural.execution import sub_task_schedule
from ..helpers import FrameContext


# The bank name last handed to `set_music_folder`, per target ID. Per-mission state, so
# it is on the reset ledger in handlerhooks - without that, run 2 of a soak reports run 1's
# bank and the end-of-game sting reaches for a folder this mission never selected.
_music_current = {}
# Kinds already reported as having nothing usable, so the warning below fires once rather
# than on every per-client re-schedule. Cleared with the rest of the per-mission state.
_warned_empty = set()


def media_get_list(kind):
    """Every usable ``@media`` label of a kind, for a picker or a report.

    "Usable" is the point: labels whose art or audio folder is missing are dropped, and so
    are labels whose ``if`` condition is false - the same test the random pick applies, so a
    dropdown can never offer something scheduling would refuse. Sorted by declaration order
    so a list is stable between runs.

    This is the function every mod has been hand-rolling. ``a28_skyboxes.py``,
    ``venus_skies.py`` and ``a28_verify.py`` each reach into ``MediaLabel.folders`` directly
    and re-implement the filtering, which is how one of them can quietly disagree with what
    the game will actually pick.

    Args:
        kind (str): ``"skybox"`` or ``"music"``.

    Returns:
        list: ``MediaLabel`` objects, each with ``.path`` and ``.display_name``.
    """
    labels = MediaLabel.get_of_type(kind)
    return sorted(labels, key=lambda m: getattr(m, "label_weight", 0))


def skybox_get_list():
    """Every usable skybox ``@media`` label. See :func:`media_get_list`."""
    return media_get_list("skybox")


def music_get_list():
    """Every usable music ``@media`` label. See :func:`media_get_list`."""
    return media_get_list("music")


def media_find(kind, spec):
    """Find one ``@media`` label from a loose spec - an index, a path, a display name, or
    an unambiguous substring of either.

    Uses the same matcher as ``maps_find`` (``maps.label_find_by_spec``) so a name typed
    into a settings file, a launch argument or a dropdown resolves the one way everywhere.
    An AMBIGUOUS spec returns None rather than guessing.

    Args:
        kind (str): ``"skybox"`` or ``"music"``.
        spec: index, path, display name, or substring.

    Returns:
        MediaLabel | None
    """
    from .maps import label_find_by_spec
    return label_find_by_spec(media_get_list(kind), spec)


def skybox_find(spec):
    """Find one skybox ``@media`` label. See :func:`media_find`."""
    return media_find("skybox", spec)


def music_find(spec):
    """Find one music ``@media`` label. See :func:`media_find`."""
    return media_find("music", spec)


def media_schedule_random(kind, ID=0):
    """Schedule a randomly chosen ``@media`` label of the given kind.

    Args:
        kind (str): Media kind, e.g. ``"skybox"`` or ``"music"``.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.

    Returns:
        Label | None: The scheduled media label, or ``None`` if none exist.
    """
    files = MediaLabel.get_of_type(kind, None)
    media_folders = [file for file in files]
    if len(media_folders) > 0:
        return _media_schedule(kind, choice(media_folders), ID)
    # Say so. "No usable labels of this kind" produces a game with no music (or the
    # engine's fallback sky) and NOTHING in the log, which is indistinguishable from
    # working - and it is exactly what a profile that excludes the add-on owning the
    # labels produces. Reported once per kind so a per-client re-schedule is not noise.
    if kind not in _warned_empty:
        _warned_empty.add(kind)
        try:
            from .execution import log
            declared = len(MediaLabel.folders.get(str(kind).lower(), []))
            if declared:
                log(f"no usable @media/{kind} labels: {declared} declared, none resolved "
                    f"(missing files, or an `if` that is false)", "media", "warning")
            else:
                log(f"no @media/{kind} labels are loaded at all - nothing will be set. "
                    f"Is the add-on that declares them in story.json, or excluded by a "
                    f"profile?", "media", "warning")
        except Exception:
            pass
    return None

        
def media_schedule(kind, name, ID=0):
    """Schedule a named ``@media`` label of the given kind.

    Args:
        kind (str): Media kind, e.g. ``"skybox"`` or ``"music"``.
        name (str | MediaLabel): Media path name or a ``MediaLabel`` object.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.

    Returns:
        Label | None: The scheduled label, or ``None`` if not found.
    """
    try:
        if isinstance(name, MediaLabel):
            return _media_schedule(kind, name, ID)

        files = MediaLabel.get_of_type(kind, None)
        for f in files:
            if f.path == name.lower():
                return _media_schedule(kind, f, ID)
        print(f"media {name} is not valid")
    except:
        raise Exception(f"Media {name} is not valid")

def _media_schedule(kind, label, ID=0):
    """Apply a media label to the engine and schedule it as a sub-task.

    Args:
        kind (str): ``"skybox"`` sets the sky box; ``"music"`` sets the music
            folder.
        label (MediaLabel): The resolved media label.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.

    Returns:
        MediaLabel: The label that was scheduled.
    """
    if kind == "skybox":
        FrameContext.context.sbs.set_sky_box(ID, label.true_path())
        sub_task_schedule(label)
    elif kind == "music":
        bank = label.true_path()
        FrameContext.context.sbs.set_music_folder(ID, bank)
        _music_current[to_id(ID) or 0] = bank
        sub_task_schedule(label)
    return label

def skybox_schedule_random(ID=0):
    """Schedule a randomly chosen skybox ``@media`` label.

    Args:
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.
    """
    return media_schedule_random("skybox", ID)

def skybox_schedule(name, ID=0):
    """Schedule a specific skybox by name.

    Args:
        name (str): Skybox media path name.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.
    """
    return media_schedule("skybox", name, ID)

def music_schedule_random(ID=0):
    """Schedule a randomly chosen music ``@media`` label.

    Args:
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.
    """
    return media_schedule_random("music", ID)

def music_schedule(name, ID=0):
    """Schedule a specific music track by name.

    Args:
        name (str): Music media path name.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.
    """
    return media_schedule("music", name, ID)


def music_schedule_select(spec, ID=0):
    """Schedule the music a setting, a map or an operator ASKED for.

    This is what replaced "the skybox label picks the music". Every skybox label used to
    end in ``if client_id==0: music_schedule_random()`` - copied into thirty A28 labels,
    eight LM ones and every mission that inlined them - because scheduling a skybox ran its
    body and nothing else ever chose a track. A skybox now sets the sky and nothing else.

    Args:
        spec: ``""``, ``None`` or ``"random"`` picks at random; anything else is resolved
            by :func:`music_find`.
        ID (int, optional): ship or client id; ``0`` (the default) targets the server.

    Returns:
        MediaLabel | None: what was scheduled, or None when there is no music at all.

    A spec that matches nothing WARNS BY NAME and falls back to random. Silence there was
    the tempting choice and the wrong one: ``MUSIC_SELECT: Artmeis2`` would play a random
    track, which is indistinguishable from working.
    """
    want = "" if spec is None else str(spec).strip()
    if not want or want.lower() == "random":
        return music_schedule_random(ID)
    label = music_find(want)
    if label is None:
        from .execution import log
        known = ", ".join(m.path for m in music_get_list()) or "none are loaded"
        log(f"MUSIC_SELECT '{want}' matched no @media/music label - playing a random one. "
            f"Available: {known}", "media", "warning")
        return music_schedule_random(ID)
    return _media_schedule("music", label, ID)


def music_current(ID=0):
    """The music bank currently playing - the bare folder name last given to the engine.

    ``"default"`` until something schedules music, because that is what the engine plays.

    Args:
        ID (int, optional): ship or client id; ``0`` (the default) is the server.

    Returns:
        str: the bank name.
    """
    return _music_current.get(to_id(ID) or 0, "default")


def music_bank_has(bank, stinger):
    """Whether a bank carries a named one-shot (``"victory"``, ``"failure"``, ...).

    A bank is conventionally ``start/main/victory/failure.ogg`` plus ``low/ medium/ high/``,
    but nothing enforces it, so a mod's bank may legitimately omit one. Asking lets a caller
    fall back to ``default`` for that ONE file instead of abandoning the mod's music.

    Args:
        bank (str): a bank name, e.g. from :func:`music_current`.
        stinger (str): the file, without ``.ogg``.

    Returns:
        bool
    """
    label = music_find(bank)
    if label is not None:
        return label.bank_has(stinger)
    # Not declared as a label - still answer for the stock banks, which are on disk
    # whether or not any @media/music label names them.
    import os
    from ..fs import get_artemis_audio_dir
    return os.path.isfile(os.path.join(get_artemis_audio_dir(), "music", str(bank),
                                       str(stinger) + ".ogg"))


def music_reset():
    """Forget which bank is playing, and re-arm the empty-media warning. Called from
    ``reset_mission_state`` - run 2 has its own labels and deserves its own warning."""
    _music_current.clear()
    _warned_empty.clear()


def media_read_relative_file(file):
    """Read a file sitting beside the .mast that is running - from the addon's zip when
    that .mast came from a mastlib, else from its folder.

    EVERY failure is logged and named. It returns None on failure, and a None flows
    straight into `document_get_amd_file(content=None)`, which yields an empty tree that
    renders as a flat, contentless page - a screen that looks broken while saying
    nothing about why. Reported as: a document whose headings "stopped being
    recognized", running a mission that gets this addon from a mastlib.
    """
    def _log(why):
        try:
            from .execution import log
            log(f"media_read_relative_file({file!r}): {why}", "media", "warning")
        except Exception:
            pass

    task = FrameContext.task
    source_map = task.get_active_node_source_map() if task is not None else None
    if source_map is None:
        _log("no source map for the running label, so there is nothing to be relative "
             "TO - the file was not read")
        return None
    try:
        if source_map.is_lib:
            return media_read_from_zip(source_map.basedir, file)
        return media_read_file(source_map.basedir, file)
    except Exception as e:
        where = "mastlib" if source_map.is_lib else "folder"
        _log(f"not found in the {where} {source_map.basedir!r} ({e})")
        return None

import os
import zipfile

def media_read_from_zip(zip_file, file, as_utf8=True):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        with zip_ref.open(file) as file:
            content = file.read()
            if as_utf8:
                content = content.decode('utf-8')
                #content = content.replace("\r", "")
            return content

def media_read_file(basedir, file):
    # Same decode as media_read_from_zip above, so a mission read from a folder
    # and the same mission read from a mastlib produce the same string.
    from sbs_utils.procedural.amd import amd_read_text
    return amd_read_text(os.path.join(basedir, file))


def media_play_audio(file, ids_or_obj=0, volume=1.0, pitch=1.0):
    """Play an audio file NOW - a stinger, a voice line, an alarm.

    Promoted out of HereThereBeMonsters, which called `sbs.play_audio_file` raw in
    seven places behind its own enable flag. The engine call needs a path relative to
    the Artemis audio directory, which is what `get_mission_audio_file` builds - a
    mission should name its file the way it stores it (`audio/briefing_01`) and never
    have to know that.

    Args:
        file (str): the file, relative to the mission folder.
        ids_or_obj (int, optional): a client id, or 0 (the default) for everyone.
        volume (float, optional): 0-1.
        pitch (float, optional): 1.0 is unshifted.

    Returns:
        bool: whether the engine was asked to play it. Silent - not an exception - when
        there is no engine or the mission disabled audio, because a missing sound must
        never end the task that was telling the story.
    """
    if not file:
        return False
    ctx = FrameContext.context
    if ctx is None:
        return False
    try:
        from .execution import get_shared_variable
        if get_shared_variable("MEDIA_AUDIO_ENABLED", True) is False:
            return False
    except Exception:
        pass
    try:
        ctx.sbs.play_audio_file(to_id(ids_or_obj) or 0, get_mission_audio_file(file),
                                float(volume), float(pitch))
        return True
    except Exception as e:
        DEBUG(f"[media] audio {file!r} did not play: {e}")
        return False
