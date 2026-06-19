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
def load_yaml_data (file, multi=False):
    """Load and parse a YAML file.
    
    Attempts to load using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        file (str): Path to the YAML file to load.
        multi (bool): return a generator of all documents
    
    Returns:
        dict or generator or None: Parsed YAML data, or None if loading fails."""
def settings_add_defaults (additions):
    """Merge additional keys into the global settings defaults.
    
    ``additions`` acts as a fallback — existing values from ``settings.yaml``
    or ``setup.json`` take precedence, so this only fills gaps.
    
    Args:
        additions (dict): Default key-value pairs to add if not already present."""
def settings_get_defaults ():
    """Return the merged default settings dict, loading ``settings.yaml`` or ``setup.json`` if present.
    
    Results are cached after the first call. Mission-specific values from the
    YAML/JSON file override the built-in defaults.
    
    Returns:
        dict: The default settings mapping."""
