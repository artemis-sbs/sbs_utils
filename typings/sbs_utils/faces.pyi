def _build_face_features ():
    ...
def _face_tone_table (race, kind):
    ...
def _indices (race, layer):
    ...
def _layer_rows (race):
    """{row: layer} for the eye and mouth rows, used to find them in a built string."""
def _maybe (chance, pool):
    ...
def _owner_of (race, col, row):
    """Which layer a (col, row) belongs to, or None.
    
    The column matters as much as the row: three Terran features share the headwear row
    and two Ximni features share row 3, so "same row" is not the same as "same feature"."""
def _parse_face_layers (face_string):
    """[{alias, color, col, row, ox, oy}] for each ';'-separated layer."""
def _parse_v1_generic (race, layers):
    """Old feature indices for one of the five alien races, or None."""
def _parse_v1_terran (layers):
    """Old feature indices for a terran face, decoding the retired +3 gender columns."""
def _pick (pool):
    ...
def _swap_one (face_string, layer, index):
    """Replace just one layer's cell, leaving every other layer and tint alone.
    
    Matching on the ROW alone would be wrong on the sheets where two features share a
    row - Terran headwear, Ximni masks and mouths - so the replacement only applies to a
    layer whose column the target feature actually owns."""
def _tone_index (color, tones):
    ...
def arvonian (face_id, eye_id, mouth_id, crown_id, collar_id, hair_id=None):
    """Create an arvonian face.
    
    The redrawn Arvonian sheet is eight COMPLETE busts - face, eyes, mouth and skin
    pattern all painted in - so there is no eye or mouth layer to set. `eye_id` and
    `mouth_id` are folded into the choice of bust, which is what now carries identity,
    and `face_id` selects it directly when it is the only thing given.
    
    Args:
        face_id (int): bust, 0-7
        eye_id (int | None): folded into the bust
        mouth_id (int | None): folded into the bust
        crown_id (int | None): hat / headdress, 0-5, or None
        collar_id (int | None): clothes, 0-7, or None
        hair_id (int | None): hair, 0-2, or None
    
    Returns:
        (str): A Face string"""
def build_face (race, values, enables=None):
    """Build a face string from per-feature indices in FACE_FEATURES order.
    
    `values[i]` is the chosen index for feature i; `enables[i]` False switches an optional
    feature off. Returns '' for a race with no recipe."""
def clear_face (ship_id):
    """Removes a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object"""
def face_blink_frame (face_string, elapsed, period=4.0, close_for=0.14):
    """The face as it looks `elapsed` seconds into an idle blink cycle.
    
    Pure, for the same reason as face_talk_frame. `period` is how often a blink starts
    and `close_for` how long the eyes stay shut - short, because a blink that lingers
    reads as falling asleep rather than as being alive.
    
    Only races with a closed-eye cell blink - which is Terran alone; everyone else is
    returned untouched."""
def face_build (race, skin=None, hairtone=None, **layers):
    """Assemble a face string from per-layer indices.
    
    Layers are named by FACE_LAYERS[race]["cells"] - body, eyes, mouth, hair, clothes and
    whatever else that race has. A layer that is absent or None is simply not drawn, which
    is how optional parts (a hat, a headset, facial hair) stay optional. `body` defaults to
    0, because a face with no body is an invisible face.
    
    An index the race does not have that many of WRAPS rather than raising: see face_cell.
    
        face_build("terran", body=0, eyes=1, mouth=11, hair=3, clothes=16, skin=9)"""
def face_cell (race, layer, index):
    """(col, row) for one choice, wrapping out-of-range indices.
    
    Wrapping rather than raising is deliberate and load-bearing: every pre-redraw caller
    passes indices sized for the OLD sheets, and every count changed. A Skaraan hat index
    of 4 against a five-wide row still has to produce a Skaraan."""
def face_expression (face_string, expression):
    """Return `face_string` wearing a different expression.
    
    Only the eye and mouth layers change - body, hair, clothes, accessories and every
    tint are left exactly as they were, so a character keeps their identity while their
    face moves. An unknown expression, or a race that has none, returns the input
    unchanged rather than a stranger.
    
        angry = face_expression(get_face(officer), "angry")"""
def face_expressions (race):
    """The expression names a race can actually wear. [] for Arvonian."""
def face_eyes (face_string, index):
    """Return `face_string` with only its eye cell replaced."""
def face_gender_index (gender):
    """A gender word as the terran builder's face index, or None for "any".
    
    0 male, 1 female, 2 fluid - the numbering :func:`terran` documents. Unknown words
    answer None rather than guessing, so a mod's own vocabulary degrades to a random face
    instead of to the wrong one."""
def face_in_uniform (face_string):
    """True when the face is dressed as crew rather than as a civilian.
    
    "Uniform" used to be a feature of its own, a (hat, shirt) pair picked from a table.
    The redrawn Terran sheet has 24 garments in one row - dress uniforms, flight jackets,
    a lab coat, a leather jacket, a suit and tie - so being in uniform is now a property
    of WHICH garment, not a separate switch. The crew system needs the question answered
    either way: a bridge officer out of uniform is not a variation, it is a stranger at
    the helm.
    
    The five alien sheets draw only formal wear, so for them any clothing counts. A face
    wearing nothing at all is not in uniform."""
def face_is_valid (face_string):
    """True when every layer names a cell that exists on the sheet it points at.
    
    A PARTIAL check, and worth knowing how partial. It catches most stale alien faces,
    whose old rows 5-7 no longer exist on sheets that are now five or six rows tall. It
    catches almost no stale Terran one, because the new 24x7 grid still contains nearly
    every coordinate the old 15x8 could name. So a True answer means "not obviously
    stale", never "current"."""
def face_layer_cells (race, layer):
    """[(col, row)] for every choice of one layer, or [] if the race has no such layer."""
def face_layer_count (race, layer):
    """How many choices a layer offers.
    
    0 means the race does not have it at all - Torgoth has no mouth, Arvonian has
    neither eyes nor mouth - which callers must treat as "skip", never as an error."""
def face_migrate (face_string):
    """Translate a face string authored BEFORE the 2026-09 sheet redraw.
    
    The old string is read against the old cell layout, then rebuilt through the current
    builders - so the fold rules for features the new art dropped (a Torgoth's mouth, an
    Arvonian's eyes) live in exactly one place, the builders themselves.
    
    Not every old face has an exact successor and none of them can: the art is different.
    What this guarantees is that a migrated face is a VALID face of the right race that
    keeps as much of the original choice as survives. Faces that differed before still
    differ afterwards.
    
    Returns the input unchanged for a mod face or anything unreadable, so it is safe to
    run over a mixed pile of strings."""
def face_mod_reset ():
    """Drop every mod registration. Called by reset_mission_state()."""
def face_mod_size ():
    """Reset-ledger probe: how much mod registration is currently held."""
def face_mouth (face_string, index):
    """Return `face_string` with only its mouth cell replaced - the primitive a talking
    animation drives. Races with no mouth row return the input unchanged."""
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
def face_race_of (face_string):
    """The race a face string belongs to, or None for a mod atlas or an unreadable one."""
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
    """(cols, rows) for an alias, or None if nothing knows that sheet.
    
    A mod registration wins over the stock table, so a mod may re-point a stock alias.
    The six stock grids are all different since the 2026-09 redraw - see FACE_SHEETS."""
def face_talk_frame (face_string, elapsed, rate=7.0):
    """The face as it looks `elapsed` seconds into speaking.
    
    A PURE function of the time, deliberately: no ticker, no registry, no per-widget
    state to reset between missions. Whatever already has a clock - a GUI sub-task loop,
    an `on change` against a counter - calls this and assigns the result:
    
        --- talking
            await delay_sim(0.15)
            the_face.value = face_talk_frame(base_face, talk_elapsed)
            talk_elapsed += 0.15
            jump talking if talk_elapsed < line_seconds
            the_face.value = base_face
    
    Assigning is enough because Face.update() marks itself visual-dirty, so the engine
    re-sends it without a page rebuild.
    
    A race with no viseme mouths (Torgoth has no mouth row; Arvonian's busts are drawn
    whole) returns the input unchanged rather than flapping something that is not a
    mouth."""
def face_tint (race, kind, tone):
    """A tint hex (no leading '#') for a tone on a race, or 'fff' for no tint.
    
    `tone` is an index into that race's palette, a raw hex string (passed straight
    through, so a caller with its own color is never second-guessed), or None."""
def face_tone_indices (race, kind, natural_only=False):
    """Palette indices for a race, optionally only the ones that read as natural.
    
    Returns [] when the race has no palette of that kind - Arvonian has no skin ramp,
    and only three races have hair - so a caller can pass the result straight to a
    random pick and get None rather than a wrong color."""
def face_tone_names (race, kind):
    """The tone names for a race's palette, for an editor's dropdown. [] if it has none -
    Arvonian has no skin palette, and only three races have hair."""
def face_tone_tints (race, kind):
    """The tint hexes for a race's palette, in the same order as face_tone_names.
    
    Parsing needs these and an editor needs the names; handing a parser the NAMES matches
    nothing and silently reports tone 0, which reads as "this face has no tint" and
    quietly strips somebody's skin color on an edit."""
def face_visemes (race):
    """The mouth indices to cycle while somebody is speaking. [] means do not animate."""
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
def kralien (face_id, eye_id, mouth_id, scalp_id, extra_id, clothes_id=None):
    """Create a kralien face.
    
    Args:
        face_id (int): body - Kralien has only one, so this is ignored
        eye_id (int): eyes, 0-4
        mouth_id (int): mouth, 0-5
        scalp_id (int | None): rank pips, 0-2, or None
        extra_id (int | None): eyewear when even, hat when odd, or None
        clothes_id (int | None): clothes, 0-5, or None
    
    Returns:
        (str): A Face string"""
def parse_face (face_string):
    """Recover (race, values, enables) from a face string - the inverse of build_face.
    
    Returns None when the string is not a readable stock face: empty, malformed, or a MOD
    atlas, whose cells are whole drawn busts with no features to take apart. All three are
    "nothing to resume", which is what an editor needs to know.
    
    The result rebuilds to the identical string through build_face, so opening an editor
    on a face cannot silently change how somebody looks."""
def probably (chance):
    """True with the given probability.
    
    Args:
        chance (float): A float between 0 and 1."""
def random_arvonian ():
    """Create a random arvonian face.
    
    Returns:
        (str): A Face string"""
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
        (str): A Face string"""
def random_skaraan ():
    """Create a random skaraan face.
    
    Returns:
        (str): A Face string"""
def random_terran (face=None, civilian=None):
    """Create a random terran face.
    
    Args:
        face (int | None): 0=masculine, 1=feminine, 2/3=fluid, None=roll one
        civilian (bool | None): True forces no uniform, False forces one, None rolls
    
    Returns:
        (str): A Face string"""
def random_terran_female (civilian=None):
    """Create a random feminine terran face.
    
    Args:
        civilian (bool, optional): True forces a civilian, False a uniform, None rolls.
    
    Returns:
        (str): A Face string"""
def random_terran_fluid (civilian=None):
    """Create a random fluid terran face, mixing masculine and feminine features.
    
    Args:
        civilian (bool, optional): True forces a civilian, False a uniform, None rolls.
    
    Returns:
        (str): A Face string"""
def random_terran_male (civilian=None):
    """Create a random masculine terran face.
    
    Args:
        civilian (bool, optional): True forces a civilian, False a uniform, None rolls.
    
    Returns:
        (str): A Face string"""
def random_torgoth ():
    """Create a random torgoth face.
    
    Returns:
        (str): A Face string"""
def random_ximni ():
    """Create a random ximni face.
    
    Returns:
        (str): A Face string"""
def set_face (ship_id, face):
    """Sets a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string"""
def skaraan (face_id, eye_id, mouth_id, horn_id, hat_id, clothes_id=None):
    """Create a skaraan face.
    
    Args:
        face_id (int): body, 0-1
        eye_id (int): eyes, 0-4
        mouth_id (int): mouth, 0-4
        horn_id (int | None): hair, 0-1, or None
        hat_id (int | None): headwear (wraps, veil, headpiece), 0-4, or None
        clothes_id (int | None): clothes, 0-4, or None. New; the old sheet had none.
    
    Returns:
        (str): A Face string"""
def terran (face_id, eye_id, mouth_id, hair_id, longhair_id, facial_id, extra_id, uniform_id, skintone, hairtone):
    """Create a terran face.
    
    Two arguments changed meaning with the redraw, both because the art merged rows.
    `longhair_id` is used only when `hair_id` is None - long and short styles now share
    one row of 22. `extra_id` selects eyewear, which is what the old "extra" cells were.
    
    Args:
        face_id (int | None): 0=masculine, 1=feminine, 2/3=fluid (body is face_id % 2)
        eye_id (int | None): eyes, 0-13
        mouth_id (int): mouth, 0-13
        hair_id (int | None): hair, 0-21, or None
        longhair_id (int | None): hair, used only when hair_id is None
        facial_id (int | None): facial hair, 0-13, or None
        extra_id (int | None): eyewear, 0-3, or None
        uniform_id (int | None): uniform, 0-9, or None for a civilian
        skintone (int | str | None): palette index, a hex string, or None
        hairtone (int | str | None): palette index, a hex string, or None
    
    Returns:
        (str): A Face string"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def torgoth (face_id, eye_id, mouth_id, hair_id, extra_id, hat_id, clothes_id=None):
    """Create a torgoth face.
    
    The redrawn Torgoth sheet has NO mouth row, so `mouth_id` is folded into the nose
    when no nose was asked for - dropping it outright would collapse distinct old faces
    onto one another.
    
    Args:
        face_id (int): body, 0-1
        eye_id (int): eyes, 0-4
        mouth_id (int): folded into the nose; Torgoth has no mouth art
        hair_id (int | None): nose / tendrils, 0-3, or None
        extra_id (int | None): armored eye plate, or None
        hat_id (int | None): hat, 0-3, or None
        clothes_id (int | None): clothes, 0-10, or None
    
    Returns:
        (str): A Face string"""
def ximni (face_id, eye_id, mouth_id, horns_id, mask_id, collar_id):
    """Create a ximni face.
    
    Args:
        face_id (int): body, 0-1
        eye_id (int): eyes, 0-3
        mouth_id (int): mouth, 0-3
        horns_id (int | None): horns, 0-3, or None
        mask_id (int | None): breathing mask, 0-3, or None
        collar_id (int | None): clothes, 0-2, or None
    
    Returns:
        (str): A Face string"""
class Characters(object):
    """A set of predefined faces"""
