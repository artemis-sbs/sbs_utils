"""Declarative IMAGE ATLASES from AMD - author a sheet's cells as data instead of a block
of `gui_image_add_atlas` calls with hand-computed pixel arithmetic.

    ## [Icons](icons)
    ---
    icons
    Sheet: icons/quest-sheet
    Cell: 64
    ---
    The quest log's glyphs. White silhouettes - color is applied per use.

    ### [Job](wanted)
    ---
    At: 0, 0
    ---

    ### [Beat](talks)
    ---
    At: 1, 0
    Color: #888
    ---

The SECTION fence carries what every cell shares - the sheet, the cell size, the domain -
and each entry says only where it is. That is the whole point: an author moving a glyph
edits one `At:` line, and nobody recomputes four pixel numbers.

TWO KINDS, ONE FORMAT. A section whose kind noun is `icons` registers into the ICON
DOMAIN, so its keys are the LOOKS that `gui_icon_name` resolves - a mission re-skins the
quest log by naming `wanted` here and nothing else changes. Any other section registers
ordinary atlas keys, which is what a card deck or a set of console backdrops wants:

    ## [Cards](cards)
    ---
    images
    Sheet: casino/terran_deck
    Cell: 190, 280
    Domain: casino
    ---

    ### [Back](card_back)
    ---
    At: 0, 0
    ---

`Sheet:` goes through `media_shared`, so a shared pack resolves the same in a clone and in
a fetched copy. A record may override the sheet (one loose file among cells), give
explicit pixels with `Rect:`, or give neither and take the whole file.
"""
from sbs_utils.mast.mast_node import MastDataObject


ICON_KINDS = ("icon", "icons")


def _numbers(value):
    """The numbers in a fact value: `0, 0` / `190x280` / `64`. Authors separate however
    reads best, and a fact sheet is not the place to be strict about a comma."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        raw = value
    else:
        raw = str(value).replace("x", ",").replace(";", ",").split(",")
    out = []
    for part in raw:
        part = str(part).strip()
        if part:
            try:
                out.append(float(part) if "." in part else int(part))
            except ValueError:
                return []
    return out


def _pair(value, default=None):
    """A two-number fact. A single number means both (a square cell)."""
    nums = _numbers(value)
    if not nums:
        return default
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (nums[0], nums[1])


def _lower(data):
    return {str(k).lower(): v for k, v in (data or {}).items()}


def _kind_of(node, data):
    """The section's kind noun - its fence's bare first line, else its key."""
    kind = data.get("__kind__") or data.get("kind")
    if not kind:
        kind = node.get("key") if hasattr(node, "get") else None
    return str(kind or "").strip().lower()


def image_record(section, data, key, name=None, domain=None):
    """One atlas record from a section's facts and an entry's. Section-level `Sheet` /
    `Cell` / `Grid` / `Domain` / `Color` are the entry's default, which is what lets an
    entry be a single `At:` line."""
    section = _lower(section)
    data = _lower(data)
    return MastDataObject({
        "key": key,
        "name": data.get("name") or name,
        "sheet": data.get("sheet") or data.get("file") or section.get("sheet")
                 or section.get("file"),
        "at": _pair(data.get("at")),
        "rect": _numbers(data.get("rect")),
        "cell": _pair(data.get("cell"), _pair(section.get("cell"))),
        "grid": _pair(data.get("grid"), _pair(section.get("grid"))),
        "color": data.get("color") or section.get("color"),
        "domain": data.get("domain") or domain,
    })


def _section_domain(kind, section):
    """Icons resolve through a domain; anything else registers a plain key."""
    return _lower(section).get("domain") or ("icon" if kind in ICON_KINDS else None)


def images_from_section(node):
    """Atlas records from an `## [Icons]` / `## [Images]` section of an `amd_document`."""
    out = []
    if node is None:
        return out
    section = _lower(node.get("data"))
    domain = _section_domain(_kind_of(node, section), section)
    for n in node.get("children", []):
        out.append(image_record(section, n.get("data"), n.get("key"),
                                n.get("display_text"), domain))
    return out


def images_from_core(section):
    """The same, from an `amd_core` node - the model the LINTER parses into. Two readers
    exist because the linter needs spans and the runtime does not; they share the record
    builder so a fact cannot mean one thing to the linter and another to the game."""
    data = _lower(getattr(section, "data", None))
    kind = str(data.get("__kind__") or section.key or "").strip().lower()
    domain = _section_domain(kind, data)
    return [(child, image_record(data, getattr(child, "data", None), child.key,
                                 getattr(child, "display", None), domain))
            for child in getattr(section, "children", [])]


def _sheet_path(sheet):
    """A sheet named in AMD is a path INSIDE a media pack first - so the same file
    resolves in a clone and in a fetched copy - and only then a plain mission path."""
    if not sheet:
        return sheet
    try:
        from sbs_utils.procedural.media_paths import media_shared
        return media_shared(str(sheet).strip())
    except Exception:
        return str(sheet).strip()


def _cell_size(record, sheet):
    """The cell size in pixels: as written, else measured off the sheet with `Grid:`."""
    cell = record.get("cell")
    if cell:
        return cell
    grid = record.get("grid")
    if not grid:
        return None
    from sbs_utils.procedural.gui.image import ImageAtlas
    width, height = ImageAtlas(None, sheet).get_size()
    if not width or not height:
        return None
    return (width / grid[0], height / grid[1])


def images_declare(records):
    """Register every record with the image atlas. Returns {key: ImageAtlas}.

    A record with `Rect:` uses those pixels; one with `At:` is placed on the cell grid;
    one with neither takes the whole file (a loose image, which is why `Sheet:` may be
    overridden per record).
    """
    from sbs_utils.procedural.gui.image import gui_image_add_atlas
    out = {}
    for r in records:
        key = r.get("key")
        sheet = _sheet_path(r.get("sheet"))
        if not key or not sheet:
            continue
        rect = r.get("rect")
        at = r.get("at")
        if rect and len(rect) >= 4:
            left, top, right, bottom = rect[:4]
        elif at:
            cell = _cell_size(r, sheet)
            if not cell:
                continue                     # unmeasurable; lint says so out loud
            col, row = at
            left, top = int(col * cell[0]), int(row * cell[1])
            right, bottom = int(left + cell[0]), int(top + cell[1])
        else:
            left = top = right = bottom = None
        out[key] = gui_image_add_atlas(key, sheet, left, top, right, bottom,
                                       r.get("color"), r.get("domain"))
    return out


def images_declare_amd(node):
    """Declare every atlas key authored under an AMD images/icons section."""
    return images_declare(images_from_section(node))


def _is_image_section(node):
    """Whether a node's kind noun names an atlas section (`icons`, `images`, `art`, ...).
    Uses the same alias table the Inspector and the linter resolve against, so a section
    word that works in one place works in all of them."""
    from sbs_utils.procedural.amd_schema import _SECTION_ALIASES
    kind = _kind_of(node, _lower(node.get("data")))
    return _SECTION_ALIASES.get(kind) == "image"


def images_sections(doc):
    """Every atlas section in a document, at any depth."""
    found = []

    def walk(node):
        for child in node.get("children", []) or []:
            if _is_image_section(child):
                found.append(child)
            else:
                walk(child)

    walk(doc)
    return found


def images_declare_document(doc):
    """Declare every atlas section in a document - the one call a mission needs, whether
    the sheets live in their own file or in a section of a bigger one. Returns
    {key: ImageAtlas}."""
    out = {}
    for section in images_sections(doc):
        out.update(images_declare_amd(section))
    return out


def images_load_amd(file_path):
    """Read an AMD file relative to the mission folder and declare every atlas in it."""
    from sbs_utils.procedural.amd_doc import amd_document
    from sbs_utils.fs import get_mission_dir_filename
    with open(get_mission_dir_filename(file_path), "r") as f:
        content = f.read()
    return images_declare_document(amd_document(content))


def images_validate(records, resolve=None, check_files=True):
    """Problems a mission would otherwise discover as a blank widget. Returns a list of
    (key, severity, code, message).

    Args:
        records: what `images_from_section` / `images_from_core` returns.
        resolve (callable, optional): `sheet -> (exists, (width, height))`. The default
            asks the image atlas, which needs the engine's mission paths; a static
            linter passes its own so it can check a file it was handed by path.
        check_files (bool): when False, only the checks that need no art - so a linter
            that cannot locate the mission root reports what it CAN know instead of
            calling every sheet missing.
    """
    problems = []
    for r in records:
        key = r.get("key") or "?"
        sheet = r.get("sheet")
        if not sheet:
            problems.append((key, "error", "image-no-sheet",
                             "no `Sheet:` - on the entry or on its section"))
            continue
        if r.get("at") and not r.get("cell") and not r.get("grid"):
            problems.append((key, "error", "image-no-cell",
                             "`At:` needs a `Cell:` (pixels) or a `Grid:` (cells across, "
                             "down) to measure against"))
            continue
        if not check_files:
            continue
        exists, size = (resolve or _resolve_with_atlas)(sheet)
        if not exists:
            problems.append((key, "error", "image-missing-file",
                             f"sheet `{sheet}` is not on disk - the widget draws nothing"))
            continue
        width, height = size
        rect = r.get("rect")
        at = r.get("at")
        if not rect and at:
            cell = _cell_size(r, _sheet_path(sheet))
            if cell:
                rect = [at[0] * cell[0], at[1] * cell[1],
                        (at[0] + 1) * cell[0], (at[1] + 1) * cell[1]]
        if rect and len(rect) >= 4 and width and height:
            if rect[2] > width or rect[3] > height:
                where = f"At: {at[0]}, {at[1]}" if at else "Rect"
                problems.append((key, "warning", "image-off-sheet",
                                 f"{where} falls outside `{sheet}` ({int(width)}x"
                                 f"{int(height)}) - that cell is empty"))
    return problems


def _resolve_with_atlas(sheet):
    """Default resolver: ask the image atlas, which is the same lookup the game does."""
    from sbs_utils.procedural.gui.image import ImageAtlas
    atlas = ImageAtlas(None, _sheet_path(sheet))
    if not atlas.is_valid():
        return False, (None, None)
    return True, atlas.get_size()
