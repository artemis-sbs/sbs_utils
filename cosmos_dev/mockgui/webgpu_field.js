// webgpu_field.js — Prong 2: a WebGPU 3D overlay for the cosmos_dev mock.
//
// Loaded ONLY with ?webgpu=1 (or #webgpu); client.html appends it as a module. It creates its
// own fullscreen canvas and renders the mock's live objects (terrain + dynamic) as INSTANCED
// 3D meshes — using the REAL game art (/ships/<art>.obj + <art>_diffuse.png), one instanced
// draw per art. Reads mock state through the window.__mockField() bridge, so Three.js is
// untouched. Press 'g' to toggle; drag to orbit, wheel to zoom.
//
// Matches the mock's transform: world = (posBuf[i*3], meta.y, posBuf[i*3+1]), oriented by
// meta.q, scaled by meta.meshscale on the native (centered) mesh. Nebulae (meta.nebula) are
// skipped here for now — the volumetric nebula shader is the next step.

const bridge = () => (window.__mockField ? window.__mockField() : null);
function wlog(m){ try{ console.log("[webgpu_field] "+m); }catch(e){} }
if(!("gpu" in navigator)){ wlog("WebGPU not available — overlay disabled."); }
else { start().catch(e=>wlog("init error: "+(e&&e.message||e))); }

async function start(){
  const canvas=document.createElement("canvas");
  canvas.id="webgpu-field";
  canvas.style.cssText="position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:0;background:#05070c;display:none";   // background layer (like the WebGL 3dview at z-1); HUDs/GUI at higher z draw on top
  document.body.appendChild(canvas);
  let visible=true; const MODES=["chase","orbit","cinematic"]; let modeIx=0, shipSel=0, npcSel=0, focusNpc=false, showGrid=true;
  let fps=60, fpsFrames=0, fpsT=performance.now();
  const hud=document.createElement("div");
  hud.style.cssText="position:fixed;top:10px;right:12px;z-index:2147483001;font:12px/1.5 ui-monospace,Consolas,monospace;color:#e7ebf2;background:rgba(10,12,17,.62);border:1px solid #232833;border-radius:8px;padding:8px 11px;pointer-events:none;white-space:pre;text-align:right";
  document.body.appendChild(hud);
  window.addEventListener("keydown",e=>{
    if(e.key==="g"){ visible=!visible; canvas.style.display=visible?"block":"none"; hud.style.display=visible?"block":"none"; }
    if(e.key==="c"){ modeIx=(modeIx+1)%MODES.length; }   // cycle chase -> orbit -> cinematic
    if(e.key==="v"){ focusNpc=false; shipSel++; }        // cycle which PLAYER ship the chase follows
    if(e.key==="n"){ focusNpc=true; npcSel++; }          // cycle NON-player ships (find a far / cloaked NPC)
    if(e.key==="B"){ beamCensus={in:0,nometa:0,noports:0,arccull:0,drawn:0,peak:0};
                     projCensus={launches:0,peak:0,now:0,prev:0,frames:0,ynone:false}; }   // zero the censuses for a fresh measurement
    if(e.key==="b"){ showGrid=!showGrid; }               // toggle the reference grid
    if(e.key==="k"){ nebBaked=!nebBaked; }               // nebula: baked (sample resident 3D pool) vs live (recompute noise)
    if(e.key==="t"){ nebSteps=({24:48,48:96,96:24})[nebSteps]||48; }  // raymarch steps knob
    if(e.key==="m"){ nebStress=({1:4,4:16,16:64,64:1})[nebStress]||1; } // stress: draw N× copies to show cost-vs-count
    if(e.key==="r"){ nebResIx=(nebResIx+1)%NEB_RES_OPTS.length; rebake(); }  // bake resolution knob (VRAM vs fidelity)
    if(e.key==="f"){ nebStepMode=nebStepMode?0:1; }      // stepping: fixed count-48 vs field-style fixed size (~11)
    if(e.key==="s"){ nebShare=!nebShare; rebake(); }     // share: N nebulae ← K templates (data-reduction) vs N unique slabs
    if(e.key==="x"){ const o=[0.3,0.18,0.12,0.06]; nebCover=o[(o.indexOf(nebCover)+1)%o.length]; rebake(); }  // cloud coverage: lower cutoff = cloud fills more of the sphere
  });

  const adapter=await navigator.gpu.requestAdapter({powerPreference:"high-performance"});
  if(!adapter){ wlog("no adapter"); return; }
  const canTS=adapter.features.has("timestamp-query");   // real per-pass GPU-ms (fps caps at vsync, useless for headroom)
  const device=await adapter.requestDevice({requiredFeatures: canTS?["timestamp-query"]:[]});
  const ctx=canvas.getContext("webgpu"); const format=navigator.gpu.getPreferredCanvasFormat();
  ctx.configure({device,format,alphaMode:"opaque"});

  const WGSL=`
  struct U { vp:mat4x4<f32>, camDir:vec4f, camRight:vec4f, camUp:vec4f, camPos:vec4f };   // camDir.w=tan(fov/2), camRight.w=aspect
  struct Inst { pr:vec4f, q:vec4f };                 // pos.xyz,scale | quaternion
  @group(0) @binding(0) var<uniform> u:U;
  @group(0) @binding(1) var<storage,read> insts:array<Inst>;
  @group(1) @binding(0) var tex:texture_2d<f32>;
  @group(1) @binding(1) var samp:sampler;
  @group(1) @binding(2) var emisTex:texture_2d<f32>;    // emissive glow (black when the art has none)
  @group(1) @binding(3) var specTex:texture_2d<f32>;    // specular intensity (black when none)
  @group(1) @binding(4) var normTex:texture_2d<f32>;    // tangent-space normal (flat 0,0,1 when none)
  fn qrot(q:vec4f,v:vec3f)->vec3f{ let t=2.0*cross(q.xyz,v); return v+q.w*t+cross(q.xyz,t); }
  struct VO { @builtin(position) pos:vec4f, @location(0) nrm:vec3f, @location(1) uv:vec2f, @location(2) wpos:vec3f, @location(3) tan:vec4f };
  @vertex fn vs(@location(0) inPos:vec3f, @location(1) inNrm:vec3f, @location(2) inUv:vec2f, @location(3) inTan:vec4f, @builtin(instance_index) ii:u32)->VO{
    let it=insts[ii];
    let world=it.pr.xyz + qrot(it.q, inPos*it.pr.w);
    var o:VO; o.pos=u.vp*vec4f(world,1.0); o.nrm=normalize(qrot(it.q, inNrm)); o.uv=inUv; o.wpos=world;
    o.tan=vec4f(qrot(it.q, inTan.xyz), inTan.w); return o;
  }
  @fragment fn fs(in:VO)->@location(0) vec4f{
    let Nn=normalize(in.nrm);                                          // TBN normal mapping
    let Tn=normalize(in.tan.xyz - Nn*dot(Nn,in.tan.xyz));
    let Bn=cross(Nn,Tn)*in.tan.w;
    let nm=textureSample(normTex,samp,in.uv).xyz*2.0-1.0;
    let n=normalize(Tn*nm.x + Bn*nm.y + Nn*nm.z);
    let L=normalize(vec3f(0.5,0.7,0.4)); let nl=max(dot(n,L),0.0);
    let fill=max(dot(n,normalize(vec3f(-0.4,-0.2,0.6))),0.0)*0.25;
    let alb=textureSample(tex,samp,in.uv).rgb;
    var col=alb*(0.22+nl*0.95+fill);                                        // diffuse: ambient + lambert key + fill
    let view=normalize(u.camPos.xyz-in.wpos); let hlf=normalize(L+view);    // Blinn-Phong spec, gated by the spec map
    col=col+vec3f(pow(max(dot(n,hlf),0.0),22.0)*textureSample(specTex,samp,in.uv).r*0.5);
    col=col+textureSample(emisTex,samp,in.uv).rgb*2.0;                      // emissive glow (unlit)
    return vec4f(pow(col, vec3f(1.0/2.2)), 1.0);
  }
  // ---- background (drawn behind, camera-relative) ----
  // The engine's own cube-cross skybox when the mission set one; otherwise a flat
  // neutral fill. This used to fall back to a procedural starfield - two hashed
  // point layers, the dense one at 320 cells per unit direction - which at a
  // distance read as static rather than as sky and was the brightest thing on
  // screen, so dark hulls and terrain art vanished into it. The real skyboxes
  // ship with the game, so use those; a backdrop the eye can ignore beats a fake
  // one it cannot. Deliberately off pure black: a dark hull on black has no
  // silhouette. Keep in step with client.html's _V3D_NO_SKY.
  const NO_SKY = vec3f(0.0824, 0.0902, 0.1059);   // 0x15171b
  fn hash13(p3in:vec3f)->f32{ var p3=fract(p3in*0.1031); p3=p3+dot(p3,p3.zyx+31.32); return fract((p3.x+p3.y)*p3.z); }
  struct VO2 { @builtin(position) pos:vec4f, @location(0) uv:vec2f };
  @vertex fn vbg(@builtin(vertex_index) vi:u32)->VO2{ var q=array<vec2f,3>(vec2f(-1,-1),vec2f(3,-1),vec2f(-1,3)); var o:VO2; o.pos=vec4f(q[vi],1.0,1.0); o.uv=q[vi]; return o; }
  @group(0) @binding(2) var skyTex: texture_2d<f32>;
  @group(0) @binding(3) var skySamp: sampler;
  fn rotuv(uv:vec2f, deg:f32)->vec2f{ let a=deg*0.017453293; let c=cos(a); let s=sin(a); let p=uv-0.5; return vec2f(p.x*c-p.y*s, p.x*s+p.y*c)+0.5; }
  fn skyboxUV(dir:vec3f)->vec2f{           // engine 4x3 cube cross (matches client.html _applySkyboxFaces)
    let ax=abs(dir.x); let ay=abs(dir.y); let az=abs(dir.z);
    var u=0.0; var v=0.0; var col=1.0; var row=1.0; var rot=0.0;
    if(ax>=ay && ax>=az){ if(dir.x>0.0){ u=-dir.z/ax; v=-dir.y/ax; col=2.0; row=1.0; rot=90.0; } else { u=dir.z/ax; v=-dir.y/ax; col=0.0; row=1.0; rot=270.0; } }
    else if(ay>=az){ if(dir.y>0.0){ u=dir.x/ay; v=dir.z/ay; col=1.0; row=1.0; rot=0.0; } else { u=dir.x/ay; v=-dir.z/ay; col=3.0; row=1.0; rot=180.0; } }
    else { if(dir.z>0.0){ u=dir.x/az; v=-dir.y/az; col=1.0; row=2.0; rot=0.0; } else { u=-dir.x/az; v=-dir.y/az; col=1.0; row=0.0; rot=180.0; } }
    var luv=rotuv(vec2f(u*0.5+0.5, v*0.5+0.5), -rot);
    luv=clamp(luv, vec2f(0.002), vec2f(0.998));
    return vec2f((col+luv.x)/4.0, (row+luv.y)/3.0);
  }
  @fragment fn fbg(in:VO2)->@location(0) vec4f{ let th=u.camDir.w; let aspect=u.camRight.w;
    let dir=normalize(u.camDir.xyz + u.camRight.xyz*(in.uv.x*th*aspect) + u.camUp.xyz*(in.uv.y*th));
    if(u.camUp.w>0.5){ return vec4f(textureSampleLevel(skyTex,skySamp,skyboxUV(dir),0.0).rgb, 1.0); }
    return vec4f(NO_SKY,1.0); }
  // ---- volumetric nebulae (procedural, additive; per-instance density/seed/swirl/warp) ----
  fn permute4n(x:vec4f)->vec4f{ return ((x*34.0+1.0)*x)%vec4f(289.0); }
  fn tinv4n(r:vec4f)->vec4f{ return 1.79284291400159-0.85373472095314*r; }
  fn snoisen(v:vec3f)->f32{
    let C=vec2f(1.0/6.0,1.0/3.0); let D=vec4f(0.0,0.5,1.0,2.0);
    var i=floor(v+dot(v,C.yyy)); let x0=v-i+dot(i,C.xxx);
    let gg=step(x0.yzx,x0.xyz); let l=1.0-gg; let i1=min(gg.xyz,l.zxy); let i2=max(gg.xyz,l.zxy);
    let x1=x0-i1+C.xxx; let x2=x0-i2+C.yyy; let x3=x0-D.yyy; i=i%vec3f(289.0);
    let p=permute4n(permute4n(permute4n(i.z+vec4f(0.0,i1.z,i2.z,1.0))+i.y+vec4f(0.0,i1.y,i2.y,1.0))+i.x+vec4f(0.0,i1.x,i2.x,1.0));
    let n_=1.0/7.0; let ns=n_*D.wyz-D.xzx;
    let j=p-49.0*floor(p*ns.z*ns.z); let x_=floor(j*ns.z); let y_=floor(j-7.0*x_);
    let px=x_*ns.x+ns.yyyy; let py=y_*ns.x+ns.yyyy; let hh=1.0-abs(px)-abs(py);
    let b0=vec4f(px.xy,py.xy); let b1=vec4f(px.zw,py.zw);
    let s0=floor(b0)*2.0+1.0; let s1=floor(b1)*2.0+1.0; let sh=-step(hh,vec4f(0.0));
    let a0=b0.xzyw+s0.xzyw*sh.xxyy; let a1=b1.xzyw+s1.xzyw*sh.zzww;
    var g0=vec3f(a0.xy,hh.x); var g1=vec3f(a0.zw,hh.y); var g2=vec3f(a1.xy,hh.z); var g3=vec3f(a1.zw,hh.w);
    let nr=tinv4n(vec4f(dot(g0,g0),dot(g1,g1),dot(g2,g2),dot(g3,g3)));
    g0=g0*nr.x; g1=g1*nr.y; g2=g2*nr.z; g3=g3*nr.w;
    var m=max(0.6-vec4f(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),vec4f(0.0)); m=m*m;
    return 42.0*dot(m*m,vec4f(dot(g0,x0),dot(g1,x1),dot(g2,x2),dot(g3,x3)));
  }
  fn spiral(pin:vec3f)->f32{ var p=pin; var n=0.0; var it=1.0; for(var i=0;i<6;i=i+1){ n=n-abs(sin(p.y*it)+cos(p.x*it))/it; let a=(p.xy+vec2f(p.y,-p.x)*0.739513)*0.80406839; p=vec3f(a.x,a.y,p.z); let b=(p.xz+vec2f(p.z,-p.x)*0.739513)*0.80406839; p=vec3f(b.x,p.y,b.y); it=it*1.733733; } return n; }
  fn rotY(p:vec3f,s:f32)->vec3f{ let c=cos(s); let si=sin(s); return vec3f(p.x*c+p.z*si,p.y,-p.x*si+p.z*c); }
  // Faithful port of the Nebula-tab sampleVolume (engine-matched). posIn is normalized to [-1,1].
  // Per-color freq/amp vary in the tab; this bakes the default preset + shared structural constants
  // (numOct=3, detailFreq 1.3055, detailLac 2.43) since the Neb struct carries no room for them.
  fn nebDensity(posIn:vec3f, density:f32, seed:f32, swirl:f32, warp:f32, cover:f32, baseFreq:f32, baseAmp:f32, detailFreq:f32, detailAmp:f32)->f32{
    let detailLac=2.43;   // shared by all 7 color presets; baseFreq/baseAmp/detailFreq/detailAmp are per-color (passed in)
    var pos=posIn; let rr=length(pos); let f=exp(-rr); let ff=f*f; var p=ff*density;
    if(p<=cover*density){ return -1.0; }   // cover = base cutoff; lower cutoff -> cloud fills more of the sphere radius
    p=p+spiral(vec3f(512.0+seed)+pos*(8.0*baseFreq))*0.75*baseAmp;
    if(swirl!=0.0){ pos=rotY(pos, pos.y*spiral(pos*4.0)*swirl); }
    p=p+spiral(vec3f(200.0+seed)+pos*(3.0*detailLac))*1.5*baseAmp/detailLac;
    pos=pos+abs(snoisen(pos*4.0))*warp;
    if(p>0.0){
      p=p*ff;
      if(p<0.15*density){
        p=p-abs(snoisen(vec3f(seed)+pos*(8.0*detailFreq)))*2.0*detailAmp;
        p=p-abs(snoisen(vec3f(seed)+pos*(16.0*detailFreq)))*1.0*detailAmp;
        if(p>0.1){ p=p+abs(snoisen(vec3f(seed)+pos*(32.0*detailFreq)))*0.25*detailAmp; }
      }
    }
    return p;
  }
  struct Neb { c:vec4f, col:vec4f, sd:vec4f };   // c=center.xyz,radius  col=emis.rgb,density  sd=seed,swirl,warp,variety
  @group(0) @binding(4) var<storage,read> nebs:array<Neb>;
  @group(0) @binding(5) var densTex:texture_3d<f32>;                 // OPTIMIZED path: resident baked density pool
  @group(0) @binding(6) var densSamp:sampler;
  struct NebU { cfg:vec4f, cfg2:vec4f };   // cfg=baked,steps,K,realCount ; cfg2=stepMode(0 count/1 size),stepFrac,-,-
  @group(0) @binding(7) var<uniform> nebU:NebU;
  // ---- bake pass: evaluate nebDensity once per resident SLAB (one Z-slab per template) ----
  struct BakeU { cfg:vec4f };   // cfg.x=RES cfg.y=slabCount(P)
  @group(0) @binding(8) var<uniform> bp:BakeU;
  @group(0) @binding(9) var densOut:texture_storage_3d<rgba16float,write>;
  @group(0) @binding(10) var<storage,read> slotPar:array<vec4f>;   // per-slab (seed,swirl,warp,density)
  @compute @workgroup_size(4,4,4) fn bakeDensity(@builtin(global_invocation_id) gid:vec3u){
    let RES=i32(bp.cfg.x+0.5); let P=i32(bp.cfg.y+0.5);
    if(i32(gid.x)>=RES || i32(gid.y)>=RES || i32(gid.z)>=RES*P){ return; }
    let v=i32(gid.z)/RES; let lz=i32(gid.z)-v*RES;
    let uvw=(vec3f(f32(gid.x),f32(gid.y),f32(lz))+0.5)/f32(RES);
    let pos=uvw*2.0-1.0;
    let vp=slotPar[v*2]; let vp2=slotPar[v*2+1];   // vp=seed,swirl,warp,density ; vp2=baseFreq,baseAmp,detailFreq,detailAmp (per color)
    textureStore(densOut, vec3i(gid), vec4f(nebDensity(pos, vp.w, vp.x, vp.y, vp.z, bp.cfg.z, vp2.x, vp2.y, vp2.z, vp2.w), 0.0, 0.0, 0.0));
  }
  fn sampleBaked(nrm:vec3f, variety:i32, K:i32)->f32{
    let uvw=clamp(nrm*0.5+0.5, vec3f(0.0), vec3f(1.0));
    let zc=clamp(uvw.z, 0.01, 0.99);                     // guard vs linear bleed across stacked varieties
    return textureSampleLevel(densTex, densSamp, vec3f(uvw.x, uvw.y, (f32(variety)+zc)/f32(K)), 0.0).r;
  }
  fn nebOffset(copy:u32, radius:f32)->vec3f{             // spread stress-test copies so they don't stack
    if(copy==0u){ return vec3f(0.0); }
    let h=f32(copy)*vec3f(12.9,78.2,37.7);
    return vec3f(sin(h.x),sin(h.y),sin(h.z))*radius*6.0;
  }
  struct NVO { @builtin(position) pos:vec4f, @location(0) @interpolate(flat) inst:u32, @location(1) rd:vec3f };
  @vertex fn nvs(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->NVO{
    let real=u32(max(nebU.cfg.w,1.0)); let ri=ii%real; let copy=ii/real;
    let nb=nebs[ri]; let radius=nb.c.w; let center=nb.c.xyz+nebOffset(copy,radius);
    let rel=center-u.camPos.xyz; let vz=dot(rel,u.camDir.xyz); let vx=dot(rel,u.camRight.xyz); let vy=dot(rel,u.camUp.xyz);
    var o:NVO; o.inst=ii;
    if(vz<=0.05){ o.pos=vec4f(0.0,0.0,-2.0,1.0); o.rd=u.camDir.xyz; return o; }
    let th=u.camDir.w; let aspect=u.camRight.w;
    let ndcx=vx/(vz*th*aspect); let ndcy=vy/(vz*th); let rx=(radius*1.5)/(vz*th*aspect); let ry=(radius*1.5)/(vz*th);
    var q=array<vec2f,6>(vec2f(-1,-1),vec2f(1,-1),vec2f(-1,1),vec2f(-1,1),vec2f(1,-1),vec2f(1,1));
    let cn=q[vi]; let ndc=vec2f(ndcx+cn.x*rx, ndcy+cn.y*ry);
    let clip=u.vp*vec4f(center,1.0);
    o.pos=vec4f(ndc, clip.z/clip.w, 1.0);
    o.rd=normalize(u.camDir.xyz + u.camRight.xyz*(ndc.x*th*aspect) + u.camUp.xyz*(ndc.y*th));
    return o;
  }
  @fragment fn nfs(in:NVO)->@location(0) vec4f{
    let real=u32(max(nebU.cfg.w,1.0)); let ri=in.inst%real; let copy=in.inst/real;
    let nb=nebs[ri]; let R=nb.c.w; let cen=nb.c.xyz+nebOffset(copy,R); let rd=normalize(in.rd);
    let ro=u.camPos.xyz-cen; let bb=dot(rd,ro); let cc=dot(ro,ro)-(R*1.2)*(R*1.2); let disc=bb*bb-cc;  // march past R so the fuller cloud fades softly instead of hard-clipping at the sphere
    if(disc<0.0){ return vec4f(0.0); }
    let sq=sqrt(disc); let t0=max(-bb-sq,0.0); let t1=-bb+sq; if(t1<=t0){ return vec4f(0.0); }
    let STEPS=i32(max(nebU.cfg.y,1.0));
    // count mode = fixed step COUNT across the sphere (fine); size mode = fixed step SIZE (field-style, ~11 steps, coarse)
    let dS=select((t1-t0)/f32(STEPS), max(nebU.cfg2.y,0.02)*R, nebU.cfg2.x>0.5);
    let emis=nb.col.rgb; let density=nb.col.w; let seed=nb.sd.x;
    let baked=nebU.cfg.x>0.5; let P=i32(max(nebU.cfg.z,1.0)); let share=nebU.cfg2.z>0.5;
    let variety=select(i32(ri)%P, i32(nb.sd.w+0.5), share);   // shared=K templates by seed ; unique=own slab
    let ang=seed*1.7;   // per-instance spin so same-template baked clouds don't read as clones
    let jit=fract(sin(dot(in.pos.xy,vec2f(12.9898,78.233)))*43758.5453);  // per-pixel offset breaks step banding
    var t=t0+jit*dS; var trans=1.0; var acc=vec3f(0.0);
    for(var i=0;i<STEPS;i=i+1){
      if(t>=t1){ break; }                            // size mode exits the sphere early (fewer steps)
      let n=(ro+rd*t)/R;
      var d:f32;
      if(baked){ d=sampleBaked(rotY(n,ang), variety, P); } else { d=nebDensity(n, density, seed, nb.sd.y, nb.sd.z, nebU.cfg2.w, 1.4, 1.87, 1.3055, 1.6); }  // live-debug uses default preset; baked path is true per-color
      if(d>0.02){ acc=acc+emis*d*trans*(dS/R)*0.5; trans=trans*exp(-d*dS/R*3.0); if(trans<0.02){ break; } }  // emission ∝ path so brightness holds across step modes
      t=t+dS; }
    return vec4f(acc, 0.0);
  }
  // ---- camera-facing billboard sized to a world sphere (shared by the planet + black-hole passes) ----
  // Same construction as the nebula quad: project the center, expand by the radius in NDC, and
  // hand the fragment a per-pixel ray so the body itself is intersected analytically.
  struct BB { ndc:vec2f, rd:vec3f, z:f32, ok:f32 };
  fn billboard(center:vec3f, R:f32, vi:u32)->BB{
    var o:BB; o.ndc=vec2f(0.0); o.rd=u.camDir.xyz; o.z=0.5; o.ok=0.0;
    let rel=center-u.camPos.xyz; let vz=dot(rel,u.camDir.xyz);
    if(vz<=0.05){ return o; }                       // center behind the camera
    let vx=dot(rel,u.camRight.xyz); let vy=dot(rel,u.camUp.xyz);
    let th=u.camDir.w; let aspect=u.camRight.w;
    let ndcx=vx/(vz*th*aspect); let ndcy=vy/(vz*th); let rx=R/(vz*th*aspect); let ry=R/(vz*th);
    var q=array<vec2f,6>(vec2f(-1,-1),vec2f(1,-1),vec2f(-1,1),vec2f(-1,1),vec2f(1,-1),vec2f(1,1));
    let cn=q[vi]; let ndc=vec2f(ndcx+cn.x*rx, ndcy+cn.y*ry);
    let clip=u.vp*vec4f(center,1.0);
    o.ndc=ndc; o.z=clamp(clip.z/clip.w, 0.0, 0.999999); o.ok=1.0;
    o.rd=normalize(u.camDir.xyz + u.camRight.xyz*(ndc.x*th*aspect) + u.camUp.xyz*(ndc.y*th));
    return o;
  }
  struct BodyVO { @builtin(position) pos:vec4f, @location(0) @interpolate(flat) inst:u32, @location(1) rd:vec3f };
  struct BodyFO { @location(0) col:vec4f, @builtin(frag_depth) depth:f32 };   // real per-pixel depth: ships pass in front of / behind the body
  // ---- gas-giant planets (analytic surface — there is no planet mesh) ----
  // A planet is spawned as terrain_spawn(..., "planet", "behav_planet") and has NO shipData
  // entry, so it has no artfileroot and no OBJ; the engine draws it with shader-gasgiant.ps.
  // This is a port of that shader's renderSurface(), fed by the same planet_* data_set levers
  // the mock streams (see _planet_info). iTime/timeScale are hardcoded to 1 in the engine (the
  // animation is disabled), so windSpeed1/2 act as fixed per-planet offsets and the surface is
  // STATIC — matching what the engine actually draws, not the tunable studio tab.
  struct Planet { c:vec4f, base:vec4f, emis:vec4f, cloud:vec4f, atm:vec4f };
  // c=center.xyz,radius | base=baseColor.rgb,bandScale | emis=emissive.rgb,cloudStrength
  // cloud=cloudColor.rgb,cloudExponent | atm=fresnelPow,fresnelBias,windSpeed1,windSpeed2
  @group(0) @binding(11) var<storage,read> planets:array<Planet>;
  fn ridgedn(p:vec3f, freq:f32, amp:f32)->f32{ return ((1.0-abs(snoisen(p*freq)))*2.0-1.0)*amp; }
  fn renderGas(pl:Planet, N:vec3f, vd:vec3f, h:f32)->vec4f{
    let cBase=pl.base.rgb; let bandScale=pl.base.w;
    let cEmis=pl.emis.rgb;  let cStr=pl.emis.w;
    let cCloud=pl.cloud.rgb; let cExp=pl.cloud.w;
    let fPow=pl.atm.x; let fBias=pl.atm.y; let ws1=pl.atm.z; let ws2=pl.atm.w;
    let fade=0.0;   // engine: min(0.5, max(1-dist/24,0)) with dist in WORLD units -> always 0
    // Per-planet LONGITUDE rotation seeded from the colors, so two planets sharing the shader
    // don't share a face (the engine's GG_SEED_FROM_EXPONENT trick; the band seed below is the
    // other half of it).
    let pa=dot(cBase+cEmis, vec3f(9.7,6.3,4.1)); let pc=cos(pa); let ps=sin(pa);
    let wn=vec3f(N.x*pc-N.z*ps, N.y, N.x*ps+N.z*pc);
    var seed=wn; seed.x=seed.x+ws1;
    let n1=ridgedn(seed,12.0,1.0);
    let n2=snoisen(seed*24.0)+n1;
    let n3=snoisen(seed*64.0)+n2;
    let n4=min(0.25, ridgedn(seed,16.0,n3)-n3);
    var offset=mix(n1+n2, n4, fade);
    seed=wn*(-0.5); seed.x=seed.x+ws2;                       // contra-rotating band layer
    let n12=ridgedn(seed,12.0,1.0);
    let n22=snoisen(seed*24.0);
    let n32=snoisen(seed*64.0);
    let n42=ridgedn(seed,32.0,n32);
    offset=offset+mix(n12+n22, n42, fade)*0.9;
    offset=offset*(1.0-cos(h*4.0)*0.7);                      // modulate the bands by latitude
    let uu=abs(h*bandScale + offset/150.0);
    var texCol=cBase*smoothstep(-1.0,2.0, 0.2+abs(snoisen(vec3f(cExp*0.7,(16.0+wn.y)*uu,0.0))));
    let cloudScale=10.0/max(pl.c.w,1.0);
    let skewed=vec3f(wn.x, wn.y*3.0+ws1, wn.z);
    let uCloud=clamp(max(snoisen(N*2.0)+snoisen(skewed*cloudScale)+snoisen(skewed*8.0)+snoisen(skewed*32.0)+n4, 0.0)*cStr, 0.0, 1.0);
    texCol=mix(texCol, cCloud, pow(uCloud, cExp));
    let L=normalize(vec3f(0.5,0.7,0.4));                     // same key light as the mesh pass
    let NdotL=clamp(dot(N,L),0.0,1.0);
    var col=texCol*NdotL+cEmis;
    let fres=clamp(fBias+40.0*pow(max(1.0+dot(vd,N),0.0), fPow), 0.0, 1.0);   // fresnel atmosphere rim
    col=vec3f(col.r*(1.0-fres*1.44), col.g*(1.0-fres*0.9), col.b*(1.0-fres*0.7));
    col=col+(vec3f(fres)+cEmis)*NdotL;
    return vec4f(col, smoothstep(0.0,0.5, smoothstep(0.0,0.9,1.0-fres)));
  }
  @vertex fn pvs(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->BodyVO{
    let pl=planets[ii]; let bb=billboard(pl.c.xyz, pl.c.w*1.08, vi);   // 8% margin for the atmosphere rim
    var o:BodyVO; o.inst=ii; o.rd=bb.rd;
    o.pos=select(vec4f(0.0,0.0,-2.0,1.0), vec4f(bb.ndc, bb.z, 1.0), bb.ok>0.5);
    return o;
  }
  @fragment fn pfs(in:BodyVO)->BodyFO{
    let pl=planets[in.inst]; let R=pl.c.w; let cen=pl.c.xyz; let rd=normalize(in.rd);
    let ro=u.camPos.xyz-cen; let b=dot(rd,ro); let cq=dot(ro,ro)-R*R; let disc=b*b-cq;
    if(disc<0.0){ discard; }                                 // ray misses the body
    let t=-b-sqrt(max(disc,0.0));                            // max(): discard doesn't stop execution in WGSL
    if(t<=0.0){ discard; }                                   // behind the camera / camera inside
    let hit=u.camPos.xyz+rd*t; let N=normalize(hit-cen);
    var col:vec4f;
    // Skip the ~13 noise evals on the unlit hemisphere (they are multiplied by NdotL~0 anyway);
    // the night side is the planet's EMISSIVE color, opaque so it still occludes. Engine parity.
    if(dot(normalize(vec3f(0.5,0.7,0.4)),N) > -0.05){ col=renderGas(pl,N,rd,N.y); }
    else { col=vec4f(pl.emis.rgb, 1.0); }
    let clip=u.vp*vec4f(hit,1.0);
    var o:BodyFO; o.col=vec4f(pow(max(col.rgb,vec3f(0.0)), vec3f(1.0/2.2)), clamp(col.a,0.0,1.0));
    o.depth=clamp(clip.z/clip.w, 0.0, 1.0); return o;
  }
  // ---- black holes (maelstrom): event horizon + accretion disc ----
  // The engine has NO maelstrom shader (the 18 DX11PAXShader* classes have no black hole, and
  // the only "maelstrom" string in the binary sits in Render2D.cpp next to icon-blackhole), so
  // there is nothing to port wholesale. What IS ported is the SHADING: shader-point-ring.ps
  //     percent    = abs(dist(worldPos, centerPoint) - distCenter) / distRadius
  //     finalColor = saturate(ambientColor * texture * (1 - percent))
  // i.e. a radial band that peaks at the mid-radius between minMaxDistance.x/.y and fades to
  // nothing at both edges — an annulus glow around a center point, which is exactly the shape
  // a gravity well wants. min/max map to the two radii a maelstrom actually has: the event
  // horizon (exclusion_radius) and the gravity radius.
  // GUESSED, because the engine keeps it internal: the GEOMETRY (a flat disc in the object's
  // y-plane — the reading that matches disk.obj / gas-ring.png / starRing1.png), the texture
  // (taken as 1.0, none), and the tint when the mission sets no radar_color_override.
  struct Hole { c:vec4f, g:vec4f };   // c=center.xyz,horizonR(min) | g=gravityR(max),tint.rgb
  @group(0) @binding(12) var<storage,read> holes:array<Hole>;
  @vertex fn hvs(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->BodyVO{
    let hl=holes[ii]; let bb=billboard(hl.c.xyz, hl.g.x*1.02, vi);   // gravity radius bounds the whole disc
    var o:BodyVO; o.inst=ii; o.rd=bb.rd;
    o.pos=select(vec4f(0.0,0.0,-2.0,1.0), vec4f(bb.ndc, bb.z, 1.0), bb.ok>0.5);
    return o;
  }
  @fragment fn hfs(in:BodyVO)->BodyFO{
    let hl=holes[in.inst]; let cen=hl.c.xyz; let Rh=max(hl.c.w,1.0); let Rg=max(hl.g.x,Rh*2.0);
    let rd=normalize(in.rd); let ro=u.camPos.xyz-cen; let b=dot(rd,ro);
    var o:BodyFO;
    // Event horizon: an opaque black sphere. Nothing in the engine says how (or whether) this
    // draws in 3D; a black disc is the least-invented way to show the object is THERE.
    let dsc=b*b-(dot(ro,ro)-Rh*Rh); let th=-b-sqrt(max(dsc,0.0));
    if(dsc>=0.0 && th>0.0){
      let clip=u.vp*vec4f(u.camPos.xyz+rd*th, 1.0);
      o.col=vec4f(0.0,0.0,0.0,1.0); o.depth=clamp(clip.z/clip.w,0.0,1.0); return o;
    }
    // Accretion disc: hit the object's y-plane, then shade by point-ring's radial band.
    if(abs(rd.y)<1e-6){ discard; }                       // ray parallel to the disc (edge-on)
    let tp=(cen.y-u.camPos.y)/rd.y;
    if(tp<=0.0){ discard; }                              // plane is behind the camera
    let hit=u.camPos.xyz+rd*tp; let d=length(hit-cen);
    if(d<Rh || d>Rg){ discard; }                         // outside minMaxDistance -> percent>1 -> black
    let distCenter=(Rg+Rh)*0.5; let distRadius=(Rg-Rh)*0.5;
    let percent=abs(d-distCenter)/distRadius;
    let lit=clamp(1.0-percent, 0.0, 1.0);                // saturate(ambient * tex * (1-percent))
    let clip=u.vp*vec4f(hit,1.0);
    o.col=vec4f(pow(hl.g.yzw*lit, vec3f(1.0/2.2)), lit); // engine multiplies alpha by the same term
    o.depth=clamp(clip.z/clip.w, 0.0, 1.0); return o;
  }
  // ---- reference grid on the y=0 plane (camera-centered, distance-faded) ----
  struct GVO { @builtin(position) pos:vec4f, @location(0) wxz:vec2f };
  @vertex fn vgrid(@builtin(vertex_index) vi:u32)->GVO{
    var q=array<vec2f,6>(vec2f(-1,-1),vec2f(1,-1),vec2f(-1,1),vec2f(-1,1),vec2f(1,-1),vec2f(1,1));
    let S=250000.0; let wx=u.camPos.x+q[vi].x*S; let wz=u.camPos.z+q[vi].y*S;
    var o:GVO; o.pos=u.vp*vec4f(wx,0.0,wz,1.0); o.wxz=vec2f(wx,wz); return o;
  }
  @fragment fn fgrid(in:GVO)->@location(0) vec4f{
    let cell=5000.0; let uv=in.wxz/cell; let gr=abs(fract(uv-0.5)-0.5)/fwidth(uv);
    let line=1.0-min(min(gr.x,gr.y),1.0);
    let d=length(in.wxz-u.camPos.xz); let fade=clamp(1.0-d/240000.0,0.0,1.0);
    return vec4f(vec3f(0.12,0.34,0.48), line*0.35*fade);
  }
  // ---- flat rings (own-ship highlight + shield-fraction rings) ----
  struct Ring { c:vec4f, col:vec4f, e:vec4f };     // center.xyz,radius | rgb,alpha | thickness,arcCenter,arcHalf,-
  @group(0) @binding(5) var<storage,read> rings:array<Ring>;
  struct RVO { @builtin(position) pos:vec4f, @location(0) col:vec3f, @location(1) @interpolate(flat) a:f32, @location(2) ang:f32, @location(3) @interpolate(flat) ac:f32, @location(4) @interpolate(flat) ah:f32 };
  @vertex fn vring(@location(0) rp:vec2f, @builtin(instance_index) ii:u32)->RVO{
    let rg=rings[ii]; let rl=max(length(rp),1e-4); let nl=1.0-((1.0-rl)/0.05)*rg.e.x;   // remap the base 5% band to this ring's thickness
    let world=rg.c.xyz + vec3f(rp.x/rl,0.0,rp.y/rl)*nl*rg.c.w;
    var o:RVO; o.pos=u.vp*vec4f(world,1.0); o.col=rg.col.rgb; o.a=rg.col.w;
    o.ang=atan2(rp.y,rp.x); o.ac=rg.e.y; o.ah=rg.e.z; return o;   // vertex angle + arc (front/aft half rings)
  }
  @fragment fn fring(in:RVO)->@location(0) vec4f{
    let dif=abs(atan2(sin(in.ang-in.ac), cos(in.ang-in.ac)));   // wrapped angular distance from the arc center
    if(dif>in.ah){ discard; }                                   // outside this ring's arc (aft/front half) -> skip
    return vec4f(in.col, in.a);
  }
  // ---- combat FX: sustained glowing beam pipe + skittering hull-impact glow + missile/projectile bloom (additive) ----
  @group(0) @binding(6) var<storage,read> beams:array<vec4f>;    // stride 3: [x1,z1,x2,z2] , [life,y1,y2,_] , [r,g,b,_]
  @group(0) @binding(7) var<storage,read> projs:array<vec4f>;    // x,y,z,kind
  struct BVO { @builtin(position) pos:vec4f, @location(0) across:f32, @location(1) alng:f32, @location(2) @interpolate(flat) life:f32, @location(3) @interpolate(flat) col:vec3f };
  @vertex fn vbeam(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->BVO{
    let bm=beams[ii*3u]; let ex=beams[ii*3u+1u]; let cl=beams[ii*3u+2u].xyz;   // ex.y/ex.z = firer/target altitude; cl = shipData beam color
    let A=vec3f(bm.x,ex.y,bm.y); let B=vec3f(bm.z,ex.z,bm.w); let life=ex.x;
    var q=array<vec2f,6>(vec2f(0.0,-1.0),vec2f(1.0,-1.0),vec2f(0.0,1.0),vec2f(0.0,1.0),vec2f(1.0,-1.0),vec2f(1.0,1.0));
    let cv=q[vi]; let P=mix(A,B,cv.x); let dir=normalize(B-A+vec3f(0.0001,0.0,0.0));
    let toCam=normalize(u.camPos.xyz-P); let side=normalize(cross(dir,toCam)); let t=u.camPos.w;
    let sh=(sin(cv.x*36.0+t*16.0)*0.5+0.5)*0.06;             // barely-there shimmer -> a steady solid pipe
    let world=P+side*(cv.y*12.0*(1.0+sh));                    // very thin beam
    var o:BVO; o.pos=u.vp*vec4f(world,1.0); o.across=cv.y; o.alng=cv.x; o.life=life; o.col=cl; return o;
  }
  @fragment fn fbeam(in:BVO)->@location(0) vec4f{
    let halo=pow(1.0-abs(in.across),2.2);                    // colored outer glow
    let hot=pow(1.0-abs(in.across),13.0);                    // white-hot center line
    let ends=1.0-pow(abs(in.alng*2.0-1.0),8.0);
    let col=in.col*halo*1.7 + vec3f(1.0)*hot*1.4;            // glowing phaser pipe, tinted by the ship's beam color
    return vec4f(col*ends*clamp(in.life,0.0,1.0), 0.0);
  }
  // impact at the target end: a soft HULL GLOW disc + sparks that skitter from point to point across the hull
  struct IVO { @builtin(position) pos:vec4f, @location(0) uv:vec2f, @location(1) @interpolate(flat) k:f32, @location(2) @interpolate(flat) life:f32, @location(3) @interpolate(flat) col:vec3f };
  @vertex fn vimp(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->IVO{
    let bm=beams[ii*3u]; let ex=beams[ii*3u+1u]; let cl=beams[ii*3u+2u].xyz; let B=vec3f(bm.z,ex.z,bm.w); let life=ex.x;   // impact at the target's altitude, beam color
    let quad=vi/6u; let corner=vi%6u; let t=u.camPos.w;
    var q=array<vec2f,6>(vec2f(-1.0,-1.0),vec2f(1.0,-1.0),vec2f(-1.0,1.0),vec2f(-1.0,1.0),vec2f(1.0,-1.0),vec2f(1.0,1.0));
    let uv=q[corner];
    var center=B; var rad=130.0;
    if(quad>0u){                                             // spark: jump to a new hull point every ~0.08s
      let seed=floor(t/0.08)+f32(quad)*17.0;
      let a=hash13(vec3f(seed,seed*1.7,3.0))*6.2832; let rr=hash13(vec3f(seed*2.3,5.0,seed))*72.0;
      center=B + u.camRight.xyz*(cos(a)*rr) + u.camUp.xyz*(sin(a)*rr); rad=22.0;
    }
    let world=center + u.camRight.xyz*(uv.x*rad) + u.camUp.xyz*(uv.y*rad);
    var o:IVO; o.pos=u.vp*vec4f(world,1.0); o.uv=uv; o.k=f32(quad); o.life=life; o.col=cl; return o;
  }
  @fragment fn fimp(in:IVO)->@location(0) vec4f{
    let d=length(in.uv); let la=clamp(in.life,0.0,1.0); let t=u.camPos.w;
    if(in.k<0.5){                                            // hull glow: soft, pulsing, beam-colored
      let g=smoothstep(1.0,0.0,d);
      return vec4f(in.col*g*g*0.85*(0.6+0.4*sin(t*11.0))*la, 0.0);
    }
    let glow=smoothstep(1.0,0.0,d); let core=smoothstep(0.5,0.0,d);   // spark: beam color + white-hot, flickering
    return vec4f((in.col*glow*1.0 + vec3f(1.0)*core*1.6)*(0.7+0.3*sin(t*60.0+in.k*11.0))*la, 0.0);
  }
  struct PVO2 { @builtin(position) pos:vec4f, @location(0) uv:vec2f, @location(1) @interpolate(flat) kind:f32, @location(2) @interpolate(flat) missile:f32 };
  @vertex fn vproj(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->PVO2{
    let pr=projs[ii*2u]; let dv=projs[ii*2u+1u];   // stride 2: [x,y,z,kind] , [dirx,dirz,_,_]
    var q=array<vec2f,6>(vec2f(-1.0,-1.0),vec2f(1.0,-1.0),vec2f(-1.0,1.0),vec2f(-1.0,1.0),vec2f(1.0,-1.0),vec2f(1.0,1.0));
    let al=q[vi].x; let ac=q[vi].y; let pos=pr.xyz; let toCam=normalize(u.camPos.xyz-pos);
    let dir2=vec3f(dv.x,0.0,dv.y); let dl=length(dir2);
    var world:vec3f; var mis:f32;
    if(dl>0.01 && pr.w<0.5){                        // warhead with a heading -> oriented missile (drones stay round)
      let axis=dir2/dl; let wside=normalize(cross(axis,toCam));
      // Constant half-width. The taper lives in fproj (wac = 1-|uv.y| shapes the body, and
      // the plume fades with smoothstep on uv.x) - doing it here as well collapsed the quad:
      // its vertices only exist at al=+-1, and the old profile term evaluated to 0 at BOTH
      // ends, so every corner had zero width, the triangles degenerated to a line and nothing
      // rasterised. Torpedoes were invisible while drones (which take the round-bloom branch
      // below) drew fine - the reported "green orbs but never an orange one".
      world=pos + axis*(al*60.0) + wside*(ac*16.0); mis=1.0;
    } else {
      world=pos + u.camRight.xyz*(al*55.0) + u.camUp.xyz*(ac*55.0); mis=0.0;   // round bloom (drone / no heading)
    }
    var o:PVO2; o.pos=u.vp*vec4f(world,1.0); o.uv=vec2f(al,ac); o.kind=pr.w; o.missile=mis; return o;
  }
  @fragment fn fproj(in:PVO2)->@location(0) vec4f{
    if(in.missile>0.5){
      let al=in.uv.x; let wac=1.0-abs(in.uv.y);
      if(al>=-0.15){                               // warhead body: orange-red with a hot nose
        return vec4f(vec3f(1.0,0.5,0.18)*pow(wac,1.4)*1.7 + vec3f(1.0,0.95,0.85)*pow(wac,5.0)*0.8, 0.0);
      }
      let flick=0.65+0.35*sin(u.camPos.w*45.0+al*22.0);   // flame flicker
      let plume=pow(wac,1.1)*smoothstep(-1.0,-0.15,al);   // brightest at the nozzle, fades down the tail
      return vec4f(vec3f(1.0,0.82,0.4)*plume*flick*1.5, 0.0);   // exhaust: yellow-white (distinct from the body)
    }
    let d=length(in.uv); let glow=smoothstep(1.0,0.0,d); let core=smoothstep(0.35,0.0,d);
    let col=select(vec3f(1.0,0.604,0.235), vec3f(0.486,0.988,0.0), in.kind>0.5);   // missile 0xff9a3c / drone 0x7CFC00
    return vec4f((col*glow*glow*1.8 + vec3f(1.0)*core*1.2), 0.0);
  }
  // ---- engine exhaust smoke: soft additive puffs, speed-driven (built on the CPU per ship) ----
  @group(0) @binding(8) var<storage,read> smoke:array<vec4f>;    // [pos.xyz,size],[alpha,_,_,_] per puff (stride 2)
  struct SVO { @builtin(position) pos:vec4f, @location(0) uv:vec2f, @location(1) @interpolate(flat) a:f32 };
  @vertex fn vsmoke(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->SVO{
    let ps=smoke[ii*2u]; let ex=smoke[ii*2u+1u];
    var q=array<vec2f,6>(vec2f(-1.0,-1.0),vec2f(1.0,-1.0),vec2f(-1.0,1.0),vec2f(-1.0,1.0),vec2f(1.0,-1.0),vec2f(1.0,1.0));
    let world=ps.xyz + u.camRight.xyz*(q[vi].x*ps.w) + u.camUp.xyz*(q[vi].y*ps.w);
    var o:SVO; o.pos=u.vp*vec4f(world,1.0); o.uv=q[vi]; o.a=ex.x; return o;
  }
  @fragment fn fsmoke(in:SVO)->@location(0) vec4f{
    let d=length(in.uv); let soft=smoothstep(1.0,0.0,d);
    return vec4f(vec3f(0.34,0.56,1.0)*soft*in.a*1.15, 0.0);   // richer ion-exhaust blue
  }`;
  const mod=device.createShaderModule({code:WGSL});
  const info=await mod.getCompilationInfo(); const es=info.messages.filter(m=>m.type==="error");
  if(es.length){ wlog("WGSL: "+es.map(x=>`[${x.lineNum}] ${x.message}`).join(" | ")); return; }   // WGSL failed -> bail BEFORE taking over, so WebGL keeps rendering (no black screen)
  window.__webgpu3dview=true;   // WGSL compiled OK -> take over the 3dview; client.html's _renderView3d now no-ops
  const ubuf=device.createBuffer({size:8*16, usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  const samp=device.createSampler({magFilter:"linear",minFilter:"linear",addressModeU:"repeat",addressModeV:"repeat"});
  const pipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"vs", buffers:[{arrayStride:48, attributes:[
      {shaderLocation:0,offset:0,format:"float32x3"},{shaderLocation:1,offset:12,format:"float32x3"},{shaderLocation:2,offset:24,format:"float32x2"},{shaderLocation:3,offset:32,format:"float32x4"}]}]},
    fragment:{module:mod,entryPoint:"fs",targets:[{format}]}, primitive:{topology:"triangle-list",cullMode:"none"},
    depthStencil:{format:"depth24plus",depthWriteEnabled:true,depthCompare:"less"}});
  const bgPipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"vbg"}, fragment:{module:mod,entryPoint:"fbg",targets:[{format}]}, primitive:{topology:"triangle-list"},
    depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"always"}});
  const nebPipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"nvs"}, fragment:{module:mod,entryPoint:"nfs",targets:[{format, blend:{color:{srcFactor:"one",dstFactor:"one",operation:"add"},alpha:{srcFactor:"one",dstFactor:"one",operation:"add"}}}]},
    primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  let nebBuf=null, nebCap=0;
  // Planets / black holes: analytic bodies, opaque with real per-pixel depth (a ship can pass
  // in front of or behind one), alpha-blended so the planet's fresnel atmosphere rim fades out.
  const ALPHA_BLEND={color:{srcFactor:"src-alpha",dstFactor:"one-minus-src-alpha",operation:"add"},alpha:{srcFactor:"one",dstFactor:"one-minus-src-alpha",operation:"add"}};
  const planetPipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"pvs"}, fragment:{module:mod,entryPoint:"pfs",targets:[{format, blend:ALPHA_BLEND}]},
    primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:true,depthCompare:"less"}});
  // The black hole does NOT write depth: most of its area is the semi-transparent accretion
  // disc, and a huge translucent plane in the depth buffer would swallow the additive FX drawn
  // after it. Ships are drawn before this pass, so they still occlude correctly.
  const holePipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"hvs"}, fragment:{module:mod,entryPoint:"hfs",targets:[{format, blend:ALPHA_BLEND}]},
    primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  let planetBuf=null, planetCap=0, holeBuf=null, holeCap=0;
  // ---- Prong-3 PoC: bake nebula density into a resident 3D texture; raymarch samples it instead of recomputing noise ----
  const bakePipe=device.createComputePipeline({layout:"auto", compute:{module:mod, entryPoint:"bakeDensity"}});
  const nebUBuf=device.createBuffer({size:32, usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  const bakeUBuf=device.createBuffer({size:16, usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  let slotParBuf=null, slotParCap=0;                     // per-slab bake params (storage) — sized to slab count
  const densSampler=device.createSampler({magFilter:"linear",minFilter:"linear",addressModeU:"clamp-to-edge",addressModeV:"clamp-to-edge",addressModeW:"clamp-to-edge"});
  const nebArr=[]; let nebCount=0;                       // hoisted: rebake() reads per-instance params in unique mode
  let nebBaked=true, nebSteps=48, nebStress=1, nebStepMode=0, nebShare=true, nebCover=0.12; // toggled live from the keyboard
  const NEB_STEP_FRAC=0.18;                              // field-style fixed step size (0.18·R ≈ 11 steps/sphere)
  // 7 COLOR templates (emission + per-color shape) — matches the sandbox field presets; each nebula maps to its nearest color.
  const NEB_PRESETS=[
    {emis:[0.63,0.0,0.9], bf:1.0,  ba:0.87, df:1.3055, da:1.6, sw:5.0},  // purple
    {emis:[1.0,0.3,0.1],  bf:0.56, ba:0.87, df:1.3055, da:0.9, sw:5.0},  // red
    {emis:[0.01,1.0,1.0], bf:3.5,  ba:1.87, df:1.3055, da:0.9, sw:5.0},  // blue
    {emis:[0.8,2.0,0.6],  bf:1.4,  ba:1.87, df:1.3055, da:1.6, sw:6.0},  // yellow
    {emis:[0.4,0.8,0.4],  bf:0.72, ba:1.0,  df:1.3055, da:1.6, sw:5.0},  // green
    {emis:[1.8,0.5,0.1],  bf:1.4,  ba:1.87, df:1.3055, da:1.6, sw:6.0},  // orange
    {emis:[1.2,1.2,1.2],  bf:2.4,  ba:0.7,  df:1.3055, da:0.8, sw:4.0},  // white
  ];
  const NEB_K=NEB_PRESETS.length;                        // SHARED templates = the color palette (the data-reduction pool)
  const nebColorToPreset=(c)=>{ let best=0,bd=1e9; for(let i=0;i<NEB_K;i++){ const e=NEB_PRESETS[i].emis; const d=(e[0]-c[0])**2+(e[1]-c[1])**2+(e[2]-c[2])**2; if(d<bd){bd=d;best=i;} } return best; };
  const NEB_SLAB_CAP=48;                                 // max physical slabs (WebGPU 3D-depth limited; field capped similarly)
  const NEB_RES_OPTS=[32,48,64,96]; let nebResIx=1;      // bake resolution knob (VRAM vs shape fidelity)
  // per-template bake params: [seed, swirl, warp, density, baseFreq, baseAmp, detailFreq, detailAmp] (2 vec4f/slab)
  const nebVarieties=[]; for(let v=0;v<NEB_K;v++){ const P=NEB_PRESETS[v]; nebVarieties.push([v*137+7, P.sw, 0.5, 7, P.bf, P.ba, P.df, P.da]); }
  let densTex=null, densView=null, nebBakedRES=0, physicalSlots=0, logicalSlots=0;
  function makeDensTex(RES,P){ if(densTex) densTex.destroy();
    densTex=device.createTexture({size:[RES,RES,RES*P], dimension:"3d", format:"rgba16float",
      usage:GPUTextureUsage.STORAGE_BINDING|GPUTextureUsage.TEXTURE_BINDING});
    densView=densTex.createView({dimension:"3d"}); }
  function rebake(){ const RES=NEB_RES_OPTS[nebResIx];
    // SHARE on: N nebulae reference K templates. off: each nebula is its own slab (VRAM ∝ N, capped ⚠).
    logicalSlots = nebShare ? NEB_K : Math.max(1, nebCount);
    physicalSlots = Math.min(logicalSlots, Math.floor(2048/RES), NEB_SLAB_CAP);
    makeDensTex(RES, physicalSlots);
    const par=new Float32Array(physicalSlots*8);   // 2 vec4f/slab: seed,swirl,warp,density + baseFreq,baseAmp,detailFreq,detailAmp
    for(let s=0;s<physicalSlots;s++){
      if(nebShare){ par.set(nebVarieties[s], s*8); }
      else { const o=s*12; const pv=NEB_PRESETS[nebArr[o+11]|0]||NEB_PRESETS[0];   // unique slab = this nebula's own seed/warp + its color's shape
        par.set([nebArr[o+8]||1, pv.sw, nebArr[o+10]||0.5, nebArr[o+7]||7, pv.bf, pv.ba, pv.df, pv.da], s*8); }
    }
    if(physicalSlots*2>slotParCap){ slotParCap=Math.max(16,physicalSlots*4); if(slotParBuf) slotParBuf.destroy();
      slotParBuf=device.createBuffer({size:slotParCap*16, usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); }
    device.queue.writeBuffer(slotParBuf,0,par);
    device.queue.writeBuffer(bakeUBuf,0,new Float32Array([RES,physicalSlots,nebCover,0]));
    const enc=device.createCommandEncoder(); const cp=enc.beginComputePass();
    cp.setPipeline(bakePipe);
    cp.setBindGroup(0,device.createBindGroup({layout:bakePipe.getBindGroupLayout(0),entries:[
      {binding:8,resource:{buffer:bakeUBuf}},{binding:9,resource:densView},{binding:10,resource:{buffer:slotParBuf}}]}));
    const g=n=>Math.ceil(n/4); cp.dispatchWorkgroups(g(RES),g(RES),g(RES*physicalSlots)); cp.end();
    device.queue.submit([enc.finish()]); nebBakedRES=RES;
  }
  rebake();
  // GPU timestamp query for the nebula pass (real ms; fps caps at vsync and hides headroom)
  let tsSet=null, tsResolve=null, tsRead=null, tsPending=false, nebGpuMs=0;
  if(canTS){ tsSet=device.createQuerySet({type:"timestamp",count:2});
    tsResolve=device.createBuffer({size:16,usage:GPUBufferUsage.QUERY_RESOLVE|GPUBufferUsage.COPY_SRC});
    tsRead=device.createBuffer({size:16,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}); }
  const ALPHA={color:{srcFactor:"src-alpha",dstFactor:"one-minus-src-alpha"},alpha:{srcFactor:"one",dstFactor:"one-minus-src-alpha"}};
  const gridPipe=device.createRenderPipeline({layout:"auto", vertex:{module:mod,entryPoint:"vgrid"}, fragment:{module:mod,entryPoint:"fgrid",targets:[{format,blend:ALPHA}]}, primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  const ringPipe=device.createRenderPipeline({layout:"auto", vertex:{module:mod,entryPoint:"vring", buffers:[{arrayStride:8, attributes:[{shaderLocation:0,offset:0,format:"float32x2"}]}]}, fragment:{module:mod,entryPoint:"fring",targets:[{format,blend:ALPHA}]}, primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  const ringGeo=buildRing(0.95,1.0,64);   // thin band (5% of radius) -> subtle rings
  const ringVb=device.createBuffer({size:ringGeo.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST}); device.queue.writeBuffer(ringVb,0,ringGeo); const ringVerts=ringGeo.length/2;
  let ringBuf=null, ringCap=0; const ringList=[];
  const ADD={color:{srcFactor:"one",dstFactor:"one",operation:"add"},alpha:{srcFactor:"one",dstFactor:"one",operation:"add"}};
  const beamPipe=device.createRenderPipeline({layout:"auto", vertex:{module:mod,entryPoint:"vbeam"}, fragment:{module:mod,entryPoint:"fbeam",targets:[{format,blend:ADD}]}, primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  const projPipe=device.createRenderPipeline({layout:"auto", vertex:{module:mod,entryPoint:"vproj"}, fragment:{module:mod,entryPoint:"fproj",targets:[{format,blend:ADD}]}, primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  const smokePipe=device.createRenderPipeline({layout:"auto", vertex:{module:mod,entryPoint:"vsmoke"}, fragment:{module:mod,entryPoint:"fsmoke",targets:[{format,blend:ADD}]}, primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  const impPipe=device.createRenderPipeline({layout:"auto", vertex:{module:mod,entryPoint:"vimp"}, fragment:{module:mod,entryPoint:"fimp",targets:[{format,blend:ADD}]}, primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  let beamBuf=null, beamCap=0, projBuf=null, projCap=0, smokeBuf=null, smokeCap=0;
  // Diagnostic: where beam-fire records go. CUMULATIVE totals, never reset per frame -- a beam
  // is lit only ~0.75s of a ~6s cycle, so a per-frame count flickers 0/1/0 and cannot be read.
  // A firer the mock says is shooting draws nothing when it is absent from this client's radar
  // stream (nometa), carries no shipData beam ports (noports), or every emitter's arc excludes
  // the target (arccull). 'B' (shift+b) zeroes them to start a fresh measurement.
  let beamCensus={in:0,nometa:0,noports:0,arccull:0,drawn:0,peak:0};
  // Projectile census (torpedoes / mines / drones). Cumulative like the beam one, so a
  // single launch every few seconds is still readable. NOTE the server streams projectiles
  // as [x, z, kind, dirx, dirz] with NO Y, so everything here is drawn on the y=0 plane.
  // An in-flight mine is still kind "missile" (it only becomes "mine" once deployed, and a
  // deployed mine is skipped by _push_fx because it is a real space object by then).
  let projCensus={launches:0,peak:0,now:0,prev:0,frames:0,ynone:false};

  // fallback gray texture (art without a diffuse map)
  const grayTex=device.createTexture({size:[1,1],format:"rgba8unorm-srgb",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
  device.queue.writeTexture({texture:grayTex},new Uint8Array([130,120,110,255]),{bytesPerRow:4},[1,1]);
  const blackTex=device.createTexture({size:[1,1],format:"rgba8unorm",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
  device.queue.writeTexture({texture:blackTex},new Uint8Array([0,0,0,255]),{bytesPerRow:4},[1,1]);   // emissive/specular fallback = none
  const flatNormalTex=device.createTexture({size:[1,1],format:"rgba8unorm",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
  device.queue.writeTexture({texture:flatNormalTex},new Uint8Array([128,128,255,255]),{bytesPerRow:4},[1,1]);   // normal fallback = flat (0,0,1)

  // real engine cube-cross skybox, loaded by name (flat neutral until ready / when none)
  let skyTex=device.createTexture({size:[1,1],format:"rgba8unorm",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
  device.queue.writeTexture({texture:skyTex},new Uint8Array([6,9,20,255]),{bytesPerRow:4},[1,1]);
  let skyView=skyTex.createView(), skyReady=false, lastSky=null;
  const skySamp=device.createSampler({magFilter:"linear",minFilter:"linear",addressModeU:"clamp-to-edge",addressModeV:"clamp-to-edge"});
  async function loadSky(name){
    const base=String(name).split(/[\\/]/).pop();
    try{ const img=new Image(); img.src='/'+base+'.png'; await img.decode(); const bmp=await createImageBitmap(img);
      const t=device.createTexture({size:[bmp.width,bmp.height],format:"rgba8unorm",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
      device.queue.copyExternalImageToTexture({source:bmp},{texture:t},[bmp.width,bmp.height]);
      const old=skyTex; skyTex=t; skyView=t.createView(); skyReady=true; if(old) old.destroy(); wlog("skybox loaded: "+base+" ("+bmp.width+"x"+bmp.height+")");
    }catch(e){ skyReady=false; wlog("skybox load failed: "+base+" — "+(e&&e.message||e)); }
  }

  // ---- real-art loader (cached by art root), self-contained fetch of the mock's /ships/ files ----
  const artCache=new Map();   // art -> {status:'loading'|'ready'|'failed', vb, ib, count, bind}
  // Art roots whose /ships/<art>.obj fetch or parse failed. An object whose art fails to load
  // is simply absent from the 3D view with no other symptom, so surface it on the HUD rather
  // than only in the console (this is how a missing wreck/hull mesh shows itself).
  const artFailed=[];
  // ...and draw it as a placeholder sphere rather than nothing, so a missing mesh reads as
  // "wrong shape here" instead of "object doesn't exist". Engine-drawn bodies with no OBJ at
  // all (planet, maelstrom) have their own passes; this catches everything else — e.g. LM's
  // typhon monsters, spawned with the art id "-".
  const PLACEHOLDER_ART="sphere"; let phRec=null;
  function loadArt(art){
    if(artCache.has(art)) return artCache.get(art);
    const rec={status:"loading"}; artCache.set(art,rec);
    (async()=>{
      try{
        const r=await fetch('/ships/'+art+'.obj'); if(!r.ok) throw new Error(r.status+" "+art);
        const mesh=parseOBJ(await r.text());
        rec.vb=device.createBuffer({size:mesh.v.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST}); device.queue.writeBuffer(rec.vb,0,mesh.v);
        rec.ib=device.createBuffer({size:mesh.i.byteLength,usage:GPUBufferUsage.INDEX|GPUBufferUsage.COPY_DST}); device.queue.writeBuffer(rec.ib,0,mesh.i);
        rec.count=mesh.i.length; rec.maxDim=mesh.maxDim||60; rec.center=mesh.center||[0,0,0];
        const loadTex=async(suffix,srgb,fallback)=>{
          try{ const img=new Image(); img.src='/ships/'+art+suffix; await img.decode(); const bmp=await createImageBitmap(img);
            const t=device.createTexture({size:[bmp.width,bmp.height],format:srgb?"rgba8unorm-srgb":"rgba8unorm",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
            device.queue.copyExternalImageToTexture({source:bmp},{texture:t},[bmp.width,bmp.height]); return t.createView();
          }catch(e){ return fallback.createView(); }
        };
        const view=await loadTex('_diffuse.png',true,grayTex);         // albedo (sRGB)
        const emisView=await loadTex('_emissive.png',true,blackTex);   // glow (sRGB), none when missing
        const specView=await loadTex('_specular.png',false,blackTex);  // spec intensity (linear), none when missing
        const normView=await loadTex('_normal.png',false,flatNormalTex); // tangent-space normal (linear), flat when missing
        rec.bind=device.createBindGroup({layout:pipe.getBindGroupLayout(1),entries:[{binding:0,resource:view},{binding:1,resource:samp},{binding:2,resource:emisView},{binding:3,resource:specView},{binding:4,resource:normView}]});
        rec.instBuf=null; rec.instCap=0; rec.status="ready";
      }catch(e){ rec.status="failed"; if(artFailed.indexOf(art)<0) artFailed.push(art);
        if(art!==PLACEHOLDER_ART && !phRec) phRec=loadArt(PLACEHOLDER_ART);   // lazy: only fetched once something is missing
        wlog("art load failed: "+art+" — "+(e&&e.message||e)); }
    })();
    return rec;
  }

  // ---- gather live objects (terrain + dynamic) grouped by art, matching the mock's transform ----
  // Per-art instance data lives on each artCache rec: rec.tInst/tCount (terrain=STATIC, uploaded only
  // when terrainVersion changes) + rec.dInst/dCount (dynamic=per-frame). This is the delta win: the
  // bulk (asteroid/nebula field) is sent once, not every frame — only the few moving ships re-upload.
  let terrainVer=-1; let fcx=0,fcz=0,fmeanR=1;   // nebArr / nebCount hoisted up to the bake section
  // Orbit framing follows the SHIPS, not the terrain. Terrain meshes only began rendering when
  // gatherTerrain's icon_index filter was corrected (data_set.get returns 0, not None, for an
  // unset key, so `icon_index!=null` had been skipping every rock) -- which silently moved the
  // orbit centre from the origin onto the asteroid field's centre of mass, and `dist` onto its
  // spread. On a wide belt that parks the camera far outside the play area. Rendering terrain
  // and framing on terrain are separate concerns; these track the dynamic objects instead.
  let dcx=0,dcz=0,dmeanR=1;
  // Analytic bodies, gathered with the terrain (static): 20 floats per planet (5 vec4, matching
  // the WGSL Planet struct), 8 per black hole (2 vec4, matching Hole). holeList keeps a CPU-side
  // copy so the far plane can be fitted to the gravity radius.
  const planetArr=[], holeArr=[], holeList=[]; let planetCount=0, holeCount=0;
  // "#rgb" / "#rrggbb" -> linear-ish 0..1 rgb, for a mission-set radar_color_override.
  const cssRGB=(s)=>{ if(typeof s!=="string") return null; const m=/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(s.trim()); if(!m) return null;
    const h=m[1].length===3?m[1].replace(/./g,c=>c+c):m[1]; const n=parseInt(h,16);
    return [((n>>16)&255)/255, ((n>>8)&255)/255, (n&255)/255]; };
  let terrainCensus={n:0,neb:0,icon:0,noart:0,wanted:[]};   // diagnostic: where terrain records go (asteroid hunt)
  function ensureInst(rec, which, list){
    const n=list.length/8; rec[which+"Count"]=n; if(n===0) return;
    const ck=which+"Cap"; if(!rec[ck]) rec[ck]=0;
    if(n>rec[ck]){ rec[ck]=Math.max(64,n*2); if(rec[which+"Inst"]) rec[which+"Inst"].destroy(); rec[which+"Inst"]=device.createBuffer({size:rec[ck]*32,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); }
    device.queue.writeBuffer(rec[which+"Inst"],0,new Float32Array(list));
  }
  // orientation: engine q is [w,x,y,z] -> shader wants [x,y,z,w]; if no q, yaw from the fx/fz heading (like the mock)
  const packObj=(arr,x,y,z,m)=>{
    let q;
    if(m.q&&m.q.length===4){ q=[m.q[1],m.q[2],m.q[3],m.q[0]]; }
    else { const a=Math.atan2(m.fx||0, m.fz||0)*0.5; q=[0, Math.sin(a), 0, Math.cos(a)]; }
    arr.push(x,y,z,(m.meshscale||1), q[0],q[1],q[2],q[3]);
  };
  // rotate a mesh-local vector by q=[x,y,z,w] — matches the WGSL qrot exactly (for engine-port smoke)
  const qrotJS=(q,vx,vy,vz)=>{ const tx=2*(q[1]*vz-q[2]*vy), ty=2*(q[2]*vx-q[0]*vz), tz=2*(q[0]*vy-q[1]*vx);
    return [vx+q[3]*tx+(q[1]*tz-q[2]*ty), vy+q[3]*ty+(q[2]*tx-q[0]*tz), vz+q[3]*tz+(q[0]*ty-q[1]*tx)]; };
  const qOf=(m)=>{ if(m.q&&m.q.length===4) return [m.q[1],m.q[2],m.q[3],m.q[0]]; const a=Math.atan2(m.fx||0,m.fz||0)*0.5; return [0,Math.sin(a),0,Math.cos(a)]; };
  function gatherTerrain(b){                    // STATIC — only re-run when terrainVersion changes
    const lists=new Map(); nebArr.length=0; planetArr.length=0; holeArr.length=0; holeList.length=0; let sx=0,sz=0,cnt=0;
    let _cN=0,_cNeb=0,_cIcon=0,_cNoart=0,_cMark=0;   // census: where terrain records go
    if(b.terrainPos) for(let i=0;i<(b.terrainCount|0);i++){
      const id=b.terrainRev&&b.terrainRev.get?b.terrainRev.get(i):undefined; if(id===undefined) continue;
      const m=b.terrainMeta.get(id); if(!m) continue;
      _cN++;
      const x=b.terrainPos[i*3], z=b.terrainPos[i*3+1], y=m.y||0;
      if(m.nebula){ _cNeb++; const c=m.color||[0.55,0.5,0.85]; const vv=nebColorToPreset(c); nebArr.push(x,y,z, Math.max(200,m.radius||2000), c[0],c[1],c[2], m.density||7, m.seed||1, m.swirl||0, m.warp||0, vv); continue; }
      // Engine-drawn bodies (no OBJ): the gas-giant surface and the black hole get their own
      // analytic passes. They DO count toward the terrain centroid — a worldlet is the biggest
      // thing on the map, so orbit framing that ignored it would park the camera off in space.
      if(m.planet){ const bs=m.pbase||[0.55,0.16,0.28], em=m.pemis||[0.06,0.04,0.03], cl=m.pcloud||[1,1,1];
        planetArr.push(x,y,z, Math.max(10,m.pradius||500),
                       bs[0],bs[1],bs[2], m.pband||3.72,
                       em[0],em[1],em[2], m.pcstr||3.12,
                       cl[0],cl[1],cl[2], m.pcexp||3.96,
                       m.pfpow||11.96, m.pfbias||0.42, m.pws1||0, m.pws2||0);
        sx+=x; sz+=z; cnt++; continue; }
      if(m.blackhole){ const R=Math.max(10,m.bhr||100), G=Math.max(R*2,m.bhgrav||R*12);
        // point-ring's ambientColor: the mission's radar_color_override if it set one, else a
        // hot amber (a guess — the engine keeps the maelstrom's tint internal).
        const c=cssRGB(m.tint)||[1.0,0.55,0.2];
        holeArr.push(x,y,z,R, G,c[0],c[1],c[2]);
        holeList.push([x,y,z,R,G]);                              // CPU copy, for the far-plane fit
        sx+=x; sz+=z; cnt++; continue; }
      if(m.tick_type==="behav_selection"){ _cMark++; continue; }   // selection markers (nebula/map/galaxy-board glyphs) are 2D-only, not 3D meshes
      if(m.icon_index){ _cIcon++; continue; }   // icon_index 0 = blank glyph (a real 3D mesh object); only a truthy (>0) index is a 2D-only marker
      if(!m.art){ _cNoart++; continue; }
      let arr=lists.get(m.art); if(!arr){ arr=[]; lists.set(m.art,arr); } packObj(arr,x,y,z,m); sx+=x; sz+=z; cnt++;
    }
    terrainCensus={n:_cN, neb:_cNeb, icon:_cIcon, noart:_cNoart, mark:_cMark, wanted:[...lists.keys()]};
    for(const rec of artCache.values()) rec.tCount=0;
    for(const [art,arr] of lists){ ensureInst(loadArt(art),"t",arr); }
    nebCount=nebArr.length/12;
    if(nebCount>0){ if(nebCount>nebCap){ nebCap=Math.max(16,nebCount*2); if(nebBuf) nebBuf.destroy(); nebBuf=device.createBuffer({size:nebCap*48,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); } device.queue.writeBuffer(nebBuf,0,new Float32Array(nebArr)); }
    planetCount=planetArr.length/20;
    if(planetCount>0){ if(planetCount>planetCap){ planetCap=Math.max(8,planetCount*2); if(planetBuf) planetBuf.destroy(); planetBuf=device.createBuffer({size:planetCap*80,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); } device.queue.writeBuffer(planetBuf,0,new Float32Array(planetArr)); }
    holeCount=holeArr.length/8;
    if(holeCount>0){ if(holeCount>holeCap){ holeCap=Math.max(8,holeCount*2); if(holeBuf) holeBuf.destroy(); holeBuf=device.createBuffer({size:holeCap*32,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); } device.queue.writeBuffer(holeBuf,0,new Float32Array(holeArr)); }
    rebake();   // scene's nebulae changed — refresh slabs (unique mode bakes from these params)
    fcx=cnt?sx/cnt:0; fcz=cnt?sz/cnt:0; let sr=0,mm=0; for(const arr of lists.values()){ for(let i=0;i<arr.length;i+=8){ sr+=Math.hypot(arr[i]-fcx, arr[i+2]-fcz); mm++; } } fmeanR=Math.max(1, mm?sr/mm:1);
    // A planet / black hole is a BODY, not a point: its own radius has to reach the far plane
    // too, or a system whose only terrain is one worldlet gets clipped away.
    for(let i=0;i<planetArr.length;i+=20) fmeanR=Math.max(fmeanR, Math.hypot(planetArr[i]-fcx, planetArr[i+2]-fcz)+planetArr[i+3]*2);
    for(const h of holeList) fmeanR=Math.max(fmeanR, Math.hypot(h[0]-fcx, h[2]-fcz)+h[4]);
  }
  const HALFPI=Math.PI/2;
  const shieldCol=(f)=> f>0.66?[0.2,1.0,0.4]:(f>0.33?[1.0,0.85,0.35]:[1.0,0.33,0.33]);   // green / yellow / red by fraction
  const smDyn=new Map();   // id -> {r:[x,y,z] smoothed pos, spd, pr, pf:[puffs]} (60fps ease over the mock's 30Hz push -> no jitter)
  let smokeArr=[];         // engine exhaust puffs this frame: [x,y,z,size, alpha,0,0,0] per puff
  function gatherDyn(b){                        // DYNAMIC — every frame (few, moving)
    const lists=new Map(); let n=0; const seen=new Set(); smokeArr.length=0;
    if(b.dynPos) for(let i=0;i<(b.dynCount|0);i++){
      const id=b.dynRev&&b.dynRev.get?b.dynRev.get(i):undefined; if(id===undefined) continue;
      const m=b.dynMeta.get(id); if(!m||!m.art||m.nebula||m.icon_index!=null) continue;
      seen.add(id);
      const tx=b.dynPos[i*3], tz=b.dynPos[i*3+1], ty=m.y||0;
      let s=smDyn.get(id);
      if(!s){ s={r:[tx,ty,tz]}; smDyn.set(id,s); }
      else { const PL=0.12; s.r[0]+=(tx-s.r[0])*PL; s.r[1]+=(ty-s.r[1])*PL; s.r[2]+=(tz-s.r[2])*PL; }   // mock's dispBuf easing
      let arr=lists.get(m.art); if(!arr){ arr=[]; lists.set(m.art,arr); } packObj(arr,s.r[0],s.r[1],s.r[2],m); n++;
      // engine exhaust: constant-LENGTH trail whose DENSITY tracks speed (thick/dense fast, thin slow).
      // Emit by DISTANCE traveled (fixed world spacing) so a slow ship never piles puffs and a fast ship
      // never leaves gaps; particle COUNT + jitter per node scale with speed; a distance-cull holds the
      // trail to a fixed length behind the ship (so it stays ~the same length, just denser when faster).
      const segx=s.pr?s.r[0]-s.pr[0]:0, segy=s.pr?s.r[1]-s.pr[1]:0, segz=s.pr?s.r[2]-s.pr[2]:0;
      const seg=Math.hypot(segx,segy,segz);
      s.spd=(s.spd||0)+(seg-(s.spd||0))*0.15;               // EMA speed (units/frame)
      if(!s.pf) s.pf=[];
      const rc2=artCache.get(m.art); const psz=(m.meshscale||1)*((rc2&&rc2.maxDim)?rc2.maxDim:60);
      const spdN=Math.min(1, (s.spd||0)/2.5);               // ~2.5 u/frame = cruising -> full density
      const L=psz*3.2, L2=L*L;                              // constant trail length
      if(s.pf.length){ const sx=s.r[0],sy=s.r[1],sz2=s.r[2];   // age (stopped trails fade) + distance-cull (constant length)
        s.pf=s.pf.filter(p=>{ p[3]-=0.02; if(p[3]<=0) return false; const ax=p[0]-sx,ay=p[1]-sy,az=p[2]-sz2; return ax*ax+ay*ay+az*az<L2; }); }
      if(spdN>0.03 && seg>1e-4){
        const ms=(m.meshscale||1), ctr=(rc2&&rc2.center)?rc2.center:[0,0,0], q=qOf(m);
        const ports=(m.exhaust&&m.exhaust.length)?m.exhaust:null;
        const off=[];   // rotated engine-port offsets (mesh-local -> world basis)
        if(ports){ for(const e of ports) off.push(qrotJS(q,(e[0]-ctr[0])*ms,(e[1]-ctr[1])*ms,(e[2]-ctr[2])*ms)); }
        else { const fn=Math.hypot(m.fx||0,m.fz||0)||1; off.push([-(m.fx||0)/fn*psz*0.6,0,-(m.fz||0)/fn*psz*0.6]); }   // fallback: stern
        const spacing=Math.max(1,psz*0.12), cnt=1+Math.round(spdN*2), jr=psz*0.035*(0.25+0.75*spdN);   // tight spacing (overlapping -> gapless), still thin via low alpha
        s.acc=(s.acc||0)+seg; let guard=0;
        while(s.acc>=spacing && guard<48){ s.acc-=spacing; guard++;
          const f=Math.max(0,Math.min(1,1-s.acc/seg)), bx=s.pr[0]+segx*f, by=s.pr[1]+segy*f, bz=s.pr[2]+segz*f;
          for(const o of off){ for(let c=0;c<cnt;c++){ const jx=c?(Math.random()*2-1)*jr:0, jy=c?(Math.random()*2-1)*jr:0, jz=c?(Math.random()*2-1)*jr:0;
            s.pf.push([bx+o[0]+jx, by+o[1]+jy, bz+o[2]+jz, 1.0, spdN]); } } }
      } else s.acc=0;
      s.pr=[s.r[0],s.r[1],s.r[2]];
      for(let k=0;k<s.pf.length;k++){ const p=s.pf[k], a=p[3]*(0.35+0.65*p[4]); if(a<=0.01) continue;
        smokeArr.push(p[0],p[1],p[2], psz*0.16*(1.0+(1.0-p[3])*0.7), a*0.28,0,0,0); }   // overlapping puffs at low alpha -> gapless but thin
      if(m.shp>=0){ const rc=artCache.get(m.art); const sz=(m.meshscale||1)*((rc&&rc.maxDim)?rc.maxDim:60);
        const hd=Math.atan2(m.fz||0, m.fx||0);                       // ship heading -> front half faces forward
        const sf=(m.shpf!=null&&m.shpf>=0)?m.shpf:m.shp, sa=(m.shpa!=null&&m.shpa>=0)?m.shpa:m.shp;
        const cf=shieldCol(sf), ca=shieldCol(sa);
        ringList.push(s.r[0],s.r[1],s.r[2], sz*1.25, cf[0],cf[1],cf[2], 0.32, 0.05, hd, HALFPI-0.14, 0);            // fore shield -> nose arc (mock facing 0 = front)
        ringList.push(s.r[0],s.r[1],s.r[2], sz*1.25, ca[0],ca[1],ca[2], 0.32, 0.05, hd+Math.PI, HALFPI-0.14, 0); }  // aft shield -> tail arc; the 0.14 gap makes the split visible even at equal charge
    }
    for(const id of smDyn.keys()) if(!seen.has(id)) smDyn.delete(id);
    for(const rec of artCache.values()) rec.dCount=0;
    for(const [art,arr] of lists){ ensureInst(loadArt(art),"d",arr); }
    // Ship centroid + mean spread, for the orbit camera (same shape as gatherTerrain's).
    // Named d* so they don't shadow the block-scoped sx/sz/cnt used in the trail code above.
    let dsx=0,dsz=0,dcnt=0;
    for(const arr of lists.values()){ for(let i=0;i<arr.length;i+=8){ dsx+=arr[i]; dsz+=arr[i+2]; dcnt++; } }
    dcx=dcnt?dsx/dcnt:0; dcz=dcnt?dsz/dcnt:0;
    let dsr=0,dmm=0; for(const arr of lists.values()){ for(let i=0;i<arr.length;i+=8){ dsr+=Math.hypot(arr[i]-dcx, arr[i+2]-dcz); dmm++; } }
    dmeanR=Math.max(1, dmm?dsr/dmm:1);
    return n;
  }
  // the client's own ship (by _myShipId, else first PLAYER-type) — for the chase camera
  let playerCount=0, npcCount=0;
  function findPlayer(b){
    if(!b||!b.dynPos||!b.dynMeta) return null;
    const pick=(id)=>{ if(id==null) return null; const idx=b.dynMap&&b.dynMap.get?b.dynMap.get(id):undefined; if(idx===undefined||idx>=(b.dynCount|0)) return null;
      const mm=b.dynMeta.get(id); if(!mm) return null; const s=smDyn.get(id);   // dead-reckoned pos so the chase cam doesn't jitter
      return {x:s?s.r[0]:b.dynPos[idx*3], y:s?s.r[1]:(mm.y||0), z:s?s.r[2]:b.dynPos[idx*3+1], fx:mm.fx||0, fz:mm.fz||0, art:mm.art||"", sc:mm.meshscale||1}; };
    if(focusNpc){   // 'n': cycle NON-player ships (enemies / allies / monsters) — to hunt a far or cloaked NPC
      const npcs=[];
      for(const [id,mm] of b.dynMeta){ if(mm.art && mm.icon_index==null && mm.tick_type && mm.tick_type.indexOf("player")<0) npcs.push(id); }
      npcCount=npcs.length;
      if(npcs.length){ const p=pick(npcs[((npcSel%npcs.length)+npcs.length)%npcs.length]); if(p) return p; }
      focusNpc=false;   // none renderable -> fall back to players
    }
    // cycle RENDERABLE player ships (tick_type is the behavior tag, e.g. "behav_player")
    const ships=[];
    for(const [id,mm] of b.dynMeta){ if(mm.art && mm.icon_index==null && mm.tick_type && mm.tick_type.indexOf("player")>=0) ships.push(id); }
    if(b.myShipId!=null){ const i=ships.indexOf(b.myShipId); if(i>0){ ships.splice(i,1); ships.unshift(b.myShipId); } }   // prefer own ship as index 0
    playerCount=ships.length;
    let id = ships.length ? ships[((shipSel%ships.length)+ships.length)%ships.length] : b.myShipId;
    let p=pick(id);
    if(!p && b.myShipId!=null) p=pick(b.myShipId);
    return p;
  }

  let W=1,H=1,depthTex=null,depthView=null;
  let yaw=0.6, pitch=0.4, dist=1, cx=0,cz=0, framed=false, chaseDist=0, recenterChase=false, chaseLocked=true;
  let smEye=null, smTgt=null, smMode=null, smFwd=null;   // smoothed camera + chase heading
  let fnum=0;
  bindOrbit();
  function ensure(){ const dpr=Math.min(devicePixelRatio||1,2); const w=Math.max(1,(canvas.clientWidth*dpr)|0), h=Math.max(1,(canvas.clientHeight*dpr)|0);
    if(w===W&&h===H&&depthTex) return; W=w;H=h; canvas.width=W; canvas.height=H;
    if(depthTex) depthTex.destroy(); depthTex=device.createTexture({size:[W,H],format:"depth24plus",usage:GPUTextureUsage.RENDER_ATTACHMENT}); depthView=depthTex.createView(); }

  function frameInner(){
    const b2=bridge();
    // Dock as the mock's 3dview: visible only while the cinematic 3dview is active, sized to its canvas rect
    // (the ship_data/target HUDs and the GUI sit at higher z-index, so they draw on top). 'g' still force-hides.
    const el=b2&&b2.view3dEl, r=el?el.getBoundingClientRect():null;
    const show=!!(b2&&b2.active&&visible&&r&&r.width>2&&r.height>2);
    if(!show){ if(canvas.style.display!=="none"){ canvas.style.display="none"; hud.style.display="none"; } return; }
    if(canvas.style.display!=="block") canvas.style.display="block";
    hud.style.display="block";
    canvas.style.left=r.left+"px"; canvas.style.top=r.top+"px"; canvas.style.width=r.width+"px"; canvas.style.height=r.height+"px";
    ensure(); fnum++;
    const skyName=b2?b2.skyName:null;
    if(skyName && skyName!==lastSky){ lastSky=skyName; loadSky(skyName); }
    else if(!skyName && lastSky){ lastSky=null; skyReady=false; }
    ringList.length=0;
    let dynN=0;
    if(b2){ const tv=b2.terrainVersion|0; if(tv!==terrainVer){ terrainVer=tv; gatherTerrain(b2); } dynN=gatherDyn(b2); }
    let tObjs=0; for(const rec of artCache.values()) tObjs+=(rec.tCount||0);
    const g={ n:tObjs+dynN, meanR:fmeanR };   // meanR stays terrain-wide: the FAR plane must still reach the whole field
    // Frame on the SHIPS. Terrain is scenery and its centroid can sit far from the play area;
    // fall back to it only while no ship is on screen, and don't latch `framed` until one is,
    // so an early terrain-only frame can't pin the camera out in empty space for the session.
    if(dynN>0){ cx=dcx; cz=dcz; if(!framed){ dist=dmeanR*2.5+2000; framed=true; } }
    else if(g.n>0){ cx=fcx; cz=fcz; }
    const player=findPlayer(b2);
    if(player){ const rc=player.art?artCache.get(player.art):null; const sz=Math.max(1,(player.sc||1)*((rc&&rc.maxDim)?rc.maxDim:60));
      ringList.push(player.x, player.y, player.z, Math.max(460,sz*1.5), 0.0,0.9,1.0, 0.35, 0.0125, 0.0, 4.0, 0); }   // own-ship highlight (thin 1/4 band, 2x more transparent, full ring)
    let want=MODES[modeIx];
    if(want==="chase" && !player) want="orbit";
    if(want==="cinematic" && !(b2 && Array.isArray(b2.cam) && Array.isArray(b2.tgt))) want="orbit";
    let mode=want, note="", EYE,TGT,FOVY,NEAR,FAR;
    if(want==="chase"){                          // orbit around the followed ship — drag to orbit, wheel to zoom (like WebGL)
      const rec=player.art?artCache.get(player.art):null; const md=(rec&&rec.status==="ready"&&rec.maxDim)?rec.maxDim:60;
      const size=Math.max(1, md*(player.sc||1)); note=`ship ~${(size*2)|0}u ${chaseLocked?'[lock]':'[free]'}`;
      if(chaseDist<=0) chaseDist=size*5;         // first frame: frame the ship; wheel adjusts thereafter
      if(recenterChase){ yaw=Math.atan2(-player.fx,-player.fz); pitch=0.22; recenterChase=false; }  // dbl-click: snap behind now
      else if(chaseLocked){ const ty=Math.atan2(-player.fx,-player.fz); const dy=((ty-yaw+Math.PI*3)%(Math.PI*2))-Math.PI; yaw+=dy*0.12; }  // locked: auto-follow behind the heading as the ship turns
      const cp=Math.cos(pitch),sy=Math.sin(pitch),cyw=Math.cos(yaw),syw=Math.sin(yaw), sp=[player.x,player.y,player.z];
      EYE=[sp[0]+cp*syw*chaseDist, sp[1]+sy*chaseDist, sp[2]+cp*cyw*chaseDist];
      TGT=[sp[0],sp[1],sp[2]];
      FOVY=50*Math.PI/180; NEAR=Math.max(1,Math.min(size*0.2, chaseDist*0.08)); FAR=chaseDist*4+g.meanR*4+1e5;
    } else if(want==="cinematic"){               // the mock's own cinematic camera (55deg, _v3dCam -> _v3dTgt)
      EYE=b2.cam.slice(); TGT=b2.tgt.slice(); const d=Math.max(1,Math.hypot(EYE[0]-TGT[0],EYE[1]-TGT[1],EYE[2]-TGT[2]));
      FOVY=55*Math.PI/180; NEAR=Math.max(5,d*0.02); FAR=d*6+g.meanR*6+1e5;
    } else {                                     // free orbit around the object bulk (drag/wheel)
      const cp=Math.cos(pitch),sp=Math.sin(pitch),cyw=Math.cos(yaw),syw=Math.sin(yaw);
      EYE=[cx+cp*syw*dist, sp*dist, cz+cp*cyw*dist]; TGT=[cx,0,cz];
      FOVY=50*Math.PI/180; NEAR=Math.max(10,dist*0.02); FAR=dist*4+g.meanR*6+1e5;
    }
    // chase is already rigid off the smoothed ship (stays perfectly framed); only ease the raw cinematic server cam. orbit snaps.
    if(smMode!==want || !smEye){ smMode=want; smEye=EYE.slice(); smTgt=TGT.slice(); }
    if(want==="cinematic"){ const L=0.12; for(let i=0;i<3;i++){ smEye[i]+=(EYE[i]-smEye[i])*L; smTgt[i]+=(TGT[i]-smTgt[i])*L; } EYE=smEye; TGT=smTgt; }
    else { smEye=EYE.slice(); smTgt=TGT.slice(); }
    const aspect=W/H, th=Math.tan(FOVY/2);
    const fwd=norml(sub(TGT,EYE),[0,0,1]), right=norml(cr(fwd,[0,1,0]),[1,0,0]), up=cr(right,fwd);
    const vp=mul(perspective(FOVY,aspect,NEAR,FAR), lookAt(EYE,TGT,[0,1,0]));
    const uf=new Float32Array(32); uf.set(vp,0); uf.set([fwd[0],fwd[1],fwd[2],th],16); uf.set([right[0],right[1],right[2],aspect],20); uf.set([up[0],up[1],up[2], skyReady?1:0],24); uf.set([EYE[0],EYE[1],EYE[2],(performance.now()*0.001)%1000],28);
    device.queue.writeBuffer(ubuf,0,uf);

    const enc=device.createCommandEncoder();
    const curView=ctx.getCurrentTexture().createView();
    const tsw=(canTS&&!tsPending)?{querySet:tsSet,beginningOfPassWriteIndex:0,endOfPassWriteIndex:1}:undefined;  // time the whole 3D pass
    const p=enc.beginRenderPass({colorAttachments:[{view:curView,clearValue:{r:0.02,g:0.03,b:0.05,a:1},loadOp:"clear",storeOp:"store"}],
      depthStencilAttachment:{view:depthView,depthClearValue:1.0,depthLoadOp:"clear",depthStoreOp:"store"}, timestampWrites:tsw});
    const bindBg=device.createBindGroup({layout:bgPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:2,resource:skyView},{binding:3,resource:skySamp}]});
    p.setPipeline(bgPipe); p.setBindGroup(0,bindBg); p.draw(3);   // real skybox if loaded, else flat neutral
    p.setPipeline(pipe);
    let draws=0, drawn=0, arts=0, loading=0;
    for(const [art,rec] of artCache){
      // A failed art borrows the placeholder mesh (its own instance buffers still apply), so a
      // missing OBJ shows up as an obviously-wrong sphere instead of an invisible object.
      const geo = rec.status==="ready" ? rec : (rec.status==="failed" && phRec && phRec.status==="ready" ? phRec : null);
      if(!geo){ if(rec.status==="loading") loading++; continue; }
      const tc=rec.tCount||0, dc=rec.dCount||0; if(tc+dc===0) continue; arts++;
      p.setBindGroup(1,geo.bind); p.setVertexBuffer(0,geo.vb); p.setIndexBuffer(geo.ib,"uint32");
      if(tc>0){ const b0=device.createBindGroup({layout:pipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:1,resource:{buffer:rec.tInst}}]}); p.setBindGroup(0,b0); p.drawIndexed(geo.count,tc,0,0,0); draws++; drawn+=tc; }
      if(dc>0){ const b0=device.createBindGroup({layout:pipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:1,resource:{buffer:rec.dInst}}]}); p.setBindGroup(0,b0); p.drawIndexed(geo.count,dc,0,0,0); draws++; drawn+=dc; }
    }
    // analytic bodies: gas-giant surfaces + black-hole horizons (opaque, own per-pixel depth)
    if(planetCount>0 && planetBuf){
      const pb=device.createBindGroup({layout:planetPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:11,resource:{buffer:planetBuf}}]});
      p.setPipeline(planetPipe); p.setBindGroup(0,pb); p.draw(6,planetCount); draws++; }
    if(holeCount>0 && holeBuf){
      const hb=device.createBindGroup({layout:holePipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:12,resource:{buffer:holeBuf}}]});
      p.setPipeline(holePipe); p.setBindGroup(0,hb); p.draw(6,holeCount); draws++; }
    // reference grid + flat rings (own-ship highlight / shield fraction), depth-tested transparents
    if(showGrid){ const gb=device.createBindGroup({layout:gridPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}}]}); p.setPipeline(gridPipe); p.setBindGroup(0,gb); p.draw(6); }
    const nr=ringList.length/12;
    if(nr>0){ if(nr>ringCap){ ringCap=Math.max(16,nr*2); if(ringBuf) ringBuf.destroy(); ringBuf=device.createBuffer({size:ringCap*48,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); }
      device.queue.writeBuffer(ringBuf,0,new Float32Array(ringList));
      const rb=device.createBindGroup({layout:ringPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:5,resource:{buffer:ringBuf}}]});
      p.setPipeline(ringPipe); p.setBindGroup(0,rb); p.setVertexBuffer(0,ringVb); p.draw(ringVerts,nr); }
    // volumetric nebulae (additive, depth-tested) — drawn BEFORE the combat FX so exhaust/beams/torpedoes stay ON TOP of the haze
    if(nebCount>0){
      device.queue.writeBuffer(nebUBuf,0,new Float32Array([nebBaked?1:0, nebSteps, physicalSlots, nebCount, nebStepMode, NEB_STEP_FRAC, nebShare?1:0, nebCover]));
      const nb=device.createBindGroup({layout:nebPipe.getBindGroupLayout(0),entries:[
        {binding:0,resource:{buffer:ubuf}},{binding:4,resource:{buffer:nebBuf}},
        {binding:5,resource:densView},{binding:6,resource:densSampler},{binding:7,resource:{buffer:nebUBuf}}]});
      p.setPipeline(nebPipe); p.setBindGroup(0,nb); p.draw(6,nebCount*nebStress); draws++;
    }
    // engine exhaust smoke (additive, behind the combat glow) — built per ship in gatherDyn
    const nsm=(smokeArr.length/8)|0;
    if(nsm>0){ if(nsm>smokeCap){ smokeCap=Math.max(64,nsm*2); if(smokeBuf) smokeBuf.destroy(); smokeBuf=device.createBuffer({size:smokeCap*32,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); }
      device.queue.writeBuffer(smokeBuf,0,new Float32Array(smokeArr));
      const sd=device.createBindGroup({layout:smokePipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:8,resource:{buffer:smokeBuf}}]}); p.setPipeline(smokePipe); p.setBindGroup(0,sd); p.draw(6,nsm); draws++; }
    // combat FX (additive glow): expand each beam to one ribbon per shipData beam-emitter (converging on the target)
    let beamOut=null;
    if(b2&&b2.beams&&b2.beams.length){ beamOut=[];
      if(b2.beams.length>beamCensus.peak) beamCensus.peak=b2.beams.length;   // most simultaneous firers seen
      for(const bb of b2.beams){ const it=(bb[4]==null?1:bb[4]), fid=bb[5], tid=bb[6];
        beamCensus.in++;
        const mm=(fid!=null&&b2.dynMeta)?b2.dynMeta.get(fid):null;
        const ports=(mm&&mm.beamports&&mm.beamports.length)?mm.beamports:null;
        if(!mm) beamCensus.nometa++;
        else if(!ports) beamCensus.noports++;
        if(!ports) continue;   // no beam-port set -> no beam weapons -> draw nothing (never fabricate a center beam)
        const sf=smDyn.get(fid), st=tid!=null?smDyn.get(tid):null;      // smoothed ends so the beam lines up with the drawn meshes
        const ox=sf?sf.r[0]:bb[0], oy=sf?sf.r[1]:0, oz=sf?sf.r[2]:bb[1];   // use the SHIP's altitude (ignore the port's Y) so the beam doesn't float
        const x2=st?st.r[0]:bb[2], ty=st?st.r[1]:0, z2=st?st.r[2]:bb[3];
        const rc=artCache.get(mm.art), ctr=(rc&&rc.center)?rc.center:[0,0,0], ms=(mm.meshscale||1), q=qOf(mm);
        // target bearing relative to the firer's heading (deg, + = starboard) — for per-emitter arc gating
        const dgx=x2-ox, dgz=z2-oz, fwx=mm.fx||0, fwz=mm.fz||0;
        const bearing=Math.atan2(fwz*dgx-fwx*dgz, fwx*dgx+fwz*dgz)*180/Math.PI;
        for(const e of ports){
          const aw=(e[7]!=null?e[7]:360);
          if(aw<359){ const ba=e[6]||0; let d=((bearing-ba+540)%360)-180; if(Math.abs(d)>aw*0.5){ beamCensus.arccull++; continue; } }   // target outside THIS emitter's arc -> it doesn't fire
          const w=qrotJS(q,(e[0]-ctr[0])*ms,(e[1]-ctr[1])*ms,(e[2]-ctr[2])*ms);
          const cr=(e[3]!=null?e[3]:0.549), cg=(e[4]!=null?e[4]:0.863), cb=(e[5]!=null?e[5]:1.0);   // shipData beam color (fallback engine cyan)
          beamOut.push(ox+w[0], oz+w[2], x2, z2, it, oy+w[1], ty, cr, cg, cb); beamCensus.drawn++; }   // emitter (full 3D incl. its Y) -> target: x1,z1,x2,z2, life, y1,y2, r,g,b
      }
    }
    const nbm=beamOut?Math.min((beamOut.length/10)|0,2048):0;
    if(nbm>0){ if(nbm>beamCap){ beamCap=Math.max(32,nbm*2); if(beamBuf) beamBuf.destroy(); beamBuf=device.createBuffer({size:beamCap*48,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); }
      const arr=new Float32Array(nbm*12); for(let i=0;i<nbm;i++){ const o=i*12, j=i*10;
        arr[o]=beamOut[j]; arr[o+1]=beamOut[j+1]; arr[o+2]=beamOut[j+2]; arr[o+3]=beamOut[j+3];
        arr[o+4]=beamOut[j+4]; arr[o+5]=beamOut[j+5]; arr[o+6]=beamOut[j+6];
        arr[o+8]=beamOut[j+7]; arr[o+9]=beamOut[j+8]; arr[o+10]=beamOut[j+9]; } device.queue.writeBuffer(beamBuf,0,arr);
      const bd=device.createBindGroup({layout:beamPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:6,resource:{buffer:beamBuf}}]}); p.setPipeline(beamPipe); p.setBindGroup(0,bd); p.draw(6,nbm);
      const td=device.createBindGroup({layout:impPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:6,resource:{buffer:beamBuf}}]}); p.setPipeline(impPipe); p.setBindGroup(0,td); p.draw(30,nbm); draws++; }
    const prj=b2&&b2.projectiles?b2.projectiles:null, npr=prj?Math.min(prj.length,1024):0;
    projCensus.now=npr;
    if(npr>projCensus.peak) projCensus.peak=npr;
    // Count LAUNCHES, not frame-samples: a torpedo alive 3s at 60fps would otherwise add ~180
    // to the total on its own, which makes the number unreadable. Rises in the in-flight count
    // are new launches (the stream carries no projectile id, so this is the honest approximation).
    if(npr>projCensus.prev) projCensus.launches+=(npr-projCensus.prev);
    projCensus.prev=npr;
    if(npr>0) projCensus.frames++;
    if(prj) for(const pp of prj){ if(pp[5]==null) projCensus.ynone=true; }
    if(prj && prj.length){ const q=prj[0], qy=(q[5]==null?0:q[5]);
      const _e=smEye||EYE||[0,0,0];   // the eye actually used for this frame's view matrix
      const ex=_e[0]-q[0], ey=_e[1]-qy, ez=_e[2]-q[1];
      projCensus.p0=`proj[0] ${q[2]} at ${q[0]|0},${qy|0},${q[1]|0} · ${Math.hypot(ex,ey,ez)|0}u from cam`;
    } else projCensus.p0="proj pos: (none in flight)";
    if(npr>0){ if(npr>projCap){ projCap=Math.max(32,npr*2); if(projBuf) projBuf.destroy(); projBuf=device.createBuffer({size:projCap*32,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); }
      // pp = [x, z, kind, dx, dz, y, dy]; y/dy are appended so older servers (5-element
      // records) still work -- they fall back to the y=0 plane rather than drawing nothing.
      const arr=new Float32Array(npr*8); for(let i=0;i<npr;i++){ const pp=prj[i], o=i*8; arr[o]=pp[0]; arr[o+1]=(pp[5]==null?0:pp[5]); arr[o+2]=pp[1]; arr[o+3]=(pp[2]==='drone')?1.0:0.0; arr[o+4]=(pp[3]==null?0:pp[3]); arr[o+5]=(pp[4]==null?0:pp[4]); } device.queue.writeBuffer(projBuf,0,arr);
      const pd=device.createBindGroup({layout:projPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:7,resource:{buffer:projBuf}}]}); p.setPipeline(projPipe); p.setBindGroup(0,pd); p.draw(6,npr); }
    p.end();
    if(tsw){ enc.resolveQuerySet(tsSet,0,2,tsResolve,0); enc.copyBufferToBuffer(tsResolve,0,tsRead,0,16); }
    device.queue.submit([enc.finish()]);
    if(tsw){ tsPending=true; tsRead.mapAsync(GPUMapMode.READ).then(()=>{
      const a=new BigInt64Array(tsRead.getMappedRange()); const ms=Number(a[1]-a[0])/1e6; tsRead.unmap();
      if(ms>0&&ms<1000) nebGpuMs=nebGpuMs*0.8+ms*0.2; tsPending=false; }).catch(()=>{tsPending=false;}); }
    fpsFrames++; { const now=performance.now(); if(now-fpsT>250){ fps=fps*0.6+(fpsFrames*1000/(now-fpsT))*0.4; fpsFrames=0; fpsT=now; } }
    const _fc=focusNpc?npcCount:playerCount, _fs=focusNpc?npcSel:shipSel, _fl=focusNpc?"npc":"ship";
    const shipNote=(mode==="chase")?`  ${_fl} ${_fc?(((_fs%_fc)+_fc)%_fc+1):0}/${_fc}`:"";
    const tArtList=[]; for(const [k,r] of artCache){ if((r.tCount||0)>0) tArtList.push(k); }   // terrain mesh arts actually rendering (asteroid check)
    // SHARE data story: N nebulae as cheap placements + K shared templates, vs N full unique definitions
    const effN=nebCount*nebStress, slabMB=nebBakedRES**3*8/1048576;
    const shareB=effN*32+NEB_K*32, uniqB=effN*64;   // 32B placement(+templateId) ; unique adds 32B shape params
    const fmtB=b=> b<1048576?(b/1024).toFixed(0)+"KB":(b/1048576).toFixed(1)+"MB";
    hud.textContent=`${fps.toFixed(0)} fps  ·  cam: ${mode}${note?"  "+note:""}${shipNote}`
      +`\n${tObjs} terrain · ${dynN} dyn · ${arts} arts · ${nebCount} neb`
      // terrain + beam censuses still tracked (terrainCensus / beamCensus) -- re-add their
      // lines here when hunting those; kept off-screen so the HUD stays readable.
      +`\n${draws} draws${loading?` · ${loading} art loading…`:``}`
      +`\nproj ${projCensus.now} in flight (peak ${projCensus.peak}) · ~${projCensus.launches} launched · y ${projCensus.ynone?"MISSING":"streamed"}  ['B'=zero]`
      // Where the first in-flight projectile actually IS, relative to the camera. If they are
      // streaming but unseen, this says whether they are off-screen / behind / miles away
      // rather than leaving it to guesswork.
      +`\n${projCensus.p0||"proj pos: -"}`
      +`\nfailed art[${artFailed.length}] ${artFailed.slice(0,4).map(a=>a===""?"(empty)":a).join(" ")||"(none)"}${artFailed.length?" -> placeholder":""}`
      +(planetCount||holeCount?`\nbodies: ${planetCount} planet${planetCount===1?"":"s"} · ${holeCount} black hole${holeCount===1?"":"s"}`:``)
      +`\nSHARE ${nebShare?"ON ":"OFF"} · ${logicalSlots}→${physicalSlots} slab${physicalSlots<logicalSlots?" ⚠cap":""} · ${nebBaked?"BAKED":"live"} · ${nebStepMode?`~${Math.round(1.9/NEB_STEP_FRAC)}`:nebSteps} steps · ${canTS?nebGpuMs.toFixed(2)+"ms/3D":"gpu n/a"}`
      +`\n data ${fmtB(shareB)} shared vs ${fmtB(uniqB)} unique = ${(uniqB/shareB).toFixed(1)}× less · N=${effN}${nebStress>1?` ×${nebStress}`:``} · cover ${nebCover}`
      +`\n vram ${physicalSlots}×${nebBakedRES}³=${(physicalSlots*slabMB).toFixed(1)}MB vs unique N=${effN}→${(effN*slabMB).toFixed(0)}MB (r16f ½)`
      +`\n'c'cam 'v'ship 'n'npc 'b'grid · neb: 's'share 'k'bake 'f'step 't'steps 'm'stress 'r'res 'x'cover · 'g'hide`;
  }
  function frame(){ try{ frameInner(); }catch(e){ wlog("frame error: "+(e&&e.message||e)); } requestAnimationFrame(frame); }   // one bad frame logs and retries, never black-screens
  requestAnimationFrame(frame);
  wlog("overlay active — real-mesh instancing by art; press 'g' to toggle");

  function bindOrbit(){
    let drag=false,px=0,py=0;
    canvas.addEventListener("pointerdown",e=>{drag=true;px=e.clientX;py=e.clientY;canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener("pointerup",()=>drag=false);
    canvas.addEventListener("pointermove",e=>{ if(!drag)return; yaw+=(e.clientX-px)*0.006; pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-py)*0.006)); px=e.clientX;py=e.clientY; chaseLocked=false; });   // dragging breaks the chase lock -> free orbit
    canvas.addEventListener("wheel",e=>{ e.preventDefault(); const f=1+Math.sign(e.deltaY)*0.08;
      if(MODES[modeIx]==="chase"){ chaseDist=Math.max(20, chaseDist*f); } else { dist=Math.max(200, dist*f); } },{passive:false});
    canvas.addEventListener("dblclick",e=>{ e.preventDefault(); if(MODES[modeIx]==="chase"){ recenterChase=true; chaseLocked=true; } });   // re-lock: snap behind + auto-follow the heading
  }
}

// ---- OBJ parse (v/vt/vn/triangulated f) -> interleaved pos,nrm,uv; CENTERED, native scale ----
function parseOBJ(text){
  const pos=[], uv=[], nrm=[], P=[], N=[], UV=[], idx=[], map=new Map(); let hadVN=false;
  for(const line of text.split("\n")){ const t=line.trim(); if(!t||t[0]==="#") continue; const s=t.split(/\s+/);
    if(s[0]==="v") pos.push([+s[1],+s[2],+s[3]]);
    else if(s[0]==="vt") uv.push([+s[1], 1-(+s[2])]);
    else if(s[0]==="vn"){ nrm.push([+s[1],+s[2],+s[3]]); hadVN=true; }
    else if(s[0]==="f"){ const f=[];
      for(let i=1;i<s.length;i++){ const tok=s[i]; let id=map.get(tok);
        if(id===undefined){ const a=tok.split("/"); const vi=(+a[0])-1, ti=a[1]?(+a[1])-1:-1, ni=a[2]?(+a[2])-1:-1;
          const p=pos[vi]||[0,0,0], tv=(ti>=0&&uv[ti])?uv[ti]:[0,0], nn=(ni>=0&&nrm[ni])?nrm[ni]:[0,0,0];
          id=P.length; P.push([p[0],p[1],p[2]]); N.push([nn[0],nn[1],nn[2]]); UV.push([tv[0],tv[1]]); map.set(tok,id); }
        f.push(id); }
      for(let k=1;k+1<f.length;k++){ idx.push(f[0],f[k],f[k+1]); } } }
  const nv=P.length;
  // Geometric normals when the OBJ has none (accumulate face normals) — else normal-mapping has no basis.
  if(!hadVN){ for(let i=0;i<nv;i++) N[i]=[0,0,0];
    for(let i=0;i<idx.length;i+=3){ const a=idx[i],b=idx[i+1],c=idx[i+2]; const fn=cr(sub(P[b],P[a]),sub(P[c],P[a]));
      for(const k of [a,b,c]){ N[k][0]+=fn[0]; N[k][1]+=fn[1]; N[k][2]+=fn[2]; } }
    for(let i=0;i<nv;i++){ const l=Math.hypot(N[i][0],N[i][1],N[i][2])||1; N[i]=[N[i][0]/l,N[i][1]/l,N[i][2]/l]; } }
  // Per-vertex tangents from UV gradients (accumulate T and bitangent B per triangle).
  const T=[], B=[]; for(let i=0;i<nv;i++){ T[i]=[0,0,0]; B[i]=[0,0,0]; }
  for(let i=0;i<idx.length;i+=3){ const a=idx[i],b=idx[i+1],c=idx[i+2]; const e1=sub(P[b],P[a]), e2=sub(P[c],P[a]);
    const du1=UV[b][0]-UV[a][0], dv1=UV[b][1]-UV[a][1], du2=UV[c][0]-UV[a][0], dv2=UV[c][1]-UV[a][1];
    const den=du1*dv2-du2*dv1, r=Math.abs(den)>1e-9?1/den:0;
    const t=[(e1[0]*dv2-e2[0]*dv1)*r,(e1[1]*dv2-e2[1]*dv1)*r,(e1[2]*dv2-e2[2]*dv1)*r];
    const bt=[(e2[0]*du1-e1[0]*du2)*r,(e2[1]*du1-e1[1]*du2)*r,(e2[2]*du1-e1[2]*du2)*r];
    for(const k of [a,b,c]){ T[k][0]+=t[0];T[k][1]+=t[1];T[k][2]+=t[2]; B[k][0]+=bt[0];B[k][1]+=bt[1];B[k][2]+=bt[2]; } }
  // Assemble stride-12 verts: pos3, nrm3, uv2, tan4 (Gram-Schmidt orthonormal T + handedness in .w).
  const v=new Float32Array(nv*12);
  for(let i=0;i<nv;i++){ const o=i*12, n=N[i]; let tx=T[i][0],ty=T[i][1],tz=T[i][2];
    const nd=n[0]*tx+n[1]*ty+n[2]*tz; tx-=n[0]*nd; ty-=n[1]*nd; tz-=n[2]*nd;
    const tl=Math.hypot(tx,ty,tz); if(tl>1e-6){ tx/=tl;ty/=tl;tz/=tl; } else { tx=1;ty=0;tz=0; }
    const hand=(dt(cr(n,[tx,ty,tz]),B[i])<0)?-1:1;
    v[o]=P[i][0];v[o+1]=P[i][1];v[o+2]=P[i][2]; v[o+3]=n[0];v[o+4]=n[1];v[o+5]=n[2];
    v[o+6]=UV[i][0];v[o+7]=UV[i][1]; v[o+8]=tx;v[o+9]=ty;v[o+10]=tz;v[o+11]=hand; }
  let cx=0,cy=0,cz=0; for(let i=0;i<nv;i++){ cx+=v[i*12];cy+=v[i*12+1];cz+=v[i*12+2]; } cx/=nv||1;cy/=nv||1;cz/=nv||1;
  for(let i=0;i<nv;i++){ v[i*12]-=cx; v[i*12+1]-=cy; v[i*12+2]-=cz; }   // center (keep native scale for meshscale)
  let md=1; for(let i=0;i<nv;i++){ md=Math.max(md, Math.hypot(v[i*12],v[i*12+1],v[i*12+2])); }
  return {v, i:new Uint32Array(idx), maxDim:md, center:[cx,cy,cz]};
}
function norml(v,fb){ const l=Math.hypot(v[0],v[1],v[2]); return l>1e-6?[v[0]/l,v[1]/l,v[2]/l]:fb; }
// flat annulus on the XZ plane (unit radius), interleaved (x,z) — for the ship/shield rings
function buildRing(inner, outer, seg){
  const v=[];
  for(let i=0;i<seg;i++){ const a0=i/seg*Math.PI*2, a1=(i+1)/seg*Math.PI*2;
    const c0=Math.cos(a0),s0=Math.sin(a0),c1=Math.cos(a1),s1=Math.sin(a1);
    v.push(c0*inner,s0*inner, c0*outer,s0*outer, c1*outer,s1*outer);
    v.push(c0*inner,s0*inner, c1*outer,s1*outer, c1*inner,s1*inner); }
  return new Float32Array(v);
}

// ---- mat4 (column-major, WebGPU z in [0,1]) ----
function perspective(fovy,aspect,near,far){ const f=1/Math.tan(fovy/2),nf=1/(near-far); return new Float32Array([f/aspect,0,0,0, 0,f,0,0, 0,0,far*nf,-1, 0,0,far*near*nf,0]); }
function lookAt(e,c,up){ const z=nrm(sub(e,c)),x=nrm(cr(up,z)),y=cr(z,x); return new Float32Array([x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0, -dt(x,e),-dt(y,e),-dt(z,e),1]); }
function mul(a,b){ const o=new Float32Array(16); for(let c=0;c<4;c++)for(let r=0;r<4;r++){ let s=0; for(let k=0;k<4;k++) s+=a[k*4+r]*b[c*4+k]; o[c*4+r]=s; } return o; }
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]], dt=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cr=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const nrm=v=>{ const l=Math.hypot(v[0],v[1],v[2])||1; return [v[0]/l,v[1]/l,v[2]/l]; };
