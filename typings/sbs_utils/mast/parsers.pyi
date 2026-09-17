def _fr_text (weight):
    """`2.0` as `2fr`, `1.5` as `1.5fr` - how the author would have written it."""
def _weighted_fr (name):
    """`Nfr` as a weighted flex size, or None when this is not one.
    
    `1fr` never reaches here - it is in `_CONTENT_BY_NAME` and comes back as the
    interned AUTO, so the identity comparisons in the layout hot path are
    untouched by this feature existing.
    
    **A weight of zero is refused**, and loudly. CSS gives a `0fr` item none of
    the leftover space, which here would be a row of no height that still DRAWS
    its text - the engine does not clip, so it would land on the row above. That
    is the exact shape of LM issue 672, and it is not worth reintroducing for a
    spelling nobody needs: a row that should not be seen is `gui_blank()` or is
    not built."""
def flex_weight (size):
    """How many shares of the leftover space this size asks for.
    
    1 for everything that is not a weighted `Nfr`, which keeps every existing
    layout exactly where it was: an even split IS a weighted split when every
    weight is 1."""
class ContentSize(object):
    """A `row-height:`/`col-width:` value that means "size to the content".
    
    Deliberately NOT a LayoutAreaNode. Every other size value is an expression
    the parser evaluates to a percentage up front; a content size cannot be
    resolved until the widgets are known, so it travels through the layout as
    an opaque marker and is interpreted by Layout.calc.
    
    Modes follow CSS:
      max-content  the text on one unbroken line
      min-content  the widest unbreakable word
      content      fit-content -- the natural size, clamped to what is available
      1fr          still FLEX, but never squeezed below its min-content
    
    NAMES follow CSS, and `1fr` is deliberate. This mode is an equal share of
    the leftover space with a minimum -- which CSS spells `1fr` (grid) or
    `flex: 1` (flexbox). CSS's own `auto` means something DIFFERENT: size to
    your content and shrink under pressure. Anyone arriving from CSS reads
    `auto` and predicts the opposite of what happens, and since this is the
    DEFAULT mode, its name is what people assume without looking.
    
    `auto` is still accepted as an alias, and today the two are identical. The
    point of introducing `1fr` while that is true is migration: if `auto` is
    ever given its CSS meaning, only scripts that explicitly wrote `auto` change
    behaviour, and they will be few.
    
    `fit-content` is likewise accepted as an alias of `content`, since that is
    what CSS calls it.
    
    `auto` is the odd one out and the one that answers LM issue 672. The other
    three take a column OUT of the flex pool and give it a size of its own.
    `auto` leaves it in the pool -- it still shares the leftover space -- but
    puts a floor under it, so a column with a long string grows and its
    roomier neighbours give way. Because col-width cascades col -> row ->
    section, putting `auto` on a row or a section makes every column in it
    minimum-aware without annotating any of them.
    
    On a ROW, `min-content` is an intentional alias of `content`: a true CSS
    row min-content (height when wrapped as narrow as possible) is expensive to
    compute and not useful here."""
    def __eq__ (self, other):
        """Return self==value."""
    def __hash__ (self):
        """Return hash(self)."""
    def __init__ (self, mode='content', weight=1.0):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
    @property
    def is_auto (self):
        """Flex, but floored at min-content. Stays in the flex pool.
        
        Named `is_auto` for continuity with the `auto` alias; the canonical
        author-facing spelling of this mode is `1fr`."""
    @property
    def is_max (self):
        ...
    @property
    def is_min (self):
        ...
class LayoutAreaNode(object):
    """class LayoutAreaNode"""
    def __init__ (self, token_type, value=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class LayoutAreaParser(object):
    """class LayoutAreaParser"""
    def compute (node, vars, aspect_ratio, font_size=20):
        ...
    def lex (source):
        ...
    def match (tokens, token):
        ...
    def parse_e (tokens):
        ...
    def parse_e2 (tokens):
        ...
    def parse_func (tokens):
        ...
    def parse_list (tokens):
        ...
    def parse_values (tokens):
        ...
class StyleDefinition(object):
    """class StyleDefinition"""
    def _content_size (value):
        ...
    def parse (style):
        ...
    def parse_area (area):
        ...
    def parse_bounds (padding):
        ...
    def parse_height (height):
        ...
    def parse_width (width):
        ...
