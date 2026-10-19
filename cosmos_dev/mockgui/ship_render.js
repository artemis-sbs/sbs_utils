// ship_render.js - turn a hull's OBJ art into a three.js mesh.
//
// SHARED by the browser mock (client.html: 3dship widgets, the 3D view) and the ship
// PORTRAIT renderer (portrait.html, driven by `sbs art portraits`). One loader means a
// portrait looks exactly like the hull does in the mock - and when the look changes, the
// portraits are rebuilt from the same code rather than drifting from it.
//
// No DOM, no fetch, no cache: the host fetches the OBJ text and supplies the texture
// loader, because the two hosts load very differently (the mock caches and retries; the
// portrait page must know when every texture has ARRIVED before it renders).
(function (global) {
  'use strict';

  // Minimal OBJ parser - handles v/vt/vn/f and triangulates polygons.
  function parseOBJ(text) {
    const pos = [], tc = [], nrm = [];
    const posOut = [], uvOut = [], nrmOut = [];
    const idxOut = [];
    const vmap = new Map();
    let vi = 0;
    let hasNormals = false;

    const addVert = key => {
      if (vmap.has(key)) return vmap.get(key);
      const parts = key.split('/');
      const pi = +parts[0] - 1;
      const ti = parts.length > 1 && parts[1] ? +parts[1] - 1 : -1;
      const ni = parts.length > 2 && parts[2] ? +parts[2] - 1 : -1;
      const p = pos[pi] || [0, 0, 0];
      posOut.push(p[0], p[1], p[2]);
      const t = ti >= 0 && tc[ti] ? tc[ti] : [0, 0];
      uvOut.push(t[0], t[1]);
      if (ni >= 0 && nrm[ni]) {
        nrmOut.push(nrm[ni][0], nrm[ni][1], nrm[ni][2]);
        hasNormals = true;
      } else {
        nrmOut.push(0, 1, 0);
      }
      vmap.set(key, vi);
      return vi++;
    };

    for (const rawLine of text.split('\n')) {
      const p = rawLine.trim().split(/\s+/);
      switch (p[0]) {
        case 'v':  pos.push([+p[1], +p[2], +p[3]]); break;
        // NO manual V flip. OBJ's V origin is bottom-left and three.js reconciles that
        // with TextureLoader's flipY, which defaults to true and is never turned off here -
        // so `1 - v` on top of it flipped the texture TWICE and hung it upside down. three's
        // own OBJLoader does not flip for exactly this reason, and these hulls are stock
        // Blender exports, so there is no non-standard convention for it to correct.
        case 'vt': tc.push([+p[1], +p[2]]); break;
        case 'vn': nrm.push([+p[1], +p[2], +p[3]]); break;
        case 'f': {
          const verts = p.slice(1).map(addVert);
          for (let i = 1; i < verts.length - 1; i++)
            idxOut.push(verts[0], verts[i], verts[i + 1]);
          break;
        }
      }
    }
    return { posOut, uvOut, nrmOut, idxOut, hasNormals };
  }

  // `artfileroot` IS A PATH NOW - the 2026-08-15 engine writes `ships/<name>` in
  // shipData.yaml where earlier builds wrote `<name>`. Prefixing unconditionally asked for
  // `ships/ships/<name>.obj`, so every ship in the 3D view lost its mesh. Bare roots still
  // arrive from mod and mission ship-data files, so accept both.
  function shipRoot(art) {
    return art.indexOf('/') >= 0 ? art : 'ships/' + art;
  }

  // A centered Phong mesh with diffuse/specular/emissive maps, from OBJ text.
  //
  // `loadTex(src, cb)` loads one texture and calls cb(tex) - or cb(null) when it is
  // missing, which is normal (not every hull has an emissive map). The mesh comes back at
  // once; `mesh.userData.ready` is a Promise that settles when all three texture loads
  // have answered, for a host that must not render before they have.
  // `mesh.userData.maxDim` is the model's largest dimension, for framing.
  function buildShipMesh(THREE, text, root, loadTex) {
    const { posOut, uvOut, nrmOut, idxOut, hasNormals } = parseOBJ(text);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(posOut), 3));
    geo.setAttribute('uv',       new THREE.BufferAttribute(new Float32Array(uvOut), 2));
    geo.setAttribute('normal',   new THREE.BufferAttribute(new Float32Array(nrmOut), 3));
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(idxOut), 1));
    if (!hasNormals) geo.computeVertexNormals();
    // Center geometry at origin.
    geo.computeBoundingBox();
    const box = geo.boundingBox;
    geo.translate(-(box.max.x + box.min.x) / 2,
                  -(box.max.y + box.min.y) / 2,
                  -(box.max.z + box.min.z) / 2);
    geo.computeBoundingBox();
    const size = new THREE.Vector3(); geo.boundingBox.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z) || 1;

    const mat = new THREE.MeshPhongMaterial({ color: 0xaaaaaa, shininess: 40, specular: 0x444444 });
    let pending = 3, done;
    const ready = new Promise(resolve => { done = resolve; });
    const settle = () => { if (--pending === 0) done(); };
    loadTex(root + '_diffuse.png',  tex => { if (tex) { mat.map = tex; mat.color.setHex(0xffffff); mat.needsUpdate = true; } settle(); });
    loadTex(root + '_specular.png', tex => { if (tex) { mat.specularMap = tex; mat.needsUpdate = true; } settle(); });
    loadTex(root + '_emissive.png', tex => { if (tex) { mat.emissiveMap = tex; mat.emissive.setHex(0xffffff); mat.emissiveIntensity = 1.5; mat.needsUpdate = true; } settle(); });

    const base = new THREE.Mesh(geo, mat);
    base.userData.maxDim = maxDim;
    base.userData.ready = ready;
    return base;
  }

  global.ShipRender = { parseOBJ, shipRoot, buildShipMesh };
})(typeof window !== 'undefined' ? window : globalThis);
