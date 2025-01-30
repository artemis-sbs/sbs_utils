from ...mast.mast import IF_EXP_REGEX, DecoratorLabel, STRING_REGEX_NAMED, mast_node
import re





    
from ...fs import get_artemis_graphics_dir, get_artemis_audio_dir, get_mod_dir, get_script_dir
import os.path as path

@mast_node()
class MediaLabel(DecoratorLabel):
    rule = re.compile(r'@media/(?P<kind>\w+)/(?P<path>[\/\w-]+)[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)
    folders = {}
    is_label = True

    def __init__(self, kind, path, display_name, if_exp=None, q=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
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
                self.code = compile(if_exp, "<string>", "eval")
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
    
    def test_file(self):
        data_folder = get_mod_dir("media")
        media_folder = path.join(get_script_dir(), "media")
        if self.kind == "skybox":
            data_folder = get_artemis_graphics_dir()
            file_name = path.join(media_folder, self.kind, self.path)
            if path.isfile(file_name+".png"):
                return True
            file_name = path.join(data_folder, self.path)
            if path.isfile(file_name+".png"):
                return True
        elif self.kind == "music":
            data_folder = path.join(get_artemis_audio_dir(), "music")
            file_name = path.join(media_folder, self.kind, self.path)
            if path.isdir(file_name):
                return True
            file_name = path.join(data_folder, self.path)
            if path.isdir(file_name):
                return True
        return False
    
    def true_path(self):
        data_folder = get_mod_dir("media")
        media_folder = path.join(get_script_dir(), "media")
        if self.kind == "skybox":
            data_folder = get_artemis_graphics_dir()
            file_name = path.join(media_folder, self.kind, self.path)
            if path.isfile(file_name+".png"):
                return file_name
            file_name = path.join(data_folder, self.path)
            if path.isfile(file_name+".png"):
                return self.path
            return "sky1"
        #
        #
        #
        elif self.kind == "music":
            data_folder = path.join(get_artemis_audio_dir(), "music")
            file_name = path.join(media_folder, self.kind, self.path)
            if path.isdir(file_name):
                return file_name
            file_name = path.join(data_folder, self.path)
            if path.isdir(file_name):
                return self.path
            return "default"


    def test(self, task):
        if self.code is not None:
            if not task.eval_code(self.code):
                return False
        return self.test_file()

