def addto_object_property (obj, prop, value, index=None):
    """2.8 ``addto_object_property``: add ``value`` to a mapped property's current value."""
def copy_object_property (src, dst, prop):
    """2.8 ``copy_object_property``: copy a mapped property from ``src`` to ``dst``."""
def fleet_coeff_mapped (prop):
    """True if a 2.8 global difficulty property maps to a fleet coefficient."""
def object_property_key (prop):
    """Return ``(data_set_key, index)`` for a data-backed 2.8 property, else ``None``.
    
    Useful for reads (``get_object_property`` / ``if_object_property``)."""
def object_property_mapped (prop):
    """True if this 2.8 property has a confirmed Cosmos mapping."""
def set_fleet_coeff (which, value):
    """2.8 global ``nonPlayer*`` / ``player*`` difficulty -> per-ship coefficients.
    
    Applies ``value/100`` to the matching data_set coeff on every current NPC (or
    player) ship. NOTE: 2.8 applied these globally including to *future* spawns; this
    sets only ships that exist now -- re-apply after later spawns if needed.
    Returns the number of ships updated, or -1 if ``which`` is unknown."""
def set_object_property (obj, prop, value, index=None):
    """Set a 2.8-named property on ``obj`` (id / object / a2x_create_* handle).
    
    Returns True if the property was mapped and set, False if it has no mapping."""
def set_relative_position (obj, ref, angle, distance):
    """2.8 ``set_relative_position``: move ``obj`` to a point ``distance`` from ``ref``
    at ``angle`` degrees (XZ plane).
    
    Approximate: ``angle`` is applied in world XZ; the 2.8 heading-relative nuance is
    left as a refinement. Returns True if both objects resolved."""
def set_ship_text (obj, name=None, race=None, ship_class=None, desc=None, scan_desc=None, hail=None):
    """2.8 ``set_ship_text``: set scan / name text on a ship.
    
    ``name``/``race``/``ship_class``/``desc`` map to ``name_tag`` / ``hull_origin`` /
    ``hull_name`` / ``long_description``. ``scan_desc`` and ``hail`` have no direct
    Cosmos data_set key and are ignored here (handle via science/comms if needed)."""
def set_side_value (obj, value):
    """2.8 ``set_side_value``: reassign an object's Cosmos side.
    
    1 -> "enemy", 2(+) -> "friendly", 0 -> "neutral". Swaps the side role (so
    ``role(side)`` queries stay correct) and sets ``.side``; does not require the side
    to be a registered side entity."""
def set_special (obj, ability=None, on=True):
    """2.8 ``set_special`` ability -> a Cosmos LegendaryMissions elite ability.
    
    Engine abilities set the ``elite_*`` data_set flag; scripted abilities (cloak,
    warp, teleport, tractor, shield drain/vamp/scramble, eft) are attached by adding
    the ability role and scheduling ``handle_elite_abilities`` (the LM fleets addon
    driver). ``on=False`` (2.8 ``clear``) removes it. Returns the ability key, or
    ``None`` if unknown."""
def special_ability_mapped (ability):
    """True if a 2.8 set_special ability maps to a Cosmos elite ability."""
