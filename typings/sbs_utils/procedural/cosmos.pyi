from sbs_utils.helpers import FrameContext
def sim_create () -> None:
    """Create a new simulation.
    
    Writes any add-on-contributed ship data FIRST. The engine reads a mission's
    `extraShipData.json` inside `create_new_sim()` - measured on engine 1.3.4, see
    `SHIP_MOD_PLAN.md` s6a - so that file has to be on disk before this call and there is
    no useful moment afterwards.
    
    The flush lives HERE rather than behind a signal emitted just before the call. A signal
    route is synchronous only while nothing in it awaits, and an add-on's route is someone
    else's code: one `await` in one mod's handler would put the write after the sim was
    created, silently, on that mod's machine only. Inside the call it is a fact of the
    ordering rather than a convention every add-on has to honor.
    
    No-ops when no add-on contributed anything, so a mission that never asked for this does
    not find its folder written to."""
def sim_pause () -> None:
    """Pause the simulation."""
def sim_resume () -> None:
    """Resume a paused simulation."""
