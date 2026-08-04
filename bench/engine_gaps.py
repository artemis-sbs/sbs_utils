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
if S is None:
    # cap: a long session must not grow an unbounded list inside the engine
    S = {"last": None, "gaps": [], "inside": [], "cap": 50000}
    S["orig"] = Gui.present
    builtins._COSMOS_GAP = S

    def tapped(event):
        t0 = time.perf_counter()
        if S["last"] is not None and len(S["gaps"]) < S["cap"]:
            S["gaps"].append((t0 - S["last"]) * 1000.0)
        try:
            return S["orig"](event)
        finally:
            t1 = time.perf_counter()
            if len(S["inside"]) < S["cap"]:
                S["inside"].append((t1 - t0) * 1000.0)
            S["last"] = t1

    Gui.present = staticmethod(tapped)
    _result = "installed"
else:
    _result = "already installed"
"""

RESET = """
import builtins
S = builtins._COSMOS_GAP
S["gaps"].clear(); S["inside"].clear(); S["last"] = None
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

_result = {
    "samples": len(g),
    "gap_med": pct(g, 0.5), "gap_p90": pct(g, 0.9),
    "gap_max": round(g[-1], 2) if g else None,
    "in_med": pct(i, 0.5), "in_p90": pct(i, 0.9),
    "in_max": round(i[-1], 2) if i else None,
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
    print(f"  {'phase':<16}{'widgets':>8}{'n':>7}{'gap med':>9}{'gap p90':>9}"
          f"{'gap max':>9}{'ours med':>10}")
    for r in rows:
        w = r.get("widgets")
        print(f"  {r['phase']:<16}{('-' if w is None else w):>8}{r['samples']:>7}"
              f"{r['gap_med'] or 0:>9.2f}{r['gap_p90'] or 0:>9.2f}"
              f"{r['gap_max'] or 0:>9.2f}{r['in_med'] or 0:>10.2f}")
    print("-" * 78)
    print("  gap  = engine time between our frames -- what to compare")
    print("  ours = time inside Gui.present -- our own cost, for context")
    print()
    print("  Every gap up while widgets are on screen -> steady-state engine cost.")
    print("  Only gap max up, right after a switch    -> one-time construction.")
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
        if not drv.ping(timeout=30):
            raise SystemExit("the devqueue did not answer -- is the mission loaded "
                             "with cosmos_devqueue.mastlib in its story.json?")
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
    rows = [r for r in _rows(args.out) if r["phase"] != args.phase]
    rows.append(row)
    _save(args.out, rows)
    _report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
