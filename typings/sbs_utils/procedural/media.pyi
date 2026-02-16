from sbs_utils.helpers import FrameContext
from sbs_utils.mast_sbs.story_nodes.media import MediaLabel
def _media_schedule (kind, label, ID=0):
    """Sets the folder from which music is streamed; ID is ship, OR client, OR zero for server.
    Args:
        kind (str): The kind of media.
        label (str | Label): The label to run.
        ID (int, optional): The ship or client ID, or zero for the server. Default is 0."""
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
def media_read_file (basedir, file):
    ...
def media_read_from_zip (zip_file, file, as_utf8=True):
    ...
def media_read_relative_file (file):
    ...
def media_schedule (kind, name, ID=0):
    """Schedule media of the specified kind (skybox or music)
    
    Args:
        kind (str): The kind of media.
        name (str): The name of the media file.
        ID (int, optional): The ship or client ID, or zero for the server. Default is 0."""
def media_schedule_random (kind, ID=0):
    """Schedule random media of the specified kind (skybox or music)
    Args:
        kind (str): The kind of media.
        ID (int, optional): The ship or client ID, or zero for the server. Default is 0.
    Returns:
        label: The scheduled label or None"""
def music_schedule (name, ID=0):
    """Schedule specific music.
    Args:
        name (str): The name of the skybox file.
        ID (int, optional): The ship or client ID, or zero for the server. Default is 0."""
def music_schedule_random (ID=0):
    """Schedule random music.
    Args:
        ID (int, optional): The ship or client ID, or zero for the server. Default is 0."""
def skybox_schedule (name, ID=0):
    """Schedule a specific skybox.
    Args:
        name (str): The name of the skybox file.
        ID (int, optional): The ship or client ID, or zero for the server. Default is 0."""
def skybox_schedule_random (ID=0):
    """Schedule a random skybox.
    Args:
        ID (int, optional): The ship or client ID, or zero for the server. Default is 0."""
def sub_task_schedule (label, data=None, var=None) -> 'MastAsyncTask':
    """create an new task and start running at the specified label
    
    Args:
        label (str or label): The label to run
        data (duct, optional): Data to initialie task variables. Defaults to None.
        var (str, optional): Set the variable to the task created. Defaults to None.
    
    Returns:
        MastAsyncTask : The MAST task created"""
