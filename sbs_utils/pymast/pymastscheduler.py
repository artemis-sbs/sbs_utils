from .pollresults import PollResults
from .pymasttask import PyMastTask, DataHolder



class PyMastScheduler:
    def __init__(self, story, label) -> None:
        self.tick_task = None
        #self.current_gen = self.start()
        self.vars = DataHolder()
        self.tasks = []
        self.remove_tasks = set()
        self.new_tasks = set()
        self.scheduler = self #Alais for scoping
        self.shared = story
        self.story = story
        self.page = None
        self.task = PyMastTask(story, self, label)
        # Initial tasks
        self.tasks.append(self.task)

    @property
    def client_id(self):
        if self.task and self.task.page:
            return self.task.page.client_id
        return 0

    def schedule_task(self, label):
        task = PyMastTask(self.story, self, label)
        task.page = self.task.page
        self.schedule_a_task(task)
        return task
    
    def schedule_a_task(self, task):
        self.new_tasks.add(task)
        return PollResults.OK_ADVANCE_TRUE

    def tick(self, sim):
        for task in self.tasks:
            self.story.task = task
            self.story.scheduler = self
            self.scheduler = self
            self.task = task            
            task.tick(sim)
            if task.last_poll_result == PollResults.OK_END:
                self.remove_tasks.add(task)
        for finished in self.remove_tasks:
            self.tasks.remove(finished)
            task.destroyed()
        self.remove_tasks.clear()
        self.tasks.extend(self.new_tasks)
        self.new_tasks.clear()

    
