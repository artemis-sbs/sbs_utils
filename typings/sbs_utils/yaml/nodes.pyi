class CollectionNode(Node):
    """class CollectionNode"""
    def __init__ (self, tag, value, start_mark=None, end_mark=None, flow_style=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class MappingNode(CollectionNode):
    """class MappingNode"""
class Node(object):
    """class Node"""
    def __init__ (self, tag, value, start_mark, end_mark):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
class ScalarNode(Node):
    """class ScalarNode"""
    def __init__ (self, tag, value, start_mark=None, end_mark=None, style=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class SequenceNode(CollectionNode):
    """class SequenceNode"""
