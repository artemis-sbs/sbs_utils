from ..mast_sbs.story_nodes.media import MediaLabel
from ..fs import load_json_data, get_mission_dir_filename, get_mission_audio_file
from ..mast.mast import DEBUG
from .query import to_id
from random import choice
from sbs_utils.procedural.execution import sub_task_schedule
from ..helpers import FrameContext


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
        FrameContext.context.sbs.set_music_folder(ID, label.true_path())
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
