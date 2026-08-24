"""Unattended engine soak: does the ObjectDataBlob server crash still happen?

WHAT THIS IS FOR. A server has been dying within ~15s of a console connecting, in
`ObjectDataBlob::Set` under `Simulation::Tick` - a use-after-free. Measured at ~15% of runs,
7 crashes in 48. Four hand-run arms changed nothing. Several things have changed since, and
the crash appears gone - but "appears gone" is worth very little at that rate.

**Arm D read 0/12 and then 4/12 on its confirmation run.** At 15%, twelve clean runs happen
by luck about 11% of the time. That is the entire reason this script exists rather than a
person watching a few games.

WHAT IT DRIVES. `profiles/soak.yaml` + the `soak/` addon churn the pre-start window - the
Player Ships slider, helm changing the ship type, a crew renaming their ship - while this
script connects clients at staggered times. Do NOT pass `map=`: it sets AUTO_START and skips
the whole window (the profile picks the map via WORLD_SELECT instead).

TWO GUARDS, BOTH FROM MISTAKES MADE BY HAND:

  * **The build is frozen.** Every `__lib__` artifact is hashed at the start and re-checked
    at the end; a changed one voids the report. A previous arm was rebuilt twice mid-run and
    its 1/24 had to be thrown away.
  * **No verdict from one arm.** Results print as crashes/runs with a plain statement of what
    that can and cannot support.

USAGE

    python -m cosmos_dev.tools.engine_soak --runs 24 --cells early
    python -m cosmos_dev.tools.engine_soak --runs 24 --label control --libs soak_libs/control

`--libs` swaps a prepared `__lib__` set in before running, which is how the A/B against a
pre-fix build is done. Preparing those sets is a manual step - see the plan file - because it
means a git checkout in a working tree shared with other sessions.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

COSMOS = r"E:\a\Cosmos-dev"
EXE = os.path.join(COSMOS, "Artemis3-x64-release.exe")
MISSIONS = os.path.join(COSMOS, "data", "missions")
LIB = os.path.join(MISSIONS, "__lib__")
MISSION = "LegendaryMissions"
VERDICT = os.path.join(MISSIONS, MISSION, "records", "verdict.json")
DUMPS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "CrashDumps")

# Client connect offsets, in seconds after the server starts. The soak's churn window is 45s
# (profiles/soak.yaml), so every one of these lands INSIDE it - which is the point.
CELLS = {
    "early":     [2],              # where every crash so far has landed
    "mid":       [20],
    "staggered": [2, 15, 40],
    "none":      [],               # control: no client at all. Server-only never crashed.
}


def _hash_libs():
    """Fingerprint every packaged artifact, so a mid-soak rebuild cannot go unnoticed."""
    out = {}
    if not os.path.isdir(LIB):
        return out
    for name in sorted(os.listdir(LIB)):
        if not name.endswith((".sbslib", ".mastlib")):
            continue
        h = hashlib.sha1()
        with open(os.path.join(LIB, name), "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        out[name] = h.hexdigest()
    return out


def _dumps():
    if not os.path.isdir(DUMPS):
        return set()
    return {n for n in os.listdir(DUMPS) if n.lower().endswith(".dmp")}


def _launch(args):
    return subprocess.Popen([EXE] + args, cwd=COSMOS,
                            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def _alive(p):
    return p is not None and p.poll() is None


def _kill_all(procs):
    for p in procs:
        try:
            if _alive(p):
                p.kill()
        except Exception:
            pass
    # The engine can take a moment to release its port; a run that starts while the previous
    # server is still listening is not the run you think you are measuring.
    time.sleep(3)


def run_once(seconds, offsets, seed, timeout):
    """One run. Returns (outcome, detail, new_dumps)."""
    try:
        os.remove(VERDICT)
    except OSError:
        pass
    before = _dumps()

    server = _launch(["autostartserver", f"defaultmission={MISSION}",
                      "profile=soak", f"test={seconds}", f"seed={seed}"])
    procs = [server]
    pending = sorted(offsets)
    t0 = time.time()
    outcome, detail = "TIMEOUT", ""

    while time.time() - t0 < timeout:
        now = time.time() - t0
        while pending and now >= pending[0]:
            pending.pop(0)
            procs.append(_launch(["autostartclient", "clientautoconnectip=127.0.0.1"]))

        if not _alive(server):
            outcome, detail = "SERVER DIED", f"t+{now:.0f}s"
            break
        dead_clients = [i for i, p in enumerate(procs[1:], 1) if not _alive(p)]
        if dead_clients:
            outcome, detail = "CLIENT DIED", f"t+{now:.0f}s client#{dead_clients[0]}"
            break
        if os.path.isfile(VERDICT):
            outcome, detail = "SURVIVED", f"t+{now:.0f}s"
            break
        time.sleep(1)

    _kill_all(procs)
    return outcome, detail, sorted(_dumps() - before)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=12, help="runs per cell")
    ap.add_argument("--cells", default="early",
                    help="comma list: " + ",".join(CELLS) + ", or 'all'")
    ap.add_argument("--seconds", type=int, default=30,
                    help="test= POST-START sim-seconds. The churn window (45s) happens "
                         "before this, so a run is roughly 45s + art load + this. Measured: "
                         "seconds=60 took 186s wall, which starved a 200s timeout.")
    ap.add_argument("--timeout", type=int, default=300, help="wall-clock cap per run")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--label", default="head", help="arm name, for the report")
    ap.add_argument("--libs", default=None,
                    help="directory of prepared __lib__ artifacts to copy in first")
    args = ap.parse_args()

    if not os.path.isfile(EXE):
        sys.exit(f"engine not found: {EXE}")

    if args.libs:
        src = os.path.abspath(args.libs)
        n = 0
        for name in os.listdir(src):
            if name.endswith((".sbslib", ".mastlib")):
                shutil.copy2(os.path.join(src, name), os.path.join(LIB, name))
                n += 1
        print(f"[soak] swapped in {n} artifact(s) from {src}")

    cells = list(CELLS) if args.cells == "all" else [c.strip() for c in args.cells.split(",")]
    for c in cells:
        if c not in CELLS:
            sys.exit(f"unknown cell {c!r}; known: {', '.join(CELLS)}")

    frozen = _hash_libs()
    print(f"[soak] arm '{args.label}', build frozen at {len(frozen)} artifact(s)")
    print(f"[soak] cells: {', '.join(cells)}   runs/cell: {args.runs}")

    results = {}
    for cell in cells:
        offsets = CELLS[cell]
        crashes, client_crashes, timeouts, dumps = 0, 0, 0, []
        print(f"\n=== cell '{cell}' - client(s) at {offsets or 'none'} ===")
        for i in range(1, args.runs + 1):
            outcome, detail, new = run_once(args.seconds, offsets, args.seed, args.timeout)
            if outcome == "SERVER DIED":
                crashes += 1
            elif outcome == "CLIENT DIED":
                client_crashes += 1
            elif outcome == "TIMEOUT":
                timeouts += 1
            dumps += new
            mark = "  <<<" if outcome.endswith("DIED") else ""
            print(f"  {cell} {i:>3}/{args.runs}: {outcome} {detail}{mark}", flush=True)
        results[cell] = (crashes, client_crashes, timeouts, args.runs, dumps)

    print(f"\n================ arm '{args.label}' ================")
    voided = 0
    for cell, (crashes, client_crashes, timeouts, runs, dumps) in results.items():
        pct = 100.0 * crashes / runs if runs else 0.0
        extra = f"   TIMEOUT {timeouts}/{runs}" if timeouts else ""
        print(f"  {cell:<10} server {crashes}/{runs} ({pct:.0f}%)   client {client_crashes}/{runs}{extra}")
        voided += timeouts
        for d in dumps:
            print(f"      dump: {d}")
    if voided:
        # A timed-out run measured nothing. Counting it as a survival would quietly bias
        # every result toward "fixed", which is the direction it is easiest to want.
        print("")
        print(f"  {voided} run(s) TIMED OUT and prove nothing either way - raise --timeout")
        print("  or lower --seconds, and treat the totals below as that many runs short.")

    after = _hash_libs()
    if after != frozen:
        changed = sorted(set(frozen) ^ set(after)) or \
                  sorted(k for k in frozen if frozen[k] != after.get(k))
        print("\n!! THE BUILD CHANGED DURING THIS SOAK - the numbers above are void.")
        print("   changed: " + ", ".join(changed))
        sys.exit(2)

    total_runs = sum(r for _, _, _, r, _ in results.values()) - voided
    total_crashes = sum(c for c, _, _, _, _ in results.values())
    print(f"\n  totals: {total_crashes} server crash(es) in {total_runs} run(s)")
    if total_crashes == 0:
        print("  NOT a verdict on its own. Against a ~15% base rate, zero crashes in")
        print(f"  {total_runs} runs has a chance of about {0.85 ** total_runs:.1%} of happening")
        print("  even if nothing was fixed. Compare against a control arm before concluding.")
    print("  build unchanged throughout.")


if __name__ == "__main__":
    main()
