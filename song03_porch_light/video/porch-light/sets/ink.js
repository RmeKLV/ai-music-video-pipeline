// ink.js: "Midnight Linework" rendering. Two palettes, chosen per fragment:
//   NIGHT (inside the dome, or everywhere when U.night = 1): navy fills, glowing gold lines
//   DAY   (outside): cream paper fills, navy ink lines
// Lines are instanced screen-space ribbons (crisp at any distance); fills are flat cel-shaded meshes.
// All animation goes through uniforms set from t (pure function of time).
import * as THREE from 'three';
import { mulberry32 } from '../lib/motion.js';

export { THREE };
const C = (h) => new THREE.Color(h);

// shared uniforms (one object, referenced by every material)
export const U = {
  uDomeC: { value: new THREE.Vector3(0, 0, -7) },
  uDomeR: { value: 26 },
  uSoft: { value: 0.25 },
  uInDay: { value: 0 },
  uDawn: { value: 0 },             // 0..1 the whole night washes to day (bridge)            // 1 = from inside the dome, still show the daylight beyond its edge (bridge)
  uNight: { value: 0 },            // 1 = the whole world is night (final chorus)
  uRes: { value: new THREE.Vector2(1920, 1080) },
  uTime: { value: 0 },
  uGlow: { value: 1.0 },           // gold line intensity (pulses with the music)
  uFogN: { value: 90 }, uFogF: { value: 900 },
  uDayInk: { value: C('#1c2547') }, uDayPaper: { value: C('#efe3c8') },
  uNightGold: { value: C('#f0bf6c') }, uNightNavy: { value: C('#0b1330') },
  uRim: { value: 1.0 },            // shimmer on the dome boundary
};

export const COMMON = /* glsl */`
uniform vec3 uDomeC; uniform float uDomeR, uSoft, uNight, uTime, uFogN, uFogF, uRim, uInDay, uDawn;
uniform vec3 uDayInk, uDayPaper, uNightGold, uNightNavy;
float nightAt0(vec3 p);
float nightAt(vec3 p) { return nightAt0(p) * (1.0 - uDawn); }
float nightAt0(vec3 p) {
  float d = length(p - uDomeC);
  float inside = (1.0 - smoothstep(uDomeR - uSoft, uDomeR + uSoft, d));
  // seen from outside, everything the view ray passes THROUGH the dome is night too (a solid hemisphere)
  vec3 oc = cameraPosition - uDomeC;
  // how far the camera is inside: fades over the last 4 m of travel so crossing the edge never pops
  float camIn = (1.0 - smoothstep(uDomeR - 4.0, uDomeR, length(oc))) * (1.0 - uInDay);
  {
    vec3 rd = p - cameraPosition; float tmax = length(rd); rd /= tmax;
    float b = dot(oc, rd), c = dot(oc, oc) - uDomeR * uDomeR, h = b * b - c;
    if (h > 0.0) { float sq = sqrt(h); float t0 = max(-b - sq, 0.0), t1 = min(-b + sq, tmax); inside = max(inside, smoothstep(0.0, 1.5, t1 - t0)); }
  }
  return max(uNight, mix(inside, 1.0, camIn));
}
float rimAt(vec3 p) {
  float d = abs(length(p - uDomeC) - uDomeR);
  return uRim * (1.0 - uNight) * exp(-d * d * 1.2) * 0.45;
}
`;

// ------------------------------------------------------------------ lines
const LINE_VS = /* glsl */`
${COMMON}
uniform float uSway;
vec3 sway(vec3 p) {   // wind: bends with height, slow gusts travelling across the valley
  float h = max(p.y, 0.0);
  float g = sin(uTime * 0.9 + p.x * 0.045 + p.z * 0.06) * 0.6 + sin(uTime * 2.1 + p.x * 0.13 - p.z * 0.09) * 0.25;
  return p + vec3(g * 0.028, 0.0, g * 0.018) * h * uSway;
}

attribute vec3 iA; attribute vec3 iB; attribute float iW; attribute float iK;
uniform vec2 uRes; uniform float uWidth, uPersp;
varying vec3 vW; varying float vK; varying float vSide; varying float vDepth; varying float vCover; varying float vHalf;
void main() {
  vec4 wa = modelMatrix * vec4(iA, 1.0), wb = modelMatrix * vec4(iB, 1.0);
  wa.xyz = sway(wa.xyz); wb.xyz = sway(wb.xyz);
  vec4 va = viewMatrix * wa, vb = viewMatrix * wb;
  float nearZ = -0.05;
  if (va.z > nearZ && vb.z > nearZ) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  if (va.z > nearZ) { float f = (nearZ - vb.z) / (va.z - vb.z); va = mix(vb, va, f); wa = mix(wb, wa, f); }
  if (vb.z > nearZ) { float f = (nearZ - va.z) / (vb.z - va.z); vb = mix(va, vb, f); wb = mix(wa, wb, f); }
  vec4 ca = projectionMatrix * va, cb = projectionMatrix * vb;
  vec2 sa = ca.xy / ca.w * uRes * 0.5, sb = cb.xy / cb.w * uRes * 0.5;
  vec2 dir = sb - sa; float L = length(dir); dir = L > 1e-5 ? dir / L : vec2(1.0, 0.0);
  vec2 nrm = vec2(-dir.y, dir.x);
  float end = position.x;               // 0 at A, 1 at B
  vec4 c = end < 0.5 ? ca : cb;
  float z = end < 0.5 ? -va.z : -vb.z;
  float w = uWidth * iW * mix(1.0, clamp(uPersp / max(z, 0.1), 0.25, 6.0), step(0.5, uPersp));
  // w = half width in px. Thin lines stay 1 px wide and fade by coverage instead of shimmering.
  float cover = clamp(w / 0.5, 0.15, 1.0);
  w = max(w, 0.5);
  float wq = w + 1.0;                       // quad grows by a 1 px feather on each side
  vec2 off = nrm * position.y * wq + dir * (end < 0.5 ? -1.0 : 1.0) * w * 0.5 * (iK > 0.5 ? 0.0 : 1.0);
  c.xy += off / (uRes * 0.5) * c.w;
  gl_Position = c;
  vW = (end < 0.5 ? wa : wb).xyz; vK = iK; vSide = position.y * wq; vDepth = z; vCover = cover; vHalf = w;
}`;
const LINE_FS = /* glsl */`
${COMMON}
uniform float uGlow; uniform float uOpacity;
varying vec3 vW; varying float vK; varying float vSide; varying float vDepth; varying float vCover; varying float vHalf;
void main() {
  float n = vK > 0.5 ? 1.0 : nightAt(vW);   // accent lines (dome rim, rays, rings) are always gold: no edge flicker
  vec3 day = uDayInk * (1.0 - 0.25 * vK);
  vec3 night = uNightGold * uGlow * (1.0 + 0.6 * vK);
  vec3 col = mix(day, night, n);
  // atmospheric depth: lines fade into their background colour
  float fog = smoothstep(uFogN, uFogF, vDepth);
  col = mix(col, mix(uDayPaper * 0.92, uNightNavy * 1.4, n), fog);
  col += vec3(1.0, 0.8, 0.5) * rimAt(vW) * 1.5;
  float a = clamp(vHalf + 0.5 - abs(vSide), 0.0, 1.0);   // exact 1 px coverage edge (vSide is in px)
  if (any(isnan(col)) || any(isinf(col))) col = vec3(0.0);
  gl_FragColor = vec4(clamp(col, 0.0, 8.0), a * uOpacity * vCover);
}`;

const quad = (() => {
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute([0, -1, 0, 1, -1, 0, 1, 1, 0, 0, 1, 0], 3));
  g.setIndex([0, 1, 2, 0, 2, 3]);
  return g;
})();

// segs: flat array of [ax, ay, az, bx, by, bz, ...]; opts.width in px (at 10 m when persp), opts.k: 0 primary / 1 accent
export function lines(segs, { width = 2.0, persp = 10, k = 0, widths = null, ks = null, opacity = 1, depthTest = true, sway = 0 } = {}) {
  const n = segs.length / 6;
  const g = quad.clone();
  const A = new Float32Array(n * 3), B = new Float32Array(n * 3), Wd = new Float32Array(n), K = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    A.set(segs.slice(i * 6, i * 6 + 3), i * 3); B.set(segs.slice(i * 6 + 3, i * 6 + 6), i * 3);
    Wd[i] = widths ? widths[i] : 1; K[i] = ks ? ks[i] : k;
  }
  g.setAttribute('iA', new THREE.InstancedBufferAttribute(A, 3));
  g.setAttribute('iB', new THREE.InstancedBufferAttribute(B, 3));
  g.setAttribute('iW', new THREE.InstancedBufferAttribute(Wd, 1));
  g.setAttribute('iK', new THREE.InstancedBufferAttribute(K, 1));
  g.instanceCount = n;
  const m = new THREE.ShaderMaterial({
    uniforms: { ...U, uWidth: { value: width }, uPersp: { value: persp * 1.0 }, uOpacity: { value: opacity }, uSway: { value: sway } },
    vertexShader: LINE_VS, fragmentShader: LINE_FS, transparent: true, depthTest, depthWrite: false, toneMapped: false,
  });
  const mesh = new THREE.Mesh(g, m); mesh.frustumCulled = false;
  mesh.renderOrder = 2;
  return mesh;
}

// polyline helper -> segment list
export function poly(pts, closed = false, out = []) {
  for (let i = 0; i < pts.length - 1 + (closed ? 1 : 0); i++) {
    const a = pts[i], b = pts[(i + 1) % pts.length];
    out.push(a[0], a[1], a[2], b[0], b[1], b[2]);
  }
  return out;
}
export function circle(c, r, n = 96, axis = 'y', out = [], a0 = 0, a1 = Math.PI * 2) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const a = a0 + (a1 - a0) * (i / n), x = Math.cos(a) * r, y = Math.sin(a) * r;
    pts.push(axis === 'y' ? [c[0] + x, c[1], c[2] + y] : axis === 'z' ? [c[0] + x, c[1] + y, c[2]] : [c[0], c[1] + y, c[2] + x]);
  }
  return poly(pts, false, out);
}
// feature edges of a geometry (crease angle) as segments in world space of an object
export function edgesOf(geo, matrix = null, angle = 30, out = []) {
  const e = new THREE.EdgesGeometry(geo, angle);
  const p = e.attributes.position.array, v = new THREE.Vector3();
  for (let i = 0; i < p.length; i += 3) {
    v.set(p[i], p[i + 1], p[i + 2]); if (matrix) v.applyMatrix4(matrix);
    out.push(v.x, v.y, v.z);
  }
  return out;
}

// ------------------------------------------------------------------ fills (cel-shaded, theme-aware)
const FILL_VS = /* glsl */`
uniform float uTime;
uniform float uSway;
vec3 sway(vec3 p) {   // wind: bends with height, slow gusts travelling across the valley
  float h = max(p.y, 0.0);
  float g = sin(uTime * 0.9 + p.x * 0.045 + p.z * 0.06) * 0.6 + sin(uTime * 2.1 + p.x * 0.13 - p.z * 0.09) * 0.25;
  return p + vec3(g * 0.028, 0.0, g * 0.018) * h * uSway;
}

varying vec3 vW; varying vec3 vN; varying float vDepth;
void main() {
  vec4 w = modelMatrix * vec4(position, 1.0); w.xyz = sway(w.xyz); vW = w.xyz;
  vN = normalize(mat3(modelMatrix) * normal);
  vec4 v = viewMatrix * w; vDepth = -v.z;
  gl_Position = projectionMatrix * v;
}`;
const FILL_FS = /* glsl */`
${COMMON}
uniform vec3 uDayA, uNightA; uniform float uShade, uLit; uniform vec3 uLitCol;
varying vec3 vW; varying vec3 vN; varying float vDepth;
void main() {
  float n = nightAt(vW);
  vec3 L = normalize(vec3(-0.45, 0.8, 0.4));
  float d = dot(normalize(vN), L);
  float band = d > 0.35 ? 1.0 : (d > -0.1 ? 0.84 : 0.7);
  vec3 day = uDayA * mix(1.0, band, uShade);
  vec3 night = uNightA * mix(1.0, band * 1.1, uShade);
  vec3 col = mix(day, night, n);
  col = mix(col, uLitCol, uLit * n);
  float fog = smoothstep(uFogN, uFogF, vDepth);
  col = mix(col, mix(uDayPaper * 0.92, uNightNavy * 1.4, n), fog);
  col += vec3(1.0, 0.8, 0.5) * rimAt(vW) * 0.35;
  if (any(isnan(col)) || any(isinf(col))) col = uNightNavy;   // never let one bad pixel poison the bloom
  gl_FragColor = vec4(clamp(col, 0.0, 8.0), 1.0);
}`;
export function fillMat(day = '#efe3c8', night = '#0e1838', { shade = 1, lit = 0, litCol = '#ffb45e', side = THREE.FrontSide, sway = 0 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: { ...U, uDayA: { value: C(day) }, uNightA: { value: C(night) }, uShade: { value: shade }, uLit: { value: lit }, uLitCol: { value: C(litCol) }, uSway: { value: sway } },
    vertexShader: FILL_VS, fragmentShader: FILL_FS, side, toneMapped: false,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  });
}

// ------------------------------------------------------------------ sky (ray-dome test for the night pocket)
export function sky(scene, radius = 1500) {
  const m = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, toneMapped: false, uniforms: { ...U, uSun: { value: new THREE.Vector3(0.6, 0.12, -0.8).normalize() } },
    vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix*vec4(position,1.); vW = w.xyz; gl_Position = projectionMatrix*viewMatrix*w; }`,
    fragmentShader: /* glsl */`
      ${COMMON}
      uniform vec3 uSun; varying vec3 vW;
      float hash(vec3 p){ p = fract(p*0.3183099+.1); p *= 17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
      void main(){
        vec3 d = normalize(vW - cameraPosition);
        vec3 oc = cameraPosition - uDomeC; float b = dot(oc, d); float c = dot(oc, oc) - uDomeR*uDomeR; float h = b*b - c;
        float chord = h > 0.0 ? max(0.0, -b + sqrt(h) - max(0.0, -b - sqrt(h))) : 0.0;
        float inside = 1.0 - smoothstep(uDomeR - 4.0, uDomeR, length(oc));
        float n = max(uNight, max(inside, smoothstep(0.0, 1.0, chord))) * (1.0 - uDawn);
        // day: warm paper gradient + sun glow
        float y = clamp(d.y, 0.0, 1.0);
        vec3 day = mix(vec3(0.97, 0.88, 0.74), vec3(0.86, 0.87, 0.85), pow(y, 0.6));
        day += vec3(1.0, 0.72, 0.45) * pow(max(dot(d, uSun), 0.0), 18.0) * 0.35;
        // night: deep navy, lighter at the horizon, stars
        vec3 night = mix(uNightNavy * 1.9, uNightNavy * 0.55, pow(y, 0.5));
        vec3 sp = floor(d * 380.0); float s = hash(sp);
        float star = step(0.9965, s) * (0.4 + 0.6 * sin(uTime * (1.0 + s * 3.0) + s * 40.0) * 0.5 + 0.5) * smoothstep(0.0, 0.15, y);
        night += uNightGold * star * 1.4;
        vec3 col = mix(day, night, n);
        // the dome rim seen against the sky
        float rim = h > 0.0 ? exp(-pow(chord - 0.0, 2.0) * 0.02) * step(0.001, h) : 0.0;
        col += vec3(1.0, 0.82, 0.55) * rim * 0.0;
        if (any(isnan(col)) || any(isinf(col))) col = uNightNavy;
        gl_FragColor = vec4(clamp(col, 0.0, 8.0), 1.0);
      }`,
  });
  const s = new THREE.Mesh(new THREE.SphereGeometry(radius, 48, 24), m); s.renderOrder = -10; scene.add(s); return s;
}

export const rnd = (seed) => mulberry32(seed);
