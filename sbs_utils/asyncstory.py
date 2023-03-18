from enum import IntEnum
from sbs_utils.tickdispatcher import TickDispatcher
import inspect

class PollResults(IntEnum):
    OK_RUN_AGAIN=1
    OK_ADVANCE_TRUE =2
    OK_ADVANCE_FALSE=3
    OK_JUMP= 4
    OK_END = 99
    FAIL_END = 100


class AsyncScope:
    def __init__(self) -> None:
        self.vars = {}

    def set_value(self, key, value ):
        self.vars[key] = value

    def get_value(self, key):
        return self.vars.get(key)

###
##
## Runs a set of generator functions
##
class AsyncTask(AsyncScope):
    def __init__(self, story, scheduler, label) -> None:
        super().__init__()
        self.stack=[]
        self.delay_time = None
        self.scheduler = scheduler
        self.story = story
        self.jump(label)
        self.last_poll_result = None
            

    def tick(self, sim):
        self.sim = sim    
        # Keep running until told to defer or you've jump 100 time
        # Arbitrary number
        throttle = 0
        while throttle < 100:
            throttle += 1
            for res in self.current_gen:
                self.last_poll_result = res
                if res == PollResults.OK_RUN_AGAIN:
                    return
                if res == PollResults.OK_JUMP:
                    break
        # don't hold pointer
        self.sim = None

    def jump(self, label):
        if isinstance(label, str):
            if getattr(self.story, label):
                self.current_gen = getattr(self.story, label)()
                return PollResults.OK_JUMP
        elif inspect.isfunction(label):
            self.current_gen = label(self.story)
            return PollResults.OK_JUMP
        elif inspect.ismethod(label):
            self.current_gen = label()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END

    def push(self, label):
        self.stack.append(self.current_gen)
        return self.jump(label)

    def pop(self):
        if len(self.stack) > 0:
            self.current_gen = self.stack.pop()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END
    
    def delay(self,  delay):
        self.stack.append(self.current_gen)
        self.current_gen = self._delay(delay)
        return PollResults.OK_RUN_AGAIN
  
    def _delay(self, delay):
        delay_time = self.sim.time_tick_counter + 30 * delay
        while delay_time > self.sim.time_tick_counter:
            #print ("tick")
            yield PollResults.OK_RUN_AGAIN
        yield self.pop()

class AsyncScheduler(AsyncScope):
    def __init__(self, story, label) -> None:
        self.tick_task = None
        #self.current_gen = self.start()
        self.tasks = []
        self.remove_tasks = []
        self.new_tasks = []
        self.scheduler = self #Alais for scoping
        self.shared = story
        self.story = story
        # Initial tasks
        story.this_scheduler = self
        self.tasks.append(AsyncTask(story, self, label))

    def schedule_task(self, label):
        self.new_tasks.append(AsyncTask(self.story, self, label))
        return PollResults.OK_RUN_AGAIN

    def tick(self, sim):
        for task in self.tasks:
            self.this_task = task
            task.tick(sim)
            if task.last_poll_result == PollResults.OK_END:
                self.remove_tasks.append(task)
        for finished in self.remove_tasks:
            self.tasks.pop(finished)
        self.tasks.extend(self.new_tasks)


class AsyncStory(AsyncScope):
    def __init__(self) -> None:
        self.schedulers = []
        self.remove_scheduler = []
        self.shared = self #Alias for scoping


    def enable(self, sim, delay=0, count=None):
        self.tick_task = TickDispatcher.do_interval(sim, self, delay, count)
        self.schedulers.append(AsyncScheduler(self, "start"))

    def delay(self,  delay):
        return self.this_scheduler.this_task.delay(delay)

    def schedule_task(self, label):
        return self.this_scheduler.schedule_task(label)


    def jump(self, label):
        return self.this_scheduler.this_task.jump(label)
    def push(self, label):
        return self.this_scheduler.this_task.push(label)
    def pop(self):
        return self.this_scheduler.this_task.pop()

    def disable(self):
        if self.tick_task is not None:
            self.tick_task.stop()
            self.tick_task = None

    def __call__(self, sim, sched=None):
        self.sim = sim
        for sched in self.schedulers:
            self.this_scheduler = sched
            sched.tick(sim)
            if len(sched.tasks) == 0:
                self.remove_scheduler.append(sched)
        for finished in self.remove_scheduler:
            self.schedulers.pop(finished)
        if len(self.schedulers)==0:
            self.disable()
        self.sim = None


    def END(self):
        self.remove_tasks.append(self.this_task)

    def start(self):
        pass
