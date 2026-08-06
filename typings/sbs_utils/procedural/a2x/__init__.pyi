from sbs_utils.vec import Vec3
def add_ai (agent, ai_type, data=None):
    """Attach a brain to ``agent`` matching a 2.8 ``add_ai`` block ``type``.
    
    Args:
        agent: the ship handle (id, object, or the value from a2x_create_*).
        ai_type (str): the 2.8 AI block type (e.g. ``"CHASE_PLAYER"``).
        data (dict, optional): variables passed to the brain label.
    
    Returns:
        str | None: the brain name added, or ``None`` if the type has no mapping."""
def add_angle (o, d28):
    """2.8 ``addto angle += d``: nudge the facing. The mirror reverses the turn sense, so a
    2.8 clockwise delta ``d`` is a Cosmos yaw of ``-d``."""
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
def big_message (title, subtitle1='', subtitle2='', to=None, time=8):
    """2.8 ``big_message`` -> a cinematic Hero chapter card on every player MAIN SCREEN.
    
    2.8 showed this as a big main-screen chapter card, so the audience is the MAIN SCREEN
    of every player ship -- not every console. ``to`` defaults to ``role("__player__")``;
    the overlay layer expands each ship to its consoles, and ``consoles="mainscreen"``
    narrows that to the main screen (the same narrowing is applied to the letterbox bars,
    so the framing matches). Pass ``to`` explicitly to aim it somewhere else.
    
    Drawn as a hero card (large centred title + combined subtitles on the ``center_hero``
    slot) with cinematic ``letterbox`` bars, via the one-call ``letterbox=`` form. Both
    auto-dismiss after ``time``.
    
    ``time`` defaults to **8 seconds**. This is a full-screen card WITH LETTERBOX BARS
    over the main screen, so the default is the length of a chapter title, not of a
    message you read at leisure - it was 30, which left the bridge letterboxed for half
    a minute. The converter emits ``a2x_big_message(title, sub1, sub2)`` with no ``time``,
    so this default is what every converted 2.8 mission actually gets. Pass ``time``
    explicitly for a card that should linger.
    
    NOTE ON TIMING: this resolves its audience WHEN CALLED, and an empty console set is
    silently ignored by the overlay layer (a normal "nobody connected yet" case). A card
    fired before the crew has taken consoles therefore goes nowhere without any error --
    so a mission-opening card belongs on ``//shared/signal/game_started``, not in the map
    task's start block."""
def caller_face (from_name):
    """A stable face for a 2.8 sender LABEL, or None if there is no label.
    
    Prefers a real one: if the mission has a lifeform of that name, that character's
    face wins. Otherwise a face is generated once and cached, picking the race from the
    label when it names one ("Kralien Warship Zeta") and a terran otherwise - most 2.8
    callers are command, stations and human captains.
    
    The caller stores the result on each ship as ``face_<from_name>``, and only when that
    key is unset, so a mission's own portrait always wins over this one.
    
    Stable for the run, not across runs: it is a portrait for a name 2.8 never gave one
    to, so consistency within a session is what matters."""
def clear_ai (agent):
    """2.8 ``clear_ai``: remove the agent's brain stack."""
def clear_station_carried (station):
    """2.8 ``clear_player_station_carried name="X"``: remove a station's stored single-seat
    craft.
    
    Deletes the STANDBY (in-hangar, not launched) craft hosted by the station --
    ``linked_to(station, "hangar_craft") & role("standby") & role("cockpit")`` -- leaving any
    already-launched craft flying. Returns the count removed."""
def console_roles (letters):
    """2.8 console letters (a subset of ``MHWESCO``) -> a Cosmos console-role csv."""
def copy_angle (src, dst):
    """2.8 ``copy angle src->dst``: copy the (yaw) facing. Both are already in Cosmos space,
    so this copies the Cosmos yaw directly -- no 2.8 conversion."""
def copy_object_property (src, dst, prop):
    """2.8 ``copy_object_property``: copy a mapped property from ``src`` to ``dst``."""
def create_anomaly (x, y, z, pickup_type, name=None):
    """2.8 ``create type="Anomaly"`` -> a Cosmos collectible pickup.
    
    Maps ``pickup_type`` (2.8 pickupType 0..7) to an upgrade key and spawns via the
    core ``pickup_spawn``. pickupType 8 (beacon) spawns an inert, recoverable Beacon
    (role ``beacon`` + ``behav_pickup``): the LegendaryMissions fabrication addon's
    fly-over route credits ``Beacon_NUM`` when a player collects it. a2x references LM
    only by the ``beacon`` role name (feature-detected), never by import."""
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
def create_neutral (x, y, z, art, name=None, side='civ', behave='behav_npcship'):
    """2.8 ``create type="neutral"`` -> an NPC ship."""
def create_player (x, y, z, art, name=None, side='tsn', slot=None):
    """2.8 ``create type="player"`` -> a player ship. Returns the ship ID.
    
    Tags the ship ``default_player_ship`` as it spawns. That is the role the
    LegendaryMissions crew-select / loadout machinery keys on, and it is normally added by
    LM's own ``create_default_player_ships`` -- which a converted mission turns off, since
    those ships are built on side "tsn" rather than the mission's declared player side.
    Doing it HERE rather than in a later route means a ship created mid-mission (some 2.8
    missions spawn players from an event, not ``<start>``) is tagged too.
    
    Pass ``slot`` (the 2.8 ``player_slot``) to make creation IDEMPOTENT: the ship is
    spawned only if that slot is empty, so a ``//shared/signal/create_player_ships``
    route emitted twice does not duplicate the roster. It also makes
    :func:`player_ship` resolve the slot by identity rather than by position. Without
    a slot this behaves exactly as before and every call mints a new hull."""
def create_station (x, y, z, art, name=None, side='friendly', behave='behav_station'):
    """2.8 ``create type="station"`` -> a station (first role = side, plus 'station')."""
def declare_sides (side_values, names=None, colors=None, hostile_color=None, neutral_color=None):
    """Declare one Cosmos side per 2.8 ``sideValue`` and apply 2.8's implicit diplomacy.
    
    Creates a side for every value in ``side_values`` (via ``side_create``, so each is
    allied to itself), then relates every pair by the 2.8 rule:
    
    * different non-zero values -> ``HOSTILE``
    * either value is 0 ("no side") -> ``NEUTRAL``
    
    Idempotent -- ``side_create`` reconfigures an existing side in place, so calling it
    twice (or alongside a mission that already declared a side) is safe. Re-declaring also
    RE-ISSUES every engine-side write (icon colours, self-ally, pairwise relations,
    diplomacy colours), so a second call fully repairs an engine table that lost the
    first one; that is what a converted mission's re-assert loop relies on.
    
    Args:
        side_values (iterable[int]): The 2.8 sideValues the mission actually uses.
            Order is irrelevant; duplicates are ignored.
        names (dict[int, str], optional): Per-value display name overrides.
        colors (dict[int, str], optional): Per-value icon color overrides.
        hostile_color (str, optional): Map colour for HOSTILE contacts. Defaults to
            LegendaryMissions' ``"#F00"``.
        neutral_color (str, optional): Map colour for NEUTRAL contacts. Defaults to
            LegendaryMissions' ``"#077"``.
    
    Returns:
        dict[int, int]: 2.8 sideValue -> the created side agent's ID.
    
    Example:
        A mission whose objects carry sideValue 1 (enemies) and 2 (player + station)::
    
            a2x_declare_sides([1, 2])"""
def default_enemy_ai (agent, enemies_only=True):
    """Attach 2.8's implicit default enemy behaviour to a freshly spawned NPC.
    
    ``brain_add``'s root is a Select: the children run in order and it stops at the
    first success, so this is a priority list, exactly like a 2.8 brain stack.
    ``ai_chase_current`` re-chases whatever last angered the ship (2.8 CHASE_ANGER) and
    fails harmlessly on a fresh spawn with no target, falling through to the station and
    then the player.
    
    Firing is NOT decided here: every LM chase brain gates its trigger on
    ``side_are_enemies(BRAIN_AGENT_ID, target)``, so a ship shoots only what diplomacy
    says is hostile -- and a ceasefire silently stops it. ``enemies_only`` likewise
    narrows target SELECTION to declared enemies, so an enemy will not shadow a neutral.
    
    The brain labels live in the LegendaryMissions ``ai`` addon and are resolved by NAME
    at runtime, so a2x keeps no import dependency on LM (the mission feature-detects the
    addon). Returns the brain list attached."""
def destroy (handle):
    """2.8 ``destroy``: remove a named object from the game.
    
    ``handle`` may be an id, object, or the value returned by an a2x_create_*.
    Returns True if an object was deleted."""
def destroy_named (name):
    """2.8 ``destroy`` by NAME for an object the converter could not statically capture --
    the name has no ``create`` the tool saw (created some other way, or a dead reference the
    2.8 mission left in). Deletes every current space object whose name matches; a no-op if
    none exist -- which mirrors 2.8, where destroying a missing object does nothing. Returns
    the count deleted."""
def destroy_near (x, y, z, radius, kind='all'):
    """2.8 ``destroy_near``: delete unnamed objects of ``kind`` within ``radius`` of a
    point. ``kind`` is a 2.8 type (nebulas/asteroids/mines/whales/drones/all). The
    point is given in 2.8 coords and flipped internally. Returns the count deleted."""
def destroy_near_object (obj, radius, kind='all'):
    """2.8 ``destroy_near`` centered on a NAMED object: delete objects of ``kind`` within
    ``radius`` of that object's runtime position (excluding the object itself). Like
    :func:`destroy_near` but the centre is a live Cosmos object, so its position is already
    in Cosmos space (no coord flip). Returns the count deleted."""
def dir_throttle (agent, heading, throttle=1.0):
    """2.8 ``add_ai DIR_THROTTLE``: fly a compass heading at a throttle. Compute a far point
    along the heading from the ship and drive there with the ``goto_object_or_location`` brain
    (via ``blackboard:target_point``).
    
    HEADING CONVENTION -- VERIFY IN-ENGINE (same open question as the 2.8 ``angle`` property):
    2.8 heading is in degrees (0=N, 90=E, ...), and Cosmos mirrors X and Z about the map centre,
    so the 2.8 direction is negated here. If ships fly the wrong way, flip the ``dx``/``dz``
    signs. Returns the brain name, or ``None`` if the ship can't be resolved."""
def distance_greater (obj1, obj2, radius):
    """2.8 ``if_distance`` (GREATER) as a live boolean for polling loops.
    
    Also False when either object is missing or destroyed: a destroyed object is
    not "infinitely far away", it is untestable, so the condition should not fire."""
def distance_less (obj1, obj2, radius):
    """2.8 ``if_distance`` (LESS) as a live boolean for polling loops.
    
    False when either object is missing or destroyed -- a 2.8 condition about an
    object that does not exist simply never fires."""
def fleet_coeff_mapped (prop):
    """True if a 2.8 global difficulty property maps to a fleet coefficient."""
def get_angle (o):
    """Read ``o``'s facing back as a 2.8 ``angle`` (radians), inverse of :func:`set_angle`."""
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
def in_box (obj, least_x, least_z, most_x, most_z, inside=True):
    """2.8 ``if_inside_box`` / ``if_outside_box`` (an XZ rectangle).
    
    The corners are converted from 2.8 to Cosmos coordinates (the 180-degree XZ
    mirror), so the test is correct in Cosmos space. Returns ``inside`` semantics
    by default; pass ``inside=False`` for the outside test."""
def incoming_comms_text (message, from_name='', title=None, to=None, time=8, consoles='mainscreen', side=None):
    """2.8 ``incoming_comms_text`` -> a comms message on the addressed player ships.
    
    JUST COMMS, JUST ONCE. It used to also throw a lower-third subtitle over the live
    view. In practice that was the wrong presentation - a 2.8 comms text is a message
    the crew reads and answers on Comms, not a film subtitle - and it arrived several
    times over, because the converter hung these bodies on a per-console route. The
    overlay is gone; the emitter now puts the body on a `//shared/signal` route so it
    runs once on the server.
    
    It goes out on the INTERNAL channel (``comms_receive_internal``). A 2.8 ``from`` is
    a LABEL with no object behind it - "TSN Command", a Kralien warship - and internal
    is exactly the channel built for a named sender that is not a ship you can select:
    it resolves the portrait from the receiving ship's own ``face_<from_name>`` key. So
    the label gets a face, which 2.8 never had.
    
    We seed that key with a generated face the first time a caller speaks (see
    :func:`caller_face`), and only if it is unset - so a mission that pre-registers
    ``face_TSN Command`` on its ships keeps its own portrait.
    
    ``comms_message`` renders the bar as ``<from>: <title>``, so a hail reads
    ``Dragon Tooth Refuge: ALERT``, coloured by the type (see :func:`type_title_color`).
    
    Args:
        message (str): body text (``^`` line breaks are converted).
        from_name (str, optional): the 2.8 ``from`` label -> the sender name and the
            key its portrait is stored under.
        title (str, optional): the 2.8 ``type`` -> the title bar and its colour.
        to (optional): audience; defaults to the player ships selected by ``side``.
        side (optional): the 2.8 ``sideValue`` this hail is addressed to. Narrows the
            audience to the player ships of that faction, which is what 2.8 meant by it -
            3247 of the corpus's 4318 tags carry one, and without it a hail meant for one
            team is read by everybody. Omitted / ``None`` = every player ship.
        time, consoles: accepted and IGNORED. They sized the old subtitle overlay; kept
            so an already-generated mission that passes them still loads."""
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
def named (name):
    """Resolve a 2.8 object NAME to a live Cosmos object ID at runtime.
    
    For a condition (or command) that references an object the converter could not statically
    capture -- a forward reference, or a name mismatch in the 2.8 source. Returns the first
    space object whose name matches, or ``None`` if none exists.
    
    Passing that ``None`` on is safe only through the guarded helpers: ``object_exists(None)``
    is False, and ``a2x_distance_less`` / ``a2x_distance_greater`` (and the core
    ``distance_less`` / ``distance_greater`` promises) treat a missing object as "condition
    does not hold". It is NOT safe to hand to ``sbs.distance_id`` directly -- the engine
    errors with "sbs.distance_id was sent None". (A bare ``role(name)`` set would throw too.)"""
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
def pickup_key (pickup_type):
    """2.8 ``pickupType`` (int) -> Cosmos upgrade key, or ``None`` for type 8 (beacon)."""
def place_player (x, y, z, slot=0, name=None, side=None):
    """2.8 ``create type="player"`` OUTSIDE the ``<start>`` block: PLACE the ship, don't
    make one. Returns the ship ID, or None if that slot has no ship.
    
    In 2.8 the player ships already exist -- the crew picks one at the console -- and
    ``create type="player"`` only positions and configures the ship in that slot. There are
    exactly 8 slots, so the command can never produce a 9th ship. For the ``<start>`` block
    that distinction does not matter (Cosmos has nothing yet, so we spawn, via
    :func:`create_player`), but for a create in an EVENT it is the whole meaning: the crew
    is already flying that ship.
    
    Spawning there instead gave the mission a second, unmanned hull while the crew sat on
    the original -- and for a mission whose only player create is in an event
    (MISS_Medusa's_Maze picks one of eight maze entrances at random) it meant no ship
    existed at ship-select time at all.
    
    Repositioning uses the engine's own ``reposition_space_object``, the same call
    ``respawn_player_ship`` uses, so the move is seen by physics rather than written behind
    its back. ``name`` renames the ship in place (2.8 missions rename per entrance);
    ``side`` moves it to another declared side, diplomacy following along."""
def player_ship (slot=0):
    """2.8 references a player ship by name or slot; Cosmos references by ID. Resolve a
    2.8 ``player_slot`` (0-based) to the Cosmos player ship at that slot. Returns its ID,
    or ``None`` if that slot has no player ship.
    
    Prefers a ship STAMPED with the slot (``create_player(..., slot=N)`` /
    ``player_ensure``), which is stable no matter what else spawns or respawns.
    
    Falls back to position in the player set for ships with no stamp. That fallback
    sorts by id: ``role()`` returns an unordered set, so the historical unsorted index
    made "slot N" mean hash order rather than creation order, and it could silently
    change as ships were added or removed. Sorting matches how every other consumer
    re-derives slot order (``sorted(..., key=lambda p: p.id)``), and is identical to
    the old behavior for the single-player-ship case."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
def sensor_range (setting):
    """2.8 ``sensorSetting`` -> scan range in Cosmos units. 0 = unlimited (the whole map =
    100 km = map size); N>0 = 100/(3N) km = 100000/(3N) units (bigger N = smaller range)."""
def set_angle (o, a28):
    """Set object ``o``'s facing from a 2.8 ``angle`` (radians): Cosmos yaw = ``pi - a28``."""
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
def set_diplomacy_colors (hostile_color='#F00', neutral_color='#077'):
    """Set the map colours the engine draws contacts with, by RELATION.
    
    Split out of :func:`declare_sides` and callable on its own, because these writes are
    frame-sensitive. ``sim`` here is ``FrameContext.context.sim`` -- the handle the engine
    passed into ``cosmos_event_handler`` at the top of the CURRENT event. ``sim_create()``
    replaces the simulation but cannot refresh that handle (the engine's ``sbs`` module
    exposes no module-level ``sim``), so anything calling this in the same frame as
    ``sim_create()`` writes to the pre-``sim_create`` simulation and the colours are lost
    silently -- contacts draw as UNKNOWN, i.e. grey.
    
    That was the real cause of the long-standing "converted missions have no diplomacy
    colours" bug: LegendaryMissions' server console ran ``sim_create()`` and
    ``signal_emit("create_sides")`` in one frame, so the whole engine-facing half of
    ``declare_sides`` went to a dead simulation. server_console now yields a frame between
    the two. The earlier "the engine does not retain early writes, re-apply at ~3s"
    reading was a misdiagnosis: the ~1s re-apply looked like it failed only because it
    re-issued the COLOURS alone, leaving the relations still missing.
    
    Safe to call repeatedly; converted missions still re-assert on a short loop so they
    keep working against an older LegendaryMissions library that lacks the frame yield.
    
    Returns True if the colours were applied, False if there was no sim to apply them to."""
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
def set_gm_instructions (title, text=''):
    """2.8 ``gm_instructions`` -> the Cosmos GM console instruction panel.
    
    Sets the shared ``GAMEMASTER_INSTRUCTIONS`` variable that ``gamemaster_panel_instructions``
    renders (via ``gui_text_area``; ``^`` = line break). The 2.8 title becomes the first line.
    Shared scope so the GM console's render task sees it."""
def set_hull_side (handle, side):
    """Force an object's ``hull_side`` blob field to match the side it was spawned on.
    
    ``hull_side`` is SCAN information the engine seeds from the ``side`` field of the
    hull's shipData entry -- so a ship on art ``tsn_light_cruiser`` reads "TSN" on the
    Science object list no matter which side it actually belongs to. A converted 2.8
    mission puts its crew on its own declared side (``friendly``), so the two disagreed:
    diplomacy said one thing and the Science list showed another.
    
    This overwrites the scan string with the spawned side, taking the side's display name
    when it resolves to a registered side and the raw key otherwise. ``side`` may be the
    full spawn string ("friendly, a2x_spare_player") -- only the first token is the side.
    
    EXPEDIENT, not the final answer: the real fix is for the hull's shipData not to carry
    a side at all, since side is a property of the ship, not of the hull."""
def set_nebula_opaque_all (opaque):
    """2.8 global ``nebulaIsOpaque`` (a nameless set_object_property) -> set every nebula's
    throttle limit. Non-zero (opaque) keeps the Cosmos default limit (2.0, which slows
    ships); 0 = no limit. Returns the number of nebulae updated."""
def set_object_property (obj, prop, value, index=None):
    """Set a 2.8-named property on ``obj`` (id / object / a2x_create_* handle).
    
    Returns True if the property was mapped and set, False if it has no mapping."""
def set_pitch (o, p28):
    """2.8 ``pitch`` (nose up/down) -> a pitch composed onto the orientation, about the
    object's LOCAL right (X) axis, preserving facing.
    
    Documented as radians (-pi..pi), but the corpus uses magnitudes beyond pi (10/20/90/120)
    -- the scripting parser is degrees everywhere else, so a magnitude > pi is treated as
    degrees. The X/Z map mirror preserves the vertical (Y is unchanged), so the pitch carries
    over directly."""
def set_relative_position (obj, ref, angle, distance):
    """2.8 ``set_relative_position``: move ``obj`` to a point ``distance`` from ``ref``
    at ``angle`` degrees (XZ plane).
    
    Approximate: ``angle`` is applied in world XZ; the 2.8 heading-relative nuance is
    left as a refinement. Returns True if both objects resolved."""
def set_roll (o, r28):
    """2.8 ``roll`` (radians, about the forward/nose axis) -> add that roll to the object's
    orientation, about its LOCAL forward (Z) axis, preserving its facing. The X/Z map mirror
    flips the roll sense, so the applied roll is ``-r28`` (pi is sign-invariant -- which is
    all the corpus uses: 180-degree warpgate flips)."""
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
def set_skybox_index (index):
    """2.8 ``set_skybox_index`` (SB00..SB29) -> schedule a Cosmos skybox.
    
    Cosmos has no SB## skyboxes; map the 2.8 index across the skyboxes the LM
    ``basic_random_skybox`` addon registers (``@media/skybox/*``), so each 2.8 index picks a
    stable Cosmos skybox. A negative / non-integer index schedules a random skybox. Returns
    the scheduled skybox label, or ``None`` when a random one was scheduled."""
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
def side_color (side_value):
    """An icon color for a 2.8 sideValue, matching the LegendaryMissions palette."""
def side_key (side_value):
    """2.8 ``sideValue`` -> the Cosmos side key for that faction.
    
    0/1/2 keep the readable legacy names (``neutral``/``enemy``/``friendly``); 3 and up
    get a synthesized ``side_N`` so an N-faction mission stays N factions. Values are
    NOT collapsed onto the three LegendaryMissions keys -- see the module docstring."""
def side_name (side_value):
    """A display name for a 2.8 sideValue (shown on the 2D map / sensor contacts)."""
def spawn_external_program (name, arguments='', id=None):
    """2.8 ``spawn_external_program``: launch an external program (non-blocking).
    
    In 2.8 this was the way to play cutscene videos (it launched a media player like
    VLC). ``name`` is resolved relative to the mission folder when not absolute, as in
    2.8. Best-effort: the 2.8 program paths (e.g. ``dat/VLCPortable/...``) won't exist
    under Cosmos, so update the path -- a failed launch is logged, not fatal. Returns
    the ``Popen`` handle, or ``None`` on failure."""
def special_ability_mapped (ability):
    """True if a 2.8 set_special ability maps to a Cosmos elite ability."""
def type_title_color (kind):
    """2.8 ``type`` -> a title colour, or None when it says nothing useful."""
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
