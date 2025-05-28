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


def media_read_relative_file(file):
    task = FrameContext.task
    source_map = task.get_active_node_source_map()
    if source_map is None:
        return 
    print(f"TEST FILE RELATIVE {source_map.file_name} {source_map.basedir}" )
    if source_map.is_lib:
        return media_read_from_zip(source_map.basedir, file)
    return media_read_file(source_map.basedir, file)

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
    with open(os.path.join(basedir, file), 'r') as file:
        content = file.read()
        return content
    return None
    


    
    

