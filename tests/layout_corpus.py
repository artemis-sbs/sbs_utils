"""A deterministic corpus of layout configurations, and their computed geometry.

Support module for test_layout_geometry_golden.py. Kept separate so the corpus
can also be driven by hand when investigating a geometry change.

The point is to pin CURRENT behaviour before refactoring Layout.calc. A real
mission run is unusable as a gate -- the runner plays N sim-seconds of real
time, so how many frames (and therefore how many layouts) get built varies with
machine load. This corpus is pure: same input, same numbers, every run.

Coverage is aimed at the parts of calc that interact, since those are what a
refactor breaks: flex vs fixed vs square columns, Hole donation, the box model,
font cascade (which drives em sizing), orientation, nesting, and several aspect
ratios (percent and fixed units diverge as the window changes).
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.hole import Hole
from sbs_utils.pages.layout.grid import Grid
from sbs_utils.pages.layout.group import Group
from sbs_utils.pages.layout.repeater import Repeater

ASPECTS = [(1024, 768), (1920, 1080), (3440, 1440)]


def _col(width=None, square=False, font=None, style=None):
    c = Hole() if width == "hole" else Column()
    if width not in (None, "hole"):
        c.set_col_width(StyleDefinition.parse(f"col-width: {width};")["col-width"])
    c.square = square
    c.default_font = font
    if style:
        parsed = StyleDefinition.parse(style)
        c.margin_style = parsed.get("margin")
        c.border_style = parsed.get("border")
        c.padding_style = parsed.get("padding")
    return c


def _row(cols, height=None, font=None, style=None):
    r = Row()
    for c in cols:
        r.add(c)
    if height is not None:
        r.set_row_height(StyleDefinition.parse(f"row-height: {height};")["row-height"])
    r.default_font = font
    if style:
        parsed = StyleDefinition.parse(style)
        r.margin_style = parsed.get("margin")
        r.border_style = parsed.get("border")
        r.padding_style = parsed.get("padding")
    return r


def cases():
    """(name, Layout) pairs. Deterministic and order-stable."""
    out = []

    def add(name, rows, **kw):
        sec = Layout(name, rows, kw.pop("left", 0), kw.pop("top", 0),
                     kw.pop("right", 100), kw.pop("bottom", 100))
        for k, v in kw.items():
            setattr(sec, k, v)
        out.append((name, sec))

    # --- flex only ---------------------------------------------------------
    add("flex_1x1", [_row([_col()])])
    add("flex_1x3", [_row([_col(), _col(), _col()])])
    add("flex_3x3", [_row([_col(), _col(), _col()]) for _ in range(3)])
    add("flex_1x7", [_row([_col() for _ in range(7)])])

    # --- fixed widths mixed with flex --------------------------------------
    add("fixed_one", [_row([_col(50), _col()])])
    add("fixed_two_flex_one", [_row([_col(30), _col(30), _col()])])
    add("fixed_all", [_row([_col(25), _col(25), _col(50)])])
    add("fixed_px", [_row([_col("200px"), _col()])])
    add("fixed_em", [_row([_col("4em"), _col()])])
    add("fixed_overflowing", [_row([_col(60), _col(60), _col()])])
    add("fixed_expr_min", [_row([_col("min(30,40)"), _col()])])

    # --- fixed / flex row heights ------------------------------------------
    add("rows_fixed_one", [_row([_col()], height=20), _row([_col()])])
    add("rows_fixed_px", [_row([_col()], height="35px"), _row([_col()])])
    add("rows_fixed_em", [_row([_col()], height="2em"), _row([_col()])])
    add("rows_all_fixed", [_row([_col()], height=30), _row([_col()], height=30)])
    add("rows_overflowing", [_row([_col()], height=70), _row([_col()], height=70)])

    # --- squares (their size depends on ROW HEIGHT -- the width/height knot)
    add("square_only", [_row([_col(square=True)])])
    add("square_plus_flex", [_row([_col(square=True), _col()])])
    add("square_plus_fixed", [_row([_col(square=True), _col(40)])])
    add("squares_many", [_row([_col(square=True) for _ in range(4)])])
    add("square_short_row", [_row([_col(square=True), _col()], height=10)])
    add("square_tall_row", [_row([_col(square=True), _col()], height=80)])
    # 3 cols + one fixed + a tall row: the case where the square clamp fires
    add("square_clamp", [_row([_col(60), _col(), _col()], height=90)])

    # --- holes (donate their width to the NEXT column) ----------------------
    add("hole_lead", [_row([_col("hole"), _col()])])
    add("hole_middle", [_row([_col(), _col("hole"), _col()])])
    add("hole_two", [_row([_col("hole"), _col("hole"), _col()])])
    add("hole_with_fixed", [_row([_col(30), _col("hole"), _col()])])

    # --- box model ----------------------------------------------------------
    add("margin_col", [_row([_col(style="margin: 2,2,2,2;"), _col()])])
    add("padding_col", [_row([_col(style="padding: 3,3,3,3;"), _col()])])
    add("border_col", [_row([_col(style="border: 1,1,1,1;"), _col()])])
    add("box_all_col", [_row([_col(style="margin:1,1,1,1;border:1,1,1,1;padding:2,2,2,2;"), _col()])])
    add("box_row", [_row([_col(), _col()], style="margin:2,2,2,2;padding:1,1,1,1;")])

    # --- fonts drive em sizing ---------------------------------------------
    add("font_row", [_row([_col("2em"), _col()], font="gui-4")])
    add("font_col", [_row([_col("2em", font="gui-6"), _col()])])
    add("font_mixed", [_row([_col("2em", font="gui-1"), _col("2em", font="gui-5")])])

    # --- section-level defaults cascade ------------------------------------
    sec_rows = [_row([_col(), _col()]), _row([_col(), _col()])]
    add("section_row_height", sec_rows, default_height=25.0)
    add("section_font", [_row([_col("3em"), _col()])], default_font="gui-5")

    # --- orientation --------------------------------------------------------
    add("orient_bt", [_row([_col()], height=20), _row([_col()])], orientation=1)

    # --- non-default section bounds ----------------------------------------
    add("offset_section", [_row([_col(), _col()])], left=10, top=20, right=90, bottom=80)

    # --- nesting (a Layout stored AS a column) ------------------------------
    inner = Layout("inner", [_row([_col(), _col()])], 0, 0, 100, 100)
    add("nested", [_row([inner, _col()])])

    inner2 = Layout("inner2", [_row([_col(30), _col()])], 0, 0, 100, 100)
    inner2.margin_style = StyleDefinition.parse("margin: 2,2,2,2;")["margin"]
    add("nested_box", [_row([inner2, _col()])])

    # --- additive containers (Grid / Group / Repeater) ----------------------
    # These emit only standard Row/Column into a Layout, so their geometry is
    # produced by the same calc the cases above pin. Content sizing made
    # col-width auto the (minimum-aware) DEFAULT -- a change that reaches every
    # un-widthed grid/group cell -- so pin the containers too, not just the
    # primitives they build on.
    def add_layout(name, sec):
        out.append((name, sec))

    def _grid(name, columns, n_cells, col_width=None, row_height=None, **kw):
        g = Grid(columns, col_width=col_width, row_height=row_height)
        for _ in range(n_cells):
            g.add(_col())
        sec = Layout(name, None, kw.pop("left", 0), kw.pop("top", 0),
                     kw.pop("right", 100), kw.pop("bottom", 100))
        g.build(sec)
        add_layout(name, sec)

    # short final row is Hole-padded; exercises the default (1fr) cell width
    _grid("grid_2col_flex", 2, 3)
    _grid("grid_3col_fixed", 3, 5, col_width=20.0)
    _grid("grid_2col_rowh", 2, 4, row_height=20.0)
    _grid("grid_4col_short_last", 4, 6)

    # Group: a titled/bordered Layout; the title row is fixed, content is flex.
    # Default border ("4px") exercises the border box on the section.
    grp = Group("grp_titled", title="Sensors", left=5, top=5, right=95, bottom=70)
    grp.add(_row([_col(), _col()]))
    grp.add(_row([_col(30), _col()]))
    add_layout("group_titled", grp.build())

    grp2 = Group("grp_plain", title=None, border_color=None)
    grp2.add(_row([_col()]))
    grp2.add(_row([_col(), _col()]))
    add_layout("group_plain", grp2.build())

    # Repeater: template-expanded cells over a data list (built on Grid)
    rep1 = Repeater(1, factory=lambda item, i: _col())
    sec = Layout("rep_1col", None, 0, 0, 100, 100)
    rep1.build([0, 1, 2], sec)
    add_layout("repeater_1col", sec)

    rep2 = Repeater(2, factory=lambda item, i: _col(), row_height=15.0)
    sec = Layout("rep_2col", None, 0, 0, 100, 100)
    rep2.build([0, 1, 2, 3, 4], sec)
    add_layout("repeater_2col", sec)

    return out


def geometry():
    """Every case at every aspect, as flat comparable lines.

    Returns a list of strings so a diff points straight at the offending
    row/column instead of just reporting 'the hash changed'.
    """
    lines = []
    for (w, h) in ASPECTS:
        FrameContext.aspect_ratios[0] = Vec3(w, h, 0)
        for name, sec in cases():
            sec.calc(0)
            lines.append(f"{w}x{h} {name} section {_fmt(sec.bounds)}")
            for ri, row in enumerate(sec.rows):
                lines.append(f"{w}x{h} {name} row{ri} "
                             f"l={row.left:.4f} t={row.top:.4f} "
                             f"w={row.width:.4f} h={row.height:.4f}")
                for ci, col in enumerate(row.columns):
                    lines.append(f"{w}x{h} {name} row{ri}col{ci} "
                                 f"{col.__class__.__name__} {_fmt(col.bounds)}")
    return lines


def _fmt(b):
    return f"l={b.left:.4f} t={b.top:.4f} r={b.right:.4f} b={b.bottom:.4f}"
