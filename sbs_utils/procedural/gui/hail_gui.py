"""What an incoming hail LOOKS like - the reusable half of the feature.

`procedural/hail.py` owns the state; this owns every widget, every label and the one
overlay slot. A console's job is reduced to saying WHERE these go, which is the test of
whether the split is right: LegendaryMissions should be a handful of call sites and no
wording of its own.

Three surfaces, and the form decides which:

* `portrait` / `still` build INLINE, wherever the console puts them. There is no live
  engine view in the way, so the console pushes its own view widget offscreen and this
  draws in the space.
* `orbit` builds NOTHING inline. The engine renders the shot full-bleed and a live
  3D view cannot be layered over - overflow cannot be hidden there at any draw layer
  (mkdocs/docs/cosmos/gui_layer.md). So the name plate and the choices go in an OVERLAY
  slot at a fixed rect with its own opaque fill, which is the same solution the
  viewscreen data column already ships.

The choices appear twice on purpose, and differently. A console that MAY answer gets
real buttons (the answer strip). A console that may not - the main screen - gets the
same list as read-only text, so the bridge can see what comms is choosing between
without being able to press it.
"""
from ...helpers import FrameContext, gui_text_escape
from ..hail import (HAIL_MAX_CHOICES, hail_accept, hail_active, hail_advance,
                    hail_answer, hail_beat, hail_answer_label, hail_choices, hail_defer,
                    hail_form, hail_is_active, hail_more, hail_pending, hail_seq,
                    hail_where, hail_where_for, hail_where_label_for, hail_where_props)
from .overlay import overlay_clear, overlay_register, overlay_show, overlay_slot_define


# The band that carries a hail over a LIVE orbit shot. Left of the viewscreen data
# column's (72, 9, 99, 96) by two points, so a hail and the science read-out can share
# the screen. Layer 22000 is above the view and BELOW hero cards and cutscenes (26000+),
# so a story beat still takes the screen off a conversation.
HAIL_BAND_SLOT = "hail_band"
HAIL_BAND_RECT = (2.0, 70.0, 70.0, 98.0)
HAIL_BAND_LAYER = 22000
overlay_slot_define(HAIL_BAND_SLOT, HAIL_BAND_RECT, draw_layer=HAIL_BAND_LAYER)

# Opaque, because this is the one place a panel sits over a live engine view and
# layering cannot clip anything. The fill IS the clip.
BAND_BACKGROUND = "#000c"

def hail_panel_icon():
    """The history tab's glyph.

    A FUNCTION, not a constant, and that is load-bearing: only functions become MAST
    globals, so a module-level `HAIL_PANEL_ICON` is invisible to every .mast file that
    tries to use it - and invisible in a way a headless run does not catch, because the
    console layout that would name it never renders there.

    Resolved by MEANING rather than by sheet index, so a mission that re-skins the icon
    sheet moves this with it and the console never carries a bare number it cannot
    explain. Falls back to the messages glyph if the name is ever retired.
    """
    try:
        from .icon_sheet import icon_resolve
        index, _atlas = icon_resolve("talks")
        return index if index is not None else 84
    except Exception:
        return 84

# The listbox palette LegendaryMissions already uses for its own lists: a translucent
# body, and a more opaque bar behind the title so the heading does not read as another
# choice. Same values as the console-select and brain-scan lists, so a hail list looks
# like every other list on the bridge.
LIST_BACKGROUND = "#1572"
LIST_TITLE_BACKGROUND = "#1578"
LIST_TITLE_STYLE = ("row-height: 1.0;padding: 2px,2px,2px,2px;"
                    f"background:{LIST_TITLE_BACKGROUND};")

_STYLE_ROW = "row-height: 2.2em;"
# NO PERCENT SIGN. A bare number IS a percentage to the style parser; `30%` raises
# "Invalid syntax on token %" from LayoutAreaParser.lex, at RUNTIME, when the row
# is built - so it only fires on the console that actually draws the conversation.
_STYLE_FACE_ROW = "row-height: 30;"


def _hail_text(value):
    """A `$text:` property with the value quoted, so a name or a line carrying `:` or
    `;` is drawn rather than parsed as style. For TEXT widgets only."""
    return f"$text:{gui_text_escape(value)};"


def _hail_label(value):
    """A BUTTON label.

    Plain text, and sanitized rather than quoted. The backtick quoting `gui_text_escape`
    applies is understood by the style parser but NOT by the engine's button, which
    draws the backticks - so a quoted label reads as ``Answer: DS 1`` with the marks
    visible. A raw label cannot be quoted either, because `:` and `;` in it would be
    parsed as style properties, so the characters that would need quoting are simply
    removed. Names are display text; losing a colon from one costs nothing.
    """
    text = str(value or "")
    for ch in (":", ";", "`", "$"):
        text = text.replace(ch, " ")
    return " ".join(text.split())


def _hail_may_answer_here(client_id):
    """Whether THIS console is one that can press an answer.

    Mirrors the server-side check in `hail_answer` rather than re-deciding it: a console
    that cannot answer must not be given buttons that will be refused.
    """
    from ..roles import has_role
    return bool(client_id) and has_role(client_id, "comms")


# --- the press handler ------------------------------------------------------
def _hail_view_press(event, item):
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
    pressed comes from its own `data`.
    """
    data = getattr(item, "data", None) or {}
    ship = data.get("hail_ship")
    # The console that BUILT this button. A server-rendered frame reports client 0,
    # which would fail the comms-console check with nothing to show for it.
    client_id = (data.get("hail_client") or getattr(event, "client_id", None)
                 or FrameContext.client_id)
    if data.get("hail_kind") == "accept":
        hail_accept(ship, data.get("hail_id"), client_id)
    elif data.get("hail_kind") == "advance":
        hail_advance(ship, client_id, seq=data.get("hail_seq"))
    else:
        hail_answer(ship, data.get("hail_index"), client_id,
                    seq=data.get("hail_seq"))


# --- the answer strip -------------------------------------------------------
def _hail_row(entry):
    """One row of the hail list.

    It opens a row - the item needs one to be hit-tested in - but declares no height:
    the listbox's `row-height` sizes the item and this fills it. Said once, on the
    listbox, instead of in two places that had to agree.
    """
    from .row import gui_row
    from .text import gui_text
    gui_row()
    gui_text(_hail_text(entry.get("label") or ""))


def _hail_row_pick(event, item):
    """A row was chosen. Same dispatch as a button press, off the row's own data."""
    entry = item.get_value() if hasattr(item, "get_value") else None
    if not entry:
        return
    ship = entry.get("hail_ship")
    client_id = (entry.get("hail_client") or getattr(event, "client_id", None)
                 or FrameContext.client_id)
    kind = entry.get("hail_kind")
    if kind == "accept":
        hail_accept(ship, entry.get("hail_id"), client_id)
    elif kind == "advance":
        hail_advance(ship, client_id, seq=entry.get("hail_seq"))
    elif kind == "answer":
        hail_answer(ship, entry.get("hail_index"), client_id, seq=entry.get("hail_seq"))
    elif kind == "back":
        hail_defer(ship, client_id, seq=entry.get("hail_seq"))


def hail_rows(ship, client_id=None):
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
    authored limit that `amd_lint_hails` enforces at write time.
    """
    if client_id is None:
        client_id = FrameContext.client_id
    if not _hail_may_answer_here(client_id):
        return []
    if not hail_is_active(ship):
        return [{"label": hail_answer_label(record), "hail_kind": "accept",
                 "hail_ship": ship, "hail_client": client_id,
                 "hail_id": record.get("id")}
                for record in hail_pending(ship)]
    # `Back` steps out WITHOUT answering, so comms can read a hail through and re-open
    # it later - on the main screen, when the captain is ready. FIRST, so it sits in one
    # constant place while the answers beneath it change from scene to scene.
    back = {"label": "Back", "hail_kind": "back", "hail_ship": ship,
            "hail_client": client_id, "hail_seq": hail_seq(ship)}
    if hail_more(ship):
        return [back, {"label": "Continue", "hail_kind": "advance", "hail_ship": ship,
                       "hail_client": client_id, "hail_seq": hail_seq(ship)}]
    return [back] + [{"label": choice.label, "hail_kind": "answer", "hail_ship": ship,
                      "hail_client": client_id, "hail_index": choice.index,
                      "hail_seq": choice.seq}
                     for choice in hail_choices(ship)]


def hail_list_title(ship):
    """The list's heading: who is talking, or what is waiting."""
    if hail_is_active(ship):
        name, _line = _hail_speaker_line(ship)
        if name:
            return _hail_label(name)
    return "Incoming Hails"


def hail_choice_strip(ship, client_id=None, style=None, row_style=None):
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
        int: how many rows were drawn.
    """
    from .row import gui_row
    from .listbox import gui_list_box
    from .message import gui_message_callback

    if client_id is None:
        client_id = FrameContext.client_id
    rows = hail_rows(ship, client_id)
    if not rows:
        return 0
    gui_row(row_style or "row-height: 8em;")
    listbox = gui_list_box(rows,
                           style or f"row-height: 1.6em;background:{LIST_BACKGROUND};",
                           item_template=_hail_row,
                           title_template=hail_list_title(ship),
                           title_section_style=LIST_TITLE_STYLE, select=True)
    gui_message_callback(listbox, _hail_row_pick)
    return len(rows)


# --- the placement dial -----------------------------------------------------
def _hail_where_changed(event, item):
    """A dial moved. The console id comes off the button data rather than the event, so
    a server-rendered frame cannot point this at client 0."""
    data = getattr(item, "data", None) or {}
    client_id = data.get("hail_client") or getattr(event, "client_id", None)
    from ..hail import hail_where_set
    hail_where_set(client_id, hail_where_for(getattr(event, "value_tag", "")))


def hail_where_dropdown(client_id=None, style=None):
    """The placement dial: Off / This Console / Main Screen / Both.

    Deliberately the same shape as the science console's On-Screen drop-down, and it
    sits in the same place - beside that console's Follow checkbox. The whole dial is
    one call because the change handler lives here: a console that had to write its own
    `on change` would be a console that could disagree with the library about what the
    labels mean.

    Returns:
        the drop-down layout item, or None when this console cannot place a hail.
    """
    from .dropdown import gui_drop_down
    from .message import gui_message_callback

    if client_id is None:
        client_id = FrameContext.client_id
    if not _hail_may_answer_here(client_id):
        return None
    current = hail_where_label_for(hail_where(client_id))
    item = gui_drop_down(hail_where_props(current), style,
                         data={"hail_client": client_id})
    gui_message_callback(item, _hail_where_changed)
    return item


# --- the conversation itself ------------------------------------------------
def _hail_speaker_line(ship):
    """(name, line) for the beat being spoken, or ("", "") between beats."""
    beat = hail_beat(ship)
    if beat is None:
        record = hail_active(ship)
        return ((record.name or record.speaker or "") if record else ""), ""
    return (beat.name or beat.speaker or ""), (beat.text or "")


def _hail_choice_readout(ship):
    """The choices as read-only lines, for a console that may not press them.

    Numbered, because the point is that the bridge can follow what comms is deciding
    between - not that anybody here can pick one.
    """
    return [f"{i + 1}. {c.label}" for i, c in enumerate(hail_choices(ship))]


def hail_view(ship, client_id=None):
    """Build the conversation into the CURRENT layout position.

    `portrait` and `still` draw here. `orbit` draws NOTHING here and returns its name
    anyway: the engine has the screen full-bleed and the band is an overlay, so a
    console that gets `"orbit"` back should simply leave its view alone.

    Returns:
        str | None: the form that was built, or None when no hail is open.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .face import gui_face
    from .image import gui_image_keep_aspect_ratio_center

    if client_id is None:
        client_id = FrameContext.client_id
    if not hail_is_active(ship):
        return None
    form = hail_form(ship, client_id)
    if form == "orbit":
        return form

    record = hail_active(ship)
    name, line = _hail_speaker_line(ship)

    if form == "still" and record.backdrop:
        gui_row("row-height: 55;")
        gui_image_keep_aspect_ratio_center(record.backdrop)
    else:
        face = record.face or (hail_beat(ship) or {}).get("face") if record else None
        if face:
            gui_row(_STYLE_FACE_ROW)
            gui_face(face)

    if record.title:
        gui_row("row-height: 1.4em;")
        gui_text(_hail_text(record.title) + "justify:center;")
    gui_row("row-height: 1.6em;")
    gui_text(_hail_text(name) + "font:gui-3;")
    gui_row("row-height: 1fr;")
    # The line goes STRAIGHT into the widget. Dialogue text may contain `{`, and a
    # bare MAST assignment would re-format it as an f-string and fail against the
    # assignment line rather than against the text.
    gui_text_area(line)

    readout = [] if _hail_may_answer_here(client_id) else _hail_choice_readout(ship)
    if readout:
        gui_row("row-height: content;")
        gui_text_area(chr(10).join(readout))
    return form


# --- the band over a live orbit shot ----------------------------------------
def _hail_band_builder(client_id, content):
    """The name plate, the line, and (read-only) the choices, over a live shot."""
    from .row import gui_row
    from .text import gui_text, gui_text_area

    name = content.get("name") or ""
    line = content.get("line") or ""
    choices = content.get("choices") or []

    gui_row(f"row-height: 1.6em; background: {BAND_BACKGROUND};")
    gui_text(_hail_text(name) + "font:gui-3;padding:4px;")
    gui_row(f"row-height: 1fr; background: {BAND_BACKGROUND};")
    gui_text_area(line, "padding: 8px;")
    if choices:
        gui_row(f"row-height: content; background: {BAND_BACKGROUND};")
        gui_text_area(chr(10).join(choices), "padding: 8px;")


overlay_register(HAIL_BAND_SLOT, _hail_band_builder)


HAIL_SCREEN_SLOT = "fullscreen"
SCREEN_BACKGROUND = "#000e"


def _hail_screen_builder(client_id, content):
    """The whole conversation, drawn OVER the main screen.

    An overlay rather than the page, because the alternative was pushing every engine
    widget offscreen - and `gui_widget_offscreen` moves a widget to 100,100 and leaves it
    there. Nothing puts it back, so the 3D view never returned; and any widget not
    explicitly moved (ship_data) stayed on top of the conversation. An opaque overlay
    covers all of them without touching one, and clearing it restores the screen exactly.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .face import gui_face
    from .image import gui_image_keep_aspect_ratio_center

    face = content.get("face")
    backdrop = content.get("backdrop")
    title = content.get("title") or ""
    name = content.get("name") or ""
    line = content.get("line") or ""
    choices = content.get("choices") or []

    if backdrop:
        gui_row(f"row-height: 55; background: {SCREEN_BACKGROUND};")
        gui_image_keep_aspect_ratio_center(backdrop)
    elif face:
        gui_row(f"row-height: 40; background: {SCREEN_BACKGROUND};")
        gui_face(face)
    if title:
        gui_row(f"row-height: 1.6em; background: {SCREEN_BACKGROUND};")
        gui_text(_hail_text(title) + "justify:center;")
    gui_row(f"row-height: 1.8em; background: {SCREEN_BACKGROUND};")
    gui_text(_hail_text(name) + "font:gui-3;padding:6px;")
    gui_row(f"row-height: 1fr; background: {SCREEN_BACKGROUND};")
    gui_text_area(line, "padding: 10px;")
    if choices:
        gui_row(f"row-height: content; background: {SCREEN_BACKGROUND};")
        gui_text_area(chr(10).join(choices), "padding: 10px;")


overlay_register("hail_screen", _hail_screen_builder)


def hail_screen_show(ship, to=None, consoles="mainscreen"):
    """Put the conversation over the main screen.

    Only for the forms that OWN the screen. An orbit shot keeps the live view and gets
    the smaller band instead.
    """
    if not hail_is_active(ship):
        return False
    record = hail_active(ship)
    name, line = _hail_speaker_line(ship)
    beat = hail_beat(ship)
    overlay_show(HAIL_SCREEN_SLOT, "hail_screen",
                 to=to if to is not None else ship, consoles=consoles,
                 face=record.face or (beat.face if beat else None),
                 backdrop=record.backdrop, title=record.title,
                 name=name, line=line, choices=_hail_choice_readout(ship),
                 seq=hail_seq(ship))
    return True


def hail_screen_clear(ship, to=None, consoles="mainscreen"):
    """Take the conversation off the main screen, restoring it untouched."""
    overlay_clear(HAIL_SCREEN_SLOT, to=to if to is not None else ship,
                  consoles=consoles)
    return True


def hail_band_show(ship, to=None, consoles="mainscreen"):
    """Put the current beat over a live orbit shot.

    Only meaningful for the `orbit` form - the other two draw inline, where a plain
    section is enough and an overlay would just be a second thing to keep in step.
    """
    if not hail_is_active(ship):
        return False
    name, line = _hail_speaker_line(ship)
    overlay_show(HAIL_BAND_SLOT, HAIL_BAND_SLOT, to=to if to is not None else ship,
                 consoles=consoles, name=name, line=line,
                 choices=_hail_choice_readout(ship), seq=hail_seq(ship))
    return True


def hail_band_clear(ship, to=None, consoles="mainscreen"):
    """Take the band down."""
    overlay_clear(HAIL_BAND_SLOT, to=to if to is not None else ship, consoles=consoles)
    return True


# --- the history tab, and replay --------------------------------------------
def hail_transcript_text(entry):
    """An archived conversation as markdown: every line in the order it was said, with
    the answers the crew gave marked as theirs.

    The answers are TEXT, deliberately. `hail_answer` refuses a replaying console, so a
    button here would be refused anyway - but the surest way not to rewrite history is
    not to draw a control that looks as though it could.
    """
    out = []
    for item in (entry.get("transcript") or []):
        text = item.get("text") or ""
        if item.get("kind") == "choice":
            out.append("> **" + text + "**")
        else:
            name = item.get("name") or ""
            out.append(("**" + name + "**  " + text) if name else text)
    return chr(10).join(out) or "(nothing was said)"


def _hail_log_row(entry):
    """One row of the history list: who called, and whether it was taken."""
    from .row import gui_row
    from .text import gui_text
    who = entry.get("name") or entry.get("speaker") or "Unknown"
    gui_row("row-height: 1.8em;")
    gui_text(_hail_text(who + (" (declined)" if entry.get("declined") else "")))


def _hail_log_pick(event, item):
    """A row was chosen: replay it. The console comes from the event because an info
    panel is always rendered for one client."""
    from ..hail import hail_replay_start
    client_id = getattr(event, "client_id", None) or FrameContext.client_id
    entry = item.get_value() if hasattr(item, "get_value") else None
    if entry is not None:
        hail_replay_start(client_id, entry.get("id"))


def _hail_replay_back(event, item):
    """Leave the replay and go back to the list."""
    from ..hail import hail_replay_stop
    data = getattr(item, "data", None) or {}
    hail_replay_stop(data.get("hail_client") or getattr(event, "client_id", None)
                     or FrameContext.client_id)


def hail_panel_history(cid, left=0, top=0, width=0, height=0):
    """The comms info-panel tab: every conversation this ship has had, re-readable.

    Two states in one tab - the list, and one conversation being replayed. The info
    panel gives a builder no way to push a second tab, and a hail's history is one idea,
    so the state lives on the console (`HAIL_REPLAY`) and this reads it.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .button import gui_button
    from .listbox import gui_list_box
    from .message import gui_message_callback
    from .viewscreen import viewscreen_home_ship
    from ..hail import hail_log, hail_log_entry, hail_replaying, hail_replay_stop

    ship = viewscreen_home_ship(cid)
    log_id = hail_replaying(cid)
    if log_id is not None:
        entry = hail_log_entry(ship, log_id)
        if entry is None:
            hail_replay_stop(cid)          # the log rolled past it; fall through
        else:
            gui_row("row-height: 2em;")
            back = gui_button(_hail_label("Back to hails"),
                              data={"hail_client": cid})
            gui_message_callback(back, _hail_replay_back)
            gui_row("row-height: 1fr;")
            gui_text_area(hail_transcript_text(entry))
            return

    entries = hail_log(ship)
    if not entries:
        gui_row("row-height: 2em;")
        gui_text(_hail_text("No hails yet."))
        return
    listbox = gui_list_box(entries, "row-height: 1.8em;",
                           item_template=_hail_log_row, select=True)
    gui_message_callback(listbox, _hail_log_pick)
