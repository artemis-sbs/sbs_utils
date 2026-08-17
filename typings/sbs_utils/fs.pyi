def _ryaml_rejected (what, err):
    """ryaml is PRESENT and refused this content - a different fact entirely.
    
    Worth saying once, with the name of the offending file: the fallback keeps
    the mission running, so nothing else will ever mention that this file is
    being parsed the slow way, or that it may be malformed."""
def add_to_path (dir):
    """Add a directory to the Python module search path.
    
    Inserts the directory at the beginning of sys.path.
    
    Args:
        dir (str): The directory path to add."""
def engine_file (path):
    """A path in the shape the ENGINE resolves: relative to the Cosmos root.
    
    THE ONE PATH HELPER. Every asset class used to compute its own shape against its own
    base - audio against `data/audio`, images against `data/graphics`, a skybox as an
    absolute path for a mission asset but a bare name for a stock one, ship data already
    root-relative. Five spellings of the same idea, and only a run of the game could say
    which of them a given engine would open.
    
    The 2026-08-15 engine resolves ONE shape for all of them, measured against it
    (`data/missions/mediapath_probe`): a path from the Cosmos root, or an absolute path.
    Both open. What does NOT open is a bare name, or a path relative to the asset's own
    old base - `../missions/<m>/<file>` against `data/audio` is what this library built
    for audio until now, and on this engine it silently plays nothing.
    
    NOTE ON EXTENSIONS, because it is the opposite of what the shape suggests: the engine
    appends the extension itself, and passing one can make the lookup FAIL. A `.wav` on an
    audio path was measured not to open while the same path without it did. So callers
    name assets the way they always have - without a suffix - and this does not add one.
    
    An absolute path outside the install is passed through unchanged: it is still a path
    the engine accepts, and rewriting it to `../../..` would only make it fragile."""
def expand_zip (zip_filepath, extract_to_path, overwrite=False):
    """Extract the contents of a zip file to a specified directory.
    
    Creates the target directory if it does not exist. Handles zip extraction
    errors gracefully with informative error messages.
    
    Args:
        zip_filepath (str): The path to the zip file to extract.
        extract_to_path (str): The directory where contents will be extracted.
            Created automatically if it does not exist.
        overwrite (bool): If True, overwrite existing files. Defaults to False."""
def file_get_stats (filename):
    ...
def file_get_time (filename):
    ...
def get_artemis_audio_dir ():
    """Get the path to the Artemis Cosmos audio directory.
    
    Returns:
        str: The audio folder path (data directory + "\audio")."""
def get_artemis_data_dir ():
    """Get the path to the Artemis Cosmos data directory.
    
    Returns:
        str: The data folder path (executable directory + "/data")."""
def get_artemis_data_dir_filename (filename):
    """Get the full path to a file in the data directory.
    
    Args:
        filename (str): The relative path from the data directory.
    
    Returns:
        str: The full path to the file in the data directory."""
def get_artemis_dir ():
    """Get the path to the root Artemis Cosmos installation directory.
    
    Returns:
        str: The parent directory of the data folder."""
def get_artemis_graphics_dir ():
    """Get the path to the Artemis Cosmos graphics directory.
    
    Returns:
        str: The graphics folder path (data directory + "\graphics")."""
def get_mission_audio_file (file):
    """The path the engine wants for an audio file kept in this mission.
    
    Args:
        file (str): The file, relative to the mission folder, WITHOUT its extension.
    
    Returns:
        str: A Cosmos-root-relative path - see :func:`engine_file`."""
def get_mission_dir ():
    """Get the directory of the current mission.
    
    Returns:
        str: The script directory path."""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
def get_mission_graphics_file (file):
    """The path the engine wants for a graphics file kept in this mission.
    
    Now the same shape as everything else - see :func:`engine_file`. It was safe to move
    only once two things were measured on engine 1.3.6: that images open from an
    exe-relative path (the `image_probe` mission, judged by eye - an image is loaded when
    it is DRAWN, so an access-time probe on the server screen answers nothing), and that
    `ImageAtlas` no longer routes through this function, so changing it cannot disturb
    the fallback chain that finds the art in the first place.
    
    Args:
        file (str): The file, relative to the mission folder, WITHOUT its extension.
    
    Returns:
        str: A Cosmos-root-relative path."""
def get_mission_name ():
    """Get the name of the current mission.
    
    Returns the name derived from the script directory basename.
    Cached after first call.
    
    Returns:
        str: The mission folder name."""
def get_missions_dir ():
    """Get the path to the missions directory.
    
    Returns:
        str: Path to the artemis data missions folder."""
def get_mod_dir (mod):
    """Get the directory path for a mission module.
    
    Args:
        mod (str): The module/mission name.
    
    Returns:
        str: The full directory path for the module."""
def get_mod_file (mod, file):
    """Get the full path to a file within a mission module.
    
    Args:
        mod (str): The module/mission name.
        file (str): The relative file path within the module.
    
    Returns:
        str: The full path to the file."""
def get_script_dir ():
    """Get the directory where the main script is located.
    
    Returns the cached script directory from sys.modules['script'] or sys.path[0].
    Paths are normalized to use backslashes on Windows.
    
    Returns:
        str: The absolute path to the script directory."""
def get_startup_mission_name ():
    """Get the default mission name from preferences.
    
    Returns:
        str: The default mission folder name from game preferences."""
def is_dev_build ():
    """Check if the current mission is a development build.
    
    Returns True if a .git directory exists in the mission folder.
    
    Returns:
        bool: True if running in development mode, False otherwise."""
def load_data (file):
    """Load a data file as YAML or JSON, dispatching on the extension.
    
    ``.yaml``/``.yml`` are parsed as YAML; ``.json`` as JSON (comment- and
    trailing-comma-tolerant). When ``file`` has no recognised extension it is
    treated as a BASE path and the ``.yaml``, ``.yml`` then ``.json`` siblings are
    tried in turn -- so a caller can pass ``"shipData"`` (no extension) and get
    whichever form is present, YAML preferred.
    
    Args:
        file (str): Path to the data file, with or without a
            ``.yaml``/``.yml``/``.json`` extension.
    
    Returns:
        dict | list | None: The parsed data, or ``None`` if nothing loaded."""
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def load_json_string (contents):
    """Parse a JSON string with comment and trailing comma support.
    
    First attempts YAML parsing (which handles more formats), then falls back
    to JSON parsing. Supports comments (# and //) and trailing commas.
    
    Args:
        contents (str): JSON content as a string.
    
    Returns:
        dict or None: Parsed data, or None if parsing fails."""
def load_yaml_data (file, multi=False):
    """Load and parse a YAML file.
    
    Uses the fast ryaml parser when the engine provides it, and the bundled
    pure-Python yaml otherwise (or when ryaml refuses the file).
    
    Args:
        file (str): Path to the YAML file to load.
        multi (bool): return a generator of all documents
    
    Returns:
        dict or generator or None: Parsed YAML data, or None if loading fails."""
def load_yaml_string (s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails."""
def ryaml_module ():
    """The fast YAML parser, or None where it is not installed.
    
    Absent is NORMAL and silent: the mock and any host-side tooling run on a
    plain Python that has no PyAddons on its path, and they must not be noisy
    about a thing they were never going to have."""
def save_json_data (file, data):
    """Save data to a JSON file with human-readable formatting.
    
    Applies regex transformations to make the JSON output more readable with
    logical line breaks and consistent spacing.
    
    Args:
        file (str): Path to the output JSON file.
        data (dict): The data structure to serialize."""
def save_yaml_data (file, data):
    """Save an object as a YAML file.
    
    Attempts to dump using ryaml first for better comment handling,
    falls back to standard yaml.safe_dump if ryaml is unavailable.
    
    Args:
        file (str): Path to the YAML file to load.
        data (dict): Dict or object to save"""
def set_dev_build (v):
    ...
def test_set_exe_dir ():
    """Set path globals using this file's known location.
    
    Used in test environments to override the default path detection.
    fs.py lives at <game_root>/data/missions/sbs_utils/sbs_utils/fs.py,
    so all paths are derived from __file__ and are reliable regardless
    of CWD, sys.path[0], or how tests are invoked (discover vs explicit
    vs IDE runner).
    
    Sets:
      exe_dir    — game root (<game_root>)
      script_dir — project root (<game_root>/data/missions/sbs_utils),
                   used by get_mission_dir() to resolve relative MAST
                   import/file paths in tests"""
