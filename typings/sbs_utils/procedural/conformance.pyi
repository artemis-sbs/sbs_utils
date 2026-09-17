from sbs_utils.helpers import FrameContext
def _sim_seconds ():
    """Sim time, or None when there is no simulation yet.
    
    `FrameContext.sim_seconds` RAISES rather than returning zero when the context has no
    sim - and this is called from `tick_the_rest`, on every tick of the shipped library.
    An exception there would take down every mission, recording or not, so it is caught
    here rather than trusted."""
def _soak_covered_routes ():
    """Entered route paths, normalized the way a scenario names them.
    
    Shares `soak_manifest.normalize_route` with the mock leg on purpose: two copies of
    this rule would drift, and a route the engine called one thing and the mock another
    would look like a regression in whichever leg ran second."""
def _soak_result ():
    """The scenario half of the verdict, or None when no soak is running."""
def command_line_get (key, default=None):
    """One `key=value` argument, or `default`.
    
    The key is matched case-insensitively and without surrounding spaces, because a launch
    argument is typed by a person or pasted from a script and `Map=` should not behave
    differently from `map=`.
    
    A mission-scoped argument (`profile=`, `map=`, `console=`, `var.NAME=`) reads as
    absent once we have switched missions, so every caller gets the scoping without having
    to remember it."""
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
def soak_active ():
    """Whether a soak scenario is loaded and driving. Cheap once resolved."""
def soak_name ():
    """The scenario `soak=` asked for, or "" when it was not requested."""
def soak_reset ():
    """Drop soak state at a mission boundary. Called from `conformance_reset`."""
def soak_tick ():
    """Drive the pilot one step. Called from `tick_the_rest`, guarded and cheap."""
class _ErrorCounter(Handler):
    """Counts records on the `mast.runtime` logger.
    
    That logger is where `MastScheduler.runtime_error` sends everything, so it is the one
    place a MAST failure is guaranteed to pass through in the engine - the same source
    behind `mast.runtime.log`."""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def emit (self, record):
        ...
