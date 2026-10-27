"""Soften robotic AI drums (song03 "Porch Light", user 2026-10-18: drums "too robotic sometimes"; pick: softer + roomier).
Works on the drum stem only and swaps it back into the instrumental, so every other sound stays bit-identical:
    instrumental' = instrumental - drums + soft(drums)
soft(): level trim, transient softening (fast vs slow envelope -> less attack on every hit), hiss gate above
5 kHz between hits (the AI drum stem carries a constant 4-16 kHz wash), and a small drums-only room
(synthetic stereo IR, 10 ms predelay, band-limited 250 Hz-6 kHz) so the kit sits behind the piano.
Then run finish_v2.py on the new take folder (same master chain as the released version).
usage: drum_soften.py <take folder> <out take folder> [level_db=-3.5] [attack_db=-4] [room_db=-15] [gate_db=-10]"""
import glob, os, shutil, sys
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, fftconvolve

take, out = sys.argv[1:3]
LEVEL, ATTACK, ROOM, GATE = [float(x) for x in (sys.argv[3:7] + ["-3.5", "-4", "-15", "-10"][len(sys.argv[3:7]):])]
rd = lambda n: sf.read(sorted(glob.glob(os.path.join(take, n + ".*")))[0], always_2d=True)
(inst, sr), (d, _) = rd("instrumental"), rd("drums")
n = min(len(inst), len(d)); inst, d = inst[:n], d[:n]
db = lambda x: 10 ** (x / 20)


def env(x, att, rel):
    """one-pole peak envelope follower (attack/release in seconds), mono"""
    a, r = np.exp(-1 / (att * sr)), np.exp(-1 / (rel * sr))
    y = np.empty_like(x); e = 0.0
    for i, v in enumerate(x):
        c = a if v > e else r
        e = c * e + (1 - c) * v; y[i] = e
    return y


mono = np.abs(d).mean(1)
# envelopes at 1/16 rate (fast enough for transients, keeps the python loop cheap), then upsampled
k = 16
m = mono[: len(mono) // k * k].reshape(-1, k).max(1)
sr_k = sr / k
def env_k(att, rel):
    a, r = np.exp(-1 / (att * sr_k)), np.exp(-1 / (rel * sr_k)); y = np.empty_like(m); e = 0.0
    for i, v in enumerate(m):
        c = a if v > e else r; e = c * e + (1 - c) * v; y[i] = e
    return y
fast, slow = env_k(0.0008, 0.04), env_k(0.015, 0.12)
# transient = how far the fast envelope jumps above the slow one; reduce gain there (up to ATTACK dB)
tr = np.clip(20 * np.log10((fast + 1e-9) / (slow + 1e-9)), 0, 12) / 12
g_att = db(ATTACK * tr)
# hiss gate: open (1) for a short decay after each hit, GATE dB in between
hit = np.clip((fast - slow) / (slow + 1e-6), 0, None) > 0.6
open_ = np.zeros_like(m); last = -1e9
tau = 0.16 * sr_k
for i in range(len(m)):
    if hit[i]: last = i
    open_[i] = np.exp(-(i - last) / tau)
g_hiss = db(GATE) + (1 - db(GATE)) * open_
# full-band tail gate (song03 1:29 "hit, then flickering static hum"): every hit decays naturally over TAIL s,
# then the whole drum stem is held FULLGATE dB down until the next hit (env FULLGATE=-35 TAIL=0.09; off if unset)
FG = float(os.environ.get("FULLGATE", "0")); TAILS = float(os.environ.get("TAIL", "0.09"))
g_full = np.ones_like(m)
if FG < 0:
    o2 = np.zeros_like(m); last = -1e9; tau2 = TAILS * sr_k
    for i in range(len(m)):
        if hit[i]: last = i
        o2[i] = np.exp(-(i - last) / tau2)
    g_full = db(FG) + (1 - db(FG)) * o2
    # keep crescendos: song03 2:04 has a drum swell rising 37 dB over 0.7 s into the chorus (no sharp onset).
    # Hum tails DECAY after a hit; swells RISE -> stay open while the 40 ms level climbs (held 150 ms).
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    w40 = max(1, int(0.04 * sr_k)); lv = 10 * np.log10(uniform_filter1d(m ** 2, w40) + 1e-12)
    lag = max(1, int(0.06 * sr_k)); rise = np.zeros_like(lv); rise[lag:] = lv[lag:] - lv[:-lag]
    keep = np.clip(rise / 3, 0, 1) * np.clip((lv + 60) / 8, 0, 1)
    keep = maximum_filter1d(keep, int(0.15 * sr_k))
    g_full = np.maximum(g_full, keep)
    KEEP = keep
else:
    KEEP = np.zeros_like(m)
up = lambda g: np.repeat(g, k)[:n] if len(g) * k >= n else np.pad(np.repeat(g, k), (0, n - len(g) * k), mode="edge")
g_att, g_hiss, g_full, g_keep = up(g_att), up(g_hiss), up(g_full), up(KEEP)
smooth = lambda g: sosfiltfilt(butter(1, 60, fs=sr, output="sos"), g)   # no zipper noise
g_att, g_hiss, g_full, g_keep = smooth(g_att), smooth(g_hiss), smooth(g_full), smooth(g_keep)

hp = butter(4, 5000, "high", fs=sr, output="sos")
d_hi = sosfiltfilt(hp, d, axis=0); d_lo = d - d_hi
lvl_g = db(LEVEL) + (1 - db(LEVEL)) * np.clip(g_keep, 0, 1)          # swells keep their full level
soft = (d_lo + d_hi * g_hiss[:, None]) * (g_att * g_full * lvl_g)[:, None]

# small room: decorrelated stereo noise IR, RT60 ~0.45 s, 10 ms predelay, band 250 Hz - 6 kHz
rng = np.random.default_rng(7)
L = int(0.6 * sr); t = np.arange(L) / sr
ir = rng.standard_normal((L, 2)) * np.exp(-6.9 * t / 0.45)[:, None]
ir[: int(0.010 * sr)] = 0
ir = sosfilt(butter(2, [250, 6000], "band", fs=sr, output="sos"), ir, axis=0)
ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
wet = np.stack([fftconvolve(soft[:, c], ir[:, c])[:n] for c in range(2)], 1)
wet *= db(ROOM) * np.sqrt((soft ** 2).mean()) / max(np.sqrt((wet ** 2).mean()), 1e-9)
new_d = soft + (wet if ROOM > -59 else 0)
# notch tonal ringing in the drum stem (song03: 164-167 Hz "robotic hum" at 1:29), env NOTCH="165,8" (Hz,dB) list
from scipy.signal import iirpeak
for spec in [x for x in os.environ.get("NOTCH", "").split(";") if x]:
    f0, cut = [float(v) for v in spec.split(",")]
    b, a = iirpeak(f0, 12, fs=sr)                   # narrow band (Q 12) around f0
    band = np.stack([np.convolve(new_d[:, c], [1], "same") for c in range(2)], 1)
    from scipy.signal import filtfilt
    band = filtfilt(b, a, new_d, axis=0)
    new_d = new_d - band * (1 - db(-cut))

os.makedirs(out, exist_ok=True)
for f in glob.glob(os.path.join(take, "*.*")):
    shutil.copy(f, out)
sf.write(os.path.join(out, "instrumental.flac"), inst - d + new_d, sr, subtype="PCM_24")
sf.write(os.path.join(out, "drums.flac"), new_d, sr, subtype="PCM_24")
print(f"notch {os.environ.get('NOTCH', '-')}; drums: level {LEVEL} dB, attack {ATTACK} dB, room {ROOM} dB, gate {GATE} dB -> {out}")
print(f"avg attack reduction {20*np.log10(g_att.mean()):.2f} dB, hiss gate avg {20*np.log10(g_hiss.mean()):.2f} dB")
