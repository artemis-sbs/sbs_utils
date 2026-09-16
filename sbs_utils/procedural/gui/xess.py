"""The xESS - the handheld a boarding party carries.

Exploration, Emergency and Shielding System, said as the letters. A communicator, a
weapon and a scanner in one, small enough for one hand, its display understood as an AR
projection in the crew member's visor. The ePADD's small sibling, and deliberately NOT a
second tablet: this is the thing you use while standing in a corridor looking at a body
on the floor.

    THE xESS ACTS. THE ePADD READS.

That rule is what keeps two devices from becoming two lists of the same things. The xESS
is a column beside a map you are watching, so everything on it is a glance and a
decision - long prose here competes with the thing you are looking at. Anything worth
reading at length belongs on the ePADD, which takes the whole screen and already has the
containers for it.

**The device owns the ACT; the mission owns the MEANING.** It aims, fires, reads a room
and opens a channel. What any of that does to the story is authored - through
`xess_fired`, through the scene's own choices, and through
`dialogue_register_outcome`.

Three modes, because the device replaces three tools. The scene's choices sit under them
always, because "what I can do here" is not a tool and should never be behind a mode.
"""
from ...helpers import FrameContext
from ..query import to_id, to_object
from .epadd import ACCENT, DIM, PANEL, PANEL_HEAD, PANEL_HI, _esc

#: On the page, so it dies with the page rather than outliving it on a module.
VIEW = "__xess_view__"

#: On the CLIENT. Which tool is showing - like everything else in boarding, per console,
#: so one crew member switching to SCAN does not switch anybody else.
KEY_MODE = "XESS_MODE"

MODE_HAIL = "hail"
MODE_SCAN = "scan"
MODE_FIRE = "fire"

#: In the order they are drawn. HAIL first because talking is the commonest thing and the
#: leftmost button is the cheapest to hit; FIRE last for the same reason in reverse.
MODES = (
    (MODE_HAIL, "HAIL"),
    (MODE_SCAN, "SCAN"),
    (MODE_FIRE, "FIRE"),
)

#: The armed colour. Loud on purpose - the whole safety argument is that nobody should
#: discover they were armed by hitting a colleague.
ARMED = "#f66"


def _client(client_id=None):
    if client_id is not None:
        return client_id
    page = FrameContext.page
    return getattr(page, "client_id", None) if page is not None else None


def xess_mode(client_id=None):
    """Which tool this console is holding."""
    from ..inventory import get_inventory_value
    cid = _client(client_id)
    if cid is None:
        return MODE_SCAN
    return get_inventory_value(cid, KEY_MODE, MODE_SCAN) or MODE_SCAN


def xess_set_mode(client_id, mode):
    """Put a different tool in their hand.

    Leaving FIRE DISARMS. Switching to the scanner with a live weapon still armed is
    exactly the accident the disarm-on-shot rule exists to prevent, one step earlier.
    """
    from ..inventory import set_inventory_value
    from ..boarding_site import boarding_disarm
    if mode != MODE_FIRE:
        boarding_disarm(client_id)
    set_inventory_value(client_id, KEY_MODE, mode)


def xess_revision(client_id=None):
    """What an `on change` watches. PER CONSOLE.

    A shared counter would mean one crew member switching tools repainted five other
    screens. Includes the armed state so the device redraws the moment the weapon is
    live - that visibility is a safety feature, not decoration.
    """
    from ..boarding_site import boarding_armed, boarding_setting
    cid = _client(client_id)
    if cid is None:
        return 0
    return (xess_mode(cid), boarding_armed(cid), boarding_setting(cid))


# --- the surface ---------------------------------------------------------------------

def gui_xess_strip(client_id=None):
    """Draw the mode strip into the caller's CURRENT FLOW. A row, nothing more.

    SPLIT FROM THE BODY ON PURPOSE, and this cost a screenshot. The first version drew the
    strip and opened the body region in one call - but opening a region ENDS the flow, so
    the reserve row emitted after it never took effect, the strip fell to the bottom of
    the section, and it was drawn straight over the "Beam up" button.

    The rule that falls out: **finish the flow, THEN open every region.** A caller draws
    this, reserves the band, and only then calls `gui_xess_body`.
    """
    return _mode_strip(_client(client_id))


def gui_xess_body(client_id=None):
    """Open the device's readout region and fill it. Call AFTER the flow is finished.

    Returns:
        dict: the held region, also stored on the page for :func:`gui_xess_tick`.
    """
    from .section import gui_region
    cid = _client(client_id)
    body = gui_region(xess_body_area())
    with body:
        _mode_body(cid)
    view = {"cid": cid, "body": body, "rev": xess_revision(cid)}
    page = FrameContext.page
    if page is not None:
        setattr(page, VIEW, view)
    return view


def xess_body_area():
    """Where the tool's own readout is drawn.

    Stated as one function so the reserving row and the region cannot drift apart - the
    same rule the crew console's choices band follows, and for the same reason: a region
    is positioned on an ABSOLUTE screen area and the flow above it knows nothing about it.
    """
    from .boarding_console import PANEL_RIGHT, ACTIONS_BAND_PX, XESS_BODY_PX, panel_left
    return ("area: %d, 100-%dpx, %d, 100-%dpx;"
            % (panel_left(), ACTIONS_BAND_PX + XESS_BODY_PX, PANEL_RIGHT, ACTIONS_BAND_PX))


def _mode_strip(client_id):
    """Three tools, one row. The one you are holding reads differently from the two you
    are not, and an armed FIRE reads differently again.

    Built the way `epadd._app_link` builds a tab, because that one is proven and this one
    was not: the click properties are ATTRIBUTES ON THE WIDGET, not keys in the style
    string. Written as style keys they are silently ignored - the widget draws, it just
    never becomes clickable, which is exactly how this shipped as "the SCAN and FIRE tabs
    do nothing". A `gui_text` rather than a `gui_button` for the same reason the PADD's
    tabs are: the engine gives a button its own bevel and renders the backticks of a
    quoted label as literal characters.
    """
    from .row import gui_row
    from .text import gui_text
    from ..boarding_site import boarding_armed
    current = xess_mode(client_id)
    armed = boarding_armed(client_id)

    gui_row("row-height: 2.4em; font:gui-2; background: %s;" % PANEL_HEAD)
    for mode, label in MODES:
        on = mode == current
        color = ACCENT if on else DIM
        if mode == MODE_FIRE and armed:
            color = ARMED
            label = "ARMED"
        click = "xess-%s" % mode
        w = gui_text("$text:`%s`;justify:center;font:gui-2;color:%s;" % (label, color))
        if w is None:
            continue
        # The hit region is the whole slot, not the width of the word.
        w.background_color = PANEL_HI if on else PANEL
        w.click_tag = click
        w.click_color = "#FFF"
        w.click_background = PANEL_HI
        _bind_mode(w, client_id, mode, click)


def _bind_mode(widget, client_id, mode, click):
    """Switch tool on click. A callback rather than `on_press=<label>`, because a label
    handler would jump this console's GUI task."""
    from .message import gui_message_callback

    def _go(event=None, sender=None, _mode=mode, _click=click):
        # FILTERED. `Layout.on_message` hands every event to every callback, so an
        # unfiltered one fires on somebody else's click - which cost the PADD a playtest
        # round and is written down in `_app_link` for exactly this reason.
        if getattr(event, "sub_tag", None) != _click:
            return
        xess_set_mode(client_id, _mode)

    gui_message_callback(widget, _go)


def _mode_body(client_id):
    """Whatever the held tool has to say. Short, always - this is a glance."""
    mode = xess_mode(client_id)
    if mode == MODE_HAIL:
        return _hail_body(client_id)
    if mode == MODE_FIRE:
        return _fire_body(client_id)
    return _scan_body(client_id)


def _hail_body(client_id):
    """Talk to the ship, or to the party.

    Nothing is invented here: a boarder already has `ultra_beam`, the ship's comms
    already lists them, and `message_send` already resolves `ship` and `boarding` as LIVE
    audiences - resolved when the inbox is READ, so a note to the party reaches whoever
    is down there at the time rather than whoever was when it was written.
    """
    from .row import gui_row
    from .button import gui_button
    from .text import gui_text
    from ..boarding import boarding_me
    who = to_object(boarding_me(client_id))
    from_name = who.name if who is not None else "Boarding party"

    for label, text, to in (
            ("Report in", "%s, reporting in." % from_name, "ship"),
            ("Need help", "%s needs assistance." % from_name, "*"),
            ("On my way", "%s, moving." % from_name, "boarding")):
        gui_row("row-height: 2.2em; font:gui-2;")
        gui_button(label, on_press=_hail,
                   data={"cid": client_id, "text": text, "to": to, "by": from_name})


def _hail(event=None, sender=None, **kwargs):
    data = getattr(sender, "data", None) or kwargs
    try:
        from ..messages import message_send
        message_send(data.get("text"), to=data.get("to"), sender=data.get("by"),
                     kind="crew")
    except Exception:
        # A mission with no inbox is not an error; the device simply has nowhere to put
        # the line, and refusing to draw the button would be worse.
        pass


def _scan_body(client_id):
    """Read the room you are standing in.

    The readout is the library's own node description rather than a second one - LM
    already renders a grid node's condition, and two descriptions of the same thing drift.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from ..boarding_site import (boarding_where, boarding_my_host, boarding_room_at,
                                 boarding_room_name, boarding_room_roles)
    at = boarding_where(client_id)
    if at is None:
        gui_row("row-height: 1fr;")
        gui_text_area("No reading. You are not standing anywhere.")
        return
    host = boarding_my_host(client_id)
    room = boarding_room_at(host, at[0], at[1], boarding_room_roles())
    lines = []
    if room is not None:
        lines.append("## %s" % boarding_room_name(room.name))
        lines.append(_condition(room))
    else:
        lines.append("## A corridor")
        lines.append("Nothing here but the way through.")
    gui_row("row-height: 1fr;")
    gui_text_area("\n".join(lines))
    # PASS 2 files this into the log the ePADD reads. The call site is here from the
    # start so the seam exists before the store does.
    _file(client_id, room)


def _condition(room):
    """One line on how a node is doing, in the words the library already uses."""
    try:
        from ..internal_damage import grid_node_state, grid_node_wear
        state = grid_node_state(room)
        wear = grid_node_wear(room)
        return "Condition %s, wear %d%%." % (state, int(round(float(wear) * 100)))
    except Exception:
        return "No condition reading."


def _file(client_id, room):
    """Scanning files the entry - there is no Record button, so the party's record fills
    in as they explore and nobody has to remember to keep it.

    A no-op until the store lands in pass 2. Deliberately called anyway: the seam is the
    thing that is hard to add later.
    """
    try:
        from ..xess_log import xess_log
    except ImportError:
        return
    if room is None:
        return
    xess_log("scan", room.name, _condition(room), by=client_id)


def _fire_body(client_id):
    """Arm, and choose what the shot is.

    Two settings, chosen BEFORE the target: a cutting beam on a person and a stun on a
    bulkhead are both things somebody might mean, so neither is inferred from what was
    hit. Arming says out loud what the next click will do, because the failure mode of
    this whole mode is shooting your own party.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from ..boarding_site import (boarding_armed, boarding_setting, boarding_disarm,
                                 SETTING_STUN, SETTING_CUT, FIRE_RANGE)
    armed = boarding_armed(client_id)
    setting = boarding_setting(client_id)

    gui_row("row-height: 2.2em; font:gui-2;")
    if armed:
        gui_text("$text:`ARMED - %s. Click the map.`;justify:center;font:gui-2;color:%s;"
                 % (setting.upper(), ARMED))
    else:
        gui_text("$text:`Safe. Range %d.`;justify:center;font:gui-2;color:%s;"
                 % (FIRE_RANGE, DIM))

    for value, label in ((SETTING_STUN, "Stun"), (SETTING_CUT, "Cut")):
        gui_row("row-height: 2.2em; font:gui-2;")
        gui_button("%s%s" % ("> " if value == setting else "", label),
                   on_press=_arm, data={"cid": client_id, "setting": value})

    gui_row("row-height: 2.2em; font:gui-2;")
    if armed:
        gui_button("Safe", on_press=_safe, data={"cid": client_id})
    else:
        gui_text("$text:` `;")


def _arm(event=None, sender=None, **kwargs):
    from ..boarding_site import boarding_arm
    data = getattr(sender, "data", None) or kwargs
    boarding_arm(data.get("cid"), data.get("setting"))


def _safe(event=None, sender=None, **kwargs):
    from ..boarding_site import boarding_disarm
    data = getattr(sender, "data", None) or kwargs
    boarding_disarm(data.get("cid"))


def gui_xess_tick():
    """Refresh the device in place. What an `on change` should CALL.

    Never a jump back to the screen label: that re-sends every widget on the console over
    the network, and a watcher would do it forever.

    Returns:
        bool: False when the screen is gone - a handler can outlive the page.
    """
    from .update import gui_rebuild
    page = FrameContext.page
    view = getattr(page, VIEW, None) if page is not None else None
    if not view:
        return False
    rev = xess_revision(view["cid"])
    if rev == view.get("rev"):
        return True
    view["rev"] = rev
    gui_rebuild(view["body"])
    with view["body"]:
        _mode_body(view["cid"])
    return True
