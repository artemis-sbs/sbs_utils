"""Step a shot list one shot at a time, from the host, and hold each one.

The library already resolves an AMD cutscene into playable shots and can apply a single
shot to a set of consoles. Both are ordinary public functions, so the host does not need
a mission-side helper at all - it drives them straight through the devqueue:

    cutscene_amd_shots(key)   -> the resolved shots (added for exactly this)
    shot_apply(cids, shot)    -> put the camera on one shot AND LEAVE IT THERE

That "leave it there" is the whole point. `cutscene_play` runs on a clock, and a clock
is useless to something trying to hold a frame still long enough to screenshot it.
"""
import json


def _py(lines):
    return "\n".join(lines)


def load_shots(drv, scene_key, timeout=20.0):
    """The resolved shots of a scene, as plain dicts the host can caption from.

    Object references cannot cross the queue, so the subject is reduced to its id and
    the rest is JSON. A shot the engine DROPPED (unresolvable subject) is simply not in
    the list - which is why the count is reported rather than assumed.
    """
    expr = (
        "__import__('json').dumps(["
        "{k: (v if isinstance(v, (int, float, str, bool, type(None), list)) else str(v))"
        " for k, v in dict(s, subject=getattr(s.get('subject'), 'id', s.get('subject'))).items()}"
        " for s in __import__('sbs_utils.procedural.amd_cutscene', fromlist=['x'])"
        ".cutscene_amd_shots(%r)])" % scene_key
    )
    return json.loads(drv.eval(expr, timeout=timeout) or "[]")


def apply_shot(drv, scene_key, index, client_ids, timeout=20.0):
    """Put the camera on shot `index` and hold. Returns its label."""
    code = _py([
        "from sbs_utils.procedural.amd_cutscene import cutscene_amd_shots",
        "from sbs_utils.procedural.gui.cutscene import shot_apply, shot_furniture",
        "from sbs_utils.procedural.gui.overlay import overlay_clear",
        "_shots = cutscene_amd_shots(%r)" % scene_key,
        "_i = %d" % index,
        "if _i >= len(_shots):",
        "    raise IndexError('shot %d of %d' % (_i, len(_shots)))",
        "_shot = _shots[_i]",
        "_cids = set(%r)" % (list(client_ids),),
        # Clear FIRST. shot_furniture returns early when a shot has no overlay, so it
        # never takes the previous one down - during normal playback _Playing tracks
        # the slots each shot used and clears them between shots, and the stepping
        # path has no such bookkeeping. Without this a shot that authors no overlay
        # inherits the last one's: a firefight still wearing the cold open's title.
        "overlay_clear(None, to=_cids)",
        "shot_apply(_cids, _shot)",
        "shot_furniture(_cids, _shot)",
        "_result = str(_shot.get('label') or _shot.get('key') or _i)",
    ])
    resp = drv.send(code, timeout=timeout)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error"))
    return resp.get("result")


def alive(drv, timeout=3.0):
    """Cheap liveness. A FROZEN server keeps its window on screen and OBS goes on
    recording a still frame quite happily, so the queue is the only thing that
    actually knows the difference."""
    try:
        return drv.eval("1+1", timeout=timeout) == 2
    except Exception:
        return False


def scene_report(drv, timeout=20.0):
    """What actually exists in the sim, and where - so an empty frame can be told from
    an empty SCENE. A shot that resolves still frames nothing if the subject never
    spawned, and the two look identical on a contact sheet."""
    expr = (
        "__import__('json').dumps({"
        "'npcs': len(__import__('sbs_utils.procedural.query', fromlist=['x'])"
        ".to_object_list(__import__('sbs_utils.procedural.roles', fromlist=['x']).role('__npc__'))),"
        "'objects': [ (o.name, round(o.pos.x), round(o.pos.y), round(o.pos.z)) "
        "for o in __import__('sbs_utils.procedural.query', fromlist=['x'])"
        ".to_object_list(__import__('sbs_utils.procedural.roles', fromlist=['x']).role('__npc__'))][:8]"
        "})"
    )
    try:
        return json.loads(drv.eval(expr, timeout=timeout) or "{}")
    except Exception as e:
        return {"error": str(e)}


def framing_report(drv, subject_id, timeout=20.0):
    """The distance `wide`/`medium`/`close` resolve to for one subject, and its hull
    radius - the two numbers that decide whether a framed shot shows a ship or a speck."""
    expr = (
        "__import__('json').dumps({"
        "'exclusion_radius': getattr(__import__('sbs_utils.procedural.query', fromlist=['x'])"
        ".to_object(%d).space_object(), 'exclusion_radius', None),"
        "'close': __import__('sbs_utils.procedural.gui.cutscene', fromlist=['x'])"
        ".cutscene_framing(%d, 'close'),"
        "'medium': __import__('sbs_utils.procedural.gui.cutscene', fromlist=['x'])"
        ".cutscene_framing(%d, 'medium'),"
        "'wide': __import__('sbs_utils.procedural.gui.cutscene', fromlist=['x'])"
        ".cutscene_framing(%d, 'wide')})" % (subject_id, subject_id, subject_id, subject_id)
    )
    try:
        return json.loads(drv.eval(expr, timeout=timeout) or "{}")
    except Exception as e:
        return {"error": str(e)}


# --- 2D console screens ----------------------------------------------------------------
#
# A screen take is not a camera take. There is no subject and no framing: the picture is
# a CONSOLE, so the shot is "send this client to that label and photograph its window".
# The camera path and this one meet only at the capture.

def seed_messages(drv, lines, timeout=20.0):
    """Put messages in the inbox before photographing it.

    An empty inbox is a bad shot - it is technically correct and says nothing. This is
    the 2D equivalent of staging a scene, and it is the part that is easy to forget
    until the contact sheet comes back showing an empty panel.
    """
    code = ["from sbs_utils.procedural.messages import message_send"]
    for sender, subject, text in lines:
        code.append("message_send(%r, sender=%r, subject=%r, kind='mail')"
                    % (text, sender, subject))
    resp = drv.send(_py(code), timeout=timeout)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error"))
    return len(lines)


def show_screen(drv, client_id, label, timeout=20.0):
    """Send one client to a named MAST label and leave it there.

    A MAST label is not a Python name in a devqueue exec, so it is looked up in the
    page's story table - naming it bare is a NameError and the reroute never runs.
    """
    code = _py([
        "from sbs_utils.gui import Gui",
        "from sbs_utils.procedural.gui.navigation import gui_reroute_client",
        "_c = Gui.clients.get(%d)" % client_id,
        "_p = _c.page_stack[-1] if _c and _c.page_stack else None",
        "_labels = getattr(getattr(_p, 'story', None), 'labels', None) or {}",
        "_lbl = _labels.get(%r)" % label,
        "if _lbl is None:",
        "    raise KeyError('no label %%r; %%d labels known' %% (%r, len(_labels)))" % label,
        "gui_reroute_client(%d, _lbl)" % client_id,
    ])
    resp = drv.send(code, timeout=timeout)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error"))
    return label


def current_label(drv, client_id, timeout=15.0):
    """What label a client is on - so a screen shot can be VERIFIED rather than assumed."""
    expr = (
        "(lambda c: 'no client' if c is None else "
        "(lambda p: 'no page' if p is None else "
        # active_label is the label NAME, a plain string (mastscheduler.py:173) - not
        # an object with .name. Reaching for .name first and falling back to 'unknown'
        # made every screen report WRONG LABEL while the reroute was working fine.
        "(lambda t: 'no gui_task' if t is None else "
        "str(getattr(t, 'active_label', None) or 'no active_label'))"
        "(getattr(p, 'gui_task', None)))"
        "(c.page_stack[-1] if getattr(c, 'page_stack', None) else None))"
        "(__import__('sbs_utils.gui', fromlist=['Gui']).Gui.clients.get(%d))" % client_id
    )
    try:
        return drv.eval(expr, timeout=timeout)
    except Exception as e:
        return "unknown: %s" % e
