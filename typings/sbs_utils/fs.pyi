def add_to_path (dir):
    """Add a directory to the Python module search path.
    
    Inserts the directory at the beginning of sys.path.
    
    Args:
        dir (str): The directory path to add."""
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
    """Get the relative path to an audio file from the mission directory.
    
    Args:
        file (str): The relative file path from the audio directory.
    
    Returns:
        str: The relative path from audio directory to the file."""
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
    """Get the relative path to a graphics file from the mission directory.
    
    Args:
        file (str): The relative file path from the graphics directory.
    
    Returns:
        str: The relative path from graphics directory to the file."""
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
    
    Attempts to load using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
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
    """Set the executable directory to the parent of the script directory.
    
    Used in test environments to override the default exe_dir detection.
    Navigates three directory levels up from the script directory."""
