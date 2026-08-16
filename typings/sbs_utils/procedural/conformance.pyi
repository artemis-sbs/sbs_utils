from sbs_utils.helpers import FrameContext
def _sim_seconds ():
    """Sim time, or None when there is no simulation yet.
    
    `FrameContext.sim_seconds` RAISES rather than returning zero when the context has no
    sim - and this is called from `tick_the_rest`, on every tick of the shipped library.
    An exception there would take down every mission, recording or not, so it is caught
    here rather than trusted."""
def command_line_get (key, default=None):
    """One `key=value` argument, or `default`.
    
    The key is matched case-insensitively and without surrounding spaces, because a launch
    argument is typed by a person or pasted from a script and `Map=` should not behave
    differently from `map=`."""
def conformance_error_count ():
    """Runtime errors seen so far. Reset-ledger probe."""
def conformance_reset ():
    """Drop state at a mission boundary. Registered with the reset ledger."""
def conformance_seconds ():
    """How long `test=` asked for, or 0 when it was not requested."""
def conformance_tick ():
    """Write the verdict once the mission has run long enough. Cheap when not requested."""
def conformance_write (sim_seconds=None):
    """Write the verdict now. Returns the path, or None."""
class _ErrorCounter(Handler):
    """Counts records on the `mast.runtime` logger.
    
    That logger is where `MastScheduler.runtime_error` sends everything, so it is the one
    place a MAST failure is guaranteed to pass through in the engine - the same source
    behind `mast.runtime.log`."""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def emit (self, record):
        ...
