def _is_client_or_server (cid):
    """0 is the server console; a client carries the 0x8000... bit. A non-int is
    passed through - Pybind11 raises a TypeError for it, which is not a crash."""
def _mast_location ():
    """The MAST file/line the current task is running, or ''."""
def _report (name, arg):
    ...
def install_engine_guards (sbs):
    """Wrap the asserting calls on `sbs`. Idempotent."""
