"""a2x -- Artemis 2.x (2.8) porting-comfort layer.

These functions mirror the vocabulary of the legacy Artemis 2.8 XML mission scripts
so that hand-ports (and the `arme2cosmos` migration tool) read like the original.
They are a **comfort layer, not the idiomatic Cosmos API** -- prefer the native
procedural functions for new missions.

Functions here are registered into the MAST global namespace with an ``a2x_`` prefix
(e.g. ``def pos`` is callable from MAST as ``a2x_pos``), via
``mast_sbs/mast_sbs_procedural.py``.

Legacy semantics this layer assumes:
  * corner-origin coordinates (0..100000) that are mirrored about the map centre in
    Cosmos -- see :func:`coords.pos`,
  * headings in degrees (0..360),
  * count / radius / range style bulk placement.
"""

from .coords import *  # noqa: F401,F403
from .terrain import *  # noqa: F401,F403
from .spawn import *  # noqa: F401,F403
from .comms import *  # noqa: F401,F403
from .ai import *  # noqa: F401,F403
