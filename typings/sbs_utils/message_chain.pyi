def _call_cb (cb, event, item):
    """Invoke a Channel-2 callback.
    
    `Layout` has always called this slot as `cb.on_message(event, item)` while
    `Column` called it as `cb(event, item)`, and both forms are in the wild, so
    accept either. (That split is why attaching a plain function -- which is all
    gui_message_callback ever assigns -- to a gui_section() used to raise
    AttributeError on the first click.)"""
def _is_inert (node):
    """True for a runtime node with nothing to run.
    
    Duck-typed on purpose: importing procedural.gui.button from here would drag
    in the whole procedural GUI surface and close an import cycle."""
def compose_handler (existing, layout_item, runtime_node):
    """Return the `(layout_item, node)` tuple a tag_map key should now hold.
    
    Replaces, exactly as before, unless there is a real handler already
    registered for this same widget -- then the two are chained."""
def invoke_message_cb (cb, event, item):
    """Call whatever is in an `on_message_cb` slot: chain, object, or function."""
def message_cb_add (layout_item, cb):
    """Register a Channel-2 callback WITHOUT dropping any already attached.
    
    Direct assignment (`item.on_message_cb = fn`) still means replace -- that is
    what the layout classes themselves do, and it is the only predictable
    meaning for `=`. This is the append form."""
def message_handlers (node):
    """Flatten a tag_map runtime node into the handlers it will actually run.
    
    For tooling and tests that inspect handlers by type -- without this a
    chained handler is invisible to them."""
class MessageChain(object):
    """An ordered list of gui_message handlers that looks like a single one.
    
    Callable as `chain(event, item)` (Channel 2) and as `chain.on_message(event)`
    (Channel 1), so it can sit in either slot."""
    def __bool__ (self):
        ...
    def __call__ (self, event, item=None):
        """Call self as a function."""
    def __contains__ (self, handler):
        ...
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __iter__ (self):
        ...
    def __len__ (self):
        ...
    def _fire (self, event, item):
        ...
    def add (self, handler, kind=None):
        """Append a handler. Returns False if this exact object is already in."""
    def clear (self):
        ...
    @property
    def handlers (self):
        ...
    def kind_of (handler):
        ...
    def on_message (self, event, item=None):
        ...
    def remove (self, handler):
        ...
