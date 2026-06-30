"""Engine-side consumer for the cosmos_dev command queue (dev-only).

Packaged into ``cosmos_devqueue.mastlib`` and opted into by a mission's
``story.json`` ``mastlib`` list. When the ``COSMOS_DEV_QUEUE`` env var is set on
the engine process, ``queue.mast`` schedules a server task that calls
``dev_queue_tick()`` every frame. The tick drains a JSON command file written by
the host driver (``cosmos_dev.engine_driver``), execs it in the live engine, and
writes the result to a JSON reply file.

Stdlib + sbs_utils only, single-threaded. It does NOT use threads/asyncio (those
are forbidden inside the embedded engine Python). The tick is non-blocking: it
returns immediately when there is nothing new; a queued command runs inline on
the tick that picks it up, so commands should be quick or schedule a task rather
than do long synchronous work.
"""
import os
import io
import json
import time
import traceback
import contextlib


def _queue_dir():
    # The host sets COSMOS_DEV_QUEUE_DIR to an absolute dir both sides agree on;
    # fall back to the running mission's dir.
    d = os.environ.get("COSMOS_DEV_QUEUE_DIR")
    if d:
        return d
    try:
        from sbs_utils.fs import get_mission_dir_filename
        return os.path.dirname(get_mission_dir_filename("dev_queue.in.json"))
    except Exception:
        return "."


def _in_path():
    return os.path.join(_queue_dir(), "dev_queue.in.json")


def _out_path():
    return os.path.join(_queue_dir(), "dev_queue.out.json")


def dev_queue_enabled():
    """True when the engine was launched with COSMOS_DEV_QUEUE set (non-empty,
    not 0/false). Keeps the consumer inert in normal play even if the mastlib is
    present."""
    v = os.environ.get("COSMOS_DEV_QUEUE", "")
    return v not in ("", "0", "false", "False")


# Per-process poll state (single-threaded, so a plain dict is fine).
_state = {"seq": -1, "mtime": None}


def _exec_globals():
    """Globals for executed commands: sbs + a few common procedural helpers.
    Commands can import anything else themselves."""
    g = {"__builtins__": __builtins__}
    try:
        import sbs
        g["sbs"] = sbs
    except Exception:
        pass
    try:
        import sbs_utils.procedural.execution as execution
        from sbs_utils.procedural.query import to_object, to_id, to_blob
        from sbs_utils.procedural.execution import task_schedule_server, get_shared_variable
        g["execution"] = execution
        g["to_object"] = to_object
        g["to_id"] = to_id
        g["to_blob"] = to_blob
        g["task_schedule_server"] = task_schedule_server
        g["get_shared_variable"] = get_shared_variable
    except Exception:
        pass
    return g


def _json_safe(v):
    try:
        json.dumps(v)
        return v
    except Exception:
        return repr(v)


def dev_queue_tick():
    """Server-side per-frame poll. Reads the command file only when it changes;
    execs a new command (by sequence number) and writes the reply file. Returns
    immediately (None) when there is nothing to do."""
    if not dev_queue_enabled():
        return
    ip = _in_path()
    try:
        m = os.path.getmtime(ip)
    except OSError:
        return
    if _state["mtime"] == m:
        return
    _state["mtime"] = m
    try:
        with open(ip, "r") as f:
            req = json.load(f)
    except Exception:
        return
    seq = req.get("seq", 0)
    if seq == _state["seq"]:
        return
    _state["seq"] = seq

    code = req.get("code", "")
    mode = req.get("mode", "exec")   # "exec" (set _result to return) | "eval"
    g = _exec_globals()
    out = io.StringIO()
    result = None
    err = None
    try:
        with contextlib.redirect_stdout(out):
            if mode == "eval":
                result = eval(code, g)
            else:
                exec(code, g)
                result = g.get("_result")
    except Exception:
        err = traceback.format_exc()

    resp = {
        "seq": seq,
        "ok": err is None,
        "stdout": out.getvalue(),
        "result": _json_safe(result),
        "error": err,
        "t": time.time(),
    }
    try:
        with open(_out_path(), "w") as f:
            json.dump(resp, f)
    except Exception:
        pass
