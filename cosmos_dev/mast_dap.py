"""Debug Adapter Protocol (DAP) front-end for the MAST debug core (dev-only).

Phase 2 of MAST_DEBUGGER_PLAN.md. Translates DAP requests into ``MastDebugCore``
calls and emits DAP events (``initialized`` / ``stopped`` / ``continued`` /
``terminated`` / ``output``). This is what VS Code's generic debugger UI drives.

Two seams keep it testable and reusable:

- **Transport-agnostic** — construct with a ``send(message: dict)`` callback.
  ``run_stdio()`` wires that to LSP-style ``Content-Length`` framing on
  stdin/stdout (the same framing ``amd_lsp`` uses); a unit test wires it to a
  list and calls ``handle()`` directly.
- **Mission-loading-agnostic** — construct with a ``runner_factory(launch_args)``
  returning ``(errors, runner, mast)``. Tests pass a factory that compiles a
  code string; the ``sbs dap`` command will pass one that loads a real mission
  via cosmos_dev.

Threading: ``MastDebugCore`` parks the MAST tick thread at a stop. A single
``_monitor`` thread owns ``wait_for_pause()`` and turns each stop into a
``stopped`` event (and mission end into ``terminated``); request handlers run on
the protocol thread. All outgoing writes go through one lock.

Like the rest of cosmos_dev this is never shipped in the ``.sbslib``.
"""
import json
import os
import re
import sys
import threading
import zipfile

from sbs_utils.agent import Agent
from .mast_debug import MastDebugCore, run_scheduler_in_thread

# A source path that lives inside a packaged library zip, e.g.
#   …\artemis-sbs.sbs_utils.v1.4.0.sbslib\sbs_utils\procedural\terrain.py
#   …\lib.mastlib\some\file.mast
_ZIP_RE = re.compile(r'(?i)^(.*?\.(?:sbslib|mastlib|zip))[\\/](.+)$')


def _read_source(path):
    """Read a source file's text — from disk, or extracted from a .sbslib /
    .mastlib / .zip when the path points inside one (zipimport / mastlib)."""
    if not path:
        raise ValueError("no source path")
    m = _ZIP_RE.match(path)
    if m:
        zip_path, internal = m.group(1), m.group(2).replace("\\", "/")
        with zipfile.ZipFile(zip_path) as z:
            return z.read(internal).decode("utf-8", "replace")
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _is_readable_source(path):
    return bool(path) and (os.path.isfile(path) or _ZIP_RE.match(path) is not None)

# Stable variablesReference ids for the four scopes at the current stop.
_SCOPE_REFS = {1: "Frame", 2: "Task", 3: "Shared", 4: "Global"}
_REF_BY_SCOPE = {v: k for k, v in _SCOPE_REFS.items()}


class MastDapAdapter:
    def __init__(self, send, runner_factory=None, attach_provider=None, on_configured=None):
        self._send_raw = send
        self._runner_factory = runner_factory
        self._attach_provider = attach_provider   # () -> (errors, running_runner, mast)
        self._on_configured = on_configured       # fired once the client finishes config
        self._seq = 0
        self._send_lock = threading.Lock()

        self._dbg = MastDebugCore()
        self._dbg.on_output = self._emit_output   # logpoints -> DAP output events
        self._runner = None
        self._mast = None
        self._worker = None            # owned tick thread (launch mode only)
        self._external = False         # True when attached to a live mission loop
        self._monitor = None
        self._stop_monitor = False
        self._released = threading.Event()
        self._launch_label = "main"
        self._launch_inputs = None

        # DAP threadId (small int) <-> MAST task
        self._threads = {}          # task.id -> threadId
        self._task_by_tid = {}      # threadId -> task

        # sourceReference -> path, for sources hosted inside a .sbslib/.mastlib zip
        self._source_refs = {}
        self._src_ref_seq = 1000

    # -- outgoing ----------------------------------------------------------
    def _next_seq(self):
        self._seq += 1
        return self._seq

    def _send(self, message):
        message["seq"] = self._next_seq()
        with self._send_lock:
            self._send_raw(message)

    def _respond(self, request, body=None, success=True, message=None):
        resp = {
            "type": "response",
            "request_seq": request.get("seq"),
            "success": success,
            "command": request.get("command"),
        }
        if message is not None:
            resp["message"] = message
        if body is not None:
            resp["body"] = body
        self._send(resp)

    def _event(self, event, body=None):
        self._send({"type": "event", "event": event, "body": body or {}})

    # -- dispatch ----------------------------------------------------------
    def handle(self, request):
        cmd = request.get("command")
        method = getattr(self, f"_req_{cmd}", None)
        if method is None:
            self._respond(request, success=False, message=f"unsupported request: {cmd}")
            return
        try:
            method(request)
        except Exception as err:  # never let one bad request kill the adapter
            self._respond(request, success=False, message=str(err))

    # -- lifecycle requests ------------------------------------------------
    def _req_initialize(self, request):
        self._respond(request, body={
            "supportsConfigurationDoneRequest": True,
            "supportsEvaluateForHovers": True,
            "supportsStepInTargetsRequest": False,
            "supportsTerminateRequest": True,
            "supportsConditionalBreakpoints": True,
            "supportsHitConditionalBreakpoints": True,
            "supportsLogPoints": True,
            "supportsSetVariable": True,
        })
        # `initialized` is emitted after launch indexes the mast, so
        # setBreakpoints (which follows it) can resolve against a real index.

    def _req_launch(self, request):
        # A socket adapter serving an already-running mission has no
        # runner_factory: a `launch` config over this socket (VS Code spawned the
        # runner and connected) means "attach to the mission I'm serving".
        if self._runner_factory is None and self._attach_provider is not None:
            return self._req_attach(request)
        args = request.get("arguments", {})
        self._launch_label = args.get("label", "main")
        self._launch_inputs = args.get("inputs")
        errors, runner, mast = self._runner_factory(args)
        if errors:
            self._respond(request, success=False, message="; ".join(map(str, errors)))
            return
        self._runner = runner
        self._mast = mast
        self._dbg.install(mast)
        self._respond(request)
        self._event("initialized")  # now the client may setBreakpoints

    def _req_attach(self, request):
        """Attach to an already-running mission loop (someone else owns ticking).
        We only install the debug seam; breakpoints park that external loop's
        thread, and disconnect detaches without ending the mission."""
        if self._attach_provider is None:
            self._respond(request, success=False, message="attach not supported")
            return
        errors, runner, mast = self._attach_provider(request.get("arguments", {}))
        if errors or runner is None:
            self._respond(request, success=False,
                          message="; ".join(map(str, errors or ["no running mission"])))
            return
        self._runner = runner
        self._mast = mast
        self._external = True
        self._dbg.install(mast)
        self._dbg.index_all()               # pick up every live mission mast
        self._respond(request)
        self._event("initialized")

    def _report_indexed_files(self):
        files = self._dbg.files()
        self._emit_output(f"[mast] {len(files)} source file(s) indexed for debugging")
        for f in files:
            self._emit_output(f"[mast]   {f}")

    def _enable_python_step(self):
        """Turn on step-into-Python. It self-guards at runtime (skips if debugpy
        already owns the tracer), so enabling is always safe."""
        try:
            self._dbg.enable_python_step()
            self._emit_output("[mast] step-into-Python enabled (Step In descends into "
                              "Python the MAST evaluates; disabled automatically under debugpy)")
        except Exception as err:
            self._emit_output(f"[mast] step-into-Python unavailable: {err}")

    def _req_setBreakpoints(self, request):
        args = request.get("arguments", {})
        source = args.get("source", {})
        name = source.get("path") or source.get("name")
        bps = args.get("breakpoints", [])
        # Re-scan live masts first so lazily-compiled map files (e.g. siege.mast)
        # are indexed by the time we arm breakpoints against them.
        self._dbg.index_all()
        specs = [{"line": bp["line"], "condition": bp.get("condition"),
                  "hitCondition": bp.get("hitCondition"),
                  "logMessage": bp.get("logMessage")} for bp in bps]
        self._dbg.set_breakpoints(name, specs)
        verified = []
        for bp in bps:
            bound = self._dbg.verified_line(name, bp["line"])
            verified.append({"verified": bound is not None, "line": bound or bp["line"]})
        if any(not v["verified"] for v in verified):
            self._emit_output(f"[mast] breakpoint(s) in {name} not bound "
                              f"(file not indexed yet — start the map, then toggle the breakpoint)")
        self._respond(request, body={"breakpoints": verified})

    def _req_configurationDone(self, request):
        self._respond(request)
        # Announce AFTER config: DAP output events emitted between `initialized`
        # and here are dropped by VS Code (the session isn't "running" yet).
        self._report_indexed_files()
        self._enable_python_step()
        self._start_inspection()
        if self._external:
            self._start_monitor()   # the mission loop already ticks; just watch
        else:
            self._start()           # launch mode: we own the tick thread
        if self._on_configured is not None:
            try:
                self._on_configured()   # e.g. release the runner's auto-start gate
            except Exception:
                pass

    def _start(self):
        self._worker = run_scheduler_in_thread(self._runner, self._launch_label, self._launch_inputs)
        self._start_monitor()

    def _start_monitor(self):
        self._stop_monitor = False
        self._released.clear()
        self._monitor = threading.Thread(target=self._monitor_loop, name="mast-dap-monitor", daemon=True)
        self._monitor.start()

    # -- run control -------------------------------------------------------
    def _req_continue(self, request):
        self._respond(request, body={"allThreadsContinued": True})
        self._release(self._dbg.resume)

    def _req_next(self, request):
        self._respond(request)
        self._release(self._dbg.step_over)

    def _req_stepIn(self, request):
        self._respond(request)
        self._release(self._dbg.step_in)

    def _req_stepOut(self, request):
        self._respond(request)
        self._release(self._dbg.step_out)

    def _release(self, action):
        action()               # resume / step_* sets the core's go event
        self._released.set()   # let the monitor loop back to wait_for_pause

    # -- state inspection --------------------------------------------------
    def _req_threads(self, request):
        threads = []
        tasks = list(self._runner.tasks) if self._runner else []
        if not tasks and self._dbg._cur:
            tasks = [self._dbg._cur[0]]
        for task in tasks:
            threads.append({"id": self._thread_id(task), "name": task.name or f"task-{self._thread_id(task)}"})
        if not threads:
            threads = [{"id": 1, "name": "main"}]
        self._respond(request, body={"threads": threads})

    def _req_stackTrace(self, request):
        task = self._resolve_thread(request.get("arguments", {}).get("threadId"))
        frames = []
        for i, f in enumerate(self._dbg.stack(task)):
            frames.append({
                "id": i,
                "name": f["label"] or "?",
                "line": f["line"] or 0,
                "column": 1,
                "source": self._source_for(f.get("path") or f.get("file")),
            })
        self._respond(request, body={"stackFrames": frames, "totalFrames": len(frames)})

    def _source_for(self, path):
        """DAP source object. A real file gets a `path` the editor opens itself;
        a file inside a .sbslib/.mastlib zip gets a `sourceReference` so the
        editor asks us (via the `source` request) for the extracted text."""
        if not path:
            return None
        name = os.path.basename(path) or path
        if os.path.isfile(path):
            return {"name": name, "path": path}
        if _ZIP_RE.match(path):
            ref = next((r for r, p in self._source_refs.items() if p == path), None)
            if ref is None:
                self._src_ref_seq += 1
                ref = self._src_ref_seq
                self._source_refs[ref] = path
            # A short display path (…lib.sbslib/…/terrain.py) reads better than the
            # full absolute zip path.
            return {"name": name, "path": path, "sourceReference": ref}
        return {"name": name, "path": path}

    def _req_source(self, request):
        # The editor can't open the file itself (e.g. inside a .sbslib/.mastlib
        # zip) and asks us for the text — read from disk or extract from the zip.
        args = request.get("arguments", {})
        ref = args.get("sourceReference")
        src = args.get("source") or {}
        path = self._source_refs.get(ref) or src.get("path") or src.get("name")
        try:
            self._respond(request, body={"content": _read_source(path)})
        except Exception as err:
            self._respond(request, success=False, message=f"cannot read {path}: {err}")

    def _req_scopes(self, request):
        # Built dynamically: MAST mode gives Frame/Task/Shared/Global; Python mode
        # (stepped into eval) gives Locals/Global.
        self._scope_refs = {}
        out = []
        for i, name in enumerate(self._dbg.scopes().keys(), start=1):
            self._scope_refs[i] = name
            out.append({"name": name, "variablesReference": i, "expensive": False})
        self._respond(request, body={"scopes": out})

    def _req_variables(self, request):
        ref = request.get("arguments", {}).get("variablesReference")
        scope = getattr(self, "_scope_refs", {}).get(ref) or _SCOPE_REFS.get(ref)
        out = []
        if scope is not None:
            for k, v in self._dbg.variables(scope).items():
                out.append({"name": str(k), "value": repr(v), "variablesReference": 0})
        self._respond(request, body={"variables": out})

    def _req_evaluate(self, request):
        expr = request.get("arguments", {}).get("expression", "")
        try:
            val = self._dbg.eval(expr)
            self._respond(request, body={"result": repr(val), "variablesReference": 0})
        except Exception as err:
            self._respond(request, success=False, message=str(err))

    def _req_setVariable(self, request):
        args = request.get("arguments", {})
        ref = args.get("variablesReference")
        scope = getattr(self, "_scope_refs", {}).get(ref) or _SCOPE_REFS.get(ref)
        if scope is None or scope not in ("Frame", "Task", "Shared", "Global"):
            self._respond(request, success=False, message="unknown variables scope")
            return
        try:
            newval = self._dbg.set_variable(scope, args.get("name"), args.get("value"))
            self._respond(request, body={"value": repr(newval), "variablesReference": 0})
        except Exception as err:
            self._respond(request, success=False, message=str(err))

    def _emit_output(self, text):
        self._event("output", {"category": "console", "output": text + "\n"})

    # -- live inspection (signals, and later gui/brains/agents) ------------
    def _start_inspection(self):
        """Stream live-inspection events (e.g. signals) to the editor as
        `mast/inspect` custom events, without pausing the mission."""
        from .mast_inspect import BUS, ALL_TAPS
        if getattr(self, "_inspect_taps", None):
            return
        BUS.subscribe(lambda ev: self._event("mast/inspect", ev))
        self._inspect_taps = [tap().install() for tap in ALL_TAPS]

    def _stop_inspection(self):
        from .mast_inspect import BUS
        for tap in getattr(self, "_inspect_taps", []) or []:
            tap.uninstall()
        self._inspect_taps = []
        BUS.unsubscribe()

    # -- teardown ----------------------------------------------------------
    def _req_disconnect(self, request):
        self._teardown()
        self._respond(request)

    _req_terminate = _req_disconnect

    def _teardown(self):
        self._stop_monitor = True
        self._stop_inspection()
        self._dbg.disable()
        self._dbg.uninstall()   # releases any parked tick thread
        self._released.set()

    # -- monitor thread ----------------------------------------------------
    def _monitor_loop(self):
        reindex_every = 20            # ~1s at 0.05s ticks
        n = 0
        prev_files = set(self._dbg.files())
        while not self._stop_monitor:
            if self._dbg.wait_for_pause(0.05):
                self._emit_stopped()
                self._released.wait()          # block until continue/step/disconnect
                self._released.clear()
            elif self._external and not self._dbg.is_paused:
                # Attach mode: maps compile lazily, so re-scan periodically and
                # re-arm (and announce) when new source files appear.
                n += 1
                if n >= reindex_every:
                    n = 0
                    self._dbg.index_all()
                    now = set(self._dbg.files())
                    for f in sorted(now - prev_files):
                        self._emit_output(f"[mast] newly indexed: {f}")
                    prev_files = now
            elif not self._external and self._worker is not None and not self._worker.is_alive():
                # Launch mode only: the mission we own finished. In attach mode
                # the mission outlives the debug session, so we never terminate
                # it here — only disconnect ends the session.
                self._event("terminated")
                self._event("exited", {"exitCode": 0})
                return

    def _emit_stopped(self):
        loc = self._dbg.location() or {}
        task = self._dbg._cur[0] if self._dbg._cur else None
        reason = {"breakpoint": "breakpoint", "step": "step"}.get(loc.get("reason"), "pause")
        self._event("stopped", {
            "reason": reason,
            "threadId": self._thread_id(task) if task is not None else 1,
            "allThreadsStopped": True,
        })

    # -- thread id mapping -------------------------------------------------
    def _thread_id(self, task):
        if task is None:
            return 1
        if task.id not in self._threads:
            tid = len(self._threads) + 1
            self._threads[task.id] = tid
            self._task_by_tid[tid] = task
        return self._threads[task.id]

    def _resolve_thread(self, tid):
        if tid in self._task_by_tid:
            return self._task_by_tid[tid]
        return self._dbg._cur[0] if self._dbg._cur else None


# ---------------------------------------------------------------------------
# stdio transport (LSP-style Content-Length framing) for the `sbs dap` command.
# ---------------------------------------------------------------------------
def _read_message(stream):
    headers = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.decode("utf-8") if isinstance(line, bytes) else line
        line = line.strip()
        if line == "":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    length = int(headers.get("content-length", 0))
    body = stream.read(length)
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return json.loads(body)


def _write_message(stream, message):
    data = json.dumps(message).encode("utf-8")
    stream.write(f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8"))
    stream.write(data)
    stream.flush()


# ---------------------------------------------------------------------------
# Launch-mode factory: compile a .mast file into a debuggable (not-yet-started)
# runner. Mirrors sbs_utils.mast.mast_run.mast_run but stops before start_task,
# so the adapter's worker thread owns starting + ticking. Targets logic/library
# .mast; full StoryScheduler missions are future attach-mode work.
# ---------------------------------------------------------------------------
_PROCEDURAL_MODULES = (
    "sbs_utils.procedural.behavior",
    "sbs_utils.procedural.brain",
    "sbs_utils.procedural.execution",
    "sbs_utils.procedural.inventory",
    "sbs_utils.procedural.lifeform",
    "sbs_utils.procedural.links",
    "sbs_utils.procedural.maps",
    "sbs_utils.procedural.objective",
    "sbs_utils.procedural.prefab",
    "sbs_utils.procedural.roles",
    "sbs_utils.procedural.signal",
    "sbs_utils.procedural.quest",
    "sbs_utils.procedural.settings",
    "sbs_utils.procedural.timers",
)


def build_file_runner(filename):
    """Compile ``filename`` and return ``(errors, runner, mast)`` without running.

    ``runner.runtime_errors`` collects any runtime errors (the worker thread
    can't assert cleanly). On compile error, ``runner`` is None.
    """
    from sbs_utils.mast.mast import Mast
    from sbs_utils.mast.mastscheduler import MastScheduler
    from sbs_utils.mast.mast_run import JustEnoughSim, JustEnoughSbs
    from sbs_utils.mast.mast_globals import MastGlobals
    from sbs_utils.helpers import FrameContext, Context, FakeEvent
    from sbs_utils.agent import clear_shared
    import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (register story nodes)

    clear_shared()   # fresh shared state so a re-launch in the same process
                     # doesn't see prior labels as "conflicts with shared name"
    for mod in _PROCEDURAL_MODULES:
        MastGlobals.import_python_module(mod)
    from sbs_utils.procedural.execution import mast_log
    Mast.make_global_var("log", mast_log)
    Mast.include_code = True   # so runtime errors + the debugger can show source

    mast = Mast()
    errors = mast.from_file(filename, None)
    if errors:
        return errors, None, mast

    class _DebugScheduler(MastScheduler):
        def __init__(self, m):
            super().__init__(m)
            self.runtime_errors = []

        def runtime_error(self, message):
            self.runtime_errors.append(message)

    FrameContext.context = Context(JustEnoughSim(), JustEnoughSbs(), FakeEvent())
    FrameContext.mast = mast
    return errors, _DebugScheduler(mast), mast


def file_runner_factory(default_mast=None):
    """A ``runner_factory`` for MastDapAdapter that compiles the launch request's
    ``program``/``mast`` (or ``default_mast``)."""
    def factory(launch_args):
        path = launch_args.get("program") or launch_args.get("mast") or default_mast
        if not path:
            return ["no .mast file given (launch.program)"], None, None
        return build_file_runner(path)
    return factory


def live_mission_provider():
    """An ``attach_provider`` for a mission that is already running in this
    process: resolve the story ``Mast`` (and, best-effort, a scheduler) from the
    live ``FrameContext``. Polls briefly because a tick may be in flight — and
    between ticks ``FrameContext.mast`` is momentarily ``None`` — when the editor
    attaches. ``runner`` may come back ``None`` (only used to list threads, which
    the adapter tolerates)."""
    def provider(_args):
        import time as _time
        from sbs_utils.helpers import FrameContext
        mast = None
        for _ in range(2000):                     # ~20s: an editor may connect
            mast = getattr(FrameContext, "mast", None)   # before the story compiles
            if mast is not None:
                break
            _time.sleep(0.01)
        if mast is None:
            return ["no running mission (FrameContext.mast is None)"], None, None
        scheds = getattr(mast, "schedulers", None)
        runner = next(iter(scheds), None) if scheds else None
        return [], runner, mast
    return provider


def serve_dap_socket(host="127.0.0.1", port=4711, runner_factory=None,
                     attach_provider=None, ready=None, stop=None, on_configured=None):
    """Serve DAP over a TCP socket (VS Code `DebugAdapterServer` mode).

    This is the attach transport: a mission is already running and ticking on its
    own thread; the editor connects here, and control requests (continue/step)
    are serviced on THIS thread, never the parked tick thread — which is what
    makes breakpoints safe in the single-loop mission runner.

    ``ready(actual_port)`` is called once bound (use ``port=0`` for an ephemeral
    port). ``stop`` (an Event) unblocks a waiting accept on shutdown.
    """
    import socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((host, port))
        srv.listen(1)
    except OSError as e:
        print(f"[mast-dap] FAILED to bind {host}:{port}: {e} "
              f"(is another mission still running on this port?)", file=sys.stderr)
        srv.close()
        return
    srv.settimeout(0.5)
    if ready is not None:
        ready(srv.getsockname()[1])

    # Serve clients one at a time but KEEP the listener open across sessions, so
    # the debugger can disconnect and re-attach (or a failed attach can retry)
    # without restarting the mission. Only `stop` (or process exit) ends it.
    try:
        while stop is None or not stop.is_set():
            conn = None
            while conn is None:
                if stop is not None and stop.is_set():
                    return
                try:
                    conn, _addr = srv.accept()
                except socket.timeout:
                    continue

            rfile = conn.makefile("rb")
            wfile = conn.makefile("wb")
            lock = threading.Lock()

            def send(message, _wfile=wfile, _lock=lock):
                with _lock:
                    _write_message(_wfile, message)

            adapter = MastDapAdapter(send, runner_factory=runner_factory,
                                     attach_provider=attach_provider, on_configured=on_configured)
            try:
                while True:
                    msg = _read_message(rfile)
                    if msg is None:
                        break
                    adapter.handle(msg)
                    if msg.get("command") in ("disconnect", "terminate"):
                        break
            except OSError:
                pass                      # client vanished; fall through to re-accept
            finally:
                adapter._teardown()       # uninstall this session's hook
                try:
                    conn.close()
                except OSError:
                    pass
    finally:
        srv.close()


def run_stdio(runner_factory, stdin=None, stdout=None):
    """Serve DAP over stdin/stdout. ``runner_factory(launch_args)`` builds the
    mission. Returns when the client disconnects."""
    rstream = stdin or sys.stdin.buffer
    wstream = stdout or sys.stdout.buffer
    lock = threading.Lock()

    def send(message):
        with lock:
            _write_message(wstream, message)

    adapter = MastDapAdapter(send, runner_factory)
    while True:
        msg = _read_message(rstream)
        if msg is None:
            break
        adapter.handle(msg)
        if msg.get("command") in ("disconnect", "terminate"):
            break
