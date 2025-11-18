from sbs_utils.helpers import FrameContext
def get_torp_string_value_dict (key: str) -> dict:
    """Get a dictionary of torp string keys for the specified topedo key.
    Args:
        key (str): The key representing the torpedo type.
    Returns:
        dict: Dictionary containing the keys and values for each torpedo value."""
def get_torp_value_string (key: str) -> str:
    """Get the torp value string, provided the key for the torpedo type.
    The torp value string is a css-style string containing values such as the torpode speed, damage, and behavior.
    
    Args:
        key (str): The key of the torpedo type.
    Returns:
        str: The torpedo value string."""
def parse_torp_string (torp_string: str) -> dict:
    """Convert a torpedo value string to a dictionary of key:value.
    Args:
        torp_string (str): The torp string, in a "key1:value1; key2:value2;" format.
    Returns:
        dict: A dictionary."""
def torpedo_type (key: str, gui_text=None, speed: int = 10, lifetime: int = 25, flare_color: str = 'white', trail_color: str = 'white', warhead: str = 'standard', blast_radius: int = 1000, damage: int = 35, explosion_size: int = 10, explosion_color: str = 'fire', behavior: str = 'homing', energy_conversion_value: int = 100, other: str = None):
    """Define a new type of torpedo for use by the players.
    * The torpedo system is still being developed, with new behaviors and warheads in the pipeline.
    * Additional entries may be added in the future to allow further customization. The `other` argument can be filled with these additional entries if they are not yet included in the function.
    
    Args:
        key (str): The key by which the torpodo is identified.
        gui_text (str, optional): The name of the torpedo as seen by the players. If None, then will be the same as the key.
        speed (int, optional): The speed at which the torpedo moves. Default is 10.
        lifetime (int, optional): How long (in seconds) the torpedo continues to move. Default is 25.
        flare_color (str, optional): The color of the torpedo's exhuast flare. Default is white.
        trail_color (str, optional): The color of the torpedo's exhaust trail. Default is white.
        warhead (str, optional): A comma-separated string defining the behavior of the warhead upon contact. Default is standard.
            * standard - the default behavior of damaging a single target upon hit.
            * blast - creates an area of effect with diminishing effects as the distance from the blast epicenter increases.
            * reduce_shields - reduces the shields of the target(s). (EMP)
        blast_radius (int, optional): How large the area of effect should be, if `warhead` has the type "blast". Default is 1000.
        damage (int, optional): The base damage dealt to the target. If `warhead` has the type "blast", damage decreases depending on the distance from the blast's epicenter. Default is 5.
        explosion_size (int, optional): The size of the explosion visual effect on the 3d view. Default is 10.
        explosion_color (str, optional): The color of the explosion visual effect on the 3d view. Default is "fire".
        behaviour (str, optional): The behavior of the torpedo guidance system. Default is homing.
            * homing - the torpedo will home in on its target, compensating for movement.
            * mine - the torpedo will not move after it has been placed and will detonate when a ship gets close.
        energy_conversion_value (int, optional): The amount of energy to provide to the ship by disassembling the torpedo. Default is 100.
        other (str, optional): Additional arguments to add, using the format "key1:value1;key2:value2;""""
def torpedo_type_string (key: str, string: str):
    """Define a torpedo type using the values specified in the string. Values that are not included will use default values.
    E.g. if you use `torpedo_type_string("SomeTorp","gui_text:Type 42;damage:12")`, it will make a homing torpedo called the Type 42 that does 12 damage, and all the other values will be identical to a regular homing torpedo.
    Args:
        key (str): The key by which the torpodo is identified.
        string (str): The torpedo value string containing any non-default values."""
