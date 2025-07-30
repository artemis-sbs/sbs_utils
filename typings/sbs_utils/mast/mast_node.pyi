from enum import Enum
from sbs_utils.mast.mast_globals import MastGlobals
def STRING_REGEX_NAMED (name):
    ...
def STRING_REGEX_NAMED_2 (name):
    ...
def STRING_REGEX_NAMED_3 (name):
    ...
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
    def parse (lines):
        ...
class MastDataObject(object):
    """class MastDataObject"""
    def __init__ (self, dictionary):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
    def get (self, key, defa):
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
    def parse (lines):
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
    TEMP : 99
    UNKNOWN : 100
