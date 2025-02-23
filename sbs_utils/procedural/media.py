from ..mast_sbs.story_nodes.media import MediaLabel
from ..fs import load_json_data, get_mission_dir_filename
from random import choice
from sbs_utils.procedural.execution import sub_task_schedule
from ..helpers import FrameContext


def media_schedule_random(kind, ID=0):
    files = MediaLabel.get_of_type(kind, None)
    media_folders = [file for file in files]
    if len(media_folders) > 0:
        return _media_schedule(kind, choice(media_folders), ID)
    return None

        
def media_schedule(kind, name, ID=0):
    """ Sets the folder from which music is streamed; ID is ship, OR client, OR zero for server.


    Args:
        name (_type_): _description_
        ID (_type_): _description_
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
    """ Sets the folder from which music is streamed; ID is ship, OR client, OR zero for server.
    """
    if kind == "skybox":
        FrameContext.context.sbs.set_sky_box(ID, label.true_path())
        sub_task_schedule(label)
    elif kind == "music":
        FrameContext.context.sbs.set_music_folder(ID, label.true_path())
        sub_task_schedule(label)
    return label

def skybox_schedule_random(ID=0):
    return media_schedule_random("skybox", ID)
def skybox_schedule(name, ID=0):
    return media_schedule("skybox", name, ID)
def music_schedule_random(ID=0):
    return media_schedule_random("music", ID)
def music_schedule(name, ID=0):
    return media_schedule("music", name, ID)




