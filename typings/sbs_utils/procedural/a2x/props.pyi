def _add_sensor_beacons_to_cargo (o, count):
    """Fabricate ``count`` Sensor Beacons into a ship's cargo (the ``beacon_built`` list the
    LM fabrication uses), and signal the cargo UI to refresh. Returns the number added."""
def addto_object_property (obj, prop, value, index=None):
    """2.8 ``addto_object_property``: add ``value`` to a mapped property's current value."""
def copy_object_property (src, dst, prop):
    """2.8 ``copy_object_property``: copy a mapped property from ``src`` to ``dst``."""
def fleet_coeff_mapped (prop):
    """True if a 2.8 global difficulty property maps to a fleet coefficient."""
def gm_coords (gm=None):
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
    rather than raising inside a console handler."""
def object_property (obj, prop, index=None):
    """Read a 2.8-named property from ``obj`` (id / object / a2x_create_* handle).
    
    The read counterpart of :func:`set_object_property`, using the SAME 2.8->Cosmos
    mapping (engine attr, coordinate-flipped ``pos``, or ``data_set`` slot). Lets a port
    evaluate a 2.8 ``if_object_property`` / ``get_object_property`` for real instead of a
    hand-check. Returns the current value, or ``None`` if the property has no confirmed
    mapping or the object is gone (a caller comparing ``None`` fails safely / by hand)."""
def object_property_key (prop):
    """Return ``(data_set_key, index)`` for a data-backed 2.8 property, else ``None``.
    
    Useful for reads (``get_object_property`` / ``if_object_property``)."""
def object_property_mapped (prop):
    """True if this 2.8 property has a confirmed Cosmos mapping."""
def sensor_range (setting):
    """2.8 ``sensorSetting`` -> scan range in Cosmos units. 0 = unlimited (the whole map =
    100 km = map size); N>0 = 100/(3N) km = 100000/(3N) units (bigger N = smaller range)."""
def set_captain (obj, captain):
    """2.8 ``set_special`` captain personality (int) -> Cosmos inventory traits.
    
    Writes ``a2x_captain_trait`` (the personality name) and, where the personality
    implies it, ``a2x_surrender_chance`` -- both keys the LM comms addons already read
    (a2x carries no LM import; LM decides the behavior). ``-1`` leaves the ship as-is.
    Returns the trait name, or ``None`` if unmapped / the object is gone."""
def set_damcon_members (ship, team_index, value):
    """2.8 ``set_damcon_members(team_index, value)`` -> set a damcon team's HP.
    
    Cosmos models each of the three damcon teams as a single grid lifeform named ``DC1``..
    ``DC3`` with HP (max ``grid_get_max_hp()``, default 6). 2.8 ``value`` is the team's
    strength/HP (0 = downed .. 4 = full in the corpus); it maps to the team's HP, clamped
    to the Cosmos max. ``team_index`` 0..2 -> DC1..DC3. Ensures the ship's damcons exist
    first (spawning the standard trio if needed). Returns True if the HP was set."""
def set_fleet_coeff (which, value):
    """2.8 global ``nonPlayer*`` / ``player*`` difficulty -> per-ship coefficients.
    
    Applies ``value/100`` to the matching data_set coeff on every current NPC (or
    player) ship. NOTE: 2.8 applied these globally including to *future* spawns; this
    sets only ships that exist now -- re-apply after later spawns if needed.
    Returns the number of ships updated, or -1 if ``which`` is unknown."""
def set_fleet_property (index, prop, value):
    """2.8 ``set_fleet_property`` on a fleet index -> configure that fleet's formation.
    
    ``fleetSpacing`` / ``fleetMaxRadius`` map to the general ``fleet_spacing`` /
    ``fleet_max_radius`` formation-ring keys on the fleet AGENT (the LM scatter-formation
    brain reads them). The agent is found via any ``fleet_<index>`` ship's ``my_fleet_id``.
    Returns the number of fleet agents updated (0 if that fleet has no agent yet, or the
    property is unmapped)."""
def set_object_property (obj, prop, value, index=None):
    """Set a 2.8-named property on ``obj`` (id / object / a2x_create_* handle).
    
    Returns True if the property was mapped and set, False if it has no mapping."""
def set_relative_position (obj, ref, angle, distance):
    """2.8 ``set_relative_position``: move ``obj`` to a point ``distance`` from ``ref``
    at ``angle`` degrees (XZ plane).
    
    Approximate: ``angle`` is applied in world XZ; the 2.8 heading-relative nuance is
    left as a refinement. Returns True if both objects resolved."""
def set_sensor_setting_all (setting):
    """2.8 global ``sensorSetting`` (a nameless set_object_property) -> set every player
    ship's ``ship_base_scan_range`` to the corresponding range. Returns the count updated."""
def set_ship_power (obj, tier):
    """2.8 ``set_special`` ship power tier (int) -> scale the ship's shield + weapon
    upgrade coeffs.
    
    v2.4+ scheme: 0 upgraded (x1.25) / 1 overpowered (x1.6) / 2 underpowered (x0.7);
    ``-1`` leaves the ship as-is. Sets the same data_set coeffs :func:`set_fleet_coeff`
    uses, so it stacks with global difficulty. Returns the coeff applied, or ``None``."""
def set_ship_text (obj, name=None, race=None, ship_class=None, desc=None, scan_desc=None, hail=None):
    """2.8 ``set_ship_text``: set scan / name text on a ship.
    
    ``name``/``race``/``ship_class``/``desc`` map to ``name_tag`` / ``hull_origin`` /
    ``hull_name`` / ``long_description``. ``scan_desc`` and ``hail`` have no direct
    Cosmos data_set key and are ignored here (handle via science/comms if needed)."""
def set_side_value (obj, value):
    """2.8 ``set_side_value``: reassign an object's Cosmos side (a mid-mission defection).
    
    Maps the sideValue through :func:`a2x.sides.side_key` -- the same table
    ``a2x_declare_sides`` used -- so the object lands on a side whose diplomacy is
    already declared. Swaps the side role (so ``role(side)`` queries stay correct) and
    sets ``.side``.
    
    Diplomacy follows the side, not the object: reassigning a ship is enough to flip who
    shoots it. The combat-scope role (``raider``) is NOT touched -- a defector that
    should stop being a valid target for enemies-near style checks needs that role
    removed separately, the same way LegendaryMissions drops it on surrender."""
def set_special (obj, ability=None, on=True):
    """2.8 ``set_special`` ability -> a Cosmos LegendaryMissions elite ability.
    
    Engine abilities set the ``elite_*`` data_set flag; scripted abilities (cloak,
    warp, teleport, tractor, shield drain/vamp/scramble, eft) are attached by adding
    the ability role and scheduling ``handle_elite_abilities`` (the LM fleets addon
    driver). ``on=False`` (2.8 ``clear``) removes it. Returns the ability key, or
    ``None`` if unknown."""
def set_special_bits (obj, bits):
    """2.8 ``eliteAbilityBits`` / ``specialAbilityBits`` (a bit-sum) -> enable each named
    elite ability whose bit is set, via :func:`set_special`. Returns the count enabled."""
def set_to_gm_position (obj, gm):
    """2.8 ``set_to_gm_position``: move the GM-selected object to the GM's position.
    
    The Cosmos GM position is the gamemaster console ship (``COMMS_ORIGIN`` in the GM comms
    tree), which relocates to wherever the GM last clicked -- so copy its position onto
    ``obj``. Both are already in Cosmos space (no coord flip). Returns True if both resolved."""
def side_key (side_value):
    """2.8 ``sideValue`` -> the Cosmos side key for that faction.
    
    0/1/2 keep the readable legacy names (``neutral``/``enemy``/``friendly``); 3 and up
    get a synthesized ``side_N`` so an N-faction mission stays N factions. Values are
    NOT collapsed onto the three LegendaryMissions keys -- see the module docstring."""
def special_ability_mapped (ability):
    """True if a 2.8 set_special ability maps to a Cosmos elite ability."""
