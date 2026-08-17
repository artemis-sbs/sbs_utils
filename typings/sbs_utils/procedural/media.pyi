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
def media_find (kind, spec):
    """Find one ``@media`` label from a loose spec - an index, a path, a display name, or
    an unambiguous substring of either.
    
    Uses the same matcher as ``maps_find`` (``maps.label_find_by_spec``) so a name typed
    into a settings file, a launch argument or a dropdown resolves the one way everywhere.
    An AMBIGUOUS spec returns None rather than guessing.
    
    Args:
        kind (str): ``"skybox"`` or ``"music"``.
        spec: index, path, display name, or substring.
    
    Returns:
        MediaLabel | None"""
def media_get_list (kind):
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
        list: ``MediaLabel`` objects, each with ``.path`` and ``.display_name``."""
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
def music_bank_has (bank, stinger):
    """Whether a bank carries a named one-shot (``"victory"``, ``"failure"``, ...).
    
    A bank is conventionally ``start/main/victory/failure.ogg`` plus ``low/ medium/ high/``,
    but nothing enforces it, so a mod's bank may legitimately omit one. Asking lets a caller
    fall back to ``default`` for that ONE file instead of abandoning the mod's music.
    
    Args:
        bank (str): a bank name, e.g. from :func:`music_current`.
        stinger (str): the file, without ``.ogg``.
    
    Returns:
        bool"""
def music_current (ID=0):
    """The music bank currently playing - the bare folder name last given to the engine.
    
    ``"default"`` until something schedules music, because that is what the engine plays.
    
    Args:
        ID (int, optional): ship or client id; ``0`` (the default) is the server.
    
    Returns:
        str: the bank name."""
def music_find (spec):
    """Find one music ``@media`` label. See :func:`media_find`."""
def music_get_list ():
    """Every usable music ``@media`` label. See :func:`media_get_list`."""
def music_reset ():
    """Forget which bank is playing. Called from ``reset_mission_state``."""
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
def music_schedule_select (spec, ID=0):
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
    track, which is indistinguishable from working."""
def skybox_find (spec):
    """Find one skybox ``@media`` label. See :func:`media_find`."""
def skybox_get_list ():
    """Every usable skybox ``@media`` label. See :func:`media_get_list`."""
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
