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
        if self.kind == "skybox":
            for root in self._media_roots():
                file_name = path.join(root, self.kind, self.path)
                if path.isfile(file_name+".png"):
                    return file_name
            if path.isfile(path.join(get_artemis_graphics_dir(), self.path) + ".png"):
                return self.path
            return "sky1"
        #
        #
        #
        elif self.kind == "music":
            for root in self._media_roots():
                file_name = path.join(root, self.kind, self.path)
                if path.isdir(file_name):
                    return file_name
            if path.isdir(path.join(get_artemis_audio_dir(), "music", self.path)):
                return self.path
            return "default"


    def test(self, task):
        if self.code is not None:
            value = task.eval_code_checked(self.code)
            # A condition that RAISED is reported and read as "not shown".
            if value is EVAL_ERROR or not value:
                return False
        return self.test_file()

