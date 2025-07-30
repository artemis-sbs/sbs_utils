from sbs_utils.agent import Agent
from sbs_utils.mast.core_nodes.assign import Assign
from sbs_utils.mast.core_nodes.comment import Comment
from enum import Enum
from sbs_utils.mast.core_nodes.label import Label
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_node import Scope
from pathlib import Path
from zipfile import ZipFile
def DEBUG (msg):
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
class InlineData(object):
    """class InlineData"""
    def __init__ (self, start, end):
        """Initialize self.  See help(type(self)) for accurate signature."""
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
    def content_from_lib_or_file (self, file_name):
        ...
    def enable_logging ():
        ...
    def expand_resources (self):
        ...
    def find_add_ons (self, folder):
        ...
    def find_imports (self, folder):
        ...
    def from_file (self, file_name, root):
        """Docstring"""
    def get_source_file_name (file_num):
        ...
    def import_content (self, filename, root, lib_name):
        ...
    def import_python_module_for_source (self, name, lib_name):
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
    def signal_register (self, name, task, label_info):
        ...
    def signal_unregister (self, name, task):
        ...
    def signal_unregister_all (self, task):
        ...
    def signal_unregister_all_inline (self, task):
        ...
    def update_shared_props_by_tag (self, tag, props, test):
        ...
class Rule(object):
    """class Rule"""
    def __init__ (self, re, cls):
        """Initialize self.  See help(type(self)) for accurate signature."""
class SourceMapData(object):
    """class SourceMapData"""
    def __init__ (self, file_name, basedir):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
