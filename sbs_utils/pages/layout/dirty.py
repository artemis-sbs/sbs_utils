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


    def represent_dirty():
        from ...helpers import FakeEvent
        for cid, cid_set in Dirty.dirty.items():
            e = FakeEvent(cid, "gui_present")
            for item in cid_set:
                item.represent(e)
        Dirty.dirty = {}


