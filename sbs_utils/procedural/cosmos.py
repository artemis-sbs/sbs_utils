from ..helpers import FrameContext

"""
Functions to the engine
"""

def sim_create() -> None:
    """ Creates a new simulation
    """    
    FrameContext.context.sbs.create_new_sim()
    

def sim_pause() -> None:
    """pauses the simulation
    """    
    FrameContext.context.sbs.pause_sim()



def sim_resume() -> None:
    """resume the simulation
    """    
    FrameContext.context.sbs.resume_sim()

