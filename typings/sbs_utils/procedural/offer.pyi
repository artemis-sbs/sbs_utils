from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject
def _context (client_id, ship_id, object_id, console):
    ...
def _install_core_providers ():
    """Register the library's own providers. Called at import AND by ``offer_clear()``."""
def _offer_log (message, level='warning'):
    """Never raise out of a provider walk - one bad provider must not cost the others."""
def _quest_provider (ctx):
    """The quest provider, bound LATE.
    
    quest_driver pulls in comms (and most of the package with it), and this module is
    imported early enough that doing it at import time is a circular import: comms is
    still half-built, quest_driver fails to import, and the library silently ships with
    no quest offers at all. Importing inside the call costs one dict lookup per walk and
    removes the cycle entirely."""
def _run_provider (name, spec, ctx):
    """One provider's rows, or [] - never an exception.
    
    A provider that raises costs itself its rows and nothing else. This is not
    defensiveness for its own sake: offers feed a badge that is computed on every tile of
    every build, so an unguarded failure is both a broken screen and a log line several
    times a second."""
def offer_clear ():
    """Drop every provider, then reinstall the library's own.
    
    The shape ``urge_clear_conditions()`` + ``_install_conditions()`` uses: a reset must
    leave the core vocabulary present, or the next mission starts with no quest offers
    and nothing says why."""
def offer_context_here ():
    """``(client_id, ship_id)`` for the console currently being drawn, or ``(None, None)``.
    
    The ship is the console's HOME ship, not ``get_ship_of_client``: a main screen
    driving a cinematic answers with the SUBJECT of the shot, so a badge would count the
    enemy's jobs. Same rule the log panel's scope already follows."""
def offer_count (client_id=None, ship_id=None, object_id=None, console=None):
    """How many offers can be TAKEN right now.
    
    Excludes ``pending`` ones: a count is a promise that there is something to act on,
    and a POSTING job that only somebody else can hand you is not that."""
def offer_count_here ():
    """How many offers this console could act on. The shape a badge wants."""
def offer_generation ():
    """A number that changes whenever the offer picture might have.
    
    Folds in ``quest_generation()`` so a quest going IDLE moves this without every
    caller having to remember to touch it. Drive an `on change` off this rather than
    calling ``offers()`` every frame - and note that a SIGNAL cannot be used here,
    because a signal does not wake ``await gui()``."""
def offer_mission_providers ():
    """The providers a MISSION registered - everything that is not core.
    
    This is what the restart-reset audit probes: ``offer_clear()`` reinstalls the core
    ones, so a non-zero count here after a reset means an addon leaked into the next run."""
def offer_providers ():
    """Every registered provider name, sorted. For tools and tests."""
def offer_record (key, title, detail='', kind='job', source=None, agent_id=None, where='', app=None, route=None, consoles=None, pending=False, sort=100, data=None, take=None, description=''):
    """One offer, as plain data.
    
    Args:
        key (str): Stable identity, unique across providers. The digest diffs these to
            work out what is NEW, so it must not change between calls for the same
            offer - prefer ``"quest:<agent>:<quest id>"`` over anything positional.
        title (str): Short ASCII label. The row's first line.
        detail (str): One line - the reward, or what the job wants.
        description (str): The long text - what the job IS. Shown in full in the board's
            reading pane; a record without one shows its ``detail`` there instead.
        kind (str): One of ``OFFER_KINDS``; drives the row's glyph and lets the digest
            say "2 jobs and a contact" instead of "3 things".
        source (str): Who is offering, by name ("DS 1", "Prof. Storm").
        agent_id: The object offering it, when one exists. ``None`` for a game-scoped
            quest. This is what lets a comms selection or a science scan say that THIS
            contact has work.
        where (str): ASCII instruction for a console that cannot take this
            ("Comms - hail DS 1"). Shown only when the reading console cannot act.
        app (str): ePADD app to open when the row is selected.
        route (str): Comms path, when the offer is taken by hailing rather than by a tab.
        consoles (str): Comma-separated console names that may take it, in the same
            spelling ``QUEST_ACCEPT_CONSOLES`` uses. ``None`` means anyone.
        pending (bool): Listed, but not takeable yet - the ``QuestState.POSTING`` case,
            where something else must offer it to you. **Never counted in a badge or a
            digest**: a count means "you can take this now".
        sort (int): Ascending. Ties fall back to title.
        data (dict): Anything the provider wants to carry through to its own renderer.
        take (callable): ``fn(client_id, record)`` - take this offer HERE.
    
            The Offers board is where untaken work is accepted, so an offer the board
            can act on carries this: an idle quest (it marks the quest active) and a
            hangar sortie (it assigns the pilot). WHO may press it is ``consoles``.
    
            An offer taken some other way has none - an Open Universe station job is
            taken by hailing the station, and its ``where`` says so."""
def offer_register (name, fn, domain=None):
    """Declare a source of offers.
    
    ``fn(ctx)`` returns a list of ``offer_record``s. ``ctx`` is a ``MastDataObject``
    carrying ``client_id``, ``ship_id``, ``console`` and ``object_id``; an
    ``object_id`` of ``None`` means "everything for this crew", and a real id means
    "what does this one object have".
    
    Same contract as ``urge_register_condition`` and ``amd_action_register``:
    re-registering a name with a DIFFERENT function raises, re-registering the identical
    one is a no-op so reloading an addon is safe."""
def offer_touch ():
    """A provider's world changed. Bumps the fingerprint an `on change` watches."""
def offer_unregister (name):
    """Drop one provider. Returns True if it was there."""
def offers (client_id=None, ship_id=None, object_id=None, kinds=None, console=None):
    """Every offer on the table, sorted.
    
    Args:
        client_id: The console asking, when there is one.
        ship_id: The ship the crew are flying.
        object_id: Narrow to what THIS object is offering. ``None`` (the default)
            means everything for this crew.
        kinds: Restrict to these kinds - a string, or a list of them.
        console (str): The console type asking, for providers that are station-specific.
    
    Returns:
        list: ``offer_record``s, ``pending`` ones included. Sorted by ``sort`` then
        ``title``, so a board's order does not move between frames."""
def offers_for_object (object_id, client_id=None, ship_id=None):
    """What this one object is offering. The hook a comms selection or a scan reads."""
def offers_here (kinds=None):
    """Offers for the console currently being drawn."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
