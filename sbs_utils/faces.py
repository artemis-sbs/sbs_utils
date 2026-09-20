from random import randrange,uniform, choice
from .procedural.query import to_id
from .face_tints import SKIN_TINTS as FACE_TINTS_SKIN, HAIR_TINTS as FACE_TINTS_HAIR

# Atlas aliases, as data/graphics/allFaceFiles.txt registers them:
#   ter Terran_Big-revised   tor Torgoth_Set   ska Skaraan_Set
#   kra Krailen_Set          zim Zimni_Set     arv Arvonian
# (Krailen and Zimni are the engine's spellings of Kralien and Ximni. They are the
# filenames on disk, so they are not ours to correct here.)

faces_map = {}

def get_face(ship_id):
    """
    Returns a face string for a specified ID

    Args:
        ship_id (Agent | int): The id of the ship/object

    Returns:
        str: A Face string
    """
    return faces_map.get(to_id(ship_id), "")

def set_face(ship_id, face):
    """
    Sets a face string for a specified ID.

    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string
    """
    faces_map[to_id(ship_id)] = face

def clear_face(ship_id):
    """ 
    Removes a face string for a specified ID.

    Args:
        ship_id (Agent | int): The id of the ship/object
    """
    faces_map.pop(to_id(ship_id), None)


# =============================================================================
# Sheet geometry
# =============================================================================
# Every atlas is a grid of 512x512 cells and a face string names one by (col, row).
# The six stock sheets were REDRAWN in 2026-09: they no longer share a grid, and the
# cell meaning changed from an ad-hoc scatter of coordinates to "one row per layer".
# So this table is the thing that has to be right - a wrong grid here silently slices
# somebody's ear out of the middle of a hat.
FACE_SHEETS = {
    "ter": (24, 7),
    "tor": (11, 5),
    "ska": (7, 5),
    "kra": (6, 6),
    "zim": (8, 5),
    "arv": (8, 4),
}

#: The grid the SAME aliases had before the redraw. Kept because an old face string is
#: still readable - see face_migrate - even though the art it named is gone.
FACE_SHEETS_V1 = {"ter": (15, 8), "tor": (8, 8), "ska": (8, 8),
                  "kra": (8, 8), "zim": (8, 8), "arv": (8, 8)}


# =============================================================================
# Layer tables
# =============================================================================
# Per race:
#   alias  - the atlas tag a face string carries
#   cells  - layer -> (row, [columns]). A COLUMN LIST rather than a range because
#            several rows hold two or three unrelated features: the Terran headwear row
#            is hats, eyewear and headsets side by side, and Ximni's row 3 is masks then
#            mouths. Splitting them lets a character wear a cap AND a headset, which is
#            free - a face string may carry any number of layers.
#   order  - draw order, LOWEST FIRST. Clothes sit under hair so long hair falls over
#            the shoulders; eyewear over eyes; a headset boom over everything.
#   tint   - which palette, if any, colors a layer. Anything unlisted draws untinted.
#
#            THE EYE AND MOUTH LAYERS TAKE THE SKIN TINT. They are not clean cutouts:
#            measured, an eye cell is 17-31% skin and a mouth cell 19-40% - brow ridge,
#            eyelid, the surround of the lips. Tint the body alone and that skin stays the
#            color it was painted, so a re-toned face wears a pale mask around the eyes
#            and a pale muzzle. It is glaring on a dark or non-human tone and it is the
#            reason the pre-redraw builder tinted face, eyes and mouth together.
#            Equipment on those same rows must NOT take it - a Ximni breathing mask and a
#            Torgoth eye-plate are hardware, not skin.
#   names  - a label per cell, so an editor can offer "Worried" instead of "Eyes 6".
#   resting- which indices suit a face AT REST, for the randomizers. Some cells are
#            states, not identities: a closed eye, an eye-roll, a mouth caught mid-word.
#            They are wanted for expressions and offered in the editor, but rolling one
#            as somebody's default portrait gives you an officer who is permanently
#            asleep or forever saying "oh". Measured before this existed: 177 random
#            Terrans in 400 wore an open mouth and 67 had closed or rolled-up eyes.
#            A layer with no entry here has no unsuitable cells.
#
# Verified cell by cell with _tools/face_contact_sheet.py, which composites every cell
# over its body. That is the only way to check this table; reading the PNG tells you
# nothing, because a mouth cell is a few hundred pixels of lip in an empty square.

_TER_EYE_NAMES = [
    "Angry", "Open", "Soft", "Glancing", "Calm", "Calm Wide", "Worried", "Looking Up",
    "Suspicious", "Closed", "Green", "Amber", "Blue", "Scowling",
]
_TER_MOUTH_NAMES = [
    "Neutral", "Thin", "Open Wide", "Open Smile", "Pale", "Gray Lips", "Pink Lips",
    "Gritted", "Pursed", "Slight", "Dismayed", "Smiling", "Closed", "Parted",
]

FACE_LAYERS = {
    "terran": {
        "alias": "ter",
        "cells": {
            "body":    (0, [0, 1]),
            "eyes":    (1, list(range(14))),
            "mouth":   (2, list(range(14))),
            "hair":    (3, list(range(22))),
            "facial":  (4, list(range(14))),
            "hat":     (5, [0, 1, 2, 3, 4, 5]),
            "eyewear": (5, [6, 7, 8, 9]),
            "headset": (5, [10, 11]),
            "clothes": (6, list(range(24))),
        },
        "order": ["body", "clothes", "eyes", "mouth", "facial", "hair",
                  "hat", "eyewear", "headset"],
        "tint": {"body": "skin", "eyes": "skin", "mouth": "skin",
                 "hair": "hair", "facial": "hair"},
        "names": {
            "body": ["Masculine", "Feminine"],
            "eyes": _TER_EYE_NAMES,
            "mouth": _TER_MOUTH_NAMES,
        },
        # Out: worried, looking up, closed; and every open or talking mouth shape.
        "resting": {"eyes": [0, 1, 2, 3, 4, 5, 8, 10, 11, 12, 13],
                    "mouth": [0, 1, 4, 5, 6, 9, 11, 12]},
    },
    "skaraan": {
        "alias": "ska",
        "cells": {
            "body":     (0, [0, 1]),
            "eyes":     (1, [0, 1, 2, 3, 4]),
            "mouth":    (2, [0, 1, 2, 3, 4]),
            # Row 3 is two features: 0-1 are hair and take the hair tint, 2-6 are wraps,
            # veils and a metal headpiece, which must NOT be recolored as if they were.
            "hair":     (3, [0, 1]),
            "headwear": (3, [2, 3, 4, 5, 6]),
            "clothes":  (4, [0, 1, 2, 3, 4]),
        },
        "order": ["body", "clothes", "eyes", "mouth", "hair", "headwear"],
        "tint": {"body": "skin", "eyes": "skin", "mouth": "skin", "hair": "hair"},
        "names": {
            "body": ["Masculine", "Feminine"],
            "eyes": ["Red", "Hazel", "Pale Blue", "Gold", "Dark"],
            "mouth": ["Grin", "Bared Teeth", "Open", "Smirk", "Neutral"],
        },
        # Out: bared teeth (a snarl) and the open talking shape.
        "resting": {"mouth": [0, 3, 4]},
    },
    "kralien": {
        "alias": "kra",
        "cells": {
            "body":    (0, [0]),
            "pips":    (1, [0, 1, 2]),
            "eyewear": (2, [0]),
            "hat":     (2, [1]),
            "eyes":    (3, [0, 1, 2, 3, 4]),
            "mouth":   (4, [0, 1, 2, 3, 4, 5]),
            "clothes": (5, [0, 1, 2, 3, 4, 5]),
        },
        "order": ["body", "clothes", "eyes", "mouth", "pips", "eyewear", "hat"],
        "tint": {"body": "skin", "eyes": "skin", "mouth": "skin"},
        "names": {
            "body": ["Kralien"],
            "pips": ["One", "Two", "Three"],
            "eyes": ["Pale Blue", "Blue", "Green", "Brown", "Amber"],
            "mouth": ["Snarl", "Speaking", "Neutral", "Grimace", "Roar", "Resting"],
        },
        # Out: snarl, mid-word, grimace and roar - none of them is a face at rest.
        "resting": {"mouth": [2, 5]},
    },
    "torgoth": {
        "alias": "tor",
        "cells": {
            "body":    (0, [0, 1]),
            "nose":    (1, [0, 1, 2, 3]),
            "hat":     (2, [0, 1, 2, 3]),
            # Column 4 of the eye row is an armored eye-plate, not an eye - a separate
            # decoration that layers OVER whichever eye was chosen.
            "eyes":    (3, [0, 1, 2, 3, 5]),
            "plate":   (3, [4]),
            "clothes": (4, list(range(11))),
        },
        # No mouth row at all: a Torgoth cannot change expression, only its eyes.
        "order": ["body", "clothes", "nose", "eyes", "plate", "hat"],
        "tint": {"body": "skin", "eyes": "skin", "nose": "skin"},
        "names": {
            "body": ["Heavy", "Lean"],
            "nose": ["Long Tendrils", "Short", "Medium", "Trunk"],
            "eyes": ["Burning", "Dark", "Faceted", "Blue", "Green Slit"],
            "plate": ["Eye Plate"],
        },
    },
    "ximni": {
        "alias": "zim",
        "cells": {
            "body":    (0, [0, 1]),
            # Row 1 mixes hair and horns; only the hair takes the hair tint.
            "hair":    (1, [0, 5]),
            "horns":   (1, [1, 2, 3, 4]),
            "eyes":    (2, [0, 1, 2, 3]),
            # Row 3 is masks then mouths - a mask covers a mouth, so both can be worn.
            "mask":    (3, [0, 1, 2, 3]),
            "mouth":   (3, [4, 5, 6, 7]),
            "clothes": (4, [0, 1, 2]),
        },
        "order": ["body", "clothes", "eyes", "mouth", "mask", "horns", "hair"],
        # Horns take the SKIN tint: they grow out of the head, so a Ximni who changes
        # color has to change with them or the horns read as a bolted-on prop. Same
        # reasoning as the Torgoth nose. The mask on the next row does NOT - that one
        # really is hardware.
        "tint": {"body": "skin", "eyes": "skin", "mouth": "skin", "horns": "skin",
                 "hair": "hair"},
        "names": {
            "body": ["Masculine", "Feminine"],
            "eyes": ["Gray", "Teal", "Narrowed", "Yellow"],
            "mouth": ["Frown", "Smirk", "Neutral", "Downturned"],
            "mask": ["Respirator", "Breather", "Armored", "Warmask"],
        },
    },
    "arvonian": {
        "alias": "arv",
        # The eight Arvonian bodies are COMPLETE busts with face and skin pattern baked
        # in. There is no eye layer and no mouth layer, so this race has no expression
        # and no meaningful skin tint - tinting it would be tinting somebody's tattoos.
        # Everything that walks these tables has to tolerate that rather than assume all
        # six races are built the same way.
        "cells": {
            "body":    (0, list(range(8))),
            "hat":     (1, [0, 1, 2, 3, 4, 5]),
            "hair":    (2, [0, 1, 2]),
            "clothes": (3, list(range(8))),
        },
        "order": ["body", "clothes", "hair", "hat"],
        "tint": {"body": "skin", "hair": "hair"},
        "names": {"body": ["Rose", "Monochrome", "Prismatic", "Aurora", "Ash",
                           "Copper", "Pale", "Verdant"]},
    },
}

#: alias -> race. Mod atlases are not in here; they register themselves instead.
FACE_ALIAS_TO_RACE = {v["alias"]: k for k, v in FACE_LAYERS.items()}


def face_layer_cells(race, layer):
    """[(col, row)] for every choice of one layer, or [] if the race has no such layer."""
    spec = FACE_LAYERS.get(str(race).lower(), {}).get("cells", {}).get(layer)
    if not spec:
        return []
    row, cols = spec
    return [(c, row) for c in cols]


def face_layer_count(race, layer):
    """How many choices a layer offers.

    0 means the race does not have it at all - Torgoth has no mouth, Arvonian has
    neither eyes nor mouth - which callers must treat as "skip", never as an error.
    """
    return len(face_layer_cells(race, layer))


def face_cell(race, layer, index):
    """(col, row) for one choice, wrapping out-of-range indices.

    Wrapping rather than raising is deliberate and load-bearing: every pre-redraw caller
    passes indices sized for the OLD sheets, and every count changed. A Skaraan hat index
    of 4 against a five-wide row still has to produce a Skaraan.
    """
    cells = face_layer_cells(race, layer)
    if not cells:
        return None
    return cells[int(index) % len(cells)]


# =============================================================================
# Tints
# =============================================================================
# The engine has exactly one blend mode for a face layer: MULTIPLY. So a tint can only
# darken, and a palette written as "the color I want to see" is half unusable - which is
# what the old skin_tones table was, measured: 23 of its 31 entries were lighter than the
# painted skin and did visibly nothing.
#
# face_tints.py is GENERATED from the art by _tools/face_tint_calibrate.py, and carries
# two kinds of tone:
#
#   HUMAN tones (`fair*`, `dark*`, `warm*`, `c*`) keep the painted skin's own character
#   and move only its lightness and warmth. A ramp down from the face as drawn, not an
#   absolute color picker - truly pale skin needs a desaturated gray body cell in the art,
#   which is an outstanding ask to the artist.
#
#   EXOTIC tones (emerald, ice-blue, crimson, ...) divide the base skin out of
#   the tint so the HUE survives the multiply. Without that correction a blue tint on warm
#   skin just darkens toward the base and comes out brown - `ice-blue` measured #67553f
#   before this existed. These read well on all five tinted races, Torgoth included.
#
# See EXOTIC_SKIN, and face_tone_index() to ask for one by name.

#: Backward-compatible names. Old code indexes these lists and passes the index to
#: terran(), so they have to keep their length and their order - only the VALUES are
#: recalibrated. Anything that passed a raw hex string still gets it through untouched.
skin_tones = [t for _name, t in FACE_TINTS_SKIN.get("ter", [])] or ["ffffff"]
hair_tones = [t for _name, t in FACE_TINTS_HAIR.get("ter", [])] or ["ffffff"]


def face_tint(race, kind, tone):
    """A tint hex (no leading '#') for a tone on a race, or 'fff' for no tint.

    `tone` is an index into that race's palette, a raw hex string (passed straight
    through, so a caller with its own color is never second-guessed), or None.
    """
    if tone is None:
        return "fff"
    if isinstance(tone, str):
        return tone.lstrip("#") or "fff"
    table = FACE_TINTS_SKIN if kind == "skin" else FACE_TINTS_HAIR
    alias = FACE_LAYERS.get(str(race).lower(), {}).get("alias")
    pool = table.get(alias)
    if not pool:
        return "fff"
    hexed = pool[int(tone) % len(pool)][1]
    # Index 0 is pure white. Spell it "fff" - that is what every hand-written face string
    # in the tree uses for "no tint", and emitting the long form instead would make
    # build_face(parse_face(s)) differ from s by six characters that mean nothing.
    return "fff" if hexed in ("ffffff", "fff") else hexed


#: Tone names that read as human. The palette deliberately carries green, blue and violet
#: skins and fuchsia hair - they are wanted, for aliens and for a mission that asks - but
#: a random TERRAN must not roll one. This was invisible before the redraw only because
#: most of the old palette multiplied to nothing; now that the ramp works, drawing
#: uniformly makes roughly two humans in five green.
#: Human-looking tones. Everything absent from this set - the greens, blues, violets and
#: the named species tones - is deliberate art that a mission or an editor can choose, and
#: that a random TERRAN must never roll.
_NATURAL_SKIN = {"none", "c1", "c2", "c3", "c4", "c5",
                 "fair1", "fair2", "fair3", "fair4", "fair5",
                 "dark1", "dark2", "dark3", "dark4", "dark5",
                 "warm1", "warm2", "warm3"}

#: The non-human skin tones, for a mission that wants one by name rather than by index:
#: ``face_build("terran", skin=face_tone_index("terran", "emerald"))``.
#: Named for the COLOR only - these ship, so no borrowed species names.
EXOTIC_SKIN = ("emerald", "jade", "ice-blue", "cobalt",
               "rust", "crimson", "ashen", "amber")
_NATURAL_HAIR = {"none", "blonde", "brown", "sandy", "chestnut", "gunmetal", "red"}


def face_tone_indices(race, kind, natural_only=False):
    """Palette indices for a race, optionally only the ones that read as natural.

    Returns [] when the race has no palette of that kind - Arvonian has no skin ramp,
    and only three races have hair - so a caller can pass the result straight to a
    random pick and get None rather than a wrong color.
    """
    keep = _NATURAL_SKIN if kind == "skin" else _NATURAL_HAIR
    names = face_tone_names(race, kind)
    return [i for i, n in enumerate(names) if (not natural_only or n in keep)]


def face_tone_names(race, kind):
    """The tone names for a race's palette, for an editor's dropdown. [] if it has none -
    Arvonian has no skin palette, and only three races have hair."""
    return [n for n, _t in _face_tone_table(race, kind)]


def face_tone_index(race, kind, name, default=0):
    """The palette index of a tone BY NAME, so a mission can ask for "emerald"
    instead of counting. Unknown names answer `default` rather than raising - a face
    built from tone 0 is still a face, and a mission should not die over a color."""
    names = face_tone_names(race, kind)
    try:
        return names.index(str(name).strip().lower())
    except ValueError:
        return default


def face_tone_tints(race, kind):
    """The tint hexes for a race's palette, in the same order as face_tone_names.

    Parsing needs these and an editor needs the names; handing a parser the NAMES matches
    nothing and silently reports tone 0, which reads as "this face has no tint" and
    quietly strips somebody's skin color on an edit.
    """
    return [t for _n, t in _face_tone_table(race, kind)]


def _face_tone_table(race, kind):
    table = FACE_TINTS_SKIN if kind == "skin" else FACE_TINTS_HAIR
    alias = FACE_LAYERS.get(str(race).lower(), {}).get("alias")
    return table.get(alias, [])


# =============================================================================
# Building a face
# =============================================================================

def face_build(race, skin=None, hairtone=None, **layers):
    """Assemble a face string from per-layer indices.

    Layers are named by FACE_LAYERS[race]["cells"] - body, eyes, mouth, hair, clothes and
    whatever else that race has. A layer that is absent or None is simply not drawn, which
    is how optional parts (a hat, a headset, facial hair) stay optional. `body` defaults to
    0, because a face with no body is an invisible face.

    An index the race does not have that many of WRAPS rather than raising: see face_cell.

        face_build("terran", body=0, eyes=1, mouth=11, hair=3, clothes=16, skin=9)
    """
    race = str(race).lower()
    spec = FACE_LAYERS.get(race)
    if spec is None:
        return ""
    layers.setdefault("body", 0)
    alias = spec["alias"]
    tints = spec.get("tint", {})
    out = []
    for name in spec["order"]:
        index = layers.get(name)
        if index is None:
            continue
        cell = face_cell(race, name, index)
        if cell is None:          # the race has no such layer - skip, do not guess
            continue
        kind = tints.get(name)
        tone = skin if kind == "skin" else (hairtone if kind == "hair" else None)
        out.append(f"{alias} #{face_tint(race, kind, tone)} {cell[0]} {cell[1]};")
    return "".join(out)


def _pick(pool):
    return choice(pool) if pool else None


def _maybe(chance, pool):
    return choice(pool) if (pool and probably(chance)) else None


def _indices(race, layer):
    """The indices a RANDOM face may use for a layer.

    Honors the race's `resting` list, so a randomizer never hands somebody a closed eye
    or a mid-word mouth as their standing portrait. The editor and face_expression reach
    the full set through face_layer_count / face_cell; this is the resting subset only.
    """
    resting = FACE_LAYERS.get(str(race).lower(), {}).get("resting", {}).get(layer)
    if resting is not None:
        return list(resting)
    return list(range(face_layer_count(race, layer)))


# Which eye and mouth cells lean which way. The old sheets encoded gender as "+3 on the
# column" across four separate layers; the new ones do not - body 0 is masculine, body 1
# feminine, and everything else is shared art. So gender survives as a PREFERENCE over
# shared cells rather than as separate cells, and "fluid" becomes what it always meant:
# the body from one pool and the features from the other.
_TER_EYES_MASC = [0, 3, 4, 8, 13]
_TER_EYES_FEM = [2, 5, 6]
_TER_EYES_ANY = [1, 7, 9, 10, 11, 12]
_TER_MOUTH_MASC = [0, 1, 7, 9, 12]
_TER_MOUTH_FEM = [5, 6]
_TER_MOUTH_ANY = [2, 3, 4, 8, 10, 11, 13]

#: Terran clothes, grouped so "civilian" keeps meaning something. Everything not listed
#: as civilian or utility is a uniform.
_TER_CLOTHES_CIVILIAN = [5, 6, 11, 13, 14, 19]
_TER_CLOTHES_UTILITY = [0, 1, 2, 3, 4, 8]
_TER_CLOTHES_UNIFORM = [c for c in range(24)
                        if c not in _TER_CLOTHES_CIVILIAN and c not in _TER_CLOTHES_UTILITY]


# =============================================================================
# Expressions and visemes
# =============================================================================
# The redrawn sheets carry expression art the old ones did not: Terran alone has 14 eye
# cells (angry, worried, glancing, eye-roll, suspicious, closed) and 14 mouths (gritted,
# smiling, dismayed, plus open shapes usable as visemes). An expression is therefore just
# a named (eyes, mouth) pair, and swapping it touches nothing else about the face.
#
# A race missing a cell for an expression falls back to neutral rather than approximating.
# Torgoth has no mouth row, so its expressions move the eyes only; Arvonian's busts are
# drawn whole and it has no expression at all.
FACE_EXPRESSIONS = {
    "terran": {"neutral": (1, 0), "happy": (2, 11), "angry": (0, 7), "worried": (6, 10),
               "suspicious": (8, 9), "shocked": (6, 2), "asleep": (9, 0)},
    "skaraan": {"neutral": (4, 4), "happy": (1, 0), "angry": (0, 1), "worried": (2, 4),
                "suspicious": (3, 3), "shocked": (2, 2)},
    "kralien": {"neutral": (0, 2), "happy": (2, 1), "angry": (3, 0), "worried": (0, 3),
                "suspicious": (4, 5), "shocked": (1, 4)},
    "ximni": {"neutral": (0, 2), "happy": (1, 1), "angry": (2, 0), "worried": (0, 3),
              "suspicious": (2, 1), "shocked": (3, 0)},
    "torgoth": {"neutral": (1, None), "angry": (0, None), "suspicious": (4, None),
                "shocked": (3, None)},
    "arvonian": {},
}

#: Mouth cells cycled to animate speech, in a reading order that looks like talking.
#: Empty where a race has no mouth to move.
FACE_VISEMES = {
    "terran": [2, 3, 8, 10, 13],
    "skaraan": [2, 1, 0, 4],
    "kralien": [1, 4, 0, 2],
    "ximni": [0, 1, 3, 2],
    "torgoth": [],
    "arvonian": [],
}


def face_expressions(race):
    """The expression names a race can actually wear. [] for Arvonian."""
    return list(FACE_EXPRESSIONS.get(str(race).lower(), {}))


def _layer_rows(race):
    """{row: layer} for the eye and mouth rows, used to find them in a built string."""
    spec = FACE_LAYERS.get(race, {})
    cells = spec.get("cells", {})
    out = {}
    for name in ("eyes", "mouth"):
        if name in cells:
            out[cells[name][0]] = name
    return out


def face_expression(face_string, expression):
    """Return `face_string` wearing a different expression.

    Only the eye and mouth layers change - body, hair, clothes, accessories and every
    tint are left exactly as they were, so a character keeps their identity while their
    face moves. An unknown expression, or a race that has none, returns the input
    unchanged rather than a stranger.

        angry = face_expression(get_face(officer), "angry")
    """
    layers = _parse_face_layers(face_string)
    if not layers:
        return face_string
    race = FACE_ALIAS_TO_RACE.get(layers[0]["alias"])
    pair = FACE_EXPRESSIONS.get(race, {}).get(str(expression).strip().lower())
    if pair is None:
        return face_string
    swap = {}
    for name, index in (("eyes", pair[0]), ("mouth", pair[1])):
        if index is None:
            continue
        cell = face_cell(race, name, index)
        if cell is not None:
            swap[cell[1]] = cell        # keyed by row - that is what identifies the layer
    rows = _layer_rows(race)
    out = []
    for lay in layers:
        cell = swap.get(lay["row"]) if lay["row"] in rows else None
        col = cell[0] if cell else lay["col"]
        out.append(f"{lay['alias']} #{lay['color']} {col} {lay['row']};")
    return "".join(out)


def _swap_one(face_string, layer, index):
    """Replace just one layer's cell, leaving every other layer and tint alone.

    Matching on the ROW alone would be wrong on the sheets where two features share a
    row - Terran headwear, Ximni masks and mouths - so the replacement only applies to a
    layer whose column the target feature actually owns.
    """
    layers = _parse_face_layers(face_string)
    if not layers:
        return face_string
    race = FACE_ALIAS_TO_RACE.get(layers[0]["alias"])
    cell = face_cell(race, layer, index)
    if cell is None:
        return face_string
    out = []
    for lay in layers:
        hit = _owner_of(race, lay["col"], lay["row"])
        col = cell[0] if (hit and hit[0] == layer) else lay["col"]
        out.append(f"{lay['alias']} #{lay['color']} {col} {lay['row']};")
    return "".join(out)


def face_mouth(face_string, index):
    """Return `face_string` with only its mouth cell replaced - the primitive a talking
    animation drives. Races with no mouth row return the input unchanged."""
    return _swap_one(face_string, "mouth", index)


def face_eyes(face_string, index):
    """Return `face_string` with only its eye cell replaced."""
    return _swap_one(face_string, "eyes", index)


#: The closed-eye cell per race, for an idle blink. ONLY TERRAN HAS ONE - the redrawn
#: alien sheets draw their eyes as color variants, not as expressions, so nobody else
#: can shut them. Listing it rather than reusing the "asleep" expression matters: asleep
#: also drops the mouth to neutral, and a blink that changes somebody's mouth reads as a
#: twitch.
FACE_BLINK = {"terran": 9}


def face_visemes(race):
    """The mouth indices to cycle while somebody is speaking. [] means do not animate."""
    return list(FACE_VISEMES.get(str(race).lower(), []))


def face_talk_frame(face_string, elapsed, rate=7.0):
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
    mouth.
    """
    race = face_race_of(face_string)
    pool = FACE_VISEMES.get(race or "", [])
    if not pool:
        return face_string
    step = int(max(0.0, float(elapsed)) * float(rate)) % len(pool)
    return face_mouth(face_string, pool[step])


def face_blink_frame(face_string, elapsed, period=4.0, close_for=0.14):
    """The face as it looks `elapsed` seconds into an idle blink cycle.

    Pure, for the same reason as face_talk_frame. `period` is how often a blink starts
    and `close_for` how long the eyes stay shut - short, because a blink that lingers
    reads as falling asleep rather than as being alive.

    Only races with a closed-eye cell blink - which is Terran alone; everyone else is
    returned untouched.
    """
    shut = FACE_BLINK.get(face_race_of(face_string) or "")
    if shut is None:
        return face_string
    if float(period) <= 0 or (float(elapsed) % float(period)) >= float(close_for):
        return face_string
    return face_eyes(face_string, shut)


def face_in_uniform(face_string):
    """True when the face is dressed as crew rather than as a civilian.

    "Uniform" used to be a feature of its own, a (hat, shirt) pair picked from a table.
    The redrawn Terran sheet has 24 garments in one row - dress uniforms, flight jackets,
    a lab coat, a leather jacket, a suit and tie - so being in uniform is now a property
    of WHICH garment, not a separate switch. The crew system needs the question answered
    either way: a bridge officer out of uniform is not a variation, it is a stranger at
    the helm.

    The five alien sheets draw only formal wear, so for them any clothing counts. A face
    wearing nothing at all is not in uniform.
    """
    layers = _parse_face_layers(face_string)
    if not layers:
        return False
    race = FACE_ALIAS_TO_RACE.get(layers[0]["alias"])
    if race is None:
        return False
    for lay in layers:
        hit = _owner_of(race, lay["col"], lay["row"])
        if hit is None or hit[0] != "clothes":
            continue
        if race != "terran":
            return True
        return lay["col"] not in _TER_CLOTHES_CIVILIAN
    return False


def face_race_of(face_string):
    """The race a face string belongs to, or None for a mod atlas or an unreadable one."""
    layers = _parse_face_layers(face_string)
    if not layers:
        return None
    return FACE_ALIAS_TO_RACE.get(layers[0]["alias"])


# =============================================================================
# The per-race builders
# =============================================================================
# These keep the argument lists they have always had, because missions call them
# positionally and a signature change would be a silent miscast rather than an error.
# What changed underneath is which layer each argument drives - see the mapping notes on
# each function. Where the redrawn art dropped a feature the argument is still ACCEPTED
# and folded into whichever layer still carries identity, so two old faces that looked
# different still look different.


def probably(chance):
    """True with the given probability.

    Args:
        chance (float): A float between 0 and 1.
    """
    return uniform(0, 1) < chance


def skaraan(face_id, eye_id, mouth_id, horn_id, hat_id, clothes_id=None):
    """Create a skaraan face.

    Args:
        face_id (int): body, 0-1
        eye_id (int): eyes, 0-4
        mouth_id (int): mouth, 0-4
        horn_id (int | None): hair, 0-1, or None
        hat_id (int | None): headwear (wraps, veil, headpiece), 0-4, or None
        clothes_id (int | None): clothes, 0-4, or None. New; the old sheet had none.

    Returns:
        (str): A Face string
    """
    return face_build("skaraan", body=face_id, eyes=eye_id, mouth=mouth_id,
                      hair=horn_id, headwear=hat_id, clothes=clothes_id)


#: Whether a random face may use the WHOLE skin palette, greens and blues included.
#:
#: True by default, and it is the owner's call: the exotic tones are real art, and a
#: randomizer that never reaches them means nobody ever sees them. The cost is worth
#: stating plainly - `random_face("terran")` is what crew.py rolls for an unnamed bridge
#: officer and what `random_face()` falls back to for an unregistered race, so roughly
#: half of a randomly-crewed bridge will not be flesh-colored.
#:
#: Set it False for flesh tones only. Nothing else needs changing; the natural subset is
#: still `face_tone_indices(race, kind, natural_only=True)` and the editor, missions and
#: `face_build` always reach every tone regardless.
RANDOM_FULL_TONE_RANGE = True


def _random_tones(race):
    """{skin, hairtone} for a random face of a race.

    Every tinted race gets skin variation, not just Terran. The five alien randomizers
    used to leave skin alone entirely - "preserve the old behavior" - which was
    defensible while the palettes barely worked and indefensible once the avatar editor
    grew a Randomize button: pressing it on a Kralien changed everything about them
    except their color.

    EVERY tinted race varies, including Arvonian, and by default every one of them draws
    from the WHOLE palette - see RANDOM_FULL_TONE_RANGE. The greens, blues and violets are
    real art; a randomizer that never reaches them means nobody ever sees them.
    """
    race = str(race).lower()
    out = {}
    for kind, key in (("skin", "skin"), ("hair", "hairtone")):
        if RANDOM_FULL_TONE_RANGE:
            pool = list(range(len(face_tone_names(race, kind))))
        else:
            pool = face_tone_indices(race, kind, natural_only=True)
        if pool:
            out[key] = choice(pool)
    return out


def random_skaraan():
    """Create a random skaraan face.

    Returns:
        (str): A Face string
    """
    return face_build("skaraan",
                      body=_pick(_indices("skaraan", "body")),
                      eyes=_pick(_indices("skaraan", "eyes")),
                      mouth=_pick(_indices("skaraan", "mouth")),
                      hair=_maybe(0.5, _indices("skaraan", "hair")),
                      headwear=_maybe(0.4, _indices("skaraan", "headwear")),
                      clothes=_maybe(0.8, _indices("skaraan", "clothes")),
                      **_random_tones("skaraan"))


def torgoth(face_id, eye_id, mouth_id, hair_id, extra_id, hat_id, clothes_id=None):
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
        (str): A Face string
    """
    nose = hair_id if hair_id is not None else mouth_id
    return face_build("torgoth", body=face_id, eyes=eye_id, nose=nose,
                      plate=extra_id, hat=hat_id, clothes=clothes_id)


def random_torgoth():
    """Create a random torgoth face.

    Returns:
        (str): A Face string
    """
    return face_build("torgoth",
                      body=_pick(_indices("torgoth", "body")),
                      eyes=_pick(_indices("torgoth", "eyes")),
                      nose=_pick(_indices("torgoth", "nose")),
                      plate=_maybe(0.15, _indices("torgoth", "plate")),
                      hat=_maybe(0.35, _indices("torgoth", "hat")),
                      clothes=_maybe(0.85, _indices("torgoth", "clothes")),
                      **_random_tones("torgoth"))


def arvonian(face_id, eye_id, mouth_id, crown_id, collar_id, hair_id=None):
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
        (str): A Face string
    """
    body = face_id
    if not body:
        body = eye_id if eye_id is not None else (mouth_id if mouth_id is not None else 0)
    return face_build("arvonian", body=body, hat=crown_id,
                      clothes=collar_id, hair=hair_id)


def random_arvonian():
    """Create a random arvonian face.

    Returns:
        (str): A Face string
    """
    return face_build("arvonian",
                      body=_pick(_indices("arvonian", "body")),
                      hair=_maybe(0.35, _indices("arvonian", "hair")),
                      hat=_maybe(0.45, _indices("arvonian", "hat")),
                      clothes=_maybe(0.8, _indices("arvonian", "clothes")),
                      **_random_tones("arvonian"))


def ximni(face_id, eye_id, mouth_id, horns_id, mask_id, collar_id):
    """Create a ximni face.

    Args:
        face_id (int): body, 0-1
        eye_id (int): eyes, 0-3
        mouth_id (int): mouth, 0-3
        horns_id (int | None): horns, 0-3, or None
        mask_id (int | None): breathing mask, 0-3, or None
        collar_id (int | None): clothes, 0-2, or None

    Returns:
        (str): A Face string
    """
    return face_build("ximni", body=face_id, eyes=eye_id, mouth=mouth_id,
                      horns=horns_id, mask=mask_id, clothes=collar_id)


def random_ximni():
    """Create a random ximni face.

    Returns:
        (str): A Face string
    """
    masked = probably(0.25)
    return face_build("ximni",
                      body=_pick(_indices("ximni", "body")),
                      eyes=_pick(_indices("ximni", "eyes")),
                      # A mask covers the mouth, so drawing one underneath is wasted work.
                      mouth=None if masked else _pick(_indices("ximni", "mouth")),
                      mask=_pick(_indices("ximni", "mask")) if masked else None,
                      horns=_maybe(0.55, _indices("ximni", "horns")),
                      hair=_maybe(0.3, _indices("ximni", "hair")),
                      clothes=_maybe(0.8, _indices("ximni", "clothes")),
                      **_random_tones("ximni"))


def kralien(face_id, eye_id, mouth_id, scalp_id, extra_id, clothes_id=None):
    """Create a kralien face.

    Args:
        face_id (int): body - Kralien has only one, so this is ignored
        eye_id (int): eyes, 0-4
        mouth_id (int): mouth, 0-5
        scalp_id (int | None): rank pips, 0-2, or None
        extra_id (int | None): eyewear when even, hat when odd, or None
        clothes_id (int | None): clothes, 0-5, or None

    Returns:
        (str): A Face string
    """
    eyewear = hat = None
    if extra_id is not None:
        if int(extra_id) % 2 == 0:
            eyewear = int(extra_id) // 2
        else:
            hat = int(extra_id) // 2
    return face_build("kralien", body=0, eyes=eye_id, mouth=mouth_id,
                      pips=scalp_id, eyewear=eyewear, hat=hat, clothes=clothes_id)


def random_kralien():
    """Create a random kralien face.

    Returns:
        (str): A Face string
    """
    hatted = probably(0.2)
    return face_build("kralien", body=0,
                      eyes=_pick(_indices("kralien", "eyes")),
                      mouth=_pick(_indices("kralien", "mouth")),
                      pips=_maybe(0.5, _indices("kralien", "pips")),
                      hat=_pick(_indices("kralien", "hat")) if hatted else None,
                      eyewear=None if hatted else _maybe(0.25, _indices("kralien", "eyewear")),
                      clothes=_maybe(0.85, _indices("kralien", "clothes")),
                      **_random_tones("kralien"))


#: (hat, clothes) per uniform index. Ten entries, keeping the old table's length and its
#: red / green / blue / black grouping, so a stored uniform_id still lands on a uniform of
#: roughly the color it used to.
terran_uniform = [
    (0, 17), (None, 23), (4, 15),     # reds
    (2, 18), (1, 20),                 # greens
    (3, 21), (5, 22),                 # blues
    (None, 16), (0, 12), (None, 7),   # blacks
]


def terran(face_id, eye_id, mouth_id, hair_id, longhair_id, facial_id, extra_id,
           uniform_id, skintone, hairtone):
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
        (str): A Face string
    """
    body = 0 if face_id is None else int(face_id) % 2
    hair = hair_id if hair_id is not None else longhair_id
    if uniform_id is None:
        # A FIXED civilian garment, not a random one. This is the explicit builder: the
        # same arguments have to produce the same face every time, or face_migrate is
        # non-deterministic and a source sweep rewrites the same file differently on
        # every run. Rolling belongs in random_terran, which does its own choosing.
        hat, clothes = None, _TER_CLOTHES_CIVILIAN[0]
    else:
        hat, clothes = terran_uniform[int(uniform_id) % len(terran_uniform)]
    return face_build("terran", body=body, eyes=eye_id, mouth=mouth_id, hair=hair,
                      facial=facial_id, eyewear=extra_id, hat=hat, clothes=clothes,
                      skin=skintone, hairtone=hairtone)


def random_terran(face=None, civilian=None):
    """Create a random terran face.

    Args:
        face (int | None): 0=masculine, 1=feminine, 2/3=fluid, None=roll one
        civilian (bool | None): True forces no uniform, False forces one, None rolls

    Returns:
        (str): A Face string
    """
    if face is None:
        fluid = probably(0.3)
        face = 2 if fluid else randrange(0, 2)
    is_fluid = int(face) >= 2
    body = int(face) % 2
    # Feminine features on a masculine body, or the reverse, is what "fluid" means. With
    # the redraw that is a choice of POOL rather than a column offset, because the eye and
    # mouth art is now shared between bodies instead of duplicated per gender.
    feminine = (body == 1)
    if is_fluid:
        feminine = not feminine
    # Intersected with the resting set, so the gender pools cannot smuggle back in the
    # closed eye and the mid-word mouths they happen to list.
    rest_eyes = set(_indices("terran", "eyes"))
    rest_mouths = set(_indices("terran", "mouth"))
    eyes = [e for e in _TER_EYES_ANY + (_TER_EYES_FEM if feminine else _TER_EYES_MASC)
            if e in rest_eyes]
    mouths = [m for m in _TER_MOUTH_ANY + (_TER_MOUTH_FEM if feminine else _TER_MOUTH_MASC)
              if m in rest_mouths]

    hair = _maybe(0.95 if feminine else 0.8, _indices("terran", "hair"))
    facial = _maybe(0.05 if feminine else 0.6, _indices("terran", "facial"))
    eyewear = _maybe(0.2, _indices("terran", "eyewear"))
    headset = _maybe(0.12, _indices("terran", "headset"))

    if civilian is True:
        hat, clothes = None, choice(_TER_CLOTHES_CIVILIAN)
    elif civilian is False:
        hat, clothes = terran_uniform[randrange(0, len(terran_uniform))]
    elif probably(0.2):
        hat, clothes = None, choice(_TER_CLOTHES_CIVILIAN)
    else:
        hat, clothes = terran_uniform[randrange(0, len(terran_uniform))]
    if hat is not None and headset is not None:
        headset = None          # a peaked cap and a headband do not share a head

    return face_build("terran", body=body, eyes=choice(eyes), mouth=choice(mouths),
                      hair=hair, facial=facial, eyewear=eyewear, headset=headset,
                      hat=hat, clothes=clothes,
                      **_random_tones("terran"))


def random_terran_male(civilian=None):
    """Create a random masculine terran face.

    Args:
        civilian (bool, optional): True forces a civilian, False a uniform, None rolls.

    Returns:
        (str): A Face string
    """
    return random_terran(0, civilian)


def random_terran_female(civilian=None):
    """Create a random feminine terran face.

    Args:
        civilian (bool, optional): True forces a civilian, False a uniform, None rolls.

    Returns:
        (str): A Face string
    """
    return random_terran(1, civilian)


def random_terran_fluid(civilian=None):
    """Create a random fluid terran face, mixing masculine and feminine features.

    Args:
        civilian (bool, optional): True forces a civilian, False a uniform, None rolls.

    Returns:
        (str): A Face string
    """
    return random_terran(randrange(0, 10) % 2 + 2, civilian)


_FACE_KEYWORDS = {
    "terran": random_terran, "male": random_terran_male, "terran_male": random_terran_male,
    "female": random_terran_female, "terran_female": random_terran_female,
    "fluid": random_terran_fluid, "terran_fluid": random_terran_fluid,
}


def face_resolve(spec):
    """Resolve a declarative face spec to a face string. A KEYWORD (terran / male / female /
    fluid) -> a fresh random face of that kind; a literal face string -> itself unchanged;
    None/empty -> a random terran. Lets AMD/data author a face as a simple word instead of a
    raw face string. (Promoted from Open Universe's lifeform_face.)"""
    if not spec:
        return random_terran()
    gen = _FACE_KEYWORDS.get(str(spec).strip().lower())
    return gen() if gen is not None else spec


# --- Mod-registered face sheets and races -------------------------------------
# The six stock races are built up layer by layer from their atlas (eyes, mouth,
# hat...). A mod atlas does not have to work that way: the TNG sheets are one whole
# bust per cell, so their "builder" is just a ready-made face string. Both kinds can
# live here at once because a face string is a face string either way.
#
# Registration is what makes `random_face("klingon")` reach a mod race at all. Before
# this the race list was a hard-coded match statement - hence the TODO that used to
# sit in random_face.
#
# Both dicts are per-mission module state, so they are cleared by
# reset_mission_state() and declared to the reset ledger in handlerhooks. An
# unregistered container is invisible to the restart soak, and a face registry that
# survived a reload would hand mission 2 the face strings of mission 1 pointing at an
# atlas alias that is no longer registered.
_MOD_SHEETS: dict = {}          # alias -> {"cols": int, "rows": int}
_MOD_RACES: dict = {}           # race  -> {"any": [...], "roles": {role: [...]}, "in_random": bool}


def face_register_sheet(alias, cols=8, rows=8):
    """Declare a mod atlas alias and its cell grid.

    `alias` is the short name in a face string ("tng1") and must match the name the
    engine reads from data/graphics/allFaceFiles.txt - the library cannot write that
    file, so registering here does NOT make the sheet loadable, it only teaches the
    library and the browser compositor how to read cells out of it.
    """
    _MOD_SHEETS[str(alias)] = {"cols": int(cols), "rows": int(rows)}


def face_sheet_grid(alias):
    """(cols, rows) for an alias, or None if nothing knows that sheet.

    A mod registration wins over the stock table, so a mod may re-point a stock alias.
    The six stock grids are all different since the 2026-09 redraw - see FACE_SHEETS.
    """
    m = _MOD_SHEETS.get(str(alias))
    if m:
        return m["cols"], m["rows"]
    return FACE_SHEETS.get(str(alias))


def face_registered_sheets():
    """{alias: {"cols","rows"}} - what the mock compositor and AMD renderer need."""
    return dict(_MOD_SHEETS)


def face_register_race(race, faces, roles=None, in_random=True):
    """Declare ready-made face strings for a race so random_face(race) can use them.

    Args:
        race:      race name as scripts will ask for it, case-insensitive.
        faces:     list of face strings - the pool used when no role is asked for.
        roles:     optional {role: [face strings]} for role-filtered picks, e.g.
                   random_face("klingon", "command").
        in_random: whether a bare random_face()/random_face("random") may return this
                   race. A mod that only wants its faces when asked for by name
                   passes False.
    """
    key = str(race).lower()
    e = _MOD_RACES.setdefault(key, {"any": [], "roles": {}, "in_random": bool(in_random)})
    e["any"].extend(faces or [])
    e["in_random"] = bool(in_random)
    for role, pool in (roles or {}).items():
        e["roles"].setdefault(str(role).lower(), []).extend(pool or [])


def face_registered_races(in_random_only=False):
    if in_random_only:
        return [r for r, e in _MOD_RACES.items() if e["in_random"] and e["any"]]
    return [r for r, e in _MOD_RACES.items() if e["any"]]


def face_random_registered(race, role=None):
    """A random registered face for a race, or None if the race was never registered.

    A role with no faces falls back to the race pool rather than returning nothing -
    asking for a Breen science officer should still get a Breen.
    """
    e = _MOD_RACES.get(str(race).lower())
    if not e:
        return None
    pool = e["roles"].get(str(role).lower()) if role else None
    if not pool:
        pool = e["any"]
    return choice(pool) if pool else None


def face_overlay(face_string, *overlays):
    """Stack overlay layers onto an existing face string.

    This is the whole point of keeping implants as separate cells: any face can be
    assimilated at runtime, including one that was never drawn with implants. Layers
    composite lowest-first, so overlays go last.

        face_overlay(random_face("terran"), "tng6 #fff 2 1", "tng6 #fff 5 3")

    Empty/None overlays are skipped so a caller can pass an optional one straight in.
    """
    parts = [p.strip() for p in str(face_string or "").split(";") if p.strip()]
    for o in overlays:
        parts.extend(p.strip() for p in str(o or "").split(";") if p.strip())
    return ";".join(parts) + ";" if parts else ""


def face_mod_reset():
    """Drop every mod registration. Called by reset_mission_state()."""
    _MOD_SHEETS.clear()
    _MOD_RACES.clear()


def face_mod_size():
    """Reset-ledger probe: how much mod registration is currently held."""
    return len(_MOD_SHEETS) + len(_MOD_RACES)


def face_race_mapped(race):
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
    already named by species (`human`) are unaffected.
    """
    if not race:
        return race
    try:
        from .procedural.settings import settings_get_defaults
        raw = settings_get_defaults().get("RACE_FACES") or {}
        if not raw:
            # An explicit setting wins; otherwise the active THEATER supplies it, so the
            # roster, the hull art and the crew faces all come from one declaration and
            # cannot drift apart.
            from .procedural.amd_theater import theater_faces
            raw = theater_faces()
    except Exception:
        return race
    if not isinstance(raw, dict):
        return race
    mapped = raw.get(str(race).strip().lower())
    if not mapped:
        for k, v in raw.items():
            if str(k).strip().lower() == str(race).strip().lower():
                mapped = v
                break
    return mapped if mapped else race


#: What a gender word means to the terran builder's `face_id`. Everything else - "", None,
#: a word nobody here knows - stays None, which is "roll one", the behavior this had before
#: the argument existed.
_FACE_GENDER = {"male": 0, "m": 0, "man": 0,
                "female": 1, "f": 1, "woman": 1,
                "fluid": 2, "nonbinary": 2, "non-binary": 2, "nb": 2}


def face_gender_index(gender):
    """A gender word as the terran builder's face index, or None for "any".

    0 male, 1 female, 2 fluid - the numbering :func:`terran` documents. Unknown words
    answer None rather than guessing, so a mod's own vocabulary degrades to a random face
    instead of to the wrong one.
    """
    return _FACE_GENDER.get(str(gender or "").strip().lower())


def random_face(race=None, role=None, gender=None, civilian=None):
    """
    Returns a random face for the specified race.

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
        str: The Face String
    """
    # Mod re-skin map first - identity unless RACE_FACES is set. See face_race_mapped.
    race = face_race_mapped(race)
    if race is not None and str(race).lower() != "random":
        s = face_random_registered(race, role)
        if s is not None:
            return s
    if race is None or race.lower() == "random":
        pool = ["kralien", "arvonian", "skaraan", "torgoth", "ximni", "terran", "civilian"]
        pool += face_registered_races(in_random_only=True)
        race = choice(pool)
        s = face_random_registered(race, role)
        if s is not None:
            return s
    race = race.lower()
    # The gender and uniform asks reach the terran builder, which is the only stock race
    # with either axis. The three `terran_*` spellings name a gender themselves, so an
    # explicit argument only fills in where the spelling did not say.
    face_id = face_gender_index(gender)
    match race:
        case "terran":
            return random_terran(face_id, civilian)
        case "terran_male":
            return random_terran_male(civilian)
        case "terran_female":
            return random_terran_female(civilian)
        case "terran_fluid":
            return random_terran_fluid(civilian)
        case "terran_civilian":
            return random_terran_fluid(True)
        case "torgoth":
            return random_torgoth()
        case "skaraan":
            return random_skaraan()
        case "ximni":
            return random_ximni()
        case "arvonian":
            return random_arvonian()
        case "kralien":
            return random_kralien()
    return random_terran(face_id, civilian)




# =============================================================================
# Face builder recipe - what an editor shows one control for
# =============================================================================
# DERIVED from FACE_LAYERS rather than hand-written. There used to be four independent
# copies of this table (here, pages/avatar.py, modding_tools' char_editor, and the LSP's
# own), and they drifted: the Terran entry capped Hair at 4 when ten cells existed, and
# Facial Hair at 4 when there were eleven. Generating it means the recipe cannot disagree
# with the art.
#
# `key` names the face_build layer the control drives; `kind: "choice"` plus `names` tells
# an editor to draw a dropdown of real words instead of a nameless slider.

#: (key, label, optional) per race, in the order an editor should present them.
_FEATURE_ORDER = {
    "terran": [("body", "Body", False), ("eyes", "Eyes", False), ("mouth", "Mouth", False),
               ("hair", "Hair", True), ("facial", "Facial Hair", True),
               ("hat", "Hat", True), ("eyewear", "Eyewear", True),
               ("headset", "Headset", True), ("clothes", "Clothes", False)],
    "skaraan": [("body", "Body", False), ("eyes", "Eyes", False), ("mouth", "Mouth", False),
                ("hair", "Hair", True), ("headwear", "Headwear", True),
                ("clothes", "Clothes", True)],
    "kralien": [("eyes", "Eyes", False), ("mouth", "Mouth", False),
                ("pips", "Rank Pips", True), ("eyewear", "Eyewear", True),
                ("hat", "Hat", True), ("clothes", "Clothes", True)],
    "torgoth": [("body", "Body", False), ("nose", "Nose", False), ("eyes", "Eyes", False),
                ("plate", "Eye Plate", True), ("hat", "Hat", True),
                ("clothes", "Clothes", True)],
    "ximni": [("body", "Body", False), ("eyes", "Eyes", False), ("mouth", "Mouth", True),
              ("mask", "Mask", True), ("horns", "Horns", True), ("hair", "Hair", True),
              ("clothes", "Clothes", True)],
    "arvonian": [("body", "Body", False), ("hair", "Hair", True), ("hat", "Headdress", True),
                 ("clothes", "Clothes", True)],
}


def _build_face_features():
    out = {}
    for race, order in _FEATURE_ORDER.items():
        feats = []
        names = FACE_LAYERS[race].get("names", {})
        for key, label, optional in order:
            count = face_layer_count(race, key)
            if count == 0:
                continue          # the race does not have this layer at all
            f = {"label": label, "key": key, "max": count - 1}
            if optional:
                f["optional"] = True
            if key in names:
                f["kind"] = "choice"
                f["names"] = list(names[key])
            feats.append(f)
        for kind, label in (("skin", "Skin Tone"), ("hair", "Hair Tone")):
            tones = face_tone_names(race, kind)
            if tones:
                feats.append({"label": label, "key": "tone:" + kind, "max": len(tones) - 1,
                              "kind": "choice", "names": tones})
        out[race] = feats
    return out


FACE_FEATURES = _build_face_features()


def build_face(race, values, enables=None):
    """Build a face string from per-feature indices in FACE_FEATURES order.

    `values[i]` is the chosen index for feature i; `enables[i]` False switches an optional
    feature off. Returns '' for a race with no recipe.
    """
    race = str(race).lower()
    feats = FACE_FEATURES.get(race)
    if feats is None:
        return ""
    kwargs = {}
    for i, f in enumerate(feats):
        if i >= len(values):
            break
        on = enables[i] if (enables is not None and i < len(enables)) else True
        value = values[i] if on else None
        key = f["key"]
        if key == "tone:skin":
            kwargs["skin"] = value
        elif key == "tone:hair":
            kwargs["hairtone"] = value
        else:
            kwargs[key] = value
    return face_build(race, **kwargs)


def _parse_face_layers(face_string):
    """[{alias, color, col, row, ox, oy}] for each ';'-separated layer."""
    layers = []
    for seg in (face_string or "").split(";"):
        p = seg.split()
        if len(p) < 4:
            continue
        try:
            layers.append({
                "alias": p[0], "color": p[1].lstrip("#").lower(),
                "col": int(p[2]), "row": int(p[3]),
                "ox": int(p[4]) if len(p) > 4 else 0,
                "oy": int(p[5]) if len(p) > 5 else 0,
            })
        except ValueError:
            continue
    return layers


def _tone_index(color, tones):
    c = (color or "").lower()
    if c in ("fff", "ffffff"):
        return 0
    for i, t in enumerate(tones):
        if t.lower() == c:
            return i
    return 0


def _owner_of(race, col, row):
    """Which layer a (col, row) belongs to, or None.

    The column matters as much as the row: three Terran features share the headwear row
    and two Ximni features share row 3, so "same row" is not the same as "same feature".
    """
    for name, (r, cols) in FACE_LAYERS[race]["cells"].items():
        if r == row and col in cols:
            return name, cols.index(col)
    return None


def parse_face(face_string):
    """Recover (race, values, enables) from a face string - the inverse of build_face.

    Returns None when the string is not a readable stock face: empty, malformed, or a MOD
    atlas, whose cells are whole drawn busts with no features to take apart. All three are
    "nothing to resume", which is what an editor needs to know.

    The result rebuilds to the identical string through build_face, so opening an editor
    on a face cannot silently change how somebody looks.
    """
    layers = _parse_face_layers(face_string)
    if not layers:
        return None
    race = FACE_ALIAS_TO_RACE.get(layers[0]["alias"])
    if race is None or race not in FACE_FEATURES:
        return None
    feats = FACE_FEATURES[race]
    index_of = {f["key"]: i for i, f in enumerate(feats)}
    values = [0] * len(feats)
    enables = [not f.get("optional", False) for f in feats]
    tints = FACE_LAYERS[race].get("tint", {})
    for lay in layers:
        hit = _owner_of(race, lay["col"], lay["row"])
        if hit is None:
            continue
        name, choice_index = hit
        i = index_of.get(name)
        if i is not None:
            values[i] = choice_index
            enables[i] = True
        kind = tints.get(name)
        if kind:
            ti = index_of.get("tone:" + kind)
            if ti is not None:
                values[ti] = _tone_index(lay["color"], face_tone_tints(race, kind))
    return {"race": race, "values": values, "enables": enables}


# =============================================================================
# Reading a pre-redraw face string
# =============================================================================
# The six stock sheets were replaced in place, under the same aliases, so an old face
# string is not wrong-looking - it names cells that now hold something else entirely. It
# is also INDISTINGUISHABLE from a new one: "ter #fff 3 0" was a feminine face and is now
# hair #3, same six tokens. Nothing can tell them apart at runtime, so migration is never
# automatic - a caller has to know that what it is holding was authored before the redraw.
#
# These tables are the OLD layout, kept purely so such a string can still be read. No art
# matches them any more.
_V1_MAPS = {
    "skaraan": {
        "face": [(0, 0)],
        "eyes": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
        "mouth": [(1, 4), (1, 5), (1, 6), (2, 1), (3, 1)],
        "horns": [(0, 6), (1, 0), (2, 0), (3, 0), (4, 0)],
        "hat": [(5, 0), (6, 0), (1, 1), (1, 2), (1, 3)],
    },
    "torgoth": {
        "face": [(0, 0)],
        "eyes": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
        "mouth": [(1, 4), (1, 5), (1, 6), (2, 1), (3, 1)],
        "hair": [(0, 6), (1, 0), (2, 0), (3, 0), (4, 0)],
        "extra": [(6, 0), (1, 1), (1, 2), (1, 3)],
        "hat": [(5, 0)],
    },
    "arvonian": {
        "face": [(0, 0)],
        "eyes": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
        "mouth": [(1, 4), (1, 5), (1, 6), (2, 1), (3, 1)],
        "crown": [(0, 6), (1, 0), (2, 0), (3, 0), (4, 0)],
        "collar": [(5, 0), (6, 0), (1, 1), (1, 2), (1, 3)],
    },
    "ximni": {
        "face": [(0, 0)],
        "eyes": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
        "mouth": [(1, 4), (1, 5), (1, 6), (2, 1), (3, 1)],
        "horns": [(0, 6), (1, 0), (2, 0), (3, 0), (4, 0)],
        "mask": [(1, 1), (1, 2), (1, 3)],
        "collar": [(5, 0), (6, 0)],
    },
    "kralien": {
        "face": [(0, 0)],
        "eyes": [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
        "mouth": [(1, 4), (1, 5), (1, 6), (2, 1), (3, 1)],
        "scalp": [(0, 6), (1, 0), (2, 0), (3, 0), (4, 0)],
        "extra": [(5, 0), (6, 0), (1, 1), (1, 2), (1, 3)],
    },
    "terran": {
        "face": [(0, 0)],
        "eyes": [(1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2)],
        "mouth": [(1, 2), (2, 2), (0, 3), (1, 3), (2, 3), (0, 4)],
        "shirt": [(1, 4), (2, 4), (0, 5), (1, 5), (2, 5), (0, 6), (1, 6), (2, 6),
                  (0, 7), (1, 7)],
        "hair": [(8, 0), (6, 1), (6, 2), (6, 3), (7, 3), (7, 4), (8, 4), (6, 5),
                 (7, 5), (8, 5)],
        "longhair": [(6, 0), (7, 0), (7, 1), (8, 1), (7, 2), (8, 2), (8, 3), (6, 4)],
        "facial": [(9, 0), (10, 0), (11, 0), (9, 1), (10, 1), (11, 1),
                   (9, 2), (10, 2), (11, 2), (9, 3), (10, 3)],
        "extra": [(13, 1), (14, 1), (12, 2), (13, 2), (14, 2), (12, 3)],
        "hat": [(12, 0), (13, 0), (14, 0), (12, 1)],
    },
}

#: (hat, shirt) per uniform index, as the old terran builder paired them.
_V1_TERRAN_UNIFORM = [(0, 0), (0, 6), (0, 8), (1, 2), (1, 5),
                      (2, 1), (2, 3), (3, 7), (3, 8), (3, 9)]

#: The old palettes, needed only to turn an old layer color back into an index.
_V1_SKIN_TONES = [
    "ffffff", "ffcd94", "fff0bd", "eac086", "ffe39f", "ffab60", "f2efee", "efe6dd",
    "ebd3c5", "d7b6a5", "9f7967", "70361c", "714937", "65371e", "492816", "321b0f",
    "bf9169", "8c644d", "593123", "964b00", "6d8b01", "009973", "69e1c3", "0095b3",
    "00c3e6", "95e3f3", "573d76", "6e5e8e", "acb057", "c0caff", "333d70",
]
_V1_HAIR_TONES = ["ffffff", "FAF0BE", "3D2314", "CC9966", "97502d", "1E1a33",
                  "7C0A02", "968b00", "964b00", "3d0463", "3d0463", "FA01B3"]


def _parse_v1_generic(race, layers):
    """Old feature indices for one of the five alien races, or None."""
    fmap = _V1_MAPS[race]
    lookup = {}
    for key, cells in fmap.items():
        for i, cell in enumerate(cells):
            lookup.setdefault((cell[0], cell[1]), (key, i))
    found = {}
    for lay in layers:
        hit = lookup.get((lay["col"], lay["row"]))
        if hit is None:
            continue
        key, i = hit
        if key != "face":
            found[key] = i
    return found


def _parse_v1_terran(layers):
    """Old feature indices for a terran face, decoding the retired +3 gender columns."""
    tm = _V1_MAPS["terran"]
    female = any(lay["row"] == 0 and lay["col"] == 3 and (lay["ox"], lay["oy"]) == (0, 0)
                 for lay in layers)
    found = {"face": 1 if female else 0}

    def find(key, col, row):
        try:
            return tm[key].index((col, row))
        except ValueError:
            return None

    def find_either(key, col, row):
        # Eyes and mouth carried their own +3 offset INDEPENDENTLY of the body - that is
        # what a "fluid" face was - so the body's gender cannot be used to un-shift them.
        i = find(key, col, row)
        if i is None and col >= 3:
            i = find(key, col - 3, row)
        return i

    shirt_i = hat_i = None
    for lay in layers:
        col, row, off, color = lay["col"], lay["row"], (lay["ox"], lay["oy"]), lay["color"]
        if off == (6, -2):
            i = find("longhair", col, row)
            if i is not None:
                found["longhair"] = i
            else:
                i = find("hair", col, row)
                if i is not None:
                    found["hair"] = i
            found["hairtone"] = _tone_index(color, _V1_HAIR_TONES)
            continue
        if off == (14, -2):
            hat_i = find("hat", col, row)
            continue
        if off == (12, 4):
            i = find("facial", col, row)
            if i is not None:
                found["facial"] = i
                found["hairtone"] = _tone_index(color, _V1_HAIR_TONES)
            continue
        if off == (20, 4):
            i = find("extra", col, row)
            if i is not None:
                found["extra"] = i
            continue
        c = col - 3 if (female and col >= 3) else col
        if (c, row) == (0, 0):
            found["skintone"] = _tone_index(color, _V1_SKIN_TONES)
            continue
        i = find_either("eyes", col, row)
        if i is not None:
            found["eyes"] = i
            found["skintone"] = _tone_index(color, _V1_SKIN_TONES)
            continue
        i = find_either("mouth", col, row)
        if i is not None:
            found["mouth"] = i
            found["skintone"] = _tone_index(color, _V1_SKIN_TONES)
            continue
        i = find_either("shirt", col, row)
        if i is not None:
            shirt_i = i
            continue
        # HAND-WRITTEN old strings left the offsets off. The builder always emitted hair
        # as "6 -2" and facial hair as "12 4", so the branches above key on that - but a
        # face typed into a .mast by hand is just "ter #964b00 8 1", and without this
        # fallback every such character migrated bald. Coordinates alone are enough here
        # because these four tables do not overlap the ones already tried.
        for key in ("longhair", "hair", "facial", "extra", "hat"):
            i = find(key, col, row)
            if i is None:
                continue
            if key == "hat":
                hat_i = i
            else:
                found[key] = i
                if key in ("longhair", "hair", "facial"):
                    found["hairtone"] = _tone_index(color, _V1_HAIR_TONES)
            break
    civilian_shirt = tm["shirt"].index((2, 5))
    if hat_i is not None or (shirt_i is not None and shirt_i != civilian_shirt):
        try:
            found["uniform"] = _V1_TERRAN_UNIFORM.index(
                (hat_i if hat_i is not None else 0, shirt_i if shirt_i is not None else 0))
        except ValueError:
            pass
    return found


def face_migrate(face_string):
    """Translate a face string authored BEFORE the 2026-09 sheet redraw.

    The old string is read against the old cell layout, then rebuilt through the current
    builders - so the fold rules for features the new art dropped (a Torgoth's mouth, an
    Arvonian's eyes) live in exactly one place, the builders themselves.

    Not every old face has an exact successor and none of them can: the art is different.
    What this guarantees is that a migrated face is a VALID face of the right race that
    keeps as much of the original choice as survives. Faces that differed before still
    differ afterwards.

    Returns the input unchanged for a mod face or anything unreadable, so it is safe to
    run over a mixed pile of strings.
    """
    layers = _parse_face_layers(face_string)
    if not layers:
        return face_string
    race = FACE_ALIAS_TO_RACE.get(layers[0]["alias"])
    if race is None:
        return face_string
    if race == "terran":
        f = _parse_v1_terran(layers)
        return terran(f.get("face", 0), f.get("eyes", 0), f.get("mouth", 0),
                      f.get("hair"), f.get("longhair"), f.get("facial"), f.get("extra"),
                      f.get("uniform"), f.get("skintone"), f.get("hairtone"))
    f = _parse_v1_generic(race, layers)
    if race == "skaraan":
        return skaraan(0, f.get("eyes", 0), f.get("mouth", 0), f.get("horns"), f.get("hat"))
    if race == "torgoth":
        return torgoth(0, f.get("eyes", 0), f.get("mouth", 0), f.get("hair"),
                       f.get("extra"), f.get("hat"))
    if race == "arvonian":
        return arvonian(0, f.get("eyes"), f.get("mouth"), f.get("crown"), f.get("collar"))
    if race == "ximni":
        return ximni(0, f.get("eyes", 0), f.get("mouth", 0), f.get("horns"),
                     f.get("mask"), f.get("collar"))
    if race == "kralien":
        return kralien(0, f.get("eyes", 0), f.get("mouth", 0), f.get("scalp"), f.get("extra"))
    return face_string


def face_is_valid(face_string):
    """True when every layer names a cell that exists on the sheet it points at.

    A PARTIAL check, and worth knowing how partial. It catches most stale alien faces,
    whose old rows 5-7 no longer exist on sheets that are now five or six rows tall. It
    catches almost no stale Terran one, because the new 24x7 grid still contains nearly
    every coordinate the old 15x8 could name. So a True answer means "not obviously
    stale", never "current".
    """
    layers = _parse_face_layers(face_string)
    if not layers:
        return False
    for lay in layers:
        grid = FACE_SHEETS.get(lay["alias"]) or face_sheet_grid(lay["alias"])
        if grid is None:
            continue                      # a mod atlas we were never told the size of
        cols, rows = grid
        if not (0 <= lay["col"] < cols and 0 <= lay["row"] < rows):
            return False
    return True


def get_face_from_data(race):
    """
    ### Deprecated in v1.1.0.
    Use random_race instead.

    Args:
        race (_type_): _description_

    Returns:
        _type_: _description_
    """
    print("get_face_from_data is depricated in v1.1.0 use random_race instead")
    return random_face(race)


#class Characters(StrEnum): # Python 3.11 will have StrEnum
class Characters:
    """
    A set of predefined faces
    """
    URSULA  = "ter #fff 1 0;ter #fff 5 6;ter #fff 0 1;ter #fff 1 2;ter #884400 6 3;"
