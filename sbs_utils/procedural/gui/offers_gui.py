"""The Offers board: what the world has for you that you have not taken.

The Quests tab answers "what am I doing?". This answers a different question - "what is
there?" - and it is the one a crew could not ask before. An Open Universe station job or
a hangar sortie is not a quest until AFTER you accept it, so neither could appear
anywhere until you had already found it by hailing the right object.

Deliberately a sibling of ``status_gui``, not a generalization of it: that board's rows
are APP registrations that happen to carry a badge, and an offer is not an app. Same
shape, same chrome, same empty state, different question.

MOSTLY THE BOARD DISCOVERS AND SOMETHING ELSE TAKES. A quest is accepted on the Quests
tab, where ``quest_tab_controls_gate`` already resolves who may act (a per-quest ``Accept
On:`` override, then ``QUEST_ACCEPT_CONSOLES``); a second implementation of that policy
would be two places that must agree and eventually will not. So a quest offer carries an
``app`` and the click goes there.

THE EXCEPTION IS AN OFFER NOTHING ELSE CAN ACCEPT. A hangar sortie is not a quest until
it is assigned, so sending a pilot to the Quests app to take one shows them a list that
cannot contain the thing they just clicked - which is exactly what it did. Such an offer
carries a ``take`` callable and is accepted here. A row that this console cannot act on
says WHERE instead.
"""
from ...helpers import FrameContext
from ..offer import offers, offer_context_here
from .epadd import ACCENT, DIM, _esc, epadd_console_name, gui_app_open, gui_app_chrome


#: An offer kind -> the icon MEANING that draws it. Meanings, never sheet indexes, so a
#: mission can re-skin the board without touching this file.
_KIND_ICON = {
    "job": "quest.job",
    "sortie": "quest.objective",
    "trade": "quest.job",
    "contact": "quest.beat",
    "lore": "quest.arc",
}


def _console_can_take(row, console):
    """Whether THIS console may act on this offer.

    An empty spec means any console, which is what ``_quest_console_set`` already means
    by it - so an offer that names no consoles is takeable everywhere rather than nowhere.
    """
    from ..quest_driver import _quest_console_allowed
    if row.get("pending"):
        return False
    return _quest_console_allowed(console, row.get("consoles"))


def offer_rows(client_id=None, ship_id=None, console=None):
    """The board's rows: every offer, each with `can_take` resolved for this console.

    Resolved ONCE here rather than in the template, because a template runs per visible
    row per build and this walks a console spec each time.
    """
    if client_id is None and ship_id is None:
        client_id, ship_id = offer_context_here()
    if console is None:
        page = FrameContext.page
        console = epadd_console_name(getattr(page, "console", None) if page else None)
    rows = []
    for r in offers(client_id=client_id, ship_id=ship_id, console=console):
        rows.append(dict(
            {k: r.get(k) for k in ("key", "title", "detail", "kind", "source",
                                   "agent_id", "where", "app", "route", "consoles",
                                   "pending", "sort", "data", "take")},
            can_take=_console_can_take(r, console)))
    return rows


def _row_template(item):
    """One board row.

    Sizes its ROW and returns None - a listbox only calls resize_to_content() when the
    template returns nothing.
    """
    from .row import gui_row
    from .text import gui_text
    from .icon import gui_icon_name

    gui_row("row-height: 1.8em;")
    icon = _KIND_ICON.get(item.get("kind"), "quest.job")
    # A pending offer is dimmed rather than hidden: knowing the work exists is the whole
    # point of the board, even when somebody else has to hand it to you.
    color = ACCENT if item.get("can_take") else DIM
    gui_icon_name(icon, color=color, style="col-width: content;")
    gui_text(f"$text:{_esc(item['title'])};font:gui-3;overflow:shrink;",
             style="col-width: 30;")
    if item.get("source"):
        gui_text(f"$text:{_esc(str(item['source']))};font:gui-1;color:{DIM};"
                 f"overflow:shrink;", style="col-width: 16;")
    # WHERE it can be taken, but only when this console cannot take it. On a console that
    # CAN, the line is just noise telling you to do what you are already able to do.
    tail = item.get("detail") or ""
    if not item.get("can_take") and item.get("where"):
        tail = item["where"]
    if tail:
        gui_text(f"$text:{_esc(str(tail))};font:gui-1;color:{DIM};overflow:ellipsis;")


def gui_offers_screen(title="Offers"):
    """Draw the Offers board for this console."""
    from .section import gui_section
    from .row import gui_row
    from .text import gui_text
    from .listbox import gui_list_box
    from .message import gui_message_callback

    rows = offer_rows()

    gui_app_chrome(title, subtitle=(None if rows else "nothing on offer"))
    gui_section(style="area: 0, 80px, 100, 100;")

    if not rows:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:Nothing on offer.;font:gui-3;color:{DIM};")
        gui_row("row-height: content; padding: 24px, 4px, 24px, 0;")
        gui_text(f"$text:Work the world has for you shows up here.;"
                 f"font:gui-1;color:{DIM};")
        return None

    gui_row("padding: 24px, 12px, 24px, 12px;")
    lb = gui_list_box(rows, "item-gap: 0.25em;", item_template=_row_template,
                      select=True, reveal=True)

    def _open(event, sender):
        item = lb.get_value()
        if item is None:
            return
        # TAKE IT HERE IF IT CAN BE. An offer that nothing else can accept carries its
        # own means of acceptance - a sortie is not a quest until it is assigned, so
        # sending a pilot to the Quests app to take one shows them the empty list that
        # does not yet contain the thing they just clicked.
        take = item.get("take")
        if callable(take) and item.get("can_take"):
            cid, _ship = offer_context_here()
            try:
                take(cid, item)
            except Exception as e:                        # noqa: BLE001
                from ..execution import log
                log(f"could not take offer {item.get('key')!r}: "
                    f"{type(e).__name__}: {e}", "offer", "warning")
            return
        # Otherwise go to where the work IS taken - the reason you read a board is to go
        # and do something about it. An offer with neither (a station job taken by
        # hailing) has nowhere to send you, so the row's `where` line is the answer and
        # the click does nothing rather than opening something unrelated.
        app = item.get("app")
        if app:
            gui_app_open(app)

    gui_message_callback(lb, _open)
    return lb
