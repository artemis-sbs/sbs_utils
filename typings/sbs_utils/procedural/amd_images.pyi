from sbs_utils.mast.mast_node import MastDataObject
def _cell_size (record, sheet):
    """The cell size in pixels: as written, else measured off the sheet with `Grid:`."""
def _is_image_section (node):
    """Whether a node's kind noun names an atlas section (`icons`, `images`, `art`, ...).
    Uses the same alias table the Inspector and the linter resolve against, so a section
    word that works in one place works in all of them."""
def _kind_of (node, data):
    """The section's kind noun - its fence's bare first line, else its key."""
def _lower (data):
    ...
def _numbers (value):
    """The numbers in a fact value: `0, 0` / `190x280` / `64`. Authors separate however
    reads best, and a fact sheet is not the place to be strict about a comma."""
def _pair (value, default=None):
    """A two-number fact. A single number means both (a square cell)."""
def _resolve_with_atlas (sheet):
    """Default resolver: ask the image atlas, which is the same lookup the game does."""
def _section_domain (kind, section):
    """Icons resolve through a domain; anything else registers a plain key."""
def _sheet_path (sheet):
    """A sheet named in AMD is a path INSIDE a media pack first - so the same file
    resolves in a clone and in a fetched copy - and only then a plain mission path."""
def image_record (section, data, key, name=None, domain=None):
    """One atlas record from a section's facts and an entry's. Section-level `Sheet` /
    `Cell` / `Grid` / `Domain` / `Color` are the entry's default, which is what lets an
    entry be a single `At:` line."""
def images_declare (records):
    """Register every record with the image atlas. Returns {key: ImageAtlas}.
    
    A record with `Rect:` uses those pixels; one with `At:` is placed on the cell grid;
    one with neither takes the whole file (a loose image, which is why `Sheet:` may be
    overridden per record)."""
def images_declare_amd (node):
    """Declare every atlas key authored under an AMD images/icons section."""
def images_declare_document (doc):
    """Declare every atlas section in a document - the one call a mission needs, whether
    the sheets live in their own file or in a section of a bigger one. Returns
    {key: ImageAtlas}."""
def images_from_core (section):
    """The same, from an `amd_core` node - the model the LINTER parses into. Two readers
    exist because the linter needs spans and the runtime does not; they share the record
    builder so a fact cannot mean one thing to the linter and another to the game."""
def images_from_section (node):
    """Atlas records from an `## [Icons]` / `## [Images]` section of an `amd_document`."""
def images_load_amd (file_path):
    """Read an AMD file relative to the mission folder and declare every atlas in it."""
def images_sections (doc):
    """Every atlas section in a document, at any depth."""
def images_validate (records, resolve=None, check_files=True):
    """Problems a mission would otherwise discover as a blank widget. Returns a list of
    (key, severity, code, message).
    
    Args:
        records: what `images_from_section` / `images_from_core` returns.
        resolve (callable, optional): `sheet -> (exists, (width, height))`. The default
            asks the image atlas, which needs the engine's mission paths; a static
            linter passes its own so it can check a file it was handed by path.
        check_files (bool): when False, only the checks that need no art - so a linter
            that cannot locate the mission root reports what it CAN know instead of
            calling every sheet missing."""
