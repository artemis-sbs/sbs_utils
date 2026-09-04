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
from ...helpers import FakeEvent, FrameContext
from ..inventory import get_inventory_value, set_inventory_value
from ..messages import (message_inbox, message_send, message_mark_read,
                        message_is_read, message_unread, message_choices,
                        message_answer, message_answered, message_select,
                        message_selected, message_forwarded_from)
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

    TWO ROWS, NOT TWO COLUMNS. Side by side, the subject had 70% of a panel that is
    itself 42% of the screen - about a quarter of the width - for the one line here
    that is actually prose. It ellipsized to nothing readable, and where it did not, it
    wrapped past a fixed 1.5em row and drew over the message under it (playtest image,
    2026-09-02). Stacked, the subject gets the panel's whole width.

    Sizes its ROWS and returns None - a listbox only calls resize_to_content() when the
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
    gui_row("row-height: 1.4em;")
    gui_text(f"$text:{_esc(mark + who)};font:gui-2;color:{tone};"
             f"overflow:shrink;")
    # INDENTED past the unread mark, so the two lines read as one message rather than
    # as two entries. Ellipsis rather than shrink: a subject that has to shrink to fit
    # is no more readable small than it is cut, and a shrunk line changes the row's
    # height under the one beside it.
    gui_row("row-height: 1.2em; padding: 18px, 0, 0, 2px;")
    gui_text(f"$text:{_esc(subject)};font:gui-1;color:{DIM if read else ACCENT};"
             f"overflow:ellipsis;")


FOLLOWED_VAR = "epadd_msg_followed"


def _follow_once(live):
    """Whether to move this console to `live` - true only the first time it is seen.

    Without this the auto-follow fights the crew: the panel repaints on its own
    counter, so every repaint dragged the selection back to the live beat and no
    other message could be opened while a scene was running.
    """
    page = FrameContext.page
    cid = getattr(page, "client_id", None) if page is not None else None
    key = live.get("scene")
    if get_inventory_value(cid, FOLLOWED_VAR, None) == key:
        return False
    set_inventory_value(cid, FOLLOWED_VAR, key)
    return True


def _live_beat(inbox):
    """The message carrying the away beat that is open right now, if any."""
    from ..away import away_scene
    key = away_scene()
    if not key:
        return None
    return next((m for m in inbox if m.get("scene") == key), None)


def _is_stale_beat(msg):
    """A beat whose scene has moved on. Still readable as a transcript line; just no
    longer the thing being asked."""
    from ..away import away_scene
    return bool(msg.get("scene")) and msg.get("scene") != away_scene()


def _answered_strip(answered):
    """The decision, in place of the buttons.

    A settled message must not still offer its replies - the press could only be
    refused - but it must not go blank either: what was said IS the transcript. The
    roads not taken are shown dimmed underneath, because a decision reads better
    beside the options it was made against.
    """
    from .row import gui_row
    from .text import gui_text

    who = answered.get("by")
    said = answered.get("label") or ""
    lead = f"{who} said:" if who and who not in ("unknown",) else "You replied:"
    gui_row("row-height: content; padding: 0, 12px, 0, 2px;")
    gui_text(f"$text:{_esc(lead)};font:gui-1;color:{DIM};",
             style="col-width: content;")
    gui_text(f"$text:{_esc(said)};font:gui-3;color:{ACCENT};overflow:shrink;")
    for other in (answered.get("others") or []):
        gui_row("row-height: content; padding: 0, 2px, 0, 0;")
        gui_text(f"$text:{_esc(other)};font:gui-1;color:#667;overflow:ellipsis;")


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
        _answered_strip(answered)
        return

    if msg.get("scene"):
        _away_reply_strip(msg)
        return

    offered = message_choices(msg.get("id"))
    if not offered:
        return
    mid = msg.get("id")
    for choice in offered:
        # ONE BUTTON PER ROW. A reply is a sentence, not a word - side by side they
        # divide a fixed width and the engine does not clip, so they draw over each
        # other and none of them can be read.
        gui_row("row-height: 2.4em; padding: 0, 6px, 0, 0;")

        # A closure with BOUND DEFAULTS, not a reference to the loop variable: the
        # buttons are built in a loop and every one of them would otherwise answer
        # with the last choice's index. `on_press` calls a callable with NO
        # arguments, so the press cannot be told apart any other way.
        def press(_mid=mid, _index=choice["index"], _seq=choice["seq"]):
            message_answer(_mid, _index, seq=_seq)

        # The label PLAINLY. Wrapped in a `$text:`...`;` style string the engine draws
        # the BACKTICKS - they quote a style value, they are not markup the renderer
        # strips - so every reply read with the marks still around it.
        gui_button(choice["label"], on_press=press)


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
    from ..away import away_scene, away_choices, away_choices_for, away_answer, away_seq
    from .away_gui import away_who

    page = FrameContext.page
    client_id = getattr(page, "client_id", None) if page is not None else None
    if client_id is None or msg.get("scene") != away_scene():
        return
    # `away_choices_for` for the ACTIVE character, not the deduped `away_choices`.
    # The deduped list collapses a shared choice - "Beam back up", "Walk in with her" -
    # onto the primary, so a console speaking for two bodies had no way to take one as
    # the second character. The roster picker in the Away Team app chooses who acts.
    active = away_who(client_id)
    offered = (away_choices_for(client_id, active) if active is not None
               else away_choices(client_id))
    if not offered:
        return

    seq = away_seq()
    for index, choice in enumerate(offered):
        gui_row("row-height: 2.4em; padding: 0, 6px, 0, 0;")

        def press(_cid=client_id, _i=index, _seq=seq,
                  _agent=getattr(choice, "agent", None)):
            away_answer(_cid, _i, seq=_seq, agent=_agent)

        gui_button(_choice_label(choice), on_press=press)


def _choice_label(choice):
    """A choice as a button label, saying so when it is somebody else's job.

    A party short of a medic is still offered the medic's line (see
    `away.away_orphan_choices`), and handing it over unmarked would read as though
    the character were qualified. Saying who is being covered for is the difference
    between a bug and a decision.
    """
    label = getattr(choice, "label", "")
    covering = choice.get("forwarded") if hasattr(choice, "get") else None
    if not covering:
        return label
    word = str(covering).split(">=")[0].strip()
    return f"{label} (covering for {word})" if word else label


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
    # "" rather than None when everything is read: the widget is made either way, so the
    # count can appear and disappear without the page being rebuilt to carry it. The
    # line still says nothing when there is nothing to say.
    subtitle_widget = gui_app_chrome(title,
                                     subtitle=(f"{unread} unread" if unread else ""))

    gui_section(style="area: 0, 80px, 100, 100;")

    # --- the inbox, and the message being read ---------------------------------
    gui_row("padding: 24px, 12px, 24px, 8px;")
    with gui_sub_section(style="col-width: 42;"):
        gui_row("row-height: content;")
        if not inbox:
            gui_text(f"$text:No messages.;font:gui-2;color:{DIM};")
            lb = None
        else:
            # `reveal=` AND `hint=`: this page repaints BECAUSE of its own selection.
            # Reveal scrolls the pick into view; without the hint a rebuild starts at
            # the top and the row that was clicked lands somewhere else under the
            # mouse. A stale hint is clamped, not an error.
            hint = get_inventory_value(page.client_id if page else None,
                                       "epadd_msg_hint", None)
            lb = gui_list_box(inbox, "item-gap: 0.15em;", item_template=_row_template,
                              select=True, reveal=True, hint=hint)

    pane = gui_sub_section()
    with pane:
        _reading_pane(inbox, lb)

    view = {"lb": lb, "pane": pane, "subtitle": subtitle_widget,
            "ids": [m.get("id") for m in inbox], "unread": unread}
    if page is not None:
        setattr(page, VIEW_ATTR, view)

    if lb is not None:
        def _open(event, sender):
            item = lb.get_value()
            if item is None:
                return
            message_mark_read(item.get("id"))
            # Recorded, and the revision moved, so the label's `on change` repaints
            # the reading pane. Selecting a row is not itself a rebuild.
            message_select(item.get("id"))
            set_inventory_value(page.client_id if page else None, "epadd_msg_hint",
                                lb.get_selection_hint())
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


#: Where the built screen is remembered, so a later tick can update it instead of
#: drawing it again. On the PAGE, so it dies with the page and needs no reset ledger.
VIEW_ATTR = "_epadd_messages_view"


def gui_messages_tick():
    """Bring the open inbox up to date WITHOUT rebuilding the screen.

    This is what the app's route calls on `on change message_revision()`. It used to
    `jump` the screen's own label, which tears down and rebuilds the whole page - the
    chrome, the list, the reading pane and the compose line - every time a single number
    moved. That is why the panel flickered, why it could be caught mid-build showing an
    empty list, and why scrolling sometimes showed what looked like two list boxes: the
    old page and the new one, briefly both on screen.

    Nothing here needs a rebuild. A listbox re-renders its own rows from `items`, and the
    reading pane is a sub-section that can be refilled on its own - so an arriving message
    touches the list, and a new selection touches the pane, and neither touches anything
    else.

    Safe to call when the screen is not up: it does nothing without a recorded view.
    """
    page = FrameContext.page
    view = getattr(page, VIEW_ATTR, None) if page is not None else None
    if not view:
        return False
    inbox = message_inbox()
    changed = False

    ids = [m.get("id") for m in inbox]
    lb = view.get("lb")
    if lb is not None and ids != view.get("ids"):
        # THE LIST ONLY. `items` swaps the data and marks the widget dirty; the engine
        # re-renders its rows next tick.
        lb.items = inbox
        view["ids"] = ids
        changed = True

    pane = view.get("pane")
    if pane is not None and pane.sub_section is not None:
        # CLEAR, not rebuild. `rebuild()` empties the MODEL; the widgets it drops are
        # still drawn on the client, because a refill allocates new tags and the engine
        # goes on drawing a tag until something takes it away. Reported from a bridge
        # as the inbox "creating numerous text areas instead of updating the one that
        # is there" - three messages' titles, senders and bodies superimposed. `clear()`
        # retires them first (Layout.clear_content).
        pane.clear()
        with pane:
            _reading_pane(inbox, lb)
        # AND SEND IT. `rebuild()` empties the rows and the refill builds new widgets,
        # but neither marks anything dirty - so the pane changed in the model and nothing
        # reached the client. Reported as "selecting a message doesn't show the message",
        # and measured: zero send_gui_* calls during a tick, three the moment this line
        # is added.
        #
        # This is the half a mock cannot see. The model was right the whole time, which
        # is why the tick's own tests passed.
        pane.sub_section.invalidate_all()
        pane.sub_section.represent(FakeEvent(page.client_id))
        changed = True

    unread = message_unread()
    sub = view.get("subtitle")
    if sub is not None and unread != view.get("unread"):
        sub.update(f"$text:{_esc(str(unread) + ' unread') if unread else ''};"
                   f"font:gui-1;color:{DIM};")
        view["unread"] = unread
        changed = True
    return changed


def _reading_pane(inbox, lb):
    """The message being read, drawn on its own so a tick can redraw JUST this."""
    from .row import gui_row
    from .text import gui_text, gui_text_area

    # The selection has to be RESTORED, not read off the listbox: a repaint makes
    # a new one whose selection starts empty, so the reading pane would otherwise
    # snap back to the newest message every time anything arrived.
    reading = None
    chosen = message_selected()
    if chosen is not None:
        reading = next((m for m in inbox if m.get("id") == chosen), None)
    # A conversation moves on: answering a beat opens the next one, and a pick
    # left on the beat just answered would leave the team reading a settled
    # question while the new one sat unseen.
    #
    # ONCE PER BEAT, THOUGH. Following on every repaint meant selecting anything
    # else while a scene was open was undone immediately - the screen repaints on
    # its own counter, so the pick was snatched back before it could be read. The
    # console remembers the last beat it was moved to and does not do it twice.
    live = _live_beat(inbox)
    if live is not None and _follow_once(live):
        reading = live
        message_select(live.get("id"))
    if reading is None and inbox:
        reading = inbox[0]
    if reading is not None and lb is not None:
        lb.value = reading
    if reading is not None:
        message_mark_read(reading.get("id"))
        gui_row("row-height: content; padding: 0, 0, 0, 4px;")
        gui_text(f"$text:{_esc(reading.get('subject') or '')};font:gui-4;"
                 f"overflow:shrink;")
        gui_row("row-height: content; padding: 0, 0, 0, 10px;")
        gui_text(f"$text:{_esc('From ' + (reading.get('from') or 'unknown'))};"
                 f"font:gui-1;color:{ACCENT};")
        # Mail for an empty post is forwarded here rather than lost. Say so, or a
        # letter addressed to somebody else reads as a mistake.
        covering = message_forwarded_from(reading)
        if covering:
            gui_row("row-height: content; padding: 0, 0, 0, 8px;")
            gui_text(f"$text:{_esc('Forwarded - addressed to ' + covering)};"
                     f"font:gui-1;color:{DIM};")
        gui_row()
        gui_text_area(reading.get("text") or "")
        _reply_strip(reading)
