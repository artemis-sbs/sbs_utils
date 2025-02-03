from sbs_utils.yaml.representer import BaseRepresenter
from sbs_utils.yaml.representer import Representer
from sbs_utils.yaml.representer import RepresenterError
from sbs_utils.yaml.representer import SafeRepresenter
from sbs_utils.yaml.resolver import BaseResolver
from sbs_utils.yaml.resolver import Resolver
from sbs_utils.yaml.emitter import Emitter
from sbs_utils.yaml.emitter import EmitterError
from sbs_utils.yaml.serializer import Serializer
from sbs_utils.yaml.serializer import SerializerError
class BaseDumper(Emitter, Serializer, BaseRepresenter, BaseResolver):
    """class BaseDumper"""
    def __init__ (self, stream, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_representer (data_type, representer):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
    def add_representer (data_type, representer):
        ...
class Dumper(Emitter, Serializer, Representer, Resolver):
    """class Dumper"""
    def __init__ (self, stream, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_representer (data_type, representer):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
    def add_representer (data_type, representer):
        ...
class SafeDumper(Emitter, Serializer, SafeRepresenter, Resolver):
    """class SafeDumper"""
    def __init__ (self, stream, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None, sort_keys=True):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_implicit_resolver (tag, regexp, first):
        ...
    def add_multi_representer (data_type, representer):
        ...
    def add_path_resolver (tag, path, kind=None):
        ...
    def add_representer (data_type, representer):
        ...
