from ..spaceobject import MSpawnPlayer, SpaceObject, MSpawnActive, MSpawnPassive
from .mastscheduler import MastAsyncTask, MastScheduler
from ..gridobject import GridObject as TheGridObject


class MastSpaceObject(SpaceObject):
    def __init__(self, scheduler: MastScheduler):
        super().__init__()
        self.scheduler = scheduler
        self.tasks = []

    def destroyed(self):
        task: MastAsyncTask
        for task in self.tasks:
            task.end()
        self.tasks.clear()
        self.remove()
        self.scheduler = None

    def start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        inputs = inputs if inputs is not None else {}
        inputs['self'] = self
        self.scheduler.start_task(label, inputs, task_name)


class PlayerShip(MastSpaceObject, MSpawnPlayer):
    def __init__(self, scheduler):
        super().__init__(scheduler)


class Npc(MastSpaceObject, MSpawnActive):
    def __init__(self, scheduler):
        super().__init__(scheduler)

class Terrain(MastSpaceObject, MSpawnPassive):
    def __init__(self, scheduler):
        super().__init__(scheduler)


class GridObject(TheGridObject):
    def __init__(self, scheduler: MastScheduler):
        super().__init__()
        self.scheduler = scheduler
        self.tasks = []

    def destroyed(self):
        task: MastAsyncTask
        for task in self.tasks:
            task.end()
        self.tasks.clear()
        self.remove()
        self.scheduler = None

    def start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        inputs = inputs if inputs is not None else {}
        inputs['self'] = self
        self.scheduler.start_task(label, inputs, task_name)
