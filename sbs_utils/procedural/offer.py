"""Offers - what the world has for you that you have not taken.

A **quest** is the record of work you HAVE. An **offer** is the answer to a different
question: *what is there?* The two overlap in exactly one case - a quest sitting at
``QuestState.IDLE`` is both - and that is correct.

The distinction exists because the answer to "what is there" is not always a quest, and
in the two places it matters most it is provably not one:

* Open Universe computes a station's work from live standing at the moment you hail it
  (``universe_side_work_offers``), so its reward is a number that moves. Freezing it into
  an IDLE quest would list a price that is already wrong.
* Neither OU's station jobs nor LegendaryMissions' hangar sortie board become quests
  until AFTER you accept them, so nothing could count an untaken one.

Rather than invent a lifetime for a "quest that is not yours yet" - when does it expire,
who reaps it, what happens to the fifty IDLE rows a campaign accumulates - offers are
**computed on demand by providers**. A provider is a function that answers "what do you
have for this crew (or for this one object) right now". Nothing is stored, so nothing
goes stale and nothing needs reaping.

    offer_register("quest", quest_offer_provider, domain="core")

    for o in offers(client_id, ship_id):
        print(o.title, o.detail)

Offers feed a badge, a board, a comms selection title and a digest. None of those may
fail because one provider is having a bad day, so a provider that raises costs itself its
rows and nothing else - the same discipline ``gui_app_badge`` already enforces, and for
the same measured reason.
"""
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural.query import to_id
from sbs_utils.helpers import FrameContext


#: name -> {"fn", "domain"}. Providers registered with ``domain="core"`` are the
#: library's own and survive ``offer_clear()``; anything else belongs to the mission and
#: is dropped on reset.
_PROVIDERS = {}

#: Providers running right now, so one that asks what the OTHER providers are offering is
#: answered rather than re-entered. Cleared in a `finally`, so it cannot outlive the call
#: and needs no reset-ledger entry. See ``gui_app_badge`` (gui/epadd.py) for the bug this
#: shape prevents: a status provider that consulted its siblings was entered 332 times for
#: one badge, unwinding only when Python's recursion limit tripped.
_RUNNING = set()

#: (provider name, exception type) pairs already reported. A provider that keeps failing
#: is worth saying ONCE: offers are computed per tile per build AND by the badge ticker,
#: so an unguarded log is several lines a second for the rest of the mission.
_OFFER_REPORTED = set()

#: Bumped by ``offer_touch()``. Combined with ``quest_generation()`` to make a cheap
#: fingerprint a GUI can drive an `on change` from. Deliberately NOT reset: a cache keyed
#: on a counter that restarts at 0 can serve an entry from before the restart, which is
#: the same trap ``_QUEST_GEN`` documents.
_OFFER_GEN = [0]


#: Kinds an offer can be. Not enforced - a mission may invent one - but these are what
#: the board knows how to draw an icon for.
OFFER_KINDS = ("job", "sortie", "trade", "contact", "lore")


def _offer_log(message, level="warning"):
    """Never raise out of a provider walk - one bad provider must not cost the others."""
    try:
        from .execution import log
        log(message, "offer", level)
    except Exception:
        pass


# --- the record ---------------------------------------------------------------
def offer_record(key, title, detail="", kind="job", source=None, agent_id=None,
                 where="", app=None, route=None, consoles=None, pending=False,
                 sort=100, data=None, take=None, description=""):
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
            taken by hailing the station, and its ``where`` says so.
    """
    return MastDataObject({
        "key": str(key), "title": str(title), "detail": str(detail or ""),
        "description": str(description or ""),
        "kind": str(kind or "job"), "source": source, "agent_id": agent_id,
        "where": str(where or ""), "app": app, "route": route,
        "consoles": consoles, "pending": bool(pending),
        "sort": int(sort or 0), "data": data or {}, "take": take,
    })


# --- the registry -------------------------------------------------------------
def offer_register(name, fn, domain=None):
    """Declare a source of offers.

    ``fn(ctx)`` returns a list of ``offer_record``s. ``ctx`` is a ``MastDataObject``
    carrying ``client_id``, ``ship_id``, ``console`` and ``object_id``; an
    ``object_id`` of ``None`` means "everything for this crew", and a real id means
    "what does this one object have".

    Same contract as ``urge_register_condition`` and ``amd_action_register``:
    re-registering a name with a DIFFERENT function raises, re-registering the identical
    one is a no-op so reloading an addon is safe.
    """
    key = str(name).strip()
    if not key:
        raise ValueError("an offer provider needs a name")
    if not callable(fn):
        raise ValueError(f"offer provider {key!r} is not callable")
    prior = _PROVIDERS.get(key)
    if prior is not None and prior["fn"] is not fn:
        who = f" (from {domain})" if domain else ""
        raise ValueError(f"offer provider {key!r}{who} is already registered by "
                         f"something else")
    _PROVIDERS[key] = {"fn": fn, "domain": domain}
    offer_touch()
    return key


def offer_unregister(name):
    """Drop one provider. Returns True if it was there."""
    if _PROVIDERS.pop(str(name).strip(), None) is None:
        return False
    offer_touch()
    return True


def offer_providers():
    """Every registered provider name, sorted. For tools and tests."""
    return sorted(_PROVIDERS)


def offer_mission_providers():
    """The providers a MISSION registered - everything that is not core.

    This is what the restart-reset audit probes: ``offer_clear()`` reinstalls the core
    ones, so a non-zero count here after a reset means an addon leaked into the next run.
    """
    return sorted(k for k, v in _PROVIDERS.items() if v.get("domain") != "core")


def offer_clear():
    """Drop every provider, then reinstall the library's own.

    The shape ``urge_clear_conditions()`` + ``_install_conditions()`` uses: a reset must
    leave the core vocabulary present, or the next mission starts with no quest offers
    and nothing says why.
    """
    _PROVIDERS.clear()
    _OFFER_REPORTED.clear()
    _RUNNING.clear()
    _install_core_providers()
    offer_touch()


# --- the generation counter ---------------------------------------------------
def offer_touch():
    """A provider's world changed. Bumps the fingerprint an `on change` watches."""
    _OFFER_GEN[0] += 1


def offer_generation():
    """A number that changes whenever the offer picture might have.

    Folds in ``quest_generation()`` so a quest going IDLE moves this without every
    caller having to remember to touch it. Drive an `on change` off this rather than
    calling ``offers()`` every frame - and note that a SIGNAL cannot be used here,
    because a signal does not wake ``await gui()``.
    """
    try:
        from .quest import quest_generation
        return (quest_generation() << 16) ^ _OFFER_GEN[0]
    except Exception:
        return _OFFER_GEN[0]


# --- asking -------------------------------------------------------------------
def _context(client_id, ship_id, object_id, console):
    return MastDataObject({"client_id": client_id, "ship_id": ship_id,
                           "object_id": object_id, "console": console})


def _run_provider(name, spec, ctx):
    """One provider's rows, or [] - never an exception.

    A provider that raises costs itself its rows and nothing else. This is not
    defensiveness for its own sake: offers feed a badge that is computed on every tile of
    every build, so an unguarded failure is both a broken screen and a log line several
    times a second.
    """
    if name in _RUNNING:
        return []                       # asked what the others offer; no answer yet
    _RUNNING.add(name)
    try:
        rows = spec["fn"](ctx)
    except Exception as e:              # noqa: BLE001 - an offer never takes a page down
        key = (name, type(e).__name__)
        if key not in _OFFER_REPORTED:
            _OFFER_REPORTED.add(key)
            # NAME THE CAUSE. Without it this is the same unactionable line forever.
            _offer_log(f"offer provider {name!r} raised {type(e).__name__}: {e}")
        return []
    finally:
        _RUNNING.discard(name)
    if not rows:
        return []
    out = []
    for r in rows:
        if r is not None:
            out.append(r)
    return out


def offers(client_id=None, ship_id=None, object_id=None, kinds=None, console=None):
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
        ``title``, so a board's order does not move between frames.
    """
    ctx = _context(client_id, ship_id, object_id, console)
    want = None
    if kinds is not None:
        want = {kinds} if isinstance(kinds, str) else set(kinds)
    rows = []
    for name in sorted(_PROVIDERS):
        for r in _run_provider(name, _PROVIDERS[name], ctx):
            if want is not None and r.get("kind") not in want:
                continue
            rows.append(r)
    rows.sort(key=lambda r: (int(r.get("sort") or 0), str(r.get("title") or "")))
    return rows


def offer_count(client_id=None, ship_id=None, object_id=None, console=None):
    """How many offers can be TAKEN right now.

    Excludes ``pending`` ones: a count is a promise that there is something to act on,
    and a POSTING job that only somebody else can hand you is not that.
    """
    n = 0
    for r in offers(client_id, ship_id, object_id, console=console):
        if not r.get("pending"):
            n += 1
    return n


def offers_for_object(object_id, client_id=None, ship_id=None):
    """What this one object is offering. The hook a comms selection or a scan reads."""
    if object_id is None:
        return []
    return offers(client_id=client_id, ship_id=ship_id, object_id=to_id(object_id))


# --- core providers -----------------------------------------------------------
def _quest_provider(ctx):
    """The quest provider, bound LATE.

    quest_driver pulls in comms (and most of the package with it), and this module is
    imported early enough that doing it at import time is a circular import: comms is
    still half-built, quest_driver fails to import, and the library silently ships with
    no quest offers at all. Importing inside the call costs one dict lookup per walk and
    removes the cycle entirely.
    """
    from .quest_driver import quest_offer_provider
    return quest_offer_provider(ctx)


def _install_core_providers():
    """Register the library's own providers. Called at import AND by ``offer_clear()``."""
    _PROVIDERS["quest"] = {"fn": _quest_provider, "domain": "core"}


_install_core_providers()


# --- "here" -------------------------------------------------------------------
# The badge, the board and the digest all want "offers for the console asking right
# now". Resolving that in each of them would be three copies of the viewscreen rule
# below, and the first one to be written differently would be a bug nobody could see.
def offer_context_here():
    """``(client_id, ship_id)`` for the console currently being drawn, or ``(None, None)``.

    The ship is the console's HOME ship, not ``get_ship_of_client``: a main screen
    driving a cinematic answers with the SUBJECT of the shot, so a badge would count the
    enemy's jobs. Same rule the log panel's scope already follows.
    """
    ctx = FrameContext.context
    if ctx is None or getattr(ctx, "sbs", None) is None:
        return (None, None)
    # THE PAGE'S CLIENT, NOT THE EVENT'S. Same rule, and the same reason, as
    # `epadd._client_id` and `console_tab._tab_client_id`: a page that runs because
    # something else emitted a signal - or a button handler called by MessageHandler -
    # runs under somebody else's event while `FrameContext.page` is still correctly this
    # console. Reading the event meant a job could be granted to the wrong client, or to
    # none, and then it appeared on nobody's Quests tab.
    page = FrameContext.page
    cid = getattr(page, "client_id", None) if page is not None else None
    if cid is None:
        cid = FrameContext.client_id
    try:
        from .gui.viewscreen import viewscreen_home_ship
        ship = viewscreen_home_ship(cid)
    except Exception:
        ship = None
    return (cid, ship or None)


def offers_here(kinds=None):
    """Offers for the console currently being drawn."""
    cid, ship = offer_context_here()
    return offers(client_id=cid, ship_id=ship, kinds=kinds)


def offer_count_here():
    """How many offers this console could act on. The shape a badge wants."""
    cid, ship = offer_context_here()
    return offer_count(client_id=cid, ship_id=ship)
