from sbs_utils.agent import Agent
from enum import Enum
from sbs_utils.helpers import FrameContext
from zipfile import ZipFile
def DEBUG (msg):
    ...
def STRING_REGEX_NAMED (name):
    ...
def STRING_REGEX_NAMED_2 (name):
    ...
def STRING_REGEX_NAMED_3 (name):
    ...
def find_exp_end (s, expect_block):
    ...
def first_newline_index (s):
    ...
def first_non_newline_index (s):
    ...
def first_non_space_index (s):
    ...
def first_non_whitespace_index (s):
    ...
def format_exception (message, source):
    ...
def getmembers (object, predicate=None):
    ...
def isfunction (object):
    ...
def mast_print (*args, **kwargs):
    ...
def signature (obj, *, follow_wrapped=True, globals=None, locals=None, eval_str=False):
    ...
class Assign(MastNode):
    """class Assign"""
    def __init__ (self, scope, lhs, oper, exp, a_wait=None, quote=None, py=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Await(MastNode):
    """waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel"""
    def __init__ (self, until=None, if_exp=None, is_end=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_inline (self, inline_data):
        ...
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class AwaitInlineLabel(MastNode):
    """class AwaitInlineLabel"""
    def __init__ (self, val=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        """cascade the dedent up to the start"""
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class Button(MastNode):
    """class Button"""
    def __init__ (self, message=None, button=None, if_exp=None, format=None, label=None, clone=False, q=None, new_task=None, data=None, path=None, block=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def been_here (self, id_tuple):
        ...
    def clone (self):
        ...
    def create_end_node (self, loc, dedent_obj, compile_info):
        """cascade the dedent up to the start"""
    def expand (self):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
    def resolve_data_context (self, task):
        ...
    def run (self, task, button_promise):
        ...
    def should_present (self, id_tuple):
        ...
    def visit (self, id_tuple):
        ...
class Comment(MastNode):
    """class Comment"""
    def __init__ (self, com=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class DecoratorLabel(Label):
    """class DecoratorLabel"""
    def __init__ (self, name, loc=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self):
        ...
    def generate_label_begin_cmds (self, compile_info=None):
        ...
    def generate_label_end_cmds (self, compile_info=None):
        ...
    def next_label_id ():
        ...
    def parse (lines):
        ...
class DescribableNode(MastNode):
    """class DescribableNode"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_option (self, prefix, text):
        ...
    def append_text (self, prefix, text):
        ...
    @property
    def desc (self):
        ...
    def parse (lines):
        ...
class ExpParseData(object):
    """class ExpParseData"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def in_something (self):
        ...
    @property
    def is_valid (self):
        ...
class FuncCommand(MastNode):
    """class FuncCommand"""
    def __init__ (self, is_await=None, py_cmds=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class IfStatements(MastNode):
    """class IfStatements"""
    def __init__ (self, end=None, if_op=None, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class Import(MastNode):
    """class Import"""
    def __init__ (self, name, lib=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class InlineData(object):
    """class InlineData"""
    def __init__ (self, start, end):
        """Initialize self.  See help(type(self)) for accurate signature."""
class InlineLabel(MastNode):
    """class InlineLabel"""
    def __init__ (self, name, m=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Jump(MastNode):
    """class Jump"""
    def __init__ (self, pop=None, jump=None, jump_name=None, if_exp=None, data=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class Label(DescribableNode):
    """class Label"""
    def __init__ (self, name, replace=None, m=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
    def add_label (self, name, label):
        ...
    def can_fallthrough (self):
        ...
    def generate_label_begin_cmds (self, compile_info=None):
        ...
    def generate_label_end_cmds (self, compile_info=None):
        ...
    def parse (lines):
        ...
class LoopBreak(MastNode):
    """class LoopBreak"""
    def __init__ (self, op=None, name=None, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class LoopEnd(MastNode):
    """LoopEnd is a node that is injected to allow loops to know where the end is"""
    def __init__ (self, start=None, name=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class LoopStart(MastNode):
    """class LoopStart"""
    def __init__ (self, while_in=None, cond=None, name=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
    def post_dedent (self, compile_info):
        ...
class Mast(object):
    """class Mast"""
    def __init__ (self, cmds=None, is_import=False):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _compile (self, lines, file_name, root):
        ...
    def add_scheduler (self, scheduler):
        ...
    def clear (self, file_name):
        ...
    def compile (self, lines, file_name, root):
        ...
    def content_from_lib_or_file (self, file_name, lib_name):
        ...
    def enable_logging ():
        ...
    def find_imports (self, folder):
        ...
    def from_file (self, file_name, root, lib_name=None):
        """Docstring"""
    def get_source_file_name (file_num):
        ...
    def import_content (self, filename, root, lib_file):
        ...
    def import_python_module (mod_name, prepend=None):
        ...
    def make_global (func):
        ...
    def make_global_var (name, value):
        ...
    def prune_main (self):
        ...
    def refresh_schedulers (self, source, label):
        """TODO: Deprecate for signals?
        
        Args:
            source (_type_): _description_
            label (_type_): _description_"""
    def remove_scheduler (self, scheduler):
        ...
    def signal_emit (self, name, sender_task, data):
        ...
    def signal_register (self, name, task, label_info, once):
        ...
    def signal_unregister (self, name, task):
        ...
    def update_shared_props_by_tag (self, tag, props, test):
        ...
class MastDataObject(object):
    """class MastDataObject"""
    def __init__ (self, dictionary):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
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
    def parse (lines):
        ...
    def post_dedent (self, compile_info):
        ...
class MatchStatements(MastNode):
    """class MatchStatements"""
    def __init__ (self, end=None, op=None, exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class OnChange(MastNode):
    """class OnChange"""
    def __init__ (self, end=None, val=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        """cascade the dedent up to the start"""
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class ParseData(object):
    """class ParseData"""
    def __init__ (self, start, end, data):
        """Initialize self.  See help(type(self)) for accurate signature."""
class PyCode(MastNode):
    """class PyCode"""
    def __init__ (self, py_cmds=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class RouteDecoratorLabel(DecoratorLabel):
    """class RouteDecoratorLabel"""
    def __init__ (self, path, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def can_fallthrough (self):
        ...
    def generate_label_begin_cmds (self, compile_info=None):
        ...
    def generate_label_end_cmds (self, compile_info=None):
        ...
    def parse (lines):
        ...
class Rule(object):
    """class Rule"""
    def __init__ (self, re, cls):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Scope(Enum):
    """class Scope"""
    ASSIGNED : 20
    CLIENT : 10
    NORMAL : 2
    SHARED : 1
    TEMP : 99
    UNKNOWN : 100
class WithEnd(MastNode):
    """LoopEnd is a node that is injected to allow loops to know where the end is"""
    def __init__ (self, start=None, name=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class WithStart(MastNode):
    """class WithStart"""
    def __init__ (self, obj=None, name=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def create_end_node (self, loc, _, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
class Yield(MastNode):
    """class Yield"""
    def __init__ (self, res=None, exp=None, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
