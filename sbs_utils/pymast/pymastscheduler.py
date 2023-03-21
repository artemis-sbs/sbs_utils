from . import PollResults
from .pymasttask import PyMastTask, DataHolder



class PyMastScheduler:
    def __init__(self, story, label) -> None:
        self.tick_task = None
        #self.current_gen = self.start()
        self.vars = DataHolder()
        self.tasks = []
        self.remove_tasks = set()
        self.new_tasks = []
        self.scheduler = self #Alais for scoping
        self.shared = story
        self.story = story
        self.task = None
        self.page = None
        # Initial tasks
        self.tasks.append(PyMastTask(story, self, label))

    def schedule_task(self, label):
        self.schedule_a_task(PyMastTask(self.story, self, label))
        return PollResults.OK_RUN_AGAIN
    
    def schedule_a_task(self, task):
        self.new_tasks.append(task)
        return PollResults.OK_RUN_AGAIN

    def tick(self, sim):
        self.story.scheduler = self.scheduler
        for task in self.tasks:
            self.story.task = task
            self.task = task            
            task.tick(sim)
            if task.last_poll_result == PollResults.OK_END:
                self.remove_tasks.add(task)
        for finished in self.remove_tasks:
            self.tasks.remove(finished)
        self.remove_tasks.clear()
        self.tasks.extend(self.new_tasks)

    def on_event(self, sim, event):
        pass

