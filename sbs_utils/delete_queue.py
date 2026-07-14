"""Deferred deletion of engine objects.

`sbs.delete_object()` frees the underlying C++ object (and its `engine_object` /
`data_set` pointers) **synchronously**. Because MAST tasks interleave across a
tick, a task that deletes an object while another task still holds a reference to
it - or a cached `engine_object`/`data_set` pointer - dereferences freed memory
on its next line: a use-after-free that crashes Cosmos to the desktop.

To close that window the native free is **deferred**:

1. A delete request **tombstones** the agent immediately (`destroyed()` drops it
   from `Agent.all`/roles), so `object_exists()`/`to_object()` report it gone this
   instant, and it enqueues the id here. The native memory is left alive.
2. `drain()` runs at the end of `cosmos_event_handler`, after
   `TickDispatcher.dispatch_tick()` has resumed every task for this event - the
   one point where no MAST task is suspended mid-statement - and calls the real
   `sbs.delete_object()` then.

Within a single handler the raw memory therefore stays valid for the whole tick
pass, so another task touching the just-deleted object this tick reads live
memory (and guarded `->END if not object_exists(id)` code bails cleanly) instead
of crashing. The set dedups, so a double delete is a harmless no-op.

This does NOT cover a holder that cached the raw `engine_object`/`data_set`
pointer across ticks and derefs it after the slot is later reused (that needs
engine-side generational handles); it does eliminate the same-tick crash, which
is the dominant path.
"""

from .helpers import FrameContext


class DeleteQueue:
    _pending = set()

    @classmethod
    def clear(cls):
        """Drop any pending deletes (fresh mission / in-process recompile)."""
        cls._pending = set()

    @classmethod
    def queue(cls, id):
        """Enqueue an id for deferred native free. Tombstoning is the caller's job."""
        if id is not None:
            cls._pending.add(id)

    @classmethod
    def has_pending(cls):
        return bool(cls._pending)

    @classmethod
    def is_pending(cls, id):
        """True if this id is tombstoned and awaiting its deferred native free.

        Callers that report liveness from the engine (e.g. ``object_exists``)
        consult this so a script-deleted object reads as gone *immediately*,
        preserving the pre-deferral contract even though its memory is still
        alive until the end-of-handler drain.
        """
        return id in cls._pending

    @classmethod
    def drain(cls):
        """Free every tombstoned object. Called at the end of the event handler."""
        if not cls._pending:
            return
        ctx = FrameContext.context
        if ctx is None or ctx.sbs is None:
            # No valid context to free against (shouldn't happen inside the
            # handler). Keep the ids and drain on the next handler.
            return
        ids = cls._pending
        cls._pending = set()
        sbs = ctx.sbs
        for id in ids:
            try:
                sbs.delete_object(id)
            except BaseException as err:
                # A double-free / already-gone id must never take down the sim.
                from .procedural.execution import log
                log(f"deferred delete failed for {id}: {err}", "delete_queue", "warning")
