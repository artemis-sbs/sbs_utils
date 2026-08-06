def _ships_of (to, ship):
    """Player ships for a comms_message twin (comms goes to SHIPS, not consoles)."""
def _twin_audience (to, ship, consoles):
    """Console ids for the info-panel card. Cards land on consoles, same as the
    overlay, so the two halves always reach the same people."""
def announce (text, title=None, level='status', to=None, ship=None, consoles=None, face=None, color=None, sender=None, seconds=None, record=None, headline=None, icon=None):
    """Show a level-appropriate overlay and leave the matching durable record.
    
    Args:
        text (str): the full message — goes to the durable twin, and (shortened)
            to the overlay when no ``headline`` is given.
        title (str, optional): speaker / header line. Used as the hero card's
            title and the lower third's name.
        level (str): ``chapter`` | ``hail`` | ``alert`` | ``status`` | ``minor``
            (see the table in the module docstring). Defaults to ``status``.
        to: the audience — a console id, a **ship**, a **side**, or a set/role
            query. See ``consoles_of``.
        ship: shorthand for "this ship's crew" — used for ``to`` when ``to`` is
            omitted, and as the comms_message recipient for a ``hail``.
        consoles (str, optional): narrow the overlay/card to console roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
        face (str, optional): face string for the card / hero card.
        color (str, optional): colour for the card and the banner.
        sender: for ``hail``, the agent the comms_message comes FROM. Without one
            the twin falls back to an info card.
        seconds (int, optional): overlay dwell; defaults per level.
        record (bool, optional): force (``True``) or suppress (``False``) the
            durable twin. Defaults to the level's own policy.
        headline (str, optional): explicit overlay text (skips the shortener).
        icon (int, optional): icon index for the card.
    
    Returns:
        The durable twin's return value (a Promise for a card with a button, else
        None)."""
def announce_clear (slot=None, to=None, consoles=None):
    """Clear an announce overlay early (the durable twin is untouched)."""
def announce_headline (text, limit=60):
    """Reduce ``text`` to a single-line ASCII headline for an overlay.
    
    Engine-rendered text is ASCII-only, and an overlay is a glance, not a
    paragraph — so smart punctuation is folded, newlines collapse, and anything
    past ``limit`` is cut at a word boundary with an ellipsis."""
def announce_last_traffic ():
    """Sim seconds when the crew was last spoken to unprompted, or None."""
def announce_note_traffic (now=None):
    """Record that something just spoke to the crew unprompted."""
def announce_traffic_reset ():
    """Drop the traffic clock (called by reset_mission_state)."""
def comms_info_card (client_id, message=None, title=None, color=None, face=None, icon_index=None, banner=None, button=None, time=10, history=True, path=None, notify=None):
    """Send an "incoming comms" card to one or more clients' info panel.
    
    A reusable wrapper over ``gui_info_panel_send_message`` for narrative / ambient
    comms that should read as a hail - a speaker name + color (and optional
    face/icon/banner), kept in the panel's history and auto-dismissed - instead of
    an ephemeral text-waterfall line. Use this for chatter, hails, and quest
    hand-offs; keep ``comms_broadcast`` for pure mechanical status text.
    
    The ``color`` is applied to both the title and the body. If ``button`` is
    given, the call returns an awaitable ``Promise`` that resolves when a player
    presses it (so the card can ask for a decision).
    
    Args:
        client_id (int | set): Client/console id(s) to receive the card. Commonly
            ``all_roles("console, comms")`` or a ship's linked comms consoles.
        message (str, optional): Card body text.
        title (str, optional): Header line - typically the speaker / clan name.
        color (str, optional): Color for the title and body (name or hex).
        face (str, optional): Face/portrait string to show alongside the message.
        icon_index (int, optional): Icon index to show alongside the message.
        banner (str, optional): Larger banner text above the title.
        button (str | list, optional): Button label(s); when set the call returns
            an awaitable Promise that resolves on press.
        time (int, optional): Auto-dismiss after this many seconds (when there is
            no button). Defaults to 10.
        history (bool, optional): Keep the card in the panel log. Defaults to True.
        path (str, optional): Info-panel tab path. Defaults to ``"message"``.
        notify (bool, optional): Interrupt - show the card live and switch the
            panel to its tab. Defaults to None ("only if it has a button"), so a
            plain card is filed in the log and the attention half is left to an
            overlay (see ``announce``). Pass True to keep the old always-interrupt
            behaviour.
    
    Returns:
        Promise | None: Resolves on button press, or None if no button was given.
    
    Example:
        comms_info_card(all_roles("console, comms"),
            "You're a long way from friends, captain.",
            title="Ashfang Raiders", color="#ee3333")"""
def comms_message (msg, from_ids_or_obj, to_ids_or_obj, title=None, face=None, color=None, title_color=None, is_receive=True, from_name=None) -> None:
    """Send a comms message with explicit sender and receiver control.
    
    Lower-level function used by ``comms_transmit`` and ``comms_receive``.
    Handles lifeforms, side colors, ``CommsOverride``, and emits the
    ``comms_message`` signal. Prefer ``comms_transmit`` or ``comms_receive``
    unless you need direct sender/receiver control.
    
    Args:
        msg (str): The message body text. Supports ``{var}`` interpolation.
        from_ids_or_obj: Sender agent ID(s) or object(s).
        to_ids_or_obj: Receiver agent ID(s) or object(s). Pass ``None`` to
            send the message to the sender (internal communication).
        title (str, optional): Title bar text. Defaults to the sender's
            comms ID.
        face (str, optional): Face asset string for the sender portrait.
            Defaults to the face registered for the sender.
        color (str, optional): Body text color. Defaults to ``"#fff"``.
        title_color (str, optional): Title text color. Defaults to the
            sender's side color.
        is_receive (bool, optional): ``True`` = message is received (``< <``
            prefix); ``False`` = message is sent (``> >`` prefix). Defaults
            to ``True``.
        from_name (str, optional): Override the display name of the sender.
            Defaults to None (uses the sender object's ``comms_id``).
    
    Example:
        comms_message("Incoming!", ENEMY_ID, SHIP_ID, title="Commander")"""
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
def is_space_object_id (id):
    """Return whether an ID belongs to a space object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the space-object bit (0x4000…) is set."""
def overlay_kind (kind, to=None, consoles=None, slot=None, seconds=None, **fields):
    """Low-level front door: show any registered ``kind`` with its default slot.
    
    The escape hatch for callers that pick the kind at runtime (the quest driver's
    inline overlay directives, AMD records). Prefer the named wrappers when the
    kind is known at author time."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_id_list (the_set):
    """Convert a set or list of agents/IDs to a list of integer IDs.
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[int]: Resolved integer IDs; unresolvable items are excluded."""
