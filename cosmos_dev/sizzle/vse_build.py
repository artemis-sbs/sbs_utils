"""Build the reel as a Blender Video Sequence Editor timeline. Runs INSIDE Blender.

    blender --background --factory-startup --python vse_build.py -- plan.json

Never imported by the host - `bpy` exists only in Blender. The host side
(`sizzle/blend.py`) writes the plan and launches this.

The point is the .blend, not the render: every take is a movie strip trimmed at its
marks rather than a pre-cut clip, so a cut that lands a few frames wrong is fixed by
dragging a strip handle in Blender, not by re-running anything. The layout:

    channel 1/2  the shots, alternating when crossfades overlap them
    channel 3    crossfade effects
    channel 5    optional title card
    channel 6    a caption per shot, MUTED - unmute to see which shot is which
    channel 8    music
    markers      one per shot, named after it

Plan (JSON):
    {"blend": ".../sizzle.blend", "render": ".../sizzle.mp4" | null,
     "stills": ".../stills" | null, "size": [w, h] | null, "fps": null,
     "xfade": 0, "title": null, "title_seconds": 2.5, "audio": null,
     "shots": [{"take": ".../x.mkv", "t": 0.8, "t_end": 2.9,
                "label": "Contact, wide", "group": "fight"}, ...]}
"""
import os
import sys
import json

import bpy


# Strip colour tags cycle per take, so where one take hands over to the next is
# visible on the timeline at a glance.
TAKE_COLORS = ["COLOR_01", "COLOR_04", "COLOR_05", "COLOR_03", "COLOR_06",
               "COLOR_02", "COLOR_07", "COLOR_08"]


def _strips(sed):
    """4.4 renamed `sequences` to `strips`; accept either."""
    return sed.strips if hasattr(sed, "strips") else sed.sequences


def _crossfade(strips, name, channel, start, end, a, b):
    """4.4 renamed new_effect's seq1/seq2 to input1/input2."""
    try:
        return strips.new_effect(name=name, type="GAMMA_CROSS", channel=channel,
                                 frame_start=start, frame_end=end, input1=a, input2=b)
    except TypeError:
        return strips.new_effect(name=name, type="GAMMA_CROSS", channel=channel,
                                 frame_start=start, frame_end=end, seq1=a, seq2=b)


def _align(text, x, y=None):
    """Text placement. 4.5 split align_x into anchor_x (where the box hangs off
    `location`) and alignment_x (how lines justify inside it)."""
    if hasattr(text, "anchor_x"):
        text.anchor_x = x
        text.alignment_x = x
        if y:
            text.anchor_y = y
    else:
        text.align_x = x
        if y:
            text.align_y = y


def _movie_info(path):
    """A movie's real frame rate and pixel size, read by loading it as a clip.

    The size is the RECORDING's, not the engine window's: OBS scales on output, so a
    2560x1440 window is routinely a 1920x1080 file.
    """
    clip = bpy.data.movieclips.load(path)
    try:
        return (float(clip.fps) or 30.0), (int(clip.size[0]), int(clip.size[1]))
    finally:
        bpy.data.movieclips.remove(clip)


def build(plan):
    scene = bpy.context.scene
    scene.name = "Sizzle"
    sed = scene.sequence_editor_create()
    strips = _strips(sed)

    shots = [s for s in plan["shots"] if float(s["t_end"]) - float(s["t"]) > 0.05]
    if not shots:
        raise SystemExit("no shots with a duration")

    # The timeline runs at the source's rate. A movie strip advances one source frame
    # per scene frame, so a scene at 30 fps over a 60 fps take plays it at half speed.
    src_fps, src_size = _movie_info(shots[0]["take"])
    fps = plan.get("fps") or round(src_fps)
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    # Before any strip exists: FIT is computed against the frame size at creation.
    size = plan.get("size") or src_size
    scene.render.resolution_x, scene.render.resolution_y = int(size[0]), int(size[1])
    scene.render.resolution_percentage = 100

    xfade = max(0, int(plan.get("xfade") or 0))
    cursor = 1
    prev = None
    colors = {}
    for i, s in enumerate(shots):
        take = s["take"]
        in_f = round(float(s["t"]) * fps)
        dur = max(1, round((float(s["t_end"]) - float(s["t"])) * fps))
        start = cursor - (xfade if prev is not None and xfade else 0)
        channel = 1 if (i % 2 == 0 or not xfade) else 2

        # A strip made from Python defaults to ORIGINAL size; one dropped in by hand is
        # scaled to fit. Fit is baked into the transform at creation, so ask for it here
        # - takes of any size, or a --width/--height output, then fill the frame.
        m = strips.new_movie(name="%02d %s" % (i, s.get("label") or "shot"),
                             filepath=take, channel=channel, frame_start=start - in_f,
                             fit_method="FIT")
        m.frame_final_start = start
        m.frame_final_end = start + dur
        grp = s.get("group") or os.path.basename(os.path.dirname(take))
        colors.setdefault(grp, TAKE_COLORS[len(colors) % len(TAKE_COLORS)])
        m.color_tag = colors[grp]

        if prev is not None and xfade:
            _crossfade(strips, "x%02d" % i, 3, start, start + xfade, prev, m)

        cap = strips.new_effect(name="cap %02d" % i, type="TEXT", channel=6,
                                frame_start=start, frame_end=start + dur)
        cap.text = "%02d  %s" % (i, s.get("label") or "")
        cap.font_size = 36
        cap.location = (0.03, 0.06)
        _align(cap, "LEFT")
        cap.use_box = True
        cap.mute = True

        scene.timeline_markers.new(s.get("label") or "shot %d" % i, frame=start)
        s["_mid"] = start + dur // 2
        cursor = start + dur
        prev = m

    end = cursor - 1
    scene.frame_start = 1
    scene.frame_end = end

    if plan.get("title"):
        n = max(1, round(float(plan.get("title_seconds") or 2.5) * fps))
        t = strips.new_effect(name="title", type="TEXT", channel=5,
                              frame_start=1, frame_end=1 + n)
        t.text = plan["title"]
        t.font_size = 110
        t.location = (0.5, 0.5)
        _align(t, "CENTER", "CENTER")
        t.use_shadow = True
        # Fade it out over its last half second.
        fade = max(1, round(0.5 * fps))
        t.blend_alpha = 1.0
        t.keyframe_insert("blend_alpha", frame=1 + n - fade)
        t.blend_alpha = 0.0
        t.keyframe_insert("blend_alpha", frame=1 + n)

    if plan.get("audio"):
        a = strips.new_sound(name="music", filepath=plan["audio"], channel=8,
                             frame_start=1)
        if a.frame_final_end > end + 1:
            a.frame_final_end = end + 1
        # Fade out over the last second so the cut does not end mid-note.
        fade = max(1, round(1.0 * fps))
        a.volume = 1.0
        a.keyframe_insert("volume", frame=end + 1 - fade)
        a.volume = 0.0
        a.keyframe_insert("volume", frame=end + 1)

    r = scene.render
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format = "MPEG4"
    r.ffmpeg.codec = "H264"
    r.ffmpeg.constant_rate_factor = "HIGH"
    r.ffmpeg.ffmpeg_preset = "GOOD"
    r.ffmpeg.audio_codec = "AAC" if plan.get("audio") else "NONE"
    r.ffmpeg.audio_bitrate = 192
    r.use_sequencer = True
    r.use_compositing = False
    return shots, end, fps


def write_stills(plan, shots, fps):
    """One PNG per shot, taken mid-shot from the EDIT - so the sheet shows what the
    timeline really holds, trims and fades included."""
    out = plan.get("stills")
    if not out:
        return
    os.makedirs(out, exist_ok=True)
    scene = bpy.context.scene
    r = scene.render
    keep = (r.image_settings.file_format, r.resolution_percentage)
    r.image_settings.file_format = "PNG"
    r.resolution_percentage = 50
    for i, s in enumerate(shots):
        scene.frame_set(s["_mid"])
        r.filepath = os.path.join(out, "shot_%02d.png" % i)
        bpy.ops.render.render(write_still=True)
    r.image_settings.file_format = "FFMPEG"
    r.resolution_percentage = keep[1]
    # Restore the video settings the format switch reset.
    r.ffmpeg.format = "MPEG4"
    r.ffmpeg.codec = "H264"
    r.ffmpeg.constant_rate_factor = "HIGH"
    r.ffmpeg.audio_codec = "AAC" if plan.get("audio") else "NONE"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: blender -b -P vse_build.py -- plan.json")
    with open(argv[0], encoding="utf-8") as f:
        plan = json.load(f)

    shots, end, fps = build(plan)
    write_stills(plan, shots, fps)

    scene = bpy.context.scene
    if plan.get("render"):
        scene.render.filepath = plan["render"]
    blend = plan["blend"]
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    # Relative paths, so the reel folder can be moved or copied as one unit.
    bpy.ops.file.make_paths_relative()
    if plan.get("render"):
        scene.render.filepath = "//" + os.path.basename(plan["render"])
    bpy.ops.wm.save_mainfile()
    print("SIZZLE blend %s  (%d shots, %d frames @ %g fps)" % (blend, len(shots), end, fps))

    if plan.get("render"):
        bpy.ops.render.render(animation=True)
        print("SIZZLE render %s" % plan["render"])


main()
