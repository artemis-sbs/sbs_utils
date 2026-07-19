"""Live inspection of a running mission (dev-only).

The debugger gave us a live socket into a running mission and the discipline of
tapping an inert seam. Inspectors reuse both: a **tap** monkeypatches a
reference-stable method (the python-step technique — no shipped-library change)
and publishes typed events to an **InspectionBus**; the DAP adapter subscribes and
forwards them to the editor as `mast/inspect` custom events, which VS Code panels
render.

Inspectors stream *while the mission runs* — they never park the tick loop — so
they're independent of breakpoints. A tap only publishes when a sink is
subscribed (inert otherwise), and installs its patch only while a tool is active.

First tap: **signals** (`Mast.signal_emit`). Others (gui / brains / agents) follow
the same shape. See MISSION_TOOLS_PLAN.md.
"""
import threading


def _json_safe(value, _depth=0):
    """Best-effort convert arbitrary MAST values to something JSON-serializable
    for the wire — dicts/lists recurse (bounded), everything else becomes repr."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if _depth < 4:
        if isinstance(value, dict):
            return {str(k): _json_safe(v, _depth + 1) for k, v in list(value.items())[:50]}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(v, _depth + 1) for v in list(value)[:50]]
    try:
        return repr(value)
    except Exception:
        return "<unrepr>"


class InspectionBus:
    """Tiny pub/sub for live-inspection events. One sink (the adapter). Inert —
    ``publish`` is a no-op — when nothing is subscribed."""

    def __init__(self):
        self._sink = None
        self._seq = 0

    def subscribe(self, sink):
        self._sink = sink

    def unsubscribe(self):
        self._sink = None

    @property
    def active(self):
        return self._sink is not None

    def publish(self, kind, payload):
        sink = self._sink
        if sink is None:
            return
        self._seq += 1
        try:
            sink({"kind": kind, "seq": self._seq, "payload": payload})
        except Exception:
            pass


# Process-wide bus the taps publish to and the adapter subscribes to.
BUS = InspectionBus()


class SignalTap:
    """Publish every emitted signal (name, data, sender, how many routes fired) by
    wrapping the reference-stable ``Mast.signal_emit`` dispatch."""

    def __init__(self, bus=BUS):
        self._bus = bus
        self._orig = None

    def install(self):
        from sbs_utils.mast.mast import Mast
        if self._orig is not None:
            return self
        # Wrap the REAL method (unwrap any prior wrapper) so re-install never nests.
        base = getattr(Mast.signal_emit, "_mast_orig", Mast.signal_emit)
        self._orig = base
        bus = self._bus

        def signal_emit(mast_self, name, sender_task, data):
            if bus.active:
                try:
                    routes = sum(len(v) for v in
                                 mast_self.signal_observers.get(name, {}).values())
                    sender = (getattr(sender_task, "name", None)
                              or getattr(sender_task, "id", None))
                    bus.publish("signal", {"name": name, "data": _json_safe(data),
                                           "sender": sender, "routes": routes})
                except Exception:
                    pass
            return base(mast_self, name, sender_task, data)

        signal_emit._mast_orig = base
        Mast.signal_emit = signal_emit
        return self

    def uninstall(self):
        from sbs_utils.mast.mast import Mast
        if self._orig is not None:
            Mast.signal_emit = self._orig
            self._orig = None


class WorldTap:
    """Publish a periodic snapshot of the world's space objects — id, name, side,
    roles, kind (player/npc/terrain), and inventory. A poller (not event-driven),
    so it runs a lightweight daemon thread while active and reads a *snapshot* of
    ``Agent.all`` (the tick thread may mutate it)."""

    def __init__(self, bus=BUS, interval=0.5):
        self._bus = bus
        self._interval = interval
        self._stop = threading.Event()
        self._thread = None

    def install(self):
        if self._thread is not None:
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="mast-world-tap", daemon=True)
        self._thread.start()
        return self

    def uninstall(self):
        self._stop.set()
        self._thread = None

    def _loop(self):
        while not self._stop.is_set():
            if self._bus.active:
                try:
                    self._bus.publish("agents", self.snapshot())
                except Exception:
                    pass
            self._stop.wait(self._interval)

    def snapshot(self):
        from sbs_utils.agent import Agent
        from sbs_utils.spaceobject import SpaceObject
        out = []
        for a in list(Agent.all.values()):
            if not isinstance(a, SpaceObject):
                continue
            try:
                out.append(self._one(a))
            except Exception:
                pass
            if len(out) >= 500:
                break
        return {"agents": out}

    @staticmethod
    def _one(a):
        kind = ("player" if a.is_player else
                "terrain" if a.is_terrain else
                "npc" if a.is_npc else "object")
        try:
            side = a.side
        except Exception:
            side = None
        roles = sorted(r for r in a.get_roles() if not (isinstance(r, str) and r.startswith("__")))
        inv = {k: v for k, v in a.inventory.collections.items()
               if not (isinstance(k, str) and (k.startswith("__") or k in ("mast_task", "SHARED")))}
        return {"id": a.get_id(), "name": getattr(a, "name", None),
                "side": side, "kind": kind, "roles": roles,
                "inventory": _json_safe(inv)}


# All available taps, so the adapter can install/uninstall the set at once.
ALL_TAPS = (SignalTap, WorldTap)
