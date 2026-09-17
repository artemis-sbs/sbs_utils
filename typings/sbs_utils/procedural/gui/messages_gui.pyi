from sbs_utils.helpers import FrameContext
def _answered_strip (answered):
    """The decision, in place of the buttons.
    
    A settled message must not still offer its replies - the press could only be
    refused - but it must not go blank either: what was said IS the transcript. The
    roads not taken are shown dimmed underneath, because a decision reads better
    beside the options it was made against."""
def _boarding_reply_strip (msg):
    """The replies an away BEAT offers this console.
    
    Asked of away.py rather than carried on the message: the options differ per
    character (`boarding_choices` is per client and guard-filtered), and `boarding_answer` is
    already seq-arbitrated. Copying them onto the message would give one scene two
    competing arbitration paths.
    
    A beat that has moved on offers nothing - the scene key on the message no longer
    matches the open one, so an old line in the transcript is just a line."""
def _choice_label (choice):
    """A choice as a button label, saying so when it is somebody else's job.
    
    A party short of a medic is still offered the medic's line (see
    `away.boarding_orphan_choices`), and handing it over unmarked would read as though
    the character were qualified. Saying who is being covered for is the difference
    between a bug and a decision."""
def _esc (text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
def _follow_once (live):
    """Whether to move this console to `live` - true only the first time it is seen.
    
    Without this the auto-follow fights the crew: the panel repaints on its own
    counter, so every repaint dragged the selection back to the live beat and no
    other message could be opened while a scene was running."""
def _is_stale_beat (msg):
    """A beat whose scene has moved on. Still readable as a transcript line; just no
    longer the thing being asked."""
def _live_beat (inbox):
    """The message carrying the boarding beat that is open right now, if any."""
def _reading_choose (inbox, lb):
    """WHICH message is being read. No drawing - the pane is already built.
    
    Kept whole from the original builder, because every line of it is a decision
    somebody made about a real complaint."""
def _reading_pane_build ():
    """The pane's fixed shape, built ONCE. Returns the handles the tick assigns to.
    
    Every row here exists whatever is being read - including the forwarded note, which
    is built EMPTY rather than skipped. A widget that comes and goes is a shape change,
    and a shape change is the thing this design exists to avoid.
    
    The last row reserves the reply band. The replies are drawn into a region pinned
    over that space (see `gui_messages_screen`), so the body must not flow into it: the
    engine does not clip, and a long message would otherwise run under the buttons."""
def _reading_pane_update (view, reading):
    """Point the pane at `reading`. Same widgets, same tags, new values.
    
    ALL FOUR MOVE TOGETHER. Updating only the interesting one is its own bug: the TNG
    face builder left the description under its preview describing the previous
    selection that way, and a pane that is half stale is worse than a blank one."""
def _reading_replies_fill (reading):
    """The reply band's contents, drawn inside its own region.
    
    ALWAYS DRAWS SOMETHING. The engine swaps a region's back buffer forward on
    `complete` only when it holds content; completing an empty one leaves what was
    there before on screen - which for this band is the previous message's buttons.
    The overlay system carries the same one-space placeholder for the same reason."""
def _reply_strip (msg):
    """The replies this message offers, or what was already chosen.
    
    `on_press=` with a bound closure, never a MAST label: the builder here is the console's
    own GUI task, and a label handler jumps that task - which takes the console over.
    `overlay.py:1510` documents the same constraint for an overlay's buttons."""
def _row_template (item):
    """One inbox row: who it is from, the subject, and whether it has been read.
    
    TWO ROWS, NOT TWO COLUMNS. Side by side, the subject had 70% of a panel that is
    itself 42% of the screen - about a quarter of the width - for the one line here
    that is actually prose. It ellipsized to nothing readable, and where it did not, it
    wrapped past a fixed 1.5em row and drew over the message under it (playtest image,
    2026-09-02). Stacked, the subject gets the panel's whole width.
    
    Sizes its ROWS and returns None - a listbox only calls resize_to_content() when the
    template returns nothing, and an item section that keeps a returned size is
    degenerate, which kills the click region along with the selection."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def gui_app_chrome (title, subtitle=None):
    """An app's title bar. OPTIONAL - an app draws it when a title helps orient.
    
    ITS OWN BAND, 45px..109px, from `design/epadd/Spec.src`. It used to be a bare
    `gui_row` with no section of its own, so it landed in the ambient full-screen section
    at y=0 and painted over the engine's Options button. Every caller already reserved
    `area: 0, 109px, 100, 100` for its body, so the bar was always MEANT to own this
    band - it just never claimed it.
    
    45px is the console body top, the LM convention every tab body already follows, so
    this clears the tab strip as well as Options.
    
    NO HOME BUTTON. The strip's status region opens the PADD home already; a HOME here
    was a second control for the same thing. And no back: the one Back in the game is
    the console's, on the tab bar, declared by every PADD screen with
    `gui_tab_back(CONSOLE_SELECT)`.
    
    NOT EVERY APP WANTS ONE. Upgrades and the other list/detail screens use their whole
    sheet and read better for it, so this is opt-in rather than something every screen
    must remember to draw.
    
    Args:
        title (str): the screen's name.
        subtitle (str, optional): a second, dimmer line. Leave it out unless it says
            something the screen below does not - a board captioned with the count of
            what it is already listing says nothing.
    
            Pass "" rather than None for a line that is EMPTY NOW but will have text
            later: the widget is created either way, so a live screen can update it in
            place instead of rebuilding the page to make one appear.
    
    Returns:
        Text | None: the subtitle widget, so a caller can keep it and update it."""
def gui_messages_screen (consoles=None, title='Messages'):
    """Draw the inbox, the reading pane and the compose line.
    
    Args:
        consoles (list, optional): who a crew message can be sent to. Defaults to the
            standard bridge consoles.
        title (str, optional): the app bar's title."""
def gui_messages_tick ():
    """Bring the open inbox up to date WITHOUT rebuilding the screen.
    
    This is what the app's route calls on `on change message_revision()`. It used to
    `jump` the screen's own label, which tears down and rebuilds the whole page - the
    chrome, the list, the reading pane and the compose line - every time a single number
    moved. That is why the panel flickered, why it could be caught mid-build showing an
    empty list, and why scrolling sometimes showed what looked like two list boxes: the
    old page and the new one, briefly both on screen.
    
    NOTHING HERE IS REBUILT. A listbox re-renders its own rows from `items`; the reading
    pane's four widgets are assigned to; the replies are the one part that changes shape,
    and they have a region that clears itself. An arriving message touches the list, a new
    selection touches the pane's values, and neither touches anything else.
    
    Safe to call when the screen is not up: it does nothing without a recorded view."""
def gui_rebuild (region):
    """Mark a section or region to rebuild its layout on the next present.
    
    Clears the region's sub-layout so it is reconstructed from scratch the
    next time the region is rendered.
    
    USE THIS ON A REGION, NOT ON A PLAIN SUB-SECTION. A region brackets its own
    drawing region and sends ``send_gui_clear`` for it before redrawing
    (``Layout.region_begin``), so its old children genuinely go. A plain
    ``gui_sub_section`` has no region to clear and the engine offers no "delete
    this widget", so a refill allocates NEW tags and every earlier fill stays
    painted underneath - which is how the ePADD inbox came to draw three
    messages on top of each other. A pane that is refilled out of band has to be
    a region, or a ``Control`` that owns its region (a text area, a listbox),
    updated in place.
    
    Args:
        region: A section or region layout item.
    
    Returns:
        The same ``region`` object, for chaining.
    
    Example:
        gui_rebuild(my_region)
        gui_represent(my_region)"""
def message_answer (mid, index, console=None, seq=None):
    """Take one of a message's replies.
    
    Returns the chosen dict, or None when the answer is refused - a stale seq, an
    already-answered message, an index that is not on offer for this console, or an
    outcome handler that says no (an unaffordable cost, say).
    
    The seq moves BEFORE the outcomes run, so a second console pressing in the same
    frame is refused rather than applying the outcome twice. That is hail.py's
    discipline and the reason is the same: the outcomes are the part that cannot be
    undone."""
def message_answered (mid):
    """What was chosen, or None. A console that arrives late reads the decision."""
def message_choices (mid, console=None):
    """The replies this console is offered on this message, guards applied.
    
    Empty once the message is answered - a decision that has been taken is not still
    on offer, and leaving the buttons up invites a second press that can only be
    refused."""
def message_forwarded_from (msg, console=None, client_id=None):
    """The post this message was really addressed to, when the reader is covering.
    
    None when it is their own mail - so a screen can label a forwarded letter without
    having to work out the addressing a second time."""
def message_inbox (console=None):
    """Messages this console can see, newest first."""
def message_is_read (mid, console=None):
    ...
def message_mark_read (mid=None, console=None):
    """Mark one message read for a console, or the whole inbox when `mid` is None."""
def message_select (mid, console=None):
    """Remember which message this console is reading, so it survives the repaint.
    
    A rebuild makes a NEW listbox whose selection starts empty; without this the
    reading pane would snap back to the newest message every time anything arrived."""
def message_selected (console=None):
    """The message id this console is reading, or None."""
def message_send (text, to='*', sender=None, subject=None, kind='crew', choices=None, scene=None):
    """Put a message in an inbox.
    
    Args:
        text (str): the body. Trimmed to MAX_TEXT.
        to (str, optional): console name, comma list, or "*" for everyone.
        sender (str, optional): who it is from. A crew message defaults to the console
            that sent it; a story message should always say.
        subject (str, optional): a short line for the list.
        kind (str, optional): "crew" or "mail" - what a story sends. The inbox shows
            them differently; nothing else depends on it.
        choices (list, optional): replies to offer, as `amd_choice` dicts
            (`{label, target, guard, outcomes}`). Capped at MAX_CHOICES. A message
            with none behaves exactly as it always did.
        scene (str, optional): an away scene key. Marks this message as that beat, so
            the inbox asks `away.py` for the replies instead of carrying its own -
            they differ per character and away already arbitrates them.
    
    Returns:
        dict: the stored message."""
def message_unread (console=None):
    """How many this console has not read. This is what the app badge shows."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
