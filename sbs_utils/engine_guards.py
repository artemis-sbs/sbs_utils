"""Guards around engine calls that ASSERT instead of raising.

A bad argument to some Pybind11 calls is not a Python error: the engine hits a CRT
assert and the whole server goes down, with no Python traceback anywhere. The first
one seen is ``get_ship_of_client`` with a space-object id (0x4000...) where a client
id belongs (2026-09-19, OpenUniverse galaxy map, assert in ``GSGetShipOfClient``).

Each guard refuses the bad call, answers the engine's "nothing" value, and logs WHO
made it - the Python traceback plus the MAST line - once per call site, to
``debug.log`` and ``mast.runtime``. The engine never sees the bad id.
"""
import logging
import traceback

_REPORTED = set()


def _mast_location():
    """The MAST file/line the current task is running, or ''."""
    try:
        from .helpers import FrameContext
        from .mast.mast import Mast
        task = FrameContext.task
        node = task.get_active_node() if task is not None and hasattr(task, "get_active_node") else None
        if node is None:
            return ""
        return f"{Mast.get_source_file_name(node.file_num)}:{node.line_num} label {getattr(task, 'active_label', '?')}"
    except Exception:                                    # noqa: BLE001 - diagnostics only
        return ""


def _report(name, arg):
    stack = traceback.format_stack()[:-2]
    key = (name, "".join(stack[-4:]))
    if key in _REPORTED:
        return
    _REPORTED.add(key)
    msg = (f"[engine_guard] {name}({arg!r} = {hex(arg) if isinstance(arg, int) else arg}) "
           f"refused: not a client id - the engine would assert and crash.\n"
           f"MAST: {_mast_location() or '(not in a MAST task)'}\n" + "".join(stack[-12:]))
    logging.getLogger("mast.runtime").error(msg)
    try:
        from .mast.mast import DEBUG
        DEBUG(msg)
    except Exception:                                    # noqa: BLE001
        pass
    print(msg)


def _is_client_or_server(cid):
    """0 is the server console; a client carries the 0x8000... bit. A non-int is
    passed through - Pybind11 raises a TypeError for it, which is not a crash."""
    if not isinstance(cid, int):
        return True
    return cid == 0 or (cid & 0x8000000000000000) != 0


def install_engine_guards(sbs):
    """Wrap the asserting calls on `sbs`. Idempotent."""
    orig = getattr(sbs, "get_ship_of_client", None)
    if orig is None or getattr(orig, "_engine_guarded", False):
        return

    def get_ship_of_client(client_id, *args, **kwargs):
        if not _is_client_or_server(client_id):
            _report("get_ship_of_client", client_id)
            return 0
        return orig(client_id, *args, **kwargs)

    get_ship_of_client._engine_guarded = True
    sbs.get_ship_of_client = get_ship_of_client
