"""The Offers app's helpers.

The Offers app is NOT a screen of its own. It is the quest-log screen
(LegendaryMissions documents/quest_tab.mast, ``quest_tab_screen``) listing what could be
taken instead of what has been - ``quest_driver.quest_offers_tab_items`` builds those
rows: untaken jobs, plus work that is not a quest yet (a hangar sortie, an Open Universe
station job) in the quest log's own row shape. So the list, the description pane and the
gated Accept button are the Quests tab's, and the two read alike.

What is left here is the COUNT the app's tile is gated on.
"""
from ...helpers import FrameContext
from ..offer import offers, offer_context_here
from .epadd import epadd_console_name


def _console_can_take(row, console):
    """Whether THIS console may act on this offer.

    An empty spec means any console, which is what ``_quest_console_set`` already means
    by it - so an offer that names no consoles is takeable everywhere rather than nowhere.
    """
    from ..quest_driver import _quest_console_allowed
    if row.get("pending"):
        return False
    return _quest_console_allowed(console, row.get("consoles"))


def _listed_elsewhere(r):
    """True for an offer that its own app lists and accepts, and the Offers app cannot.

    It names an ``app`` and carries no ``take``, so the Offers list could only show it,
    with a button that does nothing. The rule is the record's shape, not its provider, so
    a mission offer pointing at its own app behaves the same way.
    """
    return bool(r.get("app")) and not callable(r.get("take"))


def offer_rows(client_id=None, ship_id=None, console=None):
    """Every offer the Offers app lists, each with `can_take` resolved for this console."""
    if client_id is None and ship_id is None:
        client_id, ship_id = offer_context_here()
    if console is None:
        page = FrameContext.page
        console = epadd_console_name(getattr(page, "console", None) if page else None)
    rows = []
    for r in offers(client_id=client_id, ship_id=ship_id, console=console):
        if _listed_elsewhere(r):
            continue
        rows.append(dict(
            {k: r.get(k) for k in ("key", "title", "detail", "description", "kind",
                                   "source", "agent_id", "where", "app", "route",
                                   "consoles", "pending", "sort", "data", "take")},
            can_take=_console_can_take(r, console)))
    return rows


def offer_board_count_here():
    """How many offers the Offers app lists for THIS console that could be acted on -
    the tile's gate, so the tile never opens onto an empty list.

    Not ``offer_count_here``: that counts every offer, including one left to its own
    app, which this app does not list.
    """
    return sum(1 for r in offer_rows() if not r.get("pending"))
