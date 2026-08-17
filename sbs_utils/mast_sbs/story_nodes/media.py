from ...mast.mast_node import IF_EXP_REGEX, STRING_REGEX_NAMED, mast_node, mast_compile, EVAL_ERROR
from ...mast.core_nodes.decorator_label import DecoratorLabel
import re





    
from ...fs import get_artemis_graphics_dir, get_artemis_audio_dir, get_mod_dir, get_script_dir
from ...helpers import FrameContext
import os.path as path

def music_engine_accepts_paths():
    """Whether `set_music_folder` may be handed a PATH rather than a bare name.

    False, and it must stay false until an engine build is measured to survive it. On
    1.3.6 a path does not raise or fall back: an exe-relative one SEGFAULTS the engine
    (rc 139) and an absolute one hangs it. Measured across all four spellings with a
    working control - see `true_path` for the matrix, and
    `data/missions/music_probe/music.txt` for the log.

    A setting rather than a constant so `music_probe` can flip it on a build under test
    without rebuilding the library. Re-run all four cases before flipping it: the case
    that matters is 4, `data/audio/music/default`, because it proves the engine objects
    to the PATH and not to where the folder lives.
    """
    try:
        from ...procedural.settings import settings_get_defaults
        return bool(settings_get_defaults().get("MUSIC_ENGINE_ACCEPTS_PATHS", False))
    except Exception:
        return False


@mast_node()
class MediaLabel(DecoratorLabel):
    rule = re.compile(r'@media/(?P<kind>\w+)/(?P<path>[\/\w-]+)[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)
    folders = {}
    is_label = True

    @classmethod
    def clear(cls):
        """Drop registered @media labels (fresh mission / in-process recompile) - the
        folders dict APPENDS per label, so without this a reload doubles the media."""
        cls.folders = {}

    def __init__(self, kind, path, display_name, if_exp=None, q=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        self.label_weight = id
        path = path.lower()
        kind = kind.lower()
        name = f"media/{kind}/{path}/{id}"
        super().__init__(name, loc)
        self.path= path
        self.kind = kind
        
        
        folder = MediaLabel.folders.get(kind, [])
        folder.append(self)
        MediaLabel.folders[kind] = folder

        self.display_name= display_name
        self.code = None
        # need to negate if
        if if_exp is not None:
            if_exp = if_exp.strip()
            try:
                self.code = mast_compile(if_exp, "eval")
            except:
                raise Exception(f"Syntax error '{if_exp}'")
        
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, parent):
        return False
    
    _NO_TASK = object()

    def get_of_type(kind, task=_NO_TASK):
        """Every registered label of this kind whose condition passes and whose file is
        on disk.

        `task` defaults to the running one. It used to be REQUIRED and every caller in
        `procedural/media.py` passed None, so a label carrying an `if` expression - the
        one feature that makes the list worth filtering - crashed the schedule with
        `AttributeError: 'NoneType' has no attribute 'eval_code_checked'`. Nothing
        shipped used the form, so it never bit; a music picker is exactly where authors
        reach for it. With no task at all (a tool, a test) the condition is skipped
        rather than fatal: an unevaluatable `if` must not delete the label.

        A SENTINEL rather than a None default, because None is a meaningful argument
        here and `FrameContext.task` cannot represent its absence - with `_task` unset
        it falls back to the client page's gui_task, so a caller that passed None
        explicitly would silently get whatever task happened to be running."""
        if task is MediaLabel._NO_TASK:
            task = FrameContext.task
        files = MediaLabel.folders.get(kind.lower(), [])
        ret = []
        for file in files:
            if file.test(task):
                ret.append(file)
        return ret
    
    def _media_roots(self):
        """Where a media label may find its file: this mission's own `media/` first, then
        each media pack it declared - unpacked ONCE beside the libraries rather than
        copied into every mission.

        Skybox and music are resolved HERE, not by the engine, so a pack's skybox and
        music are shareable exactly like its graphics. Only the mission-local folder was
        searched before, which is why a pack had to be copied in to be usable."""
        try:
            from ...procedural.media_paths import media_roots
            return media_roots()
        except Exception:
            return [path.join(get_script_dir(), "media")]

    def test_file(self):
        if self.kind == "skybox":
            for root in self._media_roots():
                if path.isfile(path.join(root, self.kind, self.path) + ".png"):
                    return True
            if path.isfile(path.join(get_artemis_graphics_dir(), self.path) + ".png"):
                return True
        elif self.kind == "music":
            for root in self._media_roots():
                if path.isdir(path.join(root, self.kind, self.path)):
                    return True
            if path.isdir(path.join(get_artemis_audio_dir(), "music", self.path)):
                return True
        return False
    
    def true_path(self):
        """What the ENGINE is handed for this media label.

        THE TWO KINDS ARE NOT THE SAME, and that was measured rather than assumed
        (`data/missions/skybox_probe`, `data/missions/music_probe`, engine 1.3.6):

        * **Skybox** takes a PATH. Exe-relative, absolute, with or without `.png`, or a
          bare stock name - all four open the file. So a skybox may live in the mission
          or in a shared media pack, and is named the same way as everything else.

        * **Music takes a BARE NAME ONLY.** `set_music_folder` resolves it under
          `data/audio/music/`, and handing it a path does not merely fail - it KILLS THE
          ENGINE. Not an exception, not a silent fallback.

          Full matrix, `data/missions/music_probe`, engine 1.3.6 (one launch per case,
          because a dead engine cannot say which candidate killed it)::

              case 1  data/missions/music_probe/music/m1   SEGFAULT  (rc 139)
              case 2  an ABSOLUTE path to the same m1-shaped folder  HANG (never returned)
              case 3  default                              OK        <- the control
              case 4  data/audio/music/default              SEGFAULT  (rc 139)

          Case 3 is what makes the rest trustworthy: same engine, same mission, same
          launch, and it `returned normally` and was still healthy when the timeout killed
          it. The only variable is the path form.

          Case 4 is the one to remember. That is the exe-relative spelling of the very
          folder that works as the bare name in case 3 - so this is not about WHERE the
          folder is, and no amount of putting a mod's music in the right place helps. It
          is the presence of a path at all. Case 1 is the shape `engine_file()` produces,
          which is why `music_engine_accepts_paths()` stays False.

        That is why this used to be a live bug rather than a limitation: the music branch
        returned an ABSOLUTE path whenever it found the folder in the mission or in a
        pack, so any mission shipping its own music would freeze Cosmos the moment the
        label was scheduled. It now always returns a bare name, and says so when it had
        to ignore a folder it found.

        The pack branch is WRITTEN AND WITHHELD rather than deleted, behind
        `music_engine_accepts_paths()`. A mod's music belongs in its media pack beside
        the rest of its art, and is expected to work there once the engine stops hanging;
        keeping the resolution here means that day is a settings flip and a probe run,
        not a rewrite of a branch someone has to reconstruct from this docstring.
        """
        if self.kind == "skybox":
            from ...fs import engine_file
            for root in self._media_roots():
                file_name = path.join(root, self.kind, self.path)
                if path.isfile(file_name + ".png"):
                    return engine_file(file_name)
            if path.isfile(path.join(get_artemis_graphics_dir(), self.path) + ".png"):
                return engine_file(path.join(get_artemis_graphics_dir(), self.path))
            return "sky1"

        elif self.kind == "music":
            # data/audio/music FIRST, and by bare name - the one spelling that is known
            # to work, so a mission that installed its bank never depends on the flag.
            if path.isdir(path.join(get_artemis_audio_dir(), "music", self.path)):
                return self.path
            for root in self._media_roots():
                found = path.join(root, self.kind, self.path)
                if path.isdir(found):
                    if music_engine_accepts_paths():
                        from ...fs import engine_file
                        return engine_file(found)
                    self._warn_music_unreachable(found)
                    break
            return "default"

    def bank_dir(self):
        """The folder this music label resolves to on disk, or None.

        Where `true_path` answers "what do I hand the engine", this answers "where are
        the files" - which is a different question whenever the two disagree, i.e.
        whenever a pack's bank is found but withheld. Used to ask whether a bank has a
        particular stinger.
        """
        if self.kind != "music":
            return None
        installed = path.join(get_artemis_audio_dir(), "music", self.path)
        if path.isdir(installed):
            return installed
        for root in self._media_roots():
            found = path.join(root, self.kind, self.path)
            if path.isdir(found):
                return found
        return None

    def bank_has(self, stinger):
        """Whether this bank carries a named one-shot (`victory`, `failure`, ...).

        A bank is a contract - `start/main/victory/failure.ogg` plus `low/ medium/ high/`
        - but it is a convention, not something anything enforces, so a mod's bank may
        legitimately omit one. Asking rather than assuming is what lets the end-of-game
        sting fall back to `default` for that ONE file instead of abandoning the mod's
        music entirely.
        """
        folder = self.bank_dir()
        if folder is None:
            return False
        return path.isfile(path.join(folder, str(stinger) + ".ogg"))

    def _warn_music_unreachable(self, found):
        """Say when music was found somewhere the engine cannot be pointed at.

        Silence here would be the worst of both: the author sees their folder on disk,
        the label passes `test_file`, and the game plays the default track with no
        explanation. Warned once per label."""
        if getattr(self, "_warned_music", False):
            return
        self._warned_music = True
        try:
            from ...procedural.execution import log
            log(f"@media/music/{self.path}: found at {found}, but the engine only accepts "
                f"music by BARE NAME under data/audio/music - a path hangs it. Playing "
                f"'default' instead. Copy the folder into data/audio/music to use it.",
                "media", "warning")
        except Exception:
            pass

    def test(self, task):
        if self.code is not None and task is not None:
            # end_on_exception=False, and that is the whole point of testing a condition
            # here. The default REPORTS and then ENDS the task - which is the task that
            # merely asked for the list, so one mistyped `if` on one media label would
            # take down the console building the picker. A condition that raised is
            # logged and read as "not shown".
            value = task.eval_code_checked(self.code, end_on_exception=False)
            if value is EVAL_ERROR or not value:
                return False
        return self.test_file()

