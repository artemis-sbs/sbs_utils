from ..helpers import FrameContext

"""
Functions to the engine
"""

def sim_create():
    """ Creates a new simulation
    """    
    FrameContext.context.sbs.create_new_sim()
    

def sim_pause():
    """pauses the simulation
    """    
    FrameContext.context.sbs.pause_sim()



def sim_resume():
    """resume the simulation
    """    
    FrameContext.context.sbs.resume_sim()

