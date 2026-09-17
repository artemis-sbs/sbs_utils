"""The Survey log, on the ePADD - everything the boarding party has read.

    THE xESS ACTS. THE ePADD READS.

The xESS shows the LAST reading and a count, because it is a column beside a map
somebody is watching. This is the other half: the whole record, on a screen that has
room for it, which is the reason a crew member ever stops and opens the tablet.

DELIBERATELY THE SAME SHAPE AS THE INBOX - a listbox of entries beside a reading pane,
built ONCE and then updated in place. `messages_gui` is the proven layout and its
comments are the argument for every choice here; this reuses them rather than inventing
a second way to show a list of records with a body.

**BUILT ONCE, UPDATED IN PLACE.** A repaint re-sends every widget on the sheet across
the network to that console, and a watcher would do it forever. So the pane's widgets
are kept on the page and a tick assigns to them.
"""
from ...helpers import FrameContext
from .epadd import ACCENT, DIM, PANEL, _esc, gui_app_chrome
from ..survey_log import (xess_log_entries, xess_log_count, xess_log_revision)

VIEW_ATTR = "_epadd_survey_view"


def survey_badge():
    """The tile's badge: how many readings the party has taken.

    "" when there are none, which is the convention every PADD provider follows - an
    app with nothing to say says nothing rather than "0".
    """
    n = xess_log_count()
    return "%d filed" % n if n else ""


def survey_relevant():
    """Whether this app is worth a tile.

    A mission with no boarding party in it has never filed a reading, and a tile that
    opens an empty page on every console is the noise the Boarding Party app's own
    condition exists to prevent.
    """
    return xess_log_count() > 0


def gui_survey_screen(title="Survey"):
    """Draw the log and the reading pane."""
    from .section import gui_section, gui_sub_section
    from .row import gui_row
    from .text import gui_text
    from .listbox import gui_list_box
    from .message import gui_message_callback

    page = FrameContext.page
    entries = xess_log_entries()
    n = len(entries)
    # "" rather than None when empty: the widget is made either way, so the count can
    # appear and disappear without the page being rebuilt to carry it.
    subtitle = gui_app_chrome(title, subtitle=("%d readings" % n if n else ""))

    gui_section(style="area: 0, 80px, 100, 100;")
    gui_row("padding: 24px, 12px, 24px, 8px;")

    lb = None
    with gui_sub_section(style="col-width: 42;"):
        gui_row("row-height: content;")
        if not entries:
            gui_text("$text:%s;font:gui-2;color:%s;"
                     % (_esc("Nothing scanned yet."), DIM))
        else:
            # `reveal=` AND `hint=`, for the reason the inbox documents: this page
            # repaints BECAUSE of its own selection, so without the hint a rebuild
            # starts at the top and the row that was clicked lands somewhere else
            # under the mouse.
            lb = gui_list_box(entries, "item-gap: 0.15em;", item_template=_row,
                              select=True, reveal=True)

    pane = gui_sub_section()
    with pane:
        widgets = _pane_build()

    view = {"lb": lb, "pane": pane, "subtitle": subtitle,
            "ids": [e.get("id") for e in entries], "rev": xess_log_revision()}
    view.update(widgets)
    _pane_update(view, entries[0] if entries else None)
    if page is not None:
        setattr(page, VIEW_ATTR, view)

    if lb is not None:
        def _open(event, sender):
            item = lb.get_value()
            if item is None:
                return
            held = getattr(FrameContext.page, VIEW_ATTR, None)
            if held:
                _pane_update(held, item)

        gui_message_callback(lb, _open)
    return view


def _row(item, **kwargs):
    """One reading as a list row. Returns None, so the listbox sizes it.

    NEVER return a size from an item template: the listbox only calls
    `resize_to_content()` when the template returns None, and an item section starts at
    zero height - returning one leaves it degenerate, which kills selection and the
    click region with it.
    """
    from .row import gui_row
    from .text import gui_text
    gui_row("row-height: 1.6em;")
    # `overflow:shrink`: a subject that wraps makes this row a different height from
    # every other one, and the engine does not clip.
    gui_text("$text:%s;font:gui-2;overflow:shrink;" % _esc(_subject_of(item)))
    count = int(item.get("count", 1))
    if count > 1:
        # READ MORE THAN ONCE. The entry is updated rather than appended, so this is
        # how a revisit is visible at all.
        gui_text("$text:%s;font:gui-1;color:%s;col-width: content;"
                 % (_esc("x%d" % count), DIM))


def _subject_of(item):
    """A node's name is `room:thing`; the room half is what a person calls it."""
    subject = str(item.get("subject") or "").strip()
    if not subject:
        return item.get("kind", "reading")
    try:
        from ..boarding_site import boarding_room_name
        return boarding_room_name(subject) or subject
    except Exception:                                    # noqa: BLE001
        return subject


def _pane_build():
    """The reading pane, built ONCE. A tick assigns to these four."""
    from .row import gui_row
    from .text import gui_text, gui_text_area

    gui_row("row-height: 2.2em; padding: 0, 4px, 0, 12px;")
    heading = gui_text("$text: ;font:gui-4;")
    gui_row("row-height: 1.4em; padding: 0, 0, 8px, 12px;")
    byline = gui_text("$text: ;font:gui-1;color:%s;" % DIM)
    gui_row("row-height: 1fr; padding: 0, 0, 0, 12px;")
    # A Control: it clears and scrolls its own region, so assigning to it cannot leave
    # the previous reading painted underneath.
    body = gui_text_area(" ")
    return {"heading": heading, "byline": byline, "body": body}


def _pane_update(view, entry):
    """Show one reading. EVERY part of it, not only the interesting one.

    A pane that is right about the body and stale about the heading describes the
    previous reading, which is worse than a blank one.
    """
    heading = view.get("heading")
    byline = view.get("byline")
    body = view.get("body")
    if heading is None or byline is None or body is None:
        return False
    if entry is None:
        heading.update("$text:%s;font:gui-4;" % _esc("No reading"))
        byline.update("$text: ;font:gui-1;color:%s;" % DIM)
        body.value = " "
        return True
    heading.update("$text:%s;font:gui-4;" % _esc(_subject_of(entry)))
    bits = [b for b in (entry.get("by"), entry.get("at"),
                        ("read x%d" % entry["count"])
                        if int(entry.get("count", 1)) > 1 else None) if b]
    byline.update("$text:%s;font:gui-1;color:%s;" % (_esc(", ".join(bits)), DIM))
    body.value = str(entry.get("text") or " ")
    view["showing"] = entry.get("id")
    return True


def gui_survey_screen_tick():
    """Refresh the log in place. What an `on change xess_log_revision()` should CALL.

    Never a jump back to the screen label: that re-sends every widget on the sheet over
    the network, and a watcher would do it forever.

    Returns:
        bool: False when the screen is gone - a handler can outlive the page.
    """
    page = FrameContext.page
    view = getattr(page, VIEW_ATTR, None) if page is not None else None
    if not view:
        return False
    rev = xess_log_revision()
    if rev == view.get("rev"):
        return True
    view["rev"] = rev

    entries = xess_log_entries()
    ids = [e.get("id") for e in entries]
    n = len(entries)
    sub = view.get("subtitle")
    if sub is not None:
        sub.update("$text:%s;font:gui-1;color:%s;"
                   % (_esc("%d readings" % n if n else ""), DIM))
    lb = view.get("lb")
    if lb is not None and ids != view.get("ids"):
        # THE LIST'S OWN CONTENTS, not a page rebuild. A listbox re-renders its rows
        # when its items change.
        lb.items = entries
        view["ids"] = ids
    # The entry on screen may have been read again, so refresh it either way.
    showing = view.get("showing")
    entry = next((e for e in entries if e.get("id") == showing), None)
    _pane_update(view, entry or (entries[0] if entries else None))
    return True
