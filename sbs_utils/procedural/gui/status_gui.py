"""The Status app: everything the ship is currently telling you, on one screen.

The apps that carry live state - cargo filling, builds running, quests active, mail
unread - each already put a badge on their own tile. This is those same badges
gathered in one place, larger, for the console that wants a board rather than a
launcher.

It is deliberately NOT a second launcher: an app with nothing to report is left out.
A status board that lists everything is a menu, and the crew already have one.

Selecting a row opens that app, because the reason you read a number is to go and do
something about it.
"""
from ...helpers import FrameContext
from .epadd import (ACCENT, DIM, PANEL_HEAD, _esc, epadd_console_name,
                    gui_app_badge, gui_app_list, gui_app_open, gui_app_chrome)


def status_rows(console=None):
    """The apps with something to say, in the order the PADD lays them out.

    Each row is the app record plus the badge text it produced, so a caller renders
    it without calling a provider a second time - a provider can be expensive and
    can change between calls, and a row that showed one value and opened on another
    would be worse than no row.
    """
    rows = []
    for app in gui_app_list(console):
        badge = gui_app_badge(app)
        if badge:
            rows.append(dict(app, badge=badge))
    return rows


def _row_template(item):
    """One board row: the reading first, because that is what is being read.

    Sizes its ROW and returns None - a listbox only calls resize_to_content() when
    the template returns nothing.
    """
    from .row import gui_row
    from .text import gui_text
    from .icon import gui_icon_name
    gui_row("row-height: 1.8em;")
    if item.get("icon"):
        gui_icon_name(item["icon"], color=ACCENT, style="col-width: content;")
    gui_text(f"$text:{_esc(item['title'])};font:gui-3;overflow:shrink;",
             style="col-width: 26;")
    gui_text(f"$text:{_esc(item['badge'])};font:gui-3;color:{ACCENT};"
             f"overflow:shrink;", style="col-width: 22;")
    if item.get("description"):
        gui_text(f"$text:{_esc(item['description'])};font:gui-1;color:{DIM};"
                 f"overflow:ellipsis;")


def gui_status_screen(title="Status"):
    """Draw the status board for this console."""
    from .section import gui_section
    from .row import gui_row
    from .text import gui_text
    from .listbox import gui_list_box
    from .message import gui_message_callback

    page = FrameContext.page
    console = epadd_console_name(getattr(page, "console", None) if page else None)
    rows = status_rows(console)

    gui_app_chrome(title, subtitle=(f"{len(rows)} reporting" if rows else None))
    gui_section(style="area: 0, 109px, 100, 100;")

    if not rows:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:Nothing to report.;font:gui-3;color:{DIM};")
        gui_row("row-height: content; padding: 24px, 4px, 24px, 0;")
        gui_text(f"$text:Apps put a reading here when they have one.;"
                 f"font:gui-1;color:{DIM};")
        return None

    gui_row("padding: 24px, 12px, 24px, 12px;")
    lb = gui_list_box(rows, "item-gap: 0.25em;", item_template=_row_template,
                      select=True, reveal=True)

    def _open(event, sender):
        item = lb.get_value()
        if item is not None:
            gui_app_open(item["tab"])

    gui_message_callback(lb, _open)
    return lb
