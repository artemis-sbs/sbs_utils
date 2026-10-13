def _near_consoles (client_id, relic_key):
    """Other consoles whose suits are close to this console's suit, in the same relic."""
def boarding_channel_join (client_id, channel):
    """Move one console into a channel. Its reader picks up that channel's beat."""
def boarding_clients ():
    """Every client currently controlling a character."""
def boarding_encounter (scenes, key, client_id, speaker=None, channel=None, members=()):
    """Start a scene for ONE group - this console and whoever is with it.
    
    The everyday way into a side conversation: somebody walks up to the deputy, and the
    deputy's scene opens for them (and anyone else in ``members``) while the rest of the
    party carries on with whatever they are doing. If the channel already has a beat open
    the console simply joins it, so two people walking up to the same person share one
    conversation instead of starting two.
    
    Returns the channel name, or None when ``key`` names no scene."""
def boarding_is_open (channel=None):
    """True while a beat is open and answerable."""
def boarding_reader_note (client_id, text):
    """Add a line to this console's transcript that is not a beat - something picked up.
    
    It goes below whatever is there, and the Act app then has something to show. A
    console with no transcript yet starts one at the beat it is on, so the next sync
    does not add a beat that is not happening."""
def eva_place_arrive (client_id, relic_key=None, point=None, first_visit=True):
    """A suit has arrived at a place: open its scene, or leave a note. Returns the
    channel when a scene is open for this console, else None.
    
    Called by the autopilot the moment a route ends (`eva_tick`), before `eva_arrived` is
    emitted - so a mission's own `//signal/eva_arrived` sees the scene already open.
    
    ``first_visit`` is whether THIS console had been here before; a returning console gets
    no note, a new one gets the place's ``Scan:`` when its scene has already been played."""
def eva_place_channel (relic_key, point):
    """The channel a place's scene plays on."""
def eva_place_played (relic_key, point):
    """Whether a place's scene has been opened this mission."""
def eva_places_clear ():
    """Forget which places have played - the per-mission reset."""
def eva_places_count ():
    """Reset-ledger probe. Must not create anything by asking."""
def eva_places_enabled (on=None):
    """Whether arriving at a place opens its scene. Pass a value to set it; a mission
    that runs its own arrival beats turns it off."""
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
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
