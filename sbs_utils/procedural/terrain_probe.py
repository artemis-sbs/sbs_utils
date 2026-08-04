"""Phase 0 instrumentation: measure the terrain creation burst IN THE ENGINE.

Inert unless a mission calls ``terrain_probe_start()``. It answers three questions
that decide how the terrain sower is dialled:

1. How long does each terrain call actually take (wall ms, objects created)?
2. Inside that, how much is the ``terrain_spawn`` / ``npc_spawn`` Pybind call vs the
   ``blob.set`` / ``data_set.set`` / ``engine_object.*`` setters around it?
3. Does the cost stop when the call returns, or is there a client-sync **tail** --
   long frames for the seconds after the burst?

(3) is the one the mock cannot answer, and it decides whether the sower's budget
counts clusters or bytes. So this is run in a real Cosmos session and the numbers
come back in a file -- never a print, never a screenshot.

Usage from a map label (see the temp probe label in LM's sandbox map)::

    terrain_probe_start()
    terrain_probe_mark("stations")
    terrain_spawn_stations(DIFFICULTY, lethal_value)
    terrain_probe_mark("asteroids")
    terrain_asteroid_clusters(terrain_value)
    ...
    terrain_probe_mark("done")
    await delay_sim(10)        # let the sync tail land in the frame log
    terrain_probe_stop()
"""

import time

from ..tickdispatcher import TickDispatcher
from ..agent import Agent
from . import terrain as _terrain


# Probe state. Everything lives in one dict so reset/stop is a single assignment
# and there is no half-enabled state to reason about.
_P = {
    "path": None,
    "on": False,
    "sections": [],      # [name, t_start, t_end, spawn_calls, spawn_ms, agents_start, agents_end, tick_start, tick_end]
    "cur": None,
    "frames": [],        # [(tick, wall_ms_since_previous_frame)]
    "last_frame_t": None,
    "task": None,
    "saved": None,       # (terrain_spawn, npc_spawn) originals
    "spawn_calls": 0,
    "spawn_ms": 0.0,
}


def _agent_count():
    try:
        return len(Agent.all)
    except Exception:
        return 0


def _tick():
    try:
        return TickDispatcher.current
    except Exception:
        return 0


def _wrap(fn):
    """Time one leaf spawn call, so setter cost = section wall - summed spawn time."""
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            _P["spawn_ms"] += (time.perf_counter() - t0) * 1000.0
            _P["spawn_calls"] += 1
    wrapper.__name__ = getattr(fn, "__name__", "spawn")
    return wrapper


def _frame_cb(t):
    now = time.perf_counter()
    prev = _P["last_frame_t"]
    _P["last_frame_t"] = now
    if prev is not None:
        _P["frames"].append((_tick(), (now - prev) * 1000.0))


def terrain_probe_start(path=None):
    """Begin capture. Truncates the log file and returns its path."""
    if _P["on"]:
        terrain_probe_stop()

    if path is None:
        try:
            from ..fs import get_mission_dir_filename
            path = get_mission_dir_filename("terrain_burst.log")
        except Exception:
            path = "terrain_burst.log"
    try:
        open(path, "w").close()
    except Exception:
        pass

    # Patch the terrain module's own bindings -- terrain.py did
    # `from .spawn import terrain_spawn, npc_spawn`, and Python resolves module
    # globals at call time, so replacing them here reaches every terrain_* function.
    _P["saved"] = (_terrain.terrain_spawn, _terrain.npc_spawn)
    _terrain.terrain_spawn = _wrap(_P["saved"][0])
    _terrain.npc_spawn = _wrap(_P["saved"][1])

    _P["path"] = path
    _P["on"] = True
    _P["sections"] = []
    _P["cur"] = None
    _P["frames"] = []
    _P["last_frame_t"] = None
    _P["spawn_calls"] = 0
    _P["spawn_ms"] = 0.0
    _P["task"] = TickDispatcher.do_interval(_frame_cb, 0)
    return path


def _close_section():
    cur = _P["cur"]
    if cur is None:
        return
    cur["t_end"] = time.perf_counter()
    cur["agents_end"] = _agent_count()
    cur["tick_end"] = _tick()
    cur["spawn_calls"] = _P["spawn_calls"] - cur["spawn_calls"]
    cur["spawn_ms"] = _P["spawn_ms"] - cur["spawn_ms"]
    _P["sections"].append(cur)
    _P["cur"] = None


def terrain_probe_mark(name, wait=False):
    """Close the running section and open a new one called ``name``.

    ``wait=True`` marks a section that spans an ``await`` -- its wall time is the
    waiting, not the cost, so it is excluded from the totals and the per-object
    figures. The frame log still covers it, which is the point of the tail section.
    """
    if not _P["on"]:
        return
    _close_section()
    _P["cur"] = {
        "name": name,
        "wait": wait,
        "t_start": time.perf_counter(),
        "t_end": None,
        "agents_start": _agent_count(),
        "agents_end": 0,
        "tick_start": _tick(),
        "tick_end": 0,
        "spawn_calls": _P["spawn_calls"],
        "spawn_ms": _P["spawn_ms"],
    }


def terrain_probe_stop():
    """End capture, restore the real spawn functions, write the report."""
    if not _P["on"]:
        return _P["path"]
    _close_section()

    if _P["saved"] is not None:
        _terrain.terrain_spawn, _terrain.npc_spawn = _P["saved"]
        _P["saved"] = None
    if _P["task"] is not None:
        try:
            _P["task"].stop()
        except Exception:
            pass
        _P["task"] = None
    _P["on"] = False

    path = _P["path"]
    try:
        with open(path, "a") as f:
            _write_report(f)
    except Exception:
        pass
    return path


def _write_report(f):
    f.write("terrain burst probe\n")
    f.write(f"tps={TickDispatcher.tps}\n\n")

    f.write("== sections ==\n")
    f.write(f"{'section':<20}{'wall_ms':>10}{'spawn_ms':>10}{'setter_ms':>11}"
            f"{'objects':>9}{'agents':>9}{'ticks':>7}\n")
    total_wall = 0.0
    total_spawn = 0.0
    total_obj = 0
    burst_end_tick = 0
    for s in _P["sections"]:
        wall = (s["t_end"] - s["t_start"]) * 1000.0
        setter = wall - s["spawn_ms"]
        agents = s["agents_end"] - s["agents_start"]
        ticks = s["tick_end"] - s["tick_start"]
        waiting = s.get("wait")
        if not waiting:
            total_wall += wall
            total_spawn += s["spawn_ms"]
            total_obj += s["spawn_calls"]
            burst_end_tick = max(burst_end_tick, s["tick_end"])
        name = ("~" + s["name"]) if waiting else s["name"]
        f.write(f"{name[:19]:<20}{wall:>10.1f}{s['spawn_ms']:>10.1f}{setter:>11.1f}"
                f"{s['spawn_calls']:>9}{agents:>9}{ticks:>7}\n")
    setter_total = total_wall - total_spawn
    f.write(f"{'TOTAL':<20}{total_wall:>10.1f}{total_spawn:>10.1f}{setter_total:>11.1f}"
            f"{total_obj:>9}\n")
    f.write("(~ = a waiting section; its wall time is the await, not a cost, and is\n"
            " excluded from TOTAL. Its frames still count in the tail below.)\n")
    if total_obj:
        f.write(f"\nper object: {total_wall/total_obj:.3f} ms "
                f"(spawn {total_spawn/total_obj:.3f}, setters {setter_total/total_obj:.3f})\n")

    # The tail. A frame period well above 1000/tps ms AFTER the burst means the
    # engine is still paying for it -- that is the client-sync cost, and it is what
    # decides whether the sower's budget counts clusters or bytes.
    f.write("\n== frame periods ==\n")
    if not _P["frames"]:
        f.write("(none recorded)\n")
        return

    # One row per sim tick. The dispatcher can run more than once per tick counter
    # increment, so raw samples over-count frames and dilute the average.
    by_tick = {}
    for tick, ms in _P["frames"]:
        by_tick[tick] = by_tick.get(tick, 0.0) + ms
    ticks = sorted(by_tick.items())
    nominal = 1000.0 / max(1, TickDispatcher.tps)
    worst = max(ticks, key=lambda t: t[1])
    avg = sum(ms for _, ms in ticks) / len(ticks)
    f.write(f"nominal {nominal:.1f} ms   ticks {len(ticks)}   avg {avg:.1f} ms   "
            f"worst {worst[1]:.1f} ms at tick {worst[0]}\n")

    during = [ms for t, ms in ticks if t <= burst_end_tick]
    tail_window = burst_end_tick + TickDispatcher.tps * 5
    tail = [ms for t, ms in ticks if burst_end_tick < t <= tail_window]
    settled = [ms for t, ms in ticks if t > tail_window]
    f.write(f"burst ends at tick {burst_end_tick}\n")
    for label, rows in (("during burst", during), ("tail (5s after)", tail),
                        ("settled", settled)):
        if rows:
            f.write(f"  {label:<18} ticks {len(rows):>5}   avg {sum(rows)/len(rows):>8.1f} ms"
                    f"   worst {max(rows):>8.1f} ms\n")
    if tail and settled:
        ratio = (sum(tail) / len(tail)) / max(0.001, sum(settled) / len(settled))
        f.write(f"  tail / settled = {ratio:.2f}x  "
                f"({'SYNC TAIL' if ratio > 1.5 else 'no meaningful tail'})\n")

    over = [(t, ms) for t, ms in ticks if ms > nominal * 1.5]
    f.write(f"\nticks over 1.5x nominal: {len(over)}\n")
    f.write(f"{'tick':>8}{'ms':>10}\n")
    for t, ms in over[:60]:
        f.write(f"{t:>8}{ms:>10.1f}\n")
    if len(over) > 60:
        f.write(f"(+{len(over) - 60} more)\n")


def terrain_probe_active():
    return _P["on"]
