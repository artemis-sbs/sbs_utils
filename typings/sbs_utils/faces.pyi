def arvonian (face_i, eye_i, mouth_i, crown_i, collar_i):
    """Create an arvonian face
    
    Args:
        face_i ( int): The index of the face 0
        eye_id ( int): The index of the eyes 0-4
        mouth_id ( int): The index of the mouth 0-4
        crown_id ( int or None): The index of the crown 0-4 or None
        collar_id ( int or None): The index of the collar 0-4 or None
    
    Returns:
        (str):   A Face string"""
def clear_face (ship_id):
    """Removes a face string for a specified ID
    
    Args:
        ship_id (agent): The id of the ship/object"""
def get_face (ship_id):
    """returns a face string for a specified ID
    
    Args:
        ship_id (agent): The id of the ship/object
    
    Returns:
        str: A Face string"""
def get_face_from_data (race):
    """depricated in v1.1.0
    use random_race instead
    
    Args:
        race (_type_): _description_
    
    Returns:
        _type_: _description_"""
def kralien (face_i, eye_i, mouth_i, scalp_i, extra_i):
    """Create an kralien face
    
    Args:
        face_i ( int): The index of the face 0
        eye_id ( int): The index of the eyes 0-4
        mouth_id ( int): The index of the mouth 0-4
        scalp_id ( int or None): The index of the scalp 0-4 or None
        extra_id ( int or None): The index of the extra 0-4 or None
    
    Returns:
        (str):   A Face string"""
def probably (chance):
    ...
def random_arvonian ():
    """Create a random arvonian face
    
    Returns:
        (str):   A Face string"""
def random_face (race=None):
    """Returns a random face for the specified race
    
    Args:
        race (str): The Race Terran, Torgoth etc.
    
    Returns:
        str: The Face String"""
def random_kralien ():
    """Create a random kralien face
    
    Returns:
        (str):   A Face string"""
def random_skaraan ():
    """Create a random skaraan face
    
    Returns:
        (str):   A Face string"""
def random_terran (face=None, civilian=None):
    """Create a random terran face
    
    Args:
        face ( int or None): The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
        civilian ( boolean or None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def random_terran_female (civilian=None):
    """Create a random terran female face
    
    Args:
        civilian ( boolean or None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def random_terran_fluid (civilian=None):
    """Create a random fluid terran face i.e. may have male or female features
    
    Args:
        civilian ( boolean or None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def random_terran_male (civilian=None):
    """Create a random terran male face
    
    Args:
        civilian ( boolean or None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def random_torgoth ():
    """Create a random torgoth face
    
    Returns:
        (str):   A Face string"""
def random_ximni ():
    """Create a random ximni face
    
    Returns:
        (str):   A Face string"""
def set_face (ship_id, face):
    """sets a face string for a specified ID
    
    Args:
        ship_id (agent): The id of the ship/object
        face (str): A Face string"""
def skaraan (face_i, eye_i, mouth_i, horn_i, hat_i):
    """Create a skaraan face
    
    Args:
        face_i ( int): The index of the face 0
        eye_id ( int): The index of the eyes 0-4
        mouth_id ( int): The index of the mouth 0-4
        horn_id ( int or None): The index of the horn 0-4 or None
        hat_id ( int or None): The index of the hat 0-4 or None
    
    Returns:
        (str):   A Face string"""
def terran (face_i, eye_i, mouth_i, hair_i, longhair_i, facial_i, extra_i, uniform_i, skintone, hairtone):
    """Create an terran face
    
    Args:
        face_i ( int or None ): The index of the face 0=male, 1=female, 2=fluid_male, 3=fluid_female
        eye_i ( int or None): The index of the eyes 0-9
        mouth_i ( int): The index of the mouth 0-9
        hair_i ( int or None): The index of the hair 0-9 or None
        longhair_i ( int or None): The index of the hair 0-7 or None
        facial_i ( int or None): The index of the hair 0-11 or None
        extra_i ( int or None): The index of the extra 0-5 or None
        uniform_i ( int or None): The index of the uniform 0 or None. None = civilian
        skintone_i ( int, str or None): The index of the skintone 0-??, string = color string or None.
        hairtone_i ( int, str or None): The index of the skintone 0-??, string = color string  or None.
    
    Returns:
        (str):   A Face string"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def torgoth (face_i, eye_i, mouth_i, hair_i, extra_i, hat_i):
    """Create a torgoth face
    
    Args:
        face_i ( int): The index of the face 0
        eye_id ( int): The index of the eyes 0-4
        mouth_id ( int): The index of the mouth 0-4
        hair_id ( int or None): The index of the hair 0-4 or None
        extra_id ( int or None): The index of the extra 0-4 or None
        hat_id ( int or None): The index of the hat 0 or None
    
    Returns:
        (str):   A Face string"""
def ximni (face_i, eye_i, mouth_i, horns_i, mask_i, collar_i):
    """Create an ximni face
    
    Args:
        face_i ( int): The index of the face 0
        eye_id ( int): The index of the eyes 0-4
        mouth_id ( int): The index of the mouth 0-4
        horns_id ( int or None): The index of the horns 0-4 or None
        mask_id ( int or None): The index of the mask 0-4 or None
        collar_id ( int or None): The index of the collar 0 or None
    
    Returns:
        (str):   A Face string"""
class Characters(object):
    """A set of predefined faces"""
