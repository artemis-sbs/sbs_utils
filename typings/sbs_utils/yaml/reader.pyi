from sbs_utils.yaml.error import Mark
from sbs_utils.yaml.error import YAMLError
class Reader(object):
    """class Reader"""
    def __init__ (self, stream):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def check_printable (self, data):
        ...
    def determine_encoding (self):
        ...
    def forward (self, length=1):
        ...
    def get_mark (self):
        ...
    def peek (self, index=0):
        ...
    def prefix (self, length=1):
        ...
    def update (self, length):
        ...
    def update_raw (self, size=4096):
        ...
class ReaderError(YAMLError):
    """Common base class for all non-exit exceptions."""
    def __init__ (self, name, position, character, encoding, reason):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
