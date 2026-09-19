from sbs_utils.helpers import FrameContext
def _console_can_take (row, console):
    """Whether THIS console may act on this offer.
    
    An empty spec means any console, which is what ``_quest_console_set`` already means
    by it - so an offer that names no consoles is takeable everywhere rather than nowhere."""
def _listed_elsewhere (r):
    """True for an offer that its own app lists and accepts, and the Offers app cannot.
    
    It names an ``app`` and carries no ``take``, so the Offers list could only show it,
    with a button that does nothing. The rule is the record's shape, not its provider, so
    a mission offer pointing at its own app behaves the same way."""
def epadd_console_name (console):
    """The name a script would use for a console, whatever the engine calls it."""
def offer_board_count_here ():
    """How many offers the Offers app lists for THIS console that could be acted on -
    the tile's gate, so the tile never opens onto an empty list.
    
    Not ``offer_count_here``: that counts every offer, including one left to its own
    app, which this app does not list."""
def offer_context_here ():
    """``(client_id, ship_id)`` for the console currently being drawn, or ``(None, None)``.
    
    The ship is the console's HOME ship, not ``get_ship_of_client``: a main screen
    driving a cinematic answers with the SUBJECT of the shot, so a badge would count the
    enemy's jobs. Same rule the log panel's scope already follows."""
def offer_rows (client_id=None, ship_id=None, console=None):
    """Every offer the Offers app lists, each with `can_take` resolved for this console."""
def offers (client_id=None, ship_id=None, object_id=None, kinds=None, console=None):
    """Every offer on the table, sorted.
    
    Args:
        client_id: The console asking, when there is one.
        ship_id: The ship the crew are flying.
        object_id: Narrow to what THIS object is offering. ``None`` (the default)
            means everything for this crew.
        kinds: Restrict to these kinds - a string, or a list of them.
        console (str): The console type asking, for providers that are station-specific.
    
    Returns:
        list: ``offer_record``s, ``pending`` ones included. Sorted by ``sort`` then
        ``title``, so a board's order does not move between frames."""
