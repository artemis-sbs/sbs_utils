class Dirty(object):
    """class Dirty"""
    def clear_client (client_id):
        """Forget everything queued for one client.
        
        Called when a page swaps in a new layout. Every widget queued by the
        OUTGOING build belongs to a layout that is about to be replaced, and the
        incoming build is fully presented in the same pass -- so the queue holds
        nothing but orphans, each of which would otherwise re-present itself AT
        ITS OLD COORDINATES over whatever is on screen now.
        
        That is how the console's log strip landed on the end-of-game results
        screen: the last message of the game marked it dirty, the results screen
        replaced the console in the same frame, and the post-present dirty pass
        drew the strip on top of it."""
    def mark_dirty (layout_item):
        ...
    def represent_dirty ():
        ...
