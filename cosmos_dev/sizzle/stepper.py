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
