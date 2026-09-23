"""A gauge: label, value and a bar colored by how full it is.

The engine's own status panels draw this everywhere (Energy 946 over a green bar,
FRNT SHLD 45 over an orange one, ENGN/WEAP/SHLD/SENS in a grid). There is no
engine bar widget - no `send_gui_bar` - so a gauge is text plus two
`image:smallwhite` rects, the same primitive `HrLine` draws a rule with.

ONE drawer, two hosts:

* `gui_text_area` draws it as a block line or a table cell
  (`[Energy](gauge://946?max=1000)`). The text area rebuilds everything on any
  change, so that host is for values that change at human rates.
* `gui_gauge` (`Gauge` below) is a layout widget that repaints only itself through
  the dirty system - the host for a value that changes every tick.

Above max the bar is full and turns the engineering console's TUNED cyan, and
the number (value, frac or pct - "120%") is the real one, not the clamped one.

The fill and the track are drawn SIDE BY SIDE, never stacked: the engine's order
between two images on the same layer is not something to rely on, and rects that
do not overlap have no order to get wrong.
"""
from .column import Column
from .measure import measure_line_height, measure_line_width, px_to_pct_x, px_to_pct_y
from ...helpers import FrameContext, gui_text_escape

# Bar thickness and the gap above it, in PIXELS (screen-relative like every
# other measurement here, so converted with the client's aspect ratio).
BAR_PX = 4
GAP_PX = 2

COLOR_OK = "#2c2"
COLOR_WARN = "#e80"
COLOR_CRIT = "#e22"
COLOR_TRACK = "#333"
# Over max - the engineering console's TUNED cyan (procedural.grid.GRID_TUNED_COLOR),
# so a boosted system reads the same on a gauge as on the grid. Copied rather than
# imported to keep layout free of the procedural grid module; a test pins them equal.
COLOR_OVER = "#40E0E0"

DEFAULT_WARN = 0.5
DEFAULT_CRIT = 0.25

SHOW_MODES = ("value", "frac", "pct", "none")


def _num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _fmt(v):
    """946.0 -> "946", 0.25 -> "0.25"."""
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _flag(v):
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


def gauge_spec(value, max=100, label="", show=None, warn=None, crit=None,
               color=None, font="gui-2", invert=False):
    """Normalise gauge inputs into one dict. Nothing here raises: a bad number
    costs that number (it falls back to a default), not the whole panel.

    `invert` is for a value where MORE is WORSE - wear, heat, damage taken. The bar
    still grows with the value; only the colors turn round: green while low, yellow
    past `1 - warn`, red past `1 - crit`, and over max it is red, not tuned cyan."""
    v = _num(value, 0.0)
    m = _num(max, 100.0)
    label = "" if label is None else str(label)
    if show not in SHOW_MODES:
        # A labelled gauge reads like the engine's "Energy   946"; a bare bar
        # (the ENGN cell) has nowhere to put a number.
        show = "value" if label else "none"
    return {"value": v, "max": m, "label": label, "show": show,
            "warn": _num(warn, DEFAULT_WARN), "crit": _num(crit, DEFAULT_CRIT),
            "color": color or None, "font": font or "gui-2", "invert": _flag(invert)}


def gauge_spec_from_url(urn, label="", font="gui-2"):
    """`946?max=1000&show=frac&warn=0.4&invert=1` (after `gauge://`) -> spec."""
    from ...procedural.amd import amd_parse_url
    opts = amd_parse_url(urn)
    return gauge_spec(opts.get("url"), opts.get("max", 100), label,
                      opts.get("show"), opts.get("warn"), opts.get("crit"),
                      opts.get("color"), opts.get("font", font), opts.get("invert", False))


def gauge_fraction(spec):
    """0..1. Out-of-range values (the engine shows "-45 / 8") clamp the BAR;
    the number printed is still the raw value."""
    m = spec["max"]
    if m <= 0:
        return 0.0
    return min(1.0, max(0.0, spec["value"] / m))


def gauge_color(spec):
    if spec["color"]:
        return spec["color"]
    over = spec["max"] > 0 and spec["value"] > spec["max"]
    f = gauge_fraction(spec)
    if spec.get("invert"):
        if over:
            return COLOR_CRIT          # more-is-worse past its max is the worst case
        f = 1.0 - f                    # the thresholds measure how much is LEFT
    elif over:
        return COLOR_OVER
    if f < spec["crit"]:
        return COLOR_CRIT
    if f < spec["warn"]:
        return COLOR_WARN
    return COLOR_OK


def gauge_value_text(spec):
    show = spec["show"]
    if show == "value":
        return _fmt(spec["value"])
    if show == "frac":
        return f"{_fmt(spec['value'])} / {_fmt(spec['max'])}"
    if show == "pct":
        # The RAW ratio, not the clamped bar: a boosted system reads "120%".
        m = spec["max"]
        return f"{int(round(spec['value'] / m * 100)) if m > 0 else 0}%"
    return ""


def gauge_has_text(spec):
    return bool(spec["label"]) or spec["show"] != "none"


def gauge_height_px(spec):
    """Natural height: one line of text (if any) plus the bar."""
    h = BAR_PX + GAP_PX
    if gauge_has_text(spec):
        h += measure_line_height(spec["font"], "M")
    return h


def gauge_send(SBS, client_id, region_tag, tag, left, top, right, bottom, spec,
               ar, layer=None, justify="left"):
    """Draw one gauge into a rect (percent units, like every send_gui_*).

    `justify` places a label that stands ALONE (the ENGN cell is centred by its
    column); a label with a value is always label-left, value-right, the way the
    engine lays out "Energy ...... 946"."""
    lay = "" if layer is None else f"draw_layer:{int(layer)};"
    bar_h = px_to_pct_y(BAR_PX, ar)
    bar_top = bottom - bar_h
    text_bottom = bar_top - px_to_pct_y(GAP_PX, ar)

    font = spec["font"]
    label = spec["label"]
    value_text = gauge_value_text(spec)
    if gauge_has_text(spec) and text_bottom > top:
        base = f"font:{font};color:white;" + lay
        if label and value_text:
            SBS.send_gui_text(client_id, region_tag, f"{tag}:l",
                              f"$text:{gui_text_escape(label)};justify:left;{base}",
                              left, top, right, text_bottom)
            SBS.send_gui_text(client_id, region_tag, f"{tag}:v",
                              f"$text:{gui_text_escape(value_text)};justify:right;{base}",
                              left, top, right, text_bottom)
        else:
            SBS.send_gui_text(client_id, region_tag, f"{tag}:l",
                              f"$text:{gui_text_escape(label or value_text)};justify:{justify};{base}",
                              left, top, right, text_bottom)

    # Images default under text (1000 vs the engine's 1001), as HrLine does.
    img_layer = 1000 if layer is None else int(layer)
    split = left + (right - left) * gauge_fraction(spec)
    if split > left:
        SBS.send_gui_image(client_id, region_tag, f"{tag}:f",
                           f"image:smallwhite;color:{gauge_color(spec)};draw_layer:{img_layer};",
                           left, bar_top, split, bottom)
    if split < right:
        SBS.send_gui_image(client_id, region_tag, f"{tag}:t",
                           f"image:smallwhite;color:{COLOR_TRACK};draw_layer:{img_layer};",
                           split, bar_top, right, bottom)


class Gauge(Column):
    """`gui_gauge` - a gauge as a layout widget, for values that change often.

    `update()` repaints only this widget (visual-dirty); the text area host would
    re-parse and re-send its whole document for the same change."""

    def __init__(self, tag, value, max=100, label="", show=None, warn=None,
                 crit=None, color=None, invert=False) -> None:
        super().__init__()
        self.tag = tag
        self._args = {"value": value, "max": max, "label": label, "show": show,
                      "warn": warn, "crit": crit, "color": color, "invert": invert}

    def spec(self):
        return gauge_spec(font=self.get_font() or "gui-2", **self._args)

    def update(self, value=None, max=None, label=None, color=None):
        """Change any of value / max / label / color and repaint. Only what is
        passed changes."""
        changed = False
        for k, v in (("value", value), ("max", max), ("label", label), ("color", color)):
            if v is not None and self._args[k] != v:
                self._args[k] = v
                changed = True
        if not changed or self.is_hidden_by_script:
            return
        # Inside a sub-region (overlay slot, tab, listbox row) a widget CANNOT repaint
        # itself: the engine draws the re-sent value text OVER the old one instead of
        # replacing it - engine-seen here as "1" plus two overstruck digits while the
        # bar (an image) moved correctly. The region owner repaints (an overlay:
        # `overlay_patch`); see CycleButton.mark_value_dirty, the same rule.
        if self.region_tag:
            return
        self.mark_visual_dirty()

    @property
    def value(self):
        return self._args["value"]

    @value.setter
    def value(self, v):
        self.update(value=v)

    def measure(self, client_id, mode, avail_px, font, ar):
        # Height is natural. Width: a bar stretches, so it takes what it is offered;
        # with nothing offered yet, just the text it has to show.
        spec = self.spec()
        w_px = avail_px
        if not w_px:
            text = f"{spec['label']}  {gauge_value_text(spec)}".strip() or "MMMM"
            w_px = measure_line_width(spec["font"], text)
        return (px_to_pct_x(w_px, ar), px_to_pct_y(gauge_height_px(spec), ar))

    def _present(self, event):
        from ...gui import get_client_aspect_ratio
        ctx = FrameContext.context
        ar = get_client_aspect_ratio(event.client_id)
        b = self.bounds
        gauge_send(ctx.sbs, event.client_id, self.region_tag, self.tag,
                   b.left, b.top, b.right, b.bottom, self.spec(), ar,
                   self.get_layer())
