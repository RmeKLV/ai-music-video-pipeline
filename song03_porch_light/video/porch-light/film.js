// Porch Light — "Empire of Night" in Midnight Linework. A pure function of time: window.seek(t).
// Song time = film time. Shots follow docs/shotlist.md; lyrics come from lyrics.json (word-aligned).
import * as M from './lib/motion.js';
import * as G from './lib/gl.js';
import { THREE, U } from './sets/ink.js';
import { lineworldSet, BULB, roadX } from './sets/linework.js';
import { drawKeeper, lipOpen, blinkAt } from './sets/keeper.js';

const { W, H, E, clamp, lerp, kf } = M;
const S = {};
const CREAM = '#f3e7cf', AMBER = '#ffb45e', INK = '#1c2547', GOLD = '#f0bf6c';
const DOME_C = new THREE.Vector3(0, 0, 6);
const SEAT = new THREE.Vector3(0.32, 0.57, 6.05);     // where the keeper sits (top step)
const sm = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
const RX = (z) => roadX(z) + 0.75;
const TITLE = () => M.CFG.title || 'Porch Light';   // film.json "title" (pipeline/to_video.py --title)

// ------------------------------------------------------------------ lyrics
let LINES = [];
function prepLyrics(d) {
  LINES = d.lines.map((l) => {
    const w = l.words.map((x) => ({ ...x }));
    if (w.length > 1 && w[1].t0 - w[0].t0 > 1.2) w[0].t0 = w[1].t0 - 0.28;   // held/crushed first word
    return { text: l.text, section: l.section, t0: w[0].t0, t1: l.t1, words: w };
  });
}
function lineAt(t, chorus = null) {
  let best = null;
  for (const l of LINES) {
    if (chorus !== null && (l.section === 'Chorus') !== chorus) continue;
    if (t >= l.t0 - 0.15 && t <= l.t1 + 1.1 && (!best || l.t0 > best.t0)) best = l;
  }
  return best;
}
// lower-third verse line: words appear as sung, the sung word lights amber
function verseLine(ctx, t, { y = H - 118, size = 66, day = false } = {}) {
  const l = lineAt(t, false); if (!l) return;
  if (M.FORMAT.portrait) { y = H * 0.78; ctx.font = `italic 500 ${size}px Display`; size = Math.min(size * 1.15, size * (W * 0.88) / ctx.measureText(l.text).width); }
  const fin = sm(l.t0 - 0.15, l.t0 + 0.05, t), fout = 1 - sm(l.t1 + 0.6, l.t1 + 1.1, t), a = Math.min(fin, fout);
  if (a <= 0) return;
  const k = +day, g = ctx.createLinearGradient(0, y - 150, 0, H);
  g.addColorStop(0, rgba('#060a1c', '#efe3c8', k, 0)); g.addColorStop(0.6, rgba('#060a1c', '#efe3c8', k, 0.6 * a)); g.addColorStop(1, rgba('#060a1c', '#efe3c8', k, 0.72 * a));
  ctx.fillStyle = g; ctx.fillRect(0, y - 150, W, H - y + 150);
  const f = `italic 500 ${size}px Display`; ctx.font = f;
  const words = l.words.map((w) => w.w), sp = ctx.measureText(' ').width, ws = words.map((w) => ctx.measureText(w).width);
  let x = W / 2 - (ws.reduce((p, q) => p + q, 0) + sp * (words.length - 1)) / 2;
  l.words.forEach((w, i) => {
    const on = sm(w.t0 - 0.12, w.t0 + 0.05, t), cur = t >= w.t0 - 0.04 && t < (l.words[i + 1]?.t0 ?? l.t1 + 0.2);
    ctx.save(); ctx.globalAlpha = a * (0.35 + 0.65 * on); ctx.font = f;
    if (cur) { ctx.shadowColor = rgba('#ffaa50', '#fffaeb', k, 0.9); ctx.shadowBlur = lerp(24, 12, k); ctx.fillStyle = M.mix(AMBER, '#a8462a', k); }
    else { ctx.shadowColor = rgba('#050a1e', '#fffaeb', k, 0.8); ctx.shadowBlur = 12; ctx.fillStyle = M.mix(CREAM, INK, k); }
    ctx.fillText(w.w, x, y + (1 - on) * 10); ctx.restore(); x += ws[i] + sp;
  });
}

function chorusLine(ctx, t, { y = H * 0.24, size = 104, day = false } = {}) {
  const l = lineAt(t, true); if (!l) return;
  if (M.FORMAT.portrait) { y = H * 0.2; ctx.font = `italic 500 ${size}px Display`; size = Math.min(size, size * (W * 0.9) / ctx.measureText(l.text).width); }
  const a = Math.min(sm(l.t0 - 0.15, l.t0 + 0.05, t), 1 - sm(l.t1 + 0.5, l.t1 + 1.1, t)); if (a <= 0) return;
  const k = +day;
  if (k < 1) { const g = ctx.createRadialGradient(W / 2, y - size * 0.3, 10, W / 2, y - size * 0.3, W * 0.42); g.addColorStop(0, `rgba(6,10,28,${0.55 * a * (1 - k)})`); g.addColorStop(1, 'rgba(6,10,28,0)'); ctx.save(); ctx.scale(1, 0.32); ctx.fillStyle = g; ctx.fillRect(0, (y - size * 0.3) / 0.32 - W * 0.42, W, W * 0.84); ctx.restore(); }
  const f = `italic 500 ${size}px Display`; ctx.font = f;
  const sp = ctx.measureText(' ').width, ws = l.words.map((w) => ctx.measureText(w.w).width);
  let x = W / 2 - (ws.reduce((p, q) => p + q, 0) + sp * (ws.length - 1)) / 2;
  l.words.forEach((w, i) => {
    const on = sm(w.t0 - 0.15, w.t0 + 0.12, t);
    ctx.save(); ctx.font = f; ctx.globalAlpha = a * (0.16 + 0.84 * on);
    ctx.fillStyle = M.mix(on > 0.5 ? '#ffd9a0' : CREAM, INK, k);
    ctx.shadowColor = rgba('#ffaa50', '#faf4e6', k, 0.85); ctx.shadowBlur = lerp(34 * on, 18, k);
    ctx.fillText(w.w, x, y + (1 - on) * 18); ctx.restore(); x += ws[i] + sp;
  });
}

// big chorus type standing in 3-D space: one dynamic canvas plane, redrawn per frame for the active line
function makeType() {
  const cv = document.createElement('canvas'); cv.width = 2560; cv.height = 360; const c = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: new THREE.Color(1.3, 0.95, 0.55), toneMapped: false, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(25.6, 3.6), mat);
  return {
    mesh,
    draw(t, { size = 200 } = {}) {
      const l = lineAt(t, true);
      mesh.visible = !!l; if (!l) return;
      c.clearRect(0, 0, cv.width, cv.height);
      const fin = sm(l.t0 - 0.15, l.t0 + 0.05, t), fout = 1 - sm(l.t1 + 0.5, l.t1 + 1.1, t);
      const f = `italic 500 ${size}px Display`; c.font = f; c.textBaseline = 'middle';
      const sp = c.measureText(' ').width, ws = l.words.map((w) => c.measureText(w.w).width);
      let x = cv.width / 2 - (ws.reduce((p, q) => p + q, 0) + sp * (ws.length - 1)) / 2;
      l.words.forEach((w, i) => {
        const on = sm(w.t0 - 0.15, w.t0 + 0.1, t);
        c.globalAlpha = Math.min(fin, fout) * (0.18 + 0.82 * on);
        c.fillStyle = '#fff'; c.fillText(w.w, x, cv.height / 2 + (1 - on) * 30);
        x += ws[i] + sp;
      });
      c.globalAlpha = 1; tex.needsUpdate = true;
    },
  };
}

// ------------------------------------------------------------------ the keeper (billboard on the steps)
function keeperUpdate(t, cam, P = {}) {
  const right = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0);
  const flip = right.z < 0;                              // she faces +z (down the road)
  const n = clamp((U.uDomeR.value + 1.2 - SEAT.distanceTo(DOME_C)) / 2.4);   // inside the night?
  const k = Math.max(n, U.uNight.value) * (1 - U.uDawn.value);
  const line = k > 0.5 ? GOLD : INK, fill = k > 0.5 ? '#14204a' : '#efe3c8', skin = k > 0.5 ? '#1c2a5a' : '#f6ecd6';
  const c = S.kcv.getContext('2d'); c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, 800, 1500);
  c.translate(400, 0); if (flip) c.scale(-1, 1); c.translate(-70, 1000);
  drawKeeper(c, { open: lipOpen(S.LIP, t) * (P.sing ?? 1), blink: blinkAt(t), t, breathe: Math.sin(t * 1.4) * 0.5 + 0.5,
    sway: Math.sin(t * 0.9) * 6, lift: P.lift ?? 0.04, tilt: P.tilt ?? 0, line, fill, skin, glow: k > 0.5 ? 0.6 : 0 });
  S.ktex.needsUpdate = true;
  S.kplane.position.set(SEAT.x + 0.07, SEAT.y + 0.25, SEAT.z);
  S.kplane.lookAt(cam.position.x, S.kplane.position.y, cam.position.z);
  S.kplane.visible = P.visible ?? true;
  return { right, flip };
}

// silhouette of a seated person, sampled from the keeper drawing (for the moth outline)
function seatedOutline() {
  // a person in a long coat, standing by the door: explicit outline in px (380 px = 1 m), feet at y = 0
  const body = [[22, -575], [26, -552], [70, -548], [100, -535], [112, -500], [112, -470], [108, -380], [104, -300], [100, -220], [96, -150],
    [62, -150], [64, -75], [66, 0], [18, 0], [14, -70], [10, -140], [-10, -140], [-14, -70], [-18, 0], [-66, 0], [-64, -75], [-62, -150],
    [-96, -150], [-100, -220], [-104, -300], [-108, -380], [-112, -470], [-112, -500], [-100, -535], [-70, -548], [-26, -552], [-22, -575]];
  const head = []; for (let i = 0; i <= 24; i++) { const a = (110 + (320 * i) / 24) * Math.PI / 180; head.push([Math.cos(a) * 38, -620 + Math.sin(a) * 46]); }
  const raw = [...body, ...head.reverse()];
  const L = [0]; for (let i = 1; i <= raw.length; i++) { const p = raw[i % raw.length], q = raw[i - 1]; L.push(L[i - 1] + Math.hypot(p[0] - q[0], p[1] - q[1])); }
  const pts = [], total = L[L.length - 1], n = 240; let j = 0;
  for (let i = 0; i < n; i++) {
    const tl = (i / n) * total; while (L[j + 1] < tl) j++;
    const p = raw[j], q = raw[(j + 1) % raw.length], f = (tl - L[j]) / Math.max(1e-6, L[j + 1] - L[j]);
    pts.push([lerp(p[0], q[0], f) / 380, -lerp(p[1], q[1], f) / 380]);
  }
  return pts;
}

// is the screen point (sx, sy in 0..1) showing night? Same test as the shaders: ray-dome chord / inside.
function nightAtScreen(cam, sx, sy) {
  if (U.uNight.value > 0.5) return true;
  const C = U.uDomeC.value, R = U.uDomeR.value;
  const o = cam.position.clone(), d = new THREE.Vector3(sx * 2 - 1, 1 - sy * 2, 0.5).unproject(cam).sub(o).normalize();
  if (U.uDawn.value > 0.5) return false;
  const camIn = o.distanceTo(C) < R;
  const ground = d.y < -1e-4, tmax = ground ? -o.y / d.y : 1e9;
  if (ground && o.clone().addScaledVector(d, tmax).distanceTo(C) < R) return true;
  if (camIn) return !ground;                                   // inside: the sky is night, ground outside is day
  const oc = o.clone().sub(C), b = oc.dot(d), c = oc.dot(oc) - R * R, h = b * b - c; if (h <= 0) return false;
  const sq = Math.sqrt(h), t0 = Math.max(-b - sq, 0), t1 = Math.min(-b + sq, tmax);
  return t1 - t0 > 2.0;
}

function dayFraction(cam, y) {
  let d = 0; for (let i = 0; i < 9; i++) d += nightAtScreen(cam, 0.3 + 0.4 * i / 8, y) ? 0 : 1;
  const ci = 1 - sm(U.uDomeR.value - 4, U.uDomeR.value, cam.position.distanceTo(U.uDomeC.value));   // same 4 m fade as the shaders
  return (d / 9) * (1 - ci * (1 - U.uInDay.value)) * (1 - 0) + 0 * ci;
}
const rgba = (a, b, k, al) => { const A = M.hexRgb(a), B = M.hexRgb(b); return `rgba(${A.map((v, i) => Math.round(lerp(v, B[i], k))).join(',')},${al})`; };

// ------------------------------------------------------------------ camera helper: keyed [t, pos, look]
function camKeys(t, keys, ease = E.inOutSine) {
  const pos = kf(t, keys.map(([k, p]) => [k, p]), ease), look = kf(t, keys.map(([k, , l]) => [k, l]), ease);
  return { pos, look };
}

function post(ctx, u, t) {
  const g = ctx.createRadialGradient(W / 2, H / 2, H * 0.42, W / 2, H / 2, H * 1.0);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(8,10,25,0.42)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  if (!S.grain) {
    S.grain = document.createElement('canvas'); S.grain.width = 512; S.grain.height = 512; const c = S.grain.getContext('2d');
    const img = c.createImageData(512, 512), r = M.mulberry32(3);
    for (let i = 0; i < img.data.length; i += 4) { const v = r() * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 8; }
    c.putImageData(img, 0, 0);
  }
  const ox = Math.floor(M.hash01(Math.floor(t * 24), 4) * 512), oy = Math.floor(M.hash01(Math.floor(t * 24), 5) * 512);
  ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.translate(-ox, -oy);
  ctx.fillStyle = ctx.createPattern(S.grain, 'repeat'); ctx.fillRect(0, 0, W + 512, H + 512); ctx.restore();
  const fade = t >= 299.5 ? 0 : Math.max(1 - sm(0, 1.2, t), sm(205.5, 208.2, t));
  if (fade > 0) { ctx.fillStyle = `rgba(4,6,16,${fade})`; ctx.fillRect(0, 0, W, H); }
}

// the opening moth: gold line-art crossing the stars
function drawMoth(ctx, x, y, s, rot, flap, col = '#f6cf8a', glow = 18) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s * flap, s);
  ctx.strokeStyle = col; ctx.lineWidth = 2.4 / Math.max(0.3, s); ctx.shadowColor = 'rgba(255,180,90,0.9)'; ctx.shadowBlur = glow;
  for (const sgn of [-1, 1]) { ctx.save(); ctx.scale(sgn, 1);
    ctx.beginPath(); ctx.moveTo(3, -4); ctx.bezierCurveTo(30, -40, 70, -26, 66, -4); ctx.bezierCurveTo(62, 10, 30, 8, 3, 3); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(3, 4); ctx.bezierCurveTo(24, 8, 44, 28, 32, 32); ctx.bezierCurveTo(18, 36, 6, 20, 3, 6); ctx.stroke(); ctx.restore(); }
  ctx.beginPath(); ctx.ellipse(0, 2, 3.5, 15, 0, 0, 7); ctx.stroke(); ctx.restore();
}

function introMoth(ctx, t) {
  const k = sm(0.6, 6.2, t); if (k <= 0 || k >= 1) return;
  const x = lerp(-120, W + 120, k), y = H * 0.62 - Math.sin(k * Math.PI) * 260 + Math.sin(t * 5) * 14;
  const fl = 0.35 + 0.65 * Math.abs(Math.sin(t * 15));
  ctx.save(); ctx.translate(x, y); ctx.rotate(-0.25 + Math.cos(k * Math.PI) * 0.35); ctx.scale(fl, 1);
  ctx.strokeStyle = '#f6cf8a'; ctx.lineWidth = 2.4; ctx.shadowColor = 'rgba(255,180,90,0.9)'; ctx.shadowBlur = 18;
  for (const sgn of [-1, 1]) { ctx.save(); ctx.scale(sgn, 1);
    ctx.beginPath(); ctx.moveTo(3, -4); ctx.bezierCurveTo(30, -40, 70, -26, 66, -4); ctx.bezierCurveTo(62, 10, 30, 8, 3, 3); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(3, 4); ctx.bezierCurveTo(24, 8, 44, 28, 32, 32); ctx.bezierCurveTo(18, 36, 6, 20, 3, 6); ctx.stroke(); ctx.restore(); }
  ctx.beginPath(); ctx.ellipse(0, 2, 3.5, 15, 0, 0, 7); ctx.stroke();
  ctx.restore();
  // a faint trail of light behind it
  ctx.save(); ctx.globalAlpha = 0.35; ctx.strokeStyle = '#f0bf6c'; ctx.lineWidth = 1.2; ctx.beginPath();
  for (let i = 0; i <= 40; i++) { const kk = Math.max(0, k - i * 0.006); const xx = lerp(-120, W + 120, kk), yy = H * 0.62 - Math.sin(kk * Math.PI) * 260; i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); }
  ctx.stroke(); ctx.restore();
}

// title written on as tracked caps (2-D, over the shot)
function title(ctx, t, t0, t1, { y = H * 0.5, day = false, size = 120 } = {}) {
  const a = Math.min(sm(t0, t0 + 1.5, t), 1 - sm(t1 - 1.0, t1, t)); if (a <= 0) return;
  const txt = TITLE().toUpperCase();
  ctx.save(); ctx.font = `600 ${size}px Display`; ctx.letterSpacing = `${size * 0.32}px`; ctx.textAlign = 'center';
  const n = Math.floor(txt.length * sm(t0, t0 + 2.2, t) + 0.999);
  ctx.globalAlpha = a; ctx.fillStyle = day ? INK : CREAM; if (!day) { ctx.shadowColor = 'rgba(255,180,90,0.7)'; ctx.shadowBlur = 30; }
  ctx.fillText(txt.slice(0, n), W / 2 + size * 0.16, y);
  ctx.letterSpacing = '8px'; ctx.font = 'italic 400 36px UI'; ctx.globalAlpha = a * sm(t0 + 1.5, t0 + 3, t);
  ctx.fillStyle = '#b8792c'; ctx.shadowColor = day ? 'rgba(250,244,230,0.95)' : 'rgba(5,10,30,0.9)'; ctx.shadowBlur = 10;
  ctx.fillText('an original song', W / 2, y + 72);
  ctx.restore();
}

// ------------------------------------------------------------------ the film
M.film({
  fonts: ['900 100px Thumb', '500 100px Display', 'italic 500 100px Display', '600 100px Display', '400 40px UI', 'italic 400 40px UI'],
  samples: 3,
  async init() {
    await G.initGL({ exposure: 1.0 });
    G.R.toneMapping = THREE.NoToneMapping;
    S.w = lineworldSet();
    prepLyrics(await fetch('lyrics.json').then((r) => r.json()));
    S.LIP = await fetch('lipsync.json').then((r) => r.json()).catch(() => null);
    S.kcv = document.createElement('canvas'); S.kcv.width = 800; S.kcv.height = 1500;
    S.ktex = new THREE.CanvasTexture(S.kcv); S.ktex.colorSpace = THREE.SRGBColorSpace; S.ktex.anisotropy = 8;
    S.kplane = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 1.5), new THREE.MeshBasicMaterial({ map: S.ktex, transparent: true, alphaTest: 0.02, toneMapped: false, side: THREE.DoubleSide }));
    S.w.scene.add(S.kplane);
    S.type = makeType(); S.w.scene.add(S.type.mesh);
    S.tb = document.createElement('canvas'); S.tb.width = Math.round(W * M.SCALE); S.tb.height = Math.round(H * M.SCALE);
    S.ta = document.createElement('canvas'); S.ta.width = S.tb.width; S.ta.height = S.tb.height;
    S.outline = seatedOutline();
    const cv = document.createElement('canvas'); cv.width = 300; cv.height = 400; const c = cv.getContext('2d');
    c.strokeStyle = '#fff'; c.fillStyle = '#fff'; c.lineWidth = 5; c.strokeRect(12, 12, 276, 376);
    c.font = '600 92px Display'; c.textAlign = 'center'; c.fillText('MAY', 150, 130);
    c.lineWidth = 2; for (let r = 0; r < 5; r++) for (let k = 0; k < 7; k++) c.strokeRect(30 + k * 34.5, 170 + r * 40, 34.5, 40);
    c.lineWidth = 4; c.beginPath(); c.ellipse(30 + 5 * 34.5 + 17, 170 + 2 * 40 + 20, 24, 20, 0, 0, 7); c.stroke();
    const pt = new THREE.CanvasTexture(cv); pt.colorSpace = THREE.SRGBColorSpace;
    S.pages = Array.from({ length: 5 }, () => { const m = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 0.4), new THREE.MeshBasicMaterial({ map: pt, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: new THREE.Color(1.3, 0.95, 0.55), toneMapped: false, side: THREE.FrontSide })); S.w.scene.add(m); return m; });
  },
  post,
  draw(ctx, u, t) {
    if (t >= 299.5) { thumbDraw(ctx, u, t); return; }
    const idx = shotIndex(t);
    const tr = TRANS.find((x) => t >= x.c - x.pre * x.d && t < x.c + (1 - x.pre) * x.d);
    let info;
    if (tr) {
      const lin = clamp((t - (tr.c - tr.pre * tr.d)) / tr.d), p = lin * lin * lin * (lin * (lin * 6 - 15) + 10);   // smootherstep: soft start, soft landing
      const iA = shotIndex(tr.c - 0.01), iB = shotIndex(tr.c + 0.01);
      let infoA;
      if (OFF.has(tr.type)) { const ac = S.ta.getContext('2d'); ac.setTransform(M.SCALE, 0, 0, M.SCALE, 0, 0); infoA = renderShot(ac, iA, u, t); }
      else infoA = renderShot(ctx, iA, u, t);
      const bc = S.tb.getContext('2d'); bc.setTransform(M.SCALE, 0, 0, M.SCALE, 0, 0);
      const infoB = renderShot(bc, iB, u, t);
      if (tr.type === 'through') through(ctx, S.ta, S.tb, infoA.focus, infoB.focus, p, t);
      else if (OFF.has(tr.type)) FX[tr.type](ctx, S.ta, S.tb, p, t, tr, infoA, infoB);
      else transition(ctx, S.tb, tr, p, t);
      info = p < 0.5 ? infoA : infoB;
    } else info = renderShot(ctx, idx, u, t);
    overlays(ctx, u, t, info);
  },
});

// ------------------------------------------------------------------ transitions (built from the film's motifs)
// c: cut time (shot boundary), d: duration, type, opts
// every cut sits on a measured bar downbeat (beats.json); d is in beats; pre = share of the move before the downbeat
const BEAT = 0.42248;
const TRANS = [
  { c: 8.129, d: 6 * BEAT, pre: 0.5, type: 'iris', ...{ x: 0.5, y: 0.55 } },
  { c: 16.579, d: 8 * BEAT, pre: 0.5, type: 'through', ...{} },
  { c: 30.098, d: 6 * BEAT, pre: 0.5, type: 'luma', ...{} },
  { c: 40.238, d: 4 * BEAT, pre: 1.0, type: 'clock', ...{} },
  { c: 55.447, d: 4 * BEAT, pre: 0.5, type: 'flare', ...{} },
  { c: 63.897, d: 2 * BEAT, pre: 0.5, type: 'whip', ...{} },
  { c: 80.796, d: 6 * BEAT, pre: 0.5, type: 'ink', ...{ x: 0.5, y: 0.5, day: true } },
  { c: 97.695, d: 6 * BEAT, pre: 0.5, type: 'through', ...{} },
  { c: 109.525, d: 6 * BEAT, pre: 0.5, type: 'swarm', ...{} },
  { c: 123.044, d: 4 * BEAT, pre: 0.5, type: 'burst', ...{} },
  { c: 148.393, d: 8 * BEAT, pre: 0.5, type: 'luma', ...{ slow: true } },
  { c: 168.672, d: 6 * BEAT, pre: 1.0, type: 'tilt', ...{} },
  { c: 187.261, d: 8 * BEAT, pre: 0.5, type: 'ink', ...{ x: 0.5, y: 0.6 } },
];
const OFF = new Set(['through', 'luma', 'whip', 'swarm', 'burst', 'tilt']);   // types that need shot A offscreen

// fly into the porch light of shot A, the frame dissolves into warm light, shot B opens out of its own light

// ---- varied transitions (A and B are full frames; p is eased 0..1) ----
const FX = {
  // light dissolve: the brightest parts of B (windows, the bulb, gold lines) glow in first, the shadows last
  luma(ctx, A, B, p, t, tr) {
    if (!S.mk) { S.mk = document.createElement('canvas'); S.mk.width = 480; S.mk.height = 270; S.mt = document.createElement('canvas'); S.mt.width = A.width; S.mt.height = A.height; }
    const m = S.mk.getContext('2d', { willReadFrequently: true }); m.globalCompositeOperation = 'copy'; m.drawImage(B, 0, 0, 480, 270);
    const img = m.getImageData(0, 0, 480, 270), d = img.data, thr = 1.15 - p * 1.3, soft = tr.slow ? 0.3 : 0.2;
    for (let i = 0; i < d.length; i += 4) { const l = (0.3 * d[i] + 0.59 * d[i + 1] + 0.11 * d[i + 2]) / 255; d[i + 3] = 255 * clamp((l - thr) / soft + 0.5); }
    m.putImageData(img, 0, 0);
    const mt = S.mt.getContext('2d'); mt.setTransform(1, 0, 0, 1, 0, 0); mt.globalCompositeOperation = 'copy'; mt.drawImage(B, 0, 0);
    mt.globalCompositeOperation = 'destination-in'; mt.imageSmoothingQuality = 'high'; mt.drawImage(S.mk, 0, 0, S.mt.width, S.mt.height);
    mt.globalCompositeOperation = 'source-over';
    ctx.drawImage(A, 0, 0, W, H); ctx.drawImage(S.mt, 0, 0, W, H);
    const k = Math.sin(Math.PI * p) * 0.22;
    if (k > 0) { ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.fillStyle = `rgba(255,200,130,${k})`; ctx.fillRect(0, 0, W, H); ctx.restore(); }
  },
  // whip pan: both frames on screen, sliding together, smeared along the motion
  whip(ctx, A, B, p) {
    const x = -p * W, v = Math.sin(Math.PI * p);
    const smear = (img, ox) => { const n = 7; for (let i = 0; i < n; i++) { ctx.globalAlpha = 1 / (i + 1); ctx.drawImage(img, ox + (i - n / 2) * v * 18, 0, W, H); } ctx.globalAlpha = 1; };
    ctx.fillStyle = '#0b1330'; ctx.fillRect(0, 0, W, H);
    smear(A, x); smear(B, x + W);
  },
  // the moths come: a swarm flies out of the light toward the camera, fills the frame, scatters to reveal B
  swarm(ctx, A, B, p, t, tr, ia) {
    const f = ia.focus || [W / 2, H / 2];
    ctx.drawImage(A, 0, 0, W, H);
    ctx.save(); ctx.globalAlpha = sm(0.45, 0.6, p); ctx.drawImage(B, 0, 0, W, H); ctx.restore();
    for (let i = 0; i < 150; i++) {
      const r1 = M.hash01(i, 21), r2 = M.hash01(i, 22), r3 = M.hash01(i, 23);
      const start = r1 * 0.35, life = clamp((p - start) / (0.75 - start * 0.5));
      if (life <= 0 || life >= 1) continue;
      const a = r2 * Math.PI * 2, dist = E.inCubic(life) * W * (0.4 + r3), s = 0.25 + E.inCubic(life) * (2.5 + 3 * r3);
      const x = f[0] + Math.cos(a) * dist + M.noise1(t * 2 + i, 5) * 30, y = f[1] + Math.sin(a) * dist * 0.7 + M.noise1(t * 2 + i, 6) * 30;
      ctx.save(); ctx.globalAlpha = Math.sin(Math.PI * life);
      drawMoth(ctx, x, y, s, a + Math.PI / 2 + Math.sin(t * 3 + i) * 0.3, 0.3 + 0.7 * Math.abs(Math.sin(t * (14 + i % 6) + i)), '#f6cf8a', 10);
      ctx.restore();
    }
  },
  // chorus 2 downbeat: radial burst - A rushes outward in a zoom blur, peak of light, B settles in from the blur
  burst(ctx, A, B, p) {
    const zb = (img, amt, alpha) => { const n = 8; for (let i = 0; i < n; i++) { const z = 1 + amt * i / n; ctx.save(); ctx.globalAlpha = Math.min(1, alpha / (i + 1) * 1.6); ctx.translate(W / 2, H * 0.45); ctx.scale(z, z); ctx.translate(-W / 2, -H * 0.45); ctx.drawImage(img, 0, 0, W, H); ctx.restore(); } };
    ctx.fillStyle = '#0b1330'; ctx.fillRect(0, 0, W, H);
    if (p < 0.5) { ctx.drawImage(A, 0, 0, W, H); zb(A, E.inCubic(p * 2) * 0.9, 0.6); }
    else { ctx.drawImage(B, 0, 0, W, H); zb(B, (1 - E.outCubic((p - 0.5) * 2)) * 0.9, 0.6); }
    const k = Math.exp(-Math.pow((p - 0.5) / 0.12, 2));
    const g = ctx.createRadialGradient(W / 2, H * 0.45, 0, W / 2, H * 0.45, W * 0.75);
    g.addColorStop(0, `rgba(255,240,210,${0.95 * k})`); g.addColorStop(0.4, `rgba(255,200,120,${0.6 * k})`); g.addColorStop(1, `rgba(255,170,80,${0.15 * k})`);
    ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = `rgba(255,214,150,${0.7 * k})`; ctx.lineWidth = 2;
    for (let i = 0; i < 64; i++) { const a = i / 64 * Math.PI * 2, r0 = 80 + 400 * p, r1 = r0 + 250 + (i % 3) * 300; ctx.beginPath(); ctx.moveTo(W / 2 + Math.cos(a) * r0, H * 0.45 + Math.sin(a) * r0); ctx.lineTo(W / 2 + Math.cos(a) * r1, H * 0.45 + Math.sin(a) * r1); ctx.stroke(); }
    ctx.restore();
  },
  // tilt up into the stars and down into the final chorus: A drops away, a band of night sky, B arrives from above
  tilt(ctx, A, B, p) {
    const gap = H * 0.6, y = p * (H + gap), v = Math.sin(Math.PI * p);
    ctx.fillStyle = '#0b1330'; ctx.fillRect(0, 0, W, H);
    const smear = (img, oy) => { const n = 6; for (let i = 0; i < n; i++) { ctx.globalAlpha = 1 / (i + 1); ctx.drawImage(img, 0, oy + (i - n / 2) * v * 14, W, H); } ctx.globalAlpha = 1; };
    smear(A, y);
    const top = y - gap, g = ctx.createLinearGradient(0, top, 0, y); g.addColorStop(0, '#0b1330'); g.addColorStop(1, '#16224d');
    ctx.fillStyle = g; ctx.fillRect(0, top, W, gap);
    ctx.fillStyle = '#f0bf6c';
    for (let i = 0; i < 90; i++) { const sx = M.hash01(i, 31) * W, sy = top + M.hash01(i, 32) * gap; if (sy > -4 && sy < H + 4) { ctx.globalAlpha = 0.4 + 0.6 * M.hash01(i, 33); ctx.fillRect(sx, sy, 2, 2 + v * 10); } }
    ctx.globalAlpha = 1;
    smear(B, top - H);
  },
};

function through(ctx, A, B, fa, fb, p, t) {
  fa = fa || [W / 2, H / 2]; fb = fb || [W / 2, H / 2];
  const Z = 6;                                                   // zoom at the hand-off
  const draw = (img, f, z, alpha) => {
    if (alpha <= 0) return;
    ctx.save(); ctx.globalAlpha = alpha;
    // zoom about the focus and slide the focus to the frame centre, so we fly straight at the light
    const c = Math.min(1, Math.log(z) / Math.log(Z));
    const cx = lerp(f[0], W / 2, c), cy = lerp(f[1], H / 2, c);
    ctx.translate(cx, cy); ctx.scale(z, z); ctx.translate(-f[0], -f[1]);
    ctx.drawImage(img, 0, 0, W, H); ctx.restore();
  };
  const pa = clamp(p / 0.55), pb = clamp((p - 0.45) / 0.55);
  ctx.fillStyle = '#0b1330'; ctx.fillRect(0, 0, W, H);
  draw(A, fa, Math.pow(Z, E.inCubic(pa)), 1 - sm(0.42, 0.58, p));
  draw(B, fb, Math.pow(Z, 1 - E.outCubic(pb)), sm(0.42, 0.58, p));
  // the light we pass through: warm core growing to fill the frame at the hand-off
  const k = Math.sin(Math.PI * p);
  const fx = lerp(lerp(fa[0], W / 2, E.inCubic(pa)), lerp(W / 2, fb[0], E.outCubic(pb)), sm(0.4, 0.6, p));
  const fy = lerp(lerp(fa[1], H / 2, E.inCubic(pa)), lerp(H / 2, fb[1], E.outCubic(pb)), sm(0.4, 0.6, p));
  const R = lerp(60, W * 0.9, k * k);
  const g = ctx.createRadialGradient(fx, fy, 0, fx, fy, R);
  g.addColorStop(0, `rgba(255,236,200,${0.95 * k})`); g.addColorStop(0.35, `rgba(255,196,120,${0.55 * k * k})`); g.addColorStop(1, 'rgba(255,170,80,0)');
  ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
}

function transition(ctx, B, tr, p, t) {
  const e = E.inOutCubic(p);
  ctx.save();
  if (tr.type === 'fade') { ctx.globalAlpha = e; ctx.drawImage(B, 0, 0, W, H); ctx.restore(); return; }
  if (tr.type === 'flare') {
    ctx.globalAlpha = sm(0.4, 0.6, p); ctx.drawImage(B, 0, 0, W, H); ctx.globalAlpha = 1;
    const k = Math.sin(p * Math.PI);
    const g = ctx.createRadialGradient(W / 2, H * 0.42, 0, W / 2, H * 0.42, W * 0.7);
    g.addColorStop(0, `rgba(255,236,200,${0.95 * k})`); g.addColorStop(0.3, `rgba(255,190,110,${0.6 * k})`); g.addColorStop(1, 'rgba(255,160,80,0)');
    ctx.globalCompositeOperation = 'screen'; ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = `rgba(255,214,150,${0.7 * k})`; ctx.lineWidth = 2;
    for (let i = 0; i < 48; i++) { const a = i / 48 * Math.PI * 2 + t * 0.2, r0 = 40 + 200 * p, r1 = r0 + 200 + (i % 3) * 260 * k; ctx.beginPath(); ctx.moveTo(W / 2 + Math.cos(a) * r0, H * 0.42 + Math.sin(a) * r0); ctx.lineTo(W / 2 + Math.cos(a) * r1, H * 0.42 + Math.sin(a) * r1); ctx.stroke(); }
    ctx.restore(); return;
  }
  ctx.beginPath();
  let edge = null;
  if (tr.type === 'iris') {
    const cx = tr.x * W, cy = tr.y * H, R = Math.hypot(W, H) * e;
    ctx.arc(cx, cy, Math.max(0.1, R), 0, Math.PI * 2); edge = () => { ctx.beginPath(); ctx.arc(cx, cy, Math.max(0.1, R), 0, Math.PI * 2); };
  } else if (tr.type === 'clock') {
    const a0 = -Math.PI / 2, a1 = a0 + e * Math.PI * 2, cx = W / 2, cy = H / 2, R = Math.hypot(W, H);
    ctx.moveTo(cx, cy); ctx.arc(cx, cy, R, a0, a1); ctx.closePath();
    edge = () => { ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a1) * R, cy + Math.sin(a1) * R); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a1 - 0.35) * 260, cy + Math.sin(a1 - 0.35) * 260); };
  } else if (tr.type === 'line' || tr.type === 'moths') {
    const ang = tr.angle ?? -0.25, nx = Math.cos(ang), ny = Math.sin(ang), span = W * Math.abs(nx) + H * Math.abs(ny);
    const d = -span / 2 - 200 + e * (span + 400);
    // half-plane behind the moving edge (with a ragged edge for the swarm)
    const px = -ny, py = nx, cx = W / 2 + nx * d, cy = H / 2 + ny * d;
    const pts = [];
    for (let i = -20; i <= 20; i++) { const s = i / 20 * 1400, j = tr.type === 'moths' ? 70 * M.noise1(i * 0.7 + t, 4) : 0; pts.push([cx + px * s + nx * j, cy + py * s + ny * j]); }
    ctx.moveTo(pts[0][0] - nx * 3000, pts[0][1] - ny * 3000); pts.forEach(([x, y]) => ctx.lineTo(x, y)); ctx.lineTo(pts[pts.length - 1][0] - nx * 3000, pts[pts.length - 1][1] - ny * 3000); ctx.closePath();
    edge = () => { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); };
    if (tr.type === 'moths') S.mothEdge = pts; else S.mothEdge = null;
  } else if (tr.type === 'ink') {
    const cx = tr.x * W, cy = tr.y * H, R = Math.hypot(W, H) * 0.62 * e;
    for (let i = 0; i <= 96; i++) { const a = i / 96 * Math.PI * 2, r = R * (1 + 0.22 * M.noise1(Math.cos(a) * 3 + 9, 7) + 0.1 * M.noise1(a * 6, 8)); i ? ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r) : ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); }
    ctx.closePath();
  }
  ctx.save(); ctx.clip(); ctx.drawImage(B, 0, 0, W, H); ctx.restore();
  if (edge && e > 0.001 && e < 0.999) {
    edge(); ctx.strokeStyle = 'rgba(255,205,130,0.95)'; ctx.lineWidth = 2; ctx.shadowColor = 'rgba(255,170,80,0.7)'; ctx.shadowBlur = 8; ctx.stroke();
  }
  if (tr.type === 'moths' && S.mothEdge && e > 0 && e < 1) {
    // a swarm riding the edge
    for (let i = 0; i < 46; i++) {
      const q = S.mothEdge[Math.floor(M.hash01(i, 3) * S.mothEdge.length)], jx = (M.hash01(i, 5) - 0.5) * 160, jy = (M.hash01(i, 6) - 0.5) * 160;
      const fl = 0.3 + 0.7 * Math.abs(Math.sin(t * (14 + i % 5) + i));
      ctx.save(); ctx.translate(q[0] + jx, q[1] + jy); ctx.rotate(M.hash01(i, 9) * 6); ctx.scale(fl * (0.5 + M.hash01(i, 2)), 0.5 + M.hash01(i, 2));
      ctx.strokeStyle = '#ffd59a'; ctx.lineWidth = 2; ctx.shadowColor = 'rgba(255,180,90,0.9)'; ctx.shadowBlur = 10;
      for (const sg of [-1, 1]) { ctx.beginPath(); ctx.moveTo(0, 0); ctx.bezierCurveTo(sg * 18, -22, sg * 40, -12, sg * 36, 0); ctx.bezierCurveTo(sg * 30, 10, sg * 12, 8, 0, 2); ctx.stroke(); }
      ctx.restore();
    }
  }
  ctx.restore();
}

const BOUNDS = [8.129, 16.579, 30.098, 40.238, 55.447, 63.897, 80.796, 97.695, 109.525, 123.044, 148.393, 159.3, 168.672, 187.261];
function shotIndex(t) { let i = 0; while (i < BOUNDS.length && t >= BOUNDS[i]) i++; return i; }

function renderShot(ctx, idx, u, t) {
    const set = S.w; const o = { moths: 40, glow: 1.15 };
    let cam, ky = {}, typeAt = null, verse = true, verseDay = false;
    S.pages.forEach((p) => (p.visible = false));
    U.uDayPaper.value.set('#efe3c8');
    const ph = ((u / 4) % 1 + 1) % 1, bar = Math.sin(Math.PI * ph) ** 2 * 0.6;   // smooth swell per bar, no flash

    if (idx === 0) {
      cam = camKeys(t, [[0, [2, 12, 40], [0, 24, -40]], [8.5, [2, 12.5, 30], [0, 26, -40]]]);
      Object.assign(o, { night: 1, moths: 0, rays: 0, rings: 0, windows: 0, bulb: 0 });
      verse = false;
    } else if (idx === 1) {
      cam = camKeys(t, [[8.5, [RX(150) + 10, 30, 150], [0, 4, 4]], [16.3, [RX(95) + 6, 17, 95], [0, 5, 5]]]);
      Object.assign(o, { moths: 20, sun: 0.35 });
      verse = false;
    } else if (idx === 2) {
      cam = camKeys(t, [[16.3, [RX(60) - 0.6, 1.7, 60], [RX(20), 2.2, 20]], [30.6, [RX(14) - 0.4, 1.65, 14], [0.2, 2.2, 4]]], E.linear);
      Object.assign(o, { moths: 30, sun: 0.4 });
      const z = kf(t, [[16.3, 60], [30.6, 14]], E.linear);
      verseDay = Math.hypot(RX(z) - DOME_C.x, z - DOME_C.z) > U.uDomeR.value;
    } else if (idx === 3) {
      cam = camKeys(t, [[30.6, [4.8, 1.25, 9.6], [0.4, 1.15, 5.8]], [40.4, [3.7, 1.15, 8.6], [0.35, 1.2, 5.9]]]);
      Object.assign(o, { moths: 45, rays: 0.7 });
      S.pages.forEach((p, i) => {
        const ph = ((t - 30.6) / 4.5 + i / 5) % 1;
        p.visible = true; p.position.set(SEAT.x + 0.25 + Math.sin(i * 2.1 + t * 0.4) * 0.5, SEAT.y + 0.4 + ph * 2.2, SEAT.z + 0.2 + Math.cos(i * 1.7) * 0.4);
        p.lookAt(cam.pos[0], cam.pos[1], cam.pos[2]); p.rotateZ(Math.sin(t * 0.7 + i) * 0.35); p.rotateY(Math.sin(t * 0.9 + i * 2) * 0.6);   // drift, but always show the printed side
        p.material.opacity = Math.sin(ph * Math.PI) * 0.8;
      });
    } else if (idx === 4) {
      const lt = t - 40.4;
      cam = camKeys(t, [[40.4, [2.8, 2.3, 9.0], [-0.25, 2.45, 3.8]], [48, [-1.6, 2.6, 8.4], [-0.25, 2.45, 3.8]], [55.6, [-2.8, 1.6, 10.5], [0, 2.0, 4]]]);
      const tick = Math.floor(lt * 2.367) % 4;
      Object.assign(o, { moths: 50, rays: 0.4, rings: 0.3, clock: sm(40.4, 42.5, t) * (1 - sm(54.6, 55.6, t)), time: [9, 30 + tick * 0.25], sun: lt / 15.2 });
    } else if (idx === 5) {
      cam = camKeys(t, [[55.6, [3.2, 1.4, 12], [0, 2.4, 4]], [64.4, [10, 26, 44], [0, 6, 0]]]);
      Object.assign(o, { moths: 80, rays: 1, glow: 1.25 + 0.2 * bar, bloom: 0.65 });
      typeAt = { day: t > 61 }; verse = false;
    } else if (idx === 6) {
      const z = kf(t, [[64.4, 48], [81, 330]], E.inOutSine);
      cam = { pos: [RX(z) + 3, 9 + (t - 64.4) * 0.6, z], look: [RX(z + 60), 3, z + 60] };
      if (t > 68) cam = { pos: [RX(z) - 4, 7, z + 40], look: [0, 4, 6] };
      Object.assign(o, { moths: 30, car: t > 68 ? kf(t, [[68, 60], [81, 600]], E.inQuad) : -1, sun: 0.55 });
      typeAt = { day: true };
      verse = false;
    } else if (idx === 7) {
      if (t < 91.3) cam = camKeys(t, [[81, [RX(52) + 1, 2.0, 52], [RX(70) - 24, 2.2, 66]], [91.3, [RX(62) - 2, 2.2, 62], [RX(70) - 26, 2.4, 70]]]);
      else cam = camKeys(t, [[91.3, [RX(150) + 9, 7, 150], [0, 6, 6]], [98, [RX(138) + 8, 8.5, 138], [0, 6.5, 6]]]);
      Object.assign(o, { moths: 20, sun: 0.6 }); verseDay = true;
    } else if (idx === 8) {
      cam = camKeys(t, [[98, [4.2, 1.3, 11.2], [0.9, 1.3, 5.4]], [108.7, [3.2, 1.2, 9.8], [1.0, 1.35, 5.2]]]);
      const sk = sm(102.5, 104.6, t) * (1 - sm(107.4, 108.6, t));
      Object.assign(o, { moths: 120, shapeK: sk, rays: 0.35 * (1 - sk), mothScatter: sm(107.4, 108.7, t) * 0.6, bloom: 0.55 - 0.3 * sk });
      ky = { tilt: 0.12 * sm(104.2, 105.8, t) * (1 - sm(107.6, 108.6, t)), lift: 0.04 + 0.1 * sm(104.2, 105.8, t) * (1 - sm(107.6, 108.6, t)) };
    } else if (idx === 9) {
      const a = (t - 108.7) * 0.03;
      cam = { pos: [Math.sin(a) * 70, 90, 6 + Math.cos(a) * 70], look: [0, 0, 6] };
      if (t > 116) cam = camKeys(t, [[116, [-2.8, 2.0, 9.8], [-0.25, 2.45, 3.8]], [123.3, [-1.8, 2.3, 8.6], [-0.25, 2.45, 3.8]]]);
      const lt = t - 108.7, tick = Math.floor(lt * 2.367) % 4;
      Object.assign(o, { moths: 45, snow: sm(108.7, 111, t), paper: '#f3eee4', sun: 0.2, clock: t > 116 ? sm(116, 117.5, t) * (1 - sm(122.4, 123.3, t)) : 0, time: [9, 30 + tick * 0.25], rays: 0.4 });
    } else if (idx === 10) {
      const a = (t - 123.3) * 0.05;
      cam = { pos: [Math.sin(a) * 16, 3 + (t - 123.3) * 0.5, 6 + Math.cos(a) * 16], look: [0, 3.5, 4] };
      if (t > 136) cam = camKeys(t, [[136, [RX(40) + 6, 14, 40], [0, 6, 4]], [148.3, [RX(70) + 4, 22, 70], [0, 6, 4]]]);
      Object.assign(o, { moths: 110, rays: 1, rings: 1, glow: 1.25 + 0.25 * bar, bloom: 0.7, sun: (t - 123.3) / 25 });
      typeAt = { day: t > 136 }; verse = false;
    } else if (idx === 11) {
      cam = camKeys(t, [[148.3, [5.5, 1.0, 14], [0.4, 1.0, 6]], [159.3, [3.9, 1.2, 10.5], [0.4, 1.1, 6]]]);
      Object.assign(o, { dawn: 0.85 * sm(150, 158.8, t), moths: 30, rays: 0.3, sun: 0.5 });
    } else if (idx === 12) {
      cam = camKeys(t, [[159.3, [3.0, 1.6, 9.2], [-0.2, 2.2, 4.2]], [163.4, [3.4, 1.4, 9.6], [-0.2, 2.1, 4.2]], [168, [12, 6, 30], [0, 2.5, 4]]]);
      const snap = sm(165.0, 165.6, t);
      Object.assign(o, { dawn: 0.85 * (1 - snap), moths: 70, rays: 0.3 + 0.7 * snap, rim: 1 + 2 * (1 - sm(165, 167.5, t)) * snap, sun: 0.5 });
    } else if (idx === 13) {
      const a = (t - 168) * 0.02;
      cam = { pos: [Math.sin(a) * 60 + 30, 34 - (t - 168) * 0.9, 120 + Math.cos(a) * 40], look: [0, 2, 40] };
      const nf = sm(174, 180, t);
      Object.assign(o, { dome: 26 * Math.pow(4000 / 26, E.inOutSine(sm(173.5, 182, t))), neighbours: sm(178, 185, t), wave: kf(t, [[177, 0], [186.5, 1.15]], E.inOutSine), moths: 100, rays: 1, rings: 1, glow: 1.3 + 0.2 * bar, sun: 0.85 - nf * 0.4 });
      typeAt = { day: t < 178 }; verse = false;
    } else if (idx === 14) {
      const dn = sm(188, 197, t);
      cam = camKeys(t, [[186.5, [RX(30) + 3, 4, 30], [0, 3, 5]], [208.4, [RX(150) + 10, 30, 150], [0, 4, 4]]]);
      Object.assign(o, { neighbours: 1 - dn, wave: 1.2, dome: 26 * Math.pow(4000 / 26, 1 - E.inOutSine(sm(188, 198, t))), moths: 40 * (1 - sm(200, 206, t)), sun: 0.2 + dn * 0.2 });
      typeAt = t < 193.5 ? { day: dn > 0.5 } : null;
      verse = t >= 193.5;
    }

    // handheld breathing: a few cm of slow drift, scaled with the shot's distance to its target
    { const dist = Math.hypot(cam.pos[0] - cam.look[0], cam.pos[1] - cam.look[1], cam.pos[2] - cam.look[2]);
      const k = Math.min(0.5, 0.012 * dist + 0.03);
      cam = { pos: [cam.pos[0] + M.noise1(t * 0.35, 11) * k, cam.pos[1] + M.noise1(t * 0.3, 12) * k * 0.6, cam.pos[2] + M.noise1(t * 0.33, 13) * k],
              look: [cam.look[0] + M.noise1(t * 0.28, 14) * k * 0.5, cam.look[1] + M.noise1(t * 0.31, 15) * k * 0.4, cam.look[2]] }; }
    set.update(t, u, { ...o, cam: cam.pos, look: cam.look });
    set.camera.updateMatrixWorld();
    const kr = keeperUpdate(t, set.camera, ky);
    if (o.shapeK) {
      const right = kr.right.clone().setY(0).normalize();
      const pts = S.outline.map(([x, y]) => [kr.flip ? -x : x, y]);
      set.setFigure(pts, new THREE.Vector3(1.2, 0.57, 5.35), right);
    }
    S.type.mesh.visible = false;
    G.renderSet(ctx, set, t, u, { ...o, cam: cam.pos, look: cam.look });
    set.camera.updateMatrixWorld();
    const pv = BULB.clone().project(set.camera);
    const focus = (pv.z < 1 && Math.abs(pv.x) < 1.15 && Math.abs(pv.y) < 1.15) ? [(pv.x + 1) / 2 * W, (1 - pv.y) / 2 * H] : null;
    const info = { verse, verseDay: dayFraction(set.camera, 0.9), typeAt, chorusDay: dayFraction(set.camera, 0.22), focus };
    return info;
  }

function overlays(ctx, u, t, I) {
  const { verse, verseDay, typeAt } = I;
    if (t >= 8.5 && t < 16.3) title(ctx, t, 9.0, 16.0, { y: H * 0.14, day: true });
    if (t < 8.5) introMoth(ctx, t);
    if (t >= 0.8 && t < 8.5) title(ctx, t, 3.4, 8.3, { y: H * 0.36 });
    if (t >= 199) title(ctx, t, 199.5, 207.5, { y: H * 0.14, day: true });
    if (verse) verseLine(ctx, t, { day: verseDay });
    if (typeAt) chorusLine(ctx, t, { day: I.chorusDay });
}

// ------------------------------------------------------------------ YouTube thumbnails (film time >= 300: t = 300 / 301 / 302)
// Re-staged hero frames of the film's own world + bold thumbnail type (Montserrat Black, SIL OFL).
function bigText(ctx, lines, x, y, size, { align = 'left', fill = '#fff6e0', stroke = '#0a0f24', tilt = -0.025, accent = null } = {}) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(tilt);
  lines.forEach((ln, i) => {
    const s = ln.size || size, yy = i * size * 0.98;
    ctx.font = `900 ${s}px Thumb`; ctx.textAlign = align; ctx.lineJoin = 'round';
    // drop shadow, thick outline, fill (the YouTube-thumbnail recipe)
    ctx.shadowColor = 'rgba(0,0,0,0.75)'; ctx.shadowBlur = 28; ctx.shadowOffsetY = 10;
    ctx.lineWidth = s * 0.16; ctx.strokeStyle = stroke; ctx.strokeText(ln.t, 0, yy);
    ctx.shadowColor = 'transparent';
    const g = ctx.createLinearGradient(0, yy - s * 0.8, 0, yy);
    const c = ln.color || fill; g.addColorStop(0, c); g.addColorStop(1, ln.color2 || c);
    ctx.fillStyle = g; ctx.fillText(ln.t, 0, yy);
  });
  ctx.restore();
}
function serifTag(ctx, txt, x, y, size, color = '#f3e7cf', align = 'left') {
  ctx.save(); ctx.font = `italic 600 ${size}px Display`; ctx.textAlign = align; ctx.letterSpacing = `${size * 0.04}px`;
  ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 16; ctx.fillStyle = color; ctx.fillText(txt, x, y); ctx.restore();
}
function grade(ctx, warm = 0.18) {   // punchier contrast + saturation for the small-size read
  ctx.save(); ctx.globalCompositeOperation = 'soft-light'; ctx.fillStyle = `rgba(255,190,110,${warm})`; ctx.fillRect(0, 0, W, H); ctx.restore();
  const g = ctx.createRadialGradient(W * 0.5, H * 0.5, H * 0.3, W * 0.5, H * 0.5, H * 1.05);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(4,6,18,0.6)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}
function thumbDraw(ctx, u, t) {
  const set = S.w, k = Math.round(t - 300);
  S.pages.forEach((p) => (p.visible = false)); S.type.mesh.visible = false;
  U.uDayPaper.value.set('#efe3c8');
  let o, cam, ky = {};
  const tt = 33.4;   // a moment with the moths in flight
  if (k === 0) {        // A: the blazing lantern, her on the steps
    cam = { pos: [1.0, 0.9, 8.5], look: [-2.0, 1.6, 4.2] };
    o = { moths: 110, rays: 1, rings: 0.6, glow: 1.6, bloom: 1.1, windows: 1, fov: 45 };
  } else if (k === 1) { // B: the night dome in a sunlit valley
    cam = { pos: [RX(92) + 7, 16, 92], look: [0, 6.5, 5] };
    o = { moths: 20, sun: 0.42, glow: 1.4, rim: 2.2, bloom: 0.9 };
  } else {              // C: the shape of someone beside her
    cam = { pos: [2.6, 1.15, 8.5], look: [0.25, 1.3, 5.3] };
    o = { moths: 120, shapeK: 1, rays: 0.2, glow: 1.5, bloom: 1.0, figWidth: 3.2 };
    ky = { tilt: 0.12, lift: 0.14 };
  }
  set.update(tt, U_(tt), { ...o, cam: cam.pos, look: cam.look });
  set.camera.updateMatrixWorld();
  const kr = keeperUpdate(tt, set.camera, ky);
  if (o.shapeK) { const right = kr.right.clone().setY(0).normalize(); set.setFigure(S.outline.map(([x, y]) => [kr.flip ? -x : x, y]), new THREE.Vector3(1.2, 0.57, 5.35), right); }
  G.renderSet(ctx, set, tt, U_(tt), { ...o, cam: cam.pos, look: cam.look });
  grade(ctx, k === 1 ? 0.1 : 0.2);
  if (k === 0) {
    // extra bloom on the bulb: a big warm halo makes the focal point pop at phone size
    const pv = BULB.clone().project(set.camera), bx = (pv.x + 1) / 2 * W, by = (1 - pv.y) / 2 * H;
    const g = ctx.createRadialGradient(bx, by, 0, bx, by, 420); g.addColorStop(0, 'rgba(255,230,180,0.85)'); g.addColorStop(0.25, 'rgba(255,180,90,0.35)'); g.addColorStop(1, 'rgba(255,160,70,0)');
    ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
    bigText(ctx, [{ t: 'SHE NEVER' }, { t: 'TURNS IT', color: '#ffd36b', color2: '#ff9d2e' }, { t: 'OFF', color: '#ffd36b', color2: '#ff9d2e' }], 70, 280, 196);
    serifTag(ctx, TITLE(), 82, 1000, 64);
  } else if (k === 1) {
    const pv = BULB.clone().project(set.camera), bx = (pv.x + 1) / 2 * W, by = (1 - pv.y) / 2 * H;
    // hand-drawn gold circle + arrow pointing at the house (the classic thumbnail pointer)
    ctx.save(); ctx.strokeStyle = '#ffcf4a'; ctx.lineWidth = 14; ctx.lineCap = 'round'; ctx.shadowColor = 'rgba(0,0,0,0.6)'; ctx.shadowBlur = 14;
    ctx.beginPath(); ctx.ellipse(bx + 6, by + 18, 190, 120, -0.05, 0.25, Math.PI * 2 + 0.05); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx + 560, by + 330); ctx.quadraticCurveTo(bx + 420, by + 330, bx + 250, by + 150); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(bx + 250, by + 150); ctx.lineTo(bx + 330, by + 165); ctx.moveTo(bx + 250, by + 150); ctx.lineTo(bx + 268, by + 228); ctx.stroke();
    ctx.restore();
    bigText(ctx, [{ t: "IT'S ALWAYS" }, { t: 'NIGHT HERE', color: '#ffd36b', color2: '#ff9d2e' }], W / 2, 190, 190, { align: 'center', tilt: 0 });
    serifTag(ctx, TITLE(), W - 80, 1010, 64, '#1c2547', 'right');
  } else {
    // make the figure of light the subject: a warm glow behind the outline
    { const c = new THREE.Vector3(1.2, 1.45, 5.35).project(set.camera), fx = (c.x + 1) / 2 * W, fy = (1 - c.y) / 2 * H;
      const g = ctx.createRadialGradient(fx, fy, 0, fx, fy, 520); g.addColorStop(0, 'rgba(255,215,150,0.55)'); g.addColorStop(0.4, 'rgba(255,170,80,0.22)'); g.addColorStop(1, 'rgba(255,150,60,0)');
      ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore(); }
    bigText(ctx, [{ t: 'STILL' }, { t: 'WAITING', color: '#ffd36b', color2: '#ff9d2e' }], 70, 250, 220, { tilt: -0.02 });
    serifTag(ctx, "for someone who's gone", 86, 560, 74);
    serifTag(ctx, TITLE(), W - 80, 1010, 64, '#f3e7cf', 'right');
  }
}
const U_ = (t) => M.U(t);
