from sbs_utils.agent import Agent, get_story_id

class Fleet(Agent):
    
    def __init__(self):
        super().__init__()
        self.id = get_story_id()