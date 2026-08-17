from sbs_utils.helpers import FrameContext
def _hail_audio_toggled (event, item):
    """The Audio box moved. Ship-wide, so the console it came from does not matter."""
def _hail_band_builder (client_id, content):
    """The name plate, the line, and (read-only) the choices, over a live shot."""
def _hail_choice_readout (ship):
    """The choices as read-only lines, for a console that may not press them.
    
    Numbered, because the point is that the bridge can follow what comms is deciding
    between - not that anybody here can pick one."""
def _hail_label (value):
    """A BUTTON label.
    
    Plain text, and sanitized rather than quoted. The backtick quoting `gui_text_escape`
    applies is understood by the style parser but NOT by the engine's button, which
    draws the backticks - so a quoted label reads as ``Answer: DS 1`` with the marks
    visible. A raw label cannot be quoted either, because `:` and `;` in it would be
    parsed as style properties, so the characters that would need quoting are simply
    removed. Names are display text; losing a colon from one costs nothing."""
def _hail_log_pick (event, item):
    """A row was chosen: replay it. The console comes from the event because an info
    panel is always rendered for one client."""
def _hail_log_row (entry):
    """One row of the history list: who called, and whether it was taken."""
def _hail_may_answer_here (client_id):
    """Whether THIS console is one that can press an answer.
    
    Mirrors the server-side check in `hail_answer` rather than re-deciding it: a console
    that cannot answer must not be given buttons that will be refused."""
def _hail_radar_follow (ship, client_id):
    """Aim a comms console's 2D radar at the hail's subject.
    
    Only for a comms console, and only while the conversation is placed HERE - a
    console that has the hail switched off keeps its own radar. Records what it aimed
    at so `_hail_radar_release` only undoes a follow this hail started, the same
    discipline `HAIL_TOOK_VIEWER` uses for the main screen."""
def _hail_radar_release (client_id):
    """Give the radar back, if a hail was the thing holding it."""
def _hail_replay_back (event, item):
    """Leave the replay and go back to the list."""
def _hail_row (entry):
    """One row of the hail list.
    
    It opens a row - the item needs one to be hit-tested in - but declares no height:
    the listbox's `row-height` sizes the item and this fills it. Said once, on the
    listbox, instead of in two places that had to agree."""
def _hail_row_pick (event, item):
    """A row was chosen. Same dispatch as a button press, off the row's own data."""
def _hail_screen_builder (client_id, content):
    """The whole conversation, drawn OVER the main screen.
    
    An overlay rather than the page, because the alternative was pushing every engine
    widget offscreen - and `gui_widget_offscreen` moves a widget to 100,100 and leaves it
    there. Nothing puts it back, so the 3D view never returned; and any widget not
    explicitly moved (ship_data) stayed on top of the conversation. An opaque overlay
    covers all of them without touching one, and clearing it restores the screen exactly."""
def _hail_speaker_line (ship):
    """(name, line) for the beat being spoken, or ("", "") between beats."""
def _hail_text (value):
    """A `$text:` property with the value quoted, so a name or a line carrying `:` or
    `;` is drawn rather than parsed as style. For TEXT widgets only."""
def _hail_view_press (event, item):
    """Every button in the feature presses through here.
    
    Attached with `gui_message_callback`, NOT with `on_press`, and that is the whole
    reason these buttons work. `on_press` routes through MessageHandler, which begins by
    writing `__ITEM__` onto the task that BUILT the widget - and a `//gui/<console>`
    route body is a sub-task that `task_all(..., sub_tasks=True)` polls to completion, so
    that task is finished by the time anyone clicks. `on_message_cb` is invoked from the
    LAYOUT pass instead (Column.on_message), inside the live GUI task, and hands the
    widget straight to the callback - no task variable in the path at all. The
    placement drop-down beside this strip always worked for exactly this reason.
    
    ONE module-level callable, never a per-iteration closure: a closure would capture the
    loop variable and every button would answer for the last one. Which button was
    pressed comes from its own `data`."""
def _hail_where_changed (event, item):
    """A dial moved. The console id comes off the button data rather than the event, so
    a server-rendered frame cannot point this at client 0."""
def _hail_where_toggled (event, item):
    """The Off/On box moved on a console that is the ship's ONLY console."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def gui_text_escape (s):
    """Quote a dynamic value for safe inclusion as a ``$text:`` style value.
    
    Wraps ``s`` in backticks so any ``:`` or ``;`` it contains is treated as
    literal text by the style parser rather than a style property (issue #569).
    A literal backtick -- the quoting delimiter itself -- is stripped. An empty
    or ``None`` value returns ``""`` so the caller emits ``$text:;`` with no
    stray backtick in the box (issue #641).
    
    Use this ONLY on the dynamic value, e.g. ``f"$text:{gui_text_escape(name)};color:red;"``
    -- never on a whole authored props string, so the author's own ``:``/``;``
    styling is left untouched."""
def hail_accept (ship, hail_id=None, client_id=None):
    """Open a waiting hail. Normally reached from an `Answer:` button on the strip.
    
    Takes the head of the queue unless a `hail_id` names one. Resolves and caches the
    scene, bumps the arbitration token, and plays the scene's `Audio:` once - server
    side, so five consoles do not start five copies of it.
    
    Does NOT force any screen: each console shows the conversation only if its own
    placement dial says to.
    
    Returns:
        MastDataObject | None: the opened record, or None if nothing was answerable."""
def hail_active (ship):
    """The open conversation, or None."""
def hail_advance (ship, client_id=None, seq=None):
    """Move to the next beat - the crew reading on.
    
    Arbitrated exactly like `hail_answer`, and for the same reason: two officers
    pressing Continue in the same frame must not skip a line between them. A scripted
    or timed advance passes no `client_id` and so skips the console check.
    
    Returns:
        bool: True if another beat is now speaking; False when the beats are spent and
        the choices have gone live."""
def hail_answer (ship, index, client_id=None, seq=None):
    """Take one of the offered answers. The arbitration point.
    
    Refuses - returning False and changing nothing - when there is no open hail, when
    this console is replaying (a replay can never rewrite what was chosen), when the
    console is not a comms console, when `index` is out of range, when `seq` is stale
    (another console already answered), or when an outcome handler refuses the pick
    because the player cannot afford it.
    
    A scripted answer passes no `client_id` and so skips the console check.
    
    Returns:
        bool: whether the answer was taken."""
def hail_answer_label (record):
    """The text on a waiting hail's row. ASCII, and owned here so no console can drift.
    
    Who is calling, and what about: `DS 1 - Ambassador Kidnapped`. It used to read
    `Answer DS 1`, which said the same word on every row of a list already titled
    "Incoming Hails" - the verb is what the list IS, so spending the row's width on it
    crowded out the one thing that tells two calls apart. The scene's `Title:` earns
    that space instead.
    
    No colon: a row label is a style-property string to the engine, so `:` and `;` in
    it are parsed rather than drawn."""
def hail_audio (ship):
    """Whether hails may play their `Audio:` on this ship. Defaults to YES - a scene
    that ships a sound file expects to be heard."""
def hail_audio_checkbox (client_id=None, style=None):
    """`Audio` - ticked when hails may play their `Audio:`, which is the default.
    
    Ticked means SOUND, not mute: a scene that ships a sound file expects to be heard,
    and a box you have to tick to get the normal behaviour is a box people find only
    after wondering why it is quiet.
    
    Reads the SHIP's setting rather than remembering its own, so two comms consoles
    always agree - the same reason the placement dial is derived.
    
    Returns:
        the checkbox layout item, or None where a hail cannot be placed."""
def hail_audio_set (ship, on):
    """Turn hail audio on or off for a SHIP.
    
    Ship-wide, not per console, because the sound is played once for the whole bridge
    (`sbs.play_audio_file` to client 0). One sound, one switch - a per-console mute
    would silence a speaker nobody owns. Same last-writer-wins as the main screen.
    
    Returns:
        bool: whether the setting changed."""
def hail_band_clear (ship, to=None, consoles='mainscreen'):
    """Take the band down."""
def hail_band_show (ship, to=None, consoles='mainscreen'):
    """Put the current beat over a live orbit shot.
    
    Only meaningful for the `orbit` form - the other two draw inline, where a plain
    section is enough and an overlay would just be a second thing to keep in step."""
def hail_beat (ship):
    """The beat being spoken right now, or None when the beats are done.
    
    The card is already resolved: `speaker` is the cue key, `name`/`face`/`color` are
    what to draw with.
    
    NEVER assign `.text` to a bare MAST variable. Dialogue text may contain `{`, and
    MAST re-formats a string on assignment as an f-string - the failure is reported
    against the assignment line, not against the text. Pass it straight to a widget."""
def hail_choice_strip (ship, client_id=None, style=None, row_style=None):
    """The hail list: waiting hails to answer, or the open conversation's replies.
    
    A LISTBOX rather than a row of buttons. Three things follow from that, and all three
    were problems with the buttons: the queue can be any length because the list
    scrolls; the heading says what the list IS, so no separate text row is needed; and
    there is ONE widget to rebuild rather than N, so a repaint cannot leave half a strip
    behind.
    
    Args:
        style (str, optional): the LISTBOX's own style - its item row height.
        row_style (str, optional): the layout ROW the listbox sits in. It opens its own
            row, because a listbox otherwise joins whatever row is currently open and
            lands beside the control above it.
    
    Returns:
        int: how many rows were drawn."""
def hail_choices (ship):
    """The answers on offer, capped at `HAIL_MAX_CHOICES`.
    
    Empty until the beats have all been spoken, so a console can render the strip
    unconditionally and get the right thing at every moment of the conversation."""
def hail_close (ship, declined=False):
    """End the open conversation and archive it for replay.
    
    The next queued hail stays PENDING rather than opening itself, so the strip
    re-fills with an `Answer:` entry instead of the screen cutting to a stranger.
    
    Stands the main-screen shot down only if this hail is what started it
    (`HAIL_TOOK_VIEWER`) - helm may already have taken the screen back, and putting our
    idea of "before" over the top would undo their change."""
def hail_defer (ship, client_id=None, seq=None):
    """Put the open conversation back in the list, unanswered.
    
    The `Back` row. Comms can read a hail through, step back out, and re-open it later -
    on the main screen, when the captain is ready for it. That is a different act from
    declining: nothing is archived, no outcome runs, and the hail is still waiting.
    
    It goes back to the START of its scene. A hail resumed mid-sentence would show the
    captain the second half of a conversation nobody else heard, and the beats are
    already cached, so replaying them costs nothing.
    
    Arbitrated like an answer - two officers must not both step out of a hail that only
    one of them is still in.
    
    Returns:
        bool: whether a conversation was put back."""
def hail_form (ship, client_id=None):
    """How the open hail should be drawn, or None.
    
    **On a COMMS console an `orbit` always reads as `portrait`.** That is settled, not
    deferred: comms has no 3D view, and giving it one means taking the client's SHIP
    ASSIGNMENT, which is what the engine ties `comms_control` and `comms_sorted_list`
    to - the console would stop being able to do its own job in order to watch a camera
    move. A face always works, and the console still LOOKS at the caller, because its
    2D radar follows the subject (`hail_view`).
    
    The cinematic shot belongs to the main screen, which is a screen and nothing else."""
def hail_is_active (ship):
    """Whether a conversation is open on this ship."""
def hail_list_title (ship):
    """The list's heading: who is talking, or what is waiting."""
def hail_more (ship):
    """Whether the conversation has another beat waiting to be heard.
    
    What the console asks to decide between a `Continue` button and the answers. The
    LAST beat is shown together with its choices - a line and the replies to it on
    screen at once, which is how the reference conversations read - so this is false on
    the final beat and a single-beat hail is answerable the moment it opens."""
def hail_panel_history (cid, left=0, top=0, width=0, height=0):
    """The comms info-panel tab: every conversation this ship has had, re-readable.
    
    Two states in one tab - the list, and one conversation being replayed. The info
    panel gives a builder no way to push a second tab, and a hail's history is one idea,
    so the state lives on the console (`HAIL_REPLAY`) and this reads it."""
def hail_panel_icon ():
    """The history tab's glyph.
    
    A FUNCTION, not a constant, and that is load-bearing: only functions become MAST
    globals, so a module-level `HAIL_PANEL_ICON` is invisible to every .mast file that
    tries to use it - and invisible in a way a headless run does not catch, because the
    console layout that would name it never renders there.
    
    Resolved by MEANING rather than by sheet index, so a mission that re-skins the icon
    sheet moves this with it and the console never carries a bare number it cannot
    explain. Falls back to the messages glyph if the name is ever retired."""
def hail_pending (ship):
    """Hails waiting to be answered, best first.
    
    Prunes expired hails and hails whose subject has been destroyed, lazily, here -
    which is why there is no ticker and no extra entry in the reset ledger."""
def hail_rows (ship, client_id=None):
    """What the hail list should show right now, as plain rows.
    
    Three states in one list, which is what lets a console draw it unconditionally:
    
    | ship state                | rows                                    |
    |---------------------------|-----------------------------------------|
    | nothing pending or active | none - the list is not drawn            |
    | hails waiting, none open  | one per waiting hail, best first        |
    | a hail open, still talking| a single `Continue`                     |
    | a hail open, beats done   | that scene's answers                    |
    
    Waiting hails are NOT capped here. A listbox scrolls, so the queue cannot outgrow
    the space - which was the whole reason the old button strip stopped at four and
    silently dropped the fifth. The ANSWERS are still capped, because four is an
    authored limit that `amd_lint_hails` enforces at write time."""
def hail_screen_clear (ship, to=None, consoles='mainscreen'):
    """Take the conversation off the main screen, restoring it untouched."""
def hail_screen_show (ship, to=None, consoles='mainscreen'):
    """Put the conversation over the main screen.
    
    Only for the forms that OWN the screen. An orbit shot keeps the live view and gets
    the smaller band instead."""
def hail_seq (ship):
    """The ship's current arbitration token. A console stamps this onto every answer
    button it renders; `hail_answer` refuses a press carrying an older one."""
def hail_shows_here (client_id):
    """Whether THIS console should be drawing the conversation instead of its normal
    centre - the dial on a comms console, the ship's `HAIL_MAIN` on a main screen."""
def hail_transcript_text (entry):
    """An archived conversation as markdown: every line in the order it was said, with
    the answers the crew gave marked as theirs.
    
    The answers are TEXT, deliberately. `hail_answer` refuses a replaying console, so a
    button here would be refused anyway - but the surest way not to rewrite history is
    not to draw a control that looks as though it could."""
def hail_view (ship, client_id=None, face_style=None):
    """Build the conversation into the CURRENT layout position.
    
    `portrait` and `still` draw here. `orbit` draws NOTHING here and returns its name
    anyway: the engine has the screen full-bleed and the band is an overlay, so a
    console that gets `"orbit"` back should simply leave its view alone.
    
    Args:
        face_style (str, optional): the layout row the portrait sits in. The default is
            sized for a bridge console's centre column and is a percentage of the
            SCREEN, so a panel shorter than that gets a face taller than itself and
            every row beneath it - the name, the line, the answers - is pushed out of
            the panel entirely. A small panel passes its own height here. Sizing it is
            the console's call because only the console knows how much room it gave.
    
    Returns:
        str | None: the form that was built, or None when no hail is open."""
def hail_where (client_id):
    """What this console's placement drop-down reads.
    
    DERIVED, not stored, and that is the whole point. The two halves live in different
    places - whether THIS console swaps its own centre is the console's own business,
    but the main screen belongs to the ship and any comms console can move it. A dial
    that only remembered its own last click would read "Off" on the second officer's
    console while the hail was plainly up on the main screen, and their "Off" would
    then be a no-op. Deriving it means every comms console agrees about the main screen
    and disagrees only about itself, which is exactly the truth."""
def hail_where_checkbox (client_id=None, style=None, label='Hails'):
    """The placement dial reduced to Off/On, for a ship with ONE console.
    
    A fighter's cockpit is the whole bridge: there is no main screen to send a hail
    to and no second officer to disagree with, so three of the drop-down's four
    entries name places that do not exist. Ticked means "show incoming calls here",
    which is `console` placement - the same value the drop-down writes, through the
    same `hail_where_set`, so the two controls are interchangeable and a ship that
    grows a main screen later can swap back with no state to migrate.
    
    Returns:
        the checkbox layout item, or None when this console cannot place a hail."""
def hail_where_dropdown (client_id=None, style=None):
    """The placement dial: Off / This Console / Main Screen / Both.
    
    Deliberately the same shape as the science console's On-Screen drop-down, and it
    sits in the same place - beside that console's Follow checkbox. The whole dial is
    one call because the change handler lives here: a console that had to write its own
    `on change` would be a console that could disagree with the library about what the
    labels mean.
    
    Returns:
        the drop-down layout item, or None when this console cannot place a hail."""
def hail_where_for (label):
    """The placement a drop-down label means. Unknown labels read as `off`."""
def hail_where_label_for (value):
    """The drop-down label for a placement, so a repaint re-selects what is set."""
def hail_where_props (current=None):
    """The whole property string for the placement drop-down.
    
    The list key is `list:`, NOT `items:` - a dropdown built with the wrong key has no
    options to render and the engine dies allocating for it. `text:` is what shows
    while it is closed, so pass what this console is currently set to."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def overlay_clear (slot=None, to=None, consoles=None):
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets."""
def overlay_register (kind, builder):
    """Register a content builder for an overlay ``kind``.
    
    Args:
        kind (str): the ``kind`` value callers pass to ``overlay_show``.
        builder (callable): ``builder(client_id, content)`` — content is the dict
            passed to ``overlay_show`` (with ``kind`` included). Build widgets with
            the normal ``gui_*`` functions."""
def overlay_show (slot, kind, to=None, consoles=None, **content):
    """Show an overlay in ``slot`` using content builder ``kind``.
    
    Args:
        slot (str): a slot name (see ``OVERLAY_SLOTS``); unknown names use a
            centered default rect.
        kind (str): a registered builder (see ``overlay_register``).
        to: the audience — ``None`` = the current console; a client id; a **ship**
            (its consoles); a **side** key/agent (that side's consoles); or a set /
            role query mixing them. See ``consoles_of``.
        consoles (str, optional): narrow the audience to consoles with these roles,
            e.g. ``"mainscreen"``.
        **content: fields passed through to the builder.
    
    A console that joins the audience while this is still up gets it too — see
    the late-joiner note above. ``to=None`` means "the console calling", which has
    no audience to join, so it is not tracked."""
def overlay_slot_define (slot, rect, draw_layer=28000, input='passthrough'):
    """Define or override a slot's default rect / draw_layer / input mode."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
