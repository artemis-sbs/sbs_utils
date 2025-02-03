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
from sbs_utils.yaml.error import MarkedYAMLError
from sbs_utils.yaml.scanner import Scanner
from sbs_utils.yaml.scanner import ScannerError
class Parser(object):
    """class Parser"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def check_event (self, *choices):
        ...
    def dispose (self):
        ...
    def get_event (self):
        ...
    def parse_block_mapping_first_key (self):
        ...
    def parse_block_mapping_key (self):
        ...
    def parse_block_mapping_value (self):
        ...
    def parse_block_node (self):
        ...
    def parse_block_node_or_indentless_sequence (self):
        ...
    def parse_block_sequence_entry (self):
        ...
    def parse_block_sequence_first_entry (self):
        ...
    def parse_document_content (self):
        ...
    def parse_document_end (self):
        ...
    def parse_document_start (self):
        ...
    def parse_flow_mapping_empty_value (self):
        ...
    def parse_flow_mapping_first_key (self):
        ...
    def parse_flow_mapping_key (self, first=False):
        ...
    def parse_flow_mapping_value (self):
        ...
    def parse_flow_node (self):
        ...
    def parse_flow_sequence_entry (self, first=False):
        ...
    def parse_flow_sequence_entry_mapping_end (self):
        ...
    def parse_flow_sequence_entry_mapping_key (self):
        ...
    def parse_flow_sequence_entry_mapping_value (self):
        ...
    def parse_flow_sequence_first_entry (self):
        ...
    def parse_implicit_document_start (self):
        ...
    def parse_indentless_sequence_entry (self):
        ...
    def parse_node (self, block=False, indentless_sequence=False):
        ...
    def parse_stream_start (self):
        ...
    def peek_event (self):
        ...
    def process_directives (self):
        ...
    def process_empty_scalar (self, mark):
        ...
class ParserError(MarkedYAMLError):
    """Common base class for all non-exit exceptions."""
