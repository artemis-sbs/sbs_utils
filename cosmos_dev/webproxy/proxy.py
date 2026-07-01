"""Host-side web-page proxy for the REAL Cosmos engine.

Serves MAST //web/<path> pages to browsers with NO engine changes, by bridging
the browser to a running engine over the dev queue:

    browser  <-- WS/HTTP -->  this proxy  <-- dev queue files -->  real engine

The proxy reuses the mockgui WS/HTTP server (client.html renderer + /web routing)
and shuttles:
    * browser web_connect / gui event / disconnect  -> engine web_open / web_event / web_close
    * engine-rendered wire frames (web_drain)        -> browser

Prerequisites (in the running engine's mission):
    * story.json loads cosmos_devqueue.mastlib and the cosmos_dev sbslib
    * the engine was launched with COSMOS_DEV_QUEUE=1 (and COSMOS_DEV_QUEUE_DIR
      pointing at the mission dir), so the dev-queue consumer is live
    * the mission defines one or more //web/<path> routes

Run (while the engine is running):
    python -m cosmos_dev.webproxy.proxy <mission_dir> [--host H] [--port P]

Then open  http://<host>:<port>/web/<path>  in a browser.

Only this process needs a live engine to exercise; the engine-side logic it
drives (cosmos_dev.webproxy.engine_side) is unit-tested against the mock.
"""
import argparse
import json
import multiprocessing
import os
import queue as _q
import threading
import time

_WP = "cosmos_dev.webproxy.engine_side"


class _QueueClient:
    """Minimal dev-queue client that ATTACHES to an already-running engine
    (EngineDriver assumes it launched the process; here the user started it)."""

    def __init__(self, queue_dir):
        self.in_path = os.path.join(queue_dir, "dev_queue.in.json")
        self.out_path = os.path.join(queue_dir, "dev_queue.out.json")
        self._seq = 0

    def eval(self, expr, timeout=3.0, poll=0.02):
        # Monotonic ms seq so a fresh proxy never reuses a seq the long-lived
        # engine consumer already processed (which it would dedupe and skip).
        self._seq = max(self._seq + 1, int(time.time() * 1000))
        seq = self._seq
        tmp = self.in_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"seq": seq, "code": expr, "mode": "eval"}, f)
        os.replace(tmp, self.in_path)   # atomic; engine never sees a half file

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with open(self.out_path) as f:
                    resp = json.load(f)
                if resp.get("seq") == seq:
                    if not resp.get("ok"):
                        raise RuntimeError(resp.get("error"))
                    return resp.get("result")
            except (OSError, ValueError):
                pass
            time.sleep(poll)
        raise TimeoutError(f"no dev-queue reply for seq {seq} within {timeout}s "
                           "(is the mission with cosmos_devqueue loaded?)")


def _call(fn, *args):
    """A self-contained eval expression: import engine_side and call fn(*args).
    Dev-queue commands get a fresh globals each time, so it must be one-shot."""
    arglist = ", ".join(repr(a) for a in args)
    return f"__import__('{_WP}', fromlist=['{fn}']).{fn}({arglist})"


_EVENT_FIELDS = ("tag", "sub_tag", "value_tag", "sub_float", "extra_tag")

# True in-engine once push is armed. Resets to falsy when the engine process
# restarts (fresh Python -> engine_side._frames_path is None again), which is how
# the proxy detects a restart and re-arms.
_IS_ARMED_EXPR = ("bool(__import__('cosmos_dev.webproxy.engine_side', "
                  "fromlist=['x'])._frames_path)")


def _ensure_armed(client, frames_path, was_armed, label="default"):
    """Make sure push mode is armed in the (possibly just-started) engine.
    Returns the current armed state; never raises (engine may be down)."""
    try:
        is_armed = client.eval(_IS_ARMED_EXPR, timeout=3.0)
    except Exception:
        return False   # engine unreachable; re-arm when it returns
    if is_armed:
        if not was_armed:
            print(f"[webproxy] engine '{label}' up - push armed")
        return True
    try:
        client.eval(_call("set_frames_file", frames_path), timeout=3.0)
        print(f"[webproxy] engine '{label}' up - push armed")
        return True
    except Exception:
        return False


def _tail_frames(path, gui_q, stop, poll=0.02):
    """Tail the engine's NDJSON frames file and forward each wire command to the
    browser (via gui_q). Pure push: no dev-queue round-trip, so no polling stall.
    Handles truncation (new stream) and a partially-written trailing line."""
    offset = 0
    buf = ""
    while not stop.is_set():
        try:
            size = os.path.getsize(path)
        except OSError:
            time.sleep(poll)
            continue
        if size < offset:          # file was truncated -> fresh stream
            offset, buf = 0, ""
        if size > offset:
            try:
                with open(path, "r") as f:
                    f.seek(offset)
                    buf += f.read()
                    offset = f.tell()
            except OSError:
                time.sleep(poll)
                continue
            lines = buf.split("\n")
            buf = lines[-1]        # keep the incomplete trailing line
            for line in lines[:-1]:
                line = line.strip()
                if not line:
                    continue
                try:
                    gui_q.put(json.loads(line))
                except ValueError:
                    pass
        time.sleep(poll)


class _Engine:
    """Per-engine bridge state: its dev-queue client, frames file, arm status."""
    def __init__(self, name, queue_dir):
        self.name = name or ""
        self.queue_dir = queue_dir
        self.client = _QueueClient(queue_dir)
        self.frames_path = os.path.join(queue_dir, "web_frames.ndjson")
        self.armed = False
        self.last_arm = 0.0

    def disp(self, path):
        return f"/web/{self.name}/{path}" if self.name else f"/web/{path}"


def _resolve_engine(path, by_name, default):
    """Map a web path to (engine, page_path). If the first segment names a known
    engine (/web/<engine>/<page>), route there and strip it; otherwise the whole
    path is the page on the default engine (/web/<page>)."""
    seg, _, rest = path.partition("/")
    e = by_name.get(seg)
    if e is not None:
        return e, rest
    return default, path


def run(engines, host="127.0.0.1", port=8770, cosmos_dir=None, rate=0.04):
    """Serve MAST //web pages from one or more engines behind a single web
    server. `engines` is a list of (name, queue_dir); a browser routes by URL:
    /web/<name>/<page> picks a named engine, /web/<page> uses the default
    (a nameless engine, or the only one)."""
    from cosmos_dev.mockgui import server as server_mod

    eng_list = [_Engine(name, qd) for name, qd in engines]
    by_name = {e.name: e for e in eng_list if e.name}
    named = [e for e in eng_list if not e.name]
    default = named[0] if named else (eng_list[0] if len(eng_list) == 1 else None)

    gui_q = multiprocessing.Queue()
    client_q = multiprocessing.Queue()
    event_q = multiprocessing.Queue()
    ready = multiprocessing.Event()
    proc = multiprocessing.Process(
        target=server_mod.run_server,
        args=(gui_q, client_q, event_q, ready, host, port, cosmos_dir),
        daemon=True, name="webproxy-server")
    proc.start()
    if not ready.wait(timeout=10):
        proc.terminate()
        raise RuntimeError(f"web server did not start on {host}:{port}")

    # One frames tail per engine, all feeding the shared gui_q. Frames are tagged
    # with the browser's (proxy-assigned, unique) client id, so the server routes
    # each frame to the right browser regardless of which engine produced it.
    stop = threading.Event()
    for e in eng_list:
        threading.Thread(target=_tail_frames, args=(e.frames_path, gui_q, stop),
                         daemon=True, name=f"webproxy-tail-{e.name or 'default'}").start()

    # cid -> {"engine": _Engine|None, "path": page, "query": dict, "opened": bool}
    sessions = {}

    print(f"[webproxy] serving http://{host}:{port}/web/<path>")
    for e in eng_list:
        tag = f"'{e.name}'" if e.name else "default (/web/<page>)"
        print(f"[webproxy]   engine {tag} -> {e.queue_dir}")
    print("[webproxy] waiting for engine(s) (start/stop missions freely)...")
    try:
        while True:
            # --- browser events: track sessions, forward widget events -----
            while True:
                try:
                    cev = client_q.get_nowait()
                except _q.Empty:
                    break
                ev, cid = cev.get("event"), cev.get("clientID")
                if ev == "web_connect":
                    e, page = _resolve_engine(cev.get("path", ""), by_name, default)
                    sessions[cid] = {"engine": e, "path": page,
                                     "query": cev.get("query", {}), "opened": False}
                    if e is None:
                        print(f"[webproxy] no engine for /web/{cev.get('path')}")
                elif ev == "web_disconnect":
                    s = sessions.pop(cid, None)
                    if s and s["engine"] is not None:
                        try:
                            s["engine"].client.eval(_call("web_close", cid))
                        except Exception:
                            pass

            while True:
                try:
                    gev = event_q.get_nowait()
                except _q.Empty:
                    break
                cid = gev.get("clientID")
                s = sessions.get(cid)
                if s is None or s["engine"] is None:
                    continue
                payload = {k: gev[k] for k in _EVENT_FIELDS if k in gev}
                try:
                    s["engine"].client.eval(_call("web_event", cid, payload))
                except Exception:
                    pass   # engine not ready; widget events are transient

            # --- (re)arm each engine as it appears / restarts --------------
            now = time.time()
            for e in eng_list:
                if now - e.last_arm <= 1.0:
                    continue
                e.last_arm = now
                prev = e.armed
                e.armed = _ensure_armed(e.client, e.frames_path, prev,
                                        label=e.name or "default")
                if e.armed and not prev:
                    for s in sessions.values():   # re-open this engine's sessions
                        if s["engine"] is e:
                            s["opened"] = False

            # --- (re)open any sessions not yet live on their engine --------
            for cid, s in sessions.items():
                e = s["engine"]
                if e is None or s["opened"] or not e.armed:
                    continue
                try:
                    ok = e.client.eval(_call("web_open", cid, s["path"], s["query"]))
                    if ok:
                        s["opened"] = True
                        print(f"[webproxy] web_open {cid} {e.disp(s['path'])} -> True")
                except Exception:
                    e.armed = False   # engine went away mid-open; re-arm later

            time.sleep(rate)
    except KeyboardInterrupt:
        print("\n[webproxy] shutting down")
    finally:
        stop.set()
        proc.terminate()


def main():
    ap = argparse.ArgumentParser(
        description="Serve MAST //web pages from one or more running engines.")
    ap.add_argument("mission_dir", nargs="?", default=None,
                    help="Default engine's mission dir (served at /web/<page>)")
    ap.add_argument("--engine", action="append", default=[], metavar="NAME=DIR",
                    help="Named engine (repeatable); served at /web/NAME/<page>")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--cosmos-dir", default=None,
                    help="Cosmos install root (for serving /data/graphics images)")
    a = ap.parse_args()

    engines = []
    if a.mission_dir:
        engines.append(("", os.path.abspath(a.mission_dir)))
    for spec in a.engine:
        name, sep, d = spec.partition("=")
        if not sep or not name or not d:
            ap.error(f"--engine must be NAME=DIR, got: {spec!r}")
        engines.append((name, os.path.abspath(d)))
    if not engines:
        ap.error("give a mission_dir and/or at least one --engine NAME=DIR")
    run(engines, a.host, a.port, a.cosmos_dir)


if __name__ == "__main__":
    main()
