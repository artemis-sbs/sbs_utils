"""Read-only GUI layout audit for the mock/mockgui sbs layer.

SPIKE (branch gui-sizing-accuracy). Goal: prove that we can catch GUI *sizing*
bugs — a widget whose rect spills past its region, or two content widgets that
overlap — HEADLESS, from the emitted `send_gui_*` rect stream, instead of only
by eyeballing the browser. The browser mock actually *clips* at region
boundaries (`overflow:hidden` in client.html), so it HIDES the very overflow the
real engine would render; a data-level audit sees what the browser conceals.

This module is a pure, dependency-free TAP. `install(sbs_module)` monkeypatches
the module's `send_gui_*` senders with wrappers that RECORD each widget's rect
and then call the original through unchanged. It mutates nothing about
rendering, is off unless installed, and is entirely removable — so it carries
zero production risk (dev-only; never shipped in an .sbslib).

Coordinate model (confirmed against client.html): a widget's left/top/right/
bottom are PERCENT-LOCAL to its parent region (0..100), at every nesting depth.
So:
  * OVERFLOW  = any rect that leaves [0,100] of its parent (uniform, no need to
                resolve the parent's absolute box).
  * OVERLAP   = two same-draw_layer *content* siblings whose rects intersect.
  * DEGENERATE= right<=left or bottom<=top (zero/negative area).
"""

from __future__ import annotations

# --- tunables --------------------------------------------------------------
EPS = 0.5          # percent slop before a rect counts as "out of region"
MIN_OVERLAP = 1.0  # percent^2 min intersection area before flagging overlap

# Widget kinds that carry visible content and should never overlap a sibling of
# the same kind. Images/clickregions/sub_regions are structural or intentional
# background layers — excluded from the overlap check (kills the biggest
# false-positive class: a background image behind text).
_CONTENT_KINDS = frozenset({
    "text", "button", "checkbox", "colorbutton", "colorcheckbox",
    "dropdown", "typein", "slider", "icon", "iconbutton", "iconcheckbox",
    "rawiconbutton", "face", "3dship",
})

# Sender name -> index of (left, top, right, bottom) in the *args tuple after
# clientID. Most senders are (parent, tag, style, l, t, r, b); the odd ones out
# carry an extra payload arg before the rect.
_RECT_AT = {
    "send_gui_3dship":       3, "send_gui_button":        3,
    "send_gui_checkbox":     3, "send_gui_clickregion":   3,
    "send_gui_colorbutton":  3, "send_gui_colorcheckbox": 3,
    "send_gui_dropdown":     3, "send_gui_icon":          3,
    "send_gui_iconbutton":   3, "send_gui_iconcheckbox":  3,
    "send_gui_image":        3, "send_gui_rawiconbutton": 3,
    "send_gui_sub_region":   3, "send_gui_text":          3,
    "send_gui_typein":       3,
    "send_gui_face":         3,   # (parent, tag, face_string, l, t, r, b)
    "send_gui_slider":       4,   # (parent, tag, current, style, l, t, r, b)
}


def _kind(sender: str) -> str:
    return sender[len("send_gui_"):]


def _draw_layer(style: str) -> int:
    if not style or "draw_layer" not in style:
        return 0
    for part in style.split(";"):
        k, _, v = part.partition(":")
        if k.strip() == "draw_layer":
            try:
                return int(float(v.strip()))
            except ValueError:
                return 0
    return 0


class _Widget:
    __slots__ = ("cid", "parent", "tag", "kind", "layer", "l", "t", "r", "b")

    def __init__(self, cid, parent, tag, kind, layer, l, t, r, b):
        self.cid, self.parent, self.tag, self.kind, self.layer = cid, parent, tag, kind, layer
        self.l, self.t, self.r, self.b = float(l), float(t), float(r), float(b)


class LayoutAudit:
    def __init__(self):
        # live snapshot: (cid, tag) -> _Widget   (re-sends overwrite; the dirty
        # system re-emits each tick, so latest rect wins)
        self._live: dict = {}
        # deduped findings: key -> (kind, message)
        self._findings: dict = {}
        self._frames = 0
        # optional: sbs_module.get_type_of_client, to label WHICH console a
        # finding is on so it can be navigated to. Set by install().
        self._resolve_console = None

    def _console(self, cid):
        try:
            return self._resolve_console(cid) if self._resolve_console else "?"
        except Exception:
            return "?"

    # -- recording -----------------------------------------------------------
    def record(self, sender, cid, parent, tag, layer, l, t, r, b):
        self._live[(cid, tag)] = _Widget(cid, parent, tag, _kind(sender), layer, l, t, r, b)

    def clear(self, cid, tag):
        # drop this region and anything parented under it
        for k in [k for k, w in self._live.items() if k[0] == cid and (w.tag == tag or w.parent == tag)]:
            self._live.pop(k, None)

    def complete(self, cid, tag):
        self._frames += 1
        self._audit_client(cid)

    # -- checks --------------------------------------------------------------
    def _add(self, key, kind, msg):
        if key not in self._findings:
            self._findings[key] = (kind, msg)

    def _audit_client(self, cid):
        widgets = [w for (c, _), w in self._live.items() if c == cid]
        con = self._console(cid)

        # 1) overflow / degenerate — uniform [0,100]-local check
        for w in widgets:
            if w.r - w.l <= 0 or w.b - w.t <= 0:
                self._add((cid, w.tag, "degenerate"), "DEGENERATE",
                          f"({con}) [{w.kind}] {w.tag} in <{w.parent}> zero/negative area "
                          f"({w.l:.1f},{w.t:.1f})->({w.r:.1f},{w.b:.1f})")
                continue
            over = []
            if w.l < -EPS: over.append(f"left {w.l:.1f}")
            if w.t < -EPS: over.append(f"top {w.t:.1f}")
            if w.r > 100 + EPS: over.append(f"right {w.r:.1f}")
            if w.b > 100 + EPS: over.append(f"bottom {w.b:.1f}")
            if over:
                self._add((cid, w.tag, "overflow"), "OVERFLOW",
                          f"({con}) [{w.kind}] {w.tag} in <{w.parent}> spills: {', '.join(over)} "
                          f"rect=({w.l:.2f},{w.t:.2f},{w.r:.2f},{w.b:.2f})")

        # 2) sibling overlap — same parent, same draw_layer, both content kinds
        by_parent: dict = {}
        for w in widgets:
            if w.kind in _CONTENT_KINDS:
                by_parent.setdefault(w.parent, []).append(w)
        for parent, group in by_parent.items():
            n = len(group)
            for i in range(n):
                for j in range(i + 1, n):
                    a, b = group[i], group[j]
                    if a.layer != b.layer:
                        continue
                    area = self._overlap_area(a, b)
                    if area > MIN_OVERLAP:
                        key = (cid, parent, "overlap", *sorted((a.tag, b.tag)))
                        self._add(key, "OVERLAP",
                                  f"({con}) [{a.kind}] {a.tag} & [{b.kind}] {b.tag} overlap "
                                  f"in <{parent}> (~{area:.0f}%^2) "
                                  f"A=({a.l:.2f},{a.t:.2f},{a.r:.2f},{a.b:.2f}) "
                                  f"B=({b.l:.2f},{b.t:.2f},{b.r:.2f},{b.b:.2f})")

    @staticmethod
    def _overlap_area(a, b):
        ix = max(0.0, min(a.r, b.r) - max(a.l, b.l))
        iy = max(0.0, min(a.b, b.b) - max(a.t, b.t))
        return ix * iy

    # -- report --------------------------------------------------------------
    def report(self, limit=40):
        counts = {"OVERFLOW": 0, "OVERLAP": 0, "DEGENERATE": 0}
        for kind, _ in self._findings.values():
            counts[kind] = counts.get(kind, 0) + 1
        lines = ["", "=" * 60,
                 f"LAYOUT AUDIT  ({self._frames} frames audited)",
                 f"  OVERFLOW={counts['OVERFLOW']}  OVERLAP={counts['OVERLAP']}  "
                 f"DEGENERATE={counts['DEGENERATE']}  total={len(self._findings)}",
                 "-" * 60]
        for i, (kind, msg) in enumerate(self._findings.values()):
            if i >= limit:
                lines.append(f"  ... {len(self._findings) - limit} more")
                break
            lines.append(f"  {kind:10s} {msg}")
        lines.append("=" * 60)
        return "\n".join(lines)


# --- global instance + install --------------------------------------------
_AUDIT: LayoutAudit | None = None


def get() -> LayoutAudit | None:
    return _AUDIT


def report(limit=40) -> str:
    return _AUDIT.report(limit) if _AUDIT is not None else "layout audit not installed"


def install(sbs_module) -> LayoutAudit:
    """Wrap the module's send_gui_* senders with recording taps. Idempotent."""
    global _AUDIT
    if getattr(sbs_module, "_layout_audit_installed", False):
        return _AUDIT
    _AUDIT = LayoutAudit()
    _AUDIT._resolve_console = getattr(sbs_module, "get_type_of_client", None)

    def wrap_widget(name, rect_at):
        orig = getattr(sbs_module, name)

        def tap(clientID, *args, **kw):
            try:
                parent, tag = args[0], args[1]
                style = args[2] if name not in ("send_gui_face", "send_gui_slider") else (
                    args[3] if name == "send_gui_slider" else "")
                l, t, r, b = args[rect_at:rect_at + 4]
                _AUDIT.record(name, clientID, parent, tag, _draw_layer(style), l, t, r, b)
            except Exception:
                pass  # never let the tap perturb a run
            return orig(clientID, *args, **kw)
        setattr(sbs_module, name, tap)

    for name, rect_at in _RECT_AT.items():
        if hasattr(sbs_module, name):
            wrap_widget(name, rect_at)

    if hasattr(sbs_module, "send_gui_clear"):
        _oc = sbs_module.send_gui_clear
        def clear_tap(clientID, tag, *a, **k):
            try: _AUDIT.clear(clientID, tag)
            except Exception: pass
            return _oc(clientID, tag, *a, **k)
        sbs_module.send_gui_clear = clear_tap

    if hasattr(sbs_module, "send_gui_complete"):
        _oco = sbs_module.send_gui_complete
        def complete_tap(clientID, tag, *a, **k):
            try: _AUDIT.complete(clientID, tag)
            except Exception: pass
            return _oco(clientID, tag, *a, **k)
        sbs_module.send_gui_complete = complete_tap

    sbs_module._layout_audit_installed = True
    return _AUDIT
