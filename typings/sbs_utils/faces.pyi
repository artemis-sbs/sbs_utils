def arvonian (face_id, eye_id, mouth_id, crown_id, collar_id):
    """Create an arvonian face
    
    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        crown_id (int | None): The index of the crown 0-4 or None
        collar_id (int | None): The index of the collar 0-4 or None
    
    Returns:
        (str):   A Face string"""
def clear_face (ship_id):
    """Removes a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object"""
def get_face (ship_id):
    """Returns a face string for a specified ID
    
    Args:
        ship_id (Agent | int): The id of the ship/object
    
    Returns:
        str: A Face string"""
def get_face_from_data (race):
    """### Deprecated in v1.1.0.
    Use random_race instead.
    
    Args:
        race (_type_): _description_
    
    Returns:
        _type_: _description_"""
def kralien (face_id, eye_id, mouth_id, scalp_id, extra_id):
    """Create an kralien face.
    
    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        scalp_id (int | None): The index of the scalp 0-4 or None
        extra_id (int | None): The index of the extra 0-4 or None
    
    Returns:
        (str):   A Face string"""
def probably (chance):
    """Will compare a float with a random float between 0 and 1. If the provided number is larger than the random number, will return True.
    Args:
        chance (float): A float between 0 and 1."""
def random_arvonian ():
    """Create a random arvonian face.
    
    Returns:
        (str):   A Face string"""
def random_face (race=None):
    """Returns a random face for the specified race.
    
    Args:
        race (str): The Race Terran, Torgoth etc.
    
    Returns:
        str: The Face String"""
def random_kralien ():
    """Create a random kralien face.
    
    Returns:
        (str):   A Face string"""
def random_skaraan ():
    """Create a random skaraan face.
    
    Returns:
        (str):   A Face string"""
def random_terran (face=None, civilian=None):
    """Create a random terran face.
    
    Args:
        face (int | None): The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
        civilian (boolean | None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def random_terran_female (civilian=None):
    """Create a random terran female face.
    
    Args:
        civilian (boolean, optional): The force this to be a civilian=True, For non-civilian=False or None= random. Default is None.
    
    Returns:
        (str):   A Face string"""
def random_terran_fluid (civilian=None):
    """Create a random fluid terran face i.e. may have male or female features.
    
    Args:
        civilian (boolean, optional): The force this to be a civilian=True, For non-civilian=False or None= random. Default is None.
    
    Returns:
        (str):   A Face string"""
def random_terran_male (civilian=None):
    """Create a random terran male face.
    
    Args:
        civilian (boolean, optional): The force this to be a civilian=True, For non-civilian=False, or None= random. Default is None.
    
    Returns:
        (str):   A Face string"""
def random_torgoth ():
    """Create a random torgoth face.
    
    Returns:
        (str):   A Face string"""
def random_ximni ():
    """Create a random ximni face.
    
    Returns:
        (str):   A Face string"""
def set_face (ship_id, face):
    """Sets a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string"""
def skaraan (face_id, eye_id, mouth_id, horn_id, hat_id):
    """Create a skaraan face
    
    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        horn_id (int | None): The index of the horn 0-4 or None
        hat_id (int | None): The index of the hat 0-4 or None
    
    Returns:
        (str): A Face string"""
def terran (face_id, eye_id, mouth_id, hair_id, longhair_id, facial_id, extra_id, uniform_id, skintone, hairtone):
    """Create a terran face.
    
    Args:
        face_id (int | None): The index of the face 0=male, 1=female, 2=fluid_male, 3=fluid_female
        eye_id (int | None): The index of the eyes 0-9
        mouth_id (int): The index of the mouth 0-9
        hair_id (int | None): The index of the hair 0-9 or None
        longhair_id (int | None): The index of the hair 0-7 or None
        facial_id (int | None): The index of the hair 0-11 or None
        extra_id (int | None): The index of the extra 0-5 or None
        uniform_id (int | None): The index of the uniform 0 or None. None = civilian
        skintone (int | str | None): The index of the skintone 0-??, string = color string or None.
        hairtone (int | str | None): The index of the skintone 0-??, string = color string  or None.
    
    Returns:
        (str):   A Face string"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def torgoth (face_id, eye_id, mouth_id, hair_id, extra_id, hat_id):
    """Create a torgoth face.
    
    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        hair_id (int | None): The index of the hair 0-4 or None
        extra_id (int | None): The index of the extra 0-4 or None
        hat_id (int | None): The index of the hat 0 or None
    
    Returns:
        (str):   A Face string"""
def ximni (face_id, eye_id, mouth_id, horns_id, mask_id, collar_id):
    """Create an ximni face
    
    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        horns_id (int | None): The index of the horns 0-4 or None
        mask_id (int | None): The index of the mask 0-4 or None
        collar_id (int | None): The index of the collar 0 or None
    
    Returns:
        (str):   A Face string"""
class Characters(object):
    """A set of predefined faces"""
