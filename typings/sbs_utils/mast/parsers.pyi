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
    def parse_list (tokens):
        ...
    def parse_values (tokens):
        ...
class StyleDefinition(object):
    """class StyleDefinition"""
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
