"""Names for the built-in icon sheet, and one lookup that takes a NAME.

`data/graphics/grid-icon-sheet.png` is a 2560x2560 sheet of **128px cells, 20 across** -
400 slots of which **0..175 are drawn** (the rest are free for custom art). The glyphs are
white on transparent, which is why `color:` in the style string does all the work: one
glyph serves every state.

Until now every caller wrote a bare number - `gui_icon("icon_index:101;...")` - so the
quest log's state square, the list box's fold arrows and a mission's own icons were all
magic constants, and nothing could be re-skinned without editing the code that draws it.

    gui_icon_name("square")        -> the built-in glyph
    gui_icon_name("quest.job")     -> whatever a mission says a job looks like

WHY A NAME AND NOT A NUMBER. It is the same move the image atlas already makes
(`gui_image_add_atlas` maps a key onto a file + sub-rect): the caller says WHAT it wants
and the library decides where that comes from. A name can be backed by a built-in index
today and a cell of a custom sheet tomorrow, without the drawing code changing - so
consumers can be written before any art exists, and a mission can re-point
`quest.job` at its own sheet and re-skin every quest log in the game.

The identifications come from the sheet itself (most of these are from game-icons.net);
a few are best-guess and marked. Adding or correcting a name is a line here.
"""

# --- the built-in sheet: name -> icon_index --------------------------------------
# Grouped as an author would look for them, not by index. The grouping is DATA, not
# comments, because the same headings serve the docs gallery and a picker.
ICON_GROUPS = {
    "Science & space": {
        "atom": 0, "wheel": 1, "propeller": 2, "swirl": 3, "magnet": 4, "brain": 5,
        "trefoil": 6, "vortex": 7, "pinwheel": 8, "rings": 9, "satellite-dish": 11,
        "gem": 12, "globe": 13, "waveform": 15, "ram": 17, "radioactive": 29,
        "honeycomb": 30, "asteroid": 51, "specimen": 64, "microscope": 63,
        "molecule": 54, "globe-grid": 159, "dome": 138, "fallout": 139, "reactor": 125,
        "triskelion": 44,
    },
    "Ship systems & engineering": {
        "sawblade": 19, "recycle": 20, "capsule": 21, "gears": 28, "battery": 35,
        "gear": 55, "gear-solid": 56, "gears-two": 57, "maintenance": 58, "turbine": 59,
        "factory": 60, "pipes": 61, "press": 62, "gear-ring": 67, "circuit": 68,
        "circuit-maze": 69, "mechanism": 70, "forge": 113, "fountain": 114,
        "elevator": 115, "damaged": 66, "device": 65,
    },
    "Combat": {
        "turret": 36, "lightning": 39, "bullets": 40, "bullets-plus": 41,
        "bullet-plus": 42, "bullseye": 43, "flame": 45, "spider": 49, "fighter": 52,
        "fist": 53, "crosshair": 112, "rifle": 117, "sword": 172, "skull": 170,
        "skull-horned": 171, "helm-spartan": 173, "knight": 77, "goblin": 78,
        "cavalry": 75, "valkyrie": 76,
    },
    "People": {
        "person": 83, "crowd": 80, "squad": 37, "portrait": 82, "king": 73, "hero": 74,
        "robot": 72, "walk": 79, "run": 47, "muscle": 71, "teleport": 46,
        "gauntlet": 81, "bandit": 119, "meeting": 131, "talks": 132, "handshake": 175,
    },
    "Medical": {
        "first-aid": 25, "medical-cross": 100, "cross-box": 102, "hospital": 87,
        "heart-plus": 86, "heart-minus": 85, "medic-up": 84, "medic-down": 124,
        "caduceus": 133,
    },
    "Places & cargo": {
        "supplies": 32, "hex-cargo": 50, "barrel": 90, "chest": 99, "chest-open": 89,
        "container": 126, "observatory": 88, "home": 107, "tavern": 104, "bunks": 142,
        "mess": 141, "cards": 143, "chef": 127, "shell": 48,
    },
    "Signals, orders & the map": {
        "radar": 33, "antenna": 34, "hourglass": 22, "flag": 23, "hand": 24,
        "wrench": 26, "shield": 27, "shield-plain": 106, "shield-broken": 109,
        "sitemap": 31, "folder": 92, "satellite": 93, "export": 94, "import": 95,
        "burst": 96, "wanted": 111, "helm-wheel": 110, "bishop": 108, "stop": 120,
        "bell": 145, "ship-sail": 146, "acorn": 147, "patrol-badge": 140,
        "tablet": 130, "phone": 134, "python": 144, "claws": 103, "tread": 14,
        "arrow-curve": 10, "zoom-in": 16, "chevrons-right": 18,
    },
    "Rank pips": {
        "rank-1": 116, "rank-2": 105, "rank-3": 98, "rank-4": 128, "rank-cone": 135,
        "rank-star": 91, "rank-down": 123, "rank-down-2": 122, "chevrons-circle": 38,
    },
    "Emblems": {
        "emblem-compass": 164, "emblem-diamond": 165, "emblem-hex": 166,
        "emblem-bars": 167, "emblem-axe": 168, "emblem-blade": 169, "laurel": 174,
    },
    "Shapes & widget furniture": {
        "square": 101, "square-outline": 121, "circle": 97, "circle-outline": 129,
        "expand": 154, "collapse": 155, "plus": 156, "minus": 157, "ban": 158,
        "menu": 137, "move": 136, "cursor": 118, "magnifier": 160,
        "magnifier-large": 161, "magnifier-thin": 162, "magnifier-small": 163,
        "arrow-up": 148, "arrow-right": 149, "arrow-down": 150, "arrow-left": 151,
        "rewind": 152, "forward": 153,
    },
}

ICON_INDEX = {name: idx for group in ICON_GROUPS.values() for name, idx in group.items()}

# --- what a thing MEANS, as opposed to what it looks like ------------------------
# A consumer asks for the meaning; the meaning points at a look. Re-point one of these
# (or override it from a mission) and every screen that draws it changes at once.
ICON_ALIAS = {
    # the quest log, which is what this was built for
    "quest.job": "wanted",            # work posted for someone to take
    "quest.objective": "flag",        # something the crew is to do
    "quest.beat": "talks",            # a moment they live through
    "quest.arc": "sitemap",           # the heading over a run of beats
    "quest.cue": "bell",              # a stage direction; fires unseen
    "quest.state": "square",          # the state pip, recolored per state
    # widget furniture, so the numbers can leave the drawing code
    "list.expand": "expand",
    "list.collapse": "collapse",
    "list.prev": "rewind",
    "list.next": "forward",
    "check.on": "square",
    "check.off": "square-outline",
}


ICON_DOMAIN = "icon"


def icon_resolve(name):
    """A name -> (icon_index, atlas_key). Exactly one of the two is set.

    Follows aliases first, so `quest.job` lands on whatever look it currently points at.
    An unknown name resolves to (None, None) and the caller draws nothing rather than
    guessing a glyph - a wrong icon is worse than a missing one.

    The atlas branch is what makes a custom sheet a drop-in later: register the look in
    the ICON DOMAIN (`gui_icon_add_atlas`, or `Kind: icon` in AMD) and it wins, with no
    change to anything that draws it.

    The domain is a GUARD, not ceremony. `ImageAtlas.all` is one process-wide dict, so
    without it any mission registering an image called `square` or `flag` - words no one
    would think twice about - would silently re-skin every icon meaning pointing there.
    Overriding a look has to be something you meant.
    """
    from .image import ImageAtlas
    seen = set()
    key = str(name).strip()
    while key in ICON_ALIAS and key not in seen:
        seen.add(key)
        key = ICON_ALIAS[key]
    claimed = ImageAtlas.qualify(key, ICON_DOMAIN)
    if claimed in ImageAtlas.all:        # a sheet deliberately claimed this look
        return None, claimed
    idx = ICON_INDEX.get(key)
    return (idx, None) if idx is not None else (None, None)


def icon_props(name, color=None, extra=None):
    """(kind, props) for a DIRECT engine send: kind is "icon" or "image", props the style
    string to hand it.

    Widget code goes through `gui_icon_name`, but the low-level renderers call
    `send_gui_icon` themselves with a hand-written property string - which is where the
    remaining magic numbers live. This lets them name what they draw without giving up
    the direct send, and an atlas-backed name comes back as an IMAGE because the engine
    has no icon concept for art it did not ship.

    Never raises and never returns nothing: an unknown name falls back to the built-in
    look, because a renderer mid-frame is the worst place to discover a typo.
    """
    index, atlas_key = icon_resolve(name)
    if atlas_key is not None:
        from .image import ImageAtlas
        props = ImageAtlas.all[atlas_key].get_props(color)
        return "image", props + (";" + extra if extra else "")
    parts = [f"icon_index:{index}"] if index is not None else []
    if color:
        parts.append(f"color:{color}")
    if extra:
        parts.append(extra.strip().strip(";"))
    return "icon", ";".join(parts) + ";"


def icon_names():
    """Every name that resolves - the built-ins plus the meanings. For lint, for a
    picker, and for anyone wondering what they may ask for."""
    return sorted(set(ICON_INDEX) | set(ICON_ALIAS))
