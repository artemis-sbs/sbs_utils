from sbs_utils.helpers import FrameContext
class GarbageCollector(object):
    """class GarbageCollector"""
    def add_garbage_collect (cb):
        ...
    def clear ():
        """Drop tracked GC items (fresh mission / in-process recompile)."""
    def collect ():
        ...
    def remove_garbage_collect (cb):
        ...
