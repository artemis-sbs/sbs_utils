"""
Layout.calc benchmark — a BEFORE/AFTER baseline for content-based sizing.

Content sizing (row-height: content, col-width: content) adds a measure pass to
Layout.calc. The hard requirement is that layouts which use NO content keywords
pay near-zero extra cost. "Near zero" is only checkable against a number, so
this captures that number first.

It drives a REAL mission through cosmos_dev.mission_runner and times the actual
Layout.calc calls, rather than timing a synthetic layout that would not
resemble a console. LegendaryMissions is the default target: its server startup
screen and per-console client screens are layout-heavy and are built on every
session.

Primary metric is ENGINE TEXT-METRIC CALL COUNT, not wall time. Wall time in
the mock is noisy (GC, a 30Hz physics thread, other work in the same process);
call counts are deterministic and are what a measure pass actually inflates.

Lives in <repo>/bench/, tracked in git but never packaged into an .sbslib
(only sbs_utils/ and cosmos_dev/ are zipped), so it never ships and never
shadows the runtime.

Usage (from the sbs_utils repo root):
    python -m bench.bench_layout                       # LM, 1024x768 + 3440x1440
    python -m bench.bench_layout --mission ../LegendaryMissions
    python -m bench.bench_layout --seconds 20 --aspect 1024x768
    python -m bench.bench_layout --json                # machine-readable

BASELINE -- LegendaryMissions map 0, --exercise, 15s sim, seed 1234,
captured 2026-07-20 on v1.4.0_dev @ 469e2cd8, BEFORE any content sizing:

                          1024x768      3440x1440
    Layout.calc top-level        88            129
    including nested            112            178
    rows walked                 118            159
    columns walked              324            378
    engine text calls           105             98
      get_text_line_width        93             90
      get_text_line_height        6              4
      get_text_block_height       6              4
    calc total                4.6 ms         6.3 ms
    calc median              0.039 ms       0.041 ms

Two things this immediately shows:

  * Text measurement is currently RARE -- ~100 calls for a whole exercised
    session, and none of them come from Layout.calc (it never measures text
    today; they are gui_table and text_area). Content sizing adds calls in
    proportion to how many content-keyed columns exist, so this number is the
    one to watch. A layout using NO content keywords must not move it at all.

  * The heaviest single consumer is already the listbox: the "unused" tag is
    the throwaway Layout that LayoutListbox.calc_max builds PER ITEM on every
    present (layout_listbox.py:296). It is 34-45 of the ~90-130 top-level calcs
    and ~40% of the time, before content sizing exists. That is why listbox
    content support is deferred -- it multiplies the one path that is already
    the hot spot.

WHICH NUMBERS ARE ACTUALLY STABLE (measured, three runs at one commit):

    calc_top   122, 122, 94      <- NOISY, do not gate on it
    rows       152, 152, 124     <- NOISY
    engine text 105, 105, 105    <- deterministic

The runner plays N sim-seconds of real time, so how many frames (and therefore
how many screens) the exerciser gets through depends on machine load. Call
counts for Layout.calc inherit that variance; the text-metric count does not,
because it is driven by content rather than by frame count.

So: GATE ON `engine text`. Treat a change in calc_top as signal only if it is
large and reproducible across several runs.

Wall-clock is dominated by the runner itself (~60s for 15s of sim), so the ms
figures are indicative only.

Re-run after each stage. The no-content engine-text number must not move.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time

# --- force working-tree precedence -----------------------------------------
# This file lives at <repo>/bench/bench_layout.py; the package root is the
# parent of bench/. Put it first so `import sbs_utils` resolves to the edited
# source, never a packaged artemis-sbs.sbs_utils.*.sbslib on the path.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
elif sys.path[0] != _REPO_ROOT:
    sys.path.remove(_REPO_ROOT)
    sys.path.insert(0, _REPO_ROOT)

DEFAULT_MISSION = os.path.join(_REPO_ROOT, "..", "LegendaryMissions")
DEFAULT_ASPECTS = ["1024x768", "3440x1440"]


# ---------------------------------------------------------------------------
# instrumentation
# ---------------------------------------------------------------------------
def _instrument():
    """Wrap Layout.calc and the engine text metrics. Returns a stats dict.

    Layout.calc RECURSES: a sub-section is a Layout stored as a column, so the
    parent's calc calls the child's. Timing every call and summing would count
    nested work several times over, so wall time is accumulated only for
    depth-0 (top-level) calls, while the call count covers all of them.
    """
    from sbs_utils.pages.layout.layout import Layout
    from cosmos_dev.mock import sbs as mock_sbs

    st = {
        "calc_calls": 0,       # every Layout.calc, nested included
        "calc_top": 0,         # depth-0 calls only
        "top_times": [],       # seconds, depth-0 only
        "rows": 0,
        "cols": 0,
        "text_w": 0,
        "text_h": 0,
        "block_h": 0,
        "per_tag": {},         # tag -> [calls, seconds]
        "_depth": 0,
    }

    orig_calc = Layout.calc

    def timed_calc(self, client_id):
        top = st["_depth"] == 0
        st["_depth"] += 1
        st["calc_calls"] += 1
        t0 = time.perf_counter()
        try:
            return orig_calc(self, client_id)
        finally:
            st["_depth"] -= 1
            if top:
                dt = time.perf_counter() - t0
                st["calc_top"] += 1
                st["top_times"].append(dt)
                tag = getattr(self, "tag", None) or "?"
                slot = st["per_tag"].setdefault(tag, [0, 0.0])
                slot[0] += 1
                slot[1] += dt
                # Structure walked, counted once per top-level calc so the
                # numbers describe a whole screen rather than a fragment.
                try:
                    st["rows"] += len(self.rows)
                    for r in self.rows:
                        st["cols"] += len(r.columns)
                except Exception:
                    pass

    Layout.calc = timed_calc

    def count(name, key):
        orig = getattr(mock_sbs, name)

        def tap(*a, **k):
            st[key] += 1
            return orig(*a, **k)
        setattr(mock_sbs, name, tap)

    count("get_text_line_width", "text_w")
    count("get_text_line_height", "text_h")
    count("get_text_block_height", "block_h")
    return st


def _summarize(st, mission, aspect, seconds, wall):
    times = st["top_times"]
    med = statistics.median(times) * 1000 if times else 0.0
    p95 = (sorted(times)[int(len(times) * 0.95)] * 1000) if times else 0.0
    total = sum(times) * 1000
    heavy = sorted(st["per_tag"].items(), key=lambda kv: -kv[1][1])[:5]
    return {
        "mission": os.path.basename(os.path.abspath(mission)),
        "aspect": aspect,
        "sim_seconds": seconds,
        "wall_seconds": round(wall, 2),
        "calc_calls": st["calc_calls"],
        "calc_top": st["calc_top"],
        "calc_ms_total": round(total, 1),
        "calc_ms_median": round(med, 3),
        "calc_ms_p95": round(p95, 3),
        "rows_walked": st["rows"],
        "cols_walked": st["cols"],
        "engine_text_calls": st["text_w"] + st["text_h"] + st["block_h"],
        "get_text_line_width": st["text_w"],
        "get_text_line_height": st["text_h"],
        "get_text_block_height": st["block_h"],
        "heaviest": [{"tag": t, "calls": v[0], "ms": round(v[1] * 1000, 1)}
                     for t, v in heavy],
    }


# ---------------------------------------------------------------------------
# worker: one mission run in this process, results as one JSON line
# ---------------------------------------------------------------------------
def _worker(args):
    # --aspect uses action="append", so it arrives as a list even in the worker
    # where exactly one is passed. _run wants a plain "WxH" string; handing it a
    # list makes the runner's parse fail SILENTLY (it catches the exception and
    # prints "bad --aspect"), so the sweep would report per-resolution numbers
    # that were all measured at the default resolution.
    aspect = args.aspect[0] if isinstance(args.aspect, list) else args.aspect
    st = _instrument()
    from cosmos_dev import mission_runner

    t0 = time.perf_counter()
    try:
        mission_runner._run(
            args.mission,
            map_arg=args.map,
            test_seconds=args.seconds,
            exercise=True,          # drive consoles so real screens get built
            use_working_tree=True,  # measure the edited source, not a .sbslib
            aspect=aspect,
            seed=1234,              # fixed so runs are comparable
        )
    except SystemExit:
        pass
    wall = time.perf_counter() - t0

    print("BENCH_JSON " + json.dumps(
        _summarize(st, args.mission, aspect, args.seconds, wall)))
    return 0


# ---------------------------------------------------------------------------
# parent: one subprocess per configuration
# ---------------------------------------------------------------------------
def _run_config(args, aspect):
    cmd = [sys.executable, "-m", "bench.bench_layout", "--worker",
           "--mission", args.mission, "--aspect", aspect,
           "--seconds", str(args.seconds)]
    if args.map is not None:
        cmd += ["--map", str(args.map)]
    proc = subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        if line.startswith("BENCH_JSON "):
            return json.loads(line[len("BENCH_JSON "):])
    sys.stderr.write(proc.stdout[-2000:] + proc.stderr[-2000:])
    return None


def _print(results):
    print()
    print("=" * 72)
    print("LAYOUT CALC BENCHMARK")
    print("=" * 72)
    for r in results:
        if r is None:
            continue
        print(f"\n{r['mission']}  @ {r['aspect']}   "
              f"({r['sim_seconds']}s sim, {r['wall_seconds']}s wall)")
        print(f"  Layout.calc      {r['calc_top']:>7} top-level "
              f"({r['calc_calls']} incl. nested)")
        print(f"  time             {r['calc_ms_total']:>7.1f} ms total   "
              f"median {r['calc_ms_median']:.3f} ms   p95 {r['calc_ms_p95']:.3f} ms")
        print(f"  structure        {r['rows_walked']:>7} rows, "
              f"{r['cols_walked']} columns walked")
        print(f"  engine text      {r['engine_text_calls']:>7} calls  "
              f"(w={r['get_text_line_width']} h={r['get_text_line_height']} "
              f"block={r['get_text_block_height']})")
        if r["heaviest"]:
            print("  heaviest layouts:")
            for h in r["heaviest"]:
                print(f"      {h['tag']:<28} {h['calls']:>5} calls  {h['ms']:>8.1f} ms")
    print()
    print("  Primary metric is ENGINE TEXT CALLS -- deterministic, and what a")
    print("  measure pass inflates. Wall time here is indicative only.")
    print("=" * 72)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mission", default=DEFAULT_MISSION)
    ap.add_argument("--aspect", action="append",
                    help="WxH; repeatable (default 1024x768 and 3440x1440)")
    ap.add_argument("--seconds", type=float, default=15.0,
                    help="sim seconds per run (default 15)")
    ap.add_argument("--map", default=0, help="map index/name (default 0)")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.worker:
        return _worker(args)

    if not os.path.isdir(args.mission):
        print(f"mission not found: {args.mission}")
        return 2

    aspects = args.aspect or DEFAULT_ASPECTS
    results = [_run_config(args, a) for a in aspects]
    if args.json:
        print(json.dumps([r for r in results if r], indent=2))
    else:
        _print(results)
    return 0 if any(r for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
