from sbs_utils.mast.maststory import MediaLabel
from sbs_utils.fs import load_json_data, get_mission_dir_filename
from random import choice
from sbs_utils.procedural.execution import sub_task_schedule
import sbs


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
        sbs.set_sky_box(ID, label.true_path())
        sub_task_schedule(label)
    elif kind == "music":
        sbs.set_music_folder(ID, label.true_path())
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


setting_defaults = None
def settings_get_defaults():
    global setting_defaults
    if setting_defaults is not None:
        return setting_defaults
    
    defaults = {
        "operator_mode": {
            "enable": False,
            "logo": "media/operator",
            "show_logo_on_main": True,
            "pin": "000000"
        },
        "auto_start": False,
        "world_select": "siege",
        "terrain_select": "some",
        "lethal_select": "none",
        "friendly_select": "few",
        "monster_select": "none",
        "upgrade_select": "many",
        "seed_value": 0,
        "game_started": False,
        "game_ended": False,
        "difficulty": 5,
        "player_count": 1,
        "grid_theme": 0,
        "player_list": [
            {
                "name": "Artemis",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Intrepid",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Aegis",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Horatio",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Excalibur",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Hera",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Ceres",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Diana",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
        ],
    }
    setup_data = load_json_data(get_mission_dir_filename("setup.json"))
    if setup_data is not None:
        setting_defaults = defaults | setup_data
    return setting_defaults


def settings_add_defaults(additions):
    global setting_defaults
    setting_defaults = settings_get_defaults()
    #
    # Note it is in this order because the json file 
    # has the true values, the additions is jst to make
    # sure the setting has a value
    #
    setting_defaults =   additions | setting_defaults


