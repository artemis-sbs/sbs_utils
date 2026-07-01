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
import traceback

# sbs_utils project root: cosmos_dev/mission_runner.py → cosmos_dev/ → project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _log_exc(prefix: str) -> None:
    """Print a one-line prefix followed by the FULL traceback of the exception being
    handled. The runner's except blocks used to print only str(e), which hid the
    stack - making mission-end / reload crashes impossible to diagnose. Always call
    this from inside an `except` so the crash is visible on the console."""
    print(f"[runner] {prefix}")
    traceback.print_exc()


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


def _load_libs(mission_folder: str, missions_root: str,
               use_working_tree: bool = False) -> None:
    """Parse story.json and add every listed sbslib and mastlib to sys.path.

    When ``use_working_tree`` is set, the working-tree project root is moved back
    ahead of the just-added packaged ``.sbslib`` so local sbs_utils edits are what
    actually run — for smoke-testing library changes against a real mission. (By
    default the packaged sbslib wins, matching the shipped library.)"""
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
    if use_working_tree:
        # Keep the working tree ahead of the sbslib we just inserted at sys.path[0].
        # Safe because sbs_utils is imported lazily (after this call), so the path
        # order is what the first import sees.
        if _PROJECT_ROOT in sys.path:
            sys.path.remove(_PROJECT_ROOT)
        sys.path.insert(0, _PROJECT_ROOT)
        print("[runner] using working-tree sbs_utils (overrides packaged sbslib)")


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
    from sbs_utils.helpers import FrameContext

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

    # task_schedule_server needs the server page's gui task. A trivial mission can
    # reach the registered @map list before that task exists (heavier missions
    # like LegendaryMissions don't); retry next tick instead of crashing.
    try:
        server_task = task_schedule_server(map_label, defer=True)
    except Exception as e:
        return False

    print(f"[runner] auto-starting map: {getattr(map_label, 'path', map_arg)}")
    set_shared_variable("GAME_STARTED", True)

    # signal_emit() is a no-op when FrameContext.mast is None, and we run in the
    # bare tick loop (outside cosmos_event_handler), so it normally is. The real
    # engine emits "game_started" from inside the server "start" MAST label where
    # the context is live, which is what fires routes like autoplay's
    # //signal/game_started. Establish the same context here so the signal is
    # actually delivered. The next cosmos_event_handler tick resets these.
    if server_task is not None:
        FrameContext.task = server_task
        FrameContext.mast = server_task.main.mast
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
    """Drain physics events queued by the physics background thread.

    Each entry is a tuple (tag, sub_tag, origin_id, selected_id[, parent_id
    [, extra_extra_tag]]). The optional 5th/6th elements carry parent_id and
    the launch_type (extra_extra_tag) for launch events; collision/damage use
    the 4-tuple form. Uses queue.Queue.get_nowait() for thread-safe reads.
    """
    import cosmos_dev.mock.sbs as _mock
    while True:
        try:
            item = _mock._pending_physics_events.get_nowait()
        except _queue_mod.Empty:
            break
        # Optional trailing dict carries extra FakeEvent attrs (e.g. sub_float,
        # source_point for //damage/internal). Pop it before positional parsing.
        extra_attrs = None
        if isinstance(item[-1], dict):
            extra_attrs = item[-1]
            item = item[:-1]
        tag, sub_tag, origin_id, selected_id = item[0], item[1], item[2], item[3]
        parent_id = item[4] if len(item) > 4 else 0
        extra_extra = item[5] if len(item) > 5 else ""
        ev = FakeEvent(client_id=0, tag=tag, sub_tag=sub_tag,
                       origin_id=origin_id, selected_id=selected_id,
                       parent_id=parent_id)
        if extra_extra:
            ev.extra_extra_tag = extra_extra
        if extra_attrs:
            for _k, _v in extra_attrs.items():
                setattr(ev, _k, _v)
        try:
            cosmos_event_handler(sim, ev)
        except Exception as e:
            _log_exc(f"physics event error ({tag}/{sub_tag}): {e}")


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


def _detect_game_end(sbs):
    """If the mission's game-end logic has fired, return (message, is_win); else
    None. Reads Agent.SHARED (set by objective.game_end_run_all) and the
    registered end conditions for the win/lose flag - no library change needed.
    is_win may be None if the triggering condition can't be matched."""
    from sbs_utils.agent import Agent
    if not Agent.SHARED.get_inventory_value("GAME_ENDED", False):
        return None
    msg = Agent.SHARED.get_inventory_value("START_TEXT", "") or ""
    is_win = None
    try:
        import sbs_utils.procedural.objective as _obj
        for cond in getattr(_obj, "__end_game_promise", []):
            _id, promise, message, win, _music, _signal = cond
            if promise.done():
                is_win = win
                if message:
                    msg = message
                break
    except Exception:
        pass
    return (msg, is_win)


def _emit_test_report(mission_folder, map_arg, sbs, cov, verdict, junit_path,
                      exerciser=None, game_end=None) -> int:
    """Print the coverage + verdict report for a --test run; optionally write
    JUnit XML. Returns the process exit code (0 pass / 1 fail)."""
    from sbs_utils.gui import Gui
    mast = None
    gc = Gui.clients.get(0)
    if gc is not None and gc.page is not None:
        mast = getattr(gc.page, "story", None)
    summ = cov.summary(mast) if cov is not None else {}
    ok = verdict.ok if verdict is not None else True
    name = os.path.basename(os.path.abspath(mission_folder))

    print("\n==== mission test report ====")
    print(f"mission: {name}   map: {map_arg}")
    if summ:
        print(f"coverage: labels {summ.get('labels_hit')}/{summ.get('labels_defined','?')} "
              f"({summ.get('labels_pct','?')}%)   nodes {summ.get('nodes_entered')}")
        for k, hd in (summ.get("by_kind") or {}).items():
            print(f"   {k:16} {hd[0]}/{hd[1]}")
    if exerciser is not None:
        print(f"exercise: steps {exerciser.steps}, enemies(last) {exerciser.enemies_last}, "
              f"combats forced {exerciser.forced}, beam-damage hits {getattr(sbs, '_apply_damage_calls', '?')}")
    # Combat-readiness diagnostic: do ships actually have beams, and how close?
    try:
        from sbs_utils.procedural.roles import role
        space = sbs.sim.space_objects if sbs.sim is not None else {}
        pids = [i for i in role("__player__") if i in space]
        npc_ids = [i for i in space if i not in set(pids)
                   and ((space[i].data_set.get("shield_max_val") or 0) > 0
                        or (space[i].data_set.get("beamCount") or 0) > 0
                        or (space[i].data_set.get("armorMax") or 0) > 0)
                   and (space[i]._abits & 0x10)]
        def _beamed(ids):
            return sum(1 for i in ids if (space[i].data_set.get("beamCount") or 0) > 0)
        mind = None
        for pi in pids:
            for ni in npc_ids:
                dx = space[pi]._pos.x - space[ni]._pos.x
                dz = space[pi]._pos.z - space[ni]._pos.z
                d = (dx * dx + dz * dz) ** 0.5
                mind = d if mind is None else min(mind, d)
        print(f"combat-ready: players w/beams {_beamed(pids)}/{len(pids)}, "
              f"npc(armed) w/beams {_beamed(npc_ids)}/{len(npc_ids)}, "
              f"min player->enemy {round(mind) if mind is not None else '-'}")
        if pids:
            hulls = [(getattr(space[i], "_data_tag", None), getattr(space[i], "_tick_type", None))
                     for i in pids]
            print(f"  __player__ hulls: {hulls}")
        # Damage sub-route detail (the by-kind rollup collapses //damage/* into one).
        if cov is not None and mast is not None:
            hit = cov.labels_hit
            dmg = sorted(l for l in mast.labels if l.startswith("__route__damage"))
            if dmg:
                marks = ", ".join(f"{l[len('__route__'):]}[{'x' if l in hit else '-'}]"
                                  for l in dmg)
                print(f"  damage routes: {marks}")
    except Exception as _e:
        print(f"combat-ready diag error: {_e}")
    if game_end is None:
        print("game end: did not end within the test window")
    else:
        msg, is_win = game_end
        verdict_word = "WIN" if is_win else ("LOSE" if is_win is not None else "ENDED")
        print(f"game end: {verdict_word} - {msg!r}")
    print(verdict.report() if verdict is not None else "no verdict")
    print("=============================")

    if junit_path:
        try:
            _write_junit(junit_path, name, ok, verdict, summ)
            print(f"[runner] junit written: {junit_path}")
        except Exception as e:
            print(f"[runner] junit write failed: {e}")
    return 0 if ok else 1


def _write_junit(path, name, ok, verdict, summ) -> None:
    """Minimal JUnit XML: one testsuite, one testcase (the mission run)."""
    from xml.sax.saxutils import escape
    failures = 0 if ok else 1
    cov_txt = ""
    if summ:
        cov_txt = (f"coverage labels {summ.get('labels_hit')}/{summ.get('labels_defined','?')} "
                   f"({summ.get('labels_pct','?')}%), nodes {summ.get('nodes_entered')}")
    body = ""
    if not ok and verdict is not None:
        body = f'      <failure message="runtime errors">{escape(verdict.report())}</failure>\n'
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<testsuite name="cosmos_dev.mission_runner" tests="1" failures="{failures}">\n'
        f'    <testcase classname="mission" name="{escape(name)}">\n'
        f'      <system-out>{escape(cov_txt)}</system-out>\n'
        f'{body}'
        f'    </testcase>\n'
        f'</testsuite>\n'
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


def _run(
    mission_folder: str,
    mast_file: str | None = None,
    map_arg: int | str | None = None,
    gui: bool = False,
    port: int = 8765,
    tick_rate: int = 60,
    cosmos_dir: str | None = None,
    test_seconds: float | None = None,
    junit_path: str | None = None,
    exercise: bool = False,
    use_working_tree: bool = False,
    seed: int | None = None,
) -> int:
    mission_folder = os.path.abspath(mission_folder)
    missions_root  = _find_missions_root(mission_folder)

    # --test SECONDS: headless conformance run. Force GUI off, default to map 0,
    # install MAST coverage + verdict, run ~SECONDS of sim time, then report +
    # exit code (0 pass / 1 fail). See AUTOPLAY_PLAN.md.
    _test = test_seconds is not None
    if _test:
        gui = False
        if map_arg is None:
            map_arg = 0

    # Source project takes precedence over any packaged sbslib on the path
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

    _load_libs(mission_folder, missions_root, use_working_tree)

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
    # The mission dir is derived from fs.script_dir.  We set sys.modules["script"]
    # to __main__ (the runner) above, so get_script_dir() would otherwise resolve
    # to the runner's directory and get_mission_dir_filename("settings.yaml") would
    # miss — leaving every settings.yaml value (AUTO_PLAY, DIFFICULTY, PLAYER_COUNT,
    # ...) at its built-in default.  In the real engine script.py lives in the
    # mission folder, so point script_dir there explicitly to match.
    fs.script_dir = os.path.abspath(mission_folder).replace("/", "\\")

    # Import order matters: core nodes before Cosmos extensions
    from sbs_utils.mast import core_nodes               # noqa: F401 — side-effect: registers node types
    from sbs_utils.mast_sbs import story_nodes          # noqa: F401 — side-effect: registers Cosmos nodes
    from sbs_utils.mast_sbs import mast_sbs_procedural  # noqa: F401 — side-effect: wires procedural API
    from sbs_utils.mast_sbs.maststorypage import StoryPage
    from sbs_utils.helpers import FrameContext, Context, FakeEvent
    from sbs_utils.vec import Vec3
    from sbs_utils.agent import Agent, clear_shared
    from sbs_utils.handlerhooks import cosmos_event_handler, reset_mission_state
    from sbs_utils.gui import Gui

    # Seed the RNG before any world spawn so the run is reproducible.  Resolves
    # to --seed if given, else the mission's seed_value setting, else a fresh
    # random seed.  The applied seed is always printed so a failing run can be
    # reproduced by passing it back via --seed.  See AUTOPLAY_PLAN.md.
    from sbs_utils.procedural.settings import settings_seed_apply
    _seed_used = settings_seed_apply(seed)
    print(f"[runner] rng seed: {_seed_used}"
          + ("" if seed is not None else "  (pass --seed to reproduce)"))

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

    # Physics runs in a background daemon thread, decoupled from MAST.
    # The main loop drains physics events each iteration via queue.Queue.get_nowait().
    _PHYSICS_HZ = 30.0
    _PHYSICS_DT = 1.0 / _PHYSICS_HZ      # sim-seconds advanced per physics tick
    _stop_physics = threading.Event()

    def _physics_worker(sbs_mod, stop_ev):
        while not stop_ev.is_set():
            if sbs_mod.sim is not None and not sbs_mod.sim._paused:
                try:
                    sbs_mod.physics_tick(dt=_PHYSICS_DT)
                except Exception as e:
                    _log_exc(f"physics worker error: {e}")
            stop_ev.wait(timeout=_PHYSICS_DT)   # exits promptly on stop signal

    _physics_thread = threading.Thread(
        target=_physics_worker,
        args=(sbs, _stop_physics),
        daemon=True,
        name="sbs-physics",
    )
    _physics_thread.start()
    print(f"[runner] running at {tick_rate} Hz  (MAST 5 Hz, physics {_PHYSICS_HZ:g} Hz background thread)")

    # Guard: clients that connect before the server's first MAST tick would run their
    # client_connect handler against uninitialised game state.  Buffer those connections
    # and show a placeholder, then replay them once the server tick completes.
    _server_initialized = False
    _pending_client_connects: list = []   # client IDs waiting for server init
    _pending_web_connects: list = []      # (client_id, path) web pages waiting for server init

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

    def _fire_web_connect(cid: int, path: str, query: dict = None) -> None:
        # A browser opened /web/<path>: dispatch it to the matching //web/<path>
        # MAST route as a web-client GUI session. Web clients are not engine
        # consoles (no register_client / client_connect), so they never enter
        # the console-select / player flow. Query string params seed page vars.
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(client_id=cid, tag="mission_tick"))
        opened = Gui.web_page_open(cid, path, data=query or None)
        if not opened:
            print(f"[runner] web client {cid}: no //web/{path} route")
            if hasattr(sbs, "send_gui_clear"):
                sbs.send_gui_clear(cid, "")
                sbs.send_gui_text(cid, "", "web_err",
                                  f"$text:No web page at /web/{path};color:#ff5555;",
                                  5, 40, 95, 60)
                sbs.send_gui_complete(cid, "")
        else:
            print(f"[runner] web client {cid} -> //web/{path}")

    _cov = _verdict = _exerciser = None
    _test_exit = 0
    _game_end = None
    _test_client_connected = False
    _TEST_CLIENT_ID = 0x8080000000000001   # synthetic console client for --test --exercise
    _test_wall0 = time.time()
    _test_wall_cap = (test_seconds * 2 + 30) if _test else 0
    if _test:
        from cosmos_dev.coverage import MastCoverage
        from cosmos_dev.verdict import MastVerdict
        from sbs_utils.helpers import _TPS as _TEST_TPS
        _cov = MastCoverage().install()
        _verdict = MastVerdict().install()
        if exercise:
            from cosmos_dev.exerciser import Exerciser
            _exerciser = Exerciser(sbs)
        print(f"[runner] TEST mode: run ~{test_seconds:g}s sim time, map={map_arg}"
              f"{', exercising' if exercise else ''}")

    try:
        while True:
            if _test:
                _sim_s = sbs.sim.time_tick_counter / _TEST_TPS
                if _sim_s >= test_seconds or (time.time() - _test_wall0) >= _test_wall_cap:
                    break
            # run_next_mission(): restart the current mission or switch to another.
            # The engine swaps missions at the process level; here we rebuild the
            # mission in-process between ticks. Polls the mock's pending request.
            _next_mission = sbs.pop_next_mission() if hasattr(sbs, "pop_next_mission") else None
            if _next_mission is not None:
                try:
                    # run_next_mission(name) passes a mission *folder name* relative
                    # to the missions dir (like the engine), not a CWD-relative path.
                    # Resolve against missions_root; abspath(name) vs CWD pointed at a
                    # nonexistent dir, so fs.script_dir went bad and the log-file
                    # FileHandler crashed on the next mission.
                    if _next_mission:
                        cand = (_next_mission if os.path.isabs(_next_mission)
                                else os.path.join(missions_root, _next_mission))
                        new_folder = os.path.abspath(cand)
                    else:
                        new_folder = mission_folder
                    print(f"[runner] run_next_mission -> {new_folder}")
                    if not os.path.isdir(new_folder):
                        print(f"[runner] run_next_mission: no such mission folder "
                              f"{new_folder!r} (from {_next_mission!r}) - ignoring")
                        raise FileNotFoundError(new_folder)
                    if new_folder != mission_folder:
                        _load_libs(new_folder, missions_root, use_working_tree)
                        fs.script_dir = new_folder.replace("/", "\\")
                        mission_folder = new_folder
                    # Fresh page subclass so the story recompiles with fresh shared
                    # state (cls.story is a per-class cached compile).
                    story_path = os.path.join(mission_folder, mast_file or "story.mast")

                    class _MissionPage(StoryPage):
                        story_file = story_path

                    Gui.server_start_page_class(_MissionPage)
                    Gui.client_start_page_class(_MissionPage)
                    # Drop all pages; the next server tick recreates the server page
                    # (Gui.present rebuilds it when Gui.clients is empty), and the
                    # previously-connected browsers re-handshake below.
                    prev_clients = [c for c in Gui.clients if c != 0]
                    Gui.clients.clear()
                    # Reset shared/agent state so the recompile is a clean slate, like
                    # the engine's fresh process. Without this, the previous compile's
                    # label names + console types linger in Agent.SHARED and the
                    # recompile fails ("Label conflicts with shared name", duplicate
                    # console) - run_next_mission was rarely exercised, so it was latent.
                    # Reset ALL per-mission runtime state (agents, shared names, and
                    # every route/tick/damage/etc. dispatcher) via the library's single
                    # source of truth, so the recompile is a clean slate like the engine's
                    # fresh process. (MAST globals from `import file.py` persist - the
                    # import dedup keeps them; a `default` that precedes the import is
                    # allowed against a global, see assign.py is_default.)
                    reset_mission_state()
                    # Fresh sim — in GUI mode create_new_sim also broadcasts
                    # world_reset so browsers wipe the old mission's 2D/3D views.
                    sbs.create_new_sim()
                    Agent.SHARED.set_inventory_value("sim", sbs.sim)
                    FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
                    _server_initialized = False
                    _map_started = (map_arg is None)
                    _pending_client_connects = list(prev_clients)
                except Exception as e:
                    _log_exc(f"run_next_mission reload failed: {e}")

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
                        _log_exc(f"gui event error: {e}")

            if run_mast:
                # Server MAST tick at 5 Hz.
                # Use sbs.sim (not the captured sim) so that sim_create() in a script
                # replaces the active simulation without breaking the tick loop.
                try:
                    cosmos_event_handler(sbs.sim, tick_event)
                except Exception as e:
                    if _verdict is not None:
                        _verdict.record_exception(e, where="mission_tick")
                    else:
                        # GUI/interactive debug: a MAST tick error (often surfacing at
                        # mission end) must NOT kill the runner - print the full trace
                        # and keep ticking, like the engine logs to mast.runtime.log
                        # and carries on. (--test re-raises via the verdict path above.)
                        _log_exc(f"mission_tick error: {e}")
                # NOTE: sim time (time_tick_counter) is advanced by the physics
                # tick, not the MAST tick — the physics thread is the sim-time
                # source, matching the engine.  See cosmos_dev/mock/sbs.py.
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
                    for cid, path, query in _pending_web_connects:
                        print(f"[runner] deferred web_connect: {cid} -> /web/{path}")
                        _fire_web_connect(cid, path, query)
                    _pending_web_connects.clear()

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
                        elif cev.get("event") == "resync":
                            # The server page joined without a client_connect
                            # (e.g. connecting after the game already started),
                            # so resend the full radar/terrain/skybox baseline.
                            if hasattr(sbs, "_force_terrain_push"):
                                sbs._force_terrain_push()
                        elif cev.get("event") == "web_connect":
                            cid   = cev["clientID"]
                            path  = cev.get("path", "")
                            query = cev.get("query", {})
                            if not _server_initialized:
                                _pending_web_connects.append((cid, path, query))
                                _show_waiting_screen(cid)
                            else:
                                _fire_web_connect(cid, path, query)
                        elif cev.get("event") == "web_disconnect":
                            cid = cev.get("clientID")
                            print(f"[runner] web client {cid} disconnected")
                            _pending_web_connects[:] = [
                                w for w in _pending_web_connects if w[0] != cid
                            ]
                            Gui.web_page_close(cid)
                        elif cev.get("event") == "disconnect":
                            cid = cev.get("clientID")
                            print(f"[runner] client {cid} disconnected")
                            _pending_client_connects[:] = [
                                c for c in _pending_client_connects if c != cid
                            ]
                            sbs.unregister_client(cid)
                    except Exception as e:
                        _log_exc(f"client event error: {e}")

            # Auto-start: poll each tick until @map/ labels are registered,
            # then schedule the requested map (replaces extern_debug.mast logic)
            if not _map_started:
                _map_started = _try_auto_start_map(map_arg, sbs)

            # --test --exercise: connect one synthetic console client so console
            # GUI (helm/weapons/science widgets + the monkey/fuzz) gets exercised -
            # headless otherwise only has the server page.
            if (_exerciser is not None and _map_started and _server_initialized
                    and not _test_client_connected):
                _test_client_connected = True
                print(f"[runner] TEST: connecting synthetic console client {_TEST_CLIENT_ID:#x}")
                try:
                    _fire_client_connect(_TEST_CLIENT_ID)
                except Exception as e:
                    print(f"[runner] synthetic client connect failed: {e}")

            # --exercise: drive selections/comms each MAST tick once the world is up.
            if _exerciser is not None and _map_started and run_mast and not sbs.sim._paused:
                _exerciser.step()

            # Record the first game-end (win/lose) the mission's logic triggers.
            if _test and _game_end is None:
                _game_end = _detect_game_end(sbs)

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
        if _test:
            if _cov is not None:
                _cov.uninstall()
            if _verdict is not None:
                _verdict.uninstall()
            _test_exit = _emit_test_report(mission_folder, map_arg, sbs,
                                           _cov, _verdict, junit_path, _exerciser,
                                           game_end=_game_end)
    return _test_exit


def run_mission(
    caller_file: str,
    mast_file: str | None = None,
    map_arg: int | str | None = None,
    gui: bool = False,
    port: int = 8765,
    tick_rate: int = 60,
    cosmos_dir: str | None = None,
    test_seconds: float | None = None,
    junit_path: str | None = None,
    use_working_tree: bool = False,
) -> int:
    """Entry point for per-mission extern_debug.py wrappers."""
    return _run(
        mission_folder=os.path.dirname(os.path.abspath(caller_file)),
        mast_file=mast_file,
        map_arg=map_arg,
        gui=gui,
        port=port,
        tick_rate=tick_rate,
        cosmos_dir=cosmos_dir,
        test_seconds=test_seconds,
        junit_path=junit_path,
        use_working_tree=use_working_tree,
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
    ap.add_argument("--test", type=float, default=None, metavar="SECONDS",
                    help="Headless conformance run: play ~SECONDS of sim time, then "
                         "print MAST coverage + a pass/fail verdict and exit 0/1")
    ap.add_argument("--junit", default=None, metavar="PATH",
                    help="With --test, also write a JUnit XML report to PATH")
    ap.add_argument("--seed", type=int, default=None, metavar="N",
                    help="Seed the RNG for a reproducible run (overrides the "
                         "seed_value setting). Omit to use seed_value, or 0 for a "
                         "fresh random seed (the seed used is printed).")
    ap.add_argument("--exercise", action="store_true",
                    help="With --test, actively drive selections/comms each tick to "
                         "push route coverage (vs only the mission's own autoplay)")
    ap.add_argument("--use-working-tree", action="store_true",
                    help="Run the working-tree sbs_utils instead of the packaged "
                         ".sbslib (smoke-test local library edits against a mission)")
    args = ap.parse_args()

    if args.map is None:
        map_val: int | str | None = None
    else:
        try:
            map_val = int(args.map)
        except ValueError:
            map_val = args.map

    _exit = _run(
        mission_folder=args.mission,
        mast_file=args.mast,
        map_arg=map_val,
        gui=args.gui,
        port=args.port,
        tick_rate=args.tick_rate,
        cosmos_dir=args.cosmos_dir,
        test_seconds=args.test,
        junit_path=args.junit,
        exercise=args.exercise,
        use_working_tree=args.use_working_tree,
        seed=args.seed,
    )
    sys.exit(_exit or 0)
