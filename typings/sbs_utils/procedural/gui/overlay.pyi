from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.pages.widgets.layout_listbox import SubPage
def _auto_dwell (segment):
    """Seconds to hold one segment - long enough to read, short enough to move on."""
def _banner_builder (client_id, content):
    ...
def _choice_builder (client_id, content):
    ...
def _consoles_of_ship (ship_id):
    ...
def _consoles_of_ships (ships):
    ...
def _credits_builder (client_id, content):
    ...
def _dbg (line):
    ...
def _expand_audience_item (item):
    """Resolve ONE audience item to a set of console client ids."""
def _flash_builder (client_id, content):
    ...
def _hero_builder (client_id, content):
    ...
def _hud_builder (client_id, content):
    ...
def _letterbox_builder (client_id, content):
    ...
def _lower_third_builder (client_id, content):
    ...
def _lower_third_portrait_builder (client_id, content):
    ...
def _normalize_rows (rows):
    """Accept a dict or a list of (label, value) pairs; return a list of pairs."""
def _on_page (page, fn):
    """Run ``fn(page.overlays)`` in ``page``'s FrameContext so the overlay builder's
    page/task/event target that client (the gui_reroute_client template)."""
def _pages_for (to, consoles=None):
    """Resolve a ``to`` target to a list of client pages that have an overlay
    manager (see ``consoles_of`` for what ``to`` accepts)."""
def _portrait_text_frac (client_id, slot):
    """Share of the strip left for the line once the square face has taken its
    bite.
    
    Not a constant: a square is sized from the row HEIGHT, so how much of the
    strip a portrait eats depends on the client's aspect ratio. Measuring the
    line against the full strip is how it ends up drawn across the portrait -
    the engine does not clip. The slot's height is the square's ceiling, so it
    is the safe estimate; erring wide only splits the line a beat early."""
def _reply_emitter (signal_name, prom):
    """A press handler that emits ``signal_name`` and also resolves ``prom``.
    
    Both, not either: a caller can await the reply AND a route can react to it,
    which is what a dialogue driver plus a declarative AMD hook need at once.
    The emitted payload carries the label and who pressed, because with ``to=``
    several consoles a reply is meaningless without knowing whose it was.
    
    NOTE the multiplayer rule: handle this in a ``//shared/signal`` route if it
    does anything stateful (advances the scene, awards, spawns). A plain
    ``//signal`` route runs once PER CONSOLE, so five consoles would advance the
    conversation five times."""
def _schedule_dismiss (page, slot, gen, seconds):
    """Auto-clear ``page``'s ``slot`` after ``seconds`` — but only if it still holds
    generation ``gen`` (i.e. it wasn't re-shown / updated / already cleared in the
    meantime). One-shot tick; runs in the target page's FrameContext."""
def _schedule_toast_remove (page, slot, tid, seconds):
    ...
def _show_maybe_cycled (slot, kind, to, consoles, seconds, fields, field, font, cycle, dwell, loop, width_frac=None):
    """Show a single-line overlay, splitting into timed parts when it will not fit.
    
    The split is PER CLIENT, because "does it fit" depends on that screen's width."""
def _show_transient (slot, kind, to, seconds, content, consoles=None):
    """Show an overlay and, if ``seconds`` is set, auto-clear it after that long.
    The dismiss is generation-guarded per target page, so re-showing the slot before
    the timer fires supersedes it instead of clearing the newer content."""
def _slot_px_height (client_id, slot):
    """Pixel height of a slot on this client's screen - the ceiling on how wide
    a SQUARE widget inside it can be."""
def _slot_px_width (client_id, slot, pad=0.96):
    """Pixel width available to a slot's text on this client's screen."""
def _split_to_fit (client_id, slot, text, font, width_frac=1.0):
    """Segments of ``text`` that each fit the slot, or ``[text]`` when it already
    fits (or cannot be measured).
    
    ``width_frac`` is the share of the slot the text actually gets - a portrait
    lower third leaves the line only part of the strip."""
def _start_credits_roll (page, slot, title, entries, window, interval):
    """Page through ``entries`` a ``window`` at a time every ``interval`` seconds,
    then clear (a tick-driven auto-advance; smooth per-pixel scroll would need an
    engine animation channel the GUI layer doesn't expose)."""
def _start_text_cycle (page, slot, kind, fields, field, segments, dwell, loop):
    """Show ``segments`` one at a time in ``slot``, advancing on a tick.
    
    Generation-guarded: every show bumps the region's generation, so if anything
    else claims the slot (a newer banner, a clear) the cycle notices its own
    generation is stale and stops instead of fighting for the strip."""
def _toast_builder (client_id, content):
    ...
def _toast_push (ov, slot, item):
    ...
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
def gui_page_for_client (client_id):
    """Return the active GUI page for a client.
    
    Args:
        client_id (int): The client to look up.
    
    Returns:
        Page | None: The client's current page, or ``None`` if unavailable.
    
    Example:
        page = gui_page_for_client(CLIENT_ID)
        if page is not None:
            ~~ page.dirty() ~~"""
def overlay_banner (text, color='#fd0', slot='top_banner', to=None, consoles=None, seconds=None, background='#000a', cycle=True, dwell=None, loop=None):
    """Full-width top strip (alert / countdown). Auto-dismiss after ``seconds`` if set.
    Re-call it to update in place (generation-guarded) - a countdown needs no new API.
    
    ``background`` fills the strip (translucent black by default) so the text reads
    over the live view; pass ``None`` for bare text on the view.
    
    **Text too long for the strip is shown in timed parts** rather than clipped:
    it is measured against that client's screen, split into segments that each fit,
    and advanced on a tick.
    
    Args:
        cycle (bool): split-and-cycle when the text does not fit. Default True;
            pass False to let a long line spill/clip as before.
        dwell (float, optional): seconds per part. Default: paced by word count
            (about 2.6 words/second, clamped to 2.5-7s).
        loop (bool, optional): repeat the sequence. Default: loop while the banner
            is sticky (no ``seconds``), play once when it has a lifetime."""
def overlay_choice (title, buttons, to=None, consoles=None, slot='center_hero'):
    """Show a modal choice card and return an awaitable that resolves when a button
    is pressed. Await it from a story/background task (not the target console's own
    gui task); the result's ``.data`` is the chosen label.
    
        result = await overlay_choice("Fire on the ambassador?", ["Yes", "No"], to=player)
        if result.data == "Yes":
            ..."""
def overlay_clear (slot=None, to=None, consoles=None):
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets."""
def overlay_credits (entries, title=None, slot='fullscreen', to=None, consoles=None, seconds=None, roll=None, window=8):
    """Opening/closing credits: a title + a list of lines. Static by default; pass
    ``roll`` (seconds per page) to auto-advance ``window`` lines at a time, clearing
    at the end."""
def overlay_debug_log (path=None):
    """Enable overlay command-stream logging to ``path`` (default: the mission's
    overlay_debug.log). Truncates the file. Pass None-path to disable."""
def overlay_flash (color='#f006', to=None, consoles=None, slot='fullscreen', seconds=0.4):
    """Full-screen color wash (hull hit, jump). Auto-dismisses fast (default 0.4s)."""
def overlay_hero (title, subtitle=None, image=None, face=None, ship=None, icon=None, slot='center_hero', to=None, consoles=None, seconds=None, background=None, letterbox=False, bar=4):
    """Show a big centered hero / chapter card with an optional visual above the
    title (first set wins): ``face`` (a face string), ``ship`` (a ship-type key),
    ``icon`` (an icon index), or ``image`` (an image key). Auto-dismiss after
    ``seconds`` if set.
    
    Args:
        background (str, optional): a colour laid under the card's rows - a scrim,
            so the text stays legible over a bright 3D view. Usually translucent
            (``"#000a"``).
        letterbox (bool | str): also drop cinematic bars on the full-screen slot,
            so one call gives a framed title card. Pass a string to use it as the
            line between the bars. Lifts together with the card when ``seconds``
            is set.
        bar (int): letterbox bar height in em."""
def overlay_hud (rows=None, controls=None, title=None, to=None, consoles=None, slot='hud'):
    """Show a sticky HUD (label/value rows + optional control buttons) over the
    live view. Stays until cleared. Update values with ``overlay_hud_update``.
    
    Args:
        rows: a dict or list of (label, value) pairs.
        controls: list of ``{"label":.., "action": <MAST label | callable>,
            "data":..}`` — rendered as persistent sub-task buttons."""
def overlay_hud_update (rows=None, title=None, to=None, consoles=None, slot='hud'):
    """Cheaply update a live HUD's rows (and/or title). Re-fills the slot region
    out-of-band — no page repaint. Watchers call this only when a displayed value
    actually changes."""
def overlay_kind (kind, to=None, consoles=None, slot=None, seconds=None, **fields):
    """Low-level front door: show any registered ``kind`` with its default slot.
    
    The escape hatch for callers that pick the kind at runtime (the quest driver's
    inline overlay directives, AMD records). Prefer the named wrappers when the
    kind is known at author time."""
def overlay_letterbox (line=None, bar=4, to=None, consoles=None, slot='fullscreen', seconds=None):
    """Cinematic letterbox: black bars top+bottom (``bar`` em each) with an optional
    centered line. Sticky by default; pass ``seconds`` to auto-lift."""
def overlay_lower_third (name, line, slot='lower_third', to=None, consoles=None, seconds=None, cycle=True, dwell=None, loop=None):
    """Bottom name-plate + subtitle line (someone speaking over the live view).
    
    A line too long for the plate is shown in **timed parts** rather than clipped -
    which is what subtitles want anyway: the speaker's line arrives in readable
    chunks while their audio plays. See ``overlay_banner`` for ``cycle`` / ``dwell``
    / ``loop``; a lower third defaults to playing through once (``loop=False``)
    because a repeating subtitle reads as a stutter."""
def overlay_lower_third_portrait (name, line, face=None, ship=None, icon=None, image=None, align='left', buttons=None, on_reply=None, slot=None, to=None, consoles=None, seconds=None, color='#8cf', background='#000a', cycle=True, dwell=None, loop=None):
    """Lower third carrying ONE square visual, on the left or the right of the line.
    
    Same strip as ``overlay_lower_third``, plus a portrait. **A conversation is
    this called repeatedly with ``align`` alternating** - the visual moving side
    to side is what reads as a back-and-forth, and only the speaker is on screen.
    
    The visual is always laid out **square** (an image keeps its aspect ratio
    inside that square box), which is what makes the four sources interchangeable:
    the strip, the gutter and the space left for the line do not move when you
    swap a face for a ship.
    
    Args:
        name (str): the speaker's name plate.
        line (str): what they say. Too long for the remaining width and it is
            played in **timed parts** (measured against the strip MINUS the
            square), like ``overlay_lower_third``.
        face (str, optional): a face string - ``get_face(id)`` or a lifeform face.
        ship (str, optional): a ship-type key (e.g. ``"tsn_battle_cruiser"``) -
            a live 3D render.
        icon (str, optional): an icon property string or key.
        image (str, optional): an image key - letterboxed inside the square.
        align (str): ``"left"`` (default) or ``"right"`` - which side the visual
            sits on. Named ``align`` and not ``side`` because a *side* in Cosmos
            is a faction; this is layout only.
        color (str): the name-plate color.
        background (str): fill behind the strip so it reads over the live view;
            pass ``None`` for bare content.
    
    The four are **first set wins**, in ``overlay_hero``'s order (face, ship,
    icon, image). With none set the column is still reserved, so a run of beats
    does not jump sideways when one speaker has no visual.
    
    **Replies are optional.** Pass ``buttons`` and the strip grows a row of them
    below the line, pushed toward the speaker's side, in a taller slot. It then
    returns an awaitable instead of the cycled flag::
    
        reply = await overlay_lower_third_portrait(
            "Harkin", "Do we fire?", face=f, buttons=["Fire", "Hold"], to=player)
        if reply.data == "Fire":
            ...
    
    Pass ``seconds`` and it is a TIMEOUT, not just a dismiss: the card clears and
    the reply resolves with ``data is None``, so an unanswered choice never
    deadlocks the task waiting on it. Without ``seconds`` it waits indefinitely,
    which is right for a beat the story cannot proceed past::
    
        reply = await overlay_lower_third_portrait(..., buttons=[...], seconds=25)
        answer = reply.data or "Hold"      # nobody answered -> the default
    
    From MAST, hold it in a variable if you like - `p = f()` then `r = await p`
    compiles. The one form that does not is a BARE `await p` with nothing
    assigned; assign the result, or await the call.
    
    ``reply.data`` is the label pressed and ``reply.client_id`` is who pressed it,
    which matters as soon as ``to`` covers more than one console: the FIRST press
    wins and the rest are ignored, so the answer is meaningless without knowing
    whose it was.
    
    ``on_reply`` names a signal emitted on the press as well, carrying
    ``{"reply": label, "client_id": id}`` - for a caller with nobody awaiting (a
    declarative AMD hook, a fire-and-forget beat). Handle it in a
    ``//shared/signal`` route if it changes anything: a plain ``//signal`` route
    runs once PER CONSOLE, so five consoles would advance the scene five times.
    
    A **label** handler is deliberately not offered. ``gui_button`` supports one,
    but it is dispatched as a jump on the task that BUILT the widget - which for
    an overlay is the client's own GUI task, so a reply would navigate whatever
    console the player happens to be sitting at. A signal route reaches any label
    without that.
    
    See ``overlay_banner`` for ``cycle`` / ``dwell`` / ``loop``."""
def overlay_register (kind, builder):
    """Register a content builder for an overlay ``kind``.
    
    Args:
        kind (str): the ``kind`` value callers pass to ``overlay_show``.
        builder (callable): ``builder(client_id, content)`` — content is the dict
            passed to ``overlay_show`` (with ``kind`` included). Build widgets with
            the normal ``gui_*`` functions."""
def overlay_register_label (kind, label):
    """Register a MAST **label** as the builder for ``kind`` — the MAST-native way to
    author a custom overlay card without a Python builder.
    
    The label builds the card with the usual ``gui_*`` verbs and ends (``->END``);
    the content fields passed to ``overlay_show`` arrive as task variables. It is
    re-run on every repaint, so keep it **build-only** (no ``await``, no state
    changes). Reference the label by name from top-level MAST::
    
        === my_hero_card
            gui_row("row-height: content;")
            gui_text(f"$text:`{title}`;justify:center;font:gui-6")
            ->END
    
        overlay_register_label("my_hero", my_hero_card)
        # then anywhere: overlay_show("center_hero", "my_hero", title="CHAPTER TWO")"""
def overlay_show (slot, kind, to=None, consoles=None, **content):
    """Show an overlay in ``slot`` using content builder ``kind``.
    
    Args:
        slot (str): a slot name (see ``OVERLAY_SLOTS``); unknown names use a
            centered default rect.
        kind (str): a registered builder (see ``overlay_register``).
        to: the audience — ``None`` = the current console; a client id; a **ship**
            (its consoles); a **side** key/agent (that side's consoles); or a set /
            role query mixing them. See ``consoles_of``.
        consoles (str, optional): narrow the audience to consoles with these roles,
            e.g. ``"mainscreen"``.
        **content: fields passed through to the builder."""
def overlay_signal_clear (to=None, slot=None):
    """Signal-route forwarder for clear."""
def overlay_signal_show (to, slot, kind, fields=None):
    """Signal-route forwarder: overlay_show with content supplied as a dict."""
def overlay_slot_define (slot, rect, draw_layer=28000, input='passthrough'):
    """Define or override a slot's default rect / draw_layer / input mode."""
def overlay_toast (text, icon=None, seconds=3, to=None, consoles=None, slot='corner_toast'):
    """Small transient corner notification. Toasts STACK — several coexist, each
    auto-clearing after its own ``seconds`` (default 3), capped at TOAST_MAX."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
class ButtonResultLike(object):
    """Mirrors ButtonResult (.data / .client_id) for the signal+promise path."""
    def __init__ (self, layout_item, client_id):
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def data (self):
        ...
class OverlayManager(object):
    """Owns a page's overlay slots; persists across page rebuilds."""
    def __init__ (self, page):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _event (self):
        ...
    def _region (self, slot):
        ...
    def _request_repaint (self):
        """Force a full page repaint so present_all can ESTABLISH the sub-region
        (establishment is gated on the root clear("")). Used only the first time a
        slot is shown; subsequent updates go out-of-band."""
    def clear (self, slot=None):
        ...
    def patch (self, slot, fields):
        """Merge ``fields`` into a live slot's content and redraw it — the cheap
        update path for a sticky HUD (out-of-band if established, else a repaint).
        No-op if the slot was never shown."""
    def present_all (self, event):
        """Called inside the page's repaint (after root clear("")), so this is
        where sub-regions get ESTABLISHED. Draw every slot that has content in
        draw_layer order (low → high so higher slots emit last). Empty slots are
        dropped by the root clear and marked un-established so a later show
        re-establishes them via a repaint."""
    def show (self, slot, kind, content):
        ...
class OverlayRegion(object):
    """One slot: an absolute sub-region rebuilt from ``content`` on present.
    
    Modeled on ``TabbedPanel`` — brackets its own sub-region and runs a builder
    through a ``SubPage`` so procedural ``gui_*`` calls land inside it."""
    def __init__ (self, slot, spec):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _build_content (self, event):
        ...
    def _fill (self, event):
        """Draw the slot's content, or an invisible placeholder when empty.
        
        The engine only swaps the back buffer forward on `complete` when it holds
        SOMETHING; an empty back buffer isn't swapped (stale content stays). So an
        empty slot still emits one placeholder (a space renders nothing)."""
    def establish (self, event):
        """Full-repaint path: (re)register the sub-region under root, then fill it.
        Only valid while the page's root region is being rebuilt."""
    @property
    def is_empty (self):
        ...
    def update (self, event):
        """Out-of-band path: the region is already established, so just
        clear -> fill -> complete (NO sub_region). No page repaint."""
