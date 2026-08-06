from sbs_utils.helpers import FrameContext
class DeleteQueue(object):
    """class DeleteQueue"""
    def clear ():
        """Drop any pending deletes (fresh mission / in-process recompile)."""
    def drain ():
        """Free every tombstoned object. Called at the end of the event handler."""
    def has_pending ():
        ...
    def is_pending (id):
        """True if this id is tombstoned and awaiting its deferred native free.
        
        Callers that report liveness from the engine (e.g. ``object_exists``)
        consult this so a script-deleted object reads as gone *immediately*,
        preserving the pre-deferral contract even though its memory is still
        alive until the end-of-handler drain. Covers both space and grid objects."""
    def queue (id):
        """Enqueue a space-object id for deferred native free. Tombstoning is the caller's job."""
    def queue_grid (host_id, id):
        """Enqueue a grid-object id for deferred native free via ``delete_grid_object``.
        
        Tombstoning (dropping the agent from ``Agent.all``/roles) is the
        caller's job, exactly as with :meth:`queue`."""
