from sbs_utils.mast.core_nodes.decorator_label import DecoratorLabel
def STRING_REGEX_NAMED (name):
    ...
def get_artemis_audio_dir ():
    """Get the path to the Artemis Cosmos audio directory.
    
    Returns:
        str: The audio folder path (data directory + "\audio")."""
def get_artemis_graphics_dir ():
    """Get the path to the Artemis Cosmos graphics directory.
    
    Returns:
        str: The graphics folder path (data directory + "\graphics")."""
def get_mod_dir (mod):
    """Get the directory path for a mission module.
    
    Args:
        mod (str): The module/mission name.
    
    Returns:
        str: The full directory path for the module."""
def get_script_dir ():
    """Get the directory where the main script is located.
    
    Returns the cached script directory from sys.modules['script'] or sys.path[0].
    Paths are normalized to use backslashes on Windows.
    
    Returns:
        str: The absolute path to the script directory."""
def mast_compile (source, mode='eval', filename=None):
    """``compile()`` for MAST expressions, with the source kept for tracebacks.
    
    Compiling against the shared ``"<string>"`` filename leaves Python with no
    source for the frame, so ``traceback.extract_tb`` reports the offending line
    as ``None`` - which is exactly the useless report a MAST author sees today.
    Compiling against a unique pseudo-filename and registering the text in
    ``linecache`` makes every traceback (eval and ``~~`` exec alike) print the
    real expression, and lets eval_code quote the WHOLE expression even when the
    deepest frame is inside some library function.
    
    An ``mtime`` of ``None`` in the linecache tuple is the documented "loaded by
    a __loader__" form: ``linecache.checkcache`` skips those, so the entry is
    never invalidated out from under us."""
def mast_node (append=True):
    ...
class MediaLabel(DecoratorLabel):
    """class MediaLabel"""
    def __init__ (self, kind, path, display_name, if_exp=None, q=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _media_roots (self):
        """Where a media label may find its file: this mission's own `media/` first, then
        each media pack it declared - unpacked ONCE beside the libraries rather than
        copied into every mission.
        
        Skybox and music are resolved HERE, not by the engine, so a pack's skybox and
        music are shareable exactly like its graphics. Only the mission-local folder was
        searched before, which is why a pack had to be copied in to be usable."""
    def _remove (id):
        ...
    def _warn_music_unreachable (self, found):
        """Say when music was found somewhere the engine cannot be pointed at.
        
        Silence here would be the worst of both: the author sees their folder on disk,
        the label passes `test_file`, and the game plays the default track with no
        explanation. Warned once per label."""
    def can_fallthrough (self, parent):
        ...
    def clear ():
        """Drop registered @media labels (fresh mission / in-process recompile) - the
        folders dict APPENDS per label, so without this a reload doubles the media."""
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_of_type (kind, task):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def parse (src, pos=0):
        ...
    def remove_id (id):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def test (self, task):
        ...
    def test_file (self):
        ...
    def true_path (self):
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
        to ignore a folder it found."""
