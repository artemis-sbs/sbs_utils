"""The Messages app: an inbox the crew read, and a line they can write back on.

Built as one screen a mission reaches through its own `//gui/tab/messages` route, the
same shape as the rest of ePADD - the library owns the screen, the mission owns the
route.

The list is a `gui_list_box` rather than a stack of rows on purpose: it scrolls, and an
inbox is the one thing here guaranteed to outgrow its panel. Selecting a message opens
it and marks it read, which is what makes the unread badge on the tile mean anything.

Composing is a `To` dropdown plus a line of text. Addressed to a CONSOLE, because that
is what a person is sitting at - see `procedural/messages.py` for why not a crew name.
"""
from ...helpers import FrameContext
from ..messages import (message_inbox, message_send, message_mark_read,
                        message_is_read, message_unread, message_choices,
                        message_answer, message_answered)
from .epadd import ACCENT, DIM, PANEL, PANEL_HEAD, _esc, gui_app_chrome


# The consoles a crew message can be addressed to. A mission with its own consoles
# passes its own list; these are the ones every bridge has.
DEFAULT_TO = ["Everyone", "helm", "weapons", "engineering", "science", "comms"]

# What a message is stored under while it is being typed. Per client, because two
# consoles compose at the same time and neither should see the other's half-sentence.
DRAFT_VAR = "epadd_message_draft"
TO_VAR = "epadd_message_to"


def _row_template(item):
    """One inbox row: who it is from, the subject, and whether it has been read.

    Sizes its ROW and returns None - a listbox only calls resize_to_content() when the
    template returns nothing, and an item section that keeps a returned size is
    degenerate, which kills the click region along with the selection.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    read = message_is_read(item.get("id"))
    who = item.get("from") or "unknown"
    subject = item.get("subject") or (item.get("text") or "")[:48]
    tone = DIM if read else "#fff"
    mark = "  " if read else "* "
    gui_row("row-height: 1.5em;")
    gui_text(f"$text:{_esc(mark + who)};font:gui-2;color:{tone};"
             f"overflow:shrink;", style="col-width: 30;")
    gui_text(f"$text:{_esc(subject)};font:gui-2;color:{tone};overflow:ellipsis;")


def _reply_strip(msg):
    """The replies this message offers, or what was already chosen.

    `on_press=` with a bound closure, never a MAST label: the builder here is the console's
    own GUI task, and a label handler jumps that task - which takes the console over.
    `overlay.py:1510` documents the same constraint for an overlay's buttons.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button

    answered = message_answered(msg.get("id"))
    if answered is not None:
        gui_row("row-height: content; padding: 0, 12px, 0, 0;")
        gui_text(f"$text:{_esc('You replied: ' + answered['label'])};"
                 f"font:gui-1;color:{ACCENT};")
        return

    if msg.get("scene"):
        _away_reply_strip(msg)
        return

    offered = message_choices(msg.get("id"))
    if not offered:
        return
    gui_row("row-height: 2.2em; padding: 0, 12px, 0, 0;")
    mid = msg.get("id")
    for choice in offered:
        # A closure with BOUND DEFAULTS, not a reference to the loop variable: the
        # buttons are built in a loop and every one of them would otherwise answer
        # with the last choice's index. `on_press` calls a callable with NO
        # arguments, so the press cannot be told apart any other way.
        def press(_mid=mid, _index=choice["index"], _seq=choice["seq"]):
            message_answer(_mid, _index, seq=_seq)

        gui_button(f"$text:{_esc(choice['label'])};",
                   style="col-width: content;", on_press=press)


def _away_reply_strip(msg):
    """The replies an away BEAT offers this console.

    Asked of away.py rather than carried on the message: the options differ per
    character (`away_choices` is per client and guard-filtered), and `away_answer` is
    already seq-arbitrated. Copying them onto the message would give one scene two
    competing arbitration paths.

    A beat that has moved on offers nothing - the scene key on the message no longer
    matches the open one, so an old line in the transcript is just a line.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from ..away import away_scene, away_choices, away_answer, away_seq

    page = FrameContext.page
    client_id = getattr(page, "client_id", None) if page is not None else None
    if client_id is None or msg.get("scene") != away_scene():
        return
    offered = away_choices(client_id)
    if not offered:
        return

    gui_row("row-height: 2.2em; padding: 0, 12px, 0, 0;")
    seq = away_seq()
    for index, choice in enumerate(offered):
        def press(_cid=client_id, _i=index, _seq=seq,
                  _agent=getattr(choice, "agent", None)):
            away_answer(_cid, _i, seq=_seq, agent=_agent)

        gui_button(f"$text:{_esc(getattr(choice, 'label', ''))};",
                   style="col-width: content;", on_press=press)


def gui_messages_screen(consoles=None, title="Messages"):
    """Draw the inbox, the reading pane and the compose line.

    Args:
        consoles (list, optional): who a crew message can be sent to. Defaults to the
            standard bridge consoles.
        title (str, optional): the app bar's title.
    """
    from .section import gui_section, gui_sub_section
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .listbox import gui_list_box
    from .dropdown import gui_drop_down
    from .input import gui_input
    from .button import gui_button
    from .message import gui_message_callback

    page = FrameContext.page
    task = FrameContext.task
    inbox = message_inbox()

    unread = message_unread()
    gui_app_chrome(title, subtitle=(f"{unread} unread" if unread else "all read"))

    gui_section(style="area: 0, 109px, 100, 100;")

    # --- the inbox, and the message being read ---------------------------------
    gui_row("padding: 24px, 12px, 24px, 8px;")
    with gui_sub_section(style="col-width: 42;"):
        gui_row("row-height: content;")
        if not inbox:
            gui_text(f"$text:No messages.;font:gui-2;color:{DIM};")
            lb = None
        else:
            lb = gui_list_box(inbox, "item-gap: 0.15em;", item_template=_row_template,
                              select=True, reveal=True)

    with gui_sub_section():
        reading = lb.get_value() if lb is not None else None
        if reading is None and inbox:
            reading = inbox[0]
        if reading is not None:
            message_mark_read(reading.get("id"))
            gui_row("row-height: content; padding: 0, 0, 0, 4px;")
            gui_text(f"$text:{_esc(reading.get('subject') or '')};font:gui-4;"
                     f"overflow:shrink;")
            gui_row("row-height: content; padding: 0, 0, 0, 10px;")
            gui_text(f"$text:{_esc('From ' + (reading.get('from') or 'unknown'))};"
                     f"font:gui-1;color:{ACCENT};")
            gui_row()
            gui_text_area(reading.get("text") or "")
            _reply_strip(reading)

    if lb is not None:
        def _open(event, sender):
            item = lb.get_value()
            if item is not None:
                message_mark_read(item.get("id"))
        gui_message_callback(lb, _open)

    # --- the line they write back on -------------------------------------------
    gui_row(f"row-height: 2.4em; background: {PANEL_HEAD}; padding: 24px, 8px, 24px, 8px;")
    gui_drop_down(f"list: {', '.join(consoles or DEFAULT_TO)}", var=TO_VAR,
                  style="col-width: 16;")
    entry = gui_input("", var=DRAFT_VAR)

    def _send(*_a):
        text = (task.get_variable(DRAFT_VAR) if task else None) or ""
        text = str(text).strip()
        if not text:
            return
        to = (task.get_variable(TO_VAR) if task else None) or "*"
        if str(to).strip().lower() in ("everyone", "all", ""):
            to = "*"
        message_send(text, to=to)
        if task:
            task.set_variable(DRAFT_VAR, "")
        entry.value = ""

    gui_button("$text:SEND;", style="col-width: content;", on_press=_send)
