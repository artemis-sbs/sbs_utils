// Shared face compositor for Artemis Cosmos face strings.
//
// CANONICAL COPY: sbs_utils/cosmos_dev/mockgui/face.js
// A verbatim copy is vendored into the VS Code AMD extension at
// sbs_cli/editors/vscode/media/face.js — keep the two in sync.
//
// A face string is ';'-separated layers, each "<race> <#color> <col> <row> [<ox> <oy>]".
// The race maps to a sprite atlas in data/graphics/; every atlas cell is a
// full-face-sized sprite with its part already positioned, so compositing is
// just stacking the referenced cells at the same box, each tinted by its color.
// The optional trailing ox/oy is a small pixel nudge used by some overlay parts.
//
// Cell grid: the Terran sheet is 15 cols x 8 rows; every other sheet is 8 x 8.
//
// Hosts differ only in how an atlas basename becomes a URL — override that with
// setSheetResolver(). The mock server serves data/graphics/ at the root, so the
// default (basename + ".png") works there; the VS Code webview injects
// asWebviewUri() strings instead.
(function (global) {
  'use strict';

  const FACE_ALIAS = {
    ter: 'Terran_Big-revised', tor: 'Torgoth_Set', ska: 'Skaraan_Set',
    kra: 'Krailen_Set',        zim: 'Zimni_Set',   arv: 'Arvonian',
  };
  const GRID_ROWS = 8;
  function gridCols(alias) { return alias === 'ter' ? 15 : 8; }

  let _resolveUrl = (filename) => filename + '.png';
  function setSheetResolver(fn) { if (typeof fn === 'function') _resolveUrl = fn; }

  const _cache = {};  // alias -> { img, cbs }
  function getSheet(alias, cb) {
    const filename = FACE_ALIAS[alias];
    if (!filename) { cb(null); return; }
    if (!_cache[alias]) _cache[alias] = { img: null, cbs: null };
    const entry = _cache[alias];
    if (entry.img)          { cb(entry.img); return; }
    if (entry.cbs !== null) { entry.cbs.push(cb); return; }
    entry.cbs = [cb];
    const img = new Image();
    img.onload  = () => { entry.img = img; const q = entry.cbs; entry.cbs = null; q.forEach(f => f(img)); };
    img.onerror = () => { console.error('[face] failed to load ' + filename + '.png'); const q = entry.cbs; entry.cbs = null; q.forEach(f => f(null)); };
    img.src = _resolveUrl(filename);
  }

  // Seed the cache from an image the HOST already loaded.
  //
  // getSheet above answers SYNCHRONOUSLY once entry.img is set, so a caller that
  // warms every sheet a page needs makes the whole draw synchronous - there is
  // then no pending image load for a renderer to snapshot the page in front of.
  // That is what a static print host needs: a headless browser asked to print
  // will not wait for work it cannot see, so "the atlases are already decoded"
  // has to be a guarantee rather than a race that usually wins.
  function warm(alias, img) {
    if (!FACE_ALIAS[alias] || !img) return;
    if (!_cache[alias]) _cache[alias] = { img: null, cbs: null };
    const entry = _cache[alias];
    if (entry.img) return;
    entry.img = img;
    const q = entry.cbs; entry.cbs = null;
    if (q) q.forEach(f => f(img));
  }

  function parse(str) {
    return (str || '').split(';').map(layer => {
      const p = layer.trim().split(/\s+/);
      if (p.length < 4) return null;
      // p[2] indexes the X axis (column), p[3] the Y axis (row).
      return { alias: p[0], color: p[1], col: +p[2], row: +p[3],
               ox: p.length > 4 ? +p[4] : 0, oy: p.length > 5 ? +p[5] : 0 };
    }).filter(Boolean);
  }

  // Self-contained CSS color parser (own 1x1 canvas; no host dependency).
  const _colorCtx = (() => {
    const c = (typeof OffscreenCanvas !== 'undefined')
      ? new OffscreenCanvas(1, 1)
      : document.createElement('canvas');
    c.width = c.height = 1;
    return c.getContext('2d');
  })();
  function parseColor(cssColor) {
    _colorCtx.fillStyle = '#ffffff';
    _colorCtx.fillStyle = cssColor || 'white';
    const n = _colorCtx.fillStyle;  // browser normalises to #rrggbb or rgba(...)
    const hex  = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(n);
    const rgba = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)/.exec(n);
    if (hex)  return { r: parseInt(hex[1], 16) / 255, g: parseInt(hex[2], 16) / 255, b: parseInt(hex[3], 16) / 255, a: 1 };
    if (rgba) return { r: +rgba[1] / 255, g: +rgba[2] / 255, b: +rgba[3] / 255, a: rgba[4] !== undefined ? parseFloat(rgba[4]) : 1 };
    return { r: 1, g: 1, b: 1, a: 1 };  // unrecognised -> white (no tint)
  }

  function _mkCanvas(w, h) {
    if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
    const c = document.createElement('canvas'); c.width = w; c.height = h; return c;
  }

  function drawLayer(canvas, ctx2d, img, cols, col, row, ox, oy, colorStr) {
    const w = canvas.width, h = canvas.height;
    if (!img || w <= 0 || h <= 0) return;
    const cellW = img.width / cols, cellH = img.height / GRID_ROWS;
    const { r, g, b, a } = parseColor(colorStr || 'white');
    const isWhite = r >= 0.99 && g >= 0.99 && b >= 0.99;
    const sx = col * cellW + ox, sy = row * cellH + oy;
    if (isWhite) {
      ctx2d.save(); ctx2d.globalAlpha = a;
      ctx2d.drawImage(img, sx, sy, cellW, cellH, 0, 0, w, h);
      ctx2d.restore();
    } else {
      // Tint: multiply the color through, then mask back to the sprite's alpha.
      const tmp = _mkCanvas(w, h), tctx = tmp.getContext('2d');
      tctx.drawImage(img, sx, sy, cellW, cellH, 0, 0, w, h);
      tctx.globalCompositeOperation = 'multiply';
      tctx.fillStyle = `rgb(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)})`;
      tctx.fillRect(0, 0, w, h);
      tctx.globalCompositeOperation = 'destination-in';
      tctx.drawImage(img, sx, sy, cellW, cellH, 0, 0, w, h);
      ctx2d.save(); ctx2d.globalAlpha = a; ctx2d.drawImage(tmp, 0, 0); ctx2d.restore();
    }
  }

  // Composite the given layers into canvas. Async: atlases load then draw.
  function draw(canvas, ctx2d, layers) {
    const w = canvas.width, h = canvas.height;
    if (w <= 0 || h <= 0) return;
    const aliases = [...new Set(layers.map(l => l.alias).filter(a => FACE_ALIAS[a]))];
    if (!aliases.length) { ctx2d.clearRect(0, 0, w, h); return; }
    let pending = aliases.length;
    aliases.forEach(alias => getSheet(alias, () => {
      if (--pending > 0) return;
      ctx2d.clearRect(0, 0, w, h);
      layers.forEach(({ alias, color, col, row, ox, oy }) => {
        const img = _cache[alias] && _cache[alias].img;
        if (img) drawLayer(canvas, ctx2d, img, gridCols(alias), col, row, ox, oy, color);
      });
    }));
  }

  function drawString(canvas, ctx2d, str) { draw(canvas, ctx2d, parse(str)); }

  // Warm the atlas cache for the sheets a face string references.
  function preload(str) {
    [...new Set(parse(str).map(l => l.alias))].forEach(a => getSheet(a, () => {}));
  }

  global.FaceRender = { ALIAS: FACE_ALIAS, setSheetResolver, parse, draw, drawString, preload, warm, parseColor };
})(typeof window !== 'undefined' ? window : this);
