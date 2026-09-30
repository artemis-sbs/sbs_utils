"""The tile view: one console's window onto a tile area (see ``procedural/tilemap.py``).

Engine-measured before this was written (``data/missions/tilemap_probe``, 2026-09-29):
re-sending 192 atlas tiles in place costs ~2 ms on the server and a client draws them
without trouble, so a GUI tile map is affordable. Two engine facts shape the code:

* **Send order is draw order.** A tile re-sent after an actor covers it, so any pass that
  sends a tile re-sends every actor afterwards.
* **A click region with an empty style shows a magenta hover square**, so every one here
  carries a faint hover color.

THE VIEW SENDS ONLY WHAT CHANGED. It remembers what this console was last sent, per
widget tag, and a dirty pass re-sends only the tiles whose look moved (a door opening, fog
lifting) plus the actors. A fresh build is a fresh widget with an empty memory, so it
sends everything once.

THE CAMERA FOLLOWS, IN PAGES. It keeps still until the followed actor is within
``margin`` cells of an edge, then re-centres - so walking across a screen re-sends four
actor sprites a step rather than the whole viewport.
"""
from .column import Column
from ...helpers import FrameContext

HIDE = (-2.0, -2.0, -1.0, -1.0)      # kept for callers; the view no longer sends it

#: Figure slots. The engine only lets an out-of-band update change a widget that was in
#: the BUILD - a tag first sent later is never drawn (engine-seen: fog lifting showed
#: nothing, and ground the camera scrolled onto stayed black). So every tile tag carries a
#: real image from the first paint (unseen ground is the VOID look), and figures live in
#: a fixed pool of tags that park offscreen when empty, rather than one tag per actor.
#: 96, not 40: a furnished room, a city street or a generated ship deck easily shows more
#: than 40 things at once, and whatever did not get a slot was simply not drawn.
ACTOR_SLOTS = 96
#: Hint badges ("something here is worth a look") - a second pool, drawn last.
HINT_SLOTS = 24
#: A badge covers this share of its tile, in the top-right corner.
HINT_SIZE = 0.5
#: How far outside the view (in cells) an actor may stand and still reach into it - a
#: landed ship anchored off the bottom edge, a tall figure one row below it.
FOOT_REACH = 3
#: Fringe slots: where two kinds of ground meet, the edge of one frayed over the other.
#: Enough for the boundaries in one view; beyond it, a seam simply stays straight.
FRINGE_SLOTS = 160
HOVER = "background_color:#fff2;"


class TileView(Column):
    def __init__(self, tag, follow=None, area=None, cols=17, margin=3, on_click=None,
                 fog=True, hints=None):
        super().__init__()
        self.tag = tag
        self.follow = follow
        self.area = area
        self.cols = max(3, int(cols))
        # NOT `margin`: Column owns that name, and the layout overwrites it with a
        # Bounds - which made the first repaint after a step raise in the engine.
        self.edge = margin
        self.on_click = on_click
        self.fog = fog
        # fn(client_id, area) -> {(x, y): atlas key}: badges over cells worth a look.
        self.hints = hints
        self._camera = None          # (area, left cell, top cell)
        self._geometry = None        # (rows, tile_w%, tile_h%, x0%, y0%)
        self._sent = {}              # widget tag -> (props, rect) this console has
        self._slots = {}             # actor id -> figure slot
        self._order = []             # figure slots in the order last sent (row order)
        self._listening = False

    # --- where the view is looking ----------------------------------------------------

    def current_area(self):
        from ...procedural.tilemap import tilemap_where
        if self.follow is not None:
            at = tilemap_where(self.follow)
            if at is not None:
                return at[0]
        return self.area

    def _layout(self, client_id):
        """How many rows fit, and each tile's size, as screen percent."""
        from ...gui import get_client_aspect_ratio
        b = self.bounds
        ar = get_client_aspect_ratio(client_id)
        w_px = (b.right - b.left) * ar.x / 100.0
        h_px = (b.bottom - b.top) * ar.y / 100.0
        tile_px = w_px / self.cols if self.cols else 1
        rows = max(3, int(h_px // tile_px)) if tile_px > 0 else 3
        tw = 100.0 * tile_px / ar.x
        th = 100.0 * tile_px / ar.y
        x0 = b.left + ((b.right - b.left) - tw * self.cols) / 2.0
        y0 = b.top + ((b.bottom - b.top) - th * rows) / 2.0
        return rows, tw, th, x0, y0

    def _aim(self, area, rows):
        """Keep the camera still until the followed actor nears an edge."""
        from ...procedural.tilemap import tilemap_where, tilemap_size
        w, h = tilemap_size(area)
        cols = self.cols
        at = tilemap_where(self.follow) if self.follow is not None else None
        cam = self._camera
        if cam is not None and cam[0] == area and at is not None:
            _, left, top = cam
            m = self.edge
            if (left + m <= at[1] < left + cols - m or w <= cols) and \
               (top + m <= at[2] < top + rows - m or h <= rows):
                return left, top
        fx, fy = (at[1], at[2]) if at is not None else (w // 2, h // 2)

        def clamp(center, size, span):
            if size <= span:
                return -((span - size) // 2)
            return max(0, min(size - span, center - span // 2))
        left, top = clamp(fx, w, cols), clamp(fy, h, rows)
        self._camera = (area, left, top)
        return left, top

    # --- drawing ----------------------------------------------------------------------

    def _tile_props(self, area, x, y, explored, visible, void):
        """What a tile looks like - or the VOID look for nothing / not yet seen. Never
        empty: see the module docstring on why every tag carries a real image."""
        from ...procedural.tilemap import tilemap_kind, tilemap_kind_spec, tilemap_cell_look
        from ...procedural.gui.image import gui_image_get_atlas
        kind = tilemap_kind(area, x, y)
        spec = tilemap_kind_spec(area, kind) if kind else None
        if spec is None or not spec.get("cell"):
            return void
        if self.fog and (x, y) not in explored:
            return void
        color = spec.get("color") or "white"
        if self.fog and (x, y) not in visible:
            color = "#777"
        return gui_image_get_atlas(tilemap_cell_look(spec, x, y, area)).get_props(color=color)

    def _void_props(self, area):
        """Any cell of the area's tileset, tinted black: how nothing is drawn."""
        from ...procedural.tilemap import tilemap_area, _TILESETS
        from ...procedural.gui.image import gui_image_get_atlas
        rec = tilemap_area(area)
        kinds = _TILESETS.get(rec["tileset"]) if rec else None
        for spec in (kinds or {}).values():
            if spec.get("cell"):
                return gui_image_get_atlas(spec["cell"]).get_props(color="#000")
        return None

    def _send(self, sbs, cid, tag, props, rect, kind="image"):
        key = (props, rect)
        if self._sent.get(tag) == key:
            return False
        if kind == "image":
            sbs.send_gui_image(cid, self.region_tag, tag, props, *rect)
        else:
            sbs.send_gui_clickregion(cid, self.region_tag, tag, props, *rect)
        self._sent[tag] = key
        return True

    def _slot_for(self, aid):
        """A stable figure slot for an actor, or None when the pool is full."""
        slot = self._slots.get(aid)
        if slot is None:
            used = set(self._slots.values())
            free = next((i for i in range(ACTOR_SLOTS) if i not in used), None)
            if free is None:
                return None
            self._slots[aid] = slot = free
        return slot

    def _present(self, event):
        from ...procedural.tilemap import (tilemap_actors, tilemap_actor, tilemap_visible,
                                           tilemap_area, tilemap_listen, tilemap_sprite_look)
        from ...procedural.gui.image import gui_image_get_atlas
        ctx = FrameContext.context
        cid = event.client_id
        if not self._listening:
            tilemap_listen(self._world_changed)
            self._listening = True
        area = self.current_area()
        rec = tilemap_area(area) if area else None
        rows, tw, th, x0, y0 = self._layout(cid)
        if self._geometry != (rows, tw, th, x0, y0):
            self._geometry = (rows, tw, th, x0, y0)
            self._sent.clear()
            self._order = []
        if rec is None:
            return
        left, top = self._aim(area, rows)
        explored = rec["explored"]
        visible = tilemap_visible(area) if self.fog else set()
        void = self._void_props(area)
        # Offscreen, but FULL SIZE and with a real image: a parked figure slot must
        # still be a widget the engine made, or it can never be moved back on screen.
        parked = (x0 - 3 * tw, y0 - 3 * th, x0 - 2 * tw, y0 - 2 * th)

        def rect(vx, vy):
            return (x0 + vx * tw, y0 + vy * th, x0 + (vx + 1) * tw, y0 + (vy + 1) * th)

        tiles_sent = False
        for vy in range(rows):
            for vx in range(self.cols):
                x, y = left + vx, top + vy
                props = self._tile_props(area, x, y, explored, visible, void)
                tag = f"{self.tag}:t{vx}_{vy}"
                if props is not None:
                    tiles_sent |= self._send(ctx.sbs, cid, tag, props, rect(vx, vy))
                self._send(ctx.sbs, cid, f"{self.tag}:c{vx}_{vy}", HOVER, rect(vx, vy),
                           kind="click")

        fringes_sent = self._present_fringes(ctx, cid, area, left, top, rows, explored,
                                             visible, void, parked, rect, tiles_sent)

        # FIGURES, drawn after the ground, in ROW ORDER. A sprite may be taller than its
        # cell (a figure seen in 3/4) or several cells wide (a landed ship), so it
        # overlaps the cells above it - and whatever stands further SOUTH must be drawn
        # over it. Send order is draw order, so whenever any figure changes, every shown
        # figure is re-sent, north to south.
        view = (x0, y0, x0 + self.cols * tw, y0 + rows * th)
        shown = {}                      # slot -> (props, rect, sort key)
        tops = {}                       # cell -> top of the tallest sprite on it
        # People before furniture: if the pool is ever full, a chair goes undrawn, never
        # a person.
        for aid in sorted(tilemap_actors(area),
                          key=lambda i: bool((tilemap_actor(i) or {}).get("fixed"))):
            a = tilemap_actor(aid)
            if not a.get("sprite"):
                continue
            vx, vy = a["x"] - left, a["y"] - top
            if not (-FOOT_REACH <= vx < self.cols + FOOT_REACH and
                    0 <= vy < rows + FOOT_REACH):
                continue
            if self.fog and not a["party"]:
                # Never show what the crew cannot see: a mover only in sight, a fixed
                # thing once its cell has been seen.
                seen = explored if a.get("fixed") else visible
                if (a["x"], a["y"]) not in seen:
                    continue
            look = tilemap_sprite_look(a)
            drawn = self._figure(look, a.get("color"), vx, vy, tw, th, x0, y0, view)
            if drawn is None:
                continue
            slot = self._slot_for(aid)
            if slot is None:
                continue
            shown[slot] = (drawn[0], drawn[1], (a["y"], a.get("fixed") is not True, a["x"]))
            cell = (a["x"], a["y"])
            tops[cell] = min(tops.get(cell, drawn[1][1]), drawn[1][1])
        # Slots nobody is in are parked, and forgotten so the next actor can take them.
        self._slots = {aid: s for aid, s in self._slots.items() if s in shown}
        order = sorted(shown, key=lambda s: shown[s][2])
        changed = tiles_sent or fringes_sent or order != self._order or any(
            self._sent.get(f"{self.tag}:a{s}") != (shown[s][0], shown[s][1]) for s in shown)
        figures_sent = False
        if changed:
            for s in order:
                self._sent.pop(f"{self.tag}:a{s}", None)
                figures_sent |= self._send(ctx.sbs, cid, f"{self.tag}:a{s}",
                                           shown[s][0], shown[s][1])
        self._order = order
        for i in range(ACTOR_SLOTS):
            if i not in shown and void is not None:
                self._send(ctx.sbs, cid, f"{self.tag}:a{i}", void, parked)
        self._present_hints(ctx, cid, area, left, top, rows, tw, th, x0, y0, void, parked,
                            figures_sent, tops, view)

    def _present_fringes(self, ctx, cid, area, left, top, rows, explored, visible, void,
                         parked, rect, tiles_sent):
        """Where two kinds of ground meet, the one that goes OVER frays onto the other:
        its fringe strip drawn along the shared edge (``tilemap_cell_fringes``). A pool
        of slots like the figures', drawn after the ground and before the figures - so a
        tile re-sent means every fringe is re-sent over it. Returns whether any was."""
        from ...procedural.tilemap import tilemap_cell_fringes
        from ...procedural.gui.image import gui_image_get_atlas
        if void is None:
            return False
        placed = []
        for vy in range(rows):
            for vx in range(self.cols):
                x, y = left + vx, top + vy
                if self.fog and (x, y) not in explored:
                    continue
                keys = tilemap_cell_fringes(area, x, y)
                if not keys:
                    continue
                color = "#777" if self.fog and (x, y) not in visible else "white"
                for key in keys:
                    placed.append((gui_image_get_atlas(key).get_props(color=color),
                                   rect(vx, vy)))
        placed = placed[:FRINGE_SLOTS]
        if tiles_sent:
            # Only the ones ON the map must follow new tiles; parked ones are offscreen.
            for i in range(len(placed)):
                self._sent.pop(f"{self.tag}:f{i}", None)
        sent = False
        for i in range(FRINGE_SLOTS):
            tag = f"{self.tag}:f{i}"
            if i < len(placed):
                sent |= self._send(ctx.sbs, cid, tag, placed[i][0], placed[i][1])
            else:
                self._send(ctx.sbs, cid, tag, void, parked)
        return sent

    def _figure(self, key, color, vx, vy, tw, th, x0, y0, view):
        """``(props, rect)`` for a sprite standing on view cell (vx, vy): its footprint
        placed by its anchor on the cell's bottom-center, then CLIPPED to the view - a
        tall figure in the top row must not paint over whatever is above the map. None
        when nothing of it is in view."""
        from ...procedural.gui.image import gui_image_get_atlas
        from ...procedural.tilemap_art import tilemap_sprite_footprint
        atlas = gui_image_get_atlas(key)
        w, h, ax, ay = tilemap_sprite_footprint(key)
        foot_x = x0 + (vx + 0.5) * tw
        foot_y = y0 + (vy + 1) * th
        l = foot_x - ax * w * tw
        t = foot_y - ay * h * th
        r, b = l + w * tw, t + h * th
        cl, ct = max(l, view[0]), max(t, view[1])
        cr, cb = min(r, view[2]), min(b, view[3])
        if cr <= cl or cb <= ct:
            return None
        if (cl, ct, cr, cb) == (l, t, r, b) or atlas.left is None:
            return atlas.get_props(color=color), (l, t, r, b)
        # Crop the picture by the same fractions the rect lost.
        sw, sh = atlas.right - atlas.left, atlas.bottom - atlas.top
        sl = atlas.left + sw * (cl - l) / (r - l)
        sr = atlas.left + sw * (cr - l) / (r - l)
        st = atlas.top + sh * (ct - t) / (b - t)
        sb = atlas.top + sh * (cb - t) / (b - t)
        file = atlas.file.replace("\\", "/")
        props = (f"image:{file};sub_rect:{int(round(sl))},{int(round(st))},"
                 f"{int(round(sr))},{int(round(sb))};color:{color or atlas.color or 'white'};")
        return props, (cl, ct, cr, cb)

    def _present_hints(self, ctx, cid, area, left, top, rows, tw, th, x0, y0, void,
                       parked, figures_sent, tops=None, view=None):
        """Badges over what is still worth a look. Drawn after the figures, so any
        figure re-sent means every badge is re-sent too (send order is draw order). A
        badge rides at the top of the tallest sprite on its cell, so it floats over a
        figure's head rather than over its chest."""
        if self.hints is None or void is None:
            return
        from ...procedural.gui.image import gui_image_get_atlas
        try:
            badges = self.hints(cid, area) or {}
        except Exception as e:                           # noqa: BLE001
            from ...procedural.execution import log
            log(f"tile hints failed: {e}", "tilemap", "warning")
            badges = {}
        if figures_sent:
            for i in range(HINT_SLOTS):
                self._sent.pop(f"{self.tag}:h{i}", None)
        placed = []
        for (x, y), sprite in sorted(badges.items()):
            vx, vy = x - left, y - top
            if sprite and 0 <= vx < self.cols and 0 <= vy < rows:
                r = x0 + (vx + 1) * tw
                t = y0 + vy * th
                if tops and (x, y) in tops:
                    t = min(t, tops[(x, y)])
                if view is not None:
                    t = max(t, view[1])
                placed.append((gui_image_get_atlas(sprite).get_props(),
                               (r - tw * HINT_SIZE, t, r, t + th * HINT_SIZE)))
        for i in range(HINT_SLOTS):
            tag = f"{self.tag}:h{i}"
            if i < len(placed):
                self._send(ctx.sbs, cid, tag, placed[i][0], placed[i][1])
            else:
                self._send(ctx.sbs, cid, tag, void, parked)

    def _world_changed(self, area):
        if self.client_id is None:
            return
        if area == self.current_area() or (self._camera and self._camera[0] == area):
            self.mark_visual_dirty()

    # --- clicks -----------------------------------------------------------------------

    def is_message_for(self, event):
        return str(event.sub_tag).startswith(f"{self.tag}:c")

    def on_message(self, event):
        sub = str(event.sub_tag)
        prefix = f"{self.tag}:c"
        if not sub.startswith(prefix) or self._camera is None:
            return
        try:
            vx, vy = (int(n) for n in sub[len(prefix):].split("_"))
        except ValueError:
            return
        area, left, top = self._camera
        x, y = left + vx, top + vy
        if self.on_click is not None:
            try:
                self.on_click(event.client_id, area, x, y)
            except Exception as e:                       # noqa: BLE001
                from ...procedural.execution import log
                log(f"tile click failed: {e}", "tilemap", "warning")

    def on_end_presenting(self, client_id):
        # The page is going: stop repainting a view nobody can see.
        from ...procedural.tilemap import tilemap_unlisten
        tilemap_unlisten(self._world_changed)
        self._listening = False

    def view_cell(self, x, y):
        """Where a world cell sits in this view, or None when off screen. For tests."""
        if self._camera is None or self._geometry is None:
            return None
        _, left, top = self._camera
        rows = self._geometry[0]
        vx, vy = x - left, y - top
        return (vx, vy) if 0 <= vx < self.cols and 0 <= vy < rows else None
