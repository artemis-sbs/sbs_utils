"""
Overnight soak runner for the cosmos_dev mockgui.

Keeps a mission (default LegendaryMissions) cycling under autoplay for hours,
counts completed runs, survives hard crashes by relaunching, and logs progress.
Dev-only tooling - never shipped in the .sbslib.

A "run" = one mission completion. LM's autoplay calls ``sbs.run_next_mission`` when
a mission ends, which the mission_runner logs as ``run_next_mission ->``; this script
counts those lines. Most cycling happens *in-process* (the runner reloads without
restarting), so the child process normally stays up all night - a child exit is
treated as a crash, logged, and the child is relaunched. Counts persist across
relaunches in a JSON state file so the total is cumulative.

Usage (run from the sbs_utils folder, or anywhere - paths are resolved):
    python -m cosmos_dev.overnight_runner ../LegendaryMissions --map 0 --gui
    python -m cosmos_dev.overnight_runner ../LegendaryMissions --map single_front --hours 8
    python -m cosmos_dev.overnight_runner ../LegendaryMissions --max-runs 50 --gui

Open http://localhost:8765/ to watch (with --gui). Ctrl+C stops cleanly and prints a
summary. Requires LM autoplay enabled (LegendaryMissions/settings.yaml already sets
AUTO_PLAY: enable: true).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

# Repo root = the folder containing the cosmos_dev package; used as the child's cwd
# so `-m cosmos_dev.mission_runner` resolves no matter where this is launched from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_RUN_MARKER = "run_next_mission ->"     # mission_runner logs this on every cycle
# mission_runner's _log_exc prints "[runner] <prefix> error: ..." then a traceback;
# surface either to the console (the full trace still lands in the log file).
_CRASH_MARKERS = ("Traceback (most recent call last)", "error: ")


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
                    "relaunch on crash.")
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
    ap.add_argument("--log", default="overnight_run.log",
                    help="Full child output log  [default: overnight_run.log]")
    ap.add_argument("--state", default="overnight_state.json",
                    help="Cumulative run/crash counters (JSON)  [default: overnight_state.json]")
    ap.add_argument("--reset", action="store_true",
                    help="Reset the state file (start counts from zero)")
    ap.add_argument("--verbose", action="store_true",
                    help="Mirror ALL child output to the console (default: only milestones)")
    ap.add_argument("--restart-backoff", type=float, default=5.0,
                    help="Seconds to wait before relaunching after a crash  [default: 5]")
    ap.add_argument("--use-working-tree", action="store_true",
                    help="Pass --use-working-tree to the runner (test local sbs_utils edits)")
    args = ap.parse_args()

    log_path = os.path.abspath(args.log)
    state_path = os.path.abspath(args.state)

    state = {} if args.reset else _load_state(state_path)
    state.setdefault("runs", 0)
    state.setdefault("crashes", 0)
    state.setdefault("process_launches", 0)
    state.setdefault("first_started", _now())
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

    cmd = _build_cmd(args)
    stop = False
    budget_hit = False
    last_heartbeat = time.time()

    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"\n===== overnight soak started {_now()} : {' '.join(cmd)} =====\n")
        logf.flush()

        while not stop:
            if deadline and time.time() >= deadline:
                budget_hit = True
                break
            if args.max_runs and state["runs"] >= args.max_runs:
                budget_hit = True
                break

            state["process_launches"] += 1
            _save_state(state_path, state)
            print(f"[overnight] {_now()} launching runner "
                  f"(process #{state['process_launches']})", flush=True)

            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            proc = subprocess.Popen(
                cmd, cwd=_REPO_ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)

            try:
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    logf.write(line + "\n")
                    logf.flush()
                    if args.verbose:
                        print(line, flush=True)

                    if _RUN_MARKER in line:
                        state["runs"] += 1
                        _save_state(state_path, state)
                        elapsed = timedelta(seconds=int(time.time() - start_t))
                        print(f"[overnight] {_now()} RUN #{state['runs']} complete "
                              f"(elapsed {elapsed}, crashes {state['crashes']})", flush=True)
                    elif any(m in line for m in _CRASH_MARKERS) and not args.verbose:
                        print(f"[overnight] {_now()} ! {line}", flush=True)

                    now = time.time()
                    if now - last_heartbeat >= 600:        # 10-min alive heartbeat
                        last_heartbeat = now
                        elapsed = timedelta(seconds=int(now - start_t))
                        print(f"[overnight] {_now()} alive - runs {state['runs']}, "
                              f"crashes {state['crashes']}, elapsed {elapsed}", flush=True)

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

            # Child exited on its own while we still had budget => crash/unexpected.
            state["crashes"] += 1
            _save_state(state_path, state)
            print(f"[overnight] {_now()} runner exited unexpectedly "
                  f"(crash #{state['crashes']}); relaunching in {args.restart_backoff}s",
                  flush=True)
            try:
                time.sleep(args.restart_backoff)
            except KeyboardInterrupt:
                stop = True
                break

    state["last_stopped"] = _now()
    _save_state(state_path, state)
    total = timedelta(seconds=int(time.time() - start_t))
    print("\n[overnight] ===== summary =====", flush=True)
    print(f"[overnight] runs completed this session counter total: {state['runs']}", flush=True)
    print(f"[overnight] crashes/relaunches: {state['crashes']}  "
          f"process launches: {state['process_launches']}", flush=True)
    print(f"[overnight] wall-clock this session: {total}", flush=True)
    print(f"[overnight] state: {state_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
