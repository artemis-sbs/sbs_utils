class AliasToken(Token):
    """class AliasToken"""
    def __init__ (self, value, start_mark, end_mark):
        """Initialize self.  See help(type(self)) for accurate signature."""
class AnchorToken(Token):
    """class AnchorToken"""
    def __init__ (self, value, start_mark, end_mark):
        """Initialize self.  See help(type(self)) for accurate signature."""
class BlockEndToken(Token):
    """class BlockEndToken"""
class BlockEntryToken(Token):
    """class BlockEntryToken"""
class BlockMappingStartToken(Token):
    """class BlockMappingStartToken"""
class BlockSequenceStartToken(Token):
    """class BlockSequenceStartToken"""
class DirectiveToken(Token):
    """class DirectiveToken"""
    def __init__ (self, name, value, start_mark, end_mark):
        """Initialize self.  See help(type(self)) for accurate signature."""
class DocumentEndToken(Token):
    """class DocumentEndToken"""
class DocumentStartToken(Token):
    """class DocumentStartToken"""
class FlowEntryToken(Token):
    """class FlowEntryToken"""
class FlowMappingEndToken(Token):
    """class FlowMappingEndToken"""
class FlowMappingStartToken(Token):
    """class FlowMappingStartToken"""
class FlowSequenceEndToken(Token):
    """class FlowSequenceEndToken"""
class FlowSequenceStartToken(Token):
    """class FlowSequenceStartToken"""
class KeyToken(Token):
    """class KeyToken"""
class ScalarToken(Token):
    """class ScalarToken"""
    def __init__ (self, value, plain, start_mark, end_mark, style=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class StreamEndToken(Token):
    """class StreamEndToken"""
class StreamStartToken(Token):
    """class StreamStartToken"""
    def __init__ (self, start_mark=None, end_mark=None, encoding=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class TagToken(Token):
    """class TagToken"""
    def __init__ (self, value, start_mark, end_mark):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Token(object):
    """class Token"""
    def __init__ (self, start_mark, end_mark):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
class ValueToken(Token):
    """class ValueToken"""
