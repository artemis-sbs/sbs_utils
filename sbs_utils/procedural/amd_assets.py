"""Resolving `image://` art for a document rendered OUTSIDE the engine.

`media_paths` already answers "where does this logical art path live", but it
answers it through `fs.get_mission_dir_filename`, which needs an Artemis install
and a running mission. A static exporter has neither - it has a folder path - so
this mirrors that module's SEARCH ORDER against a folder handed to it:

    <mission>/media/...                                    the mission's own art
    __lib__/media/<pack-name>/...                          each pack it pinned

The pinned packs come out of `story.json` exactly as `media_paths._pinned_packs`
reads them (`resources` values plus `shared_media`, `.zip` stripped, declaration
order), because a document that resolves art differently from the game is a
document that shows the wrong picture.

What resolves, and what does not:

  * **`image://`** - a file, once the search includes the ENGINE graphics dir.
    Keys like `ball` and `test` are engine built-ins living in
    `<cosmos>/data/graphics`, not in any mission, so a search that stops at the
    mission folder reports art as missing that is sitting right there.
  * **`face://`** - no file, but not unresolvable either. The value is a
    face-BUILDER string (`arv #ffffff 0 0;arv ...`) naming cells of a race
    ATLAS, and those atlases are real PNGs in the engine graphics dir. The
    browser mock already composites them (`cosmos_dev/mockgui/face.js`, which
    carries a `setSheetResolver` hook precisely so a second host can), so a
    document can too - see `face_atlases`.
  * **`ship://`** - genuinely not resolvable. The tag names a 3D hull, and the
    `.png` beside each mesh is its DIFFUSE TEXTURE, not a picture of the ship:
    `ships/tsn_light_cruiser.png` is a near-white sheet that would print as a
    blank box. The browser mock does not draw one either. A placeholder is the
    honest answer, not a limitation to work around.

A placeholder is a real answer, not a failure: a printed page should say "a
ship goes here" rather than closing the gap silently, because art nobody can
see is missing is art nobody restores.
"""
import base64
import json
import os

# Tried in order for a key with no extension of its own.
_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".webp": "image/webp"}

# Refuse to inline anything absurd. A single 40 MB skybox would make the document
# unopenable, and the placeholder is a better outcome than a browser that hangs.
MAX_EMBED_BYTES = 4 * 1024 * 1024


def pinned_packs(mission_dir):
    """The media packs `story.json` declares, in declaration order.

    Mirrors `media_paths._pinned_packs`: `resources` values (unpacked INTO the
    mission by Mast.expand_resources - not by the engine, which has never heard of
    story.json) plus `shared_media` (read from the one shared copy), `.zip`
    stripped because the unpacked folder is named for the zip."""
    story = os.path.join(mission_dir, "story.json")
    try:
        with open(story, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return []
    declared = list((data.get("resources") or {}).values())
    declared += list(data.get("shared_media") or [])
    out = []
    for value in declared:
        for v in (value if isinstance(value, list) else [value]):
            v = str(v).strip()
            if v.lower().endswith(".zip"):
                out.append(v[:-4])
    return out


def graphics_dir(mission_dir):
    """The engine's `data/graphics`, found by walking up from the mission.

    `fs.get_artemis_graphics_dir` answers this at RUNTIME, from an install the
    engine already located. A static exporter has only a folder, so it looks the
    way the mock server does - it is handed (or finds) the Cosmos root and reads
    `data/graphics` under it. Missions live in `<cosmos>/data/missions/<name>`,
    so the graphics folder is a sibling of the missions folder."""
    here = os.path.abspath(mission_dir)
    for _ in range(6):
        cand = os.path.join(here, "graphics")
        if os.path.isdir(cand) and os.path.isdir(os.path.join(here, "missions")):
            return cand
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return None


def media_roots(mission_dir):
    """Every root a logical media path may resolve against, nearest first.

    Mission art wins over engine art, deliberately: a mission that ships its own
    `ball.png` means its own."""
    mission_dir = os.path.abspath(mission_dir)
    roots = [os.path.join(mission_dir, "media"), mission_dir]
    # `__lib__` sits beside the missions, so walk up looking for it rather than
    # assuming a layout - a mission may be nested (LegendaryMissions/maps/...).
    here = mission_dir
    for _ in range(4):
        lib = os.path.join(here, "__lib__", "media")
        if os.path.isdir(lib):
            for pack in pinned_packs(mission_dir):
                roots.append(os.path.join(lib, pack))
            roots.append(lib)
            break
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    gfx = graphics_dir(mission_dir)
    if gfx:
        roots.append(gfx)               # engine built-ins: ball, test, faces
    return [r for r in roots if os.path.isdir(r)]


class MissionAssets:
    """Resolves a media block to something a `<img src>` can use.

    `embed=True` inlines the bytes as a `data:` URI, which is what makes the page
    self-contained and therefore printable from anywhere. `embed=False` emits a
    relative path instead: a much smaller file that stops working the moment it
    is moved, which is the right trade only while iterating."""

    def __init__(self, mission_dir, embed=True, out_dir=None):
        self.mission_dir = os.path.abspath(mission_dir)
        self.embed = embed
        self.out_dir = out_dir
        self.roots = media_roots(self.mission_dir)
        self._cache = {}
        self.missing = []       # logical names that resolved to nothing
        self.skipped = []       # resolved but too large to inline

    def find(self, name):
        """The file a logical image name resolves to, or None."""
        name = str(name or "").strip().replace("\\", "/").lstrip("/")
        if not name:
            return None
        if name in self._cache:
            return self._cache[name]
        found = None
        stem, ext = os.path.splitext(name)
        tries = [name] if ext else [name + e for e in _EXTENSIONS]
        for root in self.roots:
            for candidate in tries:
                path = os.path.normpath(os.path.join(root, candidate))
                # A logical name must not escape its root - `../../secrets.png`
                # is not art, and a renderer is not a file server.
                if not path.startswith(root):
                    continue
                if os.path.isfile(path):
                    found = path
                    break
            if found:
                break
        self._cache[name] = found
        return found

    def face_sheets(self, specs):
        """`{atlas basename: url}` for every race the given face strings use.

        Only the atlases actually referenced are resolved: a mission whose cast
        is all Zimni pays 0.44 MB, not the 6.8 MB of all six sheets."""
        table = face_alias_table()
        wanted = []
        for spec in specs or ():
            for alias in face_aliases_in(spec):
                name = table.get(alias)
                if name and name not in wanted:
                    wanted.append(name)
        out = {}
        for name in wanted:
            url = self._url(self.find(name), name)
            if url:
                out[name] = url
        return out

    def media(self, block):
        """The `src` for one `media` block, or None to leave a placeholder."""
        if (block or {}).get("ns") != "image":
            return None                     # a face is composited; a ship is 3D
        path = self.find(block.get("url"))
        if path is None:
            self.missing.append(block.get("url"))
            return None
        return self._url(path, block.get("url"))

    def _url(self, path, name):
        """A resolved file -> what an `<img src>` should say, or None."""
        if path is None:
            return None
        if not self.embed:
            base = self.out_dir or self.mission_dir
            try:
                return os.path.relpath(path, base).replace("\\", "/")
            except ValueError:
                return "file:///" + path.replace("\\", "/")
        try:
            size = os.path.getsize(path)
        except OSError:
            return None
        if size > MAX_EMBED_BYTES:
            self.skipped.append((name, size))
            return None
        mime = _MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{data}"


def png_size(path):
    """A PNG's `(width, height)` from its IHDR, or None.

    Twelve bytes of header rather than an image library, because nothing in this
    stack may add a dependency and the only thing an atlas needs is the sheet's
    dimensions - the cell itself is placed with CSS `background-position`, which
    is what the engine does on the GPU anyway."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))


# --- faces -------------------------------------------------------------------
# A face is not a file, but it is not unresolvable either: it names cells of a
# race atlas, and the atlases are real PNGs. `cosmos_dev/mockgui/face.js` is the
# canonical compositor and says so in its own header - it carries a
# `setSheetResolver` hook precisely so a host other than the mock server can say
# where a sheet comes from. A printed page is simply a third host.
#
# The alias table (`arv` -> `Arvonian`) is READ OUT OF face.js rather than
# copied here. A Python copy would be a second definition of which file a race
# uses, and the whole reason this module can reuse the compositor at all is that
# nobody made that copy the last time.

def face_js_path():
    """`cosmos_dev/mockgui/face.js`, or None when cosmos_dev is not installed
    (it is a dev-only package and never ships inside the `.sbslib`)."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))        # .../sbs_utils
    cand = os.path.join(root, "cosmos_dev", "mockgui", "face.js")
    return cand if os.path.isfile(cand) else None


def face_alias_table():
    """`{alias: atlas basename}`, parsed from face.js's own `FACE_ALIAS`."""
    import re
    path = face_js_path()
    if path is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError:
        return {}
    m = re.search(r"FACE_ALIAS\s*=\s*\{(?P<body>[^}]*)\}", src)
    if m is None:
        return {}
    return {k: v for k, v in re.findall(
        r"(\w+)\s*:\s*['\"]([^'\"]+)['\"]", m.group("body"))}


def face_aliases_in(spec):
    """The race aliases one face string references (`arv #fff 0 0;arv ...`)."""
    out = []
    for layer in str(spec or "").split(";"):
        parts = layer.split()
        if parts and parts[0] not in out:
            out.append(parts[0])
    return out
