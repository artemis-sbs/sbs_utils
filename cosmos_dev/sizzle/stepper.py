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
        "_shots = cutscene_amd_shots(%r)" % scene_key,
        "_i = %d" % index,
        "if _i >= len(_shots):",
        "    raise IndexError('shot %d of %d' % (_i, len(_shots)))",
        "_shot = _shots[_i]",
        "_cids = set(%r)" % (list(client_ids),),
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
