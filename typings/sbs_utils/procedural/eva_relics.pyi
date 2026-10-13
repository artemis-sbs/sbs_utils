from sbs_utils.agent import Agent
def _dist (a, b):
    ...
def _eva_relic_built (relic_key):
    """The record of a relic whose space is standing, else None."""
def _eva_relic_crew_out (ship_id, relic_key):
    """The suits in a ruin that came from one ship.
    
    `ship_id` None asks for everybody's. A suit whose ship is not on record - one a
    script handed out with `eva_take` and no `home=` - counts for EVERY ship: not knowing
    whose it is must never be the reason an offer is pulled from under somebody."""
def _eva_relic_near (ship_id, relic_key, reach):
    """How far a ship is from a ruin's entrance, or None when it is further than `reach`
    (or either is gone, or the ruin is not standing)."""
def _eva_relic_opens ():
    """``{ship id | None: relic key}`` - what this wiring has on offer, checked against
    the offers actually standing, so one a mission has since replaced is not reported."""
def _eva_relic_opens_set (whose, relic_key):
    ...
def _eva_relic_party_is_ours (invite):
    """Whether an open invitation is one this wiring may adopt or close.
    
    A CREW party with nowhere to walk - no `site`, no tile `area` - is the EVA party by
    construction: there is no other reason to cast the bridge and give them no floor. A
    party a mission CAST (three named people), or one with an interior to beam down into,
    is the mission's own and is never touched."""
def _eva_relics_tick (t=None):
    ...
def _save (state):
    ...
def _say_once (relic_key, why, text):
    """One log line per (relic, reason) - the tick asks every couple of seconds, and a
    refusal repeated at that rate buries the line that explains it."""
def _state ():
    ...
def _unsay (relic_key):
    ...
def eva_relic_close (relic_key=None, force=False, ship=None):
    """Withdraw a ruin's offer, and take its crew back out of the party.
    
    Args:
        relic_key (optional): which ruin. Defaults to whatever is on offer.
        force (bool, optional): withdraw even with somebody still out. For a ruin that is
            being torn down; see `eva_relic_released`.
        ship (optional): only THIS ship's own offer. Left out, every offer of that ruin
            goes - each ship's, and the one for everybody.
    
    Returns:
        bool: False when nothing was withdrawn: that ruin is not on offer (to that
        ship), or one of the ship's crew is still out in it - an offer withdrawn under a
        suit would leave its console with no way to send a second crew member after the
        first."""
def eva_relic_open (relic_key, volume=None, name=None, ship=None):
    """Offer a ruin to a crew: SUIT UP goes there, and a crew party is open to join.
    
    The two halves a mission used to write by hand - `eva_offer` says WHICH ruin, and
    `boarding_invite_crew` gives the Boarding Party app a roster to show - in the one
    order that works.
    
    Args:
        relic_key: the relic, as `relics_load` registered it.
        volume (optional): the volume name. Defaults to the one the relic BUILT, which is
            the only safe guess - see `relic_volume_name`.
        name (optional): what the party is called on screen. Defaults to the relic's own.
        ship (optional): the ship whose crew is offered it. **Left out, the ruin is
            offered to EVERY player ship** - what this call has always done - and the
            party is opened from the ship nearest the entrance. Named, the offer is that
            ship's own, and another ship's offer is not touched.
    
    Returns:
        bool: True when this ruin is on offer to that ship afterwards. False is ordinary
        and logged once: the relic is not registered, a mission's own boarding party is
        open, or one of that ship's crew is still out in a different ruin.
    
    IDEMPOTENT BY IDENTITY. Asked again for the ruin already on offer it changes nothing -
    not the offer (a mission that offered it first keeps its own `hull=`), and not the
    party, so nobody who has a place loses it."""
def eva_relic_opened (ship=None):
    """The ruin this wiring has on offer, or None. Not `eva_offered()`: that answers for
    an offer a mission made by hand as well.
    
    Args:
        ship (optional): the ruin on offer to THIS ship. Left out: the one offered to
            every ship, else the lowest-numbered ship's - with one ship, the only one."""
def eva_relic_released (relic_key):
    """A ruin is being torn down: bring its suits in and withdraw its offer.
    
    What `relic_release` calls. A galaxy tears a system down under the crew - the ship
    jumped - and a suit left flying a volume that no longer exists has no route home and
    a console pointed at nothing. Each console out there is put back at its post, the
    same way COME ABOARD does it.
    
    Returns how many consoles were brought in. Never raises."""
def eva_relic_ship (relic_key, within=None):
    """The player ship nearest a ruin's entrance, or None.
    
    Args:
        within (float, optional): only a ship at most this far from the entrance.
    
    Returns:
        The ship's id, or None when there is no such relic or no ship that near."""
def eva_relics_auto (on=None):
    """Read, or set, whether built ruins are offered to the crew automatically.
    
    ON unless a mission says otherwise. `eva_relics_auto(False)` at the top of a story is
    the opt-out for a mission that calls `eva_relic_open` itself; it also withdraws
    nothing - an offer already made stays until the mission closes it.
    
    Returns:
        bool: the setting in force."""
def eva_relics_clear ():
    """Forget what is on offer and stop the pass. Called by `eva_clear()`.
    
    The `eva_relics_auto` choice is NOT cleared here: it is the mission's, made once at
    the top of its story, and `eva_clear()` is also something a mission may call in the
    middle of a game. It lives on the shared agent, which a mission reset rebuilds."""
def eva_relics_count ():
    """Reset-ledger probe: a ruin still on offer (to any ship), or a pass still ticking."""
def eva_relics_pass (reach=None):
    """One proximity pass: each ship is offered the ruin IT is at, and loses the one it
    left.
    
    Asks the WORLD each time rather than keeping a list: every registered relic whose
    space is standing is a candidate, and every player ship is asked about separately, so
    a ruin built late, rebuilt on a revisit or torn down - or a second ship arriving at a
    second ruin - needs no bookkeeping here.
    
    Returns:
        A relic key on offer afterwards, or None: the one a mission offered every ship,
        else the lowest-numbered ship's. With one ship that is simply "the one on offer"."""
def eva_relics_unwatch ():
    """Stop the proximity pass."""
def eva_relics_watch (seconds=2.0):
    """Start the proximity pass. Idempotent - asking twice watches once.
    
    Does nothing, and returns None, when a mission turned the automatic wiring off."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
