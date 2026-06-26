"""
Overnight soak runner for the cosmos_dev mockgui.

Keeps a mission (default LegendaryMissions) cycling under autoplay for hours,
counts completed runs, and - crucially for debugging - records WHY things went
wrong. Dev-only tooling, never shipped in the .sbslib.

What it tracks (persisted to a JSON state file, cumulative across relaunches):
  - runs     : mission completions (the runner logs "run_next_mission ->" per cycle)
  - errors   : in-process exceptions the runner caught and kept going past
               (its _log_exc prints "[runner] ... error:" + a traceback) - these do
               NOT exit the process, so they were previously invisible in the state
  - stalls   : the child went silent for --stall-minutes (wedged) and was relaunched
  - crashes  : the child process exited unexpectedly while we still had budget
  - events   : a timestamped ring buffer of the above, so the morning state file
               matches what scrolled past in the terminal

Robustness: a reader thread feeds output to the main loop, so heartbeats, the stall
watchdog, and budget checks fire on a timer even when the child produces nothing.
On a stall or crash the child's whole process tree is killed (freeing the mockgui
WebSocket port) and relaunched after a backoff.

Usage (run from the sbs_utils folder, or anywhere - paths are resolved):
    python -m cosmos_dev.overnight_runner ../LegendaryMissions --map 0 --gui
    python -m cosmos_dev.overnight_runner ../LegendaryMissions --map single_front --hours 8
    python -m cosmos_dev.overnight_runner ../LegendaryMissions --max-runs 50 --gui

Open http://localhost:8765/ to watch (with --gui). Ctrl+C stops cleanly and prints a
summary. Requires LM autoplay enabled (LegendaryMissions/settings.yaml sets it).
"""
import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

# Repo root = the folder containing the cosmos_dev package; used as the child's cwd
# so `-m cosmos_dev.mission_runner` resolves no matter where this is launched from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_RUN_MARKER = "run_next_mission ->"     # mission_runner logs this on every cycle
# mission_runner's _log_exc prints "[runner] <prefix> error: ..." then a traceback;
# either signals an in-process exception that was caught (process kept running).
_ERROR_MARKERS = ("Traceback (most recent call last)", "error: ")
_EVENTS_CAP = 400                       # ring-buffer size for the events list
_NO_LINE = object()                     # sentinel: reader produced nothing this interval


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_state(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(path: str, state: dict) -> None:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[overnight] WARN could not write state: {e}", flush=True)


def _event(state: dict, kind: str, detail: str = "") -> None:
    evs = state.setdefault("events", [])
    evs.append({"t": _now(), "kind": kind, "detail": detail[:300]})
    if len(evs) > _EVENTS_CAP:
        del evs[:-_EVENTS_CAP]


def _kill_tree(proc: "subprocess.Popen") -> None:
    """Kill the child AND its grandchildren (the mockgui spawns server.py, which
    otherwise lingers holding the WebSocket port and blocks the next relaunch)."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _reader(stdout, q: "queue.Queue") -> None:
    """Pump child stdout into a queue so the main loop can wake on a timer (for
    heartbeats / stall detection) instead of blocking on a silent child."""
    try:
        for line in stdout:
            q.put(line.rstrip("\n"))
    except Exception:
        pass
    finally:
        q.put(None)     # EOF sentinel -> child exited


def _build_cmd(args) -> list:
    cmd = [sys.executable, "-u", "-m", "cosmos_dev.mission_runner", args.mission]
    if args.map is not None:
        cmd += ["--map", str(args.map)]
    if args.gui:
        cmd += ["--gui", "--port", str(args.port)]
    if args.use_working_tree:
        cmd += ["--use-working-tree"]
    return cmd


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Overnight soak runner: cycle a mission under autoplay, count runs, "
                    "record errors/stalls/crashes, relaunch on failure.")
    ap.add_argument("mission", nargs="?", default="../LegendaryMissions",
                    help="Mission folder  [default: ../LegendaryMissions]")
    ap.add_argument("--map", default="0",
                    help="Map index or name to auto-start  [default: 0]")
    ap.add_argument("--gui", action="store_true",
                    help="Start the WebSocket GUI (watch at http://localhost:8765/)")
    ap.add_argument("--port", type=int, default=8765, help="GUI port  [default: 8765]")
    ap.add_argument("--hours", type=float, default=None,
                    help="Stop after this many hours  [default: run until Ctrl+C]")
    ap.add_argument("--max-runs", type=int, default=None,
                    help="Stop after this many completed runs")
    ap.add_argument("--stall-minutes", type=float, default=5.0,
                    help="Relaunch if the child produces no output for this long "
                         "(0 disables the watchdog)  [default: 5]")
    ap.add_argument("--heartbeat-minutes", type=float, default=10.0,
                    help="Console 'alive' line interval  [default: 10]")
    ap.add_argument("--log", default="overnight_run.log",
                    help="Full child output log  [default: overnight_run.log]")
    ap.add_argument("--state", default="overnight_state.json",
                    help="Cumulative counters + event log (JSON)  [default: overnight_state.json]")
    ap.add_argument("--reset", action="store_true",
                    help="Reset the state file (start counts from zero)")
    ap.add_argument("--verbose", action="store_true",
                    help="Mirror ALL child output to the console (default: milestones only)")
    ap.add_argument("--restart-backoff", type=float, default=5.0,
                    help="Seconds to wait before relaunching after a stall/crash  [default: 5]")
    ap.add_argument("--use-working-tree", action="store_true",
                    help="Pass --use-working-tree to the runner (test local sbs_utils edits)")
    args = ap.parse_args()

    log_path = os.path.abspath(args.log)
    state_path = os.path.abspath(args.state)
    stall_secs = args.stall_minutes * 60 if args.stall_minutes > 0 else None
    heartbeat_secs = args.heartbeat_minutes * 60

    state = {} if args.reset else _load_state(state_path)
    for k in ("runs", "errors", "stalls", "crashes", "process_launches"):
        state.setdefault(k, 0)
    state.setdefault("first_started", _now())
    state.setdefault("events", [])
    state["mission"] = args.mission
    state["map"] = args.map

    start_t = time.time()
    deadline = start_t + args.hours * 3600 if args.hours else None

    print(f"[overnight] {_now()} starting soak: mission={args.mission} map={args.map} "
          f"gui={args.gui}", flush=True)
    print(f"[overnight] runs so far: {state['runs']}  log: {log_path}  state: {state_path}",
          flush=True)
    if deadline:
        print(f"[overnight] will stop at {datetime.fromtimestamp(deadline):%Y-%m-%d %H:%M:%S} "
              f"({args.hours}h)", flush=True)
    if args.max_runs:
        print(f"[overnight] will stop after {args.max_runs} runs", flush=True)
    if stall_secs:
        print(f"[overnight] stall watchdog: relaunch after {args.stall_minutes:g} min of silence",
              flush=True)

    cmd = _build_cmd(args)
    stop = False
    budget_hit = False
    last_heartbeat = time.time()

    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"\n===== overnight soak started {_now()} : {' '.join(cmd)} =====\n")
        logf.flush()

        while not stop and not budget_hit:
            if deadline and time.time() >= deadline:
                break
            if args.max_runs and state["runs"] >= args.max_runs:
                break

            state["process_launches"] += 1
            _event(state, "launch", f"process #{state['process_launches']}")
            _save_state(state_path, state)
            print(f"[overnight] {_now()} launching runner "
                  f"(process #{state['process_launches']})", flush=True)

            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            proc = subprocess.Popen(
                cmd, cwd=_REPO_ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)

            q: "queue.Queue" = queue.Queue()
            reader = threading.Thread(target=_reader, args=(proc.stdout, q), daemon=True)
            reader.start()

            reason = None           # "crash" | "stall" | None(=budget/stop)
            last_output = time.time()
            try:
                while True:
                    try:
                        line = q.get(timeout=2.0)
                    except queue.Empty:
                        line = _NO_LINE

                    if line is None:                 # reader EOF -> child exited
                        reason = "crash"
                        break

                    if line is not _NO_LINE:
                        last_output = time.time()
                        logf.write(line + "\n")
                        logf.flush()
                        if args.verbose:
                            print(line, flush=True)

                        if _RUN_MARKER in line:
                            state["runs"] += 1
                            _event(state, "run", line)
                            _save_state(state_path, state)
                            elapsed = timedelta(seconds=int(time.time() - start_t))
                            print(f"[overnight] {_now()} RUN #{state['runs']} complete "
                                  f"(elapsed {elapsed}, errors {state['errors']}, "
                                  f"stalls {state['stalls']}, crashes {state['crashes']})",
                                  flush=True)
                        elif any(m in line for m in _ERROR_MARKERS):
                            # In-process exception the runner caught (process kept going).
                            # Count only the prefix line, not every traceback frame.
                            if "Traceback (most recent call last)" in line or "[runner]" in line:
                                state["errors"] += 1
                                _event(state, "error", line)
                                _save_state(state_path, state)
                            if not args.verbose:
                                print(f"[overnight] {_now()} ! {line}", flush=True)

                    now = time.time()
                    if now - last_heartbeat >= heartbeat_secs:
                        last_heartbeat = now
                        elapsed = timedelta(seconds=int(now - start_t))
                        print(f"[overnight] {_now()} alive - runs {state['runs']}, "
                              f"errors {state['errors']}, stalls {state['stalls']}, "
                              f"crashes {state['crashes']}, elapsed {elapsed}", flush=True)
                    if stall_secs and (now - last_output) >= stall_secs:
                        reason = "stall"
                        break
                    if deadline and now >= deadline:
                        budget_hit = True
                        break
                    if args.max_runs and state["runs"] >= args.max_runs:
                        budget_hit = True
                        break
            except KeyboardInterrupt:
                print(f"\n[overnight] {_now()} Ctrl+C - stopping", flush=True)
                stop = True
            finally:
                _kill_tree(proc)

            if stop or budget_hit:
                break

            if reason == "stall":
                state["stalls"] += 1
                silent = timedelta(seconds=int(time.time() - last_output))
                _event(state, "stall", f"no output for ~{silent}")
                _save_state(state_path, state)
                print(f"[overnight] {_now()} STALL - no output for ~{silent} "
                      f"(stall #{state['stalls']}); relaunching in {args.restart_backoff}s",
                      flush=True)
            else:                                    # reason == "crash"
                state["crashes"] += 1
                _event(state, "crash", f"child exit code {proc.poll()}")
                _save_state(state_path, state)
                print(f"[overnight] {_now()} runner exited unexpectedly "
                      f"(crash #{state['crashes']}, exit {proc.poll()}); "
                      f"relaunching in {args.restart_backoff}s", flush=True)
            try:
                time.sleep(args.restart_backoff)
            except KeyboardInterrupt:
                stop = True

    state["last_stopped"] = _now()
    _save_state(state_path, state)
    total = timedelta(seconds=int(time.time() - start_t))
    print("\n[overnight] ===== summary =====", flush=True)
    print(f"[overnight] runs: {state['runs']}   errors: {state['errors']}   "
          f"stalls: {state['stalls']}   crashes: {state['crashes']}", flush=True)
    print(f"[overnight] process launches: {state['process_launches']}   "
          f"wall-clock this session: {total}", flush=True)
    print(f"[overnight] full log: {log_path}", flush=True)
    print(f"[overnight] state + event log: {state_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
