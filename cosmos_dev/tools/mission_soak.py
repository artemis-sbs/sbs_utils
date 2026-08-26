"""Unattended, scenario-driven mission soak (dev-only). Mock leg, engine leg, exit code.

WHAT THIS IS FOR. `mission_runner --soak <name>` runs ONE bounded conformance pass and
returns a verdict. This runs it over and over, unattended, for hours, keeps the evidence
from every iteration, and **exits non-zero when any of them regressed**.

WHY NOT JUST EXTEND `overnight_runner.py`. Because it is a different loop shape and
extending it would serve neither. It launches `mission_runner` WITHOUT `--test`, so the
mission runs in forever-mode and the whole verdict path never executes; its only positive
signal is counting the string "run_next_mission ->" in stdout, it has no seed, it forwards
four flags, and it returns 0 no matter what it saw. It is a liveness babysitter for the
attract loop, which is a real job - just not this one. Its proven parts are reused here.

WHAT IS BORROWED, AND FROM WHERE. Neither source needed rewriting:

  * from `overnight_runner.py` - the reader thread (so the watchdog fires on a SILENT
    child, not only a chatty one), the stall watchdog, `_kill_tree` (`taskkill /F /T`,
    because the mockgui spawns server.py and a surviving grandchild holds the WebSocket
    port and blocks the next launch), and the atomic JSON state file.
  * from `tools/engine_soak.py` - the SHA1 build freeze (a mid-soak rebuild VOIDS the
    report; an arm was once rebuilt twice mid-run and had to be thrown away), the
    crash-dump census, and treating a TIMEOUT as VOID rather than as survival, so a hung
    run cannot be counted as evidence that things are fine.

TWO HONEST LIMITS, STATED HERE SO THE REPORT CANNOT IMPLY OTHERWISE.

  * A mock leg proves mission and library LOGIC. It is not the engine, and the mock says
    so itself.
  * An engine leg is NOT bit-repeatable - real physics runs on its own threads and `seed=`
    only pins the RNG. That is exactly why the pass/fail rule is a ratchet over blessed
    runs rather than a fixed list; see `cosmos_dev/soak_manifest.py`.

USAGE

    python -m cosmos_dev.tools.mission_soak ../LegendaryMissions peacetime --hours 8
    python -m cosmos_dev.tools.mission_soak ../LegendaryMissions peacetime --runs 5
    python -m cosmos_dev.tools.mission_soak ../LegendaryMissions peacetime --engine --runs 12

Exit codes: 0 all iterations passed - 1 at least one regressed or errored - 2 the build
changed mid-soak (results void) - 3 nothing ran.
"""
import argparse
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))     # the folder holding cosmos_dev/
_CHILD_CWD = _REPO_ROOT if os.path.isdir(_REPO_ROOT) else None

# Same PYTHONPATH-deaf bootstrap `overnight_runner` uses: PyRuntime ships a python._pth
# that makes the interpreter ignore PYTHONPATH, so lib paths arrive via COSMOS_DEV_LIBS.
_BOOT = (
    "import sys,os,runpy;"
    "L=os.environ.get('COSMOS_DEV_LIBS','');"
    "sys.path[:0]=[p for p in L.split(os.pathsep) if p];"
    "m=sys.argv[1];sys.argv=[m]+sys.argv[2:];"
    "runpy.run_module(m,run_name='__main__')"
)

# What NOT to carry into the soak copy. `mkdocs`/`__docs__` are large and irrelevant;
# `.git` would make the copy look like a repo and invite a commit into it.
_COPY_SKIP_DIRS = {".git", "__pycache__", "mkdocs", "__docs__", "soaks"}
_COPY_SKIP_EXT = (".log",)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# --- state ------------------------------------------------------------------------

def _load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(path, state):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, path)
    except OSError as e:
        print(f"[soak] WARN could not write state: {e}", flush=True)


# --- build freeze -----------------------------------------------------------------

def _hash_libs(lib_dir):
    """Fingerprint every packaged artifact, so a mid-soak rebuild cannot go unnoticed.

    Straight from engine_soak: a previous arm was rebuilt twice while it ran and its
    numbers had to be discarded. A soak that measured two different builds has measured
    nothing, and it is cheaper to say so than to trust the average.
    """
    out = {}
    if not os.path.isdir(lib_dir):
        return out
    for name in sorted(os.listdir(lib_dir)):
        if not name.endswith((".sbslib", ".mastlib")):
            continue
        h = hashlib.sha1()
        with open(os.path.join(lib_dir, name), "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        out[name] = h.hexdigest()
    return out


def _dumps_dir():
    return os.path.join(os.environ.get("LOCALAPPDATA", ""), "CrashDumps")


def _dumps():
    d = _dumps_dir()
    if not os.path.isdir(d):
        return set()
    return {n for n in os.listdir(d) if n.lower().endswith(".dmp")}


# --- the soak copy ----------------------------------------------------------------

def sync_soak_copy(mission_dir, dest=None, for_engine=False):
    """Materialize `<mission>_soak/` and return its path.

    WHY A COPY AT ALL, and it is two reasons rather than one:

      * `Mast()` opens `mast.runtime.log` with mode "w" IN THE MISSION DIRECTORY, so a
        soak run destroys the log a live engine session is producing. Somebody playing
        the game should not have their evidence deleted by a background test.
      * an engine leg needs the cosmos_dev sbslib declared in `story.json`, and a profile
        CANNOT add one (`PyAddons/sbslibs.py` reads that list at `import script`, before
        profiles are consulted). Nobody wants the dev harness shipped to players.

    The copy must live under the same missions root - the runner refuses to start
    anywhere it cannot find `__lib__/`.
    """
    mission_dir = os.path.abspath(mission_dir)
    if dest is None:
        dest = mission_dir + "_soak"
    os.makedirs(dest, exist_ok=True)

    for root, dirs, files in os.walk(mission_dir):
        dirs[:] = [d for d in dirs if d not in _COPY_SKIP_DIRS]
        rel = os.path.relpath(root, mission_dir)
        target_root = dest if rel == "." else os.path.join(dest, rel)
        os.makedirs(target_root, exist_ok=True)
        for fn in files:
            if fn.endswith(_COPY_SKIP_EXT):
                continue
            src = os.path.join(root, fn)
            dst = os.path.join(target_root, fn)
            # Copy only when it actually changed - a full re-copy of a 30M mission every
            # iteration is minutes of an overnight run spent on nothing.
            try:
                if (os.path.exists(dst)
                        and os.path.getmtime(dst) >= os.path.getmtime(src)
                        and os.path.getsize(dst) == os.path.getsize(src)):
                    continue
            except OSError:
                pass
            shutil.copy2(src, dst)

    # Scenarios are copied wholesale (they are small, and the BASELINE must come along or
    # the ratchet has nothing to compare against).
    src_soaks = os.path.join(mission_dir, "soaks")
    if os.path.isdir(src_soaks):
        dst_soaks = os.path.join(dest, "soaks")
        os.makedirs(dst_soaks, exist_ok=True)
        for fn in os.listdir(src_soaks):
            if fn.endswith((".yaml", ".yml", ".json")):
                shutil.copy2(os.path.join(src_soaks, fn), os.path.join(dst_soaks, fn))

    if for_engine:
        _declare_cosmos_dev(dest)
    return dest


def _declare_cosmos_dev(mission_dir):
    """Add the cosmos_dev sbslib to the COPY's story.json (idempotent).

    The engine loads the harness the same way it loads sbs_utils; `web_demo/story.json`
    is the existing precedent. Matched by prefix rather than exact name so a version bump
    does not silently leave the copy on an old lib.
    """
    sj = os.path.join(mission_dir, "story.json")
    if not os.path.isfile(sj):
        return None
    with open(sj, encoding="utf-8") as f:
        data = json.load(f)
    libs = data.setdefault("sbslib", [])
    if any(".cosmos_dev." in n for n in libs):
        return sj
    name = _find_cosmos_dev_lib(mission_dir)
    if name is None:
        print("[soak] WARN no cosmos_dev sbslib in __lib__ - the engine leg cannot "
              "assert anything without it (build one with `sbs lib`)", flush=True)
        return sj
    libs.append(name)
    with open(sj, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[soak] declared {name} in the soak copy's story.json", flush=True)
    return sj


def _find_cosmos_dev_lib(mission_dir):
    lib = os.path.join(_missions_root(mission_dir), "__lib__")
    if not os.path.isdir(lib):
        return None
    cands = sorted(n for n in os.listdir(lib) if ".cosmos_dev." in n and n.endswith(".sbslib"))
    return cands[-1] if cands else None


def _missions_root(mission_dir):
    """Walk up to the folder that holds `__lib__/` - the runner's own rule."""
    d = os.path.abspath(mission_dir)
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "__lib__")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.abspath(mission_dir))


# --- child process handling -------------------------------------------------------

def _kill_tree(proc):
    """Kill the child AND its grandchildren.

    The mockgui spawns server.py; a survivor holds the WebSocket port and the next launch
    fails for a reason that looks nothing like the real cause.
    """
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


def _reader(stdout, q):
    """Pump child stdout into a queue so the main loop wakes on a TIMER.

    Without this the loop blocks on a silent child and the stall watchdog - the one thing
    that exists for silent children - never fires.
    """
    try:
        for line in stdout:
            q.put(line.rstrip("\n"))
    except Exception:
        pass
    finally:
        q.put(None)


# --- the mock leg -----------------------------------------------------------------

def run_mock(mission, scenario, seed, seconds, artifacts, stall_secs, use_working_tree,
             verbose=False, profile=None, bless=False, home=None):
    """One bounded `mission_runner --soak` pass. Returns (outcome, detail).

    Outcomes: PASS | FAIL | STALL | CRASH. STALL and CRASH are harness events rather than
    mission verdicts and are reported separately, because "the runner wedged" and "the
    mission regressed" want completely different next steps.
    """
    os.makedirs(artifacts, exist_ok=True)
    if os.environ.get("COSMOS_DEV_LIBS"):
        cmd = [sys.executable, "-u", "-c", _BOOT, "cosmos_dev.mission_runner", mission]
    else:
        cmd = [sys.executable, "-u", "-m", "cosmos_dev.mission_runner", mission]
    cmd += ["--soak", scenario,
            "--junit", os.path.join(artifacts, "junit.xml"),
            "--coverage-json", os.path.join(artifacts, "coverage.json")]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    if seconds:
        cmd += ["--test", str(seconds)]
    if profile:
        cmd += ["--profile", profile]
    if bless:
        cmd += ["--soak-bless"]
    if use_working_tree:
        cmd += ["--use-working-tree"]

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(cmd, cwd=_CHILD_CWD, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    q = queue.Queue()
    threading.Thread(target=_reader, args=(proc.stdout, q), daemon=True).start()

    verdict_line = ""
    regressions = []
    last_output = time.time()
    log_path = os.path.join(artifacts, "run.log")
    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write(" ".join(cmd) + "\n\n")
        while True:
            try:
                line = q.get(timeout=2.0)
            except queue.Empty:
                if stall_secs and time.time() - last_output >= stall_secs:
                    _kill_tree(proc)
                    return "STALL", f"no output for {stall_secs / 60:.1f} min"
                continue
            if line is None:
                break                       # EOF: the child exited
            last_output = time.time()
            logf.write(line + "\n")
            if verbose:
                print("   | " + line, flush=True)
            # The LAST word, which this tool added to mission_runner precisely so a
            # supervisor would not have to infer the outcome from a report line that only
            # knows about runtime errors.
            if line.startswith("VERDICT:"):
                verdict_line = line
            elif line.startswith(("PASS - ", "FAIL - ")) and not verdict_line:
                verdict_line = line
            # WHAT regressed, not just that something did. Without this an overnight
            # report says "1 expectation regression(s)" and the reader has to go digging
            # in a per-run artifact to find out which - which is the difference between a
            # report you act on in the morning and one you learn to ignore.
            elif "REGRESSION:" in line:
                regressions.append(line.split("REGRESSION:", 1)[1].strip())
    rc = proc.wait()

    # Keep the mission's own runtime log with the run that produced it - it is truncated
    # on the next compile, so leaving it in place loses it.
    _keep_runtime_log(mission, artifacts)
    if bless and home:
        _return_baseline(mission, home, scenario)

    if rc == 0:
        return "PASS", verdict_line
    if rc == 2:
        return "FAIL", "scenario not found (exit 2)"
    detail = verdict_line or f"exit {rc}"
    if regressions:
        indent = chr(10) + " " * 8
        detail += indent + indent.join(regressions)
    return "FAIL", detail


def _return_baseline(copy_dir, home_dir, scenario):
    """Carry a blessed baseline back from the soak copy to the real mission.

    THE RATCHET IS A COMMITTED ARTIFACT and the run happens in a throwaway copy, so
    without this every bless was written into the copy and lost - and worse, the NEXT
    bless then read a one-run baseline that the real mission did not have, and reported
    ordinary variance as a regression. Blessing twice produced a failure and no file.
    """
    src = os.path.join(copy_dir, "soaks", f"{scenario}.baseline.json")
    if not os.path.isfile(src):
        return
    dst_dir = os.path.join(home_dir, "soaks")
    os.makedirs(dst_dir, exist_ok=True)
    try:
        shutil.copy2(src, os.path.join(dst_dir, f"{scenario}.baseline.json"))
    except OSError as e:
        print(f"[soak] WARN could not return the baseline: {e}", flush=True)


def _keep_runtime_log(mission, artifacts):
    for name in ("mast.runtime.log", "mast.compile.log"):
        src = os.path.join(mission, name)
        try:
            if os.path.isfile(src) and os.path.getsize(src) > 0:
                shutil.copy2(src, os.path.join(artifacts, name))
        except OSError:
            pass


# --- the engine leg ---------------------------------------------------------------

def run_engine(cosmos_dir, mission_name, scenario, map_arg, seed, seconds, artifacts,
               timeout, profile=None):
    """One real-engine pass. Returns (outcome, detail).

    The engine exposes no quit in the pybind surface, so the mission cannot end the
    process - it can only leave evidence in `records/verdict.json`. THIS is what supplies
    the exit code, which is the whole reason a launcher exists.

    Outcomes: PASS | FAIL | SERVER GONE | VOID(timeout).
    """
    os.makedirs(artifacts, exist_ok=True)
    exe = os.path.join(cosmos_dir, "Artemis3-x64-release.exe")
    if not os.path.isfile(exe):
        return "VOID", f"engine not found: {exe}"
    verdict_path = os.path.join(cosmos_dir, "data", "missions", mission_name,
                                "records", "verdict.json")
    try:
        os.remove(verdict_path)
    except OSError:
        pass
    before = _dumps()

    args = [f"defaultmission={mission_name}", f"soak={scenario}", "autostartserver"]
    if map_arg:
        args.append(f"map={map_arg}")
    if profile:
        # `profile=` is an engine argument in its own right, resolved by
        # `procedural/settings.py` from `<mission>/profiles/<name>.yaml`. It is how a
        # scenario picks a whole settings/addon set rather than listing keys - and the
        # mock leg honors the same name via --profile, so both legs stay comparable.
        args.append(f"profile={profile}")
    if seed is not None:
        args.append(f"seed={seed}")
    if seconds:
        args.append(f"test={seconds}")
    proc = subprocess.Popen([exe] + args, cwd=cosmos_dir,
                            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))

    t0 = time.time()
    outcome, detail = "VOID", "timeout"
    while time.time() - t0 < timeout:
        # VERDICT FIRST. A server that writes its verdict and exits in the same second
        # would otherwise be scored as a death purely because of check order - a mistake
        # engine_soak made once and documents.
        if os.path.isfile(verdict_path):
            outcome, detail = _read_engine_verdict(verdict_path, artifacts)
            break
        if proc.poll() is not None:
            rc = proc.returncode
            # THE EXIT CODE IS THE EVIDENCE. 0xC0000005 is an access violation; an MSVC
            # assert that aborts leaves no dump at all, so "no dump" is not "no failure".
            outcome = "SERVER GONE"
            detail = f"t+{time.time() - t0:.0f}s rc={rc} (0x{rc & 0xFFFFFFFF:08X})"
            break
        time.sleep(1)

    try:
        if proc.poll() is None:
            proc.kill()
    except Exception:
        pass
    time.sleep(3)       # the engine holds a fixed port; let the OS release it

    new_dumps = sorted(_dumps() - before)
    if new_dumps:
        detail += f"  dumps: {', '.join(new_dumps)}"
    return outcome, detail


def _read_engine_verdict(path, artifacts):
    try:
        shutil.copy2(path, os.path.join(artifacts, "verdict.json"))
        with open(path, encoding="utf-8") as f:
            v = json.load(f)
    except (OSError, ValueError) as e:
        return "FAIL", f"unreadable verdict: {e}"
    ok = v.get("verdict") == "PASS"
    detail = (f"{v.get('sim_seconds')}s asked {v.get('asked_seconds')} "
              f"errors {v.get('errors')}")
    if v.get("first_error"):
        detail += f" | {v['first_error'][:160]}"
    return ("PASS" if ok else "FAIL"), detail


# --- the loop ---------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mission", help="Mission folder (the REAL one; a soak copy is made)")
    ap.add_argument("scenario", help="Scenario name under <mission>/soaks/")
    ap.add_argument("--hours", type=float, default=None,
                    help="Stop after this many hours")
    ap.add_argument("--runs", type=int, default=None,
                    help="Stop after this many iterations  [default: 1 unless --hours]")
    ap.add_argument("--seed", type=int, default=None,
                    help="Override the scenario seed. Omit to use the scenario's, which "
                         "is what makes a night reproducible")
    ap.add_argument("--vary-seed", action="store_true",
                    help="Use a DIFFERENT seed each iteration (seed+N). Broadens coverage "
                         "at the cost of repeatability - off by default")
    ap.add_argument("--seconds", type=float, default=None,
                    help="Override the scenario duration")
    ap.add_argument("--profile", default=None, metavar="NAME",
                    help="Override the scenario's profile (<mission>/profiles/NAME.yaml). "
                         "Honored by BOTH legs - --profile to the mock, profile= to the "
                         "engine - so the two stay comparable")
    ap.add_argument("--bless", action="store_true",
                    help="Fold each iteration into the scenario's ratchet baseline. The "
                         "baseline demands only what EVERY blessed run reached, so "
                         "blessing more runs relaxes flaky items rather than tightening")
    ap.add_argument("--engine", action="store_true",
                    help="Run the REAL engine instead of the mock (server-only: a second "
                         "local instance makes the engine assert)")
    ap.add_argument("--cosmos-dir", default=os.path.join("E:", os.sep, "a", "Cosmos-dev"),
                    help="Cosmos install root, for --engine")
    ap.add_argument("--timeout", type=float, default=900,
                    help="Wall-clock cap per iteration  [default: 900]")
    ap.add_argument("--stall-minutes", type=float, default=10.0,
                    help="Kill a mock run producing no output for this long (0 disables)")
    ap.add_argument("--artifacts", default=None,
                    help="Where to keep per-run evidence  [default: <mission>/soaks/runs]")
    ap.add_argument("--use-working-tree", action="store_true",
                    help="Run the working-tree sbs_utils rather than the packaged sbslib")
    ap.add_argument("--verbose", action="store_true", help="Mirror child output")
    ap.add_argument("--no-copy", action="store_true",
                    help="Run against the mission folder ITSELF. Only for a throwaway "
                         "mission: it truncates mast.runtime.log in place")
    args = ap.parse_args(argv)

    mission = os.path.abspath(args.mission)
    if not os.path.isdir(mission):
        print(f"[soak] no such mission: {mission}")
        return 3

    # Resolve the scenario from the REAL mission, so a stale copy cannot hide a rename.
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    from cosmos_dev.soak_manifest import load_scenario
    scenario = load_scenario(mission, args.scenario)
    if scenario is None:
        print(f"[soak] no scenario '{args.scenario}' under {mission}/soaks/")
        return 3

    seed0 = args.seed if args.seed is not None else scenario.seed
    seconds = args.seconds if args.seconds is not None else scenario.seconds
    profile = args.profile if args.profile is not None else scenario.profile
    runs = args.runs if args.runs is not None else (None if args.hours else 1)

    target = mission
    if not args.no_copy:
        print(f"[soak] {_now()} syncing soak copy...", flush=True)
        target = sync_soak_copy(mission, for_engine=args.engine)
        print(f"[soak] copy: {target}", flush=True)

    artifacts_root = args.artifacts or os.path.join(mission, "soaks", "runs")
    os.makedirs(artifacts_root, exist_ok=True)
    state_path = os.path.join(artifacts_root, f"{args.scenario}.state.json")
    state = _load_state(state_path)
    for k in ("iterations", "passed", "failed", "void"):
        state.setdefault(k, 0)
    state.setdefault("events", [])

    lib_dir = os.path.join(_missions_root(mission), "__lib__")
    frozen = _hash_libs(lib_dir)

    start = time.time()
    deadline = start + args.hours * 3600 if args.hours else None
    results = []
    n = 0

    print(f"[soak] scenario={args.scenario} map={scenario.map} seed={seed0} "
          f"seconds={seconds} leg={'ENGINE' if args.engine else 'mock'}"
          + (f" profile={profile}" if profile else ""), flush=True)
    if deadline:
        print(f"[soak] until {datetime.fromtimestamp(deadline):%Y-%m-%d %H:%M:%S}", flush=True)
    print(f"[soak] build frozen at {len(frozen)} artifact(s); evidence -> {artifacts_root}",
          flush=True)

    try:
        while True:
            if deadline and time.time() >= deadline:
                break
            if runs is not None and n >= runs:
                break
            n += 1
            seed = None if seed0 is None else (seed0 + n - 1 if args.vary_seed else seed0)
            art = os.path.join(artifacts_root, f"{args.scenario}-{_stamp()}-{n:03d}")
            print(f"[soak] {_now()} iteration {n} (seed {seed}) ...", flush=True)
            t0 = time.time()
            if args.engine:
                outcome, detail = run_engine(
                    args.cosmos_dir, os.path.basename(target), args.scenario,
                    scenario.map, seed, seconds, art, args.timeout, profile)
            else:
                outcome, detail = run_mock(
                    target, args.scenario, seed, seconds, art,
                    args.stall_minutes * 60 if args.stall_minutes > 0 else None,
                    args.use_working_tree, args.verbose, profile, args.bless,
                    home=mission)
            took = time.time() - t0
            results.append((n, outcome, detail, took))
            state["iterations"] += 1
            if outcome == "PASS":
                state["passed"] += 1
            elif outcome == "VOID":
                state["void"] += 1
            else:
                state["failed"] += 1
            state["events"].append({"t": _now(), "n": n, "outcome": outcome,
                                    "detail": detail[:300], "seconds": round(took, 1),
                                    "artifacts": art})
            del state["events"][:-400]
            _save_state(state_path, state)
            print(f"[soak] {_now()} iteration {n}: {outcome} ({took:.0f}s) {detail}",
                  flush=True)
    except KeyboardInterrupt:
        print("\n[soak] interrupted", flush=True)

    return _report(results, frozen, lib_dir, artifacts_root, state_path)


def _report(results, frozen, lib_dir, artifacts_root, state_path):
    print("\n==== soak report ====")
    if not results:
        print("NOTHING RAN")
        return 3
    for n, outcome, detail, took in results:
        print(f"  {n:3d}  {outcome:<12} {took:6.0f}s  {detail}")

    npass = sum(1 for r in results if r[1] == "PASS")
    nvoid = sum(1 for r in results if r[1] == "VOID")
    nfail = len(results) - npass - nvoid
    # VOID runs are excluded from the denominator rather than counted as survival: a run
    # that timed out measured nothing, and letting it read as "fine" is how a soak talks
    # itself into a clean bill of health.
    counted = len(results) - nvoid
    print(f"\n  {npass}/{counted} passed"
          + (f", {nvoid} VOID (not counted)" if nvoid else ""))
    print(f"  evidence: {artifacts_root}")
    print(f"  state:    {state_path}")

    after = _hash_libs(lib_dir)
    if after != frozen:
        changed = sorted((set(frozen) ^ set(after))
                         | {k for k in frozen if k in after and frozen[k] != after[k]})
        print("\n!! THE BUILD CHANGED DURING THIS SOAK - the numbers above are void")
        for c in changed:
            print(f"   {c}")
        print("=====================")
        return 2

    print("=====================")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
