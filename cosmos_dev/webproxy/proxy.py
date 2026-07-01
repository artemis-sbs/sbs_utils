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


def _ensure_armed(client, frames_path, was_armed):
    """Make sure push mode is armed in the (possibly just-started) engine.
    Returns the current armed state; never raises (engine may be down)."""
    try:
        is_armed = client.eval(_IS_ARMED_EXPR, timeout=3.0)
    except Exception:
        return False   # engine unreachable; re-arm when it returns
    if is_armed:
        if not was_armed:
            print("[webproxy] engine up - push armed")
        return True
    try:
        client.eval(_call("set_frames_file", frames_path), timeout=3.0)
        print("[webproxy] engine up - push armed")
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


def run(queue_dir, host="127.0.0.1", port=8770, cosmos_dir=None, rate=0.04):
    from cosmos_dev.mockgui import server as server_mod

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

    client = _QueueClient(queue_dir)
    frames_path = os.path.join(queue_dir, "web_frames.ndjson")

    stop = threading.Event()
    tail = threading.Thread(target=_tail_frames, args=(frames_path, gui_q, stop),
                            daemon=True, name="webproxy-tail")
    tail.start()

    # Always-on: the engine may not be running yet, may restart, or missions may
    # come and go. All dev-queue calls happen here in the main thread (the tail
    # thread only reads the file), so no locking is needed. We (re)arm push
    # whenever the engine appears, and re-open live sessions after a restart.
    sessions = {}     # cid -> {"path", "query", "opened"}
    armed = False
    last_arm = 0.0

    print(f"[webproxy] serving http://{host}:{port}/web/<path>")
    print(f"[webproxy] bridging to engine dev queue at {queue_dir}")
    print("[webproxy] waiting for engine (start/stop missions freely)...")
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
                    sessions[cid] = {"path": cev.get("path", ""),
                                     "query": cev.get("query", {}), "opened": False}
                elif ev == "web_disconnect":
                    sessions.pop(cid, None)
                    try:
                        client.eval(_call("web_close", cid))
                    except Exception:
                        pass

            while True:
                try:
                    gev = event_q.get_nowait()
                except _q.Empty:
                    break
                cid = gev.get("clientID")
                payload = {k: gev[k] for k in _EVENT_FIELDS if k in gev}
                try:
                    client.eval(_call("web_event", cid, payload))
                except Exception:
                    pass   # engine not ready; widget events are transient

            # --- (re)arm push when the engine appears / restarts -----------
            now = time.time()
            if now - last_arm > 1.0:
                last_arm = now
                prev = armed
                armed = _ensure_armed(client, frames_path, prev)
                if armed and not prev:
                    # engine (re)appeared: re-open every known live session
                    for s in sessions.values():
                        s["opened"] = False

            # --- (re)open any sessions not yet live in the engine ----------
            if armed:
                for cid, s in sessions.items():
                    if s["opened"]:
                        continue
                    try:
                        ok = client.eval(_call("web_open", cid, s["path"], s["query"]))
                        if ok:
                            s["opened"] = True
                            print(f"[webproxy] web_open {cid} /web/{s['path']} -> True")
                    except Exception:
                        armed = False   # engine went away mid-open; re-arm later
                        break

            time.sleep(rate)
    except KeyboardInterrupt:
        print("\n[webproxy] shutting down")
    finally:
        stop.set()
        proc.terminate()


def main():
    ap = argparse.ArgumentParser(description="Serve MAST //web pages from a running engine.")
    ap.add_argument("mission_dir", help="Mission dir holding the dev_queue files")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--cosmos-dir", default=None,
                    help="Cosmos install root (for serving /data/graphics images)")
    a = ap.parse_args()
    run(os.path.abspath(a.mission_dir), a.host, a.port, a.cosmos_dir)


if __name__ == "__main__":
    main()
