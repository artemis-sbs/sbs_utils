import re
import operator

class LayoutAreaNode:
    def __init__(self, token_type, value=None):
        self.token_type = token_type
        self.value = value
        self.children = []


class ContentSize:
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
    compute and not useful here.
    """
    __slots__ = ("mode",)

    MODES = ("content", "min-content", "max-content", "1fr")

    def __init__(self, mode="content"):
        self.mode = mode

    @property
    def is_min(self):
        return self.mode == "min-content"

    @property
    def is_max(self):
        return self.mode == "max-content"

    @property
    def is_auto(self):
        """Flex, but floored at min-content. Stays in the flex pool.

        Named `is_auto` for continuity with the `auto` alias; the canonical
        author-facing spelling of this mode is `1fr`.
        """
        return self.mode == "1fr"

    def __repr__(self):
        return f"ContentSize({self.mode})"

    def __eq__(self, other):
        return isinstance(other, ContentSize) and other.mode == self.mode

    def __hash__(self):
        return hash(("ContentSize", self.mode))


# Interned, since these are compared by identity in the hot path.
CONTENT = ContentSize("content")
MIN_CONTENT = ContentSize("min-content")
MAX_CONTENT = ContentSize("max-content")
AUTO = ContentSize("1fr")          # canonical spelling: `1fr` (alias: `auto`)
_CONTENT_BY_NAME = {c.mode: c for c in (CONTENT, MIN_CONTENT, MAX_CONTENT, AUTO)}
#
# CSS spellings accepted alongside ours. `auto` is the historical name for the
# `1fr` mode and is kept working; `fit-content` is what CSS calls `content`.
#
_CONTENT_BY_NAME["auto"] = AUTO
_CONTENT_BY_NAME["fit-content"] = CONTENT

# based on https://github.com/gnebehay/parser/blob/master/parser.py
class LayoutAreaParser:
    rules = {
        "ws": r"[ \t]+",
        #
        # MUST precede the NUMERIC rules: `1fr` begins with a digit, so "digits"
        # would take the 1 and leave "fr" as an identifier. It must also precede
        # "max"/"min", which are unanchored prefixes that would otherwise steal
        # the front of "max-content"/"min-content" and leave `-content` behind
        # -- which parse_func then rejects with "Invalid syntax on token minus".
        #
        # The \b keeps "contentious" and friends lexing as an id, exactly as
        # before. Where these keywords are SUPPORTED (row-height / col-width)
        # they never reach the lexer at all -- parse_width and parse_height
        # short-circuit on the raw string. This rule only makes them HARMLESS
        # elsewhere (inside area:, or mid-expression), where they evaluate to 1,
        # identical to the long-standing fallback for an unknown identifier.
        #
        "content": r"(fit-content|(min-|max-)?content|auto|1fr)\b",
        "pixels": r"\d+px",
        "ems": r"\d+(\.\d+)?em",
        "digits": r"\d+(\.\d+)?",
        "max": r"max",
        "min": r"min",
        "id": r"[_a-zA-Z][_a-zA-Z0-9]*",
        "comma": r",",
        "plus": r"\+",
        "minus": r"\-",
        "mul": r"\*",
        "div": r"\/",
        "lparen": r"\(",
        "rparen": r"\)",
        
    }
    #AREA_LIST_TOKENS = "|".join(map(lambda a: f"({a})", rules.values()))
    STYLE_LIST_TOKENS = r"[^\n^;]*"


    def lex(source):
        start = len(source)
        tokens=[]
        while(len(source)>0):
            match = False
            for token,rule in LayoutAreaParser.rules.items():
                m = re.match(rule,source)
                if m is not None:
                    match = True
                    loc = m.span()
                    t = source[:loc[1]]
                    source = source[loc[1]:]
                    if token!= "ws":
                        tokens.append(LayoutAreaNode(token, t))
                    break
            #
            # `match` used to be set unconditionally above, which made this
            # branch dead: a character no rule matches (e.g. '%') left `source`
            # unchanged and the while loop spun forever -- a hang, not an error.
            #
            if not match:
                raise Exception(f"Invalid syntax on token {source}")

        tokens.append(LayoutAreaNode("eof", None))
        return tokens

    def match(tokens, token):
        if tokens[0].token_type == token:
            return tokens.pop(0)
        else:
            raise Exception('Invalid syntax on token {}'.format(tokens[0].token_type))        

    def parse_e(tokens):
        left_node = LayoutAreaParser.parse_e2(tokens)

        while tokens[0].token_type in ["plus", "minus"]:
            node = tokens.pop(0)
            node.children.append(left_node)
            node.children.append(LayoutAreaParser.parse_e2(tokens))
            left_node = node
            # if len(self.tokens)==0:
            #     return left_node
        return left_node

    def parse_e2(tokens):
        if tokens[0].token_type in ["min","max"]:
            return LayoutAreaParser.parse_func(tokens)
        left_node = LayoutAreaParser.parse_values(tokens)
        while tokens[0].token_type in ["mul", "div"]:
            node = tokens.pop(0)
            node.children.append(left_node)
            node.children.append(LayoutAreaParser.parse_values(tokens))
            left_node = node
            # if len(self.tokens)==0:
            #     return left_node
        return left_node


    def parse_func(tokens):
        while tokens[0].token_type in ["max", "min"]:
            node = tokens.pop(0)
            LayoutAreaParser.match(tokens,"lparen")
            node.children.append(LayoutAreaParser.parse_e(tokens))
            LayoutAreaParser.match(tokens, "comma")
            node.children.append(LayoutAreaParser.parse_e(tokens))
            LayoutAreaParser.match(tokens, "rparen")
            left_node = node
        return left_node

    def parse_values(tokens):
        if tokens[0].token_type in ["ems","pixels", "digits", "id", "content"]:
            return tokens.pop(0)
        LayoutAreaParser.match(tokens,"lparen")
        expression = LayoutAreaParser.parse_e(tokens)
        LayoutAreaParser.match(tokens, "rparen")
        return expression

    def parse_list(tokens):
        expressions = []
        while len(tokens):
            expression = LayoutAreaParser.parse_e(tokens)
            expressions.append(expression)
            if tokens[0].token_type == "comma":
                tokens.pop(0)
                continue
            elif tokens[0].token_type == "eof":
                break
            else:
                raise Exception('Invalid syntax on token {}'.format(tokens[0].token_type))            
        return expressions

    operations = {
        "plus": operator.add,
        "minus": operator.sub,
        "mul": operator.mul,
        "div": operator.truediv
    }

    def compute(node, vars, aspect_ratio, font_size=20):
        match node.token_type:
            case "digits":
                return float(node.value)
            #
            # font_size is threaded through EVERY recursion below. It used to be
            # dropped, so an `em` anywhere except at the top of an expression
            # silently fell back to the default 20 -- `1em+10px` on a gui-3 row
            # computed 20px+10px instead of 28px+10px. Same class of silent
            # wrongness as the dropped `+` term itself.
            #
            case "max":
                x = float(LayoutAreaParser.compute(node.children[0], vars, aspect_ratio, font_size))
                y = float(LayoutAreaParser.compute(node.children[1], vars, aspect_ratio, font_size))
                return max(x,y)
            case "min":
                x = float(LayoutAreaParser.compute(node.children[0], vars, aspect_ratio, font_size))
                y = float(LayoutAreaParser.compute(node.children[1], vars, aspect_ratio, font_size))
                return min(x,y)
            case "pixels":
                return (float(node.value[:-2])/aspect_ratio)*100
            case "ems":
                return (float(node.value[:-2])*font_size/aspect_ratio)*100
            case "id":
                if vars is not None and node.value in vars:
                    return vars[node.value]
                return 1  #node.value
            case "content":
                # Only reachable where a content size is NOT supported (inside
                # area:/padding:/margin:/border:, or in an expression). Return
                # 1, matching the long-standing fallback for an unknown id, so
                # this stays a no-op rather than a new failure mode.
                return 1

        left_result = LayoutAreaParser.compute(node.children[0], vars, aspect_ratio, font_size)
        right_result = LayoutAreaParser.compute(node.children[1], vars, aspect_ratio, font_size)
        operation = LayoutAreaParser.operations[node.token_type]
        return operation(left_result, right_result)


class StyleDefinition:
    styles = {}
    def parse(style):
        ret = {}
        rules = style.split(";")
        for rule in rules:
            rule = rule.strip()
            if len(rule)<1:
                continue
            item = rule.split(":")
            key = item[0]
            value = item[1]
            match key:
                case "area":
                    ret[key]=StyleDefinition.parse_area(value)
                case "padding":
                    ret[key]=StyleDefinition.parse_bounds(value)
                case "row-height":
                    ret[key]=StyleDefinition.parse_height(value)
                case "col-width":
                    ret[key]=StyleDefinition.parse_width(value)
                case "margin":
                    ret[key]=StyleDefinition.parse_bounds(value)
                case "border":
                    ret[key]=StyleDefinition.parse_bounds(value)
                case "overflow":
                    ret[key]=value
                case "background":
                    ret[key]=value
                case "background-color":
                    ret[key]=value
                case "background-image":
                    ret[key]=value
                case "border-image":
                    ret[key]=value
                case "color":
                    ret[key]=value
                case "justify":
                    ret[key]=value
                case "font":
                    ret[key]=value
                case "border-color":
                    ret[key]=value
                case "click_text":
                    ret[key]=value
                case "click_background":
                    ret[key]=value
                case "click_color":
                    ret[key]=value
                case "click_font":
                    ret[key]=value
                case "click_tag":
                    ret[key]=value
                case "tag":
                    ret[key]=value
                case "orientation":
                    ret[key]=value
        return ret

    def parse_area(area):
        tokens = LayoutAreaParser.lex(area)
        asts = LayoutAreaParser.parse_list(tokens)
        if (len(asts)!=4):
            raise Exception("Invalid area arguments")
        return asts

    def parse_bounds(padding):
        if padding is not None:
            tokens = LayoutAreaParser.lex(padding)
            return LayoutAreaParser.parse_list(tokens)
        return None
    
    #
    # `col-width:` / `row-height:` are the only two places a content size is
    # meaningful, and these are their only entry points -- so intercepting the
    # bare keyword here is complete, and keeps ContentSize out of lex/compute
    # entirely. Every existing expression takes the unchanged path below.
    #
    def _content_size(value):
        if value is None:
            return None
        return _CONTENT_BY_NAME.get(value.strip().lower())

    #
    # parse_e, NOT parse_e2. parse_e2 handles only * and /, so a `+` or `-` term
    # was lexed and then SILENTLY DROPPED: `row-height: 1em+10px` computed to
    # exactly `1em`, and `col-width: 62-25px` to exactly `62`. No error, no
    # warning -- the author's arithmetic just evaporated, which is how
    # LegendaryMissions' document screen has been running with a column 25px
    # wider than it asked for.
    #
    # `area:` never had this problem because it parses through parse_list ->
    # parse_e, which is why `area: 0, 50px, 100, 95-10px` works and the same
    # expression in row-height does not. These two entry points were simply
    # wired to the wrong level of the grammar.
    #
    def parse_width(width):
        if width is not None:
            content = StyleDefinition._content_size(width)
            if content is not None:
                return content
            tokens = LayoutAreaParser.lex(width)
            return LayoutAreaParser.parse_e(tokens)
        return None

    def parse_height(height):
        if height is not None:
            content = StyleDefinition._content_size(height)
            if content is not None:
                return content
            tokens = LayoutAreaParser.lex(height)
            return LayoutAreaParser.parse_e(tokens)
        return None



