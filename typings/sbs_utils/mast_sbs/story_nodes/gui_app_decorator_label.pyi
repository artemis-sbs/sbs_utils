from sbs_utils.mast.core_nodes.decorator_label import DecoratorLabel
from sbs_utils.mast.core_nodes.inline_function import FuncCommand
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
def mast_node (append=True):
    ...
class GuiAppDecoratorLabel(DecoratorLabel):
    """A screen INSIDE the ePADD, as against a destination on the tab bar.
    
    The twin of `GuiTabDecoratorLabel`, and deliberately a separate kind rather than a
    flag on it, because the two answer different questions:
    
    * a TAB's `if` answers "may this be offered on the bar";
    * an APP's `if` answers "is this app available right now".
    
    One route kind doing both is what made the PADD's Back inherit a tab's condition -
    `//gui/tab/away if not gui_app_mode_is_on()` correctly hid away as a tab and deleted
    the way back to the crew console with it.
    
    THE ACTIVATION KEY IS THE OTHER HALF. This injects `gui_app_activate`, which writes
    `__active_app__` and never touches `__active_tab__` - so the tab a player was on when
    they opened the PADD is still recorded, and that is what the PADD's single Back
    returns to. Nothing has to remember it.
    
    ORDER MATTERS AT IMPORT. `@mast_node(append=False)` inserts at the FRONT of the node
    list and the compiler takes the first match, so `story_nodes/__init__.py` has to
    import this AFTER `route_label` - otherwise `//gui/app/x` is swallowed by
    `RouteDecoratorLabel`'s `case ["gui", *b]` and becomes a navigation route."""
    def __init__ (self, path, if_exp=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def can_fallthrough (self, parent):
        ...
    def clear ():
        """Drop registered //gui/app labels (fresh mission / in-process recompile).
        
        Called from `reset_mission_state`. Without it the table carries two generations
        of routes across an in-process reload, and opening an app runs a label from the
        dead compile."""
    def generate_label_begin_cmds (self, compile_info=None):
        ...
    def generate_label_end_cmds (self, compile_info=None):
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def parse (src, pos=0):
        ...
    def remove_id (id):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def test (self, task):
        ...
