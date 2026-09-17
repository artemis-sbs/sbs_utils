from sbs_utils.helpers import FrameContext
def _client (client_id=None):
    ...
def _give_a_suit (client_id, relic_key, offer, home):
    """Put this console's character in a suit, and hand the console that suit.
    
    Idempotent: a console that already has one keeps it, so a second suit-up - a
    reconnect, a move between relics - does not leave an abandoned ship drifting in the
    ruin for the rest of the mission."""
def eva_console_type ():
    """What an EVA console's `CONSOLE_TYPE` is. A FUNCTION, because MAST only sees
    functions and a route has to name it."""
def eva_go_in (client_id):
    """Put this console back at the post it left, and take its suit away.
    
    The suit is DELETED rather than parked. A boarding figure is left standing because the
    interior persists and somebody may take it over; a suit is a ship in open space, and
    an abandoned one is a contact on everybody's radar for the rest of the mission."""
def eva_go_out (client_id, relic_key=None):
    """Morph this console into a suit, out in the relic, and show it what it sees.
    
    Args:
        client_id: the console going out.
        relic_key (optional): which relic. Defaults to the one :func:`eva_offer` named.
    
    Returns:
        bool: False when this console is not holding anybody, or nothing is on offer."""
def eva_home_ship (client_id):
    """The ship this console came from, read back after the morph overwrote the obvious
    place to look for it."""
