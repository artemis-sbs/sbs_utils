"""Source-level MAST debug core for the mock harness (dev-only).

Phase 0 of MAST_DEBUGGER_PLAN.md: prove the pause / step / inspect mechanics
against the mock scheduler, with **no DAP and no VS Code** — just Python.

Design
------
Like ``cosmos_dev/coverage.py`` this installs the ``MastTicker.on_enter_node``
seam (the single per-node choke point in ``MastTicker.next()``). The seam is
``None`` in production, so this has **zero impact on non-debug runs** and lives
in ``cosmos_dev`` — it is never shipped in the ``.sbslib``.

Where coverage only *records* each entered node, the debugger can *block* on it:
when the tick thread enters a node that matches an armed breakpoint (or satisfies
an active step request), the hook parks the tick thread on an ``Event`` until the
controller thread calls ``resume()`` / ``step_*()``. While parked, the tick
thread is frozen at a clean node boundary, so the controller can safely read the
call stack and variables from another thread.

Concurrency contract (two Events, one owner each — no double-clear races):
- ``_stopped`` : **set** by the hook (tick thread), **cleared** by the controller.
- ``_go``      : **set** by the controller, **cleared** by the hook.

Threading lives only in the *driver* (see ``run_scheduler_in_thread``), not in
the core: the core just parks whichever thread calls the hook. cosmos_dev is
dev-only and already uses threads (physics) + asyncio (mockgui), so this is fine.

Coverage co-existence: ``install()`` chains any previously installed
``on_enter_node`` (e.g. ``MastCoverage``), so both can tap the same seam.

Usage::

    from cosmos_dev.mast_debug import MastDebugCore, run_scheduler_in_thread
    dbg = MastDebugCore().install(mast)
    dbg.set_breakpoints("story.mast", [12])
    worker = run_scheduler_in_thread(runner, "main")   # ticks on a bg thread
    dbg.wait_for_pause()                                # blocks until BP hit
    print(dbg.location())                               # {'line': 12, ...}
    print(dbg.stack())
    print(dbg.scopes()["Task"])
    dbg.step_over()                                     # advance one source line
    ...
    dbg.resume()
    worker.join()
    dbg.uninstall()
"""
import os
import sys
import threading

from sbs_utils.mast.mastscheduler import MastTicker
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext


# Inventory keys that are engine bookkeeping, not user variables — hidden from
# the variables view so the panels show what the script author actually wrote.
_HIDDEN_KEYS = {"mast_task", "SHARED", "__MAST_TASK__"}


def _norm(path):
    """Normalize a path for matching (case-fold + separators on Windows)."""
    return os.path.normcase(os.path.normpath(path)) if path else path


def _base(path):
    """Case-folded basename, used as the file_num-independent match key."""
    return os.path.normcase(os.path.basename(path)) if path else path


def _clean(d):
    """Copy a namespace dict, dropping engine bookkeeping + dunder keys."""
    if not d:
        return {}
    return {k: v for k, v in d.items()
            if k not in _HIDDEN_KEYS and not (isinstance(k, str) and k.startswith("__"))}


def _hit_ok(hit_condition, hits):
    """Evaluate a DAP hitCondition against the current hit count.

    Supports ``N`` (== N), ``==N``, ``>N``, ``>=N``, ``<N``, ``<=N``, ``%N``
    (every Nth). An unparseable condition passes (fail open)."""
    s = str(hit_condition).strip()
    for op in (">=", "<=", "==", ">", "<", "%"):
        if s.startswith(op):
            try:
                n = int(s[len(op):].strip())
            except ValueError:
                return True
            if op == ">=":
                return hits >= n
            if op == "<=":
                return hits <= n
            if op == "==":
                return hits == n
            if op == ">":
                return hits > n
            if op == "<":
                return hits < n
            if op == "%":
                return n != 0 and hits % n == 0
    try:
        return hits == int(s)      # bare number -> break exactly on the Nth hit
    except ValueError:
        return True


def _file_name_of(cmd):
    """Clean source file name for a node (not the ``file (basedir)`` str form)."""
    if cmd is None:
        return None
    fnum = getattr(cmd, "file_num", None)
    if fnum is None:
        return None
    smap = Mast.source_map_files
    if fnum < len(smap):
        return smap[fnum].file_name
    return Mast.get_source_file_name(fnum)


def _abs_file_of(cmd):
    """Absolute on-disk path for a node's source, so the editor can open it
    directly (map files like siege.mast compile under a relative name + basedir)."""
    name = _file_name_of(cmd)
    if not name:
        return name
    if os.path.isabs(name):
        return name
    fnum = getattr(cmd, "file_num", None)
    smap = Mast.source_map_files
    if fnum is not None and fnum < len(smap):
        base = getattr(smap[fnum], "basedir", None)
        if base:
            return os.path.normpath(os.path.join(base, name))
    return name


class MastDebugCore:
    """Breakpoint index + blocking ``on_enter_node`` hook + inspection API."""

    # -- lifecycle ---------------------------------------------------------
    def __init__(self):
        self._installed = False
        self._prev_hook = None            # chained hook (e.g. coverage)
        self._enabled = True
        self._mast = None

        # breakpoint index. Matching is by BASENAME (case-folded), not file_num:
        # a real mission compiles several times (server page, client page, each
        # map) and `Mast.source_map_files` is a class-global that resets per
        # compile, so a running node's file_num is NOT stable. Basenames are.
        self._by_file = {}                # raw filename -> {line_num: node}
        self._by_base = {}                # basename(cf) -> {line_num: node}
        self._requested = {}              # filename -> {line: spec}  (for re-arm)
        self._armed = {}                  # (basename(cf), line) -> spec (+hits)
        self._armed_lines = set()         # {line} — cheap pre-filter in the hook
        self.on_output = None             # logpoint sink: callable(str) -> None
        self._trace_seen = set()          # diagnostic: armed lines already reported
        self._trace_budget = 80           # cap trace spam

        # pause / step handshake
        self._stopped = threading.Event()  # set by hook, cleared by controller
        self._go = threading.Event()       # set by controller, cleared by hook
        self._paused = False
        self._cur = None                   # (task, label, cmd) at the stop point
        self._reason = None                # "breakpoint" | "step" | "entry"
        self._prev_line = None             # (file_num, line_num) of last entered node
        self._prev_bp = None               # last breakpoint key (basename,line) — dedup
        self._step = None                  # active step request dict, or None

        # Step-into-Python (experimental): trace eval_code/exec_code with bdb.
        self._py_enabled = False           # eval/exec wrapping installed?
        self._py_armed = False             # trace the next eval/exec?
        self._pystep = None                # active PyStepper
        self._cur_py = None                # current Python frame when paused in Python
        self._py_action = "step"           # what the controller asked in Python mode
        self._stop_in = None               # step filter predicate
        self._orig_eval_code = None
        self._orig_exec_code = None

    def install(self, mast=None):
        if not self._installed:
            self._prev_hook = MastTicker.on_enter_node
            MastTicker.on_enter_node = self._on_enter
            self._installed = True
        if mast is not None:
            self.index(mast)
        return self

    def uninstall(self):
        if self._installed:
            MastTicker.on_enter_node = self._prev_hook
            self._prev_hook = None
            self._installed = False
        if self._py_enabled:
            self.disable_python_step()
        # release any parked tick thread so it can finish
        self._step = None
        self._paused = False
        self._go.set()

    # -- breakpoint index --------------------------------------------------
    def index(self, mast):
        """(Re)build the index from a single compiled Mast."""
        self._mast = mast
        self._index_masts([mast])

    def index_all(self):
        """Index every Mast reachable from live MAST tasks plus the attached one.
        A real mission has several (server/client story pages, each map), and map
        files (e.g. siege.mast) compile lazily — so re-scanning picks them up."""
        masts, seen = [], set()
        for m in ([self._mast] if self._mast is not None else []):
            if id(m) not in seen:
                masts.append(m); seen.add(id(m))
        try:
            from sbs_utils.agent import Agent
            for a in list(Agent.all.values()):
                main = getattr(a, "main", None)
                m = getattr(main, "mast", None) if main is not None else None
                if m is not None and id(m) not in seen:
                    masts.append(m); seen.add(id(m))
        except Exception:
            pass
        self._index_masts(masts)

    def _index_masts(self, masts):
        # Build fresh dicts and swap them in (assignment is atomic), so the hook
        # thread never sees a half-cleared index.
        by_file, by_base = {}, {}
        for mast in masts:
            if mast is None:
                continue
            # snapshot: the tick thread may add labels/cmds during a live compile
            for label in list(getattr(mast, "labels", {}).values()):
                for cmd in list(getattr(label, "cmds", None) or []):
                    lnum = getattr(cmd, "line_num", None)
                    if getattr(cmd, "file_num", None) is None or lnum is None:
                        continue
                    name = _file_name_of(cmd)
                    if name is None:
                        continue
                    by_file.setdefault(name, {}).setdefault(lnum, cmd)
                    by_base.setdefault(_base(name), {}).setdefault(lnum, cmd)
        self._by_file = by_file
        self._by_base = by_base
        self._rearm()

    def files(self):
        """Source file names present in the index."""
        return sorted(self._by_file)

    def set_breakpoints(self, filename, breakpoints):
        """Arm breakpoints for ``filename``. Each entry is either a line number or
        a dict ``{line, condition?, hitCondition?, logMessage?}``:

        - ``condition`` — a MAST/Python expression; stop only when it is truthy.
        - ``hitCondition`` — ``N`` / ``==N`` / ``>N`` / ``>=N`` / ``%N``; stop only
          when the (condition-passing) hit count matches.
        - ``logMessage`` — a *logpoint*: emit the message (with ``{expr}``
          interpolation) via ``on_output`` and DON'T stop.

        A requested line with no node binds to the next node on/after it (so BPs
        on blank/comment lines still resolve). Returns the resolved line numbers.
        """
        specs = {}
        for bp in breakpoints:
            if isinstance(bp, int):
                specs[bp] = {"line": bp}
            else:
                line = bp["line"]
                specs[line] = {
                    "line": line,
                    "condition": bp.get("condition"),
                    "hitCondition": bp.get("hitCondition"),
                    "logMessage": bp.get("logMessage"),
                }
        self._requested[filename] = specs
        return self._rearm().get(filename, [])

    def clear_breakpoints(self, filename=None):
        if filename is None:
            self._requested.clear()
        else:
            self._requested.pop(filename, None)
        self._rearm()

    def _lines_for(self, filename):
        """The indexed {line: node} for a requested filename, matched exact ->
        normalized path -> basename (so an absolute path from the editor finds a
        file the mission compiled under a relative/other name)."""
        if filename in self._by_file:
            return self._by_file[filename]
        want = _norm(filename)
        for name, fmap in self._by_file.items():
            if _norm(name) == want:
                return fmap
        return self._by_base.get(_base(filename))

    def _rearm(self):
        """Resolve every requested (file, line) against the current index. Builds
        a fresh armed map and swaps it in (atomic) for hook-thread safety."""
        armed, armed_lines, resolved = {}, set(), {}
        for filename, specs in self._requested.items():
            fmap = self._lines_for(filename)
            got = []
            if fmap:
                available = sorted(fmap)
                base = _base(filename if filename in self._by_file else
                             self._indexed_name_for(filename) or filename)
                for want, spec in specs.items():
                    actual = want if want in fmap else next((l for l in available if l >= want), None)
                    if actual is not None:
                        armed[(base, actual)] = {**spec, "hits": 0}
                        armed_lines.add(actual)
                        got.append(actual)
            resolved[filename] = sorted(set(got))
        self._armed = armed
        self._armed_lines = armed_lines
        return resolved

    def _indexed_name_for(self, filename):
        """The raw indexed filename a requested path resolves to (for basename)."""
        if filename in self._by_file:
            return filename
        want = _norm(filename)
        for name in self._by_file:
            if _norm(name) == want:
                return name
        b = _base(filename)
        for name in self._by_file:
            if _base(name) == b:
                return name
        return None

    def verified_line(self, filename, line):
        """The line a requested breakpoint binds to (exact node, else next after),
        or None if the file isn't indexed."""
        fmap = self._lines_for(filename)
        if not fmap:
            return None
        if line in fmap:
            return line
        after = [l for l in sorted(fmap) if l >= line]
        return after[0] if after else None

    # -- enable/disable ----------------------------------------------------
    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    @property
    def is_paused(self):
        return self._paused

    # -- step into Python (experimental) -----------------------------------
    def enable_python_step(self, stop_in=None, extra_dirs=()):
        """Wrap MastAsyncTask.eval_code/exec_code so a step-into can descend into
        the Python that MAST evaluates. Requires the plain runner (NOT debugpy —
        sys.settrace is one-per-thread). No shipped-code change: monkeypatch."""
        from .mast_pystep import default_stop_filter
        from sbs_utils.mast.mastscheduler import MastAsyncTask
        self._stop_in = stop_in or default_stop_filter(extra_dirs)
        if self._orig_eval_code is None:
            # Wrap the method that actually RUNS the eval. Since eval_code became a
            # thin wrapper over eval_code_checked (the library's nodes call the
            # checked form), wrapping eval_code alone would never be reached.
            # getattr keeps this working against an older packaged .sbslib.
            self._eval_attr = ("eval_code_checked"
                               if hasattr(MastAsyncTask, "eval_code_checked")
                               else "eval_code")
            # Always wrap the REAL method (unwrap any prior wrapper) so repeated
            # enable/disable never nests wrappers.
            _cur_eval = getattr(MastAsyncTask, self._eval_attr)
            base_eval = getattr(_cur_eval, "_mast_orig", _cur_eval)
            base_exec = getattr(MastAsyncTask.exec_code, "_mast_orig", MastAsyncTask.exec_code)
            self._orig_eval_code = base_eval
            self._orig_exec_code = base_exec
            core = self

            def eval_code(task, code, end_on_exception=True):
                return core._maybe_trace(lambda: base_eval(task, code, end_on_exception))

            def exec_code(task, code, vars, gbls):
                return core._maybe_trace(lambda: base_exec(task, code, vars, gbls))

            eval_code._mast_orig = base_eval
            exec_code._mast_orig = base_exec
            setattr(MastAsyncTask, self._eval_attr, eval_code)
            MastAsyncTask.exec_code = exec_code
        self._py_enabled = True

    def disable_python_step(self):
        from sbs_utils.mast.mastscheduler import MastAsyncTask
        if self._orig_eval_code is not None:
            setattr(MastAsyncTask, getattr(self, "_eval_attr", "eval_code"),
                    self._orig_eval_code)
            MastAsyncTask.exec_code = self._orig_exec_code
            self._orig_eval_code = self._orig_exec_code = None
        self._py_enabled = False
        self._py_armed = False

    def arm_python_step(self):
        """Trace the next eval/exec — set alongside a MAST step-in."""
        if self._py_enabled:
            self._py_armed = True

    def _maybe_trace(self, fn):
        if not (self._py_armed and self._enabled):
            return fn()
        self._py_armed = False
        tr = sys.gettrace()
        if tr is not None:
            # Another tracer (debugpy / coverage) owns sys.settrace on this
            # thread — don't fight it; just run the eval normally.
            if self.on_output:
                self.on_output(f"[mast] step-into skipped: a tracer is already active ({tr!r})")
            return fn()
        if self.on_output:
            self.on_output("[mast] step-into: tracing this eval for Python step-in")
        from .mast_pystep import PyStepper
        self._pystep = PyStepper(self._stop_in, park_fn=self._park_python)
        try:
            return self._pystep.trace_around(fn)
        finally:
            hit = self._pystep.parked if self._pystep else False
            self._pystep = None
            if self.on_output and not hit:
                self.on_output("[mast] step-into: eval ran but no user-code line matched "
                               "the step filter (stepped over)")

    def _park_python(self, frame):
        """Park the tick thread inside Python, sharing the core's handshake so
        the same monitor/wait_for_pause/stopped machinery covers both worlds."""
        self._step = None            # the MAST step-in is fulfilled by entering Python
        self._cur_py = frame
        self._reason = "step"
        self._paused = True
        self._go.clear()
        self._stopped.set()
        self._go.wait()
        self._paused = False
        self._cur_py = None
        return self._py_action

    @property
    def in_python(self):
        return self._cur_py is not None

    # -- the seam ----------------------------------------------------------
    def _on_enter(self, label, cmd):
        # Always chain the previously installed hook (coverage etc.) first.
        if self._prev_hook is not None:
            try:
                self._prev_hook(label, cmd)
            except Exception:
                pass
        if not self._enabled:
            return

        task = FrameContext.task
        lnum = getattr(cmd, "line_num", None)
        line_key = (getattr(cmd, "file_num", None), lnum)

        reason = None
        # Breakpoint: cheap line pre-filter, then confirm the file by BASENAME
        # (file_num isn't stable across a mission's several compiles). Stop once
        # per arrival (a source line can compile to several nodes).
        if lnum in self._armed_lines:
            base = _base(_file_name_of(cmd))
            bkey = (base, lnum)
            matched = bkey in self._armed
            # Diagnostic (capped): a breakpoint's LINE ran but in a different
            # file than the editor set it on — the tell-tale of a name mismatch.
            # Silent when things match, so normal runs/logpoints stay clean.
            if (not matched and self.on_output is not None and self._trace_budget > 0
                    and (base, lnum) not in self._trace_seen):
                self._trace_seen.add((base, lnum))
                self._trace_budget -= 1
                want = sorted({b for (b, l) in self._armed if l == lnum})
                self.on_output(f"[mast-trace] a breakpoint line {lnum} ran in '{base}' "
                               f"but breakpoints for that line are set in {want} (no match)")
            if matched and bkey != self._prev_bp:
                reason = self._eval_breakpoint(bkey, task)
            self._prev_bp = bkey
        else:
            self._prev_bp = None

        if reason is None and self._step is not None and self._step_satisfied(task, line_key):
            reason = "step"

        self._prev_line = line_key

        if reason is not None:
            self._step = None
            self._park(task, label, cmd, reason)

    def _eval_breakpoint(self, bkey, task):
        """Decide whether an armed line stops: honor condition, hitCondition, and
        logpoints. Returns "breakpoint" to stop, or None to keep running."""
        meta = self._armed.get(bkey)
        if meta is None:
            return "breakpoint"
        cond = meta.get("condition")
        if cond:
            try:
                if not self._eval_in_task(cond, task):
                    return None
            except Exception:
                pass  # a broken condition shouldn't swallow the breakpoint
        meta["hits"] += 1
        hc = meta.get("hitCondition")
        if hc and not _hit_ok(hc, meta["hits"]):
            return None
        log = meta.get("logMessage")
        if log is not None:
            if self.on_output is not None:
                try:
                    self.on_output(self._interpolate(log, task))
                except Exception:
                    pass
            return None  # logpoints never stop
        return "breakpoint"

    def _eval_in_task(self, expr, task):
        return eval(expr, MastGlobals.globals, task.get_symbols())

    def _interpolate(self, message, task):
        """Replace {expr} in a logpoint message with evaluated values."""
        import re
        def sub(m):
            try:
                return str(self._eval_in_task(m.group(1), task))
            except Exception as err:
                return "{" + m.group(1) + f"=?{err.__class__.__name__}}}"
        return re.sub(r"\{([^{}]+)\}", sub, message)

    def set_variable(self, scope, name, value_expr, task=None):
        """Assign a variable in a scope (evaluating value_expr in task scope).
        Returns the new value."""
        task = task or (self._cur[0] if self._cur else None)
        if task is None:
            raise RuntimeError("no paused task")
        value = self._eval_in_task(value_expr, task)
        if scope == "Shared":
            Agent.SHARED.set_inventory_value(name, value)
        elif scope == "Global":
            MastGlobals.globals[name] = value
        elif scope == "Frame" and task.label_stack and task.label_stack[-1].data is not None:
            task.label_stack[-1].data[name] = value
        else:  # Task (and Frame fallback)
            task.set_inventory_value(name, value)
        return value

    def _step_satisfied(self, task, line_key):
        st = self._step
        if st["task"] is not task:          # only the stepping task steps
            return False
        if line_key == st["line"]:          # still on the same source line
            return False
        depth = len(task.label_stack)
        mode = st["mode"]
        if mode == "in":
            return True
        if mode == "over":
            return depth <= st["depth"]
        if mode == "out":
            return depth < st["depth"]
        return True

    def _park(self, task, label, cmd, reason):
        """Freeze the tick thread here until the controller releases it."""
        self._cur = (task, label, cmd)
        self._reason = reason
        self._paused = True
        self._go.clear()
        self._stopped.set()      # tell the controller we are parked
        self._go.wait()          # <-- tick thread blocks here
        self._paused = False

    # -- controller side (called from another thread while parked) ---------
    def wait_for_pause(self, timeout=5.0):
        """Block until the tick thread parks at a stop. Returns True if paused,
        False on timeout. The controller owns clearing ``_stopped``."""
        if not self._stopped.wait(timeout):
            return False
        self._stopped.clear()
        return True

    def _release(self, step=None):
        self._step = step
        self._go.set()

    def _release_py(self, action):
        self._py_action = action
        self._go.set()

    def resume(self):
        if self._cur_py is not None:
            return self._release_py("cont")
        self._release(None)

    def step_in(self):
        if self._cur_py is not None:
            return self._release_py("step")
        self.arm_python_step()          # a MAST step-in may descend into Python
        self._release(self._make_step("in"))

    def step_over(self):
        if self._cur_py is not None:
            return self._release_py("next")
        self._release(self._make_step("over"))

    def step_out(self):
        if self._cur_py is not None:
            return self._release_py("out")
        self._release(self._make_step("out"))

    def _make_step(self, mode):
        task, _label, cmd = self._cur
        return {
            "mode": mode,
            "task": task,
            "depth": len(task.label_stack),
            "line": (getattr(cmd, "file_num", None), getattr(cmd, "line_num", None)),
        }

    # -- inspection --------------------------------------------------------
    def location(self):
        if self._cur_py is not None:
            f = self._cur_py
            code = f.f_code
            return {"reason": self._reason, "task_id": None, "label": code.co_name,
                    "file": code.co_filename, "path": code.co_filename,
                    "line": f.f_lineno, "loc": None, "cmd": "python"}
        if self._cur is None:
            return None
        task, label, cmd = self._cur
        return {
            "reason": self._reason,
            "task_id": getattr(task, "id", None),
            "label": label,
            "file": _file_name_of(cmd),
            "path": _abs_file_of(cmd),
            "line": getattr(cmd, "line_num", None),
            "loc": getattr(cmd, "loc", None),
            "cmd": cmd.__class__.__name__ if cmd is not None else None,
        }

    def _py_stack(self):
        """Python frames (innermost out) to the eval boundary, then the MAST
        node we stepped from as the bottom frame — one merged call stack."""
        frames = []
        f = self._cur_py
        while f is not None:
            code = f.f_code
            name = code.co_filename
            if name == "<string>":
                break
            frames.append({"label": code.co_name, "file": name, "path": name,
                           "line": f.f_lineno, "loc": None, "cmd": "python"})
            f = f.f_back
        if self._cur is not None:               # MAST frame underneath
            task, label, cmd = self._cur
            frames.append(self._frame(label, cmd))
        return frames

    def _frame(self, label, cmd):
        return {
            "label": label,
            "file": _file_name_of(cmd),
            "path": _abs_file_of(cmd),        # absolute, so the editor can open it
            "line": getattr(cmd, "line_num", None),
            "loc": getattr(cmd, "loc", None),
            "cmd": cmd.__class__.__name__ if cmd is not None else None,
        }

    def stack(self, task=None):
        """Call stack, innermost first: the active node then each label_stack
        caller frame (a `call`/inline push saved its return location)."""
        if self._cur_py is not None:
            return self._py_stack()
        task = task or (self._cur[0] if self._cur else None)
        if task is None:
            return []
        frames = []
        label = self._cur[1] if (self._cur and self._cur[0] is task) else getattr(task.active_ticker, "active_label", None)
        frames.append(self._frame(label, task.get_active_node()))
        for pd in reversed(task.label_stack):
            node = None
            lbl = self._mast.labels.get(pd.label) if self._mast else None
            if lbl is not None and 0 <= pd.active_cmd < len(lbl.cmds):
                node = lbl.cmds[pd.active_cmd]
            frames.append(self._frame(pd.label, node))
        return frames

    def scopes(self, task=None):
        """Separated variable scopes (Frame / Task / Shared / Global).
        In Python mode: the frame's Locals + Globals."""
        if self._cur_py is not None:
            f = self._cur_py
            return {
                "Locals": _clean(f.f_locals),
                "Global": _clean(MastGlobals.globals),
            }
        task = task or (self._cur[0] if self._cur else None)
        if task is None:
            return {}
        frame = {}
        if task.label_stack and task.label_stack[-1].data:
            frame = _clean(task.label_stack[-1].data)
        return {
            "Frame": frame,
            "Task": _clean(task.inventory.collections),
            "Shared": _clean(Agent.SHARED.inventory.collections),
            "Global": _clean(MastGlobals.globals),
        }

    def variables(self, scope, task=None):
        return self.scopes(task).get(scope, {})

    def symbols(self, task=None):
        """Merged namespace exactly as the interpreter sees it (locals for eval)."""
        task = task or (self._cur[0] if self._cur else None)
        return _clean(task.get_symbols()) if task is not None else {}

    def eval(self, expr, task=None):
        """Evaluate a watch/eval expression in the paused task's scope.

        Uses the interpreter's own namespace. Read-oriented; may have side
        effects if the expression mutates state — callers gate that."""
        task = task or (self._cur[0] if self._cur else None)
        if task is None:
            raise RuntimeError("no paused task")
        return eval(expr, MastGlobals.globals, task.get_symbols())


def run_scheduler_in_thread(runner, label="main", inputs=None):
    """Start ``label`` and tick ``runner`` to completion on a daemon thread.

    The task is started **inside the worker** because ``start_task`` ticks once
    immediately (mastscheduler.py:1350) — starting it on the caller's thread
    would let the caller block at a breakpoint. Returns the thread (already
    started); ``thread.join()`` waits for the mission to finish.
    """
    def _run():
        runner.start_task(label, inputs)
        while runner.is_running():
            runner.tick()

    t = threading.Thread(target=_run, name="mast-debug-runner", daemon=True)
    t.start()
    return t
