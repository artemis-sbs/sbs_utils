from ..fs import load_json_data, get_mission_dir_filename

setting_defaults = None
def settings_get_defaults():
    global setting_defaults
    if setting_defaults is not None:
        return setting_defaults
    
    setting_defaults = {
        "OPERATOR_MODE": {
            "enable": False,
            "logo": "media/operator",
            "show_logo_on_main": True,
            "pin": "000000"
        },
        "AUTO_START": False,
        "WORLD_SELECT": "siege",
        "TERRAIN_SELECT": "some",
        "LETHAL_SELECT": "none",
        "FRIENDLY_SELECT": "few",
        "MONSTER_SELECT": "none",
        "UPGRADE_SELECT": "many",
        "seed_value": 0,
        "GAME_STARTED": False,
        "GAME_ENDED": False,
        "DIFFICULTY": 5,
        "PLAYER_COUNT": 1,
        "GRID_THEME": 0,
        "PLAYER_LIST": [
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
        setting_defaults = setting_defaults | setup_data
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


