class Mark(object):
    """class Mark"""
    def __init__ (self, name, index, line, column, buffer, pointer):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
    def get_snippet (self, indent=4, max_length=75):
        ...
class MarkedYAMLError(YAMLError):
    """Common base class for all non-exit exceptions."""
    def __init__ (self, context=None, context_mark=None, problem=None, problem_mark=None, note=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
class YAMLError(Exception):
    """Common base class for all non-exit exceptions."""
