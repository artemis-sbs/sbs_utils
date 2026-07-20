"""
cosmos_dev/mission_runner.py — run a MAST mission outside Cosmos for debugging.

Per-mission wrapper (extern_debug.py):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../sbs_utils"))
    from cosmos_dev.mission_runner import run_mission
    run_mission(__file__, mast_file="extern_debug.mast")

CLI (run from inside missions/sbs_utils/ or pass the full path):
    python -m cosmos_dev.mission_runner ../LegendaryMissions
    python -m cosmos_dev.mission_runner ../LegendaryMissions --map 1 --gui
    python -m cosmos_dev.mission_runner ../LegendaryMissions --map "Secret Meeting"
    python -m cosmos_dev.mission_runner ../SecretMeeting --mast debug.mast --gui --port 9000
"""

import json
import os
import queue as _queue_mod
import sys
import threading
import time

# sbs_utils project root: cosmos_dev/mission_runner.py → cosmos_dev/ → project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_missions_root(start: str) -> str:
    """Walk up from start until we find a directory that contains __lib__/."""
    path = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(path, "__lib__")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            raise RuntimeError(
                f"Cannot find missions root — no __lib__/ directory found above {start!r}"
            )
        path = parent


def _load_libs(mission_folder: str, missions_root: str) -> None:
    """Parse story.json and add every listed sbslib and mastlib to sys.path."""
    story_json = os.path.join(mission_folder, "story.json")
    if not os.path.isfile(story_json):
        print(f"[runner] warning: no story.json in {mission_folder!r}")
        return
    with open(story_json) as f:
        story = json.load(f)
    lib_dir = os.path.join(missions_root, "__lib__")
    for kind in ("sbslib", "mastlib"):
        for name in story.get(kind, []):
            lib_path = os.path.join(lib_dir, name)
            if os.path.exists(lib_path):
                if lib_path not in sys.path:
                    sys.path.insert(0, lib_path)
                    print(f"[runner] {kind}: {name}")
            else:
                print(f"[runner] warning: {kind} not found — {lib_path!r}")


def _try_auto_start_map(map_arg, sbs) -> bool:
    """Try to schedule the target map. Returns True once done, False if maps not ready yet.

    Polls ``maps_get_list()`` each tick until real map labels are registered, then
    schedules the requested map and emits ``game_started``.  Replaces the
    ``await delay_app`` / ``task_schedule`` / ``sim_resume`` sequence that lived
    in the old ``extern_debug.mast``.
    """
    from sbs_utils.procedural.maps import maps_get_list
    from sbs_utils.procedural.execution import task_schedule_server, set_shared_variable
    from sbs_utils.procedural.signal import signal_emit

    mission_list = maps_get_list()
    # maps_get_list returns plain dicts (not Label objects) as a placeholder when
    # no real @map/ labels have been registered yet.
    real_maps = [m for m in mission_list if hasattr(m, "path")]
    if not real_maps:
        return False  # story still initialising — try again next tick

    if isinstance(map_arg, int):
        idx = max(0, min(map_arg, len(real_maps) - 1))
    else:
        idx = next(
            (i for i, m in enumerate(real_maps) if getattr(m, "path", None) == map_arg),
            0,
        )

    map_label = real_maps[idx]
    print(f"[runner] auto-starting map: {getattr(map_label, 'path', map_arg)}")

    task_schedule_server(map_label, defer=True)
    set_shared_variable("GAME_STARTED", True)
    signal_emit("game_started", {})
    sbs.resume_sim()
    return True


class _TeeWriter:
    """Write to the original stream AND forward lines to the browser log panel."""
    def __init__(self, original, level, queue):
        self._original = original
        self._level    = level
        self._queue    = queue
        self._buf      = ""

    def write(self, text):
        self._original.write(text)
        self._buf += text
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            if line.strip():
                try:
                    self._queue.put_nowait({"cmd": "log", "text": line, "level": self._level})
                except Exception:
                    pass

    def flush(self):
        self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


def _drain_physics_events(sim, cosmos_event_handler, FakeEvent) -> None:
    """Drain collision events queued by the physics background thread.

    Each entry in _pending_physics_events is (tag, sub_tag, origin_id, selected_id).
    Uses queue.Queue.get_nowait() for thread-safe non-blocking reads.
    """
    import cosmos_dev.mock.sbs as _mock
    while True:
        try:
            tag, sub_tag, origin_id, selected_id = _mock._pending_physics_events.get_nowait()
        except _queue_mod.Empty:
            break
        ev = FakeEvent(client_id=0, tag=tag, sub_tag=sub_tag,
                       origin_id=origin_id, selected_id=selected_id)
        try:
            cosmos_event_handler(sim, ev)
        except Exception as e:
            print(f"[runner] physics event error ({tag}/{sub_tag}): {e}")


def _drain_client_strings(sim, cosmos_event_handler, FakeEvent) -> None:
    """Fire pending client_string response events queued by request_client_string().

    The mock's request_client_string() appends (client_id, key) to
    cosmos_dev.mock.sbs._pending_client_string_events.  We import the base mock
    directly (not the mockgui wrapper) because underscore names aren't exported by
    the wildcard import in mockgui/sbs.py.  We loop here because resolving one
    ClientStringPromise may advance the MAST task to another await, immediately
    queuing the next request.
    """
    import cosmos_dev.mock.sbs as _mock
    while _mock._pending_client_string_events:
        cid, key = _mock._pending_client_string_events.pop(0)
        value = _mock._client_strings.get(cid, {}).get(key, "")
        cs_ev = FakeEvent(client_id=cid, tag="client_string", sub_tag=key, value_tag=value)
        try:
            cosmos_event_handler(sim, cs_ev)
        except Exception as e:
            print(f"[runner] client_string drain error ({key}): {e}")


def _run(
    mission_folder: str,
    mast_file: str | None = None,
    map_arg: int | str | None = None,
    gui: bool = False,
    port: int = 8765,
    tick_rate: int = 60,
    cosmos_dir: str | None = None,
) -> None:
    mission_folder = os.path.abspath(mission_folder)
    missions_root  = _find_missions_root(mission_folder)

    # Source project takes precedence over any packaged sbslib on the path
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

    _load_libs(mission_folder, missions_root)

    # Communicate map choice to the debug .mast via environment variable
    os.environ["COSMOS_DEBUG_MAP"] = str(map_arg)

    _server_proc = None
    _orig_stdout = _orig_stderr = None
    if gui:
        import cosmos_dev.mockgui.sbs as sbs
        _cosmos_dir = cosmos_dir or os.path.dirname(os.path.dirname(missions_root))
        _server_proc = sbs.start_server(port=port, cosmos_dir=_cosmos_dir)
        print(f"[runner] GUI server started — open http://localhost:{port}/")
        _orig_stdout, _orig_stderr = sys.stdout, sys.stderr
        sys.stdout = _TeeWriter(sys.__stdout__, "info",  sbs.gui_queue)
        sys.stderr = _TeeWriter(sys.__stderr__, "error", sbs.gui_queue)
    else:
        import cosmos_dev.mock.sbs as sbs

    # Make this process look like script.py (handlerhooks expects it)
    sys.modules["script"] = sys.modules.get("__main__")

    # Point sbs_utils.fs at the Cosmos install root
    # missions_root = .../data/missions  →  exe_dir = .../Cosmos-x.x.x
    from sbs_utils import fs
    fs.exe_dir = os.path.dirname(os.path.dirname(missions_root))

    # Import order matters: core nodes before Cosmos extensions
    from sbs_utils.mast import core_nodes               # noqa: F401 — side-effect: registers node types
    from sbs_utils.mast_sbs import story_nodes          # noqa: F401 — side-effect: registers Cosmos nodes
    from sbs_utils.mast_sbs import mast_sbs_procedural  # noqa: F401 — side-effect: wires procedural API
    from sbs_utils.mast_sbs.maststorypage import StoryPage
    from sbs_utils.helpers import FrameContext, Context, FakeEvent
    from sbs_utils.vec import Vec3
    from sbs_utils.agent import Agent
    from sbs_utils.handlerhooks import cosmos_event_handler
    from sbs_utils.gui import Gui

    sim = sbs.create_new_sim()
    Agent.SHARED.set_inventory_value("sim", sim)
    FrameContext.context = Context(sim, sbs, FakeEvent())

    story_path = os.path.join(mission_folder, mast_file or "story.mast")
    if not os.path.isfile(story_path):
        raise FileNotFoundError(f"Story file not found: {story_path!r}")
    print(f"[runner] story: {story_path}")

    class _MissionPage(StoryPage):
        story_file = story_path

    Gui.server_start_page_class(_MissionPage)
    Gui.client_start_page_class(_MissionPage)

    tick_sleep = 1.0 / tick_rate
    _mast_interval = max(1, round(tick_rate / 5))   # MAST at 5 Hz
    _mast_counter  = 0
    _map_started   = map_arg is None  # skip auto-start when no map was requested

    # Physics runs in a background daemon thread at 2 Hz, decoupled from MAST.
    # The main loop drains physics events each iteration via queue.Queue.get_nowait().
    _stop_physics = threading.Event()

    def _physics_worker(sbs_mod, stop_ev):
        while not stop_ev.is_set():
            if sbs_mod.sim is not None and not sbs_mod.sim._paused:
                try:
                    sbs_mod.physics_tick(dt=0.5)
                except Exception as e:
                    print(f"[runner] physics worker error: {e}")
            stop_ev.wait(timeout=0.5)   # 2 Hz; exits promptly on stop signal

    _physics_thread = threading.Thread(
        target=_physics_worker,
        args=(sbs, _stop_physics),
        daemon=True,
        name="sbs-physics",
    )
    _physics_thread.start()
    print(f"[runner] running at {tick_rate} Hz  (MAST 5 Hz, physics 2 Hz background thread)")

    # Guard: clients that connect before the server's first MAST tick would run their
    # client_connect handler against uninitialised game state.  Buffer those connections
    # and show a placeholder, then replay them once the server tick completes.
    _server_initialized = False
    _pending_client_connects: list = []   # client IDs waiting for server init

    def _show_waiting_screen(cid: int) -> None:
        if not gui or not hasattr(sbs, "send_gui_clear"):
            return
        try:
            sbs.send_gui_clear(cid, "")
            sbs.send_gui_text(cid, "", "wait_msg",
                              "$text:Server initializing – please wait…;"
                              "color:#00e5ff;font:gui-3;",
                              5, 40, 95, 60)
            sbs.send_gui_complete(cid, "")
        except Exception:
            pass

    def _fire_client_connect(cid: int) -> None:
        sbs.register_client(cid)
        cosmos_event_handler(sbs.sim, FakeEvent(client_id=cid, tag="client_connect"))
        _drain_client_strings(sbs.sim, cosmos_event_handler, FakeEvent)
        if hasattr(sbs, "_force_terrain_push"):
            sbs._force_terrain_push()

    try:
        while True:
            sim_state = "sim_paused" if sbs.sim._paused else "sim_running"
            tick_event = FakeEvent(client_id=0, tag="mission_tick", sub_tag=sim_state)

            # Determine whether this loop iteration fires a MAST tick (5 Hz).
            _mast_counter += 1
            run_mast = _mast_counter >= _mast_interval
            if run_mast:
                _mast_counter = 0

            if gui:
                # GUI widget events (button clicks etc.) — always drain every loop
                # iteration so button presses feel immediate regardless of MAST rate.
                while not sbs.gui_event_queue.empty():
                    try:
                        gev    = sbs.gui_event_queue.get_nowait()
                        cid    = gev.get("clientID", 0)
                        etype  = gev.get("type", "")
                        if etype == "screen_size":
                            gev_ev = FakeEvent(client_id=cid, tag="screen_size")
                            gev_ev.source_point = Vec3(gev.get("width", 1024),
                                                       gev.get("height", 768), 0)
                        else:
                            gev_ev = FakeEvent(client_id=cid, tag="gui_message",
                                               sub_tag=gev.get("tag", ""))
                            val = gev.get("value", gev.get("checked", ""))
                            if etype in ("change", "submit") and isinstance(val, (int, float)):
                                gev_ev.sub_float = float(val)
                            elif etype in ("change", "submit") and val != "":
                                gev_ev.value_tag = str(val)
                        cosmos_event_handler(sbs.sim, gev_ev)
                    except Exception as e:
                        print(f"[runner] gui event error: {e}")

            if run_mast:
                # Server MAST tick at 5 Hz.
                # Use sbs.sim (not the captured sim) so that sim_create() in a script
                # replaces the active simulation without breaking the tick loop.
                cosmos_event_handler(sbs.sim, tick_event)
                sbs.sim._time_tick_counter += 1
                # Drain any client_string responses queued during this tick.
                _drain_client_strings(sbs.sim, cosmos_event_handler, FakeEvent)

                if not _server_initialized:
                    _server_initialized = True
                    if _pending_client_connects:
                        print(f"[runner] server ready — replaying {len(_pending_client_connects)} "
                              f"deferred client connect(s)")
                    for cid in _pending_client_connects:
                        print(f"[runner] deferred client_connect: {cid}")
                        _fire_client_connect(cid)
                    _pending_client_connects.clear()

            # Drain physics events queued by the background physics thread.
            _drain_physics_events(sbs.sim, cosmos_event_handler, FakeEvent)

            if gui:
                # Client connect/disconnect — always check every loop iteration so
                # connections are registered promptly regardless of MAST rate.
                while not sbs.client_event_queue.empty():
                    try:
                        cev = sbs.client_event_queue.get_nowait()
                        if cev.get("event") == "connect":
                            cid = cev["clientID"]
                            if not _server_initialized:
                                print(f"[runner] client {cid} connected early "
                                      f"— deferring until server init")
                                _pending_client_connects.append(cid)
                                _show_waiting_screen(cid)
                            else:
                                print(f"[runner] client {cid} connected")
                                _fire_client_connect(cid)
                        elif cev.get("event") == "disconnect":
                            cid = cev.get("clientID")
                            print(f"[runner] client {cid} disconnected")
                            _pending_client_connects[:] = [
                                c for c in _pending_client_connects if c != cid
                            ]
                            sbs.unregister_client(cid)
                    except Exception as e:
                        print(f"[runner] client event error: {e}")

            # Auto-start: poll each tick until @map/ labels are registered,
            # then schedule the requested map (replaces extern_debug.mast logic)
            if not _map_started:
                _map_started = _try_auto_start_map(map_arg, sbs)

            time.sleep(tick_sleep)
    except KeyboardInterrupt:
        print("\n[runner] stopped")
    finally:
        _stop_physics.set()
        _physics_thread.join(timeout=1.0)
        if _orig_stdout is not None:
            sys.stdout = _orig_stdout
        if _orig_stderr is not None:
            sys.stderr = _orig_stderr
        if _server_proc is not None and _server_proc.is_alive():
            _server_proc.terminate()


def run_mission(
    caller_file: str,
    mast_file: str | None = None,
    map_arg: int | str | None = None,
    gui: bool = False,
    port: int = 8765,
    tick_rate: int = 60,
    cosmos_dir: str | None = None,
) -> None:
    """Entry point for per-mission extern_debug.py wrappers."""
    _run(
        mission_folder=os.path.dirname(os.path.abspath(caller_file)),
        mast_file=mast_file,
        map_arg=map_arg,
        gui=gui,
        port=port,
        tick_rate=tick_rate,
        cosmos_dir=cosmos_dir,
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Run a MAST mission outside Cosmos for debugging.",
        epilog=(
            "examples:\n"
            "  python -m cosmos_dev.mission_runner ../LegendaryMissions\n"
            "  python -m cosmos_dev.mission_runner ../LegendaryMissions --map 1 --gui\n"
            "  python -m cosmos_dev.mission_runner ../LegendaryMissions --map 'Secret Meeting'\n"
            "  python -m cosmos_dev.mission_runner ../SecretMeeting --gui --port 9000\n"
            "  python -m cosmos_dev.mission_runner ../MyLib --mast debug.mast\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("mission",
                    help="Path to the mission folder")
    ap.add_argument("--map", default=None,
                    help="Map index (int) or map name to auto-start  [default: show GUI picker]")
    ap.add_argument("--mast", default=None,
                    help="Debug .mast file inside mission folder  [default: story.mast]")
    ap.add_argument("--gui", action="store_true",
                    help="Start the cosmos_dev WebSocket GUI server")
    ap.add_argument("--port", type=int, default=8765,
                    help="WebSocket server port  [default: 8765]")
    ap.add_argument("--tick-rate", type=int, default=60,
                    help="Ticks per second  [default: 60]")
    ap.add_argument("--cosmos-dir", default=None,
                    help="Cosmos install root for image serving  [default: auto-detected]")
    args = ap.parse_args()

    if args.map is None:
        map_val: int | str | None = None
    else:
        try:
            map_val = int(args.map)
        except ValueError:
            map_val = args.map

    _run(
        mission_folder=args.mission,
        mast_file=args.mast,
        map_arg=map_val,
        gui=args.gui,
        port=args.port,
        tick_rate=args.tick_rate,
        cosmos_dir=args.cosmos_dir,
    )
