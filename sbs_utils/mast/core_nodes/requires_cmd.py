from ..mast_node import MastNode, mast_node
import re

#
# Addon dependency directives: `provides`, `requires`, `suggests`.
#
# An addon declares the capability tokens it PROVIDES and the ones it REQUIRES
# (hard) or SUGGESTS (soft) from other loaded addons. Tokens are opaque strings
# (dotted by convention only), e.g. `provides hangar` / `requires admiral` /
# `suggests hangar.sortie_board`. Multiple per line: `provides casino, casino.bar`.
#
# Collection is order-INDEPENDENT: the compiler gathers every `provides` into a
# story-level union as each file compiles, then validates `requires`/`suggests`
# once after the whole set (all addons) has compiled - see Mast._validate_requirements.
# So it does not matter which order addons load in.
#
# These are top-level directives (like `import`): the compile loop handles them
# by name (mast.py) and never instantiates a command, so they have no runtime
# effect. The tight, whole-line regex (keyword + whitespace + token list) means a
# variable assignment like `requires = 5` is NOT matched here (it has no token
# after the keyword) and still parses as an assignment - backward compatible.
#

_TOK = r'[A-Za-z_][\w.]*'
_TOKENS = r'(?P<tokens>' + _TOK + r'([ \t]*,[ \t]*' + _TOK + r')*)'
# End-of-LINE (not end-of-string): rule.match runs against the whole source at
# an offset, so a plain `$` (no re.MULTILINE) would only match the final line.
# A lookahead for newline-or-end anchors the directive to its own line anywhere.
_TRAIL = r'[ \t]*(#[^\n]*)?(?=\n|$)'


@mast_node(append=False)
class Provides(MastNode):
    rule = re.compile(r'provides[ \t]+' + _TOKENS + _TRAIL)

    def __init__(self, tokens=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.tokens = tokens


@mast_node(append=False)
class Requires(MastNode):
    rule = re.compile(r'requires[ \t]+' + _TOKENS + _TRAIL)

    def __init__(self, tokens=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.tokens = tokens


@mast_node(append=False)
class Suggests(MastNode):
    rule = re.compile(r'suggests[ \t]+' + _TOKENS + _TRAIL)

    def __init__(self, tokens=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.tokens = tokens
