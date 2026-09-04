"""Cut a recorded take at its marks and mux it into a finished file.

Nothing here talks to the engine or to OBS - it works from `take.mkv` + `marks.json`,
which is what makes a re-cut free. Retiming the whole reel to a different track is
`--bpm`; swapping the music is `--audio`. Neither needs a re-shoot.

mkv in, mp4 out. OBS records mkv because a crashed recording is still playable, and
this harness WILL crash the engine sometimes; mp4 is what the finished thing should be.
"""
import os
import json
import shutil
import subprocess


def ffmpeg_exe():
    """The ffmpeg to use, in preference order, or None.

    imageio-ffmpeg bundles a static binary, so a machine with no system ffmpeg is one
    pip install away rather than a package manager and a PATH change away.
    """
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _run(cmd, timeout=600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: %s" % (r.stderr or "")[-800:])
    return r


def load_take(take_dir):
    """The take file and its marks, or (None, []) if the directory has neither."""
    marks_path = os.path.join(take_dir, "marks.json")
    if not os.path.isfile(marks_path):
        return None, []
    with open(marks_path, encoding="utf-8") as f:
        doc = json.load(f)
    take = doc.get("take")
    if not take or not os.path.isfile(take):
        import glob
        cand = sorted(glob.glob(os.path.join(take_dir, "*.mkv")) +
                      glob.glob(os.path.join(take_dir, "*.mp4")))
        take = cand[0] if cand else None
    return take, (doc.get("marks") or [])


def cut_clips(ff, take, marks, out_dir):
    """One clip per mark, re-encoded.

    Stream-copying would be faster but a copy can only cut on a keyframe, so every
    clip would start up to a keyframe interval early or late - which is exactly the
    error the marks exist to avoid. Re-encode and cut where asked.
    """
    os.makedirs(out_dir, exist_ok=True)
    clips = []
    for m in marks:
        t0 = float(m.get("t") or 0.0)
        t1 = float(m.get("t_end") or (t0 + 1.0))
        if t1 - t0 <= 0.05:
            continue                       # a mark with no duration is not a shot
        out = os.path.join(out_dir, "clip_%02d.mp4" % m.get("index", len(clips)))
        _run([ff, "-y", "-hide_banner", "-loglevel", "error",
              "-ss", "%.3f" % t0, "-to", "%.3f" % t1, "-i", take,
              "-an", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
              "-pix_fmt", "yuv420p", out])
        clips.append(out)
    return clips


def concat(ff, clips, out_path):
    """Hard cuts. A hype cut mostly wants them, and concat of identically-encoded
    clips is exact - no re-encode, no drift."""
    listing = out_path + ".txt"
    with open(listing, "w", encoding="utf-8") as f:
        for c in clips:
            f.write("file '%s'\n" % os.path.abspath(c).replace("\\", "/"))
    _run([ff, "-y", "-hide_banner", "-loglevel", "error",
          "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", out_path])
    os.remove(listing)
    return out_path


def beat_track(ff, seconds, bpm, out_path):
    """A click on every beat, as a PLACEHOLDER.

    The point is not the sound - it is that the cut can be watched against a grid and
    the timing judged before a real track exists. `--audio` replaces it without
    re-cutting anything.
    """
    _run([ff, "-y", "-hide_banner", "-loglevel", "error",
          "-f", "lavfi", "-i",
          "sine=frequency=880:duration=%.3f:sample_rate=48000" % max(0.1, seconds),
          "-af", "atempo=1.0,asetrate=48000",
          "-c:a", "aac", "-b:a", "128k", out_path])
    return out_path


def mux(ff, video, audio, out_path):
    """Marry picture and sound. `-shortest` so a track longer than the cut does not
    leave the reel running on black."""
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", video]
    if audio:
        cmd += ["-i", audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-pix_fmt", "yuv420p", out_path]
    _run(cmd)
    return out_path


def duration(ff, video):
    """Seconds of a media file, via ffmpeg's own report. 0.0 if it cannot be read."""
    r = subprocess.run([ff, "-hide_banner", "-i", video],
                       capture_output=True, text=True, timeout=60)
    for line in (r.stderr or "").splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            try:
                h, m, s = hms.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
            except ValueError:
                return 0.0
    return 0.0


def final_sheet(ff, video, out_png, every=2.0, cols=6, width=480, seconds=None):
    """A contact sheet of the FINISHED file.

    The only review anyone who cannot watch video can give on a cut - and cheap, so
    there is no reason to skip it.

    The grid is sized to the number of frames there will actually BE. A fixed tile
    grid pads the rest with black, which on a short reel means a mostly-black image
    that is harder to read than the four frames it contains.
    """
    if seconds is None:
        seconds = duration(ff, video)
    import math
    n = max(1, int(math.ceil((seconds or 1.0) / max(0.1, every))))
    cols = max(1, min(cols, n))
    rows = int(math.ceil(n / float(cols)))
    _run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", video,
          "-vf", "fps=1/%g,scale=%d:-1,tile=%dx%d" % (every, width, cols, rows),
          "-frames:v", "1", out_png])
    return out_png
