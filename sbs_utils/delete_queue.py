"""Deferred deletion of engine objects.

`sbs.delete_object()` (space objects) and `sbs.delete_grid_object()` (grid
objects) free the underlying C++ object (and its `engine_object` / `data_set`
pointers) **synchronously**. Because MAST tasks interleave across a tick, a task
that deletes an object while another task still holds a reference to it - or a
cached `engine_object`/`data_set` pointer - dereferences freed memory on its next
line: a use-after-free that crashes Cosmos to the desktop.

Both kinds are queued here: space objects via `queue()` (freed with
`delete_object`), grid objects via `queue_grid()` (freed with
`delete_grid_object`, which needs the host ship id).

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
    # Grid objects are freed with ``sbs.delete_grid_object(host_id, id)`` rather
    # than ``sbs.delete_object(id)``, so they need their host id carried along.
    # id -> host_id (a dict also dedups on the grid id).
    _pending_grid = {}

    @classmethod
    def clear(cls):
        """Drop any pending deletes (fresh mission / in-process recompile)."""
        cls._pending = set()
        cls._pending_grid = {}

    @classmethod
    def queue(cls, id):
        """Enqueue a space-object id for deferred native free. Tombstoning is the caller's job."""
        if id is not None:
            cls._pending.add(id)

    @classmethod
    def queue_grid(cls, host_id, id):
        """Enqueue a grid-object id for deferred native free via ``delete_grid_object``.

        Tombstoning (dropping the agent from ``Agent.all``/roles) is the
        caller's job, exactly as with :meth:`queue`.
        """
        if id is not None and host_id is not None:
            cls._pending_grid[id] = host_id

    @classmethod
    def has_pending(cls):
        return bool(cls._pending) or bool(cls._pending_grid)

    @classmethod
    def is_pending(cls, id):
        """True if this id is tombstoned and awaiting its deferred native free.

        Callers that report liveness from the engine (e.g. ``object_exists``)
        consult this so a script-deleted object reads as gone *immediately*,
        preserving the pre-deferral contract even though its memory is still
        alive until the end-of-handler drain. Covers both space and grid objects.
        """
        return id in cls._pending or id in cls._pending_grid

    @classmethod
    def drain(cls):
        """Free every tombstoned object. Called at the end of the event handler."""
        if not cls._pending and not cls._pending_grid:
            return
        ctx = FrameContext.context
        if ctx is None or ctx.sbs is None:
            # No valid context to free against (shouldn't happen inside the
            # handler). Keep the ids and drain on the next handler.
            return
        ids = cls._pending
        grid = cls._pending_grid
        cls._pending = set()
        cls._pending_grid = {}
        sbs = ctx.sbs
        for id in ids:
            try:
                sbs.delete_object(id)
            except BaseException as err:
                # A double-free / already-gone id must never take down the sim.
                from .procedural.execution import log
                log(f"deferred delete failed for {id}: {err}", "delete_queue", "warning")
        for id, host_id in grid.items():
            try:
                sbs.delete_grid_object(host_id, id)
            except BaseException as err:
                # A double-free / already-gone id must never take down the sim.
                from .procedural.execution import log
                log(f"deferred grid delete failed for {id} (host {host_id}): {err}", "delete_queue", "warning")
