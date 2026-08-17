from enum import Enum
from sbs_utils.mast.mast_globals import MastGlobals
def STRING_REGEX_NAMED (name):
    ...
def STRING_REGEX_NAMED_2 (name):
    ...
def STRING_REGEX_NAMED_3 (name):
    ...
def lru_cache (maxsize=128, typed=False):
    """Least-recently-used cache decorator.
    
    If *maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.
    
    If *typed* is True, arguments of different types will be cached
    separately.  For example, f(decimal.Decimal("3.0")) and f(3.0) will be
    treated as distinct calls with distinct results.  Some types such as
    str and int may be cached separately even when typed is false.
    
    Arguments to the cached function must be hashable.
    
    View the cache statistics named tuple (hits, misses, maxsize, currsize)
    with f.cache_info().  Clear the cache and statistics with
    f.cache_clear().  Access the underlying function with f.__wrapped__.
    
    See:  https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)"""
def mast_compile (source, mode='eval', filename=None):
    """``compile()`` for MAST expressions, with the source kept for tracebacks.
    
    Compiling against the shared ``"<string>"`` filename leaves Python with no
    source for the frame, so ``traceback.extract_tb`` reports the offending line
    as ``None`` - which is exactly the useless report a MAST author sees today.
    Compiling against a unique pseudo-filename and registering the text in
    ``linecache`` makes every traceback (eval and ``~~`` exec alike) print the
    real expression, and lets eval_code quote the WHOLE expression even when the
    deepest frame is inside some library function.
    
    An ``mtime`` of ``None`` in the linecache tuple is the documented "loaded by
    a __loader__" form: ``linecache.checkcache`` skips those, so the entry is
    never invalidated out from under us."""
def mast_expr_source (code):
    """The MAST source text a code object was compiled from, or None.
    
    ``eval``/``exec`` also accept a raw string (a few nodes build one on the
    fly), in which case the source IS the argument."""
def mast_expr_source_count ():
    ...
def mast_expr_sources_clear ():
    """Drop every registered expression source (per-mission reset).
    
    cosmos_dev reuses one interpreter across run_next_mission, so this dict and
    its linecache entries would otherwise accumulate mission after mission."""
def mast_node (append=True):
    ...
class DescribableNode(MastNode):
    """class DescribableNode"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_option (self, prefix, text):
        ...
    def append_text (self, prefix, text):
        ...
    def apply_metadata (self, data):
        ...
    @property
    def desc (self):
        ...
    def parse (src, pos=0):
        ...
    def pick_option (self, task=None):
        """Choose a line: drop gated lines whose condition is false (evaluated in
        the task scope), then weighted-random among the rest. Returns None if
        nothing is eligible (author should include an ungated fallback). Falls
        back to uniform choice when no task or no gates are present."""
class MastDataObject(object):
    """class MastDataObject"""
    def __init__ (self, dictionary):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
    def get (self, key, defa=None):
        ...
class MastNode(object):
    """class MastNode"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_child (self, cmd):
        ...
    def compile_formatted_string (self, message):
        ...
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def is_virtual (self):
        """Virtual nodes are not added to the command stack
        instead the interact with other nodes"""
    def must_indent (self):
        ...
    def never_indent (self):
        ...
    def parse (src, pos=0):
        ...
    def post_dedent (self, compile_info):
        ...
class ParseData(object):
    """class ParseData"""
    def __init__ (self, start, end, data):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Scope(Enum):
    """Create a collection of name/value pairs.
    
    Example enumeration:
    
    >>> class Color(Enum):
    ...     RED = 1
    ...     BLUE = 2
    ...     GREEN = 3
    
    Access them by:
    
    - attribute access:
    
      >>> Color.RED
      <Color.RED: 1>
    
    - value lookup:
    
      >>> Color(1)
      <Color.RED: 1>
    
    - name lookup:
    
      >>> Color['RED']
      <Color.RED: 1>
    
    Enumerations can be iterated over, and know how many members they have:
    
    >>> len(Color)
    3
    
    >>> list(Color)
    [<Color.RED: 1>, <Color.BLUE: 2>, <Color.GREEN: 3>]
    
    Methods can be added to enumerations, and members can have their own
    attributes -- see the documentation for details."""
    ASSIGNED : 20
    CLIENT : 10
    NORMAL : 2
    SHARED : 1
    SUB_TASK_LOCAL : 99
    UNKNOWN : 100
class _EvalError(object):
    """Unique "this expression raised" marker returned by ``eval_code_checked``.
    
    ``None`` is a perfectly legal MAST value (``default ship_art = None``), so a
    node that got ``None`` back could never tell a real result from a blown-up
    expression - it went on to assign None, take the ``else:`` branch, or iterate
    None into a second, unrelated error. This sentinel is never a legal value, so
    the node can stop at the FIRST failure, which is the one worth reporting."""
    def __bool__ (self):
        ...
    def __repr__ (self):
        """Return repr(self)."""
