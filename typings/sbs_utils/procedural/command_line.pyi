from sbs_utils.helpers import FrameContext
def _sbs ():
    """The sbs module for this frame, or None outside a frame (import time, tests)."""
def command_line_dict ():
    """The `key=value` launch arguments, parsed.
    
    Bare flags are absent - see :func:`command_line_has` for those.
    
    Returns:
        dict[str, str]: empty when the runtime has no command line."""
def command_line_get (key, default=None):
    """One `key=value` argument, or `default`.
    
    The key is matched case-insensitively and without surrounding spaces, because a launch
    argument is typed by a person or pasted from a script and `Map=` should not behave
    differently from `map=`."""
def command_line_has (flag):
    """Whether a BARE flag was passed, e.g. `autostartserver`.
    
    Bare flags never reach `command_line_dict`, so this walks the list. The exe path at
    index 0 is skipped - otherwise a mission launched from a folder called `autostartserver`
    would match, which is absurd but free to rule out."""
def command_line_list ():
    """Every launch argument as a list of strings, INCLUDING the exe path at index 0.
    
    Returns:
        list[str]: empty when the runtime has no command line (the mock) or the engine
        predates 1.3.5."""
