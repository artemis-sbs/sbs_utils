from sbs_utils.yaml.events import AliasEvent
from sbs_utils.yaml.events import CollectionEndEvent
from sbs_utils.yaml.events import CollectionStartEvent
from sbs_utils.yaml.events import DocumentEndEvent
from sbs_utils.yaml.events import DocumentStartEvent
from sbs_utils.yaml.events import Event
from sbs_utils.yaml.events import MappingEndEvent
from sbs_utils.yaml.events import MappingStartEvent
from sbs_utils.yaml.events import NodeEvent
from sbs_utils.yaml.events import ScalarEvent
from sbs_utils.yaml.events import SequenceEndEvent
from sbs_utils.yaml.events import SequenceStartEvent
from sbs_utils.yaml.events import StreamEndEvent
from sbs_utils.yaml.events import StreamStartEvent
from sbs_utils.yaml.nodes import CollectionNode
from sbs_utils.yaml.nodes import MappingNode
from sbs_utils.yaml.nodes import Node
from sbs_utils.yaml.nodes import ScalarNode
from sbs_utils.yaml.nodes import SequenceNode
from sbs_utils.yaml.error import MarkedYAMLError
class Composer(object):
    """class Composer"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def check_node (self):
        ...
    def compose_document (self):
        ...
    def compose_mapping_node (self, anchor):
        ...
    def compose_node (self, parent, index):
        ...
    def compose_scalar_node (self, anchor):
        ...
    def compose_sequence_node (self, anchor):
        ...
    def get_node (self):
        ...
    def get_single_node (self):
        ...
class ComposerError(MarkedYAMLError):
    """Common base class for all non-exit exceptions."""
