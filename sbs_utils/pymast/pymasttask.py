from .pollresults import PollResults
import inspect
from .pymastscience import PyMastScience
from .pymastcomms import PyMastComms
from functools import partial, partialmethod
import types
import sbs
from ..engineobject import EngineObject, get_task_id

class DataHolder(object):
    pass

# defining a decorator that can take anything
def label(*dargs, **dkwargs):
    def dec(func):
        def inner(*args, **kwargs):
            return func(*args, **kwargs)
        inner.__name__ = func.__name__
        return inner
    return dec

###
##
## Runs a set of generator functions
##
class PyMastTask(EngineObject):
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
        self.events = {}
        self.page = None
        self.pop_on_jump = 0
        self.current_gen = None
        self.id = get_task_id()
        self.add()
        #self.jump(label)

        self.COMMS_ORIGIN_ID = None
        self.COMMS_SELECTED_ID = None
        
        self.last_poll_result = None
        self.done = False


    @property
    def client_id(self):
        if self.page:
            return self.page.client_id
        return 0

    def end(self):
        self.last_poll_result = PollResults.OK_END
        self.done = True
            

    def tick(self, ctx):
        if ctx is None:
            print("ctx is NONE")
        
        self.sim = ctx.sim
        self.story.sim = ctx.sim
        self.scheduler.sim = ctx.sim
        self.ctx = ctx
        self.story.ctx = ctx
        self.scheduler.ctx = ctx
        self.story.task = self
        # Keep running until told to defer or you've jump 100 time
        # Arbitrary number
        throttle = 0
        is_new_jump = False
        while not self.done and throttle < 100:
            throttle += 1
            if self.pending_jump:
                #print(f"jump to {self.pending_jump}")
                res = self.do_jump()
                self.pending_pop = None
                is_new_jump = True
            elif self.pending_pop:
                # Pending jump trumps pending pop
                #print(f"pending pop to {self.pending_pop.__name__}")
                self.current_gen = self.pending_pop
                self.pending_pop = None

            
            gen = self.current_gen
            # It is possible that the label
            # did not Yield, which is OK just End 
            if gen is None:
                #print("Gen None")
                #self.last_poll_result = PollResults.OK_END
                self.end()
                self.sim = None
                return self.last_poll_result
            
            #self.last_poll_result = None
            gen_done = True
            for res in gen:
                is_new_jump = False
                if res is None:
                    #print("Label yielded None")
                    gen_done = True
                    break
                gen_done = False
                if res is not None:
                    self.last_poll_result = res
                if res == PollResults.OK_RUN_AGAIN:
                    self.sim = None
                    return self.last_poll_result
                if res == PollResults.OK_JUMP:
                    break
                
            if self.last_poll_result == PollResults.OK_JUMP:
                continue
            
            if gen_done:
                #
                # The generator finished without jumping or popping
                #
                #
                # This could be because the handler did not yield
                #
                # If there is a pending Jump DON't pop
                #
                if self.pending_jump is not None:
                #
                # jump was called and the generate just never yielded
                    pass
                elif len(self.stack)>0:
                    # if there things on the stack treat this as a pop
                    # Pop wasn't called
                    # assuming it should pop
                    self.last_poll_result = self.pop()
                else:
                    self.current_gen = self.pending_pop
                    if self.current_gen is None:
                        self.end()
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
        self.current_gen = gen
        # if gen is None:
        #     print("Get_gen failed?")
        return res

    def get_gen(self, label):
        gen = None
        res = PollResults.FAIL_END
        if inspect.isfunction(label):
            gen = label(self.story)
            res = PollResults.OK_JUMP
            #print(f"IS func {label.__name__}")
        elif inspect.ismethod(label):
            gen = label()
            res = PollResults.OK_JUMP
            #print(f"IS method {label.__name__} {gen}")
        else:
            print("Partial?")
        
        return (gen, res)
    
    def jump(self, label):
        while self.pop_on_jump>0:
            #print(f"I popped {label.__name__}")
            #self.pop_on_jump -= 1
            #self.stack.pop()
            self.pop()
        self.pending_jump = label
        # jump cancels out pops
        self.pending_pop = None
        return PollResults.OK_JUMP

    def push(self, label):
        if self.current_gen is not None:
            self.stack.append(self.current_gen)
        return self.jump(label)
    
    def quick_push(self, func):
        # The function proviced is expected to pop
        if self.current_gen is not None:
            self.stack.append(self.current_gen)
        #gen, res = self.get_gen(func)
        self.pending_jump = func 
        return PollResults.OK_JUMP

    
    def push_jump_pop(self, label):
        if self.current_gen is not None:
            self.stack.append(self.current_gen)
        self.pending_jump = label
        self.pop_on_jump += 1
        return PollResults.OK_JUMP

    def pop(self):
        if len(self.stack) > 0:
            if self.pop_on_jump >0:
                self.pop_on_jump-=1
            self.pending_pop = self.stack.pop()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END
    
    def delay(self,  seconds=0, minutes=0, use_sim=False):
        return self.push_jump_pop(lambda _: self._delay(seconds, minutes, use_sim))
        #return self.push_jump_pop(partialmethod(self._delay,seconds, minutes, use_sim))
        # self.stack.append(self.current_gen)
        # self.current_gen = self._delay(delay)
        # return PollResults.OK_RUN_AGAIN

    def _delay(self,  seconds=0, minutes=0, use_sim=False):
        if use_sim:
            delay_time = self.sim.time_tick_counter + 30 * (seconds+60*minutes)
            current_time = self.sim.time_tick_counter
        else:
            delay_time = sbs.app_seconds() + seconds+60*minutes
            current_time = sbs.app_seconds()
        
        while delay_time > current_time:
            if use_sim:
                current_time = self.sim.time_tick_counter
            else:
                current_time = sbs.app_seconds()
            yield PollResults.OK_RUN_AGAIN
        yield self.pop()

    def await_science(self, scans, player=None, npc=None):
        if player is None:
            player = self.SCIENCE_ORIGIN_ID
        if npc is None:
            npc = self.SCIENCE_SELECTED_ID

        # Then Await for it to finish
        science = PyMastScience(self, scans, player, npc)
        science.handle_selected(self.sim, player, npc, "scan")
        def pusher(story):
            return self.run_science(science)
        self.task.push_jump_pop(pusher)
        return PollResults.OK_JUMP

    def run_science(self, science):
        while science.done == False:
            yield PollResults.OK_RUN_AGAIN
        self.pop()


    def await_comms(self, buttons, player=None, npc=None):
        if player is None:
            player = self.COMMS_ORIGIN_ID
        if npc is None:
            npc = self.COMMS_SELECTED_ID


        # Create this here so the comms is updated NOW
        comms = PyMastComms(self, buttons, player, npc)
        # Then Await for it to finish
        def pusher(story):
            return comms.run()
        self.task.push_jump_pop(pusher)
        return PollResults.OK_JUMP

    # def run_comms(self, comms):
    #     while comms.done == False:
    #         yield PollResults.OK_RUN_AGAIN
    #     #print("COMMS DONE")
    #     self.pop()


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

    def on_event(self, ctx, event):
        #
        # This is another push_jump_pop
        # So if a jump occurs in unwinds the push stack for all push_jump_pop:s
        label = self.events.get(event.tag)
        if label is None:
            return
        def pusher(story):
            return self._run_event(label, ctx, event)
        self.task.push_jump_pop(pusher)
    
    def _run_event(self, label, ctx, event):    
        gen = None
        res = PollResults.FAIL_END
        if inspect.isfunction(label):
            gen = label(self.story, ctx, event)
            res = PollResults.OK_JUMP
        elif inspect.ismethod(label):
            gen = label(ctx,event)
            res = PollResults.OK_JUMP
        if gen is not None:
            for this_res in gen:
                res = this_res
                yield res
        self.last_poll_result = res
        yield self.pop()



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
            yield res
        if res == PollResults.OK_END:
            self.last_poll_result = PollResults.FAIL_END
            return self.pop()
        elif res == PollResults.FAIL_END:
            self.last_poll_result = PollResults.OK_END
            return self.pop()
        self.last_poll_result = res
        return self.pop()

            


        



        


