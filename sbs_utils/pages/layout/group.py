"""Group / Panel — an *additive* titled, bordered frame.

A Group is just a standard ``Layout`` (section) configured with a border and an
optional title row — no new render path, so the engine lays it out and draws its
border exactly as it does any bordered section. You fill it with content rows the
same way you fill a Layout.

    grp = Group("sensors", title="Sensors")
    grp.add(my_row)              # add content rows
    grp.layout                   # the underlying Layout to present/add to a page

Because it only sets attributes the layout engine already honours
(``border_style``/``border_color`` + a title ``Row`` holding a ``Text``), it
can't introduce a new failure mode; a Group with no border/title is an ordinary
Layout.
"""
from .layout import Layout
from .row import Row
from .text import Text
from ...mast.parsers import StyleDefinition


class Group:
    def __init__(self, tag, title=None, left=0, top=0, right=100, bottom=50,
                 border_color="#3af", border_style="4px",
                 title_height=6.0, title_font="gui-2", title_color=None):
        self.tag = tag
        self.layout = Layout(tag, None, left, top, right, bottom)
        if border_color is not None:
            self.layout.border_color = border_color
            # calc() runs border_style through the layout-area parser, which needs
            # the parsed node form (as StyleDefinition produces) -- a raw string
            # like "4px" crashes at layout time. Parse a string here; a value that
            # is already parsed (a caller passing a node) is passed through.
            if isinstance(border_style, str):
                border_style = StyleDefinition.parse(f"border: {border_style};")["border"]
            self.layout.border_style = border_style
        self.title_row = None
        if title is not None:
            self.title_row = self._make_title(title, title_height, title_font, title_color)
            self.layout.add(self.title_row)

    def _make_title(self, title, height, font, color):
        row = Row()
        if height is not None:
            row.set_row_height(height)        # keep the title off the flex share
        text = Text(f"{self.tag}:title", f"$text:{title}")
        if font is not None:
            text.default_font = font
        if color is not None:
            text.default_color = color
        row.add(text)
        return row

    def add(self, row):
        """Add a content Row to the group. Returns self."""
        self.layout.add(row)
        return self

    def add_all(self, rows):
        for r in rows:
            self.add(r)
        return self

    def build(self):
        """Return the underlying Layout (for presenting / adding to a page)."""
        return self.layout
