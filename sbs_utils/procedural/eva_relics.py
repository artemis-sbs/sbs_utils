"""The wiring between a built ruin and the crew who can go into it.

`eva.py` is the suit and `amd_relics.py` is the ruin. What joined them used to be a page of
MAST every mission had to copy out of Storm's Beacon: answer `relic_built`, call
`eva_offer`, open a crew party so the Boarding Party app had something to show, and
remember to do it on a `//shared/signal` route. A mission that did not copy it had a ruin
nobody could enter, and nothing said so.

This is that page, once. With LegendaryMissions' `boarding` addon loaded it is AUTOMATIC:

* a built ruin offers SUIT UP while a player ship is within `EVA_RELIC_RANGE` of its
  entrance, and
* withdraws the offer when the ship leaves - unless somebody is still out there.

An offer a MISSION made by hand is never withdrawn by this, and never replaced: only the
offers the proximity pass made are its own to take back.

`eva_relics_auto(False)` is the opt-out, for a mission that wires its ruins by hand with
`eva_relic_open` / `eva_relic_close`.

WHY PROXIMITY, AND WHY ONE AT A TIME
------------------------------------
`eva_offer` is ONE slot: the relic a console suits up into. Offering every ruin the moment
it is built meant the last one built won, and SUIT UP worked from the far side of the map.
Following the ship answers both: the ruin on offer is the one the crew is AT.

It is still one slot. Two player ships at two ruins get the offer of whichever ruin was
reached first, and the second ruin waits its turn. Making the offer per ship is a change
to `eva_offer` itself, not to this.

IDENTITY, NOT A LATCH. Every verb here can be called again - by a mission's own route that
still does the same job, by a second `relic_built`, by the tick - and does nothing the
second time. That is what lets a mission written before this existed keep its own
handlers and still work.
"""
from ..agent import Agent
from .query import to_id, to_object

#: How close to a ruin's entrance a player ship has to be for SUIT UP to be offered.
EVA_RELIC_RANGE = 3000.0

#: How much further out the ship has to go before the offer is withdrawn again, as a
#: multiple of the range. A ship holding station right on the line would otherwise open and
#: close the party every pass.
EVA_RELIC_LEAVE = 1.15

_STATE_KEY = "__EVA_RELICS__"        # {"open": relic key, "refused": {relic key: why}}
_AUTO_KEY = "__EVA_RELICS_AUTO__"    # False when a mission wires by hand
_TICK_KEY = "__EVA_RELICS_TICK__"
_BY_PASS = "proximity"               # the mark on an offer the proximity pass made


def _state():
    state = Agent.SHARED.get_inventory_value(_STATE_KEY, None)
    return state if isinstance(state, dict) else {}


def _save(state):
    Agent.SHARED.set_inventory_value(_STATE_KEY, state)


def _say_once(relic_key, why, text):
    """One log line per (relic, reason) - the tick asks every couple of seconds, and a
    refusal repeated at that rate buries the line that explains it."""
    state = _state()
    refused = dict(state.get("refused") or {})
    if refused.get(relic_key) == why:
        return
    refused[relic_key] = why
    state["refused"] = refused
    _save(state)
    from .execution import log
    log(text, "eva", "warning")


def _unsay(relic_key):
    state = _state()
    refused = dict(state.get("refused") or {})
    if relic_key in refused:
        del refused[relic_key]
        state["refused"] = refused
        _save(state)


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _eva_relic_built(relic_key):
    """The record of a relic whose space is standing, else None."""
    from .amd_relics import relic_record, relic_volume_name
    from .volume import volume_get
    rec = relic_record(relic_key)
    if rec is None or volume_get(relic_volume_name(rec)) is None:
        return None
    return rec


def eva_relic_ship(relic_key, within=None):
    """The player ship nearest a ruin's entrance, or None.

    Args:
        within (float, optional): only a ship at most this far from the entrance.

    Returns:
        The ship's id, or None when there is no such relic or no ship that near.
    """
    from .amd_relics import relic_entrance
    from .roles import role
    door = relic_entrance(relic_key)
    if door is None:
        return None
    best, best_d = None, float("inf")
    for ship_id in sorted(role("__player__")):
        ship = to_object(ship_id)
        if ship is None:
            continue
        p = ship.pos
        d = _dist((p.x, p.y, p.z), door)
        if within is not None and d > float(within):
            continue
        if d < best_d:
            best, best_d = ship_id, d
    return best


def _eva_relic_party_is_ours(invite):
    """Whether an open invitation is one this wiring may adopt or close.

    A CREW party with nowhere to walk - no `site`, no tile `area` - is the EVA party by
    construction: there is no other reason to cast the bridge and give them no floor. A
    party a mission CAST (three named people), or one with an interior to beam down into,
    is the mission's own and is never touched.
    """
    return (bool(invite.get("crew")) and invite.get("site") is None
            and invite.get("area") is None)


def eva_relic_open(relic_key, volume=None, name=None, ship=None):
    """Offer a ruin to the crew: SUIT UP goes there, and a crew party is open to join.

    The two halves a mission used to write by hand - `eva_offer` says WHICH ruin, and
    `boarding_invite_crew` gives the Boarding Party app a roster to show - in the one
    order that works.

    Args:
        relic_key: the relic, as `relics_load` registered it.
        volume (optional): the volume name. Defaults to the one the relic BUILT, which is
            the only safe guess - see `relic_volume_name`.
        name (optional): what the party is called on screen. Defaults to the relic's own.
        ship (optional): the ship the crew leaves from. Defaults to the player ship
            nearest the entrance.

    Returns:
        bool: True when this ruin is on offer afterwards. False is ordinary and logged
        once: the relic is not registered, a mission's own boarding party is open, or
        somebody is still out in a different ruin.

    IDEMPOTENT BY IDENTITY. Asked again for the ruin already on offer it changes nothing -
    not the offer (a mission that offered it first keeps its own `hull=`), and not the
    party, so nobody who has a place loses it.
    """
    from .amd_relics import relic_record, relic_volume_name
    from .boarding import (INVITE_KEY, boarding_invitation, boarding_invite_crew,
                           boarding_team)
    from .eva import eva_offer, eva_offered, eva_suits
    rec = relic_record(relic_key)
    if rec is None:
        _say_once(relic_key, "unknown",
                  f"EVA: relic '{relic_key}' is not registered, so it was not offered. "
                  f"Load its file first (relics_load / relics_spawn).")
        return False

    # A MISSION'S OWN PARTY COMES FIRST, and the reason is the button. `eva_offered()` is
    # what turns BEAM DOWN into SUIT UP, so putting a ruin on offer while a mission has
    # three named people waiting to beam down to a station would send them out of an
    # airlock instead. Never replaced, never re-labelled.
    invite = boarding_invitation()
    if invite is not None and not _eva_relic_party_is_ours(invite):
        _say_once(relic_key, "party",
                  f"EVA: relic '{relic_key}' was not offered because the mission has a "
                  f"boarding party of its own open ('{invite.get('title')}'). It is "
                  f"offered once that one is closed.")
        return False

    offer = eva_offered()
    if offer is not None and offer.get("relic") != relic_key:
        if eva_suits(offer.get("relic")):
            _say_once(relic_key, "busy",
                      f"EVA: relic '{relic_key}' was not offered because somebody is "
                      f"still out in '{offer.get('relic')}'. It is offered when they "
                      f"are back aboard.")
            return False
        offer = None
    if offer is None:
        # No `hull=`: `eva_suit_hull()` answers at the moment a suit is made, so a
        # mission that sets its hull after the ruin is built still gets it.
        eva_offer(relic_key, volume=volume or relic_volume_name(rec))
    _unsay(relic_key)

    if ship is None:
        ship = eva_relic_ship(relic_key)
    ship_id = to_id(ship) if ship is not None else None
    title = name or rec.get("name") or relic_key
    if ship_id is not None:
        same = invite is not None and invite.get("ship") == ship_id
        if invite is None or (not same and not boarding_team()):
            # `boarding_invite_crew` is identity too: a console that already has a body
            # keeps it, so opening the party again is the same people.
            invite = boarding_invite_crew(ship_id, title=title)
        # OURS, said on the invitation, so `eva_relic_close` knows which ruin it is for.
        if invite.get("eva_relic") != relic_key:
            invite["eva_relic"] = relic_key
            Agent.SHARED.set_inventory_value(INVITE_KEY, invite)

    state = _state()
    if state.get("open") != relic_key:
        state["open"] = relic_key
        _save(state)
    return True


def eva_relic_close(relic_key=None, force=False):
    """Withdraw a ruin's offer, and close the crew party that went with it.

    Args:
        relic_key (optional): which ruin. Defaults to whichever is on offer.
        force (bool, optional): withdraw even with somebody still out. For a ruin that is
            being torn down; see `eva_relic_released`.

    Returns:
        bool: False when that ruin is not the one on offer, or somebody is still out in
        it - an offer withdrawn under a suit would leave its console with no way to send
        a second crew member after the first.
    """
    from .boarding import boarding_invitation, boarding_invite_close
    from .eva import eva_offer_clear, eva_offered, eva_suits
    offer = eva_offered()
    if offer is None:
        return False
    key = offer.get("relic")
    if relic_key is not None and key != relic_key:
        return False
    if not force and eva_suits(key):
        return False
    eva_offer_clear()
    invite = boarding_invitation()
    if invite is not None and _eva_relic_party_is_ours(invite):
        boarding_invite_close()
    state = _state()
    if state.get("open") is not None:
        state["open"] = None
        _save(state)
    return True


def eva_relic_opened():
    """The ruin this wiring has on offer, or None. Not `eva_offered()`: that answers for
    an offer a mission made by hand as well."""
    return _state().get("open")


def eva_relic_released(relic_key):
    """A ruin is being torn down: bring its suits in and withdraw its offer.

    What `relic_release` calls. A galaxy tears a system down under the crew - the ship
    jumped - and a suit left flying a volume that no longer exists has no route home and
    a console pointed at nothing. Each console out there is put back at its post, the
    same way COME ABOARD does it.

    Returns how many consoles were brought in. Never raises.
    """
    from .eva import eva_clear, eva_drivers, eva_my_relic, eva_my_suit
    back = 0
    for cid in list(eva_drivers()):
        if eva_my_relic(cid) != relic_key or eva_my_suit(cid) is None:
            continue
        try:
            # Lazily, and from `gui`: the way home re-seats a console, which is screen
            # work. `procedural` is what `gui` is built on, never the other way round.
            from .gui.eva_gui import eva_go_in
            if eva_go_in(cid):
                back += 1
        except Exception as e:                            # noqa: BLE001
            from .execution import log
            log(f"EVA: console {cid} could not be brought in from '{relic_key}': {e}",
                "eva", "warning")
    # Whatever is left goes with the ruin: a suit nobody is flying, and a suit a SCRIPT
    # handed a console without a boarding party behind it (`eva_take` alone), which the
    # door above has no way home for. The console is told it flies nothing, or it would
    # go on steering a ship that is about to be deleted.
    try:
        from .eva import eva_release
        for cid in list(eva_drivers()):
            if eva_my_relic(cid) == relic_key:
                eva_release(cid)
        eva_clear(relic_key)
    except Exception:                                    # noqa: BLE001
        pass
    eva_relic_close(relic_key, force=True)
    _unsay(relic_key)
    return back


# --- automatic ----------------------------------------------------------------------------

def eva_relics_auto(on=None):
    """Read, or set, whether built ruins are offered to the crew automatically.

    ON unless a mission says otherwise. `eva_relics_auto(False)` at the top of a story is
    the opt-out for a mission that calls `eva_relic_open` itself; it also withdraws
    nothing - an offer already made stays until the mission closes it.

    Returns:
        bool: the setting in force.
    """
    if on is not None:
        Agent.SHARED.set_inventory_value(_AUTO_KEY, bool(on))
        if not on:
            eva_relics_unwatch()
    got = Agent.SHARED.get_inventory_value(_AUTO_KEY, None)
    return True if got is None else bool(got)


def eva_relics_pass(reach=None):
    """One proximity pass: offer the ruin the crew is at, withdraw the one they left.

    Asks the WORLD each time rather than keeping a list: every registered relic whose
    space is standing is a candidate, so a ruin built late, rebuilt on a revisit or torn
    down needs no bookkeeping here.

    Returns:
        The relic key on offer afterwards, or None.
    """
    from .amd_relics import relic_keys
    from .eva import _OFFER_KEY, eva_offered, eva_suits
    reach = float(reach if reach is not None else EVA_RELIC_RANGE)
    offer = eva_offered()
    current = offer.get("relic") if offer is not None else None

    if current is not None:
        # A MISSION'S OWN OFFER STANDS. One made by hand - `eva_offer` from a route the
        # mission wrote before any of this existed - is the mission saying when, and the
        # pass neither withdraws it for being far away nor replaces it with a nearer
        # ruin. Only an offer this pass made is this pass's to take back.
        if offer.get("by") != _BY_PASS:
            return current
        # Somebody out there keeps it open whatever the ship does: the crew's way to send
        # a second boarder after the first is this offer.
        if eva_suits(current):
            return current
        near = None
        if _eva_relic_built(current) is not None:
            near = eva_relic_ship(current, reach * EVA_RELIC_LEAVE)
        if near is not None:
            # Still here. Asked again so a party that was never opened - the ruin was
            # offered before any ship existed - is put right. Identity, so it is free.
            eva_relic_open(current, ship=near)
            return current
        eva_relic_close(current, force=True)

    # Nothing on offer: the ruin with a ship nearest its door, if any is near enough.
    best, best_d, best_ship = None, float("inf"), None
    from .amd_relics import relic_entrance
    for key in relic_keys():
        if _eva_relic_built(key) is None:
            continue
        ship = eva_relic_ship(key, reach)
        if ship is None:
            continue
        p = to_object(ship).pos
        d = _dist((p.x, p.y, p.z), relic_entrance(key))
        if d < best_d:
            best, best_d, best_ship = key, d, ship
    if best is None:
        return None
    if not eva_relic_open(best, ship=best_ship):
        return None
    # OURS, said on the offer itself rather than beside it: a mission that offers the
    # same ruin again afterwards writes a fresh offer without the mark, and from then on
    # it is the mission's.
    made = eva_offered()
    if made is not None and made.get("relic") == best:
        made["by"] = _BY_PASS
        Agent.SHARED.set_inventory_value(_OFFER_KEY, made)
    return best


def _eva_relics_tick(t=None):
    if not eva_relics_auto():
        eva_relics_unwatch()
        return
    try:
        eva_relics_pass()
    except Exception as e:                                # noqa: BLE001
        # A tick that raises is dropped by the dispatcher, and the symptom would be SUIT
        # UP silently never appearing again. Say it and keep ticking.
        from .execution import log
        log(f"EVA: the relic proximity pass failed: {e}", "eva", "warning")


def eva_relics_watch(seconds=2.0):
    """Start the proximity pass. Idempotent - asking twice watches once.

    Does nothing, and returns None, when a mission turned the automatic wiring off.
    """
    if not eva_relics_auto():
        return None
    from ..tickdispatcher import TickDispatcher
    task = Agent.SHARED.get_inventory_value(_TICK_KEY, None)
    if task is not None:
        return task
    task = TickDispatcher.do_interval(_eva_relics_tick, seconds)
    Agent.SHARED.set_inventory_value(_TICK_KEY, task)
    return task


def eva_relics_unwatch():
    """Stop the proximity pass."""
    task = Agent.SHARED.get_inventory_value(_TICK_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:                                # noqa: BLE001
            pass            # already dropped by a reset or the end of the mission
    Agent.SHARED.set_inventory_value(_TICK_KEY, None)


def eva_relics_clear():
    """Forget what is on offer and stop the pass. Called by `eva_clear()`.

    The `eva_relics_auto` choice is NOT cleared here: it is the mission's, made once at
    the top of its story, and `eva_clear()` is also something a mission may call in the
    middle of a game. It lives on the shared agent, which a mission reset rebuilds.
    """
    eva_relics_unwatch()
    Agent.SHARED.set_inventory_value(_STATE_KEY, None)


def eva_relics_count():
    """Reset-ledger probe: a ruin still on offer, or a pass still ticking."""
    n = 1 if _state().get("open") else 0
    return n + (1 if Agent.SHARED.get_inventory_value(_TICK_KEY, None) is not None else 0)
