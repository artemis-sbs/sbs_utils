from sbs_utils.yaml.constructor import BaseConstructor
from sbs_utils.yaml.constructor import Constructor
from sbs_utils.yaml.constructor import ConstructorError
from sbs_utils.yaml.constructor import FullConstructor
from sbs_utils.yaml.constructor import SafeConstructor
from sbs_utils.yaml.constructor import UnsafeConstructor
from sbs_utils.yaml.resolver import BaseResolver
from sbs_utils.yaml.resolver import Resolver
from sbs_utils.yaml.composer import Composer
from sbs_utils.yaml.composer import ComposerError
from sbs_utils.yaml.parser import Parser
from sbs_utils.yaml.parser import ParserError
from sbs_utils.yaml.reader import Reader
from sbs_utils.yaml.reader import ReaderError
from sbs_utils.yaml.scanner import Scanner
from sbs_utils.yaml.scanner import ScannerError
class BaseLoader(Reader, Scanner, Parser, Composer, BaseConstructor, BaseResolver):
    """class BaseLoader"""
    def __init__ (self, stream):
        """Initialize the scanner."""
    def add_constructor (tag, constructor):
        ...
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_constructor (tag_prefix, multi_constructor):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
class FullLoader(Reader, Scanner, Parser, Composer, FullConstructor, Resolver):
    """class FullLoader"""
    def __init__ (self, stream):
        """Initialize the scanner."""
    def add_constructor (tag, constructor):
        ...
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_constructor (tag_prefix, multi_constructor):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
class Loader(Reader, Scanner, Parser, Composer, Constructor, Resolver):
    """class Loader"""
    def __init__ (self, stream):
        """Initialize the scanner."""
    def add_constructor (tag, constructor):
        ...
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_constructor (tag_prefix, multi_constructor):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
class SafeLoader(Reader, Scanner, Parser, Composer, SafeConstructor, Resolver):
    """class SafeLoader"""
    def __init__ (self, stream):
        """Initialize the scanner."""
    def add_constructor (tag, constructor):
        ...
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_constructor (tag_prefix, multi_constructor):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
class UnsafeLoader(Reader, Scanner, Parser, Composer, Constructor, Resolver):
    """class UnsafeLoader"""
    def __init__ (self, stream):
        """Initialize the scanner."""
    def add_constructor (tag, constructor):
        ...
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_constructor (tag_prefix, multi_constructor):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
