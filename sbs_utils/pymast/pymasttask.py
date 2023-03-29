from .pollresults import PollResults
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
        self.task = self
        self.pending_jump = label
        self.pending_pop = None
        self.await_gen = None
        self.events = {}
        self.page = None
        self.pop_on_jump = 0
        #self.jump(label)
        
        self.last_poll_result = None
        self.last_popped_poll_result = None
        self.done = False


    def end(self):
        self.last_poll_result = PollResults.OK_END
        self.done = True
            

    def tick(self, sim):
        # if sim is None:
        #     self.last_poll_result = PollResults.OK_RUN_AGAIN
        #     return
        
        self.sim = sim
        self.story.sim = sim
        self.scheduler.sim = sim
        # Keep running until told to defer or you've jump 100 time
        # Arbitrary number
        throttle = 0
        while not self.done and throttle < 100:
            throttle += 1
            if self.pending_jump:
                self.do_jump()

            if self.pending_pop:
                self.current_gen = self.pending_pop
                self.pending_pop = None
            
            gen = self.await_gen if self.await_gen else self.current_gen
            # It is possible that the label
            # did not Yield, which is OK just End 
            if gen is None:
                self.last_poll_result = PollResults.OK_END
                self.sim = None
                return self.last_poll_result
            gen_done = True
            for res in gen:
                gen_done = False                
                self.last_poll_result = res
                if res == PollResults.OK_RUN_AGAIN:
                    self.sim = None
                    return
                if res == PollResults.OK_JUMP:
                    break
            if gen_done:
                if len(self.stack)>0:
                    return self.pop()
                elif self.await_gen:
                    self.await_gen = None
                    return
                else:
                    self.current_gen = self.pending_pop
                    if self.current_gen is None:
                        self.last_poll_result = PollResults.OK_END
                    else:
                        self.last_poll_result = PollResults.OK_JUMP
                    self.sim = None
                    return self.last_poll_result
                    


          
        # don't hold pointer
        self.sim = None
        return self.last_poll_result

    def do_jump(self):
        label = self.pending_jump
        self.pending_jump = None
        gen, res = self.get_gen(label)
        if res == PollResults.OK_JUMP:
            self.current_gen = gen
        return res

    def get_gen(self, label):
        gen = None
        res = PollResults.FAIL_END
        if isinstance(label, str):
            if getattr(self.story, label):
                gen = getattr(self.story, label)()
                res= PollResults.OK_JUMP
        elif inspect.isfunction(label):
            gen = label(self.story)
            res = PollResults.OK_JUMP
        elif inspect.ismethod(label):
            gen = label()
            res = PollResults.OK_JUMP
        return (gen, res)
    
    def jump(self, label):
        while self.pop_on_jump>0:
            print(f"I popped {label.__name__}")
            self.pop()
        self.pending_jump = label
        return PollResults.OK_JUMP

    def push(self, label):
        self.stack.append(self.current_gen)
        return self.jump(label)
    
    def push_jump_pop(self, label):
        self.stack.append(self.current_gen)
        self.pending_jump = label
        self.pop_on_jump += 1
        return PollResults.OK_JUMP

    def pop(self):
        self.last_popped_poll_result = self.last_poll_result
        #pickup where you left off
        if len(self.stack) > 0:
            if self.pop_on_jump >0:
                self.pop_on_jump-=1
            self.pending_pop = self.stack.pop()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END
    
    def delay(self,  delay):
        return self.quick_push(lambda _: self._delay(delay))
        # self.stack.append(self.current_gen)
        # self.current_gen = self._delay(delay)
        # return PollResults.OK_RUN_AGAIN
  
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
        comms = PyMastComms(self, player, npc, buttons, False)
        while comms.done == False:
            yield PollResults.OK_RUN_AGAIN
        self.await_gen = None

    def await_gui(self, buttons, timeout, on_message=None, test_refresh=None, test_end_await = None, on_disconnect=None):
        if self.page is None:
            return
        page = self.page
        page.on_message_cb = on_message
        page.test_refresh_cb = test_refresh
        page.test_end_await_cb = test_end_await
        page.disconnect_cb = on_disconnect
        page.set_buttons(buttons)
        # page.present(self.story.sim, None)
        # self.await_gen = self.run_gui()
        #return PollResults.OK_RUN_AGAIN
        page.run(timeout)
        return PollResults.OK_JUMP
    
    
    def watch_event(self, event_tag, label):
        self.events[event_tag] = label

    def on_event(self, sim, event):
        #
        # This is another push_jump_pop
        # So if a jump occurs in unwinds the push stack for all push_jump_pop:s
        label = self.events.get(event.tag)
        if label is None:
            return
        def pusher(story):
            return self._run_event(label, sim, event)
        self.task.push_jump_pop(pusher)
    
    def _run_event(self, label, sim, event):    
        gen, res = self.task.get_gen(label)
        if gen is not None:
            for this_res in gen:
                res = this_res
                yield res
        self.last_poll_result = res
        return self.pop()



    def quick_push(self, func):
        # The function proviced is expected to pop
        self.stack.append(self.current_gen)
        #gen, res = self.get_gen(func)
        self.pending_jump = func 
        return PollResults.OK_JUMP

    def behave_sel(self,*labels):
        return self.quick_push(lambda _: self._run_sel(labels))

    def _run_sel(self, labels):
        final_res = None
        for label in labels:
            gen, res = self.task.get_gen(label)
            gen_done = True
            for res in gen:
                gen_done = False
                final_res = res
                if res == PollResults.FAIL_END:
                    break
                if res == PollResults.OK_END:
                    break
                #if res is None:
                #    res = PollResults.OK_RUN_AGAIN
                # Keep running this generator
                # As long as needed
                yield res
            # If FAIL try the next Label
            if final_res == PollResults.FAIL_END:
                continue
            # if SUCCESS then done with this try
            if final_res == PollResults.OK_END:
                self.last_poll_result = final_res
                return self.pop()
            # The generator is no longer running code
            if gen_done:
                continue
            # Run next label
            yield PollResults.OK_RUN_AGAIN
        # OK All label ran, final result
        self.last_poll_result = final_res
        return self.pop()
        

    def behave_seq(self,*labels):
        return self.quick_push(lambda _: self._run_seq(labels))

    def _run_seq(self, labels):
        final_res = None
        for label in labels:
            gen, res = self.task.get_gen(label)
            gen_done = True
            for res in gen:
                gen_done = False
                final_res = res
                if res == PollResults.FAIL_END:
                    break
                if res == PollResults.OK_END:
                    break
                #if res is None:
                #    res = PollResults.OK_RUN_AGAIN
                # Keep running this generator
                # As long as needed
                yield res
            # If success Run the next Label
            if final_res == PollResults.OK_END:
                continue
            # if Fail then done with this try
            if final_res == PollResults.FAIL_END:
                self.last_poll_result = final_res
                return self.pop()

            # Got to the end of the code and didn't return anything
            if gen_done:
                self.last_poll_result = PollResults.FAIL_END
                return self.pop()
            # Run next label
            yield PollResults.OK_RUN_AGAIN
        # OK All label ran, final result
        self.last_poll_result = final_res
        return self.pop()

    def behave_until(self, poll_result, label):
        return self.quick_push(lambda _: self._run_until(poll_result, label))

    def _run_until(self, poll_result, label):
        gen, res = self.task.get_gen(label)
        gen_done = True
        for this_res in gen:
            gen_done = False
            res = this_res
            if res == poll_result:
                break
            yield res
        if gen_done:
            # Run again until we get the desired result
            gen, res = self.task.get_gen(label)

            
        self.last_poll_result = res
        return self.pop()


    def behave_invert(self, label):
        return self.quick_push(lambda _: self._run_invert(label))

    def _run_invert(self, label):
        gen, res = self.task.get_gen(label)
        for res in gen:
            pass
        if res == PollResults.OK_END:
            self.last_poll_result = PollResults.FAIL_END
            return self.pop()
        elif res == PollResults.FAIL_END:
            self.last_poll_result = PollResults.OK_END
            return self.pop()
        self.last_poll_result = res
        return self.pop()

            


        



        


