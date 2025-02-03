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
from sbs_utils.yaml.error import YAMLError
class Serializer(object):
    """class Serializer"""
    def __init__ (self, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def anchor_node (self, node):
        ...
    def close (self):
        ...
    def generate_anchor (self, node):
        ...
    def open (self):
        ...
    def serialize (self, node):
        ...
    def serialize_node (self, node, parent, index):
        ...
class SerializerError(YAMLError):
    """Common base class for all non-exit exceptions."""
