"""Phase 2 tests: drive the MAST DAP adapter with Debug Adapter Protocol
messages, no VS Code and no stdio — a list captures emitted messages and we
assert the initialize -> launch -> setBreakpoints -> stopped -> inspect -> step
-> continue -> terminated flow end to end.

See MAST_DEBUGGER_PLAN.md phase 2.
"""
import io
import os
import threading
import time
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

# Reuse the compile harness + fixtures from the debug-core tests.
from tests.test_mast_debug import (
    build_runner, line_of, logged, CODE, FILE, LOOP5_CODE, SETVAR_CODE,
)
from cosmos_dev.mast_dap import (
    MastDapAdapter, build_file_runner, file_runner_factory, run_stdio,
    serve_dap_socket, _read_message, _write_message, _read_source, _is_readable_source,
)
from cosmos_dev.mast_debug import MastDebugCore, run_scheduler_in_thread

FIXTURE = os.path.join(os.path.dirname(__file__), "mast", "debug_fixture.mast")


class DapClient:
    """Minimal in-memory DAP client: sends request dicts, captures messages."""
    def __init__(self, runner_factory=None, attach_provider=None, on_configured=None):
        self._seq = 0
        self._messages = []
        self._lock = threading.Lock()
        self.adapter = MastDapAdapter(self._capture, runner_factory=runner_factory,
                                      attach_provider=attach_provider, on_configured=on_configured)
        self.runner = None  # set by the factory wrapper
        self._cursor = {}   # event name -> count already consumed

    def _capture(self, message):
        with self._lock:
            self._messages.append(message)

    def send(self, command, **arguments):
        self._seq += 1
        req = {"type": "request", "seq": self._seq, "command": command}
        if arguments:
            req["arguments"] = arguments
        self.adapter.handle(req)
        return self.response(command)

    def response(self, command):
        with self._lock:
            for m in reversed(self._messages):
                if m.get("type") == "response" and m.get("command") == command:
                    return m
        return None

    def events(self, name):
        with self._lock:
            return [m for m in self._messages if m.get("type") == "event" and m.get("event") == name]

    def wait_event(self, name, timeout=4.0):
        """Return the next event of ``name`` not yet consumed (cursor-based, so
        repeated calls wait for successive stops rather than the same one)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            evs = self.events(name)
            seen = self._cursor.get(name, 0)
            if len(evs) > seen:
                self._cursor[name] = seen + 1
                return evs[seen]
            time.sleep(0.01)
        return None

    def wait_inspect(self, kind, timeout=4.0):
        """Return the next ``mast/inspect`` event of a given ``kind`` (signal /
        agents / brains / quests / widgets), cursor-based per kind.

        The adapter installs ALL taps at once, so the poller taps (WorldTap /
        BrainTap / QuestTap) stream ``agents`` / ``brains`` / ``quests``
        snapshots under the same ``mast/inspect`` event name the instant
        inspection starts — usually BEFORE the mission emits its first signal.
        Waiting for the first ``mast/inspect`` event is therefore racy; a test
        must filter by the kind it actually asserts on."""
        cursor_key = ("mast/inspect", kind)
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                evs = [m for m in self._messages
                       if m.get("type") == "event" and m.get("event") == "mast/inspect"
                       and m.get("body", {}).get("kind") == kind]
            seen = self._cursor.get(cursor_key, 0)
            if len(evs) > seen:
                self._cursor[cursor_key] = seen + 1
                return evs[seen]
            time.sleep(0.01)
        return None


class TestMastDap(unittest.TestCase):
    def tearDown(self):
        from sbs_utils.mast.mastscheduler import MastTicker
        MastTicker.on_enter_node = None

    def _factory(self, holder):
        def factory(launch_args):
            errors, runner, mast = build_runner(CODE)
            holder["runner"] = runner
            holder["mast"] = mast
            return errors, runner, mast
        return factory

    def test_full_dap_session(self):
        holder = {}
        client = DapClient(self._factory(holder))

        # Pre-compute line numbers from an identical compile (deterministic).
        _e, _r, probe_mast = build_runner(CODE)
        bp_x2 = line_of(probe_mast, "x = 2")
        ln_logx = line_of(probe_mast, 'log("x is')

        # -- initialize -----------------------------------------------------
        resp = client.send("initialize", adapterID="mast")
        self.assertTrue(resp["success"])
        self.assertTrue(resp["body"]["supportsConfigurationDoneRequest"])

        # -- launch (builds + indexes the mast, then emits `initialized`) ---
        resp = client.send("launch", label="main")
        self.assertTrue(resp["success"], resp.get("message"))
        self.assertTrue(client.events("initialized"), "no initialized event")

        # -- setBreakpoints -------------------------------------------------
        resp = client.send("setBreakpoints",
                           source={"path": FILE},
                           breakpoints=[{"line": bp_x2}])
        bps = resp["body"]["breakpoints"]
        self.assertTrue(bps[0]["verified"])
        self.assertEqual(bps[0]["line"], bp_x2)

        # -- configurationDone starts the run; expect a stopped event -------
        client.send("configurationDone")
        stopped = client.wait_event("stopped")
        self.assertIsNotNone(stopped, "never received stopped event")
        self.assertEqual(stopped["body"]["reason"], "breakpoint")
        tid = stopped["body"]["threadId"]

        # -- threads / stackTrace -------------------------------------------
        resp = client.send("threads")
        self.assertTrue(any(t["id"] == tid for t in resp["body"]["threads"]))

        resp = client.send("stackTrace", threadId=tid)
        frames = resp["body"]["stackFrames"]
        self.assertEqual(frames[0]["line"], bp_x2)
        self.assertEqual(frames[0]["name"], "main")
        self.assertEqual(frames[0]["source"]["path"], FILE)

        # -- scopes / variables: stopped BEFORE `x = 2` runs, so x == 1 -----
        resp = client.send("scopes", frameId=frames[0]["id"])
        scope_names = {s["name"]: s["variablesReference"] for s in resp["body"]["scopes"]}
        task_ref = scope_names["Task"]
        resp = client.send("variables", variablesReference=task_ref)
        vars_by_name = {v["name"]: v["value"] for v in resp["body"]["variables"]}
        self.assertEqual(vars_by_name.get("x"), "1")

        # -- step over -> next line, x now 2 --------------------------------
        client.send("next", threadId=tid)
        stopped = client.wait_event("stopped", timeout=4.0)
        # (clear so a later wait doesn't see this same one)
        resp = client.send("stackTrace", threadId=tid)
        self.assertEqual(resp["body"]["stackFrames"][0]["line"], ln_logx)

        resp = client.send("variables", variablesReference=task_ref)
        self.assertEqual({v["name"]: v["value"] for v in resp["body"]["variables"]}.get("x"), "2")

        # -- evaluate in the paused scope -----------------------------------
        resp = client.send("evaluate", expression="x + 40")
        self.assertTrue(resp["success"])
        self.assertEqual(resp["body"]["result"], "42")

        # -- continue to completion -----------------------------------------
        client.send("continue", threadId=tid)
        term = client.wait_event("terminated")
        self.assertIsNotNone(term, "never received terminated event")

        self.assertEqual(holder["runner"].runtime_errors, [])
        self.assertEqual(logged(holder["runner"]), "x is 2\ndone 10\n")


# A perpetual "mission": main falls through to spin_loop, which increments a
# task-local counter once per iteration and never ends. Models a real mission
# that outlives a debug session.
LOOP_CODE = """
counter = 0
=== spin_loop ===
counter = counter + 1
await delay_test(1)
jump spin_loop
"""

# Same loop, but emits a signal each iteration — for the live Signal Tracer.
SIGNAL_LOOP_CODE = """
counter = 0
=== spin_loop ===
counter = counter + 1
signal_emit("tick_sig", {"n": counter})
await delay_test(1)
jump spin_loop
"""


class TestAttachMode(unittest.TestCase):
    """Attach to a live, indefinitely-running mission loop, break repeatedly,
    then detach WITHOUT ending the mission."""
    def tearDown(self):
        from sbs_utils.mast.mastscheduler import MastTicker
        from sbs_utils.mast.mast import Mast
        MastTicker.on_enter_node = None
        base = getattr(Mast.signal_emit, "_mast_orig", None)
        if base is not None:
            Mast.signal_emit = base   # restore if a signal tap lingered

    def test_signal_tracer_streams_over_attach(self):
        errors, runner, mast = build_runner(SIGNAL_LOOP_CODE)
        self.assertEqual(errors, [])
        stop = threading.Event()

        def mission_loop():
            runner.start_task("main")
            while not stop.is_set():
                runner.tick()
        loop_thread = threading.Thread(target=mission_loop, daemon=True)
        loop_thread.start()
        time.sleep(0.05)

        client = DapClient(attach_provider=lambda a: (errors, runner, mast))
        try:
            client.send("initialize")
            client.send("attach")
            client.send("setBreakpoints", source={"path": FILE}, breakpoints=[])
            client.send("configurationDone")          # starts live inspection
            # Filter by kind: the poller taps (agents/brains/quests) also stream
            # `mast/inspect`, and usually beat the first signal to the bus.
            ev = client.wait_inspect("signal")
            self.assertIsNotNone(ev, "no signal mast/inspect event streamed")
            self.assertEqual(ev["body"]["kind"], "signal")
            self.assertEqual(ev["body"]["payload"]["name"], "tick_sig")
            self.assertIn("n", ev["body"]["payload"]["data"])
            client.send("disconnect")
        finally:
            stop.set()
            loop_thread.join(2.0)

    def test_launch_over_socket_routes_to_attach(self):
        # The one-click mission-launch config is request:"launch", but the runner's
        # socket adapter has an attach_provider (no runner_factory). A `launch`
        # request must route to attach, not call the None runner_factory.
        errors, runner, mast = build_runner(CODE)
        self.assertEqual(errors, [])
        sent = []
        adapter = MastDapAdapter(sent.append, attach_provider=lambda a: ([], runner, mast))
        try:
            adapter.handle({"type": "request", "seq": 1, "command": "initialize"})
            adapter.handle({"type": "request", "seq": 2, "command": "launch", "arguments": {}})
            inits = [m for m in sent if m.get("event") == "initialized"]
            self.assertTrue(inits, "launch did not route to attach")
            resp = [m for m in sent if m.get("command") == "launch"][-1]
            self.assertTrue(resp["success"], resp.get("message"))
        finally:
            adapter.handle({"type": "request", "seq": 3, "command": "disconnect"})

    def test_attach_break_continue_detach(self):
        errors, runner, mast = build_runner(LOOP_CODE)
        self.assertEqual(errors, [])

        # A separate thread owns ticking (as mission_runner does in real life).
        stop = threading.Event()

        def mission_loop():
            runner.start_task("main")
            while not stop.is_set():
                runner.tick()

        loop_thread = threading.Thread(target=mission_loop, name="mission", daemon=True)
        loop_thread.start()
        time.sleep(0.05)  # let it spin a few iterations before we attach

        client = DapClient(attach_provider=lambda args: (errors, runner, mast))
        try:
            self.assertTrue(client.send("initialize")["success"])
            self.assertTrue(client.send("attach")["success"])
            self.assertTrue(client.events("initialized"))

            bp = line_of(mast, "counter = counter + 1")
            client.send("setBreakpoints", source={"path": FILE},
                        breakpoints=[{"line": bp}])
            client.send("configurationDone")

            # First stop inside the loop.
            stopped = client.wait_event("stopped")
            self.assertIsNotNone(stopped, "attach never broke in the loop")
            tid = stopped["body"]["threadId"]
            resp = client.send("scopes", frameId=0)
            task_ref = {s["name"]: s["variablesReference"] for s in resp["body"]["scopes"]}["Task"]
            first = self._var(client, task_ref, "counter")

            # Continue -> the loop runs another iteration and breaks again.
            client.send("continue", threadId=tid)
            self.assertIsNotNone(client.wait_event("stopped"), "did not re-break next iteration")
            second = self._var(client, task_ref, "counter")
            self.assertEqual(second, first + 1, "counter should advance one iteration per stop")

            # Detach: the mission keeps running.
            client.send("disconnect")
            time.sleep(0.05)
            self.assertTrue(loop_thread.is_alive(), "detach must not end the mission")
            self.assertEqual(runner.runtime_errors, [])
        finally:
            stop.set()
            loop_thread.join(timeout=2.0)

    def _var(self, client, ref, name):
        resp = client.send("variables", variablesReference=ref)
        for v in resp["body"]["variables"]:
            if v["name"] == name:
                return int(v["value"])
        raise AssertionError(f"{name} not in variables")


class SocketDapClient:
    """DAP client over a real TCP socket, with a background reader thread so
    async events (stopped/...) are captured while we send requests."""
    def __init__(self, host, port):
        import socket
        self.sock = socket.create_connection((host, port), timeout=5.0)
        self.wfile = self.sock.makefile("wb")
        self.rfile = self.sock.makefile("rb")
        self.msgs = []
        self.lock = threading.Lock()
        self.seq = 0
        self.cursor = {}
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

    def _read_loop(self):
        try:
            while True:
                m = _read_message(self.rfile)
                if m is None:
                    break
                with self.lock:
                    self.msgs.append(m)
        except Exception:
            pass

    def send(self, command, **args):
        self.seq += 1
        req = {"type": "request", "seq": self.seq, "command": command}
        if args:
            req["arguments"] = args
        _write_message(self.wfile, req)

    def wait_event(self, name, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self.lock:
                evs = [m for m in self.msgs if m.get("type") == "event" and m.get("event") == name]
            seen = self.cursor.get(name, 0)
            if len(evs) > seen:
                self.cursor[name] = seen + 1
                return evs[seen]
            time.sleep(0.01)
        return None

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class TestSocketTransport(unittest.TestCase):
    """DAP over a real TCP socket (VS Code DebugAdapterServer / attach mode)."""
    def tearDown(self):
        from sbs_utils.mast.mastscheduler import MastTicker
        MastTicker.on_enter_node = None

    def test_socket_attach_session(self):
        errors, runner, mast = build_runner(LOOP_CODE)
        self.assertEqual(errors, [])

        stop = threading.Event()

        def mission_loop():
            runner.start_task("main")
            while not stop.is_set():
                runner.tick()
        loop_thread = threading.Thread(target=mission_loop, daemon=True)
        loop_thread.start()

        port_box = {}
        port_ready = threading.Event()

        def on_ready(p):
            port_box["port"] = p
            port_ready.set()

        srv_stop = threading.Event()
        server = threading.Thread(target=serve_dap_socket, kwargs=dict(
            host="127.0.0.1", port=0,
            attach_provider=lambda args: (errors, runner, mast),
            ready=on_ready, stop=srv_stop), daemon=True)
        server.start()
        self.assertTrue(port_ready.wait(3.0), "socket server never bound")

        client = SocketDapClient("127.0.0.1", port_box["port"])
        try:
            client.send("initialize")
            client.send("attach")
            self.assertIsNotNone(client.wait_event("initialized"), "no initialized over socket")

            bp = line_of(mast, "counter = counter + 1")
            client.send("setBreakpoints", source={"path": FILE}, breakpoints=[{"line": bp}])
            client.send("configurationDone")

            stopped = client.wait_event("stopped")
            self.assertIsNotNone(stopped, "socket attach never broke")
            self.assertEqual(stopped["body"]["reason"], "breakpoint")

            client.send("continue", threadId=stopped["body"]["threadId"])
            self.assertIsNotNone(client.wait_event("stopped"), "no second stop over socket")

            client.send("disconnect")
            time.sleep(0.1)
            self.assertTrue(loop_thread.is_alive(), "mission ended on detach")
            self.assertEqual(runner.runtime_errors, [])
        finally:
            client.close()
            srv_stop.set()
            stop.set()
            loop_thread.join(timeout=2.0)
            server.join(timeout=2.0)


class TestConditionalAndSetVar(unittest.TestCase):
    """Phase 5 over DAP: conditional/logpoint breakpoints and setVariable."""
    def tearDown(self):
        from sbs_utils.mast.mastscheduler import MastTicker
        MastTicker.on_enter_node = None

    def _factory(self, code, holder):
        def factory(launch_args):
            errors, runner, mast = build_runner(code)
            holder["runner"] = runner
            return errors, runner, mast
        return factory

    def test_on_configured_fires(self):
        # The runner's --dap-wait gate rides this callback: it must fire once the
        # client finishes configurationDone.
        fired = threading.Event()
        client = DapClient(self._factory(CODE, {}), on_configured=fired.set)
        client.send("initialize")
        client.send("launch")
        self.assertFalse(fired.is_set(), "fired too early")
        client.send("setBreakpoints", source={"path": FILE}, breakpoints=[])
        client.send("configurationDone")
        self.assertTrue(fired.wait(2.0), "on_configured never fired")
        client.send("disconnect")

    def test_capabilities_advertised(self):
        client = DapClient(self._factory(CODE, {}))
        caps = client.send("initialize")["body"]
        for cap in ("supportsConditionalBreakpoints", "supportsHitConditionalBreakpoints",
                    "supportsLogPoints", "supportsSetVariable"):
            self.assertTrue(caps.get(cap), f"missing capability {cap}")

    def test_logpoint_emits_output_events(self):
        holder = {}
        client = DapClient(self._factory(LOOP5_CODE, holder))
        _e, _r, probe = build_runner(LOOP5_CODE)
        bp = line_of(probe, "total = total + i")

        client.send("initialize")
        client.send("launch")
        client.send("setBreakpoints", source={"path": FILE},
                    breakpoints=[{"line": bp, "logMessage": "i={i}"}])
        client.send("configurationDone")
        self.assertIsNotNone(client.wait_event("terminated"), "logpoint run never ended")
        # Filter out the adapter's own [mast] diagnostic lines; keep logpoint output.
        outputs = [m["body"]["output"].strip() for m in client.events("output")
                   if not m["body"]["output"].startswith("[mast]")]
        self.assertEqual(outputs, ["i=0", "i=1", "i=2", "i=3", "i=4"])

    def test_set_variable_request(self):
        holder = {}
        client = DapClient(self._factory(SETVAR_CODE, holder))
        _e, _r, probe = build_runner(SETVAR_CODE)
        bp = line_of(probe, "gate = 1")

        client.send("initialize")
        client.send("launch")
        client.send("setBreakpoints", source={"path": FILE}, breakpoints=[{"line": bp}])
        client.send("configurationDone")
        stopped = client.wait_event("stopped")
        self.assertIsNotNone(stopped)
        tid = stopped["body"]["threadId"]

        resp = client.send("scopes", frameId=0)
        task_ref = {s["name"]: s["variablesReference"] for s in resp["body"]["scopes"]}["Task"]
        resp = client.send("setVariable", variablesReference=task_ref, name="x", value="42")
        self.assertTrue(resp["success"], resp.get("message"))
        self.assertEqual(resp["body"]["value"], "42")

        client.send("continue", threadId=tid)
        self.assertIsNotNone(client.wait_event("terminated"))
        self.assertEqual(logged(holder["runner"]), "x is 42\n")


class TestZipSource(unittest.TestCase):
    """Serve source that lives inside a .sbslib / .mastlib zip."""

    def _make_zip(self, name, arcname, text):
        import tempfile, zipfile, os
        d = tempfile.mkdtemp()
        zpath = os.path.join(d, name)
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr(arcname, text)
        return os.path.join(zpath, arcname.replace("/", os.sep))  # a path INTO the zip

    def test_read_source_from_sbslib_and_mastlib(self):
        py_in_zip = self._make_zip("lib.sbslib", "sbs_utils/procedural/terrain.py",
                                   "def terrain_to_value(x):\n    return 42\n")
        self.assertTrue(_is_readable_source(py_in_zip))
        self.assertIn("return 42", _read_source(py_in_zip))

        mast_in_zip = self._make_zip("lib.mastlib", "maps/siege.mast", 'log("hi from lib")\n')
        self.assertIn("hi from lib", _read_source(mast_in_zip))

    def test_source_request_serves_zip_hosted_file(self):
        inside = self._make_zip("lib.sbslib", "pkg/mod.py", "X = 99\n")
        sent = []
        adapter = MastDapAdapter(sent.append)
        src = adapter._source_for(inside)
        self.assertIn("sourceReference", src, "zip path should get a sourceReference")
        adapter.handle({"type": "request", "seq": 1, "command": "source",
                        "arguments": {"sourceReference": src["sourceReference"], "source": src}})
        resp = [m for m in sent if m.get("command") == "source"][-1]
        self.assertTrue(resp["success"], resp.get("message"))
        self.assertIn("X = 99", resp["body"]["content"])

    def test_real_file_gets_path_not_reference(self):
        adapter = MastDapAdapter(lambda m: None)
        src = adapter._source_for(FIXTURE)          # a real .mast on disk
        self.assertEqual(src["path"], FIXTURE)
        self.assertNotIn("sourceReference", src)


class TestFileRunner(unittest.TestCase):
    """Launch-mode factory: compile a real .mast file and debug it."""
    def tearDown(self):
        from sbs_utils.mast.mastscheduler import MastTicker
        MastTicker.on_enter_node = None

    def test_build_file_runner_breakpoint(self):
        errors, runner, mast = build_file_runner(FIXTURE)
        self.assertEqual(errors, [])
        self.assertIsNotNone(runner)

        dbg = MastDebugCore().install(mast)
        try:
            filename = dbg.files()[0]                 # source name from the compile
            bp = line_of(mast, "x = 2")
            self.assertEqual(dbg.set_breakpoints(filename, [bp]), [bp])

            worker = run_scheduler_in_thread(runner, "main")
            self.assertTrue(dbg.wait_for_pause(), "breakpoint never hit")
            self.assertEqual(dbg.location()["line"], bp)
            self.assertEqual(dbg.variables("Task").get("x"), 1)
            dbg.resume()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
            self.assertEqual(runner.runtime_errors, [])
            self.assertEqual(logged(runner), "x is 2\ndone 10\n")
        finally:
            dbg.uninstall()

    def test_file_runner_factory_compile_error(self):
        factory = file_runner_factory()
        errors, runner, mast = factory({"program": FIXTURE})
        self.assertEqual(errors, [])
        self.assertIsNotNone(runner)
        # No path -> a clear error, no runner.
        errors, runner, _ = factory({})
        self.assertTrue(errors)
        self.assertIsNone(runner)


class TestStdioTransport(unittest.TestCase):
    """The Content-Length framing + serve loop the `sbs dap` command uses."""
    def tearDown(self):
        from sbs_utils.mast.mastscheduler import MastTicker
        MastTicker.on_enter_node = None

    def test_frame_roundtrip(self):
        buf = io.BytesIO()
        _write_message(buf, {"type": "event", "event": "hello", "seq": 1})
        buf.seek(0)
        msg = _read_message(buf)
        self.assertEqual(msg["event"], "hello")
        self.assertIsNone(_read_message(buf))   # clean EOF

    def _frame(self, obj):
        import json
        data = json.dumps(obj).encode("utf-8")
        return f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8") + data

    def test_run_stdio_initialize_disconnect(self):
        stdin = io.BytesIO(
            self._frame({"type": "request", "seq": 1, "command": "initialize",
                         "arguments": {"adapterID": "mast"}})
            + self._frame({"type": "request", "seq": 2, "command": "disconnect"})
        )
        stdout = io.BytesIO()
        run_stdio(file_runner_factory(FIXTURE), stdin=stdin, stdout=stdout)

        stdout.seek(0)
        messages = []
        while True:
            m = _read_message(stdout)
            if m is None:
                break
            messages.append(m)
        commands = [m.get("command") for m in messages if m.get("type") == "response"]
        self.assertIn("initialize", commands)
        init = next(m for m in messages if m.get("command") == "initialize")
        self.assertTrue(init["body"]["supportsConfigurationDoneRequest"])


if __name__ == "__main__":
    unittest.main()
