"""Open Sound Control: drive a player ship from a TouchOSC tablet, and send its state back.

The listener lives INSIDE the engine. That works because nothing here ever waits: the
UDP socket is non-blocking and is drained once per update from a `TickDispatcher`
interval, so there is no thread (the engine's Python has none) and no blocking call.
Measured in the real engine 2026-09-27: the per-update poll costs ~0.06 ms, and input
arrives within one update (median 35 ms at ~15 updates a second).

    osc_listen(8000)                      # from MAST or Python, on the server

A tablet then sends, for example:

    /helm/throttle 0.5                    # a fader
    /helm/red_alert 1                     # a toggle
    /weapons/fire/Nuke 1                  # a button - the choice is IN the address
    /eng/power/beam 1.5                   # engineering units, 0..3
    /ship/2/helm/shields 1                # any address, aimed at player slot 2
    /bind 2                               # everything from this tablet -> slot 2

Buttons put their choice in the address because a TouchOSC button sends 1 when pressed
and 0 when released: a press does the action, a release does nothing.

Every value it receives is DATA. Addresses resolve against one table
(`OSC_ADDRESS_MAP`); nothing that arrives is evaluated, and an address that is not in the
table is dropped and reported once.

State goes back to every tablet heard from in the last 30 seconds, only when a value
changed: gauges on `/state/...`, and the controls' own addresses too, so a fader moved at
the real console snaps to the same place on the tablet.
"""
import math
import socket
import struct
import time

from ..helpers import FrameContext, FakeEvent
from ..tickdispatcher import TickDispatcher
from .execution import log
from .query import (to_id, to_id_list, to_object, to_blob, get_data_set_value,
                    set_weapons_selection, set_science_selection, set_comms_selection,
                    get_weapons_selection, get_science_selection, get_comms_selection)
from .roles import role
from .spawn import player_slot_id, player_slots
from .space_objects import closest_list
from .sides import side_hostile_ships, side_allied_members
from .helm import (helm_throttle, helm_stop, helm_steer_to_vec, helm_shields,
                   helm_dock_request, helm_undock, helm_is_docked, helm_set_power,
                   helm_eng_controls, helm_energy, helm_shield_fraction)
from .torpedoes import (fire_torpedo, torpedo_get_available_types_for_ship,
                        torpedo_get_count_for_ship)
from .routes import follow_route_select_science, follow_route_select_comms


# --- codec: OSC 1.0 ------------------------------------------------------------------

def _pad(n):
    return (4 - n % 4) % 4


def _osc_str(s):
    b = str(s).encode("utf-8") + b"\0"
    return b + b"\0" * _pad(len(b))


def _read_str(data, i):
    end = data.index(b"\0", i)          # ValueError on a string with no terminator
    s = data[i:end].decode("utf-8")
    n = end - i + 1
    return s, i + n + _pad(n)


def osc_encode(address, *args):
    """One OSC message as bytes. bool -> T/F, int -> i, float -> f, str -> s, None -> N."""
    tags = ","
    payload = b""
    for a in args:
        if a is True:
            tags += "T"
        elif a is False:
            tags += "F"
        elif a is None:
            tags += "N"
        elif isinstance(a, int):
            tags += "i"
            payload += struct.pack(">i", a)
        elif isinstance(a, float):
            tags += "f"
            payload += struct.pack(">f", a)
        else:
            tags += "s"
            payload += _osc_str(a)
    return _osc_str(address) + _osc_str(tags) + payload


def osc_decode(data):
    """Every message in a packet as ``[(address, [args])]``, bundles flattened.

    Raises ValueError (or struct.error / UnicodeDecodeError) on anything malformed, so
    the caller can drop the packet whole rather than act on half of it.
    """
    if data[:8] == b"#bundle\0":
        if len(data) < 16:
            raise ValueError("truncated bundle header")
        out = []
        i = 16                          # the tag, then an 8-byte time tag we ignore
        while i < len(data):
            size = struct.unpack(">i", data[i:i + 4])[0]
            i += 4
            if size <= 0 or i + size > len(data):
                raise ValueError("bad bundle element size")
            out.extend(osc_decode(data[i:i + size]))
            i += size
        return out
    address, i = _read_str(data, 0)
    if not address.startswith("/"):
        raise ValueError("not an OSC address")
    if i >= len(data):
        return [(address, [])]          # no type tag string: a bare message
    tags, i = _read_str(data, i)
    if not tags.startswith(","):
        raise ValueError("bad type tag string")
    args = []
    for t in tags[1:]:
        if t == "i":
            args.append(struct.unpack(">i", data[i:i + 4])[0])
            i += 4
        elif t == "f":
            args.append(struct.unpack(">f", data[i:i + 4])[0])
            i += 4
        elif t == "h":
            args.append(struct.unpack(">q", data[i:i + 8])[0])
            i += 8
        elif t == "d":
            args.append(struct.unpack(">d", data[i:i + 8])[0])
            i += 8
        elif t == "s":
            s, i = _read_str(data, i)
            args.append(s)
        elif t == "T":
            args.append(True)
        elif t == "F":
            args.append(False)
        elif t == "N":
            args.append(None)
        else:
            raise ValueError(f"unsupported OSC type {t!r}")
    return [(address, args)]


# --- listener state ---------------------------------------------------------------------

# Per-mission, and registered with the reset ledger: a socket left open by run 1 is a
# "port in use" on run 2 of the dev runner's reused interpreter.
_OSC = {"sock": None, "task": None, "port": None, "feedback_port": None, "allow": None,
        "rate": 5.0, "next_feedback": 0.0, "senders": {}, "reported": set(),
        "received": 0, "dropped": 0}

MAX_PACKETS_PER_TICK = 64       # a flood is served over several updates, never one
SENDER_TIMEOUT = 600.0          # seconds without a packet before feedback stops.
                                # LONG, because a panel of gauges is watched, not touched:
                                # at 30 s a tablet nobody pressed went quiet mid-game.
RECV_BUFFER = 4096


def _report_once(key, message, level="warning"):
    if key in _OSC["reported"]:
        return
    _OSC["reported"].add(key)
    log(message, "osc", level)


def osc_listen(port=8000, feedback_port=9000, host="0.0.0.0", allow=None, rate=5.0):
    """Start listening for OSC on UDP ``port``. Server only; call once.

    Args:
        port (int, optional): The UDP port tablets send to. Defaults to 8000.
        feedback_port (int | None, optional): The port state is sent back to, on each
            tablet's own address. None replies to the port the packet came from.
            Defaults to 9000, TouchOSC's usual receive port.
        host (str, optional): The interface to bind. "0.0.0.0" accepts the LAN;
            "127.0.0.1" only this machine. Defaults to "0.0.0.0".
        allow (list[str], optional): Address prefixes a sender must match, for example
            ``["192.168.1."]``. None accepts anyone who can reach the port.
        rate (float, optional): Feedback sends per second. 0 turns feedback off.
            Defaults to 5.

    Returns:
        bool: True when listening. False (with the reason logged) if the port could not
            be bound - most often another program already holds it.
    """
    osc_stop()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, int(port)))
        sock.setblocking(False)
    except OSError as e:
        log(f"OSC could not listen on {host}:{port}: {e}", "osc", "error")
        return False
    _OSC.update(sock=sock, port=int(port), feedback_port=feedback_port,
                allow=list(allow) if allow else None, rate=float(rate or 0),
                next_feedback=0.0, received=0, dropped=0)
    # delay 0 fires on EVERY dispatch_tick, and dispatch_tick runs on every engine event
    # including the paused mission_tick - so tablets work at the lobby and while paused.
    _OSC["task"] = TickDispatcher.do_interval(_osc_tick, 0)
    log(f"OSC listening on {host}:{port}, feedback to port {feedback_port}", "osc")
    return True


def osc_stop():
    """Stop listening and forget every tablet. Safe to call when not listening."""
    task = _OSC.get("task")
    if task is not None:
        try:
            task.stop()
        except Exception:
            pass
    sock = _OSC.get("sock")
    if sock is not None:
        try:
            sock.close()
        except Exception:
            pass
    _OSC.update(sock=None, task=None, port=None)
    _OSC["senders"].clear()
    _OSC["reported"].clear()


def osc_is_listening():
    """True while the OSC listener is open."""
    return _OSC["sock"] is not None


def osc_status():
    """A snapshot for a debug page: port, packets received/dropped, tablets heard from."""
    now = time.time()
    return {"listening": osc_is_listening(), "port": _OSC["port"],
            "received": _OSC["received"], "dropped": _OSC["dropped"],
            "senders": {f"{ip}:{p}": {"slot": s.get("slot"), "seen": round(now - s["seen"], 1)}
                        for (ip, p), s in _OSC["senders"].items()}}


def _osc_tick(t=None):
    # NOTHING may escape this. It runs inside the engine's event handler, and an
    # exception here is a hook-level error on EVERY update - measured 2026-09-27, one bad
    # field read in the feedback took the whole handler down (the devqueue stopped
    # answering). A tablet feature must never be able to do that to the game.
    try:
        _osc_tick_body()
    except Exception as e:
        _report_once(("tick", type(e).__name__, str(e)), f"OSC update failed: {e}", "error")


def _osc_tick_body():
    sock = _OSC["sock"]
    if sock is None:
        return
    for _ in range(MAX_PACKETS_PER_TICK):
        try:
            data, addr = sock.recvfrom(RECV_BUFFER)
        except BlockingIOError:
            break
        except OSError as e:
            # Windows reports an ICMP "port unreachable" from an earlier sendto as an
            # error on the NEXT recvfrom (WSAECONNRESET). It is about a tablet that went
            # away, not about this socket, so it is skipped rather than fatal.
            if getattr(e, "winerror", None) == 10054:
                continue
            _report_once(("recv", str(e)), f"OSC receive error: {e}", "error")
            break
        _osc_packet(data, addr)
    if _OSC["rate"] > 0:
        now = time.time()
        if now >= _OSC["next_feedback"]:
            _OSC["next_feedback"] = now + 1.0 / _OSC["rate"]
            _osc_feedback(now)


def _osc_packet(data, addr):
    allow = _OSC["allow"]
    if allow and not any(addr[0].startswith(p) for p in allow):
        _OSC["dropped"] += 1
        _report_once(("deny", addr[0]), f"OSC ignoring {addr[0]} (not in allow list)")
        return
    try:
        messages = osc_decode(data)
    except Exception as e:
        _OSC["dropped"] += 1
        _report_once(("bad", addr[0]), f"OSC dropped a malformed packet from {addr[0]}: {e}")
        return
    sender = _OSC["senders"].setdefault(addr, {"slot": None, "last": {}})
    sender["seen"] = time.time()
    for address, args in messages:
        _OSC["received"] += 1
        try:
            osc_dispatch(address, args, sender)
        except Exception as e:
            _report_once(("err", address), f"OSC {address} failed: {e}", "error")


# --- ship binding ------------------------------------------------------------------------

def _osc_ship(slot):
    """The ship a tablet drives: player slot ``slot``, else the lowest filled slot, else
    the first player ship. A mission that never assigns slots still gets its only ship."""
    if slot is not None:
        sid = player_slot_id(slot)
        if sid is not None:
            return sid
    slots = player_slots()
    if slot is None and slots:
        return slots[min(slots)]
    ids = sorted(to_id_list(role("__player__")))
    if not ids:
        return None
    if slot is not None:
        # No slot roles on this mission: count ships in id order instead, 1-based.
        return ids[int(slot) - 1] if 0 < int(slot) <= len(ids) else None
    return ids[0]


# --- the handlers ------------------------------------------------------------------------

def _num(args, default=0.0):
    for a in args:
        if isinstance(a, bool):
            return 1.0 if a else 0.0
        if isinstance(a, (int, float)):
            return float(a)
        if isinstance(a, str):
            try:
                return float(a)
            except ValueError:
                pass
    return default


def _pressed(args):
    """A button press. No argument counts as a press (a bare message is a trigger)."""
    return not args or _num(args) != 0.0


def _norm(name):
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _cycle(ship, candidates, current, mode):
    """Pick a target from ``candidates`` by distance: nearest, next farther, or previous."""
    ranked = [c.id for c in sorted(closest_list(ship, candidates), key=lambda c: c.distance)]
    if not ranked:
        return None
    if mode == "nearest" or current not in ranked:
        return ranked[0]
    i = ranked.index(current)
    return ranked[(i + (1 if mode != "prev" else -1)) % len(ranked)]


def _contacts(ship):
    """What science and comms can pick: ships and stations, not this ship itself."""
    return (role("__npc__") | role("__player__")) - {to_id(ship)}


def _h_throttle(ship, args, key):
    helm_throttle(ship, _num(args))


def _throttle_now(ship):
    try:
        return float(get_data_set_value(ship, "playerThrottle", default=0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _h_impulse(ship, args, key):
    """The game's throttle bar in impulse: 0..1. Keeps REVERSE if it is engaged, and
    drops out of warp - moving the impulse lever is asking for impulse."""
    level = max(0.0, min(1.0, _num(args)))
    helm_throttle(ship, -level if _throttle_now(ship) < 0 else level)


def _h_reverse(ship, args, key):
    """The game's REV toggle: the same power, backwards. Engaged from a standstill it
    backs off at half power, because reverse at 0 would do nothing."""
    now = _throttle_now(ship)
    level = min(1.0, abs(now)) if abs(now) > 0.001 else 0.5
    helm_throttle(ship, -level if _num(args) != 0.0 else level)


def _h_warp(ship, args, key):
    """Warp 1..4 is throttle 2..5 (the engine: 0-5, anything over 1 is warp). Warp 0
    drops back to full impulse. helm_throttle refuses warp a ship cannot sustain."""
    if not _pressed(args):
        return
    n = max(0, min(4, int(float(key))))
    helm_throttle(ship, 1.0 + n if n else 1.0)


def _h_stop(ship, args, key):
    if _pressed(args):
        helm_stop(ship)


def _h_heading(ship, args, key):
    # Compass degrees, 0 = +Z. Steering by direction is the path autoplay proved; the
    # analog playerSYaw fields exist but are untested.
    deg = _num(args) % 360.0
    rad = math.radians(deg)
    helm_steer_to_vec(ship, math.sin(rad), 0.0, math.cos(rad))


def _h_shields(ship, args, key):
    helm_shields(ship, _num(args) != 0.0)


def _h_red_alert(ship, args, key):
    blob = to_blob(ship)
    if blob is not None:
        blob.set("red_alert", 1 if _num(args) != 0.0 else 0, 0)


def _h_dock(ship, args, key):
    if not _pressed(args):
        return
    stations = side_allied_members(ship, "station")
    near = closest_list(ship, stations)
    if near:
        helm_dock_request(ship, min(near, key=lambda c: c.distance).id)


def _h_undock(ship, args, key):
    if _pressed(args):
        helm_undock(ship)


def _h_weapons_target(ship, args, key):
    if not _pressed(args):
        return
    if key == "clear":
        set_weapons_selection(ship, 0)
        return
    pick = _cycle(ship, side_hostile_ships(ship), get_weapons_selection(ship), key)
    if pick is not None:
        set_weapons_selection(ship, pick)


def _h_weapons_fire(ship, args, key):
    if not _pressed(args):
        return
    types = torpedo_get_available_types_for_ship(ship)
    kind = next((t for t in types if _norm(t) == _norm(key)), None)
    if kind is None:
        _report_once(("torp", key), f"OSC: no torpedo type {key!r} on this ship ({types})")
        return
    fire_torpedo(ship, kind)




def _follow(route, ship, pick):
    """Fire a console's selection routes, as a click on that contact would.

    Those routes start their task on the SERVER console's GUI task. This runs from a tick
    callback, not from a task, so without a server page (a bare unit test, a tool host)
    there is nowhere to start it: the selection still lands, the routes are skipped, and
    that is said once rather than raised every press.
    """
    if FrameContext.server_task is None:
        _report_once(("noroute", route.__name__),
                     f"OSC: no server task, so {route.__name__} was skipped")
        return
    route(ship, pick)


def _h_science_target(ship, args, key):
    if not _pressed(args):
        return
    pick = _cycle(ship, _contacts(ship), get_science_selection(ship), key)
    if pick is not None:
        set_science_selection(ship, pick)
        _follow(follow_route_select_science, ship, pick)


def _h_comms_target(ship, args, key):
    if not _pressed(args):
        return
    pick = _cycle(ship, _contacts(ship), get_comms_selection(ship), key)
    if pick is not None:
        set_comms_selection(ship, pick)
        _follow(follow_route_select_comms, ship, pick)


def _h_comms_button(ship, args, key):
    if not _pressed(args):
        return
    target = get_comms_selection(ship)
    if not target:
        return
    from ..consoledispatcher import ConsoleDispatcher
    # The same event a click on the engine's comms button produces (handlerhooks'
    # press_comms_button case), so the comms routes cannot tell the difference.
    ev = FakeEvent(client_id=0, tag="press_comms_button", sub_tag=str(int(key)),
                   origin_id=to_id(ship), selected_id=target, value_tag="comms_target_UID")
    ConsoleDispatcher.dispatch_message(ev, "comms_target_UID")


def _h_power(ship, args, key):
    value = max(0.0, min(3.0, _num(args)))
    for i, label, _sysi in helm_eng_controls(ship):
        if _norm(label) == _norm(key):
            to_blob(ship).set("eng_control_value", value, i)
            return
    # A looser match for tablets that say "beams" or "shields" - helm_set_power's rule.
    if not helm_set_power(ship, key.replace("_", " "), value):
        _report_once(("power", key), f"OSC: no engineering control named {key!r}")


def _h_coolant(ship, args, key):
    blob = to_blob(ship)
    if blob is None:
        return
    i = int(key)
    want = max(0, int(round(_num(args))))
    available = int(get_data_set_value(ship, "system_coolant_available", default=0) or 0)
    others = sum(int(get_data_set_value(ship, "system_coolant_used", j, default=0) or 0)
                 for j in range(4) if j != i)
    blob.set("system_coolant_used", max(0, min(want, available - others)), i)


def _h_bind(sender, args):
    slot = int(_num(args, 0))
    sender["slot"] = slot if slot > 0 else None
    sender["last"] = {}                 # a new ship: resend every value


# address -> (handler, argument kind, description). A trailing `*` segment is the key the
# handler receives: `/weapons/fire/*` + `/weapons/fire/Nuke` -> key "Nuke".
OSC_ADDRESS_MAP = {
    "/helm/throttle": (_h_throttle, "fader", "Raw throttle: -1 reverse, 0 stop, 1 full impulse, 2-5 warp 1-4."),
    "/helm/impulse": (_h_impulse, "fader", "Impulse, 0..1 - the game's throttle bar. Keeps reverse; leaves warp."),
    "/helm/reverse": (_h_reverse, "toggle", "Reverse (1) or forward (0) at the same power."),
    "/helm/warp/*": (_h_warp, "button", "Warp 1-4, or 0 to drop back to full impulse."),
    "/helm/stop": (_h_stop, "button", "All stop."),
    "/helm/heading": (_h_heading, "fader", "Steer to a compass heading, degrees."),
    "/helm/shields": (_h_shields, "toggle", "Shields up (1) or down (0)."),
    "/helm/red_alert": (_h_red_alert, "toggle", "Red alert on (1) or off (0)."),
    "/helm/dock": (_h_dock, "button", "Dock at the nearest friendly station."),
    "/helm/undock": (_h_undock, "button", "Undock."),
    "/weapons/target/*": (_h_weapons_target, "button", "Weapons target: nearest, next, prev or clear (hostiles only)."),
    "/weapons/fire/*": (_h_weapons_fire, "button", "Fire one torpedo of the named type at the weapons target."),
    "/science/target/*": (_h_science_target, "button", "Science target: nearest, next or prev."),
    "/comms/target/*": (_h_comms_target, "button", "Comms target: nearest, next or prev."),
    "/comms/button/*": (_h_comms_button, "button", "Press comms button N (0 is the first) for the comms target."),
    "/eng/power/*": (_h_power, "fader", "Power to the named system, 0..3 (1 = 100%)."),
    "/eng/coolant/*": (_h_coolant, "fader", "Coolant on system N (0..3), capped by what is available."),
}


def osc_dispatch(address, args, sender=None):
    """Act on one OSC message. Returns True when the address was recognised.

    ``sender`` is the tablet's record (its bound slot); None means the default ship.
    """
    sender = sender if sender is not None else {"slot": None, "last": {}}
    if address == "/bind":
        _h_bind(sender, args)
        return True
    slot = sender.get("slot")
    parts = address.split("/")
    # /ship/<n>/<rest>: aim this one message at another slot.
    if len(parts) > 3 and parts[1] == "ship":
        try:
            slot = int(parts[2])
        except ValueError:
            return False
        address = "/" + "/".join(parts[3:])
    entry = OSC_ADDRESS_MAP.get(address)
    key = None
    if entry is None:
        head, _, tail = address.rpartition("/")
        entry = OSC_ADDRESS_MAP.get(head + "/*")
        key = tail
    if entry is None or (key is not None and key == ""):
        _report_once(("unknown", address), f"OSC: unknown address {address}")
        return False
    ship = _osc_ship(slot)
    if ship is None:
        _report_once(("noship", slot), f"OSC: no player ship for slot {slot}")
        return True
    entry[0](ship, args, key)
    return True


# --- feedback --------------------------------------------------------------------------

def _name_of(obj_id):
    obj = to_object(obj_id) if obj_id else None
    return str(getattr(obj, "name", "") or "") if obj is not None else ""


def osc_state(ship):
    """Every value sent back to a tablet for ``ship``, as ``{address: value}``."""
    ship = to_id(ship)
    if ship is None or to_object(ship) is None:
        return {}
    def num(key, i=0):
        # The engine answers None for an unset field and some fields are strings, so a
        # value that will not read as a number is 0 here rather than an exception.
        try:
            return float(get_data_set_value(ship, key, i, default=0) or 0)
        except (TypeError, ValueError):
            return 0.0
    throttle = num("playerThrottle")
    state = {
        "/state/shields/front": round(helm_shield_fraction(ship, 0), 3),
        "/state/shields/rear": round(helm_shield_fraction(ship, 1), 3),
        "/state/energy": round(helm_energy(ship), 1),
        "/state/docked": 1 if helm_is_docked(ship) else 0,
        "/state/target/weapons": _name_of(get_weapons_selection(ship)),
        "/state/target/science": _name_of(get_science_selection(ship)),
        "/state/target/comms": _name_of(get_comms_selection(ship)),
        # The controls' own addresses too, so a fader moved at the console follows.
        "/helm/throttle": round(throttle, 3),
        "/helm/impulse": round(min(1.0, abs(throttle)), 3),
        "/helm/reverse": 1 if throttle < 0 else 0,
        "/state/warp": int(round(throttle - 1)) if throttle > 1 else 0,
        "/helm/shields": 1 if num("shields_raised_flag") else 0,
        "/helm/red_alert": 1 if num("red_alert") else 0,
    }
    for i, label, _sysi in helm_eng_controls(ship):
        state[f"/eng/power/{_norm(label)}"] = round(num("eng_control_value", i), 3)
    for i in range(4):
        state[f"/state/heat/{i}"] = round(num("system_cur_heat", i), 3)
        state[f"/eng/coolant/{i}"] = int(num("system_coolant_used", i))
    for kind in torpedo_get_available_types_for_ship(ship):
        have, _mx = torpedo_get_count_for_ship(ship, kind)
        state[f"/state/torps/{_norm(kind)}"] = int(have or 0)
    return state


def _osc_feedback(now):
    sock = _OSC["sock"]
    for addr, sender in list(_OSC["senders"].items()):
        if now - sender.get("seen", 0) > SENDER_TIMEOUT:
            del _OSC["senders"][addr]
            continue
        ship = _osc_ship(sender.get("slot"))
        if ship is None:
            continue
        dest = (addr[0], _OSC["feedback_port"] or addr[1])
        last = sender["last"]
        for address, value in osc_state(ship).items():
            if last.get(address) == value:
                continue
            last[address] = value
            try:
                sock.sendto(osc_encode(address, value), dest)
            except BlockingIOError:
                return                  # send buffer full: the rest go next time
            except OSError as e:
                _report_once(("send", addr[0]), f"OSC could not reach {addr[0]}: {e}")
                break


def osc_address_map_json():
    """The address table as plain data, for tools that build tablet layouts from it."""
    rows = []
    for address, (_fn, kind, desc) in OSC_ADDRESS_MAP.items():
        rows.append({"address": address, "kind": kind, "description": desc})
    rows.append({"address": "/bind", "kind": "fader", "description": "Bind this tablet to player slot N."})
    return rows
