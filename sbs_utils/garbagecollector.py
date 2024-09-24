from .helpers import FrameContext

class GarbageCollector:
    _items = set()
    _done = set()
    next_run = 0

    def add_garbage_collect(cb):
        GarbageCollector._items.add(cb)
    def remove_garbage_collect(cb):
        GarbageCollector._done.add(cb)

    def collect():
        #run every 30 seconds
        now = FrameContext.sim_seconds
        if GarbageCollector.next_run > now:
            return
        
        GarbageCollector.next_run = now + 30
        GarbageCollector._items -= GarbageCollector._done
        GarbageCollector._done = set()
        # print(f"GARBAGE COLLECT {len(GarbageCollector._items)}")
        for cb in GarbageCollector._items:
            if cb():
                GarbageCollector._done.add(cb)
        






