from . import PollResults
import inspect
from .pymastscience import PyMastScience
from .pymastcomms import PyMastComms


class DataHolder(object):
    pass
###
##
## Runs a set of generator functions
##
class PyMastTask:
    def __init__(self, story, scheduler, label) -> None:
        super().__init__()
        self.vars = DataHolder()
        self.stack=[]
        self.delay_time = None
        self.scheduler = scheduler
        self.story = story
        self.pending_jump = label
        self.await_gen = None
        #self.jump(label)
        
        self.last_poll_result = None
            

    def tick(self, sim):
        self.sim = sim
        self.story.sim = sim
        self.scheduler.sim = sim
        # Keep running until told to defer or you've jump 100 time
        # Arbitrary number
        throttle = 0
        while throttle < 100:
            throttle += 1
            if self.pending_jump:
                self.do_jump()
            
            gen = self.await_gen if self.await_gen else self.current_gen
            # It is possible that the label
            # did not Yield, which is OK just End 
            if gen is None:
                self.last_poll_result = PollResults.OK_END
                return self.last_poll_result

            for res in gen:
                self.last_poll_result = res
                if res == PollResults.OK_RUN_AGAIN:
                    return
                if res == PollResults.OK_JUMP:
                    break

        # don't hold pointer
        self.sim = None
        return self.last_poll_result

    def do_jump(self):
        label = self.pending_jump
        self.pending_jump = None
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
    
    def jump(self, label):
        self.pending_jump = label
        return PollResults.OK_JUMP

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

    def await_science(self, player, npc, scans):
        self.await_gen = self.run_science(player, npc, scans)
        return PollResults.OK_RUN_AGAIN

    def run_science(self, player, npc, scans):
        science = PyMastScience(self, player, npc, scans)
        while science.done == False:
            yield PollResults.OK_RUN_AGAIN
        self.await_gen = None

    def await_comms(self, player, npc, buttons):
        self.await_gen = self.run_comms(player, npc, buttons)
        return PollResults.OK_RUN_AGAIN

    def run_comms(self, player, npc, buttons):
        comms = PyMastComms(self, player, npc, buttons)
        while comms.done == False:
            yield PollResults.OK_RUN_AGAIN
        self.await_gen = None

    def await_gui(self, buttons, timeout):
        self.await_gen = self.run_comms( buttons, timeout)
        return PollResults.OK_RUN_AGAIN

    def run_gui(self, buttons, timeout):
        gui = PyMastGui(self, buttons)
        delay_time = self.sim.time_tick_counter + 30 * timeout
        while gui.done == False:
            if delay_time > self.sim.time_tick_counter:
                break
            yield PollResults.OK_RUN_AGAIN
        self.await_gen = None

