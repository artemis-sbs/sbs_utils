from sbs_utils.yaml.nodes import CollectionNode
from sbs_utils.yaml.nodes import MappingNode
from sbs_utils.yaml.nodes import Node
from sbs_utils.yaml.nodes import ScalarNode
from sbs_utils.yaml.nodes import SequenceNode
from sbs_utils.yaml.error import Mark
from sbs_utils.yaml.error import MarkedYAMLError
from sbs_utils.yaml.error import YAMLError
class BaseResolver(object):
    """class BaseResolver"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
    def ascend_resolver (self):
        ...
    def check_resolver_prefix (self, depth, path, kind, current_node, current_index):
        ...
    def descend_resolver (self, current_node, current_index):
        ...
    def resolve (self, kind, value, implicit):
        ...
class Resolver(BaseResolver):
    """class Resolver"""
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
class ResolverError(YAMLError):
    """Common base class for all non-exit exceptions."""
