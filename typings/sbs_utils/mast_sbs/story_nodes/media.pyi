from sbs_utils.mast.core_nodes.decorator_label import DecoratorLabel
from sbs_utils.helpers import FrameContext
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
def music_engine_accepts_paths ():
    """Whether `set_music_folder` may be handed a PATH rather than a bare name.
    
    False, and it must stay false until an engine build is measured to survive it. On
    1.3.6 a path does not raise or fall back: an exe-relative one SEGFAULTS the engine
    (rc 139) and an absolute one hangs it. Measured across all four spellings with a
    working control - see `true_path` for the matrix, and
    `data/missions/music_probe/music.txt` for the log.
    
    A setting rather than a constant so `music_probe` can flip it on a build under test
    without rebuilding the library. Re-run all four cases before flipping it: the case
    that matters is 4, `data/audio/music/default`, because it proves the engine objects
    to the PATH and not to where the folder lives."""
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
    def bank_dir (self):
        """The folder this music label resolves to on disk, or None.
        
        Where `true_path` answers "what do I hand the engine", this answers "where are
        the files" - which is a different question whenever the two disagree, i.e.
        whenever a pack's bank is found but withheld. Used to ask whether a bank has a
        particular stinger."""
    def bank_has (self, stinger):
        """Whether this bank carries a named one-shot (`victory`, `failure`, ...).
        
        A bank is a contract - `start/main/victory/failure.ogg` plus `low/ medium/ high/`
        - but it is a convention, not something anything enforces, so a mod's bank may
        legitimately omit one. Asking rather than assuming is what lets the end-of-game
        sting fall back to `default` for that ONE file instead of abandoning the mod's
        music entirely."""
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
    def get_of_type (kind, task=<object object at 0x0000015606F410B0>):
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
        not a rewrite of a branch someone has to reconstruct from this docstring."""
