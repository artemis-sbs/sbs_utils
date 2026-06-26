import random
from ..fs import load_json_data, get_mission_dir_filename, load_yaml_data

setting_defaults = None
def settings_get_defaults():
    """Return the merged default settings dict, loading ``settings.yaml`` or ``setup.json`` if present.

    Results are cached after the first call. Mission-specific values from the
    YAML/JSON file override the built-in defaults.

    Returns:
        dict: The default settings mapping.
    """
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
        "AUTO_START_DELAY": 10,
        "WORLD_SELECT": "siege",
        "TERRAIN_SELECT": "some",
        "LETHAL_SELECT": "none",
        "FRIENDLY_SELECT": "few",
        "MONSTER_SELECT": "none",
        "UPGRADE_SELECT": "max",
        "seed_value": 0,
        "GAME_STARTED": False,
        "GAME_ENDED": False,
        "DIFFICULTY": 5,
        "PLAYER_CREATE_DEFAULT": True,
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
    setup_data = load_yaml_data(get_mission_dir_filename("settings.yaml"))
    if setup_data is None:
        setup_data = load_json_data(get_mission_dir_filename("setup.json"))
    if setup_data is not None:
        setting_defaults = setting_defaults | setup_data
    return setting_defaults


def settings_seed_apply(value=None):
    """Seed the global RNG so a run is reproducible.

    Every random draw in sbs_utils flows through Python's single global
    ``random.Random`` instance -- both module-level ``random.*`` calls and the
    ``from random import ...`` bindings (scatter, vec) resolve to it -- so one
    seed here makes terrain scatter, fleet-race weights, dialogue ``%``
    selection, faces, and names all reproducible.

    Args:
        value (int|None): explicit seed. If ``None`` the ``seed_value`` setting
            is used. A falsy seed (the default ``0`` = "don't care") means pick
            one: a fresh entropy-based seed is generated, applied, and returned,
            so a run can always be reproduced later by passing the value back.

    Returns:
        int: the seed actually applied.
    """
    if value is None:
        value = settings_get_defaults().get("seed_value", 0)
    value = int(value) if value else random.randrange(1, 2**31)
    random.seed(value)
    return value


def settings_add_defaults(additions):
    """Merge additional keys into the global settings defaults.

    ``additions`` acts as a fallback — existing values from ``settings.yaml``
    or ``setup.json`` take precedence, so this only fills gaps.

    Args:
        additions (dict): Default key-value pairs to add if not already present.
    """
    global setting_defaults
    setting_defaults = settings_get_defaults()
    #
    # Note it is in this order because the json file 
    # has the true values, the additions is jst to make
    # sure the setting has a value
    #
    setting_defaults =   additions | setting_defaults
    # NOTE: Should this return the setting_defaults?


