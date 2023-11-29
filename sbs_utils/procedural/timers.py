from .inventory import get_inventory_value, set_inventory_value
from ..helpers import FrameContext
from ..futures import Promise

TICK_PER_SECONDS = 30
def set_timer(id_or_obj, name, seconds=0, minutes =0):
    seconds += minutes*60
    seconds *= TICK_PER_SECONDS
    seconds += FrameContext.context.sim.time_tick_counter
    set_inventory_value(id_or_obj, f"__timer__{name}", seconds)

def is_timer_set(id_or_obj, name):
    return get_inventory_value(id_or_obj, f"__timer__{name}", None) is not None


def is_timer_finished(id_or_obj, name):
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return True
    now = FrameContext.context.sim.time_tick_counter
    if now > target:
        return True
    return False

def format_time_remaining(id_or_obj, name):
    time = get_time_remaining(id_or_obj, name)
    if time is None or time ==0:
        return ""
    minutes = time // 60
    seconds = str(time % 60).zfill(2)
    return f"{minutes}:{seconds}"
    

def get_time_remaining(id_or_obj, name):
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return 0
    now = FrameContext.context.sim.time_tick_counter
    return (target - now) // TICK_PER_SECONDS
    


def is_timer_set_and_finished(id_or_obj, name):
    target = get_inventory_value(id_or_obj, f"__timer__{name}")
    if target is None or target == 0:
        return False
    now = FrameContext.context.sim.time_tick_counter
    if now > target:
        return True
    return False


def clear_timer(id_or_obj, name):
    set_inventory_value(id_or_obj, f"__timer__{name}", None)

def start_counter(id_or_obj, name):
    set_inventory_value(id_or_obj, f"__counter__{name}", FrameContext.context.sim.time_tick_counter)

def get_counter_elapsed_seconds(id_or_obj, name):
    start = get_inventory_value(id_or_obj, f"__counter__{name}")
    now =  FrameContext.context.sim.time_tick_counter
    if start is None:
        return None
    return int((now-start) / TICK_PER_SECONDS)
    

def clear_counter(id_or_obj, name):
    set_inventory_value(id_or_obj, f"__counter__{name}", None)


class Delay(Promise):
    def __init__(self,  seconds, minutes, sim) -> None:
        super().__init__()

        

        self.is_sim = sim
        if self.is_sim:
            self.timeout = FrameContext.sim_seconds + (minutes*60+seconds) 
        else:
            self.timeout = FrameContext.app_seconds + (minutes*60+seconds)

    def done(self):
        #
        # Tiny hack to just do the work in done
        #
        if self.is_sim: 
            if self.timeout < FrameContext.sim_seconds:
                self.set_result(True)
        else:
            if self.timeout < FrameContext.app_seconds:
                self.set_result(True)
        return super().done()
    
def delay_sim(seconds=0, minutes=0):
    return Delay(seconds, minutes, True)

def delay_app(seconds=0, minutes=0):
    return Delay(seconds, minutes, False)




class DelayForTests(Promise):
    def __init__(self,  seconds, minutes) -> None:
        super().__init__()
        self.count = seconds+minutes*60
        
    def done(self):
        #
        # Tiny hack to just do the work in done
        #
        self.count -= 1
        if self.count <=0:
            self.set_result(True)
        return super().done()
    
def delay_test(seconds=0, minutes=0):
    return DelayForTests(seconds, minutes)