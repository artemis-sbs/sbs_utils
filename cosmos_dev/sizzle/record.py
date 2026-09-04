"""Record one continuous take, and write the marks that say where each shot began.

ONE recording, not one per shot. OBS takes several hundred milliseconds to spin an
encoder up and nvenc drops frames at the head of every clip, so start/stop per shot
loses exactly the frames a cut lands on. Instead the take runs unbroken, the stepper
writes a mark at each shot boundary, and ffmpeg cuts at the marks afterwards - which
also means a shot that ran long is fixable in the edit instead of needing a re-shoot.

Marks are wall-clock offsets from the moment StartRecord returned. That is the only
clock both ends share: the engine has its own sim time, and OBS reports its own
duration, and neither can be read at the instant a shot is applied.
"""
import os
import json
import time


class Take:
    """One recording session: the scene it captures, and the marks written during it."""

    def __init__(self, obs, scene, source, out_dir):
        self.obs = obs
        self.scene = scene
        self.source = source
        self.out_dir = out_dir
        self.t0 = None
        self.marks = []
        self.path = None

    def start(self):
        os.makedirs(self.out_dir, exist_ok=True)
        self.obs.set_record_directory(os.path.abspath(self.out_dir))
        self.obs.set_current_scene(self.scene)
        time.sleep(1.0)                 # let game_capture hook before tape rolls
        self.obs.start_record()
        # StartRecord returns before the first frame is written; the offset that
        # matters is measured from here, so every mark is consistently late by the
        # same small amount rather than each being late by a different one.
        self.t0 = time.time()
        return self.t0

    def mark(self, index, label, shot):
        """Record where a shot began, in seconds from the start of the take."""
        self.marks.append({
            "index": index,
            "label": label,
            "t": round(time.time() - self.t0, 3),
            "framing": shot.get("framing"),
            "seconds": shot.get("seconds"),
            "subject": shot.get("subject"),
        })

    def stop(self):
        try:
            self.path = self.obs.stop_record()
        except Exception:
            self.path = None
        # Close the last mark so every shot has an end, not just a start.
        if self.marks and self.t0:
            self.marks[-1]["t_end"] = round(time.time() - self.t0, 3)
        for a, b in zip(self.marks, self.marks[1:]):
            a["t_end"] = b["t"]
        return self.path

    def write_marks(self, extra=None):
        path = os.path.join(self.out_dir, "marks.json")
        doc = {"take": self.path, "t0": self.t0, "marks": self.marks}
        if extra:
            doc.update(extra)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        return path


def abort(take, out_dir, reason, log_tail=None):
    """Stop the take and preserve it as a FAILED one, with why.

    A partial take is worth keeping - it usually contains the moment things went wrong -
    but it must never be mistaken for a good one, so it goes somewhere else entirely
    and assembly is not attempted.
    """
    aborted = os.path.join(out_dir, "aborted")
    os.makedirs(aborted, exist_ok=True)
    try:
        take.stop()
    except Exception:
        pass
    take.out_dir = aborted
    take.write_marks({"aborted": True, "reason": reason, "log_tail": log_tail})
    return aborted
