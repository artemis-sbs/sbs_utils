from .execution import task_schedule, sub_task_schedule
from ..futures import PromiseAllAny, awaitable
from ..helpers import FrameContext
import re

class PrefabAll(PromiseAllAny):
    def __init__(self, proms) -> None:
        super().__init__(proms, True)
        self.set_built = False

    def result(self):
        """
        Get a set of the results of all of the promises.
        Returns:
            set[Promise]: The set of promise results
        """
        #
        # Return just the results in order they finished
        #
        if len(self.promises) >0:
            return None
        if self.set_built:
            return self._results

        results = set()
        
        for p in self._result:
            if p is None:
                continue
            r = p.result()
            if isinstance(r, int):
                results.add(r)
            else:
                results.update(r)
        self.set_built = True
        self._result = results
        return self._result



@awaitable
def prefab_spawn(label, data=None, OFFSET_X=None, OFFSET_Y= None, OFFSET_Z= None):
    """Spawn a prefab label as an independent task and return it.

    Positional keys ``START_X``, ``START_Y``, ``START_Z`` inside ``data``
    set the spawn origin (default 0). The ``OFFSET_*`` params shift that
    origin without modifying the original ``data`` dict. If ``data`` contains
    a ``NAME`` key with a ``#`` placeholder, ``prefab_autoname`` is applied
    to generate a unique name.

    Args:
        label (str | Label): The label to spawn.
        data (dict, optional): Variables passed into the prefab task. May
            include ``START_X``, ``START_Y``, ``START_Z``, and ``NAME``.
            Defaults to None.
        OFFSET_X (float, optional): X offset added to ``START_X``. Defaults
            to None (no offset).
        OFFSET_Y (float, optional): Y offset added to ``START_Y``. Defaults
            to None (no offset).
        OFFSET_Z (float, optional): Z offset added to ``START_Z``. Defaults
            to None (no offset).

    Returns:
        MastAsyncTask: The running prefab task, or ``None`` if the label is
            invalid.
    """
    name = ""
    sx = 0
    sy = 0
    sz = 0
    if data is not None:
        name = data.get("NAME")
        sx = data.get("START_X", sx)
        sy = data.get("START_Y", sy)
        sz = data.get("START_Z", sz)
        if name is not None:
            data["NAME"] = prefab_autoname(name)
    else:
        data = {}

    # If an offset used, apply it
    
    if OFFSET_X is not None:
        if sx is None:
            data["START_X"] = OFFSET_X
        else:
            data["START_X"] = sx + OFFSET_X

    if OFFSET_Y is not None:
        if sy is not None:
            data["START_Y"] = sy + OFFSET_Y
        else:
            data["START_Y"] = OFFSET_Y
    
    if OFFSET_Z is not None:
        if sz is not None:
            data["START_Z"] = sz + OFFSET_Z
        else:
            data["START_Z"] = OFFSET_Z

    t = task_schedule(label, data=data, defer=True, inherit=False)
    if t is None:
        print(f"Invalid prefab label: {label}")
        return None
    t.set_variable("self", t)
    t.set_variable("prefab", t)
    t.tick_in_context()
    return t

__auto_name_counts = {}
def prefab_autoname(name):
    """Return ``name`` with the ``#`` placeholder replaced by an auto-incrementing number.

    If ``name`` contains ``#``, the prefix before ``#`` is used as a counter
    key and the ``#`` (plus any trailing characters) is replaced with a
    zero-padded incrementing integer. Names without ``#`` are returned
    unchanged.

    Args:
        name (str): Name template, optionally containing ``#``.

    Returns:
        str: The name with ``#`` replaced by a unique number, or the original
            name if no ``#`` was found.
    """
    match = re.search(r'#|%', name)

    if match:
        first = match.start()
        start = name[:first]
        end = name[first:].strip()
        if end.startswith('#'):
            key = start.strip()
            count = __auto_name_counts.get(key, 1)
            __auto_name_counts[key] = count +1
            l = str(count).zfill(len(end))

            return start+l
        else:
            # get psuedo random 
            pass

    
    return name


@awaitable
def prefab_extends(label, data=None):
    """Run a prefab label as a sub-task of the current task.

    Unlike ``prefab_spawn``, which creates an independent task, this attaches
    the prefab as a child of the calling task and sets ``self``/``prefab``
    variables so the sub-task can refer back to its parent.

    Args:
        label (str | Label): The label to run as a sub-task.
        data (dict, optional): Variables passed into the sub-task. Defaults to
            None.

    Returns:
        MastAsyncTask: The running sub-task.
    """
    prefab = FrameContext.task
    if data is None:
        data = {}
# Need to set the self and prefab properly
    data["self"] = prefab
    data["prefab"] = prefab
    t = sub_task_schedule(label, data=data)
    t.tick_in_context()
    return t


# ---------------------------------------------------------------------------
# Prefabs by TYPE - the one create path AMD content goes through.
#
# A prefab is named by its metadata type (`npc/station/industry` finds the label whose
# metadata says `type: prefab/npc/station/industry`) or by its exact label name. A
# mission's MAST prefab always wins; the library registers DEFAULT prefabs (plain Python
# spawners) for the types AMD content uses, so a mission with no prefab labels at all
# still gets today's npc_spawn / terrain_spawn behavior, and a mission overrides one by
# writing a label of the same type.
# ---------------------------------------------------------------------------

_DEFAULTS = {}   # type -> PrefabRef. Library defaults: process-global, like vocabulary.
_PENDING = {}    # key role -> a MAST prefab task still running. Per mission.
_WARNED = set()  # specs already reported as unresolved this mission (one line each).

# Names an AMD-authored argument may never carry: prefab_spawn owns `self`/`prefab`, and
# a MAST expression builtin passed as a task variable hides that builtin for the prefab's
# whole body (the ns-metadata-shadows-builtin bug, reached from data instead).
_OWNED_ARGS = frozenset({"self", "prefab"})


class PrefabRef:
    """A resolved prefab: a MAST label, or a library default.

    ``type`` is the type without its ``prefab/`` prefix. ``args`` is what the prefab
    declares it takes, with defaults - a MAST label's metadata, or a default's
    registered table.
    """
    def __init__(self, prefab_type, label=None, fn=None, args=None, display_text=None):
        self.type = prefab_type
        self.label = label
        self.fn = fn
        self._args = dict(args or {})
        self.display_text = display_text

    @property
    def is_default(self):
        return self.fn is not None

    @property
    def name(self):
        if self.label is not None:
            return getattr(self.label, "name", None) or self.type
        return self.type

    @property
    def args(self):
        if self.label is not None:
            inv = getattr(self.label, "inventory", None)
            meta = dict(inv.collections) if inv is not None else {}
            meta.pop("type", None)
            return meta
        return dict(self._args)

    def __repr__(self):
        return f"PrefabRef({self.type!r}, {'default' if self.is_default else self.name})"


def _norm_type(spec):
    s = str(spec or "").strip().strip("/").lower()
    if s.startswith("prefab/"):
        s = s[len("prefab/"):]
    return s


def prefab_register(prefab_type, fn, args=None, display_text=None):
    """Register a library DEFAULT prefab for ``prefab_type``.

    ``fn(data) -> result`` must be synchronous and return what it created: an object, an
    id, or a set/list of ids (None when it deliberately creates nothing). ``args`` is the
    table of arguments it reads, with defaults - what lint and the editor check an AMD
    ``Data:`` block against, the same job metadata does for a MAST prefab.

    A mission's MAST label of the same type always wins over this.
    """
    t = _norm_type(prefab_type)
    _DEFAULTS[t] = PrefabRef(t, fn=fn, args=args, display_text=display_text)
    return _DEFAULTS[t]


# Modules that register library defaults when imported. Loaded on first lookup, so a
# default resolves even in a mission that never imported the module that owns it.
_DEFAULT_OWNERS = ("sbs_utils.procedural.amd_landmarks",
                   "sbs_utils.procedural.prefab_defaults")
_OWNERS_LOADED = [False]


def _ensure_defaults():
    if _OWNERS_LOADED[0]:
        return
    _OWNERS_LOADED[0] = True
    import importlib
    for mod in _DEFAULT_OWNERS:
        importlib.import_module(mod)


def prefab_defaults():
    """{type: PrefabRef} of every registered library default."""
    _ensure_defaults()
    return dict(_DEFAULTS)


def _prefab_story():
    page = FrameContext.page
    story = getattr(page, "story", None) if page is not None else None
    return story or FrameContext.mast


def _label_type(label):
    getter = getattr(label, "get_inventory_value", None)
    t = getter("type") if getter is not None else None
    return t if isinstance(t, str) else None


def _mast_prefabs():
    """[(type-without-prefix, label)] for every MAST label typed ``prefab/...``."""
    story = _prefab_story()
    labels = getattr(story, "labels", None)
    if not labels:
        return []
    out = []
    for name in list(labels):
        label = labels.get(name)
        if label is None:
            continue
        t = _label_type(label)
        if t and t.lower().startswith("prefab/"):
            out.append((t[len("prefab/"):].strip("/").lower(), label))
    return out


def _warn_once(spec, message):
    if spec in _WARNED:
        return
    _WARNED.add(spec)
    from .execution import log
    log(message, "prefab", "warning")


def prefab_resolve(spec, warn=True):
    """Find the prefab ``spec`` names, or None.

    Tried in order: an exact label name; a MAST label whose type is exactly
    ``prefab/<spec>``; a library default registered for exactly ``spec``; a MAST label
    whose type is under ``prefab/<spec>/`` when exactly ONE is. Exact beats prefix, so
    `npc` is the library's npc even in a mission with a dozen `npc/...` prefabs. An
    unresolved or ambiguous spec is logged once and returns None - never a nearby guess.
    """
    if isinstance(spec, PrefabRef):
        return spec
    raw = str(spec or "").strip()
    if not raw:
        return None
    story = _prefab_story()
    labels = getattr(story, "labels", None) or {}
    label = labels.get(raw) if hasattr(labels, "get") else None
    if label is not None:
        t = _label_type(label) or ""
        return PrefabRef(_norm_type(t) or raw, label=label)

    t = _norm_type(raw)
    mast = _mast_prefabs()
    for mt, lbl in mast:
        if mt == t:
            return PrefabRef(mt, label=lbl)
    _ensure_defaults()
    if t in _DEFAULTS:
        return _DEFAULTS[t]
    under = [(mt, lbl) for mt, lbl in mast if mt.startswith(t + "/")]
    if len(under) == 1:
        return PrefabRef(under[0][0], label=under[0][1])
    if len(under) > 1:
        if warn:
            names = ", ".join(sorted(mt for mt, _ in under))
            _warn_once(raw, f"prefab '{raw}' is ambiguous - it could be any of: {names}. "
                            f"Name one.")
        return None
    if warn:
        _warn_once(raw, f"prefab '{raw}' not found: no label of that name, no label typed "
                        f"prefab/{t}, and no library default. Nothing was created.")
    return None


def prefab_catalog(prefix=""):
    """Every prefab whose type starts with ``prefix``: MAST labels first, then the library
    defaults no MAST label overrides. Sorted by type."""
    p = _norm_type(prefix)
    seen = {}
    for mt, lbl in _mast_prefabs():
        if mt.startswith(p) and mt not in seen:
            seen[mt] = PrefabRef(mt, label=lbl)
    _ensure_defaults()
    for t, ref in _DEFAULTS.items():
        if t.startswith(p) and t not in seen:
            seen[t] = ref
    return [seen[k] for k in sorted(seen)]


def prefab_args(spec):
    """{argument: default} the prefab ``spec`` declares (empty when it does not resolve)."""
    ref = prefab_resolve(spec, warn=False)
    return ref.args if ref is not None else {}


def prefab_norm_arg(name):
    """An authored argument name as a prefab variable: ``Fleet Difficulty`` -> ``fleet_difficulty``."""
    return re.sub(r"[\s\-]+", "_", str(name).strip()).lower()


def prefab_data(authored, aliases=None, where=None):
    """Normalize an AMD-authored argument block (``Data:``) into prefab variables.

    Keys are lower-cased with spaces as underscores, then mapped through ``aliases``
    (``{"difficulty": "fleet_difficulty"}``) so AMD can use a plain word for an existing
    prefab's argument without that prefab being renamed. ``self``/``prefab`` and MAST
    expression builtins are dropped with a warning naming ``where``.
    """
    from ..mast.mast_globals import MastGlobals
    out = {}
    if not authored:
        return out
    if not hasattr(authored, "items"):
        return out
    for k, v in authored.items():
        nk = prefab_norm_arg(k)
        if aliases and nk in aliases:
            nk = aliases[nk]
        if nk in _OWNED_ARGS or nk in MastGlobals.EXPRESSION_BUILTINS:
            from .execution import log
            log(f"prefab argument '{k}'{' in ' + str(where) if where else ''} is reserved "
                f"(it would hide a MAST name in the prefab body) - dropped. Rename it.",
                "prefab", "warning")
            continue
        out[nk] = v
    return out


_COUNT_WORD = re.compile(r"^(?:x(\d+)|(\d+)x)$", re.I)


def amd_prefab_spec(value):
    """A field that creates something on its own (`Guards:`, `Spawn:`, `Terrain:`) read
    as ``{"prefab", "count", "args", "words"}``, or None when nothing is written.

    Two shapes, both plain AMD:

        Guards: fleet/raider x2          one line: a prefab, an optional xN count
        Guards:                          nested: Prefab / Count / Data
          Prefab: fleet/raider
          Count: 2
          Data:
            Race: torgoth

    ``args`` is the raw ``Data:`` block (normalize it with ``prefab_data``). ``words``
    are the one-line form's other words, so a caller can still read an older phrase
    (`Guards: torgoth 3`) when the first word turns out not to be a prefab.
    """
    if value is None:
        return None
    if hasattr(value, "items"):
        d = {prefab_norm_arg(k): v for k, v in value.items()}
        spec = d.get("prefab")
        if not spec:
            return None
        try:
            count = int(d.get("count") or 1)
        except (TypeError, ValueError):
            count = 1
        args = d.get("data")
        return {"prefab": str(spec).strip().lower(), "count": max(1, count),
                "args": dict(args) if hasattr(args, "items") else {}, "words": []}
    toks = str(value).split()
    if not toks:
        return None
    count, words = 1, []
    for t in toks[1:]:
        m = _COUNT_WORD.match(t)
        if m:
            count = int(m.group(1) or m.group(2))
        else:
            words.append(t)
    return {"prefab": toks[0].strip().lower(), "count": max(1, count), "args": {},
            "words": words}


def prefab_key_role(family, key):
    """The role marking what a keyed prefab created - ``prefab_key:<family>:<key>``.

    A role because role sets self-clean when the object is deleted, so a destroyed thing
    is re-created by simply asking again, with no bookkeeping.
    """
    return f"prefab_key:{str(family).strip().lower()}:{str(key).strip()}"


def _result_ids(result):
    """Every id a prefab result names (an object, an id, a SpawnData, or a collection)."""
    from .query import to_id
    if result is None:
        return []
    if isinstance(result, (set, list, tuple, frozenset)):
        out = []
        for r in result:
            out.extend(_result_ids(r))
        return out
    try:
        i = to_id(result)
    except Exception:                              # noqa: BLE001
        return []
    return [i] if i else []


def _tag(role, result):
    from .roles import add_role
    for i in _result_ids(result):
        add_role(i, role)


def _settle_pending(role):
    """Tag a pending prefab's result once its task finishes; True while still running."""
    t = _PENDING.get(role)
    if t is None:
        return False
    if not t.done():
        return True
    _PENDING.pop(role, None)
    try:
        _tag(role, t.result())
    except Exception:                              # noqa: BLE001
        pass
    return False


def prefab_first(result):
    """The first object a prefab result names, as an object handle (SpawnData when the
    prefab returned one, else the live Agent), or None. For callers that go on to
    decorate what was created - scale it, tag it, link it."""
    if result is None:
        return None
    if hasattr(result, "engine_object") and hasattr(result, "id"):
        return result
    from .query import to_object
    ids = _result_ids(result)
    return to_object(ids[0]) if ids else None


def prefab_object(family, key):
    """What a keyed prefab already created and is still alive: one object, a set of ids
    when it made several, or None."""
    from .roles import role
    from .query import to_id_list, object_exists, to_object
    if not key:
        return None
    r = prefab_key_role(family, key)
    _settle_pending(r)
    ids = [i for i in to_id_list(role(r)) if object_exists(i)]
    if not ids:
        return None
    if len(ids) == 1:
        return to_object(ids[0])
    return set(ids)


def prefab_create(spec, data=None, family=None, key=None, where=None):
    """Create what prefab ``spec`` makes, synchronously where the prefab allows it.

    ``data`` is the prefab's variables (already normalized - see ``prefab_data``).
    With ``family`` + ``key`` the creation is IDEMPOTENT: everything it made carries
    ``prefab_key_role(family, key)``, a second call returns what is still alive, and a
    destroyed one is re-created.

    Returns the prefab's result: an object, an id, or a set of ids. A MAST prefab that
    awaits before creating returns its TASK (still pending; a repeat call returns the
    same task rather than spawning twice, and its result is tagged when it finishes).
    None when nothing was created - the reason is logged.

    Runs with no task context too (a tick callback): the prefab is scheduled on the
    server task, which is where a mission's world-building runs anyway.
    """
    from .execution import log
    ref = prefab_resolve(spec)
    if ref is None:
        return None
    role = prefab_key_role(family or ref.type, key) if key else None
    if role is not None:
        if role in _PENDING and _settle_pending(role):
            return _PENDING[role]
        existing = prefab_object(family or ref.type, key)
        if existing is not None:
            return existing

    pdata = dict(data or {})
    # Every prefab reads its origin; prefab_spawn only defaults it in its own locals.
    for k in ("START_X", "START_Y", "START_Z"):
        pdata.setdefault(k, 0)
    if ref.is_default:
        try:
            result = ref.fn(pdata)
        except Exception as e:                     # noqa: BLE001
            log(f"default prefab '{ref.type}'{' for ' + str(where) if where else ''} "
                f"failed: {type(e).__name__}: {e}", "prefab", "error")
            return None
        if role is not None:
            _tag(role, result)
        return result

    try:
        if FrameContext.task is None:
            task = _server_prefab_spawn(ref.label, pdata)
        else:
            task = prefab_spawn(ref.label, pdata)
    except Exception as e:                         # noqa: BLE001
        # Under a running story an undefined label RAISES where the mock returns None.
        log(f"prefab '{ref.name}'{' for ' + str(where) if where else ''} failed to start: "
            f"{type(e).__name__}: {e}", "prefab", "error")
        return None
    if task is None:
        log(f"prefab '{ref.name}'{' for ' + str(where) if where else ''} did not start "
            f"(no task context)", "prefab", "error")
        return None
    if not task.done():
        if role is not None:
            _PENDING[role] = task
        return task
    result = task.result()
    if role is not None:
        _tag(role, result)
    return result


def _server_prefab_spawn(label, data):
    from ..helpers import FrameContextOverride
    from ..agent import Agent
    server = Agent.get(0)
    page = getattr(server, "page", None) if server is not None else None
    task = getattr(page, "gui_task", None) if page is not None else None
    if task is None:
        return None
    with FrameContextOverride(task=task, page=page):
        return prefab_spawn(label, data)


def prefab_reset():
    """Per-mission reset: pending prefab tasks and the already-warned set."""
    _PENDING.clear()
    _WARNED.clear()


def prefab_pending_count():
    """Reset-ledger probe."""
    return len(_PENDING) + len(_WARNED)