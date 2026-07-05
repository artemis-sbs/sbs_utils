from sbs_utils.vec import Vec3
def add_ai (agent, ai_type, data=None):
    """Attach a brain to ``agent`` matching a 2.8 ``add_ai`` block ``type``.
    
    Args:
        agent: the ship handle (id, object, or the value from a2x_create_*).
        ai_type (str): the 2.8 AI block type (e.g. ``"CHASE_PLAYER"``).
        data (dict, optional): variables passed to the brain label.
    
    Returns:
        str | None: the brain name added, or ``None`` if the type has no mapping."""
def addto_object_property (obj, prop, value, index=None):
    """2.8 ``addto_object_property``: add ``value`` to a mapped property's current value."""
def ai_brain_for (ai_type):
    """2.8 AI block type -> a Cosmos brain label name, or ``None`` if unmapped."""
def angle (deg):
    """Convert a 2.8 heading (degrees) to the equivalent Cosmos heading (degrees).
    
    The horizontal-plane mirror is a 180 degree yaw rotation, so a heading vector is
    negated -- i.e. the converted heading is ``(deg + 180) mod 360``. This accounts
    for the flip itself; if a given mission also needs a handedness correction it is
    a per-mission ``# TODO verify heading`` (Cosmos vs 2.8 zero-reference), not
    something this function can know.
    
    Args:
        deg (float): a heading in Artemis 2.8 degrees (0..360).
    
    Returns:
        float: the equivalent Cosmos heading in degrees, in [0, 360)."""
def big_message (title, subtitle1='', subtitle2='', to=None, time=30):
    """2.8 ``big_message`` -> a chapter-title info-panel card.
    
    (2.8 showed this as a main-screen chapter card; an info-panel card with a banner
    is the closest scaffold equivalent.) Uses a long auto-dismiss ``time`` so the
    chapter title stays up like the 2.8 main-screen card."""
def clear_ai (agent):
    """2.8 ``clear_ai``: remove the agent's brain stack."""
def console_roles (letters):
    """2.8 console letters (a subset of ``MHWESCO``) -> a Cosmos console-role csv."""
def copy_object_property (src, dst, prop):
    """2.8 ``copy_object_property``: copy a mapped property from ``src`` to ``dst``."""
def create_anomaly (x, y, z, pickup_type, name=None):
    """2.8 ``create type="Anomaly"`` -> a Cosmos collectible pickup.
    
    Maps ``pickup_type`` (2.8 pickupType 0..7) to an upgrade key and spawns via the
    core ``pickup_spawn``. Returns ``None`` for type 8 (beacon), which has no Cosmos
    equivalent."""
def create_asteroids (count, start, end=None, radius=0, random_range=0, seed=None, height=1000, selectable=False):
    """Spawn ``count`` asteroids (2.8 ``create type="asteroids"``). See
    :func:`create_nebulas` for the shared argument meanings."""
def create_black_hole (x, y, z, gravity_radius=10000, gravity_strength=1.0, turbulence_strength=1.0, collision_damage=200):
    """2.8 ``create type="blackHole"`` -> a Cosmos maelstrom terrain object."""
def create_enemy (x, y, z, art, name=None, side='enemy', behave='behav_npcship'):
    """2.8 ``create type="enemy"`` -> an NPC ship (no brain attached here; see a2x_add_ai)."""
def create_generic (x, y, z, art, name=None, side=None, behave='behav_do_nothing'):
    """2.8 ``create type="genericMesh"`` -> nearest-art NPC (raw .dxs meshes have no
    Cosmos equivalent; ``art`` is a best-fit chosen by the caller)."""
def create_mines (count, start, end=None, radius=0, random_range=0, seed=None, damage=5, blast_radius=1000):
    """Spawn ``count`` mines (2.8 ``create type="mines"``).
    
    Cosmos has no bulk-mine helper, so this places each mine with ``terrain_spawn``
    and sets ``damage_done`` / ``blast_radius`` on its data_set."""
def create_monster (x, y, z, monster_type=0, art=None, name=None, side='monster', behave='behav_do_nothing'):
    """2.8 ``create type="monster"`` -> a placeholder creature.
    
    Uses real Cosmos art for classic (0) and derelict (8); a placeholder hull for the
    rest. Always tags the spawn with a ``creature_*`` role so the whole field can be
    re-skinned in one query when Cosmos ships real creature art."""
def create_nebulas (count, start, end=None, radius=0, random_range=0, seed=None, neb_type=1, height=1000, selectable=False):
    """Spawn ``count`` nebula clusters (2.8 ``create type="nebulas"``).
    
    Args:
        count (int): number of clusters.
        start (Vec3 | tuple): origin in 2.8 coords.
        end (Vec3 | tuple, optional): if given, distribute start->end (line mode).
        radius (float, optional): sphere-cloud radius when ``end`` is None.
        random_range (float, optional): isotropic per-cluster jitter.
        seed (int, optional): reproducible placement (2.8 randomSeed).
        neb_type (int, optional): 2.8 nebType 1..3 -> colour.
        height (int, optional): vertical scatter passed to the spawner.
        selectable (bool, optional): selectable on 2D radar.
    
    Returns:
        list: the spawned nebula objects."""
def create_neutral (x, y, z, art, name=None, side='civilian', behave='behav_npcship'):
    """2.8 ``create type="neutral"`` -> an NPC ship."""
def create_player (x, y, z, art, name=None, side='tsn'):
    """2.8 ``create type="player"`` -> a player ship. Returns the ship ID."""
def create_station (x, y, z, art, name=None, side='friendly', behave='behav_station'):
    """2.8 ``create type="station"`` -> a station (first role = side, plus 'station')."""
def destroy (handle):
    """2.8 ``destroy``: remove a named object from the game.
    
    ``handle`` may be an id, object, or the value returned by an a2x_create_*.
    Returns True if an object was deleted."""
def destroy_near (x, y, z, radius, kind='all'):
    """2.8 ``destroy_near``: delete unnamed objects of ``kind`` within ``radius`` of a
    point. ``kind`` is a 2.8 type (nebulas/asteroids/mines/whales/drones/all). The
    point is given in 2.8 coords and flipped internally. Returns the count deleted."""
def fleet_coeff_mapped (prop):
    """True if a 2.8 global difficulty property maps to a fleet coefficient."""
def in_box (obj, least_x, least_z, most_x, most_z, inside=True):
    """2.8 ``if_inside_box`` / ``if_outside_box`` (an XZ rectangle).
    
    The corners are converted from 2.8 to Cosmos coordinates (the 180-degree XZ
    mirror), so the test is correct in Cosmos space. Returns ``inside`` semantics
    by default; pass ``inside=False`` for the outside test."""
def incoming_comms_text (message, from_name='', title=None, to=None, time=30):
    """2.8 ``incoming_comms_text`` -> an info-panel "hail" card plus a comms message.
    
    Shows a ``comms_info_card`` (the promoted HTBM info-panel pattern: speaker name,
    history, auto-dismiss) and also delivers the text as an incoming comms message via
    ``comms_receive_internal`` (a ``comms_message`` whose sender/receiver are the player
    ship). The 2.8 ``from`` is just the sender label, not an object reference, so it is
    used purely as the message's ``from_name`` (the comms title) -- there is no sender
    ship to attach.
    
    Args:
        message (str): body text (``^`` line breaks are converted).
        from_name (str, optional): sender label -> the card title and comms ``from_name``.
        title (str, optional): overrides the card title (defaults to ``from_name``).
        to (optional): target console client id/set for the card; defaults to all consoles.
        time (int, optional): card auto-dismiss seconds. Defaults to 30."""
def incoming_message (from_name, filename, to=None):
    """2.8 ``incoming_message`` (a comms button that plays an ogg) -> play the audio.
    
    Simplified: 2.8 created a button; this plays the file directly. ``filename`` is
    resolved relative to the mission's media folder."""
def is_docked (ship, station=None):
    """2.8 ``if_docked``: True if ``ship`` is currently docked.
    
    The engine stores ``dock_state`` as ``"undocked"`` when not docked (otherwise a
    docked marker / station). ``station`` is accepted for call-site parity with 2.8
    but not matched -- Cosmos dock state is effectively boolean here."""
def monster_art (monster_type):
    """2.8 ``monsterType`` -> Cosmos art key (placeholder for types without real art)."""
def monster_role (monster_type):
    """2.8 ``monsterType`` -> a ``creature_*`` role tag (the re-skin seam)."""
def object_property_key (prop):
    """Return ``(data_set_key, index)`` for a data-backed 2.8 property, else ``None``.
    
    Useful for reads (``get_object_property`` / ``if_object_property``)."""
def object_property_mapped (prop):
    """True if this 2.8 property has a confirmed Cosmos mapping."""
def pickup_key (pickup_type):
    """2.8 ``pickupType`` (int) -> Cosmos upgrade key, or ``None`` for type 8 (beacon)."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
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
def spawn_external_program (name, arguments='', id=None):
    """2.8 ``spawn_external_program``: launch an external program (non-blocking).
    
    In 2.8 this was the way to play cutscene videos (it launched a media player like
    VLC). ``name`` is resolved relative to the mission folder when not absolute, as in
    2.8. Best-effort: the 2.8 program paths (e.g. ``dat/VLCPortable/...``) won't exist
    under Cosmos, so update the path -- a failed launch is logged, not fatal. Returns
    the ``Popen`` handle, or ``None`` on failure."""
def special_ability_mapped (ability):
    """True if a 2.8 set_special ability maps to a Cosmos elite ability."""
def warning_popup (message, consoles=None, ship=None, title='Warning', time=30):
    """2.8 ``warning_popup_message``: a short message to specific consoles.
    
    Maps to an info-panel message card (``comms_info_card``) with a ``title`` and an
    auto-dismiss ``time`` -- closer to 2.8's transient warning than the waterfall. If
    ``ship`` is given the message goes to that ship's consoles; otherwise to all
    console clients. ``consoles`` (e.g. ``"HW"``) is a 2.8 console-letter string; each
    letter selects a console role to target (see :func:`console_roles`)."""
def within (obj, x, y, z, radius):
    """True if ``obj`` is within ``radius`` of a 2.8-coord point (flipped internally).
    
    A boolean for polling loops (2.8 if_distance-to-point / if_inside_sphere)."""
