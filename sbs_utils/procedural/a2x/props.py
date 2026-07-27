"""2.8 ``set_object_property`` -> Cosmos ``data_set`` / ``engine_object``.

2.8 property names differ from Cosmos data-set keys. This maps the high-confidence
subset (see ``docs/property_map.md`` in the arme2cosmos tool) so a port can set them
for real instead of leaving a TODO. Unmapped 2.8 properties return ``False`` so the
caller knows to handle them by hand.

Each entry is either ``("engine", attr)`` (an ``engine_object`` attribute) or
``("data", key, index)`` (a ``data_set`` slot).
"""

_MAP_SIZE = 100_000  # 2.8/Cosmos map size; X and Z mirror about it

# 2.8 property -> Cosmos target. Entry forms:
#   ("engine", attr)        -> engine_object.<attr>
#   ("data", key, index)    -> data_set slot
#   ("pos", axis, flip)     -> engine_object.pos.<axis>; flip=True mirrors (X/Z)
#   ("obj", attr)           -> a space_object attribute (e.g. cur_speed; physics-driven)
_PROP = {
    # position -> engine_object.pos with the 2.8->Cosmos coordinate flip (X,Z mirror)
    "positionX": ("pos", "x", True),
    "positionY": ("pos", "y", False),
    "positionZ": ("pos", "z", True),
    # absolute facing: 2.8 `angle` (yaw, radians, CW-from-south) -> the engine rotation
    # quaternion. Handled by the ("quat", ...) branch below via a2x.coords (Cosmos yaw =
    # pi - angle; the mirror also reverses the turn sense for addto).
    "angle": ("quat", "yaw", 0),
    # 2.8 `roll` (radians about the forward axis) -> a roll composed onto the rotation
    # quaternion (a2x.coords.set_roll; the mirror flips the sense, pi is sign-invariant).
    "roll": ("roll", "roll", 0),
    # 2.8 `pitch` (nose up/down) -> a pitch composed onto the quaternion (a2x.coords.set_pitch;
    # radians, but corpus values > pi are treated as degrees).
    "pitch": ("pitch", "pitch", 0),
    # spin rates -> engine_object steering (as the HTBM port does)
    "angleDelta": ("engine", "steer_yaw"),
    "rollDelta": ("engine", "steer_roll"),
    "pitchDelta": ("engine", "steer_pitch"),
    # turn/steer rate -> the data_set key the engine steering ACTUALLY reads (turn_rate).
    # (Was "turnRate", a dead key the engine never reads; drives NPC + player steering.)
    "turnRate": ("data", "turn_rate", 0),
    # NPC top-speed coefficient: cruise = throttle * 36 u/s * speed_coeff (0-1). 2.8
    # topSpeed values are already 0-1 coeffs, so this is 1:1. NOTE: applies to NPC hulls
    # only -- Cosmos player top speed is fixed (playerThrottle * 180, no speed_coeff), so
    # setting this on a PLAYER is a no-op (players have no per-hull top-speed lever).
    "topSpeed": ("data", "speed_coeff", 0),
    # current speed (read): a space_object attribute, physics-driven (effectively read-only).
    "currentRealSpeed": ("obj", "cur_speed"),
    # 2.8 push radius = the object's exclusion (collision) radius (a space_object property).
    "pushRadius": ("obj", "exclusion_radius"),
    # scalar data_set values
    "throttle": ("data", "throttle", 0),
    "artScale": ("data", "local_scale_coeff", 0),
    "energy": ("data", "energy", 0),
    "hasSurrendered": ("data", "surrender_flag", 0),
    "shieldsOn": ("data", "shields_raised_flag", 0),
    # shields (array: 0 = front, 1 = back)
    # a station has a SINGLE shield -> the first slot (same as a ship's front shield).
    "shieldState": ("data", "shield_val", 0),
    "shieldStateFront": ("data", "shield_val", 0),
    "shieldStateBack": ("data", "shield_val", 1),
    "shieldMaxStateFront": ("data", "shield_max_val", 0),
    "shieldMaxStateBack": ("data", "shield_max_val", 1),
    # torpedo stores / ammo counts -> <Type>_NUM
    "missileStoresNuke": ("data", "Nuke_NUM", 0),
    "missileStoresHoming": ("data", "Homing_NUM", 0),
    "missileStoresMine": ("data", "Mine_NUM", 0),
    "missileStoresEMP": ("data", "EMP_NUM", 0),
    "countNuke": ("data", "Nuke_NUM", 0),
    "countHoming": ("data", "Homing_NUM", 0),
    "countMine": ("data", "Mine_NUM", 0),
    "countEMP": ("data", "EMP_NUM", 0),
    # PShock (plasma shock) and Tag are first-class LM torpedo types now; ECM ~ EMP.
    "missileStoresPShock": ("data", "PShock_NUM", 0),
    "missileStoresTag": ("data", "Tag_NUM", 0),
    "missileStoresECM": ("data", "EMP_NUM", 0),
    "countShk": ("data", "PShock_NUM", 0),
    # Beacon is now a first-class LM ordnance type (fabricate-only); map its 2.8 store.
    "missileStoresBeacon": ("data", "Beacon_NUM", 0),
    "countBea": ("data", "Beacon_NUM", 0),
    # 2.8 Probe has no Cosmos torpedo type -> treat it as a Sensor Beacon (the passive
    # sensor-relay beacon kind). SET writes the loadable count (Beacon_NUM); ADDTO fabricates
    # that many sensor beacons into cargo (beacon_built) -- adding stock, not loaded rounds.
    "missileStoresProbe": ("probe", "Beacon_NUM", 0),
    "countProbe": ("probe", "Beacon_NUM", 0),
    # behaviour switches read by the LM damage/comms addons off the object's inventory
    # (a2x sets the value; LM decides what to do with it -- a2x carries no LM import).
    "surrenderChance": ("inv", "a2x_surrender_chance"),   # 0-100
    "tauntImmunityIndex": ("inv", "a2x_taunt_immunity"),  # 0 none / 1 temp / 2 perm
    # 2.8 pirate docking reputation (v2.7.1+): only meaningful if the player ship has the
    # "pirate" role. 0 = stations refuse to let the pirate dock, >0 = they allow it. The LM
    # docking addon reads this off the player inventory (a2x carries no LM import). Both the
    # plural corpus spelling and the singular doc spelling map to the same key.
    "pirateRepWithStations": ("inv", "a2x_pirate_rep"),
    "pirateRepWithStation": ("inv", "a2x_pirate_rep"),
    # 2.8 age (on wrecks/objects): Cosmos has no object-age mechanic beyond the monster
    # stage system, and these are plain objects (WRECKs were a monster type in 2.8, but in
    # Cosmos they are ordinary objects). Keep the datum on the inventory so science flavor
    # text can surface it later; nothing reads it yet.
    "age": ("inv", "a2x_age"),
    # 2.8 nebulaIsOpaque: whether the nebula slows ships. Cosmos nebulae throttle-limit via
    # the max_throttle data_set key (default 2.0); 0 = no limit. Opaque -> keep the limit,
    # not opaque -> 0. ("bool_data" sets the key to [scale] when truthy, else 0.)
    "nebulaIsOpaque": ("bool_data", "max_throttle", 2.0),
    # 2.8 sensorSetting (int): the ship's sensor/scan range. 0 = unlimited (100 km = the
    # whole map); N>0 = 100/(3N) km, i.e. 100000/(3N) Cosmos units (bigger N = smaller
    # range). -> the ship_base_scan_range data_set key. ("sensor" applies that progression.)
    "sensorSetting": ("sensor", "ship_base_scan_range", 0),
    # 2.8 warpState is really the throttle: 0-4 maps to Cosmos throttle 1-5 (+1 offset).
    "warpState": ("warp", "throttle", 0),
    # 2.8 canBuild: toggle a station's ability to build. LM's build console reads
    # a2x_can_build off the station inventory (0 = cannot build); a2x carries no LM import.
    "canBuild": ("inv", "a2x_can_build"),
}

# 2.8 engineering exposes 8 named systems; Cosmos SHPSYS has 4 slots
# (WEAPONS=0, ENGINES=1, SENSORS=2, SHIELDS=3). Collapse 8 -> 4. This is lossy:
# systems that share a slot (Beam+Torpedo -> WEAPONS; Impulse+Warp+Turning -> ENGINES;
# Front+Back shield -> SHIELDS) overwrite each other, later-write-wins. Tactical == the
# sensor system. NOTE: these are usually set on NPCs; Cosmos NPCs don't run the player
# engineering model, so systemCurEnergy on an NPC is a harmless no-op, and heat/damage
# are approximate -- fine for a scaffold.
_SHPSYS = {
    "Beam": 0, "Torpedo": 0,                  # WEAPONS
    "Turning": 1, "Impulse": 1, "Warp": 1,    # ENGINES (maneuver / impulse / jump)
    "Tactical": 2,                            # SENSORS
    "FrontShield": 3, "BackShield": 3,        # SHIELDS
}
for _sys, _idx in _SHPSYS.items():
    _PROP[f"systemCurHeat{_sys}"] = ("data", "system_cur_heat", _idx)   # 0.0-1.0
    _PROP[f"systemDamage{_sys}"] = ("data", "system_damage", _idx)      # damaged-node count
    _PROP[f"systemCurEnergy{_sys}"] = ("data", "eng_control_value", _idx)  # 0.0-1.0 slider


# 2.8 global difficulty knobs ("nonPlayer" = all NPC ships) -> per-ship Cosmos
# coefficients, applied across the fleet. Value 100 = baseline, so coeff = value/100.
_FLEET_COEFF = {
    "nonPlayerSpeed": ("__npc__", ["speed_coeff"]),
    "nonPlayerShield": ("__npc__", ["all_shield_upgrade_coeff"]),
    "nonPlayerWeapon": ("__npc__", ["all_beam_upgrade_coeff", "all_tube_upgrade_coeff"]),
    "playerShields": ("__player__", ["all_shield_upgrade_coeff"]),
    "playerWeapon": ("__player__", ["all_beam_upgrade_coeff"]),
}


def fleet_coeff_mapped(prop):
    """True if a 2.8 global difficulty property maps to a fleet coefficient."""
    return prop in _FLEET_COEFF


def set_fleet_coeff(which, value):
    """2.8 global ``nonPlayer*`` / ``player*`` difficulty -> per-ship coefficients.

    Applies ``value/100`` to the matching data_set coeff on every current NPC (or
    player) ship. NOTE: 2.8 applied these globally including to *future* spawns; this
    sets only ships that exist now -- re-apply after later spawns if needed.
    Returns the number of ships updated, or -1 if ``which`` is unknown.
    """
    spec = _FLEET_COEFF.get(which)
    if spec is None:
        return -1
    role_name, keys = spec
    coeff = value / 100.0
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_space_object_list

    n = 0
    for o in to_space_object_list(role(role_name)):
        for k in keys:
            o.data_set.set(k, coeff, 0)
        n += 1
    return n


# 2.8 sideValue -> Cosmos side key. Lives in a2x.sides (one table, so a runtime
# set_side_value can only land on a side a2x_declare_sides actually declared).
from .sides import side_key


# 2.8 set_fleet_property -> the general LM fleet-formation keys the scatter-formation brain
# reads off the fleet agent (brain_fleet.mast). Other 2.8 fleet properties are unmapped.
_FLEET_PROP = {"fleetSpacing": "fleet_spacing", "fleetMaxRadius": "fleet_max_radius"}


def set_fleet_property(index, prop, value):
    """2.8 ``set_fleet_property`` on a fleet index -> configure that fleet's formation.

    ``fleetSpacing`` / ``fleetMaxRadius`` map to the general ``fleet_spacing`` /
    ``fleet_max_radius`` formation-ring keys on the fleet AGENT (the LM scatter-formation
    brain reads them). The agent is found via any ``fleet_<index>`` ship's ``my_fleet_id``.
    Returns the number of fleet agents updated (0 if that fleet has no agent yet, or the
    property is unmapped).
    """
    key = _FLEET_PROP.get(prop)
    if key is None:
        return 0
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_object_list
    from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value

    agents = set()
    for ship in to_object_list(role(f"fleet_{index}")):
        fid = get_inventory_value(ship, "my_fleet_id", None)
        if fid is not None:
            agents.add(fid)
    for fid in agents:
        set_inventory_value(fid, key, value)
    return len(agents)


def set_side_value(obj, value):
    """2.8 ``set_side_value``: reassign an object's Cosmos side (a mid-mission defection).

    Maps the sideValue through :func:`a2x.sides.side_key` -- the same table
    ``a2x_declare_sides`` used -- so the object lands on a side whose diplomacy is
    already declared. Swaps the side role (so ``role(side)`` queries stay correct) and
    sets ``.side``.

    Diplomacy follows the side, not the object: reassigning a ship is enough to flip who
    shoots it. The combat-scope role (``raider``) is NOT touched -- a defector that
    should stop being a valid target for enemies-near style checks needs that role
    removed separately, the same way LegendaryMissions drops it on surrender.
    """
    from sbs_utils.procedural.roles import add_role, remove_role
    from sbs_utils.procedural.query import to_space_object, to_id

    o = to_space_object(obj)
    if o is None:
        return False
    new_side = side_key(value)
    oid = to_id(obj)
    old = o.side
    if old and old != new_side:
        remove_role(oid, old)
    add_role(oid, new_side)
    o.side = new_side
    return True


def object_property_mapped(prop):
    """True if this 2.8 property has a confirmed Cosmos mapping."""
    return prop in _PROP


def object_property_key(prop):
    """Return ``(data_set_key, index)`` for a data-backed 2.8 property, else ``None``.

    Useful for reads (``get_object_property`` / ``if_object_property``).
    """
    m = _PROP.get(prop)
    return (m[1], m[2]) if m and m[0] == "data" else None


def set_relative_position(obj, ref, angle, distance):
    """2.8 ``set_relative_position``: move ``obj`` to a point ``distance`` from ``ref``
    at ``angle`` degrees (XZ plane).

    Approximate: ``angle`` is applied in world XZ; the 2.8 heading-relative nuance is
    left as a refinement. Returns True if both objects resolved.
    """
    import math
    from sbs_utils.procedural.query import to_space_object

    o, r = to_space_object(obj), to_space_object(ref)
    if o is None or r is None:
        return False
    rp = r.engine_object.pos
    rad = math.radians(float(angle))
    o.engine_object.pos.x = rp.x + float(distance) * math.sin(rad)
    o.engine_object.pos.y = rp.y
    o.engine_object.pos.z = rp.z + float(distance) * math.cos(rad)
    return True


def addto_object_property(obj, prop, value, index=None):
    """2.8 ``addto_object_property``: add ``value`` to a mapped property's current value."""
    from sbs_utils.procedural.query import to_space_object

    m = _PROP.get(prop)
    if m is None:
        return False
    o = to_space_object(obj)
    if o is None:
        return False
    if m[0] == "quat":
        from . import coords
        coords.add_angle(o, value)
    elif m[0] == "probe":
        # 2.8 addto Probe -> ADD stock: fabricate that many Sensor Beacons into cargo.
        _add_sensor_beacons_to_cargo(o, value)
    elif m[0] == "engine":
        setattr(o.engine_object, m[1], (getattr(o.engine_object, m[1], 0) or 0) + value)
    elif m[0] == "pos":
        # a 2.8 delta on a mirrored axis is negated in Cosmos space
        delta = -value if m[2] else value
        setattr(o.engine_object.pos, m[1], getattr(o.engine_object.pos, m[1]) + delta)
    elif m[0] == "obj":
        setattr(o, m[1], (getattr(o, m[1], 0) or 0) + value)  # a space_object attr
    elif m[0] == "inv":
        from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
        set_inventory_value(o, m[1], (get_inventory_value(o, m[1]) or 0) + value)
    else:
        idx = m[2] if index is None else index
        o.data_set.set(m[1], (o.data_set.get(m[1], idx) or 0) + value, idx)
    return True


def copy_object_property(src, dst, prop):
    """2.8 ``copy_object_property``: copy a mapped property from ``src`` to ``dst``."""
    from sbs_utils.procedural.query import to_space_object

    m = _PROP.get(prop)
    if m is None:
        return False
    so, do = to_space_object(src), to_space_object(dst)
    if so is None or do is None:
        return False
    if m[0] == "quat":
        from . import coords
        coords.copy_angle(so, do)
    elif m[0] == "engine":
        setattr(do.engine_object, m[1], getattr(so.engine_object, m[1], 0))
    elif m[0] == "pos":
        # both already in Cosmos space -> copy the axis directly (no flip)
        setattr(do.engine_object.pos, m[1], getattr(so.engine_object.pos, m[1]))
    elif m[0] == "obj":
        setattr(do, m[1], getattr(so, m[1], 0))  # a space_object attr
    elif m[0] == "inv":
        from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
        set_inventory_value(do, m[1], get_inventory_value(so, m[1]))
    else:
        do.data_set.set(m[1], so.data_set.get(m[1], m[2]), m[2])
    return True


# 2.8 set_ship_text field -> Cosmos data_set scan-text key.
_SHIP_TEXT = {
    "name": "name_tag", "race": "hull_origin", "ship_class": "hull_name",
    "desc": "long_description",
}


def set_to_gm_position(obj, gm):
    """2.8 ``set_to_gm_position``: move the GM-selected object to the GM's position.

    The Cosmos GM position is the gamemaster console ship (``COMMS_ORIGIN`` in the GM comms
    tree), which relocates to wherever the GM last clicked -- so copy its position onto
    ``obj``. Both are already in Cosmos space (no coord flip). Returns True if both resolved.
    """
    from sbs_utils.procedural.query import to_space_object

    o = to_space_object(obj)
    g = to_space_object(gm)
    if o is None or g is None:
        return False
    gp = g.engine_object.pos
    o.engine_object.pos.x = gp.x
    o.engine_object.pos.y = gp.y
    o.engine_object.pos.z = gp.z
    return True


def gm_coords(gm=None):
    """The GM's position expressed in **2.8 coordinates** -- an (x, y, z) tuple.

    ``gm`` defaults to whichever agent holds the ``gamemaster`` role, so this works outside
    a GM comms handler too -- 2.8 uses ``use_gm_position`` in ordinary events as well, where
    there is no ``COMMS_ORIGIN`` to hand. Pass the origin explicitly inside a GM button if
    a mission runs more than one GM console and you need the one that clicked.

    2.8 lets a GM-button command spawn "where the GM is" (``use_gm_position="yes"``) rather
    than at fixed coordinates; the Cosmos equivalent is the gamemaster console ship, which
    relocates to wherever the GM last clicked (see :func:`set_to_gm_position`).

    It hands back 2.8 coordinates, not Cosmos ones, so the result drops straight into the
    ``a2x_create_*`` helpers -- which flip every position they are given. The flip mirrors
    about the map centre and is its own inverse, so converting the live Cosmos position
    "back" is the same operation, and the round trip lands exactly on the GM.

    Returns ``(0, 0, 0)`` if the GM cannot be resolved, which spawns at the 2.8 origin
    rather than raising inside a console handler.
    """
    from sbs_utils.procedural.query import to_space_object, to_id_list
    from sbs_utils.procedural.roles import role
    from .coords import pos

    if gm is None:
        ids = to_id_list(role("gamemaster"))
        gm = ids[0] if ids else None
    g = to_space_object(gm) if gm is not None else None
    if g is None:
        return (0, 0, 0)
    p = g.engine_object.pos
    v = pos(p.x, p.y, p.z)   # same mirror, applied the other way
    return (v.x, v.y, v.z)


def set_ship_text(obj, name=None, race=None, ship_class=None, desc=None,
                 scan_desc=None, hail=None):
    """2.8 ``set_ship_text``: set scan / name text on a ship.

    ``name``/``race``/``ship_class``/``desc`` map to ``name_tag`` / ``hull_origin`` /
    ``hull_name`` / ``long_description``. ``scan_desc`` and ``hail`` have no direct
    Cosmos data_set key and are ignored here (handle via science/comms if needed).
    """
    from sbs_utils.procedural.query import to_space_object

    o = to_space_object(obj)
    if o is None:
        return False
    for field, val in (("name", name), ("race", race),
                       ("ship_class", ship_class), ("desc", desc)):
        if val is not None:
            o.data_set.set(_SHIP_TEXT[field], val, 0)
    return True


# 2.8 set_special ability -> Cosmos LegendaryMissions elite-ability key. Five are
# engine "blob flag" abilities (a data_set value); the rest are scripted in the LM
# fleets addon (a role + the handle_elite_abilities task drives them).
_ELITE_ENGINE = {
    "Stealth": "elite_main_scn_invis",   # invisible to main-screen 2d radar
    "LowVis": "elite_low_vis",           # restricted 2d radar visibility
    "Drones": "elite_drone_launcher",
    "AntiMine": "elite_anti_mine",
    "AntiTorp": "elite_anti_torpedo",
}
_ELITE_SCRIPT = {
    "Cloak": "elite/cloak",
    "HET": "elite/eft",
    "Warp": "elite/warp",
    "Teleport": "elite/jump/forward",
    "TeleBack": "elite/jump/back",
    "Tractor": "elite/tractor",
    "ShldDrain": "elite/shield_drain",
    "ShldVamp": "elite/shield_vamp",
    "ShldReset": "elite/shield_scramble",
}
_ELITE_ABILITY = {**_ELITE_ENGINE, **_ELITE_SCRIPT}

# 2.8 eliteAbilityBits / specialAbilityBits: a bit-sum of the ships' elite abilities.
_ELITE_BITS = {
    1: "Stealth", 2: "LowVis", 4: "Cloak", 8: "HET", 16: "Warp", 32: "Teleport",
    64: "Tractor", 128: "Drones", 256: "AntiMine", 512: "AntiTorp",
    1024: "ShldDrain", 2048: "ShldVamp", 4096: "TeleBack", 8192: "ShldReset",
}


def set_special_bits(obj, bits):
    """2.8 ``eliteAbilityBits`` / ``specialAbilityBits`` (a bit-sum) -> enable each named
    elite ability whose bit is set, via :func:`set_special`. Returns the count enabled."""
    bits = int(bits)
    n = 0
    for bit, name in _ELITE_BITS.items():
        if bits & bit:
            set_special(obj, name, on=True)
            n += 1
    return n


def special_ability_mapped(ability):
    """True if a 2.8 set_special ability maps to a Cosmos elite ability."""
    return ability in _ELITE_ABILITY


def set_special(obj, ability=None, on=True):
    """2.8 ``set_special`` ability -> a Cosmos LegendaryMissions elite ability.

    Engine abilities set the ``elite_*`` data_set flag; scripted abilities (cloak,
    warp, teleport, tractor, shield drain/vamp/scramble, eft) are attached by adding
    the ability role and scheduling ``handle_elite_abilities`` (the LM fleets addon
    driver). ``on=False`` (2.8 ``clear``) removes it. Returns the ability key, or
    ``None`` if unknown.
    """
    key = _ELITE_ABILITY.get(ability)
    if key is None:
        return None
    from sbs_utils.procedural.roles import add_role, remove_role
    from sbs_utils.procedural.query import to_id, to_space_object, set_data_set_value
    from sbs_utils.procedural.execution import task_schedule

    if to_space_object(obj) is None:
        return None
    oid = to_id(obj)
    engine = key in _ELITE_ENGINE.values()
    if on:
        if engine:
            set_data_set_value(oid, key, 1)
        add_role(oid, key)
        task_schedule("handle_elite_abilities", {"ELITE_ID": oid})
    else:
        if engine:
            set_data_set_value(oid, key, 0)
        remove_role(oid, key)
    return key


# --- 2.8 set_special ship/captain form (no `ability`): a power tier + a captain
# personality, e.g. <set_special name="X" ship="2" captain="1"/>. Both are enumerated
# ints, not ability names. a2x writes inventory/data values the LM comms + fleets
# addons already read (surrender chance / captain trait) plus a ship power coeff; it
# never imports LM. -1 means "leave unchanged" for both.

# captain personality (2.8: -1 nothing / 0 cowardly / 1 brave / 2 bombastic /
# 3 seething / 4 duplicitous / 5 exceptional) -> a trait name LM acts on.
_CAPTAIN = {
    0: "cowardly",     # readily surrenders
    1: "brave",        # will not surrender
    2: "bombastic",    # sends taunts to the players
    3: "seething",     # too angry to surrender; starts enraged
    4: "duplicitous",  # fake-surrenders, then re-engages
    5: "exceptional",  # fights harder; resists surrender
}
# the a2x_surrender_chance (0-100, centered 50) a personality implies. Reuses the exact
# key enemy_surrender.mast already reads (0 => never surrender / hide the button). None =
# leave the surrender chance alone (bombastic/duplicitous still surrender normally).
_CAPTAIN_SURRENDER = {
    "cowardly": 90,     # much readier to give up
    "brave": 0,         # never (existing "0 == never" path)
    "seething": 0,      # never
    "exceptional": 20,  # resists
}

# ship power tier. 2.8 v2.4+ scheme (these are 2.8 missions): 0 upgraded / 1 overpowered
# / 2 underpowered; -1 = leave. -> a multiplier on the ship's shield + weapon upgrade
# coeffs (same data_set keys set_fleet_coeff uses). (Pre-2.4 used a different 0..3 scheme;
# not expected in 2.8 corpora.)
_SHIP_POWER = {0: 1.25, 1: 1.6, 2: 0.7}
_SHIP_POWER_KEYS = ["all_shield_upgrade_coeff", "all_beam_upgrade_coeff",
                    "all_tube_upgrade_coeff"]


def set_captain(obj, captain):
    """2.8 ``set_special`` captain personality (int) -> Cosmos inventory traits.

    Writes ``a2x_captain_trait`` (the personality name) and, where the personality
    implies it, ``a2x_surrender_chance`` -- both keys the LM comms addons already read
    (a2x carries no LM import; LM decides the behavior). ``-1`` leaves the ship as-is.
    Returns the trait name, or ``None`` if unmapped / the object is gone.
    """
    trait = _CAPTAIN.get(int(captain))
    if trait is None:
        return None
    from sbs_utils.procedural.query import to_space_object
    from sbs_utils.procedural.inventory import set_inventory_value

    o = to_space_object(obj)
    if o is None:
        return None
    set_inventory_value(o, "a2x_captain_trait", trait)
    sc = _CAPTAIN_SURRENDER.get(trait)
    if sc is not None:
        set_inventory_value(o, "a2x_surrender_chance", sc)
    # bombastic (proactive taunts) and seething (starts enraged) need an active driver;
    # cowardly/brave/exceptional are fully covered by the surrender chance above, and
    # duplicitous acts at surrender time. Schedule the LM driver BY NAME so a2x stays
    # LM-free (same feature-detection pattern as set_special -> handle_elite_abilities).
    if trait in ("bombastic", "seething"):
        from sbs_utils.procedural.query import to_id
        from sbs_utils.procedural.execution import task_schedule
        task_schedule("a2x_captain_driver", {"CAP_ID": to_id(o)})
    return trait


def set_ship_power(obj, tier):
    """2.8 ``set_special`` ship power tier (int) -> scale the ship's shield + weapon
    upgrade coeffs.

    v2.4+ scheme: 0 upgraded (x1.25) / 1 overpowered (x1.6) / 2 underpowered (x0.7);
    ``-1`` leaves the ship as-is. Sets the same data_set coeffs :func:`set_fleet_coeff`
    uses, so it stacks with global difficulty. Returns the coeff applied, or ``None``.
    """
    coeff = _SHIP_POWER.get(int(tier))
    if coeff is None:
        return None
    from sbs_utils.procedural.query import to_space_object

    o = to_space_object(obj)
    if o is None:
        return None
    for k in _SHIP_POWER_KEYS:
        o.data_set.set(k, coeff, 0)
    return coeff


def set_damcon_members(ship, team_index, value):
    """2.8 ``set_damcon_members(team_index, value)`` -> set a damcon team's HP.

    Cosmos models each of the three damcon teams as a single grid lifeform named ``DC1``..
    ``DC3`` with HP (max ``grid_get_max_hp()``, default 6). 2.8 ``value`` is the team's
    strength/HP (0 = downed .. 4 = full in the corpus); it maps to the team's HP, clamped
    to the Cosmos max. ``team_index`` 0..2 -> DC1..DC3. Ensures the ship's damcons exist
    first (spawning the standard trio if needed). Returns True if the HP was set.
    """
    from sbs_utils.procedural.query import to_id
    from sbs_utils.procedural.internal_damage import (
        grid_restore_damcons, grid_set_hp, grid_get_max_hp)
    from sbs_utils.helpers import FrameContext

    idx = int(team_index)
    if idx < 0 or idx > 2:
        return False
    ship_id = to_id(ship)
    sbs = FrameContext.context.sbs
    hm = sbs.get_hull_map(ship_id)
    if hm is None:
        return False
    name = f"DC{idx + 1}"
    go = hm.get_grid_object_by_name(name)
    if go is None:
        grid_restore_damcons(ship_id)   # create the standard DC1..DC3
        go = hm.get_grid_object_by_name(name)
    if go is None:
        return False
    hp = max(0, min(int(round(float(value))), grid_get_max_hp()))
    grid_set_hp(ship_id, go.unique_ID, hp)
    return True


def sensor_range(setting):
    """2.8 ``sensorSetting`` -> scan range in Cosmos units. 0 = unlimited (the whole map =
    100 km = map size); N>0 = 100/(3N) km = 100000/(3N) units (bigger N = smaller range)."""
    sv = int(setting)
    return float(_MAP_SIZE) if sv <= 0 else _MAP_SIZE / (3.0 * sv)


def set_sensor_setting_all(setting):
    """2.8 global ``sensorSetting`` (a nameless set_object_property) -> set every player
    ship's ``ship_base_scan_range`` to the corresponding range. Returns the count updated."""
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_space_object_list

    rng = sensor_range(setting)
    n = 0
    for o in to_space_object_list(role("__player__")):
        o.data_set.set("ship_base_scan_range", rng, 0)
        n += 1
    return n


def _add_sensor_beacons_to_cargo(o, count):
    """Fabricate ``count`` Sensor Beacons into a ship's cargo (the ``beacon_built`` list the
    LM fabrication uses), and signal the cargo UI to refresh. Returns the number added."""
    from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
    from sbs_utils.procedural.query import to_id

    n_add = int(round(float(count)))
    if n_add <= 0:
        return 0
    built = get_inventory_value(o, "beacon_built", []) or []
    built.extend({"kind": "sensor"} for _ in range(n_add))
    set_inventory_value(o, "beacon_built", built)
    try:
        from sbs_utils.procedural.signal import signal_emit
        signal_emit("item_changed", {"holder_id": to_id(o)})
    except Exception:
        pass   # cargo is added even if the UI-refresh signal isn't wired
    return n_add


def set_object_property(obj, prop, value, index=None):
    """Set a 2.8-named property on ``obj`` (id / object / a2x_create_* handle).

    Returns True if the property was mapped and set, False if it has no mapping.
    """
    from sbs_utils.procedural.query import to_space_object

    m = _PROP.get(prop)
    if m is None:
        return False
    o = to_space_object(obj)
    if o is None:
        return False
    if m[0] == "quat":
        from . import coords
        coords.set_angle(o, value)
    elif m[0] == "roll":
        from . import coords
        coords.set_roll(o, value)
    elif m[0] == "pitch":
        from . import coords
        coords.set_pitch(o, value)
    elif m[0] == "bool_data":
        # boolean 2.8 flag -> a data_set key: [scale] when truthy, else 0 (e.g. nebulaIsOpaque
        # -> max_throttle 2.0/0). m[2] carries the truthy value.
        o.data_set.set(m[1], m[2] if value else 0.0, 0)
    elif m[0] == "sensor":
        # 2.8 sensorSetting -> scan range (units): 0 = unlimited (map size); N>0 = 100000/(3N).
        o.data_set.set(m[1], sensor_range(value), 0)
    elif m[0] == "probe":
        # 2.8 Probe store == the loadable Sensor-Beacon count (Beacon_NUM data_set).
        o.data_set.set(m[1], value, 0)
    elif m[0] == "warp":
        # 2.8 warpState 0-4 -> throttle 1-5 (+1 offset)
        o.data_set.set(m[1], int(round(float(value))) + 1, 0)
    elif m[0] == "engine":
        setattr(o.engine_object, m[1], value)
    elif m[0] == "pos":
        setattr(o.engine_object.pos, m[1], (_MAP_SIZE - value) if m[2] else value)
    elif m[0] == "obj":
        setattr(o, m[1], value)  # a physics-driven space_object attr; may be overwritten
    elif m[0] == "inv":
        from sbs_utils.procedural.inventory import set_inventory_value
        set_inventory_value(o, m[1], value)  # LM addon reads this off the inventory
    else:
        o.data_set.set(m[1], value, m[2] if index is None else index)
    return True


def object_property(obj, prop, index=None):
    """Read a 2.8-named property from ``obj`` (id / object / a2x_create_* handle).

    The read counterpart of :func:`set_object_property`, using the SAME 2.8->Cosmos
    mapping (engine attr, coordinate-flipped ``pos``, or ``data_set`` slot). Lets a port
    evaluate a 2.8 ``if_object_property`` / ``get_object_property`` for real instead of a
    hand-check. Returns the current value, or ``None`` if the property has no confirmed
    mapping or the object is gone (a caller comparing ``None`` fails safely / by hand).
    """
    from sbs_utils.procedural.query import to_space_object

    m = _PROP.get(prop)
    if m is None:
        return None
    o = to_space_object(obj)
    if o is None:
        return None
    if m[0] == "quat":
        from . import coords
        return coords.get_angle(o)
    if m[0] in ("probe", "sensor", "warp"):
        return o.data_set.get(m[1], m[2])   # the data_set count/value these kinds write
    if m[0] == "engine":
        return getattr(o.engine_object, m[1])
    if m[0] == "pos":
        raw = getattr(o.engine_object.pos, m[1])
        return (_MAP_SIZE - raw) if m[2] else raw  # un-flip (flip is its own inverse)
    if m[0] == "obj":
        return getattr(o, m[1], None)
    if m[0] == "inv":
        from sbs_utils.procedural.inventory import get_inventory_value
        return get_inventory_value(o, m[1])
    return o.data_set.get(m[1], m[2] if index is None else index)
