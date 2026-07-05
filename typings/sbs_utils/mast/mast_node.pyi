from enum import Enum
from sbs_utils.mast.mast_globals import MastGlobals
def STRING_REGEX_NAMED (name):
    ...
def STRING_REGEX_NAMED_2 (name):
    ...
def STRING_REGEX_NAMED_3 (name):
    ...
def compile_format_string (message):
    """Compile a MAST format string into a code object (eval mode).
    
    Text containing ``{`` is wrapped as an f-string and compiled so it can be
    formatted later; other text is returned unchanged. A triple-quote delimiter
    that does not occur in the text (and won't be escaped by a trailing quote)
    is chosen so embedded quotes don't terminate the literal early. If the text
    still cannot be wrapped safely, a clear error is raised rather than emitting
    broken code (the old ``f"""{message}"""`` wrapping silently produced a
    cryptic SyntaxError on any embedded triple-quote)."""
def mast_node (append=True):
    ...
class DescribableNode(MastNode):
    """class DescribableNode"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_option (self, prefix, text):
        ...
    def append_text (self, prefix, text):
        ...
    def apply_metadata (self, data):
        ...
    @property
    def desc (self):
        ...
    def parse (src, pos=0):
        ...
    def pick_option (self, task=None):
        """Choose a line: drop gated lines whose condition is false (evaluated in
        the task scope), then weighted-random among the rest. Returns None if
        nothing is eligible (author should include an ungated fallback). Falls
        back to uniform choice when no task or no gates are present."""
class MastDataObject(object):
    """class MastDataObject"""
    def __init__ (self, dictionary):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
    def get (self, key, defa=None):
        ...
class MastNode(object):
    """class MastNode"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
    def compile_formatted_string (self, message):
        ...
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def is_virtual (self):
        """Virtual nodes are not added to the command stack
        instead the interact with other nodes"""
    def must_indent (self):
        ...
    def never_indent (self):
        ...
    def parse (src, pos=0):
        ...
    def post_dedent (self, compile_info):
        ...
class ParseData(object):
    """class ParseData"""
    def __init__ (self, start, end, data):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Scope(Enum):
    """class Scope"""
    ASSIGNED : 20
    CLIENT : 10
    NORMAL : 2
    SHARED : 1
    SUB_TASK_LOCAL : 99
    UNKNOWN : 100
