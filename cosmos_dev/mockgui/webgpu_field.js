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
  canvas.style.cssText="position:fixed;inset:0;width:100vw;height:100vh;z-index:2147483000;background:#05070c;display:block";
  document.body.appendChild(canvas);
  let visible=true; const MODES=["chase","orbit","cinematic"]; let modeIx=0, shipSel=0;
  let fps=60, fpsFrames=0, fpsT=performance.now();
  const hud=document.createElement("div");
  hud.style.cssText="position:fixed;top:10px;left:12px;z-index:2147483001;font:12px/1.5 ui-monospace,Consolas,monospace;color:#e7ebf2;background:rgba(10,12,17,.62);border:1px solid #232833;border-radius:8px;padding:8px 11px;pointer-events:none;white-space:pre";
  document.body.appendChild(hud);
  window.addEventListener("keydown",e=>{
    if(e.key==="g"){ visible=!visible; canvas.style.display=visible?"block":"none"; hud.style.display=visible?"block":"none"; }
    if(e.key==="c"){ modeIx=(modeIx+1)%MODES.length; }   // cycle chase -> orbit -> cinematic
    if(e.key==="v"){ shipSel++; }                        // cycle which player ship the chase follows
  });

  const adapter=await navigator.gpu.requestAdapter({powerPreference:"high-performance"});
  if(!adapter){ wlog("no adapter"); return; }
  const device=await adapter.requestDevice();
  const ctx=canvas.getContext("webgpu"); const format=navigator.gpu.getPreferredCanvasFormat();
  ctx.configure({device,format,alphaMode:"opaque"});

  const WGSL=`
  struct U { vp:mat4x4<f32>, camDir:vec4f, camRight:vec4f, camUp:vec4f, camPos:vec4f };   // camDir.w=tan(fov/2), camRight.w=aspect
  struct Inst { pr:vec4f, q:vec4f };                 // pos.xyz,scale | quaternion
  @group(0) @binding(0) var<uniform> u:U;
  @group(0) @binding(1) var<storage,read> insts:array<Inst>;
  @group(1) @binding(0) var tex:texture_2d<f32>;
  @group(1) @binding(1) var samp:sampler;
  fn qrot(q:vec4f,v:vec3f)->vec3f{ let t=2.0*cross(q.xyz,v); return v+q.w*t+cross(q.xyz,t); }
  struct VO { @builtin(position) pos:vec4f, @location(0) nrm:vec3f, @location(1) uv:vec2f };
  @vertex fn vs(@location(0) inPos:vec3f, @location(1) inNrm:vec3f, @location(2) inUv:vec2f, @builtin(instance_index) ii:u32)->VO{
    let it=insts[ii];
    let world=it.pr.xyz + qrot(it.q, inPos*it.pr.w);
    var o:VO; o.pos=u.vp*vec4f(world,1.0); o.nrm=normalize(qrot(it.q, inNrm)); o.uv=inUv; return o;
  }
  @fragment fn fs(in:VO)->@location(0) vec4f{
    let n=normalize(in.nrm); let L=normalize(vec3f(0.5,0.7,0.4)); let nl=max(dot(n,L),0.0);
    let fill=max(dot(n,normalize(vec3f(-0.4,-0.2,0.6))),0.0)*0.25;
    let alb=textureSample(tex,samp,in.uv).rgb;
    return vec4f(pow(alb*(0.22+nl*0.95+fill), vec3f(1.0/2.2)), 1.0);
  }
  // ---- procedural starfield background (drawn behind, camera-relative) ----
  fn hash13(p3in:vec3f)->f32{ var p3=fract(p3in*0.1031); p3=p3+dot(p3,p3.zyx+31.32); return fract((p3.x+p3.y)*p3.z); }
  fn skyd(rd:vec3f)->vec3f{
    var col=vec3f(0.0);
    let p=rd*320.0; let id=floor(p); let f=fract(p)-0.5; let h=hash13(id);
    if(h>0.94){ col=col+vec3f(smoothstep(0.5,0.0,length(f))*(h-0.94)/0.06)*mix(vec3f(0.7,0.8,1.0),vec3f(1.0,0.9,0.75),hash13(id+7.0))*2.8; }
    let p2=rd*90.0; let id2=floor(p2); let f2=fract(p2)-0.5; let h2=hash13(id2+3.0);
    if(h2>0.985){ col=col+vec3f(smoothstep(0.5,0.0,length(f2)))*mix(vec3f(0.9,0.95,1.0),vec3f(1.0,0.85,0.7),hash13(id2))*3.2; }
    let up=rd.y*0.5+0.5; let band=exp(-abs(rd.y)*3.0)*0.05;
    col=col+mix(vec3f(0.02,0.024,0.04),vec3f(0.032,0.03,0.052),up)+vec3f(0.05,0.04,0.07)*band;
    return col; }
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
    return vec4f(skyd(dir),1.0); }
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
  fn spiral(pin:vec3f)->f32{ var p=pin; var n=0.0; var it=1.0; for(var i=0;i<5;i=i+1){ n=n-abs(sin(p.y*it)+cos(p.x*it))/it; let a=(p.xy+vec2f(p.y,-p.x)*0.739513)*0.80406839; p=vec3f(a.x,a.y,p.z); let b=(p.xz+vec2f(p.z,-p.x)*0.739513)*0.80406839; p=vec3f(b.x,p.y,b.y); it=it*1.733733; } return n; }
  fn rotY(p:vec3f,s:f32)->vec3f{ let c=cos(s); let si=sin(s); return vec3f(p.x*c+p.z*si,p.y,-p.x*si+p.z*c); }
  fn nebDensity(posIn:vec3f, density:f32, seed:f32, swirl:f32, warp:f32)->f32{
    var pos=posIn; let rr=length(pos); let f=exp(-rr*1.3); let ff=f*f; var p=ff*density;
    if(p<=0.3*density){ return -1.0; }
    p=p+spiral(vec3f(512.0+seed)+pos*8.0)*0.75;
    if(swirl!=0.0){ pos=rotY(pos, pos.y*spiral(pos*4.0)*swirl); }
    p=p+spiral(vec3f(200.0+seed)+pos*3.0)*0.6;
    pos=pos+abs(snoisen(pos*4.0))*warp;
    p=p*ff;
    if(p<0.15*density){ p=p-abs(snoisen(vec3f(seed)+pos*8.0))*1.5; }
    return p;
  }
  struct Neb { c:vec4f, col:vec4f, sd:vec4f };
  @group(0) @binding(4) var<storage,read> nebs:array<Neb>;
  struct NVO { @builtin(position) pos:vec4f, @location(0) @interpolate(flat) inst:u32, @location(1) rd:vec3f };
  @vertex fn nvs(@builtin(vertex_index) vi:u32, @builtin(instance_index) ii:u32)->NVO{
    let nb=nebs[ii]; let center=nb.c.xyz; let radius=nb.c.w;
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
    let nb=nebs[in.inst]; let R=nb.c.w; let rd=normalize(in.rd);
    let ro=u.camPos.xyz-nb.c.xyz; let bb=dot(rd,ro); let cc=dot(ro,ro)-(R*0.98)*(R*0.98); let disc=bb*bb-cc;
    if(disc<0.0){ return vec4f(0.0); }
    let sq=sqrt(disc); let t0=max(-bb-sq,0.0); let t1=-bb+sq; if(t1<=t0){ return vec4f(0.0); }
    let dS=(t1-t0)/26.0; let emis=nb.col.rgb; let density=nb.col.w; let seed=nb.sd.x;
    var t=t0; var trans=1.0; var acc=vec3f(0.0);
    for(var i=0;i<26;i=i+1){ let n=(ro+rd*t)/R; let d=nebDensity(n, density, seed, nb.sd.y, nb.sd.z);
      if(d>0.02){ acc=acc+emis*d*trans*0.03; trans=trans*exp(-d*dS/R*4.0); if(trans<0.02){ break; } }
      t=t+dS; }
    return vec4f(acc, 0.0);
  }`;
  const mod=device.createShaderModule({code:WGSL});
  const info=await mod.getCompilationInfo(); const es=info.messages.filter(m=>m.type==="error");
  if(es.length){ wlog("WGSL: "+es.map(x=>`[${x.lineNum}] ${x.message}`).join(" | ")); return; }
  const ubuf=device.createBuffer({size:8*16, usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  const samp=device.createSampler({magFilter:"linear",minFilter:"linear",addressModeU:"repeat",addressModeV:"repeat"});
  const pipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"vs", buffers:[{arrayStride:32, attributes:[
      {shaderLocation:0,offset:0,format:"float32x3"},{shaderLocation:1,offset:12,format:"float32x3"},{shaderLocation:2,offset:24,format:"float32x2"}]}]},
    fragment:{module:mod,entryPoint:"fs",targets:[{format}]}, primitive:{topology:"triangle-list",cullMode:"none"},
    depthStencil:{format:"depth24plus",depthWriteEnabled:true,depthCompare:"less"}});
  const bgPipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"vbg"}, fragment:{module:mod,entryPoint:"fbg",targets:[{format}]}, primitive:{topology:"triangle-list"},
    depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"always"}});
  const nebPipe=device.createRenderPipeline({layout:"auto",
    vertex:{module:mod,entryPoint:"nvs"}, fragment:{module:mod,entryPoint:"nfs",targets:[{format, blend:{color:{srcFactor:"one",dstFactor:"one",operation:"add"},alpha:{srcFactor:"one",dstFactor:"one",operation:"add"}}}]},
    primitive:{topology:"triangle-list"}, depthStencil:{format:"depth24plus",depthWriteEnabled:false,depthCompare:"less"}});
  let nebBuf=null, nebCap=0;

  // fallback gray texture (art without a diffuse map)
  const grayTex=device.createTexture({size:[1,1],format:"rgba8unorm-srgb",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
  device.queue.writeTexture({texture:grayTex},new Uint8Array([130,120,110,255]),{bytesPerRow:4},[1,1]);

  // real engine cube-cross skybox, loaded by name (falls back to procedural stars until ready)
  let skyTex=device.createTexture({size:[1,1],format:"rgba8unorm-srgb",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
  device.queue.writeTexture({texture:skyTex},new Uint8Array([2,3,8,255]),{bytesPerRow:4},[1,1]);
  let skyView=skyTex.createView(), skyReady=false, lastSky=null;
  const skySamp=device.createSampler({magFilter:"linear",minFilter:"linear",addressModeU:"clamp-to-edge",addressModeV:"clamp-to-edge"});
  async function loadSky(name){
    const base=String(name).split(/[\\/]/).pop();
    try{ const img=new Image(); img.src='/'+base+'.png'; await img.decode(); const bmp=await createImageBitmap(img);
      const t=device.createTexture({size:[bmp.width,bmp.height],format:"rgba8unorm-srgb",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
      device.queue.copyExternalImageToTexture({source:bmp},{texture:t},[bmp.width,bmp.height]);
      const old=skyTex; skyTex=t; skyView=t.createView(); skyReady=true; if(old) old.destroy(); wlog("skybox loaded: "+base+" ("+bmp.width+"x"+bmp.height+")");
    }catch(e){ skyReady=false; wlog("skybox load failed: "+base+" — "+(e&&e.message||e)); }
  }

  // ---- real-art loader (cached by art root), self-contained fetch of the mock's /ships/ files ----
  const artCache=new Map();   // art -> {status:'loading'|'ready'|'failed', vb, ib, count, bind}
  function loadArt(art){
    if(artCache.has(art)) return artCache.get(art);
    const rec={status:"loading"}; artCache.set(art,rec);
    (async()=>{
      try{
        const r=await fetch('/ships/'+art+'.obj'); if(!r.ok) throw new Error(r.status+" "+art);
        const mesh=parseOBJ(await r.text());
        rec.vb=device.createBuffer({size:mesh.v.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST}); device.queue.writeBuffer(rec.vb,0,mesh.v);
        rec.ib=device.createBuffer({size:mesh.i.byteLength,usage:GPUBufferUsage.INDEX|GPUBufferUsage.COPY_DST}); device.queue.writeBuffer(rec.ib,0,mesh.i);
        rec.count=mesh.i.length; rec.maxDim=mesh.maxDim||60;
        let view=grayTex.createView();
        try{ const img=new Image(); img.src='/ships/'+art+'_diffuse.png'; await img.decode(); const bmp=await createImageBitmap(img);
          const t=device.createTexture({size:[bmp.width,bmp.height],format:"rgba8unorm-srgb",usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});
          device.queue.copyExternalImageToTexture({source:bmp},{texture:t},[bmp.width,bmp.height]); view=t.createView();
        }catch(e){}
        rec.bind=device.createBindGroup({layout:pipe.getBindGroupLayout(1),entries:[{binding:0,resource:view},{binding:1,resource:samp}]});
        rec.instBuf=null; rec.instCap=0; rec.status="ready";
      }catch(e){ rec.status="failed"; wlog("art load failed: "+art+" — "+(e&&e.message||e)); }
    })();
    return rec;
  }

  // ---- gather live objects (terrain + dynamic) grouped by art, matching the mock's transform ----
  // Per-art instance data lives on each artCache rec: rec.tInst/tCount (terrain=STATIC, uploaded only
  // when terrainVersion changes) + rec.dInst/dCount (dynamic=per-frame). This is the delta win: the
  // bulk (asteroid/nebula field) is sent once, not every frame — only the few moving ships re-upload.
  let terrainVer=-1; const nebArr=[]; let nebCount=0; let fcx=0,fcz=0,fmeanR=1;
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
  function gatherTerrain(b){                    // STATIC — only re-run when terrainVersion changes
    const lists=new Map(); nebArr.length=0; let sx=0,sz=0,cnt=0;
    if(b.terrainPos) for(let i=0;i<(b.terrainCount|0);i++){
      const id=b.terrainRev&&b.terrainRev.get?b.terrainRev.get(i):undefined; if(id===undefined) continue;
      const m=b.terrainMeta.get(id); if(!m) continue;
      const x=b.terrainPos[i*3], z=b.terrainPos[i*3+1], y=m.y||0;
      if(m.nebula){ const c=m.color||[0.55,0.5,0.85]; nebArr.push(x,y,z, Math.max(200,m.radius||2000), c[0],c[1],c[2], m.density||7, m.seed||1, m.swirl||0, m.warp||0, 0); continue; }
      if(m.icon_index!=null || !m.art) continue;
      let arr=lists.get(m.art); if(!arr){ arr=[]; lists.set(m.art,arr); } packObj(arr,x,y,z,m); sx+=x; sz+=z; cnt++;
    }
    for(const rec of artCache.values()) rec.tCount=0;
    for(const [art,arr] of lists){ ensureInst(loadArt(art),"t",arr); }
    nebCount=nebArr.length/12;
    if(nebCount>0){ if(nebCount>nebCap){ nebCap=Math.max(16,nebCount*2); if(nebBuf) nebBuf.destroy(); nebBuf=device.createBuffer({size:nebCap*48,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}); } device.queue.writeBuffer(nebBuf,0,new Float32Array(nebArr)); }
    fcx=cnt?sx/cnt:0; fcz=cnt?sz/cnt:0; let sr=0,mm=0; for(const arr of lists.values()){ for(let i=0;i<arr.length;i+=8){ sr+=Math.hypot(arr[i]-fcx, arr[i+2]-fcz); mm++; } } fmeanR=Math.max(1, mm?sr/mm:1);
  }
  const smDyn=new Map();   // id -> [x,y,z] smoothed dynamic position (60fps ease over the mock's 30Hz push -> no jitter)
  function gatherDyn(b){                        // DYNAMIC — every frame (few, moving)
    const lists=new Map(); let n=0; const seen=new Set();
    if(b.dynPos) for(let i=0;i<(b.dynCount|0);i++){
      const id=b.dynRev&&b.dynRev.get?b.dynRev.get(i):undefined; if(id===undefined) continue;
      const m=b.dynMeta.get(id); if(!m||!m.art||m.nebula||m.icon_index!=null) continue;
      seen.add(id);
      const tx=b.dynPos[i*3], tz=b.dynPos[i*3+1], ty=m.y||0;
      let s=smDyn.get(id);
      if(!s){ s={r:[tx,ty,tz], b:[tx,ty,tz], v:[0,0,0], still:0}; smDyn.set(id,s); }
      else {                                  // dead-reckoning: estimate velocity per push, extrapolate between them
        if(tx!==s.b[0]||ty!==s.b[1]||tz!==s.b[2]){ const dt=Math.max(1,s.still); s.v[0]=(tx-s.b[0])/dt; s.v[1]=(ty-s.b[1])/dt; s.v[2]=(tz-s.b[2])/dt; s.b[0]=tx; s.b[1]=ty; s.b[2]=tz; s.still=0; }
        else s.still++;
        const st=Math.min(s.still,20), k=0.5;   // ease toward the *extrapolated* (smoothly-moving) target -> smooth + no lag
        s.r[0]+=((s.b[0]+s.v[0]*st)-s.r[0])*k; s.r[1]+=((s.b[1]+s.v[1]*st)-s.r[1])*k; s.r[2]+=((s.b[2]+s.v[2]*st)-s.r[2])*k;
      }
      let arr=lists.get(m.art); if(!arr){ arr=[]; lists.set(m.art,arr); } packObj(arr,s.r[0],s.r[1],s.r[2],m); n++;
    }
    for(const id of smDyn.keys()) if(!seen.has(id)) smDyn.delete(id);
    for(const rec of artCache.values()) rec.dCount=0;
    for(const [art,arr] of lists){ ensureInst(loadArt(art),"d",arr); }
    return n;
  }
  // the client's own ship (by _myShipId, else first PLAYER-type) — for the chase camera
  let playerCount=0;
  function findPlayer(b){
    if(!b||!b.dynPos||!b.dynMeta) return null;
    const pick=(id)=>{ if(id==null) return null; const idx=b.dynMap&&b.dynMap.get?b.dynMap.get(id):undefined; if(idx===undefined||idx>=(b.dynCount|0)) return null;
      const mm=b.dynMeta.get(id); if(!mm) return null; const s=smDyn.get(id);   // dead-reckoned pos so the chase cam doesn't jitter
      return {x:s?s.r[0]:b.dynPos[idx*3], y:s?s.r[1]:(mm.y||0), z:s?s.r[2]:b.dynPos[idx*3+1], fx:mm.fx||0, fz:mm.fz||0, art:mm.art||"", sc:mm.meshscale||1}; };
    const players=[]; for(const [id,mm] of b.dynMeta){ if(mm.tick_type==="PLAYER"||mm.tick_type==="player") players.push(id); }
    playerCount=players.length;
    let id = players.length ? players[((shipSel%players.length)+players.length)%players.length] : b.myShipId;
    let p=pick(id);
    if(!p && b.myShipId!=null) p=pick(b.myShipId);
    return p;
  }

  let W=1,H=1,depthTex=null,depthView=null;
  let yaw=0.6, pitch=0.4, dist=1, cx=0,cz=0, framed=false;
  let smEye=null, smTgt=null, smMode=null;   // smoothed following camera (glue-follow through 30Hz jumps)
  bindOrbit();
  function ensure(){ const dpr=Math.min(devicePixelRatio||1,2); const w=Math.max(1,(canvas.clientWidth*dpr)|0), h=Math.max(1,(canvas.clientHeight*dpr)|0);
    if(w===W&&h===H&&depthTex) return; W=w;H=h; canvas.width=W; canvas.height=H;
    if(depthTex) depthTex.destroy(); depthTex=device.createTexture({size:[W,H],format:"depth24plus",usage:GPUTextureUsage.RENDER_ATTACHMENT}); depthView=depthTex.createView(); }

  function frame(){
    if(!visible){ requestAnimationFrame(frame); return; }
    ensure();
    const b2=bridge();
    const skyName=b2?b2.skyName:null;
    if(skyName && skyName!==lastSky){ lastSky=skyName; loadSky(skyName); }
    else if(!skyName && lastSky){ lastSky=null; skyReady=false; }
    let dynN=0;
    if(b2){ const tv=b2.terrainVersion|0; if(tv!==terrainVer){ terrainVer=tv; gatherTerrain(b2); } dynN=gatherDyn(b2); }
    let tObjs=0; for(const rec of artCache.values()) tObjs+=(rec.tCount||0);
    const g={ n:tObjs+dynN, meanR:fmeanR };
    if(g.n>0){ cx=fcx; cz=fcz; if(!framed){ dist=g.meanR*2.5+2000; framed=true; } }
    const player=findPlayer(b2);
    let want=MODES[modeIx];
    if(want==="chase" && !player) want="orbit";
    if(want==="cinematic" && !(b2 && Array.isArray(b2.cam) && Array.isArray(b2.tgt))) want="orbit";
    let mode=want, note="", EYE,TGT,FOVY,NEAR,FAR;
    if(want==="chase"){                          // behind the player ship, sized to the ship — a real scale reference
      const fwd=norml([player.fx,0,player.fz],[0,0,1]);
      const rec=player.art?artCache.get(player.art):null; const md=(rec&&rec.status==="ready"&&rec.maxDim)?rec.maxDim:60;
      const size=Math.max(1, md*(player.sc||1)); note=`ship ~${(size*2)|0}u`;
      const back=size*7, up=size*2.5, ahead=size*3, sp=[player.x,player.y,player.z];
      EYE=[sp[0]-fwd[0]*back, sp[1]+up, sp[2]-fwd[2]*back];
      TGT=[sp[0]+fwd[0]*ahead, sp[1], sp[2]+fwd[2]*ahead];
      FOVY=50*Math.PI/180; NEAR=Math.max(2,size*0.2); FAR=size*500+g.meanR*4+1e5;
    } else if(want==="cinematic"){               // the mock's own cinematic camera (55deg, _v3dCam -> _v3dTgt)
      EYE=b2.cam.slice(); TGT=b2.tgt.slice(); const d=Math.max(1,Math.hypot(EYE[0]-TGT[0],EYE[1]-TGT[1],EYE[2]-TGT[2]));
      FOVY=55*Math.PI/180; NEAR=Math.max(5,d*0.02); FAR=d*6+g.meanR*6+1e5;
    } else {                                     // free orbit around the object bulk (drag/wheel)
      const cp=Math.cos(pitch),sp=Math.sin(pitch),cyw=Math.cos(yaw),syw=Math.sin(yaw);
      EYE=[cx+cp*syw*dist, sp*dist, cz+cp*cyw*dist]; TGT=[cx,0,cz];
      FOVY=50*Math.PI/180; NEAR=Math.max(10,dist*0.02); FAR=dist*4+g.meanR*6+1e5;
    }
    // smooth the following cameras (chase/cinematic) so they glue to the ship through 30Hz jumps + heading swings; orbit snaps (user-driven)
    if(smMode!==want || !smEye){ smMode=want; smEye=EYE.slice(); smTgt=TGT.slice(); }
    if(want==="orbit"){ smEye=EYE.slice(); smTgt=TGT.slice(); }
    else { const L=0.3; for(let i=0;i<3;i++){ smEye[i]+=(EYE[i]-smEye[i])*L; smTgt[i]+=(TGT[i]-smTgt[i])*L; } }
    EYE=smEye; TGT=smTgt;
    const aspect=W/H, th=Math.tan(FOVY/2);
    const fwd=norml(sub(TGT,EYE),[0,0,1]), right=norml(cr(fwd,[0,1,0]),[1,0,0]), up=cr(right,fwd);
    const vp=mul(perspective(FOVY,aspect,NEAR,FAR), lookAt(EYE,TGT,[0,1,0]));
    const uf=new Float32Array(32); uf.set(vp,0); uf.set([fwd[0],fwd[1],fwd[2],th],16); uf.set([right[0],right[1],right[2],aspect],20); uf.set([up[0],up[1],up[2], skyReady?1:0],24); uf.set([EYE[0],EYE[1],EYE[2],0],28);
    device.queue.writeBuffer(ubuf,0,uf);

    const enc=device.createCommandEncoder();
    const p=enc.beginRenderPass({colorAttachments:[{view:ctx.getCurrentTexture().createView(),clearValue:{r:0.02,g:0.03,b:0.05,a:1},loadOp:"clear",storeOp:"store"}],
      depthStencilAttachment:{view:depthView,depthClearValue:1.0,depthLoadOp:"clear",depthStoreOp:"store"}});
    const bindBg=device.createBindGroup({layout:bgPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:2,resource:skyView},{binding:3,resource:skySamp}]});
    p.setPipeline(bgPipe); p.setBindGroup(0,bindBg); p.draw(3);   // real skybox if loaded, else procedural starfield
    p.setPipeline(pipe);
    let draws=0, drawn=0, arts=0, loading=0;
    for(const [art,rec] of artCache){
      if(rec.status!=="ready"){ if(rec.status==="loading") loading++; continue; }
      const tc=rec.tCount||0, dc=rec.dCount||0; if(tc+dc===0) continue; arts++;
      p.setBindGroup(1,rec.bind); p.setVertexBuffer(0,rec.vb); p.setIndexBuffer(rec.ib,"uint32");
      if(tc>0){ const b0=device.createBindGroup({layout:pipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:1,resource:{buffer:rec.tInst}}]}); p.setBindGroup(0,b0); p.drawIndexed(rec.count,tc,0,0,0); draws++; drawn+=tc; }
      if(dc>0){ const b0=device.createBindGroup({layout:pipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:1,resource:{buffer:rec.dInst}}]}); p.setBindGroup(0,b0); p.drawIndexed(rec.count,dc,0,0,0); draws++; drawn+=dc; }
    }
    // volumetric nebulae (additive, depth-tested so meshes occlude them) — persistent buffer
    if(nebCount>0){ const nb=device.createBindGroup({layout:nebPipe.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:ubuf}},{binding:4,resource:{buffer:nebBuf}}]});
      p.setPipeline(nebPipe); p.setBindGroup(0,nb); p.draw(6,nebCount); draws++; }
    p.end(); device.queue.submit([enc.finish()]);
    fpsFrames++; { const now=performance.now(); if(now-fpsT>250){ fps=fps*0.6+(fpsFrames*1000/(now-fpsT))*0.4; fpsFrames=0; fpsT=now; } }
    const shipNote=(mode==="chase"&&playerCount>1)?`  ship ${((shipSel%playerCount)+playerCount)%playerCount+1}/${playerCount}`:"";
    hud.textContent=`${fps.toFixed(0)} fps  ·  cam: ${mode}${note?"  "+note:""}${shipNote}`
      +`\n${g.n} objects · ${arts} art types · ${nebCount} nebulae`
      +`\n${draws} draws (terrain static)${loading?` · ${loading} art loading…`:``}`
      +`\n'c' cam · 'v' ship · drag+wheel · 'g' hide`;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  wlog("overlay active — real-mesh instancing by art; press 'g' to toggle");

  function bindOrbit(){
    let drag=false,px=0,py=0;
    canvas.addEventListener("pointerdown",e=>{drag=true;px=e.clientX;py=e.clientY;canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener("pointerup",()=>drag=false);
    canvas.addEventListener("pointermove",e=>{ if(!drag)return; yaw+=(e.clientX-px)*0.006; pitch=Math.max(-1.4,Math.min(1.4,pitch+(e.clientY-py)*0.006)); px=e.clientX;py=e.clientY; });
    canvas.addEventListener("wheel",e=>{ e.preventDefault(); dist=Math.max(200, dist*(1+Math.sign(e.deltaY)*0.08)); },{passive:false});
  }
}

// ---- OBJ parse (v/vt/vn/triangulated f) -> interleaved pos,nrm,uv; CENTERED, native scale ----
function parseOBJ(text){
  const pos=[], uv=[], nrm=[], verts=[], idx=[], map=new Map();
  for(const line of text.split("\n")){ const t=line.trim(); if(!t||t[0]==="#") continue; const s=t.split(/\s+/);
    if(s[0]==="v") pos.push([+s[1],+s[2],+s[3]]);
    else if(s[0]==="vt") uv.push([+s[1], 1-(+s[2])]);
    else if(s[0]==="vn") nrm.push([+s[1],+s[2],+s[3]]);
    else if(s[0]==="f"){ const f=[];
      for(let i=1;i<s.length;i++){ const tok=s[i]; let id=map.get(tok);
        if(id===undefined){ const a=tok.split("/"); const vi=(+a[0])-1, ti=a[1]?(+a[1])-1:-1, ni=a[2]?(+a[2])-1:-1;
          const P=pos[vi]||[0,0,0], T=(ti>=0&&uv[ti])?uv[ti]:[0,0], Nn=(ni>=0&&nrm[ni])?nrm[ni]:[0,1,0];
          id=verts.length/8; verts.push(P[0],P[1],P[2],Nn[0],Nn[1],Nn[2],T[0],T[1]); map.set(tok,id); }
        f.push(id); }
      for(let k=1;k+1<f.length;k++){ idx.push(f[0],f[k],f[k+1]); } } }
  const v=new Float32Array(verts); const n=v.length/8;
  let cx=0,cy=0,cz=0; for(let i=0;i<n;i++){ cx+=v[i*8];cy+=v[i*8+1];cz+=v[i*8+2]; } cx/=n||1;cy/=n||1;cz/=n||1;
  for(let i=0;i<n;i++){ v[i*8]-=cx; v[i*8+1]-=cy; v[i*8+2]-=cz; }   // center only (keep native scale for meshscale)
  let md=1; for(let i=0;i<n;i++){ md=Math.max(md, Math.hypot(v[i*8],v[i*8+1],v[i*8+2])); }   // native radius (for chase-cam sizing)
  return {v, i:new Uint32Array(idx), maxDim:md};
}
function norml(v,fb){ const l=Math.hypot(v[0],v[1],v[2]); return l>1e-6?[v[0]/l,v[1]/l,v[2]/l]:fb; }

// ---- mat4 (column-major, WebGPU z in [0,1]) ----
function perspective(fovy,aspect,near,far){ const f=1/Math.tan(fovy/2),nf=1/(near-far); return new Float32Array([f/aspect,0,0,0, 0,f,0,0, 0,0,far*nf,-1, 0,0,far*near*nf,0]); }
function lookAt(e,c,up){ const z=nrm(sub(e,c)),x=nrm(cr(up,z)),y=cr(z,x); return new Float32Array([x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0, -dt(x,e),-dt(y,e),-dt(z,e),1]); }
function mul(a,b){ const o=new Float32Array(16); for(let c=0;c<4;c++)for(let r=0;r<4;r++){ let s=0; for(let k=0;k<4;k++) s+=a[k*4+r]*b[c*4+k]; o[c*4+r]=s; } return o; }
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]], dt=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cr=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const nrm=v=>{ const l=Math.hypot(v[0],v[1],v[2])||1; return [v[0]/l,v[1]/l,v[2]/l]; };
