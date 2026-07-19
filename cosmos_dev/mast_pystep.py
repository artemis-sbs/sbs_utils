"""Step INTO Python from MAST (dev-only, experimental).

When a MAST node evaluates Python (`~~ ... ~~`, a function call in an expression,
a condition), execution leaves the node granularity of the MAST debugger and
becomes pure CPython. To step through *that*, we need `sys.settrace` — which is
exactly what the stdlib ``bdb.Bdb`` base class (the one ``pdb`` is built on)
provides. This module is a thin adapter over ``bdb``: it runs a compiled
`eval`/`exec` under trace, parks the running thread on the first line of "user"
code (mission `.py` / procedural API — not stdlib plumbing), and lets a
controller thread step / next / out / continue and read Python frames.

It is scoped: tracing is installed only for the one stepped `eval_code` /
`exec_code` call and torn down when it returns, so there's no whole-mission
perf hit.

Caveat: ``sys.settrace`` is one-per-thread and **debugpy owns it** — so this only
works on the plain runner (``--dap-port`` without a debugpy launch), never under
a debugpy session.
"""
import bdb
import sys
import threading


class PyStepper(bdb.Bdb):
    """Run a MAST eval/exec under trace; park on user-code lines.

    ``stop_in(filename) -> bool`` decides which files are "user code" worth
    stopping in (the step filter). The park/resume handshake mirrors
    MastDebugCore: the traced thread blocks in ``_park`` until the controller
    thread calls one of step/next/out/cont.
    """

    def __init__(self, stop_in, park_fn=None):
        super().__init__()
        self.stop_in = stop_in
        # park_fn(frame) -> action string. When given (integration mode), the
        # MAST core owns the pause handshake and we just apply its decision.
        # When None (standalone), we use our own events.
        self._park_fn = park_fn
        self._stopped = threading.Event()   # set on the traced thread when parked
        self._go = threading.Event()        # set by the controller to resume
        self.frame = None                   # current parked Python frame
        self._action = "step"
        self.finished = False
        self.parked = False                 # did we stop on a user line at least once?
        self.result = None

    # -- bdb callbacks (run on the traced thread) --------------------------
    def user_call(self, frame, argument_list):
        # Keep tracing into the callee; we decide whether to stop at its lines.
        self.set_step()

    def user_line(self, frame):
        if self.stop_in(frame.f_code.co_filename):
            self._park(frame)
        else:
            self.set_step()

    def user_return(self, frame, return_value):
        # nothing special; stepping continues per the last set_*
        pass

    def user_exception(self, frame, exc_info):
        pass

    def _park(self, frame):
        # Handshake with a single clearer per event (no double-clear race):
        # worker SETS _stopped, controller CLEARS it; controller SETS _go,
        # worker CLEARS it.
        self.frame = frame
        self.parked = True
        if self._park_fn is not None:
            act = self._park_fn(frame)      # MAST core parks the thread + decides
        else:
            self._go.clear()
            self._stopped.set()
            self._go.wait()                 # <-- traced thread blocks here
            act = self._action
        if act == "next":
            self.set_next(frame)
        elif act == "out":
            self.set_return(frame)
        elif act == "cont":
            self.set_continue()
        else:
            self.set_step()

    # -- controller side (another thread) ----------------------------------
    def wait(self, timeout=5.0):
        """Block until the tracer parks or the eval finishes. Returns True if
        parked (inspectable), False if the eval completed."""
        if not self._stopped.wait(timeout):
            return False
        self._stopped.clear()               # controller owns clearing _stopped
        return not self.finished

    def _resume(self, action):
        self._action = action
        self._go.set()

    def step(self):
        self._resume("step")

    def next(self):
        self._resume("next")

    def out(self):
        self._resume("out")

    def cont(self):
        self._resume("cont")

    # -- inspection --------------------------------------------------------
    def location(self):
        if self.frame is None:
            return None
        code = self.frame.f_code
        return {"file": code.co_filename, "line": self.frame.f_lineno,
                "func": code.co_name}

    def variables(self):
        if self.frame is None:
            return {}
        return {k: v for k, v in self.frame.f_locals.items()
                if not k.startswith("__")}

    def stack(self, boundary=None):
        """Python frames from the current one outward, stopping at the eval
        boundary (the compiled `<string>` frame or an explicit boundary frame)."""
        frames = []
        f = self.frame
        while f is not None:
            code = f.co_code if False else f.f_code
            name = code.co_filename
            if name == "<string>" or (boundary is not None and f is boundary):
                break
            frames.append({"file": name, "line": f.f_lineno, "func": code.co_name})
            f = f.f_back
        return frames

    # -- run ---------------------------------------------------------------
    def trace_around(self, fn):
        """Run ``fn`` (which does the actual eval/exec) with this tracer active,
        stopping at the first user line. Tracing is torn down when ``fn``
        returns — scoped to just this call."""
        self.reset()
        self.set_step()                     # stop at the first traced line
        sys.settrace(self.trace_dispatch)
        try:
            self.result = fn()
        except bdb.BdbQuit:
            self.result = None
        finally:
            self.quitting = True
            sys.settrace(None)
            self.frame = None
            self.finished = True
            if self._park_fn is None:
                self._stopped.set()         # release any standalone controller
        return self.result

    def run_eval(self, code, glbls, lcls):
        """Trace an *expression* (eval). Standalone helper for tests."""
        return self.trace_around(lambda: eval(code, glbls, lcls))

    def run_exec(self, code, glbls, lcls):
        """Trace *statements* (exec). Standalone helper for tests."""
        return self.trace_around(lambda: exec(code, glbls, lcls))


def default_stop_filter(extra_dirs=()):
    """A step filter: stop in mission `.py` and the sbs_utils procedural API,
    skip the stdlib, the compiled `<string>` eval frame, and the debugger itself.
    ``extra_dirs`` adds more roots (normalized) to treat as user code."""
    import os
    roots = [os.path.normcase(os.path.normpath(d)) for d in extra_dirs]
    py_prefix = os.path.normcase(os.path.normpath(os.path.dirname(os.__file__)))
    proc_marker = os.path.normcase(os.path.join("sbs_utils", "procedural"))
    self_file = os.path.normcase(os.path.normpath(__file__))

    def stop_in(filename):
        if not filename or filename.startswith("<"):
            return False
        n = os.path.normcase(os.path.normpath(filename))
        if n == self_file:
            return False
        if n.startswith(py_prefix):          # stdlib / site-packages under it
            return False
        if proc_marker in n:                 # sbs_utils.procedural.* — the API
            return True
        if any(n.startswith(r) for r in roots):
            return True
        # Otherwise: a real project file that isn't stdlib -> treat as user code.
        return "sbs_utils" not in n or proc_marker in n

    return stop_in
