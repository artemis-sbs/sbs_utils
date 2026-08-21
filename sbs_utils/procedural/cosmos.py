from ..helpers import FrameContext

"""
Functions to the engine
"""

def sim_create() -> None:
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
    not find its folder written to.

    Re-registers add-on ship data AFTERWARDS, for the same reason and in the same spirit.
    Rebuilding the table is how the engine loses everything `add_extra_ship_data` was told
    before this point, and a mission registers at story load - which is always before its
    first map calls this. Nothing reports the loss; it arrives later as a spawn failing for
    a hull the engine no longer has. Replaying here makes it an ordering fact rather than
    something every add-on has to remember.

    Then SAYS what could not be replayed. The replay only knows about files registered
    through `ship_data_add_extra`; a mod that calls `sbs.add_extra_ship_data()` itself is
    invisible to it, and its hulls are gone from this point on with nothing reporting it.
    This is the only moment the fact is both known and still worth printing.
    """
    from .ship_data_mod import ship_data_flush_mod_file
    from .ship_data import extra_replay, extra_report_untold
    ship_data_flush_mod_file()
    FrameContext.context.sbs.create_new_sim()
    extra_replay()
    extra_report_untold()
    

def sim_pause() -> None:
    """Pause the simulation."""
    FrameContext.context.sbs.pause_sim()



def sim_resume() -> None:
    """Resume a paused simulation."""
    FrameContext.context.sbs.resume_sim()

