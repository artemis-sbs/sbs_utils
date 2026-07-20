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
# Overshoot is RESOLUTION-DEPENDENT: layouts mix percent with fixed px/em units, so a
# fixed row/font takes a different fraction of a %-derived region as the window
# resizes (small windows = worst case). So don't desensitize to a single resolution —
# the valuable audit sweeps aspect ratios and takes the WORST case (see LAYOUT_AUDIT.md).
EPS = 0.5          # percent slop before a rect counts as "out of region"
MIN_OVERLAP = 1.0  # percent^2 min intersection area before flagging overlap
TEXT_EPS_PX = 2.0  # pixel slop before drawn text counts as not fitting its box

# Widget kinds whose args[2] is a props string carrying the drawn text.
_TEXT_KINDS = frozenset({"text", "button"})

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


#
# Local copies of the props parsing, kept deliberately tiny. This module is a
# dependency-free tap -- importing sbs_utils here would couple the audit to the
# very library it audits.
#
def _prop(props: str, key: str):
    """Value of `key` in a props string, honouring backtick quoting."""
    i = 0
    n = len(props)
    while i < n:
        colon = props.find(":", i)
        if colon == -1:
            return None
        k = props[i:colon].strip()
        j = colon + 1
        while j < n and props[j] == " ":
            j += 1
        if j < n and props[j] == "`":          # opaque: ':'/';' inside are literal
            close = props.find("`", j + 1)
            end = props.find(";", close + 1) if close != -1 else -1
        else:
            end = props.find(";", colon)
        val = props[colon + 1:] if end == -1 else props[colon + 1:end]
        if k == key:
            return val
        if end == -1:
            return None
        i = end + 1
    return None


def _display_text(props: str) -> str:
    if not props:
        return ""
    val = _prop(props, "$text")
    if val is None:
        val = _prop(props, "text")
    if val is None:
        return "" if ":" in props else props.strip()
    val = val.strip()
    if len(val) >= 2 and val.startswith("`") and val.endswith("`"):
        val = val[1:-1]
    return val


def _props_font(props: str):
    f = _prop(props or "", "font")
    f = f.strip() if f else ""
    return f or None


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
    __slots__ = ("cid", "parent", "tag", "kind", "layer", "l", "t", "r", "b", "msg")

    def __init__(self, cid, parent, tag, kind, layer, l, t, r, b, msg=None):
        self.cid, self.parent, self.tag, self.kind, self.layer = cid, parent, tag, kind, layer
        self.l, self.t, self.r, self.b = float(l), float(t), float(r), float(b)
        self.msg = msg


class LayoutAudit:
    def __init__(self):
        # live snapshot: (cid, tag) -> _Widget   (re-sends overwrite; the dirty
        # system re-emits each tick, so latest rect wins)
        self._live: dict = {}
        # region geometry, persistent across clear() -- see record()
        self._regions: dict = {}
        # deduped findings: key -> (kind, message)
        self._findings: dict = {}
        self._frames = 0
        # optional: sbs_module.get_type_of_client, to label WHICH console a
        # finding is on so it can be navigated to. Set by install().
        self._resolve_console = None
        # set by install(): the sbs module (for text metrics) and the screen
        # size in pixels. Without both, the text-fit check is skipped.
        self._sbs = None
        self._aspect = None
        self._text_cache = {}
        # Coverage, so "0 findings" is interpretable: it separates "measured
        # 500 labels, all fit" from "never measured anything". An audit that
        # cannot tell those apart is not worth trusting.
        self._text_checked = set()
        self._text_skipped = set()

    def _console(self, cid):
        try:
            return self._resolve_console(cid) if self._resolve_console else "?"
        except Exception:
            return "?"

    # -- recording -----------------------------------------------------------
    def record(self, sender, cid, parent, tag, layer, l, t, r, b, msg=None):
        w = _Widget(cid, parent, tag, _kind(sender), layer, l, t, r, b, msg)
        self._live[(cid, tag)] = w
        if w.kind == "sub_region":
            #
            # Region GEOMETRY is kept in its own map, deliberately outside the
            # clear() lifecycle. A region is declared and then immediately
            # cleared (Layout.region_begin sends send_gui_sub_region followed by
            # send_gui_clear on the same tag), so a region recorded only in
            # _live is erased the instant it is created -- which left the
            # text-fit check unable to resolve a pixel size for 86% of widgets.
            #
            self._regions[(cid, tag)] = w

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

            # 1b) does the TEXT fit the rect? (rects above are necessary but
            # not sufficient -- the engine draws unclipped past a correct box)
            if w.kind in _TEXT_KINDS:
                self._audit_text(w, con)

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

    # -- text fit ------------------------------------------------------------
    #
    # The checks above reason about RECTS. They cannot see a correctly sized
    # rect holding text too big for it -- and since the engine does not clip,
    # that text is drawn anyway, over whatever is next to or below it. This
    # check closes that gap by measuring what will actually be drawn.
    #
    # Rects are percent-local to the parent region at every depth, so a pixel
    # comparison needs the parent region's true pixel size: walk the
    # sub_region chain up to the root and multiply.
    #
    def _region_px(self, cid, tag, seen=None):
        """(width_px, height_px) of a region, or None if unresolvable."""
        if self._aspect is None:
            return None
        if not tag:                      # root region == the whole screen
            return self._aspect
        if seen is None:
            seen = set()
        if tag in seen:                  # malformed tree; do not spin
            return None
        seen.add(tag)
        w = self._regions.get((cid, tag))
        if w is None:
            return None
        parent = self._region_px(cid, w.parent, seen)
        if parent is None:
            return None
        return (parent[0] * (w.r - w.l) / 100.0,
                parent[1] * (w.b - w.t) / 100.0)

    def _audit_text(self, w, con):
        if self._sbs is None or self._aspect is None or not w.msg:
            return
        text = _display_text(w.msg)
        if not text:
            return
        region = self._region_px(w.cid, w.parent)
        if region is None:
            self._text_skipped.add((w.cid, w.tag))
            return
        box_w = region[0] * (w.r - w.l) / 100.0
        box_h = region[1] * (w.b - w.t) / 100.0
        if box_w <= 1 or box_h <= 1:
            self._text_skipped.add((w.cid, w.tag))
            return
        self._text_checked.add((w.cid, w.tag))

        # A font declared in the widget's own props wins at render time. When
        # none is declared we do NOT guess a default -- we measure with the
        # SMALLEST font, so a finding means "overflows even at the smallest
        # font". That trades recall for precision: every finding is real.
        font = _props_font(w.msg)
        assumed = font is None
        if assumed:
            font = "smallest"

        key = (font, text, int(box_w))
        got = self._text_cache.get(key)
        if got is None:
            try:
                line_w = self._sbs.get_text_line_width(font, text)
                block_h = self._sbs.get_text_block_height(font, text, max(1, int(box_w)))
            except Exception:
                return
            got = (line_w, block_h)
            self._text_cache[key] = got
        line_w, block_h = got

        note = " (font assumed 'smallest')" if assumed else f" (font {font})"
        short = text if len(text) <= 40 else text[:37] + "..."

        if line_w > box_w + TEXT_EPS_PX:
            self._add((w.cid, w.tag, "text_wide"), "TEXT_WIDE",
                      f"({con}) [{w.kind}] {w.tag} in <{w.parent}> text {short!r} "
                      f"needs {line_w:.0f}px, box is {box_w:.0f}px{note}")
        if block_h > box_h + TEXT_EPS_PX:
            self._add((w.cid, w.tag, "text_tall"), "TEXT_TALL",
                      f"({con}) [{w.kind}] {w.tag} in <{w.parent}> text {short!r} "
                      f"wraps to {block_h:.0f}px, box is {box_h:.0f}px{note}")

    # -- report --------------------------------------------------------------
    def report(self, limit=40):
        counts = {"OVERFLOW": 0, "OVERLAP": 0, "DEGENERATE": 0,
                  "TEXT_WIDE": 0, "TEXT_TALL": 0}
        for kind, _ in self._findings.values():
            counts[kind] = counts.get(kind, 0) + 1
        if not self._aspect or self._sbs is None:
            text_note = "  (text-fit check OFF)"
        else:
            text_note = (f"  [measured {len(self._text_checked)} text widgets, "
                         f"{len(self._text_skipped)} skipped]")
        lines = ["", "=" * 60,
                 f"LAYOUT AUDIT  ({self._frames} frames audited)",
                 f"  OVERFLOW={counts['OVERFLOW']}  OVERLAP={counts['OVERLAP']}  "
                 f"DEGENERATE={counts['DEGENERATE']}  total={len(self._findings)}",
                 f"  TEXT_WIDE={counts['TEXT_WIDE']}  TEXT_TALL={counts['TEXT_TALL']}"
                 f"{text_note}",
                 "-" * 60]
        if counts["TEXT_WIDE"] or counts["TEXT_TALL"]:
            lines += [
                "  Reading the text findings (the engine does not clip, so"
                " anything that",
                "  does not fit is DRAWN over its neighbours):",
                "    TEXT_TALL             - real: wraps to more height than the"
                " box has,",
                "                            so it spills into whatever is below.",
                "    TEXT_WIDE + TEXT_TALL - real: too big in both axes.",
                "    TEXT_WIDE alone       - usually benign: the line is longer"
                " than the box",
                "                            but it wraps and still fits the"
                " height.",
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


def install(sbs_module, aspect=None) -> LayoutAudit:
    """Wrap the module's send_gui_* senders with recording taps. Idempotent.

    `aspect` is the screen size in pixels as (width, height). It is required
    for the text-fit check (TEXT_WIDE / TEXT_TALL), which converts a widget's
    percent-local rect into pixels to compare against measured text. Omit it
    and only the rect checks run.
    """
    global _AUDIT
    if getattr(sbs_module, "_layout_audit_installed", False):
        return _AUDIT
    _AUDIT = LayoutAudit()
    _AUDIT._resolve_console = getattr(sbs_module, "get_type_of_client", None)
    # Text metrics come from the module under audit, so the audit measures with
    # exactly the same numbers the layout did.
    if all(hasattr(sbs_module, n) for n in
           ("get_text_line_width", "get_text_block_height")):
        _AUDIT._sbs = sbs_module
    if aspect is not None:
        _AUDIT._aspect = (float(aspect[0]), float(aspect[1]))

    def wrap_widget(name, rect_at):
        orig = getattr(sbs_module, name)

        def tap(clientID, *args, **kw):
            try:
                parent, tag = args[0], args[1]
                style = args[2] if name not in ("send_gui_face", "send_gui_slider") else (
                    args[3] if name == "send_gui_slider" else "")
                l, t, r, b = args[rect_at:rect_at + 4]
                # For text-bearing widgets args[2] IS the props string holding
                # the drawn text, so `style` doubles as the message.
                msg = style if _kind(name) in _TEXT_KINDS else None
                _AUDIT.record(name, clientID, parent, tag, _draw_layer(style),
                              l, t, r, b, msg)
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
