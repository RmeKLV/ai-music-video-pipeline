// keeper.js: the woman who keeps the light on. Gold line-art on navy, drawn in code, seated in profile
// (facing right in model space), knees drawn up, arms around them, looking down the road.
// drawKeeper(c, P): model units ~ 1000 x 1500, origin at the seat (hips on the step), +y down.
// P: { open 0..1 (mouth), blink 0..1, tilt (rad, head), lift (rad, chin up), breathe 0..1, sway (hair), t,
//      line '#f0bf6c', fill '#14204a', skin '#1d2b5c', glow 0..1, pose 'sit' | 'stand' }
const TAU = Math.PI * 2;

function strokeFill(c, path, fill, line, w) {
  c.fillStyle = fill; c.fill(path);
  c.strokeStyle = line; c.lineWidth = w; c.lineJoin = 'round'; c.lineCap = 'round'; c.stroke(path);
}
const P2 = (d) => new Path2D(d);

export function drawKeeper(c, P = {}) {
  const line = P.line || '#f0bf6c', fill = P.fill || '#14204a', skin = P.skin || '#1c2a5a', lw = P.lw || 5;
  const br = (P.breathe ?? 0) * 4, t = P.t || 0;
  c.save();
  if (P.glow) { c.shadowColor = `rgba(255,180,90,${0.55 * P.glow})`; c.shadowBlur = 18; }

  // Seat on the step at (0, 0); knees drawn up and hugged; long skirt draping over them.
  const skirt = P2(`M -125 5 C -140 -60 -120 -150 -70 -200 C -20 -240 80 -262 170 -268
    C 215 -270 238 -250 240 -215 C 244 -150 256 -40 268 60 C 274 110 282 150 296 176
    C 250 186 200 184 160 178 C 120 172 70 150 40 120 C 10 92 -20 40 -60 22 C -90 10 -112 12 -125 5 Z`);
  strokeFill(c, skirt, fill, line, lw);
  // skirt folds following the drape
  c.strokeStyle = line; c.lineWidth = lw * 0.5; c.globalAlpha = 0.75;
  c.stroke(P2('M 200 -250 C 214 -150 228 -40 246 110')); c.stroke(P2('M 150 -245 C 168 -140 186 -30 210 150'));
  c.stroke(P2('M 60 -235 C 80 -180 96 -120 110 -60')); c.stroke(P2('M -40 -190 C -20 -150 0 -100 20 -60'));
  c.globalAlpha = 1;
  // shoe tips under the hem, on the lower step
  strokeFill(c, P2('M 240 176 C 262 168 300 170 318 182 C 322 190 316 196 300 196 L 242 196 Z'), skin, line, lw * 0.8);

  // ---- bodice: back curving up from the seat, leaning toward the knees
  c.save(); c.rotate(br * 0.0015);
  const bodice = P2(`M -110 -150 C -128 -230 -118 -330 -80 -400 C -60 -436 -26 -456 10 -458
    C 40 -458 66 -446 82 -424 C 104 -392 120 -340 128 -290 C 120 -250 96 -220 60 -205
    C 10 -190 -60 -178 -110 -150 Z`);
  strokeFill(c, bodice, fill, line, lw);
  c.lineWidth = lw * 0.5; c.globalAlpha = 0.7;
  c.stroke(P2('M -90 -380 C -70 -320 -56 -260 -50 -200')); c.stroke(P2('M 2 -452 C 14 -430 22 -412 26 -396')); c.globalAlpha = 1;
  // ---- head (pivot at the neck top)
  c.save(); c.translate(26, -432); c.rotate((P.tilt || 0) - (P.lift || 0) - 0.12); c.scale(0.86, 0.86);
  // neck
  strokeFill(c, P2('M -14 26 C -12 0 -8 -28 -4 -52 L 30 -52 C 28 -24 32 2 40 26 Z'), skin, line, lw * 0.9);
  // hair back + low bun
  const sway = P.sway || 0;
  strokeFill(c, P2(`M -40 -90 C -95 -120 -110 -190 -70 -235 C -30 -275 50 -272 88 -226 C 60 -224 30 -214 12 -196
    C -2 -180 -14 -150 -24 -120 C -30 -104 -34 -96 -40 -90 Z`), fill, line, lw);
  c.beginPath(); c.ellipse(-92, -120, 38, 34, 0.3, 0, TAU); c.fillStyle = fill; c.fill(); c.strokeStyle = line; c.lineWidth = lw; c.stroke();
  c.lineWidth = lw * 0.5; c.beginPath(); c.ellipse(-92, -120, 22, 18, 0.3, 0.4, 4.6); c.stroke();
  // face (profile, facing right): brow, nose, lips, chin; the jaw opens with the vocal
  const o = Math.max(0, Math.min(1, P.open || 0));
  const face = P2(`M 85 -230 C 100 -205 104 -185 100 -165 C 112 -150 122 -132 120 -122 C 118 -116 108 -114 102 -112
    C 106 -104 106 -96 102 -92 C ${104 + o * 2} ${-86 + o * 4} ${100 + o * 3} ${-80 + o * 9} ${96 + o * 2} ${-76 + o * 10}
    C ${100 + o * 2} ${-68 + o * 11} ${96 + o * 2} ${-56 + o * 12} 84 ${-48 + o * 10}
    C 64 ${-38 + o * 8} 40 -44 20 -54 C 0 -64 -16 -82 -30 -96 C 0 -130 40 -170 85 -230 Z`);
  strokeFill(c, face, skin, line, lw);
  if (o > 0.08) { c.fillStyle = '#0a1028'; c.beginPath(); c.ellipse(98 + o, -84 + o * 4, 3 + o * 3, 2 + o * 5, 0, 0, TAU); c.fill(); }
  // eye: lash line that closes with the blink; she looks down the road
  const bl = Math.max(0, Math.min(1, P.blink || 0));
  c.strokeStyle = line; c.lineWidth = lw * 0.8;
  c.beginPath(); c.moveTo(66, -170); c.quadraticCurveTo(80, -176 + bl * 8, 92, -168); c.stroke();
  if (bl < 0.7) { c.beginPath(); c.moveTo(70, -166); c.quadraticCurveTo(80, -162, 88, -165); c.lineWidth = lw * 0.45; c.stroke(); }
  c.lineWidth = lw * 0.6; c.beginPath(); c.moveTo(90, -168); c.lineTo(97, -171); c.stroke();
  // brow
  c.beginPath(); c.moveTo(62, -186); c.quadraticCurveTo(82, -194, 98, -186); c.lineWidth = lw * 0.6; c.stroke();
  // ear + loose strands over the ear, swaying
  c.beginPath(); c.ellipse(-2, -150, 12, 20, 0.2, 0, TAU); c.fillStyle = skin; c.fill(); c.lineWidth = lw * 0.6; c.stroke();
  for (let i = 0; i < 3; i++) {
    const s = sway * (0.6 + i * 0.25) + Math.sin(t * 1.3 + i) * 3;
    c.beginPath(); c.moveTo(-18 - i * 10, -175 + i * 4);
    c.bezierCurveTo(-30 - i * 8 + s * 0.4, -130, -24 - i * 6 + s, -90, -34 - i * 4 + s * 1.4, -40 + i * 10);
    c.lineWidth = lw * 0.45; c.stroke();
  }
  // hair texture lines sweeping back to the bun
  c.lineWidth = lw * 0.4; c.globalAlpha = 0.7;
  for (let i = 0; i < 4; i++) { c.beginPath(); c.moveTo(70 - i * 6, -232 + i * 5); c.quadraticCurveTo(10 - i * 6, -252 + i * 10, -64, -150 + i * 6); c.stroke(); }
  c.globalAlpha = 1;
  c.restore(); // head

  // ---- arm: from the shoulder, wrapped around the front of the shins, hands clasped
  const arm = P2(`M -30 -430 C 10 -440 40 -420 60 -390 C 90 -345 120 -300 160 -262 C 190 -236 222 -222 250 -214
    C 266 -210 274 -196 266 -184 C 258 -172 238 -174 222 -180 C 190 -192 150 -214 116 -244
    C 76 -280 40 -320 10 -360 C -10 -386 -40 -400 -30 -430 Z`);
  strokeFill(c, arm, fill, line, lw);
  strokeFill(c, P2('M 244 -218 C 262 -226 284 -222 290 -208 C 294 -196 284 -186 268 -186 C 256 -186 246 -194 244 -204 Z'), skin, line, lw * 0.8);
  c.lineWidth = lw * 0.5; c.globalAlpha = 0.7; c.stroke(P2('M 40 -400 C 70 -360 96 -322 126 -290')); c.globalAlpha = 1;
  c.restore(); // bodice
  c.restore();
}

// ------------------------------------------------------------------ performance helpers (lip sync, blinks)
export function lipOpen(LIP, t) {
  if (!LIP) return 0;
  const i = Math.max(0, Math.min(LIP.open.length - 1, Math.round(t * LIP.rate)));
  let s = 0, n = 0;
  for (let k = -3; k <= 3; k++) { const j = i + k; if (j >= 0 && j < LIP.open.length) { s += LIP.open[j]; n++; } }
  return Math.min(1, (s / n) * 1.4);
}
export function blinkAt(t, seed = 3) {
  // seeded blinks every 2.5-5 s, 0.16 s long
  const period = 3.6, k = Math.floor(t / period), r = Math.sin(k * 91.7 + seed) * 43758.5453 % 1;
  const tb = k * period + Math.abs(r) * (period - 0.4);
  const d = t - tb;
  return d > 0 && d < 0.16 ? Math.sin((d / 0.16) * Math.PI) : 0;
}
