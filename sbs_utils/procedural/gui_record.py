"""Record GUI interaction to a transcript, so a session can be described exactly.

    Artemis3-x64-release.exe autostartclient record=session

Writes `<mission>/records/session.jsonl`, one line per interaction.

WHY RECORD THE WIDGET AND NOT JUST THE EVENT. A widget tag is `str(int)`, assigned in
page-build order - it is an ORDINAL, not a name. One extra row in a list shifts every tag
after it, so a transcript of raw tags describes a layout that no longer exists the moment
anything changes. That is the classic reason record/replay tools rot.

We are not limited to the event, because we own the widget that produced it: when a click
lands, `Layout.on_message` knows it is the button labelled "Fire", not tag 47. So each line
carries a LOGICAL identity - label, kind, console - and the raw tag is kept only as a
tiebreaker. A transcript written that way still means something after the page is edited.

WHAT THIS IS NOT. Not a deterministic recording. Physics runs on its own 30 Hz thread and
`seed=` only pins the RNG, so replaying at the same wall-clock offsets will not reproduce a
run exactly - it is a script of actions, not a tape. And **object selection does not
survive**: `selected_id` is a per-session id, so "select 4611686018427387905" means nothing
next launch. Console and GUI interaction transcribe well; world interaction does not.

Off by default and cheap when off - one module-level boolean before anything else happens.
"""

import json
import os

from .command_line import command_line_get

_enabled = None            # None = not yet resolved
_path = None
_file = None
_current = None            # the interaction being described, until the dispatch finishes
_seq = 0


def gui_record_enabled():
    """Whether recording is on, resolved once.

    Enabled by `record=<name>` on the command line, or a `gui_record.enable` marker file in
    the mission - the same two ways the dev queue is enabled, so there is one convention to
    learn rather than two.
    """
    global _enabled, _path
    if _enabled is not None:
        return _enabled
    name = (command_line_get("record") or "").strip()
    if not name:
        try:
            from ..fs import get_mission_dir_filename
            if os.path.exists(get_mission_dir_filename("gui_record.enable")):
                name = "session"
        except Exception:
            pass
    if not name:
        _enabled = False
        return False
    try:
        from ..fs import get_mission_dir
        folder = os.path.join(get_mission_dir(), "records")
        os.makedirs(folder, exist_ok=True)
        _path = os.path.join(folder, os.path.basename(name) + ".jsonl")
    except Exception:
        _enabled = False
        return False
    _enabled = True
    return True


def gui_record_path():
    """Where the transcript is being written, or None."""
    return _path if gui_record_enabled() else None


def _write(entry):
    global _file
    try:
        if _file is None:
            _file = open(_path, "a", encoding="utf-8")
        _file.write(json.dumps(entry) + "\n")
        _file.flush()          # a crash is exactly when the transcript matters most
    except OSError:
        pass


def gui_record_begin(event):
    """Start describing one interaction. Called before the event is dispatched."""
    global _current, _seq
    if not gui_record_enabled():
        return
    _seq += 1
    _current = {
        "seq": _seq,
        "client": str(getattr(event, "client_id", "")),
        "tag": getattr(event, "sub_tag", None),
        "value": getattr(event, "value_tag", None),
        "float": getattr(event, "sub_float", None),
    }
    try:
        from ..helpers import FrameContext
        _current["t"] = round(FrameContext.sim_seconds or 0, 2)
    except Exception:
        pass


def gui_record_note(event, widget):
    """The widget the event turned out to be for. Called from `Layout.on_message`.

    This is the whole value of recording from inside: the LABEL is stable across page
    edits in a way the tag is not.
    """
    if _current is None or not _enabled:
        return
    label = getattr(widget, "message", None)
    if isinstance(label, str) and label:
        # Style strings carry the label plus presentation; keep it whole rather than
        # guessing at a parse - a transcript is read by a person, and too much beats wrong.
        _current["label"] = label[:200]
    _current["kind"] = type(widget).__name__
    click = getattr(widget, "click_tag", None)
    if click and getattr(event, "sub_tag", None) == click:
        _current["click"] = True


def gui_record_end():
    """Finish the interaction and write it. Called after the event is dispatched."""
    global _current
    if _current is not None and _enabled:
        _write(_current)
    _current = None


def gui_record_reset():
    """Drop state at a mission boundary. Registered with the reset ledger."""
    global _enabled, _path, _file, _current, _seq
    if _file is not None:
        try:
            _file.close()
        except OSError:
            pass
    _enabled = None
    _path = None
    _file = None
    _current = None
    _seq = 0


def gui_record_count():
    """How many interactions have been recorded. Reset-ledger probe."""
    return _seq
