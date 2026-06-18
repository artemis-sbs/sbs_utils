from ..helpers import FrameContext

"""
Functions to the engine
"""

def sim_create() -> None:
    """Create a new simulation."""
    FrameContext.context.sbs.create_new_sim()
    

def sim_pause() -> None:
    """Pause the simulation."""
    FrameContext.context.sbs.pause_sim()



def sim_resume() -> None:
    """Resume a paused simulation."""
    FrameContext.context.sbs.resume_sim()

