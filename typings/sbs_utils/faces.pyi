def _parse_face_generic (race, feats, layers):
    ...
def _parse_face_layers (face_string):
    ...
def _parse_face_terran (feats, layers):
    ...
def _tone_index (color, tones):
    ...
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
def build_face (race, values, enables=None):
    """Build a face string from per-feature indices in FACE_FEATURES order.
    
    `values[i]` is the chosen index for feature i; `enables[i]` False sets an
    (optional) feature to None. Terran maps 1:1 to terran(); other races prepend
    face_id 0 (the slot their builders expect). Returns '' for an unknown race."""
def clear_face (ship_id):
    """Removes a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object"""
def face_gender_index (gender):
    """A gender word as the terran builder's face index, or None for "any".
    
    0 male, 1 female, 2 fluid - the numbering :func:`terran` documents. Unknown words
    answer None rather than guessing, so a mod's own vocabulary degrades to a random face
    instead of to the wrong one."""
def face_mod_reset ():
    """Drop every mod registration. Called by reset_mission_state()."""
def face_mod_size ():
    """Reset-ledger probe: how much mod registration is currently held."""
def face_overlay (face_string, *overlays):
    """Stack overlay layers onto an existing face string.
    
    This is the whole point of keeping implants as separate cells: any face can be
    assimilated at runtime, including one that was never drawn with implants. Layers
    composite lowest-first, so overlays go last.
    
        face_overlay(random_face("terran"), "tng6 #fff 2 1", "tng6 #fff 5 3")
    
    Empty/None overlays are skipped so a caller can pass an optional one straight in."""
def face_race_mapped (race):
    """Re-point a race name at the face race its portraits should come from. ART ONLY.
    
    The third of the mod re-skin maps (`RACE_ART` and `ART_KEYS` are the other two, in
    procedural/ship_data.py). Returns `race` unchanged unless a mission or profile set
    ``RACE_FACES``, so stock behavior is untouched.
    
    WHY FACES NEED THEIR OWN MAP AND CANNOT REUSE `RACE_ART`: face races are SPECIES,
    ship-data sides are FACTIONS, and they do not spell the same. A mod's Federation ships
    are crewed by `human`, not by `federation`; a faction can field hulls and register no
    portraits at all (Cosmos-TNG-Mod has Breen ships and no Breen faces). Feeding a faction
    name to random_face() therefore matches nothing and falls back to terran - the exact
    "NPC comms faces are still stock" symptom this exists to fix.
    
    Applied INSIDE random_face() rather than at its call sites, because a mission has many
    (LM alone has four for NPCs, one of them in a fleet spawner) and a missed one looks
    identical to the bug. A name with no entry passes through untouched, so player faces
    already named by species (`human`) are unaffected."""
def face_random_registered (race, role=None):
    """A random registered face for a race, or None if the race was never registered.
    
    A role with no faces falls back to the race pool rather than returning nothing -
    asking for a Breen science officer should still get a Breen."""
def face_register_race (race, faces, roles=None, in_random=True):
    """Declare ready-made face strings for a race so random_face(race) can use them.
    
    Args:
        race:      race name as scripts will ask for it, case-insensitive.
        faces:     list of face strings - the pool used when no role is asked for.
        roles:     optional {role: [face strings]} for role-filtered picks, e.g.
                   random_face("klingon", "command").
        in_random: whether a bare random_face()/random_face("random") may return this
                   race. A mod that only wants its faces when asked for by name
                   passes False."""
def face_register_sheet (alias, cols=8, rows=8):
    """Declare a mod atlas alias and its cell grid.
    
    `alias` is the short name in a face string ("tng1") and must match the name the
    engine reads from data/graphics/allFaceFiles.txt - the library cannot write that
    file, so registering here does NOT make the sheet loadable, it only teaches the
    library and the browser compositor how to read cells out of it."""
def face_registered_races (in_random_only=False):
    ...
def face_registered_sheets ():
    """{alias: {"cols","rows"}} - what the mock compositor and AMD renderer need."""
def face_resolve (spec):
    """Resolve a declarative face spec to a face string. A KEYWORD (terran / male / female /
    fluid) -> a fresh random face of that kind; a literal face string -> itself unchanged;
    None/empty -> a random terran. Lets AMD/data author a face as a simple word instead of a
    raw face string. (Promoted from Open Universe's lifeform_face.)"""
def face_sheet_grid (alias):
    """(cols, rows) for an alias. Stock geometry for the six built-ins: the Terran
    sheet is 15 wide, every other sheet is 8."""
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
def parse_face (face_string):
    """Recover (race, values, enables) from a face string — the inverse of
    build_face. Returns None if the string is not a recognized face. The result
    rebuilds to the same visual face via build_face (indices reproduce the same
    cells), so an editor can seed its controls from an existing face."""
def probably (chance):
    """Will compare a float with a random float between 0 and 1. If the provided number is larger than the random number, will return True.
    Args:
        chance (float): A float between 0 and 1."""
def random_arvonian ():
    """Create a random arvonian face.
    
    Returns:
        (str):   A Face string"""
def random_face (race=None, role=None, gender=None, civilian=None):
    """Returns a random face for the specified race.
    
    Mod races registered with face_register_race() are checked FIRST, so an add-on
    can supply "klingon" or "cardassian" without this function knowing they exist.
    That is what the TODO which used to sit here was asking for.
    
    Args:
        race (str): The Race Terran, Torgoth etc, or a registered mod race.
        role (str): optional role filter for registered races ("command", "ops"...).
                    Ignored by the six stock races, which have no role concept.
        gender (str): "male", "female", "fluid" - so a face can be asked to AGREE with
                    a name. Only terran has a gender axis; the other stock races ignore
                    it, as do mod races, whose faces are whole drawn portraits.
        civilian (bool): True forces no uniform, False forces one, None (the default)
                    leaves it to chance - which is one civilian in five. A crew member
                    wants False: a bridge officer out of uniform is not a variation, it
                    is a stranger on the bridge. Terran only, for the same reason.
    
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
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
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
