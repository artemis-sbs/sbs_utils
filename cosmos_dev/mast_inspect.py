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
        # The diplomacy verdict "is this an enemy of the players?" is a relationship,
        # not a label — resolve the whole hostile-to-players set ONCE per snapshot
        # (pure diplomacy, no combat-role filter) so each agent is an O(1) lookup.
        try:
            from sbs_utils.procedural.sides import players_hostile_members
            foes = set(players_hostile_members(scope_role=None))
        except Exception:
            foes = set()
        out = []
        for a in list(Agent.all.values()):
            if not isinstance(a, SpaceObject):
                continue
            try:
                out.append(self._one(a, foes))
            except Exception:
                pass
            if len(out) >= 500:
                break
        return {"agents": out}

    @staticmethod
    def _one(a, foes=frozenset()):
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
                "enemy": a.get_id() in foes,
                "inventory": _json_safe(inv)}


class GuiTap:
    """Publish the widget list a console builds each frame, by wrapping the live
    ``sbs`` module's ``send_gui_*`` functions (attribute lookups, so a patch is
    seen — unlike cached MAST globals). Widgets are accumulated between
    ``send_gui_clear`` and ``send_gui_complete`` and published per client, with
    parent/tag/rect/type so a panel can show the tree. Only meaningful with a GUI
    (the headless mock's ``send_gui_*`` are no-ops)."""

    def __init__(self, bus=BUS):
        self._bus = bus
        self._sbs = None
        self._orig = {}
        self._frames = {}   # clientID -> [widget dicts]

    def install(self):
        from sbs_utils.helpers import FrameContext
        ctx = getattr(FrameContext, "context", None)
        sbs = getattr(ctx, "sbs", None)
        if sbs is None or self._orig:
            return self
        self._sbs = sbs
        for name in dir(sbs):
            if not name.startswith("send_gui_"):
                continue
            orig = getattr(sbs, name)
            if not callable(orig):
                continue
            self._orig[name] = orig
            setattr(sbs, name, self._make(name, orig))
        return self

    def uninstall(self):
        if self._sbs is not None:
            for name, orig in self._orig.items():
                try:
                    setattr(self._sbs, name, orig)
                except Exception:
                    pass
        self._orig = {}
        self._sbs = None

    def _make(self, name, orig):
        tap = self

        def wrap(*args, **kwargs):
            try:
                tap._capture(name, args)
            except Exception:
                pass
            return orig(*args, **kwargs)
        return wrap

    def _capture(self, name, args):
        kind = name[len("send_gui_"):]
        if not args:
            return
        cid = args[0]
        if kind == "clear":
            self._frames[cid] = []
        elif kind == "complete":
            widgets = self._frames.get(cid, [])
            self._bus.publish("widgets", {"client": str(cid), "widgets": widgets})
        else:
            w = {"type": kind}
            if len(args) >= 3:
                w["parent"] = args[1]
                w["tag"] = args[2]
            # rect = the last 4 numeric args (l,t,r,b) — robust across the varied
            # send_gui_* signatures (slider/face insert an extra arg before them).
            nums = [a for a in args if isinstance(a, (int, float)) and not isinstance(a, bool)]
            if len(nums) >= 4:
                w["rect"] = nums[-4:]
            style = next((a for a in args[3:] if isinstance(a, str)), None)
            if style is not None:
                w["style"] = style
            self._frames.setdefault(cid, []).append(w)


def _brain_label_name(lbl):
    if lbl is None:
        return None
    if isinstance(lbl, str):
        return lbl
    return getattr(lbl, "name", None)


def _brain_type_name(brain):
    from sbs_utils.procedural.brain import BrainType
    bt = getattr(brain, "brain_type", 0)
    if bt & BrainType.Select:
        return "select"
    if bt & BrainType.Sequence:
        return "sequence"
    return "simple"


class BrainTap:
    """Publish a periodic snapshot of every agent's behaviour-tree brain — the
    node tree (select/sequence/simple), each node's label and last result, and
    which child a composite currently has active. A poller (brains mutate on the
    tick thread), so it reads a best-effort snapshot like ``WorldTap``.

    Reads the ``__BRAIN__`` inventory the brain system already maintains, so it
    needs no library change and adds nothing to a non-inspected run."""

    def __init__(self, bus=BUS, interval=0.5):
        self._bus = bus
        self._interval = interval
        self._stop = threading.Event()
        self._thread = None

    def install(self):
        if self._thread is not None:
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="mast-brain-tap", daemon=True)
        self._thread.start()
        return self

    def uninstall(self):
        self._stop.set()
        self._thread = None

    def _loop(self):
        while not self._stop.is_set():
            if self._bus.active:
                try:
                    self._bus.publish("brains", self.snapshot())
                except Exception:
                    pass
            self._stop.wait(self._interval)

    def snapshot(self):
        from sbs_utils.procedural.inventory import has_inventory, get_inventory_value
        from sbs_utils.agent import Agent
        out = []
        for agent_id in list(has_inventory("__BRAIN__")):
            try:
                root = get_inventory_value(agent_id, "__BRAIN__", None)
                if root is None:
                    continue
                obj = Agent.get(agent_id)
                paused = bool(get_inventory_value(agent_id, "__BRAIN_PAUSED__", False))
                out.append({"agent": agent_id,
                            "name": getattr(obj, "name", None),
                            "paused": paused,
                            "tree": self._node(root)})
            except Exception:
                pass
            if len(out) >= 200:
                break
        return {"brains": out}

    def _node(self, brain, depth=0):
        node = {"type": _brain_type_name(brain),
                "label": _brain_label_name(getattr(brain, "label", None)),
                "result": getattr(getattr(brain, "result", None), "name", None)}
        children = getattr(brain, "children", None)
        if children and depth < 8:
            active = getattr(brain, "_active", None)
            node["children"] = kids = [self._node(c, depth + 1) for c in children]
            for c, kid in zip(children, kids):
                if c is active:
                    kid["active"] = True
        return node


# All available taps, so the adapter can install/uninstall the set at once.
ALL_TAPS = (SignalTap, WorldTap, GuiTap, BrainTap)
