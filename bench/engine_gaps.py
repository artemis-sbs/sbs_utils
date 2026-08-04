"""What does the ENGINE do while our Python is not running?

We already know what our side costs: a top-tab click builds and emits a whole
console in ~2.8ms, inside the click's own event (bench/probe: mock). What that
cannot show is the engine's half -- and "consoles are slow to appear, widget-less
tabs are instant" points there.

So measure the GAPS. The wall-clock time between one Gui.present returning and
the next one starting is time the engine spent not-us. Sample that distribution
while a client sits on a widget-less screen, then while it sits on a console, and
the difference is what having widgets costs, in milliseconds, in the real engine.

    widget-less baseline   vs   console with N widgets
      -> every gap larger while widgets are up     = steady-state render cost
      -> one fat gap just after the widget list    = one-time construction

Both are the engine's side of the line, but they are different bugs with
different owners, and this is what tells them apart.

NOTHING IS SHIPPED. The tap is injected into the live process through the
cosmos_devqueue channel and dies with it -- there is no instrumentation in the
library to remember to remove. (The engine forks a fresh process per mission, so
a mission change drops the tap; re-run with --install.)

The engine loads PACKAGED libs from data/missions/__lib__, so rebuild the sbslib
(`sbs.pyz lib sbs_utils`) before measuring working-tree changes.

USAGE -- the engine must already be up with a devqueue-enabled mission loaded
(Start Server / Start Mission / connect a client are still manual clicks):

    # once per engine session
    python -m bench.engine_gaps --install

    # park the client on a widget-less tab (library), then:
    python -m bench.engine_gaps --phase library --seconds 15

    # switch the client to helm, then:
    python -m bench.engine_gaps --phase helm --seconds 15

    # compare everything captured so far
    python -m bench.engine_gaps --report

Each phase records the widget list that client actually has, so a row is labelled
with its own widget count rather than with whatever we believed was on screen.

NOTE the handler's own ">33ms Elapsed time" spike report is print()ed, and engine
print output does not reach any log file (debug.log has none of it). So it cannot
be read after the fact -- which is why the tap times our frames itself, and why
"ours med/p90/max" in the report is the answer to "are OUR frames slow?".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

DEFAULT_COSMOS = r"f:/a/Cosmos-1-3-0"
DEFAULT_MISSION = "LegendaryMissions"
DEFAULT_OUT = os.path.join(_REPO_ROOT, "bench", "engine_gaps.json")


# --- code that runs INSIDE the engine ---------------------------------------
#
# Kept as plain strings: it crosses the queue as source and is exec'd there, so
# it can only use what the engine already has.

INSTALL = """
import builtins, time
from sbs_utils.gui import Gui
S = getattr(builtins, "_COSMOS_GAP", None)
if S is not None:
    # Put the original back before re-wrapping, so re-installing an updated tap
    # cannot stack wrappers on top of each other.
    Gui.present = staticmethod(S["orig"])
    orig = S["orig"]
else:
    orig = Gui.present

# cap: a long session must not grow an unbounded list inside the engine
S = {"last": None, "gaps": [], "inside": [], "big": [], "t0": None,
     "cap": 50000, "big_ms": 100.0, "orig": orig}
builtins._COSMOS_GAP = S


def tapped(event):
    t = time.perf_counter()
    if S["t0"] is None:
        S["t0"] = t
    if S["last"] is not None and len(S["gaps"]) < S["cap"]:
        gap = (t - S["last"]) * 1000.0
        S["gaps"].append(gap)
        # A big gap is only actionable if we know WHEN it happened and what came
        # out of it -- a bare max cannot be told apart from the 5Hz tick period.
        if gap >= S["big_ms"] and len(S["big"]) < 400:
            S["big"].append([round(gap, 1), round(t - S["t0"], 2),
                             str(getattr(event, "tag", "?"))])
    try:
        return S["orig"](event)
    finally:
        t1 = time.perf_counter()
        if len(S["inside"]) < S["cap"]:
            S["inside"].append((t1 - t) * 1000.0)
        S["last"] = t1

Gui.present = staticmethod(tapped)

# How often does a page do a FULL repaint (clear + re-emit everything) versus
# just sitting there? A console sees far more engine events than a widget-less
# screen, and if those events drive rebuilds, the re-emitting is OURS, not the
# engine's. Counting the branch StoryPage.present actually takes is the only way
# to tell "the engine is busy" from "we are repainting 20x a second".
from sbs_utils.mast_sbs.maststorypage import StoryPage
P = getattr(builtins, "_COSMOS_PAINT", None)
if P is not None:
    StoryPage.present = P["orig"]
P = {"repaint": 0, "refresh": 0, "idle": 0, "orig": StoryPage.present}
builtins._COSMOS_PAINT = P


def painted(self, event):
    state = getattr(self, "gui_state", None)
    if state == "repaint":
        P["repaint"] += 1
    elif state == "refresh":
        P["refresh"] += 1
    else:
        P["idle"] += 1
    return P["orig"](self, event)


StoryPage.present = painted
_result = "installed"
"""

RESET = """
import builtins
S = builtins._COSMOS_GAP
S["gaps"].clear(); S["inside"].clear(); S["big"].clear()
S["last"] = None; S["t0"] = None
P = getattr(builtins, "_COSMOS_PAINT", None)
if P is not None:
    P["repaint"] = P["refresh"] = P["idle"] = 0
_result = "reset"
"""

STATS = """
import builtins
from sbs_utils.gui import Gui
S = builtins._COSMOS_GAP
g = sorted(S["gaps"]); i = sorted(S["inside"])

def pct(a, p):
    if not a:
        return None
    k = int(len(a) * p)
    return round(a[min(k, len(a) - 1)], 2)

# Label the row with the widget list the client ACTUALLY has, rather than with
# whatever we assumed was on screen. Needs the send-only-when-changed memo.
wl = {}
for cid, pair in getattr(Gui, "widget_list_sent", {}).items():
    if cid:
        wl[str(cid)] = [pair[0], len(pair[1].split("^")) if pair[1] else 0]

# mission_tick arrives at 5Hz, so ~200ms between our frames is the CADENCE, not
# a stall. Count those separately or the tick clock reads as engine slowness.
tick_ish = len([x for x in g if 150.0 <= x <= 260.0])
over = len([x for x in g if x > 260.0])

P = getattr(builtins, "_COSMOS_PAINT", None) or {}

_result = {
    "samples": len(g),
    "gap_med": pct(g, 0.5), "gap_p90": pct(g, 0.9),
    "gap_max": round(g[-1], 2) if g else None,
    "in_med": pct(i, 0.5), "in_p90": pct(i, 0.9),
    "in_max": round(i[-1], 2) if i else None,
    "tick_ish": tick_ish, "over_tick": over,
    "repaints": P.get("repaint"), "refreshes": P.get("refresh"),
    "big": sorted(S["big"], key=lambda b: -b[0])[:12],
    "widget_lists": wl,
}
"""

REROUTE = """
from sbs_utils.gui import Gui
from sbs_utils.procedural.gui.navigation import gui_reroute_client
sent = []
for cid in list(Gui.clients.keys()):
    if cid:
        gui_reroute_client(cid, {label!r})
        sent.append(str(cid))
_result = sent
"""


def _driver(args):
    from cosmos_dev.engine_driver import EngineDriver
    drv = EngineDriver(cosmos_dir=args.cosmos_dir, mission=args.mission)
    if not drv.is_running():
        # Attach to an engine someone else started: send() only needs the queue
        # files, but is_running() guards on our own child process, so give it one.
        class _Attached:
            def poll(self):
                return None
        drv.proc = _Attached()
    return drv


def _preflight(drv):
    """Say WHY the queue is silent, instead of timing out with a guess.

    Three things have to be true, and a plain TimeoutError cannot tell you which
    one is missing -- the consumer is deliberately inert otherwise, so silence is
    its normal state, not a fault.
    """
    problems = []
    lib = os.path.join(drv.missions_dir, "__lib__", "cosmos_devqueue.mastlib")
    if not os.path.isfile(lib):
        problems.append(
            "the queue mastlib is not built\n"
            "      fix: python -c \"from cosmos_dev.engine_driver import EngineDriver;"
            " EngineDriver(r'%s','%s').build_mastlib()\""
            % (drv.cosmos_dir, drv.mission))

    sj = os.path.join(drv.mission_dir, "story.json")
    try:
        with open(sj) as f:
            libs = json.load(f).get("mastlib", [])
        if "cosmos_devqueue.mastlib" not in libs:
            problems.append(f"cosmos_devqueue.mastlib is not in {sj}")
    except OSError:
        problems.append(f"cannot read {sj}")

    marker = os.path.join(drv.mission_dir, "dev_queue.enable")
    env_on = os.environ.get("COSMOS_DEV_QUEUE", "") not in ("", "0", "false", "False")
    if not os.path.isfile(marker) and not env_on:
        problems.append(
            f"the queue is not enabled\n      fix: create {marker} (empty file), "
            "or launch the engine with COSMOS_DEV_QUEUE=1")
    return problems


def _rows(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(path, rows):
    with open(path, "w") as f:
        json.dump(rows, f, indent=2)


def _report(rows):
    if not rows:
        print("no phases captured yet")
        return
    print()
    print("=" * 78)
    print("ENGINE GAPS  --  time between our frames (ms)")
    print("=" * 78)
    print(f"  {'phase':<14}{'widgets':>8}{'n':>6}{'gap med':>9}{'~tick':>7}"
          f"{'>tick':>7}{'gap max':>10}{'ours med':>10}{'repaint/s':>11}")
    for r in rows:
        w = r.get("widgets")
        rp = r.get("repaints")
        rps = "-" if rp is None else f"{rp / max(1e-9, r.get('seconds', 1)):.1f}"
        print(f"  {r['phase']:<14}{('-' if w is None else w):>8}{r['samples']:>6}"
              f"{r['gap_med'] or 0:>9.2f}{r.get('tick_ish', 0):>7}"
              f"{r.get('over_tick', 0):>7}{r['gap_max'] or 0:>10.2f}"
              f"{r['in_med'] or 0:>10.2f}{rps:>11}")
    print("-" * 78)
    print("  gap med  = typical time between our frames")
    print("  ~tick    = gaps of 150-260ms. mission_tick is 5Hz, so these are the")
    print("             CADENCE, not stalls. Ignore them.")
    print("  >tick    = gaps LONGER than a tick period. THIS is the count that")
    print("             matters -- each one is the engine busy past its own clock.")
    print("  ours med = time inside Gui.present. Our cost, for context.")
    print("  repaint/s= FULL page repaints per second (clear + re-emit the lot).")
    print("             A console sees far more engine events than a plain screen;")
    print("             if this is high there, the re-emitting is OURS, not the")
    print("             engine's. It should be ~0 on a screen sitting still.")
    for r in rows:
        big = r.get("big") or []
        if not big:
            continue
        print()
        print(f"  {r['phase']}: longest holes (ms, seconds-into-phase, next event)")
        for gap, at, tag in big[:6]:
            print(f"      {gap:>8.1f}ms   at t+{at:>6.2f}s   -> {tag}")
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cosmos-dir", default=DEFAULT_COSMOS)
    ap.add_argument("--mission", default=DEFAULT_MISSION)
    ap.add_argument("--install", action="store_true",
                    help="inject the tap (once per engine session)")
    ap.add_argument("--phase", help="capture a phase under this name")
    ap.add_argument("--seconds", type=float, default=15.0,
                    help="how long to sample (default 15)")
    ap.add_argument("--reroute", metavar="LABEL",
                    help="send every client to LABEL first (else switch by hand)")
    ap.add_argument("--report", action="store_true", help="print what was captured")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--reset", action="store_true", help="drop captured phases")
    args = ap.parse_args()

    if args.reset:
        _save(args.out, [])
        print(f"cleared {args.out}")
        return 0

    if args.report and not args.phase:
        _report(_rows(args.out))
        return 0

    drv = _driver(args)

    if args.install:
        try:
            alive = drv.ping(timeout=20)
        except TimeoutError:
            alive = False
        if not alive:
            print("the dev queue did not answer.")
            problems = _preflight(drv)
            if problems:
                for p in problems:
                    print(f"  ! {p}")
            else:
                # Everything on disk is right, so the RUNNING mission predates it.
                print("  ! setup on disk looks correct, so the loaded mission is")
                print("    older than it. story.json and the enable marker are read")
                print("    when the mission STARTS - back out to the mission list")
                print("    and start it again, then re-run --install.")
            return 1
        resp = drv.send(INSTALL)
        print(f"tap: {resp.get('result')}")
        if not args.phase:
            return 0

    if not args.phase:
        ap.error("nothing to do: pass --install, --phase or --report")

    if args.reroute:
        resp = drv.send(REROUTE.format(label=args.reroute))
        print(f"rerouted clients: {resp.get('result')}")
        time.sleep(1.0)      # let the new screen settle before sampling

    drv.send(RESET)
    print(f"sampling '{args.phase}' for {args.seconds}s ...")
    time.sleep(args.seconds)
    resp = drv.send(STATS)
    if not resp.get("ok"):
        raise SystemExit(f"stats failed: {resp.get('error')}")
    stats = resp["result"]

    # Widget count for the row: the busiest client, since that is the one whose
    # console we are actually asking about.
    widgets = None
    for _cid, (_console, n) in (stats.get("widget_lists") or {}).items():
        widgets = n if widgets is None else max(widgets, n)

    row = {"phase": args.phase, "widgets": widgets,
           "seconds": args.seconds, **{k: v for k, v in stats.items()
                                       if k != "widget_lists"}}
    if row.get("over_tick") and not row.get("big"):
        print("  note: gaps over a tick period were seen but not captured -- the "
              "tap predates --install of this version; re-run --install.")
    rows = [r for r in _rows(args.out) if r["phase"] != args.phase]
    rows.append(row)
    _save(args.out, rows)
    _report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
