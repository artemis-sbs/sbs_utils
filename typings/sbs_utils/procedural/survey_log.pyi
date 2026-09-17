from sbs_utils.agent import Agent
def _all ():
    """Every entry. **READ-ONLY - this must never write.**
    
    It used to create the list lazily when it was missing, which meant the reset
    ledger's own probe (`xess_log_count`) gave `Agent.SHARED` an inventory by ASKING
    whether it had one. `test_restart_reset` reported `Agent._has_inventory: 1`
    surviving a reset with nothing running - state conjured by measuring it. A reader
    that writes is the one thing an audit cannot see past."""
def _name_of (client_id):
    """The crew member who took the reading, by NAME.
    
    A client id means nothing to somebody reading this later, and the console that
    took a reading may be holding somebody else by then."""
def _save (log):
    ...
def _site_of (client_id):
    ...
def _stamp ():
    ...
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def xess_log (kind, subject, text, by=None, site=None):
    """File one reading, or update the one already filed for this subject.
    
    Args:
        kind (str): what sort of reading - "scan", "shot", whatever a mission files.
        subject (str): what was read. The room's node name, a body, a console.
        text (str): the reading itself.
        by (optional): the CLIENT that took it. Stored as the crew member's name,
            because a client id means nothing to somebody reading the log later.
        site (optional): the interior it was taken on. Defaults to the party's.
    
    Returns:
        dict: the entry, new or updated."""
def xess_log_bump ():
    ...
def xess_log_clear ():
    """Forget the whole log. The mission reset calls this.
    
    Only writes when there is something to forget, so a reset on a mission that never
    boarded anything does not hand `Agent.SHARED` an inventory it did not have. The
    reset ledger reports exactly that as leftover state."""
def xess_log_count (kind=None):
    """How many readings there are. What the tile's badge says."""
def xess_log_entries (kind=None, site=None):
    """Every reading, newest first. Filtered by kind or site when asked."""
def xess_log_get (entry_id):
    ...
def xess_log_last (kind=None):
    """The newest reading, which is what the DEVICE shows. None when there are none."""
def xess_log_revision ():
    ...
