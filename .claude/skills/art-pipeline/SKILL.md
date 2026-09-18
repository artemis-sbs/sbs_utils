---
name: art-pipeline
description: Making and converting art for the Artemis Cosmos engine - OBJ + texture sets the engine loads, Blender (headless or the official Blender Lab MCP add-on), Synty packs and rigged characters, kitbash-and-bake, palette textures, the generic-* primitives, cube-cross skyboxes, Trellis2 image-to-3D, the WebGPU shader tools, the gas giant and nebula shaders, and mirror/orientation conventions. Use when making or converting 3D art for Cosmos (Blender via MCP or --background, Synty assets and characters, kitbashing), exporting an OBJ the engine must load, making or importing a skybox, fixing or reusing the generic primitives, drawing a top-down plan or minimap, generating a mesh with Trellis2/ComfyUI, editing or optimizing shader-gasgiant / shader-emissivenebula, working in webgpu_tools or the mock's webgpu_field.js, or when a render or view looks mirrored.
---

Art for Cosmos is mostly files on disk that the engine loads by name: meshes and texture
sets under `data/graphics/ships/` (or a mod's media pack), skies as one PNG, and HLSL
shaders under `data/graphics/` that recompile at app launch. This file holds the formats,
the tool locations, and the traps that each cost real time. Most of the art lives in
sibling repos and folders next to `sbs_utils`; paths below are relative to
`E:/a/Cosmos-dev/data/missions/` unless absolute.

Already covered elsewhere - read them rather than re-deriving:

- The `engine-debugging` skill - launching the real exe, crash dumps (the 3D-ship render
  CTD, ObjectDataBlob), and getting values out of the engine.
- The `packaging-and-release` skill - media packs, `story.json` `shared_media`.
- The `writing-a-mission` skill - `@media/skybox` labels in context, terrain spawning.

---

## Where things live

| What | Location |
|---|---|
| Blender (unzipped, not on PATH) | `C:/b/stable/blender-*/blender.exe` - glob it; the folder name carries the build hash (currently `blender-5.2.1-lts.9e2066aef7ef`) and changes on update |
| Blender MCP add-on (official, Blender Lab) | `%APPDATA%/Blender Foundation/Blender/5.2/extensions/lab_blender_org/mcp`, auto-start, `127.0.0.1:9876` |
| Blender MCP stdio server | source `E:/ai/code/blender_mcp` (from `projects.blender.org/lab/blender_mcp.git`), installed as `C:/Users/DougR/.local/bin/blender-mcp.exe` |
| Synty archive (canonical, SMB) | `N:\data_backup\purchased-backups\3D-assets\synty` - 59 `*SourceFiles*.zip` |
| Synty working copies | `E:\ai\kits\<PackName>\` |
| ComfyUI (prop_farm) | `E:\ai\ComfyUI`, conda env `comfyui`, port 8188 |
| Trellis2 ComfyUI | `E:/ai/ComfyUI-Trellis2`, env `comfyui-t2`, port 8189, `start_trellis2.bat`, `SETUP_NOTES.md` |
| Other 3D gen | `E:/ai/Hunyuan3D-2.1`, `E:/ai/prop_farm` |
| Kitbash / bake / skybox tools | `VenusClouds-Mod/_venus_kit_*.py`, `_venus_scratch_ship.py`, `_gen_skybox.py`, `_calibrate_cross.py` |
| TNG skybox tools | `Cosmos-TNG-Mod/_tools/gen_skybox_tng.py`, `import_cross.py`; skies in `Cosmos-TNG-Mod/media/skybox/` |
| Synty character pipeline | `LegendaryMissions/_art/crew_exosuit/` (long-form notes + scripts) |
| Generic primitives (fixed) | `modding_tools/generic_primitives/` (untracked on purpose - modified Artemis art); packaged `cosmos-generics-normals-fixed.zip` |
| WebGPU shader tools | `webgpu_tools/` (`web/`, `docs/`, `shaders/`) - **deliberately outside every git repo** |
| Shader writeups + harnesses | `nebula_shader_optimization/{NEBULA,GASGIANT}_OPTIMIZATION.md`, `nebula_size_test/` |
| Engine shaders | `data/graphics/shader-*.ps/.vs/.cginc`; backups in `data/graphics/_shader_backups/` |
| HLSL compiler | `C:/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64/fxc.exe` |

Never make OneDrive (`E:\o\OneDrive\...`) or `E:\tmp` a build dependency: OneDrive files can
be cloud-only placeholders that stall a read, and a temp dir can be cleaned out from under a
build. Building straight off the `N:` SMB mount is slow and needs the network - extract only
the packs a project uses into `E:\ai\kits`.

---

## Blender

### Headless

```
"C:/b/stable/blender-<ver>/blender.exe" --background --python script.py
```

Blender 5.2 bundles its own Python **3.13** - neither the dev 3.14 nor the engine's 3.11, so a
bake script shares no site-packages with mission tooling (numpy is bundled with Blender).
Driver scripts that post-process PNGs need **Pillow in the dev Python**.

### The MCP

- **The official Blender Lab add-on is already installed** - check for it before installing
  any third-party Blender MCP. A second add-on silently loses the port bind and you debug the
  wrong server. Its tell: replies are raw JSON, NUL-terminated, with no length header, and
  tracebacks name `mcp_to_blender_server.py`.
- **The PyPI `blender-mcp` package is NOT Blender's** (its project URL is literally
  `github.com/yourusername/blender-mcp`). Build the server from the projects.blender.org clone:
  `uv tool install --python 3.13 --with "mcp[cli]<2" E:/ai/code/blender_mcp/mcp`, registered
  with `claude mcp add blender --scope user`.
- **`mcp[cli]<2` is required.** mcp 2.0.0 removed `mcp.server.fastmcp`; unpinned it dies at
  import with `ModuleNotFoundError`.
- **Blender must be RUNNING with a GUI.** The add-on drives its queue from `bpy.app.timers`,
  which do not fire under `--background`. For background mode use
  `blender --background file.blend --command blender_mcp`.

### Talking to the add-on socket directly

A script can skip the MCP server and talk to port 9876 itself (`VenusClouds-Mod/_venus_kit_live.py` does):

- **Messages are NUL-terminated with NO length prefix.** An unterminated request blocks the
  full 10 s client timeout and returns `"Client timed out"` - reads like a hang, not a framing
  bug. A length prefix instead gets a JSONDecodeError.
- Request: `{"type": "execute", "code": ..., "strict_json": bool}`. `rstrip("\x00")` replies
  before parsing.
- **Operators fail "context is incorrect"** (e.g. `bpy.ops.wm.obj_import`) because code runs
  from a timer with no 3D-view context. Borrow one with
  `bpy.context.temp_override(window=..., screen=..., area=<VIEW_3D>, region=<WINDOW>)`.
- **`read_factory_settings` is blocked by the add-on sandbox**; use
  `read_homefile(use_empty=True, use_factory_startup=True)`. The sandbox names the
  replacement in its error - read the error.

### bmesh authoring rules

- **Never identify new geometry by a positional slice** (`list(bm.verts)[v0:]`). The vertex
  sequence is not an append-only log once `bmesh.ops` has run a few times, and a following
  `bmesh.ops.transform` smears unrelated geometry. Use the op's return value
  (`res = bmesh.ops.create_cone(...)`; `res["verts"]`) and derive faces from `link_faces`.
- **When geometry looks wrong, run a per-shell bounding-box audit before theorizing**: walk
  connected components via `edge.link_faces`, print each shell's face count and size. A
  40-face hoop measuring 8.76 units instead of 1.2 ends the argument.
- **Recalc normals per primitive while each shell is isolated.** One blanket
  `recalc_face_normals` over a soup of closed and open shells flips whole bodies inside out.
- **Review from an orbit, never one camera.**
- **Render-engine enum is unreliable for feature detection** in 5.2 (lists only
  `BLENDER_EEVEE` though `CYCLES` and `BLENDER_WORKBENCH` assign fine). Pick an engine by
  assigning inside try/except. EEVEE Next is `BLENDER_EEVEE_NEXT` on 4.x and plain
  `BLENDER_EEVEE` on 5.x - same engine, renamed.

---

## Exporting a mesh the engine loads

A ship/prop art set is `<root>.obj` plus `<root>_diffuse.png`, `_emissive.png`,
`_normal.png`, `_specular.png`, and two radar sprites `<root>1024.png` / `<root>256.png`.
The engine derives `<root>.paxmesh` from the OBJ.

- **The OBJ exporter empties an INSTANCED mesh.** It writes a shared mesh once per instance
  group, so exporting one object of an instanced mesh with "selected only" produces a header
  and no geometry. The engine then asserts `art3D && "the artfileroot of this ship was not
  found."` (ObjectTypeDrawData.cpp:40). **Export from a single-user copy and check the file
  has `v` and `f` lines.**
- **Flat art stays `s off`.** Exporting smooth averages normals across 90-degree edges and a
  flat plate renders as a soft gradient that reads as "not solid".
- **A missing `.paxmesh` is rebuilt on demand.** Engine 1.3.5 ran a full mission with OBJs
  replaced and every `.paxmesh` deleted. This contradicts the warning in `making-a-mod.md`
  that generating derived art from a bare `.obj` crashes the engine - it did not bite in that
  test. Textures need no rebuild at all: a `.paxmesh` stores texture PATHS, not pixels.
- **The constraint is ONE TEXTURE SET, not one object.** Measured across all 201 stock `.obj`:
  `God_Phoenix` ships 16 submeshes, `TSN_Escort` 6, 102 declare no material; stock `monster2`
  is itself a two-part kitbash. "Every engine mesh is 1 object" is wrong.
- **Triangle budget is not an engine limit.** Stock art ranges 1,790-7,784 tris, but the 46
  meshes in `Cosmos-TNG-Mod` load fine at a median of 14,092 and a max of 145,856
  (`FED_Ambassador`), with up to 31 objects in one model. Target the TNG median or above for
  new art rather than treating the stock sample as a cap.
- **Measure in the unit the budget is written in.** `obj_export(export_triangulated_mesh=True)`
  triangulates on the way out (~1.75x faces for quads/ngons), so a hull logged at 7,427 "tris"
  shipped 12,958. Apply a TRIANGULATE modifier BEFORE decimating; verify by counting `f `
  lines in the shipped `.obj`, never the builder's log.
- **Always render the SHIPPED `.obj` + `_diffuse.png`**, not the working blend - it is the only
  render that proves the artifact.
- Engine loading of new mod ship art is not a given - mod art has a crash history (see
  `engine-debugging`). Treat a set as unverified until it has drawn in the engine.

---

## Synty packs

Pack shape varies - check before assuming a path. Older packs ship `SourceFiles/OBJ` +
`SourceFiles/Textures`; newer ones (Kaiju, Mech) are **FBX only, zero OBJ**; Sci-Fi Space puts
`OBJ/` at the pack root. Kaiju is not a parts kit (two whole creatures plus a destroyed city);
anything organic has to be generated.

### Rigged characters

`POLYGON_ScifiSpace_SourceFiles/Characters/FBX 2013/` has 28 rigged `SK_Chr_*` characters (EVA
suit, soldiers, crew, cryo, aliens, a war robot) on one UE-style skeleton (`Pelvis`,
`spine_01..03`, `UpperArm_L`, `lowerarm_l`, `Thigh_L`, `calf_l`...). **Casing is inconsistent**
(`Foot_L` but `calf_l`) - resolve bone names case-insensitively.

- **Import space:** the armature object carries a 0.01 scale and a Y/Z swap, so inside armature
  space +X = the figure's left, +Y = world up, +Z = the facing direction, in centimeters. In
  world the characters face **-Y**.
- **FBX 2013 custom split normals import as shard soup.** 35 of the EVA suit's 37 shells come
  in dark and faceted - it reads as broken geometry, not shading. Clear them
  (`customdata_custom_splitnormals_clear`), then fix winding **one shell at a time, flipping
  only shells with negative signed volume**. A blanket `recalc_face_normals` turns the head into
  a bowl. POLYGON art is flat shaded; smoothing makes it worse.
- **`SK_Chr_BR_EVA_Suit_01` is HEADLESS** - the helmet is a hollow shell. Graft a head from
  `SK_Chr_Crew_Male_01` (same skeleton: retarget the armature modifier, join before posing),
  drop the donor's cap/visor by atlas color, scale ~0.90 to seat it. **Put the donor verts in
  a vertex group** - nothing downstream can find the head otherwise.
- **Aim LIMB bones at absolute directions, never spine/neck/head.** The `head` bone points
  forward through the skull in rest, so "aim it up" is a 60-degree swing that shreds the
  skinning; nudge those relatively. Robust limb primitive, parents first, with
  `view_layer.update()` between bones:
  `pb.matrix = translate(head) @ rotation_difference(cur_dir, target).to_4x4() @ translate(-head) @ pb.matrix`
- **Atlas color cannot tell you which way a face looks** - Synty bakes lighting into the atlas,
  so the LIT cells are the top of the skull. Record the head bone's world direction onto the
  object while the armature still exists.
- **All six atlas variants (A, Alts B-F) are identical for characters**; the alts recolor ship
  cells only. To recolor, cluster faces by flat atlas color (the EVA suit uses 12) and assign
  named flat materials.

### Flat-color sets want a PALETTE texture, not a bake

When every material is one flat color, give each material one large cell of a small PNG (12
materials -> a 4x4 grid of 64 px cells in 256 px) and point every face at its cell's center:
~2 KB, no seams, no bake noise, and the PNG's bytes ARE the palette, hand-editable. Big cells
on purpose - mipmapping bleeds small ones together at distance.

**Write Base Color straight into the image.** It is already linear and Blender encodes on save.
Converting sRGB->linear first looks like the fix and darkens the whole set by a stop (orange to
blood red, greys to near-black).

---

## Kitbashing and baking (VenusClouds-Mod)

`_venus_kit_bake.py` + `_venus_kit_bake_blender.py` build a Cosmos art set from declarative
recipes in `venus_kit_recipes.py`; parts can come from any Synty pack, prop-farm GLBs, or both.
It globs `C:/b/stable/blender-*/blender.exe` (`VENUS_BLENDER` overrides). Rebuilding on 5.2 gave
geometry bit-identical to the 4.5 build; only baked PNGs differ by ordinary Cycles noise.

- **Two UV layers, never one.** `smart_project` writes into the ACTIVE layer, which is the one
  source atlases sample through - bake that way and the ship is a patchwork. Bind source
  textures to an explicit UVMap node.
- **Recipe scale multiplies the UNIT-SCALED size.** Packs differ ~30-50x, so each declares a
  `unit_scale`. Helpers that take fleet units (`deck(23, 25)`, `env(20, 4.4)`) remove the class
  of error.
- **Check part ORIGINS.** A wall authored to stand on the ground (bbox y 0..313) laid flat as
  a deck becomes a half-length offset.
- **Decimate AFTER assembly and protect small parts.** A uniform ratio flattens the cheap
  parts that carry the read.
- **Pick palettes by LOOKING, not averaging.** A mean color hides a high-variance atlas (a
  "dark neutral" candidate rendered purple-and-lime). `_venus_kit_palette.py` renders the
  dominant colors a recipe actually samples, per candidate atlas.
- **Use parts shaped like what they stand in for.** Capital-ship armor mirrored as nacelle
  rails on small hulls out-masses the hull and makes different hulls read as one ship.

`_venus_kit_live.py <recipe> [--build|--watch]` pushes a built hull into a running Blender
over the add-on socket so it can be orbited; `--watch` rebuilds on every recipe save.

`_venus_scratch_ship.py` builds a set from pure procedural geometry (high-poly -> decimate ->
bake diffuse/emissive/normal into one atlas). At that density: **bevel only HARD edges**
(`e.calc_face_angle(0) > radians(22)`) or smooth surfaces quilt, and **subdivide the high-poly
copy** (SUBSURF 2) or high == low and the normal bake writes the mesh against itself.

---

## The generic-* primitives

Twelve fly-through shapes (`exclusionradius 0`) that build relics and set dressing with no mod
and no new art. ShipData keys are `generic-cube`, `generic-rectangle`, `generic-cylinder`,
`generic-sphere`, `generic-disk`, `generic-hexagon`, `generic-cone`, `generic-torus`,
`generic-tetrahedron`, `generic-octohedron`, `generic-icosahedron`, `generic-dodecahedron`; the
art roots in `data/graphics/ships/` are the bare names (`cube.obj`, `rectangle.obj`...). World
size = OBJ extent x `meshscale`: rectangle 100 x 100 x 1.25 (thin in local +Z), cube 40 a side,
cylinder 100 long, sphere 200 across.

As shipped (measured 2026-08-13):

- **Ten of twelve are INSIDE-OUT** (all faces toward the center); only cube and rectangle face
  outward, torus is legitimately half. Inward is right for a shell seen from inside (a chamber
  as one inverted sphere); outward for a pillar or panel.
- **The translucency is in the TEXTURE**: `<root>_diffuse.png` carries a flat alpha of ~150-158,
  so anything built from them reads as a ghost.
- **`<root>1024.png` / `<root>256.png` are radar sprites whose alpha IS the icon shape.**
  Flattening their alpha turns every radar blip into a solid square. Only `_diffuse` should be
  made opaque.
- **Colors are a debug palette**, one per shape (rectangle/cylinder orange, cube/octohedron red,
  sphere/disk green, hexagon cyan, cone magenta, torus purple, tetrahedron/dodecahedron yellow,
  icosahedron blue).

---

## Skyboxes

**A sky is ONE PNG: a 4x3 cube cross**, no manifest, no six-file set. Stock skies are
`data/graphics/sky*.png` at 8192x6144 (2048 px faces); 4096x3072 and 2048x1536 also work.
Starfields compress well (TNG skies are 0.5-0.8 MB at 1024 px faces). Cell layout (row, col),
origin top-left:

```
  .     front   .      .
 left    up    right  down
  .     back    .      .
```

- **The skybox path is unrestricted.** `sbs.set_sky_box(clientID, path)` takes exe-relative or
  absolute paths, so a mod ships skies from its own media pack. (It is `set_music_folder` that
  hangs on a path, not this.) **Never pass the `.png` extension** - the engine appends its own.
- **A `@media/skybox/<path> "Name"` label only registers.** Something must schedule it: LM's
  server console does `shared skybox = skybox_schedule_random()`, and console select applies a
  per-client cascade (shared `skybox` < ship's `skybox` inventory < client's). There is no
  `SKYBOX_SELECT` setting.
- **Silent failure:** a label whose PNG is missing is dropped from the random pick with no
  message - "the new skies never come up". Usual cause: the consuming mission lacks the
  `shared_media` line in `story.json`. The mission runner logs "no `@media/skybox` labels are
  loaded at all" when a mission has none; that line disappearing confirms registration.
- **Do not re-derive the cube geometry.** `VenusClouds-Mod/_gen_skybox.py` has it solved. The
  cross exposes only 5 of the cube's 12 edges, so fitting per-face rotations to minimize
  visible seams can score better than stock and still tear the 7 hidden edges. The invariant is
  handedness: `cross(r, d) == -n` on every face. `_calibrate_cross.py --geometry` walks all
  twelve edges; `--verify <png>` scores a cross (stock `sky1.png` = 1.01, a scrambled face = 21).
- **space-3d (tools.wwwtyro.net/space-3d) needs no conversion** - its 4x3 download is already
  in Cosmos's unfolding (measured 1.72 as cosmos vs 12.0 as standard). Rename and drop it in
  `media/skybox/`.
- **Other tools:** `Cosmos-TNG-Mod/_tools/import_cross.py` detects the unfolding by resampling
  each candidate and scoring all twelve edges; `--install NAME` drops it into `media/skybox`
  and prints the label line.
- **Generation, ranked:** procedural (seamless by construction; `gen_skybox_tng.py` is a
  template: 3-layer starfield + masked nebula + galactic band + optional sun) > Spacescape
  (six faces -> `boxey` assembles the cross) > diffusion LAST and only as an equirect
  panorama, never six independently generated faces.
- **Tuning:** star thresholds 0.91-0.94 (0.97 reads unfinished); keep nebula masked and low or
  the sky drowns the ships.

---

## Trellis2 (image -> 3D)

A second ComfyUI isolated from the prop_farm one so neither disturbs the other.

- **Version pins are load-bearing, install as ONE command:** torch 2.8.0+cu128, torchvision
  0.23.0+cu128, torchaudio 2.8.0+cu128, xformers 0.0.32.post2, triton-windows 3.4.0.post21.
  Pinning only torch pulled a mismatched torchaudio (`WinError 127`); a bare `pip install
  xformers` pulled a new torch.
- Node is `visualbruno/ComfyUI-Trellis2` (prebuilt cp311 wheels). **LoadModel defaults to
  `flash_attn`, which is not installed** - set `backend: sdpa`, `sparse_backend: xformers`.
- **CuMesh `connectivity.cu:125` CUDA error 9 means an EMPTY mesh**, not a GPU fault. Usually a
  miswired graph: DecodeLatents `resolution` must be wired from ShapeCascadeGenerator's
  `resolution` output.
- **Input: photo/render-like 3/4 views.** It fails silently on flat orthographic schematic art -
  returns a relief slab or a sphere with the drawing wrapped on it; multi-view of two
  orthographic elevations is worse. Check `min(extents)/max(extents)` on the result (a flat card
  is ~0.2). SDXL 3/4 prop renders reconstruct excellently. This inverts Hunyuan3D-2.1's
  preference for side views.
- Output is millions of faces - run `Trellis2SimplifyMesh` before anything goes in-engine.

---

## Engine shaders

Shaders under `data/graphics/` are **engine-free to edit but compile only at app launch** - a
mission reload does NOT recompile, so every A/B needs a clean relaunch. **Compile with `fxc`
first**; from Git Bash, `export MSYS2_ARG_CONV_EXCL='*' MSYS_NO_PATHCONV=1` or the `/T /E /Fo`
flags get mangled, and fxc cannot open MSYS `/tmp` paths. Diffing the compiled `.asm` of old vs
new is a cheap correctness proof. Shared includes (`noise.cginc`, `volume.cginc`) ripple into
every shader that includes them. Back up to `_shader_backups/` before editing.

### Nebula

**Live path:** `shader-nebulavolume.vs` (`DX11PAXShaderNebulaVolume`) -> `shader-emissivenebula.ps`
raymarches into an offscreen buffer -> `shader-volumepostprocess.ps` (`DX11PAXShaderVolumePost`)
blurs it to screen. **Dead:** `shader-nebula.ps/.vs` (legacy `3DNebula`) - do not optimize it.
`shader-testvolume.*` is referenced by the exe but absent on disk.

- **Size ceiling:** a hardcoded `10000` far plane in `linearDepth()` drew a "sphere at the
  origin" above size ~3000. `#define NEB_DEPTH_PROJECTION 1` derives depth from the real
  projection and lifts the ceiling past 7000. Cluster object count is
  `cluster_size // NEB_SIZE_LARGE` (1500), so raising `NEB_SIZE_LARGE`/`NEB_MAX_SIZE` yields
  fewer, bigger objects without re-tuning the generator.
- **Perf:** cost is the raymarch (`SpiralNoiseC` + `snoise` per step). Cutting octaves or steps
  is visible and was rejected. Quality-preserving levers: the transmittance early-out (the
  shipped `result.a >= 1.0` test was dead - `a` is transmittance, starting at 1.0 and falling)
  and cbuffer params `downsampleRatio`, `numOctaves`, `maxSteps`, `stepSize`.
- **Nebulae paint over near ships because the depth SRV at `t1` is cleared, not populated** -
  it reads a flat 1.0 everywhere (engine-measured, `NEB_DEBUG_MODE` probes left in the shader).
  The engine ask: bind the populated scene depth to `t1` for `DX11PAXShaderNebulaVolume`, and to
  `shader-volumepostprocess.ps` for a bilateral upsample (else a ~4 px halo hugs silhouettes).
  The shader side already ships behind `NEB_DEPTH_OCCLUSION 1` (per-pixel ray truncation), inert
  until then, **guarded on raw depth strictly inside (0,1)** - a cleared 1.0 and an unbound 0.0
  both mean "nothing drawn".
- The engine depth buffer is already DX convention; `depthDXtoGL()` is misnamed (it returns
  `(z+1)/2`) and must not wrap it.
- Presets: `_neb_colors` in `terrain.py` (HDR up to 2.0); baseline density 7.24. Output is SDR.

### Gas giant

`shader-gasgiant.ps/.vs` (`DX11PAXShaderGasGiant`) renders `terrain_spawn(..., "#,gasgiant",
"planet", "behav_planet")`. It is a SURFACE renderer (no overdraw). Writeup:
`nebula_shader_optimization/GASGIANT_OPTIMIZATION.md`; harness and `PLANET_PRESETS`:
`nebula_size_test/`.

- Dark-side skip is enabled (the old `else` returned white - the "white dark side" bug).
  `GG_ANALYTIC_INTERSECT` (off) swaps the 32-step sphere trace for a closed-form ellipsoid hit.
- No radius cap in the shader; the ceiling is `render-distance-large-objects` in
  `preferences.json` (50000) - big planets tear when they cross it.
- **data_set levers** (`planet_` prefix): bandScale 0-12, upperCloudStrength 0-12,
  upperCloudExponent 0-12 (effectively boolean: clouds on below 1), baseColor / emissiveColor /
  upperCloudColor 0-2 (HDR), fresnel 1.5-150, fresnelBias 0.015-1.15, radius 10-3000. **Dead:**
  windSpeed1/2, storm params, oblateness.
- **Per-planet variety without a seed input** (`GG_SEED_FROM_EXPONENT 1`): use
  upperCloudExponent as a band seed for banded planets (random 2-12), and rotate the normal
  about the pole by an angle seeded from the jittered base color. Static only - spin, cloud
  animation and a real seed need engine uniforms (time is hardcoded; object rotation does not
  reach the world matrix).

Gas giant **docking** (orbit capture) is gameplay code, not art: `sbs_utils/procedural/orbit.py`
and `LM_TestRange/maps/test_gas_giant_dock.mast`.

---

## WebGPU tools

`webgpu_tools/` (outside all git repos by design; plan in `docs/WEBGPU_TOOLS_PLAN.md`) holds
browser WGSL tools for the engine shaders - `web/nebula.html`, `celestial.html`,
`gasgiant.html` (port of the live shader), `field.html` - bundled into one `studio.html` by
`build_studio.py` (artifacts cannot iframe each other). The nebula engine handoff is
`nebula_engine_handoff.zip` / `docs/NEBULA_ENGINE_IMPL_GUIDE.md` plus fxc-validated HLSL in
`shaders/hlsl/`.

- **`build_studio.py` keeps only the shared STYLE, dropping each tool's `<style>`** - add
  tool-specific CSS there. CSS unicode escapes in it need doubled backslashes (`\\2713`), or Python eats them as octal.
- WGSL: `target` is reserved; `r16float` is not a core storage format (bake `r32float`, which
  needs `float32-filterable` to sample linearly).

**The mock's 3D view** is `sbs_utils/cosmos_dev/mockgui/webgpu_field.js` (default; `?webgl` or a
WGSL failure falls back to WebGL). Meshes use native OBJ scale x `meshscale` (do not
normalize); the mock quaternion `q` is **[w,x,y,z]**; cube-cross skyboxes load **non-sRGB**
while mesh diffuse stays sRGB. Mock **Python** edits need a runner process restart; JS/HTML
edits need only a browser refresh.

---

## Orientation and mirror traps

Three separate mirrors. Each is invisible to tests written in the same wrong convention - get a
picture early.

- **Top-down XZ plans: +Z is UP.** The mock radar projects `toY = cy - (wz - cz) * scale`. SVG
  and canvas y grow downward, so negate z. Drawing `y = z` mirrors north for south, and 63
  passing tests once missed exactly that. Pin it with an explicit "+Z draws above the origin"
  test. Grid is 1000 minor / 10000 major (engine 2D view); the browser mock's 3D grids use
  5000 u cells - a known discrepancy. A drag should report WORLD deltas: negate at the
  boundary.
- **The engine mirrors a cinematic camera offset through the dolly.** Handing it `+Z * 500`
  puts the lens 500 along -Z. Invisible to single-subject shots. `_engine_lens(base, want)` in
  `sbs_utils/procedural/gui/camera.py` is the one place that compensates. **Do not "fix"
  `camera_shot`** - authored cutscenes everywhere were tuned against the mirrored behavior.
  `tests/test_camera_convention.py` pins both halves. A camera test must assert the position
  the ENGINE derives, not the mock's kinder `dolly + offset`.
- **VisualTestRange frames are mirrored in world X**: camera at -Z looking +Z, world +X lands
  screen-LEFT. Label visual specimens by ship NAME, never by side, and bracket a by-eye test
  with a positive and a negative control that must differ before the middle result counts.
