// linework.js: the "Midnight Linework" valley. House front faces +z; the road runs from the house toward +z.
// opts for update(): cam, look, fov, roll, dome (radius), night (0..1 global), glow, rays (0..1), rings,
//   moths (count), mothScatter, bulb (0..1), windows (0..1), shapeK (moths -> person outline 0..1)
import * as G from '../lib/gl.js';
import { THREE, U, COMMON, lines, poly, circle, edgesOf, fillMat, sky, rnd } from './ink.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { noise1, clamp, lerp } from '../lib/motion.js';

export const DOME_C = [0, 0, 6];
export const roadX = (z) => { const s = 1 / (1 + Math.exp(-(z - 40) / 12)); return s * (16 * Math.sin((z - 40) / 75) + 34 * Math.sin((z - 40) / 260)); };
export const BULB = new THREE.Vector3(-0.25, 2.47, 3.72);

function addFill(list, geo, m4) { const g = geo.clone(); if (m4) g.applyMatrix4(m4); list.push(g); }

// ------------------------------------------------------------------ house (fills + edge lines)
function house(segs, fills, litFills, at = [0, 0, 0], rotY = 0, s = 1, detail = true) {
  const M = new THREE.Matrix4().compose(new THREE.Vector3(...at), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, rotY, 0)), new THREE.Vector3(s, s, s));
  const add = (geo, x, y, z, ry = 0, edgeAngle = 25) => {
    const m = new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, ry, 0)), new THREE.Vector3(1, 1, 1)).premultiply(M);
    addFill(fills, geo, m); edgesOf(geo, m, edgeAngle, segs);
  };
  const box = (w, h, d, x, y, z) => add(new THREE.BoxGeometry(w, h, d), x, y, z);
  box(8.4, 0.5, 7.4, 0, 0.25, 0);
  box(8, 3, 7, 0, 2, 0);
  // gable roof
  const sh = new THREE.Shape([new THREE.Vector2(-4.1, 0), new THREE.Vector2(4.1, 0), new THREE.Vector2(0, 2.4)]);
  const rg = new THREE.ExtrudeGeometry(sh, { depth: 8.8, bevelEnabled: false }); rg.rotateY(Math.PI / 2); rg.translate(-4.4, 3.5, 0);
  add(rg, 0, 0, 0, 0, 20);
  box(0.7, 2.7, 0.7, 2.6, 4.95, -1.2);               // chimney: from inside the walls up through the roof
  // siding lines on the front wall (the engraved look)
  for (let y = 0.85; y < 3.45; y += 0.24) {
    for (const [x0, x1] of [[-4, -3.1], [-1.75, 0.15], [1.35, 2.05], [3.45, 4]]) {
      const a = new THREE.Vector3(x0, y, 3.51).applyMatrix4(M), b = new THREE.Vector3(x1, y, 3.51).applyMatrix4(M);
      segs.push(a.x, a.y, a.z, b.x, b.y, b.z);
    }
  }
  // windows (lit fills) + muntins, door
  for (const [x, y, w, h] of [[-2.45, 2.15, 1.3, 1.45], [2.75, 2.15, 1.3, 1.45]]) {
    const g = new THREE.PlaneGeometry(w, h); const m = new THREE.Matrix4().makeTranslation(x, y, 3.52).premultiply(M); addFill(litFills, g, m);
    const P = (px, py) => new THREE.Vector3(px, py, 3.53).applyMatrix4(M).toArray();
    poly([P(x - w / 2, y - h / 2), P(x + w / 2, y - h / 2), P(x + w / 2, y + h / 2), P(x - w / 2, y + h / 2)], true, segs);
    poly([P(x, y - h / 2), P(x, y + h / 2)], false, segs); poly([P(x - w / 2, y), P(x + w / 2, y)], false, segs);
    // curtains: a few drape folds each side
    for (const sd of [-1, 1]) for (let k = 0; k < 3; k++) { const cx = x + sd * (w / 2 - 0.08 - k * 0.09); const pts = []; for (let j = 0; j <= 8; j++) { const yy = y + h / 2 - j * h / 8; pts.push(P(cx - sd * 0.04 * Math.sin(j * 0.9), yy)); } poly(pts, false, segs); }
  }
  box(1.05, 2.15, 0.1, 0.75, 1.57, 3.52);
  // porch: deck, posts, roof, rail, steps
  box(8.8, 0.14, 2.6, 0, 0.5, 4.8);                   // deck boards (top at 0.57)
  // structure under the deck: piers under every post and at the wall, a rim beam, lattice panels between
  const piersX = [-4.2, -0.4, 1.9, 4.2];
  for (const x of piersX) for (const z of [3.75, 6.0]) box(0.2, 0.43, 0.2, x, 0.215, z);
  box(8.8, 0.12, 0.08, 0, 0.37, 6.08);                // rim beam along the front
  for (const z of [3.75, 6.0]) box(8.6, 0.1, 0.12, 0, 0.38, z);   // joist carriers
  { const LP = (px, py, pz) => new THREE.Vector3(px, py, pz).applyMatrix4(M).toArray();
    const lattice = (x0, x1, z) => { for (let u = x0; u < x1 + 0.3; u += 0.18) {
        const a0 = [Math.max(x0, u - 0.3), 0.31 - (Math.max(x0, u - 0.3) - (u - 0.3))], a1 = [Math.min(x1, u), 0.01 + (u - Math.min(x1, u))];
        segs.push(...LP(a0[0], Math.min(0.31, a0[1]), z), ...LP(a1[0], Math.max(0.01, a1[1]), z));
        const b0 = [Math.max(x0, u - 0.3), 0.01 + (Math.max(x0, u - 0.3) - (u - 0.3))], b1 = [Math.min(x1, u), 0.31 - (u - Math.min(x1, u))];
        segs.push(...LP(b0[0], Math.max(0.01, b0[1]), z), ...LP(b1[0], Math.min(0.31, b1[1]), z)); } };
    for (let i = 0; i < piersX.length - 1; i++) {
      const x0 = piersX[i] + 0.1, x1 = piersX[i + 1] - 0.1;
      if (x0 < 1.75 && x1 > -0.25) { lattice(x0, -0.25, 6.09); lattice(1.75, x1, 6.09); } else lattice(x0, x1, 6.09);
    }
    const back = new THREE.PlaneGeometry(8.4, 0.31); const bm = new THREE.Matrix4().makeTranslation(0, 0.155, 5.95).premultiply(M); addFill(fills, back, bm);   // dark space behind the lattice
  }
  for (const x of [-4.2, -0.4, 1.9, 4.2]) box(0.16, 2.72, 0.16, x, 1.93, 6.0);
  box(8.7, 0.2, 0.16, 0, 3.39, 6.0);                  // header beam on the posts, carries the porch roof
  const pr = new THREE.BoxGeometry(9.0, 0.1, 3.0); pr.rotateX(0.1); add(pr, 0, 3.36, 4.85, 0, 20);
  for (const [a, b] of [[-4.2, -0.4], [1.9, 4.2]]) {
    const P = (px, py) => new THREE.Vector3(px, py, 6.0).applyMatrix4(M).toArray();
    poly([P(a, 1.4), P(b, 1.4)], false, segs); poly([P(a, 0.65), P(b, 0.65)], false, segs);
    for (let x = a + 0.16; x < b - 0.05; x += 0.16) poly([P(x, 0.65), P(x, 1.4)], false, segs);
  }
  for (let i = 0; i < 3; i++) { const top = 0.46 - i * 0.16; box(2.0, top, 0.34, 0.75, top / 2, 6.25 + i * 0.32); }   // each step stands on the ground
  // side railings on the porch ends (house wall to the front posts)
  { const SP = (px, py, pz) => new THREE.Vector3(px, py, pz).applyMatrix4(M).toArray();
    for (const x of [-4.2, 4.2]) { poly([SP(x, 1.4, 3.5), SP(x, 1.4, 6.0)], false, segs); poly([SP(x, 0.65, 3.5), SP(x, 0.65, 6.0)], false, segs);
      for (let z = 3.66; z < 5.95; z += 0.16) poly([SP(x, 0.65, z), SP(x, 1.4, z)], false, segs); } }
  if (detail) {
    // the lantern
    box(0.16, 0.32, 0.04, -0.25, 2.45, 3.56);
    const lg = new THREE.CylinderGeometry(0.085, 0.07, 0.26, 4, 1, true); lg.rotateY(Math.PI / 4); add(lg, -0.25, 2.47, 3.72);
    const cap = new THREE.ConeGeometry(0.14, 0.1, 4); cap.rotateY(Math.PI / 4); add(cap, -0.25, 2.65, 3.72);
    // the rocking chair, as lines only
    const C = (px, py, pz) => new THREE.Vector3(px, py, pz).applyMatrix4(M).toArray();
    const cx = -2.7, cz = 4.9;
    poly([C(cx - 0.28, 1.0, cz), C(cx + 0.28, 1.0, cz), C(cx + 0.28, 1.0, cz + 0.5), C(cx - 0.28, 1.0, cz + 0.5)], true, segs);
    poly([C(cx - 0.28, 1.0, cz), C(cx - 0.28, 1.75, cz - 0.08), C(cx + 0.28, 1.75, cz - 0.08), C(cx + 0.28, 1.0, cz)], false, segs);
    for (const sx of [-0.28, 0.28]) {
      const arc = []; for (let i = 0; i <= 12; i++) { const a = -0.7 + 1.4 * i / 12; arc.push(C(cx + sx, 0.62 + 0.25 * (1 - Math.cos(a)), cz + 0.25 + Math.sin(a) * 0.55)); }
      poly(arc, false, segs);
    }
  }
}

function conifer(segs, fills, x, z, h, r) {
  const g = new THREE.ConeGeometry(h * 0.26, h * 0.8, 6, 1); g.translate(0, h * 0.5, 0);
  const g2 = new THREE.ConeGeometry(h * 0.2, h * 0.6, 6, 1); g2.translate(0, h * 0.78, 0);
  const t = new THREE.CylinderGeometry(h * 0.025, h * 0.03, h * 0.25, 5); t.translate(0, h * 0.12, 0);
  const m = new THREE.Matrix4().compose(new THREE.Vector3(x, 0, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, r() * 6, 0)), new THREE.Vector3(1, 1, 1));
  for (const gg of [g, g2, t]) { addFill(fills, gg, m); }
  edgesOf(g, m, 40, segs); edgesOf(g2, m, 40, segs);
}
function roundTree(segs, fills, x, z, h, r) {
  const c = new THREE.IcosahedronGeometry(h * 0.32, 0); c.scale(1, 0.9, 1); c.translate(0, h * 0.68, 0);
  const t = new THREE.CylinderGeometry(h * 0.03, h * 0.045, h * 0.45, 5); t.translate(0, h * 0.22, 0);
  const m = new THREE.Matrix4().compose(new THREE.Vector3(x, 0, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, r() * 6, 0)), new THREE.Vector3(1, 1, 1));
  addFill(fills, c, m); addFill(fills, t, m); edgesOf(c, m, 10, segs); edgesOf(t, m, 40, segs);
}

// a moth drawn as gold line-art (canvas), for instanced sprites
function mothTexture() {
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 128; const c = cv.getContext('2d');
  c.translate(128, 64); c.strokeStyle = '#fff'; c.lineWidth = 4; c.lineJoin = 'round';
  for (const s of [-1, 1]) {
    c.save(); c.scale(s, 1);
    c.beginPath(); c.moveTo(4, -6); c.bezierCurveTo(50, -64, 118, -40, 112, -6); c.bezierCurveTo(106, 18, 50, 14, 4, 4); c.stroke();
    c.beginPath(); c.moveTo(4, 6); c.bezierCurveTo(40, 14, 76, 48, 56, 56); c.bezierCurveTo(30, 62, 10, 34, 4, 10); c.stroke();
    c.lineWidth = 2; c.beginPath(); c.moveTo(10, -2); c.lineTo(92, -24); c.moveTo(12, 2); c.lineTo(96, -2); c.moveTo(10, 8); c.lineTo(46, 40); c.stroke();
    c.beginPath(); c.arc(70, -18, 9, 0, 7); c.stroke();
    c.lineWidth = 2.5; c.beginPath(); c.moveTo(2, -26); c.quadraticCurveTo(14, -52, 30, -58); c.stroke();
    c.restore();
  }
  c.beginPath(); c.ellipse(0, 4, 6, 26, 0, 0, 7); c.lineWidth = 4; c.stroke();
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export function lineworldSet() {
  const scene = new THREE.Scene();
  const cam = G.camera(35, 0.05, 3000);
  U.uDomeC.value.set(...DOME_C);
  const skyMesh = sky(scene);
  const r = rnd(5);
  const segs = [], fills = [], lit = [], segsAccent = [], treeFills = [], treeSegs = [];

  // ground + field linework
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000, 64, 64), fillMat('#ecdfc4', '#0c1534', { shade: 0 })); ground.rotation.x = -Math.PI / 2; scene.add(ground);
  // road edges + centre dashes, path
  const L = [], R = [];
  for (let z = 7.2; z < 1400; z += z < 80 ? 1 : 4) { const x = roadX(z) + 0.75; L.push([x - 3.2, 0.02, z]); R.push([x + 3.2, 0.02, z]); }
  poly(L, false, segs); poly(R, false, segs);
  for (let z = 20; z < 900; z += 6) { const x = roadX(z) + 0.75, x2 = roadX(z + 2.6) + 0.75; segs.push(x, 0.02, z, x2, 0.02, z + 2.6); }
  // ploughed fields: patches of parallel furrows (the engraving texture of the valley)
  for (let i = 0; i < 70; i++) {
    const z0 = 30 + r() * 900, side = r() < 0.5 ? -1 : 1, x0 = roadX(z0) + side * (14 + r() * 160);
    const w = 30 + r() * 60, d = 30 + r() * 70, a = (r() - 0.5) * 0.8, step = 2.2 + r() * 2.5;
    const ca = Math.cos(a), sa = Math.sin(a);
    // keep fields off the road (and its verges): reject if any corner or edge midpoint is near it
    const probe = [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2], [0, -d / 2], [0, d / 2], [-w / 2, 0], [w / 2, 0], [0, 0]].map(([u, v]) => [x0 + ca * u - sa * v, z0 + sa * u + ca * v]);
    if (probe.some(([px, pz]) => Math.abs(px - roadX(pz) - 0.75) < 12) || Math.sign(probe[0][0] - roadX(probe[0][1])) !== Math.sign(probe[2][0] - roadX(probe[2][1])) || Math.sign(probe[1][0] - roadX(probe[1][1])) !== Math.sign(probe[3][0] - roadX(probe[3][1]))) continue;
    for (let u = -w / 2; u < w / 2; u += step) {
      const p0 = [x0 + ca * u - sa * (-d / 2), 0.03, z0 + sa * u + ca * (-d / 2)], p1 = [x0 + ca * u - sa * (d / 2), 0.03, z0 + sa * u + ca * (d / 2)];
      segs.push(...p0, ...p1);
    }
    const corners = [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]].map(([u, v]) => [x0 + ca * u - sa * v, 0.03, z0 + sa * u + ca * v]);
    poly(corners, true, segs);
  }
  // layered hills: paper-cut ridges far away (fill strip + outline)
  for (let layer = 0; layer < 4; layer++) {
    const dist = 420 + layer * 180, hgt = 40 + layer * 35, pts = [], tri = [], verts = [];
    for (let i = 0; i <= 160; i++) {
      const a = -1.6 + 3.2 * i / 160, x = Math.sin(a) * dist, z = 40 + Math.cos(a) * dist;
      const y = hgt * (0.55 + 0.45 * Math.sin(i * 0.11 + layer * 2) * Math.cos(i * 0.043 + layer)) + 12 * noise1(i * 0.3, layer + 3);
      pts.push([x, y, z]); verts.push(x, -5, z, x, y, z);
    }
    for (let i = 0; i < 160; i++) { const k = i * 2; tri.push(k, k + 2, k + 1, k + 1, k + 2, k + 3); }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3)); g.setIndex(tri); g.computeVertexNormals();
    const m = new THREE.Mesh(g, fillMat(['#d9cfae', '#d4c3a3', '#cbb898', '#c2ae8f'][layer], ['#101b40', '#0e183a', '#0c1534', '#0a122e'][layer], { shade: 0, side: THREE.DoubleSide }));
    scene.add(m); poly(pts, false, segs);
  }
  // trees: forest behind the house, scattered along the valley
  for (let i = 0; i < 420; i++) {
    let x, z;
    if (i < 140) { x = -70 + r() * 140; z = -14 - r() * 70; } else { z = -20 + r() * 700; x = roadX(z) + (r() < 0.5 ? -1 : 1) * (12 + r() * 140); }
    if (Math.hypot(x - DOME_C[0], z - DOME_C[2]) < 22 && z > -8) continue;
    const h = 7 + r() * 9;
    if (r() < 0.6) conifer(treeSegs, treeFills, x, z, h, r); else roundTree(treeSegs, treeFills, x, z, h * 0.85, r);
  }
  // our house + neighbours
  house(segs, fills, lit, [0, 0, 0], 0, 1, true);
  const NB = [[-26, 70, 0.4], [28, 125, -0.5], [-30, 195, 0.3], [30, 265, -0.4], [-32, 345, 0.2]];
  const nbLit = [];
  NB.forEach(([dx, z, ry]) => { const nl = []; house(segs, fills, nl, [roadX(z) + dx, 0, z], ry + (dx < 0 ? Math.PI / 2 : -Math.PI / 2), 0.9, false); nbLit.push(nl); });
  // life in the daylight: picket fences along the road, washing lines with sheets by the neighbours
  for (let z = 40; z < 420; z += 1.2) {
    if (Math.floor(z / 60) % 2) continue;
    for (const sd of [-1, 1]) { const x = roadX(z) + 0.75 + sd * 6.5; segs.push(x, 0, z, x, 0.9, z); }
  }
  for (const sd of [-1, 1]) for (let z0 = 40; z0 < 420; z0 += 120) { const pts = [], pts2 = []; for (let z = z0; z <= z0 + 60; z += 2) { const x = roadX(z) + 0.75 + sd * 6.5; pts.push([x, 0.75, z]); pts2.push([x, 0.35, z]); } poly(pts, false, segs); poly(pts2, false, segs); }
  const sheets = [];
  NB.forEach(([dx, z], i) => {
    const hx = roadX(z) + dx, side = dx < 0 ? 1 : -1, x0 = hx + side * 2, z0 = z - 9;
    segs.push(x0, 0, z0, x0, 2.2, z0, x0 + side * 0.01, 2.2, z0 + 7, x0, 0, z0 + 7);
    const wire = []; for (let k = 0; k <= 10; k++) wire.push([x0, 2.2 - Math.sin(k / 10 * Math.PI) * 0.15, z0 + k * 0.7]); poly(wire, false, segs);
    for (let k = 0; k < 3; k++) sheets.push([x0, 2.05, z0 + 1 + k * 2.1, i * 3 + k]);
  });
  const sheetGeo = new THREE.PlaneGeometry(1.6, 1.2, 8, 1); sheetGeo.translate(0, -0.6, 0);
  const sheetMat = fillMat('#f7efdd', '#16224d', { shade: 0, side: THREE.DoubleSide });
  const sheetMeshes = sheets.map(([x, y, z, k]) => { const m = new THREE.Mesh(sheetGeo.clone(), sheetMat); m.position.set(x, y, z); m.rotation.y = Math.PI / 2; m.userData.k = k; scene.add(m);
    const e = edgesOf(new THREE.PlaneGeometry(1.6, 1.2).translate(0, -0.6, 0), new THREE.Matrix4().compose(m.position, m.quaternion, new THREE.Vector3(1, 1, 1)), 10, []); segs.push(...e); return m; });

  // the village: small houses across the valley; at night their windows light in a wave outward from hers
  const vWin = [], vDelay = [], vr = rnd(53);
  for (let i = 0; i < 70; i++) {
    const z = 40 + vr() * 520, side = vr() < 0.5 ? -1 : 1, x = roadX(z) + side * (30 + vr() * 220);
    if (Math.hypot(x - DOME_C[0], z - DOME_C[2]) < 40) continue;
    const s = 0.7 + vr() * 0.4, ry = vr() * 6;
    const M4 = new THREE.Matrix4().compose(new THREE.Vector3(x, 0, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, ry, 0)), new THREE.Vector3(s, s, s));
    const b = new THREE.BoxGeometry(6, 3, 5); b.translate(0, 1.5, 0); addFill(fills, b, M4); edgesOf(b, M4, 25, segs);
    const sh = new THREE.Shape([new THREE.Vector2(-2.9, 0), new THREE.Vector2(2.9, 0), new THREE.Vector2(0, 1.9)]);
    const rg = new THREE.ExtrudeGeometry(sh, { depth: 6.4, bevelEnabled: false }); rg.rotateY(Math.PI / 2); rg.translate(-3.2, 3, 0); addFill(fills, rg, M4); edgesOf(rg, M4, 20, segs);
    const d = Math.hypot(x - DOME_C[0], z - DOME_C[2]) / 600;
    for (const wx of [-1.6, 1.6]) { const w = new THREE.PlaneGeometry(1.0, 1.1); w.translate(wx, 1.6, 2.52); w.applyMatrix4(M4); vWin.push(w); vDelay.push(...new Array(w.attributes.position.count).fill(d + vr() * 0.08)); }
  }
  const vGeo = mergeGeometries(vWin); vGeo.setAttribute('aDelay', new THREE.Float32BufferAttribute(vDelay, 1));
  const vMat = new THREE.ShaderMaterial({ toneMapped: false, uniforms: { ...U, uWave: { value: 0 } },
    vertexShader: `attribute float aDelay; varying float vD; varying vec3 vW; void main(){ vD = aDelay; vec4 w = modelMatrix*vec4(position,1.); vW = w.xyz; gl_Position = projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `${COMMON}
      uniform float uWave; varying float vD; varying vec3 vW;
      void main(){ float n = nightAt(vW); float on = smoothstep(vD, vD + 0.04, uWave) * n;
        vec3 off = mix(uDayPaper * 0.97, uNightNavy * 1.6, n); vec3 lit = vec3(1.6, 1.05, 0.5);
        gl_FragColor = vec4(mix(off, lit, on), 1.0); }` });
  scene.add(new THREE.Mesh(vGeo, vMat));

  // telephone poles + sagging wires
  const tops = [];
  for (let i = 0; i < 16; i++) {
    const z = 40 + i * 28, x = roadX(z) + 5.4;
    segs.push(x, 0, z, x, 8, z, x - 1.1, 7.4, z, x + 1.1, 7.4, z);
    tops.push([x, 7.4, z]);
  }
  for (const dx of [-0.95, 0.95]) {
    let prev = null;
    for (const [x, y, z] of tops) {
      if (!prev) { prev = [x + dx, y, z]; continue; }
      const b = [x + dx, y, z], seg = [];
      for (let k = 0; k <= 14; k++) { const f = k / 14; seg.push([lerp(prev[0], b[0], f), lerp(prev[1], b[1], f) - Math.sin(f * Math.PI) * 0.7, lerp(prev[2], b[2], f)]); }
      poly(seg, false, segs); prev = b;
    }
  }
  // dome rim on the ground (the boundary line)
  circle([DOME_C[0], 0.05, DOME_C[2]], 26, 720, 'y', segsAccent);

  const fillMesh = new THREE.Mesh(mergeGeometries(fills.map((g) => g.index ? g.toNonIndexed() : g).map((g) => { ['uv', 'uv1'].forEach((k) => g.deleteAttribute && g.getAttribute(k) && g.deleteAttribute(k)); return g; })), fillMat('#e8d6bc', '#13204a'));
  scene.add(fillMesh);
  const clean = (g) => { g = g.index ? g.toNonIndexed() : g; ['uv', 'uv1'].forEach((k) => g.getAttribute(k) && g.deleteAttribute(k)); return g; };
  scene.add(new THREE.Mesh(mergeGeometries(treeFills.map(clean)), fillMat('#d5d6b4', '#101c42', { sway: 1 })));
  const litMesh = new THREE.Mesh(mergeGeometries(lit), fillMat('#f2e6cc', '#ffb45e', { shade: 0, lit: 1, litCol: '#ffbe6e' })); scene.add(litMesh);
  const nbMats = nbLit.map((nl) => { const m = fillMat('#f2e6cc', '#1a2550', { shade: 0, lit: 0, litCol: '#ffd08a' }); scene.add(new THREE.Mesh(mergeGeometries(nl), m)); return m; });
  // foreground grass tufts: along the road verges, in the yard and around the porch (line-art, they sway)
  const gr = rnd(71), grassSegs = [];
  const tuft = (x, z, hgt) => { const n = 3 + Math.floor(gr() * 3);
    for (let k = 0; k < n; k++) { const a = gr() * 6.28, lean = 0.1 + gr() * 0.25, hh = hgt * (0.6 + gr() * 0.5);
      grassSegs.push(x, 0, z, x + Math.cos(a) * lean * hh, hh, z + Math.sin(a) * lean * hh); } };
  for (let i = 0; i < 1900; i++) {
    let x, z;
    if (i < 500) { z = 7 + gr() * 120; x = roadX(z) + 0.75 + (gr() < 0.5 ? -1 : 1) * (4.2 + gr() * 7); }
    else if (i < 1500) { const a = gr() * 6.28, rr = 6 + gr() * 18; x = Math.cos(a) * rr; z = 2 + Math.sin(a) * rr; if (Math.abs(x) < 4.6 && z > -4 && z < 7.3) continue; }
    else { z = gr() * 300; x = roadX(z) + (gr() < 0.5 ? -1 : 1) * (8 + gr() * 50); }
    tuft(x, z, 0.25 + gr() * 0.3);
  }
  const ink = lines(segs, { width: 1.6, persp: 12 }); scene.add(ink);
  const treeInk = lines(treeSegs, { width: 1.6, persp: 12, sway: 1 }); scene.add(treeInk);
  const grassInk = lines(grassSegs, { width: 0.8, persp: 5, sway: 1, opacity: 0.55 }); scene.add(grassInk);
  // air: gold motes inside the night, dust in the daylight (one particle field around the house and road)
  const AN = 1000, apos = new Float32Array(AN * 3), aph = new Float32Array(AN), ar = rnd(83);
  for (let i = 0; i < AN; i++) { const z = -20 + ar() * 140, x = roadX(Math.max(z, 0)) + (ar() - 0.5) * 60; apos.set([x, 0.3 + ar() * 7, z], i * 3); aph[i] = ar() * 100; }
  const ag = new THREE.BufferGeometry(); ag.setAttribute('position', new THREE.BufferAttribute(apos, 3)); ag.setAttribute('aPh', new THREE.BufferAttribute(aph, 1));
  const airMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, toneMapped: false, uniforms: { ...U, uAir: { value: 1 } },
    vertexShader: `${COMMON}
      attribute float aPh; uniform float uAir; varying float vN; varying float vA;
      void main(){ vec3 p = position; float t = uTime * 0.25 + aPh;
        p += vec3(sin(t * 1.3) * 0.8 + uTime * 0.12, sin(t * 0.9) * 0.4, cos(t * 1.1) * 0.8);
        vec4 mv = viewMatrix * vec4(p, 1.0); gl_Position = projectionMatrix * mv;
        vN = nightAt(p); vA = (0.45 + 0.55 * sin(uTime * 1.7 + aPh * 3.0)) * uAir * smoothstep(60.0, 8.0, -mv.z);
        gl_PointSize = clamp(90.0 / -mv.z, 1.0, 5.0); }`,
    fragmentShader: `uniform vec3 uNightGold, uDayInk; varying float vN; varying float vA;
      void main(){ float d = length(gl_PointCoord - 0.5); if (d > 0.5) discard;
        vec3 c = mix(uDayInk * 1.4, uNightGold * 1.6, vN); float a = vA * (1.0 - smoothstep(0.1, 0.5, d)) * mix(0.18, 0.5, vN);
        gl_FragColor = vec4(c, a); }` });
  const air = new THREE.Points(ag, airMat); air.frustumCulled = false; scene.add(air);
  const rim = lines(segsAccent, { width: 2.2, persp: 0, k: 1 }); scene.add(rim);

  // the bulb + its sunburst rays and rings (in the plane of the house front, facing the road)
  const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 2.6, 1.3), toneMapped: false })); bulb.position.copy(BULB); scene.add(bulb);
  const raySegs = [], rayW = [];
  const rr = rnd(77);
  for (let i = 0; i < 64; i++) {
    const a = (i / 64) * Math.PI * 2, l0 = 0.35 + rr() * 0.2, l1 = l0 + 0.7 + rr() * (i % 4 === 0 ? 2.6 : 1.4);
    raySegs.push(Math.cos(a) * l0, Math.sin(a) * l0, 0, Math.cos(a) * l1, Math.sin(a) * l1, 0); rayW.push(i % 4 === 0 ? 1.6 : 0.8);
  }
  const rays = lines(raySegs, { width: 1.4, persp: 10, k: 1, widths: rayW, opacity: 0.85 }); rays.position.copy(BULB).add(new THREE.Vector3(0, 0, 0.3)); scene.add(rays);
  const ringSegs = []; for (let i = 1; i <= 5; i++) circle([0, 0, 0], [0.3, 0.5, 0.75, 1.05, 1.4][i - 1], 96, 'z', ringSegs);
  const rings = lines(ringSegs, { width: 1.0, persp: 10, k: 1, opacity: 0.7 }); rings.position.copy(rays.position); scene.add(rings);

  // moths: instanced line-art sprites orbiting the bulb (additive gold)
  const MN = 120, mt = mothTexture();
  const mothMat = new THREE.MeshBasicMaterial({ map: mt, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: new THREE.Color(1.5, 1.05, 0.55), toneMapped: false, side: THREE.DoubleSide });
  const moths = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.42, 0.21), mothMat, MN); moths.frustumCulled = false; scene.add(moths);
  const mr = rnd(9), MP = Array.from({ length: MN }, () => ({ rad: 0.25 + mr() * 1.4, sp: (0.7 + mr() * 1.5) * (mr() < 0.5 ? -1 : 1), ph: mr() * 6.28, tilt: mr() - 0.5, flap: 13 + mr() * 9, s: 0.8 + mr() * 0.7, tx: mr(), ty: mr() }));
  // the outline of a person (for "still holds the shape"): sampled points of a standing figure, in the porch plane
  const figure = [];
  { const prof = [[0, 1.78], [0.11, 1.74], [0.13, 1.6], [0.09, 1.5], [0.22, 1.42], [0.26, 1.1], [0.2, 0.95], [0.24, 0.6], [0.16, 0.02], [0.05, 0.02], [0.06, 0.8], [0, 0.85]];
    for (let i = 0; i < MN; i++) { const f = i / MN * 2, side = f < 1 ? 1 : -1, ff = f % 1, k = ff * (prof.length - 1), j = Math.floor(k), t = k - j;
      const a = prof[j], b = prof[Math.min(j + 1, prof.length - 1)]; figure.push([side * lerp(a[0], b[0], t) * 1.1, lerp(a[1], b[1], t) * 1.05]); } }
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), p = new THREE.Vector3();
  const FIG = new Float32Array(MN * 3);
  const FO = new THREE.Vector3(1.0, 0.64, 5.6), FR = new THREE.Vector3(1, 0, 0);
  const figLines = lines(new Array(MN * 6).fill(0), { width: 1.6, persp: 0, k: 0, opacity: 0.8 }); scene.add(figLines);

  // clock: numerals ring + two hands, centred on the lantern, facing the camera
  const clock = new THREE.Group(); clock.position.copy(BULB).add(new THREE.Vector3(0, 0, 0.35)); scene.add(clock);
  { const cv = document.createElement('canvas'); cv.width = cv.height = 1024; const c = cv.getContext('2d');
    c.translate(512, 512); c.strokeStyle = '#fff'; c.fillStyle = '#fff'; c.lineWidth = 3;
    c.beginPath(); c.arc(0, 0, 500, 0, 7); c.stroke(); c.beginPath(); c.arc(0, 0, 470, 0, 7); c.lineWidth = 1.5; c.stroke();
    c.font = '500 64px Display'; c.textAlign = 'center'; c.textBaseline = 'middle';
    const R = ['XII', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
    R.forEach((n, i) => { const a = i / 12 * Math.PI * 2; c.save(); c.translate(Math.sin(a) * 405, -Math.cos(a) * 405); c.rotate(a); c.fillText(n, 0, 0); c.restore(); });
    for (let i = 0; i < 60; i++) { const a = i / 60 * Math.PI * 2, r0 = i % 5 ? 455 : 440; c.lineWidth = i % 5 ? 2 : 4; c.beginPath(); c.moveTo(Math.sin(a) * r0, -Math.cos(a) * r0); c.lineTo(Math.sin(a) * 470, -Math.cos(a) * 470); c.stroke(); }
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const face = new THREE.Mesh(new THREE.PlaneGeometry(3.6, 3.6), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: new THREE.Color(1.3, 0.92, 0.5), toneMapped: false }));
    clock.add(face); clock.userData.face = face; }
  const hand = (len, w) => { const g = new THREE.PlaneGeometry(w, len); g.translate(0, len / 2 - 0.08, 0.01); const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: new THREE.Color(1.6, 1.15, 0.6), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false })); clock.add(m); return m; };
  const hourH = hand(0.85, 0.035), minH = hand(1.35, 0.022);
  // a car leaving: two red tail-lights moving away down the road
  const tail = new THREE.Group(); scene.add(tail);
  const tl = (x) => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.09, 10, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 0.5, 0.3), toneMapped: false })); m.position.x = x; tail.add(m); };
  tl(-0.7); tl(0.7);
  // snow: ink flakes over the whole valley, culled inside the dome by the shader
  const SN = 6000, spos = new Float32Array(SN * 3), sr = rnd(31);
  for (let i = 0; i < SN; i++) spos.set([sr() * 400 - 200, sr(), sr() * 500 - 60], i * 3);
  const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(spos, 3));
  const snowMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, toneMapped: false, uniforms: { ...U, uSnow: { value: 0 }, uSpeed: { value: 3 } },
    vertexShader: `uniform float uTime, uSpeed; uniform vec3 uDomeC; uniform float uDomeR; varying float vA;
      void main(){ vec3 p = position; float y = mod(p.y * 40.0 - uTime * uSpeed, 40.0); p.y = y; p.x += sin(uTime * 0.6 + position.z) * 0.8;
        vec4 mv = viewMatrix * vec4(p, 1.0); gl_Position = projectionMatrix * mv;
        float inside = step(length(p - uDomeC), uDomeR);
        vA = 1.0 - inside; gl_PointSize = clamp(220.0 / -mv.z, 1.0, 7.0); }`,
    fragmentShader: `uniform float uSnow; uniform vec3 uDayInk; varying float vA; void main(){ float d = length(gl_PointCoord - 0.5); if (d > 0.5) discard; gl_FragColor = vec4(uDayInk, uSnow * vA * (1.0 - smoothstep(0.2, 0.5, d))); }` });
  const snow = new THREE.Points(sg, snowMat); snow.frustumCulled = false; scene.add(snow);

  const SET = {
    setFigure(pts, origin, right) { for (let i = 0; i < MN; i++) figure[i] = pts[Math.floor(i * pts.length / MN)]; FO.copy(origin); FR.copy(right); },
    scene, camera: cam, bloom: 0.55, bloomThreshold: 1.0, bloomRadius: 0.35,
    update(t, u, o = {}) {
      G.lookFrom(cam, o.cam || [0.8, 1.6, 60], o.look || [0.3, 2.2, 3], o.roll || 0);
      cam.aspect = (G.R.domElement.width / G.R.domElement.height); cam.fov = (o.fov || 35) * (cam.aspect < 1 ? 1.75 : 1); cam.updateProjectionMatrix();
      U.uDomeR.value = o.dome ?? 26; U.uNight.value = o.night ?? 0; U.uTime.value = t; U.uInDay.value = o.inDay ?? 0; U.uDawn.value = o.dawn ?? 0;
      U.uGlow.value = o.glow ?? 1.15; U.uRim.value = o.rim ?? 1;
      U.uRes.value.set(1920, 1080);   // line widths are in 1080p pixels at any render scale
      const B = o.bulb ?? 1;
      bulb.material.color.setRGB(0.2 + 4 * B, 0.2 + 2.6 * B, 0.2 + 1.3 * B);
      const bn = Math.max(U.uNight.value, clamp((U.uDomeR.value + 1 - BULB.distanceTo(new THREE.Vector3(...DOME_C))) / 2));
      const above = clamp(1 - (cam.position.y - BULB.y - 1.5) / 5);   // fade rays/rings for high cameras
      const front = clamp((cam.position.z - BULB.z) / 3);             // and when looking from behind/side of the wall
      const rk = (o.rays ?? 1) * B * bn * above * front;
      rays.visible = rk > 0.01; rays.material.uniforms.uOpacity.value = 0.85 * rk; rays.rotation.z = t * 0.03;
      rays.scale.setScalar(0.6 + 0.4 * rk);
      rings.visible = (o.rings ?? 1) * B * bn * above * front > 0.01; rings.material.uniforms.uOpacity.value = 0.6 * (o.rings ?? 1) * B * bn * above * front;
      rings.scale.setScalar(1 + 0.08 * Math.sin(t * 1.3)); rings.lookAt(cam.position);
      rays.lookAt(cam.position);
      litMesh.material.uniforms.uLit.value = o.windows ?? 1;
      const nk = o.neighbours ?? 0; nbMats.forEach((m, i) => { m.uniforms.uLit.value = clamp(nk * nbMats.length - i); });
      // moths
      const count = o.moths ?? 30, sk = clamp(o.shapeK ?? 0), sct = o.mothScatter ?? 0;
      for (let i = 0; i < MN; i++) {
        const M = MP[i], here = clamp(count - i);
        const a = M.ph + t * M.sp, wr = M.rad * (1 + 0.3 * noise1(t * 0.8, i + 3)) + (1 - here) * 8 + sct * (3 + 6 * M.tx);
        p.set(BULB.x + Math.cos(a) * wr, BULB.y + Math.sin(a * 0.7 + M.ph) * 0.45 * wr + 0.3 * noise1(t * 1.2, i + 7) + (1 - here) * 3, BULB.z + 0.4 + Math.sin(a) * wr * 0.6);
        if (sk > 0) { const [fx, fy] = figure[i]; const tgt = FO.clone().addScaledVector(FR, fx).add(new THREE.Vector3(0, fy, 0)); tgt.x += 0.015 * noise1(t * 3, i); tgt.y += 0.015 * noise1(t * 3, i + 50); p.lerp(tgt, sk); FIG[i * 3] = p.x; FIG[i * 3 + 1] = p.y; FIG[i * 3 + 2] = p.z; }
        const fl = 0.3 + 0.7 * Math.abs(Math.sin(t * M.flap + M.ph));
        e.set(M.tilt * 0.6, -a + Math.PI / 2, 0.2 * Math.sin(t * 2 + M.ph)); q.setFromEuler(e);
        if (sk > 0.5) q.slerp(cam.quaternion, (sk - 0.5) * 2);
        const vis = here > 0 ? M.s * (1 - 0.72 * sk) : 0; sc.set(fl * vis, vis, 1);
        m4.compose(p, q, sc); moths.setMatrixAt(i, m4);
      }
      moths.instanceMatrix.needsUpdate = true;
      const wantB = bn > 0.98 ? THREE.AdditiveBlending : THREE.NormalBlending; if (mothMat.blending !== wantB) { mothMat.blending = wantB; mothMat.needsUpdate = true; }
      if (bn > 0.98) { mothMat.color.setRGB(1.5, 1.05, 0.55).multiplyScalar(lerp(1, 0.5, sk)); }
      else { mothMat.color.set('#1c2547').lerp(new THREE.Color(1.0, 0.75, 0.4), bn * 0.8); }
      // constellation: thin gold lines joining the moths of the figure outline
      figLines.visible = sk > 0.6;
      if (figLines.visible) {
        const A = figLines.geometry.attributes.iA.array, Bv = figLines.geometry.attributes.iB.array;
        for (let i = 0; i < MN; i++) { const j = (i + 1) % MN; A.set(FIG.subarray(i * 3, i * 3 + 3), i * 3); Bv.set(FIG.subarray(j * 3, j * 3 + 3), i * 3); }
        figLines.geometry.attributes.iA.needsUpdate = true; figLines.geometry.attributes.iB.needsUpdate = true;
        figLines.material.uniforms.uOpacity.value = clamp((sk - 0.6) / 0.3) * 1.0; figLines.material.uniforms.uWidth.value = o.figWidth ?? 1.6;
      }
      // clock
      const ck = o.clock ?? 0; clock.visible = ck > 0.01; clock.scale.setScalar(0.4 + 0.6 * ck);
      if (clock.visible) { clock.lookAt(cam.position); clock.userData.face.material.opacity = ck; const [hh, mm] = o.time || [9, 30];
        minH.rotation.z = -(mm / 60) * Math.PI * 2; hourH.rotation.z = -(((hh % 12) + mm / 60) / 12) * Math.PI * 2; minH.material.opacity = hourH.material.opacity = ck; }
      // car
      const cz = o.car ?? -1; tail.visible = cz >= 0; if (tail.visible) { tail.position.set(roadX(cz) + 0.75 + 1.4, 0.8, cz); tail.lookAt(roadX(cz - 4) + 0.75 + 1.4, 0.8, cz - 4); }
      // snow + sun
      snowMat.uniforms.uSnow.value = o.snow ?? 0; snow.visible = (o.snow ?? 0) > 0.01;
      const sa = o.sun ?? 0.3; skyMesh.material.uniforms.uSun.value.set(Math.cos(sa * Math.PI) * 0.8, Math.sin(sa * Math.PI) * 0.6 + 0.05, -0.6).normalize();
      if (o.paper) U.uDayPaper.value.set(o.paper);
      sheetMeshes.forEach((m) => { m.rotation.x = Math.sin(t * 2.1 + m.userData.k) * 0.25; m.rotation.z = Math.sin(t * 1.3 + m.userData.k * 2) * 0.08; });
      vMat.uniforms.uWave.value = o.wave ?? 0;
      SET.bloom = o.bloom ?? 0.55;
    },
  };
  return SET;
}
