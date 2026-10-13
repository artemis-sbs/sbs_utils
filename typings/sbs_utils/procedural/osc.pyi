from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher
def _contacts (ship):
    """What science and comms can pick: ships and stations, not this ship itself."""
def _cycle (ship, candidates, current, mode):
    """Pick a target from ``candidates`` by distance: nearest, next farther, or previous."""
def _follow (route, ship, pick):
    """Fire a console's selection routes, as a click on that contact would.
    
    Those routes start their task on the SERVER console's GUI task. This runs from a tick
    callback, not from a task, so without a server page (a bare unit test, a tool host)
    there is nowhere to start it: the selection still lands, the routes are skipped, and
    that is said once rather than raised every press."""
def _h_bind (sender, args):
    ...
def _h_comms_button (ship, args, key):
    ...
def _h_comms_target (ship, args, key):
    ...
def _h_coolant (ship, args, key):
    ...
def _h_dock (ship, args, key):
    ...
def _h_heading (ship, args, key):
    ...
def _h_impulse (ship, args, key):
    """The game's throttle bar in impulse: 0..1. Keeps REVERSE if it is engaged, and
    drops out of warp - moving the impulse lever is asking for impulse."""
def _h_power (ship, args, key):
    ...
def _h_red_alert (ship, args, key):
    ...
def _h_reverse (ship, args, key):
    """The game's REV toggle: the same power, backwards. Engaged from a standstill it
    backs off at half power, because reverse at 0 would do nothing."""
def _h_science_target (ship, args, key):
    ...
def _h_shields (ship, args, key):
    ...
def _h_stop (ship, args, key):
    ...
def _h_throttle (ship, args, key):
    ...
def _h_undock (ship, args, key):
    ...
def _h_warp (ship, args, key):
    """Warp 1..4 is throttle 2..5 (the engine: 0-5, anything over 1 is warp). Warp 0
    drops back to full impulse. helm_throttle refuses warp a ship cannot sustain."""
def _h_weapons_fire (ship, args, key):
    ...
def _h_weapons_target (ship, args, key):
    ...
def _name_of (obj_id):
    ...
def _norm (name):
    ...
def _num (args, default=0.0):
    ...
def _osc_feedback (now, deadline=None):
    ...
def _osc_packet (data, addr):
    ...
def _osc_ship (slot):
    """The ship a tablet drives: player slot ``slot``, else the lowest filled slot, else
    the first player ship. A mission that never assigns slots still gets its only ship."""
def _osc_str (s):
    ...
def _osc_tick (t=None):
    ...
def _osc_tick_body ():
    ...
def _pad (n):
    ...
def _pressed (args):
    """A button press. No argument counts as a press (a bare message is a trigger)."""
def _read_str (data, i):
    ...
def _report_once (key, message, level='warning'):
    ...
def _throttle_now (ship):
    ...
def closest_list (source: int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData | sbs_utils.agent.Agent | sbs_utils.vec.Vec3, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """Return all objects in a set within optional distance and filter criteria.
    
    Args:
        source (Agent | int | CloseData | SpawnData | Vec3): The reference
            agent ID, object, or position.
        the_set (set[int]): IDs of candidates to test.
        max_dist (float, optional): Maximum distance to include. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``
            applied to each candidate. Defaults to None.
    
    Returns:
        list[CloseData]: All qualifying candidates with their distances."""
def fire_torpedo (id_or_obj, kind=None, tube_index=0) -> None:
    """Fire a torpedo at the ship's current weapon target, via the engine
    (``sbs.simulation.launch_torpedo``). Callable from MAST or Python.
    
    Beams auto-fire, but torpedoes need an explicit launch - this is that call. If
    ``kind`` is given (e.g. ``"Nuke"``, ``"EMP"``), the tube holding that loaded type is
    selected; otherwise ``tube_index`` fires as-is (``0`` = the default/first loaded
    type). No-ops if the ship is gone or the type is out of ammo.
    
    Args:
        id_or_obj (int | Agent): The firing ship.
        kind (str, optional): Torpedo type to fire; resolved to its tube. Defaults to
            None (fire ``tube_index``).
        tube_index (int, optional): Tube to fire when ``kind`` is not given. Defaults 0."""
def follow_route_select_comms (origin_id, selected_id):
    """Programmatically fire the comms selection route as if the player made a selection.
    
    Args:
        origin_id (Agent | int): The player ship agent ID or object.
        selected_id (Agent | int): The target space object agent ID or object."""
def follow_route_select_science (origin_id, selected_id):
    """Programmatically fire the science selection route as if the player made a selection.
    
    Args:
        origin_id (Agent | int): The player ship agent ID or object.
        selected_id (Agent | int): The target space object agent ID or object."""
def get_comms_selection (id_or_not):
    """Return the ID of the object currently selected on the comms console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_data_set_value (id_or_obj, key, index=0, default=None):
    """Get a value from the engine data-set (blob) of a space or grid object.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
            **This is an INDEX, not a fallback** - the third positional argument is
            which slot to read (shield 0 vs shield 1), and passing a "default" there
            reads the wrong slot or fails outright.
        default (any, optional): what to return when the field has never been set.
            The engine answers ``None`` for such a field, and a mission that then
            compares it (``if fuel < 1000``) raises on a real bridge while running
            clean against the mock's typed defaults - the bug behind LM's Florbin
            cargo-hold watcher and an earlier helm crash. Pass ``default=0`` (or
            ``default=""``) and the caller gets something it can use. ``sbs lint``
            flags the unguarded shape as ``blob-unguarded-none``.
    
    Returns:
        any: The stored value, ``default`` if the object or key is not found."""
def get_science_selection (id_or_not):
    """Return the ID of the object currently selected on the science console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_weapons_selection (id_or_not):
    """Return the ID of the object currently selected on the weapons console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def helm_dock_request (ship, station):
    """Ask to dock: name the base, then start the state walk if it has not started.
    
    The engine takes it from `dock_start` through to `docked` on its own. Docking refills
    the tank fast, which makes it the quick way out of a low-energy situation when a
    friendly station is in reach."""
def helm_energy (ship):
    """Current energy in the tank."""
def helm_eng_controls (ship):
    """Yield ``(index, label, system_index)`` for each engineering control the ship has.
    
    One walk of the `eng_control_label` array, which was written out by hand in three
    places: autoplay's can-turn check and its power loop, and `set_engineering_value`.
    Stops at the first empty label, which is how the engine marks the end."""
def helm_is_docked (ship):
    """True while the ship is docked."""
def helm_set_power (ship, name, value):
    """Set the power level of every control whose label matches `name`. Returns how many.
    
    Unlike `set_engineering_value`, which stops at the first match, this sets all of them -
    a hull can expose more than one control feeding the same system."""
def helm_shield_fraction (ship, facing=0):
    """How full one shield facing is, 0..1. 0 when the ship has no shields."""
def helm_shields (ship, up=True):
    """Raise or lower shields."""
def helm_steer_to_vec (ship, x, y=None, z=None):
    """Steer along a direction vector. Accepts (vec) or (x, y, z)."""
def helm_stop (ship):
    """Cut the throttle and drop direction steering.
    
    Stopping cuts the speed drain, but the sliders and shields still draw, and the auxiliary
    power unit only refills to `helm_apu_ceiling` (~200). It buys a trickle, not a full tank."""
def helm_throttle (ship, level, allow_warp=True, reserve=None):
    """Set the throttle, refusing a warp the ship cannot actually sustain.
    
    Returns the throttle actually set, which may be lower than asked. Two reasons it
    clamps, and both are silent failures otherwise:
    
    * the hull has no warp drive (`warp != 1.0`), so the engine ignores the warp band;
    * the tank is below the reserve, and warp burns it fastest. Clamping to impulse keeps
      enough in hand to reach a station.
    
    Pass `allow_warp=False` to hold impulse regardless - a caller that has decided to
    conserve does not need to restate why."""
def helm_undock (ship):
    """Release the dock.
    
    Clears `dock_base_id` as well as the state: the engine holds a docked ship with a
    TRACTOR, and a cancel that only rewrites the state leaves the ship attached to a base
    it believes it has left."""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
def osc_address_map_json ():
    """The address table as plain data, for tools that build tablet layouts from it."""
def osc_decode (data):
    """Every message in a packet as ``[(address, [args])]``, bundles flattened.
    
    Raises ValueError (or struct.error / UnicodeDecodeError) on anything malformed, so
    the caller can drop the packet whole rather than act on half of it."""
def osc_dispatch (address, args, sender=None):
    """Act on one OSC message. Returns True when the address was recognised.
    
    ``sender`` is the tablet's record (its bound slot); None means the default ship."""
def osc_encode (address, *args):
    """One OSC message as bytes. bool -> T/F, int -> i, float -> f, str -> s, None -> N."""
def osc_is_listening ():
    """True while the OSC listener is open."""
def osc_listen (port=8000, feedback_port=9000, host='0.0.0.0', allow=None, rate=5.0, budget_ms=0.5):
    """Start listening for OSC on UDP ``port``. Server only; call once.
    
    Args:
        port (int, optional): The UDP port tablets send to. Defaults to 8000.
        feedback_port (int | None, optional): The port state is sent back to, on each
            tablet's own address. None replies to the port the packet came from.
            Defaults to 9000, TouchOSC's usual receive port.
        host (str, optional): The interface to bind. "0.0.0.0" accepts the LAN;
            "127.0.0.1" only this machine. Defaults to "0.0.0.0".
        allow (list[str], optional): Address prefixes a sender must match, for example
            ``["192.168.1."]``. None accepts anyone who can reach the port.
        rate (float, optional): Feedback sends per second. 0 turns feedback off.
            Defaults to 5.
        budget_ms (float, optional): The most one update may spend on OSC. Reading
            stops when it is spent and the rest waits in the socket for the next update,
            so tablets can never take time from brains and the rest of the script.
            Defaults to 0.5 ms - normal use measures ~0.03 ms.
    
    Returns:
        bool: True when listening. False (with the reason logged) if the port could not
            be bound - most often another program already holds it."""
def osc_state (ship):
    """Every value sent back to a tablet for ``ship``, as ``{address: value}``."""
def osc_status ():
    """A snapshot for a debug page: port, packets received/dropped, tablets heard from."""
def osc_stop ():
    """Stop listening and forget every tablet. Safe to call when not listening."""
def player_slot_id (slot):
    """The live player ship holding ``slot``, or ``None``.
    
    Args:
        slot (int): The player slot.
    
    Returns:
        int|None: The ship's ID, or None if the slot is empty."""
def player_slots ():
    """Every filled player slot as ``{slot: id}``.
    
    Returns:
        dict: Slot number -> ship ID, for live player ships carrying a slot."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_comms_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the comms console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_science_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the science console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_weapons_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the weapons console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def side_allied_members (observer, scope_role=None):
    """Return the agent IDs on ``observer``'s OWN side or a side ALLIED to it (the
    "friendly" set from observer's point of view), optionally intersected with a
    class role. The ally analog of :func:`side_hostile_members`.
    
    Args:
        observer (str | int | Agent): Side key, side agent ID, or any object whose
            side is used as the point of view.
        scope_role (str, optional): A role to intersect the result with (e.g.
            ``"station"``). Defaults to None (all own+allied members). Prefer a
            scope role, as the raw set includes non-ship side members (clients).
    
    Returns:
        set[int]: IDs of own-side and allied-side agents, optionally scoped."""
def side_hostile_ships (observer):
    """Space objects HOSTILE to ``observer`` that are still in the fight.
    
    The diplomacy-only answer to "who may I fight" — the replacement for scoping a
    hostile set by a faction tag such as ``role("raider")``. Allegiance comes from the
    side relations alone, so a ceasefired or defected side drops out the moment its
    diplomacy changes, with no tag to keep in sync; wrecks and surrendered ships are
    excluded because they are not combatants, not because of who they belong to.
    
    Includes hostile stations (they are on a hostile side like anything else). Intersect
    with a CLASS role when you want a narrower kind, e.g.
    ``side_hostile_ships(x) & role("station")`` or ``- role("station")``.
    
    Args:
        observer (str | int | Agent): Side key, side agent ID, or any object whose side
            is the point of view.
    
    Returns:
        set[int]: IDs of hostile, in-the-fight space objects."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_id_list (the_set):
    """Convert a set or list of agents/IDs to a list of integer IDs.
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[int]: Resolved integer IDs; unresolvable items are excluded."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def torpedo_get_available_types_for_ship (id) -> list[str]:
    """Return the torpedo type keys currently available to a player ship.
    
    Args:
        id (int | Agent): The player ship.
    
    Returns:
        list[str]: Torpedo type key strings, or an empty list if none."""
def torpedo_get_count_for_ship (id, key) -> tuple[int, int]:
    """Return the current count and maximum capacity of a torpedo type on a ship.
    
    Args:
        id (int | Agent): The player ship.
        key (str): Torpedo type identifier.
    
    Returns:
        tuple[int, int]: ``(current_count, max_capacity)``, or ``(0, 0)`` if
            the torpedo type is not available on the ship."""
