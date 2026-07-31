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


def _pid_alive(pid: int) -> bool:
    try:
        if os.name == "nt":
            import subprocess
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                 capture_output=True, text=True)
            return str(pid) in out.stdout
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _kill_tree(pid: int) -> None:
    try:
        if os.name == "nt":
            import subprocess
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        else:
            import signal
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


def _ensure_single_runner(tag) -> None:
    """Make the debug runner a singleton per port: on start, stop any previous
    instance we launched on the same port (and its child GUI server), then record
    our own PID. This means a re-launch "just works" — no zombie processes or
    port conflicts for the user to clean up by hand.

    Only ever targets a PID we ourselves recorded (a prior runner), and only if
    it's still alive — so it can't hit an unrelated process.
    """
    import tempfile
    import atexit
    pidfile = os.path.join(tempfile.gettempdir(), f"cosmos_dev_runner_{tag}.pid")
    try:
        if os.path.isfile(pidfile):
            with open(pidfile) as f:
                old = int((f.read() or "0").strip() or 0)
            if old and old != os.getpid() and _pid_alive(old):
                print(f"[runner] stopping previous debug runner (pid {old}) on port {tag}")
                _kill_tree(old)
                time.sleep(0.6)   # let the OS release the ports
    except Exception:
        pass
    try:
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))
        atexit.register(lambda: os.path.isfile(pidfile) and os.remove(pidfile))
    except Exception:
        pass


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


def _preview_story_args(payload: dict):
    """Map an ``amd/preview`` payload (dialogue/scan/face/text) to the four
    ``send_story_dialog(title, text, face, color)`` args, so an authored node can be
    rendered live in a running session. Pure (unit-tested) - the transport (an HTTP
    POST to /debug/command) and the sbs call live in the runner."""
    p = payload or {}
    kind = str(p.get("kind", ""))
    key = p.get("key", "")
    if kind == "dialogue":
        sp = p.get("speaker") or {}
        lines = p.get("lines") or []
        return (sp.get("name") or key, lines[0] if lines else "",
                sp.get("face") or "", sp.get("color") or "#0cf")
    if kind == "face":
        return (p.get("name") or key, "", p.get("face") or "", p.get("color") or "#0cf")
    if kind == "scan":
        lines = p.get("lines") or []
        return (f"Scan: {p.get('role', '')}".strip(), lines[0] if lines else "", "", "#0aa")
    return (p.get("display") or key, p.get("body") or "", "", "#888")


def _merge_cosmos_settings(extra: dict) -> None:
    """Merge keys into the ``COSMOS_SETTINGS`` override env var.

    Uses setdefault so an explicit ``sbs debug --set KEY=...`` already in the var
    keeps priority over anything the runner infers.
    """
    import json
    try:
        current = json.loads(os.environ.get("COSMOS_SETTINGS") or "{}")
        if not isinstance(current, dict):
            current = {}
    except Exception:
        current = {}
    for key, value in extra.items():
        current.setdefault(key, value)
    os.environ["COSMOS_SETTINGS"] = json.dumps(current)


def map_label_name(sched, label):
    """The label's canonical name if it is a ``@map`` entry point, else None.

    Accepts a name or a Label, matching ``start_task``, and always answers with the
    Label's own ``name`` so the two never disagree.
    """
    if isinstance(label, str):
        label = sched.mast.labels.get(label, None)
    name = getattr(label, "name", None)
    if isinstance(name, str) and name.startswith("map/"):
        return name
    return None


def live_map_task(sched, map_name):
    """The live task running the named ``@map`` label on this scheduler, or None.

    Liveness is membership in ``sched.tasks`` - the scheduler drops finished tasks
    from it - so a map whose task has ended can be launched again (mission restart).
    Deliberately does NOT consult ``task.done``: that is a Promise METHOD until
    do_jump overwrites it with a bool, so its truthiness says nothing about whether
    the task finished. Identity comparison because tasks are Agents and may define
    __eq__.
    """
    running = getattr(sched, "_map_tasks", {}).get(map_name)
    if running is None:
        return None
    return running if any(t is running for t in sched.tasks) else None


def install_map_launch_guard():
    """Make launching a ``@map`` label idempotent for this mock session.

    A map is a mission entry point and must run exactly once, but the mock has TWO
    ways to launch one: this runner's ``--map`` auto-start, and the operator pressing
    "Start Mission" on the server console's picker - which stays live and clickable
    after an auto-start, and which EVERY ``/server`` browser tab gets its own copy of
    (they all attach as clientID 0). Launch it twice and the whole map body re-runs,
    duplicating every spawn; because map seeds are fixed the duplicates land on
    IDENTICAL positions, so it reads as a mission content bug and silently invalidates
    any measurement taken on that session. Measured on the a2x hamaksector conversion:
    1392 terrain objects (461 nebulae + 931 asteroids) became 2784.

    Patched in HERE rather than shipped in sbs_utils on purpose. Neither launcher
    exists in the engine - it has exactly one server console and no --map auto-start -
    so this is a harness-only condition and the library keeps its exact production
    behaviour. ``--map <name>`` avoids the situation entirely by handing the launch to
    the console (see _run); this covers ``--map <int>``, which cannot resolve an index
    to a path before the console reads AUTO_START and so keeps runner-side scheduling.
    """
    from sbs_utils.mast.mastscheduler import MastScheduler
    if getattr(MastScheduler, "_map_launch_guarded", False):
        return
    _orig_start_task = MastScheduler.start_task

    def start_task(self, label="main", inputs=None, task_name=None, defer=False,
                   unscheduled=False, loc=0):
        name = map_label_name(self, label)
        if name is not None:
            running = live_map_task(self, name)
            if running is not None:
                print(f'[runner] map "{name}" is already running; '
                      f'ignoring duplicate launch')
                return running
        t = _orig_start_task(self, label, inputs, task_name, defer, unscheduled, loc)
        # unscheduled tasks are not in sched.tasks, so they have no liveness to track.
        if name is not None and not unscheduled:
            if getattr(self, "_map_tasks", None) is None:
                self._map_tasks = {}
            self._map_tasks[name] = t
        return t

    MastScheduler.start_task = start_task
    MastScheduler._map_launch_guarded = True


def _console_started_map() -> bool:
    """True once the story itself has started a map (server console `start` path).

    The console sets the shared ``GAME_STARTED`` when it launches WORLD_SELECT.
    """
    from sbs_utils.procedural.execution import get_shared_variable
    try:
        return bool(get_shared_variable("GAME_STARTED"))
    except Exception:
        return False


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

    # Apply the map's Defaults metadata (set-if-absent shared vars) before starting it - the
    # real engine does this when presenting the properties panel and again at launch, but the
    # headless runner skips the panel, so a map-local property var (e.g. JOBS_SELECT) would
    # otherwise be undefined in the map body.
    from sbs_utils.procedural.maps import map_apply_defaults
    map_apply_defaults(map_label)

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


_NOTHING_RAN = (
    "FAIL - mission executed 0 labels\n"
    "  Nothing ran, not even the story's own main. Usually the story or one of its\n"
    "  story.json mastlibs failed to load, or a parse error desynced the compiler.\n"
    "  Check mast.compile.log and that every declared lib is in __lib__.")


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
    # A run that executed NOTHING is a failure even though nothing raised. `ok` only ever
    # meant "no error was reported to the verdict", and the errors that kill a story
    # loudest are the ones nobody reports: an addon whose archive cannot be read, a parse
    # desync from a multi-line literal, a story.json lib that never loaded. Each compiles
    # to zero labels and used to print PASS - which is how a broken mastlib shipped
    # unnoticed across every release.
    #
    # No map needed to judge this: the story's own top-level `main` runs regardless, so
    # zero means even that never happened.
    ran_nothing = bool(summ) and not summ.get("labels_hit") and not summ.get("nodes_entered")
    ok = (verdict.ok if verdict is not None else True) and not ran_nothing
    name = os.path.basename(os.path.abspath(mission_folder))

    print("\n==== mission test report ====")
    print(f"mission: {name}   map: {map_arg}")
    if summ:
        print(f"coverage: labels {summ.get('labels_hit')}/{summ.get('labels_defined','?')} "
              f"({summ.get('labels_pct','?')}%)   nodes {summ.get('nodes_entered')}")
        for k, hd in (summ.get("by_kind") or {}).items():
            print(f"   {k:16} {hd[0]}/{hd[1]}")
    if exerciser is not None:
        print(f"exercise: steps {exerciser.steps}, clicks {getattr(exerciser, 'clicked', 0)}, "
              f"enemies(last) {exerciser.enemies_last}, "
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
    # Its own line, not folded into the verdict: "no errors" and "nothing ran" are
    # different diagnoses and want different next steps.
    if ran_nothing:
        print(_NOTHING_RAN)
    print("=============================")

    if junit_path:
        try:
            _write_junit(junit_path, name, ok, verdict, summ, ran_nothing)
            print(f"[runner] junit written: {junit_path}")
        except Exception as e:
            print(f"[runner] junit write failed: {e}")
    return 0 if ok else 1


def _write_junit(path, name, ok, verdict, summ, ran_nothing=False) -> None:
    """Minimal JUnit XML: one testsuite, one testcase (the mission run)."""
    from xml.sax.saxutils import escape
    failures = 0 if ok else 1
    cov_txt = ""
    if summ:
        cov_txt = (f"coverage labels {summ.get('labels_hit')}/{summ.get('labels_defined','?')} "
                   f"({summ.get('labels_pct','?')}%), nodes {summ.get('nodes_entered')}")
    body = ""
    # Distinct message so a CI run can tell "the mission errored" from "the mission never
    # ran at all" without reading the log.
    if ran_nothing:
        body = f'      <failure message="mission executed 0 labels">{escape(_NOTHING_RAN)}</failure>\n'
    elif not ok and verdict is not None:
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
    exercise_console: str | None = None,
    exercise_dwell: int | None = None,
    exercise_click: str | None = None,
    exercise_click_every: int = 3,
    use_working_tree: bool = False,
    seed: int | None = None,
    audit_layout: bool = False,
    aspect: str | None = None,
    dap_port: int | None = None,
    dap_wait: bool = False,
    probe_leak: float | None = None,
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

    # Be a singleton per port: stop any previous runner we launched on this port
    # (and its child GUI server) so a re-launch never leaves zombies / port
    # conflicts for the user to clean up. Scoped to the debug port when present.
    #
    # ONLY when we actually own a port. This used to run for every invocation,
    # including headless --test runs that bind nothing -- so any second runner
    # force-killed the first via the shared cosmos_dev_runner_<port>.pid, and the
    # victim died before emitting a single line (rc=1, empty stdout AND stderr).
    # That made concurrent headless runs impossible and looked like random
    # flakiness; it also killed --gui sessions that were minding their own
    # business. A run with no GUI and no debugger has nothing to be singleton
    # about.
    if gui or dap_port:
        _ensure_single_runner(dap_port or port)

    # Opt-in MAST source debugger (dev-only). Off by default: with dap_port unset
    # nothing here runs and the mission behaves exactly as before. Started HERE —
    # right after libs load, before the ~seconds of GUI/story setup — so the
    # socket is listening almost immediately and a one-click attach doesn't race
    # it. A daemon thread serves DAP; the editor attaches and its breakpoints park
    # the tick loop while control is serviced on that thread.
    _dap_ready = threading.Event()          # set once an editor has attached + configured
    if dap_port:
        from cosmos_dev.mast_dap import serve_dap_socket, live_mission_provider
        threading.Thread(
            target=serve_dap_socket,
            kwargs=dict(host="127.0.0.1", port=dap_port,
                        attach_provider=live_mission_provider(),
                        on_configured=_dap_ready.set,
                        ready=lambda p: print(f"[runner] MAST debug adapter LISTENING on 127.0.0.1:{p}")),
            daemon=True, name="mast-dap").start()
        if dap_wait:
            print("[runner] --dap-wait: holding map auto-start until a debugger attaches")

    # Communicate map choice to the debug .mast via environment variable
    os.environ["COSMOS_DEBUG_MAP"] = str(map_arg)

    # Map auto-start: prefer the launcher the real engine uses. LM's server console
    # reaches its `start` label via `jump start if AUTO_START` and launches
    # WORLD_SELECT itself (also doing sim_resume, map_apply_defaults and the
    # game_started emit), so hand a NAMED --map over as settings and let the console
    # start it - one launcher, so the map body cannot run twice.
    #
    # An INDEX cannot be turned into a path until the story has compiled and
    # registered its @map labels, which is after the console's AUTO_START check, so
    # `--map <int>` keeps the runner-side scheduling path below. Either way
    # MastScheduler.start_task makes a map launch idempotent.
    # Dev-only safety net: a map body must never run twice (see the docstring).
    # Installed after _load_libs so it patches whichever sbs_utils actually loaded
    # (packaged .sbslib, or the working tree under --use-working-tree).
    install_map_launch_guard()

    _console_launch = isinstance(map_arg, str)
    if _console_launch:
        _merge_cosmos_settings({"WORLD_SELECT": map_arg, "AUTO_START": True})
        print(f"[runner] map '{map_arg}' handed to the server console (AUTO_START)")

    _server_proc = None
    _orig_stdout = _orig_stderr = None
    if gui:
        import cosmos_dev.mockgui.sbs as sbs
        _cosmos_dir = cosmos_dir or os.path.dirname(os.path.dirname(missions_root))
        # Serve art from the mission and from the missions root: a mission's own
        # media/ and any pack it pins under shared_media: live outside
        # data/graphics, and a shared pack is addressed `../__lib__/media/<pack>/`
        # which the browser normalises to `/__lib__/media/...`.
        _server_proc = sbs.start_server(
            port=port, cosmos_dir=_cosmos_dir,
            static_roots=[mission_folder, missions_root])
        print(f"[runner] GUI server started — open http://localhost:{port}/")
        _orig_stdout, _orig_stderr = sys.stdout, sys.stderr
        sys.stdout = _TeeWriter(sys.__stdout__, "info",  sbs.gui_queue)
        sys.stderr = _TeeWriter(sys.__stderr__, "error", sbs.gui_queue)
    else:
        import cosmos_dev.mock.sbs as sbs

    # Resolution sweep: force a client screen size so layouts build at it (mixed
    # %/px units make overflow resolution-dependent — small windows are worst).
    # Parsed BEFORE the audit installs, because the text-fit check needs the
    # screen size to turn percent-local rects back into pixels.
    _aspect_wh = None
    if aspect:
        try:
            _w, _h = (int(x) for x in aspect.lower().split("x"))
            _aspect_wh = (_w, _h)
            print(f"[runner] forcing aspect {_w}x{_h}")
        except Exception:
            print(f"[runner] bad --aspect {aspect!r}, expected WxH (e.g. 1280x720)")

    # SPIKE (gui-sizing-accuracy): tap the emitted rect stream for a read-only
    # layout audit (overflow / overlap / text-fit). Zero render change; off
    # unless asked.
    if audit_layout:
        from cosmos_dev import layout_audit
        layout_audit.install(sbs, aspect=_aspect_wh or (1024, 768))
        print("[runner] layout audit installed")

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
    # Watchdog on the console-launch handover above: a mission without the LM
    # consoles addon has nothing to act on AUTO_START, so take the launch back
    # rather than sitting on a paused sim forever.
    _CONSOLE_LAUNCH_GRACE = 30.0
    _console_deadline = None

    # Physics runs in a background daemon thread, decoupled from MAST.
    # The main loop drains physics events each iteration via queue.Queue.get_nowait().
    _PHYSICS_HZ = 30.0
    _PHYSICS_DT = 1.0 / _PHYSICS_HZ      # sim-seconds advanced per physics tick
    _stop_physics = threading.Event()

    # Physics timing, sampled by --probe-leak: how long a tick actually takes and
    # what rate the thread achieves. `busy` is work time, `ticks` completed ticks.
    _phys_stats = {"ticks": 0, "busy": 0.0, "wall0": time.perf_counter()}
    _mast_stats = {"ticks": 0, "busy": 0.0}   # main-thread MAST cost (same sampler)

    def _physics_worker(sbs_mod, stop_ev):
        # FIXED-RATE, not fixed-delay.  This used to tick and then wait a FULL
        # _PHYSICS_DT, so the period was (work + dt) and sim time advanced at
        # dt/(work+dt) of wall clock -- a heavy mission (~27ms of physics work
        # against a 33ms budget) ran the sim at ~0.55x and looked "frozen" in the
        # browser.  Track an absolute deadline and sleep only the remainder; when
        # a tick overruns the budget, resync instead of spiral-of-death catching up.
        _next = time.perf_counter()
        while not stop_ev.is_set():
            if sbs_mod.sim is not None and not sbs_mod.sim._paused:
                _t0 = time.perf_counter()
                try:
                    sbs_mod.physics_tick(dt=_PHYSICS_DT)
                except Exception as e:
                    _log_exc(f"physics worker error: {e}")
                _phys_stats["busy"] += time.perf_counter() - _t0
                _phys_stats["ticks"] += 1
            _next += _PHYSICS_DT
            _sleep = _next - time.perf_counter()
            if _sleep <= 0:
                _next = time.perf_counter()   # overran the budget - resync, don't chase
                _sleep = 0
            stop_ev.wait(timeout=_sleep)      # exits promptly on stop signal

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

    # GUI Editor live preview: the last design pushed via a gui_preview command,
    # plus the browser client ids showing it (see _fire_web_connect / gui_preview).
    _preview = {"code": None, "clients": set()}

    def _fire_web_connect(cid: int, path: str, query: dict = None) -> None:
        # A browser opened /web/<path>: dispatch it to the matching //web/<path>
        # MAST route as a web-client GUI session. Web clients are not engine
        # consoles (no register_client / client_connect), so they never enter
        # the console-select / player flow. Query string params seed page vars.
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(client_id=cid, tag="mission_tick"))
        # /web/gui_preview is the GUI Editor's live preview: render the last design
        # the editor pushed (a gui_preview command) as THIS browser's own page.
        if str(path).strip("/") == "gui_preview":
            # Always track this browser, so a design that's still being stored (the
            # POST is processed a tick later than the browser connects) lands here
            # when the gui_preview command arrives.
            _preview["clients"].add(cid)
            if _preview["code"]:
                from cosmos_dev.gui_preview import present_gui_code
                errs = present_gui_code(_preview["code"], client_id=cid)
                if errs:
                    msg = "; ".join(str(e).strip() for e in errs)
                    print(f"[runner] preview compile errors: {msg}")
                    sbs.send_gui_clear(cid, "")
                    sbs.send_gui_text(cid, "", "perr",
                                      "$text:Preview error: " + msg.replace(";", ",")[:300] + ";color:#f66;",
                                      5, 5, 95, 95)
                    sbs.send_gui_complete(cid, "")
                else:
                    print(f"[runner] preview client {cid:#x} rendered ({len(_preview['code'])} chars)")
            else:
                print(f"[runner] preview client {cid:#x}: no design stored yet")
                sbs.send_gui_clear(cid, "")
                sbs.send_gui_text(cid, "", "no_preview",
                                  "$text:Waiting for a design — press Preview in the GUI Editor.;color:#8ab;",
                                  5, 40, 95, 60)
                sbs.send_gui_complete(cid, "")
            return
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

    # ---- /debug control channel (mockgui /ws/debug) ---------------------------
    def _debug_reply(cid: int, data: dict) -> None:
        """Send a control-plane reply to one /debug tab. The fixed tag makes
        repeat replies replace in place in the server's frame state instead of
        accumulating."""
        try:
            payload = {"cmd": "debug_status", "clientID": cid, "tag": "status"}
            payload.update(data)
            sbs.gui_queue.put(payload)
        except Exception as e:
            _log_exc(f"debug reply error: {e}")

    def _debug_status() -> dict:
        from sbs_utils.helpers import _TPS
        # Count LIVE objects from the sim itself (ground truth), NOT Agent.all - which also
        # holds brains/objectives/the shared agent (and can retain stale entries), so it reads
        # high and "accumulates". Break the live count down PER SIDE so it's obvious what's left.
        players = npcs = terrain = 0
        by_side: dict = {}
        if sbs.sim is not None:
            for obj in list(sbs.sim.space_objects.values()):
                ab   = getattr(obj, "_abits", 0)
                # Spell the empty side out. It renders next to real side names, and a
                # bare "-" next to "monster" read as "2004 monsters" when it is really
                # 2004 SIDELESS TERRAIN - the biggest bucket on any map.
                side = getattr(obj, "_side", "") or "(no side)"
                row  = by_side.setdefault(side, {"players": 0, "npcs": 0, "terrain": 0})
                if ab & 0x20:
                    row["players"] += 1; players += 1
                elif ab & 0x10:
                    row["npcs"] += 1; npcs += 1
                else:
                    row["terrain"] += 1; terrain += 1
        # Break Agent.all down by class so a leak is obvious (which kind is piling up).
        agent_types: dict = {}
        for a in list(Agent.all.values()):
            tn = type(a).__name__
            agent_types[tn] = agent_types.get(tn, 0) + 1
        agent_types = dict(sorted(agent_types.items(), key=lambda kv: -kv[1])[:8])
        return {
            "mission": os.path.basename(mission_folder),
            "map": str(map_arg) if map_arg is not None else "(picker)",
            "sim_seconds": round(sbs.sim.time_tick_counter / _TPS, 1) if sbs.sim else 0.0,
            "paused": bool(sbs.sim._paused) if sbs.sim else True,
            "clients": [f"{c:#x}" for c in Gui.clients if c != 0],
            "agents": len(Agent.all),   # NOTE: all agents (incl. brains/objectives/shared) - NOT a ship count
            "players": players,
            "npcs": npcs,
            "terrain": terrain,
            "by_side": by_side,         # accurate LIVE per-side breakdown (from sim.space_objects)
            "agent_types": agent_types, # Agent.all by class - to spot what's leaking
            "tick_rate": tick_rate,
        }

    def _leak_probe(wall0: float) -> None:
        """One periodic leak sample (--probe-leak).

        The question this answers: when the sim "crawls", is Agent.all GROWING,
        and are the extra agents ENDED MAST tasks (corpses that nothing purges)
        rather than live work?  `rate` is sim-seconds gained per wall-second —
        the actual throughput number behind the "frozen mission" symptom.
        """
        from sbs_utils.helpers import _TPS
        from sbs_utils.mast.mastscheduler import MastAsyncTask
        sim_s  = sbs.sim.time_tick_counter / _TPS if sbs.sim else 0.0
        wall_s = max(time.time() - wall0, 1e-6)
        objs   = len(sbs.sim.space_objects) if sbs.sim else 0
        agents = list(Agent.all.values())
        tasks  = [a for a in agents if isinstance(a, MastAsyncTask)]
        ended  = sum(1 for t in tasks if t.done())
        types: dict = {}
        for a in agents:
            tn = type(a).__name__
            types[tn] = types.get(tn, 0) + 1
        # Are the players actually being DRIVEN?  A mock player ship moves ONLY when
        # something writes playerThrottle (a helm console, or the mission's autoplay) -
        # so "the whole mission is frozen" is often just N parked ships nobody is
        # flying, which is a completely different fault from a slow sim.  Same for
        # NPCs, whose brains write target_pos_*.
        pl = pl_thr = pl_mov = pl_dead = npc_mov = 0
        for obj in (list(sbs.sim.space_objects.values()) if sbs.sim else []):
            ab = getattr(obj, "_abits", 0)
            spd = abs(getattr(obj, "_cur_speed", 0.0) or 0.0)
            if ab & 0x20:
                pl += 1
                try:
                    if (obj.data_set.get("playerThrottle") or 0.0) > 0.0:
                        pl_thr += 1
                    # A dead ship is zeroed by _playership_drive, so "stopped"
                    # means destroyed here, NOT "autoplay quit driving it".
                    if (obj.data_set.get("deathState") or 0) > 0:
                        pl_dead += 1
                except Exception:
                    pass
                if spd > 0.01:
                    pl_mov += 1
            elif ab & 0x10 and spd > 0.01:
                npc_mov += 1

        # Grid objects are a ship's INTERIOR map (rooms/systems/damcons), so a big
        # count is only alarming if the objects outlive their host. Split them by
        # whether host_id is still a live space object: orphaned == leaked.
        from sbs_utils.gridobject import GridObject
        live_ids = set(sbs.sim.space_objects.keys()) if sbs.sim else set()
        g_hosts: dict = {}
        g_orphan = 0
        for a in agents:
            if not isinstance(a, GridObject):
                continue
            h = getattr(a, "host_id", 0)
            if h in live_ids:
                g_hosts[h] = g_hosts.get(h, 0) + 1
            else:
                g_orphan += 1

        # Any ENDED task still registered escaped disposal. Group them by label so
        # the leaking spawn site is named rather than guessed.
        stale: dict = {}
        for t in tasks:
            if not t.done():
                continue
            try:
                lbl = t.active_label
                lbl = getattr(lbl, "name", lbl)
            except Exception:
                lbl = "?"
            kind = "sub" if getattr(t, "is_sub_task", False) else "top"
            try:
                sched = t.main
                where = "in-sched" if t in getattr(sched, "tasks", []) else "orphan"
            except Exception:
                where = "?"
            stale[f"{lbl}[{kind},{where}]"] = stale.get(f"{lbl}[{kind},{where}]", 0) + 1
        stale_top = " ".join(f"{k}={v}" for k, v in
                             sorted(stale.items(), key=lambda kv: -kv[1])[:4])

        top = " ".join(f"{k}={v}" for k, v in
                       sorted(types.items(), key=lambda kv: -kv[1])[:5])
        # Report costs for THIS interval, not cumulative averages - a cumulative mean
        # smears the degradation that is the whole point of sampling.
        now = time.perf_counter()
        d_wall = max(now - _probe_last["wall"], 1e-6)
        d_pt   = max(_phys_stats["ticks"] - _probe_last["p_ticks"], 1)
        d_pb   = _phys_stats["busy"] - _probe_last["p_busy"]
        d_mt   = max(_mast_stats["ticks"] - _probe_last["m_ticks"], 1)
        d_mb   = _mast_stats["busy"] - _probe_last["m_busy"]
        _probe_last.update(wall=now, p_ticks=_phys_stats["ticks"], p_busy=_phys_stats["busy"],
                           m_ticks=_mast_stats["ticks"], m_busy=_mast_stats["busy"])
        print(f"[probe] sim={sim_s:7.1f}s wall={wall_s:6.1f}s "
              f"rate={sim_s / wall_s:5.2f}x objs={objs:5d} "
              f"agents={len(agents):6d} tasks={len(tasks):6d} ended={ended:6d} | "
              f"phys {d_pb / d_pt * 1000:5.1f}ms/tick {d_pt / d_wall:5.1f}Hz  "
              f"mast {d_mb / d_mt * 1000:6.1f}ms/tick | "
              f"players {pl_thr}/{pl} throttled {pl_mov}/{pl} moving "
              f"{pl_dead} dead, npcs moving {npc_mov} | "
              f"grids {len(g_hosts)} hosts/{g_orphan} orphaned | {top}")
        if stale_top:
            print(f"[probe]   undisposed ended tasks by label: {stale_top}")

        # Name WHY each stopped player is stopped. LM autoplay records its decision in
        # the ship's `ap_helm_mode` inventory value, so the stop reason (dock latch vs
        # "cannot turn" hold vs standoff) is readable rather than guessable.
        if pl_mov < pl:
            for obj in list(sbs.sim.space_objects.values()):
                if not (getattr(obj, "_abits", 0) & 0x20):
                    continue
                if abs(getattr(obj, "_cur_speed", 0.0) or 0.0) > 0.01:
                    continue
                ds = obj.data_set
                try:
                    a = Agent.get(getattr(obj, "_id", 0))
                    mode = a.get_inventory_value("ap_helm_mode", "?") if a else "?"
                except Exception:
                    mode = "?"
                def _g(k, i=0, d=0):
                    try:
                        return ds.get(k, i) or d
                    except Exception:
                        return d
                print(f"[probe]   stopped {getattr(obj, '_name', '?')!r:>22} "
                      f"mode={mode!s:<10} dock={_g('dock_state', 0, '')!s:<10} "
                      f"thr={_g('playerThrottle'):<4} energy={_g('energy'):<7.0f} "
                      f"shield={_g('shield_val'):.0f}/{_g('shield_max_val', 0, 1):.0f} "
                      f"turn_coeff={_g('turn_damage_coeff', 0, 1):.2f}")

    def _handle_debug_command(cev: dict) -> None:
        nonlocal map_arg
        cid    = cev.get("clientID", 0)
        data   = cev.get("data") or {}
        action = str(data.get("action", "")).strip().lower()
        if action == "status":
            _debug_reply(cid, {"status": _debug_status()})
        elif action == "pause":
            sbs.pause_sim()
            _debug_reply(cid, {"ack": "sim paused", "status": _debug_status()})
        elif action == "resume":
            sbs.resume_sim()
            _debug_reply(cid, {"ack": "sim resumed", "status": _debug_status()})
        elif action == "restart":
            # Optionally retarget the auto-start map, then ride the existing
            # run_next_mission reload path (recompile + reset_mission_state +
            # fresh sim + browser re-handshake). The server process and every
            # browser websocket stay up - no teardown.
            if str(data.get("map", "")).strip() != "":
                m = str(data["map"]).strip()
                map_arg = int(m) if m.lstrip("-").isdigit() else m
                os.environ["COSMOS_DEBUG_MAP"] = str(map_arg)
            elif data.get("picker"):
                map_arg = None
                os.environ["COSMOS_DEBUG_MAP"] = "None"
            sbs.run_next_mission(str(data.get("mission", "") or ""))
            print(f"[runner] debug: restart requested (map={map_arg})")
            _debug_reply(cid, {"ack": f"restarting (map={map_arg if map_arg is not None else 'picker'})"})
        elif action == "preview":
            # Render an authored AMD node (from the VS Code extension's amd/preview)
            # live in this session as a story dialog - the highest-fidelity preview.
            payload = data.get("payload") or {}
            try:
                title, text, face, color = _preview_story_args(payload)
                sbs.send_story_dialog(0, title, text, face, color)
                _debug_reply(cid, {"ack": f"previewed {payload.get('kind') or 'node'} "
                                          f"'{payload.get('key', '')}'"})
            except Exception as e:
                _debug_reply(cid, {"error": f"preview failed: {e}"})
        elif action == "gui_preview":
            # Store a GUI Editor design (a block of gui_* MAST). A browser at
            # /web/gui_preview renders it as its own page (see _fire_web_connect);
            # if a preview browser is already open, re-render it there now.
            code = data.get("code", "")
            _preview["code"] = code
            print(f"[runner] gui_preview: stored {len(code)} chars; "
                  f"open browsers: {[f'{c:#x}' for c in _preview['clients'] if c in Gui.clients]}")
            try:
                from cosmos_dev.gui_preview import present_gui_code
                live = [c for c in list(_preview["clients"]) if c in Gui.clients]
                _preview["clients"] = set(live)
                errs = []
                for c in live:
                    errs = present_gui_code(code, client_id=c) or errs
                if errs:
                    _debug_reply(cid, {"error": "gui_preview: " + "; ".join(str(e).strip() for e in errs)})
                else:
                    _debug_reply(cid, {"ack": f"gui preview stored"
                                            + (f", shown on {len(live)} browser(s)" if live else " — open /web/gui_preview")})
            except Exception as e:
                _debug_reply(cid, {"error": f"gui_preview failed: {e}"})
        elif action == "signal":
            name = str(data.get("name", "")).strip()
            if not name:
                _debug_reply(cid, {"error": "signal needs a name"})
                return
            from sbs_utils.procedural.signal import signal_emit
            sig_data = data.get("data") if isinstance(data.get("data"), dict) else None
            try:
                # Best-effort: FrameContext.mast is whatever the last MAST tick
                # left in place; before the first tick this is a no-op.
                signal_emit(name, sig_data)
                _debug_reply(cid, {"ack": f"signal '{name}' emitted"})
            except Exception as e:
                _debug_reply(cid, {"error": f"signal failed: {e}"})
        else:
            _debug_reply(cid, {"error": f"unknown action {action!r}"})

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
            _extra_consoles = [c.strip() for c in (exercise_console or "").split(",") if c.strip()]
            _clicks = [c.strip() for c in (exercise_click or "").split(",") if c.strip()]
            _exerciser = Exerciser(sbs, extra_consoles=_extra_consoles,
                                   console_dwell=exercise_dwell,
                                   click_labels=_clicks,
                                   click_every=exercise_click_every)
        print(f"[runner] TEST mode: run ~{test_seconds:g}s sim time, map={map_arg}"
              f"{', exercising' if exercise else ''}")

    _dap_wait_deadline = None   # set on first auto-start attempt so we don't wait forever

    _probe_wall0 = time.time()
    _probe_next = 0.0
    _probe_last = {"wall": time.perf_counter(), "p_ticks": 0, "p_busy": 0.0,
                   "m_ticks": 0, "m_busy": 0.0}

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
                        elif etype == "red_alert_toggle":
                            # The red_alert toggle button (comms widget) → the engine's
                            # "red_alert" event; handlerhooks sets the ship's red_alert and
                            # emits red_alert_change. value_tag "on"/"off" per the browser
                            # button's requested next state.
                            gev_ev = FakeEvent(client_id=cid, tag="red_alert")
                            gev_ev.value_tag = "on" if gev.get("on") else "off"
                        elif etype == "comms_button":
                            # A click on a comms_control menu button → the engine's
                            # press_comms_button event. sub_tag = the button INDEX (the comms
                            # system reads int(event.sub_tag)); routed by the comms origin (the
                            # client's ship/cam) + its current comms selection (the object —
                            # which can legitimately be id 0).
                            origin = 0
                            try:
                                origin = sbs.get_ship_of_client(cid) or 0
                            except Exception:
                                origin = 0
                            selected = 0
                            try:
                                from sbs_utils.procedural.query import get_comms_selection
                                selected = get_comms_selection(origin) or 0
                            except Exception:
                                selected = 0
                            gev_ev = FakeEvent(client_id=cid, tag="press_comms_button",
                                               sub_tag=str(gev.get("tag", "")),
                                               origin_id=origin, selected_id=selected)
                        elif etype == "select_space_object":
                            # A 2D-view click in the browser radar → the engine's
                            # select_space_object event (same type name the engine uses).
                            # The runner supplies origin_id (the client's assigned ship/cam)
                            # and sub_tag (the console name); consoledispatcher.py routes to
                            # comms/science by name.
                            try:
                                sel = int(gev.get("id", 0) or 0)
                            except (TypeError, ValueError):
                                sel = 0
                            origin = 0
                            try:
                                origin = sbs.get_ship_of_client(cid) or 0
                            except Exception:
                                origin = 0
                            console = ""
                            _getname = getattr(sbs, "get_client_console_name", None)
                            if _getname is not None:
                                console = _getname(cid) or ""
                            # consoledispatcher routes a selection by the target-UID it
                            # derives (convert_to_console_id). For a 2D-view click that UID
                            # must be the console's registered selection key — comms/science
                            # register under comms_target_UID / science_target_UID, NOT the
                            # ..._2d_ variant. Set extra_tag to the right UID (matched early in
                            # convert) so the registered select callback actually fires.
                            _cn = console.lower()
                            if "weap" in _cn:
                                _uid = "weapon_target_UID"
                            elif "sci" in _cn or "admiral" in _cn:
                                _uid = "science_target_UID"
                            elif "comm" in _cn:
                                _uid = "comms_target_UID"
                            else:
                                _uid = "normal_target_UID"
                            # value_tag is the real 2D WIDGET name (engine sends e.g.
                            # "comms_2d_view", not "2dview"); the mock knows it per client.
                            _w2d = getattr(sbs, "get_client_2d_widget", None)
                            _widget = (_w2d(cid) if _w2d is not None else "") \
                                or gev.get("widget", "2dview") or "2dview"
                            gev_ev = FakeEvent(client_id=cid, tag="select_space_object",
                                               sub_tag=console, origin_id=origin,
                                               selected_id=sel)
                            gev_ev.value_tag = _widget
                            gev_ev.extra_tag = _uid
                            gev_ev.extra_extra_tag = gev.get("button", "lmb")
                            gev_ev.source_point = Vec3(gev.get("wx", 0.0),
                                                       gev.get("wy", 0.0),
                                                       gev.get("wz", 0.0))
                        elif etype == "hold_click":
                            # Right-click / long-press on a 2D view → the engine's hold_click
                            # event (popup / move-camera path, distinct from selection). sub_tag
                            # is the console TYPE (e.g. "comms"), not the full name; convert_to_
                            # console_id maps a hold to "<type>_popup". No value_tag/extra_tag.
                            try:
                                sel = int(gev.get("id", 0) or 0)
                            except (TypeError, ValueError):
                                sel = 0
                            origin = 0
                            try:
                                origin = sbs.get_ship_of_client(cid) or 0
                            except Exception:
                                origin = 0
                            console = ""
                            _getname = getattr(sbs, "get_client_console_name", None)
                            if _getname is not None:
                                console = _getname(cid) or ""
                            _cn = console.lower()
                            if "weap" in _cn:
                                _ctype = "weapons"
                            elif "sci" in _cn or "admiral" in _cn:
                                _ctype = "science"
                            elif "comm" in _cn:
                                _ctype = "comms"
                            elif "helm" in _cn:
                                _ctype = "helm"
                            else:
                                _ctype = _cn
                            gev_ev = FakeEvent(client_id=cid, tag="hold_click",
                                               sub_tag=_ctype, origin_id=origin,
                                               selected_id=sel)
                            gev_ev.parent_id = origin
                            gev_ev.source_point = Vec3(gev.get("wx", 0.0),
                                                       gev.get("wy", 0.0),
                                                       gev.get("wz", 0.0))
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
                _mast_t0 = time.perf_counter()
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
                # Main-thread MAST cost, sampled by --probe-leak.  Read it NEXT TO the
                # physics ms/tick: the physics thread contends with this one for the
                # GIL and sim._lock, so MAST getting heavier shows up as physics
                # "work" getting slower even when object count is flat.
                _mast_stats["ticks"] += 1
                _mast_stats["busy"] += time.perf_counter() - _mast_t0
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

            if probe_leak:
                from sbs_utils.helpers import _TPS as _PROBE_TPS
                _probe_sim = sbs.sim.time_tick_counter / _PROBE_TPS if sbs.sim else 0.0
                if _probe_sim >= _probe_next:
                    _probe_next = _probe_sim + probe_leak
                    _leak_probe(_probe_wall0)

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
                        elif cev.get("event") == "debug":
                            # /debug page control command (restart/pause/...).
                            _handle_debug_command(cev)
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
            # then schedule the requested map (replaces extern_debug.mast logic).
            # With --dap-wait, hold auto-start until a debugger has attached (so
            # breakpoints in the map are armed before its code runs) — but not
            # forever: fall through after ~120s if nobody attaches.
            if not _map_started:
                _hold = dap_wait and dap_port and not _dap_ready.is_set()
                if _hold:
                    if _dap_wait_deadline is None:
                        _dap_wait_deadline = time.time() + 120.0
                    elif time.time() > _dap_wait_deadline:
                        print("[runner] --dap-wait timed out; auto-starting without a debugger")
                        _hold = False
                if not _hold:
                    if _console_launch:
                        # The server console owns the launch (AUTO_START handover).
                        if _console_deadline is None:
                            _console_deadline = time.time() + _CONSOLE_LAUNCH_GRACE
                        if _console_started_map():
                            print("[runner] map started by the server console")
                            _map_started = True
                        elif time.time() > _console_deadline:
                            print("[runner] server console did not start the map "
                                  "in time; falling back to runner auto-start")
                            _console_launch = False
                    else:
                        _map_started = _try_auto_start_map(map_arg, sbs)

            # Resolution sweep: pin every client's screen size each tick so layouts
            # (re)build at the forced aspect instead of the 1024x768 default.
            if _aspect_wh is not None:
                _arv = Vec3(_aspect_wh[0], _aspect_wh[1], 1)
                for _cid in (0, _TEST_CLIENT_ID, *_pending_client_connects):
                    FrameContext.aspect_ratios[_cid] = _arv

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
                # Last word to the log. The seams miss library code that catches
                # its own exception and only logs it, so a run could print
                # "PASS - no runtime errors" with errors sitting in
                # mast.runtime.log. Swept AFTER uninstall, so nothing else can
                # write between the sweep and the report.
                # Same path Mast() opened the handler on, so this reads the file
                # that was actually written rather than a same-named one in CWD.
                from sbs_utils import fs as _fs
                _verdict.sweep_runtime_log(
                    _fs.get_mission_dir_filename("mast.runtime.log"))
            _test_exit = _emit_test_report(mission_folder, map_arg, sbs,
                                           _cov, _verdict, junit_path, _exerciser,
                                           game_end=_game_end)
        if audit_layout:
            from cosmos_dev import layout_audit
            print(layout_audit.report())
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
    ap.add_argument("--exercise-console", default=None, metavar="NAME[,NAME]",
                    help="With --exercise, also cycle these mission-defined consoles "
                         "(e.g. gallery). The default cycle is core gameplay consoles "
                         "only, so a custom console is otherwise never entered.")
    ap.add_argument("--exercise-dwell", type=int, default=None, metavar="N",
                    help="With --exercise, steps to sit on each console before "
                         "moving on (default 3). Raise it (e.g. 25) to give "
                         "`on change` / watcher logic time to fire at all -- at "
                         "the default a console is swapped in under a sim-second.")
    ap.add_argument("--exercise-click", default=None, metavar="LABEL[,LABEL]",
                    help="With --exercise, press any live button whose DISPLAYED "
                         "label matches, every --exercise-click-every steps. Lets "
                         "one boot walk a mission's own paging control (a tour, a "
                         "wizard) instead of booting once per state.")
    ap.add_argument("--exercise-click-every", type=int, default=3, metavar="N",
                    help="Steps between --exercise-click presses (default 3).")
    ap.add_argument("--use-working-tree", action="store_true",
                    help="Run the working-tree sbs_utils instead of the packaged "
                         ".sbslib (smoke-test local library edits against a mission)")
    ap.add_argument("--audit-layout", action="store_true",
                    help="Tap the emitted GUI rect stream and report widget "
                         "overflow / overlap (read-only; prints at end of run)")
    ap.add_argument("--aspect", default=None, metavar="WxH",
                    help="Force the client screen size (e.g. 1280x720) so layouts "
                         "build at it — with --audit-layout, sweep sizes to find "
                         "where fixed fonts break the %%-layout")
    ap.add_argument("--dap-port", type=int, default=None, metavar="PORT",
                    help="Serve the MAST source debugger (DAP) on this localhost "
                         "port so VS Code can attach and set breakpoints (dev-only)")
    ap.add_argument("--dap-wait", action="store_true",
                    help="With --dap-port, hold map auto-start until a debugger "
                         "attaches (so early breakpoints aren't missed)")
    ap.add_argument("--probe-leak", type=float, default=None, metavar="SECONDS",
                    help="Every N sim-seconds print a leak sample: sim/wall rate, "
                         "live space objects, Agent.all size, MAST task count and "
                         "how many of those tasks have ENDED (leaked corpses)")
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
        exercise_console=args.exercise_console,
        exercise_dwell=args.exercise_dwell,
        exercise_click=args.exercise_click,
        exercise_click_every=args.exercise_click_every,
        use_working_tree=args.use_working_tree,
        seed=args.seed,
        audit_layout=args.audit_layout,
        aspect=args.aspect,
        dap_port=args.dap_port,
        dap_wait=args.dap_wait,
        probe_leak=args.probe_leak,
    )
    sys.exit(_exit or 0)
