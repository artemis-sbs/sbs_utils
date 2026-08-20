import weakref
class Dirty:
    dirty = {}

    def mark_dirty(layout_item):
        if layout_item is None:
            return
        CID = layout_item.client_id
        if CID is None:
            return
        client_dirt = Dirty.dirty.get(CID, set())
        client_dirt.add(layout_item)

        Dirty.dirty[CID] = client_dirt


    def clear_client(client_id):
        """Forget everything queued for one client.

        Called when a page swaps in a new layout. Every widget queued by the
        OUTGOING build belongs to a layout that is about to be replaced, and the
        incoming build is fully presented in the same pass -- so the queue holds
        nothing but orphans, each of which would otherwise re-present itself AT
        ITS OLD COORDINATES over whatever is on screen now.

        That is how the console's log strip landed on the end-of-game results
        screen: the last message of the game marked it dirty, the results screen
        replaced the console in the same frame, and the post-present dirty pass
        drew the strip on top of it.
        """
        if client_id is None:
            return
        Dirty.dirty.pop(client_id, None)


    def represent_dirty():
        from ...helpers import FakeEvent
        # Allow marking dirty while processing dirty
        cur = Dirty.dirty.items()
        Dirty.dirty = {}
        for cid, cid_set in cur:
            e = FakeEvent(cid, "gui_present")
            for item in cid_set:
                item.represent(e)
