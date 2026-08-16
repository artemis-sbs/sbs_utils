from sbs_utils.helpers import FrameContext
from sbs_utils.mast_sbs.story_nodes.media import MediaLabel
def DEBUG (msg):
    ...
def _media_schedule (kind, label, ID=0):
    """Apply a media label to the engine and schedule it as a sub-task.
    
    Args:
        kind (str): ``"skybox"`` sets the sky box; ``"music"`` sets the music
            folder.
        label (MediaLabel): The resolved media label.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.
    
    Returns:
        MediaLabel: The label that was scheduled."""
def get_mission_audio_file (file):
    """The path the engine wants for an audio file kept in this mission.
    
    Args:
        file (str): The file, relative to the mission folder, WITHOUT its extension.
    
    Returns:
        str: A Cosmos-root-relative path - see :func:`engine_file`."""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def media_play_audio (file, ids_or_obj=0, volume=1.0, pitch=1.0):
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
        never end the task that was telling the story."""
def media_read_file (basedir, file):
    ...
def media_read_from_zip (zip_file, file, as_utf8=True):
    ...
def media_read_relative_file (file):
    """Read a file sitting beside the .mast that is running - from the addon's zip when
    that .mast came from a mastlib, else from its folder.
    
    EVERY failure is logged and named. It returns None on failure, and a None flows
    straight into `document_get_amd_file(content=None)`, which yields an empty tree that
    renders as a flat, contentless page - a screen that looks broken while saying
    nothing about why. Reported as: a document whose headings "stopped being
    recognized", running a mission that gets this addon from a mastlib."""
def media_schedule (kind, name, ID=0):
    """Schedule a named ``@media`` label of the given kind.
    
    Args:
        kind (str): Media kind, e.g. ``"skybox"`` or ``"music"``.
        name (str | MediaLabel): Media path name or a ``MediaLabel`` object.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.
    
    Returns:
        Label | None: The scheduled label, or ``None`` if not found."""
def media_schedule_random (kind, ID=0):
    """Schedule a randomly chosen ``@media`` label of the given kind.
    
    Args:
        kind (str): Media kind, e.g. ``"skybox"`` or ``"music"``.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0.
    
    Returns:
        Label | None: The scheduled media label, or ``None`` if none exist."""
def music_schedule (name, ID=0):
    """Schedule a specific music track by name.
    
    Args:
        name (str): Music media path name.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0."""
def music_schedule_random (ID=0):
    """Schedule a randomly chosen music ``@media`` label.
    
    Args:
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0."""
def skybox_schedule (name, ID=0):
    """Schedule a specific skybox by name.
    
    Args:
        name (str): Skybox media path name.
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0."""
def skybox_schedule_random (ID=0):
    """Schedule a randomly chosen skybox ``@media`` label.
    
    Args:
        ID (int, optional): Ship or client ID; ``0`` targets the server.
            Defaults to 0."""
def sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """Schedule a sub-task under the current task starting at the given label.
    
    Sub-tasks share lifecycle with the parent task.
    
    Args:
        label (str | Label): The label to start the sub-task at.
        data (dict, optional): Initial sub-task variables. Defaults to None.
        var (str, optional): Variable name to store the created sub-task.
            Defaults to None.
    
    Returns:
        MastAsyncTask: The sub-task created, or None outside a task context."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
