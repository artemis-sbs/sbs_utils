from ...mast.mast_node import IF_EXP_REGEX, STRING_REGEX_NAMED, mast_node, mast_compile, EVAL_ERROR
from ...mast.core_nodes.decorator_label import DecoratorLabel
import re





    
from ...fs import get_artemis_graphics_dir, get_artemis_audio_dir, get_mod_dir, get_script_dir
import os.path as path

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
    
    def get_of_type(kind, task):
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
          `data/audio/music/`, and handing it a path does not merely fail - it HANGS THE
          ENGINE. Not an exception, not a silent fallback: the call never returns, which
          from outside is a frozen game. Even `data/audio/music/default`, the exe-relative
          spelling of the very folder that works as the bare name `default`, hangs it.

        That is why this used to be a live bug rather than a limitation: the music branch
        returned an ABSOLUTE path whenever it found the folder in the mission or in a
        pack, so any mission shipping its own music would freeze Cosmos the moment the
        label was scheduled. It now always returns a bare name, and says so when it had
        to ignore a folder it found.
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
            # A bare name, always - see the docstring. The engine has no way to be told
            # about music anywhere but its own folder.
            if path.isdir(path.join(get_artemis_audio_dir(), "music", self.path)):
                return self.path
            for root in self._media_roots():
                if path.isdir(path.join(root, self.kind, self.path)):
                    self._warn_music_unreachable(path.join(root, self.kind, self.path))
                    break
            return "default"

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
        if self.code is not None:
            value = task.eval_code_checked(self.code)
            # A condition that RAISED is reported and read as "not shown".
            if value is EVAL_ERROR or not value:
                return False
        return self.test_file()

