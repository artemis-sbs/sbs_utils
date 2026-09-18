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
    """One board row: what it is, and who is offering it. TWO COLUMNS, not three.

    The objective used to be a third column sharing the row, and with the title at 30 and
    the source at 16 there was almost nothing left for it - so "Destroy 10 raiders" wrapped
    one character wide and ran down the screen. A row says WHICH offer this is; what it
    asks of you belongs in the detail line, where there is room for a sentence.

    Sizes its ROW and returns None - a listbox only calls resize_to_content() when the
    template returns nothing.
    """
    from .row import gui_row
    from .text import gui_text
    from .icon import gui_icon_name

    gui_row("row-height: 1.8em;")
    icon = _KIND_ICON.get(item.get("kind"), "quest.job")
    # A pending offer is dimmed rather than hidden: knowing the work exists is the point
    # of the board, even when somebody else has to hand it to you.
    color = ACCENT if item.get("can_take") else DIM
    gui_icon_name(icon, color=color, style="col-width: content;")
    gui_text(f"$text:{_esc(str(item.get('title') or ''))};font:gui-3;overflow:shrink;")
    if item.get("source"):
        gui_text(f"$text:{_esc(str(item['source']))};font:gui-1;color:{DIM};"
                 f"overflow:shrink;", style="col-width: 22;")


def _detail_text(item):
    """The line under the list. One string, so it can be pushed into a held widget.

    A HELD WIDGET AND A NEW VALUE - never a rebuilt panel. Refilling a `gui_sub_section`
    leaves the previous fill painted underneath (the ePADD inbox's three superimposed
    messages), and rebuilding the page to show a different line is the anti-pattern that
    manufactures bugs which read as layout faults.
    """
    if item is None:
        return "Select an offer to see what it asks."
    bits = []
    if item.get("detail"):
        bits.append(str(item["detail"]))
    # Where it is taken, but only when this console cannot take it - on one that can, the
    # Take button below is the answer and the line would just be telling you to do what
    # you are already doing.
    if not (callable(item.get("take")) and item.get("can_take")) and item.get("where"):
        bits.append(str(item["where"]))
    return "   ".join(bits) if bits else str(item.get("title") or "")


def _take_label(item):
    """What the button says, so it can be pushed into the held button's style."""
    if item is None:
        return "Take"
    if callable(item.get("take")) and item.get("can_take"):
        return "Take"
    return "-"


def gui_offers_screen(title="Offers"):
    """Draw the Offers board for this console.

    BUILT ONCE. Selecting updates the detail line's VALUE and the list's own rows; it
    never rebuilds the page and never jumps to a repaint label. That is not an
    optimisation - a repaint re-sends every widget on the screen over the wire, and two
    builds landing at once is what makes a board look scrambled.
    """
    from .section import gui_section
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .listbox import gui_list_box
    from .message import gui_message_callback

    cid, ship = offer_context_here()
    rows = offer_rows(cid, ship)

    gui_app_chrome(title, subtitle=(None if rows else "nothing on offer"))
    gui_section(style="area: 0, 80px, 100, 100;")

    if not rows:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:Nothing on offer.;font:gui-3;color:{DIM};")
        gui_row("row-height: content; padding: 24px, 4px, 24px, 0;")
        gui_text(f"$text:Work the world has for you shows up here.;"
                 f"font:gui-1;color:{DIM};")
        return None

    gui_row("padding: 24px, 12px, 24px, 4px;")
    lb = gui_list_box(rows, "item-gap: 0.25em;", item_template=_row_template,
                      select=True, reveal=True)

    # THE DETAIL LINE AND THE BUTTON ARE BUILT ONCE AND UPDATED. Both are held, so a
    # selection sets a value rather than throwing the screen away and sending it again.
    first = lb.get_value()

    def _line(item):
        return (f"$text:{_esc(_detail_text(item))};font:gui-1;color:{DIM};"
                f"overflow:shrink;")

    # CLIENT BOUND AT BUILD TIME. `MessageHandler` calls a handler with no arguments, so
    # one that reads the ambient client works until the frame belongs to somebody else -
    # and a job granted to the wrong client lands on nobody's Quests tab, which is
    # exactly how this failed. No REQUIRED parameter, so the no-argument call is correct.
    def _take(_cid=cid):
        item = lb.get_value()
        if item is None or not callable(item.get("take")) or not item.get("can_take"):
            return
        try:
            item["take"](_cid, item)
        except Exception as e:                            # noqa: BLE001
            from ..execution import log
            log(f"could not take offer {item.get('key')!r}: "
                f"{type(e).__name__}: {e}", "offer", "warning")
            return
        # UPDATE, DO NOT REPAINT. The taken row is gone from what the providers answer,
        # so the list is re-rendered from the new answer and the two held widgets are set
        # - no page rebuild, no jump, nothing re-sent that did not change.
        lb.items = offer_rows(_cid, ship)
        nxt = lb.get_value()
        detail.value = _line(nxt)
        take_btn.update(_take_label(nxt))

    def _select(event, sender):
        item = lb.get_value()
        detail.value = _line(item)
        take_btn.update(_take_label(item))

    gui_row("row-height: 1.6em; padding: 24px, 2px, 24px, 2px;")
    detail = gui_text(_line(first))
    gui_row("row-height: 2.2em; padding: 24px, 2px, 24px, 8px;")
    # Wired at CONSTRUCTION, not assigned afterwards - `on_press` is what the button
    # carries into its own handler registration.
    take_btn = gui_button(_take_label(first), on_press=_take)

    gui_message_callback(lb, _select)
    return lb
