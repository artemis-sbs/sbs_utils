"""What a room NAME means, mechanically.

Roles are MECHANICS: `weapon`/`engine`/`sensor`/`shield` set a ship's
`system_max_damage` pools, and `beam`/`torpedo`/`impulse`/`warp`/`maneuver` set the damage
coefficients (`GRID_REFERENCE.md` s3). They must therefore NOT live in the grid theme -
a theme is a SKIN (colors and icons; `Retro` exists to re-skin the same ships), and roles
riding a skin would mean re-skinning changes what a ship can survive.

They also should not be retyped in every layout file. Measured across the shipped
interiors: **60 distinct room names, exactly one with more than one roleset** - `rec-room`,
53x `room,cabin,recreation` against one `...,gym` and one `...,brig`, both authoring
mistakes. Name -> roles is effectively a function, so repeating it per file buys nothing
and invites silent drift: one typo and that ship has a room contributing to no system
pool, with nothing to complain about.

So the ASCII layout format names a room and gets its roles from here::

    q: crew-quarters                    # roles from this registry
    p: plunder-hold / room,bay,cargo    # a new room type declares its own

ROLE ORDER IS SIGNIFICANT and this table preserves it. Icon and color resolve from the
LAST role that has a theme entry, so `room,bay,cargo` and `bay,cargo,room` can render
differently - under `Retro`, which defines a `room` icon, the reordered one would draw a
generic room instead of a cargo hold.

GENERATED from `data/grid_data.json` by the migration; hand-editing is fine but prefer
regenerating so the table keeps matching the shipped data.
"""

# name -> comma-separated roles, in significant order.
_ROOMS = {
    "aft-shield": "system,shield,aft",
    "airlock": "access,airlock",
    "astro-lab": "room,lab,astro",
    "beam": "system,weapon,beam",
    "beam-aft": "system,weapon,beam",
    "beam-fwd": "system,weapon,beam",
    "beam-port": "system,weapon,beam",
    "beam-port-aft": "system,weapon,beam",
    "beam-port-fwd": "system,weapon,beam",
    "beam-starboard": "system,weapon,beam",
    "beam-starboard-aft": "system,weapon,beam",
    "beam-starboard-fwd": "system,weapon,beam",
    "bio-lab": "room,lab,bio",
    "brig": "room,cabin,brig",
    "cargo": "room,bay,cargo",
    "cargo_hatch": "access,hatch",
    "computer": "room,computer",
    "conference-room": "room,cabin,conference",
    "crew-galley": "room,cabin,galley",
    "crew-mess": "room,cabin,mess",
    "crew-quarters": "room,cabin,quarters",
    "crews-mess": "room,cabin,mess",
    "fighter-bay": "room,bay,fighter",
    "fwd-shield": "system,shield,fwd",
    "galley": "room,cabin,galley",
    "gymnasium": "room,cabin,gym",
    "hyper-drive": "system,engine,hyper",
    "impulse": "system,engine,impulse",
    "jump-drive": "system,engine,jump",
    "maneuver": "system,engine,maneuver",
    "maneuvering": "system,engine,maneuver",
    "observation-lounge": "room,cabin,lounge",
    "officer-quarters": "room,cabin,quarters",
    "officers-galley": "room,cabin,galley",
    "officers-mess": "room,cabin,mess",
    "officers-quarters": "room,cabin,quarters",
    "passenger": "room,passenger,cabin",
    "passenger-mess": "room,cabin,mess",
    "passenger-quarters": "room,cabin,quarters",
    "physical-lab": "room,lab,physics",
    "physics-lab": "room,lab,physics",
    "priest-quarters": "room,priest,cabin",
    "production": "room,production",
    "ready_room": "room,cabin,recreation",
    "rec-room": "room,cabin,recreation",  # 53/55; other spellings are mistakes
    "recreation": "room,cabin,rec",
    "saloon": "room,cabin,saloon",
    "school": "room,cabin,school",
    "science-lab": "room,lab,bio",
    "sensors": "system,sensor",
    "shield": "system,shield,aft",
    "shrine": "room,shrine,cabin",
    "shuttle": "room,bay,shuttle",
    "shuttle-bay": "room,bay,shuttle",
    "sick-bay": "room,med,sickbay",
    "torp-tube": "system,weapon,torpedo",
    "torpedo-tube": "system,weapon,torpedo",
    "vip-quarters": "room,cabin,vip",
    "warp": "system,engine,warp",
    "workshop": "room,lab,workshop",
}


def grid_room_roles(name, default=None):
    """The roles a room name means, or ``default`` when it is not a known type."""
    if not name:
        return default
    return _ROOMS.get(str(name).strip().lower(), default)


def grid_room_register(name, roles):
    """Declare a room type at runtime, so a mod can add one without editing this file.

    Re-registering an existing name replaces it - a mod may deliberately redefine what a
    room means for its own ships.
    """
    if not name or not roles:
        return
    _ROOMS[str(name).strip().lower()] = str(roles).strip()


def grid_room_names():
    """Every known room type name."""
    return sorted(_ROOMS)


def grid_room_is_known(name):
    return bool(name) and str(name).strip().lower() in _ROOMS
