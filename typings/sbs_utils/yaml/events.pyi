class AliasEvent(NodeEvent):
    """class AliasEvent"""
class CollectionEndEvent(Event):
    """class CollectionEndEvent"""
class CollectionStartEvent(NodeEvent):
    """class CollectionStartEvent"""
    def __init__ (self, anchor, tag, implicit, start_mark=None, end_mark=None, flow_style=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class DocumentEndEvent(Event):
    """class DocumentEndEvent"""
    def __init__ (self, start_mark=None, end_mark=None, explicit=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class DocumentStartEvent(Event):
    """class DocumentStartEvent"""
    def __init__ (self, start_mark=None, end_mark=None, explicit=None, version=None, tags=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Event(object):
    """class Event"""
    def __init__ (self, start_mark=None, end_mark=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
class MappingEndEvent(CollectionEndEvent):
    """class MappingEndEvent"""
class MappingStartEvent(CollectionStartEvent):
    """class MappingStartEvent"""
class NodeEvent(Event):
    """class NodeEvent"""
    def __init__ (self, anchor, start_mark=None, end_mark=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class ScalarEvent(NodeEvent):
    """class ScalarEvent"""
    def __init__ (self, anchor, tag, implicit, value, start_mark=None, end_mark=None, style=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class SequenceEndEvent(CollectionEndEvent):
    """class SequenceEndEvent"""
class SequenceStartEvent(CollectionStartEvent):
    """class SequenceStartEvent"""
class StreamEndEvent(Event):
    """class StreamEndEvent"""
class StreamStartEvent(Event):
    """class StreamStartEvent"""
    def __init__ (self, start_mark=None, end_mark=None, encoding=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
