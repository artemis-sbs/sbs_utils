"""Drive the real Artemis Cosmos engine from the host (dev-only).

Runs outside the engine, so threads / queues / pip are all allowed here. It:

  * builds cosmos_devqueue.mastlib from cosmos_dev/devqueue/ into <missions>/__lib__
  * launches Artemis3-x64-release.exe with COSMOS_DEV_QUEUE set
  * sends Python to the live engine and reads the result (via the file queue)
  * tails mast.runtime.log / a probe log
  * screenshots the desktop (PIL; no extra pip needed)

Control happens through the queue (e.g. task_schedule_server a map), so no mouse
choreography is needed except whatever the engine requires to load the opted-in
mission. Screenshots are only for visual confirmation of the rendered frame.

Typical use:

    from cosmos_dev.engine_driver import EngineDriver
    drv = EngineDriver(cosmos_dir=r"f:/a/Cosmos-1-3-0",
                       mission="quick_example")
    drv.build_mastlib()          # refresh the .mastlib in __lib__
    drv.launch()                 # start the engine with the queue enabled
    print(drv.eval("1+1"))       # -> 2, proving the round-trip
    drv.screenshot("frame.png")
    drv.close()
"""
import os
import json
import time
import shutil
import zipfile
import subprocess


def _repo_devqueue_dir():
    # cosmos_dev/engine_driver/driver.py -> cosmos_dev/devqueue
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "devqueue"))


# Files that make up the mastlib (flat at the zip root, like LM mastlibs).
_MASTLIB_FILES = ("__init__.mast", "queue.mast", "dev_queue.py")
MASTLIB_NAME = "cosmos_devqueue.mastlib"


def build_mastlib(missions_dir, src_dir=None, name=MASTLIB_NAME):
    """Zip cosmos_dev/devqueue/ into <missions_dir>/__lib__/<name> (flat root)."""
    src_dir = src_dir or _repo_devqueue_dir()
    lib_dir = os.path.join(missions_dir, "__lib__")
    os.makedirs(lib_dir, exist_ok=True)
    out = os.path.join(lib_dir, name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in _MASTLIB_FILES:
            p = os.path.join(src_dir, fn)
            if not os.path.isfile(p):
                raise FileNotFoundError(p)
            z.write(p, fn)
    return out


class EngineDriver:
    def __init__(self, cosmos_dir, mission, release=True, missions_dir=None):
        self.cosmos_dir = os.path.abspath(cosmos_dir)
        self.missions_dir = missions_dir or os.path.join(self.cosmos_dir, "data", "missions")
        self.mission = mission
        self.mission_dir = os.path.join(self.missions_dir, mission)
        exe = "Artemis3-x64-release.exe" if release else "Artemis3-x64-debug.exe"
        self.exe = os.path.join(self.cosmos_dir, exe)
        # Both sides agree on this dir for the command/reply files.
        self.queue_dir = self.mission_dir
        self.in_path = os.path.join(self.queue_dir, "dev_queue.in.json")
        self.out_path = os.path.join(self.queue_dir, "dev_queue.out.json")
        self.proc = None
        self._seq = 0

    # --- packaging -----------------------------------------------------------
    def build_mastlib(self):
        return build_mastlib(self.missions_dir)

    def enable_in_story(self):
        """Add cosmos_devqueue.mastlib to the mission's story.json (idempotent)."""
        sj = os.path.join(self.mission_dir, "story.json")
        with open(sj) as f:
            data = json.load(f)
        libs = data.setdefault("mastlib", [])
        if MASTLIB_NAME not in libs:
            libs.append(MASTLIB_NAME)
            with open(sj, "w") as f:
                json.dump(data, f, indent=4)
        return sj

    # --- lifecycle -----------------------------------------------------------
    @staticmethod
    def stop_engines():
        """Kill any running engine. The server port (serverNetworkPort in
        preferences.json, default 2023) is fixed, so a second instance collides
        with the first - always stop before launching."""
        for exe in ("Artemis3-x64-release.exe", "Artemis3-x64-debug.exe"):
            subprocess.run(["taskkill", "/f", "/im", exe],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)   # let the OS release the port

    def launch(self, extra_env=None):
        # The fixed server port means stacked instances conflict - stop first.
        self.stop_engines()
        for p in (self.in_path, self.out_path):
            try:
                os.remove(p)
            except OSError:
                pass
        env = dict(os.environ)
        env["COSMOS_DEV_QUEUE"] = "1"
        env["COSMOS_DEV_QUEUE_DIR"] = self.queue_dir
        if extra_env:
            env.update(extra_env)
        self.proc = subprocess.Popen([self.exe], cwd=self.cosmos_dir, env=env)
        return self.proc

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def close(self):
        if self.is_running():
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    # --- command queue -------------------------------------------------------
    def send(self, code, mode="exec", timeout=15.0, poll=0.05):
        """Send code to the engine and wait for its reply. Set `_result` in the
        code (exec mode) or use mode="eval" to return a value."""
        # Monotonic, process-independent seq: a fresh driver must not reuse a seq
        # the long-lived engine consumer already processed, or the command would
        # be deduped and never run. Time-based ms keeps it increasing across runs.
        self._seq = max(self._seq + 1, int(time.time() * 1000))
        seq = self._seq
        tmp = self.in_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"seq": seq, "code": code, "mode": mode}, f)
        os.replace(tmp, self.in_path)   # atomic so the engine never sees half a file

        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.is_running():
                raise RuntimeError("engine process exited before replying")
            try:
                with open(self.out_path) as f:
                    resp = json.load(f)
                if resp.get("seq") == seq:
                    return resp
            except (OSError, ValueError):
                pass
            time.sleep(poll)
        raise TimeoutError(f"no reply for seq {seq} within {timeout}s "
                           "(is the mission with cosmos_devqueue loaded yet?)")

    def eval(self, expr, **kw):
        """Convenience: evaluate an expression, return its value (or raise)."""
        resp = self.send(expr, mode="eval", **kw)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error"))
        return resp.get("result")

    def ping(self, timeout=60.0):
        """Block until the consumer answers (mission + mastlib are live)."""
        return self.eval("1+1", timeout=timeout) == 2

    # --- observation ---------------------------------------------------------
    def screenshot(self, path):
        """Full virtual-screen capture via PIL (already installed; no pip)."""
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        img.save(path)
        return path

    def read_log(self, name="mast.runtime.log", tail=4000):
        p = os.path.join(self.missions_dir, name)
        try:
            with open(p, "r", errors="replace") as f:
                return f.read()[-tail:]
        except OSError:
            return ""
