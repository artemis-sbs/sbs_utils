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
    print(f"[webproxy] serving http://{host}:{port}/web/<path>")
    print(f"[webproxy] bridging to engine dev queue at {queue_dir}")
    try:
        while True:
            # --- browser -> engine -------------------------------------
            while True:
                try:
                    cev = client_q.get_nowait()
                except _q.Empty:
                    break
                ev, cid = cev.get("event"), cev.get("clientID")
                try:
                    if ev == "web_connect":
                        ok = client.eval(_call("web_open", cid,
                                               cev.get("path", ""),
                                               cev.get("query", {})))
                        print(f"[webproxy] web_open {cid} /web/{cev.get('path')} -> {ok}")
                    elif ev == "web_disconnect":
                        client.eval(_call("web_close", cid))
                except Exception as e:
                    print(f"[webproxy] client-event error: {e}")

            while True:
                try:
                    gev = event_q.get_nowait()
                except _q.Empty:
                    break
                cid = gev.get("clientID")
                payload = {k: gev[k] for k in _EVENT_FIELDS if k in gev}
                try:
                    client.eval(_call("web_event", cid, payload))
                except Exception as e:
                    print(f"[webproxy] gui-event error: {e}")

            # --- engine -> browser -------------------------------------
            try:
                frames = client.eval(_call("web_drain")) or []
            except Exception as e:
                print(f"[webproxy] drain error: {e}")
                frames = []
            for fr in frames:
                gui_q.put(fr)

            time.sleep(rate)
    except KeyboardInterrupt:
        print("\n[webproxy] shutting down")
    finally:
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
