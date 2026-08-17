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
from sbs_utils.yaml.tokens import AliasToken
from sbs_utils.yaml.tokens import AnchorToken
from sbs_utils.yaml.tokens import BlockEndToken
from sbs_utils.yaml.tokens import BlockEntryToken
from sbs_utils.yaml.tokens import BlockMappingStartToken
from sbs_utils.yaml.tokens import BlockSequenceStartToken
from sbs_utils.yaml.tokens import DirectiveToken
from sbs_utils.yaml.tokens import DocumentEndToken
from sbs_utils.yaml.tokens import DocumentStartToken
from sbs_utils.yaml.tokens import FlowEntryToken
from sbs_utils.yaml.tokens import FlowMappingEndToken
from sbs_utils.yaml.tokens import FlowMappingStartToken
from sbs_utils.yaml.tokens import FlowSequenceEndToken
from sbs_utils.yaml.tokens import FlowSequenceStartToken
from sbs_utils.yaml.tokens import KeyToken
from sbs_utils.yaml.tokens import ScalarToken
from sbs_utils.yaml.tokens import StreamEndToken
from sbs_utils.yaml.tokens import StreamStartToken
from sbs_utils.yaml.tokens import TagToken
from sbs_utils.yaml.tokens import Token
from sbs_utils.yaml.tokens import ValueToken
from sbs_utils.yaml.dumper import BaseDumper
from sbs_utils.yaml.dumper import Dumper
from sbs_utils.yaml.dumper import SafeDumper
from sbs_utils.yaml.loader import BaseLoader
from sbs_utils.yaml.loader import FullLoader
from sbs_utils.yaml.loader import Loader
from sbs_utils.yaml.loader import SafeLoader
from sbs_utils.yaml.loader import UnsafeLoader
from sbs_utils.yaml.nodes import CollectionNode
from sbs_utils.yaml.nodes import MappingNode
from sbs_utils.yaml.nodes import Node
from sbs_utils.yaml.nodes import ScalarNode
from sbs_utils.yaml.nodes import SequenceNode
from sbs_utils.yaml.error import Mark
from sbs_utils.yaml.error import MarkedYAMLError
from sbs_utils.yaml.error import YAMLError
def add_constructor (tag, constructor, Loader=None):
    """Add a constructor for the given tag.
    Constructor is a function that accepts a Loader instance
    and a node object and produces the corresponding Python object."""
def add_implicit_resolver (tag, regexp, first=None, Loader=None, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>):
    """Add an implicit scalar detector.
    If an implicit scalar value matches the given regexp,
    the corresponding tag is assigned to the scalar.
    first is a sequence of possible initial characters or None."""
def add_multi_constructor (tag_prefix, multi_constructor, Loader=None):
    """Add a multi-constructor for the given tag prefix.
    Multi-constructor is called for a node if its tag starts with tag_prefix.
    Multi-constructor accepts a Loader instance, a tag suffix,
    and a node object and produces the corresponding Python object."""
def add_multi_representer (data_type, multi_representer, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>):
    """Add a representer for the given type.
    Multi-representer is a function accepting a Dumper instance
    and an instance of the given data type or subtype
    and producing the corresponding representation node."""
def add_path_resolver (tag, path, kind=None, Loader=None, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>):
    """Add a path based resolver for the given tag.
    A path is a list of keys that forms a path
    to a node in the representation tree.
    Keys can be string values, integers, or None."""
def add_representer (data_type, representer, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>):
    """Add a representer for the given type.
    Representer is a function accepting a Dumper instance
    and an instance of the given data type
    and producing the corresponding representation node."""
def compose (stream, Loader=<class 'sbs_utils.yaml.loader.Loader'>):
    """Parse the first YAML document in a stream
    and produce the corresponding representation tree."""
def compose_all (stream, Loader=<class 'sbs_utils.yaml.loader.Loader'>):
    """Parse all YAML documents in a stream
    and produce corresponding representation trees."""
def dump (data, stream=None, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>, **kwds):
    """Serialize a Python object into a YAML stream.
    If stream is None, return the produced string instead."""
def dump_all (documents, stream=None, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True):
    """Serialize a sequence of Python objects into a YAML stream.
    If stream is None, return the produced string instead."""
def emit (events, stream=None, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None):
    """Emit YAML parsing events into a stream.
    If stream is None, return the produced string instead."""
def full_load (stream):
    """Parse the first YAML document in a stream
    and produce the corresponding Python object.
    
    Resolve all tags except those known to be
    unsafe on untrusted input."""
def full_load_all (stream):
    """Parse all YAML documents in a stream
    and produce corresponding Python objects.
    
    Resolve all tags except those known to be
    unsafe on untrusted input."""
def load (stream, Loader):
    """Parse the first YAML document in a stream
    and produce the corresponding Python object."""
def load_all (stream, Loader):
    """Parse all YAML documents in a stream
    and produce corresponding Python objects."""
def parse (stream, Loader=<class 'sbs_utils.yaml.loader.Loader'>):
    """Parse a YAML stream and produce parsing events."""
def safe_dump (data, stream=None, **kwds):
    """Serialize a Python object into a YAML stream.
    Produce only basic YAML tags.
    If stream is None, return the produced string instead."""
def safe_dump_all (documents, stream=None, **kwds):
    """Serialize a sequence of Python objects into a YAML stream.
    Produce only basic YAML tags.
    If stream is None, return the produced string instead."""
def safe_load (stream):
    """Parse the first YAML document in a stream
    and produce the corresponding Python object.
    
    Resolve only basic YAML tags. This is known
    to be safe for untrusted input."""
def safe_load_all (stream):
    """Parse all YAML documents in a stream
    and produce corresponding Python objects.
    
    Resolve only basic YAML tags. This is known
    to be safe for untrusted input."""
def scan (stream, Loader=<class 'sbs_utils.yaml.loader.Loader'>):
    """Scan a YAML stream and produce scanning tokens."""
def serialize (node, stream=None, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>, **kwds):
    """Serialize a representation tree into a YAML stream.
    If stream is None, return the produced string instead."""
def serialize_all (nodes, stream=None, Dumper=<class 'sbs_utils.yaml.dumper.Dumper'>, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None):
    """Serialize a sequence of representation trees into a YAML stream.
    If stream is None, return the produced string instead."""
def unsafe_load (stream):
    """Parse the first YAML document in a stream
    and produce the corresponding Python object.
    
    Resolve all tags, even those known to be
    unsafe on untrusted input."""
def unsafe_load_all (stream):
    """Parse all YAML documents in a stream
    and produce corresponding Python objects.
    
    Resolve all tags, even those known to be
    unsafe on untrusted input."""
def warnings (settings=None):
    ...
class YAMLObject(object):
    """An object that can dump itself to a YAML stream
    and load itself from a YAML stream."""
    def from_yaml (loader, node):
        """Convert a representation node to a Python object."""
    def to_yaml (dumper, data):
        """Convert a Python object to a representation node."""
class YAMLObjectMetaclass(type):
    """The metaclass for YAMLObject."""
    __abstractmethods__ : getset_descriptor
    ...
    def __init__ (cls, name, bases, kwds):
        """Initialize self.  See help(type(self)) for accurate signature."""
