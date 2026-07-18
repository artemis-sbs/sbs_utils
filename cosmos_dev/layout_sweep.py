"""Resolution sweep for the GUI layout audit (gui-sizing-accuracy).

WHY: layouts mix percent with fixed px/em units, so a fixed row/font takes a
different fraction of a %-derived region as the window resizes. Overflow is
therefore RESOLUTION-DEPENDENT — a widget that fits at 1920x1080 can clip badly at
640x480. A single-resolution audit misses that; this sweeps a range of window sizes
and reports, per widget-class, the WORST overflow and the size where it happens.

HOW: runs the headless audit (`mission_runner --audit-layout --aspect WxH`) once per
size, parses each run's OVERFLOW findings, and aggregates by (console, widget-kind) —
the stable identity across runs (numeric widget tags vary run-to-run, console+kind
doesn't). Pure driver; the audit itself is unchanged.

    python -m cosmos_dev.layout_sweep ../LegendaryMissions --map 0
    python -m cosmos_dev.layout_sweep ../OpenUniverse --map universe --secs 20 \
        --aspects 640x480,1024x768,1920x1080
"""
import argparse
import os
import re
import subprocess
import sys

# Small -> large, plus a tall/narrow and an ultrawide — the extremes are where
# mixed-unit layouts break.
DEFAULT_ASPECTS = ["640x480", "800x600", "1024x768", "1280x720",
                   "1600x900", "1920x1080", "2560x1080", "768x1024"]

_OVERFLOW_RE = re.compile(
    r"OVERFLOW\s+\((?P<con>[^)]*)\)\s+\[(?P<kind>[^\]]+)\]"
    r".*?rect=\((?P<rect>[^)]+)\)")


def _area(wh):
    w, h = (int(x) for x in wh.lower().split("x"))
    return w * h


def _worst_spill(rect):
    """Max percent a rect leaves [0,100] on any edge (0 if inside)."""
    l, t, r, b = (float(x) for x in rect.split(","))
    return max(r - 100.0, b - 100.0, -l, -t, 0.0)


def _run_one(py, runner_cwd, mission, map_arg, secs, aspect):
    """One headless audit run at a forced aspect; return its stdout."""
    cmd = [py, "-m", "cosmos_dev.mission_runner", mission,
           "--test", str(secs), "--map", str(map_arg),
           "--exercise", "--audit-layout", "--aspect", aspect]
    p = subprocess.run(cmd, cwd=runner_cwd, capture_output=True, text=True)
    return p.stdout + p.stderr


def sweep(mission, map_arg, secs, aspects):
    py = sys.executable
    runner_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # results[(console, kind)][aspect] = worst spill %
    results = {}
    for aspect in aspects:
        print(f"[sweep] {aspect} ...", flush=True)
        out = _run_one(py, runner_cwd, mission, map_arg, secs, aspect)
        for m in _OVERFLOW_RE.finditer(out):
            key = (m.group("con"), m.group("kind"))
            spill = _worst_spill(m.group("rect"))
            cur = results.setdefault(key, {})
            cur[aspect] = max(cur.get(aspect, 0.0), spill)
    return results


def _bar(pct, width=20):
    n = min(width, int(round(pct / 5.0)))   # 1 block per 5%
    return "#" * n + "." * (width - n)


def report(results, aspects):
    ordered = sorted(aspects, key=_area)      # small -> large
    lines = ["", "=" * 66, "RESOLUTION SWEEP - worst overflow by widget-class", "=" * 66]
    if not results:
        lines.append("  no overflow at any tested size — clean across resolutions.")
        lines.append("=" * 66)
        return "\n".join(lines)
    # rank by worst spill anywhere
    ranked = sorted(results.items(),
                    key=lambda kv: max(kv[1].values()), reverse=True)
    for (con, kind), by_aspect in ranked:
        worst = max(by_aspect.values())
        worst_at = min((a for a in by_aspect if by_aspect[a] == worst), key=_area)
        lines.append(f"\n  {con} / {kind}   worst {worst:.1f}% @ {worst_at}")
        for a in ordered:
            v = by_aspect.get(a, 0.0)
            tag = f"{v:5.1f}%  {_bar(v)}" if v > 0 else "   (fits)"
            lines.append(f"      {a:>10}  {tag}")
    lines.append("\n" + "-" * 66)
    lines.append("Rule of thumb: >~2% at a plausible window size = a real clip to fix;")
    lines.append("grows as the window shrinks = mixed %/fixed-unit layout (scale the unit).")
    lines.append("=" * 66)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Sweep window sizes and report resolution-dependent GUI overflow.")
    ap.add_argument("mission", help="mission folder (e.g. ../LegendaryMissions)")
    ap.add_argument("--map", default="0", help="map index or name (default 0)")
    ap.add_argument("--secs", type=float, default=15, help="sim seconds per run (default 15)")
    ap.add_argument("--aspects", default=None,
                    help="comma list WxH,WxH,... (default: a small->large spread)")
    args = ap.parse_args()
    aspects = args.aspects.split(",") if args.aspects else DEFAULT_ASPECTS
    results = sweep(args.mission, args.map, args.secs, aspects)
    print(report(results, aspects))


if __name__ == "__main__":
    main()
