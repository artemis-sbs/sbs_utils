"""Suiting up, and coming back in.

The door between a bridge console and an EVA console, and the exact counterpart of
`boarding_go_down` / `boarding_go_up` in `boarding_gui.py`. Beaming down puts a character
on a floor and assigns the console to the ship whose floor it is; going EVA puts a
character in a SUIT and assigns the console to the suit, because the suit is the thing the
3D view has to draw.

Everything else about the morph is the same, including the two renames it has to defend
against - and they are the reason this is not three lines:

* **`gui_console_enter` is given the console's OWN ship, never the relic.** The door
  re-asserts the crew seat, and a seat resolved against another hull renames anybody who
  was auto-named. The crew would suit up and come out as strangers.
* **The name is re-asserted afterwards anyway**, because the door autonames per
  (ship, CONSOLE) seat and `eva_crew` is a different seat from `science`. Correct for a
  bridge crew changing station; wrong for the same people putting on a suit.

Both of those are `boarding_gui.py`'s findings, paid for there. This inherits them rather
than rediscovering them.
"""
from ...helpers import FrameContext

#: What a console BECOMES out in a relic. Its own type, not the grid one: the two draw
#: different maps, and `gui_console_enter` does nothing at all when the type is unchanged.
EVA_CONSOLE = "eva_crew"

#: On the client. The post to put it back at, and the ship to put it back on.
RETURN_KEY = "EVA_RETURN"
HOME_KEY = "EVA_HOME_SHIP"


def _client(client_id=None):
    if client_id is not None:
        return client_id
    page = FrameContext.page
    return getattr(page, "client_id", None) if page is not None else None


def eva_go_out(client_id, relic_key=None):
    """Morph this console into a suit, out in the relic, and show it what it sees.

    Args:
        client_id: the console going out.
        relic_key (optional): which relic. Defaults to the one :func:`eva_offer` named.

    Returns:
        bool: False when this console is not holding anybody, or nothing is on offer.
    """
    from ..boarding import boarding_held, boarding_me
    from ..eva import eva_offered, eva_watch
    from ..crew import crew_assign
    from ..inventory import get_inventory_value, set_inventory_value
    from ..query import is_client_id, to_id
    from ..signal import signal_emit
    from .console import gui_console_enter
    from .viewscreen import viewscreen_home_ship

    if not boarding_held(client_id):
        return False
    offer = eva_offered() or {}
    key = relic_key or offer.get("relic")
    if not key:
        return False

    # Captured BEFORE anything moves, because the move is what makes it unanswerable.
    home = viewscreen_home_ship(client_id)
    set_inventory_value(client_id, HOME_KEY, home)
    post_name = get_inventory_value(client_id, "CREW_NAME", None)
    post_face = get_inventory_value(client_id, "CREW_FACE", None)
    post_portrait = get_inventory_value(client_id, "CREW_PORTRAIT", None)
    if not get_inventory_value(client_id, RETURN_KEY, None):
        set_inventory_value(client_id, RETURN_KEY,
                            get_inventory_value(client_id, "CONSOLE_TYPE", "helm"))

    gui_console_enter(client_id, EVA_CONSOLE, ship=home)
    if post_name:
        crew_assign(client_id, home, EVA_CONSOLE, own_name=post_name,
                    own_face=post_face, own_portrait=post_portrait)

    suit = _give_a_suit(client_id, key, offer, home)
    if suit is None:
        return False

    if is_client_id(client_id) or client_id == 0:
        # AFTER the door, and unconditionally for a real console: `gui_console_enter`
        # returns False and does nothing when the type is unchanged, so a console moving
        # between two relics would never be re-assigned if this were left to it.
        #
        # THE GUARD IS NOT CEREMONY - the engine ASSERTS when handed an id that is not a
        # client, which is a hard stop on a live bridge rather than a logged warning.
        # `or client_id == 0` because the server console is id 0 and `is_client_id` tests
        # a bit that 0 does not have.
        FrameContext.context.sbs.assign_client_to_ship(client_id, to_id(suit))

    eva_watch()
    signal_emit("eva_went_out", {"EVA_CLIENT": client_id,
                                 "EVA_WHO": boarding_me(client_id),
                                 "EVA_SUIT": to_id(suit),
                                 "EVA_RELIC": key})
    return True


def _give_a_suit(client_id, relic_key, offer, home):
    """Put this console's character in a suit, and hand the console that suit.

    Idempotent: a console that already has one keeps it, so a second suit-up - a
    reconnect, a move between relics - does not leave an abandoned ship drifting in the
    ruin for the rest of the mission.
    """
    from ..boarding import boarding_me
    from ..eva import eva_entry, eva_suit_of, eva_suit_spawn, eva_take
    from ..query import to_object
    who = boarding_me(client_id)
    if not who:
        return None
    suit = eva_suit_of(who)
    if not suit:
        x, y, z = eva_entry(relic_key, offer)
        side = offer.get("side")
        if side is None:
            ship = to_object(home)
            side = getattr(ship, "side", None) if ship is not None else None
        suit = eva_suit_spawn(who, relic_key, x, y, z, hull=offer.get("hull"),
                              side=side, volume=offer.get("volume"))
    if suit is not None:
        eva_take(client_id, suit, relic_key, volume=offer.get("volume"), home=home)
    return suit


def eva_go_in(client_id):
    """Put this console back at the post it left, and take its suit away.

    The suit is DELETED rather than parked. A boarding figure is left standing because the
    interior persists and somebody may take it over; a suit is a ship in open space, and
    an abandoned one is a contact on everybody's radar for the rest of the mission.
    """
    from ..boarding import boarding_beam_up
    from ..eva import eva_lifeform_of, eva_my_suit, eva_release
    from ..inventory import get_inventory_value, set_inventory_value
    from ..links import unlink
    from ..signal import signal_emit
    from ..space_objects import delete_object
    from .console import gui_console_enter

    suit = eva_my_suit(client_id)
    if not boarding_beam_up(client_id):
        return False
    home = get_inventory_value(client_id, HOME_KEY, None)
    back = get_inventory_value(client_id, RETURN_KEY, None) or "helm"
    set_inventory_value(client_id, RETURN_KEY, None)
    set_inventory_value(client_id, HOME_KEY, None)
    eva_release(client_id)
    if suit:
        who = eva_lifeform_of(suit)
        if who:
            # Both directions. The lifeform survives - it is `boarding.py`'s - and a stale
            # "suit" link on it would hand the next screen a dead ship id.
            unlink(who, "suit", suit)
            unlink(suit, "lifeform", who)
        try:
            delete_object(suit)
        except Exception:                                # noqa: BLE001
            pass
    gui_console_enter(client_id, back, ship=home)
    signal_emit("eva_came_back", {"EVA_CLIENT": client_id,
                                  "EVA_CONSOLE": back,
                                  "EVA_HOME": home})
    return True


def eva_home_ship(client_id):
    """The ship this console came from, read back after the morph overwrote the obvious
    place to look for it."""
    from ..inventory import get_inventory_value
    return get_inventory_value(client_id, HOME_KEY, None)


def eva_console_type():
    """What an EVA console's `CONSOLE_TYPE` is. A FUNCTION, because MAST only sees
    functions and a route has to name it."""
    return EVA_CONSOLE
